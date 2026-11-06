"""주문 담당(5-1). 상담원이 쥐고 있던 주문 도구를 넘겨받았다."""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.coupons import issue_coupon
from crew.tools.orders import change_my_address, get_order

INSTRUCTIONS = """너는 주문 담당이다. 로그인한 고객의 주문 조회, 출고 전 배송지 변경, 배송 지연 보상 쿠폰을 맡는다.
도구 결과로만 짧게 한국어로 답한다."""


def build_order_agent() -> Agent:
    return Agent(name="주문 담당", instructions=INSTRUCTIONS, model=get_model(),
                 tools=[get_order, change_my_address, issue_coupon])  # ✏️ 5-6: output_guardrails
