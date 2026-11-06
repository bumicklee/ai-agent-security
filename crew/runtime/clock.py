"""랩 시계(완성본). 11-5 서킷 브레이커, 12-1 "밤새" 장면, 12-3 감시자가 쓴다.

보통은 진짜 시각이다. lab_flags의 clock에 시각을 넣으면(예: 2026-10-31T02:00:00) 랩 전체가 그 시각인 척한다.
레드팀 시나리오가 "새벽 2시"를 결정적으로 만들 때 쓴다. 실제 서비스에는 없는 실험 장치다.
"""
from __future__ import annotations

from datetime import datetime


def now() -> datetime:
    from crew.db import get_flag

    fixed = get_flag("clock")
    return datetime.fromisoformat(fixed) if fixed else datetime.now()


def stamp(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat(timespec="seconds")
