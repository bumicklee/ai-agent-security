"""주문 담당(5-1). 상담원이 쥐고 있던 주문 도구를 넘겨받았다. 7-1에서 직원 대신 처리 도구를 더했다."""
from __future__ import annotations

from agents import Agent

from crew.guards.output import leak_guard
from crew.runtime.llm import get_model
from crew.tools.coupons import issue_coupon
from crew.tools.orders import change_my_address, get_order
from crew.tools.staff import staff_change_address

INSTRUCTIONS = """너는 주문 담당이다. 로그인한 고객의 주문 조회, 출고 전 배송지 변경, 배송 지연 보상 쿠폰을 맡는다.
"[직원 대신 처리]"로 시작하는 요청은 직원이 고객 대신 맡긴 일이다. 그때는 직원 대신 처리 도구를 쓴다.
도구 결과로만 짧게 한국어로 답한다."""


def build_order_agent() -> Agent:
    return Agent(name="주문 담당", instructions=INSTRUCTIONS, model=get_model(),  # ✏️ 8-1: 지시문을 함수로(고객 메모를 붙인다)
                 tools=[get_order, change_my_address, issue_coupon, staff_change_address],  # ✏️ 8-1: 메모 도구 두 개
                 output_guardrails=[leak_guard])
