# cs-crew 명령. make가 없으면 같은 이름으로 `python -m crew <명령>`을 쓴다(Windows 등).
# 수업 번호는 L=2-4 처럼 넘긴다.
PY := .venv/bin/python
ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python
endif

.PHONY: setup seed run next lesson check check-all status solution apply-solution redteam goto reset verify-course import live-check live-record

setup:            ## 처음 한 번: 가상환경 + 의존성 + .env + 가게 데이터
	@command -v uv >/dev/null 2>&1 && uv venv -q .venv && uv pip install -q --python $(PY) -r requirements.txt \
	  || (python3 -m venv .venv && $(PY) -m pip install -q -r requirements.txt)
	@test -f .env || cp .env.example .env
	@$(PY) -m crew seed
	@echo "준비 끝. 다음: make run (화면) / make next (다음 수업 카드)"

seed:             ## 가게 데이터를 처음 상태로
	@$(PY) -m crew seed
run:              ## 화면 띄우기 http://127.0.0.1:8000
	@$(PY) -m crew run
next:             ## 다음 수업 카드
	@$(PY) -m crew next
lesson:           ## 수업 카드: make lesson L=2-4
	@$(PY) -m crew lesson $(L)
check:            ## 수업 확인: make check L=2-4
	@$(PY) -m crew check $(L)
check-all:        ## 마친 수업 모두 다시 확인
	@$(PY) -m crew check-all
status:           ## 진도와 OWASP 지도
	@$(PY) -m crew status
solution:         ## 정답과의 차이: make solution L=2-4
	@$(PY) -m crew solution $(L)
apply-solution:   ## 정답으로 덮어쓰기: make apply-solution L=2-4
	@$(PY) -m crew apply-solution $(L)
redteam:          ## 레드팀 시나리오: make redteam (전체) / make redteam S=1 / CI: make redteam S=--ci
	@$(PY) -m crew redteam $(S)
goto:             ## 수업 시작 지점으로 이동: make goto L=5-1 (완료 지점: make goto L=5-1 AT=done)
	@$(PY) -m crew goto $(L) $(AT)
verify-course:    ## 강사용: 모든 수업이 시작=레드, 정답=그린인지
	@$(PY) -m crew verify-course
import:           ## 내 데이터 넣기: make import CSV=samples/ (products·orders·docs CSV, 13-3)
	@$(PY) -m crew import $(or $(CSV),samples)
reset: seed       ## seed와 같다

# --- 작성자용: 진짜 OpenAI 모델(TODO.md 1절). 키·비용이 들어서 수강생 수업에는 쓰지 않는다 ---
LIVE_DIR := data/live
live-check:       ## 작성자용: 진짜 OpenAI 모델로 레드팀 실행(S=번호 가능). 결과는 data/live/에 남김. 요금 차단기 LAB_MAX_USD
	@grep -q '^OPENAI_API_KEY=.' .env 2>/dev/null || test -n "$$OPENAI_API_KEY" || (echo "OPENAI_API_KEY가 없습니다(.env에 강의용 Restricted 키)"; exit 1)
	@mkdir -p $(LIVE_DIR) && f=$(LIVE_DIR)/redteam-$$(date +%Y%m%d-%H%M%S).txt && \
	  echo "LLM_MODE=live · $$(date '+%F %T') · S=$(S)" > $$f && \
	  LLM_MODE=live $(PY) -m crew redteam $(S) 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | tee -a $$f && echo "→ $$f"
live-record:      ## 작성자용: 진짜 모델 응답을 cassettes/에 녹화(LLM_MODE=record). 녹화 뒤 카세트를 한 번 훑어 가짜 값만 있는지 확인
	@grep -q '^OPENAI_API_KEY=.' .env 2>/dev/null || test -n "$$OPENAI_API_KEY" || (echo "OPENAI_API_KEY가 없습니다"; exit 1)
	@LLM_MODE=record $(PY) -m crew redteam $(S)
	@ls -la cassettes/
