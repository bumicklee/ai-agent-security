"""10-1 만들기: 택배사 배송 조회 MCP 서버 연결."""
import pytest
from crew.runtime.run import ask
from crew.team import mcp_names


def test_주문_담당에_택배사_서버가_붙는다():
    assert "carrier" in mcp_names(), "기대: 주문 담당의 mcp_servers에 carrier 서버(MCPServerStdio)가 있다"


def test_운송장으로_배송을_조회한다():
    out = ask("alice", "운송장 FAKE-TRK-001001 배송 조회해 주세요")
    assert out.agent == "주문 담당" and "track_shipment" in out.tools, "기대: 주문 담당이 MCP 도구 track_shipment를 부른다"
    assert "배송 완료" in out.reply, "기대: 택배사 DB(data/carrier.db)의 상태가 답에 보인다"


@pytest.mark.normal
def test_MCP를_안_쓰는_문의는_그대로():
    out = ask("alice", "주문 1002 어디쯤 왔어요?")
    assert "1002" in out.reply, "기대: 다른 문의는 그대로 된다"
