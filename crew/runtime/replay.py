"""녹화(record)와 재생(replay). 키 없는 수강생도 실제 OpenAI 응답을 그대로 본다.

같은 입력(에이전트 지시문·대화·도구 이름)이면 같은 칸을 찾는다. 카세트는 cassettes/에 JSON으로 쌓인다.
카세트에는 가짜 값만 있다. 녹화 뒤 강사가 한 번 훑어 확인한다.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from agents import Model, ModelResponse, Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage

from crew.config import ROOT

CASSETTES = ROOT / "cassettes"
_TYPES = {"message": ResponseOutputMessage, "function_call": ResponseFunctionToolCall}


def _key(system_instructions: str | None, input: Any, tools: list) -> str:
    raw = json.dumps({"s": system_instructions, "i": input, "t": sorted(getattr(t, "name", "") for t in tools)},
                     ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class ReplayModel(Model):
    def __init__(self, inner: Model | None, cassette: str = "default", record: bool = False) -> None:
        self.inner, self.record = inner, record
        self.path = CASSETTES / f"{cassette}.json"
        self.tape: dict[str, Any] = json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs,
                           tracing, **kw: Any) -> ModelResponse:
        key = _key(system_instructions, input, tools)
        if not self.record:
            if key not in self.tape:
                raise LookupError("녹화된 응답이 없습니다. 수업 카드의 문장을 그대로 넣었는지 확인하세요 "
                                  "(또는 LLM_MODE=live로 바꿉니다).")
            hit = self.tape[key]
            return ModelResponse(output=[_TYPES[o["type"]].model_validate(o) for o in hit["output"]],
                                 usage=Usage(**hit["usage"]), response_id=None)
        resp = await self.inner.get_response(system_instructions, input, model_settings, tools, output_schema,
                                             handoffs, tracing, **kw)
        self.tape[key] = {"output": [o.model_dump(exclude_none=True) for o in resp.output if o.type in _TYPES],
                          "usage": {"requests": 1, "input_tokens": resp.usage.input_tokens,
                                    "output_tokens": resp.usage.output_tokens,
                                    "total_tokens": resp.usage.total_tokens}}
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(self.tape, ensure_ascii=False, indent=1), "utf-8")
        return resp

    def stream_response(self, *args: Any, **kwargs: Any):
        raise NotImplementedError
