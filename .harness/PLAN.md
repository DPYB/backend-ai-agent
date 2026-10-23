# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 본 레포(`backend-ai-agent`) 작업 체크리스트만 유지합니다.
> 타 레포 작업은 해당 레포의 `PLAN.md`에서 관리하며, 완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제합니다.

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

