# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다.
> **관리 규칙**: 본 문서에는 **최근 3~5개 세션만 유지**하며, 과거 세션 로그는 `.harness/archive/`에 보관합니다. 타 레포 내부 작업은 기록하지 않고 연동 링크만 참조합니다.
> *(과거 세션 1~60 내역은 `.harness/archive/HANDOFF_2026-09.md` 참조)*



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
- **Yes24 OpenAPI 도입 또는 Phase 60 (국립도서관 KDC 부재 시 5자리 부가기호 다중 폴백)** 착수.
