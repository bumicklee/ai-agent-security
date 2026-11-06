"""7-3: 위임 토큰. 직원이 "대신 처리"를 누르면 그 직원 권한만큼만, 짧게, 좁게 발급한다.

완성본 게이트웨이(crew/runtime/run.py)가 대신 처리 요청마다 issue()를 불러 토큰 번호를 ctx.context.delegation에 넣는다.
모델은 토큰을 보지 못한다(도구 인자에도, 지시문에도 없다). 도구는 비밀값 브로커(crew/runtime/broker.py)에 토큰을 내민다.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from crew.db import session
from crew.runtime.clock import now, stamp

TTL_MINUTES = 10                # 짧게: 10분
SCOPES = ("orders:write",)      # 좁게: 주문 배송지 변경만


def issue(staff, purpose: str) -> str:
    token = secrets.token_hex(8)
    expires = stamp(now() + timedelta(minutes=TTL_MINUTES))  # 랩 시계(브로커도 같은 시계로 만료를 본다)
    with session() as db:
        db.execute("INSERT INTO delegations(token_id, staff_id, store_id, scopes, purpose, expires_at) "
                   "VALUES (?, ?, ?, ?, ?, ?)",
                   (token, staff.id, staff.store_id, ",".join(SCOPES), purpose[:100], expires))  # 요청한 직원의 매장만
    return token
