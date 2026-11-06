"""랩 화면이 뜨는지(수업과 상관없이 늘 그린이어야 한다)."""
from fastapi.testclient import TestClient


def test_화면_네_개가_뜬다():
    from crew.web.app import app

    c = TestClient(app)
    for path in ("/chat", "/inbox", "/staff", "/ops"):
        assert c.get(path).status_code == 200, path
    r = c.post("/api/chat", json={"text": "배송은 얼마나 걸려요?"})
    assert r.status_code == 200 and "1~3일" in r.json()["reply"]


def test_킬_스위치():
    from crew.web.app import app

    c = TestClient(app)
    c.post("/api/kill", json={"on": True})
    assert c.post("/api/chat", json={"text": "안녕하세요"}).json()["blocked_by"] == "switch"
    c.post("/api/kill", json={"on": False})


def test_운영_화면_버튼():
    from crew.web.app import app

    c = TestClient(app)
    c.cookies.set("crew_user", "erin")
    r = c.get("/ops")
    assert r.status_code == 200 and "행동 기록 체인" in r.text
    assert c.post("/api/ops/watchdog").status_code == 200
