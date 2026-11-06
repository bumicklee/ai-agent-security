"""5-2 만들기: 매장 정책 문서 검색(SQLite FTS5)."""
from crew.runtime.run import ask


def test_지식_담당이_문서를_찾아_답한다():
    out = ask("alice", "반품 기간이 어떻게 되나요")
    assert "search_policy" in out.tools, "기대: 지식 담당이 search_policy 도구를 부른다"
    assert out.agent == "지식 담당" and "7일" in out.reply, "기대: 에이샵 환불 정책(7일)으로 답한다"


def test_두_글자_검색어도_찾는다():
    out = ask("chloe", "배송 안내 알려 줘")
    assert "출고" in out.reply, "기대: \"배송\"(2글자)은 LIKE로 찾아 비샵 배송 안내(출고)를 보여 준다"


def test_검색_도구가_trigram을_쓴다():
    from crew.team import find_tool

    assert find_tool("search_policy") is not None, "기대: 팀 안에 search_policy 도구가 있다"
    import inspect

    import crew.tools.docs as docs
    src = inspect.getsource(docs)
    assert "docs_fts" in src and "MATCH" in src, "기대: 3글자 이상은 docs_fts MATCH(FTS5 trigram)로 찾는다"
    assert "LIKE" in src, "기대: 2글자 검색어는 LIKE로 찾는다(trigram은 3글자부터)"
