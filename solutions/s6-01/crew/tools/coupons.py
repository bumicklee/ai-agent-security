"""할인 코드와 보상 쿠폰. 3-3에서 만들었다.

비밀(할인 코드)은 지시문이 아니라 DB(lab_flags)에 있다. 꺼내는 일은 "누가 묻는가"를 보는 도구가 한다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import get_flag, session


@function_tool
def get_discount_code(ctx: RunContextWrapper[CrewContext]) -> str:
    """이번 달 직원 할인 코드를 확인한다. 직원만 받을 수 있다."""
    if not ctx.context.user.is_staff:
        return "거부: 할인 코드는 직원에게만 알려 드립니다."
    return f"이번 달 직원 할인 코드는 {get_flag('staff_discount_code')} 입니다."


@function_tool  # ✏️ 6-6: 쿠폰도 돈이다. 직원 승인을 붙인다
def issue_coupon(ctx: RunContextWrapper[CrewContext], reason: str) -> str:
    """로그인한 고객 본인에게 배송 지연 보상 쿠폰(5,000원)을 발급한다."""
    user = ctx.context.user
    with session() as db:
        db.execute("INSERT INTO coupons(customer_id, amount_krw, reason, status, created_at) "
                   "VALUES (?, 5000, ?, 'issued', datetime('now', 'localtime'))", (user.id, reason[:50]))
    return f"{user.name}님께 보상 쿠폰 5,000원을 발급했습니다."
