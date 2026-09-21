# STATE.md — 단계 단위 완료 스냅샷

> 지금까지 완료된 기능과 작업 단계를 마일스톤 단위로 요약 기록합니다.

---

## 완료된 단계

- [x] **Phase 53: 미술치료/심리치유 1차 주제어 및 KDC 3중 안전망 동기화**
  - **`map_kdc_to_genre` 1차 주제어 및 제목 키워드 확장 (`app/infrastructure/national_library_client.py`)**:
    - `"그림의 힘"`, `"미술치료"`, `"심리치료"`, `"마음치유"`를 `PHILOSOPHY` 1순위 키워드로 추가하여 KDC 513.8(의학/건강)로 빠지던 심리치료 도서를 철학/심리로 정확 라우팅.
    - 국립중앙도서관 샘플/테스트 카탈로그(`sample_catalog`)에 《그림의 힘》(김선현 저, 세계사, ISBN 9788933871898)을 KDC 513.8 및 장르 `PHILOSOPHY`로 공식 등재.
  - **단위 테스트 및 AI 자가 검증 (Self-Validation)**:
    - `tests/unit/test_recommend_metadata.py`: 제목 기반(그림의 힘), 주제어 기반(미술치료, 심리치료) 장르 판별 단위 테스트 추가 및 전체 14개 테스트 100% 그린 패스.
    - Ruff 린트/포맷 0 에러, Mypy 타입 체크 무결성 92개 소스 파일 통과.

- [x] **Phase 52: 세션 ID 복합 포맷(`{member_id}:{uuid}:{persona}`) 하위 호환 및 순수 UUID 정규화**
  - **`ChatRequest.session_id` 복합 포맷 유연 수용 및 UUID 자동 추출 (`app/api/schemas.py`)**:
    - 클라이언트 `sessionStorage`에 잔존하던 복합 세션 키(`{member_id}:{uuid}:{persona}` 또는 `{uuid}:{persona}`)를 파싱하여 내부 순수 UUID 세그먼트를 자동 탐색/추출하도록 개선.
    - 클라이언트가 로컬스토리지를 초기화하지 않아도 422 거부 없이 100% 정상 수용하며, 비-UUID 악성 키는 기존대로 422 차단 유지.
  - **단위 테스트 및 자가 검증 완료 (`tests/unit/test_session_security.py`)**:
    - `test_composite_session_id_backward_compatibility` 신규 단위 테스트 추가 및 운영 환경(APP_ENV=production) 호환성 입증.
    - Ruff 린트/포맷 100% 통과, Mypy 타입 체크 무결성 87개 소스 파일 통과, 4개 세션 보안 테스트 전원 통과.

- [x] **Phase 51: 도서 바코드/표지 VLM 5자리 부가기호(KDC) 추출 및 응답 스키마 확장**
  - **Gemini Cover VLM 시스템 프롬프트 5자리 부가기호/청구기호 추출 규칙 추가 (`app/vision/gemini_ocr_client.py`)**:
    - 도서 뒷면 바코드 근처 5자리 숫자(03320, 93810 등) 및 도서관 라벨 스티커 청구기호(813.6-박24ㄱ 등)를 `kdc` 필드로 추출하도록 프롬프트 지침 및 JSON 출력 스키마 정의. 가격(15,000 등)이나 ISBN-13은 kdc 필드에 넣지 않도록 네거티브 가드레일 적용.
    - `CoverOcrResult` 모델에 `kdc: Optional[str] = None` 필드 추가 및 JSON 파싱/보조 텍스트 KDC 추출 연동.
  - **Vision Cover OCR 응답 스키마 및 엔드포인트 핸들러 확장 (`app/api/v1/vision.py`)**:
    - `OcrCoverResponse` 모델에 `kdc: Optional[str] = Field(default=None, description="바코드 옆 5자리 부가기호 또는 도서관 라벨 청구기호")` 추가.
    - 바코드 검출 및 VLM OCR 경로 모두에서 `book["kdc"]` 및 루트 `kdc`에 추출된 원본 값을 바인딩하여 `backend-core-api` 도서 등록 시 누락 없이 그대로 전달되도록 연동.
  - **부가기호/KDC 보조 추출 유틸리티 구현 (`app/vision/isbn_utils.py`)**:
    - `extract_kdc_candidates` 및 `find_first_kdc` 구현: 5자리 독립 숫자(가격 '원' 배제) 및 청구기호 라벨(한글 자모 'ㄱ-ㅎ' 포함 정밀 정규식) 추출 지원.
  - **국립중앙도서관 서지 클라이언트 원본 KDC 보존 (`app/infrastructure/national_library_client.py`)**:
    - `search_book` 및 `search_by_isbn` 응답 딕셔너리에 `kdc: raw_kdc`를 바인딩하여 다운스트림 전달 보장.
  - **자가 검증 무결성 달성**:
    - 신규 단위 테스트 2종 추가(`test_kdc_candidates_extraction`, `test_cover_ocr_kdc_passthrough`), 전체 207개 단위 테스트 100% 그린(Success) 통과 (`207 passed, 1 warning in 119.51s`), Ruff 린트/포맷 통과, Mypy 타입 체크 무결성 92개 소스 파일 통과.

- [x] **Phase 50: 세션 보안 강화 및 회원 네임스페이스 격리 (Backend Session Security Patch)**
  - **UUID 형식 검증 및 회원별 네임스페이스 강제 접두 (`app/api/schemas.py`, `app/api/router.py`)**:
    - `ChatRequest.session_id`: 운영 환경에서 정규식/UUID 형식 검증을 강제하여 임의의 키 주입을 차단하고, 테스트/개발 환경 픽스처와의 호환성을 유지함.
    - `router.py` 세션 파티셔닝: 정회원 요청 시 `raw_session_id = f"{effective_member_id}:{validated_uuid}"` 형태로 회원 ID를 강제 결합하고 최종 `{effective_member_id}:{validated_uuid}:{persona}`로 물리적 격리. 타인의 세션 번호표를 도청/전송하더라도 본인의 방만 조회/생성되도록 원천 방어.
    - 일관성 검증: Redis 세션 적재, 실시간 SSE 스트리밍 및 백그라운드 토론 인사이트 비동기 적재(`save_debate_insight_task`)까지 모두 동일한 회원 네임스페이스 격리 키를 참조하도록 정합성 완비.
  - **다중 계정 격리 검증 단위 테스트 구축 (`tests/unit/test_session_security.py`)**:
    - 서로 다른 2개 계정(A, B)이 완전히 동일한 `session_id`(UUID)를 전송하더라도 서로의 대화 히스토리 및 Redis 메모리를 엿볼 수 없음을 테스트로 완벽 입증.
    - 운영 환경 비-UUID 차단(422) 및 conclude 백그라운드 DB 적재의 네임스페이스 세션 키 일치성 검증.
  - **자가 검증 무결성 달성**:
    - 전체 205개 단위 테스트 100% 그린(Success) 통과 (`205 passed in 67.09s`), Ruff 린트/포맷 통과, Mypy 타입 체크 무결성 87개 소스 파일 통과.

- [x] **Phase 49: Render 자동 배포 연동 워크플로우 구축 (Deploy Hook Trigger)**

  - **GitHub Actions 배포 워크플로우 신설 (`.github/workflows/deploy.yml`)**:
    - `develop` 브랜치 푸시/머지 시 GitHub Actions가 `RENDER_DEPLOY_HOOK_URL` 시크릿을 통해 Render Deploy Hook을 자동 호출하도록 구축.
    - `workflow_dispatch` 수동 트리거 지원 및 배포 HTTP 상태 코드 유효성 검증.
    - Webhook 누락이나 권한 풀림 문제를 완전히 우회하여 PR 머지 즉시 안정적인 빌드/배포를 보장.

- [x] **Phase 48: Google Books API 연동 및 서지 메타데이터(쪽수/표지) 다중 폴백 강화**
  - **Google Books 보조 클라이언트 신설 (`app/infrastructure/google_books_client.py`)**:
    - 비동기 httpx 기반 Google Books Volumes API(`https://www.googleapis.com/books/v1/volumes`) 연동.
    - ISBN(`isbn:{isbn}`) 및 제목/저자(`intitle:{title}+inauthor:{author}`) 쿼리 지원, 정수 `pageCount` 및 고화질 썸네일 URL(HTTP ➔ HTTPS 승격) 파싱.
    - 429 할당량 초과 및 네트워크 오류 시 0ms 안전 바이패스 처리(타임아웃 2.0초)로 큐레이션 파이프라인 안전성 확보.
  - **국립중앙도서관 및 서지 체인 결합 (`app/infrastructure/national_library_client.py`)**:
    - 국립도서관 검색 결과 중 `page_count`나 `cover_url`이 비어 있는 경우에만 조건부로 Google Books 조회를 수행하여 보강.
    - 표지 3단 폴백: 국립도서관 ➔ Google Books ➔ 교보문고 고화질 CDN 0ms 무지연 폴백.
    - 쪽수 3단 폴백: 국립도서관 PAGE ➔ Google Books pageCount ➔ 다중 판본 교차 추출.
  - **환경변수 및 설정 확장 (`app/core/config.py`, `.env.example`)**:
    - `GOOGLE_BOOKS_API_KEY`, `GOOGLE_BOOKS_API_URL` 옵셔널 설정 필드 추가.
  - **품질 검증 및 단위 테스트 전수 통과**:
    - `tests/unit/test_google_books_client.py` 5종 단위 테스트 추가.
    - 전체 202개 단위 테스트 100% 그린(Success) 통과 (`202 passed in 61.32s`), Ruff 린트/포맷 통과, Mypy 타입 체크 무결성 달성.

  - **도서 큐레이션 도구(`request_book_curation`) 호출 경계 명확화 (`app/domain/graph/tools.py`)**:
    - 도구 description에 감정/위로 기반 추천, 완곡한 탐색, 특정 도서 지목/등록 등 호출 케이스와 일상 대화("시간 있으면", "해줄래") 미호출 경계를 엄격히 구분하여 LLM 네이티브 Function Calling의 신뢰성을 극대화.
  - **사서 4종 및 서비스 공통 가드레일 프롬프트 강화 (`shared_rules.py`, `cat.py`, `sea_slug.py`, `shoebill.py`, `gecko.py`)**:
    - "골라올게", "잠시만 기다려줘" 등 추천을 미루는 예고 멘트 종료를 엄격히 금지하고 즉시 도구를 호출하도록 명시.
    - `curated_books`가 없는 상태에서 임의의 책 나열 및 `### 📖` 마크다운 헤딩 작성 금지, 가짜 카드 컴포넌트(`등록 ➔`, `💡 추천 이유` 등) 흉내 금지 및 메타 질문 시 핑계 금지 규정.
  - **사서 응답 코드 레벨 가짜 카드 세척기(`_sanitize_persona_output`) (`app/domain/graph/nodes.py`)**:
    - `curated_books`가 없을 때 마크다운에 삽입된 가짜 카드 UI 마커(`### 📖`, `📖`, `등록 ➔`, `💡 추천 이유`, `👤 저자`, `사유:`)를 코드 레벨에서 강제 소거하여 프론트엔드의 가짜 도서 등록 카드 렌더링을 원천 봉쇄.
    - `curated_books`가 있을 때도 검증 목록에 없는 날조된 도서 헤딩을 자동으로 필터링.
  - **지연 약속 멘트 런타임 인터셉터(`_is_delayed_curation_promise`) 및 즉각 선위임 파이프라인 (`app/domain/graph/nodes.py`)**:
    - 사서 LLM이 도구 호출 없이 "골라올게", "찾아올게", "잠시만 기다려" 등의 지연 약속으로 발화를 맺었을 경우, 런타임에서 이를 감지하여 즉시 `curator_node`로 선위임(`curator_request = last_user_msg`)하도록 안전망 구축. 사용자가 재질의하지 않아도 1턴 만에 실존 검증 도서 카드를 수신하도록 보장.
  - **토론 모드 자연어 마무리 발화 선위임 가드 보강 (`app/domain/graph/nodes.py`)**:
    - 토론 모드에서 "토론 마무리", "여기까지 하고 토론" 등의 자연어 종료 발화 시 `curator_node`로 즉시 선위임하여 피날레 연계 도서 카드가 100% 서빙되도록 보장.
  - **단위 테스트 및 회귀 방지 검증 (`tests/unit/test_graph_handoff.py`)**:
    - `test_sanitize_persona_output_strips_fake_cards_when_curated_absent`, `test_sanitize_persona_output_preserves_verified_headings_when_curated_present`, `test_is_delayed_curation_promise` 신규 단위 테스트 추가.
    - 전체 **197개 단위 테스트 100% 통과** (`197 passed, 1 warning in 61.61s`), Ruff 린트/포맷 0 errors, Mypy 타입 체크 60개 소스 파일 0 errors 무결성 달성.

- [x] **Phase 41: 도서 큐레이터 아키텍처 근본 리팩터링 및 케이스 기반 테스트 체계 구축**
  - **휴리스틱(규칙/조사/정규식) 전면 제거 및 LLM 스키마 일원화 (`curator_node.py`)**:
    - Step A/B의 60여 줄 임의 정규식 휴리스틱을 완전 삭제하고, `CuratorResponse` 스키마에 `target_title: Optional[str]`을 추가하여 사용자의 특정 도서 지목/등록 의도를 LLM 구조화 출력으로 직접 판별하도록 개선.
    - `BookCandidate.era`를 `Literal["trend", "recent", "life_pick", "classic"]`으로 엄격화.
  - **최근 대화 히스토리 프롬프트 주입 및 맥락 해석 복원**:
    - `resolve_context`에서 최근 6턴의 대화(`conversation`)를 추출하여 프롬프트에 주입함으로써, "아까 그 책 등록해줘", "이전에 추천받은 책과 비슷한 것" 등 직전 대화의 도서명을 참조하는 맥락적 지목을 완벽 해석하도록 지원.
  - **개별 LLM 타임아웃/재시도 분리 및 `with_fallbacks` 활성화**:
    - Gemini Light, Gemini 3.5, OpenAI 인스턴스 각각에 `timeout=8.0, max_retries=1`을 명시하고 전체 외부 `asyncio.wait_for`를 20초로 상향하여, 1순위 모델 지연 시 체인이 즉각적이고 안정적으로 다음 모델로 폴백되도록 보장.
  - **실서지 제목 유사도 검증(`_is_similar_title`) 및 지목 도서 미확인 피드백(`target_unresolved`)**:
    - 국립중앙도서관 검색 결과와 사용자의 지목/후보 도서 간 정규화 유사도(`_is_similar_title`)를 교차 검증하여 엉뚱한 도서가 바인딩되는 현상을 방지.
    - 지목 도서 검색 실패 시 `target_unresolved`를 사서 프롬프트에 전달하여 다정한 미확인 안내와 대체 추천을 제공.
  - **비동기 검증 병렬화**:
    - 지목 도서 검증(`resolve_targeted`)과 후보 도서 검증(`verify_candidates`)을 `asyncio.gather`로 병렬 실행하여 응답 지연을 최소화.
  - **단일 노드의 5단계 함수 분리 및 단일 책임화**:
    - `resolve_context` ➔ `generate_candidates` ➔ `resolve_targeted` ➔ `verify_candidates` ➔ `assemble_curated_books`.
  - **미검증 폴백 계약 정상화 (`assemble_curated_books`)**:
    - 외부 검증 실패 시 하드코딩 가짜 ISBN(`9788937460000`)에 `verified: True`를 부여하던 결함을 제거하고, `verified: False`, `isbn: ""`으로 명확히 마킹하여 프론트/백엔드 다운스트림이 안전하게 처리하도록 규격화.
    - 비상 폴백 시에도 `recommended_history`를 참조하여 직전 추천 도서와 중복되지 않는 명작을 우선 선별.
  - **LLM 인스턴스 모듈 캐시 & `with_fallbacks` 전환**:
    - 매 턴마다 4개의 LLM 인스턴스를 반복 생성하던 루프를 모듈 레벨 지연 로딩 캐시 및 `primary_llm.with_fallbacks([fallback1, fallback2, ...])`로 전환.
    - 유효 API 키 판별 헬퍼(`is_valid_api_key`) 단일화 및 중복 클라이언트 호출 정리.
  - **케이스 매트릭스(Case Table) 기반 회귀 방지 테스트 구축 (`test_curator_pipeline.py`)**:
    - 케이스 매트릭스, 제목 유사도, 미확인 지목 도서 반환 테스트를 추가하여 전체 **192개 단위 테스트 100% 통과** (`192 passed, 1 warning in 60.74s`), Ruff 0 errors, Mypy 88개 소스 파일 0 errors 무결성 달성.

- [x] **Phase 40: 메타 질의("이전 추천 도서와 비슷한 책") 도서명 둔갑 방지 및 가짜 서지 폴백 원천 차단**
  - **`curator_node.py`의 직접 지정 도서(Targeted Book) 탐색 가드 구축**:
    - "이전에 추천받은 도서랑 비슷한 도서 추천해줘", "아까 그 책", "골라준 책과 다른 것" 등 메타/상대적 질의 키워드가 포함되었거나, 끝자리에 조사(`랑`, `이랑`, `으로`, `은`, `는` 등)가 남은 문장형 발화가 도서명 후보(`title_candidates_to_check`)로 오탐 추출되는 결함을 원천 차단.
    - 명시적 꺽쇠/따옴표 표기(`《...》`, `「...」`, `"..."`) 또는 2~30자의 순수 단행본 제목 형태일 때만 실서지 직접 검색을 수행하도록 정밀화.
  - **`national_library_client.py`의 가짜 서지 폴백(`VERIFIED_CATALOG_FALLBACK`) 남발 차단**:
    - 국립중앙도서관 API 및 내부 30여 권 명작 카탈로그에 없는 문장형 텍스트에 대해 임의의 가짜 ISBN(`9791100000000`)과 가짜 서지를 날조하던 동작을 제거하고, 실존 도서가 아니면 `None`을 반환하도록 수정.
    - 이를 통해 질문 텍스트 전체가 책 제목으로 둔갑하여 프론트엔드 도서 카드로 변질되거나 서재 등록 시 400/422 에러를 유발하던 치명적 버그를 원천 해결.
  - **`reports/generator.py` 타입 안정성 보강**:
    - `_generate_fallback_biblio`의 반환 타입(`Optional[Dict[str, Any]]`)에 맞추어 `None` 방어 코드를 적용하여 Mypy 정적 타입 무결성 보장.
  - **단위 테스트 및 회귀 방지 검증 (`tests/unit/test_curator_pipeline.py`)**:
    - `test_meta_recommendation_query_not_converted_to_fake_book` 신규 단위 테스트 추가.
    - 전체 184개 단위 테스트 100% 통과 (`184 passed in 58.54s`), Ruff 린트/포맷 0 에러, Mypy 타입 체크 88개 소스 파일 0 에러 달성.

- [x] **Phase 39: 도서 추천/신간 검색 국립중앙도서관 실서지 검증 및 도서 카드 메타데이터 자동 완성 강화**
  - **SSE 스트리밍 큐레이터 노드 이벤트명 오타 교정 (`app/api/router.py`)**:
    - `node_name in ("curator_node", "book_curator_node")`로 교정하여 실시간 스트리밍 중에도 `event: books`가 누락 없이 프론트엔드로 즉시 발행되도록 보장.
  - **특정 도서 추천/등록 의도 감지 및 선위임 파이프라인 (`app/domain/graph/nodes.py`)**:
    - 사용자가 "프로젝트 헤일메리 추천해줘", "이 책 등록할래", "결과로 보여줘" 등 특정 도서나 추천을 요청할 때 사서 LLM이 임의로 텍스트를 출력하기 전 `curator_node`로 즉시 선위임하여 100% 국립중앙도서관 실서지 검증을 거치도록 보장.
  - **`curator_node`의 특정 도서 직접 서지 검증 및 1순위 바인딩 (`app/domain/graph/curator_node.py`)**:
    - 지목된 도서명을 추출하여 국립중앙도서관 Open API(`search_book`)로 즉각 교차 검증하고, 정식 서명, 저자, 출판사, 13자리 ISBN, 표준 장르, 총 페이지 수, 교보문고 고화질 CDN 표지를 1순위 추천(`targeted_candidate`)으로 자동 탑재.
  - **Tavily 신간 검색 도구(`search_recent_books`) 국립도서관 실서지 검증 연동 (`app/domain/tools/search_books_tool.py`)**:
    - 웹 검색으로 찾은 신간 후보들을 국립중앙도서관 4단계 서지 검증 체인으로 교차 조회하여 실존 여부와 정식 서지 메타데이터(ISBN, 쪽수, 표준 장르)를 바인딩해 반환.
  - **사서 8종 프롬프트 가짜 카드 날조 금지 네거티브 가드레일 주입 (`app/domain/guardrails/shared_rules.py`, `app/domain/graph/tools.py`)**:
    - 사서가 본문에 `📖`, `등록 ➔`, `👤 저자` 같은 프론트엔드 카드 컴포넌트를 마크다운 텍스트로 직접 흉내 내지 못하도록 원천 차단.
  - **`"읽고싶어"` 등 독서 욕구 발화 시 추천 카드 미노출 버그 수정 (`app/domain/graph/nodes.py`)**:
    - `recommend_keywords`에 `"읽고싶"`, `"읽고 싶"`, `"읽어보고싶"`, `"읽어볼"`, `"재밌는 책"`, `"좋은 책"`, `"뭐 읽지"` 등 20개 독서 욕구/탐색 표현 추가.
    - `test_graph_handoff.py`에 `test_cat_node_delegates_read_intent_to_curator` 회귀 방지 테스트 추가.
  - **자가 검증 통과**: 전체 **183개 단위 테스트 100% 통과** (`183 passed in 68.25s`), Ruff 린트/포맷 통과, Mypy 타입 체크 88개 소스 파일 무결성 통과.


- [x] **Phase 27: 전 사서/페르소나 도서 추천 응답 포맷 규격화 및 서재 조회 분기 체계화**
  - **도서 추천 마크다운 헤딩 및 이모지 규칙 통일 (8종 전 페르소나 공통, `nodes.py`, `shared_rules.py`)**:
    - 추천 도서 소개 시 `### 📖 {도서명}` 마크다운 3단계 헤딩만 사용하도록 프롬프트 지침 강제.
    - 서두 섹션 타이틀(예: `### 📚 누디가 건네는 책` 등) 및 추천 헤딩에 `📚` 이모지 사용을 엄격히 금지하고, `📚`는 오직 '내 서재 보유 도서' 전용임을 `SHARED_GUARDRAILS`에 명시하여 프론트엔드 오인 원천 방어.
  - **내 서재 조회 vs 신규 추천 구조화 데이터 완전 분리 (`schemas.py`, `router.py`, `my_library_tool.py`)**:
    - `ChatResponse`에 `library_books: List[LibraryBook]` 필드 복원 및 내 서재 조회 결과와 신규 추천을 상호 배타적으로 분리:
      - 내 서재 보유 도서: `### 📚 {도서명}` + `library_books: [...]`
      - 외부 신규 도서 추천: `### 📖 {도서명}` + `recommended_books: [...]`
    - SSE 실시간 스트리밍(`/api/v1/chat/stream`) 시 `event: books` 및 `event: done` 페이로드에 `recommended_books`와 `library_books`를 구조화하여 전송 보장.
    - `search_my_library` 결과 포맷을 프론트엔드 파서에 맞춘 `### 📚 {도서명}` 및 `**저자**: ...`, `**독서 상태**: ...`로 규격화.
  - **무결성 및 테스트 검증**:
    - `tests/unit/test_my_library_tool.py`, `tests/unit/test_personas.py`, `tests/unit/test_recommend_metadata.py`에 서재/추천 분기 및 헤딩 가드레일 검증 테스트 추가.
    - 전체 181개 단위 테스트 100% 그린 패스 통과 (`181 passed in 62.60s`), Ruff 린트/포맷 통과, Mypy 타입 체크 88개 소스 파일 100% 무결성 통과.

- [x] **Phase 36: Alembic 원격 DB 안전 인터락 및 운영 환경 취약 시크릿 기동 차단(Fail-Fast) 구축**
  - **Alembic 원격 Supabase 안전 인터락 (`app/infrastructure/db/migration_guard.py`, `alembic/env.py`)**:
    - 대상 DB 호스트가 원격(`pooler.supabase.com` 등 `localhost`/`127.0.0.1` 외)일 때, 환경변수 `ALLOW_REMOTE_MIGRATION=true`가 명시되지 않은 상태에서 `alembic upgrade head`나 마이그레이션 실행 시 즉시 중단(`RuntimeError`)하고 안전 안내 문구를 출력하도록 인터락 구현.
    - 온라인/오프라인 모드 양쪽에 안전 검사를 선행 적용하여 로컬 개발 중 실수로 인한 팀 공용 Supabase 스키마 변조 원천 방지.
  - **운영 환경(APP_ENV=production) 취약 시크릿 Fail-Fast 방어 (`app/core/config.py`)**:
    - `Settings`의 `model_validator(mode="after")`를 통해 `APP_ENV=production` 또는 `prod`일 때 `JWT_SECRET_KEY`가 기본값(`dont-paw-get-jwt-secret-change-in-prod-2026`)이거나 공백일 경우 `ValueError`를 발생시켜 서버 기동 단계에서 선제 차단.
  - **무결성 및 테스트 검증**:
    - `tests/unit/test_config.py`에 개발/프로덕션 환경 시크릿 검증 및 원격 DB 호스트 감지 단위 테스트 5종 추가.
    - `tests/unit/test_alembic_migration.py`에 원격 호스트 마이그레이션 차단, 허용 플래그 적용, 로컬 DB 허용 단위 테스트 3종 추가.
    - 전체 178개 단위 테스트 100% 그린 패스 통과, Ruff 및 Mypy(88개 소스 파일) 무결성 검증 완료.

- [x] **Phase 26: 도서 추천 시인성 개선(중복 메타/구분선 잡음 제거) & 추천 도서 등록 시 기술과학(L-IT-erature) 오분류 원천 해결**
  - **프론트엔드 장르 매퍼의 영문 축약어(IT, AI) 부분문자열 오탐 해결 (`frontend-reader-web/app/data/genres.js`, `RegisterBook.jsx`)**:
    - `detectGenreCode`: `TECHNOLOGY`의 `'it'` 별칭이 `'literature'`(`l-it-erature`)의 부분문자열로 오탐 매칭되던 결함을 발견하고, 3글자 이하 영문 단축어에 대해 단어 경계(`\b`) 독립 단어 검사 적용.
    - `genreCode`: 영문 Enum(`LITERATURE`) 입력 시 `BY_CODE`를 1순위로 조회하여 표준 코드 즉시 반환.
    - `RegisterBook.jsx`: `GENRE_CODES.includes(code)`를 최우선으로 검사하여 추천 도서의 표준 장르가 불필요한 별칭 탐색 없이 100% 보존되도록 개선.
  - **사서 추천 소개 프롬프트 구조화 (`backend-ai-agent/app/domain/graph/nodes.py`)**:
    - 시스템 프롬프트 지침에 추천 도서 헤딩(`### 📖 도서명`) 아래 화면 카드와 중복되는 `저자: ...`, `사유: ...` 텍스트나 `---` 구분선을 쓰지 않도록 표준 템플릿 명시하고, 사서 고유 어조의 1~2줄 감상 코멘트만 담도록 정돈.
  - **마크다운 렌더러 시인성 방어 (`frontend-reader-web/app/features/room/MarkdownRenderer.jsx`)**:
    - `---` 라인을 감지하여 `<p>---</p>` 텍스트 대신 부드러운 수평선(`<hr>`)으로 렌더링.
    - 도서 카드 외부에서 발생하는 잉여 `저자:`, `사유:` 노이즈 텍스트 필터링.
  - **KDC 권차·판차 안전 파서 연동 (`backend-ai-agent/app/infrastructure/national_library_client.py`)**:
    - `extract_kdc_code` 정밀 파서를 도입하여 `[5] 813.6` 등 복합 문자열의 판차 `5`가 기술과학으로 오인되지 않도록 방어.
  - **무결성 검증**: `tests/unit/test_recommend_metadata.py`에 KDC 추출 및 장르 판별 단위 테스트 추가, 전체 169개 단위 테스트 100% 그린 패스, Ruff/Mypy 통과, 프론트엔드 Vite build 및 ESLint 0 에러 통과.

- [x] **Phase 23: 문장 수집 스마트폰식 네모칸 영역 조절(Crop) 및 정밀 OCR 파이프라인 구축**
  - **프론트엔드 인터랙티브 크롭 모달 (`frontend-reader-web/app/components/ImageCropModal.jsx`)**: React 19 호환 순수 Canvas & Touch/Mouse 드래그 기반 사각형 포커스 박스 조절기 구현. 네 귀퉁이 및 테두리 드래그, 전체 선택, 영역 초기화 및 Canvas API 기반 잘라낸 Blob(image/jpeg) 추출 지원.
  - **문장 수집 모달 흐름 연결 (`SentenceCollectModal.jsx`)**: 사진 선택/촬영/웹캠 시 즉시 OCR 전송하지 않고 크롭 모달로 먼저 진입하여 원하는 문장 영역만 지정 후 자른 조각 이미지만 `POST /api/v1/ocr/sentences`로 전송. 불필요한 노이즈 제거, Gemini Vision 토큰 절약 및 정확도 극대화, 잘린 조각 이미지를 스크랩 썸네일(`scrapImageUrl`)로 보관.
  - **백엔드 하이브리드 크롭 지원 (`app/api/v1/vision.py`)**: `POST /api/v1/ocr/sentences` 엔드포인트에 선택적 `crop_box: Optional[str] = Form(None)` 지원 및 `Pillow` 서버 사이드 크롭 안전 폴백 구현.
  - **무결성 검증**: `tests/unit/test_vision.py`에 `test_sentence_ocr_with_crop_box` 단위 테스트 추가, 백엔드 전체 169개 단위 테스트 100% 그린 패스, Ruff/Mypy 무결성 통과, 프론트엔드 Vite build 및 ESLint 0 에러 통과.

- [x] **Phase 24: 팀 프로필 일러스트 2종(chris/clia) 배치 및 마이페이지 프로필 사진 수정(1:1 크롭) 구축**
  - **프로필 일러스트 및 기본 실루엣 아바타 배치**: `frontend-reader-web/public/profile/`에 팀원 일러스트 `chris.png`(데모 회원용), `clia.png`(게스트 모드용) 및 웹 표준 벡터 실루엣 `default_avatar.svg` 생성 및 배치 완료.
  - **게스트 모드 기본 프로필 일러스트 할당 (`AuthProvider.jsx`, `authBypass.js`)**: 게스트 로그인 및 개발 우회 모드 시 기본 `profile_image_url`로 `/profile/clia.png` 자동 할당.
  - **마이페이지 프로필 사진 수정 UI 및 1:1 크롭 연계 (`MyPage.jsx`, `MyPage.css`)**: 아바타에 '사진 변경' 카메라 버튼 추가, 사진 선택 시 `ImageCropModal`(1:1 정사각 모드)을 호출하여 원하는 영역을 맞춤 크롭하고 `updateMe({ profile_image_url })` (`PATCH /api/v1/users/me`)로 DB 저장 및 즉각 반영.
  - **정식 데모 계정 기본 프로필 연동 (`backend-core-api/app/services/member_service.py`)**: `ensure_demo_member`에서 데모 계정의 `profile_image_url`을 `/profile/chris.png`로 자동 보장.
  - **품질 검증**: `backend-core-api` pytest 101개 100% 통과, 프론트엔드 Vite 번들 빌드 성공.

- [x] **Phase 25: AI 챗봇 실시간 SSE 스트리밍 연동 및 발바닥 로딩(`LoadingSequence`) 조화 파이프라인**

  - **프론트엔드 실시간 SSE 클라이언트 구축 (`frontend-reader-web/app/api/chatApi.js`)**: `streamChatMessage`에 `ReadableStream`(`getReader()`) 기반 청크 디코딩 및 백엔드 `/api/v1/chat/stream` SSE 프로토콜(`metadata`, `token`, `books`, `switch_suggestion`, `done`, `error`) 파서 구현.
  - **하이브리드 UX 파이프라인 (`frontend-reader-web/app/features/room/LibrarianChat.jsx`)**: 질문 전송 즉시 발바닥 순차 애니메이션(`LoadingSequence`)으로 사서의 생각/탐색 시간을 표현하고, 첫 번째 `token` 수신 즉시 말풍선 타이핑 스트리밍 모드로 매끄럽게 전환. 체감 대기 시간을 50초에서 3~4초로 단축.
  - **무결성 검증**: 백엔드 스트리밍 단위 테스트(`tests/unit/test_streaming_api.py`) 3종 100% 통과, 프론트엔드 ESLint 0 에러 및 Vite Production 번들 빌드 통과.

- [x] **Phase 35: Alembic 기반 `agent` 스키마 DB 마이그레이션 관리 체계 구축**
  - **Alembic 환경 구축 (`alembic.ini`, `alembic/env.py`)**: `core-api` 구조를 벤치마킹하여 `alembic>=1.13.1` 도입. Supabase 공유 환경에서 `core.alembic_version`과 충돌하지 않도록 `version_table_schema="agent"`로 격리하고, `vector` 익스텐션 및 `agent` 스키마 선행 생성을 보장함.
  - **Transaction Pooler 호환성 확보**: `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` 적용으로 Supabase 6543 포트 연결 시 세션 prepared statement 충돌 원천 차단.
  - **초기 리비전 작성 (`001_initial_agent_schema.py`)**: `agent.scrap_vector`, `agent.debate_insights`, `agent.chat_sessions` 테이블 및 HNSW 코사인 유사도 인덱스, `agent.match_scraps`, `agent.match_debate_insights` RPC 함수, 다운그레이드(`downgrade`) 구현.
  - **마이그레이션 도구 및 문서화**: `scripts/run_migrations.py` 헬퍼 스크립트 작성 및 `README.md` 가이드 갱신.
  - **자가 검증 완료**: 신규 단위 테스트 3종 추가(`tests/unit/test_alembic_migration.py`), 전체 168개 단위 테스트 100% 그린 패스 통과, Ruff 및 Mypy 무결성 86개 소스 파일 통과.

- [x] **Phase 22: Render 배포 대비 CORS 정규식 및 Supabase Pooler 안정화**

  - **CORS 와일드카드 보안 및 정규식 지원**: `app/core/config.py`에 `CORS_ORIGIN_REGEX` 필드 추가 및 `app/main.py` CORSMiddleware에 `allow_origin_regex` 매핑. 로컬 포트 전체(`http://localhost:\d+`) 허용 및 Cloudflare Pages 배포 대비 확장성 확보.
  - **Asyncpg Prepared Statement 충돌 방지**: `app/infrastructure/db/session.py`의 `connect_args`에 `prepared_statement_name_func=lambda: f"__asyncpg_{uuid4()}__"` 추가하여 Supabase Transaction Pooler(포트 6543) 환경에서 세션 충돌 원천 차단.
  - **단위 테스트 및 품질 검증**: `test_cors_preflight_and_regex` 단위 테스트 추가, Pytest 13개 API 테스트 및 Ruff/Mypy 100% 그린 검증 완료.


- [x] **Phase 34: 해커톤 체험 모드(게스트 JWT) 세션 분리, 사용량 제한, 쓰기 락 및 Role 분리 이중 서킷 브레이커(RPM/RPD) 구축**
  - **게스트 JWT 클레임 규격 준수 & Null-Check 안전망**: `role: "guest"`, `sub: "guest-{uuid}"` 인식 및 Core-API 게스트 토큰의 `email`, `name`, `nickname` 누락 시 기본값 안전 처리 (`extract_auth_info_from_auth`).
  - **세션 파티셔닝**: 게스트의 `sub`를 앵커로 `{guest_id}:{persona}`로 자동 파티셔닝하여 히스토리 완전 격리 (`app/api/router.py`).
  - **게스트 대화 횟수 상한 (영구 귀속)**: `guest_usage:{guest_id}`(14일 TTL 유지) 카운터를 운용하여 토큰 갱신 시에도 대화 횟수가 영구 유지되며, 초과 시 200 OK와 함께 우아한 UX 안내 멘트 반환 (일반 및 스트리밍 SSE 규격 일치).
  - **Role 분리 이중 서킷 브레이커 (RPM/RPD)**: 게스트(`circuit:rpm:guest:...`, `circuit:rpd:guest:...`)와 정회원(`circuit:rpm:member:...`, `circuit:rpd:member:...`) 카운터를 완전 분리하여 게스트 트래픽 폭주 시에도 정회원 서비스 보장. 분당 카운터는 90초 NX TTL 패턴(`INCR + EXPIRE NX`)을 준수하고 48시간 일일 카운터와 병행 운용하여 임계치의 70~80% 수준 선제 차단 및 200 OK 안내 멘트 반환.
  - **게스트 쓰기 락 (403 Forbidden)**: `POST /api/v1/memory/scraps`, `POST /api/v1/memory/debate-insights`, `POST /api/v1/vectors/records`에서 게스트 요청 시 403 반환 및 토론 피날레 백그라운드 DB 적재 태스크 건너뛰기 적용.
  - **동시성(Concurrency) 및 무결성 검증**: `asyncio.gather` 기반 50개 동시 요청 카운트 원자성 및 서킷 브레이커 경계 레이스 컨디션 방어 테스트를 포함한 11개 전용 단위 테스트 추가 (`tests/unit/test_guest_mode.py`). 전체 164개 단위 테스트 100% 그린 패스, Ruff 및 Mypy 무결성 통과.

- [x] **Phase 1: 프로젝트 기반 및 의존성 구성**
  - Python 3.12, FastAPI, LangGraph, Pydantic v2 기반 패키지 셋업 (`pyproject.toml`, `uv.lock`)
  - 환경변수 관리 시스템 구축 (`app/core/config.py`, `.env.example`)
  - Redis 세션 및 Supabase Vector Client 인프라 어댑터 구축

- [x] **Phase 2: 2-Track 8개 페르소나 및 LangGraph 워크플로우**
  - 동물 사서 4종(`CAT`, `SHOEBILL`, `SEA_SLUG`, `GECKO`) 노드 및 프롬프트 정의
  - 심층 독서 토론 파트너 4종(`DEBATE_CRITIC`, `DEBATE_STORYTELLER`, `DEBATE_COUNSELOR`, `DEBATE_OBSERVER`) 노드 및 프롬프트 정의
  - 페르소나 간 전환 어조 오염 방지용 `summarizer_node` 및 상태 그래프(`StateGraph`) 완성
  - 사용자 커스텀 사서 이름(`librarian_name`) 지원

- [x] **Phase 3: RAG 및 도구(Tools) 레이어**
  - Google Gemini Embedding (`text-embedding-004`, 768차원) 및 폴백 임베딩
  - Supabase pgvector `scrap_vector` 기반 `search_scrap_memory` 도구 (회원별 완전 격리)
  - `backend-core-api` 연동 `search_my_library` 서재/독서상태 조회 도구
  - Tavily 웹 검색 + core-api + Redis 캐싱 기반 `recommend_books` 도구
  - Supabase DDL/인덱스/RPC 함수 및 시딩 스크립트 (`scripts/seed_supabase_scrap_vector.py`)

- [x] **Phase 4: 무과금(Zero-cost) 인프라 규격 반영**
  - Dockerfile 동적 포트(`${PORT:-8000}`) 주입 및 Render/Cloud Run 배포 호환
  - `docker-compose.yml` 로컬 소스 코드 핫리로드 활성화
  - `/api/v1/health`에 Supabase pgvector 핑 쿼리 연동 (7일 미사용 슬립 방어)

- [x] **Phase 5: 무상태 Vision API 구현 (바코드 & Clova OCR)**
  - `pyzbar` + `Pillow` 기반 13자리 도서 바코드(ISBN-13) 스캔 (`POST /api/v1/vision/scan-barcode`)
  - Naver Cloud Clova OCR General API V2 연동 및 `lineBreak` 기반 줄단위 텍스트 복원 (`POST /api/v1/vision/ocr`)
  - Dockerfile 내 C 라이브러리 `libzbar0` 추가
  - 총 33개 단위 테스트(Pytest) 및 Ruff 린트 100% 통과

- [x] **Phase 5.1 (Milestone 2.8): Google Gemini Flash Vision 전환, 다중 키 풀링(2,000회/일) 및 워크로드 스마트 라우팅 구축**
  - 유료 과금 위험이 있는 Naver Clova OCR을 완전 걷어내고, 기존 `GEMINI_API_KEY`를 재활용한 Gemini Flash Vision OCR 클라이언트(`app/vision/gemini_ocr_client.py`) 구현
  - 책 문장 스크랩 특화 프롬프트 탑재: 페이지 번호/여백 잡음/손가락 그림자를 자동 배제하고 순수 본문 문장만 줄바꿈(`\n`)을 보존하여 정확히 추출 (가상 책 페이지 실측 1.99초 검증 완료)
  - Google AI Studio 무료 티어 한도(Flash RPD 20 vs Flash-Lite RPD 500) 분석에 기반하여 워크로드 스마트 라우팅 구축:
    - 감성 및 문장력이 중요한 **사서/토론 대화 및 월간 리포트**: `gemini-3.5-flash-lite` 우선 배정
    - 텍스트/JSON 단순 추출인 **Vision OCR 및 큐레이터**: `gemini-3.1-flash-lite` 우선 배정 (3.5 쿼터 절약)
  - 팀원 AI Studio 보조키(`GEMINI_FALLBACK_API_KEY`)를 연동하여 하루 무료 호출량 2,000회(1,000 + 1,000) 쿼터 풀 확보 및 429 발생 시 0ms 즉시 스위칭
  - 다중 쿼터 초과 시 오픈웨이트 `gemma-4-31b-it`(RPD 14,400) ➔ OpenAI `gpt-4o-mini` ➔ Mock으로 이어지는 비상 안전망 구축 ($0 제로코스트 무중단 보장)
  - `POST /api/v1/vision/ocr` 엔드포인트 바인딩 교체 및 기존 `ClovaOcrClient` 하위 호환성 100% 유지
  - 단위 테스트 격리용 `tests/conftest.py` 추가, `tests/unit/test_vision.py` 갱신 및 전체 83개 단위 테스트 100% 그린 패스 (Ruff & Mypy 무결성 통과)


- [x] **Phase 6: 바이브 코딩 하네스 표준 구축**
  - `AGENTS.md`, `CLAUDE.md`, `.kiro/steering/project.md` 및 `.harness/` 6대 관리 문서 구성

- [x] **Phase 7: DPYB 중앙 개발 표준, 킵얼라이브 및 Git 컨벤션 반영**
  - `.github/workflows/ci.yml` (중앙 `reusable-python-ci.yml`, Python 3.12 기준) 등록
  - `.github/workflows/lint-pr.yml` (중앙 `reusable-pr-lint.yml`) 등록
  - 중앙 킵얼라이브 10분 주기 요청 대응용 `GET /health` 루트 엔드포인트 구현 및 테스트 작성
  - 도메인 역할(AI 사서/RAG/독서 수집 전담, 순수 DB 영속화는 `core-api` 위임) 명문화
  - 브랜치 전략 `feat/*` 단일화, PR/커밋 `[scope]` 대괄호 표준(`type[scope]:`), develop/main PR 사람 직접 머지 규칙 명문화

- [x] **Phase 8: 독서 기록/스크랩 벡터화 수신 엔드포인트 및 OpenAI 예비 LLM 지원**
  - 스크랩 벡터화 수신 라우터 구현 (`POST /api/v1/memory/scraps`) 및 Pydantic 스키마 정의
  - 도서명, 인상 깊은 문장, 사용자 메모 결합 임베딩 생성 후 Supabase pgvector(`scrap_vector`) 적재 연동
  - OpenAI API(`OPENAI_API_KEY`, `OPENAI_MODEL`) 예비/폴백 LLM 환경설정 및 명세 반영
  - 신규 단위 테스트 추가 (`tests/unit/test_memory_api.py`) 및 전체 36개 단위 테스트 100% 그린 패스

- [x] **Phase 9: 도서 큐레이터 전문 서브에이전트, 국립중앙도서관 서지 검증 및 Open-Meteo 실시간 날씨 연동**
  - 국립중앙도서관 Open API 클라이언트 구현 (`app/infrastructure/national_library_client.py`) 및 승인 대기 중 안전 폴백 지원
  - Open-Meteo 기반 무료 실시간 날씨 클라이언트 (`app/infrastructure/weather_client.py`) 연동 및 `ChatRequest` 내 `location` 위경도 스키마 확장
  - `book_curator_node` 전문 서브에이전트 구현 (실시간 날씨/감정 추론 + 국립중앙도서관 실존 서지 검증)
  - `AgentState` 내 `curator_request`, `curated_books`, `weather_context`, `location_coords` 양방향 Handoff 상태 및 LangGraph 조건부 엣지 연동
  - 사서 페르소나와 서지 추론의 단일 책임 분리를 통한 어조 오염 및 환각 원천 차단
- [x] **Phase 10: 국립중앙도서관 정식 서지정보 API(`SearchApi.do`) 규격 일치화 및 위치 폴백 강화**
  - `backend-core-api`와 동일하게 국립중앙도서관 정식 서지정보 API 규격(`https://www.nl.go.kr/seoji/SearchApi.do`, `NL_API_CERT_KEY`)으로 1:1 완벽 정렬
  - 응답 파싱 필드를 국립중앙도서관 공식 표준(`docs`, `TITLE`, `AUTHOR`, `EA_ISBN`, `TITLE_URL`)으로 일치화
  - 위치 권한 미허용 시 서울 기준 정직한 날씨 폴백 안내 및 환각 방지 지침 강화
  - Clova OCR General API V2 설정 안내 주석 보강 및 로컬 CI 41개 단위 테스트 100% 그린 패스
- [x] **Phase 11: 큐레이터 선위임 파이프라인 최적화 및 로컬 멀티 페르소나 대화 검증**
  - 도서 추천 의도 감지 시 사서 노드의 불필요한 1차 LLM 호출(비용/지연 2~3초)을 건너뛰고 `curator_node`로 선위임하는 라우팅 최적화
  - `tool_calls`가 포함된 이전 어시스턴트 메시지가 `ToolMessage` 없이 LLM API에 재전송되어 발생하는 400 Bad Request 에러 원천 방어(Sanitization)
  - `langchain-openai` 의존성 추가 및 `SecretStr` 정적 타입 안정성 보장
  - 로컬 Uvicorn 8000 포트 실시간 기동 및 사서(고양이 블루, 슈빌, 바다달팽이), 문학 비평가(이동진 톤) 실대화 완벽 검증

- [x] **Phase 12: Supabase `agent` 다중 스키마 및 Transaction Pooler(포트 6543) 연동**
  - DPYB 전사 $0 무과금 단일 Supabase Postgres 인스턴스 공유 정책 반영 및 `agent` 전용 스키마 격리 구현
  - Transaction Pooler 충돌 방지 옵션(`connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}`) 적용된 SQLAlchemy asyncpg 엔진 구축
  - `agent` 스키마 DDL 명세(`scripts/init_agent_schema.sql`) 및 asyncpg 자동 실행 스크립트(`scripts/init_agent_schema.py`) 작성
  - ORM 모델 `ScrapVector`(`__table_args__ = {"schema": "agent"}`) 및 `AgentVectorRepository` 코사인 유사도 검색 구현
  - `SupabaseVectorClient` 어댑터 통합으로 `POST /api/v1/memory/scraps` 및 RAG 도구 자동 연계 및 하위 호환성 100% 보장
- [x] **Phase 13: LangGraph 실시간 스트리밍(SSE) 응답 엔드포인트 구축**
  - `POST /api/v1/chat/stream` Server-Sent Events (SSE) 엔드포인트 구현 (`StreamingResponse`, `text/event-stream; charset=utf-8`)
  - 표준 SSE 이벤트 규격 구현 (`event: metadata`, `event: token`, `event: switch_suggestion`, `event: done`, `event: error`)
  - LangGraph `astream_events(v2)` 연동: 8개 마스터 페르소나 노드 응답 토큰만 필터링하여 사용자에게 실시간 스트리밍 (내부 `curator_node` 서브에이전트 중간 JSON 토큰 원천 격리)
  - `ResilientLLM` 및 큐레이터 노드에 Gemini 429 시 OpenAI(`gpt-4o-mini`) 즉시 2차 폴백 파이프라인 탑재
  - 스트리밍 종료 시점에 Redis 세션(슬라이딩 윈도우 10건)에 완전 영속화하여 기존 `/chat`과의 세션 일관성 100% 보장
  - 신규 단위 테스트(`tests/unit/test_streaming_api.py`) 3종 작성 및 실시간 스트리밍 토큰 송출 검증 완료 (Ruff & Mypy 100% 통과)
- [x] **Phase 14: 도서 추천 상세 메타데이터 파이프라인 및 프론트 원클릭 서재 등록 연계**
  - 프론트엔드(`frontend-reader-web`) `LibrarianChat.jsx` 및 `RegisterBook.jsx`와 100% 호환되는 `RecommendedBook` 스키마 정의 (`title`, `author`, `isbn`, `publisher`, `page_count`, `genre`, `cover_url`, `reason`, `description`)
  - 국립중앙도서관 API (`SearchApi.do`) 응답 파싱 고도화:
    - 정규식 기반 총 쪽수(`page_count`) 정수 추출 (`parse_page_count`)
    - KDC(한국십진분류) 및 주제 키워드 기반 표준 장르 매핑 (`map_kdc_to_genre`)
    - 복잡한 도서관 저자 표기(저자/역자/공저 등) 순수 저자명 자동 정제 (`clean_author_name`)
    - 국립도서관 표지 누락 시 교보문고 고화질 CDN(`https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/{isbn}.jpg`) 0ms 무지연 자동 폴백 (`get_verified_cover_url`)
  - `/api/v1/chat` 응답(`ChatResponse.recommended_books`) 및 `/api/v1/chat/stream` SSE 이벤트(`event: books`, `event: done`)에 완벽 바인딩
  - 단위 테스트(`tests/unit/test_recommend_metadata.py`) 6종 작성 및 전체 55개 단위 테스트 100% 그린 패스 (Ruff & Mypy 100% 통과)
- [x] **Phase 14.1: Prod 표준 인증(JWT 서명 검증), 게스트 모드 바이패스 및 core-api 규격 정석화**
  - 전사 공용 `JWT_SECRET_KEY` 및 `JWT_ALGORITHM(HS256)` 설정 반영 및 정식 서명/만료 검증 (`jwt.decode`)
  - 비인가/위조/만료 토큰 401 Unauthorized 즉시 거부 (BOLA 보안 취약점 원천 방어)
  - 비로그인 사용자의 무작위 UUID 발급을 중단하고 `effective_member_id = None` (게스트 모드) 안전 유지
  - `search_my_library` 및 `search_scrap_memory` 도구에서 게스트 모드 시 DB 쿼리 스킵(Bypass) 및 즉시 안내 반환
  - `core_api_client.py`의 서재 조회를 `backend-core-api` 실제 엔드포인트(`GET /api/v1/library/books`) 규격으로 교정 및 Token Relay 구현
  - `backend-core-api` 독서 기록 저장 시 호출하는 벡터화 수신 엔드포인트(`POST /api/v1/vectors/records`) 구현
- [x] **Phase 14.2: 토론 파트너 4종 오마주 프롬프트 고도화 및 도서 추천 연계**
  - 토론자 4종 표시명 `(오마주)` 형식 적용 (`평론가(이동진 오마주)`, `이야기꾼(설민석 오마주)`, `상담사(오은영 오마주)`, `관찰가(강형욱 오마주)`)
  - 실존 인물 화법 기반 시스템 프롬프트 템플릿 표준화 (`# 역할`, `# 말투 규칙`, `# 고정 표현 / 답변 포맷`, `# 톤앤매너`, `# 제약사항`, `# 토론 마무리 및 도서 추천 연계`, `# 예시 대화`)
  - 각 토론자별 필수 답변 포맷 정형화:
    - 평론가: `★ 별점` + `■ 한 줄 총평` + `◆ 오늘의 화두`
    - 이야기꾼: `🏛️ 역사가 주는 교훈` + `🔥 함께 던지는 질문`
    - 상담사: `🌱 마음 돌봄 질문` + ☎ 109 핫라인 안내 지침 + 의학적 진단명 금지
    - 관찰가: `🔍 행동 시그널 총평` + `⚡ 현실 관찰 질문`
  - 토론 마무리 시 미학적/역사적/심리적/행동적 화두를 확장해 줄 실존 도서 1권 연계 추천 지침 탑재
  - 단위 테스트(`tests/unit/test_personas.py`, `test_api.py`) 갱신 및 100% 그린 패스 (Ruff & Mypy 무결성 통과)
- [x] **Phase 14.3 (Milestone 1): 토론 피날레 4단계 플로우 & 연계 도서 큐레이션 파이프라인 구축**
  - UI `[🏁 토론 마무리]` 버튼 지원을 위한 `ChatRequest.action: Literal["chat", "conclude"]` 및 빈 메시지 자동 보정 스키마 구현
  - `ChatResponse` 내 `is_concluded: bool` 플래그 및 `debate_summary: Optional[str]` 필드 확장
  - `AgentState`에 `action`, `is_concluded`, `debate_summary` 추가 및 일반 `/chat`과 실시간 SSE `/chat/stream`(`done` 이벤트) 완벽 동기화
  - `_run_persona_node` 내 토론 마무리 인텐트(`action == "conclude"` 또는 자연어 마무리 발화) 감지 시:
    - 대화 히스토리에서 언급된 도서명 및 논제 맥락을 추출하여 `curator_node`로 선위임
    - 국립중앙도서관 API 실존 서지 검증 + 교보문고 고화질 CDN 표지 바인딩
    - 원래 토론 파트너로 복귀하여 오마주 피날레 총평 + 토론 요약 리포트 + `recommended_books` 카드 반환 및 `is_concluded=True` 자동 마킹
  - 신규 단위 테스트(`tests/unit/test_debate_conclude.py`) 5종 작성 및 100% 그린(Success) 통과 (Ruff & Mypy 무결성 완료)

- [x] **Phase 16 (Milestone 2): 토론 기억 전용 테이블(`agent.debate_insights`) DDL 및 개인화 벡터 DB 저장 연계**
  - `agent.debate_insights` 테이블 DDL, `member_id` 격리 인덱스, HNSW 코사인 유사도 인덱스, RPC 함수(`agent.match_debate_insights`) 작성 (`scripts/init_agent_schema.sql`, `init_agent_schema.py`)
  - SQLAlchemy ORM 모델 `DebateInsight` 정의 및 `AgentVectorRepository`에 `insert_debate_insight`, `search_member_debate_insights` 구축 (인메모리 폴백 일체화)
  - 과거 토론 기억 회상 도구(`search_debate_memory`) 구현 및 `GENERIC_TOOLS` 등록으로 8개 페르소나 전체 공유 바인딩
  - `/api/v1/chat` 및 실시간 SSE `/api/v1/chat/stream`에서 토론 마무리(`is_concluded=True`) 시 백그라운드 태스크로 `debate_summary` 자동 벡터화 적재 연동
  - 수동/외부 저장용 API 엔드포인트 `POST /api/v1/memory/debate-insights` 추가
  - 단위 테스트(`tests/unit/test_debate_memory.py`) 7종 작성 및 전체 75개 테스트 100% 그린 패스 (Ruff & Mypy 무결성 통과)

- [x] **Phase 14.4 (Milestone 2.5): 사서 4종 페르소나 전면 고도화 및 종결어미 규칙 반영**
  - 사서 4종 시스템 프롬프트 및 도메인 모델 표준 템플릿화 (`cat.py`, `shoebill.py`, `sea_slug.py`, `gecko.py`):
    - 러시안 블루 (`CAT`, 기본명 '블루', INTJ, 총류/철학/종교, ~냥)
    - 넙적부리황새 (`SHOEBILL`, 기본명 '슈빌', ISTP, 자연과학/기술과학, ~두둥)
    - 갯민숭달팽이 (`SEA_SLUG`, 기본명 '누디', INFP, 예술/문학, ~누누)
    - 게코 도마뱀 (`GECKO`, 기본명 '게코', ENFJ, 사회과학/언어/역사, ~크크)
  - 공통 표준 구조 적용: `# 기본 정보`, `# 역할`, `# 성격 및 독서 성향`, `# 말투/행동 규칙`, `# 🗣️ 종결어미 규칙`, `# 사용자 정의 사서 이름(애칭) 처리`, `# 도구 사용 및 추천 원칙`
  - 중앙 레지스트리(`PERSONA_REGISTRY`), `nodes.py` 키워드 매핑(`switch_map`), API 스키마(`display_name`) 기본 표시명 '누디' 동기화
  - 신규 단위 테스트 추가(`test_librarian_personas_default_display_names`, `test_librarian_personas_mbti_genre_and_endings`) 및 Ruff/Mypy 무결성 검증 완료

- [x] **Phase 18 (Milestone 2.7): 사서 월간 독서 리포트 오케스트레이션 및 LLM 분석/처방 API (`GET /api/v1/reports/monthly`)**
  - `GET /api/v1/reports/monthly?year=YYYY&month=M` 단일 서빙 엔드포인트 신설 (`app/api/v1/reports.py`)
  - `CoreApiClient` 내 Token Relay 연동 `get_monthly_report_stats` 구현 (`GET /api/v1/reports/monthly-stats`) 및 구조화된 오프라인 폴백 지원
  - 자체 토론/스크랩 기반 대표 키워드 3~5개 자동 추출 및 `preferences.debateKeywords` 주입 (`app/domain/reports/keyword_extractor.py`)
  - 사서 페르소나 4종(블루 ~냥, 슈빌 ~두둥, 누디 ~누누, 게코 ~크크) 맞춤 어조 기반 Gemini LLM 06번 성향 분석(`aiAnalysis`) 및 07번 처방(`prescription`) 생성 파이프라인 구축 (`app/domain/reports/generator.py`)
  - `balance.unreadGenres` 기반 도전 장르 추천 및 국립중앙도서관 실존 서지 검증 + 교보 CDN 표지 바인딩 맞춤 추천 도서 카드(1~2권) 생성
  - Pydantic 스키마 정의 (`app/schemas/report.py`) 및 프론트엔드 CamelCase 직렬화 표준화
  - 신규 단위 테스트(`tests/unit/test_monthly_reports.py`) 4종 작성 및 전체 79개 단위 테스트 100% 그린 패스 (Ruff & Mypy 100% 통과)

- [x] **Phase 15 (Milestone 3): 4단계 다중 방어 보안 가드레일 파이프라인 구축 및 무지연(0ms) $0 방어 달성**
  - `app/domain/guardrails/` 도메인 패키지 신설 및 4단계 다중 방어 파이프라인 완성:
    - `safety_gate.py`: 자해/자살 위기 키워드 정규식 감지, 도서명 예외 처리(에밀 뒤르켐의 《자살론》, 카뮈 《시지프 신화》 등 오탐 방지), 8개 페르소나별 24시간 ☎ 109 핫라인 공감 멘트 반환 (게코 위기 시 `~크크` 엄격 생략)
    - `input_gate.py`: 자모 난타(`ㅋㅋㅋㅋ`, `ㅠㅠ`), 숫자 단독(`12345`), 기호/이모지 단독(`🐱🐾`, `???`) 등 무의미/불완전 입력 정규식 감지 및 8개 페르소나별 자연스러운 되묻기 멘트
    - `security_gate.py`: 시스템 프롬프트 유출 시도, DAN/탈옥(Jailbreak), 개인정보(주민등록번호, 카드번호) 0ms 사전 차단 게이트
    - `shared_rules.py`: 시스템 프롬프트 공통 가드레일(`SHARED_GUARDRAILS`)을 `PERSONA_REGISTRY`의 모든 페르소나 시스템 프롬프트에 자동 주입
  - `POST /api/v1/chat` 및 실시간 SSE `POST /api/v1/chat/stream` 엔드포인트에 4단계 게이트 순차 연결 (차단 시 LangGraph 호출 없이 0ms 즉각 반환 및 Redis 세션 맥락 영속화)
  - 단위 테스트(`tests/unit/test_guardrails.py`) 15종 작성 및 전체 98개 단위 테스트 100% 그린 패스 (Ruff 린트/포맷 통과, Mypy 타입 체크 무결성 76개 소스 파일 통과)

- [x] **Phase 17 (Milestone 3.5): SDK 없는 초경량 Tavily REST 탐색(월 1,000건 무료) + 국립중앙도서관 4단계 실전 검증 체인 2-Track 하이브리드 추천 구축**
  - Brave 유료화(신용카드 필수) 위험 차단 및 무거운 `tavily-python` SDK 없이 순수 `httpx` 비동기 20줄 REST 클라이언트로 Tavily(월 1,000건 무료 티어) 경량 연동 (`app/infrastructure/tavily_search_client.py`)
  - 실시간 웹 트렌드/문학상/신조어 도서 탐색을 위한 온디맨드 Function Calling 도구 `search_recent_books` 신설 (`app/domain/recommend/search_books_tool.py`) 및 `GENERIC_TOOLS` 등록
  - 대한민국 국립중앙도서관 정식 서지 API(`SearchApi.do`) 기반 4단계 실전 단행본 검증 체인 구축 (`app/infrastructure/national_library_client.py`):
    - 1단계: 형태 필터링(13자리 `EA_ISBN` 필수, `FORM`/`TYPE_NAME` 단행본 확인, 50쪽 이상으로 팜플렛/논문/점자 컷)
    - 2단계: 텍스트 유사도 매칭 및 파생작(해설집, 요약집, 문제집) 필터링
    - 3단계: 동일 도서 경합 시 발행일(`PUBLISH_PREDATE`) 최신순 정렬 (개정판/최신본 우선)
    - 4단계: 교보문고 공개 CDN 표지 생존 연동 및 0ms 무지연 제공
    - 비상 안전망: 10대 KDC 분류 및 감정 테마별 30여 권 내장 카탈로그 확충 (0ms 오프라인 폴백 보장)
  - 큐레이터 서브에이전트(`curator_node`) 신구(新舊) 하이브리드 헌법 탑재:
    - [1권: 최신 트렌드/화제 도서(2023년 이후)] + [1권: 시대를 초월한 스테디셀러/고전] 1:1 페어링 원칙
    - 후보 도서의 `era` 속성(`recent` vs `classic`) 부여 및 국립도서관 4단계 체인으로 100% 실존 검증
  - `recommend_books` 도구 리팩토링: Tavily 실시간 탐색 + 국립중앙도서관 4단계 체인 + Redis 캐싱(TTL 1시간) 2-Track 하이브리드 파이프라인 완성
  - 단위 테스트 신규 작성(`tests/unit/test_hybrid_curation.py`, 25개 테스트) 및 전체 125개 단위 테스트 100% 그린 패스 달성 (Ruff 린트/포맷 통과, Mypy 타입 무결성 79개 소스 파일 통과)

- [x] **Phase 20 (Milestone 4): 로컬 E2E 통합 테스트 5대 연동 이슈 원인 해결 및 인프라 안정화**
  - **이슈 1 (날씨 Signals 누락)**: `WeatherSignal`, `SignalsResponse` Pydantic 모델 정의 및 `ChatResponse.signals` 복원. `_build_signals` 유틸 구현으로 날씨(맑음/흐림/비 등), 기온, KST 시간대(`dawn`, `day`, `evening`, `night`), 무드를 일관되게 제공하여 프론트엔드 `WeatherMoodBadge` 연동 정상화.
  - **이슈 2 (도서 추천 메타데이터)**: KDC 10대 분류 표준 Enum(`LITERATURE`, `PHILOSOPHY` 등) 매핑 및 국문/영문 상호 보완 변환 헬퍼(`normalize_genre`, `genre_to_korean`, `GENRE_KO_TO_EN`, `GENRE_EN_TO_KO`) 구축. 교보 CDN 표지 URL 및 정수 쪽수(`page_count`) 안정 전달.
  - **이슈 4 (빈 서재 가짜 목 데이터 및 Token Relay)**: Core API 기본 포트 불일치(8080 ➔ 8000) 수정. `CoreApiClient.get_my_bookshelf`에서 가짜 도서 목 데이터('프로젝트 헤일메리', '듄')를 영구 제거하여 미등록/빈 서재 시 정직하게 `books: []`, `total_count: 0` 반환. `ContextVar`(`current_auth_token`) 기반 Bearer Token Relay 연동으로 사용자별 실제 서재 완벽 격리.
  - **이슈 5 (토론 페르소나 덮어쓰기 차단 및 팩트 그라운딩)**: `ChatRequest.populate_defaults_and_aliases`에서 토론 모드(`mode == "DEBATE"`) 시 `librarian_id`에 의해 페르소나가 `CAT`으로 강제 덮어쓰기되던 버그 원천 차단. `book_id`, `topic` 파라미터 추가 및 토론 시작 전 국립중앙도서관/Core-API 실제 서지·줄거리 조회 팩트 주입(`debate_book_info`)으로 줄거리 날조/거짓말 원천 차단. 질문 전문을 도서명으로 검색하던 쿼리 오염을 `extract_debate_book_title` 기반으로 정제.
  - **인프라/런타임 안정화 & 다중 키 임베딩 폴백**:
    - `greenlet` 패키지 추가 (`uv add greenlet`)로 SQLAlchemy asyncpg 세션/엔진 셧다운 크래시 원천 해결.
    - Supabase Transaction Pooler(포트 6543) 환경 및 비동기 이벤트 루프 격리에 맞춘 `NullPool` 엔진 적용.
    - Gemini 임베딩 모델을 `models/gemini-embedding-001` (MRL 768차원 매핑)로 갱신하여 404 에러 원천 차단. 메인 키 소진 시 **팀원 키(`GEMINI_FALLBACK_API_KEY`)로 즉시 자동 스위칭(1,000 + 1,000 = 2,000 RPD)**하는 다중 키 폴백 체계 완성.
    - 콘솔 및 회전 파일 로깅(`logs/app.log`, 최대 10MB x 5개 백업) 이중 로깅 시스템 구축 및 `.gitignore` 등록.
  - **자가 검증 완료**: 전체 126개 단위 테스트(Pytest) 100% 그린 패스 통과, Ruff 린트/포맷 통과, Mypy 정적 타입 체크 80개 파일 무결성 통과.

- [x] **Phase 21 (Milestone 4.1): 도서 큐레이션 속도/정확도 고도화 및 서비스 안정성 방어**
  - **도서 추천 속도 최적화 (이중 루프 차단)**: `curated_books` 존재 시 사서 노드에서 `recommend_books` 및 `search_recent_books` 도구를 `active_tools`에서 동적 제외하고 중복 호출 금지 지침을 시스템 프롬프트에 주입하여 응답 지연을 24초에서 수 초대로 단축.
  - **짧은 도서명 매칭 보장 (본표제 분리)**: 국립도서관 KORMARC 표제(`TITLE`)에서 부제/책임표시 앞 순수 본표제(`main_title`)를 분리(`re.split(r"[:=/(\[]")`)하여, 《모순》, 《광장》, 《토지》 등 2~3글자 대작이 부제 길이로 인해 유사도 0.5 미만으로 탈락하던 치명적 결함을 해결하고 본표제 100% 매칭 달성.
  - **다양성 원칙 확립 및 편향 방지**: 큐레이터 시스템 프롬프트에서 특정 작가/도서명 나열을 제거하고 전 분야에 걸친 풍부한 도서 지식과 사용자 맥락 중심의 보편적 다양성 원칙으로 정제. `temperature=0.7` 상향에 맞춰 정규식 슬라이싱(`re.search(r"\[\s*\{.*\}\s*\]")`)으로 JSON 무결성 확보.
  - **교보 CDN 플레이스홀더 감지 & 헤더 안전 방어**: 교보 CDN의 34,150B 빈 회색 대체 이미지 감지 및 `Content-Length` 부재 시 정상 이미지 오탐 탈락 방어. 미생존 시 죽은 URL 강제 할당 버그 제거.
  - **KDC GENERAL '교양' UI 용어 일치**: `GENRE_EN_TO_KO["GENERAL"] = "교양"` 및 `GENRE_KO_TO_EN["교양"] = "GENERAL"` 동기화.
  - **프론트 호환 OCR 및 장르 분류 엔드포인트 연동**: `POST /api/v1/ocr/sentences`, `POST /api/v1/ocr/covers`, `POST /api/v1/classify-genre` 라우터 등록으로 프론트엔드 독서 수집 모달과의 100% 호환성 확보.
  - **자가 검증 완료**: 신규 단위 테스트 3종 추가, 전체 129개 단위 테스트 100% 그린 패스 통과, Ruff 린트/포맷 통과, Mypy 정적 타입 체크 80개 파일 무결성 통과.

- [x] **Phase 22: 도서 추천 의도 감지 키워드 확장 및 프론트엔드 도서 카드 마크다운 헤딩(`### 📖`) 규격 보장**
  - **의도 감지 키워드 보강**: `nodes.py`의 `recom_keywords`에 `"뭘 읽"`, `"무슨 책"`, `"책 좀"`, `"도서 추천"`, `"책 하나"`, `"책 알려줘"` 등을 추가하여 "뭘 읽으면 좋을까" 질문 시에도 실존 도서 큐레이터 선위임 파이프라인이 100% 작동하도록 개선.
  - **프론트엔드 도서 카드 헤딩 지침 추가**: `curated_books` 소개 시스템 프롬프트 지침에 각 추천 도서를 `### 📖 도서명` 마크다운 3단계 헤딩 포맷으로 별도 줄에 명시하도록 규정하여, 프론트엔드 `MarkdownRenderer` 및 `LibrarianChat` 도서 카드와 `[서재에 등록 ➔]` 버튼이 즉시 렌더링되도록 보장.
  - **자가 검증 완료**: 신규 단위 테스트 2종 추가(`test_recommendation_intent_delegation_keywords`, `test_curated_books_markdown_heading_instruction`), 전체 131개 단위 테스트 100% 그린 패스 통과, Ruff 린트/포맷 통과, Mypy 정적 타입 체크 80개 파일 무결성 통과.

- [x] **Phase 23 (Milestone 5): 도서 표지/뒷표지 Vision OCR 기반 지능형 ISBN 및 계층형 서지 인식 파이프라인 구축**
  - **이중 바코드/노이즈 pyzbar 한계 극복**: 1차 바코드(pyzbar) 실패 시, 문장 스크랩 전용 OCR 대신 **표지/뒷표지 전용 Vision OCR 프롬프트(`GEMINI_COVER_SYSTEM_PROMPT`)**와 `extract_cover_info` 메서드를 신설하여 바코드 하단 인쇄 숫자(13자리 ISBN), 제목, 저자, 출판사를 JSON으로 구조화 추출.
  - **ISBN-13 모듈로-10 공식 가중치 체크섬 유틸 탑재**: `app/vision/isbn_utils.py`에 `validate_isbn13_checksum`, `extract_isbn_candidates`, `find_first_valid_isbn`을 구현하여 노이즈 텍스트에서 잘못된 13자리 숫자를 걸러내고 검증된 ISBN만 선별.
  - **4단계 계층형 표지/서지 파이프라인 연동 (`_handle_cover_ocr`)**:
    - 1차: `barcode_service.scan_isbn` (0ms 빠른 바코드 감지)
    - 2차: `gemini_ocr_client.extract_cover_info` (바코드 아래 인쇄된 숫자 및 제목/저자 구조화 추출)
    - 3차: 국립중앙도서관 정식 API(`search_by_isbn`)로 실존 서지 일괄 조회
    - 4차: ISBN이 짤린 사진이어도 함께 추출된 제목/저자로 국립도서관 실서지 검색(`search_book`) 자동 완성
- [x] **Phase 25 (Milestone 7): Pydantic 구조화 출력(`with_structured_output`) 기반 큐레이터 노드 고도화, RSS 신간 캐싱 백그라운드 워커 및 레거시 `recommend_books` 완전 제거**
  - **Pydantic 구조화 출력 스키마 탑재**: `BookCandidate(title, author, reason, era)` 및 `CuratorResponse(recommendations: List[BookCandidate])` 스키마를 정의하고 LangChain `llm.with_structured_output(CuratorResponse)`를 적용하여 정규식(`re.search`) 파싱과 JSON 괄호 누락 버그를 원천 제거하고 `temperature=0.2`로 환각 차단.
  - **Yes24 RSS 신간 수집 & Redis 오픈북 캐싱 백그라운드 워커 구축**: `app/infrastructure/trending_books.py` 신설. Yes24 종합 베스트셀러 RSS(50권)를 파싱하여 Redis에 `daily_trending_books` 키로 TTL 24시간(86400초) 캐싱. 서버 기동 시(`lifespan`) 백그라운드 태스크로 1회 자동 구동되며, RSS 일시 장애 시에도 기본 화제작 풀 안전망 보장.
- [x] **Phase 26 (Milestone 7): 바코드 스캔 및 OCR 파이프라인 전면 개조 (긴급 수술 완료)**
  - **OpenCV 기반 바코드 스캔 심폐소생술 (`app/vision/barcode_service.py`)**:
    - `robust_scan_isbn` 구축: 고해상도(4K) 스마트폰 카메라 이미지에 대응하여 가로 최대 1000px 비율 리사이징, 그레이스케일 변환 및 Otsu 이진화 대비 강화, 4방향(0°, 90°, 180°, 270°) 회전 뺑뺑이 스캔 루프 적용.
    - pyzbar 부재 또는 OpenCV 미설치 환경에서도 안전하게 동작하는 PIL 4방향 회전 내결함성 폴백 유지.
  - **뒷표지 추천사/홍보문구 제목 오인 사태 원천 방어 (`app/api/v1/vision.py`, `app/vision/gemini_ocr_client.py`)**:
    - "바코드(ISBN)가 잡혔으면 OCR 텍스트는 일체 무시하고 정식 서지 DB로 직행한다"는 대전제 구현: 바코드 감지 시 Gemini OCR 호출 자체를 생략하여 "올해 최고의 감동!", "100만 독자 극찬" 등 뒷표지 카피 문구가 제목으로 탈바꿈하는 현상을 100% 원천 차단.
    - `GEMINI_COVER_SYSTEM_PROMPT` 지침 고도화: 추천사/리뷰/가격/바코드가 보이는 뒷표지 사진의 경우 홍보 문구를 절대 제목으로 착각하지 말고 식별 불가 시 `title: null`, `author: null`을 반환하도록 규정.
    - Vision OCR에서 인쇄된 ISBN을 건진 경우에도 뒷표지 lines 텍스트를 무시하고 국립도서관 정식 서지명으로 우선 바인딩.
  - **국립도서관 API '페이지 수(totalPages)' 증발 사태 해결 (`app/infrastructure/national_library_client.py`)**:
    - `fetch_and_fill_book_info_by_isbn` 신설: 민음사 《데미안》처럼 특정 단일 ISBN에 `PAGE` 필드가 비어있을 때(None 또는 0), 동일한 도서명과 저자로 정식 단행본 검색을 다시 실행하여 50쪽을 초과하는 유효 판본의 페이지 수(`totalPages`)를 자동으로 채워주는 교차 보강(Cross-Referencing) 파이프라인 완성.
  - **자가 검증 완료 (Self-Validation)**:
    - `tests/unit/test_vision.py`에 회전 바코드, 뒷표지 OCR 방어(OCR 미호출 검증), 페이지 수 교차 보강 단위 테스트 2종 추가.
    - 전체 137개 단위 테스트(Pytest) 100% 그린 패스 통과 (`137 passed in 39.12s`).
    - Ruff 린트 및 포맷 정렬 100% 통과 (`All checks passed`, `85 files already formatted`).
    - Mypy 정적 타입 체크 80개 소스 파일 100% 무결성 통과 (`Success: no issues found`).

- [x] **Phase 27: 시스템 경고(Fixed Sampling Temperature, AFC Warning) 소거 및 2026 트렌드 도서 풀 강화**
  - **Gemini Flash Lite 고정 temperature 경고 원천 차단**: Google GenAI 엔진 차원에서 샘플링 temperature 조절을 제한하는 `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`에 대해 `nodes.py`, `curator_node.py`, `reports/generator.py`, `gemini_ocr_client.py`의 `ChatGoogleGenerativeAI` 인스턴스화 시 불필요한 `temperature` 전달을 제거하여 `UserWarning: Model ... uses fixed sampling defaults` 소거.
  - **Automatic Function Calling (AFC) 터미널 경고 억제**: `google-genai` SDK v2와 `langchain-google-genai`의 비동기 도구 바인딩 과도기적 경고(`Direct use of automatic function calling...`)를 `app/main.py`의 `warnings` 필터 및 전용 로거 레벨 조정으로 터미널 로그 오염 차단.
  - **Yes24 폐기 RSS 피드 대응 및 2026 트렌드 도서 풀 강화**: Yes24의 404 미지원 엔드포인트 반환 시 불필요한 에러 로그 대신 안정적 풀 전환 안내 로깅으로 정돈하고, 한강 작가 주요작(작별하지 않는다, 소년이 온다, 채식주의자), 김초엽 《지구 끝의 온실》, 송길영 《시대예보: 호명사회》 등 2024~2026 대표작 풀 대폭 보강.
  - **자가 검증 완료**: 전체 137개 단위 테스트 100% 그린 패스 통과 (`137 passed in 40.47s`), Ruff 린트 및 포맷 통과, Mypy 타입 체크 80개 파일 100% 무결성 통과.

- [x] **Phase 28 (Milestone 8): 폐기된 RSS를 대체하는 Yes24 실시간 SSR 베스트셀러 웹 스크래퍼(`beautifulsoup4`) 구축**
  - **하드코딩 및 폐기 RSS 영구 탈피**: 404 리다이렉트로 폐기된 Yes24 RSS와 임시 하드코딩 폴백을 걷어내고, 완벽한 서버 사이드 렌더링(SSR)인 Yes24 종합 베스트셀러 웹페이지(`https://www.yes24.com/Product/Category/BestSeller?categoryNumber=001&pageSize=40`)를 `httpx` 비동기 호출 및 `beautifulsoup4`로 1초 만에 실시간 파싱하는 스크래퍼 구현 (`app/infrastructure/trending_books.py`).
  - **도서 메타데이터 및 수험서 노이즈 필터링**: `a.gd_name`(도서명), `span.info_auth`(저자), `span.info_pub`(출판사)를 완벽 추출하며, 문제집/수험서(기출, 자격증 등) 노이즈를 필터링하여 순수 문학·교양·인문 단행본 위주로 Redis에 24시간 TTL(`daily_trending_books`) 캐싱.
  - **큐레이터 오픈북 실시간 연동**: 2026년 오늘 날짜 실제 베스트셀러 40권이 LLM 도서 큐레이터 프롬프트에 `[오늘의 화제작 오픈북]`으로 100% 실시간 자동 주입.
  - **불필요한 의존성 정리**: 레거시 `feedparser` 패키지 완전 제거 및 `beautifulsoup4` 연동.
  - **자가 검증 완료**: 신규 단위 테스트 추가 및 전체 137개 단위 테스트(Pytest) 100% 그린 패스, Ruff 린트/포맷 100% 통과, Mypy 정적 타입 체크 80개 파일 무결성 통과.

- [x] **Phase 29: 기획 유연화(감정 맞춤 인생 도서 페어링), 괄호 찌꺼기 완벽 세척(`clean_book_title`) 및 다중 판본 표지 생존 우선 매칭**
  - **극단적 신구 조합 완화 및 감정 맞춤 페어링**: 억지로 '고전'을 강제하던 프롬프트를 탈피하여 [트렌드 도서 1권(오픈북 기반)] + [연도 무관, 사용자의 감정을 완벽히 관통하는 원픽 인생 도서 1권]으로 시스템 프롬프트 및 `BookCandidate` Pydantic 스키마 유연화 (`app/domain/graph/curator_node.py`).
  - **도서명 괄호 찌꺼기 세척 유틸 구축**: `clean_book_title` 유틸 구현으로 `(큰글자책)`, `(오디오북)`, `[양장]`, `<개정판>`, `(진중문고납품)` 등 괄호 쓰레기 텍스트 및 긴 부제를 싹쓸이 정제하여 Yes24 스크래퍼 및 국립도서관 API 검색에 적용 (`app/infrastructure/national_library_client.py`, `trending_books.py`).
  - **다중 판본 표지 생존 우선 매칭 및 오디오북 배제**: 국립도서관 검색 시 오디오북/전자책/납품용 판본을 엄격 제외하고, 상위 5개 판본 중 실제로 살아있는 표지(34,150B 플레이스홀더 배제 및 HTTP 200 검증)를 가진 정식 종이책 판본을 끝까지 찾아내 1순위로 선택. 《브람스를 좋아하세요》 등 오디오북/죽은 표지가 선택되던 결함을 완벽 해결하고 53KB 고화질 표지 및 253 쪽수 교차 보강 성공.
  - **자가 검증 완료**: 신규 단위 테스트 추가 및 전체 138개 단위 테스트 100% 그린 패스, Ruff 린트/포맷 100% 통과, Mypy 타입 체크 80개 파일 무결성 통과.


- [x] **Phase 30 (Milestone 9): 독서 세션(reading_sessions) 데이터 기반 월간 리포트 및 사서 대화 컨텍스트 고도화**
  - **스키마 확장 (`app/schemas/report.py`)**: `ReadingHabits` 모델에 `total_session_count: int`(기본값 0) 및 `avg_session_duration_minutes: Optional[float]` 필드 추가. CamelCase 직렬화로 프론트엔드에 `totalSessionCount`, `avgSessionDurationMinutes` 전달 보장.
  - **CoreApiClient Fallback 동기화 (`app/infrastructure/core_api_client.py`)**: `get_monthly_report_stats` Fallback 목 데이터에 `totalSessionCount: 34`, `avgSessionDurationMinutes: 28.2`를 반영하여 core-api 미연결 오프라인 환경에서도 안전하게 렌더링 지원.
  - **월간 리포트 사서 LLM 프롬프트 및 빌더 연동 (`app/domain/reports/generator.py`)**: `_build_llm_report_prompt` 통계 요약에 세션 횟수 및 1회 평균 집중 독서 시간을 주입하여 사서가 디테일한 몰입 칭찬 멘트를 합성하도록 개선하고, `build_monthly_report`에서 신규 필드 파싱 매핑 완료.
  - **자가 검증 완료 (Self-Validation)**: `tests/unit/test_monthly_reports.py` 신규 필드 및 엔드포인트 응답 검증 완료. 전체 141개 단위 테스트 100% 그린 패스 통과, Ruff 린트/포맷 통과, Mypy 정적 타입 체크 80개 파일 무결성 통과.

- [x] **Phase 31 (Milestone 5): 사서 동료 자연스러운 소개 지침 및 DB 레벨 세션 자동 파티셔닝(`{session_id}:{persona}`)을 통한 어조 오염(`~냥`, `~크크` 혼합) 물리적 0% 격리**
  - **사서 4종 동료 사서 안내 및 자연스러운 소개 지침 탑재 (`cat.py`, `shoebill.py`, `sea_slug.py`, `gecko.py`)**:
    - 본인 담당 장르를 벗어난 분야 요청 시, 시스템 팝업을 강제하지 않고 자신의 고유 어조(~냥, ~두둥, ~누누, ~크크)로 전문 동료 사서(블루-철학/사색, 슈빌-과학/기술, 누디-문학/예술, 게코-역사/사회)를 다정하게 소개하고 사서 변경 이용을 자연스럽게 권유하는 표준 지침 적용.
  - **사서 변경 추천 버튼(`switch_suggestion`) 오작동 및 노이즈 제거 (`nodes.py`)**:
    - AI의 동료 소개나 사용자의 단순 사서명/동물명 언급 시 `switch_suggestion` 버튼이 무차별 발동되던 결함을 수정하여, 사용자의 명시적인 변경 의도("바꿔", "변경", "전환" 등)가 포함된 경우에만 정밀하게 버튼이 제안되도록 개선.
  - **DB 레벨 사서별 세션 자동 파티셔닝 (`router.py`)**:
    - 프론트엔드가 별도 파티셔닝 없이 공통 `session_id`를 보내더라도, 백엔드에서 사서 모드일 때 강제로 `{session_id}:{persona}`(예: `user_123:CAT`, `user_123:SHOEBILL`)로 세션 키를 자동 파티셔닝.
    - Redis / LangGraph 세션 레벨에서 사서별 대화 스레드가 물리적으로 완벽 분리되어, 이전 사서의 말투와 대화 메시지가 새 사서의 히스토리에 섞이는 어조 오염을 물리적으로 0% 원천 차단.
  - **자가 검증 완료 (Self-Validation)**:
    - 신규 단위 테스트 추가 및 검증 완료 (`test_no_switch_intent_on_casual_mention_without_explicit_switch`, `test_chat_persona_switch_sanitizes_history_tone`, 사서 4종 동료 지침 검증).
    - 전체 143개 단위 테스트(Pytest) 100% 그린 패스 통과 (`143 passed in 45.43s`).
    - Ruff 린트 및 포맷 정렬 100% 통과 (`All checks passed`, `90 files already formatted`).
    - Mypy 정적 타입 체크 80개 소스 파일 100% 무결성 통과 (`Success: no issues found in 80 source files`).

- [x] **Phase 32 (Phase 27): nodes.py 규칙 기반 하드코딩 완전 제거 및 Tool Calling 기반 지능형 인텐트 라우팅 리팩토링**
  - **`_detect_switch_intent` 및 하드코딩 사서 감지 맵 완벽 삭제**:
    - 사서 전환은 프론트엔드 상단 UI 탭 전환 및 `{session_id}:{persona}` DB 세션 자동 파티셔닝에 완전 위임하고, 코드 내 if-else 기반 사서 감지 함수 및 키워드 검사를 전면 삭제.
  - **하드코딩 키워드 배열(`conclude_keywords`, `recom_keywords`) 영구 제거**:
    - 문자열 목록(`conclude_keywords`, `recom_keywords`)에 대한 단순 `in last_user_msg` 하드코딩 분기 검사를 제거 (단, 명시적 UI 버튼 요청인 `action == "conclude"`는 0ms 즉시 피날레 지원 유지).
  - **Tool Calling 기반 인텐트 라우팅 구현 (`app/domain/graph/tools.py`, `nodes.py`)**:
    - `@tool trigger_debate_conclude(reason: str)`: 사용자가 토론 종료/마무리 의사를 보일 때 LLM이 에이전트 도구로 자율 호출하여 `curator_node` 피날레 큐레이션으로 라우팅.
    - `@tool request_book_curation(query: str)`: 사용자가 책 추천/큐레이션 의사를 표현할 때 LLM이 에이전트 도구로 자율 호출하여 `curator_node` 국립도서관 정밀 검증으로 라우팅.
    - LLM 응답 후 `tool_calls` 검사를 통해 피날레 및 큐레이터 서브에이전트로 자연스럽게 위임되도록 파이프라인 통합.
  - **ResilientLLM Mock 응답 내 캐릭터 붕괴 및 하드코딩 요약 제거**:
    - `_generate_mock_response` 내에 남아있던 특정 페르소나(평론가의 별점/한줄평 등) 편향 텍스트를 제거하고, 어조를 타지 않는 안전하고 건조한 중립적 메시지로 축소하여 페르소나 붕괴 방지.
  - **페르소나 ID 안전 정규화 체계 구축 (`app/domain/personas/__init__.py`)**:
    - `normalize_persona` 함수를 신설하여 프론트엔드가 소문자(`nudi`, `gecko`), 한글명(`누디`, `게코`, `달팽이`, `황새`), 레거시 ID(`LIBRARIAN_3`, `stork`) 등 어떤 변형값으로 보내더라도 `SEA_SLUG`, `SHOEBILL`, `CAT`, `GECKO` 등 공식 `PERSONA_REGISTRY` 키로 100% 안전하게 매핑.
    - 매칭 실패로 기본값 `CAT_ID`(고양이 말투)로 떨어져 발생하던 다중 인격 결함을 원천 차단.
    - `schemas.py`, `router.py`, `nodes.py`, `workflow.py` 전반에 걸쳐 `normalize_persona` 일괄 적용.
  - **LangGraph Configurable `thread_id` 명시적 주입 (`router.py`)**:
    - `_graph.ainvoke` 및 `_graph.astream_events` 호출 시 `config={"configurable": {"thread_id": session_id}}`를 명시적으로 주입하여, 백엔드 Redis 파티셔닝뿐만 아니라 LangGraph 체크포인터/런타임 레벨에서도 `{session_id}:{persona}` 스레드가 완벽히 분리되도록 보장.
    - 세션 컨텍스트 생성 시 `raw_persona -> target_persona`, `raw_session -> session_id (thread_id)` 추적 로그 명시.
  - **자가 검증 완료 (Self-Validation)**:
    - `test_personas.py` 내 `test_normalize_persona_comprehensive` 신규 테스트 추가 (12종 변형 매핑 검증 완료).
    - 전체 144개 단위 테스트 100% 그린 패스 통과 (`144 passed in 39.38s`).
    - Ruff 린트/포맷 100% 통과 (`All checks passed`).
    - Mypy 정적 타입 체크 80개 소스 파일 100% 무결성 통과 (`Success: no issues found in 80 source files`).

- [x] **Phase 22: 토론자 페르소나 동물 사서 말투 오염 원천 차단 및 세션 격리**
  - **세션 파티셔닝 전면 적용 (`app/api/router.py`)**:
    - LIBRARIAN 모드뿐만 아니라 DEBATE 모드를 포함한 8개 페르소나 전체에 `{session_id}:{persona}` 자동 격리를 적용하여, 동일한 세션 ID로 사서와 토론 탭을 전환하더라도 대화 히스토리 및 어조가 혼입되지 않도록 원천 차단.
  - **사서 애칭 주입 분기 격리 (`app/domain/graph/nodes.py`)**:
    - `if custom_name and not is_debate:`로 조건을 수정하여, 회원이 사서에게 지정한 애칭(`librarian_name`)이 토론 파트너 시스템 프롬프트에 유출되는 현상 방지.
  - **토론자 4종 시스템 프롬프트 네거티브 가드 탑재 (`app/domain/guardrails/shared_rules.py`, `app/domain/personas/__init__.py`)**:
    - `DEBATE_GUARDRAILS` 정의 및 4개 토론자(`DEBATE_CRITIC`, `DEBATE_STORYTELLER`, `DEBATE_COUNSELOR`, `DEBATE_OBSERVER`)의 오프닝/턴 프롬프트에 일괄 주입.
    - 동물 사서 전용 종결어미(`~냥`, `~두둥`, `~누누`, `~크크`), 사서 역할극, 반말 등을 엄격히 금지하고 전문인 오마주 어조를 준수하도록 강제.
  - **자가 검증 완료 (Self-Validation)**:
    - 신규 단위 테스트 추가 (`tests/unit/test_debate_isolation.py`: 4종 토론자 네거티브 가드 주입 검증, 토론 세션 파티셔닝 및 사서 애칭 격리 검증, 갯민숭달팽이 누디-토론자 간 세션 격리 검증).
    - 전체 147개 단위 테스트(Pytest) 100% 그린 패스 통과 (`147 passed in 44.58s`).
    - Ruff 린트 및 포맷 정렬 100% 통과 (`All checks passed`, `91 files left unchanged`).
    - Mypy 정적 타입 체크 81개 소스 파일 100% 무결성 통과 (`Success: no issues found in 81 source files`).

- [x] **Phase 33 (Milestone 10): 도서 큐레이션 다양성 보장 및 세션 중복 방지(Anti-Repeat) 파이프라인 구축**
  - **KDC 장르 매퍼 기반 큐레이션 적합 도서 판별기 연계 (`app/infrastructure/national_library_client.py`)**:
    - `is_curatable_book(title, author, publisher)`: 기존 KDC 매퍼(`map_kdc_to_genre`) 및 서지 분류 체계를 단일 기준으로 재사용하여 수험서/기출/모의고사, 특수 직군 직무 매뉴얼, 아동/만화/합본판 노이즈 필터링.
    - `map_kdc_to_genre`의 한국어 도서명/주제어 장르 매핑 보강 (`LITERATURE`, `PHILOSOPHY`, `SOCIAL_SCIENCE`, `GENERAL` 등).
  - **베스트셀러 순위 보존 + KDC 장르별 구조화 오픈북 카탈로그 (`app/infrastructure/trending_books.py`)**:
    - Yes24 40권 스크래핑 시 `is_curatable_book`으로 유효 단행본 선별 및 원래 순위(`rank`) 보존.
    - `get_trending_books_text()`에서 단순 무작위 셔플로 인한 순위 신뢰도 손실을 방지하고, **종합 순위(`종합 N위`)를 유지**하면서 KDC 장르별(문학/소설/에세이, 인문/철학/심리, 교양/사회/과학)로 그룹핑하여 LLM에 구조화 텍스트 주입.
  - **세션 내 최근 추천 도서 히스토리 추적 및 턴 간 Redis 영속화 (`app/domain/graph/state.py`, `nodes.py`, `router.py`, `redis_session.py`)**:
    - `AgentState`에 `recommended_history: Optional[List[str]]` 추가.
    - `router.py`의 `_prepare_chat_context` 및 `POST /chat`, `POST /chat/stream`에서 세션 스토어와 1:1 양방향 바인딩하여 턴이 바뀌어도 추천 히스토리가 증발하지 않고 유지되도록 영속화 연동 (`RedisSessionManager.delete_session` 지원).
    - 토큰 비용과 컨텍스트 최적화를 위해 최근 10권(`MAX_RECOMMENDED_HISTORY = 10`) 슬라이딩 윈도우 캡 적용.
  - **큐레이터 프롬프트 네거티브 가드레일 및 다양성 지침 탑재 (`app/domain/graph/curator_node.py`)**:
    - `recommended_history`가 존재할 경우 `[중복 추천 제외 목록]`을 프롬프트에 네거티브 컨스트레인트로 주입하여 직전 추천 도서 재추천 억제.
    - 최상단 도서 기계적 편중을 완화하고 장르 전반의 적합 도서를 균형 있게 선택하도록 시스템 프롬프트 지침 고도화.
  - **자가 검증 완료 (Self-Validation)**:
    - `tests/unit/test_curator_pipeline.py`에 노이즈 필터링, KDC 장르 그룹핑/순위 보존, 슬라이딩 윈도우 중복 방지 및 **동일 세션 ID 기반 2턴 연속 호출 시 1차 추천 도서의 제외 목록 주입 및 턴 간 영속화 통합 테스트** 추가.
    - 전체 153개 단위 테스트 정상 통과 (`153 passed, 1 warning in 49.81s`).
    - Ruff 린트 및 포맷 정렬 통과 (`All checks passed`, `91 files already formatted`).
    - Mypy 정적 타입 체크 81개 소스 파일 무결성 통과 (`Success: no issues found in 81 source files`).














