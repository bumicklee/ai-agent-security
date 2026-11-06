"""LLM_MODE에 따라 모델을 고른다. 에이전트 코드는 `get_model()`만 부른다."""
from __future__ import annotations

import asyncio
import os
import re
import weakref

from functools import lru_cache

from agents import Model, OpenAIChatCompletionsModel, OpenAIResponsesModel
from openai import AsyncOpenAI

from crew.config import get_settings
from crew.runtime.fake_model import FakeModel
from crew.runtime.replay import ReplayModel

MODES = ("fake", "live", "replay", "record", "local")



def _last_json(t: str):
    """글 속에서 json으로 읽히는 마지막 {…} 덩어리(생각 과정이 닫히지 않았거나 중괄호가 섞여도)."""
    import json
    for i in [k for k, ch in enumerate(t) if ch == "{"][::-1]:
        depth = 0
        for j in range(i, len(t)):
            depth += {"{": 1, "}": -1}.get(t[j], 0)
            if depth == 0:
                try:
                    json.loads(t[i:j + 1])
                    return t[i:j + 1]
                except ValueError:
                    break
    return None

def _clean_tool_name(name: str, known: set) -> str:
    """도구 이름 꼬리 지우기. gpt-oss는 `run_python.json`, `get_order<|channel|>commentary`처럼 부르기도 한다
    (2026-11-06 Bedrock 실측: 없는 도구라며 ModelBehaviorError로 멈춤). 지운 이름이 이번 요청의 도구일 때만 바꾼다."""
    if name in known:
        return name
    cleaned = re.sub(r"<\|.*$", "", name, flags=re.S).strip()
    cleaned = re.sub(r"\.json$", "", cleaned).strip()
    return cleaned if cleaned in known else name


class _PerLoopClient:
    """이벤트 루프마다 클라이언트를 따로 쓴다. AsyncOpenAI(httpx)의 연결은 처음 쓴 루프에 묶인다. 화면(uvicorn 루프)과
    스레드에서 도는 동기 함수(ask·레드팀 버튼의 run_sync 루프)가 클라이언트 하나를 나눠 쓰면 "Event loop is closed"나
    "다른 루프에 묶임" 오류가 난다(2026-11-06 /ops 버튼에서 발견). get_model()은 lru_cache라 모델 객체는 하나다."""

    def __init__(self, *args, make_client, **kwargs):
        self._make_client = make_client
        self._per_loop = weakref.WeakKeyDictionary()
        super().__init__(*args, openai_client=make_client(), **kwargs)

    @property
    def _client(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return self._first
        c = self._per_loop.get(loop)
        if c is None:
            c = self._per_loop[loop] = self._make_client()
        return c

    @_client.setter
    def _client(self, value):
        self._first = value


class _LiveResponses(_PerLoopClient, OpenAIResponsesModel):
    pass


class _NoReasoningChat(_PerLoopClient, OpenAIChatCompletionsModel):
    """일부 공개 모델(gpt-oss 등)은 답 앞에 <reasoning>…</reasoning>을 붙인다. 그대로 두면 구조화 출력(JSON) 판별기가
    읽지 못해 fail-closed로 모두 막힌다(2026-11-06 Bedrock 실측). SDK가 읽기 전에 생각 과정을 지운다."""

    JSON_TRIES = 3  # 구조화 출력인데 JSON 없이 생각 과정만 내고 끝나는 일이 있다(2026-11-06 실측). 그때만 다시 묻는다

    async def get_response(self, *args, **kwargs):
        schema = kwargs.get("output_schema", args[4] if len(args) > 4 else None)
        for _ in range(self.JSON_TRIES if schema is not None else 1):
            r, has_json = await self._one(*args, **kwargs)
            if has_json:
                break
        return r

    async def _one(self, *args, **kwargs):
        r = await super().get_response(*args, **kwargs)
        schema = kwargs.get("output_schema", args[4] if len(args) > 4 else None)
        has_json = False
        tools = kwargs.get("tools", args[3] if len(args) > 3 else None) or []
        handoffs = kwargs.get("handoffs", args[5] if len(args) > 5 else None) or []
        known = {getattr(t, "name", None) for t in tools} | {getattr(h, "tool_name", None) for h in handoffs}
        for item in getattr(r, "output", []) or []:
            if isinstance(getattr(item, "name", None), str):
                item.name = _clean_tool_name(item.name, known)
            for c in getattr(item, "content", None) or []:
                t = getattr(c, "text", None)
                if not isinstance(t, str):
                    continue
                t = re.sub(r"<reasoning>.*?</reasoning>\s*", "", t, flags=re.S)
                t = re.sub(r"<\|[^|]*\|>[^<{]*", "", t)                  # <|channel|>final<|message|> 같은 표시
                if schema is not None:                                   # 구조화 출력: 실제로 읽히는 마지막 {…} 하나만
                    found = _last_json(t)
                    has_json = has_json or found is not None
                    t = found or t
                c.text = t.strip() if schema is not None else t
            if getattr(item, "name", None):                              # 도구 호출이 있으면 다시 묻지 않는다
                has_json = True
        return r, has_json


@lru_cache(maxsize=None)
def get_model(cassette: str = "default") -> Model:
    s = get_settings()
    if s.llm_mode == "fake":
        return FakeModel()
    if s.llm_mode == "local":
        # LM Studio는 키가 필요 없다. OpenAI 형식 주소를 주는 다른 곳(예: AWS Bedrock)은 LOCAL_API_KEY로 키를 넘긴다
        make = lambda: AsyncOpenAI(base_url=s.local_base_url, api_key=os.environ.get("LOCAL_API_KEY") or "lm-studio")
        return _NoReasoningChat(model=s.local_model, make_client=make)
    if s.llm_mode in ("live", "record"):
        live = _LiveResponses(model=s.model, make_client=AsyncOpenAI)  # 키는 OPENAI_API_KEY에서
        return ReplayModel(live, cassette, record=True) if s.llm_mode == "record" else live
    if s.llm_mode == "replay":
        return ReplayModel(None, cassette)
    raise ValueError(f"LLM_MODE는 {MODES} 중 하나여야 합니다: {s.llm_mode}")


def model_label() -> str:
    s = get_settings()
    where = "AWS Bedrock" if "bedrock" in s.local_base_url else "LM Studio"
    return {"fake": "가짜 LLM", "local": f"{where} · {s.local_model}"}.get(s.llm_mode, f"OpenAI · {s.model}") \
        + f" ({s.llm_mode})"
