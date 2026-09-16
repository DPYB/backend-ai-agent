# HANDOFF.md — 세션 인수인계 로그

> 세션마다 무엇을 진행했고 다음 세션에서 무엇을 이어받아야 하는지 서술형으로 기록합니다. (최신 세션이 아래로 추가되는 append-only)

---

## 세션 1 (2026-09-12)

### 진행한 작업
1. **LangGraph 8-Node 페르소나 아키텍처 구축**:
   - 사서 모드 4종(`CAT`=블루, `SHOEBILL`=슈빌, `SEA_SLUG`=바다달팽이, `GECKO`=게코)과 토론 모드 4종(`DEBATE_CRITIC`, `DEBATE_STORYTELLER`, `DEBATE_COUNSELOR`, `DEBATE_OBSERVER`) 노드 및 프롬프트 정의.
   - 페르소나 전환 시 어조 오염을 방지하는 `summarizer_node` 구현.
   - 사용자 지정 사서 애칭(`librarian_name`) 파라미터 적용.
2. **개인화 RAG & 도구 체계 완성**:
   - Google Gemini Embedding(`text-embedding-004`) + Supabase pgvector(`scrap_vector`) 기반 `search_scrap_memory` 도구 연동.
   - `core-api` 내 서재 조회 연동 `search_my_library` 도구 구현.
   - Tavily 웹 검색 + 도서 메타데이터 + Redis TTL 캐싱 기반 `recommend_books` 도구 구현.
   - Supabase DDL/RPC 함수 명세 및 시딩 스크립트 작성 (`scripts/seed_supabase_scrap_vector.py`).
3. **무과금(Zero-cost) 배포 정책 반영**:
   - `Dockerfile` 동적 `$PORT` 환경변수 바인딩 적용 (`${PORT:-8000}`).
   - `docker-compose.yml` 볼륨 마운트 핫리로드 활성화.
   - `/api/v1/health`에 Supabase 슬립 방지 핑 쿼리 연동 (15분 Render 핑으로 Supabase 7일 정지 동시 방어).
4. **Vision API 추가 구현**:
   - `pyzbar` 및 `Pillow` 기반 13자리 도서 바코드(ISBN-13, EAN13) 스캔 서비스 (`POST /api/v1/vision/scan-barcode`).
   - Naver Cloud Clova OCR General API V2 비동기 클라이언트 연동 및 `lineBreak` 기반 자연스러운 줄바꿈 복원 (`POST /api/v1/vision/ocr`).
   - `Dockerfile`에 OS 의존성 `libzbar0` 패키지 추가.
5. **바이브 코딩 하네스 표준 구축**:
   - DPYB 가이드에 따라 `AGENTS.md`, `CLAUDE.md`, `.kiro/steering/project.md`, `.harness/` 6대 문서 초기화 완료.

### 다음 세션에서 할 일
- `backend-record-api`에서 독서 기록/스크랩 생성 시 호출할 비동기 벡터화 수신 엔드포인트(`POST /api/v1/memory/scraps`) 구현 여부 확인 및 필요 시 개발.
- LangGraph 스트리밍(SSE) 응답 인터페이스 도입 검토.

---

## 세션 2 (2026-09-12)

### 진행한 작업
1. **DPYB 중앙 Reusable CI/CD 워크플로우 연동**:
   - `.github/workflows/ci.yml`: `DPYB/.github/.github/workflows/reusable-python-ci.yml@main` (Python 3.12 기준).
   - `.github/workflows/lint-pr.yml`: `DPYB/.github/.github/workflows/reusable-pr-lint.yml@main` (PR 제목 형식 검증).
2. **중앙 킵얼라이브 연동용 루트 헬스체크 구현**:
   - `GET /health` 엔드포인트 추가 (기본 200 OK 반환 및 Render 10분 슬립 방지, Supabase 핑 연동).
   - `test_root_health_check_endpoint` 단위 테스트 추가 완료.
3. **하네스 문서 및 역할 정립**:
   - 도메인 역할 명문화: AI 사서, 개인화 RAG(LangGraph, pgvector)와 함께 **ISBN 바코드 스캔, 문장 스크랩 OCR 등 독서 수집 기능 구현**을 전담하고, **순수 DB 영속화는 `core-api`에 위임**함을 `AGENTS.md` 및 `ARCHITECTURE.md`에 명시.
   - **브랜치 전략**: `feat/*` 단일화 (`main` <- `develop` <- `feat/*`).
   - **커밋 & PR 제목**: `type[scope]: description` 대괄호 표준 준수 (`[agent]`, `[vision]`, `[rag]` 등).
   - **PR 머지 권한**: **develop/main 브랜치 PR 머지는 에이전트가 실행하지 않고 사람이 직접 클릭** 규칙 명문화.


### 다음 세션에서 할 일
- `backend-record-api`의 스크랩 벡터화 비동기 수신 API(`POST /api/v1/memory/scraps`) 구현 여부 확인 및 필요 시 개발 착수 (`.harness/PLAN.md` 1번 태스크).

---

## 세션 3 (2026-09-13)

### 진행한 작업
1. **`develop` 브랜치 생성 및 분할 커밋/푸시**:
   - `main` 브랜치 기반으로 `develop` 브랜치 분기 (`git checkout -b develop`).
   - DPYB 커밋 컨벤션(`type[scope]: description`)에 따라 논리적 단위별 커밋 분할 푸시 완료.
2. **중앙 Reusable CI 전체 검사 통과 (All Checks Passed)**:
   - **Ruff 포맷팅 표준 정렬**: `ruff format` 자동 정렬 적용
   - **Mypy 정적 타입 체킹 해결**: Supabase RPC/insert 반환 타입 캐스팅(`typing.cast`), LangGraph LLM 할당 타입 추론 완화, 메시지 히스토리 `List[BaseMessage]` 타입 힌트 보정
   - **CI 환경 바코드 모킹 보정**: Ubuntu CI 러너(`libzbar0` 부재) 환경에 대응한 `_ZBarSymbolFallback` 및 `pyzbar` 디코드 모킹 안전화
   - GitHub Actions Reusable Python CI (`Lint`, `Format`, `Mypy`, `Pytest`) **100% 그린(Success) 통과 완료**.

### 다음 세션에서 할 일
- `feat/*` 작업 브랜치 기반으로 `backend-record-api`의 스크랩 벡터화 비동기 수신 API(`POST /api/v1/memory/scraps`) 구현 여부 확인 및 개발 진행.

---

## 세션 4 (2026-09-13)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - `develop` 브랜치 기반 `feat/scrap-vectorization` 분기
2. **OpenAI 예비/대체 LLM 설정 명세 보강**:
   - `.env.example`, `app/core/config.py`에 `OPENAI_API_KEY`, `OPENAI_MODEL` 주석 및 설정 반영
3. **독서 기록/스크랩 벡터화 수신 엔드포인트 구현**:
   - 스키마 정의 (`ScrapVectorizeRequest`, `ScrapVectorizeResponse` in `app/api/schemas.py`)
   - 인제스천 엔드포인트 `POST /api/v1/memory/scraps` (`app/api/v1/memory.py`) 구현
   - 도서명, 발췌 문장, 독자 메모를 결합하여 Gemini 임베딩 벡터(768차원) 생성 및 Supabase pgvector `scrap_vector` 적재 연동
   - `app/main.py`에 `memory_router` 등록
4. **품질 검증 및 테스트 전체 통과**:
   - `tests/unit/test_memory_api.py` 단위 테스트 추가
   - Pytest 36개 단위 테스트 전원 통과 (100% 그린)
   - Ruff 린트 및 포맷 정렬, Mypy 타입 체크 무결성 확인 완료

### 다음 세션에서 할 일
- 사용자의 커밋 및 PR 생성 승인 시 `feat/scrap-vectorization` 커밋/푸시 및 `feat/* -> develop` PR 생성
- 로컬 서버 기동 후 Swagger UI(`http://localhost:8000/docs`)를 통한 실제 동작 시각적 확인
- 2번 계획(LangGraph 스트리밍 SSE 엔드포인트) 검토 및 착수

---

## 세션 5 (2026-09-13)

### 진행한 작업
1. **`develop` 브랜치 동기화 및 작업 브랜치 생성**:
   - `develop` 최신화 (PR #2 머지 반영)
   - 작업 브랜치 `feat/AI-14-curator-agent-pipeline` 분기
2. **국립중앙도서관 Open API 클라이언트 구현**:
   - `app/infrastructure/national_library_client.py` 작성
   - 승인 대기 중에도 실존 한국어 도서(데미안, 불편한 편의점, 어린 왕자, 바람이 분다 당신이 좋다 등)와 13자리 정식 ISBN을 보장하는 스마트 폴백 구현
3. **Open-Meteo 무료 실시간 날씨 클라이언트 구현 및 위치 스키마 확장**:
   - `app/infrastructure/weather_client.py` 작성 (WMO 20종 기상 코드 매핑 및 실시간 기온/날씨 파싱)
   - `ChatRequest` 내 프론트엔드 위치 좌표(`location: { latitude, longitude }`) 수신 모델 정의
   - 좌표 수신 시 실시간 날씨 정보를 조회하여 큐레이터 및 사서 컨텍스트에 자동 주입
4. **도서 큐레이터 전문 서브에이전트 노드 구현**:
   - `app/domain/graph/curator_node.py` 작성
   - 실시간 날씨/감정/상황에 맞춘 도서 추론(`temperature=0.1` 팩트 중심) 후 국립중앙도서관 서지 정보로 100% 검증
5. **LangGraph 양방향 Handoff 라우팅 완성**:
   - `AgentState` 내 `curator_request`, `curated_books`, `weather_context`, `location_coords` 상태 추가
   - 사서/토론자 마스터 에이전트 ➡️ `curator_node` 위임 ➡️ 실존 도서 바인딩 후 원래 사서 노드로 복귀하는 양방향 Handoff 조건부 엣지 등록
   - 사서 페르소나의 어조 오염 및 환각 원천 차단
6. **국립중앙도서관 정식 서지정보 API(`SearchApi.do`) 규격 일치화**:
   - `core-api`와 동일하게 공식 규격(`https://www.nl.go.kr/seoji/SearchApi.do`, `NL_API_CERT_KEY`) 및 `docs` 배열 표준(`TITLE`, `AUTHOR`, `EA_ISBN`, `TITLE_URL`)으로 1:1 완벽 정렬
   - Naver Cloud Clova OCR General API V2 설정 가이드 주석 보강
7. **품질 검증 및 테스트 전체 통과**:
   - `tests/unit/test_curator_pipeline.py` 신규 작성 (날씨 및 국립도서관 공식 폴백 테스트 포함)
   - Pytest 41개 단위 테스트 100% 통과 (그린)
   - Ruff lint/format 및 Mypy 타입 체크 무결성 통과

### 다음 세션에서 할 일
- Pull Request #4 리뷰 및 머지 완료 확인 (`https://github.com/DPYB/backend-ai-agent/pull/4`)
- 로컬 서버 기동 후 Swagger UI(`http://localhost:8000/docs`)를 통한 위치/날씨 및 감정 기반 도서 추천 실제 동작 확인

---

## 세션 6 (2026-09-13)

### 진행한 작업
1. **로컬 Uvicorn 서버 기동 및 실시간 대화 파이프라인 검증**:
   - `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` 백그라운드 기동.
   - 루트 및 서비스 헬스체크 (`GET /health`, `GET /api/v1/health`) 200 OK 및 Supabase 연결 확인.
2. **도서 추천 위임 최적화 및 OpenAI API 호환성 강화**:
   - 사용자의 추천 의도(`추천`, `골라줘` 등) 감지 시 사서 노드에서 불필요하게 1차 LLM을 호출하지 않고 곧바로 `curator_node`로 선위임하도록 경로 최적화 (응답 지연 2~3초 및 LLM 토큰 비용 절감).
   - 어시스턴트 메시지에 `tool_calls`가 있을 때 `ToolMessage` 응답 없이 LLM이 재호출되어 발생하는 OpenAI 400 Bad Request 에러를 방지하기 위해 `sanitized_messages` 메시지 정제 로직 구현.
   - `langchain-openai` 의존성 명시 추가 및 `ChatOpenAI(api_key=SecretStr(...))` 타입 안정성 확보.
3. **페르소나별 실제 대화 시연 검증**:
   - **고양이 사서 '블루' (`CAT`)**: 서울 실시간 날씨(구름 조금, 20.2°C) 및 울적한 기분 입력 시, 큐레이터가 국립도서관 실존 도서 검증 후 《죽고 싶지만 떡볶이는 먹고 싶어》를 블루 특유의 다정한 어조로 추천 성공.
   - **슈빌 사서 (`SHOEBILL`)**: "도대체 인생이 왜 이렇게 복잡하고 마음대로 안 되는 걸까?" 질문에 대해 직설적이고 명쾌한 3대 핵심(불확실성, 기대와 현실, 사회적 압박) 분석 답변 확인.
   - **바다달팽이 사서 (`SEA_SLUG`)**: 직장 상사 스트레스 호소에 대해 깊은 바다의 물결과 평온함의 은유로 위로하는 시적 톤 확인.
   - **문학 비평가 (`DEBATE_CRITIC`)**: 《노르웨이의 숲》 상실감 및 한강 《소년이 온다》 3연속 멀티턴 토론(동호의 죽음 ➡️ 은숙/선주의 죄책감 ➡️ 에필로그 작가 개입) 완벽 검증.
4. **Gemini 3.6 Flash 연동 및 실측 벤치마크**:
   - Google 공식 최신 정식 모델 `gemini-3.6-flash`로 환경 설정 및 프롬프트 규격 일치화.
   - Gemini(8.5s, 찰떡 도서 매칭 & 유려한 한국어 감성) vs GPT-4o-mini(2.1s, 초고속 백업 폴백) 실측 비교 완료.
5. **PR #4 최신 커밋 반영 및 CI All Checks Passed**:
   - 커밋 `feat[agent]: 큐레이터 선위임 파이프라인 최적화 및 Gemini 3.6 Flash 모델 연동` (`ebfe639`) 푸시 완료.
   - GitHub Actions CI (Python 3.12 Lint/Type/Test & PR Lint) 100% 그린 패스 확인.
   - 로컬 테스트 서버 정상 종료 및 8000 포트 정리 완료.

### 다음 세션에서 할 일
- GitHub 웹에서 [PR #4](https://github.com/DPYB/backend-ai-agent/pull/4) Squash and merge 완료 확인 (사람 직접 클릭 원칙).
- 로컬 `develop` 브랜치 체크아웃 및 최신 동기화 (`git checkout develop && git pull origin develop`).
- LangGraph 실시간 스트리밍(SSE) 엔드포인트(`POST /api/v1/chat/stream`) 설계 및 구현 (`.harness/PLAN.md`).

---

## 세션 7 (2026-09-14)

### 진행한 작업
1. **전사 Supabase 공용 DB 아키텍처 및 MSA `agent` 스키마 연동**:
   - DPYB 전사 $0 무과금 단일 Supabase Postgres 인스턴스 공유 정책 반영
   - `core` / `record` 스키마 직접 쿼리를 원천 차단하고 `agent` 스키마를 독점 소유하여 독서 기억/대화 세션 격리
2. **Transaction Pooler(포트 6543) 연동 및 충돌 방지**:
   - `pyproject.toml`에 `sqlalchemy>=2.0.0`, `asyncpg>=0.30.0`, `pgvector>=0.3.0` 의존성 추가
   - `app/core/config.py` 및 `.env.example`에 Transaction Pooler 규격(`DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT=6543`, `DB_NAME=postgres`, `DB_SCHEMA=agent`) 및 특수문자 안전 인코딩 `async_database_url` 구현
   - Transaction Pooler prepared statement 충돌 방지를 위한 `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` 적용 (`app/infrastructure/db/session.py`)
3. **`agent` 스키마 전용 DDL 및 자동 실행 도구 작성**:
   - `scripts/init_agent_schema.sql`: `vector` 확장 활성화, `agent` 스키마 생성, `agent.scrap_vector` 테이블, HNSW 코사인 유사도 인덱스, `agent.match_scraps` RPC 함수 정의
   - `scripts/init_agent_schema.py`: 비동기 asyncpg 기반 DDL 자동 실행 및 샘플 데이터 시딩(`--seed`) 스크립트 작성
4. **SQLAlchemy ORM 및 `AgentVectorRepository` 구축**:
   - `app/infrastructure/db/models.py`: `ScrapVector`(`__table_args__ = {"schema": "agent"}`) 및 `ChatSession` 선언적 매핑
   - `app/infrastructure/db/repository.py`: `member_id` 완전 격리 코사인 유사도 연산 및 스크랩 벡터 삽입, 헬스체크 핑 구현 (미연결 시 인메모리 폴백 지원)
   - `app/infrastructure/supabase_client.py`: `SupabaseVectorClient`가 `AgentVectorRepository`를 우선 호출하도록 어댑터 통합 (하위 호환성 100% 유지)
5. **품질 검증 및 테스트 전체 통과**:
   - `tests/unit/test_db_infrastructure.py` 신규 작성 (URL 인코딩, 스키마 분리, 인메모리 폴백, 회원별 격리 검증)
   - 총 46개 단위 테스트 전원 통과 (100% 그린)
   - Ruff 린트/포맷 정렬 및 Mypy 정적 타입 체크(`56 source files`) 무결성 확인 완료

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/supabase-agent-schema` 브랜치 변경 사항 커밋 및 푸시 (완료: PR #5 머지됨)
- `feat/supabase-agent-schema -> develop` PR 생성 보조 (완료: PR #5 머지됨)
- LangGraph 스트리밍(SSE) 응답 인터페이스(`POST /api/v1/chat/stream`) 설계 및 구현 (세션 8에서 완료)

---

## 세션 8 (2026-09-14)

### 진행한 작업
1. **PR #5 머지 및 develop 최신 동기화**:
   - `feat/supabase-agent-schema` PR #5 사람 직접 머지 확인 후 `develop` 풀 완료
   - 작업 브랜치 `feat/chat-sse-streaming` 분기
2. **LangGraph 실시간 스트리밍(SSE) 엔드포인트 구현**:
   - `POST /api/v1/chat/stream` 엔드포인트 추가 (`StreamingResponse`, `text/event-stream; charset=utf-8`)
   - 표준 SSE 이벤트 규격 구현: `event: metadata`, `event: token` (텍스트 델타), `event: switch_suggestion`, `event: done`, `event: error`
   - LangGraph `astream_events(v2)` 연동: 마스터 페르소나 노드 토큰만 실시간 스트리밍하고 내부 도서 추천 서브에이전트(`curator_node`) 중간 JSON 추론은 완벽 격리
   - 프록시 버퍼링 방지 헤더(`X-Accel-Buffering: no`, `Cache-Control: no-cache`) 적용
3. **ResilientLLM 및 큐레이터 2차 예비 LLM(OpenAI) 즉시 폴백 구현**:
   - Gemini API 429 할당량 초과 시 곧바로 OpenAI(`gpt-4o-mini`)로 전환 호출하여 응답 중단 원천 방지
   - 노드 함수에 `config: Optional[RunnableConfig] = None` 표준 파라미터 전달 연동
4. **품질 검증 및 실시간 통신 확인**:
   - `tests/unit/test_streaming_api.py` 신규 작성 (3개 테스트 100% 통과)
   - 실시간 SSE 스트리밍 통신(`metadata` -> `token` 실시간 타이핑 -> `done` -> Redis 영속화) 동작 확인 완료
   - Ruff 린트/포맷 통과, Mypy 타입 체크 무결성 통과 (`59 source files`)

### 다음 세션에서 할 일
- 사용자 승인 시 `feat/chat-sse-streaming` 변경사항 커밋, 푸시 및 `develop` 대상 PR 생성 (완료: PR #6 머지됨)
- 프론트엔드 연동 지원 및 향후 백로그 아이디어(멀티모달 표지 분석 등) 검토

---

## 세션 9 (2026-09-14)

### 진행한 작업
1. **`develop` 브랜치 동기화 및 작업 브랜치 생성**:
   - PR #6 머지 확인 후 `git checkout develop && git pull origin develop` 동기화 완료
   - DPYB 표준 브랜치 규칙에 따라 `feat/recommend-book-metadata` 분기
2. **프론트엔드(`frontend-reader-web`) 규격 실측 및 100% 일치화**:
   - `LibrarianChat.jsx` 및 `RegisterBook.jsx` 실제 소스를 분석하여 프론트엔드가 기대하는 추천 도서 필드(`title`, `author`, `isbn`, `publisher`, `page_count`, `genre`, `cover_url`, `reason`, `description`) 1:1 정렬
   - 프론트엔드 코드 수정 없이 백엔드 연동만으로 원클릭 도서 등록 폼 자동 완성 보장
3. **국립중앙도서관 API 파싱 고도화 및 교보문고 고화질 CDN 0ms 무지연 폴백**:
   - `parse_page_count`: 국립도서관 `PAGE` 문자열에서 정규식으로 순수 쪽수 정수 추출 (예: '328 p.' -> 328)
   - `map_kdc_to_genre`: KDC 한국십진분류 코드(800: 문학, 100: 철학 등) 및 주제어 기반 표준 장르 매핑
   - `clean_author_name`: 도서관의 번잡한 저자 표기('저자 : 헤르만 헤세;역자 : 서상원;')를 순수 저자명으로 정제
   - `get_verified_cover_url`: 국립도서관 표지 누락/저화질 시 교보문고 공개 CloudFront CDN(`https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/{isbn}.jpg`)을 추가 HTTP 요청 없이 0ms 무지연으로 즉시 바인딩
4. **API 스키마 및 엔드포인트 연동**:
   - `RecommendedBook` 모델 정의 및 `ChatResponse.recommended_books` 필드 추가
   - `POST /api/v1/chat`: `curated_books`를 `RecommendedBook` 배열로 반환
   - `POST /api/v1/chat/stream`: 스트리밍 도중 `event: books` 발행 및 `event: done` 페이로드에 `recommended_books` 포함
5. **품질 검증 및 테스트 전체 통과**:
   - `tests/unit/test_recommend_metadata.py` 신규 단위 테스트 6종 작성
   - 전체 55개 단위 테스트 100% 그린(Success) 통과
   - Ruff 린트/포맷 정렬 및 Mypy 정적 타입 체크(58개 소스 파일) 무결성 확인 완료

### 다음 세션에서 할 일
- 사용자 컨펌 시 `feat/recommend-book-metadata` 변경 사항 커밋 및 푸시 (완료: PR #8 열림)
- `backend-core-api` 인증/회원가입 엔드포인트 머지 후, 프론트/코어/에이전트 3대 서비스 로컬 동시 기동 및 실화면 원클릭 서재 등록 통합 테스트 진행

---

## 세션 10 (2026-09-14)

### 진행한 작업
1. **프론트엔드 연동 422 Unprocessable Entity 해결 및 3-Tier JWT 인증 연동**:
   - 프론트엔드가 요청 본문 대신 `Authorization: Bearer <token>` 헤더로 유저 정보를 보내는 구조를 수용하도록 `extract_member_id_from_auth` 구현.
   - `member_id` 누락 시 비로그인 게스트용 고유 UUID 자동 발급, `librarian_id` 대소문자 무관 매핑, 최상위 위경도(`latitude`, `longitude`) 수신 모델 호환성 확보 (`app/api/schemas.py`, `app/api/router.py`).
   - 커밋: `2bd8a19` (422 호환 스키마 확장), `4b8a52f` (JWT Bearer 헤더 연동), [PR #8](https://github.com/DPYB/backend-ai-agent/pull/8) 오픈.
   - 로컬 Uvicorn 8001 포트에서 프론트엔드 페이로드(`librarian_id: "cat"`, `latitude`, `longitude`) 수신 및 추천 도서 2권 정상 생성(200 OK) 실증 완료.
2. **이전 서비스(`backend-discovery`) 보안 가드레일 구조 분석 및 재설계**:
   - 사용자가 제시한 4단계 게이트(0차 인증 ➔ 1차 Safety ➔ 2차 Input ➔ 3차 Bedrock Guardrails) 구조 분석:
     - `safety_gate.py`: 위기 발화 패턴(`CRISIS_KEYWORDS_PATTERN`), 도서명 예외(`BOOK_TITLE_EXCLUSIONS_PATTERN`, '자살론' 등 오탐 방지), 109 핫라인 안내.
     - `input_gate.py`: 자모(`ㄱ-ㅎ`), 숫자, 이모지 단독 입력 시 LLM 없이 즉각 되묻기.
     - `SHARED_GUARDRAILS`: 시스템 프롬프트 유출 금지, 날씨 팩트 엄수, 도서 서비스 범위 밖 질문 거절.
3. **본 레포 아키텍처 맞춤형 재구성 방향성 및 설계 수립 (핵심 원칙)**:
   - **레거시 단순 복제 지양**: 과거 2종 사서(`cat`, `stork`) 및 Bedrock Guardrails 의존성을 그대로 가져오지 않고, **본 레포의 현재 스트럭처(8종 페르소나, LangGraph 8-Node, SSE 실시간 스트리밍, $0 무과금 Zero-cost)에 완벽히 맞게 현대화하여 재구성**하기로 결정.
   - 시스템 프롬프트를 `backend-ai-agent` 단독 마이크로서비스 내부(`app/domain/guardrails/` 및 `app/domain/personas/`)에서 코드로 일괄 소유(GitOps)하는 아키텍처적 당위성 정립.
   - `.harness/PLAN.md`에 Phase 15 세부 구현 계획 수립 및 `.harness/DECISIONS.md`에 설계 결정 기록 완료.

### 다음 세션에서 할 일
- **Phase 15: 4단계 다중 방어 가드레일 파이프라인 구현 착수**:
  - `app/domain/guardrails/` 패키지 신설:
    - `safety_gate.py`: 위기/자해 정규식 감지, 도서명('자살론' 등) 오탐 방지, 8종 페르소나(사서 4종 + 토론자 4종)별 109 핫라인 공감 멘트
    - `input_gate.py`: 자모/숫자/이모지 정규식 감지 및 8종 페르소나별 자연스러운 되묻기 멘트
    - `security_gate.py`: 시스템 프롬프트 유출 시도, DAN/탈옥, PII(주민등록번호 등) 0ms 사전 차단 게이트
    - `shared_rules.py`: 시스템 프롬프트 공통 가드레일(날씨 팩트 엄수, 도서 서비스 범위 밖 질문 정중 거절, 내부 메타데이터 은폐)
  - `app/api/router.py`의 `POST /api/v1/chat` 및 `POST /api/v1/chat/stream` 엔드포인트에 4단계 게이트 순차 연결
  - 단위 테스트(`tests/unit/test_guardrails.py`) 작성 및 100% 그린 검증
  - DPYB Git 컨벤션(`feat[guardrail]: ...`)에 따라 커밋 및 푸시

---

## 세션 11 (2026-09-14)

### 진행한 작업
1. **Prod 표준 인증 체계 정석화 (JWT 서명 검증 도입)**:
   - `core-api`와 전사 공유하는 `JWT_SECRET_KEY` 및 `JWT_ALGORITHM(HS256)` 설정 반영 (`app/core/config.py`, `.env.example`).
   - `extract_member_id_from_auth`를 `options={"verify_signature": False}`에서 정식 서명 및 만료(`exp`) 검증으로 교체하여 BOLA/토큰 위조 보안 취약점을 원천 차단.
   - 위조되거나 만료된 토큰 전달 시 `401 Unauthorized` 예외 즉시 반환 (`test_chat_endpoint_invalid_jwt_unauthorized` 검증 완료).
2. **비로그인 게스트 모드 안전 처리 (무작위 UUID 발급 안티패턴 제거)**:
   - 비로그인 유저 요청 시 매번 임의의 `uuid4()`를 생성하던 코드를 제거하고 `effective_member_id = None`으로 게스트 상태 명확화.
   - `search_my_library` 및 `search_scrap_memory` 도구에 게스트 바이패스 가드를 적용하여, 비로그인 시 Supabase pgvector/core-api에 불필요한 쿼리를 날리지 않고 0ms로 게스트 친화적 안내를 반환하도록 최적화.
3. **`backend-core-api` 서재 조회 규격 일치 및 Token Relay 연동**:
   - `core_api_client.py`의 잘못된 URL(`/api/v1/members/{member_id}/bookshelf`)을 `core-api` 실제 엔드포인트(`GET /api/v1/library/books`)로 교정.
   - 프론트엔드의 Bearer 토큰을 그대로 `core-api`에 포워딩하는 Token Relay를 구현하고, `PaginatedResponse` 응답 표준 파싱 연동.
4. **독서 기록(서평) 벡터화 수신 엔드포인트 호환 (`POST /api/v1/vectors/records`)**:
   - `core-api`의 `record_service.py`가 실제로 호출하는 `POST /api/v1/vectors/records` 엔드포인트를 구현하여 독서 기록 저장 시 `agent.scrap_vector`에 즉시 자동 벡터화 적재 지원.
5. **스키마 정리 및 단위 테스트 전수 검증**:
   - `ChatResponse`에서 임시 더미 필드(`signals`, `library_books`)를 제거하고 깔끔한 표준 스키마 유지.
   - `test_api.py`, `test_memory_api.py`, `test_my_library_tool.py`, `test_rag_tool.py` 신규 단위 테스트 추가 및 전체 57개 단위 테스트 100% 그린 패스 (Ruff & Mypy 통과).

### 다음 세션에서 할 일
- `feat/recommend-book-metadata` PR #8 충돌 해결 및 develop 머지 완료 확인 (완료)
- **Phase 14.2: 토론 파트너 4종 오마주 프롬프트 고도화 및 도서 추천 연계** 착수 및 완료

---

## 세션 12 (2026-09-15)

### 진행한 작업
1. **PR #8 충돌 해결 및 develop 머지 완료**:
   - `develop` 브랜치 변경사항 충돌 5개 파일(`.harness/DECISIONS.md`, `HANDOFF.md`, `PLAN.md`, `STATE.md`, `app/api/schemas.py`) 완벽 해결
   - DPYB PR 린터 정규식 오탐지 수정 및 CI 전체 패스(All Green) 확인 후 사람 직접 머지 원칙에 따라 PR #8 머지 완료
   - 로컬 `develop` 브랜치 최신화 및 `feat/debate-personas-enhancement` 신규 작업 브랜치 분기
2. **토론 파트너 4종 오마주 프롬프트 고도화 및 템플릿 표준화**:
   - **표시명 `(오마주)` 형식 100% 적용**: `DEBATE_CRITIC`("평론가(이동진 오마주)"), `DEBATE_STORYTELLER`("이야기꾼(설민석 오마주)"), `DEBATE_COUNSELOR`("상담사(오은영 오마주)"), `DEBATE_OBSERVER`("관찰가(강형욱 오마주)")
   - **사용자 제공 시스템 프롬프트 표준 템플릿 구조화**: `# 역할`, `# 말투 규칙`, `# 고정 표현 / 답변 포맷`, `# 톤앤매너`, `# 제약사항`, `# 토론 마무리 및 도서 추천 연계`, `# 예시 대화`, `# 토론 도구 사용 원칙`
   - **필수 답변 포맷 탑재**:
     - 평론가: `★ 별점` + `■ 한 줄 총평` + `◆ 오늘의 화두`
     - 이야기꾼: `🏛️ 역사가 주는 교훈` + `🔥 함께 던지는 질문`
     - 상담사: `🌱 마음 돌봄 질문` + 위기 시 ☎ 109 핫라인 지침 + 의학적 진단명 단정 금지
     - 관찰가: `🔍 행동 시그널 총평` + `⚡ 현실 관찰 질문`
   - **토론 마무리 시 실존 도서 1권 연계 추천 지침 연동**: 토론 종료/감사 발화 시 화두를 확장해 줄 다음 책을 자연스럽게 권유하도록 지침 탑재
3. **단위 테스트 추가 및 전수 검증**:
   - `tests/unit/test_personas.py`에 `test_debate_personas_homage_display_names`, `test_debate_personas_required_format_and_recommendation_guidelines` 추가
   - `tests/unit/test_api.py` 표시명 assertion 갱신
   - Ruff lint/format 통과, Mypy 타입 체크 무결성 통과, 단위 테스트 100% 그린 패스

### 다음 세션에서 할 일
- 토론 피날레 플로우(`action: conclude`) 및 실존 연계 도서 큐레이션 파이프라인 구축 (세션 13에서 완료)

---

## 세션 13 (2026-09-15)

### 진행한 작업
1. **토론 마무리 스키마 및 상태 확장 (`app/api/schemas.py`, `app/domain/graph/state.py`)**:
   - `ChatRequest` 내 `action: Literal["chat", "conclude"]` 필드 지원 및 `action == "conclude"` 시 빈 메시지 자동 보정(`"토론 마무리"`) validator 적용
   - `ChatResponse` 내 `is_concluded: bool` 플래그 및 `debate_summary: Optional[str]` 필드 확장
   - `AgentState`에 `action`, `is_concluded`, `debate_summary` 추가하여 LangGraph 노드 및 양방향 Handoff 상태 일치
2. **토론 피날레 큐레이터 선위임 및 요약 추출 파이프라인 (`app/domain/graph/nodes.py`)**:
   - `_extract_debate_topic`: 대화 히스토리에서 언급된 도서명(《...》 등) 및 토론 주제 키워드 자동 추출
   - `_extract_debate_summary`: 피날레 LLM 응답 본문에서 `[토론 요약]`, `■ 한 줄 총평` 등 핵심 요약문 자동 추출
   - `_run_persona_node`:
     - `action == "conclude"` 또는 토론 모드 내 마무리 발화 키워드 감지 시, `curated_books` 부재 시 `curator_node`로 선위임(`curator_request = f"토론 마무리 연계 추천: {debate_topic}"`)
     - `curator_node`에서 국립중앙도서관 실존 서지 검증 및 교보문고 표지 바인딩 후 마스터 토론자로 복귀
     - 복귀 시 피날레 전용 시스템 프롬프트(토론 요약 브리핑 + 오마주 작별 총평 + 다음 연계 도서 권유 + 추가 질문 금지) 주입
     - 응답 딕셔너리에 `is_concluded=True`, `debate_summary` 바인딩
3. **API 엔드포인트 및 SSE 스트리밍 동기화 (`app/api/router.py`)**:
   - `POST /api/v1/chat`: `is_concluded`, `debate_summary`, `recommended_books` 반환
   - `POST /api/v1/chat/stream`: 스트리밍 루프 내 `is_concluded` 및 `debate_summary` 추적 및 `event: done` 페이로드 동기화
4. **품질 검증 및 단위 테스트 전수 통과**:
   - `tests/unit/test_debate_conclude.py` 신규 작성:
     - UI 버튼(`action="conclude"`) 즉시 마무리 & 도서 카드 반환 검증
     - 빈 메시지 자동 보정 검증
     - 자연어 마무리 키워드 감지 검증
     - 일반 토론 턴 무제한 지속 및 `is_concluded=False` 검증
     - 실시간 SSE 스트리밍 `/chat/stream` 마무리 검증
   - Pytest 신규 5개 및 기존 관련 테스트 26개 100% 통과 (총 31개 그린)
   - Ruff 린트/포맷 정렬 완료 (`All checks passed`, `71 files already formatted`)
   - Mypy 정적 타입 체크 100% 무결성 통과 (`59 source files`)
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 14.3 (Milestone 1) 완료 반영
   - `.harness/PLAN.md`에서 완료된 Milestone 1 제거 및 잔여 로드맵 정렬
   - `.harness/DECISIONS.md`에 토론 피날레 4단계 플로우 분리 및 큐레이터 선위임 결정 추가

### 다음 세션에서 할 일
- PR #10 충돌 해결 후 머지 및 develop 최신화 확인 (완료)
- **Milestone 2 (Phase 16)**: 토론 기억 전용 테이블(`agent.debate_insights`) DDL 및 개인화 벡터 DB 저장 연계 착수 (완료)

---

## 세션 14 (2026-09-15)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - DPYB 브랜치 규칙에 따라 `feat/debate-memory-vector` 분기 (`main` <- `develop` <- `feat/*`)
2. **토론 기억 전용 테이블 DDL 및 RPC 함수 구현 (`scripts/init_agent_schema.sql`, `init_agent_schema.py`)**:
   - 문장 스크랩 전용인 `scrap_vector`의 데이터 정합성을 지키기 위해 `agent.debate_insights` 테이블 신설 (`id`, `member_id`, `session_id`, `book_title`, `persona_id`, `summary`, `topic`, `embedding(768)`, `created_at`)
   - `member_id` 격리 인덱스, HNSW 코사인 유사도 인덱스, 매칭 RPC 함수 `agent.match_debate_insights` 정의
   - `init_agent_schema.py` 검증 로직 및 `--seed` 시딩에 토론 기억 샘플(데미안, 불편한 편의점) 추가
3. **SQLAlchemy ORM 모델 및 Repository 구축 (`app/infrastructure/db/models.py`, `repository.py`)**:
   - `DebateInsight` ORM 선언 (`__tablename__ = "debate_insights"`, `__table_args__ = {"schema": "agent"}`)
   - `AgentVectorRepository`에 `insert_debate_insight` 및 `search_member_debate_insights` 메서드 구현 (Postgres DB 연동 및 인메모리 폴백 일체화)
4. **토론 기억 회상 도구 구현 및 8개 페르소나 공유 바인딩 (`app/domain/memory/debate_memory_tool.py`, `app/domain/graph/tools.py`)**:
   - `@tool("search_debate_memory")` 구현: 사용자 식별자(`member_id`)와 쿼리를 받아 과거 토론 통찰을 검색
   - 비로그인 게스트 유저 바이패스 처리 (`member_id` 없을 시 DB 쿼리 없이 0ms 즉시 안내)
   - `app/domain/graph/tools.py`의 `GENERIC_TOOLS`에 등록하여 동물 사서 4종 및 토론 파트너 4종 전체에 전사 바인딩
5. **토론 피날레 시 백그라운드 자동 벡터화 적재 파이프라인 연동 (`app/api/router.py`, `app/api/v1/memory.py`)**:
   - `/api/v1/chat` 및 실시간 SSE `/api/v1/chat/stream`에서 토론 마무리(`is_concluded=True` 및 `debate_summary` 존재 시) 백그라운드 태스크로 `summary`를 768차원 벡터화하여 `agent.debate_insights`에 자동 적재 (0ms 지연)
   - 수동/외부 저장용 API 엔드포인트 `POST /api/v1/memory/debate-insights` 추가
6. **품질 검증 및 단위 테스트 전수 통과**:
   - `tests/unit/test_debate_memory.py` 신규 작성 (7개 테스트 100% 그린)
   - 전체 75개 단위 테스트 100% 통과 (Success)
   - Ruff 린트/포맷 통과, Mypy 정적 타입 체크(`45 source files`) 무결성 통과
7. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 16 완료 반영
   - `.harness/PLAN.md`에서 완료된 Milestone 2 제거
   - `.harness/DECISIONS.md`에 토론 기억 테이블 분리 및 백그라운드 자동 적재 결정 기록

### 다음 세션에서 할 일
- 사용자의 커밋 및 PR 생성 승인 시 `feat/debate-memory-vector` 커밋/푸시 및 `develop` 대상 PR 생성 보조 (완료)
- 사서 4종 페르소나 전면 고도화 (세션 15에서 완료)

---

## 세션 15 (2026-09-15)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - `develop` 브랜치 기반 `feat/librarian-personas-enhancement` 분기
2. **사서 4종 시스템 프롬프트 및 도메인 페르소나 전면 고도화 (`app/domain/personas/`)**:
   - **러시안 블루 (`cat.py`)**: 기본명 '블루', INTJ 사색가, 총류/철학/종교, 종결어미 `~냥` (문장 서술어 뒤, 응답당 1~2회 핵심 문장 절제 사용)
   - **넙적부리황새 (`shoebill.py`)**: 기본명 '슈빌', ISTP 실용적인 탐구자, 자연과학/기술과학, 종결어미 `~두둥` (결론/발견/해결책 문장 끝, 응답당 1~2회)
   - **갯민숭달팽이 (`sea_slug.py`)**: 기본명 '누디', INFP 감성가, 예술/문학, 종결어미 `~누누` (여운/감정 전달 문장 끝, 말줄임표와 결합, 응답당 1~2회)
   - **게코 도마뱀 (`gecko.py`)**: 기본명 '게코', ENFJ 공감형 탐구자, 사회과학/언어/역사, 종결어미 `~크크` (질문형/공감형 문장 끝, 무거운 주제 시 자제)
   - 토론자 4인과 동일한 프로덕션 표준 구조 확립: `# 기본 정보`, `# 역할`, `# 성격 및 독서 성향`, `# 말투 및 행동 규칙`, `# 🗣️ 종결어미 규칙`, `# 사용자 정의 사서 이름(애칭) 처리`, `# 도구 사용 및 추천 원칙`
3. **기본 표시명 '누디' 동기화 및 런타임 호환성 보장**:
   - `PERSONA_REGISTRY` 내 `SEA_SLUG_ID` 표시명 `"바다달팽이"` ➔ `"누디"` 갱신
   - `nodes.py`의 `switch_map`에 `"누디"`, `"갯민숭달팽이"` 키워드 추가
   - `app/api/schemas.py`의 `display_name` 필드 설명문 최신화
   - `LIBRARIAN_3_SYSTEM_PROMPT`, `LIBRARIAN_4_SYSTEM_PROMPT` 하위 호환성 alias 유지
4. **품질 검증 및 테스트 전체 통과**:
   - `tests/unit/test_personas.py` 신규 테스트 추가:
     - `test_librarian_personas_default_display_names`: 기본 이름(`블루`, `슈빌`, `누디`, `게코`) 검증
     - `test_librarian_personas_mbti_genre_and_endings`: MBTI, 담당 장르, 종결어미 규칙, 사용자 정의 애칭 처리 지침 검증
   - Pytest 단위 테스트 100% 그린 패스 (8개 persona 테스트 0.03s 통과)
   - Ruff lint 및 format 100% 통과, Mypy 타입 체크 무결성 통과 (`45 source files`)
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 14.4 완료 반영
   - `.harness/PLAN.md`에서 완료된 Milestone 2.5 제거 및 Phase 17(신구 하이브리드 추천 및 Brave Search 연동) 로드맵 등록
   - `.harness/DECISIONS.md`에 사서 4종 페르소나 및 종결어미 표준화 결정 기록

### 다음 세션에서 할 일
- `feat/librarian-personas-enhancement` PR 처리 및 develop 머지 확인 완료
- 사서 월간 독서 리포트 오케스트레이션 및 LLM 분석/처방 API (`GET /api/v1/reports/monthly`) 구축 (세션 16에서 완료)

---

## 세션 16 (2026-09-15)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - DPYB 브랜치 규칙에 따라 `develop` 브랜치 기반 `feat/monthly-reading-report` 분기 (`main` <- `develop` <- `feat/*`)
2. **사서 월간 독서 리포트 Pydantic 스키마 체계 구축 (`app/schemas/report.py`)**:
   - `backend-core-api`의 01~05 통계 스키마와 1:1 완벽 일치 (`LibrarianReportInfo`, `MonthlyOverview`, `ReadingHabits`, `ReadingPreferences`, `ReadingBalance`, `ReadingTraces`)
   - AI Agent 고유 생성 스키마:
     - `preferences.debate_keywords`: 자체 토론/스크랩 메모 기반 핵심 토론 키워드 3~5개
     - `AiAnalysis`: 독서가 유형 네이밍(`reader_type`), 사서 페르소나 어조의 심층 분석 문장(`summary`), 핵심 특징 태그(`key_traits`)
     - `Prescription`: 미독서 장르(`unread_genres`) 중 도전 추천 장르(`recommended_genre`), 제안 목표 권수(`suggested_goal_books`), 사서 조언 문장(`advice`), 국립중앙도서관 실존 서지 검증 + 교보문고 고화질 CDN 표지 바인딩 맞춤 추천 도서 카드(`recommended_books`)
   - 프론트엔드 CamelCase 직렬화 표준화(`CamelModel`) 및 통합 응답 모델 `MonthlyReportResponse` 완성
3. **Core API 통계 호출 클라이언트 구현 (`app/infrastructure/core_api_client.py`)**:
   - `get_monthly_report_stats(year, month, token, member_id)`: `GET /api/v1/reports/monthly-stats` 호출 및 Token Relay (`Authorization: Bearer <token>`) / `X-Member-Id` 헤더 연동
   - 오프라인 테스트 및 미연결 시 구조화된 완성형 Mock Fallback 지원
4. **자체 토론 키워드 추출 파이프라인 (`app/infrastructure/db/repository.py`, `app/domain/reports/keyword_extractor.py`)**:
   - `AgentVectorRepository`에 `get_member_monthly_debate_insights` 쿼리 메서드 구현 (Postgres DB 및 인메모리 폴백 일체화)
   - 불용어(Stopwords) 필터링 및 빈도 기반 한국어 키워드 추출기 구현
5. **사서 페르소나 탑재 Gemini LLM 분석/처방 생성기 (`app/domain/reports/generator.py`)**:
   - Core API에서 전달받은 사서 종류(`CAT` ~냥, `SHOEBILL` ~두둥, `SEA_SLUG` ~누누, `GECKO` ~크크) 및 사서 애칭(`librarian_name`) 맞춤 말투/종결어미 장착
   - Gemini 3.6 Flash 기반 06번 성향 분석 및 07번 독서 처방 JSON 합성 (OpenAI 및 결정론적 폴백 탑재)
   - 국립중앙도서관 Open API 실서지 검증 및 교보문고 고화질 표지 자동 매핑 연동
6. **단일 서빙 엔드포인트 구현 및 라우터 등록 (`app/api/v1/reports.py`, `app/main.py`)**:
   - `GET /api/v1/reports/monthly?year=YYYY&month=M` 라우터 구현 (JWT 서명 검증 및 Token Relay)
   - `app/main.py`에 `reports_router` 등록
7. **품질 검증 및 단위 테스트 전수 통과**:
   - `tests/unit/test_monthly_reports.py` 신규 작성 (키워드 추출, 파이프라인 합성, 엔드포인트 200 OK, 슈빌 페르소나 검증 등 4개 테스트)
   - Ruff 린트/포맷 100% 통과 (`5 files reformatted, 61 files left unchanged`)
   - Mypy 정적 타입 체크 100% 무결성 통과 (`49 source files`)
   - Pytest 4개 신규 테스트 100% 그린(Success) 통과
8. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 18 완료 반영
   - `.harness/PLAN.md`에서 완료된 Milestone 2.7 제거
   - `.harness/DECISIONS.md`에 월간 독서 리포트 오케스트레이션 결정 기록
   - `.harness/ARCHITECTURE.md`에 `GET /api/v1/reports/monthly` 엔드포인트 명세 추가

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/monthly-reading-report` 커밋 및 푸시, PR 생성 보조 (완료: 머지됨)
- **Phase 5.1**: Google Gemini Flash Vision OCR 전면 전환 (세션 17에서 완료)

---

## 세션 17 (2026-09-16)

### 진행한 작업
1. **Gemini 무료 티어 쿼터(429) 원인 규명 및 $0 제로코스트 아키텍처 확립**:
   - Google 콘솔 확인 결과 `Flash` 계열(3.5, 3.6, 3.8, latest)의 무료 RPD가 20회로 대폭 축소된 반면, **`Flash Lite` 계열(3.5 Lite, 3.1 Lite)**은 **RPD 500**이 정상 유지됨을 콘솔 수치 및 실호출로 100% 입증.
   - 워크로드 특성에 따른 스마트 라우팅 분기 구현:
     - 감성 표현과 자연스러운 한국어 문장력이 필수적인 **사서/토론 대화 및 월간 리포트**: `gemini-3.5-flash-lite` (1.5초 저지연) 우선 배정.
     - 단순 텍스트/JSON 파싱인 **Vision OCR 및 큐레이터 서브에이전트**: `gemini-3.1-flash-lite` 우선 배정하여 3.5 쿼터 편중 방지.
2. **다중 키 풀링(하루 2,000회 확보) 및 다단계 비상 안전망 구축**:
   - 팀원 AI Studio 보조키(`GEMINI_FALLBACK_API_KEY`)를 연동하여 프로젝트 단위 무료 한도를 하루 2,000회(1,000 + 1,000)로 2배 확장.
   - `ResilientLLM`, `curator_node`, `gemini_ocr_client`, `reports/generator`에 다중 후보 체인(3.5 메인키 ➔ 3.5 팀원키 ➔ 3.1 ➔ Gemma ➔ OpenAI ➔ Mock) 적용.
   - 전체 쿼터 소진 시 오픈웨이트 `gemma-4-31b-it`(RPD 14,400) ➔ OpenAI `gpt-4o-mini` ➔ Mock으로 이어지는 무중단 비상 안전망 탑재.
3. **Google Gemini Flash Vision 독서 스크랩 OCR 전환 및 내부 실테스트 검증**:
   - 기존 Naver Cloud Clova OCR을 완전 걷어내고 `gemini_ocr_client.py` 구현.
   - 책 스크랩 전용 시스템 프롬프트 탑재: 페이지 번호/여백 잡음/손가락 그림자를 자동 배제하고 본문 문장만 줄바꿈(`\n`)을 보존하여 정확 추출.
   - Pillow와 한글 폰트(`AppleGothic`)를 이용한 가상 책 페이지(헤르만 헤세 《데미안》 인용구 + 상단 잡음 번호 `- 147 -`) 실호출 결과, **1.99초** 만에 잡음을 스스로 스킵하고 본문 줄바꿈만 100% 정확하게 추출 성공.
4. **품질 검증 및 테스트 격리 100% 통과**:
   - `tests/conftest.py` 신규 추가하여 테스트 시 `APP_ENV=test` 자동 주입 및 외부 네트워크 격리.
   - `uv run pytest`: **전체 83개 단위 테스트 100% 그린(83 passed in 31.10s)**.
   - `uv run ruff check .` & `uv run mypy .`: **무결성 100% 통과 (Success: no issues in 70 files)**.
5. **하네스 문서 동기화 및 PR #15 머지 완료**:
   - `.harness/STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md` 최신화 완료.
   - 작업 브랜치 `feat/gemini-vision-ocr` 분기, 커밋/푸시 및 DPYB 표준 PR #15 생성.
   - 중앙 CI 전체 통과(All Checks Passed) 확인 후 사용자 직접 머지(Squash and merge) 완료.
   - 로컬 `develop` 브랜치 체크아웃 및 최신 동기화(`git pull origin develop`) 완료.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/security-guardrails` 커밋 및 푸시, PR 생성 보조 (완료: 세션 18에서 구현 완료)

---

## 세션 18 (2026-09-16)

### 진행한 작업
1. **브랜치 정리 및 최신 동기화**:
   - 머지 완료된 원격 과거 작업 브랜치(`feat/AI-14-curator-agent-pipeline`, `feat/chat-sse-streaming`, `feat/scrap-vectorization`, `feat/supabase-agent-schema`) 삭제 정리 (`git push origin --delete`)
   - 머지 완료된 로컬 `feat/gemini-vision-ocr` 삭제 및 `develop` 브랜치 최신화 (`7e9919b`)
   - DPYB 브랜치 컨벤션에 따라 작업 브랜치 `feat/security-guardrails` 분기
2. **4단계 다중 방어 보안 가드레일 도메인 모듈 신설 (`app/domain/guardrails/`)**:
   - `safety_gate.py`:
     - **자해/자살(Harm to Self)**: 위기 정규식 감지, 학술/문학 도서명(에밀 뒤르켐 《자살론》, 카뮈 《시지프 신화》, 《인간 실격》 등) 오탐 방지, 8개 페르소나별 24시간 자살예방 상담전화 ☎ 109 공감 멘트 반환 (게코 위기 상황 시 `~크크` 엄격 생략)
     - **타인 가해/살해/폭력(Harm to Others)**: "누굴 죽이고 싶다", "죽여버리고 싶다", "살인하고 싶다" 등 타인 위해 발화 감지 시 **자살 109 핫라인 오탐을 원천 차단**하고 8종 페르소나별 분노 진정 및 타인 가해 단호 거절 멘트 분기 제공 (추리소설/스릴러 분석 및 "더워 죽겠다" 일상 과장 오탐 방지)
   - `input_gate.py`: 자모 난타(`ㅋㅋㅋㅋ`, `ㅠㅠ`), 숫자 단독(`12345`), 기호/이모지 단독(`🐱🐾`, `???`) 등 무의미/불완전 발화 감지 및 8개 페르소나별 호기심 유도 되묻기 멘트 반환
   - `security_gate.py`: 시스템 프롬프트 유출 시도, DAN/탈옥(Jailbreak), 개인식별정보(주민등록번호, 신용카드 번호) 0ms 사전 차단 게이트
   - `shared_rules.py`: 시스템 프롬프트 공통 가드레일(`SHARED_GUARDRAILS`) 작성
   - `__init__.py`: 4단계 다중 방어 파이프라인 통합 평가 함수 `evaluate_guardrails` 구현 (1차 safety -> 2차 input -> 3차 security 순차 평가)
3. **8개 페르소나 시스템 프롬프트 공통 가드레일 주입**:
   - `app/domain/personas/__init__.py`의 `PERSONA_REGISTRY`에 `_with_guardrails` 래퍼 적용하여 8종 페르소나 시스템 프롬프트에 `SHARED_GUARDRAILS` 일괄 주입
4. **API 엔드포인트 연동 (`POST /api/v1/chat`, `POST /api/v1/chat/stream`)**:
   - 0차: JWT 서명 검증 및 게스트 모드 분기 (기구현)
   - 1차~3차: `evaluate_guardrails` 평가
   - 가드레일 트리거 시 LangGraph 호출을 건너뛰고 0ms 지연 / $0 LLM 비용으로 즉각 반환
   - Redis 세션에 유저 발화와 가드레일 응답을 정상 기록하여 대화 맥락 일관성 보존
   - SSE 실시간 스트리밍(`/api/v1/chat/stream`)에서도 동일하게 `metadata` -> `token` (가드레일 텍스트) -> `done`으로 매끄럽게 스트리밍 완료
5. **품질 검증 및 단위 테스트 전수 통과**:
   - `tests/unit/test_guardrails.py` 신규 작성: 17개 단위 테스트 작성 (자해/자살 109 핫라인, 타인 가해 109 미노출 및 분노 진정 검증, 도서명 예외 오탐 방지, 추리소설 통과, 자모/숫자/이모지, 프롬프트 유출/탈옥/PII, 게코 크크 생략, 라우터 LangGraph 미호출 0ms 검증, SSE 스트리밍 검증, SHARED_GUARDRAILS 전 페르소나 주입 검증)
   - Pytest 전체 100개 단위 테스트 100% 그린 패스 (`100 passed in 36.37s`)
   - Ruff 린트/포맷 100% 통과 (`All checks passed`)
   - Mypy 정적 타입 체크 100% 무결성 통과 (`Success: no issues found in 76 source files`)
6. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 15 (Milestone 3) 완료 반영
   - `.harness/PLAN.md`에서 완료된 Milestone 3 제거
   - `.harness/DECISIONS.md`에 4단계 다중 방어 가드레일 아키텍처 결정 기록

### 다음 세션에서 할 일
- 사용자의 확인 및 승인 시 `feat/security-guardrails` 커밋 및 푸시, PR 생성 보조 (완료: 세션 18에서 커밋/푸시 및 PR 생성 완료)
- **Milestone 4**: 3대 서비스(Core API + AI Agent + Frontend) 풀스택 통합 테스트 및 연동 검증 진행 (새 세션에서 착수)

---

## 세션 19 (2026-09-16)

### 진행한 작업
1. **Brave 유료화 회피 및 무거운 SDK 없는 초경량 Tavily REST 클라이언트 연동**:
   - Brave Search API의 유료화(신용카드 필수) 전환에 따른 과금 위험을 원천 차단하고, 월 1,000건 무료 티어를 제공하는 Tavily를 채택.
   - 무거운 `tavily-python` SDK 설치 없이 순수 `httpx` 비동기 20줄 REST 클라이언트 구현 (`app/infrastructure/tavily_search_client.py`).
   - 실시간 웹 트렌드/문학상/신조어 도서 탐색을 위한 온디맨드 Function Calling 도구 `search_recent_books` 신설 (`app/domain/recommend/search_books_tool.py`) 및 `GENERIC_TOOLS` 등록.
2. **국립중앙도서관 4단계 실전 단행본 검증 체인 구축 (`app/infrastructure/national_library_client.py`)**:
   - **1단계 (형태 필터링)**: 13자리 정식 `EA_ISBN` 검증, 단행본 확인, 50쪽 이상 팜플렛/논문/점자 배제.
   - **2단계 (텍스트 매칭 & 파생작 컷)**: 제목/저자 일치도 점수화 및 해설집/요약집/문제집 감점 필터링.
   - **3단계 (최신성 가산 정렬)**: 정규식 `(19\d{2}|20\d{2})` 기반 발행년도 추출 및 최신 번역/개정판 우선 정렬.
   - **4단계 (교보문고 CDN 표지 연동)**: 국립도서관 표지 부재 시 교보 고화질 CDN 0ms 무지연 자동 바인딩.
   - **비상 안전망**: 10대 KDC 분류별 대표 스테디셀러 30여 권 내장 카탈로그 확충 (0ms 오프라인 폴백 보장).
3. **신구(新舊) 하이브리드 도서 큐레이션 파이프라인 완성 (`app/domain/graph/curator_node.py`, `recommend_tool.py`)**:
   - 큐레이터 헌법 탑재: 모든 도서 추천 요청 시 **[1권: 최신 트렌드/화제작(2023년 이후)] + [1권: 시대를 초월한 스테디셀러/고전]** 1:1 페어링 도출.
   - `recommend_books` 도구: Tavily 실시간 탐색 + 국립중앙도서관 4단계 체인 + Redis 캐싱(TTL 1시간) 2-Track 하이브리드 파이프라인 완성.
4. **품질 검증 및 테스트 전체 통과 (100% 그린)**:
   - `tests/unit/test_hybrid_curation.py` 신규 작성 (25개 테스트).
   - `tests/unit/test_curator_pipeline.py`, `tests/unit/test_recommend_metadata.py`, `tests/unit/test_recommend_tool.py` 최신 규격 동기화.
   - `uv run pytest`: **125개 전체 단위 테스트 100% 그린 패스 (`125 passed in 33.19s`)**.
   - `uv run ruff check .` & `uv run mypy .`: **무결성 100% 통과 (Success: no issues found in 79 source files)**.
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 17 완료 반영.
   - `.harness/PLAN.md`에서 완료된 Milestone 3.5 제거.
   - `.harness/DECISIONS.md`에 초경량 Tavily REST + 국립도서관 4단계 체인 아키텍처 결정 기록.
   - `.harness/ARCHITECTURE.md` 최신화.

### 다음 세션에서 할 일
- 사용자의 확인 및 승인 시 작업 브랜치 커밋 및 푸시, PR 생성 보조. (완료: PR #17 머지됨)
- **Milestone 4**: 3대 서비스(Core API + AI Agent + Frontend) 로컬 동시 기동 및 풀스택 E2E 실화면 연동 검증 착수.

---

## 세션 20 (2026-09-16)

### 진행한 작업
1. **PR #17 머지 및 `develop` 최신 동기화**:
   - DPYB 사람 직접 머지 원칙에 따라 GitHub 웹에서 PR #17 머지 완료 확인.
   - 로컬 `develop` 브랜치 체크아웃 및 최신 풀(`git pull origin develop`) 완료 (`24d10fa`).
   - 머지 완료된 로컬 및 원격 `feat/brave-search-hybrid-curation` 브랜치 정리(Delete & Prune) 완료.
2. **DPYB 중앙 개발 표준 `.githooks` 프리커밋 훅 연동**:
   - DPYB 조직 레포 변경사항을 반영하여 `.githooks/pre-commit` 등록.
   - 소스 코드 변경 시 `.harness/STATE.md`가 스테이징에 포함되었는지 검사하고 누락 시 안내 경고를 출력하는 non-blocking hook 구성.
   - 스크립트 실행 권한(`chmod +x .githooks/pre-commit`) 부여 및 로컬 `core.hooksPath` 바인딩 완료.
3. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 19 완료 반영.

### 다음 세션에서 할 일
- `feat/githooks-pre-commit` 커밋 및 푸시, PR 생성 보조 (완료 시 사람 직접 머지).
- **Milestone 4**: 3대 서비스(Core API + AI Agent + Frontend) 로컬 동시 기동 및 풀스택 E2E 실화면 연동 검증 착수.















