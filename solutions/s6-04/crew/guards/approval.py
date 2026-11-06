"""6-4: 승인 화면. 모델이 쓴 요약 대신 실제로 바뀌는 내용(diff)과 위험 색을 보여 준다.

완성본(crew/runtime/approvals.py)이 승인 대기를 저장할 때 describe()를 부른다.
돌려주는 값: {"diff": 화면에 보일 글, "risk": "low"|"mid"|"high", "approvers": 필요한 승인자 수}
"""
from __future__ import annotations

from crew.tools.refunds import preview


def describe(action: str, args: dict, user) -> dict:
    if action == "request_refund":
        p = preview(user.id, args.get("order_ids", []))
        risk = "high" if len(p.rows) > 1 or p.total > 300_000 else "mid" if p.total > 50_000 else "low"
        return {"diff": p.text, "risk": risk}  # ✏️ 6-5: 필요한 승인자 수(approvers)도 돌려준다
    return {"diff": f"{action} {args}", "risk": "mid"}
