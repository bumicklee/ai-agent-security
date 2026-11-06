"""수업 진도. 어느 수업을 마쳤는지, 다음은 무엇인지, OWASP 지도가 얼마나 찼는지."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from crew.config import DATA, ROOT

COURSE = ROOT / "course"
CARDS = ROOT / "lessons"
SOLUTIONS = ROOT / "solutions"
PROGRESS = DATA / "progress.json"


def norm(lesson: str) -> str:
    """'2-4', 's2-04', 's2-4' → 's2-04'"""
    m = re.fullmatch(r"s?(\d+)-(\d+)", lesson.strip())
    if not m:
        raise SystemExit(f"수업 번호는 2-4처럼 씁니다: {lesson}")
    return f"s{int(m.group(1))}-{int(m.group(2)):02d}"


def short(lid: str) -> str:
    sec, no = lid[1:].split("-")
    return f"{int(sec)}-{int(no)}"


def sections() -> list[dict]:
    return yaml.safe_load((COURSE / "lessons.yaml").read_text("utf-8"))


def lessons() -> list[dict]:
    return [l | {"section": s["section"]} for s in sections() for l in s["lessons"]]


def find(lid: str) -> dict:
    lid = norm(lid)
    for l in lessons():
        if l["id"] == lid:
            return l
    raise SystemExit(f"없는 수업입니다: {short(lid)}")


def done() -> set[str]:
    try:
        return set(json.loads(PROGRESS.read_text("utf-8")))
    except (FileNotFoundError, ValueError):
        return set()


def mark_done(lid: str) -> None:
    d = done() | {norm(lid)}
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(sorted(d)), "utf-8")


def set_done(ids: list[str]) -> None:
    """진도를 정확히 이 수업들로 바꾼다(goto: 그 앞 수업들까지)."""
    PROGRESS.parent.mkdir(exist_ok=True)
    PROGRESS.write_text(json.dumps(sorted({norm(i) for i in ids})), "utf-8")


def next_lesson() -> dict | None:
    d = done()
    return next((l for l in lessons() if l["id"] not in d), None)


def tests_for(lid: str) -> list[Path]:
    return sorted((ROOT / "tests").glob(f"test_{norm(lid).replace('-', '_')}_*.py"))


def card(lid: str) -> str:
    path = CARDS / f"{norm(lid)}.md"
    if path.exists():
        return path.read_text("utf-8")
    l = find(lid)
    return f"# {l['no']} {l['title']}\n\n(이 수업의 따라 하기 카드는 아직 준비 중입니다.)\n"


def owasp_map() -> list[tuple[str, int]]:
    d = {short(x) for x in done()}
    raw = yaml.safe_load((COURSE / "owasp_map.yaml").read_text("utf-8"))
    return [(name, max([lvl for no, lvl in steps if str(no) in d], default=0)) for name, steps in raw.items()]


def gauge(level: int) -> str:
    return "●" * level + "○" * (3 - level)


# ── 수업 이동(git 없이): 처음 상태(course/base) + 앞 수업들의 정답(solutions/)을 차례로 덮는다 ──
BASE = COURSE / "base"
STUDENT_DIRS = ("crew/agents", "crew/tools", "crew/guards")


def order() -> list[str]:
    return [l["id"] for l in lessons()]


def goto(lid: str, *, done: bool = False, root: Path = ROOT, src: Path | None = None) -> list[str]:
    """lid 수업의 시작 지점(done=True면 완료 지점)으로 학생 폴더를 맞춘다. 적용한 정답 목록을 돌려준다.
    src: course/base·solutions를 읽을 곳(기본은 이 랩. verify-course는 임시 복사본 자신을 쓴다)"""
    import shutil

    base = (src / "course" / "base") if src else BASE
    solutions = (src / "solutions") if src else SOLUTIONS
    target = norm(lid)
    ids = order()
    stop = ids.index(target) + (1 if done else 0)
    for d in STUDENT_DIRS:
        shutil.rmtree(root / d, ignore_errors=True)
        shutil.copytree(base / d, root / d)
    applied = []
    for i in ids[:stop]:
        sol = solutions / i
        if sol.exists():
            for f in sorted(sol.rglob("*")):
                if f.is_file() and "__pycache__" not in f.parts:
                    dest = root / f.relative_to(sol)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dest)
            applied.append(i)
    return applied
