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

#### Step 2: Core API(YES24) 우선 ➔ 국립중앙도서관 폴백 계층형 서지 검증 체계 구현 (완료)
- [x] **1. `CoreApiClient.search_books` 응답 스키마 정규화 (`app/infrastructure/core_api_client.py`)**:
  - `items` 키 파싱 및 CamelCase(`coverUrl`, `totalPages` 등) -> snake_case(`cover_url`, `page_count` 등) 정규화.
  - 가짜 목데이터 배제 및 통신 실패 시 정직한 빈 리스트(`[]`) 반환.
- [x] **2. ISBN 검증 및 ISBN-10 ➔ ISBN-13 체크디지트 재계산 (`app/domain/graph/curator_node.py`)**:
  - `validate_isbn10`: Modulo 11 검증.
  - `calculate_isbn13_check_digit`: EAN-13 가중치(1, 3 반복) 기반 13번째 체크디지트 신규 산출.
  - `validate_isbn13`: 13자리 및 체크디지트 유효성 검증.
  - `convert_isbn10_to_isbn13`: 유효한 ISBN-10 검증 후 `978` + 9자리에 신규 체크디지트 결합.
  - `normalize_and_validate_isbn`: VALID_13, CONVERTED_10, INVALID, MISSING 4대 상태 분류.
- [x] **3. 저자 이름 정규화 및 보수적 비교 (`app/domain/graph/curator_node.py`)**:
  - 특수문자(가운뎃점, 쉼표, 마침표 등) 및 역할 표기(지음, 옮김, 저 등) 정규화.
  - 서양식 성·이름 반전(`George Orwell` <-> `Orwell, George`) 지원.
  - 단순 글자 set 비교 원천 금지 (보수적 토큰 일치), 주 저자/번역자 분리.
- [x] **4. 판본 의도 추출 및 캐시 키 분리 (`app/domain/graph/curator_node.py`)**:
  - `extract_edition_intent`: 일반(`GENERAL`), 아동(`CHILDREN`), 만화(`COMICS`), 원서(`ORIGINAL`), 특정 출판사(`PUB:{name}`).
  - 모호한 다중 의도 시 캐시 bypass(`None`).
  - 캐시 키 `book_biblio:v1:{edition_tag}:{hash}` 기반 Redis 24h TTL 캐싱 및 캐시 오염 방지.
- [x] **5. 계층형 서지 검증 체인 구축 (`verify_candidates`, `resolve_targeted`)**:
  - 1차 Core API(YES24, 2.5s) -> 2차 국립중앙도서관(3.5s) 폴백.
  - Track A(ISBN 유효) / Track B(ISBN 누락 시 제목+저자+출판사+표지+쪽수 엄격 검증).
  - 구조화된 로그(`[BIBLIO_SUCCESS]`, `[BIBLIO_FALLBACK]`, `[BIBLIO_REJECT]`) 표준화.
- [x] **6. 신규 단위 테스트 작성 및 Tier 1/2 검증 (`tests/unit/test_hierarchical_curator_verification.py`)**:
  - ISBN-10/13 검증/변환 테스트 (유효/잘못된/누락된/변환된 구분).
  - 저자 정규화 및 서양식 반전/단순 set 오탐 방지 테스트.
  - 판본별 캐시 분리 및 오염 방지/우회 테스트.
  - Core API 파싱/null 방어 및 국립도서관 폴백 테스트.
  - 전체 단위 회귀 100% 그린 검증 및 하네스 검증.

---

### 📌 Milestone 4 (E2E 연동 스모크 테스트 준비)
> **본 레포 AI 서빙 API 상태 점검 항목**

- [ ] **도서 추천 카드 응답 규격 점검**:
  - `### 📖 {도서명}` 헤딩, 표지 이미지(`cover_url`), 장르, 총 쪽수(`page_count`) 구조 정합성
- [ ] **서재 도서 조회 분기 점검**:
  - `### 📚 {도서명}` 헤딩 및 `library_books` 객체 규격 유지 확인
- [ ] **토론 모드 팩트 그라운딩 및 페르소나 정합성**:
  - 페르소나 전환 시 어조 소거 및 도서 메타데이터 기반 대화 검증
