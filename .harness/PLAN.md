# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 미완료 작업 체크리스트

### 📌 Phase 21 (Step 1): 실시간 독서 세션 도구 구축 (`check_user_reading_streak`)
> **진행 조건**: 대표님 로컬 터미널에서 `grep -rn "StateGraph\|from langgraph" app/` 직접 검증 후 승인 시 착수
> **핵심 원칙**: 도구는 오직 가공되지 않은 순수 정형 데이터(팩트 JSON)만 반환하며, 페르소나 어조(~냥, ~두둥 등)는 사서 노드 LLM이 전담함.

- [ ] **Core API 클라이언트 연동 메서드 구현 (`app/infrastructure/core_api_client.py`)**:
  - `get_user_reading_streak(member_id: str, token: Optional[str] = None)`: `backend-core-api`의 세션 API 호출 (Token Relay 및 게스트 바이패스, 오프라인 Mock 지원).
- [ ] **순수 팩트 반환 도구 구현 (`app/domain/memory/reading_streak_tool.py`)**:
  - `@tool("check_user_reading_streak")`: 누적 시간, 연속 일수(Streak), 최근 세션 정보 JSON 문자열 반환.
- [ ] **도구 전사 바인딩 (`app/domain/graph/tools.py`)**:
  - `GENERIC_TOOLS`에 `check_user_reading_streak` 등록하여 8개 페르소나에 자동 바인딩.
- [ ] **단위 테스트 작성 및 무결성 검증 (`tests/unit/test_reading_streak_tool.py`)**:
  - 로그인 유저 정상 데이터 반환, 비로그인 게스트 바이패스, Core API 오류 시 안전 폴백, Ruff/Mypy/Pytest 100% 통과.

---

### 📌 Milestone 4 (Phase 20 E2E 통합 검증): 프론트엔드 연동 후 3대 서비스 통합 스모크 테스트
> **백엔드(backend-ai-agent) 구현 및 단위 테스트 완료 상태**

- [ ] **E2E 스모크 테스트 1: 날씨 뱃지 (Signals 연동)**
  - 브라우저 위치 허용 시 `/api/v1/chat` 응답의 `signals` 객체(날씨/기온/시간대/무드)가 프론트엔드 상단 `WeatherMoodBadge`에 정상 렌더링되는지 확인

- [ ] **E2E 스모크 테스트 2: 도서 추천 카드 메타데이터**
  - 도서 추천 발화 시 표지 이미지(`cover_url`), 장르(국문/영문 유연 지원), 총 쪽수(`page_count`)가 `BookCardView`에 올바르게 표시되고 '내 서재에 담기' 원클릭 등록이 정상 동작하는지 확인

- [ ] **E2E 스모크 테스트 3: 빈 서재 정직 응답**
  - 서재가 비어있는 상태에서 "내 서재에 무슨 책 있어?" 질문 시 더 이상 거짓 도서를 지어내지 않고 "등록된 도서가 없습니다"로 정직하게 답변하는지 확인

- [ ] **E2E 스모크 테스트 4: 토론 모드 평론가 페르소나 및 팩트 그라운딩**
  - 평론가 선택 후 토론 시 고양이 말투(~냥) 오염 없이 비평가 특유의 어조로 답변하는지, 대상 도서의 실제 서지/줄거리를 바탕으로 대화가 진행되는지 확인
