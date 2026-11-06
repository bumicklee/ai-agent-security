"""주문 담당(5-1). 상담원이 쥐고 있던 주문 도구를 넘겨받았다. 7-1에서 직원 대신 처리 도구를 더했다.
8-1: 고객 메모를 기억한다. 지시문을 함수로 만들어, 대화를 시작할 때마다 그 고객의 메모를 붙인다.
10-1: 택배사 MCP 서버(carrier)를 붙인다. 배송 조회 도구(track_shipment)는 서버가 알려 준다.
"""
from __future__ import annotations

from agents import Agent, RunContextWrapper

from crew.context import CrewContext
from crew.guards.output import leak_guard
from crew.runtime.llm import get_model
from crew.tools.carrier import carrier_server
from crew.tools.coupons import issue_coupon
from crew.tools.memories import notes_for, recall_memory, remember
from crew.tools.orders import change_my_address, get_order
from crew.tools.staff import staff_change_address

INSTRUCTIONS = """너는 주문 담당이다. 로그인한 고객의 주문 조회, 출고 전 배송지 변경, 배송 지연 보상 쿠폰을 맡는다.
"[직원 대신 처리]"로 시작하는 요청은 직원이 고객 대신 맡긴 일이다. 그때는 직원 대신 처리 도구를 쓴다.
고객이 기억해 달라는 것은 메모 도구로 적고, 아래 [고객 메모]를 참고한다.
운송장 번호로 배송을 물으면 택배사 도구로 조회한다.
도구 결과로만 짧게 한국어로 답한다."""


def instructions(ctx: RunContextWrapper[CrewContext], agent: Agent) -> str:
    notes = notes_for(ctx.context.user.id)
    return INSTRUCTIONS + "".join(f"\n[고객 메모] {n}" for n in notes)


def build_order_agent() -> Agent:
    return Agent(name="주문 담당", instructions=instructions, model=get_model(),
                 tools=[get_order, change_my_address, issue_coupon, staff_change_address, remember, recall_memory],  # ✏️ 13-3
                 output_guardrails=[leak_guard], mcp_servers=[carrier_server()])
