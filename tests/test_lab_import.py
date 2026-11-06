"""CSV 가져오기 완성본(crew/db/importer.py)의 오류 글. 수업과 상관없이 늘 그린이어야 한다."""
import pytest

from crew.db import session


def _orders(tmp_path, line: str):
    f = tmp_path / "orders.csv"
    f.write_text("id,store_id,customer_id,status,total_krw,address,created_at\n" + line + "\n", encoding="utf-8")
    return f


def test_없는_고객을_가리키면_한국어_한_줄로_알린다(tmp_path, capsys):
    from crew.cli import cmd_import

    f = _orders(tmp_path, "9101,shop-a,nobody99,paid,39000,서울시 가짜구 예시길 1,2026-10-30T10:00:00")
    with pytest.raises(SystemExit) as e:
        cmd_import(str(f))
    msg = str(e.value)
    assert "가져오기 실패" in msg and "orders.csv 2줄" in msg and "customer_id" in msg and "Traceback" not in msg
    with session() as db:
        assert db.execute("SELECT COUNT(*) FROM orders WHERE id = 9101").fetchone()[0] == 0, "아무것도 넣지 않는다"


def test_숫자_칸이_틀리면_알린다(tmp_path):
    from crew.db.importer import ImportProblem, import_csv

    with pytest.raises(ImportProblem, match="숫자"):
        import_csv(_orders(tmp_path, "9102,shop-a,alice,paid,삼만원,서울시 가짜구 예시길 1,2026-10-30T10:00:00"))
