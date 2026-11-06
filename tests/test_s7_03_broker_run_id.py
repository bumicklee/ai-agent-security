"""7-3 회귀: 브로커 기록(delegation_use)이 그 요청의 run_id로 남는다."""
from crew.db import session
from crew.runtime.run import act


def test_브로커_기록이_요청_번호로_남는다():
    out = act("dave", 7)
    with session() as db:
        rows = db.execute("SELECT run_id FROM audit_log WHERE action = 'delegation_use'").fetchall()
    assert rows and all(r["run_id"] == out.run_id for r in rows), "기대: 위임 토큰 사용 기록이 그 요청(run_id)에 묶인다"
