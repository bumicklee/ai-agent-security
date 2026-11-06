"""환불 도구(6-1). 되돌리기 어려운 일이라 직원 승인 뒤에 실행한다(needs_approval).

needs_approval=True면 SDK가 도구를 부르기 전에 실행을 멈춘다. 완성본(crew/runtime/approvals.py)이 그 상태를
승인 대기열에 저장하고, 직원이 /staff에서 승인하면 이어서 실행한다.
6-4: 승인 화면은 모델이 쓴 요약이 아니라 preview()가 DB에서 읽은 실제 diff를 보여 준다.
"""
from __future__ import annotations

from dataclasses import dataclass

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


@dataclass
class Preview:
    rows: list
    total: int

    @property
    def text(self) -> str:
        lines = [f"- 주문 {r['id']} ({r['status']}) {r['total_krw']:,}원 → 환불" for r in self.rows]
        return "\n".join([f"환불 {len(self.rows)}건 · 합계 {self.total:,}원", *lines])


def preview(user_id: str, order_ids: list[int]) -> Preview:
    """미리보기(dry-run). 읽기만 하고 아무것도 바꾸지 않는다. 승인 화면의 diff가 이것을 쓴다."""
    with session() as db:
        rows = [r for oid in dict.fromkeys(order_ids) if (r := db.execute(
            "SELECT id, status, total_krw FROM orders WHERE id = ? AND customer_id = ? AND status != 'cancelled'",
            (oid, user_id)).fetchone())]
    return Preview(rows, sum(r["total_krw"] for r in rows))


@function_tool
def preview_refund(ctx: RunContextWrapper[CrewContext], order_ids: list[int]) -> str:
    """환불하면 무엇이 바뀌는지 미리 본다(실제로 환불하지 않는다)."""
    return preview(ctx.context.user.id, order_ids).text


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
