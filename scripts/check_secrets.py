"""pre-commit 훅(1-4): .env 파일이나 sk- 로 시작하는 키 모양 글이 커밋에 들어가면 막는다.

설치 없이 표준 라이브러리만 쓴다. pre-commit이 바뀐 파일 이름을 인자로 넘긴다.
  python scripts/check_secrets.py 파일…   → 문제가 있으면 이유를 찍고 1로 끝난다
키 값은 찍지 않는다(앞 6글자만).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

KEY = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
ALLOWED_ENV = {".env.example"}


def problems(paths: list[str]) -> list[str]:
    out = []
    for name in paths:
        p = Path(name)
        if p.name.startswith(".env") and p.name not in ALLOWED_ENV:
            out.append(f"{name}: .env 파일은 커밋하지 않습니다(.gitignore)")
            continue
        try:
            text = p.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in KEY.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            out.append(f"{name}:{line}: 키처럼 보이는 글({m.group(0)[:6]}…)이 있습니다")
    return out


if __name__ == "__main__":
    found = problems(sys.argv[1:])
    for f in found:
        print(f"✘ {f}")
    sys.exit(1 if found else 0)
