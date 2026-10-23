# STATE.md — 단계 단위 완료 스냅샷

> 지금까지 완료된 기능과 작업 단계를 마일스톤 단위로 요약 기록합니다.
> **관리 규칙**: 본 문서에는 **본 레포(`backend-ai-agent`)의 핵심 마일스톤 완료 상태만 간결하게(1~3줄 요약)** 유지합니다. 타 레포 상세 구현이나 장황한 코드 diff는 기록하지 않습니다.

---

### 🏛️ 핵심 도메인 아키텍처 완성 현황

- [x] **2-Track 8개 페르소나 오케스트레이션 (`app/domain/graph/`)**:
  - 사서 모드 4종(`CAT`, `SHOEBILL`, `SEA_SLUG`, `GECKO`) 및 토론 모드 4종(`CRITIC`, `STORYTELLER`, `COUNSELOR`, `OBSERVER`).
  - 페르소나 전환 시 어조 오염을 물리적으로 차단하는 `summarizer_node` 및 Redis 세션 네임스페이스(`{member_id}:{uuid}:{persona}`) 격리 완료.
  - SSE 실시간 스트리밍 엔드포인트(`POST /api/v1/chat/stream`) 구축.

- [x] **도서 큐레이션 & 실서지 검증 엔진 (`app/domain/curator/`, `app/infrastructure/`)**:
  - 국립중앙도서관 정식 서지 API(`SearchApi.do`) 연동 및 4단계 실전 검증 체인(제목 정제, 표지 생존 검증, 실서지 바인딩).
  - 깨진 이미지 방지를 위한 교보 CDN/국립도서관 검증 및 `DEFAULT_BOOK_COVER_URL` 고화질 폴백 SSOT 구축.
  - KDC 십진분류 기반 장르 매핑(`map_kdc_to_genre`) 및 `513.8`(심리요법) 철학 승격 라우팅.

- [x] **개인화 RAG & 독서 리포트 (`app/domain/reports/`, `app/domain/memory/`)**:
  - Gemini 임베딩(`text-embedding-004`, 768차원) + Supabase pgvector(`agent.scrap_vector`) 독서 기록/스크랩 벡터화 수신.
  - 사서 월간 독서 리포트(`GET /api/v1/reports/monthly`): 코어 API 통신 실패 시 가짜 목데이터 배제 및 정직한 0건 스켈레톤/사서 격려 멘트 반환.
  - 두 백엔드 서버 간 연결성 진단 필드(`core_api_connected`, `core_api_url`) 연동.

- [x] **무상태 Vision API (`app/domain/vision/`)**:
  - `pyzbar` 기반 13자리 바코드(ISBN-13, EAN13) 스캔 (`POST /api/v1/vision/scan-barcode`).
  - Gemini Flash Vision OCR ($0 Zero-cost, OpenAI 폴백) 및 5자리 부가기호(KDC) 추출.

- [x] **프로덕션 인프라 & 제로비용 정책 (`app/core/`, Docker, CI/CD)**:
  - Google Cloud Run(서울 `asia-northeast3` 리전) 프로덕션 마이그레이션 및 Render 레거시 배포 제거.
  - Upstash Serverless Redis(`rediss://...`) 연동을 통한 멀티 인스턴스 세션 보존.
  - Tiered Verification(Tier 1 린트 0.2s ➔ Tier 2 로컬 단위회귀 10s ➔ Tier 3 GitHub Actions CI) 구축.

---

### 📌 최근 마일스톤 완료 내역

- [x] **Phase 71 Step 1: 회상 질문 분기 및 허위 추천 차단 (PR #72 머지 및 경계 사례 정밀화 완료)**
  - `nodes.py`: `check_recall_intent` / `check_new_recommendation_intent` 직교 분해 및 경계 사례("책 추천해 줘. 그런데 너 나 기억나?") 정규식 정밀화로 일반 봇 기억 질의 오탐 원천 차단.
  - 세션 실제 추천 기록(`state.recommended_history`) 프롬프트 주입: 기록 부재 시 가짜 책 날조 없이 정직한 안내, 기록 존재 시 해당 도서만 정확히 상기 및 신규 추천과 분리 소개.
  - 단위 테스트 총 51종(`test_recall_curation.py`) 작성 및 369개 전체 단위 회귀 100% 그린 검증 완료.
- [x] **Phase 70-6: 해외 도서 수용 및 다국어 서지 검증 체계 구축 (PR #72 머지 완료)**
  - `core_api_client.py`에서 `data_source` 보존. `national_library_client.py`에 10대 영문 카테고리 매핑 테이블 및 `map_english_category_to_genre` 신설.
  - `curator_node.py`: 서양 인명 이니셜/미들네임 매칭 유연화(`_is_matching_author`), `ORIGINAL` 판본 및 영문 장르 매핑 연동.
  - 신규 단위 테스트 32종(`test_global_curation.py`) 작성 및 366개 단위 회귀 100% 그린.
- [x] **Phase 70-3: Core API 추천 도서 서지 장르 누락 수정 (PR #71 머지 완료)**
  - `core_api_client.py`에서 `genre`, `kdc`, `subject` 딕셔너리 정규화 보존.
  - `curator_node.py`의 `_verify_single_candidate`에서 Core API 1차 검증 성공 시 표준 장르 정규화(`_normalize_to_core_genre`) 및 KDC 폴백(`map_kdc_to_genre`), 부재 시 `None` 유지 적용.
  - 신규 단위 테스트 4종(`test_hierarchical_curator_verification.py`) 추가, PR #71 머지 완료 (커밋 `e29a390`).
- [x] **Phase 70-2: 도서 추천 카드 응답 규격 점검 (분석 완료, E2E 검증 미완료)**
  - 큐레이터 응답 ➔ 프론트엔드 카드 렌더링 ➔ 도서 등록 폼(`/register`) 전체 데이터 흐름 읽기 전용 점검 완료.
  - `### 📖 {도서명}`, `cover_url`, `page_count` 규격 일치 확인 및 Core API 1차 검증 경로 `genre` 누락 결함 식별.
  - 추천 카드 E2E 실연동 검증 및 카드 UI 계약 엔드투엔드 통합 테스트 공백 식별 (Milestone 4 미완료 유지).
- [x] **Phase 70-1: 문장 스크랩 OCR(`_handle_sentence_ocr`) 구간별 성능 계측(Timing Logging) 구현**
  - `_handle_sentence_ocr`에 `time.perf_counter()` 기반 크롭(`crop_ms`), Gemini Flash Vision VLM(`vlm_ms`), 전체 요청(`total_ms`) 독립 계측 및 세부 상태 코드(`SUCCESS`, `FALLBACK`, `SKIPPED`, `TIMEOUT`, `ERROR`) 로깅.
  - 8자리 `correlation_id` 및 `text_len` 추적, `try...finally`로 비즈니스 로직/예외 무간섭 100% 보존.
  - 신규 단위 테스트 7종(`test_vision_timing.py`) 추가 작성 및 304개 전체 단위 회귀 100% 그린 검증 완료.
- [x] **Phase 70: Vision 및 도서 분류(classify-genre) 구간별 성능 계측(Timing Logging) 구현**
  - `_handle_cover_ocr`에 `time.perf_counter()` 기반 바코드(zbar), Gemini Vision VLM, 국립도서관 API 구간별 독립 계측 및 상태 코드(`SUCCESS`, `NOT_FOUND`, `SKIPPED`, `ERROR`) 로깅.
  - `mask_isbn` 도입으로 민감정보 마스킹(`97911****3135`) 및 8자리 `correlation_id` 추적. `try...finally`로 비즈니스 로직/예외 무간섭 100% 보존.
  - `POST /api/v1/classify-genre` LLM 및 KDC fallback 구간별 시간/상태 분리 계측, 신규 단위 테스트 10종(`test_vision_timing.py`) 작성 및 297개 전체 단위 회귀 100% 그린 검증 완료.
- [x] **Phase 69 Step 2: Core API(YES24) 우선 ➔ 국립중앙도서관 폴백 계층형 서지 검증 체계 구현**
  - Core API `items` 파싱 정규화 및 통신 실패 시 가짜 목데이터 배제/빈 리스트(`[]`) 반환. ISBN-10 Modulo 11 검증 ➔ EAN-13 가중치 체크디지트 재계산 변환 및 4대 상태(`VALID_13`, `CONVERTED_10`, `INVALID`, `MISSING`) 분류.
  - 서양식 성·이름 반전(`George Orwell` <-> `Orwell, George`) 지원 및 단순 글자 set 오탐 차단. 판본 의도(`GENERAL`, `COMICS`, `CHILDREN`, `ORIGINAL`, `PUB:*`) 캐시 키 분리/우회, 1차 Core API(2.5s) -> 2차 국립도서관(3.5s) 무중단 폴백 및 Track A/B 검증 체인 구축 (신규 단위 테스트 22종 포함 전체 284개 100% 그린).
- [x] **Phase 69 Step 1: 도서 추천 권수 유연화(기본 1권, 탐색 2~3권, 명시적 최대 10권) & 억지 고전 주입 폴백 제거**
  - `CuratorResponse.recommendations(min_length=1, max_length=10)` 및 `parse_requested_book_count` 함수 신설, 4권 이상 추천 시 간결한 번호 목록(`1. 《도서명》 - 저자: 핵심 이유`) 출력 프롬프트 및 `_sanitize_persona_output` 정규식 연동.
  - `assemble_curated_books`에서 강제 고전 주입 루프(`if len(final_books) < 2:`) 완전 삭제 및 서지 검증 통과 도서만 정직하게 반환(검증 부족 시 축소 반환, 0건 시 빈 배열).
  - 신규 단위 테스트 10종 포함 전체 262개 단위 회귀 100% 그린 검증 완료.
- [x] **Phase 68: 도서 장르 경량 분류 API 신설 및 Gemini Flash-Lite 연동 (`POST /api/v1/classify-genre`) & Phase 60 통합**
  - Core API `GenreType` 10종 규격(`ARTS`, `NATURAL_SCIENCE` 등) 일치 `GenreLiteral` 스키마 및 DTO 확정.
  - Gemini Flash-Lite 기반 2.0s 하드 타임아웃, `max_retries=0`, 429/타임아웃/파싱 에러 시 `map_kdc_to_genre` 무중단 KDC 폴백(200 OK) 구현.
  - KDC 513.8 철학 승격 및 5자리 부가기호(`EA_ADD_CODE`) 3자리 추출 연동, 신규 단위 테스트 5종 포함 전체 251개 단위 회귀 100% 그린 검증.
- [x] **Phase 67: Clova OCR 레거시 잔재 전면 제거 및 Gemini Vision 단일화**
  - `app/vision/clova_ocr_client.py` 삭제, `gemini_ocr_client.py`/`__init__.py` 하위 호환 별칭 제거 및 `config.py`의 `naver_clova_*` 미사용 필드 제거.
  - `AGENTS.md`, `.harness/ARCHITECTURE.md`, `README.md`에서 Clova 언급 전면 제거 및 단위 테스트 17종 포함 전체 회귀 100% 그린 검증.
- [x] **Phase 66: 토론 파트너 4종 논리적 핑퐁(완전 독립 1:1 토론 + 팩트 그라운딩 반론 + 꼬리물기 질문) 고도화**
  - `COMMON_DEBATE_TURN_RULES` 신설 및 4종 토론자(`CRITIC`, `STORYTELLER`, `COUNSELOR`, `OBSERVER`) 턴 프롬프트에 논리의 대립(건설적 반론), 완전 독립 1:1 토론(타 파트너 언급/연계 지침 원천 배제), 꼬리물기 질문(Ping-Pong, 피날레 제외) 지침 연동.
  - 서지/줄거리 팩트 기반 반론 및 사서 말투(`~냥`, `~두둥` 등) 코드 레벨 소거(`_strip_debate_animal_endings`), 토론 모드 시 사서 추천 선위임 차단/사서 이름 격리 및 신규 단위 테스트 8종 포함 전체 247개 단위 회귀 100% 그린 검증.
- [x] **Phase 65-1: 큐레이터 폴리싱 (8종 페르소나 어조 분기 및 게스트 E2E 모킹 최적화)**
  - 사서 4종(`CAT`: ~냥, `SHOEBILL`: ~두둥, `SEA_SLUG`: ~누누, `GECKO`: ~크크) 및 토론자 4종(평론가, 이야기꾼, 상담사, 관찰가) 맞춤형 대체 문구/빈 응답 폴백 매핑 SSOT 구축.
  - 게스트 E2E 테스트의 LLM/날씨 네트워크 호출 모킹 최적화로 단위 회귀 실행 시간 대폭 단축(144s ➔ 30s) 및 전체 239개 단위 회귀 100% 그린 검증.
- [x] **Phase 65: Curator 실패 재현 테스트 및 헛도는 루프 방어 (P2 안정성 패치)**
  - 3중 재진입 경로(선위임, 도구 호출, 빈 지연 약속) 차단 및 사서 모드 전용 `curator_attempted: bool` 플래그 관리 (토론 모드 격리).
  - 큐레이터 실패 시 사서 도구에서 `request_book_curation` 배제(Dangling 방지), 지연 약속 문장 단위 치환 및 허위 카드 마커 100% 후처리/빈 응답 방어.
  - `recursion_limit: 25` 버퍼 및 스트리밍 시 실패 복귀 턴 버퍼링(on_chain_end 정제 토큰 방출) + `GraphRecursionError` 우아한 대체 멘트/Redis 보존 핸들링.
  - 신규 단위/재현/SSE/게스트 E2E 테스트 12종 작성 및 전체 237개 단위 회귀 100% 그린 검증.
- [x] **Phase 64-1: 게스트 복합 세션 ID 422 해결 및 세션 키 JWT 단일 소유화 (핫픽스)**
  - `ChatRequest.session_id` 정규식(`^[A-Za-z0-9:_-]{1,128}$`) 검증 일원화 및 콜론 세그먼트 순회 시 회원 세션 UUID 보존 (`session_uuid` > `member_id`).
  - `router.py` 게스트 JWT `sub` 유효성 검증(비정상 시 401) 및 바디 `session_id` 무시 후 JWT `sub` 기반 `guest:{uuid}:{persona}` 키 강제 생성(타 게스트 도청 차단).
  - 미인증 요청 `guest:` 접두사 사칭 방지 및 신규 보안/회귀 테스트 4종 포함 225개 단위 테스트 100% 그린 검증.
- [x] **Phase 64: 도구 바인딩 분리 및 member_id ContextVar 주입 (P1 보안 IDOR 차단 & 게스트 매핑)**
  - 메모리 도구(`search_scrap_memory`, `search_debate_memory`, `search_my_library`) 인자에서 `member_id` 완전 제거 및 `current_member_id` ContextVar 주입 고정.
  - LLM 도구 스키마 및 프롬프트에서 `member_id` 노출 전면 제거, 비동기 요청 간 ContextVar 격리 및 fail-closed 거부 반환 구현.
  - 사서 모드(`LIBRARIAN_TOOLS`)와 토론 모드(`DEBATE_TOOLS`) 도구 분리 바인딩 및 전용 보안 테스트 suite(`test_tool_security.py`) 구축.
  - 코어 API 단일 공용 방과 일치하는 `settings.guest_member_id`(`00000000-0000-0000-0000-000000000003`) 매핑 및 게스트 토론 인사이트 쓰기 방지/요청 바디 ID 완전 무시 보안 테스트 15종 100% 그린 검증.
- [x] **Phase 63: 월간 독서 리포트 정직한 0건 스켈레톤 및 코어 API 헬스체크 연결성 진단**
  - 통신 실패 시 하드코딩 3권/832쪽 목데이터 전면 제거 (`_empty_monthly_stats` 스켈레톤 교체).
  - 활동 0건 시 억지 LLM 호출 방지 및 사서 격려 멘트 반환, `GET /api/v1/health`에 `core_api_connected` 진단 필드 추가.
- [x] **Phase 62: Google Cloud Run 이전 및 Render 레거시 정리**
  - Render Deploy Hook 워크플로우 삭제, 아키텍처 및 환경변수 명세를 Cloud Run / Upstash Redis로 정렬.
- [x] **Phase 61: 테스트 검증 계층화 (Tiered Verification)**
  - `pyproject.toml` 테스트 옵션 최적화 (`-q --tb=short`), 외부 LLM 모킹을 통한 단위 회귀 10초 이내 달성 (중앙값 9.92s).
- [x] **Phase 59: 국립중앙도서관 표지 생존 판본 최우선 선별 및 디폴트 커버 방어**
  - HTTP 200 및 교보 플레이스홀더 배제 판본 우선 채택, `DEFAULT_BOOK_COVER_URL` 안전 폴백.
- [x] **Phase 58: 큐레이터 타임아웃 현실화(15초) 및 비상 폴백 도서 100% 실서지 바인딩**
  - 타임아웃 넉넉하게 확장, 비상 명작 8종에 대해 국립도서관 API를 호출하여 13자리 ISBN/실제 쪽수/표지 완성형 제공.
- [x] **Phase 57: KDC 513.8(미술치료/심리요법) 철학(PHILOSOPHY) 라우팅 SSOT 확립**
  - `map_kdc_to_genre`에 순수 KDC 코드 `513.8` 감지 시 `PHILOSOPHY` 승격 규칙 추가.
- [x] **Phase 50~52: 세션 보안 강화, UUID 정규화 및 바코드 KDC 추출 확장**
  - 회원 네임스페이스 격리, `{member_id}:{uuid}:{persona}` 복합 포맷 파싱 및 바코드 응답 스키마 확장.
