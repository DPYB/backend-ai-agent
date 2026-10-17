# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다.
> **관리 규칙**: 본 문서에는 **최근 3~5개 세션만 유지**하며, 과거 세션 로그는 `.harness/archive/`에 보관합니다. 타 레포 내부 작업은 기록하지 않고 연동 링크만 참조합니다.
> *(과거 세션 1~60 내역은 `.harness/archive/HANDOFF_2026-09.md` 참조)*



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
- **Phase 69 Step 2 변경 사항 검토 보고 및 PR 생성**:
  - 사용자에게 변경 사항 최종 보고 후 승인 하에 PR 생성.
