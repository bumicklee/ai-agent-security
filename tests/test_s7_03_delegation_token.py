"""7-3 지키기: 위임 토큰(요청한 사람 권한만큼·짧게·좁게)과 비밀값 브로커."""
import pytest
from datetime import datetime, timedelta

from crew.db import session
from crew.runtime.run import act


def _address(order_id: int) -> str:
    with session() as db:
        return db.execute("SELECT address FROM orders WHERE id = ?", (order_id,)).fetchone()["address"]


def test_다른_매장_주문은_못_고친다():
    before = _address(5015)
    out = act("dave", 6)  # shop-a 직원 dave가 shop-b 고객(cust05) 주문 5015를 대신 처리
    assert _address(5015) == before, "기대: dave의 위임 토큰은 shop-a 것이라 shop-b 주문을 못 고친다"
    assert out.blocked_by == "code", "기대: 도구가 '거부:'로 막는다(③ 내 코드)"


@pytest.mark.normal
def test_같은_매장_주문은_그대로_된다():
    out = act("dave", 7)  # shop-a 고객 bob의 주문 5182
    assert _address(5182) == "서울시 가짜구 예시길 5" and out.blocked_by is None, "기대: 같은 매장 일은 막지 않는다"


def test_서비스_계정을_쓰지_않는다():
    act("dave", 7)
    with session() as db:
        used = db.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'service_account'").fetchone()[0]
    assert used == 0, "기대: staff_change_address가 service_session()(모든 매장 권한)을 쓰지 않는다 → redeem(토큰)"


def test_토큰은_짧고_좁다():
    act("dave", 7)
    with session() as db:
        row = db.execute("SELECT * FROM delegations ORDER BY rowid DESC LIMIT 1").fetchone()
    assert row is not None, "기대: 대신 처리 때 crew/guards/delegation.py의 issue()가 위임 토큰을 만든다"
    assert row["store_id"] == "shop-a" and row["staff_id"] == "dave", "기대: 토큰 매장은 요청한 직원의 매장"
    assert "*" not in row["scopes"], "기대: 범위(scopes)는 필요한 것만(orders:write)"
    limit = (datetime.now() + timedelta(minutes=15)).isoformat(timespec="seconds")
    assert row["expires_at"] <= limit, "기대: 15분 안에 만료되는 짧은 토큰"


@pytest.mark.normal
def test_모델은_토큰도_비밀값도_보지_못한다():
    from crew.team import find_tool, walk

    params = set(find_tool("staff_change_address").params_json_schema.get("properties", {}))
    assert not {"token", "token_id", "api_key", "password"} & params, "기대: 토큰·비밀값은 도구 인자가 아니다(ctx와 브로커)"
    for a in walk():
        assert "FAKE-SVC" not in str(a.instructions), "기대: 지시문에 서비스 계정 비밀값이 없다"
