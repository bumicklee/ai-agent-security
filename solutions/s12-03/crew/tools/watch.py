"""감시자 도구(12-3). 읽기만 한다. 고객에게 답하지 않는다."""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.guards.watch import anomalies
from crew.runtime.audit import verify
from crew.runtime.watch import recent


@function_tool
def read_audit(ctx: RunContextWrapper[CrewContext]) -> str:
    """감시자용: 행동 기록의 해시 체인을 검사하고, 최근 한 시간의 이상 징후를 요약한다."""
    v = verify()
    if not v["ok"]:
        return f"경고: 행동 기록 체인이 #{v['bad_id']}에서 끊겼습니다({v['why']}). 기록을 믿을 수 없습니다."
    found = anomalies(recent())
    return f"기록 {v['rows']}줄, 체인 정상. 이상 징후 {len(found)}건" + "".join(f" · {a['why']}" for a in found)
