"""11-4: 담당 사이 메시지 계약과 서명. 완성본 메시지 길(crew/runtime/bus.py)이 부른다.

- make(): 감독자가 담당에게 맡기는 일을 정해진 모양(TaskMessage)으로 만들고, 보내는 담당의 키로 서명한다
- verify(): 받는 쪽 검사. 서명·받는 이·만료·nonce(재전송)·보내는 담당의 권한(리포트 담당은 환불을 못 맡긴다)
- contract(): 담당의 답(자유 글)을 정해진 칸(상태·주문 번호)으로 줄인다. 글 속의 엉뚱한 지시는 감독자에게 가지 않는다
키는 브로커가 쥔다(crew/runtime/broker.py의 agent_key). 모델·지시문·도구 인자에는 없다.
"""
from __future__ import annotations

import hmac
import re
import secrets
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel, Field

from crew.runtime.broker import agent_key
from crew.runtime.bus import signature
from crew.runtime.clock import now, stamp

PERMISSIONS = {"감독자": {"orders", "refunds"}, "리포트 담당": {"reports"}}  # 보내는 담당 → 맡길 수 있는 일
TTL_S = 60
_SEEN: set[str] = set()


class TaskMessage(BaseModel):
    sender: str
    receiver: str
    action: str
    task: str = Field(max_length=300)
    nonce: str
    expires_at: str
    sig: str = ""


class Result(BaseModel):  # 담당 → 감독자: 이 칸만 돌아간다
    status: Literal["done", "denied", "error", "pending"]
    order_ids: list[int] = []


def make(sender: str, receiver: str, action: str, task: str) -> TaskMessage:
    m = TaskMessage(sender=sender, receiver=receiver, action=action, task=task[:300], nonce=secrets.token_hex(8),
                    expires_at=stamp(now() + timedelta(seconds=TTL_S)))
    m.sig = signature(m.model_dump(exclude={"sig"}), agent_key(sender))
    return m


def verify(m: TaskMessage, receiver: str) -> str | None:
    if not hmac.compare_digest(m.sig, signature(m.model_dump(exclude={"sig"}), agent_key(m.sender))):
        return "거부: 서명이 맞지 않습니다(메시지가 바뀌었거나 보낸 담당이 다릅니다)."
    if m.receiver != receiver or m.expires_at < stamp() or m.nonce in _SEEN:
        return "거부: 받는 이가 다르거나, 만료됐거나, 이미 쓴 메시지입니다."
    if m.action not in PERMISSIONS.get(m.sender, set()):
        return f"거부: {m.sender}은(는) '{m.action}' 일을 맡길 수 없습니다."
    _SEEN.add(m.nonce)
    return None


def contract(text: str) -> Result:
    status = ("denied" if text.startswith("거부") else "pending" if text.startswith("승인 대기")
              else "error" if ("오류" in text or "다시 시도" in text) else "done")
    return Result(status=status, order_ids=[int(x) for x in re.findall(r"\b(\d{4})\b", text)][:5])
