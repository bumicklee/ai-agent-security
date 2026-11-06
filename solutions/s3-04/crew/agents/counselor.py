"""상담원. 1-5에서 만들고, 2-1에서 주문 조회 도구, 3-3·3-4에서 입력 가드레일을 붙였다."""
from __future__ import annotations

from agents import Agent

from crew.guards.injection import injection_guard
from crew.guards.moderation import moderation_guard
from crew.runtime.llm import get_model
from crew.tools.coupons import get_discount_code, issue_coupon
from crew.tools.orders import change_my_address, get_order

# 3-3: 할인 코드는 지시문에서 뺐다. 지시문에 있는 것은 언젠가 새어 나간다고 보고, 비밀은 DB에 두고 도구가 권한을 본다.
INSTRUCTIONS = """너는 쇼핑몰 고객센터 상담원이다. 친절하고 짧게 한국어로 답한다.
아래 FAQ에 있는 내용으로만 답하고, 모르면 "확인 후 다시 안내드리겠습니다"라고 말한다.
주문 번호를 말하면 주문 조회 도구를 쓴다. 할인 코드는 할인 코드 도구로만 확인한다.
배송이 늦어진 고객에게는 보상 쿠폰 도구로 쿠폰을 줄 수 있다.

FAQ
- 환불은 상품을 받은 날부터 7일 안에 요청할 수 있습니다.
- 배송은 보통 결제 후 1~3일 걸립니다.
- 배송지는 출고 전(결제 완료 상태)에만 바꿀 수 있습니다.
- 회원 등급은 매달 1일에 바뀝니다.
- 할인 행사는 매달 첫 주에 공지합니다.
"""


def build_counselor() -> Agent:
    return Agent(
        name="상담원",
        instructions=INSTRUCTIONS,
        model=get_model(),
        tools=[get_order, change_my_address, get_discount_code, issue_coupon],
        input_guardrails=[moderation_guard, injection_guard],
        # ✏️ 3-5: output_guardrails=[leak_guard] 를 더한다
    )
