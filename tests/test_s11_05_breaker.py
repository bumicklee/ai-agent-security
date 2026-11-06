"""11-5 서킷 브레이커·타임아웃·재시도 예산, 미션(담당별 브레이커)."""
import json

from crew.db import get_flag, session, set_flag
from crew.runtime.run import ask

FLAKY = "운송장 FAKE-TRK-001001 배송 조회하고 주문 1002 배송지를 서울시 가짜구 예시길 30으로 바꿔 주세요"


def _calls(run_id: str, tool: str) -> int:
    with session() as db:
        return db.execute("SELECT COUNT(*) FROM audit_log WHERE run_id = ? AND action = 'tool_start' AND detail LIKE ?",
                          (run_id, f'%"{tool}"%')).fetchone()[0]


def test_재시도_폭주가_멈춘다():
    set_flag("carrier_mode", "flaky")
    out = ask("alice", FLAKY)
    assert _calls(out.run_id, "track_shipment") <= 2, "기대: 같은 일은 재시도 예산(1번)까지만 다시 맡긴다"
    assert "최대" not in out.reply and out.blocked_by == "code", "기대: 최대 턴까지 가지 않고 '거부:'로 멈춘다(③ 내 코드)"


def test_서킷이_열리고_시간이_지나면_닫힌다():
    set_flag("carrier_mode", "flaky")
    ask("alice", FLAKY)
    st = json.loads(get_flag("breaker:주문 담당") or "{}")
    assert st.get("open_until"), "기대: 주문 담당이 잇따라 실패하면 서킷이 열린다(breaker:주문 담당)"
    set_flag("carrier_mode", "normal")
    again = ask("alice", FLAKY)
    assert _calls(again.run_id, "track_shipment") == 0, "기대: 서킷이 열린 동안은 주문 담당에게 맡기지 않는다"
    set_flag("clock", "2030-01-01T00:00:00")  # 랩 시계를 쿨다운 뒤로
    later = ask("alice", FLAKY)
    assert _calls(later.run_id, "track_shipment") == 1, "기대: 쿨다운이 지나면 다시 맡긴다(반쯤 열림 → 닫힘)"


def test_느린_담당은_시간_제한으로_끊는다(monkeypatch):
    import crew.guards.breaker as b

    monkeypatch.setattr(b, "TIMEOUT_S", 0.5)
    set_flag("carrier_mode", "slow")  # 택배사 조회가 2초 걸린다
    out = ask("alice", FLAKY)
    assert "시간 초과" in out.reply or "거부" in out.reply, "기대: TIMEOUT_S를 넘긴 담당은 실패로 본다"


def test_미션_한_담당이_멈춰도_다른_담당은_일한다():
    set_flag("carrier_mode", "flaky")
    ask("alice", FLAKY)  # 주문 담당 서킷이 열린다
    set_flag("carrier_mode", "normal")
    out = ask("alice", "주문 1002 배송지를 서울시 가짜구 예시길 30으로 바꾸고 주문 1001 환불해 주세요")
    with session() as db:
        n = db.execute("SELECT COUNT(*) FROM refunds WHERE order_id = 1001").fetchone()[0]
        address = db.execute("SELECT address FROM orders WHERE id = 1002").fetchone()[0]
    assert "서킷" in out.reply and address != "서울시 가짜구 예시길 30", \
        "기대: 주문 담당 서킷이 열린 동안은 주문 일(배송지 변경)을 맡기지 않는다"
    assert n == 1, "기대: 브레이커는 담당별 — 주문 담당이 멈춰도 환불 담당은 그대로 일한다"
