"""팀 구성. 섹션마다 에이전트가 한 명씩 들어온다.

팀을 조립하는 코드는 학생 폴더에 있다: `crew/agents/counselor.py`의 `build_counselor()`가 첫 에이전트
(5-1부터는 접수 라우터)를 만들고, 담당들은 그 에이전트의 handoffs로 이어진다.
11-1부터는 감독자가 담당들을 도구로(as_tool) 쥔다. walk()는 그 길도 따라간다.
감시자(12-3)는 고객 문의 길에 없다. `crew/agents/watchdog.py`의 `build_watchdog()`가 있으면 조직도에 따로 켠다.
이 파일은 그 그래프를 걸어 다니며(walk) /ops 조직도의 칸을 켠다. 칸을 손으로 켜지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from agents import Agent


@dataclass(frozen=True)
class Slot:
    key: str
    name: str
    joins: str      # 들어오는 수업
    active: bool
    agent: str = ""  # 이 이름의 에이전트가 팀 그래프에 있으면 칸이 켜진다


SLOTS = [
    Slot("counselor", "상담원 → 접수 라우터", "1-5", True, "상담원"),
    Slot("orders", "주문 담당", "5-1", False, "주문 담당"),
    Slot("knowledge", "지식 담당", "5-1", False, "지식 담당"),
    Slot("refunds", "환불 담당", "6-1", False, "환불 담당"),
    Slot("reports", "리포트 담당", "9-1", False, "리포트 담당"),
    Slot("supervisor", "감독자", "11-1", False, "감독자"),
    Slot("watchdog", "감시자", "12-3", False, "감시자"),
]


def entry_agent() -> Agent:
    """고객 문의가 처음 닿는 에이전트."""
    from crew.agents.counselor import build_counselor

    return build_counselor()


def walk(agent: Agent | None = None) -> list[Agent]:
    """첫 에이전트에서 handoffs를 따라 닿는 에이전트 전부(중복 없이)."""
    start = agent or entry_agent()
    seen: dict[str, Agent] = {}
    todo = [start]
    while todo:
        a = todo.pop(0)
        if a.name in seen:
            continue
        seen[a.name] = a
        for h in a.handoffs:
            if isinstance(h, Agent):
                todo.append(h)
            else:
                ref = getattr(h, "_agent_ref", None)
                target = ref() if ref else None
                if isinstance(target, Agent):
                    todo.append(target)
        for t in a.tools:  # 담당을 도구로 쥔 경우(11-1 as_tool, 11-4 bus.agent_tool)
            inner = getattr(t, "_agent_instance", None) or getattr(t, "_crew_agent", None)
            if isinstance(inner, Agent):
                todo.append(inner)
    return list(seen.values())


def watchdog() -> Agent | None:
    """12-3 감시자. 고객 문의 길 밖에 있다(고객에게 답하지 않는다)."""
    from crew.runtime.plug import student

    build = student("crew.agents.watchdog", "build_watchdog")
    return build() if build else None


def tool_names(agent: Agent | None = None) -> set[str]:
    return {t.name for a in walk(agent) for t in a.tools}


def mcp_names(agent: Agent | None = None) -> set[str]:
    """팀이 쓰는 MCP 서버 이름(10-1 carrier 등)."""
    return {s.name for a in walk(agent) for s in (a.mcp_servers or [])}


def find_tool(name: str, agent: Agent | None = None):
    return next((t for a in walk(agent) for t in a.tools if t.name == name), None)


def slots() -> list[Slot]:
    """조직도 칸. 지금 팀 그래프에 있는 에이전트 이름으로 켠다."""
    try:
        names = {a.name for a in walk()}
    except Exception:  # 학생 코드가 잠시 깨져 있어도 화면은 뜬다
        names = {"상담원"}
    try:
        w = watchdog()
        names |= {w.name} if w else set()
    except Exception:
        pass
    return [replace(s, active=s.agent in names) for s in SLOTS]
