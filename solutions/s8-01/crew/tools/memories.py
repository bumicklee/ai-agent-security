"""고객 메모(8-1). 상담원 팀이 고객을 기억한다: 선호 배송지, 연락 시간, 지난 문의.

- remember: 고객이 "기억해 둬"라고 한 것을 memories 테이블에 적는다
- recall_memory: 메모를 찾아 본다
- notes_for: 다음 상담에서 주문 담당의 지시문에 붙일 메모(crew/agents/orders.py)
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


@function_tool
def remember(ctx: RunContextWrapper[CrewContext], text: str) -> str:
    """고객이 기억해 달라고 한 것(선호 배송지·연락 시간 등)을 메모한다."""
    user, text = ctx.context.user, text.strip()[:200]
    with session() as db:
        db.execute("INSERT INTO memories(customer_id, text, source, trust, created_at, run_id) "  # ✏️ 8-3: 출처·확인 등급·만료
                   "VALUES (?, ?, 'customer', 'confirmed', datetime('now', 'localtime'), ?)",
                   (user.id, text, ctx.context.run_id))
    return f"기억해 두겠습니다: {text}"


@function_tool
def recall_memory(ctx: RunContextWrapper[CrewContext], query: str = "") -> str:
    """메모를 찾아 본다(빈 검색어면 최근 메모)."""
    with session() as db:
        rows = db.execute("SELECT text FROM memories WHERE text LIKE ? ORDER BY id DESC LIMIT 5",  # ✏️ 8-3: 이 고객 것만
                          (f"%{query.strip()}%",)).fetchall()
    return "메모: " + " / ".join(r["text"] for r in rows) if rows else "메모가 없습니다."


def notes_for(user_id: str) -> list[str]:
    """다음 상담에서 기억할 것. 지시문에 [고객 메모]로 붙는다."""
    with session() as db:
        rows = db.execute("SELECT text FROM memories WHERE customer_id = ? ORDER BY id",  # ✏️ 8-3: 확인된·안 지난 것만
                          (user_id,)).fetchall()
    return [r["text"] for r in rows]
