"""모든 확인은 가짜 LLM으로, 시험용 임시 DB에서 돈다. 키가 필요 없고 결과가 늘 같다.

선택 패키지(requirements-extra.txt: openai-guardrails·presidio)가 설치돼 있어도 시험은 가벼운 대체 구현으로 돈다.
Presidio가 있으면 pii.mask()가 영어 모델로 "사람 이름"을 더 가려서(예: 도구 인자·주문 문장 속 낱말) 가짜 LLM의
답과 시험의 기대가 달라진다. 그래서 시험 동안은 두 패키지를 없는 것으로 본다(import하면 ImportError).
"""
import os
import sys

import pytest


@pytest.fixture(autouse=True)
def lab(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_MODE", "fake")
    for extra in ("presidio_analyzer", "presidio_anonymizer", "guardrails"):  # 선택 패키지는 시험에서 끈다
        monkeypatch.setitem(sys.modules, extra, None)
    monkeypatch.setenv("CREW_SANDBOX", "process")  # 9장 샌드박스는 시험에서 늘 제한 프로세스 모드
    monkeypatch.setenv("CREW_DB", str(tmp_path / "cs_crew.db"))
    monkeypatch.setenv("CREW_SESSIONS_DB", str(tmp_path / "sessions.db"))
    from crew.db.seed import build
    from crew.runtime.audit import CURRENT_USER
    from crew.runtime.llm import get_model

    get_model.cache_clear()
    build()
    who = CURRENT_USER.set(None)  # 시험이 직접 넣은 "요청한 사람"이 다음 시험으로 새지 않게
    yield
    CURRENT_USER.reset(who)
    get_model.cache_clear()
