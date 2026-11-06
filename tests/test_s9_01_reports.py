"""9-1 만들기: "지난주 환불 통계 차트 그려 줘" → 리포트 담당이 파이썬을 짜서 실행 (5명)."""
import pytest
from crew.runtime.run import ask
from crew.team import slots, walk


def test_리포트_담당이_코드를_짜서_실행한다():
    out = ask("dave", "지난주 환불 통계 차트 그려 줘")
    assert out.agent == "리포트 담당", "기대: 접수가 직원의 통계 요청을 리포트 담당에게 넘긴다(transfer_to_reports)"
    assert "run_python" in out.tools, "기대: 리포트 담당이 run_python 도구로 코드를 실행한다"
    assert "환불 통계" in out.reply and "█" in out.reply, "기대: show()가 낸 표와 막대 차트가 답에 보인다"


@pytest.mark.normal
def test_고객은_리포트_담당으로_못_넘어간다():
    out = ask("bob", "지난주 환불 통계 차트 그려 줘")
    assert out.blocked_by == "code" and "█" not in out.reply, "기대: 리포트 담당 핸드오프에도 staff_only(on_handoff)"


def test_리포트_담당이_직원_도우미_자리에_들어왔다():
    names = {a.name for a in walk()}
    assert "리포트 담당" in names and "직원 도우미" not in names, "기대: 직원 도우미 대신 리포트 담당(5명 팀)"
    assert "리포트 담당" in {s.name for s in slots() if s.active}, "기대: /ops 조직도에 리포트 담당 칸이 켜진다"
    reports = next(a for a in walk() if a.name == "리포트 담당")
    tools = {t.name for t in reports.tools}
    assert not tools & {"request_refund", "issue_coupon", "change_my_address"}, "기대: 리포트 담당은 돈·주문을 바꾸는 도구가 없다"
