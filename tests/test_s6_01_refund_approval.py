"""6-1 만들기: 환불 도구와 needs_approval, 직원 콘솔 승인 대기열."""
import json

from crew.db import session
from crew.runtime.approvals import decide
from crew.runtime.run import ask


def _refunds(order_id: int) -> int:
    with session() as db:
        return db.execute("SELECT COUNT(*) FROM refunds WHERE order_id = ?", (order_id,)).fetchone()[0]


def _approval(approval_id: int):
    with session() as db:
        return db.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()


def test_환불은_승인_대기로_멈춘다():
    out = ask("alice", "주문 5046 환불해 주세요")
    assert out.agent == "환불 담당", "기대: 접수가 환불 요청을 환불 담당에게 넘긴다(transfer_to_refunds)"
    assert out.blocked_by == "approval" and out.approval_id, "기대: request_refund(needs_approval=True)에서 실행이 멈춘다"
    assert _refunds(5046) == 0, "기대: 승인 전에는 환불이 일어나지 않는다"
    row = _approval(out.approval_id)
    assert row["status"] == "pending" and json.loads(row["run_state_json"]), "기대: RunState가 승인 대기열에 저장된다"


def test_직원이_승인하면_이어서_실행된다():
    out = ask("alice", "주문 5046 환불해 주세요")
    r = decide(out.approval_id, "dave", True)
    assert r["status"] == "approved" and _refunds(5046) == 1, "기대: 승인 → RunState.approve() → 이어서 실행 → 환불 1건"
    assert "환불" in r["reply"], "기대: 이어서 실행한 답이 돌아온다"


def test_직원이_거절하면_실행되지_않는다():
    out = ask("alice", "주문 5046 환불해 주세요")
    assert out.approval_id, "기대: 환불은 승인 대기로 멈춘다(needs_approval)"
    r = decide(out.approval_id, "dave", False)
    assert r["status"] == "rejected" and _refunds(5046) == 0, "기대: 거절 → RunState.reject() → 환불 없음"


def test_고객은_승인할_수_없다():
    out = ask("alice", "주문 5046 환불해 주세요")
    assert out.blocked_by == "approval", "기대: 환불은 먼저 승인 대기로 멈춘다(needs_approval=True)"
    decide(out.approval_id, "bob", True)
    assert _refunds(5046) == 0 and _approval(out.approval_id)["status"] == "pending", "기대: 고객은 승인 버튼을 눌러도 소용없다"
