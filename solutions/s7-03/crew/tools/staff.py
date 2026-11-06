"""직원 대신 처리 도구(7-1). 직원 콘솔의 "대신 처리" 버튼이 직원 신원으로 에이전트 팀을 부른다.

7-3: 서비스 계정을 버렸다. 위임 토큰(요청한 직원의 매장·범위·짧은 수명)을 브로커에서 확인하고, 그 매장 주문만 고친다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session
from crew.runtime.broker import redeem


@function_tool
def staff_change_address(ctx: RunContextWrapper[CrewContext], order_id: int, new_address: str) -> str:
    """직원이 고객 대신: 출고 전 주문의 배송지를 바꾼다."""
    if not ctx.context.user.is_staff:
        return "거부: 직원만 쓸 수 있습니다."
    grant = redeem(ctx.context.delegation, "orders:write")  # 토큰은 ctx에만 있다. 모델은 모른다
    if grant is None:
        return "거부: 유효한 위임 토큰이 없습니다(없음·만료·폐기·범위 밖)."
    new_address = new_address.strip()[:100]
    with session() as db:
        cur = db.execute("UPDATE orders SET address = ? WHERE id = ? AND status = 'paid' AND store_id = ?",
                         (new_address, order_id, grant.store_id))
    if cur.rowcount == 0:
        return "거부: 위임받은 매장의 출고 전 주문이 아니라 배송지를 바꿀 수 없습니다."
    return f"[대신 처리] 주문 {order_id}의 배송지를 {new_address}(으)로 바꿨습니다."
