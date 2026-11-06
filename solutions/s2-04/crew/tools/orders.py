"""주문 도구. 2-4에서 소유권 검사를 넣었다."""
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
    user = ctx.context.user  # 누가 묻는가: 로그인 정보에서 온다. 모델이 정할 수 없다
    with session() as db:
        # 소유권은 SQL에서 검사한다: 내 주문만 찾는다
        row = db.execute("SELECT * FROM orders WHERE id = ? AND customer_id = ?", (order_id, user.id)).fetchone()
    if row is None:
        return "거부: 내 주문이 아니거나 없는 주문입니다."  # 남의 주문인지 없는 주문인지 알려 주지 않는다
    return _format(row)
