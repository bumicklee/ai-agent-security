"""리포트 담당의 코드 실행기(완성본). 9-1~9-5에서 쓴다. 모델이 짠 코드는 이 파일의 함수로만 실행한다.

두 가지 길
- run_in_place(code): 9-1 맛보기. 랩 데이터 폴더(data/)에서, 진짜 DB로, 시간 제한 없이(랩이 멈추지 않게 30초 상한만) 돈다.
  9-2 사고의 원인이다. 랩은 실제로 밖으로 보내지 않는다: 네트워크 연결 시도는 outbox 테이블에 "보내려 했다"로 적고 끊는다
- run(code, policy): 9-4 샌드박스. Policy대로 가둔다
    · Docker가 있고 python:3.12-slim 이미지가 이미 있으면 컨테이너(--network none, --user <Policy.run_as>, --read-only,
      -w /work, 메모리·프로세스 한도). docker_command()가 명령을 만든다
    · 없으면 제한 프로세스 모드: 하위 프로세스 + 시간 제한 + 임시 폴더 + DB 읽기 전용 사본 + 파이썬 감사 훅(sys.addaudithook)으로
      네트워크·다른 프로그램 실행·작업 폴더 밖 쓰기를 막는다. 흉내에 가깝다(같은 사용자 권한으로 돈다). 진짜 격리는 컨테이너다
    · 두 모드는 수업에서 보이는 결과가 같다: 같은 감사 훅·같은 오류 글·같은 시간 제한(컨테이너 뜨는 시간은 빼고 잰다)
  CREW_SANDBOX=auto(기본)|docker|process 로 고른다. auto는 컨테이너가 뜨지 못하면 제한 프로세스 모드로 돈다. 시험은 process로 돈다
- DB 읽기 전용 사본은 요청한 사람의 매장 것만 담는다(store_copy). 다른 매장 고객·주문·문의, 행동 기록·랩 설정은 사본에 없다

모델 코드가 쓸 수 있는 도우미(코드 앞에 붙는다)
  q(sql, *params) → 행 목록(dict)      show(title, rows) → 표와 막대 차트를 출력
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

from crew.config import get_settings

IMAGE = "python:3.12-slim"
HARD_CAP_S = 30.0       # 어떤 길이든 이보다 오래 돌지 않는다(랩 보호용)
RAW_CAP = 100_000       # 출력을 이 글자 수까지만 받는다(랩 보호용. 9-5의 결과 제한과 다르다)


@dataclass(frozen=True)
class Policy:
    timeout_s: float = 5.0
    network: bool = False             # False면 연결 시도 자체를 막는다
    db: str = "readonly-copy"         # "readonly-copy"(사본·읽기 전용) | "live"(진짜 DB)
    workdir: str = "temp"             # "temp"(빈 임시 폴더) | "lab"(랩 데이터 폴더)
    run_as: str = "nobody"            # 컨테이너에서 쓸 사용자(관리자 권한 없음). 제한 프로세스 모드는 사용자를 못 바꾼다


@dataclass
class Result:
    ok: bool
    output: str
    error: str
    mode: str
    timed_out: bool = False
    seconds: float = 0.0


PRELUDE = r'''
import json, os, sqlite3, sys
_CFG = json.loads(os.environ["CREW_SBX"])
REPORT_DB = _CFG["db"]
_WORK = os.path.realpath(_CFG["work"])
_db = None

def _inside(p):
    try:
        return os.path.realpath(os.fspath(p)).startswith(_WORK + os.sep) or os.path.realpath(os.fspath(p)) == _WORK
    except TypeError:
        return True

def _deny(what):
    raise PermissionError("샌드박스: " + what + " 은(는) 막혀 있습니다")

_NET = ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.bind", "socket.sendto",
        "socket.sendmsg", "socket.connect_ex")
_RUN = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork", "os.forkpty", "pty.spawn")
_FS = ("os.remove", "os.rmdir", "os.rename", "os.replace", "shutil.rmtree", "shutil.move", "os.truncate", "os.chmod",
       "os.mkdir", "os.symlink", "os.link")
_SENT = []

def _hook(ev, args):
    if ev in _NET:
        if _CFG["network"] == "record" and not _SENT:
            _SENT.append(1)
            target = str(args[0] if ev != "socket.connect" else args[1])[:80]
            con = sqlite3.connect(REPORT_DB)
            con.execute("INSERT INTO outbox(to_email, subject, body, created_at) VALUES (?, ?, ?, datetime('now','localtime'))",
                        (target, "리포트 코드의 외부 전송 시도", "랩은 실제로 보내지 않았습니다"))
            con.commit(); con.close()
            raise ConnectionError("랩: 외부 전송 시도를 outbox에 적고 끊었습니다(실제로 보내지 않음)")
        if _CFG["network"] is False:
            _deny("네트워크(" + ev + ")")
    if not _CFG["guard"]:
        return
    if ev in _RUN:
        _deny("다른 프로그램 실행(" + ev + ")")
    if ev == "open" and not isinstance(args[0], int):
        mode, flags = args[1] or "", args[2] or 0
        writing = any(c in mode for c in "wax+") or (flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND))
        if writing and not _inside(args[0]):
            _deny("작업 폴더 밖 쓰기(" + str(args[0])[:60] + ")")
    if ev in _FS and args and not isinstance(args[0], int) and not _inside(args[0]):
        _deny("작업 폴더 밖 파일 바꾸기(" + ev + ")")
    if ev == "sqlite3.connect" and args and str(args[0]) not in (REPORT_DB, _CFG["db_uri"], ":memory:"):
        _deny("다른 DB 열기")

def q(sql, *params):
    global _db
    if _db is None:
        _db = sqlite3.connect(_CFG["db_uri"], uri=_CFG["db_uri"].startswith("file:"))
        _db.row_factory = sqlite3.Row
    return [dict(r) for r in _db.execute(sql, params).fetchall()]

def show(title, rows):
    print("[" + str(title) + "]")
    for r in rows:
        vals = list(r.values()) if isinstance(r, dict) else list(r)
        nums = [v for v in vals if isinstance(v, int)]
        bar = (" " + "█" * max(1, min(20, nums[0]))) if nums and nums[0] > 0 else ""
        print(" | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in vals) + bar)

_SRC = open(os.path.join(_WORK, "job.py"), encoding="utf-8").read()
sys.addaudithook(_hook)
exec(compile(_SRC, "job.py", "exec"), {"q": q, "show": show, "REPORT_DB": REPORT_DB, "__name__": "__main__"})
'''


def _mode() -> str:
    want = os.environ.get("CREW_SANDBOX", "auto")
    if want in ("docker", "process"):
        return want
    return "docker" if _docker_ready() else "process"


@lru_cache(maxsize=1)
def _docker_ready() -> bool:
    """Docker 데몬이 돌고 이미지가 이미 있을 때만(내려받지 않는다)."""
    if not shutil.which("docker"):
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True, timeout=3).returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


# 9-4: 사본에 담을 줄. 매장 칸이 있는 표는 그 매장 것만, 주문·고객에 딸린 표는 그 매장 주문·고객 것만.
# 여기 없는 표(행동 기록·요금·랩 설정·outbox·위임 토큰 등)는 모양만 있고 비어 있다(새 표가 생겨도 기본은 비어 있다)
_SCOPE = {
    "stores": "id = :store",
    "users": "store_id = :store",
    "products": "store_id = :store",
    "orders": "store_id = :store",
    "docs": "store_id = :store",
    "order_items": "order_id IN (SELECT id FROM live.orders WHERE store_id = :store)",
    "shipments": "order_id IN (SELECT id FROM live.orders WHERE store_id = :store)",
    "refunds": "order_id IN (SELECT id FROM live.orders WHERE store_id = :store)",
    "coupons": "customer_id IN (SELECT id FROM live.users WHERE store_id = :store)",
    "tickets": "customer_id IN (SELECT id FROM live.users WHERE store_id = :store)",
    "memories": "customer_id IN (SELECT id FROM live.users WHERE store_id = :store)",
    "approvals": "store_id = :store",
}


def _requester_store() -> str | None:
    """지금 요청한 사람의 매장(게이트웨이가 CURRENT_USER에 넣는다). 모르면 None → 사본은 비어 있다."""
    from crew.runtime.audit import CURRENT_USER

    user = CURRENT_USER.get()
    return getattr(user, "store_id", None)


def store_copy(src: Path, folder: Path, store: str | None) -> Path:
    """9-4: 새 DB 파일에 표 모양을 만들고, 그 매장 줄만 옮긴다. 읽기 전용으로 잠근다."""
    dst = folder / "report.db"
    db = sqlite3.connect(dst)
    try:
        db.execute("ATTACH DATABASE ? AS live", (str(src),))
        tables = db.execute("SELECT name, sql FROM live.sqlite_master WHERE type = 'table' AND sql IS NOT NULL "
                            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        virtual = [n for n, sql in tables if sql.upper().startswith("CREATE VIRTUAL")]
        for name, sql in tables:
            if name in virtual or any(name.startswith(v + "_") for v in virtual):
                continue  # 검색 색인(docs_fts)은 옮기지 않는다
            db.execute(sql)
            where = _SCOPE.get(name)
            if where and store:
                db.execute(f"INSERT INTO main.{name} SELECT * FROM live.{name} WHERE {where}", {"store": store})
        db.commit()
        db.execute("DETACH DATABASE live")
    finally:
        db.close()
    dst.chmod(0o444)
    return dst


def _limits(timeout: float):  # 제한 프로세스 모드: CPU 시간과 파일 크기 상한(POSIX에서만)
    def apply() -> None:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (int(timeout) + 1, int(timeout) + 2))
            resource.setrlimit(resource.RLIMIT_FSIZE, (5_000_000, 5_000_000))
        except (ImportError, ValueError, OSError):
            pass
    return apply if os.name == "posix" else None


USERS = {"nobody": "65534:65534", "root": "0:0"}  # 이름 → uid:gid (이미지 안 /etc/passwd와 같은 값)
DOCKER_GRACE_S = 20.0   # 컨테이너가 뜨는 데 드는 시간. 코드의 시간 제한은 컨테이너 안에서 따로 잰다
TIMEOUT_EXIT = 124      # 컨테이너 안 `timeout`이 시간 제한으로 끊었을 때의 종료 값


def docker_command(work: Path, main: Path, db: str, policy: Policy, cfg: dict, timeout: float,
                   name: str = "crew-sbx") -> list[str]:
    """컨테이너 모드의 docker run 명령(실행하지 않는다. 시험이 모양을 본다)."""
    user = USERS.get(policy.run_as, policy.run_as)
    return ["docker", "run", "--rm", "--name", name, "--network", "none", "--user", user, "--read-only",
            "--tmpfs", "/tmp:rw,size=16m", "--memory", "256m", "--pids-limit", "64", "--cpus", "1",
            "--ulimit", "fsize=5000000:5000000", "-e", "CREW_SBX=" + json.dumps(cfg), "-e", "PYTHONIOENCODING=utf-8",
            "-v", f"{work}:/work:rw", "-v", f"{main}:/sbx/main.py:ro", "-v", f"{db}:/data/report.db:ro",
            "-w", "/work", IMAGE, "timeout", "-s", "KILL", f"{timeout:g}", "python", "-I", "-B", "/sbx/main.py"]


def _execute(code: str, policy: Policy, *, network, guard: bool, cap: float) -> Result:
    live = Path(get_settings().db_path)
    scratch = Path(tempfile.mkdtemp(prefix="crew-sbx-"))
    work = live.parent if policy.workdir == "lab" else scratch / "work"
    work.mkdir(parents=True, exist_ok=True)
    try:
        if policy.db == "live":
            db, uri = str(live), str(live)
        else:
            ro = store_copy(live, scratch, _requester_store())
            db, uri = str(ro), f"file:{ro}?mode=ro"
        (work / "job.py").write_text(code, encoding="utf-8")
        (scratch / "main.py").write_text(PRELUDE, encoding="utf-8")
        timeout = min(policy.timeout_s, cap)
        want = _mode()
        if policy.workdir == "temp" and policy.db != "live" and want == "docker":
            r = _in_docker(work, scratch, db, policy, network, guard, timeout)
            if r is not None or os.environ.get("CREW_SANDBOX") == "docker":
                return r or Result(False, "", "Docker 컨테이너를 띄우지 못했습니다", "docker")
        return _in_process(work, scratch, db, uri, policy, network, guard, timeout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def _in_process(work: Path, scratch: Path, db: str, uri: str, policy: Policy, network, guard: bool,
                timeout: float) -> Result:
    cfg = {"db": db, "db_uri": uri, "work": str(work), "network": network, "guard": guard}
    cmd = [sys.executable, "-I", "-B", str(scratch / "main.py")]
    env = {"CREW_SBX": json.dumps(cfg), "PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8",
           "NO_PROXY": "*", "HTTP_PROXY": "", "HTTPS_PROXY": ""}
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout,
                           preexec_fn=_limits(timeout) if guard else None)
    except subprocess.TimeoutExpired:
        return Result(False, "", f"시간 제한({timeout:g}초)을 넘어 멈췄습니다", "process", True, time.monotonic() - t0)
    return _result(p, "process", time.monotonic() - t0)


def _in_docker(work: Path, scratch: Path, db: str, policy: Policy, network, guard: bool,
               timeout: float) -> Result | None:
    """컨테이너 모드. 컨테이너가 뜨지 못하면(데몬 오류 등) None → auto는 제한 프로세스 모드로 돈다."""
    import uuid

    cfg = {"db": "/data/report.db", "db_uri": "file:/data/report.db?mode=ro", "work": "/work",
           "network": network, "guard": guard}
    os.chmod(work, 0o777)                     # 컨테이너 안의 관리자 권한이 없는 사용자가 작업 폴더에 쓸 수 있게(임시 폴더라 괜찮다)
    (work / "job.py").chmod(0o644)
    (scratch / "main.py").chmod(0o644)
    name = f"crew-sbx-{uuid.uuid4().hex[:8]}"
    cmd = docker_command(work, scratch / "main.py", db, policy, cfg, timeout, name)
    t0 = time.monotonic()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + DOCKER_GRACE_S)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True, timeout=10)
        return Result(False, "", f"시간 제한({timeout:g}초)을 넘어 멈췄습니다", "docker", True, time.monotonic() - t0)
    except OSError:
        return None
    if p.returncode in (TIMEOUT_EXIT, 137) and not p.stderr.strip():
        return Result(False, p.stdout[:RAW_CAP], f"시간 제한({timeout:g}초)을 넘어 멈췄습니다", "docker", True,
                      time.monotonic() - t0)
    if p.returncode in (125, 126, 127) and "/sbx/main.py" not in p.stderr:
        return None                           # docker 자체가 실패했다(코드는 돌지 않았다)
    return _result(p, "docker", time.monotonic() - t0)


def _result(p: subprocess.CompletedProcess, mode: str, seconds: float) -> Result:
    err = p.stderr.strip().splitlines()
    return Result(p.returncode == 0, p.stdout[:RAW_CAP], err[-1] if err else "", mode, False, seconds)


def run_in_place(code: str) -> Result:
    """9-1 맛보기: 랩 데이터 폴더에서 진짜 DB로 그대로 실행한다. 9-2 사고의 원인."""
    return _execute(code, Policy(timeout_s=HARD_CAP_S, network=True, db="live", workdir="lab"),
                    network="record", guard=False, cap=HARD_CAP_S)


def run(code: str, policy: Policy = Policy()) -> Result:
    """9-4 샌드박스: policy대로 가둬서 실행한다."""
    return _execute(code, policy, network=policy.network, guard=True, cap=HARD_CAP_S)


def describe(policy: Policy) -> dict:
    return asdict(policy) | {"mode": _mode()}
