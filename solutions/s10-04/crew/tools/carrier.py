"""택배사 MCP 서버 연결(10-1). 가짜택배가 주는 MCP 서버(carrier-mcp/server.py)를 stdio 하위 프로세스로 띄운다.

서버가 어떤 도구를 주는지는 서버가 정한다. 우리는 서버를 붙이기만 하면 도구 목록(이름·설명·인자)을 받아 쓴다.
띄우는 명령(파이썬 경로·버전 설정)은 완성본이 준다: crew/runtime/mcp_link.py 의 carrier_params()

10-4: 남의 서버는 업데이트되면 도구 설명이 바뀔 수 있다(그 설명이 모델의 지시가 된다).
- 해시 고정: 믿기로 한 버전(v1)의 도구 설명 해시만 받는다. `python -m crew mcp-pins`로 뽑았다
- 최소 노출: 쓰는 도구(track_shipment)만. create_static_tool_filter의 허용 목록
- 목록 캐시: 한 연결 안에서 도구 목록을 다시 받지 않는다(cache_tools_list)
- 인자 직접 검사: MCP의 require_approval 함수는 호출 인자를 못 본다. 도구 입력 가드레일로 "내 운송장인가"를 본다
"""
from __future__ import annotations

import json

from agents import ToolGuardrailFunctionOutput, tool_input_guardrail
from agents.mcp import MCPServerStdio, create_static_tool_filter

from crew.db import session
from crew.runtime.audit import record
from crew.runtime.mcp_link import carrier_params, tool_hash

PINNED = {  # 믿기로 한 v1 도구 설명의 sha256
    "track_shipment": "0d77136fc446dd6bb6be3826a8062a766838687b81f6ed9dadc205b22a94d0d9",
}
ALLOW = create_static_tool_filter(allowed_tool_names=list(PINNED))  # 최소 노출


def pinned_only(fctx, tool) -> bool:
    ok = tool.name in ALLOW["allowed_tool_names"] and tool_hash(tool) == PINNED.get(tool.name)
    if not ok:
        c = fctx.run_context.context
        record(c.run_id, c.user.id, fctx.agent.name, "tool_hidden",
               {"tool": tool.name, "server": fctx.server_name, "why": "허용 목록 밖이거나 설명 해시가 다름", "denied": True})
    return ok


@tool_input_guardrail
def my_tracking_only(data):
    """track_shipment 인자 검사: 로그인한 고객 주문의 운송장인가."""
    no = json.loads(data.context.tool_arguments or "{}").get("tracking_no", "")
    with session() as db:
        mine = db.execute("SELECT 1 FROM shipments s JOIN orders o ON o.id = s.order_id "
                          "WHERE s.tracking_no = ? AND o.customer_id = ?", (no, data.context.context.user.id)).fetchone()
    if mine is None:
        return ToolGuardrailFunctionOutput.reject_content("거부: 내 주문의 운송장이 아닙니다.")
    return ToolGuardrailFunctionOutput.allow()


def carrier_server() -> MCPServerStdio:
    return MCPServerStdio(params=carrier_params(), name="carrier", tool_filter=pinned_only, cache_tools_list=True,
                          tool_input_guardrails=[my_tracking_only])
