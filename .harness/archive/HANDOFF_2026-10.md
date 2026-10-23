# HANDOFF_2026-10.md — 2026년 10월 세션 인수인계 아카이브

---

## 세션 61 (2026-10-01)

### 진행한 작업
1. **Google Cloud Run 프로덕션 마이그레이션**:
   - 서울 `asia-northeast3` 리전 Cloud Run 배포 완료.
   - 컨테이너 기동 시 Supabase 원격 DB DDL 안전 인터락(`ALLOW_REMOTE_MIGRATION=true`) 및 Upstash Serverless Redis(`rediss://...`) 세션 스토리지 연동.
2. **Render 배포 레거시 완전 제거**:
   - `.github/workflows/deploy.yml` 워크플로우 삭제. 불필요한 배포 훅 및 러너 낭비 차단.
3. **인프라 문서 및 환경변수 템플릿 최신화**:
   - `README.md`, `ARCHITECTURE.md`, `.env.example`, `AGENTS.md`의 배포 환경 명세를 Render에서 Cloud Run으로 정렬.

---

## 세션 62 (2026-10-01)

### 진행한 작업
1. **중앙 린터 및 멀티 서비스 CI 규격 동기화**:
   - DPYB 중앙 CI(`reusable-python-ci.yml`, `reusable-pr-lint.yml`)의 커밋/PR 컨벤션 유연화(소괄호/대괄호 scope 지원)에 맞춰 본 레포 설정 정렬.
2. **배포 정리 브랜치 점검**:
   - 로컬 `feat/cleanup-render-deploy` 브랜치 변경사항 최종 검증.

---

## 세션 63 (2026-10-02)

### 진행한 작업
1. **월간 독서 리포트 가짜 목데이터(데미안, 완독 3권 832쪽) 제거 (`app/infrastructure/core_api_client.py`)**:
   - `get_monthly_report_stats` 통신 실패 시 반환하던 하드코딩 응답을 `_empty_monthly_stats` 정적 메소드로 일원화하여 완독 0권, 0쪽의 정직한 빈 스켈레톤 반환으로 교체.
2. **독서 활동 0건 시 정직한 Empty State 반환 (`app/domain/reports/generator.py`)**:
   - `has_activity == False`일 때 억지 LLM 호출을 방지하고 사서 페르소나 어조가 적용된 시작 권유 멘트(`reader_type: "독서 시작을 기다리는 여행자"`, `recommended_books: []`) 반환.
3. **두 백엔드 서버 간 연결성 진단 헬스체크 연동 (`app/infrastructure/core_api_client.py`, `app/api/schemas.py`, `app/api/router.py`)**:
   - `CoreApiClient.ping_core_api()` 구현 및 `/api/v1/health` 응답에 `core_api_connected`, `core_api_url` 필드 추가.
4. **품질 검증 및 PR #58 반영**:
   - [PR #58](https://github.com/DPYB/backend-ai-agent/pull/58) 생성 및 CI 통과 확인. 204개 단위 테스트 100% 그린.

---

## 세션 64 (2026-10-02)

### 진행한 작업
1. **하네스 문서 비대화 및 도메인 오염 정밀 진단**:
   - `HANDOFF.md`(2,100줄), `STATE.md`(648줄), `DECISIONS.md`(51KB) 비대화 원인 규명 및 전 레포 실측.
2. **하네스 문서 슬림화 및 롤링 아카이빙**:
   - `HANDOFF.md`: 과거 세션 1~59를 `archive/HANDOFF_2026-09.md`로 분리 보관 (2,100줄 ➔ 76줄).
   - `STATE.md`: 과거 세부 diff를 `archive/STATE_2026-09.md`로 보관하고 마일스톤 스냅샷으로 정돈 (648줄 ➔ 52줄).
   - `DECISIONS.md`: [결정/이유/영향] 3단 압축 및 Superseded 링크 보존, 구체값 전량 유지 (51KB ➔ 17KB).
   - `PLAN.md`: 타 레포 태스크(Phase 50 2단계) 및 미착수 태스크(Phase 64) 제거, Phase 60으로 정돈.
3. **토큰 보호 및 전사 자동 검증 체계 구축**:
   - `scripts/check_harness.py`: 전 레포 공통 검증 도구 신설 (레포 자동 감지, 상한 검증, archive 파일명 정규식).
   - 중앙 CI(`reusable-python-ci.yml`)에 `Validate Harness Specifications` 스텝 추가 및 영구 안착.
   - `.agyignore`, `.claude/settings.json` 등록으로 archive/ 디렉토리 에이전트 읽기 차단.
   - `AGENTS.md` 규격 단일화 (최대 5세션/200줄, Phase/Session 분리, 타 레포 격리).

### 다음 세션에서 할 일
- **Phase 60 구현 (`feat/national-library-kdc-fallback`)**: KDC 부재 시 부가기호 다중 폴백 및 심리치료 철학 승격.

---

## 세션 65 (2026-10-03)

### 진행한 작업
1. **LangGraph 아키텍처 정밀 분석 및 전면 개정 (v2 리포트)**:
   - `file:line` 전수 검증 기반 아키텍처 분석 리포트 작성 (`langgraph-architecture-analysis.md`).
   - 무한 루프 과장 정정(LangGraph 기본 한도 10,007), State Race Condition 배제, LLM 라우터 도입 철회(순수 함수 통합 정합성).
   - Worst-case Latency, 다중 인스턴스 서킷 브레이커, 간접 프롬프트 인젝션 취약점 규명.
2. **도구 바인딩 분리 및 `member_id` ContextVar 주입 (P1 보안 IDOR 차단 / Phase 64)**:
   - `app/core/context.py`에 `current_member_id` ContextVar 신설 및 `router.py`에서 인증된 JWT sub 설정 연동.
   - 비-테스트 환경에서 토큰 없는 `request.member_id` 신뢰 차단 (fail-closed).
   - 메모리 도구 3종(`search_scrap_memory`, `search_debate_memory`, `search_my_library`) 시그니처에서 `member_id` 인자 완전 제거 및 ContextVar에서 직접 조회. 미인증 시 fail-closed 거부 반환.
   - `nodes.py:710`의 `system_prompt` 내 `member_id` UUID 노출 영구 제거.
   - 사서 모드(`LIBRARIAN_TOOLS`)와 토론 모드(`DEBATE_TOOLS`) 도구 분리 바인딩 (`nodes.py`, `tools.py`).
3. **게스트 `GUEST_MEMBER_ID` 매핑 및 요청 바디 ID 완전 무시 (보안 테스트 보강)**:
   - `app/core/config.py`에 `guest_member_id`(`00000000-0000-0000-0000-000000000003`) 정의하여 코어 API 공용 방 규격과 일치.
   - `router.py`에서 서명 검증된 JWT의 `sub/role`이 게스트일 때 `current_member_id`에 `settings.guest_member_id` 주입, 인증 요청 시 바디의 `request.member_id` 완전 무시.
   - 도구 3종(`rag_tool`, `my_library_tool`, `debate_memory_tool`)의 `startswith("guest-")` 거부 제거, `None`일 때 fail-closed 유지.
   - 게스트는 conclude 시 토론 인사이트 DB 저장을 건너뛰도록 가드 보강.
   - 보안 테스트 4종 추가, 전체 219개 단위 테스트 100% 그린 (`219 passed in 9.97s`).

---

## 세션 66 (2026-10-05)

### 진행한 작업
1. **게스트 복합 세션 ID 422 Unprocessable Entity 긴급 해결 (`app/api/schemas.py`)**:
   - `SESSION_ID_REGEX = re.compile(r"^[A-Za-z0-9:_-]{1,128}$")` 정규식 검증을 최상단에 배치하여 특수문자 및 인젝션 차단 (전 환경 일원화).
   - 콜론 복합 세션 ID 순회 시 `clean_seg = seg.removeprefix("guest-").removeprefix("guest:")` 지원 및 `break` 없이 끝까지 순회하여 회원 세션 UUID 보존 (`session_uuid` > `member_id`).
   - 환경별 분기(`app_env in ('test', 'development')`) 제거로 프로덕션 환경에서도 안정적 검증 보장.
2. **게스트 세션 키 JWT 단일 소유화 및 사칭 방지 (`app/api/router.py`)**:
   - `extract_auth_info_from_auth`: 게스트 JWT의 `sub`에 대해 UUID 유효성을 검증하고, 유효하지 않으면 401 Unauthorized 즉시 거절.
   - `_prepare_chat_context`: 게스트는 바디 `session_id`를 무시하고 JWT `sub`로부터 `guest:{clean_guest_uuid}:{persona}` 키 강제 생성(타 게스트 도청 차단).
   - 미인증(익명) 요청 시 `raw_sid.startswith(("guest:", "guest-"))` 사칭 방지(`removeprefix`).
3. **단위 테스트 보강 및 회귀 검증 (`tests/unit/test_session_security.py`)**:
   - `test_guest_composite_session_id_in_production` (200 OK & SSE 스트리밍 정상 검증)
   - `test_guest_a_cannot_impersonate_guest_b_session_id` (바디 UUID 무시, JWT A 키 생성 검증)
   - `test_invalid_guest_sub_rejected_with_401` (401 반환 검증)
   - `test_invalid_session_id_characters_rejected_with_422_in_all_envs` (전 환경 특수문자 422 거절 검증)
   - 225개 전체 단위 테스트 100% 그린 (`225 passed in 18.29s`), ruff 및 mypy 통과.

### 다음 세션에서 할 일
- **Phase 65 착수: Curator 실패 재현 테스트 및 헛도는 루프 방어 (`feat/curator-reentry-loop`)**: 완료 (세션 67).

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
- **Phase 67 PR 생성 및 develop 머지 지원**: 완료.


---

## 세션 72 (2026-10-16)

### 진행한 작업
1. **도서 장르 경량 분류 API 신설 및 Gemini Flash-Lite 연동 (`POST /api/v1/classify-genre`)**:
   - `app/api/schemas.py`: Core API와 100% 일치하는 `GenreLiteral` 10종(`GENERAL`, `PHILOSOPHY`, `RELIGION`, `SOCIAL_SCIENCE`, `NATURAL_SCIENCE`, `TECHNOLOGY`, `ARTS`, `LANGUAGE`, `LITERATURE`, `HISTORY`) 확정.
   - `ClassifyGenreRequest(title, author, description, kdc, isbn)`, `ClassifyGenreResponse(genre, subject, confidence, source, reason)` 스키마 확정.
   - `app/api/router.py`: `settings.gemini_light_model` 기반 LangChain ChatGoogleGenerativeAI 바인딩, `max_retries=0`, `asyncio.wait_for(timeout=2.0)` 하드 타임아웃, `clean_desc` 1,500자 슬라이싱 적용.
   - 429 Rate Limit, 타임아웃, 파싱/스키마 에러 시 500 없이 `map_kdc_to_genre` 200 OK 무중단 KDC 폴백(`source="KDC_FALLBACK"`, `reason` 실패 원인 기록).
2. **Phase 60 통합 (KDC 513.8 철학 승격 및 5자리 부가기호 폴백 보강)**:
   - `app/infrastructure/national_library_client.py`: `_normalize_to_core_genre` 헬퍼 신설 및 `CORE_GENRE_ALIASES`(`ART`->`ARTS`, `SCIENCE`->`NATURAL_SCIENCE`) SSOT 정규화.
   - 5자리 부가기호(`EA_ADD_CODE`, 예: `03320` -> `320`) 기반 KDC 추출 및 `513.8` 심리/미술치료 철학 승격 정상 연동.
3. **품질 검증**:
   - `tests/unit/test_classify_genre.py` 신규 테스트 5종 작성: 정상 LLM 판정(《그림의 힘》 -> `PHILOSOPHY`), Gemini 429 Rate Limit 폴백, 2초 타임아웃 폴백, 파싱/불법 장르 폴백, KDC 513.8 및 5자리 부가기호 폴백 전수 통과.
   - 전체 251개 단위 회귀 100% 그린 (`251 passed in 35.71s`), ruff check & format 통과, mypy 통과, `scripts/check_harness.py` 통과.

### 다음 세션에서 할 일
- **Phase 68 PR 생성 및 develop 머지 지원**: 완료 (PR #66 머지 완료, 커밋 `7ae875f`).


---

## 세션 73 (2026-10-17)

### 진행한 작업
1. **도서 추천 권수 정책 유연화 (Phase 69 Step 1)**:
   - `app/domain/graph/curator_node.py`: `CuratorResponse.recommendations` 제약을 `min_length=1, max_length=10`으로 완화.
   - `parse_requested_book_count` 함수 신설: 기본 1권(원픽), 비교/탐색형("두세 권", "다양하게", "비교" 등) 2~3권, 명시적 숫자(아라비아/한글 수사) 최대 10권 파싱 지원.
   - `CURATOR_SYSTEM_PROMPT` 유연화: "딱 2권" 하드코딩 제거 및 권수 가변 추천 지침 반영.
2. **억지 고전 강제 주입 폴백 제거 및 정직한 서지 반환 (`assemble_curated_books`)**:
   - `if len(final_books) < 2:` 고전 강제 주입 루프 완전 삭제.
   - 국립중앙도서관 서지 검증(`verified=True`)을 통과한 도서만 반환하며, 10권 요청 중 4권만 성공 시 4권만 반환, 0권 성공 시 빈 리스트(`[]`) 정직하게 반환.
3. **사서 노드 프롬프트 및 산출물 정제 개선 (`nodes.py`)**:
   - `system_prompt` 조립 시 4권 이상 다수 추천일 경우 독자의 스크롤 압박 완화를 위해 간결한 번호 목록(`1. 《도서명》 - 저자: 핵심 이유`) 출력 지침 적용 (1~3권은 기존 `### 📖` 유지).
   - 본문 서술 도서명과 `curated_books` 배열의 제목/개수 100% 일치 지침 강화.
   - `_sanitize_persona_output`: `1. 《도서명》` 번호 목록 포맷 정합성 검증 추가 및 `curated_books` 부재 시 가짜 번호 목록 카드 마커 소거.
4. **단위 테스트 작성 및 기존 테스트 갱신**:
   - `tests/unit/test_curator_node.py` 신규 10종 작성: 기본 1권, 3권, 5권 요청, 10권 요청 중 4권 성공 시 4권 반환, 0권 성공 시 빈 리스트 반환, 본문 마크다운 제목/개수 일치 및 프론트 정규식 매칭 전수 통과.
   - `tests/unit/test_curator_pipeline.py`: 기존 2권 고정 전제 테스트 9종을 유연한 권수 계약으로 갱신 (전체 28개 100% 통과).
   - 전체 262개 단위 회귀 100% 그린 (`262 passed in 31.69s`), ruff check & format 통과, mypy 통과, `scripts/check_harness.py` 통과.

### 다음 세션에서 할 일
- **Phase 69 Step 2: Core API / YES24 도서 검색 1차 연동 및 후보 검증 체계 고도화**: 완료 (세션 74).


---

## 세션 74 (2026-10-17)

### 진행한 작업
1. **Core API 응답 스키마 정규화 (`app/infrastructure/core_api_client.py`)**:
   - `search_books` 메소드가 `items` 키를 올바르게 파싱하도록 수정하고, CamelCase(`coverUrl`, `totalPages` 등)를 snake_case(`cover_url`, `page_count` 등)로 정규화.
   - 통신 장애/에러 시 가짜 목데이터 생성을 배제하고 정직한 빈 리스트(`[]`)를 반환하도록 안전화.
2. **ISBN-10 / ISBN-13 체크디지트 검증 및 재계산 로직 신설 (`app/domain/graph/curator_node.py`)**:
   - `validate_isbn10`: Modulo 11 체크디지트 알고리즘 검증.
   - `calculate_isbn13_check_digit`: EAN-13 가중치(1, 3 교대) 기반 13번째 체크디지트 계산기 구현.
   - `validate_isbn13`: 13자리 및 EAN-13 체크디지트 유효성 검증.
   - `convert_isbn10_to_isbn13`: 유효한 ISBN-10 검증 후 앞 9자리에 `978`을 붙이고 EAN-13 가중치로 새로운 체크디지트를 산출하여 결합.
   - `normalize_and_validate_isbn`: VALID_13, CONVERTED_10, INVALID, MISSING 4대 상태로 엄격 분류.
3. **저자 성명 정규화 및 보수적 비교 (`app/domain/graph/curator_node.py`)**:
   - `_extract_primary_author`: 쉼표/슬래시/역할표기 분리 및 번역자/일러스트레이터와 원작자 구분.
   - `_is_matching_author`: 서양식 성·이름 반전(`George Orwell` <-> `Orwell, George`) 지원, 단순 글자 set 비교 원천 금지로 한글 성명 오탐(`김영하` != `김하영`) 차단, 빈 expected author는 도서명 단독 검색 허용.
4. **판본 의도 추출 및 캐시 분리 (`app/domain/graph/curator_node.py`)**:
   - `extract_edition_intent`: 일반(`GENERAL`), 만화(`COMICS`), 아동(`CHILDREN`), 원서(`ORIGINAL`), 출판사(`PUB:{name}`) 판본 태그 분리 및 상충/모호 요청 시 캐시 bypass(`None`).
   - `get_biblio_cache_key`: SHA-256 기반 판본 격리 캐시 키 생성 및 서로 다른 판본 요청 간 캐시 오염 차단.
5. **계층형 서지 검증 체인 구축 (`_verify_single_candidate`, `resolve_targeted`, `verify_candidates`)**:
   - 1차 Core API(YES24, 2.5s) -> 2차 국립중앙도서관(3.5s) 무중단 폴백 체계 안착.
   - Track A(ISBN 유효) 및 Track B(ISBN 누락 시 출판사/표지/쪽수 3대 조건 엄격 검증) 적용. INVALID ISBN 즉시 탈락.
   - 구조화된 로그(`[BIBLIO_SUCCESS]`, `[BIBLIO_FALLBACK]`, `[BIBLIO_REJECT]`, `[BIBLIO_CACHE_HIT]`) 표준화.
6. **단위 테스트 작성 및 품질 검증**:
   - `tests/unit/test_hierarchical_curator_verification.py` 22종 신규 작성 (ISBN 검증/변환, 저자 정규화, 캐시 격리, 계층형 폴백, Track A/B 검증).
   - 전체 284개 단위 회귀 100% 그린 (`284 passed in 46.68s`), ruff check & format 통과, mypy 통과, `check_harness.py` 통과.

### 다음 세션에서 할 일
- **Phase 69 Step 2 변경 사항 검토 보고 및 PR 생성**: 완료 (세션 75).

---

## 세션 75 (2026-10-20)

### 진행한 작업
1. **웹 프런트엔드 장르 라벨 다국어 연동 완료**:
   - 도서 등록 화면에서 장르 Enum이 raw 영문으로 노출되던 문제를 다국어 체계와 연동하여 한국어(`기술과학 (건강/의학)`), 영어(`Technology / Science`) 분기 렌더링으로 정비 ([PR #181](https://github.com/DPYB/frontend-reader-web/pull/181) 머지 완료 참조).
2. **Phase 2 성능 계측 설계 및 비기능 원칙 수립**:
   - 도서 등록 지연 구간 분석: 바코드 스캔 vs Gemini Vision VLM 지연, 국립도서관 API 중복 호출, 대형서점 1차 병렬 및 2차 직렬 fallback 구간 식별.
   - 계측 설계: 전체 요청 시간과 개별 하위 시간 분리, 상태 코드(`SUCCESS`, `CACHE_HIT`, `TIMEOUT`, `SKIPPED`) 세분화, 마스킹 ISBN(`97911****3135`) 및 correlation_id 연계 규격 수립.
   - 무간섭 원칙: `try...finally`로 감싸 기존 비즈니스 로직, 반환값, 타임아웃, 예외 전파 100% 보존.
3. **타 서비스 작업 트리 격리 및 보호**:
   - 코어 API 서비스가 팀원의 별도 작업 브랜치(`feat/scrap-presigned-url`) 진행 중임을 확인하고 일체 수정 없이 안전하게 격리 보호.

### 다음 세션에서 할 일
- **Phase 70 1차 구현 착수 (`backend-ai-agent` 단독)**: 완료 (세션 76).
