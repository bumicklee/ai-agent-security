"""감시자 순찰(완성본). 12-3부터 쓴다.

요청이 끝날 때마다(crew/runtime/run.py) 최근 한 시간(랩 시계)의 행동 기록을 학생의 감시 규칙에 넘긴다.
- 학생의 `crew/guards/watch.py`의 `anomalies(rows)`가 이상 징후 목록을 돌려준다(12-3). 없으면 조용히 쉰다
  이상 징후 한 건: {"key": "refund_volume", "agent": "환불 담당", "why": "…", "count": 6}
- 새 이상 징후는 행동 기록에 `감시자 · alert`로 남는다(/ops 타임라인·감시자 칸)
- 학생의 `crew/guards/killswitch.py`의 `respond(anomaly)`가 있으면 부른다(12-4: 담당 멈춤·토큰 폐기·MCP 차단)

완성본이 12-3부터(학생의 anomalies가 생기면) 함께 켜는 것
- 고객 신고(ASI09-M4): /chat 답 옆 "신고" 버튼 → report() → 행동 기록 `report` → 경보 customer_report → /ops 감시자 칸
- 담당별 속도 제한(ASI08-M6): 한 담당이 1분(랩 시계)에 RATE_PER_MIN번 넘게 도구를 부르면 audit.py가 "거부:"로 멈춘다
- 새·전이 권한(ASI03-M8): 담당이 닿는 도구(직접 + 핸드오프·담당 도구를 거쳐)가 처음 본 것보다 늘면 경보 new_permission
- 에이전트 간 권한 상승(ASI03-M9): 권한표(11-4 PERMISSIONS) 밖의 일을 맡기려는 메시지면 경보 agent_elevation
"""
from __future__ import annotations

import json
from datetime import timedelta

from crew.db import session
from crew.runtime.clock import now, stamp
from crew.runtime.plug import student

WINDOW = timedelta(hours=1)
RATE_PER_MIN = 30   # 담당 하나가 1분에 부를 수 있는 도구 수(ASI08-M6)


def active() -> bool:
    """12-3 감시 규칙(학생의 anomalies)이 있으면 완성본 감시 장치도 켠다."""
    return bool(student("crew.guards.watch", "anomalies"))


def recent(window: timedelta = WINDOW) -> list[dict]:
    """최근 window(랩 시계)의 기록. 레드팀이 시나리오마다 watch_since를 옮기면 그 뒤 줄만(crew/redteam.py)."""
    from crew.db import get_flag

    t = now()
    since = int(get_flag("watch_since", "0") or 0)
    with session() as db:
        rows = db.execute("SELECT * FROM audit_log WHERE ts >= ? AND ts <= ? AND id > ? ORDER BY id",
                          (stamp(t - window), stamp(t), since)).fetchall()
    return [dict(r) | {"detail": json.loads(r["detail"])} for r in rows]


def alerts(limit: int = 10) -> list[dict]:
    with session() as db:
        rows = db.execute("SELECT ts, detail FROM audit_log WHERE action = 'alert' ORDER BY id DESC LIMIT ?",
                          (limit,)).fetchall()
    return [{"ts": r["ts"], **json.loads(r["detail"])} for r in rows]


def patrol() -> list[dict]:
    from crew.runtime.audit import record

    anomalies = student("crew.guards.watch", "anomalies")
    if not anomalies:
        return []
    rows = recent()
    found = list(anomalies(rows) or []) + builtin(rows)
    seen = {(r["detail"].get("key"), r["detail"].get("agent"), r["detail"].get("run")) for r in rows
            if r["action"] == "alert"}
    for a in found:
        if (a.get("key"), a.get("agent"), a.get("run")) not in seen:
            record("watch", None, "감시자", "alert", a)
    respond = student("crew.guards.killswitch", "respond")
    if respond:
        for a in found:
            respond(a)
    return found


def builtin(rows: list[dict]) -> list[dict]:
    """완성본 감시 규칙(12-3부터). 학생의 anomalies()와 같은 모양의 이상 징후를 돌려준다."""
    out: list[dict] = []
    for r in rows:
        d = r["detail"]
        if r["action"] == "report":  # ASI09-M4 고객 신고
            out.append({"key": "customer_report", "agent": d.get("agent", ""), "run": r["run_id"],
                        "why": f"고객 신고({r['user_id']}): {d.get('reason', '')[:60]}"})
        elif r["action"] == "blocked" and d.get("by") == "rate":  # ASI08-M6 속도 제한에 걸림
            out.append({"key": "agent_rate", "agent": r["agent"], "why": d.get("why", "")[:80]})
        elif r["action"] in ("message", "blocked") and d.get("action") and _elevation(d, r):
            sender = d.get("from") or r["agent"]  # ASI03-M9 권한표 밖의 일을 맡기려 함
            out.append({"key": "agent_elevation", "agent": sender, "run": r["run_id"],
                        "why": f"{sender} → {d.get('to') or r['agent']}: 권한 밖의 일({d['action']})을 맡기려 함"})
    out += new_permissions()
    return out


def _elevation(d: dict, r: dict) -> bool:
    perms = student("crew.guards.messages", "PERMISSIONS") or {"감독자": {"orders", "refunds"}}
    sender = d.get("from") or r["agent"]
    return d["action"] not in set(perms.get(sender, ()))


def reach() -> dict[str, list[str]]:
    """담당마다 닿는 도구: 자기 도구 + 핸드오프·담당 도구(as_tool·bus)를 거쳐 닿는 도구(전이)."""
    from crew.runtime.mcp_link import _children
    from crew.team import walk

    agents = {a.name: a for a in walk()}
    out = {}
    for name, a in agents.items():
        tools, todo, seen = set(), [a], set()
        while todo:
            x = todo.pop()
            if x.name in seen:
                continue
            seen.add(x.name)
            tools |= {t.name for t in x.tools if not getattr(t, "_crew_agent", None) and not getattr(t, "_agent_instance", None)}
            todo.extend(_children(x))
        out[name] = sorted(tools)
    return out


def new_permissions() -> list[dict]:
    """ASI03-M8: 처음 본 권한(lab_flags의 perm_baseline)보다 닿는 도구가 늘었나. 처음 부르면 기준선을 적는다."""
    from crew.db import get_flag, set_flag

    try:
        now_reach = reach()
    except Exception:  # 학생 코드가 잠시 깨져 있어도 순찰은 돈다
        return []
    base = json.loads(get_flag("perm_baseline") or "null")
    if base is None:
        set_flag("perm_baseline", json.dumps(now_reach, ensure_ascii=False))
        return []
    out = []
    for name, tools in now_reach.items():
        extra = sorted(set(tools) - set(base.get(name, [])))
        if extra:
            mine = {t.name for a in _team() if a.name == name for t in a.tools}
            kind = "직접" if set(extra) <= mine else "전이(다른 담당을 거쳐)"
            out.append({"key": "new_permission", "agent": name, "tools": extra,
                        "why": f"{name}이(가) 새로 닿는 도구({kind}): {', '.join(extra)}"})
    return out


def _team():
    from crew.team import walk

    return walk()


def rate_check(agent: str) -> str | None:
    """ASI08-M6: 이 담당이 지난 1분(랩 시계)에 부른 도구 수가 한도를 넘었으면 거부 이유. audit.py가 도구마다 부른다."""
    from crew.db import get_flag

    if not active():
        return None
    t = now()
    since = int(get_flag("watch_since", "0") or 0)
    with session() as db:
        n = db.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'tool_start' AND agent = ? AND ts >= ? "
                       "AND ts <= ? AND id > ?", (agent, stamp(t - timedelta(minutes=1)), stamp(t), since)).fetchone()[0]
    if n >= RATE_PER_MIN:
        return f"거부: '{agent}'의 도구 호출이 너무 빠릅니다(1분에 {RATE_PER_MIN}번 한도). 잠시 뒤 다시 시도해 주세요."
    return None


def report(user_id: str, run_id: str, reason: str = "") -> str:
    """ASI09-M4: 고객이 /chat에서 답 하나를 신고한다. 그 답을 받은 본인만. 기록하고 바로 순찰한다(→ /ops 감시자 칸)."""
    from crew.runtime.audit import record

    with session() as db:
        row = db.execute("SELECT agent FROM audit_log WHERE run_id = ? AND user_id = ? AND action = 'reply' "
                         "ORDER BY id DESC LIMIT 1", (run_id, user_id)).fetchone()
    if row is None:
        return "거부: 내가 받은 답만 신고할 수 있습니다."
    record(run_id, user_id, "고객", "report", {"agent": row["agent"], "reason": (reason or "수상한 답")[:200]})
    patrol()
    return "신고를 받았습니다. 운영자가 /ops 감시자 칸에서 봅니다."


async def ask_watchdog(user_id: str, text: str = "최근 기록 점검해 줘") -> str:
    """/ops의 "감시자 점검" 버튼. 감시자 에이전트(12-3)에게 묻는다. 운영자(직원)만."""
    import uuid

    from agents import Runner

    from crew.context import CrewContext, load_user
    from crew.runtime.audit import AuditHooks
    from crew.runtime.run import _run_config
    from crew.team import watchdog

    agent = watchdog()
    if agent is None:
        return "감시자는 12-3 수업에서 들어옵니다."
    user = load_user(user_id)
    if not user.is_staff:
        return "거부: 운영자(직원)만 감시자를 부를 수 있습니다."
    ctx = CrewContext(user=user, run_id=uuid.uuid4().hex[:8], channel="ops")
    result = await Runner.run(agent, text, context=ctx, hooks=AuditHooks(), run_config=_run_config(), max_turns=4)
    return str(result.final_output)
