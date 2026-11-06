"""3-5: 출력 가드레일. 고객에게 나가는 답에 내부 코드나 다른 사람의 연락처가 섞이면 막는다.

출력 가드레일은 "마지막으로 답한 에이전트"의 것만 돈다(5-6에서 다시 본다).
"""
from __future__ import annotations

import re

from agents import GuardrailFunctionOutput, output_guardrail

from crew.db import session

INTERNAL = re.compile(r"FAKE-(?:STAFF|INTERNAL|SVC)[A-Z0-9-]*")      # 직원 할인 코드·내부 메모·서비스 계정
CONTACT = re.compile(r"[\w.-]+@[\w.-]+\.example|010-\d{4}-\d{4}")   # 랩의 가짜 이메일·전화 형식


@output_guardrail
async def leak_guard(ctx, agent, output) -> GuardrailFunctionOutput:
    user, text = ctx.context.user, str(output)
    found = [] if user.is_staff else [m.group(0) for m in INTERNAL.finditer(text)]
    with session() as db:  # 다른 사람의 연락처인가? (내 것이거나 DB에 없는 번호는 통과)
        for c in CONTACT.findall(text):
            owner = db.execute("SELECT id FROM users WHERE email = ? OR phone = ?", (c, c)).fetchone()
            if owner and owner["id"] != user.id:
                found.append(c)
    return GuardrailFunctionOutput(output_info={"found": found}, tripwire_triggered=bool(found))
