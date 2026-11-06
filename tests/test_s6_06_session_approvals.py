"""6-6 회귀: 대화 기록을 켠 한 대화에서 승인을 두 번 받아도 이어서 실행된다(서버를 다시 띄워도)."""
from crew.db import session
from crew.runtime.approvals import decide
from crew.runtime.llm import get_model
from crew.runtime.run import ask


def _count(sql: str) -> int:
    with session() as db:
        return db.execute(sql).fetchone()[0]


def test_한_대화에서_승인을_두_번():
    first = ask("alice", "주문 5046 환불해 주세요", remember=True)
    assert first.blocked_by == "approval", "기대: 환불은 승인 대기"
    assert decide(first.approval_id, "dave", True)["status"] == "approved"
    get_model.cache_clear()  # 서버를 다시 띄운 것처럼(가짜 LLM의 호출 번호가 처음부터)
    second = ask("alice", "배송 지연 보상 쿠폰 주세요", remember=True)
    assert second.blocked_by == "approval", "기대: 쿠폰도 승인 대기(issue_coupon에 needs_approval)"
    r = decide(second.approval_id, "dave", True)
    assert r["status"] == "approved" and _count("SELECT COUNT(*) FROM coupons WHERE customer_id = 'alice'") >= 1, \
        "기대: 같은 대화의 두 번째 승인도 이어서 실행된다"
