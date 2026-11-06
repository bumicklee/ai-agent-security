"""설정. .env 파일과 환경 변수에서 읽는다(환경 변수가 이긴다)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    llm_mode: str
    model: str
    local_base_url: str
    local_model: str
    max_usd: float
    price_in: float
    price_out: float
    tracing: bool
    db_path: Path
    sessions_path: Path


def get_settings() -> Settings:
    _load_dotenv()
    e = os.environ.get
    return Settings(
        llm_mode=e("LLM_MODE", "fake"),
        model=e("CREW_MODEL", "gpt-5-mini"),
        local_base_url=e("LOCAL_BASE_URL", "http://127.0.0.1:1234/v1"),
        local_model=e("LOCAL_MODEL", "local-model"),
        max_usd=float(e("LAB_MAX_USD", "1.00")),
        price_in=float(e("CREW_PRICE_IN", "0.25")),
        price_out=float(e("CREW_PRICE_OUT", "2.00")),
        tracing=e("CREW_TRACING", "on") == "on",
        db_path=Path(e("CREW_DB", str(DATA / "cs_crew.db"))),
        sessions_path=Path(e("CREW_SESSIONS_DB", str(DATA / "sessions.db"))),
    )
