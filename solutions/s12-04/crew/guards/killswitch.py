"""12-4: 킬 스위치를 넓힌다. 완성본이 부르는 자리
- run.py: 요청마다 over_budget(user) — 사용자별 요금 차단(랩 전체 LAB_MAX_USD와 따로)
- watch.py: 이상 징후마다 respond(anomaly) — 감시자가 멈출지 정한다
- /ops 버튼: pause_agent · revoke_all_tokens · block_mcp
멈춤 표시는 lab_flags에 둔다. 기록(pause·mcp_block)은 표시가 실제로 바뀔 때만 남긴다. 완성본이 읽는다: pause:<담당>(audit.py), mcp_block:<서버>(mcp_link.py), 위임 토큰은 revoked(broker.py)
"""
from __future__ import annotations

from datetime import timedelta

from crew.db import get_flag, session, set_flag
from crew.runtime.audit import record
from crew.runtime.clock import now, stamp

TOKENS_PER_USER_HOUR = 15_000


def _switch(flag: str, on: bool) -> bool:
    """표시를 바꾸고, 실제로 바뀌었는지 돌려준다(순찰이 요청마다 respond를 불러도 기록은 바뀔 때 한 줄만)."""
    want = "on" if on else "off"
    if (get_flag(flag) or "off") == want:
        return False
    set_flag(flag, want)
    return True


def pause_agent(name: str, on: bool = True) -> str:
    if _switch(f"pause:{name}", on):
        record("ops", None, "감시자", "pause" if on else "resume", {"agent": name})
    return f"'{name}'을(를) {'멈췄습니다' if on else '다시 켰습니다'}."


def revoke_all_tokens() -> str:
    with session() as db:
        n = db.execute("UPDATE delegations SET revoked = 1 WHERE revoked = 0").rowcount
    record("ops", None, "감시자", "revoke_tokens", {"count": n})
    return f"위임 토큰 {n}개를 폐기했습니다."


def block_mcp(name: str, on: bool = True) -> str:
    if _switch(f"mcp_block:{name}", on):
        record("ops", None, "감시자", "mcp_block" if on else "mcp_unblock", {"server": name})
    return f"MCP 서버 '{name}'을(를) {'막았습니다' if on else '다시 열었습니다'}."


def over_budget(user) -> str | None:
    with session() as db:
        used = db.execute("SELECT COALESCE(SUM(tokens_in + tokens_out), 0) FROM usage WHERE user_id = ? AND ts >= ?",
                          (user.id, stamp(now() - timedelta(hours=1)))).fetchone()[0]
    if used > TOKENS_PER_USER_HOUR:
        return f"거부: 한 시간 사용량({used:,} 토큰)이 한도({TOKENS_PER_USER_HOUR:,})를 넘었습니다. 잠시 뒤 다시 시도해 주세요."
    return None


def respond(a: dict) -> None:
    """감시자의 대응. 돈이 나가는 이상 징후는 그 담당을 멈추고, 바뀐 MCP는 서버째 막는다."""
    if a["key"] in ("refund_volume", "night_refunds", "tool_storm"):
        pause_agent(a["agent"])
    elif a["key"] == "mcp_changed" and a.get("server"):
        block_mcp(a["server"])
