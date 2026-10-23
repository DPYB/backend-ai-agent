# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다.
> **관리 규칙**: 본 문서에는 **최근 3~5개 세션만 유지**하며, 과거 세션 로그는 `.harness/archive/`에 보관합니다. 타 레포 내부 작업은 기록하지 않고 연동 링크만 참조합니다.
> *(과거 세션 1~74 내역은 `.harness/archive/HANDOFF_2026-10.md` 참조)*

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
- **Phase 70-3 변경 사항 최종 검토 및 사용자 승인 후 커밋/PR 생성 (`feat/fix-core-api-genre-curation`)**: 완료 (PR #71 머지 완료, 커밋 `e29a390`).
- **Milestone 4 남은 점검 항목 착수**:
  - 추천 카드 마커 `### 📖 {도서명}` 및 카드 메타데이터의 프론트엔드 E2E 실연동 검증 (대기)

---

## 세션 79 (2026-10-24)

### 진행한 작업
1. **해외 도서 수용 및 다국어 서지 검증 체계 구축 (Phase 70-6)**:
   - `core_api_client.py`: Core API 도서 검색 시 `data_source` 보존.
   - `national_library_client.py`: 10대 표준 영문 카테고리 매핑 및 `map_english_category_to_genre` 구현.
   - `curator_node.py`: 서양 인명 이니셜/미들네임 매칭 유연화(`_is_matching_author`), `ORIGINAL` 판본 영문 도서 수용 및 영문 장르 매핑 연동.
   - `nodes.py`: 프롬프트 시스템 문구 및 헤딩 일관화.
   - `tests/unit/test_global_curation.py`: 32개 단위 테스트 작성 및 전수 통과.
2. **과거 추천 회상 질문 분기 및 허위 추천 차단 (Phase 71 Step 1)**:
   - `nodes.py`: `is_recall_query` 의도 분류기 신설로 "이전에 추천한 도서", "아까 추천해준 책" 등 회상 질의 감지 시 `curator_node` 선위임 전면 차단.
   - `state.recommended_history` 주입: 이전 추천 기록이 없을 때 가짜 책 날조 없이 정직한 멘트 반환, 기록이 있을 때 해당 도서만 정확히 답변.
   - `tests/unit/test_recall_curation.py`: 18개 단위 테스트 작성 및 전수 통과.
3. **Tier 1/2 정적 검사 및 PR #72 머지 완료**:
   - `test_recall_curation.py`의 미사용 import 정리 및 `AgentState` TypedDict 타입 검사 완전 해소.
   - 의도 분해 로직(`check_recall_intent`, `check_new_recommendation_intent`) 직교 분리 및 Ruff 포맷 반영.
   - 전체 비통합 단위 테스트 366개 100% 그린 (`366 passed in 21.19s`), Ruff 린트/포맷 통과, Mypy 통과, `scripts/check_harness.py` 통과.
   - PR #72(`feat[curator]: 해외 도서 서지 검증 체계 구축 및 과거 추천 회상 질문 분기 구현`) 생성 및 `develop` 머지 완료 (커밋 `94dccc1`).
   - 머지 완료 브랜치 `feat/recommendation-card-contract` 정리 완료.

### 다음 세션에서 할 일
- **Phase 71 Step 2 착수**: 대화 세션 복원 및 소유권 검증 엔드포인트 (`GET /api/v1/chat/history`) 구현.
- **Phase 70-5 (추천 카드 응답 계약 테스트)**: Core API 미국 도서(Google Books) 스키마 확정 시 재개.
