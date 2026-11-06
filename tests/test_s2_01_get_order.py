"""2-1 첫 도구: 상담원이 주문 조회 도구를 부른다."""
from crew.runtime.run import ask


def test_내_주문을_조회한다():
    out = ask("alice", "주문 1002 어디쯤 왔어요?")
    assert "get_order" in out.tools or "get_my_order" in out.tools, "기대: 주문 조회 도구를 부른다"
    assert "1002" in out.reply
