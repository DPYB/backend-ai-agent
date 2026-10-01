# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

### 📌 Phase 60: 국립도서관 KDC 부재 시 EA_ADD_CODE 5자리 다중 폴백 및 분류 체계 SSOT 강화

- [ ] **`app/infrastructure/national_library_client.py` KDC 다중 폴백 및 5자리 부가기호 연동**:
  - `search_book` 및 `search_by_isbn`에서 KDC 필드가 누락/공백(`""`)인 경우, `EA_ADD_CODE`(예: `"03320"`)의 5자리 부가기호에서 뒤 3자리(`"320"`)를 추출하여 `raw_kdc`로 폴백
  - `map_kdc_to_genre`:
    - `extract_kdc_code`를 거쳐 추출된 `raw_code`가 KDC `513.8`(미술치료/심리치료/임상요법)인 경우 즉시 `PHILOSOPHY`로 승격
    - `SUBJECT`에 `"3"` 같은 1자리 KDC 대분류 숫자만 오는 경우와 실제 주제어 텍스트(예: `"미술치료"`, `"심리"`)가 오는 경우를 엄격히 분기하여, 텍스트 주제어일 때 키워드 매핑을 우선 수행
    - 반환 딕셔너리에 `subject` 및 `display_genre`를 명시적으로 채워 프론트엔드/추천 카드 전달 보장
- [ ] **`app/api/router.py` `classify_genre` 엔드포인트 응답 확장**:
  - `ClassifyGenreResponse`에 `subject`, `display_genre`를 함께 반환하여 프론트엔드 도서 등록 폼의 자동 채움 지원
- [ ] **단위 테스트 작성 및 AI 자가 검증 (Self-Validation)**:
  - `tests/unit/test_recommend_metadata.py`:
    - `EA_ADD_CODE: "03320"` 기반 KDC 추출 및 장르 판별 단위 테스트
    - KDC가 비어있고 `SUBJECT`가 단일 숫자이거나 비어있을 때의 다중 폴백 단위 테스트
    - 순수 KDC `513.8` 및 주제어 기반 `PHILOSOPHY` 승격 회귀 테스트
  - `uv run pytest tests/unit/test_recommend_metadata.py`, `uv run ruff check .`, `uv run mypy .` 무결점 검증

### 📌 Phase 50: 세션 보안 강화 및 대화 초기화(새 대화/되돌리기) 연동

#### [2단계] 프론트엔드 대화 초기화 및 방어 로직 구현 (`frontend-reader-web`)

- [ ] **`is_concluded` 필드 실측 및 중복 방지 플래그**:
  - 서버 응답에 `is_concluded: bool`이 정상 반환됨을 확인 (`currentAnswer?.is_concluded`)
  - 이미 완료된 토론은 새 대화를 눌러도 conclude 재전송 스킵
- [ ] **지연 저장(5초 뒤 conclude) 4대 안전망 구축**:
  - **옛 스냅샷 고정**: 타이머 생성 시점의 `oldSessionId`, `oldMessages`를 클로저 변수로 캡처하여 새 칠판 오염 방지
  - **순수 유저 2턴 이상 검증**: 사서 첫 인사 제외하고 `userMessages.length >= 2`일 때만 지연 conclude 예약
  - **연속 새 대화 클릭(겹침) 방어**: 이전 대기 중인 저장이 있다면 즉시 실행 후 새 타이머 세팅
  - **컴포넌트 언마운트 / 탭 닫기 방어**: `fetch(..., { keepalive: true })`로 페이지 이탈/모드 변경 시에도 인증 헤더를 보존하여 안전 전송
- [ ] **즉시 리셋 + 5초 되돌리기(Undo) 토스트 UI**:
  - 새 번호표 발급 (`crypto.randomUUID()`)
  - 되돌리기 클릭 시 `sessionStorage`와 리액트 상태 동시 복원
  - 작성 중 새 대화 클릭 시 `abortController.abort()` 호출 및 `activeSessionId` 대조로 유령 답변 드랍
  - 중단된 턴에 대해 되돌린 후 이어서 질문 시나리오 스모크 테스트

---

### 📌 Milestone 4 (Phase 20 E2E 통합 검증): 프론트엔드 연동 후 3대 서비스 통합 스모크 테스트
> **백엔드(backend-ai-agent) 구현 및 단위 테스트 완료 상태**

- [ ] **E2E 스모크 테스트 1: 날씨 뱃지 (Signals 연동)**
  - 브라우저 위치 허용 시 `/api/v1/chat` 응답의 `signals` 객체(날씨/기온/시간대/무드)가 프론트엔드 상단 `WeatherMoodBadge`에 정상 렌더링되는지 확인
- [ ] **E2E 스모크 테스트 2: 도서 추천 카드 메타데이터 및 포맷**
  - 도서 추천 발화 시 `### 📖 {도서명}` 헤딩 아래 표지 이미지(`cover_url`), 장르, 총 쪽수(`page_count`)가 `BookCardView`에 올바르게 표시되고 `📚` 오인 없이 '내 서재에 담기' 원클릭 등록이 정상 동작하는지 확인
- [ ] **E2E 스모크 테스트 3: 서재 조회 분기**
  - "내 서재에 무슨 책 있어?" 질문 시 `### 📚 {도서명}` 헤딩과 함께 보유 도서 카드(`library_books`)가 올바르게 렌더링되는지 확인
- [ ] **E2E 스모크 테스트 4: 토론 모드 평론가 페르소나 및 팩트 그라운딩**
  - 평론가 선택 후 토론 시 고양이 말투(~냥) 오염 없이 비평가 특유의 어조로 답변하는지, 대상 도서의 실제 서지/줄거리를 바탕으로 대화가 진행되는지 확인
