"""리포트 담당(9-1). 팀의 다섯 번째 담당. 직원이 부르는 통계·차트 담당이다(5-1의 직원 도우미 자리).

파이썬 코드를 짜서 실행한다. 직원만 넘어온다(on_handoff=staff_only). 환불 도구는 쥐지 않는다.
"""
from __future__ import annotations

from agents import Agent

from crew.runtime.llm import get_model
from crew.tools.reports import run_python
from crew.tools.stats import store_ticket_stats

INSTRUCTIONS = """너는 리포트 담당이다. 직원이 요청한 매장 통계를 낸다.
간단한 문의 건수는 통계 도구로, 표·차트가 필요하면 파이썬 코드를 짜서 run_python으로 실행한다.
코드에서는 q(sql)로 읽고 show(제목, 행)로 출력한다. 결과를 짧게 한국어로 전한다."""


def build_report_agent() -> Agent:
    return Agent(name="리포트 담당", instructions=INSTRUCTIONS, model=get_model(),
                 tools=[store_ticket_stats, run_python])
