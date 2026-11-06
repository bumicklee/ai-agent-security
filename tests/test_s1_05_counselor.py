"""1-5 첫 상담원: FAQ로 답한다."""
from crew.runtime.run import ask


def test_FAQ로_답한다():
    out = ask("alice", "환불 기간이 어떻게 되나요?")
    assert "7일" in out.reply, "기대: 상담원이 지시문의 FAQ(환불 7일)로 답한다"
    assert out.agent == "상담원"
