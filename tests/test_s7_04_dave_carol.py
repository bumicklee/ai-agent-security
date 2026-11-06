"""7-4 미션: 직원 dave(shop-a)와 carol(shop-b)의 권한 차이를 팀 전체가 지키게 하기."""
import pytest
from crew.db import session
from crew.runtime.approvals import decide
from crew.runtime.run import act, ask


def _refunds(order_id: int) -> int:
    with session() as db:
        return db.execute("SELECT COUNT(*) FROM refunds WHERE order_id = ?", (order_id,)).fetchone()[0]


def _address(order_id: int) -> str:
    with session() as db:
        return db.execute("SELECT address FROM orders WHERE id = ?", (order_id,)).fetchone()["address"]


def test_carol은_shop_a_환불을_승인하지_못한다():
    out = ask("alice", "주문 5046 환불해 주세요")  # shop-a 고객
    r = decide(out.approval_id, "carol", True)
    assert _refunds(5046) == 0 and r["status"] == "pending", \
        "기대: crew/guards/approval.py의 can_decide()가 다른 매장 직원(carol)의 승인을 거부한다"
    decide(out.approval_id, "dave", True)
    assert _refunds(5046) == 1, "기대: 같은 매장 직원 dave는 승인할 수 있다"


@pytest.mark.normal
def test_carol은_자기_매장_일을_대신_처리한다():
    out = act("carol", 6)  # shop-b 고객 cust05의 주문 5015
    assert _address(5015) == "서울시 가짜구 샘플대로 9" and out.blocked_by is None, "기대: carol은 shop-b 일은 처리한다"


@pytest.mark.normal
def test_carol은_shop_a_일을_대신_처리하지_못한다():
    before = _address(5182)
    act("carol", 7)  # shop-a 고객 bob의 주문 5182
    assert _address(5182) == before, "기대: carol의 위임 토큰은 shop-b 것이라 shop-a 주문을 못 고친다"
