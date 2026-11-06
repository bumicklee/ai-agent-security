"""4-3 FastAPI 앞단(게이트웨이)에서 한국형 패턴으로 마스킹."""
import pytest
import json

from crew.db import session
from crew.runtime.run import ask
from crew.runtime.plug import need


def _log(run_id: str) -> str:
    with session() as db:
        return " ".join(r["detail"] for r in db.execute("SELECT detail FROM audit_log WHERE run_id = ?", (run_id,)))


def test_세_가지_패턴을_가린다():
    mask = need("crew.guards.pii", "mask", "개인정보 가리기 mask()를 만든다")

    text, _ = mask("카드 0000-1111-2222-3333, 주민번호 991231-0000000, 전화 010-0000-1234")
    for raw in ("0000-1111-2222-3333", "991231-0000000", "010-0000-1234"):
        assert raw not in text, f"기대: {raw} 가 가려진다"
    for label in ("카드", "주민번호", "전화"):
        assert f"[MASKED:{label}" in text, f"기대: [MASKED:{label}] 자리표가 남는다"


def test_카드_번호가_모델과_로그에_가지_않는다():
    out = ask("alice", "결제가 안 돼요. 카드 번호 0000-1111-2222-3333 이에요")
    assert "1111-2222" not in out.reply, "기대: 답에 카드 번호가 없다(모델이 원래 값을 받은 적이 없다)"
    assert "1111-2222" not in _log(out.run_id), "기대: 행동 기록(audit_log)에도 카드 번호가 없다"
    assert out.masked >= 1, "기대: 게이트웨이가 mask()를 불러 1개 이상 가렸다"


@pytest.mark.normal
def test_주문_번호는_가리지_않는다():
    out = ask("alice", "주문 1002 결제 확인해 주세요")
    assert "1002" in out.reply and out.masked == 0, "기대: 4자리 주문 번호는 개인정보가 아니다(오탐 없음)"
