"""막을 때 쓰는 예외. 학생 코드(on_handoff 검사 등)가 이것을 던지면 run.py가 "③ 내 코드가 막음"으로 기록한다."""
from __future__ import annotations

from agents.exceptions import AgentsException


class Denied(AgentsException):  # SDK 예외로 두어야 훅(on_tool_start 등)에서 던져도 감싸지지 않고 run.py까지 온다
    """권한이 없어 거부한다. 메시지는 "거부: …"로 시작하게 쓴다(점수판 약속)."""

    def __str__(self) -> str:
        text = super().__str__()
        return text if text.startswith("거부") else f"거부: {text}"
