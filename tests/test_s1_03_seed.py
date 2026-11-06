"""1-3 설치와 가게 데이터: make seed가 같은 데이터를 만든다."""
from crew.db import session


def test_가게_데이터가_들어_있다():
    with session() as db:
        count = lambda t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        assert count("stores") == 2
        assert count("orders") == 300
        assert count("docs") == 20


def test_수업에서_부르는_고정_값():
    with session() as db:
        owner = {r["id"]: r["customer_id"] for r in db.execute("SELECT id, customer_id FROM orders WHERE id < 5000")}
    assert owner == {1001: "alice", 1002: "alice", 2001: "bob", 3001: "chloe"}
