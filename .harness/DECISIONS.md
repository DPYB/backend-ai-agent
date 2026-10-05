# DECISIONS.md — 아키텍처 및 정책 결정 히스토리

> 중요한 기술 스택, 아키텍처, 비즈니스 정책 결정의 이유를 기록합니다. (최신 결정이 맨 위로 오는 append-only)
> **작성 규칙**: [결정 / 이유 / 영향] 3단 압축 구조 준수 (구체적 수치, 환경변수, 제약조건 필수 보존). 폐기된 결정은 `~~취소선~~ → [Superseded by 날짜 결정명]` 1줄 링크로 보존.

---

### 2026-10-05: 게스트 복합 세션 ID 422 해결 및 세션 키 JWT 단일 소유화
- **결정**: `ChatRequest.session_id` 검증 시 정규식(`^[A-Za-z0-9:_-]{1,128}$`)을 최상단에 배치하여 특수문자 및 인젝션을 차단하고, `guest-` 접두사 제거 후 UUID를 추출하되 루프 break 없이 마지막 세그먼트를 우선 보존. `router.py`에서 게스트 요청은 바디 `session_id`를 무시하고 JWT `sub`로부터 `guest:{clean_guest_uuid}:{persona}` 키를 강제 생성하고, 미인증 요청의 `guest:` 접두사 사칭을 차단.
- **이유**: 프로덕션 배포 시 게스트 복합 세션(`guest-{uuid}:{persona}`)이 `UUID()` 파싱 실패로 422 Unprocessable Entity 에러를 유발하던 결함 해결 및 타 게스트 세션 UUID 도청 시도 원천 차단.
- **영향**: 회원/게스트 전 환경 일관된 200 OK 처리, 회원 복합 세션 키 하위 호환 완벽 보존, 세션 키 위변조 원천 방어 및 225개 회귀 전수 통과.

### 2026-10-03: 메모리 도구 member_id ContextVar 주입 및 게스트 공용방 매핑 (IDOR 차단)
- **결정**: `search_scrap_memory`, `search_debate_memory`, `search_my_library` 시그니처에서 `member_id` 인자를 완전 제거하고 `app/core/context.py`의 `current_member_id` ContextVar에서 읽도록 고정. 게스트 JWT 수신 시 `core-api` 단일 방과 일치하는 `settings.guest_member_id`(`00000000-0000-0000-0000-000000000003`)로 안전 매핑하고 요청 바디의 `member_id`는 완전 무시.
- **이유**: LLM의 도구 인자 조작 및 프롬프트 인젝션을 통한 비공개 데이터 탈취(IDOR) 원천 차단. 게스트마다 UUID로 분할 시 발생하는 코어 서재와의 정합성 분열 및 크론 청소 불가 좀비 데이터 축적 방지.
- **영향**: LLM 도구 스키마에서 `member_id` 100% 은닉, 인증 누락 시 fail-closed 거부, 게스트의 안전한 서재 조회 허용 및 토론 인사이트 쓰기 차단 확립.

### 2026-10-01: Google Cloud Run 프로덕션 마이그레이션 및 Render 레거시 정리
- **결정**: 서울 리전(`asia-northeast3`) Cloud Run 및 Upstash Serverless Redis(`rediss://...`)로 완전 이전하고 Render 배포 워크플로우(`.github/workflows/deploy.yml`) 삭제.
- **이유**: Render 무료 티어(512MB RAM) 제약, 슬립 지연, 404 빌드 실패 리스크를 제거하고 Cloud Build GitHub 자체 연동(`develop` 브랜치) 활용.
- **영향**: 컨테이너 메모리 1~2GiB 확보, 배포 파이프라인 단일화, 멀티 인스턴스 간 Upstash Redis 세션 영속성 확립.
- ~~2026-09-12 Dockerfile 동적 $PORT 바인딩 및 Render 512MB 제약 설계~~ → [Superseded by 2026-10-01 Google Cloud Run 프로덕션 마이그레이션]

### 2026-09-28: 검증 계층화(Tiered Verification) 및 테스트 I/O 병목 해소
- **결정**: 검증을 3단계(Tier 1 작업 중 `ruff check .` 0.2s + 타깃 테스트 ➔ Tier 2 커밋 직전 `mypy .` 2s + `pytest -m "not integration" -x` ➔ Tier 3 원격 CI)로 분리하고, 외부 I/O(`test_ocr_endpoint` 55.7s, Open-Meteo)를 좁게 모킹.
- **이유**: 212개 전체 테스트 반복 실행 시 소요 시간(84.7s)의 93% 이상이 CPU 연산이 아닌 외부 LLM/API 네트워크 대기 병목이었음.
- **영향**: Tier 2 로컬 단위 회귀 시간 9.92s(88.3% 단축) 달성, pyproject `addopts = "-q --tb=short"` 적용으로 컨텍스트 토큰 소모 최소화.

### 2026-09-22: 국립중앙도서관 표지 생존 판본 최우선 선별 및 디폴트 커버 방어
- **결정**: 도서 검색 결과에서 표지(HTTP 200 & 교보 CDN의 34,150B 회색 플레이스홀더 배제)가 살아있는 판본을 최우선 채택하고, 전멸 시 고화질 `DEFAULT_BOOK_COVER_URL = "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=450&q=80"` 폴백 바인딩.
- **이유**: 오래된 절판본/표지 미제공본이 1순위로 선정되어 브라우저에 깨진 엑스박스나 플레이스홀더가 노출되는 결함 원천 차단.
- **영향**: 표지 누락률 0% 달성, `get_verified_cover_url`, `search_book`, `search_by_isbn`에서 일관된 커버 보장.
- ~~2026-09-14 국립도서관 표지 누락 시 교보문고 CDN 단순 조립(0ms)~~ → [Superseded by 2026-09-22 국립중앙도서관 표지 생존 판본 최우선 선별 및 디폴트 커버 방어]

### 2026-09-22: 도서 큐레이터 타임아웃 현실화(15초) 및 폴백 도서 100% 실서지 완성형 바인딩
- **결정**: 개별 LLM 타임아웃 15초(큐레이터 전체 `wait_for` 35초), 서지 검증 5초로 확장하고, 비상 폴백 명작 8종에 대해 국립도서관 API를 호출해 13자리 ISBN, 교보 CDN(458px), 실제 쪽수, 출판사를 100% 채운 완성형 객체 반환.
- **이유**: 네트워크 지연으로 인한 억울한 폴백 방어 및 빈 껍데기(`isbn: ""`, `cover_url: ""`) 반환으로 인한 프론트 등록 에러 차단.
- **영향**: 장애 상황에서도 프론트 도서 등록 폼(`/register`) 이동 시 정보 누락 0건 보장.

### 2026-09-22: 도서 추천 포맷 하이재킹 방지 및 4단계 응답 시퀀스 강제화
- **결정**: 추천 발화 시 필수 순서(1단계: 공감 ➔ 2단계: 처방 사유 ➔ 3단계: `### 📖 {도서명}` 헤딩 및 카드 트리거 ➔ 4단계: 마무리 멘트) 프롬프트 제약 및 공통 가드레일(`SHARED_GUARDRAILS`) 반영.
- **이유**: 사서 LLM이 UI 포맷팅 압박에 짓눌려 감정 공감이나 처방 사유 없이 헤딩만 덩그러니 던지는 자판기식 출력 결함 해결.
- **영향**: 8종 페르소나 고유의 정서적 온기 및 추천 타당성 보장.

### 2026-09-21: 세션 ID 복합 포맷(`{member_id}:{uuid}:{persona}`) 하위 호환 및 순수 UUID 정규화
- **결정**: `ChatRequest.session_id` 검증 시 콜론 구분 복합 문자열이 들어와도 유효한 UUID 세그먼트를 자동 추출하여 순수 UUID로 정규화.
- **이유**: 기존 브라우저 `sessionStorage`에 저장되어 있던 콜론 구분자 세션 키로 인한 Pydantic 422 Unprocessable 거부 및 로컬 오프라인 폴백 방어.
- **영향**: 클라이언트 로컬스토리지 청소 없이도 100% 무중단 하위 호환성 유지, 백엔드 내부는 회원 격리 유지.

### 2026-09-21: 도서 바코드/표지 VLM 5자리 부가기호(KDC) 원본 추출 및 SSOT 연동
- **결정**: Vision 모델이 장르를 직접 추론하지 않고, 바코드 옆 5자리 부가기호(예: `03320`)나 도서관 라벨 청구기호(예: `813.6-박24ㄱ`)를 원본 그대로 추출해 `CoverOcrResult.kdc`로 `core-api`에 전달.
- **이유**: Vision 모델의 장르 환각을 차단하고 도서관 정식 십진분류체계를 단일 진실 공급원(SSOT)으로 활용.
- **영향**: `GEMINI_COVER_SYSTEM_PROMPT` 및 `extract_kdc_candidates` 다단계 안전망 구축, KDC 원본 누락 0건 달성.

### 2026-09-21: 회원별 세션 네임스페이스 격리(`{effective_member_id}:{validated_uuid}:{persona}`)
- **결정**: 서버(`router.py`)에서 인증된 `effective_member_id`를 강제 접두하여 Redis 키 및 LangGraph 스레드 격리, `ChatRequest.session_id` UUID 형식 엄격 검증.
- **이유**: 타인의 세션 UUID를 엿보거나 임의 키를 주입하는 크로스 어카운트 세션 도청 및 Redis 키 인젝션 원천 차단.
- **영향**: 회원 간, 게스트 간 대화 맥락 침범 0% 물리적 격리 달성.

### 2026-09-20: Google Books API 보조 클라이언트 연동 및 서지 메타데이터 다중 폴백
- **결정**: 인프라 레이어(`GoogleBooksClient`)를 캡슐화하여 국립중앙도서관 서지 조립 시 `page_count`나 `cover_url` 누락 시에만 조건부 보조 호출(2.0s 타임아웃, 429 시 0ms 바이패스).
- **이유**: 국립도서관의 비정형 권차 표기(`v, 1책`)로 인한 쪽수 파싱 실패율 최소화.
- **영향**: 쪽수 보강률 대폭 향상, 최종 표지는 교보 CDN 0ms 폴백으로 이어지는 3단 안전망 확립.

### 2026-09-20: 큐레이터 5단계 파이프라인 및 LLM 구조화 출력(`with_structured_output`) 단일화
- **결정**: 큐레이터 노드를 5개 독립 함수(`resolve_context` ➔ `generate_candidates` ➔ `resolve_targeted` ➔ `verify_candidates` ➔ `assemble_curated_books`)로 분리하고, 의도 판별을 `CuratorResponse.target_title` Pydantic 스키마로 일원화.
- **이유**: 정규식 덧붙이기 오탐의 악순환 및 LLM JSON 파싱 실패 차단.
- **영향**: 특정 도서 지목/일반 추천/메타 질의 구분 정확도 향상, 미검증 도서는 `verified: False`, `isbn: ""` 계약 확립.
- ~~2026-09-13 사서 노드에서 큐레이터 선위임 및 텍스트 파싱~~ → [Superseded by 2026-09-20 큐레이터 5단계 파이프라인 및 LLM 구조화 출력 단일화]

### 2026-09-20: 메타 질의("이전 추천 책과 비슷한 책") 도서명 둔갑 방지 및 가짜 서지 폴백 차단
- **결정**: 메타 키워드(`이전`, `아까`, `비슷`, `골라준` 등)나 조사(`이랑`, `으로` 등)가 남은 문장형 텍스트의 도서명 후보 추출을 차단하고, `national_library_client.py`의 미확인 찌꺼기에 대한 가짜 서지 생성을 금지.
- **이유**: 사용자의 자연어 대화 문장이 국립도서관 가짜 ISBN(`9791100000000`) 카드로 변질되던 결함 해결.
- **영향**: 엉뚱한 대화가 도서 카드로 둔갑하지 않고 LLM의 정상 큐레이션 추론으로 연결.

### 2026-09-20: 전 사서 도서 추천 마크다운 헤딩(`### 📖`) 규격화 및 서재(`library_books`) vs 추천(`recommended_books`) 분기
- **결정**: 추천 도서는 오직 `### 📖 {도서명}` 헤딩만 허용하고 `📚` 이모지 추천 섹션 타이틀 사용 금지. 응답 페이로드에서 `recommended_books`와 `library_books` 구조화 데이터를 상호 배타적으로 분리.
- **이유**: 사서가 서두에 `### 📚 누디가 건네는 책`을 출력하여 프론트엔드가 추천 카드를 '내 서재 보유 도서'로 오인 렌더링하던 결함 차단.
- **영향**: 서재 조회와 도서 추천 UI 렌더링 100% 정합성 확보.

### 2026-09-20: Supabase 원격 마이그레이션 인터락(`ALLOW_REMOTE_MIGRATION`)
- **결정**: 원격 호스트 대상 `alembic upgrade` 실행 시 `ALLOW_REMOTE_MIGRATION=true` 환경변수가 없으면 `RuntimeError`로 즉시 차단하는 `migration_guard.py` 구축.
- **이유**: 로컬 개발 중 실수로 팀 공용 Supabase DB(`agent` 스키마) 형상을 무단 수정하는 참사 방지.
- **영향**: 로컬 마이그레이션 실수 방어. *(운영 주의: Dockerfile 기동 CMD에 `alembic upgrade head`가 포함되어 Cloud Run에서 상시 켜져 있으므로, 향후 1회성 마이그레이션 잡 분리 검토 필요)*

### 2026-09-19: Alembic 기반 비동기 마이그레이션 체계 도입 및 `agent.alembic_version` 스키마 격리
- **결정**: 수동 SQL 스크립트 대신 Alembic 비동기 마이그레이션을 도입하고, `version_table_schema="agent"`, `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}`(포트 6543 Pooler 환경) 적용.
- **이유**: Supabase 단일 공유 DB 환경에서 `core-api`(`core.alembic_version`)와의 충돌 방지 및 Transaction Pooler prepared statement 에러 방지.
- **영향**: `agent` 스키마 DDL(벡터 테이블 `scrap_vector`, `debate_insights`, HNSW 인덱스)의 결정론적 버전 추적 가능.

### 2026-09-18: 해커톤 체험 모드 게스트 JWT 기반 세션 격리 및 Role 분리 이중 서킷 브레이커
- **결정**: 게스트 JWT(`sub: "guest-{uuid}"`, `role: "guest"`) 식별, 세션 키 `{guest_id}:{persona}` 파티셔닝, 영구 사용량 카운터 `guest_usage:{guest_id}`(14일 TTL), 분당(`circuit:rpm:...`, 90초 NX TTL) / 일일(`circuit:rpd:...`, 48시간 NX TTL) 이중 서킷 브레이커 적용.
- **이유**: 로그인 없는 핵심 기능 체험 제공 시 정회원 서비스 안정성 보호 및 개인 기억 데이터 오염 방지.
- **영향**: 개인 기억/벡터화 엔드포인트(`POST /memory/scraps`, `POST /memory/debate-insights`, `POST /vectors/records`) 쓰기 락(403 Forbidden 및 비동기 스킵), 한도 초과 시 200 OK 우아한 UX 폴백 멘트 반환.

### 2026-09-18: 페르소나 간 어조 오염 방지: 전 모드 세션 파티셔닝(`{session_id}:{persona}`) 및 네거티브 가드
- **결정**: 8개 페르소나 전체에 세션 파티셔닝 적용, `librarian_name` 토론자 주입 차단, `DEBATE_GUARDRAILS` 신설하여 동물 종결어미(`~냥`, `~두둥`, `~누누`, `~크크`), 사서 사칭, 반말 엄격 금지.
- **이유**: 탭 전환 시 동일 `session_id` 유지로 인해 사서 종결어미가 토론 파트너로 유입되는 현상 차단.
- **영향**: 페르소나 전환 시 어조 전이 0% 물리적 격리 달성.
- ~~2026-09-18 독서 세션 도구 check_user_reading_streak 및 비동기 정정(pending_correction)~~ → [미구현 가상 설계안으로 아카이브 보존(DECISIONS_2026-10.md)]

### 2026-09-17: Yes24 실시간 SSR 베스트셀러 웹 스크래퍼(`beautifulsoup4`) 채택
- **결정**: 폐기된 Yes24 RSS 대신 실시간 종합 베스트셀러 웹페이지(`pageSize=40`)를 `httpx` + `beautifulsoup4`(0.8초 소요)로 파싱하여 Redis에 24시간 TTL(`daily_trending_books`) 캐싱.
- **이유**: 404 리다이렉트되는 RSS 피드 의존성 탈피, 추가 API 키 발급 없이 $0 제로코스트로 실시간 단행본 수집.
- **영향**: 최신 화제작 오픈북 주입을 통한 LLM 추천 신선도 확보 및 신간 환각 차단.
- ~~2026-09-17 Yes24 RSS 종합 베스트셀러 신간 오픈북 주입~~ → [Superseded by 2026-09-17 Yes24 실시간 SSR 베스트셀러 웹 스크래퍼]

### 2026-09-16: 도서 표지/뒷표지 Vision OCR 기반 지능형 ISBN 및 계층형 서지 인식
- **결정**: 도서 뒷표지 서지 전용 프롬프트(`GEMINI_COVER_SYSTEM_PROMPT`) 신설, 공식 ISBN-13 모듈로-10 체크섬(`isbn_utils.py`) 검증, 4단계 계층형 파이프라인(1차 pyzbar ➔ 2차 Gemini Vision OCR ➔ 3차 국립도서관 ISBN ➔ 4차 제목/저자 검색) 구축.
- **이유**: 바코드 하단 텍스트 간섭 및 이중 바코드로 인한 pyzbar 디코딩 실패율(90%) 극복.
- **영향**: 실전 도서 촬영 인식률 95% 이상으로 대폭 개선.

### 2026-09-16: Tavily 경량 REST 탐색(월 1,000건 무료) + 국립중앙도서관 4단계 실전 검증 체인 하이브리드 추천
- **결정**: 무거운 SDK 없이 순수 `httpx` 비동기 REST(20줄)로 Tavily(월 1,000건 무료 티어)를 1-Track 탐색용으로 연동하고, 발굴된 도서는 국립도서관 4단계 체인([1단계: 13자리 ISBN/50쪽 필터] ➔ [2단계: 유사도/해설집 컷] ➔ [3단계: 최신일 정렬] ➔ [4단계: 교보 CDN 고화질 표지])을 필수로 거치도록 설계.
- **이유**: Brave Search 유료 전환 리스크 방어, 실시간 웹 트렌드 탐색 및 100% 실존 도서 추천 보장.
- **영향**: 쿼터 초과 시 0ms 국립도서관 내장 카탈로그로 무중단 자동 폴백.

### 2026-09-16: 4단계 다중 방어 보안 가드레일(0차 Auth ➔ 1차 Safety ➔ 2차 Input ➔ 3차 Security) 전면 구축
- **결정**: 유해 발화, 무의미 자모/숫자 난타, 프롬프트 탈옥, PII 노출을 LLM 호출 전 파이썬 고속 정규식 게이트(0ms)로 사전 차단하고 위기 시 ☎ 109 핫라인 공감 안내.
- **이유**: LLM 호출 비용 $0 원천 방어, 0ms 레이턴시 달성, 위기 상황 안전 대응.
- **영향**: 일반 대화 및 SSE 스트리밍 공통 보안 확립, 에밀 뒤르켐 《자살론》 등 정당한 인문학 도서 맥락 오탐 방어.

### 2026-09-16: Gemini Flash-Lite 스마트 워크로드 라우팅 및 Google Gemini Flash Vision 전면 전환
- **결정**: 감성 대화/리포트에는 `gemini-3.5-flash-lite`(1.5s), 단순 OCR/큐레이터에는 `gemini-3.1-flash-lite`를 배정하고, 팀원 키(`GEMINI_FALLBACK_API_KEY`) 연동 및 전체 429 시 `gemma-4-31b-it`(RPD 14,400) ➔ `gpt-4o-mini` ➔ Mock 다중 안전망 구축. Clova OCR은 Gemini Vision으로 전면 교체.
- **이유**: Google Flash 계열 무료 RPD 축소(20회) 대응, Flash-Lite(RPD 500) 활용 극대화, Clova 유료 과금 위험 제거.
- **영향**: 하루 무료 호출량 2,000회 확보, $0 제로코스트 무중단 서비스 달성.
- ~~2026-09-12 Clova OCR을 통한 문장 스크랩 전담~~ → [Superseded by 2026-09-16 Google Gemini Flash Vision 전면 전환]
- ~~2026-09-16 E2E 5대 연동 이슈(signals, 서재 0권 Token Relay 등) 해결~~ → [버그 해결 이력으로 아카이브 보존(DECISIONS_2026-10.md)]

### 2026-09-15: 사서 월간 독서 리포트 단일 서빙 엔드포인트(`GET /api/v1/reports/monthly`)
- **결정**: Core API 통계(01~05, Token Relay)와 AI Agent 토론 인사이트(03), 사서 4종 페르소나 어조 LLM 처방(06~07)을 결합하여 단일 응답으로 서빙.
- **이유**: 프론트엔드가 여러 마이크로서비스를 개별 호출/조합하는 복잡성 해소.
- **영향**: 단일 진입점 호출로 풍성한 성향 분석 및 처방 제공.

### 2026-09-15: 토론 기억 전용 테이블(`agent.debate_insights`) 분리 및 비동기 벡터화
- **결정**: 스크랩 수첩(`agent.scrap_vector`)과 분리된 전용 테이블 및 HNSW 인덱스 구축, 피날레 시 FastAPI `BackgroundTasks`로 비동기 적재, `search_debate_memory` 도구를 `GENERIC_TOOLS`에 전사 바인딩.
- **이유**: 순수 도서 발췌문과 AI 토론 사유 결실(통찰) 간 데이터 오염 방지 및 사용자 응답 지연(0ms) 차단.
- **영향**: 8개 페르소나 모두가 과거 토론 기억을 자연스럽게 회상할 수 있는 영구 자산화 완료.

### 2026-09-14: 전사 중앙 인증(JWT 서명 검증), 게스트 바이패스 및 MSA Token Relay
- **결정**: `core-api`의 `JWT_SECRET_KEY`를 전사 공유받아 0ms 로컬 HS256 서명 검증, 게스트 요청 DB 쿼리 스킵, 서재 조회는 Token Relay로 `core-api`의 `GET /api/v1/library/books` 호출.
- **이유**: `verify_signature=False` 보안 취약점(BOLA/토큰 위조) 원천 차단 및 MSA 간 일관된 인증 유지.
- **영향**: 비인가 접근 차단, 불필요한 게스트 DB 쿼리 방어.

### 2026-09-14: Supabase 공용 DB MSA 스키마 격리(`agent`) 및 Transaction Pooler 연동
- **결정**: 단일 Supabase Postgres 인스턴스 내 `agent` 독점 스키마 운용, 타 스키마(`core`/`record`) 직접 쿼리 금지(REST API 원칙), Transaction Pooler(포트 6543) `statement_cache_size: 0` 설정.
- **이유**: 전사 $0 단일 DB 공유 정책 준수 및 멀티 테넌트 충돌 방지.
- **영향**: pgvector 코사인 유사도 검색 최적화 및 커넥션 풀 안정성 확보.
