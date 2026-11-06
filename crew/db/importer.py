"""13-3 내 데이터로 바꾸기(완성본): CSV를 SQLite로. `make import CSV=samples/` 또는 `python -m crew import 파일.csv`

CSV 첫 줄(머리글)로 어느 테이블인지 안다. 같은 id가 있으면 바꾸고(INSERT OR REPLACE), 없으면 더한다.
  products: id, store_id, name, price_krw, stock
  orders:   id, store_id, customer_id, status, total_krw, address, created_at   (customer_id는 이미 있는 사용자)
  docs:     id, store_id, visibility, trust, title, body                         (검색 색인 docs_fts도 함께)
진짜 개인정보가 든 파일은 넣지 않는다. 랩 DB는 평문 SQLite다.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from crew.db import session

TABLES = {
    "products": ["id", "store_id", "name", "price_krw", "stock"],
    "orders": ["id", "store_id", "customer_id", "status", "total_krw", "address", "created_at"],
    "docs": ["id", "store_id", "visibility", "trust", "title", "body"],
}
INTS = {"id", "price_krw", "stock", "total_krw"}


class ImportProblem(ValueError):
    """수강생에게 보일 한국어 한 줄. CLI가 스택 없이 이 글만 보여 준다. 이때 DB에는 아무것도 넣지 않는다."""


def _table(header: list[str]) -> str:
    for name, cols in TABLES.items():
        if set(cols) <= set(header) and (name != "products" or "price_krw" in header):
            return name
    raise ImportProblem(f"어느 테이블인지 모르는 머리글입니다: {', '.join(header)}")


def import_csv(path: str | Path) -> dict[str, int]:
    path = Path(path)
    files = sorted(path.glob("*.csv")) if path.is_dir() else [path]
    done: dict[str, int] = {}
    with session() as db:
        for f in files:
            with f.open(encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.DictReader(fh))
            if not rows:
                continue
            try:
                table = _table(list(rows[0]))
            except ImportProblem as e:
                raise ImportProblem(f"{f.name}: {e}") from None
            cols = TABLES[table]
            values = []
            for line, r in enumerate(rows, start=2):  # 1줄은 머리글
                try:
                    values.append([int(r[c]) if c in INTS and table != "docs" else r[c].strip() for c in cols])
                except (ValueError, AttributeError):
                    raise ImportProblem(f"{f.name} {line}줄: 숫자 칸({', '.join(c for c in cols if c in INTS)})에 "
                                        "숫자가 아닌 값이 있습니다. 아무것도 넣지 않았습니다.") from None
            for line, v in enumerate(values, start=2):
                try:
                    db.execute(f"INSERT OR REPLACE INTO {table}({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                               v)
                except sqlite3.IntegrityError as e:
                    db.rollback()
                    raise ImportProblem(_friendly(f.name, line, table, v, e)) from None
            if table == "docs":
                for v in values:
                    db.execute("DELETE FROM docs_fts WHERE id = ?", (v[0],))
                    db.execute("INSERT INTO docs_fts(id, title, body) VALUES (?, ?, ?)", (v[0], v[4], v[5]))
            done[table] = done.get(table, 0) + len(values)
    return done


def _friendly(name: str, line: int, table: str, v: list, e: sqlite3.IntegrityError) -> str:
    msg = str(e)
    if "FOREIGN KEY" in msg:
        refs = {"orders": "store_id(매장)·customer_id(고객)", "products": "store_id(매장)", "docs": "store_id(매장)"}
        return (f"{name} {line}줄: 없는 값을 가리킵니다 — {refs.get(table, '참조 칸')}은 가게 DB에 이미 있는 값이어야 합니다"
                f"(매장 shop-a·shop-b, 고객 alice·bob·chloe·cust04…). 아무것도 넣지 않았습니다.")
    if "CHECK" in msg:
        return f"{name} {line}줄: 허용하지 않는 값이 있습니다({msg.split(':')[-1].strip()}). 아무것도 넣지 않았습니다."
    return f"{name} {line}줄: 넣을 수 없습니다({msg}). 아무것도 넣지 않았습니다."
