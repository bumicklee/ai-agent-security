"""상담원 → 접수 라우터(5-1, 6-1 환불 담당, 9-1 리포트 담당, 11-1 감독자). FAQ는 직접 답하고, 나머지는 담당에게 넘긴다(핸드오프).

가드레일은 여기(첫 에이전트)에 붙인다. 입력 가드레일은 첫 에이전트에서만 돈다.
출력 가드레일은 마지막으로 답한 에이전트의 것만 돈다. 그래서 고객에게 답하는 담당마다 leak_guard를 붙인다(5-6).
"""
from __future__ import annotations

from agents import Agent, handoff

from crew.agents.knowledge import build_knowledge
from crew.agents.orders import build_order_agent
from crew.agents.refunds import build_refund_agent
from crew.agents.reports import build_report_agent
from crew.agents.supervisor import build_supervisor
from crew.guards.injection import injection_guard
from crew.guards.moderation import moderation_guard
from crew.guards.output import leak_guard
from crew.guards.team import staff_only
from crew.runtime.llm import get_model

INSTRUCTIONS = """너는 쇼핑몰 고객센터 접수 상담원이다. 친절하고 짧게 한국어로 답한다.
아래 FAQ로 답할 수 있으면 직접 답한다. 아니면 알맞은 담당에게 넘긴다.
* 주문 조회·배송지 변경·보상 쿠폰 → 주문 담당
* 매장 정책·공지·문서, 할인 코드 → 지식 담당
* 환불 요청 → 환불 담당
* 직원용 통계·리포트·차트 → 리포트 담당(직원만)
* 여러 가지 일을 한 번에(…하고 …하고) → 감독자

FAQ
- 환불은 상품을 받은 날부터 7일 안에 요청할 수 있습니다.
- 배송은 보통 결제 후 1~3일 걸립니다.
- 배송지는 출고 전(결제 완료 상태)에만 바꿀 수 있습니다.
- 회원 등급은 매달 1일에 바뀝니다.
- 할인 행사는 매달 첫 주에 공지합니다.
"""


def build_counselor() -> Agent:
    # 핸드오프 도구 이름은 영어로 정해 준다(한글 이름은 transfer_to____ 처럼 뭉개져 서로 겹친다)
    orders, refunds = build_order_agent(), build_refund_agent()  # 감독자도 같은 담당을 쓴다
    return Agent(
        name="상담원",
        instructions=INSTRUCTIONS,
        model=get_model(),
        handoffs=[
            handoff(orders, tool_name_override="transfer_to_orders"),
            handoff(build_knowledge(), tool_name_override="transfer_to_knowledge"),
            handoff(refunds, tool_name_override="transfer_to_refunds"),
            handoff(build_report_agent(), tool_name_override="transfer_to_reports", on_handoff=staff_only),
            handoff(build_supervisor(orders, refunds), tool_name_override="transfer_to_supervisor"),
        ],
        input_guardrails=[moderation_guard, injection_guard],
        output_guardrails=[leak_guard],
    )
