"""3-3: 유해 표현 검사(Moderation). 모델에 닿기 전에 입력 가드레일로 거른다.

live면 OpenAI Moderation(omni-moderation-latest, 무료), 키가 없으면 로컬 단어 목록으로 대신한다.
Moderation은 폭력·혐오·자해 같은 유해 표현을 잡는다. "이전 지시를 무시해" 같은 지시 바꾸기는 잡지 못한다(3-4).
3-4: 입력 가드레일 기본값은 병렬 실행이다. 병렬이면 검사가 끝나기 전에 담당이 도구를 부를 수 있어 블로킹으로 바꿨다.
"""
from __future__ import annotations

from agents import GuardrailFunctionOutput, input_guardrail

from crew.runtime.guardkit import moderate, user_text


@input_guardrail(run_in_parallel=False)  # 3-4: 이 상담원 뒤에는 부작용 있는 도구가 있다. 검사가 먼저 끝나야 한다
async def moderation_guard(ctx, agent, input) -> GuardrailFunctionOutput:
    result = await moderate(user_text(input))
    return GuardrailFunctionOutput(output_info={"flagged": result.flagged, "categories": result.categories},
                                   tripwire_triggered=result.flagged)
