"""완성본(runtime·web)이 학생 코드를 찾아 부르는 곳.

학생 파일이 아직 없으면(그 수업 전이면) 기본값으로 조용히 쉰다. 예: 4-3 전에는 마스킹 없이 그대로 보낸다.
"""
from __future__ import annotations

import importlib
from typing import Any


def student(module: str, name: str, default: Any = None) -> Any:
    """`crew.guards.pii`의 `mask`처럼 학생 폴더의 이름을 찾는다. 없으면 default."""
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as e:
        if e.name and (e.name == module or module.startswith(e.name + ".")):
            return default
        raise
    return getattr(mod, name, default)


def student_module(module: str) -> Any:
    """학생 파일(모듈) 자체. 없으면 None."""
    marker = object()
    return importlib.import_module(module) if student(module, "__name__", marker) is not marker else None


def need(module: str, name: str, expect: str) -> Any:
    """시험용: 학생 파일의 이름을 찾는다. 아직 없으면 스택 대신 "기대: …" 한 문장으로 실패한다."""
    try:
        value = student(module, name)
    except ImportError:
        value = None
    if value is None:
        raise AssertionError(f"기대: {expect} ({module.replace('.', '/')}.py 의 {name})")
    return value
