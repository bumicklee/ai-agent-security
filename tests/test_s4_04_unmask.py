"""4-4 Presidio로 보강(선택)하고 응답에서 되돌리기."""
import pytest
from crew.runtime.run import ask
from crew.runtime.plug import need


def test_자리표마다_짝이_남는다():
    mask = need("crew.guards.pii", "mask", "개인정보 가리기 mask()를 만든다")

    text, mapping = mask("전화 010-0000-1234, 메일 me@example.com")
    assert len(mapping) == 2, "기대: 가린 값 2개의 짝(자리표 → 원래 값)이 남는다"
    assert "010-0000-1234" in mapping.values() and "me@example.com" in mapping.values()
    assert all(k in text for k in mapping), "기대: 글에는 번호 붙은 자리표([MASKED:전화#1] 등)가 들어간다"


def test_내_연락처는_답에서_되돌린다():
    out = ask("alice", "연락처는 010-0000-1234 입니다. 이 번호로 연락 주세요")
    assert "010-0000-1234" in out.reply, "기대: 모델은 자리표만 봤지만, 고객에게는 원래 번호로 되돌려 보여 준다"


@pytest.mark.normal
def test_카드_번호는_되돌리지_않는다():
    out = ask("alice", "결제가 안 돼요. 카드 번호 0000-1111-2222-3333 이에요")
    assert "1111-2222" not in out.reply and "[MASKED:카드]" in out.reply, "기대: 카드·주민번호는 답에서도 가린 채로 둔다"
