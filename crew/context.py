"""누가 묻고 있나. 에이전트와 도구는 이 값을 `ctx.context`로 받는다.

모델은 이 값을 보지 못한다. 도구 인자에도 넣지 않는다(2-4에서 이유를 본다).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from crew.db import session


@dataclass(frozen=True)
class User:
    id: str
    store_id: str
    role: str  # customer | staff | manager
    name: str

    @property
    def is_staff(self) -> bool:
        return self.role in ("staff", "manager")


@dataclass
class CrewContext:
    user: User
    run_id: str = ""
    notes: list[str] = field(default_factory=list)  # 도구·가드레일이 남기는 메모(점수판용)
    channel: str = "chat"            # chat | email | staff(직원 대신 처리, 7-1)
    acting_for: str | None = None    # 직원이 대신 처리할 때 고객 id
    delegation: str | None = None    # 위임 토큰 번호(7-3). 모델은 보지 못한다
    budget: dict = field(default_factory=dict)  # 한 요청 안의 담당 호출·재시도 횟수(11-5)
    session: str | None = None       # 대화 기록(SQLiteSession) 이름. 승인 뒤 이어서 실행할 때도 같은 기록에 잇는다

    def to_json(self) -> dict:
        """승인 대기(6-1) 때 RunState와 함께 저장한다. 사용자 객체 대신 id만 남긴다."""
        return {"user": self.user.id, "run_id": self.run_id, "channel": self.channel,
                "acting_for": self.acting_for, "delegation": self.delegation, "session": self.session}

    @classmethod
    def from_json(cls, data: dict) -> "CrewContext":
        return cls(user=load_user(data["user"]), run_id=data.get("run_id", ""), channel=data.get("channel", "chat"),
                   acting_for=data.get("acting_for"), delegation=data.get("delegation"), session=data.get("session"))


def load_user(user_id: str) -> User:
    with session() as db:
        row = db.execute("SELECT id, store_id, role, name FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise KeyError(f"없는 사용자: {user_id}")
    return User(row["id"], row["store_id"], row["role"], row["name"])


def list_login_users() -> list[User]:
    """화면의 로그인 선택 상자(가짜 로그인). 고정 사용자만 보인다."""
    with session() as db:
        rows = db.execute("SELECT id, store_id, role, name FROM users WHERE id NOT LIKE 'cust%' ORDER BY role, id").fetchall()
    return [User(r["id"], r["store_id"], r["role"], r["name"]) for r in rows]
