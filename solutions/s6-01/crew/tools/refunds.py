"""환불 도구(6-1). 되돌리기 어려운 일이라 직원 승인 뒤에 실행한다(needs_approval).

needs_approval=True면 SDK가 도구를 부르기 전에 실행을 멈춘다. 완성본(crew/runtime/approvals.py)이 그 상태를
승인 대기열에 저장하고, 직원이 /staff에서 승인하면 이어서 실행한다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


@function_tool
def list_my_orders(ctx: RunContextWrapper[CrewContext]) -> str:
    """로그인한 고객의 주문 목록(번호·상태·금액)."""
    with session() as db:
        rows = db.execute("SELECT id, status, total_krw FROM orders WHERE customer_id = ? ORDER BY id",
                          (ctx.context.user.id,)).fetchall()
    return "\n".join(f"주문 {r['id']}: {r['status']} {r['total_krw']:,}원" for r in rows) or "주문이 없습니다."


@function_tool(needs_approval=True)  # ✏️ 6-5: 금액·건수에 따라 자동/사람/두 사람 승인을 고른다
def request_refund(ctx: RunContextWrapper[CrewContext], order_ids: list[int], reason: str, summary: str) -> str:
    """내 주문을 환불한다. 직원 승인 뒤에 실행된다. summary에는 직원이 볼 한 줄 요약을 쓴다."""
    user = ctx.context.user
    done = []
    with session() as db:
        for oid in order_ids:
            row = db.execute("SELECT id, total_krw FROM orders WHERE id = ? AND customer_id = ? AND status != 'cancelled'",
                             (oid, user.id)).fetchone()
            if row:
                db.execute("INSERT INTO refunds(order_id, amount_krw, reason, status, requested_by, created_at) "
                           "VALUES (?, ?, ?, 'approved', ?, datetime('now', 'localtime'))",
                           (row["id"], row["total_krw"], reason[:100], user.id))
                done.append(row)
    if not done:
        return "거부: 환불할 수 있는 내 주문이 없습니다."
    return f"환불 {len(done)}건을 처리했습니다: " + ", ".join(f"주문 {r['id']} {r['total_krw']:,}원" for r in done)
# ✏️ 6-4: 상태를 바꾸지 않는 미리보기(preview)를 만들어 승인 화면에 실제로 바뀌는 내용(diff)을 보여 준다
