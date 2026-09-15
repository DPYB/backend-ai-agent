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






