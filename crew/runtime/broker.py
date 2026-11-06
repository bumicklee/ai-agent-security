"""비밀값 브로커(완성본). 7-1·7-3에서 쓴다.

모델은 비밀값(서비스 계정 키·위임 토큰)을 보지 않는다. 도구가 ctx.context에 든 토큰 번호를 브로커에 내밀면,
브로커가 delegations 테이블을 보고 "이 토큰으로 무엇을 할 수 있나"(Grant)를 돌려준다.

- service_session(): 서비스 계정(모든 매장 주문을 고칠 수 있음). 쓸 때마다 감사 기록에 남는다. 7-2 사고의 원인
- redeem(token, scope): 위임 토큰 확인. 없거나·만료됐거나·폐기됐거나·범위 밖이면 None
- agent_key(name): 담당별 서명 키(11-4). 담당마다 다르고, 모델·지시문·도구 인자에는 없다
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from crew.db import session
from crew.runtime.clock import stamp

import hashlib
import hmac

_LAB_SECRET = b"FAKE-LAB-SIGNING-SECRET"  # 랩용 가짜 비밀값. 실제 서비스에서는 비밀값 저장소(KMS·Vault)에 둔다
SERVICE_ACCOUNT = "svc-admin"  # 실제 비밀값은 여기(브로커)에만 있다는 가정. 모델·도구 인자·지시문에는 없다


@dataclass(frozen=True)
class Grant:
    token_id: str
    staff_id: str
    store_id: str
    scopes: tuple[str, ...]
    purpose: str


@contextmanager
def service_session(reason: str = "") -> Iterator:
    from crew.runtime.audit import CURRENT_RUN, record

    record(CURRENT_RUN.get(), SERVICE_ACCOUNT, "broker", "service_account", {"reason": reason[:100]})
    with session() as db:
        yield db


def redeem(token_id: str | None, scope: str) -> Grant | None:
    from crew.runtime.audit import CURRENT_RUN, record

    if not token_id:
        return None
    with session() as db:
        row = db.execute("SELECT * FROM delegations WHERE token_id = ?", (token_id,)).fetchone()
    if row is None or row["revoked"] or row["expires_at"] <= stamp():  # 랩 시계(crew/runtime/clock.py)
        return None
    scopes = tuple(s.strip() for s in row["scopes"].split(","))
    if scope not in scopes and "*" not in scopes:
        return None
    record(CURRENT_RUN.get(), row["staff_id"], "broker", "delegation_use",
           {"token": token_id[:4] + "…", "scope": scope, "store": row["store_id"]})
    return Grant(row["token_id"], row["staff_id"], row["store_id"], scopes, row["purpose"])


def agent_key(agent_name: str) -> bytes:
    """11-4: 담당별 서명 키. 한 담당의 키가 새도 다른 담당 이름으로 서명하지 못한다."""
    return hmac.new(_LAB_SECRET, f"agent:{agent_name}".encode(), hashlib.sha256).digest()
