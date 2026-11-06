"""직원 도우미(5-1). 직원이 쓰는 매장 통계 담당. 9-1의 리포트 담당이 들어오기 전 맛보기다.

"직원만 여기로 온다"고 가정하고 만들었다. 그 가정이 깨지는 것이 5-6의 사고다.
"""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.stats import store_ticket_stats

INSTRUCTIONS = "너는 직원 도우미다. 직원에게 매장 문의 통계를 짧게 알려 준다."


def build_staff_desk() -> Agent:
    return Agent(name="직원 도우미", instructions=INSTRUCTIONS, model=get_model(), tools=[store_ticket_stats])
