"""리포트 도구(9-1). 리포트 담당이 짠 파이썬 코드를 실행해 통계·차트를 낸다. 직원만 쓴다.

모델이 짠 코드는 완성본 실행기(crew/runtime/sandbox.py)로만 돌린다. 코드 안에서는 q(sql)로 읽고 show(제목, 행)로 낸다.
9-4: 샌드박스에 가둔다. 빈 임시 폴더에서, DB 읽기 전용 사본만 보고, 네트워크 없이, 5초 안에, 관리자 권한 없음로.
9-5: 실행 전 검사(금지 모듈·호출, import 허용 목록 밖은 승인)와 결과 크기 제한. 미션: 결과에 섞인 개인정보는 4-3의 mask()로 가린다.
"""
from __future__ import annotations

from agents import RunContextWrapper, function_tool

from crew.context import CrewContext
from crew.guards.code_check import check, limit, needs_review
from crew.guards.pii import mask
from crew.runtime import sandbox

POLICY = sandbox.Policy(
    timeout_s=5,            # 시간 제한
    network=False,          # 네트워크 차단
    db="readonly-copy",     # DB 읽기 전용 사본
    workdir="temp",         # 빈 임시 폴더(랩 폴더가 아니다)
    run_as="nobody",        # 관리자 권한 없이 실행(컨테이너 모드)
)


@function_tool(needs_approval=needs_review)  # 허용 목록 밖 import는 직원 승인 뒤에
def run_python(ctx: RunContextWrapper[CrewContext], code: str) -> str:
    """직원용: 통계 파이썬 코드를 실행한다. q(sql)로 DB를 읽고 show(제목, 행)로 표와 막대 차트를 낸다."""
    if not ctx.context.user.is_staff:
        return "거부: 직원만 리포트 코드를 실행할 수 있습니다."
    if why := check(code):  # 돌리기 전에
        return why
    r = sandbox.run(code, POLICY)
    out = r.output if r.ok else f"오류: {r.error}\n{r.output}".strip()
    if why := limit(out):   # 돌린 뒤에
        return why
    return mask(out)[0]     # 미션: 연락처·카드 번호가 섞여 나오면 가린다
