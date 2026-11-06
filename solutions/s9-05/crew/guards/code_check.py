"""9-5: 리포트 코드 실행 전 검사와 결과 크기 제한.

샌드박스(9-4)는 "실행해도 덜 다치게", 실행 전 검사는 "위험한 코드는 아예 돌리지 않게". 둘 다 둔다.
리포트 코드는 q()로 읽고 show()로 내는 것만 하면 된다. 위험한 모듈·내장 함수는 쓰지 못하게 한다.
import는 허용 목록(ALLOWED_IMPORTS)만 바로 돈다. 목록 밖 모듈은 직원 승인 뒤에만 돈다(needs_review → 승인 대기열).
"""
from __future__ import annotations

import ast

BANNED_MODULES = {"os", "sys", "subprocess", "socket", "shutil", "urllib", "http", "requests", "pathlib", "ctypes",
                  "importlib", "multiprocessing", "sqlite3", "pickle"}
ALLOWED_IMPORTS = {"math", "statistics", "collections", "json", "datetime", "csv"}  # 계산·정리용만
BANNED_CALLS = {"open", "eval", "exec", "compile", "__import__", "getattr", "setattr", "globals", "vars", "input"}
MAX_LINES, MAX_CHARS = 25, 2000   # 결과는 집계표 한 장 크기까지


def check(code: str) -> str | None:
    """막을 이유(거부: …) 또는 None."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"거부: 코드 문법 오류({e.msg})"
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if bad := next((n for n in names if n.split(".")[0] in BANNED_MODULES), None):
                return f"거부: 실행 전 검사 — '{bad}' 모듈은 리포트 코드에서 쓸 수 없습니다"
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in BANNED_CALLS:
            return f"거부: 실행 전 검사 — '{node.func.id}()'는 쓸 수 없습니다"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "거부: 실행 전 검사 — 밑줄 두 개(__…) 속성은 쓸 수 없습니다"
    return None


def imports(code: str) -> set[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set()
    names = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    return {n.split(".")[0] for n in names}


async def needs_review(ctx, params: dict, call_id: str) -> bool:
    """run_python의 needs_approval. 허용 목록 밖(금지 목록도 아닌) 모듈을 쓰면 직원 승인을 받는다."""
    extra = imports(params.get("code", "")) - ALLOWED_IMPORTS
    return bool(extra) and not extra & BANNED_MODULES  # 금지 모듈은 승인 없이 check()가 바로 거부한다


def limit(text: str) -> str | None:
    lines = text.strip().splitlines()
    if len(lines) > MAX_LINES or len(text) > MAX_CHARS:
        return f"거부: 결과가 너무 큽니다({len(lines)}줄·{len(text)}자). 집계표 한 장({MAX_LINES}줄)으로 줄여 주세요."
    return None
