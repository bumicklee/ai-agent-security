"""6-4: 승인 화면. 모델이 쓴 요약 대신 실제로 바뀌는 내용(diff)과 위험 색을 보여 준다.
6-5: 금액·건수 예산과 승인 단계(자동 / 사람 한 명 / 두 사람).

완성본(crew/runtime/approvals.py)이 승인 대기를 저장할 때 describe()를 부른다.
돌려주는 값: {"diff": 화면에 보일 글, "risk": "low"|"mid"|"high", "approvers": 필요한 승인자 수}
"""
from __future__ import annotations

from crew.db import session

AUTO_MAX = 50_000        # 한 건, 이 금액 이하 → 자동 승인
ONE_MAX = 300_000        # 한 건, 이 금액 이하 → 직원 한 명
REQUEST_MAX = (3, 500_000)   # 한 번에: 3건, 50만 원까지. 넘으면 거부
DAILY_MAX = 5            # 고객 한 명이 하루에 환불할 수 있는 건수


def tier(p) -> str:
    if len(p.rows) == 1 and p.total <= AUTO_MAX:
        return "auto"
    return "one" if len(p.rows) == 1 and p.total <= ONE_MAX else "two"


def over_budget(user, p) -> str | None:
    if len(p.rows) > REQUEST_MAX[0] or p.total > REQUEST_MAX[1]:
        return "거부: 한 번에 환불할 수 있는 한도(3건·500,000원)를 넘었습니다. 나눠서 요청하거나 직원에게 문의해 주세요."
    with session() as db:
        today = db.execute("SELECT COUNT(*) FROM refunds WHERE requested_by = ? AND date(created_at) = date('now', 'localtime')",
                           (user.id,)).fetchone()[0]
    if today + len(p.rows) > DAILY_MAX:
        return "거부: 오늘 환불할 수 있는 건수를 넘었습니다. 직원에게 문의해 주세요."
    return None


async def needs_refund_approval(ctx, params: dict, call_id: str) -> bool:
    """request_refund의 needs_approval. 예산을 넘으면 도구가 바로 거부하게 두고, 작은 한 건은 자동."""
    from crew.tools.refunds import preview

    p = preview(ctx.context.user.id, params.get("order_ids", []))
    return over_budget(ctx.context.user, p) is None and tier(p) != "auto"


def describe(action: str, args: dict, user) -> dict:
    from crew.tools.refunds import preview

    if action == "request_refund":
        p = preview(user.id, args.get("order_ids", []))
        risk = "high" if len(p.rows) > 1 or p.total > ONE_MAX else "mid" if p.total > AUTO_MAX else "low"
        return {"diff": p.text, "risk": risk, "approvers": 2 if tier(p) == "two" else 1}
    # ✏️ 6-6: issue_coupon 갈래 — 금액(5,000원)과 받는 사람이 보이는 diff
    return {"diff": f"{action} {args}", "risk": "mid", "approvers": 1}
