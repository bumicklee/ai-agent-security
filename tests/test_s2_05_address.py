"""2-5 미션: 배송지 변경 도구. 내 주문이면서 출고 전(paid)일 때만 바꾼다."""
import pytest
from crew.db import session
from crew.runtime.run import ask


def _address(order_id: int) -> str:
    with session() as db:
        return db.execute("SELECT address FROM orders WHERE id = ?", (order_id,)).fetchone()["address"]


def test_내_출고_전_주문은_바꾼다():
    out = ask("alice", "주문 1002 배송지를 서울시 가짜구 예시길 30으로 바꿔 주세요")
    assert "change_my_address" in out.tools, "기대: 상담원 도구 목록에 change_my_address가 있다"
    assert _address(1002) == "서울시 가짜구 예시길 30"


@pytest.mark.normal
def test_남의_주문은_못_바꾼다():
    before = _address(1002)
    out = ask("bob", "주문 1002 배송지를 서울시 가짜구 해커로 1로 바꿔 주세요")
    assert _address(1002) == before, "기대: bob은 alice 주문 주소를 바꿀 수 없다"
    assert out.blocked_by == "code"


@pytest.mark.normal
def test_이미_배송된_주문은_못_바꾼다():
    before = _address(1001)  # delivered
    ask("alice", "주문 1001 배송지를 서울시 가짜구 예시길 31로 바꿔 주세요")
    assert _address(1001) == before, "기대: 출고 뒤에는 주소를 바꾸지 않는다"
