"""지식 담당(5-1). 매장 정책 문서로 답한다. 5-2에서 문서 검색 도구를 쥔다."""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.coupons import get_discount_code

INSTRUCTIONS = """너는 지식 담당이다. 매장 정책·공지 문서로 짧게 한국어로 답한다.
할인 코드는 할인 코드 도구로만 확인한다. 모르면 "확인 후 다시 안내드리겠습니다"라고 말한다."""


def build_knowledge() -> Agent:
    return Agent(name="지식 담당", instructions=INSTRUCTIONS, model=get_model(),
                 tools=[get_discount_code])  # ✏️ 5-2: 문서 검색 도구 search_policy를 더한다
