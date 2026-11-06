"""4-3: 모델에 보내기 전에 개인정보를 가린다. 한국형 패턴(주민번호·카드·휴대폰).
4-4: 가린 자리마다 번호를 붙여 짝을 남기고, 답에서 되돌려도 되는 것(전화·이메일)만 되돌린다.
4-5: 행동 기록에 남기 전에 한 번 더 가리고(scrub_log), 트레이스에 원문을 싣지 않는다.

완성본 게이트웨이(crew/runtime/run.py)가 요청마다 mask()를, 답이 나오면 unmask()를 부른다.
Presidio가 설치돼 있으면(requirements-extra.txt) 영어 이름 같은 것을 더 잡는다. 없으면 정규식만 쓴다.
"""
from __future__ import annotations

import re

PATTERNS = [
    ("주민번호", re.compile(r"\b\d{6}-\d{7}\b")),                      # 991231-0000000 모양
    ("카드", re.compile(r"\b\d{4}-?\d{4}-?\d{4}-?\d{4}\b")),            # 16자리, 붙임표는 있어도 없어도
    ("전화", re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b")),            # 010-0000-0000 모양
    ("이메일", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
]
RESTORE = {"전화", "이메일"}  # 고객 본인에게 되돌려 보여도 되는 것. 카드·주민번호는 되돌리지 않는다
TRACE_INCLUDE_SENSITIVE = False  # RunConfig.trace_include_sensitive_data. SDK 기본값은 True(모델 입력·출력 원문이 트레이스로)


def _presidio(text: str) -> list[str]:
    """선택: Presidio(영어 모델 기준)가 찾은 사람 이름. 설치돼 있지 않으면 빈 목록."""
    try:
        from presidio_analyzer import AnalyzerEngine
    except ImportError:
        return []
    return [text[r.start:r.end] for r in AnalyzerEngine().analyze(text=text, language="en", entities=["PERSON"])]


def mask(text: str) -> tuple[str, dict[str, str]]:
    """가린 글과, 가린 값의 짝({"[MASKED:전화#1]": "010-…"})을 돌려준다."""
    mapping: dict[str, str] = {}

    def keep(label: str, value: str) -> str:
        key = f"[MASKED:{label}#{len(mapping) + 1}]"
        mapping[key] = value
        return key

    for label, pattern in PATTERNS:
        text = pattern.sub(lambda m, label=label: keep(label, m.group(0)), text)
    for name in _presidio(text):
        text = text.replace(name, keep("이름", name))
    return text, mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    for key, value in mapping.items():
        label = key[len("[MASKED:"):].split("#")[0]
        text = text.replace(key, value if label in RESTORE else f"[MASKED:{label}]")
    return text


def scrub_log(text: str) -> str:
    """기록용: 되돌린 답(4-4)도 행동 기록에는 가린 채로 남긴다."""
    return mask(text)[0]
