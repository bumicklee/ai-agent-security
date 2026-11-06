"""13-2 레드팀 콘솔 replay를 CI 게이트로."""
from pathlib import Path

import pytest

from crew.config import ROOT


def test_워크플로가_게이트를_돌린다():
    wf = (ROOT / ".github" / "workflows" / "redteam.yml").read_text("utf-8")
    assert "redteam --ci" in wf and "check-all" in wf, "기대: CI가 레드팀 게이트와 check-all을 돌린다"
    assert "OPENAI_API_KEY" not in wf, "기대: CI는 키 없이(fake·replay) 돈다"


def test_사고가_있으면_게이트가_실패한다(monkeypatch):
    import crew.redteam as rt
    from crew.cli import cmd_redteam

    monkeypatch.setattr(rt, "run_scenario", lambda sc: {"state": "incident" if sc["id"] == 3 else "blocked"})
    with pytest.raises(SystemExit) as e:
        cmd_redteam("--ci")
    assert e.value.code == 1, "기대: 사고가 하나라도 있으면 1로 끝난다"
    monkeypatch.setattr(rt, "run_scenario", lambda sc: {"state": "blocked"})
    with pytest.raises(SystemExit) as e:
        cmd_redteam("--ci")
    assert e.value.code == 0, "기대: 모두 막히면 0"
