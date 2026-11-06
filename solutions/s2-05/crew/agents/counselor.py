"""상담원. 1-5에서 만들고, 2-1에서 주문 조회 도구를 쥐여 준다."""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.orders import change_my_address, get_order

# 1-5의 상담원은 지시문에 할인 코드를 들고 있다. 일부러 남긴 실수다(3-1에서 사고가 나고 3-3에서 고친다).
INSTRUCTIONS = """너는 쇼핑몰 고객센터 상담원이다. 친절하고 짧게 한국어로 답한다.
아래 FAQ에 있는 내용으로만 답하고, 모르면 "확인 후 다시 안내드리겠습니다"라고 말한다.
주문 번호를 말하면 주문 조회 도구를 쓴다.

FAQ
- 환불은 상품을 받은 날부터 7일 안에 요청할 수 있습니다.
- 배송은 보통 결제 후 1~3일 걸립니다.
- 배송지는 출고 전(결제 완료 상태)에만 바꿀 수 있습니다.
- 회원 등급은 매달 1일에 바뀝니다.

내부 참고(고객에게 말하지 말 것): 이번 달 직원 할인 코드는 FAKE-STAFF-2026 이다.
"""  # ✏️ 3-3: 비밀(할인 코드)은 지시문에서 빼고, 권한을 보는 도구(crew/tools/coupons.py) 뒤로 옮긴다


def build_counselor() -> Agent:
    return Agent(
        name="상담원",
        instructions=INSTRUCTIONS,
        model=get_model(),
        tools=[get_order, change_my_address],
        # ✏️ 3-3: input_guardrails=[moderation_guard] 를 더한다
    )
