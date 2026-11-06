"""택배사 MCP 서버 연결(10-1). 가짜택배가 주는 MCP 서버(carrier-mcp/server.py)를 stdio 하위 프로세스로 띄운다.

서버가 어떤 도구를 주는지는 서버가 정한다. 우리는 서버를 붙이기만 하면 도구 목록(이름·설명·인자)을 받아 쓴다.
띄우는 명령(파이썬 경로·버전 설정)은 완성본이 준다: crew/runtime/mcp_link.py 의 carrier_params()
한 번의 상담 동안만 잇고 닫는 일도 완성본(게이트웨이)이 한다.
"""
from __future__ import annotations

from agents.mcp import MCPServerStdio

from crew.runtime.mcp_link import carrier_params


def carrier_server() -> MCPServerStdio:
    return MCPServerStdio(params=carrier_params(), name="carrier")  # ✏️ 10-4: 해시 고정·도구 필터·목록 캐시·인자 검사
