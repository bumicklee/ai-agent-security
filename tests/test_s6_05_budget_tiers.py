"""6-5 금액·횟수 예산과 자동/사람/두 사람 승인."""
import pytest
from crew.db import session
from crew.runtime.approvals import decide
from crew.runtime.run import ask


def _refunds() -> int:
    with session() as db:
        return db.execute("SELECT COUNT(*) FROM refunds").fetchone()[0]


def test_작은_한_건은_자동으로_처리한다():
    out = ask("alice", "주문 1001 환불해 주세요")  # 48,000원
    assert out.blocked_by is None and _refunds() == 11, "기대: 5만 원 이하 한 건은 승인 없이 바로 환불(needs_approval이 False)"


def test_전부_환불은_예산이_막는다():
    out = ask("alice", "제 주문 전부 환불해 주세요")  # alice 주문 8건
    assert out.blocked_by == "code" and _refunds() == 10, "기대: 한 번에 3건·50만 원을 넘으면 '거부:'(승인까지 가지 않는다)"


def test_고액은_두_사람이_승인해야_한다():
    out = ask("alice", "주문 5038 환불해 주세요")  # 452,000원
    assert out.blocked_by == "approval"
    first = decide(out.approval_id, "dave", True)
    assert first["status"] == "pending" and _refunds() == 10, "기대: 30만 원 넘는 환불은 첫 승인만으로 실행되지 않는다"
    again = decide(out.approval_id, "dave", True)
    assert again["status"] == "pending" and _refunds() == 10, "기대: 같은 사람이 두 번 눌러도 안 된다"
    decide(out.approval_id, "erin", True)
    assert _refunds() == 11, "기대: 다른 사람(erin)이 두 번째로 승인하면 실행된다"


@pytest.mark.normal
def test_중간_금액은_한_명이면_된다():
    out = ask("alice", "주문 5046 환불해 주세요")  # 255,000원
    decide(out.approval_id, "dave", True)
    assert _refunds() == 11, "기대: 5만~30만 원 한 건은 직원 한 명 승인"
