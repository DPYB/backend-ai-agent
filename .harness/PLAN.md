# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 전체 진행 계획 (사용자 승인 범위 총괄 로드맵)


### 📌 Milestone 2: 토론 기억 전용 테이블 DDL 설계 및 개인화 벡터 DB 저장 연계
> **`scrap_vector`(OCR 문장 스크랩 전용)의 순수성을 보존하고, 토론 요약을 영구 자산화하기 위한 전용 테이블 구축**

- [ ] **1. 토론 기억 전용 테이블 DDL 작성 및 실행 스크립트 (`scripts/init_agent_schema.sql`, `init_agent_schema.py`)**:
  - `agent.debate_insights` 테이블 신설 (`id`, `member_id`, `session_id`, `book_title`, `persona_id`, `summary`, `embedding(768)`, `created_at`)
  - HNSW 코사인 유사도 인덱스 및 매칭 RPC 함수(`agent.match_debate_insights`) 정의
- [ ] **2. SQLAlchemy ORM 모델 및 Repository 구축 (`app/infrastructure/db/models.py`, `repository.py`)**:
  - `DebateInsight` ORM 선언 및 회원별(`member_id`) 완전 격리 벡터 검색/저장 메서드 구현
- [ ] **3. 토론 피날레 시 자동 벡터화 적재 파이프라인 연동**:
  - 토론 종료 시 생성된 `debate_summary`를 Gemini Embedding(768차원) 변환 후 `agent.debate_insights`에 자동 적재
- [ ] **4. 토론 기억 회상 도구(`search_debate_memory`) 추가 및 페르소나 연동**:
  - 다음 대화 시 사용자가 과거에 나눈 토론 통찰을 회상하여 대화에 반영하는 초개인화 도구 탑재
- [ ] **5. 단위 테스트 및 검증 (`tests/unit/test_debate_memory.py`)**:
  - 테이블 매핑, 회원 격리, 벡터 검색 정확도 100% 검증

---

### 📌 Milestone 3: 4단계 다중 방어 보안 가드레일 파이프라인 구축 (Phase 15)
> **0ms $0 비용으로 유해 발화, 무의미 입력, 프롬프트 탈취를 차단하는 다중 방어 체계**

- [ ] **1. 가드레일 도메인 모듈 신설 (`app/domain/guardrails/`)**:
  - `safety_gate.py`: 자해/자살 위기 발화 정규식(`CRISIS_KEYWORDS_PATTERN`), 도서명 예외 처리(`BOOK_TITLE_EXCLUSIONS_PATTERN`, '자살론' 등 오탐 방지), 8개 페르소나별 109 핫라인 맞춤 공감 응답 (0ms 무지연, LLM 비용 $0)
  - `input_gate.py`: 자모 난타(`ㅋㅋㅋㅋ`), 숫자 단독(`12345`), 이모지 단독(`🐱🐾`) 비정상 입력 정규식 감지 및 8개 페르소나별 즉각 안내 응답
  - `security_gate.py`: 시스템 프롬프트 유출 시도, 탈옥(Jailbreak / DAN / Ignore instructions), PII(주민등록번호 등) 사전 차단 게이트
  - `shared_rules.py`: 시스템 프롬프트 레벨 공통 가드레일 (날씨 팩트 엄수, 도서 서비스 범위 밖 질문 정중 거절, 내부 메타데이터 은폐)
- [ ] **2. API 엔드포인트(`POST /api/v1/chat`, `POST /api/v1/chat/stream`) 4단계 게이트 연동**:
  - 0차: 인증 확인 (`evaluate_auth_gate`) ➔ 1차: `evaluate_safety_gate` ➔ 2차: `evaluate_input_gate` ➔ 3차: `evaluate_security_gate`
  - 통과 시에만 LangGraph 실행 (일반/스트리밍 100% 동일 적용)
- [ ] **3. 단위 테스트 작성 및 전수 검증 (`tests/unit/test_guardrails.py`)**

---

### 📌 Milestone 4: 3대 레포(Core API + AI Agent + Frontend) 풀스택 통합 테스트 및 연동 검증
> **실제 로컬 기동 상태에서 토론 ➔ 마무리 ➔ 추천 카드 ➔ 서재 등록 화면 완벽 동작 실증**

- [ ] **1. 3대 서비스 로컬 동시 기동**:
  - `backend-core-api`: 로컬 서버 기동 (`uvicorn app.main:app --port 8080`)
  - `backend-ai-agent`: 로컬 서버 기동 (`uv run uvicorn app.main:app --port 8000`)
  - `frontend-reader-web`: Vite 개발 서버 기동 (`npm run dev`)
- [ ] **2. 실화면 E2E 시나리오 검증**:
  - 프론트엔드 브라우저 접속 후 토론 모드 진입 (이동진/설민석/오은영/강형욱)
  - 1단계: 자유 토론 질의응답 (2~3회 사유 교환)
  - 2단계: UI의 `[🏁 토론 마무리]` 버튼 클릭
  - 3단계: AI 토론자의 피날레 총평 + 토론 요약 리포트 + 연계 추천 도서 카드 노출 확인
  - 4단계: 추천 도서 카드의 `[등록 ➔]` 클릭 시 `/register` 폼에 도서 정보 100% 자동 채움 확인 및 내 서재 등록 완료 확인
