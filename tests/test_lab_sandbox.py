"""샌드박스 완성본(crew/runtime/sandbox.py)의 컨테이너 명령. 수업과 상관없이 늘 그린이어야 한다.

시험은 Docker를 돌리지 않는다(제한 프로세스 모드). 여기서는 docker run 명령의 모양만 본다.
"""
from pathlib import Path

from crew.runtime import sandbox


def test_컨테이너_명령의_모양():
    policy = sandbox.Policy(run_as="1234:1234")
    cmd = sandbox.docker_command(Path("/tmp/sbx/work"), Path("/tmp/sbx/main.py"), "/tmp/sbx/report.db", policy,
                                 {"work": "/work"}, 5)
    joined = " ".join(cmd)
    assert cmd[:2] == ["docker", "run"] and "--rm" in cmd
    assert cmd[cmd.index("-w") + 1] == "/work", "작업 폴더(-w /work)에서 돈다"
    assert "/tmp/sbx/work:/work:rw" in cmd, "작업 폴더를 /work에 붙인다"
    assert "/tmp/sbx/report.db:/data/report.db:ro" in cmd, "DB 사본은 읽기 전용으로 붙인다"
    assert cmd[cmd.index("--user") + 1] == "1234:1234", "Policy.run_as를 따른다"
    assert cmd[cmd.index("--network") + 1] == "none" and "--read-only" in cmd
    assert "timeout -s KILL 5 python" in joined, "코드의 시간 제한은 컨테이너 안에서 잰다"
    nobody = sandbox.docker_command(Path("w"), Path("m"), "d", sandbox.Policy(), {}, 5)
    assert nobody[nobody.index("--user") + 1] == "65534:65534", "nobody는 65534:65534"


def test_auto는_컨테이너가_없으면_제한_프로세스(monkeypatch):
    monkeypatch.setenv("CREW_SANDBOX", "auto")
    monkeypatch.setattr(sandbox, "_docker_ready", lambda: False)
    r = sandbox.run('print("ok")')
    assert r.ok and r.mode == "process"


def test_요청한_사람을_모르면_사본은_비어_있다():
    r = sandbox.run('show("n", q("SELECT COUNT(*) AS n FROM users"))')
    assert r.ok and r.output.splitlines()[-1] == "0", "누가 요청했는지 모르면 어느 매장 줄도 담지 않는다"
