"""강사용 도구. 수강생은 쓰지 않는다."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from crew.config import ROOT

README = ROOT.parent.parent / "README.md"  # book-3-llm-agent-보안-실전/README.md (기획서)


def sync_lessons(readme: Path = README) -> None:
    text = readme.read_text("utf-8")
    cur = text[text.index("## 7. 커리큘럼"):text.index("## 8.")]
    out: list[dict] = []
    for line in cur.splitlines():
        if m := re.match(r"### 섹션 (\d+)\. (.+?) \(\d+수업\)", line):
            out.append({"section": int(m.group(1)), "title": m.group(2), "lessons": []})
        elif m := re.match(r"^(\d+)-(\d+) (.+)$", line):
            title = m.group(3)
            item = {"id": f"s{int(m.group(1))}-{int(m.group(2)):02d}", "no": f"{m.group(1)}-{m.group(2)}",
                    "title": title.replace("★ ", "").replace(" (무료)", "")}
            if "★" in title:
                item["owasp"] = True
            if "(무료)" in title:
                item["free"] = True
            out[-1]["lessons"].append(item)
    header = "# 수업 목록. README 7절에서 만든다(python -m crew sync-lessons). 손으로 고치지 않는다.\n"
    (ROOT / "course" / "lessons.yaml").write_text(
        header + yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=200), "utf-8")
    print(f"수업 {sum(len(s['lessons']) for s in out)}개를 course/lessons.yaml에 썼습니다.")
