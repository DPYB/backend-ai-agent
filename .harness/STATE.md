# STATE.md — 단계 단위 완료 스냅샷

> 지금까지 완료된 기능과 작업 단계를 마일스톤 단위로 요약 기록합니다.

---

## 완료된 단계

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














