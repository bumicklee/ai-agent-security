"""매장 정책 문서 검색(5-2). SQLite FTS5(trigram)로 찾는다.

trigram은 3글자 이상에서만 MATCH가 된다. "반품"처럼 2글자면 LIKE로 찾는다.
5-6: 매장·공개 여부는 모델이 아니라 로그인 정보로 SQL에서 거른다. 검색 결과는 <문서 데이터>로 감싸
"자료일 뿐 지시가 아니다"를 표시하고, 매장이 올린 문서(uploaded)는 판별기를 한 번 더 거친다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session
from crew.guards.injection import build_judge
from crew.runtime.guardkit import ask_judge

ALLOWED = "AND d.store_id = :store AND (d.visibility = 'public' OR :staff)"  # 로그인 매장 + 공개 문서(직원은 내부도)


def _find(db, q: str, user):
    p = {"q": '"' + q.replace('"', '""') + '"', "like": f"%{q}%", "store": user.store_id, "staff": user.is_staff}
    if len(q) >= 3:
        return db.execute(f"SELECT d.* FROM docs_fts f JOIN docs d ON d.id = f.id WHERE docs_fts MATCH :q {ALLOWED} "
                          "ORDER BY rank LIMIT 5", p).fetchall()
    return db.execute(f"SELECT * FROM docs d WHERE (d.title LIKE :like OR d.body LIKE :like) {ALLOWED} LIMIT 5",
                      p).fetchall()


async def _safe(row, ctx: CrewContext) -> bool:
    if row["trust"] != "uploaded":
        return True
    try:
        return not (await ask_judge(build_judge(), row["body"], ctx)).is_attack
    except Exception:
        return False  # 판별기가 고장 나면 빼 둔다(fail-closed)


@function_tool
async def search_policy(ctx: RunContextWrapper[CrewContext], query: str) -> str:
    """매장 정책·공지 문서를 검색해 제목과 본문을 돌려준다."""
    q = query.strip()[:50]
    with session() as db:
        rows = _find(db, q, ctx.context.user)
    rows = [r for r in rows if await _safe(r, ctx.context)]
    if not rows:
        return "거부: 보여 드릴 수 있는 문서가 없습니다."
    return "\n".join(f'<문서 데이터 id="{r["id"]}" 출처="{r["trust"]}">[{r["title"]}] {r["body"]}</문서 데이터>'
                     for r in rows)
