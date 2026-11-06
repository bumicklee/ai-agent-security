"""리포트 도구(9-1). 리포트 담당이 짠 파이썬 코드를 실행해 통계·차트를 낸다. 직원만 쓴다.

모델이 짠 코드는 완성본 실행기(crew/runtime/sandbox.py)로만 돌린다. 코드 안에서는 q(sql)로 읽고 show(제목, 행)로 낸다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.runtime import sandbox


@function_tool
def run_python(ctx: RunContextWrapper[CrewContext], code: str) -> str:
    """직원용: 통계 파이썬 코드를 실행한다. q(sql)로 DB를 읽고 show(제목, 행)로 표와 막대 차트를 낸다."""
    if not ctx.context.user.is_staff:
        return "거부: 직원만 리포트 코드를 실행할 수 있습니다."
    r = sandbox.run_in_place(code)  # ✏️ 9-4: 샌드박스(sandbox.run + Policy)로 가둔다
    return r.output if r.ok else f"오류: {r.error}\n{r.output}".strip()
