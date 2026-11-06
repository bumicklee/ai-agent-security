"""감독자(11-1). 팀의 여섯 번째. "환불하고 배송지 바꾸고 쿠폰도" 같은 복합 문의를 나눠 담당들에게 맡긴다.

핸드오프는 대화를 통째로 넘긴다. 감독자는 넘기지 않고, 담당을 도구로 쥐고(as_tool) 한 가지씩 맡긴 뒤 결과를 모은다.
감독자는 계획만 세운다. 실제 일(환불·주소 변경)은 각 담당의 도구와 정책(승인·예산·소유권)을 그대로 지난다.
"""
from __future__ import annotations

from agents import Agent, handoff

from crew.runtime.audit import AuditHooks
from crew.runtime.llm import get_model

INSTRUCTIONS = """너는 감독자다. 고객의 복합 문의를 한 가지 일씩 나눠 알맞은 담당 도구에 맡기고, 결과를 모아 짧게 한국어로 답한다.
주문 조회·배송 조회·배송지 변경·보상 쿠폰은 ask_orders, 환불은 ask_refunds에 맡긴다. 직접 처리하지 않는다."""


def build_supervisor(orders: Agent, refunds: Agent) -> Agent:
    return Agent(name="감독자", instructions=INSTRUCTIONS, model=get_model(),
                 handoffs=[handoff(orders, tool_name_override="transfer_to_orders"),  # 맡기기 어려운 일은
                           handoff(refunds, tool_name_override="transfer_to_refunds")],  # 대화째 넘길 수 있게
                 tools=[  # ✏️ 11-4: 메시지 길(bus.agent_tool)로, 핸드오프는 빼기
        orders.as_tool(tool_name="ask_orders", tool_description="주문 담당에게 한 가지 일을 맡긴다",
                       hooks=AuditHooks(), max_turns=4),
        refunds.as_tool(tool_name="ask_refunds", tool_description="환불 담당에게 한 가지 일을 맡긴다",
                        hooks=AuditHooks(), max_turns=4),
    ])
