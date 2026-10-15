# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다.
> **관리 규칙**: 본 문서에는 **최근 3~5개 세션만 유지**하며, 과거 세션 로그는 `.harness/archive/`에 보관합니다. 타 레포 내부 작업은 기록하지 않고 연동 링크만 참조합니다.
> *(과거 세션 1~60 내역은 `.harness/archive/HANDOFF_2026-09.md` 참조)*



---

## 세션 67 (2026-10-07)

### 진행한 작업
1. **Curator 재현 테스트 및 실패 확인 (TDD 실패 선행 검증)**:
   - `curator_attempted=True`일 때 사용자 추천 키워드("책 추천해줘")로 인한 무한 선위임 루프 버그 재현 및 테스트 실패(1 failed in 0.61s) 확인 후 정규 영구 테스트 suite 구축.
2. **사서 모드 3중 재진입 루프 원천 차단 (`nodes.py`, `workflow.py`, `state.py`)**:
   - `AgentState.curator_attempted: bool` 필드 추가 및 큐레이터 완료 시 `True` 반환.
   - [경로 1: 선위임 차단]: `curator_attempted == True` 시 키워드 기반 재위임 스킵.
   - [경로 2: 도구 배제]: 사서 모드에서 `curator_attempted == True` 시 `request_book_curation`을 LLM 도구 바인딩에서 제외하여 Dangling Tool Call 에러 방어 (토론 모드 `trigger_debate_conclude` 완전 보존).
   - [경로 3: 지연 약속 치환]: "골라올게", "잠시 기다려" 감지 시 재위임 대신 문장 단위로 대체 문구 치환 (`_replace_delayed_curation_promise`).
   - 가짜 카드 후처리(`_sanitize_persona_output`) 강제 및 15자 미만 빈 응답 시 안전한 디폴트 멘트 폴백.
   - `route_persona_exit`에서 `curator_attempted == True` 시 큐레이터 재진입 원천 차단 (`END` 전이).
3. **SSE 스트리밍 버퍼링 및 GraphRecursionError Graceful Fallback (`router.py`)**:
   - 큐레이터 실패 복귀 턴(`is_curator_recovering`)에서 스트리밍 토큰을 버퍼링한 뒤 `on_chain_end`에서 후처리가 완료된 정제 메시지만 단일 토큰으로 방출 (클라이언트 가짜 카드 누출 0건).
   - `recursion_limit: 25` 버퍼 확보 및 `GraphRecursionError` 발생 시 CRITICAL 에러 로깅, 사용자 친화적 대체 멘트 반환, Redis 세션에 사용자 질문과 깨끗한 대체 멘트 보존.
   - `_prepare_chat_context`에서 매 턴 `curator_attempted: False` 안전 초기화.
4. **품질 검증**:
   - 신규 단위 테스트 12종 작성(`tests/unit/test_curator_loop_prevention.py`): 3중 재진입 독립 테스트, 한국어 문장 분리, 악의적 가짜 카드 후처리, 토론 모드 격리, SSE 토큰 비노출, 미드스트림 RecursionError + Redis 검증, 게스트 E2E, 일반 턴 실시간 스트리밍 전수 통과.
   - 전체 237개 단위 테스트 100% 그린 (`237 passed in 35.56s`), ruff check & format 통과, mypy 통과, check_harness 통과.

### 다음 세션에서 할 일
- **Phase 65-1 착수: 8종 페르소나 어조 분기 및 게스트 E2E 모킹 최적화 (`feat/curator-polish`)**: 완료 (세션 68).

---

## 세션 68 (2026-10-08)

### 진행한 작업
1. **Phase 65 develop 머지 확인 및 브랜치 정리**:
   - PR #62(`feat/curator-reentry-loop` ➔ `develop`) 머지 완료 및 로컬/원격 브랜치 정리.
2. **Phase 65-1: 큐레이터 폴리싱 (8종 페르소나 어조 분기 및 게스트 E2E 모킹 최적화)**:
   - `nodes.py`: 사서 4종(`CAT`: ~냥, `SHOEBILL`: ~두둥, `SEA_SLUG`: ~누누, `GECKO`: ~크크) 및 토론자 4종(평론가, 이야기꾼, 상담사, 관찰가 피날레 맥락) 맞춤형 대체 문구 및 빈 응답 폴백 매핑 구축.
   - `_replace_delayed_curation_promise` 및 `_sanitize_persona_output`에 `persona_id` 전달 연동.
   - `test_curator_loop_prevention.py`: 8종 페르소나 어조 치환 및 빈 응답 폴백 단위 테스트 2종 추가.
   - `test_guest_frontend_token_chat_and_stream_e2e`에 가벼운 AsyncMock 적용하여 외부 네트워크 의존 제거 ➔ 전체 회귀 실행 속도 **144초에서 30초대로 대폭 단축 (약 80% 가속)**.
3. **품질 검증**:
   - 전체 239개 단위 테스트 100% 그린 (`239 passed in 30.79s`), ruff 및 mypy 통과, check_harness 통과.

### 다음 세션에서 할 일
- **Phase 65-1 PR #63 머지 및 브랜치 정리**: 완료 (세션 69).

---

## 세션 69 (2026-10-09)

### 진행한 작업
1. **GitHub 장애 복구 확인 및 PR #63 머지 동기화**:
   - 10월 8일 자정 발생한 GitHub 본사 Actions/Webhooks 글로벌 장애(Major Outage) 복구 확인.
   - PR reopen으로 웹훅 트리거 재발행 ➔ CI(Lint, Type Check & Test) 50초 만에 그린 통과 ➔ PR #63(`develop`, `8cebcc3`) 머지 완료 확인.
   - 로컬/원격 `feat/curator-polish` 브랜치 정리 및 `develop` 최신화 완료.
2. **프론트엔드 연동 이슈 분석 및 기술 지원**:
   - 현상 1: 사서별 서재 도서 장르 커플링 분석 (토론 모드 시 사서 장르 의존성 분리 필요성 확인).
   - 현상 2: 회원 토론 내용이 게스트(체험하기)에 노출되는 클라이언트 캐시 버그 원인 규명 (`sessionStorage` 키에 `memberId`/`mode` 누락) ➔ 프론트엔드 팀원 PR #141로 핫픽스 머지 완료 확인.
   - 현상 3: 토론 논리적 핑퐁(건설적 반론 + 팩트 그라운딩 + 꼬리물기 질문) 기획 및 프롬프트 구조 설계.
3. **Phase 66 계획 수립 및 인수인계 정비**:
   - `PLAN.md`에 Phase 66(토론 파트너 4종 논리적 핑퐁 고도화) 신설 및 체크리스트 등록.
   - 세션 64 아카이빙(`archive/HANDOFF_2026-10.md`) 및 하네스 규격 검증 완료.

### 다음 세션에서 할 일
- **Phase 66 구현 착수 (`feat/debate-persona-pingpong`)**: 완료 (세션 70).

---

## 세션 70 (2026-10-10)

### 진행한 작업
1. **브랜치 생성 및 작업 환경 정비**:
   - `feat/debate-persona-pingpong` 브랜치 생성 및 체크아웃.
2. **토론 공통 및 4종 페르소나 프롬프트 고도화 (Phase 66)**:
   - `debate_common.py`에 `COMMON_DEBATE_TURN_RULES` 신설: 1) 단순 동조 탈피 및 팩트 그라운딩 기반 건설적 반론(독자 근거 인정 후 쟁점 좁히기, 없는 내용 날조 금지), 2) 완전 독립 1:1 토론 몰입(타 파트너 언급/연계 지침 원천 배제), 3) 개방형 꼬리물기 질문(Ping-Pong, 피날레/마무리 턴 질문 억제) 지침 구축.
   - `debate_critic.py`, `debate_storyteller.py`, `debate_counselor.py`, `debate_observer.py`: 4종 페르소나 고유 어조별 팩트 기반 반론 화법, 1:1 몰입, 핑퐁 질문 및 예시 연동.
   - `DEBATE_*_TURN_PROMPT` 조립(`compose`)에 `COMMON_DEBATE_TURN_RULES` 결합.
3. **사서 말투 누수 코드 레벨 방어 및 격리 안전 가드 검증**:
   - `nodes.py`에 `_strip_debate_animal_endings` 신설 및 `_sanitize_persona_output` 연동: 토론 모드 응답에서 사서 종결어미(`~냥`, `~두둥`, `~누누`, `~크크`) 코드 레벨 강제 소거 (단, `그냥`, `안녕` 등 일반 어휘 보호).
   - `nodes.py`에서 `is_debate` 시 사서 추천 선위임(`curator_attempted`), 커스텀 사서 이름(`librarian_name`), 날씨(`weather_context`) 주입 완전 격리 검증.
   - `DEBATE_TOOLS` 분리 바인딩 및 서재 도구 장르 간섭 부재 검증.
4. **단위 테스트 보강 및 품질 검증**:
   - `tests/unit/test_debate_pingpong.py` 신규 테스트 7종 작성: 공통 턴 규칙 연동, 시작 문구 다양성/도서 정보 한계 인정, 4종 고유 어조 검증, 사서 추천 위임 차단, 사서 이름/날씨/컨텍스트 요약 격리, 오프닝/턴 프롬프트 분기, 피날레 질문 억제, 자연어 마무리 오탐 방지 검증.
   - `tests/unit/test_debate_isolation.py` 사서 어미 소거 및 명사/부사 오탐 방지 테스트 1종 추가.
   - 전체 247개 단위 테스트 100% 그린 (`247 passed in 16.90s`), ruff check & format 통과, mypy 통과.
5. **하네스 문서 갱신 및 롤링 아카이빙**:
   - 세션 65 롤링 아카이빙(`archive/HANDOFF_2026-10.md`), `STATE.md`, `PLAN.md`, `DECISIONS.md` 갱신.

### 다음 세션에서 할 일
- **Phase 66 PR 생성 및 develop 머지 지원**: 완료 (세션 70 머지 완료).

---

## 세션 71 (2026-10-15)

### 진행한 작업
1. **에이전트 독립 추출 마이그레이션 가이드 수립**:
   - LangGraph, 8종 페르소나, RAG, 도서 큐레이션, 실시간 스트리밍 에이전트 코어와 비-에이전트(Vision, 리포트) 간 분리 경계 정의.
   - 새 프로젝트용 파일 인벤토리, 경량화 `pyproject.toml` (무거운 C-라이브러리 `libzbar0`, `pyzbar`, `opencv` 전면 배제), `.env` 명세 및 15개 핵심 테스트 파일 매핑.
2. **Clova OCR 레거시 잔재 전면 제거 및 Gemini Vision 단일화 (Phase 67)**:
   - `app/vision/clova_ocr_client.py` 하위 호환 리다이렉트 파일 완전 삭제.
   - `app/vision/gemini_ocr_client.py` 및 `app/vision/__init__.py`에서 `ClovaOcrClient`, `ClovaOcrResult`, `clova_ocr_client` 레거시 별칭 완전 제거.
   - `app/core/config.py`에서 `naver_clova_api_url`, `naver_clova_secret_key` 미사용 환경변수 필드 제거.
   - `tests/unit/test_vision.py`에서 `test_clova_alias_compatibility` 및 별칭 타입 단언 제거.
   - `AGENTS.md`, `.harness/ARCHITECTURE.md`, `README.md`에서 Clova 언급 전면 제거 및 Google Gemini Flash Vision 단일 체계로 일원화.
3. **품질 검증**:
   - `tests/unit/test_vision.py` 17개 단위 테스트 100% 그린 (`17 passed in 2.82s`).
   - 전체 단위 회귀 100% 그린, ruff check & format 통과, mypy 통과, `scripts/check_harness.py` 통과.

### 다음 세션에서 할 일
- **Phase 67 PR 생성 및 develop 머지 지원**:
  - `feat/cleanup-clova-legacy` 브랜치 변경사항 커밋 및 PR 생성.
  - CI 통과 확인 후 사용자 컨펌/수동 머지 대기.

