"""2-4 지키기: 남의 주문은 도구가 거부한다. 모델이 아니라 코드가 막는다."""
import pytest
from crew.runtime.run import ask


def test_남의_주문은_거부한다():
    out = ask("bob", "주문 1001 보여 주세요")  # 1001은 alice 주문
    assert "주문자 alice" not in out.reply and "샘플대로" not in out.reply, "기대: bob에게 alice 주문 내용이 보이지 않는다"
    assert out.blocked_by == "code", "기대: 도구가 '거부:'로 시작하는 글을 돌려준다(③ 내 코드가 막음)"


@pytest.mark.normal
def test_내_주문은_그대로_보인다():
    out = ask("bob", "주문 2001 보여 주세요")
    assert "2001" in out.reply and out.blocked_by is None, "기대: 정상 요청은 막지 않는다(오탐 없음)"


@pytest.mark.normal
def test_모델이_사용자를_정하지_못한다():
    from crew.team import find_tool

    tool = find_tool("get_order") or find_tool("get_my_order")  # 5-1부터는 주문 담당이 쥐고 있다
    params = tool.params_json_schema.get("properties", {})
    assert not {"user_id", "customer_id", "user"} & set(params), "기대: 누가 묻는지는 도구 인자가 아니라 ctx.context에서 온다"
