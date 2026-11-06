"""11-1 만들기: 감독자가 복합 문의를 나눠 맡긴다 (6명)."""
import pytest
from crew.db import session
from crew.runtime.run import ask
from crew.team import slots

COMPOUND = "주문 1002 배송지를 서울시 가짜구 예시길 30으로 바꾸고 주문 1001 환불해 주세요"


def _one(sql: str):
    with session() as db:
        return db.execute(sql).fetchone()[0]


def test_복합_문의를_나눠_맡긴다():
    out = ask("alice", COMPOUND)
    assert out.agent == "감독자", "기대: 접수가 일이 둘 이상인 문의를 감독자에게 넘긴다(transfer_to_supervisor)"
    assert {"ask_orders", "ask_refunds"} <= set(out.tools), "기대: 감독자가 담당들을 도구로(as_tool) 부른다"
    assert _one("SELECT address FROM orders WHERE id = 1002") == "서울시 가짜구 예시길 30", "기대: 주문 담당이 배송지를 바꾼다"
    assert _one("SELECT COUNT(*) FROM refunds WHERE order_id = 1001") == 1, "기대: 환불 담당이 1001을 환불한다(5만 원 이하 자동)"


@pytest.mark.normal
def test_한_가지_일은_감독자를_거치지_않는다():
    out = ask("alice", "주문 1001 환불해 주세요")
    assert out.agent == "환불 담당", "기대: 단순 문의는 그대로 담당에게(감독자는 복합 문의만)"


def test_조직도에_감독자가_켜진다():
    assert "감독자" in {s.name for s in slots() if s.active}, "기대: /ops 조직도에 감독자 칸(6명)"


def test_쿠폰도_승인_길을_그대로_지난다():
    from crew.runtime.approvals import decide

    out = ask("alice", "주문 1001 환불하고 주문 1002 배송지를 서울시 가짜구 예시길 30으로 바꾸고 보상 쿠폰도 주세요")
    assert out.agent == "감독자" and "ask_orders" in out.tools, "기대: 일이 셋인 문의는 감독자가 나눠 맡긴다"
    assert out.blocked_by == "approval", "기대: 감독자가 맡겨도 쿠폰은 직원 승인 대기(담당의 정책을 그대로 지난다)"
    decide(out.approval_id, "dave", True)
    assert _one("SELECT COUNT(*) FROM coupons WHERE customer_id = 'alice'") == 1, "기대: 승인 뒤 이어서 쿠폰 발급"
