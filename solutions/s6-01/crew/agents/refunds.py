"""환불 담당(6-1). 팀의 네 번째 담당."""
from __future__ import annotations

from agents import Agent

from crew.guards.output import leak_guard
from crew.runtime.llm import get_model
from crew.tools.refunds import list_my_orders, request_refund

INSTRUCTIONS = """너는 환불 담당이다. 로그인한 고객의 주문을 환불 요청한다.
"전부" 같은 말이면 먼저 주문 목록을 확인한다. 환불은 직원 승인 뒤에 처리된다. 짧게 한국어로 답한다."""


def build_refund_agent() -> Agent:
    return Agent(name="환불 담당", instructions=INSTRUCTIONS, model=get_model(),
                 tools=[list_my_orders, request_refund], output_guardrails=[leak_guard])
