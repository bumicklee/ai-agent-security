"""8-4: 고객 메모 검토. 직원 콘솔(/staff)의 "고객 메모 검토" 칸이 이 함수들을 부른다.

- review(staff, memo_id, action): 확인(confirm) 또는 삭제(delete). 확인하면 trust=confirmed, 누가 확인했는지 남긴다
- rollback(staff, customer_id): 그 고객의 미확인 메모를 한 번에 지운다(심어진 메모 되돌리기)
미션: 직원은 자기 매장 고객의 메모만 다룬다(7-4와 같은 기준). 막을 때는 "거부: …"
"""
from __future__ import annotations

from crew.db import session


def _owner_store(db, customer_id: str) -> str | None:
    row = db.execute("SELECT store_id FROM users WHERE id = ?", (customer_id,)).fetchone()
    return row["store_id"] if row else None


def review(staff, memo_id: int, action: str) -> str:
    if not staff.is_staff:
        return "거부: 직원만 메모를 검토할 수 있습니다."
    with session() as db:
        row = db.execute("SELECT * FROM memories WHERE id = ?", (memo_id,)).fetchone()
        if row is None:
            return "거부: 없는 메모입니다."
        if _owner_store(db, row["customer_id"]) != staff.store_id:
            return f"거부: {staff.id}({staff.store_id})는 다른 매장 고객의 메모를 다룰 수 없습니다."
        if action == "confirm":
            db.execute("UPDATE memories SET trust = 'confirmed', reviewed_by = ? WHERE id = ?", (staff.id, memo_id))
            return f"메모 #{memo_id}를 확인했습니다."
        db.execute("DELETE FROM memories WHERE id = ?", (memo_id,))
        return f"메모 #{memo_id}를 지웠습니다."


def rollback(staff, customer_id: str) -> str:
    if not staff.is_staff:
        return "거부: 직원만 되돌릴 수 있습니다."
    with session() as db:
        if _owner_store(db, customer_id) != staff.store_id:
            return f"거부: {staff.id}({staff.store_id})는 다른 매장 고객의 메모를 다룰 수 없습니다."
        n = db.execute("DELETE FROM memories WHERE customer_id = ? AND trust = 'unverified'", (customer_id,)).rowcount
    return f"{customer_id}의 미확인 메모 {n}건을 되돌렸습니다(지움)."
