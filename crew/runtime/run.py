"""한 번 묻고 답 받기. 화면(/chat·/inbox·/staff), 레드팀 콘솔, 시험이 모두 이 함수를 부른다.

여기가 대기업 고객센터의 "게이트웨이" 자리다. 요청 하나가 들어오면 차례로
1. 킬 스위치·요금 차단(랩 전체 LAB_MAX_USD, 12-4부터는 학생의 `crew/guards/killswitch.py`의 `over_budget()`로 사용자별)
2. 개인정보 가리기(4-3): 학생의 `crew/guards/pii.py`에 `mask()`가 있으면 모델에 보내기 전에 부른다
   (웹 미들웨어가 하던 일을 여기서 한다. 화면·메일·레드팀이 모두 이 길로 들어오기 때문이다)
3. 에이전트 팀 실행. 가드레일 트립와이어·`Denied`·승인 대기(6-1)를 점수판 약속대로 기록한다
   팀이 MCP 서버를 쓰면(10-1) 이 실행 동안만 잇는다(crew/runtime/mcp_link.py). 최대 턴(8)을 넘으면 멈춘다(11-2)
4. 답에서 되돌리기(4-4): `unmask()`가 있으면 고객에게 보여도 되는 값만 되돌린다
5. 감시자 순찰(12-3): 학생의 `crew/guards/watch.py`가 있으면 요청마다 행동 기록을 훑는다(crew/runtime/watch.py)
"""
from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass, field

from agents import (InputGuardrailTripwireTriggered, MaxTurnsExceeded, ModelBehaviorError,
                    OutputGuardrailTripwireTriggered, RunConfig, Runner, SQLiteSession)

from crew.config import get_settings
from crew.context import CrewContext, load_user
from crew.db import get_flag, session
from crew.runtime.audit import CURRENT_RUN, CURRENT_USER, AuditHooks, record, total_cost
from crew.runtime.errors import Denied
from crew.runtime.mcp_link import attached
from crew.runtime.plug import student
from crew.runtime.sync import run_sync

MAX_TURNS = 8


@dataclass
class Outcome:
    reply: str
    agent: str
    blocked_by: str | None = None  # None | "guardrail" | "code" | "approval" | "switch" | "budget"
    tools: list[str] = field(default_factory=list)
    run_id: str = ""
    masked: int = 0                 # 4-3: 모델에 보내기 전에 가린 값 개수
    approval_id: int | None = None  # 6-1: 승인 대기 번호


def trace_policy(mode: str | None = None) -> dict:
    """트레이스가 OpenAI로 가는지, 간다면 모델 입력·출력 원문이 실리는지(4-1·4-5)."""
    s = get_settings()
    mode = mode or s.llm_mode
    include = student("crew.guards.pii", "TRACE_INCLUDE_SENSITIVE", True)  # SDK 기본값은 True
    return {"tracing": mode in ("live", "record") and s.tracing, "include_sensitive": bool(include)}


def _run_config() -> RunConfig:
    # 트레이싱은 live·record에서만, 그것도 CREW_TRACING=on일 때만 OpenAI로 간다(4-5에서 다시 본다)
    p = trace_policy()
    return RunConfig(tracing_disabled=not p["tracing"], trace_include_sensitive_data=p["include_sensitive"],
                     workflow_name="cs-crew")


def _mask(text: str) -> tuple[str, dict, int]:
    mask = student("crew.guards.pii", "mask")
    if not mask:
        return text, {}, 0
    out = mask(text)
    masked, mapping = out if isinstance(out, tuple) else (out, {})
    return masked, mapping, masked.count("[MASKED")


def _unmask(reply: str, mapping: dict) -> str:
    unmask = student("crew.guards.pii", "unmask")
    return unmask(reply, mapping) if unmask and mapping else reply


def _tool_rejections(result, ctx: CrewContext, agent: str) -> None:
    """도구 가드레일(10-4 인자 검사 등)이 reject_content로 막은 호출. SDK는 예외를 내지 않고 모델에 글만 돌려주므로
    여기서 기록에 남긴다(denied → 점수판 ③ 내 코드)."""
    results = list(getattr(result, "tool_input_guardrail_results", None) or [])
    results += list(getattr(result, "tool_output_guardrail_results", None) or [])
    for g in results:
        behavior = getattr(g.output, "behavior", None) or {}
        if behavior.get("type") == "reject_content":
            record(ctx.run_id, ctx.user.id, agent, "blocked",
                   {"by": "tool_guardrail", "guardrail": g.guardrail.get_name(),
                    "why": str(behavior.get("message", ""))[:200], "denied": True})


def _tools_used(run_id: str) -> tuple[list[str], bool]:
    """이번 실행에서 쓴 도구와, 내 코드가 막은 적이 있는지(도구의 "거부:"·숨긴 MCP 도구 등 denied 표시)."""
    with session() as db:
        rows = db.execute("SELECT action, detail FROM audit_log WHERE run_id = ?", (run_id,)).fetchall()
    details = [(r["action"], json.loads(r["detail"])) for r in rows]
    return [d["tool"] for a, d in details if a == "tool_end"], any(d.get("denied") for _, d in details)


async def ask_async(user_id: str, text: str, *, channel: str = "chat", remember: bool = False,
                    acting_for: str | None = None) -> Outcome:
    from crew.runtime.watch import patrol

    out = await _ask(user_id, text, channel=channel, remember=remember, acting_for=acting_for)
    patrol()  # 12-3: 감시자 순찰(학생 코드가 없으면 조용히 쉰다)
    return out


async def _ask(user_id: str, text: str, *, channel: str, remember: bool, acting_for: str | None) -> Outcome:
    from crew.runtime import approvals
    from crew.team import entry_agent  # 팀 구성은 수업마다 바뀐다

    run_id = uuid.uuid4().hex[:8]
    CURRENT_RUN.set(run_id)  # 브로커 기록도 이 요청 번호로
    user = load_user(user_id)
    CURRENT_USER.set(user)  # 샌드박스 DB 사본의 매장(9-4)
    if get_flag("kill_switch") == "on":
        record(run_id, user.id, "lab", "blocked", {"by": "kill_switch"})
        return Outcome("지금은 상담이 잠시 멈춰 있습니다. 잠시 뒤 다시 시도해 주세요.", "lab", "switch", run_id=run_id)
    if total_cost() >= get_settings().max_usd:
        record(run_id, user.id, "lab", "blocked", {"by": "budget"})
        return Outcome("랩 예산(LAB_MAX_USD)을 다 썼습니다.", "lab", "budget", run_id=run_id)
    over_budget = student("crew.guards.killswitch", "over_budget")  # 12-4: 사용자별 요금 차단
    if over_budget and (why := over_budget(user)):
        record(run_id, user.id, "lab", "blocked", {"by": "budget", "why": why[:200]})
        return Outcome(why, "lab", "budget", run_id=run_id)

    text, mapping, n_masked = _mask(text)
    ctx = CrewContext(user=user, run_id=run_id, channel=channel, acting_for=acting_for)
    if channel == "staff":
        issue = student("crew.guards.delegation", "issue")  # 7-3: 직원 대신 처리에는 짧고 좁은 위임 토큰
        if issue and user.is_staff:
            ctx.delegation = issue(user, f"대신 처리:{acting_for or ''}")
    record(run_id, user.id, "lab", "request", {"channel": channel, "text": text[:300], "masked": n_masked})
    agent = entry_agent()
    ctx.session = f"{channel}:{user.id}" if remember else None
    sess = SQLiteSession(ctx.session, get_settings().sessions_path) if remember else None
    try:
        async with attached(agent):
            result = await Runner.run(agent, text, context=ctx, hooks=AuditHooks(), session=sess,
                                      run_config=_run_config(), max_turns=MAX_TURNS)
    except MaxTurnsExceeded:
        record(run_id, user.id, agent.name, "max_turns", {"max_turns": MAX_TURNS})
        tools, _ = _tools_used(run_id)
        return Outcome(f"처리가 너무 길어져 멈췄습니다(최대 {MAX_TURNS}턴). 담당 사이에서 같은 일을 되풀이했습니다.",
                       agent.name, None, tools, run_id, n_masked)
    except ModelBehaviorError as e:  # 진짜 모델이 없는 도구 이름(run_python.json 등)을 부를 때. 레드팀이 멈추지 않게
        record(run_id, user.id, agent.name, "model_error", {"why": str(e)[:200]})
        tools, _ = _tools_used(run_id)
        return Outcome("처리 중 모델 응답 오류로 멈췄습니다. 다시 시도해 주세요.", agent.name, None, tools, run_id, n_masked)
    except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as e:
        name = type(e).__name__.replace("TripwireTriggered", "")
        g = e.guardrail_result.guardrail.get_name()
        info = str(getattr(e.guardrail_result.output, "output_info", ""))[:200]  # "공격 판정: …" / "판별기 오류, 막음: …"
        record(run_id, user.id, agent.name, "blocked", {"by": "guardrail", "which": name, "guardrail": g, "info": info})
        tools, _ = _tools_used(run_id)
        return Outcome("죄송합니다. 이 요청은 처리할 수 없습니다.", agent.name, "guardrail", tools, run_id, n_masked)
    except Denied as e:
        by = "switch" if "멈춰 있습니다" in str(e) else "code"  # 12-4: 담당 멈춤은 킬 스위치 층
        record(run_id, user.id, agent.name, "blocked", {"by": by, "why": str(e)[:200]})
        tools, _ = _tools_used(run_id)
        return Outcome(str(e), agent.name, by, tools, run_id, n_masked)

    _tool_rejections(result, ctx, result.last_agent.name)
    if result.interruptions:
        approval_id = approvals.save(result, ctx)
        reply = f"직원 승인을 기다리고 있습니다(승인 #{approval_id}). 승인되면 이어서 처리합니다."
        record(run_id, user.id, result.last_agent.name, "approval_wait", {"approval": approval_id})
        tools, _ = _tools_used(run_id)
        return Outcome(reply, result.last_agent.name, "approval", tools, run_id, n_masked, approval_id)

    nested = approvals.pending_for_run(run_id)  # 11-4: 감독자의 메시지 길(bus) 안에서 멈춘 승인
    if nested:
        reply = f"직원 승인을 기다리고 있습니다(승인 #{nested}). 승인되면 이어서 처리합니다. " + str(result.final_output)
        record(run_id, user.id, result.last_agent.name, "approval_wait", {"approval": nested})
        tools, _ = _tools_used(run_id)
        return Outcome(reply, result.last_agent.name, "approval", tools, run_id, n_masked, nested)

    tools, denied = _tools_used(run_id)
    blocked = "code" if denied else None
    # 일부 공개 모델(gpt-oss 등)은 생각 과정을 <reasoning>…</reasoning>으로 답에 섞어 보낸다 → 고객에게는 답만
    reply = _unmask(re.sub(r"<reasoning>.*?</reasoning>\s*", "", str(result.final_output), flags=re.S), mapping)
    record(run_id, user.id, result.last_agent.name, "reply", {"text": reply[:300], "blocked_by": blocked})
    return Outcome(reply, result.last_agent.name, blocked, tools, run_id, n_masked)


def ask(user_id: str, text: str, **kw) -> Outcome:
    return run_sync(ask_async(user_id, text, **kw))


async def act_async(staff_id: str, ticket_id: int) -> Outcome:
    """7-1: 직원 콘솔의 "대신 처리". 직원 신원으로, 고객 문의를 에이전트 팀에 맡긴다."""
    with session() as db:
        t = db.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if t is None:
        raise KeyError(f"없는 문의: {ticket_id}")
    text = f"[직원 대신 처리] 고객 {t['customer_id']}의 문의(#{t['id']}): {t['body']}"
    return await ask_async(staff_id, text, channel="staff", acting_for=t["customer_id"])


def act(staff_id: str, ticket_id: int) -> Outcome:
    return run_sync(act_async(staff_id, ticket_id))
