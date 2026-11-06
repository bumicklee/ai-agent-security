"""MCP 서버 잇기(완성본). 10-1부터 쓴다.

- carrier_params(): 가짜택배 MCP 서버(carrier-mcp/server.py)를 stdio 하위 프로세스로 띄우는 설정.
  버전(v1/v2)과 상태(normal/flaky/slow)는 lab_flags의 carrier_version·carrier_mode를 따른다(레드팀이 바꾼다)
- tool_hash(tool): 도구 이름·설명·인자 모양의 sha256. 10-4에서 "이 설명만 믿는다"를 고정할 때 쓴다
  `python -m crew mcp-pins` 가 지금 서버의 해시를 보여 준다
- attached(agent): 한 번의 실행 동안 팀이 쓰는 MCP 서버를 잇고, 끝나면 닫는다.
  하위 프로세스는 도구를 실제로 부를 때(call_tool) 처음 띄운다(lazy). 띄우는 데 1~2초 걸리기 때문이다.
  도구 목록은 띄우는 설정(명령·버전·상태·DB 경로)이 같으면 이 프로세스가 한 번 받은 것을 다시 쓴다(_TOOLS).
  설정이 바뀌면(예: carrier_version v2) 새로 띄워 새 목록을 받는다. 도구 필터(10-4 해시 고정)는 목록을 줄 때마다 돈다.
  그래서 주문 담당에게 간 문의라도 배송 조회를 하지 않으면 하위 프로세스를 띄우지 않는다
  lab_flags의 mcp_block:<서버 이름> 이 on이면 그 서버를 팀에서 뗀다(12-4 MCP 차단)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from crew.config import ROOT, get_settings
from crew.db import get_flag

SERVER = ROOT / "carrier-mcp" / "server.py"


def carrier_params() -> dict:
    db = Path(get_settings().db_path).parent / "carrier.db"
    return {"command": sys.executable,
            "args": ["-I", str(SERVER), "--version", get_flag("carrier_version", "v1") or "v1",
                     "--mode", get_flag("carrier_mode", "normal") or "normal"],
            "env": {"CARRIER_DB": str(db), "PYTHONIOENCODING": "utf-8"}}


def tool_hash(tool: Any) -> str:
    schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
    body = json.dumps({"name": tool.name, "description": tool.description or "", "schema": schema},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def _children(agent: Any) -> list:
    from agents import Agent

    out = []
    for h in getattr(agent, "handoffs", []):
        ref = getattr(h, "_agent_ref", None)
        out.append(h if isinstance(h, Agent) else (ref() if ref else None))
    for t in getattr(agent, "tools", []):
        out.append(getattr(t, "_agent_instance", None))  # as_tool로 감싼 담당(11-1)
        out.append(getattr(t, "_crew_agent", None))      # 완성본 bus.agent_tool로 감싼 담당(11-4)
    return [a for a in out if a is not None]


def agents_in(agent: Any) -> list:
    """팀 그래프의 에이전트 객체 전부(이름이 같아도 객체가 다르면 따로). MCP 서버는 객체마다 따로 잇는다."""
    seen: dict[int, Any] = {}
    todo = [agent]
    while todo:
        a = todo.pop()
        if id(a) in seen:
            continue
        seen[id(a)] = a
        todo.extend(_children(a))
    return list(seen.values())


class _Owner:
    """서버 하나를 자기 작업(task) 안에서 열고 닫는다. 여러 작업에서 불러도 안전하게."""

    def __init__(self, server: Any) -> None:
        self.server, self.task, self.ready, self.stop, self.error = server, None, asyncio.Event(), asyncio.Event(), None

    async def _hold(self) -> None:
        try:
            async with self.server:
                self.ready.set()
                await self.stop.wait()
        except BaseException as e:  # 연결 실패도 기다리는 쪽에 알린다
            self.error = e
            self.ready.set()

    async def ensure(self) -> None:
        if self.task is None:
            self.task = asyncio.create_task(self._hold())
        await self.ready.wait()
        if self.error:
            raise RuntimeError(f"MCP 서버 '{self.server.name}'에 연결하지 못했습니다: {self.error}")

    async def close(self) -> None:
        if self.task is not None:
            self.stop.set()
            await asyncio.gather(self.task, return_exceptions=True)


_TOOLS: dict[tuple, list] = {}  # 띄우는 설정 → 서버가 보낸 도구 목록(필터 전, 원본)


def _key(server: Any) -> tuple:
    p = getattr(server, "params", None)
    env = getattr(p, "env", None) or {}
    return (server.name, getattr(p, "command", ""), tuple(getattr(p, "args", ()) or ()), tuple(sorted(env.items())))


def _lazy_list(owner: _Owner):
    async def list_tools(run_context=None, agent=None):
        server = owner.server
        raw = _TOOLS.get(_key(server))
        if raw is None:  # 이 설정으로는 처음: 띄워서 받는다
            await owner.ensure()
            raw = list((await server.session.list_tools()).tools)
            _TOOLS[_key(server)] = raw
        tools = [t.model_copy(deep=True) for t in raw]
        if server.tool_filter is not None:  # 10-4의 tool_filter(해시 고정)는 매번 돈다
            tools = await server._apply_tool_filter(tools, run_context, agent)
        return tools
    return list_tools


def _lazy_call(owner: _Owner, method):
    async def call(*a, **kw):
        await owner.ensure()  # 도구를 실제로 부를 때만 하위 프로세스를 띄운다
        return await method(*a, **kw)
    return call


@asynccontextmanager
async def attached(agent: Any) -> AsyncIterator[None]:
    owners: list[_Owner] = []
    for a in agents_in(agent):
        servers = list(getattr(a, "mcp_servers", []) or [])
        if not servers:
            continue
        keep = [s for s in servers if get_flag(f"mcp_block:{s.name}") != "on"]  # 12-4: 막힌 서버는 뗀다
        a.mcp_servers = keep
        for s in keep:
            if getattr(s, "_crew_owner", None) is None:
                if not hasattr(s, "_crew_orig"):
                    s._crew_orig = (s.list_tools, s.call_tool)
                o = _Owner(s)
                s._crew_owner = o
                s.list_tools, s.call_tool = _lazy_list(o), _lazy_call(o, s._crew_orig[1])
                owners.append(o)
    try:
        yield
    finally:
        for o in owners:
            await o.close()
            o.server._crew_owner = None


async def current_hashes() -> dict[str, str]:
    """`python -m crew mcp-pins`: 지금 carrier 서버(lab_flags의 버전)가 내놓는 도구들의 해시."""
    from agents.mcp import MCPServerStdio

    async with MCPServerStdio(params=carrier_params(), name="carrier") as s:
        return {t.name: tool_hash(t) for t in await s.list_tools()}
