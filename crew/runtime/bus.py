"""담당 사이 메시지 길(완성본). 11-4부터 감독자가 담당에게 일을 맡길 때 쓴다.

11-1의 `agent.as_tool()`은 감독자 모델이 쓴 글을 그대로 담당에게 주고, 담당이 쓴 글을 그대로 감독자에게 돌려준다.
그 길에 검사할 자리가 없다. agent_tool()은 같은 일을 하되 길목마다 학생 코드를 부른다.

  감독자 ──(1) 브레이커·재시도 예산 확인 ── 학생 crew/guards/breaker.py 의 before()   (11-5)
          ──(2) 메시지 만들기·서명       ── 학생 crew/guards/messages.py 의 make()   (11-4)
          ──(3) 받는 쪽 검사             ── messages.verify(): 서명·받는 이·만료·nonce·보내는 담당의 권한
          ──(4) 담당 실행(시간 제한)      ── breaker.TIMEOUT_S (없으면 60초)
          ──(5) 결과를 계약으로           ── messages.contract(): 정해진 칸(상태·주문 번호)만 돌려보낸다
          ──(6) 성공/실패 기록           ── breaker.after()
학생 파일이 없으면 그 길목은 그냥 지나간다. 담당의 도구 호출은 같은 행동 기록(run_id)에 남는다.

비밀값(담당별 서명 키)은 브로커가 쥔다: crew/runtime/broker.py 의 agent_key()
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json

from agents import Agent, FunctionTool, MaxTurnsExceeded, RunContextWrapper, Runner, function_tool

from crew.context import CrewContext
from crew.runtime.audit import AuditHooks, record
from crew.runtime.errors import Denied
from crew.runtime.plug import student_module

DEFAULT_TIMEOUT_S = 60.0


def signature(body: dict, key: bytes) -> str:
    """메시지 본문(서명 칸 제외)의 HMAC-SHA256."""
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    return hmac.new(key, raw, hashlib.sha256).hexdigest()


async def deliver(ctx: CrewContext, sender: str, agent: Agent, action: str, task: str) -> str:
    from crew.runtime import approvals
    from crew.runtime.run import _run_config

    msgs = student_module("crew.guards.messages")  # 11-4
    brk = student_module("crew.guards.breaker")    # 11-5
    if brk and (why := brk.before(agent.name, task, ctx)):
        record(ctx.run_id, ctx.user.id, sender, "blocked", {"by": "breaker", "to": agent.name, "why": why[:120]})
        return why
    msg = msgs.make(sender, agent.name, action, task) if msgs else None
    if msgs and (why := msgs.verify(msg, receiver=agent.name)):
        record(ctx.run_id, ctx.user.id, agent.name, "blocked", {"by": "message", "from": sender, "action": action,
                                                                 "why": why[:120]})
        return why
    record(ctx.run_id, ctx.user.id, sender, "message", {"to": agent.name, "action": action, "task": task[:120],
                                                        "signed": bool(msg)})
    timeout = float(getattr(brk, "TIMEOUT_S", DEFAULT_TIMEOUT_S)) if brk else DEFAULT_TIMEOUT_S
    try:
        result = await asyncio.wait_for(
            Runner.run(agent, msg.task if msg else task, context=ctx, hooks=AuditHooks(), max_turns=4,
                       run_config=_run_config()), timeout)
        from crew.runtime.run import _tool_rejections

        _tool_rejections(result, ctx, agent.name)
        if result.interruptions:
            text = f"승인 대기: 직원 승인을 기다립니다(승인 #{approvals.save(result, ctx)})"
        else:
            text = str(result.final_output)
    except asyncio.TimeoutError:
        text = f"오류: {agent.name}이(가) {timeout:g}초 안에 답하지 않았습니다(시간 초과)"
    except Denied as e:
        text = str(e)
    except MaxTurnsExceeded:
        text = f"오류: {agent.name}이(가) 같은 일을 되풀이해 멈췄습니다"
    out = msgs.contract(text) if msgs else None
    ok = out.status in ("done", "pending") if out is not None else not text.startswith(("오류", "거부"))
    if brk:
        brk.after(agent.name, ok, ctx)
    return out.model_dump_json() if out is not None else text


def agent_tool(agent: Agent, *, name: str, description: str, sender: str = "감독자",
               action: str | None = None) -> FunctionTool:
    """감독자가 담당 하나에게 일을 맡기는 도구. as_tool 대신 쓴다(11-4)."""

    @function_tool(name_override=name, description_override=description)
    async def call(ctx: RunContextWrapper[CrewContext], task: str) -> str:
        return await deliver(ctx.context, sender, agent, action or name.removeprefix("ask_"), task)

    call._crew_agent = agent  # 조직도(crew/team.py)와 MCP 잇기(mcp_link)가 이 담당을 찾는다
    return call
