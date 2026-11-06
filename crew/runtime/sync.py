"""동기 함수(ask·act·decide)가 쓰는 이벤트 루프.

asyncio.run()은 부를 때마다 루프를 새로 만들고 닫는다. 진짜 모델 클라이언트(OpenAI·Bedrock)는 처음 쓴 루프에 묶여 있어서,
한 프로세스에서 ask()를 두 번 부르면 두 번째에 "Event loop is closed"가 난다(2026-11-06 발견). 그래서 루프를 닫지 않고 다시 쓴다.

- 스레드마다 루프 하나: 화면(FastAPI)의 동기 엔드포인트(레드팀 버튼 등)는 스레드 풀에서 돈다. 두 스레드가 루프 하나를
  같이 돌리면 "This event loop is already running"이 난다. 모델 클라이언트도 루프마다 따로다(crew/runtime/llm.py).
- 이미 루프가 도는 스레드(async 함수 안)에서 부르면 그 루프를 막을 수 없으니 별도 스레드의 루프에서 돌린다.
"""
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

_local = threading.local()
_helper = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crew-sync")


def _thread_loop():
    loop = getattr(_local, "loop", None)
    if loop is None or loop.is_closed():
        loop = _local.loop = asyncio.new_event_loop()
    return loop


def run_sync(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _thread_loop().run_until_complete(coro)
    return _helper.submit(lambda: _thread_loop().run_until_complete(coro)).result()
