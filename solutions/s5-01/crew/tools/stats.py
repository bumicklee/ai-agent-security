"""직원용 통계 도구(5-1). 매장 운영 정보라 고객에게 보여 주면 안 된다."""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


@function_tool
def store_ticket_stats(ctx: RunContextWrapper[CrewContext]) -> str:
    """직원용: 매장별·주제별 미처리 문의 건수."""
    with session() as db:
        rows = db.execute("SELECT u.store_id, t.subject, COUNT(*) AS n FROM tickets t JOIN users u ON u.id = t.customer_id "
                          "WHERE t.status = 'open' GROUP BY 1, 2 ORDER BY 1, 3 DESC").fetchall()
    total = sum(r["n"] for r in rows)
    return f"미처리 문의 {total}건: " + ", ".join(f"{r['store_id']} {r['subject']} {r['n']}건" for r in rows)
