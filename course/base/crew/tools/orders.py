"""주문 도구. 2-1에서 만든 첫 도구.

지금 모습은 2-1 그대로다. 주문 번호만 있으면 누구 주문이든 보여 준다(2-2에서 사고가 난다).
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


def _format(row) -> str:
    return (f"주문 {row['id']}: 상태 {row['status']}, 금액 {row['total_krw']:,}원, "
            f"배송지 {row['address']}, 주문자 {row['customer_id']}")


@function_tool
def get_order(ctx: RunContextWrapper[CrewContext], order_id: int) -> str:
    """주문 번호로 주문 상태·금액·배송지를 조회한다."""
    # ✏️ 2-4: 여기서 "누가 묻는가"(ctx.context.user)를 확인한다
    with session() as db:
        row = db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        return "그런 주문이 없습니다."
    return _format(row)
