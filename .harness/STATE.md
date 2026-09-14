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
  - 신규 단위 테스트(`tests/unit/test_db_infrastructure.py`) 포함 총 46개 단위 테스트, Ruff 린트, Mypy 타입 체크 무결성 100% 통과





