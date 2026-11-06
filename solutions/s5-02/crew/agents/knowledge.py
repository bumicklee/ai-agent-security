"""지식 담당(5-1). 5-2에서 매장 정책 문서 검색 도구를 쥐었다."""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.coupons import get_discount_code
from crew.tools.docs import search_policy

INSTRUCTIONS = """너는 지식 담당이다. 문서 검색 도구로 매장 정책·공지 문서를 찾아 짧게 한국어로 답한다.
할인 코드는 할인 코드 도구로만 확인한다. 모르면 "확인 후 다시 안내드리겠습니다"라고 말한다."""


def build_knowledge() -> Agent:
    return Agent(name="지식 담당", instructions=INSTRUCTIONS, model=get_model(),
                 tools=[get_discount_code, search_policy])  # ✏️ 5-6: output_guardrails
