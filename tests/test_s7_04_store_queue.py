"""7-4: 직원 콘솔 승인 대기열은 자기 매장 것만 보인다(화면). 권한 검사는 can_decide()가 따로 한다."""
import pytest
from fastapi.testclient import TestClient

from crew.runtime.run import ask


@pytest.mark.normal
def test_다른_매장_카드는_화면에_없다():
    from crew.web.app import app

    out = ask("alice", "주문 5046 환불해 주세요")  # shop-a
    c = TestClient(app)
    c.cookies.set("crew_user", "carol")
    assert f'id="ap-{out.approval_id}"' not in c.get("/staff").text, "기대: shop-b 직원 carol에게 shop-a 승인 카드가 안 보인다"
    c.cookies.set("crew_user", "dave")
    assert f'id="ap-{out.approval_id}"' in c.get("/staff").text, "기대: 같은 매장 dave에게는 보인다"
