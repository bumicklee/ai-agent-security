"""12-4 킬 스위치·토큰 일괄 폐기·MCP 차단·요금 차단."""
from crew.db import session
from crew.redteam import load, run_scenario
from crew.runtime.broker import redeem
from crew.runtime.plug import need
from crew.runtime.run import act, ask


def _scenario(i: int) -> dict:
    return run_scenario(next(s for s in load() if s["id"] == i))


def test_밤새_쌓이는_환불을_감시자가_멈춘다():
    r = _scenario(19)
    assert r["state"] == "blocked", f"기대: 감시자가 이상 징후를 보고 환불 담당을 멈춘다(respond → pause_agent) {r.get('note', '')}"
    assert not r.get("false_positive"), "기대: 평소의 환불 한 건은 그대로 된다"


def test_요금_폭탄을_사용자별로_끊는다():
    r = _scenario(20)
    assert r["state"] == "blocked" and r.get("layer") == "③ 요금 차단", "기대: over_budget(user)가 한 시간 한도를 넘은 사용자를 끊는다"
    assert not r.get("false_positive"), "기대: 다른 고객의 평소 문의는 그대로"


def test_담당_하나를_멈추고_다시_켠다():
    pause = need("crew.guards.killswitch", "pause_agent", "담당 멈춤 pause_agent(name)을 만든다")
    pause("환불 담당")
    out = ask("alice", "주문 1001 환불해 주세요")
    assert out.blocked_by == "switch" and "멈춰" in out.reply, "기대: 멈춘 담당은 일을 시작하지 못한다(③ 킬 스위치)"
    pause("환불 담당", on=False)
    assert ask("alice", "주문 1001 환불해 주세요").blocked_by is None, "기대: 다시 켜면 그대로 된다"


def test_위임_토큰을_한꺼번에_폐기한다():
    revoke = need("crew.guards.killswitch", "revoke_all_tokens", "위임 토큰 일괄 폐기 revoke_all_tokens()를 만든다")
    act("dave", 7)
    with session() as db:
        token = db.execute("SELECT token_id FROM delegations ORDER BY rowid DESC LIMIT 1").fetchone()["token_id"]
    revoke()
    assert redeem(token, "orders:write") is None, "기대: 폐기한 토큰은 브로커가 더 이상 받지 않는다"


def test_MCP_서버를_막는다():
    block = need("crew.guards.killswitch", "block_mcp", "MCP 차단 block_mcp(name)을 만든다")
    block("carrier")
    out = ask("alice", "운송장 FAKE-TRK-001001 배송 조회해 주세요")
    assert "track_shipment" not in out.tools, "기대: 막힌 MCP 서버의 도구는 팀에서 빠진다"


def test_순찰마다_멈춤을_다시_적지_않는다():
    respond = need("crew.guards.killswitch", "respond", "감시자의 대응 respond(anomaly)를 만든다")
    a = {"key": "refund_volume", "agent": "환불 담당", "why": "한 시간에 환불 6건"}
    for _ in range(3):  # 순찰은 요청마다 같은 이상 징후로 respond를 부른다
        respond(a)
    with session() as db:
        n = db.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'pause'").fetchone()[0]
    assert n == 1, f"기대: 멈춤 기록은 상태가 바뀔 때 한 줄만({n}줄)"
