"""MCP 잇기 완성본(crew/runtime/mcp_link.py). 수업과 상관없이 늘 그린이어야 한다.

하위 프로세스(택배사 서버)는 도구를 실제로 부를 때만 띄운다. 목록은 같은 설정이면 한 번 받은 것을 다시 쓴다.
"""
import asyncio

from agents import Agent
from agents.mcp import MCPServerStdio

from crew.db import set_flag
from crew.runtime import mcp_link


def _agent() -> Agent:
    return Agent(name="주문 담당", mcp_servers=[MCPServerStdio(params=mcp_link.carrier_params(), name="carrier")])


async def _list_then_maybe_call(call: bool) -> tuple[list[str], bool]:
    agent = _agent()
    server = agent.mcp_servers[0]
    async with mcp_link.attached(agent):
        names = [t.name for t in await server.list_tools()]
        if call:
            await server.call_tool("track_shipment", {"tracking_no": "FAKE-TRK-001001"})
        spawned = server._crew_owner.task is not None
    return names, spawned


def test_도구를_부를_때만_띄운다():
    names, spawned = asyncio.run(_list_then_maybe_call(False))  # 이 설정으로는 처음: 목록을 받으려고 띄운다
    assert names == ["track_shipment"] and spawned
    names, spawned = asyncio.run(_list_then_maybe_call(False))  # 같은 설정: 목록만 보는 실행은 띄우지 않는다
    assert names == ["track_shipment"] and not spawned, "목록만 보는 실행은 하위 프로세스를 띄우지 않는다"
    _, spawned = asyncio.run(_list_then_maybe_call(True))
    assert spawned, "도구를 실제로 부르면 띄운다"


def test_설정이_바뀌면_새_목록을_받는다():
    asyncio.run(_list_then_maybe_call(False))
    set_flag("carrier_version", "v2")
    names, spawned = asyncio.run(_list_then_maybe_call(False))
    assert spawned and "file_claim" in names, "버전이 바뀌면(업데이트된 서버) 새로 띄워 새 목록을 받는다"
