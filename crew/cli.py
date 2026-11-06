"""수강생 명령 모음. make가 없으면(Windows 등) `python -m crew <명령>`으로 똑같이 쓴다.

  python -m crew next              다음 수업 카드 보기
  python -m crew lesson 2-4        수업 카드 보기
  python -m crew check 2-4         수업 확인(그린이면 완료로 표시)
  python -m crew check-all         지금까지 마친 수업 모두 다시 확인
  python -m crew status            진도와 OWASP 지도
  python -m crew solution 2-4      내 코드와 정답의 차이 보기
  python -m crew apply-solution 2-4  정답으로 덮어쓰기(내 파일은 data/backup에 남김)
  python -m crew redteam [번호]    레드팀 시나리오 돌리기 (--ci: 사고·오탐이 있으면 실패로 끝남)
  python -m crew goto 5-1          5-1 수업 시작 지점으로 이동(내 파일은 data/backup에 남김)
  python -m crew seed              가게 데이터 처음 상태로
  python -m crew run               화면 띄우기 http://127.0.0.1:8000 (CREW_PORT로 바꿈)
  python -m crew mcp-pins          택배사 MCP 도구 설명의 해시 보기(10-4 고정용)
  python -m crew import samples/   CSV(products·orders·docs)를 가게 DB에 넣기(13-3)
"""
from __future__ import annotations

import difflib
import shutil
from pathlib import Path
import subprocess
import sys
from datetime import datetime

from crew import course
from crew.config import DATA, ROOT
from crew.runtime.sync import run_sync

GREEN, RED, DIM, END = "\033[32m", "\033[31m", "\033[2m", "\033[0m"


def cmd_lesson(lid: str) -> None:
    print(course.card(lid))


def cmd_next() -> None:
    nxt = course.next_lesson()
    if nxt is None:
        print(f"{GREEN}65개 수업을 모두 마쳤습니다. 수고하셨습니다!{END}")
        return
    print(f"{DIM}다음 수업 → {nxt['no']}{END}\n")
    print(course.card(nxt["id"]))


def _pytest(paths: list) -> int:
    return subprocess.call([sys.executable, "-m", "pytest", *map(str, paths)], cwd=ROOT)


def cmd_check(lid: str) -> None:
    lid = course.norm(lid)
    l = course.find(lid)
    tests = course.tests_for(lid)
    if not tests:
        course.mark_done(lid)
        print(f"{GREEN}✔ {l['no']} 확인할 시험이 없는 수업입니다(보고 따라 하는 수업). 완료로 표시했습니다.{END}")
        return
    if _pytest(tests) == 0:
        course.mark_done(lid)
        print(f"\n{GREEN}✔ {l['no']} 통과! 다음 수업은 `make next`{END}")
    else:
        print(f"\n{RED}✘ {l['no']} 아직입니다. 위 레드 줄의 '기대' 문장을 읽어 보세요.{END}\n"
              f"  막히면: make solution L={l['no']}  (정답과의 차이)")
        sys.exit(1)


def cmd_check_all() -> None:
    tests = [t for lid in sorted(course.done()) for t in course.tests_for(lid)]
    tests += sorted((ROOT / "tests").glob("test_lab_*.py"))
    sys.exit(_pytest(tests))


def cmd_status() -> None:
    d = course.done()
    for s in course.sections():
        ids = [l["id"] for l in s["lessons"]]
        n = sum(1 for i in ids if i in d)
        bar = "█" * n + "·" * (len(ids) - n)
        print(f"섹션 {s['section']:>2} {bar:<6} {n}/{len(ids)}  {s['title']}")
    print("\nOWASP Agentic Top 10 지도")
    for name, lvl in course.owasp_map():
        print(f"  {course.gauge(lvl)}  {name}")
    nxt = course.next_lesson()
    if nxt:
        print(f"\n다음 수업: {nxt['no']} {nxt['title']}  → make next")


def _solution_files(lid: str):
    base = course.SOLUTIONS / course.norm(lid)
    if not base.exists():
        raise SystemExit("이 수업은 정답 파일이 없습니다(고칠 코드가 없는 수업).")
    return [(p, ROOT / p.relative_to(base)) for p in sorted(base.rglob("*.py"))]


def cmd_solution(lid: str) -> None:
    for sol, mine in _solution_files(lid):
        a = mine.read_text("utf-8").splitlines() if mine.exists() else []
        b = sol.read_text("utf-8").splitlines()
        rel = mine.relative_to(ROOT)
        diff = list(difflib.unified_diff(a, b, f"내 코드 {rel}", f"정답 {rel}", lineterm=""))
        if not diff:
            print(f"{GREEN}{rel}: 정답과 같습니다{END}")
            continue
        for line in diff:
            color = GREEN if line.startswith("+") else RED if line.startswith("-") else ""
            print(f"{color}{line}{END if color else ''}")


def cmd_apply_solution(lid: str) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for sol, mine in _solution_files(lid):
        if mine.exists():
            backup = DATA / "backup" / stamp / mine.relative_to(ROOT)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mine, backup)
        mine.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sol, mine)
        print(f"정답으로 바꿨습니다: {mine.relative_to(ROOT)}")
    print(f"{DIM}내 원래 파일은 data/backup/{stamp}/에 있습니다.{END}")


def cmd_redteam(*args: str) -> None:
    """레드팀 시나리오. `--ci`면 사고·오탐이 하나라도 있을 때 1로 끝난다(13-2 CI 게이트)."""
    from crew.redteam import load, run_scenario

    ci = "--ci" in args
    which = next((a for a in args if a != "--ci"), None)
    bad = 0
    for sc in load():
        if which and str(sc["id"]) != which:
            continue
        r = run_scenario(sc)
        mark = {"incident": f"{RED}사고{END}", "blocked": f"{GREEN}막힘{END}", "locked": f"{DIM}잠김{END}"}[r["state"]]
        extra = f" · 막은 층: {r['layer']}" if r.get("layer") else ""
        extra += f" · {RED}정상 요청도 막힘(오탐){END}" if r.get("false_positive") else ""
        print(f"{sc['id']:>2}. {mark}  {sc['title']}{extra}  {DIM}{r.get('note', '')}{END}")
        bad += r["state"] == "incident" or bool(r.get("false_positive"))
    if ci:
        print(f"\n레드팀 게이트: {'통과' if not bad else f'실패 {bad}건(사고·오탐)'}")
        sys.exit(1 if bad else 0)


def cmd_goto(lid: str, which: str = "start") -> None:
    import shutil

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for d in course.STUDENT_DIRS:
        if (ROOT / d).exists():
            shutil.copytree(ROOT / d, DATA / "backup" / stamp / d, dirs_exist_ok=True)
    applied = course.goto(lid, done=(which == "done"))
    l = course.find(lid)
    ids = course.order()
    course.set_done(ids[:ids.index(l["id"]) + (1 if which == "done" else 0)])  # 뒤 수업의 진도는 지운다
    from crew.db.seed import build

    build()
    print(f"{GREEN}{l['no']} 수업 {'완료' if which == 'done' else '시작'} 지점으로 왔습니다{END} "
          f"{DIM}(정답 {len(applied)}개 적용, 내 파일은 data/backup/{stamp}/){END}")
    if which == "done":
        ids = course.order()
        i = ids.index(l["id"]) + 1
        print(f"다음: make lesson L={course.short(ids[i])}" if i < len(ids) else "마지막 수업까지 왔습니다.")
    else:
        print(f"다음: make lesson L={l['no']}")


def _passed(junit: Path) -> list[str]:
    """pytest --junitxml 결과에서 통과한 시험 이름."""
    import xml.etree.ElementTree as ET

    if not junit.exists():
        return []
    out = []
    for case in ET.parse(junit).iter("testcase"):
        if not any(child.tag in ("failure", "error", "skipped") for child in case):
            out.append(f"{case.get('classname', '').rsplit('.', 1)[-1]}::{case.get('name')}")
    return out


def _verify_lesson(lid: str, tmp: Path) -> tuple[str, list[str]]:
    """한 수업을 자기 임시 복사본에서 확인한다. (표시 글, 문제 목록)"""
    import os

    lab = tmp / lid
    shutil.copytree(ROOT, lab, ignore=shutil.ignore_patterns(".venv", "data", "__pycache__", "cassettes"))
    env = os.environ | {"PYTHONPATH": str(lab)}
    tests = [str(t.relative_to(ROOT)) for t in course.tests_for(lid)]
    has_sol = (course.SOLUTIONS / lid).exists()
    bad: list[str] = []
    try:
        if tests and has_sol:
            # 시작 지점: 시험 하나하나가 레드여야 한다. @pytest.mark.normal(오탐 없음·그대로 되는지 보는 짝)만 그린이어도 된다
            course.goto(lid, root=lab, src=lab)
            junit = lab / "start.xml"
            subprocess.call([sys.executable, "-m", "pytest", "-q", "-m", "not normal", f"--junitxml={junit}", *tests],
                            cwd=lab, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            green = _passed(junit)
            if green:
                bad.append(f"{lid}: 시작 지점에서 이미 그린(고칠 것이 없음): {', '.join(green)}")
        course.goto(lid, done=True, root=lab, src=lab)
        if tests:
            ok = subprocess.call([sys.executable, "-m", "pytest", "-q", *tests], cwd=lab, env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ok != 0:
                bad.append(f"{lid}: 완료 지점에서 레드")
    finally:
        shutil.rmtree(lab, ignore_errors=True)
    return f"{'시험' if tests else '-'} {'정답' if has_sol else ''}", bad


def cmd_verify_course(*args: str) -> None:  # 강사용: 모든 수업이 '시작=레드, 정답 적용=그린'인지 임시 복사본에서 확인
    """수업마다 따로 임시 복사본을 만들어 나란히 돌린다(CREW_VERIFY_JOBS, 기본 4).
    끝으로 마지막 수업 완료 지점에서 전체 시험을 돌린다."""
    import os
    import tempfile
    from concurrent.futures import ThreadPoolExecutor

    tmp = Path(tempfile.mkdtemp(prefix="crew-verify-"))
    jobs = int(os.environ.get("CREW_VERIFY_JOBS", "4"))
    bad = 0
    try:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = [(lid, pool.submit(_verify_lesson, lid, tmp)) for lid in course.order()]
            for lid, fut in futures:
                label, problems = fut.result()
                for msg in problems:
                    print(f"{RED}✘ {msg}{END}", flush=True)
                bad += len(problems)
                if not problems:
                    print(f"{GREEN}✔{END} {lid} {label}", flush=True)
        lab = tmp / "final"
        shutil.copytree(ROOT, lab, ignore=shutil.ignore_patterns(".venv", "data", "__pycache__", "cassettes"))
        course.goto(course.order()[-1], done=True, root=lab, src=lab)
        final = subprocess.call([sys.executable, "-m", "pytest", "-q", "tests"], cwd=lab,
                                env=os.environ | {"PYTHONPATH": str(lab)})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n전체 시험(마지막 수업 완료 지점): {'그린' if final == 0 else '레드'} · 문제 {bad}개")
    sys.exit(1 if bad or final else 0)


def cmd_seed() -> None:
    from crew.db.seed import build

    print(f"가게 데이터를 처음 상태로 만들었습니다: {build()}")


def cmd_run() -> None:
    import os
    import socket

    import uvicorn

    from crew.config import get_settings

    get_settings()  # .env를 읽는다
    port = int(os.environ.get("CREW_PORT", "8000"))
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"{RED}{port}번 포트를 다른 프로그램이 쓰고 있습니다. "
                             f".env에 CREW_PORT=8001 처럼 다른 번호를 넣고 다시 실행하세요.{END}")
    print(f"http://127.0.0.1:{port} 을 브라우저로 여세요. 끄려면 Ctrl+C")
    uvicorn.run("crew.web.app:app", host="127.0.0.1", port=port, reload=False)


def cmd_import(path: str = "samples") -> None:
    """13-3: CSV(products·orders·docs)를 가게 DB에 넣는다."""
    from crew.db.importer import ImportProblem, import_csv

    src = ROOT / path if not Path(path).is_absolute() else Path(path)
    if not src.exists():
        raise SystemExit(f"{RED}가져오기 실패: {path} 이(가) 없습니다.{END}")
    try:
        done = import_csv(src)
    except ImportProblem as e:
        raise SystemExit(f"{RED}가져오기 실패: {e}{END}")
    for table, n in done.items():
        print(f"{table}: {n}줄 넣었습니다")


def cmd_mcp_pins() -> None:
    """10-4: 지금 택배사 서버(lab_flags의 carrier_version, 기본 v1)가 내놓는 도구 해시. 믿을 버전에서 한 번 뽑아 고정한다."""
    import asyncio

    from crew.runtime.mcp_link import current_hashes

    for name, h in run_sync(current_hashes()).items():
        print(f'    "{name}": "{h}",')


def cmd_sync_lessons() -> None:  # 강사용: README 7절 → course/lessons.yaml
    from crew.authoring import sync_lessons

    sync_lessons()


COMMANDS = {"lesson": cmd_lesson, "next": cmd_next, "check": cmd_check, "check-all": cmd_check_all,
            "status": cmd_status, "solution": cmd_solution, "apply-solution": cmd_apply_solution,
            "redteam": cmd_redteam, "goto": cmd_goto, "verify-course": cmd_verify_course, "seed": cmd_seed, "run": cmd_run, "sync-lessons": cmd_sync_lessons,
            "mcp-pins": cmd_mcp_pins, "import": cmd_import}


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if not args else 2)
    COMMANDS[args[0]](*args[1:])
