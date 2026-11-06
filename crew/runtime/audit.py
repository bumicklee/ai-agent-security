"""행동 기록과 요금 미터. /ops 화면의 타임라인·요금 미터가 여기서 읽는다.

기록은 해시 체인으로 잇는다(앞 줄의 hash가 다음 줄의 prev_hash). 12-3에서 이 체인이 왜 필요한지 본다.
- verify(): 체인을 처음부터 다시 계산해, 누가 기록을 고치거나 지웠으면 그 줄 번호를 돌려준다(12-3)
- 에이전트가 시작할 때 멈춤 표시(lab_flags의 pause:<이름>)가 있으면 막는다(12-4 킬 스위치)
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from agents import Agent, RunContextWrapper, RunHooks, Tool

from crew.config import get_settings
from crew.context import CrewContext
from crew.db import session


import contextvars

# 지금 처리 중인 요청의 run_id. 브로커(비밀값)처럼 ctx를 받지 않는 완성본 코드도 같은 요청 번호로 기록하게 한다
CURRENT_RUN: contextvars.ContextVar[str] = contextvars.ContextVar("crew_run_id", default="svc")
# 지금 요청한 사람(User). 샌드박스(9-4)가 DB 사본을 그 사람 매장 것만 담을 때 쓴다
CURRENT_USER: contextvars.ContextVar[Any] = contextvars.ContextVar("crew_user", default=None)


def _now() -> str:
    from crew.runtime.clock import stamp

    return stamp()  # 랩 시계(보통은 진짜 시각)


def _scrub(body: str) -> str:
    """4-5: 학생의 crew/guards/pii.py에 scrub_log가 있으면 기록 전에 개인정보를 가린다."""
    from crew.runtime.plug import student

    scrub = student("crew.guards.pii", "scrub_log")
    if not scrub:
        return body
    out = scrub(body)
    try:
        json.loads(out)
        return out
    except ValueError:
        # Presidio(선택 설치)가 따옴표까지 걸친 "이름"을 가리면 JSON이 깨진다(타임라인·도구 목록이 읽지 못함).
        # 그때는 값 하나하나를 가린 뒤 다시 JSON으로 만든다
        def each(v):
            if isinstance(v, str):
                return scrub(v)
            if isinstance(v, dict):
                return {k: each(x) for k, x in v.items()}
            if isinstance(v, list):
                return [each(x) for x in v]
            return v
        return json.dumps(each(json.loads(body)), ensure_ascii=False, sort_keys=True)


def record(run_id: str, user_id: str | None, agent: str, action: str, detail: dict[str, Any]) -> None:
    body = _scrub(json.dumps(detail, ensure_ascii=False, sort_keys=True))
    with session() as db:
        row = db.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else "0" * 16
        ts = _now()
        h = _hash(prev, ts, run_id, agent, action, body)
        db.execute("INSERT INTO audit_log(ts, run_id, user_id, agent, action, detail, prev_hash, hash) "
                   "VALUES (?,?,?,?,?,?,?,?)", (ts, run_id, user_id, agent, action, body, prev, h))


def _hash(prev: str, ts: str, run_id: str, agent: str, action: str, body: str) -> str:
    return hashlib.sha256(f"{prev}|{ts}|{run_id}|{agent}|{action}|{body}".encode()).hexdigest()[:16]


def verify() -> dict:
    """12-3: 해시 체인 검사. {"ok": bool, "rows": 줄 수, "bad_id": 처음 어긋난 줄 번호 또는 None, "why": …}"""
    prev = "0" * 16
    with session() as db:
        rows = db.execute("SELECT * FROM audit_log ORDER BY id").fetchall()
    for r in rows:
        if r["prev_hash"] != prev:
            return {"ok": False, "rows": len(rows), "bad_id": r["id"], "why": "앞 줄과 이어지지 않습니다(지워졌거나 끼워 넣음)"}
        if _hash(prev, r["ts"], r["run_id"], r["agent"], r["action"], r["detail"]) != r["hash"]:
            return {"ok": False, "rows": len(rows), "bad_id": r["id"], "why": "내용이 기록 뒤에 바뀌었습니다"}
        prev = r["hash"]
    return {"ok": True, "rows": len(rows), "bad_id": None, "why": ""}


def add_usage(agent: str, tokens_in: int, tokens_out: int, user_id: str | None = None, run_id: str = "") -> float:
    s = get_settings()
    cost = tokens_in / 1e6 * s.price_in + tokens_out / 1e6 * s.price_out
    with session() as db:
        db.execute("INSERT INTO usage(ts, agent, model, tokens_in, tokens_out, cost_usd, user_id, run_id) "
                   "VALUES (?,?,?,?,?,?,?,?)",
                   (_now(), agent, s.llm_mode if s.llm_mode in ("fake", "local") else s.model,
                    tokens_in, tokens_out, cost, user_id, run_id))
    return cost


def total_cost() -> float:
    with session() as db:
        return float(db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM usage").fetchone()[0])


class AuditHooks(RunHooks[CrewContext]):
    """에이전트가 움직일 때마다 한 줄씩 남긴다."""

    def _ids(self, ctx: RunContextWrapper[CrewContext]) -> tuple[str, str]:
        return ctx.context.run_id, ctx.context.user.id

    async def on_agent_start(self, context, agent: Agent) -> None:
        from crew.db import get_flag
        from crew.runtime.errors import Denied

        if get_flag(f"pause:{agent.name}") == "on":  # 12-4: 멈춘 담당은 일을 시작하지 못한다
            record(*self._ids(context), agent.name, "blocked", {"by": "pause"})
            raise Denied(f"거부: '{agent.name}'은(는) 지금 멈춰 있습니다(감시자·운영자가 멈춤). 잠시 뒤 다시 시도해 주세요.")
        record(*self._ids(context), agent.name, "agent_start", {})

    async def on_handoff(self, context, from_agent: Agent, to_agent: Agent) -> None:
        record(*self._ids(context), from_agent.name, "handoff", {"to": to_agent.name})

    async def on_tool_start(self, context, agent: Agent, tool: Tool) -> None:
        from crew.runtime.errors import Denied
        from crew.runtime.watch import rate_check

        CURRENT_USER.set(context.context.user)
        if why := rate_check(agent.name):  # 12-3: 담당별 속도 제한(ASI08-M6)
            record(*self._ids(context), agent.name, "blocked", {"by": "rate", "tool": tool.name, "why": why})
            raise Denied(why)
        record(*self._ids(context), agent.name, "tool_start",
               {"tool": tool.name, "args": getattr(context, "tool_arguments", "")})

    async def on_tool_end(self, context, agent: Agent, tool: Tool, result: object) -> None:
        text = str(result)
        record(*self._ids(context), agent.name, "tool_end",
               {"tool": tool.name, "result": text[:300], "denied": text.startswith("거부")})

    async def on_llm_end(self, context, agent: Agent, response) -> None:
        run_id, user_id = self._ids(context)
        add_usage(agent.name, response.usage.input_tokens, response.usage.output_tokens, user_id, run_id)
