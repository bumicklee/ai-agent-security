"""4-3: 모델에 보내기 전에 개인정보를 가린다. 한국형 패턴(주민번호·카드·휴대폰).

완성본 게이트웨이(crew/runtime/run.py)가 요청마다 mask()를 부른다. 화면·메일·레드팀이 모두 이 길로 들어온다.
"""
from __future__ import annotations

import re

PATTERNS = [
    ("주민번호", re.compile(r"\b\d{6}-\d{7}\b")),                      # 991231-0000000 모양
    ("카드", re.compile(r"\b\d{4}-?\d{4}-?\d{4}-?\d{4}\b")),            # 16자리, 붙임표는 있어도 없어도
    ("전화", re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")),            # 010-0000-0000 모양
]


def mask(text: str) -> tuple[str, dict[str, str]]:
    """가린 글과, 가린 값의 짝(4-4에서 채운다)을 돌려준다."""
    for label, pattern in PATTERNS:
        text = pattern.sub(f"[MASKED:{label}]", text)
    return text, {}  # ✏️ 4-4: 가린 자리마다 번호를 붙이고 짝(자리표 → 원래 값)을 남긴다
