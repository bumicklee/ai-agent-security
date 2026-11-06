"""12-3 지키기: 해시 체인 행동 기록과 감시자 투입 (7명 완성)."""
import asyncio
import json

from agents.tool_context import ToolContext

from crew.context import CrewContext, load_user
from crew.db import session, set_flag
from crew.runtime.plug import need
from crew.runtime.run import ask
from crew.team import slots

NIGHT = [("bob", 5162), ("cust04", 5036), ("cust06", 5002), ("cust08", 5290), ("cust10", 5242), ("cust30", 5086)]


def _read_audit() -> str:
    tool = need("crew.tools.watch", "read_audit", "감시자 도구 read_audit를 만든다")
    tctx = ToolContext(context=CrewContext(user=load_user("erin")), tool_name=tool.name, tool_call_id="t1",
                       tool_arguments="{}")
    return str(asyncio.run(tool.on_invoke_tool(tctx, "{}")))


def _alerts() -> list[dict]:
    with session() as db:
        return [json.loads(r["detail"]) for r in db.execute("SELECT detail FROM audit_log WHERE action = 'alert'")]


def test_기록을_고치면_감시자가_알아챈다():
    ask("alice", "배송은 얼마나 걸려요?")
    assert "체인 정상" in _read_audit(), "기대: read_audit가 해시 체인을 검사한다(crew/runtime/audit.py의 verify)"
    with session() as db:
        db.execute("UPDATE audit_log SET detail = '{\"text\": \"고친 글\"}' WHERE id = 1")  # 누군가 기록 한 줄을 고쳤다
    assert "끊겼" in _read_audit(), "기대: 고친 줄에서 체인이 끊긴 것을 보고한다"


def test_밤새_쌓이는_환불을_이상_징후로_잡는다():
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    for i, (user, order) in enumerate(NIGHT):
        set_flag("clock", f"2026-10-31T02:{i * 5:02d}:00")
        ask(user, f"주문 {order} 환불해 주세요")
    keys = {a["key"] for a in _alerts()}
    assert "night_refunds" in keys, "기대: 새벽(0~6시)에 환불이 몰리면 감시자 경보(시간 기준선)"


def test_낮에도_양이_많으면_잡는다():
    anomalies = need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    rows = [{"ts": "2026-10-31T14:00:00", "run_id": f"r{i}", "agent": "환불 담당", "action": "tool_end",
             "detail": {"tool": "request_refund", "denied": False}} for i in range(5)]
    assert "refund_volume" in {a["key"] for a in anomalies(rows)}, "기대: 한 시간에 환불 5건이면 양 기준선 경보"


def test_평소_양은_경보가_없다():
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    ask("alice", "주문 1001 환불해 주세요")
    assert not _alerts(), "기대: 환불 한 건은 이상 징후가 아니다(오탐 없음)"


def test_감시자가_들어와_7명이_된다():
    on = {s.name for s in slots() if s.active}
    assert len(on) == 7 and "감시자" in on, "기대: /ops 조직도 7칸이 모두 켜진다(crew/agents/watchdog.py의 build_watchdog)"


def test_고객_신고가_운영_화면_경보가_된다():
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    from fastapi.testclient import TestClient

    from crew.web.app import app

    c = TestClient(app)
    c.cookies.set("crew_user", "alice")
    out = c.post("/api/chat", json={"text": "배송은 얼마나 걸려요?"}).json()
    assert "신고" in c.get("/chat").text, "기대: /chat 답 옆에 신고 버튼(12-3부터)"
    note = c.post("/api/report", json={"run_id": out["run_id"], "reason": "엉뚱한 답"}).json()["note"]
    assert "받았습니다" in note, f"기대: 내가 받은 답은 신고된다 ({note})"
    assert "customer_report" in {a["key"] for a in _alerts()}, "기대: 신고는 감시자 경보가 된다(ASI09-M4)"
    assert "고객 신고" in TestClient(app).get("/ops").text, "기대: /ops 감시자 칸에 고객 신고가 보인다"
    c.cookies.set("crew_user", "bob")
    assert c.post("/api/report", json={"run_id": out["run_id"]}).json()["note"].startswith("거부"), "기대: 남의 답은 신고 못 한다"


def test_담당별_속도_제한(monkeypatch):
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    import crew.runtime.watch as w

    monkeypatch.setattr(w, "RATE_PER_MIN", 2)  # 한도를 낮춰 본다(기본 30)
    outs = [ask("alice", f"주문 {n} 보여 주세요") for n in (1001, 1002, 1001)]
    assert outs[0].blocked_by is None and outs[1].blocked_by is None, "기대: 한도 안의 호출은 그대로"
    assert outs[2].blocked_by == "code" and "너무 빠릅니다" in outs[2].reply, "기대: 1분에 한도를 넘긴 담당은 '거부:'(ASI08-M6)"


def test_새로_닿는_권한을_경보한다():
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    from crew.runtime.watch import patrol, reach

    base = reach()
    assert "request_refund" in base["감독자"], "기대: 감독자는 환불 담당을 거쳐 request_refund에 닿는다(전이 권한)"
    base["감독자"] = [t for t in base["감독자"] if t != "request_refund"]  # 어제의 기준선에는 없었다고 치자
    set_flag("perm_baseline", json.dumps(base, ensure_ascii=False))
    patrol()
    alert = next((a for a in _alerts() if a["key"] == "new_permission"), None)
    assert alert and alert["agent"] == "감독자" and "request_refund" in alert["tools"] and "전이" in alert["why"], \
        "기대: 담당이 새로(전이로) 닿는 도구가 생기면 경보(ASI03-M8)"


def test_에이전트_사이_권한_상승을_경보한다():
    need("crew.guards.watch", "anomalies", "감시 규칙 anomalies(rows)를 만든다")
    from crew.runtime.bus import deliver
    from crew.runtime.watch import patrol
    from crew.team import walk

    refunds = next(a for a in walk() if a.name == "환불 담당")
    ctx = CrewContext(user=load_user("dave"), run_id="elev0001")
    asyncio.run(deliver(ctx, "리포트 담당", refunds, "refunds", "주문 1001 환불해 주세요"))
    patrol()
    alert = next((a for a in _alerts() if a["key"] == "agent_elevation"), None)
    assert alert and alert["agent"] == "리포트 담당", "기대: 리포트 담당이 환불을 맡기려 하면 경보(ASI03-M9)"
