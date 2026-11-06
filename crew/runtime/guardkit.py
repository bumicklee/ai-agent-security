"""가드레일 공구함(완성본). 학생의 가드레일 코드(crew/guards/)가 이 함수들을 부른다.

- user_text(input): 가드레일이 받는 입력(str 또는 대화 목록)에서 이번 차례의 고객 글만 꺼낸다
- moderate(text): 유해 표현 검사. live·record면 OpenAI Moderation(omni-moderation-latest, 무료), 아니면 로컬 단어 목록
- ask_judge(agent, text, ctx): 작은 모델 판별기를 한 번 돌린다. 시간 제한이 있고, 3-5 실험용 고장 스위치(guard_fault)를 따른다
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

from agents import Agent, RunConfig, Runner

from crew.config import get_settings
from crew.db import get_flag

JUDGE_TIMEOUT = 8.0  # 초. 판별기가 이보다 늦으면 TimeoutError


def user_text(input: str | list[Any]) -> str:
    """가드레일이 볼 글: 이번 차례의 고객 글 하나. 대화 기록(SQLiteSession)의 지난 글은 넣지 않는다.

    지난 글까지 합치면 공격 한 번이 막힌 뒤에도 그 글이 기록에 남아 이후 모든 질문이 막힌다.
    """
    if isinstance(input, str):
        return input
    for item in reversed(input):
        if isinstance(item, dict) and item.get("role") == "user":
            content = item.get("content", "")
            if isinstance(content, str):
                return content
            return "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


@dataclass
class Moderation:
    flagged: bool
    categories: list[str] = field(default_factory=list)
    source: str = "local"


# 로컬 대체 구현: 아주 작은 단어 목록. 진짜 Moderation보다 훨씬 약하다(키 없이 수업을 따라오게 하는 용도)
LOCAL_LEXICON = {
    "violence": re.compile(r"죽여|죽이겠|죽일 거|살해|폭탄"),
    "self-harm": re.compile(r"자해|자살"),
    "harassment": re.compile(r"멍청한 상담원|쓰레기 같은"),
}


async def moderate(text: str) -> Moderation:
    s = get_settings()
    if s.llm_mode in ("live", "record"):
        from openai import AsyncOpenAI

        res = await AsyncOpenAI().moderations.create(model="omni-moderation-latest", input=text)  # 키는 OPENAI_API_KEY
        r = res.results[0]
        cats = [k for k, v in r.categories.model_dump().items() if v]
        return Moderation(bool(r.flagged), cats, "openai")
    cats = [name for name, pat in LOCAL_LEXICON.items() if pat.search(text)]
    return Moderation(bool(cats), cats, "local")


async def ask_judge(agent: Agent, text: str, context: Any = None) -> Any:
    """판별기 에이전트를 한 번 돌려 final_output(보통 Pydantic 객체)을 돌려준다."""
    if get_flag("guard_fault") == "on":
        await asyncio.sleep(0)
        raise TimeoutError("판별기가 제시간에 답하지 않았습니다(실험용 고장 스위치 guard_fault)")
    s = get_settings()
    config = RunConfig(tracing_disabled=s.llm_mode not in ("live", "record") or not s.tracing,
                       workflow_name="cs-crew judge")
    result = await asyncio.wait_for(Runner.run(agent, text, context=context, run_config=config, max_turns=2),
                                    timeout=JUDGE_TIMEOUT)
    return result.final_output
