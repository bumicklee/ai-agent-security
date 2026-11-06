"""5-1 만들기: 핸드오프로 접수 → 주문 담당·지식 담당."""
import pytest
from crew.runtime.run import ask
from crew.team import entry_agent, slots, walk


def test_팀이_세_명_이상이다():
    names = {a.name for a in walk()}
    assert {"상담원", "주문 담당", "지식 담당"} <= names, "기대: 상담원(접수)의 handoffs로 주문 담당·지식 담당이 이어진다"


def test_접수는_도구_없이_넘기기만_한다():
    assert not entry_agent().tools, "기대: 접수 상담원의 tools는 비어 있다(도구는 담당들이 쥔다)"
    names = {h.tool_name for h in entry_agent().handoffs}
    assert {"transfer_to_orders", "transfer_to_knowledge"} <= names, \
        "기대: handoff(..., tool_name_override='transfer_to_orders') 처럼 영어 이름을 준다"


def test_주문_문의는_주문_담당이_답한다():
    out = ask("alice", "주문 1002 어디쯤 왔어요?")
    assert out.agent == "주문 담당" and "1002" in out.reply, "기대: 주문 문의는 주문 담당에게 넘어가 get_order로 답한다"


@pytest.mark.normal
def test_FAQ는_접수가_바로_답한다():
    out = ask("alice", "배송은 얼마나 걸려요?")
    assert out.agent == "상담원" and "1~3일" in out.reply, "기대: FAQ는 넘기지 않고 접수가 답한다"


def test_조직도에_칸이_켜진다():
    on = {s.name for s in slots() if s.active}
    assert {"주문 담당", "지식 담당"} <= on, "기대: /ops 조직도에 주문 담당·지식 담당 칸이 켜진다"
