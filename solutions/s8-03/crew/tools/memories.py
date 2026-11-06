"""고객 메모(8-1). 상담원 팀이 고객을 기억한다: 선호 배송지, 연락 시간, 지난 문의.

- remember: 고객이 "기억해 둬"라고 한 것을 memories 테이블에 적는다
- recall_memory: 메모를 찾아 본다
- notes_for: 다음 상담에서 주문 담당의 지시문에 붙일 메모(crew/agents/orders.py)

8-3: 메모는 "사실"이 아니라 "누가 언제 한 말"이다.
- 출처(source): 모델이 정리해 적은 메모는 agent. 확인 등급(trust)은 늘 unverified로 시작한다
- 만료(expires_at): 30일. 지난 메모는 읽지 않는다
- 고객별 격리: 로그인한 고객의 메모만 읽는다(검색도)
- 지시문에는 직원이 확인한(confirmed) 메모만 붙인다. 미확인 메모는 할인·권한의 근거가 되지 않는다
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session

TTL_DAYS = 30
FRESH = "(expires_at IS NULL OR expires_at > datetime('now', 'localtime'))"


@function_tool
def remember(ctx: RunContextWrapper[CrewContext], text: str) -> str:
    """고객이 기억해 달라고 한 것(선호 배송지·연락 시간 등)을 메모한다."""
    user, text = ctx.context.user, text.strip()[:200]
    with session() as db:
        db.execute("INSERT INTO memories(customer_id, text, source, trust, created_at, expires_at, run_id) "
                   "VALUES (?, ?, 'agent', 'unverified', datetime('now', 'localtime'), "
                   "datetime('now', 'localtime', ?), ?)", (user.id, text, f"+{TTL_DAYS} days", ctx.context.run_id))
    return f"기억해 두겠습니다(직원 확인 전까지는 참고만 합니다): {text}"


@function_tool
def recall_memory(ctx: RunContextWrapper[CrewContext], query: str = "") -> str:
    """메모를 찾아 본다(빈 검색어면 최근 메모)."""
    with session() as db:
        rows = db.execute(f"SELECT text, trust FROM memories WHERE customer_id = ? AND text LIKE ? AND {FRESH} "
                          "ORDER BY id DESC LIMIT 5", (ctx.context.user.id, f"%{query.strip()}%")).fetchall()
    if not rows:
        return "메모가 없습니다."
    return "메모: " + " / ".join(r["text"] + ("" if r["trust"] == "confirmed" else "(미확인)") for r in rows)


def notes_for(user_id: str) -> list[str]:
    """다음 상담에서 기억할 것. 직원이 확인했고 만료되지 않은 메모만 지시문에 [고객 메모]로 붙는다."""
    with session() as db:
        rows = db.execute(f"SELECT text FROM memories WHERE customer_id = ? AND trust = 'confirmed' AND {FRESH} "
                          "ORDER BY id", (user_id,)).fetchall()
    return [r["text"] for r in rows]
