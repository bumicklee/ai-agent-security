"""12-3: 감시자 규칙. 완성본 순찰(crew/runtime/watch.py)이 요청마다 최근 한 시간(랩 시계)의 행동 기록을 넘긴다.

하나하나는 정상인 일도 모이면 이상하다. 평소 기준선(BASELINES)을 넘으면 이상 징후로 돌려준다.
- 양: 한 시간에 환불이 평소보다 많다
- 시간: 새벽(0~6시)에 환불이 몰린다
- 도구: 한 요청이 도구를 너무 많이 부른다(폭주)
- 공급망: MCP 도구 설명이 바뀌어 숨겨졌다(10-4의 tool_hidden)
"""
from __future__ import annotations

from collections import Counter

BASELINES = {"refunds_per_hour": 5, "night_hours": (0, 6), "night_refunds": 4, "tools_per_run": 15}


def anomalies(rows: list[dict]) -> list[dict]:
    b, out = BASELINES, []
    refunds = [r for r in rows if r["action"] == "tool_end" and r["detail"].get("tool") == "request_refund"
               and not r["detail"].get("denied")]
    if len(refunds) >= b["refunds_per_hour"]:
        out.append({"key": "refund_volume", "agent": "환불 담당", "count": len(refunds),
                    "why": f"한 시간에 환불 {len(refunds)}건(기준 {b['refunds_per_hour']}건)"})
    night = [r for r in refunds if b["night_hours"][0] <= int(r["ts"][11:13]) < b["night_hours"][1]]
    if len(night) >= b["night_refunds"]:
        out.append({"key": "night_refunds", "agent": "환불 담당", "count": len(night), "why": f"새벽 환불 {len(night)}건"})
    for run, n in Counter(r["run_id"] for r in rows if r["action"] == "tool_start").items():
        if n > b["tools_per_run"]:
            out.append({"key": "tool_storm", "agent": "감독자", "count": n, "why": f"요청 {run}의 도구 호출 {n}번"})
    for r in rows:
        if r["action"] == "tool_hidden":
            out.append({"key": "mcp_changed", "agent": r["agent"], "server": r["detail"].get("server", ""),
                        "why": f"MCP 도구 설명이 바뀜: {r['detail'].get('tool')}"})
            break
    return out
