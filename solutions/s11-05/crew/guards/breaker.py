"""11-5: 서킷 브레이커·시간 제한·재시도 예산. 완성본 메시지 길(crew/runtime/bus.py)이 담당에게 맡기기 전·후에 부른다.

- 서킷 브레이커: 한 담당이 FAIL_MAX번 잇따라 실패하면 COOL_S초 동안 그 담당에게 맡기지 않는다(담당별로 따로)
- 재시도 예산: 한 요청 안에서 같은 일을 RETRY_BUDGET번까지만 다시 맡긴다
- 시간 제한: 담당이 TIMEOUT_S초 안에 답하지 않으면 실패로 본다(bus가 읽는다)
상태는 lab_flags(breaker:<담당>)에 둔다. 시각은 랩 시계(crew/runtime/clock.py)를 쓴다.
"""
from __future__ import annotations

import json
from datetime import timedelta

from crew.db import get_flag, set_flag
from crew.runtime.clock import now, stamp

FAIL_MAX, COOL_S, RETRY_BUDGET, TIMEOUT_S = 2, 60, 1, 10.0


def _state(agent: str) -> dict:
    return json.loads(get_flag(f"breaker:{agent}") or '{"fails": 0, "open_until": ""}')


def before(agent: str, task: str, ctx) -> str | None:
    st = _state(agent)
    if st["open_until"] and stamp() < st["open_until"]:
        return f"거부: {agent} 서킷이 열려 잠시 맡기지 않습니다({st['open_until'][11:]}까지)."
    key = f"{agent}|{task}"
    ctx.budget[key] = ctx.budget.get(key, 0) + 1
    if ctx.budget[key] > 1 + RETRY_BUDGET:
        return f"거부: 같은 일을 {RETRY_BUDGET}번 다시 맡겼습니다(재시도 예산 끝)."
    return None


def after(agent: str, ok: bool, ctx) -> None:
    st = _state(agent)
    st["fails"] = 0 if ok else st["fails"] + 1
    if st["fails"] >= FAIL_MAX:
        st["open_until"] = stamp(now() + timedelta(seconds=COOL_S))
    set_flag(f"breaker:{agent}", json.dumps(st))
