"""13-3 내 데이터로 바꾸기: CSV를 SQLite로, 내 도메인 도구(재고 조회) 하나 더하기."""
import pytest
from crew.config import ROOT
from crew.db import session
from crew.db.importer import import_csv
from crew.runtime.run import ask


@pytest.mark.normal
def test_CSV를_가게_DB로_넣는다():
    done = import_csv(ROOT / "samples")
    assert done == {"docs": 1, "orders": 1, "products": 3}, "기대: samples/의 CSV 세 개가 테이블별로 들어간다"
    with session() as db:
        assert db.execute("SELECT COUNT(*) FROM docs_fts WHERE id = 'a-camping'").fetchone()[0] == 1, "기대: 문서는 검색 색인에도"


def test_재고_도구는_로그인_매장_것만_본다():
    import_csv(ROOT / "samples")
    out = ask("alice", "캠핑 의자 재고 있어요?")
    assert "check_stock" in out.tools and "39,000원" in out.reply, "기대: 주문 담당이 check_stock으로 shop-a 재고를 본다"
    assert "41,000원" not in out.reply, "기대: 다른 매장(shop-b) 상품은 보이지 않는다"
