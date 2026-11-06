# cs-crew · 쇼핑몰 고객센터 에이전트 팀 랩

「LLM 에이전트 보안 실전」 강의 랩입니다. 상담원 1명에서 시작해 7명 팀까지 직접 만들고, 기능이 늘 때마다 생기는 사고를 내 보고 막습니다.

- 모든 값은 가짜입니다(`*.example`, `FAKE-…`). 화면은 127.0.0.1에서만 뜹니다.
- 공격은 이 랩에만 보냅니다. 남의 서비스에 쓰지 않습니다.

## 3분 시작

```bash
make setup      # 처음 한 번: 가상환경·의존성·.env·가게 데이터
make run        # 화면: http://127.0.0.1:8000
make next       # 다음 수업 카드
```

make가 없으면(Windows 등) 같은 이름으로 `python -m crew <명령>`을 씁니다. 예: `.venv\Scripts\python -m crew next`

## 수업 한 편 따라 하기: 네 줄이면 됩니다

```bash
make lesson L=2-4         # 1. 카드 읽기: 무엇을, 어디를, 어떻게
make check L=2-4          # 2. 레드인 것 보기: '기대' 문장이 할 일을 알려 줍니다
#   (고칠 곳은 코드에 ✏️ 2-4 로 표시돼 있습니다)
make check L=2-4          # 3. 고친 뒤 다시: ✔ 그린이면 완료
make redteam S=1          # 4. 눈으로: 사고 → 막힘(어느 층이 막았나)
```

막히면 `make solution L=2-4`로 정답과의 차이를 봅니다. `make apply-solution L=2-4`는 정답으로 덮어씁니다(내 파일은 `data/backup/`에 남습니다). `make status`로 진도와 OWASP 지도를 봅니다.

## 실행 방식 (`.env`의 `LLM_MODE`)

| 값 | 언제 | 비용 |
|---|---|---|
| `fake` (기본) | 키 없이 시작, `make check` | 0원 · 결과가 늘 같음 |
| `live` | 내 OpenAI 키로 진짜 모델 | 강의 전체 수 달러(작은 모델). `LAB_MAX_USD`가 넘으면 멈춤 |
| `replay` | 키 없이 강사가 녹화한 실제 OpenAI 응답 보기 | 0원 |
| `local` | OpenAI 호환 주소의 모델(LM Studio, AWS Bedrock의 `openai.gpt-oss-20b-1:0` 등) | LM Studio 0원 · Bedrock은 AWS 요금 |

`make check`는 `.env`와 상관없이 늘 `fake`로 돕니다.

`local`은 `LOCAL_BASE_URL`·`LOCAL_MODEL`·`LOCAL_API_KEY`로 OpenAI 호환 주소에 붙습니다. LM Studio는 `http://127.0.0.1:1234/v1`(키 없음), AWS Bedrock은 `https://bedrock-runtime.<region>.amazonaws.com/openai/v1`과 `openai.gpt-oss-20b-1:0`, Bedrock API 키입니다(`.env.example` 참고). gpt-oss가 답 앞에 붙이는 reasoning은 랩이 걷어 냅니다. Moderation API·openai-guardrails·Traces는 OpenAI 전용이라 `LLM_MODE=live`와 OpenAI 키가 있어야 합니다. 이 강의의 진짜 모델 실측은 AWS Bedrock의 gpt-oss-20b로 했습니다(2026-11-06).

## 화면

| 주소 | 누가 | 무엇을 |
|---|---|---|
| `/chat` | 고객 | 상담원과 대화. 오른쪽 위에서 alice·bob·chloe 등으로 바꿉니다 |
| `/inbox` | 메일 문의 | 메일 본문을 에이전트에게 맡깁니다(간접 인젝션이 들어오는 길) |
| `/staff` | 직원(dave·carol) | 문의·승인·메모·리포트. 🔒는 그 수업에서 열립니다 |
| `/ops` | 운영자 | 조직도, 행동 타임라인, 요금 미터, 킬 스위치, 레드팀 콘솔, OWASP 지도 |

## 그 밖의 명령

| 명령 | 무엇을 |
|---|---|
| `make import CSV=samples/` | 내 CSV(products·orders·docs)를 가게 DB에 넣기(13-3) |
| `make redteam S=--ci` | 레드팀 게이트: 사고·오탐이 있으면 실패로 끝남(13-2, `.github/workflows/redteam.yml`) |
| `python -m crew mcp-pins` | 택배사 MCP 도구 설명의 해시(10-4 고정용) |
| `make goto L=9-4 AT=done` | 그 수업 완료 지점으로 이동(내 파일은 `data/backup/`) |

- 택배사 MCP 서버(`carrier-mcp/server.py`)는 stdio 하위 프로세스로 뜹니다. 네트워크를 쓰지 않습니다.
- 리포트 담당의 코드는 Docker가 있고 `python:3.12-slim` 이미지가 이미 있으면 컨테이너에서, 아니면 제한 프로세스 모드로 돕니다(`CREW_SANDBOX=auto|docker|process`). 이미지를 자동으로 내려받지 않습니다.
- `.pre-commit-config.yaml`: `.env`와 `sk-` 키 모양 글이 커밋에 들어가지 않게 막는 훅(1-4).

## 내가 고치는 곳

```
crew/agents/   에이전트 정의
crew/tools/    도구
crew/guards/   가드레일·마스킹 (섹션 3부터)
```

나머지(`crew/web`, `crew/db`, `crew/runtime`)는 고치지 않습니다.

## 가게 데이터

`data/cs_crew.db`(SQLite)에 들어 있고, `make seed`로 언제든 처음 상태로 돌아갑니다.

| 종류 | 고정 값 |
|---|---|
| 매장 | shop-a, shop-b |
| 고객 | alice·bob(shop-a), chloe(shop-b) |
| 직원 | dave(shop-a), carol(shop-b), gina(shop-a) |
| 매니저 | erin(shop-a), frank(shop-b) |
| 주문 | 1001(alice, 배송 완료), 1002(alice, 출고 전), 2001(bob), 3001(chloe) |

## 수업마다 시작 지점

git 없이 수업 지점을 오갑니다. 뒤처지면 `make goto L=2-4`로 그 수업 시작 지점에서 다시 시작하고, `make goto L=2-4 AT=done`으로 완료 지점을 봅니다. 내 파일은 `data/backup/`에 남습니다.

이 폴더는 지금 **2-4 수업 시작 지점**입니다. 그래서 `make check L=2-4`와 `L=2-5`가 레드인 것이 정상입니다.
