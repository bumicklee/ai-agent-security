"""SQLite 연결. 표준 sqlite3만 쓴다."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from crew.config import get_settings


def connect(path: Path | None = None) -> sqlite3.Connection:
    db = sqlite3.connect(path or get_settings().db_path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def session(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    db = connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def get_flag(name: str, default: str = "") -> str:
    with session() as db:
        row = db.execute("SELECT value FROM lab_flags WHERE name = ?", (name,)).fetchone()
    return row["value"] if row else default


def set_flag(name: str, value: str) -> None:
    with session() as db:
        db.execute("INSERT INTO lab_flags(name, value) VALUES(?, ?) "
                   "ON CONFLICT(name) DO UPDATE SET value = excluded.value", (name, value))
