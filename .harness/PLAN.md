# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 본 레포(`backend-ai-agent`) 작업 체크리스트만 유지합니다.
> 타 레포 작업은 해당 레포의 `PLAN.md`에서 관리하며, 완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제합니다.

---

### 📌 Phase 71: 신뢰할 수 있는 사서 에이전트 고도화 (남은 3단계 점진적 구현)
> **사용자 피드백 기반: 단계적 접근, 소유권 검증 세션 복원, 중립 인정 분위기 판정, 운영 폴백 선별 제거**

- [ ] **Step 2: 대화 세션 복원 및 소유권 검증 (`GET /api/v1/chat/history`)**:
  - **1. 스키마 및 DTO 정의 (`app/schemas/chat.py`)**:
    - `ChatMessageItem`: `role` ('user' | 'assistant'), `content` (str)
    - `ChatHistoryResponse`: `session_id`, `active_persona`, `display_name`, `mode`, `messages` (List[ChatMessageItem]), `recommended_history` (List[str]), `context_summary` (Optional[str])
  - **2. 세션 조회 및 소유권 보안 인터락 엔드포인트 신설 (`app/api/router.py`)**:
    - `GET /api/v1/chat/history?session_id=...&persona=...&mode=...` 구현
    - 인증 토큰 파싱: 회원 JWT `sub` 추출 및 게스트 토큰 식별 (`get_authenticated_member_id`)
    - 세션 키 정규화 및 파티셔닝: `{member_id}:{uuid}:{persona}` 또는 `guest:{clean_uuid}:{persona}`
    - IDOR 방어 소유권 검증:
      - 회원: 요청자의 JWT `sub`와 세션 키/저장 데이터의 `member_id` 불일치 시 `403 Forbidden` 반환
      - 게스트: 요청자의 게스트 `sub`와 세션의 `clean_guest_uuid` 불일치 시 `403 Forbidden` 반환
      - 미인증자: 타인의 회원/게스트 세션 접근 시 `401 Unauthorized` / `403 Forbidden` 차단
    - 세션 부재/만료: Redis 키가 없거나 만료된 경우 `404 Not Found` (detail="Session not found or expired") 반환
    - 정상 반환: Redis `session:{partitioned_id}`의 `messages`, `recommended_history`, `context_summary` 정규화 반환
  - **3. 단위 및 보안 회귀 테스트 작성 (`tests/unit/test_chat_history.py`)**:
    - 정상 조회: 본인 세션의 메시지 히스토리 및 `recommended_history` 복원 검증
    - 소유권 검증 (IDOR 차단): 회원 A가 회원 B 세션 조회 시 403, 게스트 A가 게스트 B 세션 조회 시 403 검증
    - 미인증 차단: 토큰 없이 타인/보호 세션 조회 시 401/403 검증
    - 미존재 세션: 존재하지 않거나 만료된 세션 조회 시 404 Not Found 검증
    - 일반/스트리밍 턴 완료 후 저장된 데이터와 복원 데이터의 100% 일치 검증
  - **4. 프론트엔드 연동 지원 인터페이스 규격**:
    - 대화 턴 완료 후 세션 동기화 및 마운트 시 `GET /api/v1/chat/history` 호출을 통한 말풍선/과거 추천 목록 복원 지원 규격 확립

- [ ] **Step 3: 분위기(Mood) 판정 개선 (LLM 기반 & 중립 상태 인정)**:
  - `_build_signals`의 하드코딩 if-else 키워드 매칭 규칙 걷어내기
  - 사서 LLM의 자연스러운 응답 흐름에서 분위기 추출 (추가 네트워크 지연 방지)
  - 명확한 분위기 근거가 부족하거나 단순 인사/회상/기능 문의일 경우 억지 매핑 없이 `None`(중립) 정상 반환
  - 허용된 6개 Enum 검증 및 분류 실패 시 `cozy`로 되돌아가지 않도록 안전화
  - 단위 테스트 작성 및 회귀 검증

- [ ] **Step 4: 운영 폴백 하드코딩 선별 제거 (테스트 Fixture 보존)**:
  - 실제 운영 경로의 임의 도서 폴백 선별 제거:
    - `curator_node.py`의 `_get_random_elegant_fallback` (운영 에러 시 가짜 명작 주입) 제거 ➔ 빈 리스트(`[]`) 정직한 반환
    - `trending_books.py`의 `EMERGENCY_FALLBACK_BOOKS` (스크래핑/캐시 실패 시 모순 등 주입) 제거 ➔ 빈 목록 반환 및 LLM 정직한 안내
  - 테스트 환경 전용 목 카탈로그(`test_catalog`)는 fixture로 안전하게 보존
  - `CuratorResponse.recommendations(min_length=0)` 완화 및 빈 추천 결과 시 스트리밍/일반 응답 및 사서 정직한 대체 멘트 무결성 검증

---

### 📌 Phase 70-5: 추천 카드 응답 계약 테스트 구축 (Milestone 4 - 작업 2)
> **프론트엔드 연동을 위한 일반/스트리밍 추천 카드 응답 계약을 코드로 영구 고정**

- [ ] **1. 신규 계약 테스트 파일 작성 (`tests/unit/test_recommendation_card_contract.py`)**:
  - `POST /api/v1/chat` 단건 추천 응답의 `recommended_books` 7대 핵심 필드(`title`, `author`, `isbn`, `publisher`, `page_count`, `genre`, `cover_url`, `reason`) 직렬화 검증
  - 사서 발화 본문의 `### 📖 {도서명}` 마크다운 3단계 헤딩 포맷 및 큐레이션 결과 1:1 일치 검증
  - 4권 이상 다수 추천 시 `1. 《도서명》 - 저자: 핵심 이유` 간결 번호 목록 포맷 출력 및 큐레이션 일치 검증
  - `POST /api/v1/chat/stream` SSE 실시간 스트리밍 중 `books` 이벤트 payload 및 `done` 이벤트 `recommended_books` 직렬화 계약 검증
  - 서지 장르 미제공 시 임의 날조 없이 정직한 `genre=None` 반환 계약 검증
  - 표지 미제공 시 `DEFAULT_BOOK_COVER_URL` 및 Kyobo CDN 안전 폴백 계약 검증
  - 내 서재 조회(`### 📚 {도서명}`, `library_books`)와의 상호 간섭 차단 분기 검증
- [ ] **2. 로컬 계층형 검증 (Tier 1/2)**:
  - `uv run ruff check .`
  - `uv run mypy .`
  - `uv run pytest tests/unit/test_recommendation_card_contract.py`
  - `python3 scripts/check_harness.py`
- [ ] **3. 커밋 및 PR 생성 (사용자 승인 후)**:
  - 브랜치: `feat/recommendation-card-contract`
  - 커밋/PR 제목: `test[chat]: 추천 카드 응답 규격 및 스트리밍 이벤트 계약 테스트 추가`

---

### 📌 Milestone 4: E2E 연동 스모크 테스트 및 계약 검증 (미완료 보존)
> **본 레포 AI 서빙 API 상태 점검 및 남은 E2E 검증 항목**

- [ ] **추천 카드 마커 및 카드 메타데이터 프론트엔드 E2E 실연동 검증**:
  - `### 📖 {도서명}` 마커 파싱 및 도서 등록 폼 연동 시 실제 메타데이터 누락 여부 점검
  - 추천 카드 UI 계약을 엔드투엔드로 고정하는 통합/E2E 테스트 공백 보완
- [ ] **서재 도서 조회 분기 점검**:
  - `### 📚 {도서명}` 헤딩 및 `library_books` 객체 규격 유지 확인
- [ ] **토론 모드 팩트 그라운딩 및 페르소나 정합성**:
  - 페르소나 전환 시 어조 소거 및 도서 메타데이터 기반 대화 검증

---

### 📌 Phase 70-6: 해외 도서 수용 및 다국어 서지 검증 후속 과제
> **Core API Google Books categories 직렬화 및 정밀 매핑 연동 (후속 대기)**

- [ ] **[후속 과제] Core API Google Books categories 직렬화 및 정밀 매핑 연동**:
  - 현재 Core API 계약상 Google Books의 원본 `categories`가 전달되지 않아, Agent 영문 장르 분류가 실제 전달되는 `title` 및 `description` 키워드 규칙에 의존하는 제한이 있음
  - 향후 Core API에서 Google Books `categories`를 `subject` 필드로 정식 직렬화 계약에 포함할 경우, Agent의 `map_english_category_to_genre`에서 원본 카테고리(예: "Computers", "Fiction" 등)를 직접 활용한 1순위 매핑 활성화

