"""12-5 레드팀 콘솔 20개 모두 그린: 사고 0, 오탐 0, 잠김 0."""
from crew.redteam import load, run_scenario


def test_시나리오_20개가_모두_막히고_오탐이_없다():
    bad = []
    for sc in load():
        r = run_scenario(sc)
        if r["state"] != "blocked" or r.get("false_positive"):
            bad.append(f"{sc['id']}번 {sc['title']}: {r['state']}{' · 오탐' if r.get('false_positive') else ''}")
    assert not bad, "기대: 20개 모두 '막힘'이고 오탐 확인용 정상 문의도 통과한다 → " + " / ".join(bad)
