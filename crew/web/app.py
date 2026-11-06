"""화면 4개: /chat(고객) · /inbox(메일 문의) · /staff(직원) · /ops(운영). 127.0.0.1 전용.

로그인은 랩용 가짜 로그인이다(선택 상자 + 쿠키). 실제 서비스에서는 이렇게 하지 않는다.
수강생은 이 파일을 고치지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from crew import course
from crew.context import list_login_users, load_user
from crew.db import get_flag, session, set_flag
from crew.redteam import load as load_scenarios, run_scenario
from crew.runtime.audit import total_cost, verify as verify_chain
from crew.runtime.watch import active as watch_active, alerts as watch_alerts, ask_watchdog, report as watch_report
from crew.runtime.llm import model_label
from crew.runtime import approvals as approval_queue
from crew.runtime.plug import student
from crew.runtime.run import act_async, ask_async
from crew.config import get_settings
from crew.team import slots, tool_names

HERE = Path(__file__).parent
app = FastAPI(title="cs-crew")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")


def _user(request: Request):
    uid = request.cookies.get("crew_user", "alice")
    try:
        return load_user(uid)
    except KeyError:
        return load_user("alice")


def _page(request: Request, name: str, **extra):
    base = {"me": _user(request), "users": list_login_users(), "model": model_label(), "page": name}
    return templates.TemplateResponse(request, f"{name}.html", base | extra)


def _unlocked(no: str) -> bool:
    return course.norm(no) in course.done()


@app.get("/")
def home():
    return RedirectResponse("/chat")


@app.post("/login")
def login(user: str = Form(...), back: str = Form("/chat")):
    resp = RedirectResponse(back if back.startswith("/") else "/chat", status_code=303)
    resp.set_cookie("crew_user", user, httponly=True, samesite="strict")
    return resp


@app.get("/chat")
def chat_page(request: Request):
    return _page(request, "chat", report_on=watch_active())


@app.post("/api/report")
async def api_report(request: Request):
    """12-3 고객 신고 버튼(ASI09-M4). 내가 받은 답 하나를 신고하면 /ops 감시자 칸에 경보가 뜬다."""
    if not watch_active():
        raise HTTPException(404, "12-3 수업에서 만듭니다")
    body = await request.json()
    return {"note": watch_report(_user(request).id, str(body.get("run_id", "")), str(body.get("reason", ""))[:200])}


@app.post("/api/chat")
async def api_chat(request: Request):
    body = await request.json()
    text = str(body.get("text", "")).strip()[:2000]
    if not text:
        raise HTTPException(400, "빈 메시지")
    out = await ask_async(_user(request).id, text, remember=True)
    return _out(out)


@app.get("/inbox")
def inbox_page(request: Request):
    with session() as db:
        rows = db.execute("SELECT t.*, u.name FROM tickets t JOIN users u ON u.id = t.customer_id "
                          "WHERE channel = 'email' ORDER BY t.id LIMIT 30").fetchall()
    return _page(request, "inbox", tickets=rows)


@app.post("/api/inbox/{ticket_id}")
async def api_inbox(ticket_id: int):
    with session() as db:
        t = db.execute("SELECT * FROM tickets WHERE id = ? AND channel = 'email'", (ticket_id,)).fetchone()
    if t is None:
        raise HTTPException(404, "없는 메일")
    out = await ask_async(t["customer_id"], t["body"], channel="email")
    return _out(out)


def _out(out) -> dict:
    return {"reply": out.reply, "agent": out.agent, "blocked_by": out.blocked_by, "tools": out.tools,
            "approval_id": out.approval_id, "run_id": out.run_id}


@app.get("/staff")
def staff_page(request: Request):
    me = _user(request)
    with session() as db:
        tickets = db.execute("SELECT t.*, u.name, u.store_id FROM tickets t JOIN users u ON u.id = t.customer_id "  # 자기 매장만
                             "WHERE t.status = 'open' AND u.store_id = ? AND ? ORDER BY t.id LIMIT 30",
                             (me.store_id, me.is_staff)).fetchall()
        memories = db.execute("SELECT m.* FROM memories m JOIN users u ON u.id = m.customer_id "  # 직원: 자기 매장 고객만
                              "WHERE u.store_id = ? AND ? ORDER BY m.id DESC LIMIT 30",
                              (me.store_id, me.is_staff)).fetchall()
        n_approvals = db.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
    try:
        tools = tool_names()
    except Exception:  # 학생 코드가 잠시 깨져 있어도 화면은 뜬다
        tools = set()
    # 잠긴 칸은 그 기능의 도구가 팀에 생기면 열린다(진도 표시와 상관없이)
    panels = {"approvals": "request_refund" in tools or n_approvals > 0, "delegate": "staff_change_address" in tools,
              "memories": "remember" in tools, "review": bool(student("crew.guards.memory", "review")),
              "reports": "run_python" in tools}
    return _page(request, "staff", tickets=tickets, approvals=approval_queue.pending(me.store_id) if me.is_staff else [], memories=memories,
                 panels=panels, is_staff=me.is_staff)


@app.post("/api/approvals/{approval_id}")
async def api_approval(approval_id: int, request: Request):
    body = await request.json()
    return await approval_queue.decide_async(approval_id, _user(request).id, bool(body.get("approve")))


@app.post("/api/memories/{memo_id}")
async def api_memory(memo_id: int, request: Request):
    review = student("crew.guards.memory", "review")  # 8-4
    if not review:
        raise HTTPException(404, "8-4 수업에서 만듭니다")
    return {"note": review(_user(request), memo_id, str((await request.json()).get("action", "")))}


@app.post("/api/memories/rollback/{customer_id}")
def api_memory_rollback(customer_id: str, request: Request):
    rollback = student("crew.guards.memory", "rollback")
    if not rollback:
        raise HTTPException(404, "8-4 수업에서 만듭니다")
    return {"note": rollback(_user(request), customer_id)}


@app.post("/api/staff/report")
async def api_staff_report(request: Request):
    me = _user(request)
    if not me.is_staff:
        raise HTTPException(403, "직원만 리포트를 만듭니다")
    return _out(await ask_async(me.id, "지난주 환불 통계 차트 그려 줘"))


@app.post("/api/staff/act/{ticket_id}")
async def api_staff_act(ticket_id: int, request: Request):
    me = _user(request)
    if not me.is_staff:
        raise HTTPException(403, "직원만 대신 처리할 수 있습니다")
    try:
        return _out(await act_async(me.id, ticket_id))
    except KeyError:
        raise HTTPException(404, "없는 문의")


def _ops_state() -> dict:
    with session() as db:
        rows = db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 60").fetchall()
        paused = db.execute("SELECT name FROM lab_flags WHERE name LIKE 'pause:%' AND value = 'on'").fetchall()
        mcp_blocked = db.execute("SELECT name FROM lab_flags WHERE name LIKE 'mcp_block:%' AND value = 'on'").fetchall()
    timeline = [{"ts": r["ts"][11:], "run": r["run_id"], "user": r["user_id"], "agent": r["agent"],
                 "action": r["action"], "detail": json.loads(r["detail"])} for r in rows]
    return {
        "slots": [{"name": s.name, "agent": s.agent, "joins": s.joins, "active": s.active} for s in slots()],
        "timeline": timeline,
        "cost": round(total_cost(), 4), "max_usd": get_settings().max_usd,
        "kill": get_flag("kill_switch") == "on",
        "chain": verify_chain(),
        "alerts": watch_alerts(8),
        "controls": bool(student("crew.guards.killswitch", "pause_agent")),
        "paused": [r["name"][6:] for r in paused],
        "mcp_blocked": [r["name"][10:] for r in mcp_blocked],
        "map": [{"name": n, "level": lvl, "gauge": course.gauge(lvl)} for n, lvl in course.owasp_map()],
    }


@app.get("/ops")
def ops_page(request: Request):
    return _page(request, "ops", state=_ops_state(), scenarios=load_scenarios())


@app.get("/api/ops")
def api_ops():
    return _ops_state()


@app.post("/api/kill")
async def api_kill(request: Request):
    on = bool((await request.json()).get("on"))
    set_flag("kill_switch", "on" if on else "off")
    return {"kill": on}


def _killswitch(name: str):
    fn = student("crew.guards.killswitch", name)  # 12-4
    if not fn:
        raise HTTPException(404, "12-4 수업에서 만듭니다")
    return fn


@app.post("/api/ops/pause")
async def api_ops_pause(request: Request):
    body = await request.json()
    return {"note": _killswitch("pause_agent")(str(body.get("agent", "")), bool(body.get("on", True)))}


@app.post("/api/ops/revoke")
def api_ops_revoke():
    return {"note": _killswitch("revoke_all_tokens")()}


@app.post("/api/ops/mcp")
async def api_ops_mcp(request: Request):
    body = await request.json()
    return {"note": _killswitch("block_mcp")(str(body.get("name", "carrier")), bool(body.get("on", True)))}


@app.post("/api/ops/watchdog")
async def api_ops_watchdog(request: Request):
    return {"note": await ask_watchdog(_user(request).id)}


@app.post("/api/redteam/{sid}")
def api_redteam(sid: int):
    sc = next((s for s in load_scenarios() if s["id"] == sid), None)
    if sc is None:
        raise HTTPException(404, "없는 시나리오")
    return JSONResponse(run_scenario(sc))
