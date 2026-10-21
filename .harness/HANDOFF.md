# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다.
> **관리 규칙**: 본 문서에는 **최근 3~5개 세션만 유지**하며, 과거 세션 로그는 `.harness/archive/`에 보관합니다. 타 레포 내부 작업은 기록하지 않고 연동 링크만 참조합니다.
> *(과거 세션 1~73 내역은 `.harness/archive/HANDOFF_2026-10.md` 참조)*

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
- **Phase 69 Step 2 변경 사항 검토 보고 및 PR 생성**:
  - 사용자에게 변경 사항 최종 보고 후 승인 하에 PR 생성.

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

---

## 세션 76 (2026-10-20)

### 진행한 작업
1. **ISBN 민감정보 마스킹 유틸리티 구현 (`app/vision/isbn_utils.py`)**:
   - `mask_isbn` 함수 신설: 13자리(`97911****3135`), 10자리(`893****607`), 미인식(`NONE`), 비정규(`***`) 마스킹 규격 정립.
2. **Vision 표지/바코드 OCR 구간별 성능 계측 (`app/api/v1/vision.py`)**:
   - `_handle_cover_ocr`에 `time.perf_counter()` 기반으로 전체 요청(`total_ms`), 바코드 스캔(`barcode_ms`), Gemini Vision VLM(`vlm_ms`), 국립도서관 API(`nl_api_ms`) 구간 분리 계측.
   - 바코드 성공 시 VLM 스킵(`vlm_status=SKIPPED`, `vlm_ms=0.00`) 및 세부 상태 코드(`SUCCESS`, `NOT_FOUND`, `SKIPPED`, `ERROR`) 로깅.
   - 8자리 `correlation_id` 및 `isbn_masked` 연동, `try...finally`로 예외 전파 및 비즈니스 로직 100% 무간섭 보존.
3. **도서 장르 분류 API 구간별 성능 계측 (`app/api/router.py`)**:
   - `POST /api/v1/classify-genre`에서 전체 요청(`total_ms`), LLM 호출(`llm_ms`), KDC 폴백(`fallback_ms`) 분리 계측.
   - 세부 상태 코드(`SUCCESS`, `TIMEOUT`, `RATE_LIMIT`, `ERROR`, `SKIPPED`) 및 `correlation_id`, `source`, `genre` 로깅.
4. **신규 단위 테스트 작성 및 기존 테스트 안정화**:
   - `tests/unit/test_vision_timing.py` 10종 작성: mask_isbn 변형, 바코드 성공/VLM 스킵, VLM 검출, 제목 검색 폴백, sleep(0.04s) 주입 타이밍 정밀도(>=35ms), 예외 발생 시 finally 로그 보존, classify_genre LLM/타임아웃/키부재/429 로깅 전수 검증.
   - `tests/unit/test_vision.py`의 미모킹 국립도서관 외부 API 호출을 Mock 격리하여 불안정성 해소.
5. **Tier 1/2 품질 검증**:
   - Ruff 린트/포맷 통과, Mypy 타입 체크 99개 파일 100% 통과, 로컬 단위 회귀 297개 100% 그린 (`297 passed in 19.89s`), `scripts/check_harness.py` 하네스 검증 통과.

### 다음 세션에서 할 일
- **Phase 70-1 착수: 문장 스크랩 OCR(`_handle_sentence_ocr`) 구간별 성능 계측 구현 (`feat/perf-timing-sentence-ocr`)**: 완료 (세션 77).

---

## 세션 77 (2026-10-21)

### 진행한 작업
1. **문장 스크랩 OCR 구간별 성능 계측 구현 (Phase 70-1)**:
   - `app/api/v1/vision.py`의 `_handle_sentence_ocr`에 `time.perf_counter()` 기반으로 전체 요청(`total_ms`), 크롭 처리(`crop_ms`), Gemini Flash Vision VLM(`vlm_ms`) 구간 분리 계측.
   - 크롭 상태(`SUCCESS`, `FALLBACK`, `SKIPPED`, `ERROR`) 및 VLM 상태(`SUCCESS`, `TIMEOUT`, `ERROR`, `SKIPPED`), `text_len` 로깅.
   - 8자리 `correlation_id` 발급 및 `try...finally` 구조로 예외 발생/타임아웃 시에도 타이밍 유실 없이 기존 비즈니스 로직 및 `OcrSentenceResponse` 반환 100% 무간섭 보존.
2. **신규 단위 테스트 작성 및 품질 검증**:
   - `tests/unit/test_vision_timing.py`에 문장 OCR 계측 테스트 7종 추가: 정상 호출(crop_status=SKIPPED), 유효한 crop_box(crop_status=SUCCESS), 잘못된 crop_box(crop_status=FALLBACK), sleep(0.04s) 주입 타이밍 정밀도(>=35ms), VLM 예외 발생 시 finally 로깅 보존, 타임아웃(vlm_status=TIMEOUT), 레거시 엔드포인트(`/api/v1/ocr/sentences`) 연동 전수 통과.
   - Tier 1/2 검증: Ruff 린트/포맷 100% 통과, Mypy 타입 체크 99개 파일 100% 통과, 로컬 단위 회귀 304개 100% 그린 (`304 passed in 19.62s`).
3. **Phase 70-1 머지 및 브랜치 정리**:
   - PR #70(`feat/perf-timing-sentence-ocr` ➔ `develop`) 머지 완료 (커밋 `f98ae41`).

### 다음 세션에서 할 일
- **Phase 70-2 착수: 도서 추천 카드 응답 규격 점검 및 Milestone 4 준비**: 완료 (세션 78).

---

## 세션 78 (2026-10-21)

### 진행한 작업
1. **도서 추천 카드 응답 규격 점검 (Phase 70-2, 분석 완료)**:
   - 큐레이터 응답 ➔ 프론트엔드 카드 렌더링 ➔ 도서 등록 폼(`/register`) 전체 데이터 흐름 읽기 전용 점검.
   - 제목(`### 📖 {도서명}`), 표지 이미지(`cover_url`), 총 쪽수(`page_count`) 규격 일치 확인.
   - Core API 1차 서지 검증 성공 경로에서 `genre`가 `None`으로 누락되는 유일한 결함 식별.
   - 추천 카드 UI 계약 E2E 실연동 및 통합 테스트 공백 식별 (Milestone 4 미완료 유지).
2. **Core API 추천 도서 서지 장르 보존 구현 (Phase 70-3, 구현 완료 / PR 대기)**:
   - `app/infrastructure/core_api_client.py`: `search_books` 정규화 시 Core API 응답의 `genre`, `kdc`, `subject` 딕셔너리 보존.
   - `app/domain/graph/curator_node.py`: `_verify_single_candidate`에서 Core API 성공 경로에 3단계 장르 바인딩 적용 (1순위 Core API `genre` 정규화, 2순위 `kdc` 매핑 폴백, 3순위 서지 부재 시 `None` 유지).
   - `tests/unit/test_hierarchical_curator_verification.py`: 회귀 테스트 4종 추가 (Core API genre 제공, KDC 제공, 장르 부재 시 `None`, 국립도서관 폴백).
   - 품질 검증 이력 (이전 세션 실측 기록): 단위 테스트 29개(0.50s), 전체 비통합 308개(63.24s) 100% 그린, Ruff, Mypy, 하네스 규격 통과 (커밋, 푸시, PR 미실행 상태).

### 다음 세션에서 할 일
- **Phase 70-3 변경 사항 최종 검토 및 사용자 승인 후 커밋/PR 생성 (`feat/fix-core-api-genre-curation`)**.
- **Milestone 4 남은 점검 항목 착수**:
  - 추천 카드 마커 `### 📖 {도서명}` 및 카드 메타데이터의 프론트엔드 E2E 실연동 검증
  - 서재 도서 조회 분기(`### 📚 {도서명}`, `library_books`) 검증
  - 토론 모드 팩트 그라운딩 및 페르소나 전환 정합성 검증
