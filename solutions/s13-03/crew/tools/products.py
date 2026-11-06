"""재고 조회(13-3). 내 도메인 도구 하나 더하기의 예. 같은 레시피를 따른다.

1. 누가 묻는가는 ctx에서(인자로 받지 않는다) 2. 로그인 매장 것만 SQL 조건으로 3. 읽기 전용, 결과는 짧게
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.db import session


@function_tool
def check_stock(ctx: RunContextWrapper[CrewContext], product: str) -> str:
    """상품 이름으로 로그인한 매장의 재고와 가격을 본다."""
    with session() as db:
        rows = db.execute("SELECT name, price_krw, stock FROM products WHERE store_id = ? AND name LIKE ? LIMIT 5",
                          (ctx.context.user.store_id, f"%{product.strip()[:30]}%")).fetchall()
    if not rows:
        return "거부: 이 매장에서 찾을 수 없는 상품입니다."
    return " / ".join(f"{r['name']} {r['price_krw']:,}원 재고 {r['stock']}개" for r in rows)
