"""4-5 로그·트레이스 마스킹과 트레이싱을 켤지 끌지."""
from crew.db import session
from crew.runtime.run import _run_config, ask, trace_policy


def _log(run_id: str) -> str:
    with session() as db:
        return " ".join(r["detail"] for r in db.execute("SELECT detail FROM audit_log WHERE run_id = ?", (run_id,)))


def test_되돌린_답도_기록에는_가려진다():
    out = ask("alice", "연락처는 010-0000-1234 입니다. 이 번호로 연락 주세요")
    assert "010-0000-1234" in out.reply, "기대: 고객 화면에는 되돌린 번호가 보인다(4-4)"
    assert "0000-1234" not in _log(out.run_id), "기대: 행동 기록(audit_log)에는 번호가 없다 → pii.scrub_log()"


def test_트레이스에_원문을_싣지_않는다():
    assert _run_config().trace_include_sensitive_data is False, \
        "기대: crew/guards/pii.py에 TRACE_INCLUDE_SENSITIVE = False (SDK 기본값 True를 끈다)"
    assert trace_policy("live")["include_sensitive"] is False, "기대: live로 돌려도 트레이스에 입력·출력 원문이 없다"
