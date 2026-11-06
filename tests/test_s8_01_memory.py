"""8-1 만들기: 고객 메모(선호 배송지, 지난 문의)를 다음 상담에서 기억."""
import asyncio

from agents import RunContextWrapper

from crew.context import CrewContext, load_user
from crew.db import session
from crew.runtime.run import ask


def _prompt(user_id: str) -> str:
    from crew.team import walk

    agent = next(a for a in walk() if a.name == "주문 담당")
    ctx = RunContextWrapper(CrewContext(user=load_user(user_id)))
    return asyncio.run(agent.get_system_prompt(ctx)) or ""


def test_기억해_달라는_것을_메모한다():
    out = ask("alice", "기억해 둬, 배송은 경비실에 맡겨 주세요")
    assert "remember" in out.tools, "기대: 주문 담당이 remember 도구로 메모를 남긴다"
    with session() as db:
        row = db.execute("SELECT * FROM memories WHERE customer_id = 'alice' ORDER BY id DESC LIMIT 1").fetchone()
    assert row and "경비실" in row["text"], "기대: memories 테이블에 alice의 메모가 한 줄 생긴다"


def test_다음_상담에서_메모를_기억한다():
    assert "문 앞" in _prompt("alice"), "기대: 주문 담당 지시문에 alice의 메모(문 앞에 두기)가 [고객 메모]로 붙는다"
    assert "문 앞" not in _prompt("bob"), "기대: bob과 상담할 때는 alice의 메모가 붙지 않는다"


def test_메모를_찾아_본다():
    out = ask("alice", "내 메모 보여 줘")
    assert "recall_memory" in out.tools and "문 앞" in out.reply, "기대: recall_memory 도구로 메모를 보여 준다"
