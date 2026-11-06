# 강사용 · 랩 수업 만드는 규칙

수강생에게는 보이지 않아도 되는 문서. 섹션을 더할 때 이 규칙을 지킨다. 기준 문서: `../../README.md`(기획서 7절 커리큘럼), `../../랩-설계.md`.

## 1. 폴더의 두 종류

| 종류 | 폴더 | 규칙 |
|---|---|---|
| 수강생이 고치는 곳 | `crew/agents/`, `crew/tools/`, `crew/guards/` | 수업마다 바뀐다. 처음 모습은 `course/base/`, 각 수업의 완료 모습은 `solutions/sN-MM/`(바뀐 파일 **전체**를 넣는다) |
| 완성본으로 주는 곳 | `crew/runtime/`, `crew/web/`, `crew/db/`, `crew/redteam.py`, `crew/team.py`의 SLOTS 등 | **처음부터 최종 모습**으로 둔다. 학생 코드가 아직 없으면 조용히 쉬거나 🔒로 보인다(예: 승인 대기열은 approvals 테이블이 비면 "6-1에서 만듭니다") |

- `make goto L=x`는 `course/base`를 깔고 x 이전 수업들의 `solutions/`를 순서대로 덮는다.
- 따라서 `course/base/`는 강의 시작 상태다(1-5 상담원 + 2-1 `get_order`까지 들어 있음). **base는 고치지 않는다.** 바꿀 일이 생기면 그 내용을 해당 수업의 solution으로 넣는다.
- 지금 작업 폴더(`crew/agents` 등)는 수업 시작 지점 상태로 둔다. 기본값은 `make goto L=2-4`의 결과다. 작업이 끝나면 반드시 `python -m crew goto 2-4`로 되돌린다.
- 학생 코드가 import하는 이름은 미래 수업에서도 깨지지 않게 둔다. 예: `crew.team.entry_agent()`는 늘 있다. team.py의 팀 조립 함수는 학생 폴더(`crew/agents/team_build.py` 등)에 두고 team.py는 그것을 부른다.

## 2. 수업 하나에 필요한 것

| 파일 | 언제 |
|---|---|
| `lessons/sN-MM.md` 카드 | 모든 수업. 형식은 `lessons/s2-04.md`를 따른다: 제목 줄, ⏱·고칠 파일 수·바뀌는 줄, 따라 하기(번호), 확인, 막히면, 기억할 한 줄 |
| `tests/test_sN_MM_*.py` | 코드를 고치는 수업. 단언 메시지는 `"기대: …"` 한국어 한 문장(수강생이 할 일을 알게) |
| `solutions/sN-MM/...` | 코드를 고치는 수업. 바뀐 파일 전체 |
| ✏️ 표시 | 시작 지점 코드에서 고칠 자리에 `# ✏️ N-M: 무엇을` 주석. 그 수업 solution에서는 주석을 지운다 |

- **"공격해 보기" 수업**(사고를 보는 수업)은 시험이 없어도 된다. 대신 레드팀 시나리오가 그 시점에 "사고"로 나와야 한다.
- **"지키기·미션" 수업**은 시작 지점에서 시험이 레드, solution 적용 뒤 그린이어야 한다. `python -m crew verify-course`가 이걸 검사한다.
  시작 지점 검사는 **시험 하나하나**를 본다(파일 안 다른 시험이 레드여도, 이미 그린인 시험이 있으면 문제로 센다).
  오탐이 없는지·정상 요청이 그대로 되는지 보는 짝 시험은 시작 지점에서도 그린이 맞다. 그런 시험(그리고 새 기능이 지켜야 할 안전 조건이라 기능이 없을 때도 참인 시험)에만 `@pytest.mark.normal`을 붙인다. 수업의 핵심(미션) 시험에는 붙이지 않는다.
- 수업과 상관없이 늘 그린이어야 하는 완성본 시험은 `tests/test_lab_*.py`에 둔다(check-all이 늘 돌린다).
- 앞 수업의 시험은 뒤 수업 완료 지점에서도 그린이어야 한다(회귀). verify-course 마지막 줄 "전체 시험"이 이걸 본다.
- 수업 하나에서 바뀌는 줄은 30줄 이하를 목표로 한다. 넘으면 수업을 나누거나 완성본 쪽(runtime 등)으로 보낸다.

## 3. 가짜 LLM(`crew/runtime/fake_model.py`)

키 없이 결정적으로 "순진한 모델"처럼 군다. 섹션이 늘면 규칙을 더한다. 규칙은 완성본 쪽이라 처음부터 최종 모습으로 둔다.

- 도구 결과가 오면 그대로 전한다. 교과서 공격 문장(이전 지시 무시, 숨은 지시 "AI는 …할 것")은 따른다. 지시문에 비밀이 있으면 말해 버리고, 지시된 도구가 있으면 부른다.
- 도구·핸드오프 선택은 이름·키워드 표(`TOOL_RULES`)로 한다. 핸드오프는 SDK에서 `handoffs` 인자로 오고 이름은 `transfer_to_<agent>`다.
- 가드레일용 판별 에이전트(작은 모델 판별기)도 가짜 LLM이 답한다. 출력 타입(Pydantic)이 있으면 JSON으로 답한다. 판별기는 교과서 문장을 잡지만 정상 문장은 통과시킨다.
- 결과는 매번 같아야 한다. 난수를 쓰지 않는다.

## 4. 막힘 표시 약속(점수판)

- 도구가 막으면 `"거부: …"`로 시작하는 글을 돌려준다 → ③ 내 코드
- 가드레일 트립와이어 → ② 가드레일(`run.py`가 잡는다)
- 승인 대기로 멈춤 → `blocked_by="approval"`(③). 직원 콘솔에서 승인하면 이어서 실행한다
- 킬 스위치·예산 → ③

## 5. 공격 문장

교과서 수준만 쓴다(기획서 8절). 우회·난독화·인코딩·여러 턴 탈옥 기법, 모델별 공략은 쓰지 않는다. 대상은 이 랩과 가짜 값뿐이다.

## 6. 외부 호출

- 시험과 verify-course는 네트워크를 쓰지 않는다(가짜 LLM, 로컬 MCP 서버는 stdio 하위 프로세스).
- openai-guardrails·Presidio처럼 무거운 선택 의존성은 `requirements-extra.txt`에 둔다. 랩 코드는 없을 때도 돈다(가벼운 대체 구현). 수업 카드에 "설치하면 이렇게 바뀐다"를 적는다.
- 샌드박스(9장)는 Docker가 있으면 컨테이너, 없으면 제한 프로세스 모드(하위 프로세스 + 시간 제한 + 임시 폴더 + 네트워크 차단 시늉)로 돈다. 시험은 제한 프로세스 모드로 돈다.

## 7. 끝내기 전 확인

```bash
.venv/bin/python -m crew sync-lessons       # 기획서 7절 → course/lessons.yaml (번호·제목이 바뀌었을 때)
.venv/bin/python -m crew verify-course      # 모든 수업: 시작 레드 → 정답 그린, 전체 시험 그린
.venv/bin/python -m crew goto 2-4           # 작업 폴더를 배포 상태로 되돌리기
.venv/bin/python -m crew check-all          # 2-4 시작 지점에서 마친 수업(2-3까지) 시험이 모두 그린
rm -f data/progress.json                    # 배포 상태는 진도 없음
```

## 8. 섹션 8~13 완성본 조각(학생 코드가 없으면 조용히 쉰다)

| 조각 | 파일 | 학생 쪽 이름(plug) |
|---|---|---|
| 메모 검토 버튼 | `crew/web/app.py` `/api/memories/…` | `crew.guards.memory.review`·`rollback` (8-4) |
| 코드 실행기 | `crew/runtime/sandbox.py` (`run_in_place` 9-1 사고용, `run(code, Policy)` 9-4: DB 사본은 요청한 사람 매장 줄만, `docker_command()`) | `crew.tools.reports.POLICY` |
| MCP 잇기 | `crew/runtime/mcp_link.py` (하위 프로세스는 `call_tool` 때만 띄움, 목록은 같은 설정이면 다시 씀, `mcp_block:<서버>`), `carrier-mcp/server.py` | `crew.tools.carrier.carrier_server` |
| 담당 사이 메시지 길 | `crew/runtime/bus.py` (`agent_tool`) | `crew.guards.messages`(11-4), `crew.guards.breaker`(11-5) |
| 감시자 순찰 | `crew/runtime/watch.py` (요청마다 `patrol()`. 12-3부터 완성본 규칙도: 고객 신고·담당별 속도 제한·새/전이 권한·에이전트 간 권한 상승) | `crew.guards.watch.anomalies`(12-3), `crew.guards.killswitch.respond`(12-4) |
| 고객 신고 버튼 | `crew/web/app.py` `/api/report` → `watch.report()` | 12-3(`anomalies`가 있으면 열림) |
| 멈춤·요금 | `audit.py`(`pause:<담당>`), `run.py`(`over_budget`) | `crew.guards.killswitch` |
| 랩 시계 | `crew/runtime/clock.py` (lab_flags `clock`) | 브레이커·감시자·승인·브로커·위임 토큰(7-3)이 쓴다 |

- 지금 요청한 사람은 `crew.runtime.audit.CURRENT_USER`(게이트웨이가 넣는다)에 있다. 샌드박스 사본의 매장을 정한다. 시험이 도구를 직접 부를 때는 이것도 넣는다.
- 시험이 학생 이름을 쓸 때는 `crew.runtime.plug.need(모듈, 이름, "기대 문장")`으로 꺼낸다. 시작 지점에서 스택 대신 "기대: …"가 보인다.
- 레드팀 시나리오 칸: `steps`, `flags`, `repeat`, `incident_files`, `needs_mcp`, `needs_module`(코드 없는 공격해 보기 수업의 시나리오를 그 수업부터 열 때: 바로 앞 수업의 학생 파일), `layer`(조용히 막혔을 때의 층 이름). `redteam.py` 머리말 참고.
- 레드팀은 시나리오마다 업무 데이터·요금(usage)·택배사 청구를 되돌리고, 감시자가 그 뒤 기록부터 보게 한다(lab_flags `watch_since`). 그래서 `--ci`를 거듭 돌려도 결과가 같다.
- 가짜 LLM의 호출 번호는 실행마다 다르다(대화 기록 속 옛 번호와 겹치지 않게). 답의 내용은 결정적이다.
