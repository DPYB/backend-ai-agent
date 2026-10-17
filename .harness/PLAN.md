# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 본 레포(`backend-ai-agent`) 작업 체크리스트만 유지합니다.
> 타 레포 작업은 해당 레포의 `PLAN.md`에서 관리하며, 완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제합니다.

---







### 📌 Phase 69: 도서 추천 에이전트 구조 개선 및 추천 품질 향상

#### Step 1: 추천 권수 정책 유연화 & 억지 고전 주입 폴백 제거 (완료)
- [x] **1. `CuratorResponse` 스키마 및 시스템 프롬프트 유연화 (`app/domain/graph/curator_node.py`)**:
  - `CuratorResponse.recommendations`: `min_length=1, max_length=10`으로 상한 완화 (가변 수용).
  - `CURATOR_SYSTEM_PROMPT`: "딱 2권" 하드코딩 제거, 기본 1권 / 탐색형 2~3권 / 명시적 요청 최대 10권 유연 추천 지침 반영.
  - 4권 이상 추천 요청 시 프론트엔드 파싱 정합성을 위한 간결한 번호 목록(`1. 《도서명》 - 저자: 핵심 이유`) 출력 지침 반영.
- [x] **2. 억지 고전 강제 주입 폴백 제거 (`app/domain/graph/curator_node.py`)**:
  - `assemble_curated_books`에서 `if len(final_books) < 2:` 고전 강제 주입 루프 완전 삭제.
  - 서지 검증 통과 도서만 반환 (`final_books` 유지, 검증 성공 0권 시 빈 리스트 `[]` 반환).
  - `requested_count`에 맞춰 슬라이싱 및 중복 제거.
- [x] **3. 사서 노드 프롬프트 및 본문-추천배열 일치성 보강 (`app/domain/graph/nodes.py`)**:
  - 4권 이상 다수 추천 시 본문 서술을 간결한 번호 목록(`1. 《도서명》 - 저자`)으로 안내.
  - 본문에 언급되는 도서명과 `recommended_books` 배열의 제목/개수 100% 일치 지침 강화.
  - `_sanitize_persona_output`: 번호 목록 포맷 검증 추가 및 `curated_books` 부재 시 가짜 번호 목록 카드 마커 소거.
- [x] **4. 단위 테스트 작성 및 기존 파이프라인 테스트 갱신**:
  - `tests/unit/test_curator_node.py` 신설: 기본 1권, 명시적 3권, 5권, 10권 중 4권만 성공 시 4권만 반환, 0권 성공 시 빈 리스트 반환, 본문-배열 일치 테스트.
  - `tests/unit/test_curator_pipeline.py`: 기존 2권 고정 전제 테스트 9종을 유연한 권수 계약에 맞게 갱신.
- [x] **5. Tier 1/2 품질 검증 완료**:
  - ruff, mypy, 전체 262개 단위 회귀(100% 그린, 31.69s), check_harness 통과.

#### Step 2: Core API / YES24 도서 검색 1차 연동 및 후보 검증 체계 고도화 (사용자 승인 대기)
- [ ] **1. Core API 도서 검색 클라이언트 메소드 확장**:
  - `CoreApiClient.search_books(query: str, page: int, size: int)` 연동 규격 확인 및 바인딩.
- [ ] **2. 1차 Core API(YES24) ➔ 2차 국립중앙도서관 계층형 서지 검증 체인 구축**:
  - 제목·저자·ISBN 종합 매칭 및 번역본 원작자/번역자 구분 로직.
- [ ] **3. Step 2 단위/회귀 테스트 작성 및 품질 검증**:
  - Core API 정상/에러 시 국립도서관 폴백 검증, 판본 불일치 제외 검증.

---

### 📌 Milestone 4 (E2E 연동 스모크 테스트 준비)
> **본 레포 AI 서빙 API 상태 점검 항목**

- [ ] **도서 추천 카드 응답 규격 점검**:
  - `### 📖 {도서명}` 헤딩, 표지 이미지(`cover_url`), 장르, 총 쪽수(`page_count`) 구조 정합성
- [ ] **서재 도서 조회 분기 점검**:
  - `### 📚 {도서명}` 헤딩 및 `library_books` 객체 규격 유지 확인
- [ ] **토론 모드 팩트 그라운딩 및 페르소나 정합성**:
  - 페르소나 전환 시 어조 소거 및 도서 메타데이터 기반 대화 검증
