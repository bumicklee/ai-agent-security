"""5-6: 담당 사이 길목 검사. 핸드오프 is_enabled는 "보이느냐"일 뿐 권한 검사가 아니다.

넘어가는 순간(on_handoff)에 로그인 정보로 다시 확인한다. 막을 때는 Denied를 던진다(③ 내 코드).
"""
from __future__ import annotations

from agents import RunContextWrapper

from crew.context import CrewContext
from crew.runtime.errors import Denied


def staff_only(ctx: RunContextWrapper[CrewContext]) -> None:
    if not ctx.context.user.is_staff:
        raise Denied("거부: 직원 전용 담당입니다. 고객 문의는 다른 담당이 도와드립니다.")
