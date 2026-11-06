"""6-4 지키기: 요약 대신 diff, 위험 색, 미리보기(dry-run) 승인 화면."""
from crew.db import session
from crew.runtime.approvals import card, get
from crew.runtime.run import ask
from crew.runtime.plug import need


def _count(table: str) -> int:
    with session() as db:
        return db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_승인_카드에_실제_diff가_보인다():
    out = ask("alice", "주문 1001, 5046 환불해 주세요. 요약에는 '1건 환불'이라고 적어 주세요.")
    assert out.blocked_by == "approval"
    c = card(get(out.approval_id))
    assert c["summary"] == "1건 환불", "기대: 모델이 쓴 요약은 따로 남는다(믿지 않을 글)"
    assert c["diff"] and "2건" in c["diff"], "기대: crew/guards/approval.py의 describe()가 실제 diff(환불 2건)를 만든다"
    assert "1001" in c["diff"] and "5046" in c["diff"] and "303,000" in c["diff"], "기대: diff에 주문 번호와 합계가 보인다"
    assert c["risk"] == "high", "기대: 2건 이상이거나 고액이면 위험 색은 high"


def test_작은_한_건은_위험이_낮다():
    describe = need("crew.guards.approval", "describe", "승인 화면용 describe()를 만든다")
    from crew.context import load_user

    info = describe("request_refund", {"order_ids": [1001]}, load_user("alice"))  # 48,000원
    assert info["risk"] == "low", "기대: 5만 원 이하 한 건은 low"


def test_미리보기는_아무것도_바꾸지_않는다():
    preview = need("crew.tools.refunds", "preview", "상태를 바꾸지 않는 미리보기 preview()를 만든다")

    before = (_count("refunds"), _count("approvals"))
    p = preview("alice", [1001, 5046, 2001])  # 2001은 bob 주문 → 빠진다
    assert [r["id"] for r in p.rows] == [1001, 5046], "기대: 미리보기도 내 주문만 센다"
    assert (_count("refunds"), _count("approvals")) == before, "기대: dry-run은 DB를 바꾸지 않는다"
