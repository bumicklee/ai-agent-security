"""직원 대신 처리 도구(7-1). 직원 콘솔의 "대신 처리" 버튼이 직원 신원으로 에이전트 팀을 부른다.

고객 주문은 직원 본인 것이 아니라서, 빠르게 만들려고 서비스 계정(모든 매장 주문을 고칠 수 있음)을 썼다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.runtime.broker import service_session


@function_tool
def staff_change_address(ctx: RunContextWrapper[CrewContext], order_id: int, new_address: str) -> str:
    """직원이 고객 대신: 출고 전 주문의 배송지를 바꾼다."""
    if not ctx.context.user.is_staff:
        return "거부: 직원만 쓸 수 있습니다."
    new_address = new_address.strip()[:100]
    with service_session("대신 처리: 배송지 변경") as db:  # ✏️ 7-3: 서비스 계정 대신 위임 토큰(redeem)으로, 그 매장 주문만
        cur = db.execute("UPDATE orders SET address = ? WHERE id = ? AND status = 'paid'", (new_address, order_id))
    if cur.rowcount == 0:
        return "거부: 출고 전 주문이 아니라 배송지를 바꿀 수 없습니다."
    return f"[대신 처리] 주문 {order_id}의 배송지를 {new_address}(으)로 바꿨습니다."
