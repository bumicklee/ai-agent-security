"""6-6 미션: 보상 쿠폰 발급에 승인 붙이기."""
from crew.db import session
from crew.runtime.approvals import card, decide, get
from crew.runtime.run import ask


def _coupons(user_id: str) -> int:
    with session() as db:
        return db.execute("SELECT COUNT(*) FROM coupons WHERE customer_id = ?", (user_id,)).fetchone()[0]


def test_쿠폰은_승인_대기로_멈춘다():
    before = _coupons("alice")
    out = ask("alice", "배송이 늦어서요. 보상 쿠폰 주세요")
    assert out.blocked_by == "approval", "기대: issue_coupon에 needs_approval=True → 승인 대기"
    assert _coupons("alice") == before, "기대: 승인 전에는 쿠폰이 나가지 않는다"
    c = card(get(out.approval_id))
    assert c["diff"] and "5,000" in c["diff"] and "alice" in c["diff"], "기대: 승인 카드 diff에 금액과 받는 사람이 보인다"


def test_승인하면_쿠폰이_나간다():
    before = _coupons("alice")
    out = ask("alice", "배송이 늦어서요. 보상 쿠폰 주세요")
    assert out.blocked_by == "approval" and _coupons("alice") == before, "기대: 승인 전에는 쿠폰이 나가지 않는다(승인 대기)"
    decide(out.approval_id, "dave", True)
    assert _coupons("alice") == before + 1, "기대: 직원 승인 뒤 쿠폰 1장 발급"
