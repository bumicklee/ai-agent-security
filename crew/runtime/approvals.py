"""승인 대기열(완성본). 6-1부터 쓴다.

도구에 `needs_approval`이 붙어 있으면 SDK는 실행을 멈추고 `result.interruptions`를 돌려준다.
여기서 하는 일
1. save(): `result.to_state().to_json()`을 approvals 테이블에 저장한다. 화면에 보일 diff·위험 색·필요한 승인자 수는
   학생의 `crew/guards/approval.py`의 `describe()`가 있으면 그것으로 채운다(6-4·6-5). 없으면 모델이 쓴 요약만 보인다(6-2 사고)
2. decide(): 직원이 승인·거절하면 `RunState.from_json()`으로 되살려 `approve()`/`reject()` 뒤 이어서 실행한다.
   두 사람 승인(approvers=2)이면 서로 다른 두 사람이 승인해야 실행된다. 학생의 `can_decide()`가 있으면 먼저 묻는다(7-4)
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from agents import (MaxTurnsExceeded, ModelBehaviorError, OutputGuardrailTripwireTriggered, RunContextWrapper, RunState,
                    Runner)

from crew.context import CrewContext, load_user
from crew.db import session
from crew.runtime.errors import Denied
from crew.runtime.plug import student
from crew.runtime.sync import run_sync


def _now() -> str:
    from crew.runtime.clock import stamp

    return stamp()  # 랩 시계(보통은 진짜 시각)


def _args(item: Any) -> dict:
    try:
        return json.loads(getattr(item, "arguments", None) or "{}")
    except ValueError:
        return {}


def save(result: Any, ctx: CrewContext) -> int:
    """멈춘 실행 하나를 승인 대기 한 줄로 저장하고 번호를 돌려준다."""
    items = list(result.interruptions)
    first = items[0]
    action = getattr(first, "name", None) or getattr(first, "tool_name", "") or "tool"
    args = _args(first)
    info = {"diff": None, "risk": "unknown", "approvers": 1}
    describe = student("crew.guards.approval", "describe")
    if describe:
        info |= describe(action, args, ctx.user) or {}
    state = result.to_state().to_json(context_serializer=lambda c: c.to_json())
    with session() as db:
        cur = db.execute(
            "INSERT INTO approvals(action, payload_json, run_state_json, diff, risk, status, created_at, run_id, user_id,"
            " store_id, summary, approvers) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (action, json.dumps({"calls": [{"tool": getattr(i, "name", ""), "args": _args(i)} for i in items]},
                                ensure_ascii=False),
             json.dumps(state, ensure_ascii=False), info["diff"], info["risk"], "pending", _now(), ctx.run_id,
             ctx.user.id, ctx.user.store_id, str(args.get("summary", ""))[:200] or None, int(info["approvers"])))
        return int(cur.lastrowid)


def _session(ctx: CrewContext):
    """승인을 요청한 대화의 기록(SQLiteSession). 이어서 실행한 결과도 같은 기록에 남겨야 다음 요청이 꼬이지 않는다."""
    from agents import SQLiteSession

    from crew.config import get_settings

    return SQLiteSession(ctx.session, get_settings().sessions_path) if ctx.session else None


def card(row: Any) -> dict:
    """승인 화면 카드 한 장(직원 콘솔·레드팀 직원 봇이 같은 것을 본다)."""
    payload = json.loads(row["payload_json"])
    return {"id": row["id"], "action": row["action"], "summary": row["summary"], "diff": row["diff"],
            "risk": row["risk"], "approvers": row["approvers"], "status": row["status"],
            "decided_by": row["decided_by"], "store_id": row["store_id"], "user_id": row["user_id"],
            "calls": payload.get("calls", [])}


def pending(store_id: str | None = None) -> list[dict]:
    """대기 중인 승인. store_id를 주면 그 매장 요청만(직원 콘솔은 자기 매장 것만 보여 준다)."""
    with session() as db:
        rows = db.execute("SELECT * FROM approvals WHERE status = 'pending' AND (? IS NULL OR store_id = ?) ORDER BY id",
                          (store_id, store_id)).fetchall()
    return [card(r) for r in rows]


def pending_for_run(run_id: str) -> int | None:
    """이 요청(run_id)이 만든 대기 중 승인 번호(마지막 것)."""
    with session() as db:
        row = db.execute("SELECT MAX(id) FROM approvals WHERE run_id = ? AND status = 'pending'", (run_id,)).fetchone()
    return row[0] if row and row[0] else None


def get(approval_id: int) -> Any:
    with session() as db:
        return db.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()


async def decide_async(approval_id: int, staff_id: str, approve: bool) -> dict:
    from crew.runtime.audit import AuditHooks, record
    from crew.runtime.run import _run_config
    from crew.team import entry_agent

    staff = load_user(staff_id)
    row = get(approval_id)
    if row is None:
        return {"status": "missing", "note": "없는 승인 요청입니다."}
    if row["status"] != "pending":
        return {"status": row["status"], "note": "이미 결정된 요청입니다."}
    if not staff.is_staff:
        return {"status": "pending", "note": "거부: 직원만 승인할 수 있습니다."}
    can_decide = student("crew.guards.approval", "can_decide")
    why = can_decide(staff, card(row)) if can_decide else None
    if why:
        record(row["run_id"] or "", staff.id, "staff", "approval_denied", {"approval": approval_id, "why": why})
        return {"status": "pending", "note": why if why.startswith("거부") else f"거부: {why}"}

    if approve and row["approvers"] >= 2 and row["decided_by"] is None:
        with session() as db:
            db.execute("UPDATE approvals SET decided_by = ? WHERE id = ?", (staff.id, approval_id))
        record(row["run_id"] or "", staff.id, "staff", "approval_first", {"approval": approval_id})
        return {"status": "pending", "note": "첫 번째 승인을 받았습니다. 다른 직원의 두 번째 승인이 필요합니다."}
    if approve and row["approvers"] >= 2 and row["decided_by"] == staff.id:
        return {"status": "pending", "note": "거부: 같은 사람이 두 번 승인할 수 없습니다."}

    agent = entry_agent()
    data = json.loads(row["run_state_json"])
    ctx = CrewContext.from_json(data.get("context", {}).get("context") or {"user": row["user_id"],
                                                                         "run_id": row["run_id"]})
    from crew.runtime.audit import CURRENT_RUN, CURRENT_USER
    from crew.runtime.mcp_link import attached

    CURRENT_RUN.set(ctx.run_id)
    CURRENT_USER.set(ctx.user)  # 요청한 사람(승인한 직원이 아니라)
    async with attached(agent):  # 되살릴 때도 도구 목록이 필요하다(MCP 서버 포함)
        return await _resume(agent, data, ctx, row, staff, approve, approval_id)


async def _resume(agent, data: dict, ctx: CrewContext, row: Any, staff, approve: bool, approval_id: int) -> dict:
    from crew.runtime.audit import AuditHooks, record
    from crew.runtime.run import _run_config

    state = await RunState.from_json(agent, data, context_override=RunContextWrapper(ctx))
    for item in state.get_interruptions():
        if approve:
            state.approve(item)
        else:
            state.reject(item, rejection_message="거부: 직원이 승인하지 않았습니다.")
    second = row["approvers"] >= 2 and approve
    with session() as db:
        db.execute("UPDATE approvals SET status = ?, decided_by = ?, decided_by_2 = ?, decided_at = ? WHERE id = ?",
                   ("approved" if approve else "rejected", row["decided_by"] if second else staff.id,
                    staff.id if second else None, _now(), approval_id))
    record(ctx.run_id, staff.id, "staff", "approved" if approve else "rejected", {"approval": approval_id})
    try:
        result = await Runner.run(agent, state, hooks=AuditHooks(), run_config=_run_config(), max_turns=8,
                                  session=_session(ctx))
    except Denied as e:
        reply = str(e)
    except MaxTurnsExceeded:  # 진짜 모델이 승인 뒤 같은 도구를 되풀이할 때(2026-11-06 Bedrock 실측, 15번)
        reply = "처리가 너무 길어져 멈췄습니다(최대 8턴)."
        record(ctx.run_id, ctx.user.id, "staff", "max_turns", {"max_turns": 8, "approval": approval_id})
    except ModelBehaviorError as e:  # 진짜 모델이 없는 도구 이름을 부를 때 등
        reply = "처리 중 모델 응답 오류로 멈췄습니다."
        record(ctx.run_id, ctx.user.id, "staff", "model_error", {"why": str(e)[:200], "approval": approval_id})
    except OutputGuardrailTripwireTriggered:
        reply = "죄송합니다. 이 요청은 처리할 수 없습니다."
        record(ctx.run_id, ctx.user.id, "staff", "blocked", {"by": "guardrail", "which": "OutputGuardrail"})
    else:
        from crew.runtime.run import _tool_rejections

        _tool_rejections(result, ctx, result.last_agent.name)
        if result.interruptions:
            new_id = save(result, ctx)
            reply = f"이어서 다른 승인이 필요합니다(승인 #{new_id})."
        else:
            reply = str(result.final_output)
    with session() as db:
        db.execute("UPDATE approvals SET result = ? WHERE id = ?", (reply[:500], approval_id))
    record(ctx.run_id, ctx.user.id, "staff", "reply", {"text": reply[:300], "approval": approval_id})
    return {"status": "approved" if approve else "rejected", "reply": reply}


def decide(approval_id: int, staff_id: str, approve: bool) -> dict:
    return run_sync(decide_async(approval_id, staff_id, approve))
