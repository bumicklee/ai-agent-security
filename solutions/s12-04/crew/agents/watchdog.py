"""감시자(12-3). 팀의 일곱 번째. 고객 문의 경로에는 없다(접수의 핸드오프에 넣지 않는다).

/ops에서 운영자가 부르고, 완성본 순찰(crew/runtime/watch.py)이 요청마다 감시 규칙(crew/guards/watch.py)을 돌린다.
권한은 읽기(read_audit)와 멈춤(pause_agent·revoke_tokens)뿐이다(12-4).
"""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.watch import pause_agent, read_audit, revoke_tokens

INSTRUCTIONS = """너는 감시자다. 팀의 행동 기록을 점검해 운영자에게 짧게 한국어로 보고한다.
기록 도구 결과만 전한다. 고객에게 답하지 않고, 환불·주문 같은 일을 하지 않는다."""


def build_watchdog() -> Agent:
    return Agent(name="감시자", instructions=INSTRUCTIONS, model=get_model(), tools=[read_audit, pause_agent, revoke_tokens])
