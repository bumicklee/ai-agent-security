"""매장 정책 문서 검색(5-2). SQLite FTS5(trigram)로 찾는다.

trigram은 3글자 이상에서만 MATCH가 된다. "반품"처럼 2글자면 LIKE로 찾는다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


def _find(db, q: str):
    if len(q) >= 3:
        return db.execute("SELECT d.* FROM docs_fts f JOIN docs d ON d.id = f.id WHERE docs_fts MATCH ? "
                          "ORDER BY rank LIMIT 5", ('"' + q.replace('"', '""') + '"',)).fetchall()
    return db.execute("SELECT * FROM docs WHERE title LIKE ? OR body LIKE ? LIMIT 5", (f"%{q}%", f"%{q}%")).fetchall()


@function_tool
def search_policy(ctx: RunContextWrapper[CrewContext], query: str) -> str:
    """매장 정책·공지 문서를 검색해 제목과 본문을 돌려준다."""
    q = query.strip()[:50]
    with session() as db:
        rows = _find(db, q)  # ✏️ 5-6: 로그인 매장(store_id)과 공개 문서(visibility)만 찾게 SQL에 조건을 더한다
    if not rows:
        return "찾는 문서가 없습니다."
    return "\n".join(f"[{r['title']}] {r['body']}" for r in rows)  # ✏️ 5-6: 문서는 <문서 데이터>로 감싼다
