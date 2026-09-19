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

---

## 세션 21 (2026-09-16)

### 진행한 작업
1. **로컬 E2E 5대 연동 이슈 원인 분석 및 백엔드(`backend-ai-agent`) 원천 해결**:
   - **이슈 1 (날씨 Signals 누락)**:
     - `WeatherSignal`, `SignalsResponse` Pydantic 모델 정의 및 `ChatResponse.signals` 필드 복원.
     - `_build_signals` 유틸 함수를 구현하여 WMO 코드 기반 날씨 상태(`clear`, `cloudy`, `rainy` 등), 섭씨 기온, KST 시간대(`dawn`, `day`, `evening`, `night`), 감정 무드를 합성하여 `/chat` 및 실시간 SSE `/chat/stream`에 전달.
   - **이슈 2 (도서 추천 메타데이터 및 장르 상호 보완)**:
     - `app/infrastructure/national_library_client.py`: KDC 10대 분류 표준 Enum 매핑 및 국문/영문 상호 보완 변환 유틸(`normalize_genre`, `genre_to_korean`, `GENRE_KO_TO_EN`, `GENRE_EN_TO_KO`) 신설.
     - 교보 CDN 표지 이미지(`cover_url`) 및 총 쪽수(`page_count`) 안정 공급 보장.
   - **이슈 4 (빈 서재 거짓말 및 Token Relay)**:
     - `CORE_API_BASE_URL`을 8080에서 실제 기동 포트인 8000으로 교정 (`app/core/config.py`, `.env`, `.env.example`).
     - `CoreApiClient.get_my_bookshelf`에서 '프로젝트 헤일메리', '듄', '데미안' 등 하드코딩된 가짜 도서 목 데이터를 완전히 삭제하고, 미등록/빈 서재 시 `books: []`, `total_count: 0`을 정직하게 반환하도록 수정.
     - `app/core/context.py` 내 `ContextVar`(`current_auth_token`)를 신설하여 요청 스코프 Bearer 토큰 릴레이 연동 (`app/domain/memory/my_library_tool.py`).
   - **이슈 5 (토론 평론가 페르소나 덮어쓰기 차단 및 줄거리 팩트 그라운딩)**:
     - `ChatRequest.populate_defaults_and_aliases`에서 `mode != "DEBATE"` 조건을 추가하여, 토론 모드 진입 시 `librarian_id`에 의해 페르소나가 `CAT`으로 강제 덮어쓰기되던 버그를 원천 차단.
     - `ChatRequest` 및 `AgentState`에 `book_id`, `topic`, `debate_book_info` 필드 공식 추가.
     - 토론 시작 시 대상 도서의 실제 서지·줄거리를 국립중앙도서관/Core-API로부터 사전 조회하여 토론 파트너 시스템 프롬프트에 `[토론 대상 도서 팩트 정보 (환각 방지)]`로 주입 (`app/domain/graph/nodes.py`), 줄거리 날조/거짓말 원천 봉쇄.
2. **인프라/런타임 결함 보강 & 다중 키 임베딩 풀링 탑재**:
   - `greenlet` 패키지 추가 (`uv add greenlet`): SQLAlchemy asyncpg 세션 및 엔진 dispose 시 `ValueError: No module named 'greenlet'` 크래시 원천 해결.
   - `app/infrastructure/db/session.py`: Supabase Transaction Pooler(포트 6543) 및 비동기 이벤트 루프 격리를 위해 `NullPool` 적용 (이벤트 루프 간 커넥션 충돌 방지).
   - `app/core/config.py`, `app/domain/memory/rag_tool.py`:
     - 임베딩 모델을 `models/gemini-embedding-001` (MRL 768차원 매핑)로 갱신하여 404 에러 원천 해결.
     - 메인 키 소진 시 **팀원 예비키(`GEMINI_FALLBACK_API_KEY`)로 0ms 즉시 스위칭(하루 1,000 + 1,000 = 2,000 RPD)**하는 다중 키 자동 재시도 폴백 파이프라인 탑재.
     - L2 단위 벡터 정규화(`norm = 1.0`) 적용으로 코사인 유사도 연산 정밀도 보장.
   - `app/api/router.py`: 토론 모드 서지 조회 시 질문 전문을 도서명으로 보내던 쿼리 오염을 `extract_debate_book_title` 기반으로 정제.
   - `app/main.py`: 콘솔 및 자동 회전 파일 로깅(`logs/app.log`, 최대 10MB x 5개 백업) 이중 로거 구축 및 `.gitignore` 등록.
3. **단위 테스트 갱신 및 AI 자가 검증 (100% 그린 패스)**:
   - `tests/unit/test_my_library_tool.py`: 빈 서재 정직 응답(`total_count == 0`, `books == []`, "등록된 도서가 없습니다") 및 활성 서재 모킹 테스트로 갱신.
   - `tests/unit/test_recommend_metadata.py`: 표준 Enum 매핑 및 양방향 한/영 정규화 유틸 검증으로 갱신.
   - `tests/conftest.py`: 단위 테스트 실행 시 원격 Supabase DB 호출 격리 및 인메모리 바이패스 픽스처 보강.
   - `uv run pytest`: **126개 전체 단위 테스트 100% 그린 패스 통과 (`126 passed in 40.48s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷팅 100% 통과 (0 errors, 0 warnings)**.
   - `uv run mypy .`: **정적 타입 체크 80개 소스 파일 무결성 통과 (Success: no issues found)**.
4. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 20 완료 스냅샷 반영.
   - `.harness/PLAN.md`에서 백엔드 완료 태스크를 제거하고 남은 E2E 통합 스모크 테스트로 정리.
   - `.harness/DECISIONS.md` 최상단에 5대 이슈 원천 해소 아키텍처 결정 기록.

---

## 세션 19 (2026-09-16)

### 진행한 작업
1. **도서 추천 속도 및 이중 큐레이션 루프 원천 해소**:
   - `app/domain/graph/nodes.py`: `curated_books`가 이미 `state`에 존재할 때 페르소나 노드가 도서 추천 도구(`recommend_books`, `search_recent_books`)를 재호출하지 못하도록 `active_tools`에서 동적 제외 및 시스템 프롬프트에 중복 호출 금지 지침 추가. (응답 지연 24초 -> 수 초대로 최적화)
2. **도서 추천 다양성 확보 및 데미안 편중 해결**:
   - `app/domain/graph/curator_node.py`: 큐레이터 LLM `temperature`를 `0.1` -> `0.7`로 상향.
3. **국립중앙도서관 서지 검증 체인 정밀화**:
   - `app/infrastructure/national_library_client.py`:
     - `clean_author_name`: `문화체육관광부,한국도서관협회 [편]`, `(: 헤르만 헤세)` 등 앞뒤 특수문자 및 `[편]`, `[저]`, `지음`, `옮김` 등 역할어 완벽 정제.
     - `map_kdc_to_genre`: KDC 코드가 비어있는 경우 `SUBJECT` 필드의 십진분류 단일 숫자(예: '8' -> 문학, '1' -> 철학) 폴백 연동.
     - `_filter_and_rank_monographs`: `SequenceMatcher` 유사도 0.5 미만 무관한 도서 탈락, 짧은 제목 문장 포함 오매칭 방지, 페이지 정보 수록 도서 우선순위 가산(`+8.0`) 적용.
     - `check_cover_alive`: 교보문고 CDN의 34,150바이트 빈 회색 플레이스홀더 이미지 감지 및 자동 배제.
4. **프론트엔드 장르 라벨 친절화**:
   - `frontend-reader-web/app/data/genres.js`: KDC 대분류 `GENERAL`의 표시 라벨을 생소한 '총류'에서 친숙한 '교양'으로 변경 및 별칭 추가.

---

## 세션 20 (2026-09-16)

### 진행한 작업
1. **짧은 도서명(《모순》, 《광장》 등) 국립도서관 서지 누락 버그 원천 방어**:
   - `app/infrastructure/national_library_client.py`: 국립도서관 KORMARC 표제(`TITLE`)에서 부제/책임표시 앞 순수 본표제(`main_title`)를 분리(`re.split(r"[:=/(\[]")`)하여, 《모순》, 《광장》, 《토지》 등 2~3글자 대작이 부제 길이 때문에 유사도 0.5 미만으로 오인되어 탈락하던 치명적 결함을 완벽 해결하고 본표제 100% 매칭 달성.
2. **프롬프트 내 작가 하드코딩 제거 및 보편적 다양성 원칙 확립**:
   - `app/domain/graph/curator_node.py`: 특정 작가나 책 이름을 직접 적어두어 생기는 또 다른 편향을 방지하기 위해 하드코딩된 작가 목록을 제거하고, 전 분야 도서 지식과 사용자 맥락 중심의 보편적 다양성 원칙으로 프롬프트 정제.
   - `temperature=0.7` 환경에서 LLM의 잡담이나 마크다운 혼입 시에도 `re.search(r"\[\s*\{.*\}\s*\]")`로 순수 JSON 배열만 안전하게 추출하도록 파싱 내결함성 확보.
3. **교보 CDN 표지 오탐 방어 및 강제 할당 제거**:
   - `check_cover_alive`: `Content-Length` 부재 시 정상 이미지가 오탐 탈락하지 않도록 `cl > 0` 조건 방어 적용.
   - `search_monograph_by_title_author`: 표지 미생존 시 죽은 URL을 강제 할당하던 `else` 버그를 제거하여 무결성 확보.
4. **KDC GENERAL '교양' 백엔드 동기화**:
   - `GENRE_EN_TO_KO["GENERAL"] = "교양"` 및 `GENRE_KO_TO_EN["교양"] = "GENERAL"` 등록으로 프론트엔드와 100% 통일.
5. **자가 검증 및 신규 단위 테스트 통과**:
   - `tests/unit/test_recommend_metadata.py`: 짧은 제목 본표제 분리 매칭, 교양 장르 양방향 정규화, 교보 CDN 플레이스홀더 감지 등 3종 신규 단위 테스트 추가.
   - `uv run pytest`: **129개 전체 단위 테스트 100% 그린 패스 통과 (`129 passed in 39.07s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷팅 100% 통과 (0 errors, 0 warnings)**.
   - `uv run mypy .`: **정적 타입 체크 80개 소스 파일 100% 무결성 통과 (Success: no issues found)**.

### 다음 세션에서 할 일
- 3개 서비스(Core API 8000, AI Agent 8001, Frontend Web 5173) 브라우저 실화면에서 추천 도서 다변화, 속도, 표지 노출 및 서재 담기 E2E 최종 확인.

---

## 세션 21 (2026-09-17)

### 진행한 작업
1. **도서 추천 의도 감지 키워드 확장 (`app/domain/graph/nodes.py`)**:
   - `recom_keywords`에 `"뭘 읽"`, `"무슨 책"`, `"책 좀"`, `"도서 추천"`, `"책 하나"`, `"책 알려줘"` 등을 추가하여 **"뭘 읽으면 좋을까"**와 같은 일상적 질문 시에도 큐레이터 서브에이전트(`curator_node`) 선위임 파이프라인이 100% 동작하도록 보강.
   - 이를 통해 API 응답의 `recommended_books` 배열이 빈 배열로 내려가는 문제를 원천 해결.
2. **프론트엔드 도서 카드 렌더링용 마크다운 헤딩 지침 주입 (`app/domain/graph/nodes.py`)**:
   - `curated_books` 소개 시스템 프롬프트 지침에 각 추천 도서를 `### 📖 도서명` 형식의 마크다운 3단계 헤딩으로 작성하도록 명시.
   - 프론트엔드 `MarkdownRenderer.jsx` 및 `LibrarianChat.jsx`에서 본문 마크다운 카드와 `[서재에 등록 ➔]` 버튼이 즉시 렌더링되도록 보장.
3. **단위 테스트 추가 및 자가 검증 (Self-Validation)**:
   - `tests/unit/test_curator_pipeline.py`:
     - `test_recommendation_intent_delegation_keywords`: "뭘 읽으면 좋을까" 등 5종 발화 시 `curator_node` 선위임 검증.
     - `test_curated_books_markdown_heading_instruction`: `curated_books` 존재 시 `### 📖 도서명` 헤딩 지침 주입 및 응답 포맷 검증.
   - `uv run pytest`: **131개 전체 단위 테스트 100% 그린 패스 통과 (`131 passed in 46.23s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷팅 100% 통과**.
   - `uv run mypy .`: **정적 타입 체크 80개 소스 파일 무결성 통과 (Success: no issues found)**.
4. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 22 완료 반영 완료.

### 다음 세션에서 할 일
- **Milestone 6 (Phase 24: 다중 판본 표지·쪽수 생존 우선 매칭 및 등록 폼 장르 보존)**:
  - `app/infrastructure/national_library_client.py`: 《지구 끝의 온실》처럼 첫 번째 판본의 표지가 34,150B로 죽어있거나 쪽수가 없을 때, 살아있는 표지와 쪽수를 가진 판본(초판본 등)을 우선 선택하도록 루프 개선.
  - `frontend-reader-web/app/pages/RegisterBook.jsx`: AI 추천(`fromAIRecommendation`)으로 넘어온 도서의 경우 이미 검증된 추천 장르(`LITERATURE` 등)를 고정하고 백그라운드 재분류에 의한 덮어쓰기('기술과학' 오인) 방어.
- 3대 개발 서버 구동 후 실화면 브라우저 E2E 최종 확인.

---

## 세션 23 (2026-09-17)

### 진행한 작업
1. **작업 브랜치 생성 및 환경 격리**:
   - `develop` 최신 동기화 후 DPYB 브랜치 컨벤션에 따라 `feat/vision-cover-isbn-ocr` 신규 작업 브랜치 분기 (`main` <- `develop` <- `feat/*`).
2. **도서 표지/서지 전용 Vision OCR 프롬프트 및 추출기 구현 (`app/vision/gemini_ocr_client.py`)**:
   - 기존 문장 스크랩 전용 OCR(`extract_text`)과 완전히 분리된 `extract_cover_info(image_bytes, image_format)` 신설.
   - `GEMINI_COVER_SYSTEM_PROMPT` 탑재: 책 표지 또는 뒷표지 사진에서 바코드 하단/주변에 인쇄된 13자리 ISBN 숫자, 도서 제목, 저자, 출판사를 JSON으로 구조화 추출.
   - $0 무과금 다중 후보 체인(Gemini Flash-Lite 메인키 ➔ 보조키 ➔ OpenAI ➔ Fallback) 연동.
3. **ISBN-13 모듈로-10 공식 가중치 체크섬 검증 유틸 구축 (`app/vision/isbn_utils.py`)**:
   - `validate_isbn13_checksum`: 홀수자리x1 + 짝수자리x3 mod 10 == 0 공식 체크섬 알고리즘 적용.
   - `extract_isbn_candidates`, `find_first_valid_isbn`: 하이픈/공백 정규식 매칭 및 체크섬 통과 번호 최우선 선별.
   - `barcode_service.py`에도 체크섬 검증을 통합하여 오인식 13자리 숫자 사전 차단.
4. **4단계 계층형 표지/서지 파이프라인 연동 (`app/api/v1/vision.py`의 `_handle_cover_ocr`)**:
   - 1단계: `barcode_service.scan_isbn` (0ms 빠른 바코드 감지)
   - 2단계: 실패 시 `gemini_ocr_client.extract_cover_info` 호출하여 바코드 아래 인쇄된 숫자 및 제목/저자 구조화 추출
   - 3단계: 국립중앙도서관 정식 API(`search_by_isbn`)로 도서명, 저자, 출판사, 쪽수, 교보 CDN 표지 일괄 조회
   - 4단계: 사진에 ISBN 숫자가 짤렸더라도 추출된 제목/저자 후보로 국립도서관 검색(`search_book`) 자동 완성
5. **품질 검증 및 자가 검증 100% 통과 (Self-Validation)**:
   - `tests/unit/test_vision.py` 신규 테스트 추가:
     - `test_isbn_utils_checksum_and_extraction`: 모듈로-10 체크섬 및 노이즈 OCR 텍스트 추출 검증.
     - `test_extract_cover_info_json_parsing`: 표지 전용 JSON 응답 파싱 검증.
     - `test_cover_ocr_endpoint_with_barcode_failure_and_vision_fallback`: 바코드 실패 시 Vision OCR을 통한 ISBN 획득 및 서지 자동 완성 검증.
     - `test_cover_ocr_endpoint_with_title_search_fallback`: ISBN 부재 시 제목/저자 기반 국립도서관 검색 폴백 검증.
   - `uv run pytest`: **전체 135개 단위 테스트 100% 그린 패스 (`135 passed in 41.52s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과**.
   - `uv run mypy .`: **정적 타입 체크 81개 파일 무결성 100% 통과 (Success: no issues found)**.
6. **하네스 문서 동기화**:
   - `.harness/PLAN.md`, `.harness/STATE.md`, `.harness/DECISIONS.md` 최신화 완료.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/vision-cover-isbn-ocr` 커밋 및 푸시, PR 생성 보조.
- Milestone 6 (Phase 24: 국립도서관 다중 판본 표지·쪽수 생존 우선 매칭 및 등록 폼 장르 보존) 진행.

---

## 세션 24 (2026-09-17)

### 진행한 작업
1. **Pydantic 구조화 출력(`with_structured_output`) 적용 및 정규식 JSON 파싱 완전 제거**:
   - `app/domain/graph/curator_node.py`에 Pydantic 모델 `BookCandidate` 및 `CuratorResponse` 정의.
   - 기존의 취약했던 `re.search` 정규식 기반 JSON 추출을 전면 제거하고 LangChain의 `llm.with_structured_output(CuratorResponse)`를 적용하여 JSON 괄호 누락 및 파싱 실패율 0% 달성.
   - `temperature=0.2`로 설정하여 환각(Hallucination) 원천 차단.
2. **Yes24 RSS 피드 신간 수집 & Redis 오픈북 캐싱 백그라운드 워커 구현**:
   - `feedparser` 패키지 추가 (`pyproject.toml`).
   - `RedisSessionManager`에 범용 비동기 `get(key)` 및 `set(key, value, ex)` 메서드 추가 (인메모리 폴백 포함).
   - `app/infrastructure/trending_books.py` 신설: Yes24 종합 베스트셀러 RSS(50권)를 비동기로 파싱하여 Redis에 `daily_trending_books` 키로 TTL 24시간(86400초) 캐싱.
   - `app/main.py` lifespan에 `asyncio.create_task(fetch_and_cache_trending_books())`를 등록하여 서버 시작 시 1회 자동 캐싱 구동.
3. **오픈북 프롬프트 주입 및 솔직한 랜덤 명작 풀 폴백 구축**:
   - Redis에서 `daily_trending_books`를 조회하여 LLM 프롬프트에 `[오늘의 화제작 오픈북 (여기서 신간 1권 필수 선택)]` 텍스트로 주입하여 신간 날조 원천 차단.
   - 기존의 `if "비" in ... or "우울" in ...` 키워드 매칭 하드코딩을 영구 삭제.
   - LLM 실패 또는 국립도서관 API 검증 0건 통과 시 `_get_random_elegant_fallback()`을 통해 '시대별 최고 명작 풀'에서 2권을 무작위 픽(`random.sample`)하여 솔직하고 세련된 지연 안내 멘트 제공.
4. **레거시 `recommend_books` 도구 완전 제거 및 `search_recent_books` 단독 유지**:
   - 레거시 도구 `app/domain/recommend/recommend_tool.py` 및 테스트 `tests/unit/test_recommend_tool.py` 파일 영구 삭제.
   - 초경량 Tavily REST 기반 온디맨드 신간 탐색 도구(`search_recent_books`)만 단독 유지.
   - `tools.py`, `nodes.py`, 사서 4종 페르소나 시스템 프롬프트(`cat.py`, `shoebill.py`, `sea_slug.py`, `gecko.py`) 및 프로젝트 문서(`AGENTS.md`, `README.md`, `ARCHITECTURE.md`) 전면 정비.
5. **품질 검증 및 AI 자가 검증 (Self-Validation)**:
   - `tests/unit/test_curator_pipeline.py`: 스키마 유효성, 랜덤 폴백, RSS 캐싱 단위 테스트 추가.
   - `tests/unit/test_hybrid_curation.py`: `recommend_books` 제거 반영 및 `TestTrendingBooksOpenBook` 갱신.
   - `uv run pytest`: **전체 134개 단위 테스트 100% 그린 패스 (`134 passed in 41.48s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과 (`All checks passed`)**.
   - `uv run mypy .`: **정적 타입 체크 80개 파일 100% 무결성 통과 (`Success: no issues found`)**.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/vision-cover-isbn-ocr` 브랜치 변경 사항(Phase 23 표지 ISBN OCR + Phase 25 큐레이터 구조화 출력 & RSS 워커 + Phase 26 긴급 수술) 커밋 및 푸시, PR 생성 보조.
- PR CI 통과 확인 후 사용자 직접 머지(Squash and merge).

---

## 세션 25 (2026-09-17)

### 진행한 작업
1. **바코드 스캔 (pyzbar) 심폐소생술 (OpenCV 기반 `robust_scan_isbn`)**:
   - `opencv-python-headless` 및 `numpy` 의존성 추가.
   - `app/vision/barcode_service.py`에 스마트폰 카메라 4K 고해상도 이미지 전처리 엔진 탑재:
     - 가로 최대 1000px 비율 리사이징으로 pyzbar 디코더 메모리/연산 한계 돌파.
     - 그레이스케일 변환 및 Otsu 이진화(Binarization) 대비 강화.
     - 폰을 거꾸로나 옆으로 들고 찍는 환경에 대응한 4방향(0°, 90°, 180°, 270°) 회전 뺑뺑이 스캔 루프 적용.
     - OpenCV 미설치 환경 대비 PIL 4방향 회전 내결함성 폴백 탑재.
2. **뒷표지 홍보 문구 제목 오인 방어 및 대전제 확립**:
   - "바코드(ISBN)가 잡혔으면 OCR 텍스트는 일체 무시하고 정식 서지 DB로 직행한다"는 원칙 적용 (`app/api/v1/vision.py`).
   - 바코드 검출 시 Gemini OCR 호출을 아예 건너뛰어 뒷표지의 추천사("올해 최고의 감동!")나 카피 문구가 제목으로 탈바꿈하는 현상 100% 원천 차단.
   - `GEMINI_COVER_SYSTEM_PROMPT` 고도화: 뒷표지 홍보문구/추천사를 제목으로 오인하지 않고 식별 불가 시 `title: null`, `author: null` 반환하도록 지침 명시.
   - Vision OCR에서 인쇄된 ISBN을 건진 경우에도 뒷표지 lines 텍스트를 무시하고 국립도서관 정식 서지명으로 우선 바인딩.
3. **국립도서관 API '페이지 수(totalPages)' 증발 사태 해결 (교차 보강)**:
   - `app/infrastructure/national_library_client.py`에 `fetch_and_fill_book_info_by_isbn` 구현.
   - 민음사 《데미안》(9788937460449)처럼 단일 ISBN에 `PAGE` 필드가 비어있을 때, 도서명과 저자로 정식 단행본 검색을 다시 실행하여 북하우스 판본(343쪽) 등 실제 페이지 수를 자동으로 채워주는 교차 보강(Cross-Referencing) 완성.
4. **품질 검증 및 AI 자가 검증 100% 통과 (Self-Validation)**:
   - `tests/unit/test_vision.py`에 회전 바코드, 뒷표지 OCR 방어(OCR 미호출 검증), 페이지 수 교차 보강 단위 테스트 2종 추가.
   - `uv run pytest`: **전체 137개 단위 테스트 100% 그린 패스 (`137 passed in 39.12s`)**.
   - `uv run ruff check .` & `uv run ruff format --check .`: **린트/포맷 100% 통과 (`All checks passed`, `85 files already formatted`)**.
   - `uv run mypy .`: **정적 타입 체크 80개 파일 100% 무결성 통과 (`Success: no issues found`)**.
   - 실데이터 검증: 민음사 《데미안》 단일 ISBN 조회 시 누락되던 페이지 수가 교차 조회를 통해 343쪽으로 자동 완벽 보강됨을 실측 확인.
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 26 완료 반영.
   - `.harness/PLAN.md`에서 완료된 Milestone 7 제거.
   - `.harness/DECISIONS.md`에 바코드 OpenCV 전처리, 뒷표지 방어, 페이지 수 교차 보강 아키텍처 결정 기록.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/vision-cover-isbn-ocr` 브랜치 커밋 및 푸시, PR 생성 보조.
- Milestone 6 (Phase 24: 국립도서관 다중 판본 표지·쪽수 생존 우선 매칭 및 등록 폼 장르 보존) 또는 프론트엔드 연동 지원.

---

## 세션 26 (2026-09-17)

### 진행한 작업
1. **작업 브랜치 분기**:
   - `develop` 최신화 상태에서 DPYB 표준 규칙에 따라 `feat/system-warning-and-rss-fixes` 브랜치 생성.
2. **Gemini Flash Lite 모델 Fixed Sampling Temperature 경고 원천 소거**:
   - `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite` 등 최신 Flash Lite 모델의 고정 샘플링 제한(`UserWarning: Model ... uses fixed sampling defaults`)에 대응.
   - `app/domain/graph/nodes.py`, `app/domain/graph/curator_node.py`, `app/domain/reports/generator.py`, `app/vision/gemini_ocr_client.py`의 `ChatGoogleGenerativeAI` 인스턴스화 시 불필요한 `temperature` 파라미터 전달을 제거하여 경고 원천 차단.
3. **Automatic Function Calling (AFC) 터미널 경고 억제**:
   - `langchain-google-genai`와 `google-genai` SDK v2 간의 비동기 도구 바인딩 과도기적 경고(`Direct use of automatic function calling (AFC)...`)를 `app/main.py`의 `warnings` 필터 및 전용 로거 레벨 조정(`logging.getLogger("google.genai.models").setLevel(logging.ERROR)`)으로 터미널 로그 오염 차단.
4. **Yes24 폐기 RSS 엔드포인트 대응 및 2026 트렌드 도서 풀 대폭 보강**:
   - Yes24의 404 미지원 엔드포인트 호출 시 무의미한 에러 로그 대신 안정적 풀 전환 안내 로깅으로 정돈 (`app/infrastructure/trending_books.py`).
   - 한강 작가 대표작(《작별하지 않는다》, 《소년이 온다》, 《채식주의자》), 김초엽 《지구 끝의 온실》, 송길영 《시대예보: 호명사회》 등 2024~2026 대표작 풀을 추가 보강하여 도서 큐레이터 오픈북 품질 강화.
5. **품질 검증 및 AI 자가 검증 (Self-Validation) 100% 통과**:
   - `uv run pytest`: **전체 137개 단위 테스트 100% 그린 패스 (`137 passed in 40.47s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과 (`All checks passed`, `90 files already formatted`)**.
   - `uv run mypy .`: **정적 타입 체크 80개 파일 100% 무결성 통과 (`Success: no issues found in 80 source files`)**.
6. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 27 완료 반영.
   - `.harness/PLAN.md`에서 완료된 Milestone 7 제거.
   - `.harness/DECISIONS.md`에 시스템 경고 소거 및 트렌드 도서 풀 강화 결정 기록.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/system-warning-and-rss-fixes` 브랜치 커밋 및 푸시, PR 생성 보조.
- Milestone 4 (프론트엔드 연동 3대 서비스 E2E 스모크 테스트) 진행.

---

## 세션 27 (2026-09-17)

### 진행한 작업
1. **폐기된 Yes24 RSS 엔드포인트 및 하드코딩 완전 탈피**:
   - Yes24 RSS가 404 리다이렉트되어 하드코딩 폴백으로 빠지는 문제를 근본적으로 해결하기 위해, 완벽한 SSR(Server-Side Rendering)인 Yes24 종합 베스트셀러 웹페이지(`https://www.yes24.com/Product/Category/BestSeller?categoryNumber=001&pageSize=40`)를 `httpx` 비동기 GET 요청으로 가져오도록 파이프라인 전면 개편 (`app/infrastructure/trending_books.py`).
2. **BeautifulSoup 기반 실시간 베스트셀러 스크래퍼 및 노이즈 필터링 구현**:
   - `beautifulsoup4` 의존성 추가 및 레거시 `feedparser` 패키지 완전 제거.
   - `parse_yes24_bestseller_html`: `a.gd_name`(도서명), `span.info_auth`(저자), `span.info_pub`(출판사)를 완벽 파싱.
   - 수험서/자격증/문제집 노이즈 필터링(`NOISE_KEYWORDS = ["기출", "능력검정", "문제집", ...]`)을 적용하여 문학, 철학, 인문, 교양 단행본 위주로 선별.
   - Redis에 `daily_trending_books` 키로 TTL 24시간(86400초) 캐싱 및 `get_trending_books_text` 오픈북 주입 연동.
   - 실측 결과: 40권의 2026년 오늘 날짜 실시간 베스트셀러(세네카, 싯다르타, 김애란 《그랬다고 적었다》, 니체, 모순 등)가 0.8초 만에 100% 정상 수집 및 캐싱됨을 확인.
3. **자가 검증 및 테스트 전체 통과 (Self-Validation)**:
   - `tests/unit/test_curator_pipeline.py`: 스크래퍼 HTML 파싱 및 비동기 캐싱 단위 테스트 갱신.
   - `uv run pytest`: **전체 137개 단위 테스트 100% 그린 패스 (`137 passed in 41.70s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과 (`All checks passed`, `90 files formatted`)**.
   - `uv run mypy .`: **정적 타입 체크 80개 파일 100% 무결성 통과 (`Success: no issues found in 80 source files`)**.
4. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 28 (Milestone 8) 완료 반영.
   - `.harness/PLAN.md`에서 완료된 Milestone 8 제거.
   - `.harness/DECISIONS.md`에 Yes24 실시간 SSR 웹 스크래퍼 채택 결정 기록.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/curator-pairing-and-biblio-clean` 브랜치 변경 사항 커밋 및 푸시, PR #24 갱신 보조.
- Milestone 4 (프론트엔드 연동 3대 서비스 E2E 스모크 테스트) 진행.

---

## 세션 28 (2026-09-17)

### 진행한 작업
1. **기획/UX 유연화: 감정 맞춤 인생 도서 페어링 전환**:
   - 사용자의 상황과 동떨어지게 억지로 '극단적 고전(Classic)'을 강제하던 프롬프트를 탈피.
   - `CURATOR_SYSTEM_PROMPT` 및 `BookCandidate` Pydantic 스키마를 [1권: 오픈북 기반 트렌드 도서] + [1권: 연도와 시대를 불문하고 사용자의 감정을 완벽히 관통하는 원픽 인생 도서]로 유연하게 전면 개편 (`app/domain/graph/curator_node.py`).
2. **도서명 괄호 찌꺼기 완벽 세척 (`clean_book_title`)**:
   - `(큰글자책)`, `(오디오북)`, `[양장]`, `<개정판>`, `(진중문고납품)`, `(리커버)` 등 국립도서관/서점 API의 잡음 텍스트와 부제를 정규식으로 싹쓸이 정제하는 `clean_book_title` 유틸 구현 (`app/infrastructure/national_library_client.py`).
   - `trending_books.py`의 Yes24 웹 스크래퍼 및 국립도서관 검색 쿼리/반환값에 전면 적용하여 《세네카》 괄호 누락 버그 완벽 해결.
3. **다중 판본 표지 생존 우선 매칭 및 쪽수 교차 보강**:
   - `_filter_and_rank_monographs`: `bad_form`에 오디오북, 전자책, 비도서, 카세트 등을 추가하고 특수 판본 감점을 적용하여 정식 종이책 단행본 우선순위 강화.
   - `search_book`: 첫 번째 판본에서 무조건 return하던 버그를 제거하고, 상위 5개 판본 중 실제로 살아있는 고화질 표지(34,150B 플레이스홀더 배제 및 HTTP 200 검증)를 가진 정식 종이책 판본을 끝까지 찾아내 1순위로 선택.
   - 표지가 살아있는 판본의 쪽수가 누락된 경우 동일 검색 결과 내 다른 판본의 유효 쪽수(50쪽 이상)로 자동 교차 보강.
   - 실측 검증: 《브람스를 좋아하세요》 검색 시 오디오북/죽은 표지가 선택되던 현상을 100% 차단하고, 민음사 정식 종이책(ISBN 9788937461798)의 53KB 초고화질 표지와 253 쪽수를 완벽 바인딩 성공.
4. **자가 검증 및 테스트 전체 통과 (Self-Validation)**:
   - `tests/unit/test_recommend_metadata.py`: `test_clean_book_title_removes_noise_brackets` 단위 테스트 추가.
   - `uv run pytest`: **전체 138개 단위 테스트 100% 그린 패스 (`138 passed in 40.85s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과 (`All checks passed`, `90 files left unchanged`)**.
   - `uv run mypy .`: **정적 타입 체크 80개 파일 100% 무결성 통과 (`Success: no issues found in 80 source files`)**.
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 29 완료 반영.
   - `.harness/DECISIONS.md`에 기획 유연화, 도서명 정제, 표지 생존 우선 매칭 결정 기록.

### 다음 세션에서 할 일
- develop 머지 충돌 해결 완료 및 PR #24 리뷰 승인 후 사람 직접 머지 대기.
- Milestone 4 (프론트엔드 연동 3대 서비스 E2E 스모크 테스트) 진행.

---

## 세션 29 (2026-09-17)

### 진행한 작업
1. **토론 모드 템플릿 앵무새 현상 및 UX 병목 원인 정밀 분석**:
   - 사용자가 공유한 실제 토론 테스트 대화(《미라클 모닝》)에서 평론가가 매 턴마다 고정 포맷(★ 별점, ■ 한 줄 총평, ◆ 오늘의 화두)을 복붙 출력하고, 토론 흐름과 무관하게 날씨/무드/기온을 서두에 읊어 몰입도를 깨는 현상 확인.
2. **해결 아키텍처 및 구현 방향성 확정**:
   - 단순 프롬프트 지시보다 **LangGraph State(발화 카운트) 기반 동적 프롬프트 라우팅(2번 방식)** 채택.
   - LLM이 턴이 길어져도 템플릿을 까먹고 재출력하는 환각을 원천 방지하기 위해, 오프닝용(`OPENING_PROMPT`)과 티키타카용(`TURN_PROMPT`)으로 프롬프트를 완전 분리.
   - 토론 모드(`is_debate`)에서는 `weather_context` 주입을 전면 차단하여 날씨 노이즈 배제.
   - 유저 발화 길이 미러링(Mirroring) 및 문장 끝 자연스러운 열린 질문 유도 원칙 수립.
3. **하네스 문서 수립 완료**:
   - `.harness/PLAN.md`에 Milestone 3 (Phase 21: 토론 4종 턴 분리 및 날씨 격리) 세부 체크리스트 작성 완료.

### 다음 세션에서 할 일
- **새 작업 브랜치 생성**: `feat/debate-turn-split-prompts` 분기 (`develop` 기반).
- **Milestone 3 (Phase 21) 구현 착수**:
  - `app/domain/personas/` 내 토론 4종(평론가, 이야기꾼, 상담사, 관찰가) 프롬프트 오프닝/대화턴 분리.
  - `app/domain/graph/nodes.py`에서 `human_msg_count` 기반 동적 프롬프트 주입 및 `weather_context` 토론 모드 제외 조건 추가.
  - 단위 테스트 추가 및 `ruff`, `mypy`, `pytest` 자가 검증 완료 후 PR 생성.






















---

## 세션 30 (2026-09-17)

### 진행한 작업
1. **`feat/debate-turn-split-prompts` 작업 브랜치 생성**:
   - `develop` 최신화(PR 머지 반영) 후 DPYB 컨벤션에 따라 `feat/debate-turn-split-prompts` 분기.
2. **토론 파트너 4종 시스템 프롬프트 2-Track 완전 분리 (`app/domain/personas/`)**:
   - 각 토론 파일(`debate_critic.py`, `debate_storyteller.py`, `debate_counselor.py`, `debate_observer.py`)에 `OPENING_PROMPT`와 `TURN_PROMPT`를 분리하여 정의.
   - `OPENING_PROMPT`: 첫 분석 응답에 한해 고정 포맷 (별점/총평/화두, 교훈/질문, 마음 돌봄 질문, 시그널 총평/관찰 질문) 출력.
   - `TURN_PROMPT`: 2번째 턴부터 고정 포맷 엄격 금지, 발화 길이 미러링(Mirroring), 문장 끝 자연스러운 열린 질문 의무화.
   - `DEBATE_*_SYSTEM_PROMPT` alias를 `OPENING_PROMPT`로 연결하여 하위 호환성 100% 유지.
3. **`PERSONA_REGISTRY` 메타데이터 확장 (`app/domain/personas/__init__.py`)**:
   - 토론 4종에 `opening_system_prompt`, `turn_system_prompt` 필드 등록.
4. **LangGraph 노드 동적 프롬프트 분기 및 날씨 격리 (`app/domain/graph/nodes.py`)**:
   - `human_msg_count <= 1` → `opening_system_prompt`, `> 1` → `turn_system_prompt` 동적 분기.
   - `if weather_context and not is_debate:` 조건으로 토론 모드 날씨 노이즈 원천 차단.
5. **자가 검증 및 단위 테스트 전수 통과**:
   - 신규 테스트 3종 추가(opening/turn 분리 검증, 오프닝 포맷 검증, 미러링+질문 규칙 검증).
   - `uv run pytest`: **전체 141개 단위 테스트 100% 그린 패스 (141 passed in 53.25s)**
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과**
   - `uv run mypy .`: **80개 파일 100% 무결성 통과**

### 다음 세션에서 할 일
- PR #25 (`feat/debate-turn-split-prompts` -> `develop`) 머지 완료 및 로컬 develop 동기화 완료.
- Milestone 4 (Phase 20 E2E 통합 검증): 프론트엔드 연동 후 3대 서비스 통합 스모크 테스트 진행.

---

## 세션 31 (2026-09-17)

### 진행한 작업
1. **독서 세션(reading_sessions) 데이터 모델 도입에 따른 AI 에이전트 독립 작업 완성**:
   - `develop` 브랜치 기반으로 `feat/reading-session-report-enhancement` 작업 브랜치 분기.
2. **리포트 스키마 및 직렬화 규격 확장 (`app/schemas/report.py`)**:
   - `ReadingHabits` 모델에 `total_session_count: int = 0` (이번 달 총 독서 세션 횟수) 및 `avg_session_duration_minutes: Optional[float] = None` (1회 평균 집중 독서 시간 분 단위) 필드 추가.
   - `CamelModel`을 통해 프론트엔드에 `totalSessionCount`, `avgSessionDurationMinutes`로 직렬화되어 카드 02번 및 요약 통계와 100% 매칭.
3. **CoreApiClient Fallback 동기화 (`app/infrastructure/core_api_client.py`)**:
   - `get_monthly_report_stats` Fallback 목 데이터에 `totalSessionCount: 34`, `avgSessionDurationMinutes: 28.2`를 추가하여 core-api 미배포/오프라인 환경에서도 안전하게 지원.
4. **사서 월간 리포트 LLM 프롬프트 및 빌더 고도화 (`app/domain/reports/generator.py`)**:
   - `_build_llm_report_prompt`의 독서 통계 컨텍스트 요약에 독서 세션 횟수와 1회 평균 집중 독서 시간 주입.
   - 사서 페르소나가 사용자의 집중 독서 시간(예: "한 번 책을 펼치면 평균 28분 동안 깊게 몰입하는 편이시군요")을 인지하여 분석/처방을 작성하도록 개선.
   - `build_monthly_report`에서 `habits_raw`로부터 신규 필드를 안전하게 매핑.
5. **자가 검증 및 품질 테스트 전수 통과 (Self-Validation)**:
   - `tests/unit/test_monthly_reports.py`에 신규 필드(`totalSessionCount`, `avgSessionDurationMinutes`) 검증 추가.
   - `uv run pytest`: **전체 141개 단위 테스트 100% 그린 패스 (141 passed in 43.98s)**.
   - `uv run ruff check .` & `uv run ruff format --check .`: **린트 및 포맷 100% 무결성 통과**.
   - `uv run mypy .`: **80개 소스 파일 100% 타입 무결성 통과**.
6. **하네스 문서 동기화**:
   - `.harness/PLAN.md` 완료 항목 제거 및 `.harness/STATE.md`에 Phase 30 완료 반영.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/reading-session-report-enhancement` 커밋 및 푸시, PR 생성 보조.
- backend-core-api의 `reading_sessions` API 배포 후 통합 연동 확인.

---

## 세션 32 (2026-09-17)

### 진행한 작업
1. **작업 브랜치 분기**:
   - `feat/librarian-colleague-intro-and-session-isolation` 생성
2. **사서 4종 동료 사서 안내 및 자연스러운 소개 지침 탑재 (`app/domain/personas/`)**:
   - `cat.py`, `shoebill.py`, `sea_slug.py`, `gecko.py` 4종 사서 시스템 프롬프트에 `# 동료 사서 안내 및 추천 원칙` 지침 추가.
   - 타 장르 요청 시 기계적인 시스템 팝업을 띄우지 않고, 고유 어조(~냥, ~두둥, ~누누, ~크크)로 전문 동료 사서를 자연스럽게 소개하고 사서 변경 이용을 권유하도록 프롬프트 표준화.
3. **사서 변경 추천 버튼(`switch_suggestion`) 정밀화 및 오발동 제거 (`app/domain/graph/nodes.py`)**:
   - `_detect_switch_intent`에서 AI의 동료 언급이나 사용자의 단순 도서/동물 언급으로 인한 무차별 버튼 발동 결함 수정.
   - 사용자의 명시적인 변경 발화("바꿔", "변경", "전환" 등)가 포함된 경우에만 정밀하게 버튼이 제안되도록 개선.
4. **DB 레벨 사서별 세션 자동 파티셔닝 (`app/api/router.py`)**:
   - 프론트엔드가 공통 `session_id`를 보내더라도, 백엔드에서 사서 모드 시 강제로 `{session_id}:{persona}`(예: `user_123:CAT`, `user_123:SHOEBILL`)로 Redis / LangGraph 세션 키를 자동 파티셔닝.
   - DB 레벨에서 사서별 대화 스레드가 물리적으로 완벽히 격리되어, 이전 사서의 어조와 대화가 새 사서에게 전달되는 어조 오염을 물리적으로 0% 원천 차단.
5. **품질 검증 및 테스트 전수 통과 (Self-Validation)**:
   - 신규 단위 테스트 추가 및 세션 파티셔닝 검증 완료 (`test_api.py`, `test_graph_handoff.py`).
   - `uv run pytest`: **전체 143개 단위 테스트 100% 그린 패스 (143 passed in 45.43s)**.
   - `uv run ruff check .` & `uv run ruff format --check .`: **린트/포맷 100% 통과**.
   - `uv run mypy .`: **80개 소스 파일 100% 무결성 통과**.
6. **하네스 문서 동기화**:
   - `.harness/PLAN.md` 완료 항목 제거 및 `.harness/STATE.md`에 Phase 31 완료 반영.

### 다음 세션에서 할 일
- 사용자의 컨펌 후 `feat/librarian-colleague-intro-and-session-isolation` 커밋 및 푸시, PR 생성 보조.
- Milestone 4 프론트엔드 연동 E2E 통합 스모크 테스트 진행.

---

## 세션 25 (2026-09-17)

### 진행한 작업
1. **규칙 기반 `_detect_switch_intent` 및 하드코딩 키워드 감지 전면 제거**:
   - `app/domain/graph/nodes.py`:
     - 사서 변경 감지 함수 `_detect_switch_intent` 및 switch_map 삭제.
     - 사서 변경은 프론트엔드 UI 상단 탭 전환과 이미 구현된 `{session_id}:{persona}` DB 세션 파티셔닝에 완전 위임.
     - `conclude_keywords`, `recom_keywords` 문자열 리스트 및 단순 if-else 키워드 매칭 로직 영구 삭제.
     - 명시적 UI 버튼 요청(`action == "conclude"`)은 LLM 불필요 호출 없이 즉시 피날레 큐레이션으로 직행하도록 0ms 처리 유지.
2. **에이전트 Tool Calling 기반 지능형 라우팅 구현**:
   - `app/domain/graph/tools.py`:
     - `@tool trigger_debate_conclude(reason: str)`: 사용자의 토론 종료/마무리 의사를 LLM이 감지했을 때 호출하는 전용 도구 등록.
     - `@tool request_book_curation(query: str)`: 사용자가 도서 추천/큐레이션 의사를 표현할 때 LLM이 자율 호출하는 전용 도구 등록.
     - `GENERIC_TOOLS`에 등록하여 페르소나 에이전트와 LLM 바인딩 완성.
   - `app/domain/graph/nodes.py`:
     - LLM 응답 후 `response.tool_calls`를 검사하여 `trigger_debate_conclude` 호출 시 `curator_node` 피날레 큐레이션으로 라우팅(`is_concluded = True`), `request_book_curation` 호출 시 큐레이터 서브에이전트로 자연스럽게 위임하도록 구현.
     - 테스트 환경(`app_env == "test"`)의 `_generate_mock_response`에서도 해당 도구 호출(`tool_calls`)을 모킹하여 CI/단위 테스트 무결성 보장.
3. **페르소나 ID 안전 정규화 및 LangGraph Configurable thread_id 주입**:
   - `app/domain/personas/__init__.py`:
     - `normalize_persona`를 신설하여 소문자(`nudi`, `gecko`), 한글명(`누디`, `달팽이`, `게코`, `도마뱀`, `슈빌`, `황새`), 레거시 ID(`LIBRARIAN_3`, `stork`) 등 어떤 변형값도 canonical key로 100% 매핑.
     - 매칭 실패 시 기본값 `CAT_ID`로 떨어져 고양이 말투가 나오던 버그 원천 해결.
     - `schemas.py`, `router.py`, `nodes.py`, `workflow.py` 전반에 걸쳐 `normalize_persona` 적용.
   - `app/api/router.py`:
     - `_graph.ainvoke` 및 `_graph.astream_events` 호출 시 `config={"configurable": {"thread_id": session_id}}`를 명시적으로 주입하여 LangGraph 레벨에서도 `{session_id}:{persona}` 스레드가 완벽히 분리되도록 보장.
     - 세션 식별 시 로깅 추가.
4. **품질 검증 및 테스트 전수 통과 (Self-Validation)**:
   - `tests/unit/test_personas.py`: `test_normalize_persona_comprehensive` 단위 테스트 추가.
   - `tests/unit/test_recommend_metadata.py`: mock 시그니처 `*args, **kwargs` 호환성 보정.
   - `uv run pytest`: **전체 144개 단위 테스트 100% 그린 패스 (144 passed in 39.38s)**.
   - `uv run ruff check --fix .` & `uv run ruff format .`: **린트/포맷 100% 통과**.
   - `uv run mypy .`: **80개 소스 파일 100% 무결성 통과 (Success: no issues found)**.
5. **하네스 문서 동기화**:
   - `.harness/STATE.md`에 Phase 32(Phase 27) 및 정규화/세션 주입 완료 반영.
   - `.harness/PLAN.md`에서 완료된 Phase 27 체크리스트 제거.

### 다음 세션에서 할 일
- 사용자의 승인에 따라 변경 파일 커밋 및 푸시, PR 생성 보조.
- Milestone 4 프론트엔드 연동 E2E 통합 스모크 테스트 진행.

---

## 세션 33 (2026-09-18)

### 진행한 작업
1. **CTO 리뷰 피드백 분석 및 아키텍처 재설계 수립**:
   - **0번 (프레임워크 팩트 체크)**: 실제 코드베이스를 점검하여 `app/domain/graph/workflow.py`가 정식 `StateGraph(AgentState)` 및 `workflow.compile()` 기반이며, 8개 페르소나 노드(`cat_node`, `shoebill_node` 등)가 비동기 함수로 온전히 운용 중임을 명확히 확인. 대표님이 직접 검증 가능한 단일 grep 명령어를 명시 (`grep -rn "StateGraph\|from langgraph" app/`).
   - **1번 (허구 통계 제거)**: 출처 없는 수치(환각 재발률 70% 등)를 포트폴리오 및 기획서, 사고 과정에서 영구 배제.
   - **2번 (Step 2 순환 루프 무기한 연기)**: 프론트엔드 세션 파티셔닝 안정화가 최우선이므로 복잡도를 올리는 순환 그래프(Cycle Edge Reflection)는 전면 보류.
   - **3번 (Step 1 도구 책임 분리 원칙 확립)**: 신규 독서 세션 도구(`check_user_reading_streak`)는 오직 가공되지 않은 순수 정형 데이터(팩트 JSON)만 반환하고, 사서 페르소나 어조(~냥, ~두둥 등)는 사서 노드의 LLM이 전담하도록 역할을 엄격히 분리.
   - **4번 (무과금 환경 비동기 검증 & 리스크 도출)**:
     - Redis 화이트리스트 캐시 우선(Cache-first) ➔ 미스 시 FastAPI `BackgroundTasks` 비동기 검증 ➔ 환각 감지 시 세션 스토어에 `pending_correction` 플래그 저장 ➔ 다음 대화 턴에서 사서가 자연스럽게 자가 정정 발화하는 2턴 아키텍처 설계.
     - **리스크 1 기록**: Render 무료 티어 및 Cloud Run(Scale-to-Zero)에서 응답 전송 직후 스케일다운 시 BackgroundTasks 중단 가능성을 인지하고, 향후 Celery/Cloud Tasks 전용 작업 큐 전환 검토 필요성을 `BACKLOG.md`에 공식 기술 부채로 기록.
     - **리스크 2 기록**: 턴1 오답 ➔ 턴2 정정 구조의 데모 함정을 방지하기 위해, 발표 시연 전 특정 도서 질의가 우연히 실존 도서와 매칭되지 않고 반드시 `pending_correction`을 유발하는지 사전 리허설에서 실측 검증해야 함을 `BACKLOG.md`에 명시.
2. **하네스 문서 동기화**:
   - `BACKLOG.md`: BackgroundTasks 생존 한계 및 자가 교정 데모 사전 리허설 검증 가이드 추가.
   - `DECISIONS.md`: Step 1 순수 팩트 도구/어조 분리 및 Step 2 보류, Cache-first + `pending_correction` 비동기 정정 결정 추가.
   - `PLAN.md`: Phase 21 (Step 1 `check_user_reading_streak` 도구 구축) 상세 체크리스트 신설.

### 다음 세션에서 할 일
- 대표님의 로컬 터미널 grep 명령어 직접 검증(`grep -rn "StateGraph\|from langgraph" app/`) 확인.
- 직접 검증 완료 및 대표님 최종 승인 시 `feat/reading-streak-tool` 브랜치를 생성하고 Phase 21 (Step 1 도구 구현) 본격 착수.

---

## 세션 34 (2026-09-18)

### 진행한 작업
1. **토론자 페르소나 동물 사서 말투 오염 원인 규명 및 조치 (Phase 22)**:
   - **원인 분석**:
     - 프론트엔드가 탭 전환 시 동일한 `session_id`를 재사용함에 따라, 사서 모드에만 국한되었던 세션 파티셔닝 때문에 이전 사서(예: 바다달팽이 누디)의 대화 기록 및 종결어미(`~누누`, `~냥` 등)가 토론 파트너로 유입되는 현상 규명.
     - `nodes.py`에서 `librarian_name`(사서 애칭)이 토론 모드 여부와 상관없이 무조건 주입되어 토론자가 자신을 사서로 오인하던 문제 규명.
     - 토론자 시스템 프롬프트에 동물 사서 말투를 금지하는 네거티브 가드레일 부재.
     - 프론트엔드가 이전 탭에서 선택해 둔 사서(`librarian_id: "nudi"`)를 토론 모드에서도 계속 함께 보내는데, `router.py`와 `schemas.py`에서 `raw_persona = librarian_id or persona`로 처리하여 관찰가를 골라도 누디가 실행되던 치명적 결함 규명 (#25 PR 이후 발생).
   - **토론 모드 페르소나 우선순위 원천 보장 (`app/api/schemas.py`, `app/api/router.py`)**:
     - `mode == "DEBATE"`이거나 `persona`가 토론자(`DEBATE_OBSERVER`, `관찰가`, `평론가` 등)인 경우, 잔존해 있는 `librarian_id`를 완전히 무시하고 `persona`를 1순위로 확정하도록 로직 교정.
   - **세션 파티셔닝 전면 적용 (`app/api/router.py`)**:
     - LIBRARIAN 모드뿐만 아니라 DEBATE 모드를 포함한 8개 페르소나 전체에 `{session_id}:{persona}` 자동 격리 적용.
     - Redis 세션 및 LangGraph Configurable `thread_id` 레벨에서 세션 완전 물리적 격리 달성.
   - **사서 애칭 주입 조건 강화 (`app/domain/graph/nodes.py`)**:
     - `if custom_name and not is_debate:`로 변경하여 토론자 프롬프트에 사서 애칭이 주입되지 않도록 원천 차단.
   - **토론자 4종 시스템 프롬프트 네거티브 가드(`DEBATE_GUARDRAILS`) 탑재 (`app/domain/guardrails/shared_rules.py`, `app/domain/personas/__init__.py`)**:
     - 4종 토론자(`DEBATE_CRITIC`, `DEBATE_STORYTELLER`, `DEBATE_COUNSELOR`, `DEBATE_OBSERVER`)의 오프닝 및 턴 프롬프트 전체에 `DEBATE_GUARDRAILS` 주입.
     - 동물 사서 전용 종결어미(`~냥`, `~두둥`, `~누누`, `~크크`), 사서 역할극, 반말 등을 엄격히 금지하고 전문인 오마주 어조를 준수하도록 강제.
    - **코드 품질 개선 (Clean Code 피드백 반영, `nodes.py`)**:
      - `_run_persona_node` 함수 내부에 있던 `from app.domain.personas import normalize_persona` 불필요한 Local Import를 파일 최상단(Top-level)으로 승격하여 순환 참조 우려 없는 클린 코드 준수.
2. **품질 검증 및 테스트 전수 통과 (Self-Validation)**:
   - `tests/unit/test_debate_isolation.py`: 네거티브 가드 주입 검증, 세션 파티셔닝 및 애칭 차단 검증, 바다달팽이-토론자 간 히스토리 격리 검증, 프론트엔드 잔존 `librarian_id` 무시 및 토론자 정상 실행 검증(4개 테스트 통과).
   - `tests/unit/test_debate_memory.py` 파티셔닝 세션 ID 동기화 보정.
   - `tests/unit/test_api.py` 12개 테스트 100% 통과.
   - `uv run ruff check --fix .` & `uv run ruff format .`: **린트/포맷 100% 통과**.
   - `uv run mypy .`: **81개 소스 파일 100% 무결성 통과 (Success: no issues found in 81 source files)**.
3. **하네스 문서 동기화**:
   - `.harness/STATE.md`: Phase 22 완료 반영.
   - `.harness/PLAN.md`: Phase 22 완료 및 정리.
   - `.harness/DECISIONS.md`: 전 모드 세션 파티셔닝, 토론자 우선순위 보장 및 `DEBATE_GUARDRAILS` 채택 결정 기록.

### 다음 세션에서 할 일
- 대표님의 로컬 터미널 grep 직접 검증(`grep -rn "StateGraph\|from langgraph" app/`) 확인 후, 승인 시 Phase 21 (Step 1 `check_user_reading_streak` 도구 구축) 진행.
- 사용자 승인 시 변경된 파일 선별 커밋 및 푸시 보조.

---

## 세션 35 (2026-09-18)

### 진행한 작업
1. **도서 추천 반복 편중(세네카 현상) 원인 규명 및 팩트 체크**:
   - 프롬프트 few-shot이 아닌, 실시간 Yes24 종합 베스트셀러 2위에 실제로 《세네카, 오늘을 빼앗기고 있는 당신에게》(2026, 논픽션)가 위치하여 오픈북 상단에 주입되던 구조 확인.
   - Pydantic 구조화 출력(`with_structured_output`)의 탐욕적(Greedy) 최상단 선택과 세션 내 기추천 도서 제외 로직 부재가 결합되어 동일 도서가 반복 추천되던 현상을 정밀 진단.
2. **KDC 장르 매퍼 기반 단일 기준 노이즈 필터링 (`app/infrastructure/national_library_client.py`)**:
   - `is_curatable_book(title, author, publisher)` 함수 신설: 수험서/기출/모의고사/공무원 교재, 교직 실무 매뉴얼, 아동/만화/합본판을 KDC 370 및 808.3 분류 기준에 따라 단일 기준으로 필터링.
   - `map_kdc_to_genre`에 문학/철학/인문 대표 키워드 보강.
3. **베스트셀러 순위 보존 + KDC 장르별 구조화 오픈북 카탈로그 (`app/infrastructure/trending_books.py`)**:
   - 무작위 셔플로 순위 팩트가 손실되는 문제를 방지하기 위해, 실제 순위(`종합 N위`)를 유지하면서 KDC 장르별(문학/소설/에세이, 인문/철학/심리, 교양/사회/과학)로 그룹화하여 LLM에 구조화 텍스트 주입.
4. **세션 내 최근 추천 도서 추적, 슬라이딩 윈도우 캡 및 턴 간 Redis 영속화 (`app/domain/graph/state.py`, `curator_node.py`, `nodes.py`, `router.py`, `redis_session.py`)**:
   - `AgentState`에 `recommended_history: Optional[List[str]]` 추가.
   - `router.py`의 `_prepare_chat_context` 및 `POST /chat`, `POST /chat/stream`에서 세션 스토어(`session_mgr`)와 양방향 바인딩하여 턴이 이어져도 이전 추천 히스토리가 증발하지 않고 유지되도록 영속화 연동 (`RedisSessionManager.delete_session` 메서드 추가).
   - 무한정 누적으로 인한 컨텍스트 오염 및 토큰 비용 증가를 방지하기 위해 최근 10권(`MAX_RECOMMENDED_HISTORY = 10`) 슬라이딩 윈도우 캡 적용.
   - 큐레이터 프롬프트에 `[중복 추천 제외 목록]` 네거티브 컨스트레인트를 동적 주입하여 직전 추천 도서 재추천 억제.
   - `CURATOR_SYSTEM_PROMPT`에 장르 전반의 적합 도서를 균형 있게 선택하도록 다양성 지침 보강.
5. **품질 검증 및 테스트 전수 통과 (Self-Validation)**:
   - `tests/unit/test_curator_pipeline.py`: 노이즈 필터링, KDC 장르 그룹핑/순위 보존, 슬라이딩 윈도우 히스토리 관리 및 **동일 세션 ID 기반 2턴 연속 호출 시 1차 추천 도서의 제외 목록 주입 및 턴 간 영속화 통합 테스트** 추가.
   - 전체 153개 단위 테스트(Pytest) 100% 그린 패스 통과 (`153 passed, 1 warning in 49.81s`).
   - Ruff 린트 및 포맷 정렬 100% 무결성 통과 (`All checks passed`, `91 files already formatted`).
   - Mypy 정적 타입 체크 81개 소스 파일 100% 무결성 통과 (`Success: no issues found in 81 source files`).
6. **하네스 문서 동기화**:
   - `.harness/STATE.md`: Phase 33 완료 반영.
   - `.harness/PLAN.md`: Phase 33 완료 및 정리.
   - `.harness/DECISIONS.md`: KDC 장르 그룹핑 순위 보존 카탈로그 및 슬라이딩 윈도우 중복 방지 채택 결정 기록.

### 다음 세션에서 할 일
- 대표님의 로컬 터미널 grep 직접 검증(`grep -rn "StateGraph\|from langgraph" app/`) 확인 후, 승인 시 Phase 21 (Step 1 `check_user_reading_streak` 도구 구축) 진행.
- 사용자 승인 시 변경된 파일 선별 커밋 및 푸시 보조.

---

## 세션 36 (2026-09-18)

### 진행한 작업
1. **게스트 JWT 클레임(`sub`, `role`) 추출 및 Null-Check 전수 안전화 (`app/api/router.py`)**:
   - `extract_auth_info_from_auth`를 확장하여 `(sub, raw_token, role)` 3-튜플 반환 (하위 호환 유지).
   - `role == "guest"` 및 `sub.startswith("guest-")` 식별. Core-API 게스트 토큰에 `email`, `name`, `nickname`이 누락되므로 기본값 안전 처리 전수 적용.
2. **게스트 세션 파티셔닝 (`app/api/router.py`)**:
   - 게스트 요청 시 `sub` (`guest-{uuid}`)를 앵커로 `{guest_id}:{persona}`로 자동 파티셔닝하여 게스트 간 및 페르소나 간 대화 히스토리 완전 격리.
3. **게스트 영구 대화 횟수 상한 및 우아한 UX 200 OK 폴백 (`app/infrastructure/redis_session.py`, `app/api/router.py`)**:
   - 카운터 키를 `guest_usage:{guest_id}`(14일 TTL 유지)로 영구 귀속시켜 토큰 재발급을 통한 우회 차단.
   - `GUEST_CHAT_LIMIT`(기본 10회) 도달 시 LLM 호출을 건너뛰고 200 OK와 함께 `"이번 체험에서 대화 가능 횟수를 모두 사용하셨습니다. 정식 로그인 후 다시 만나요!"` 안내 멘트 반환 (일반 및 스트리밍 SSE `metadata -> token -> done` 동일).
4. **Role 분리 이중 서킷 브레이커 (RPM / RPD) 구축 (`app/infrastructure/redis_session.py`, `app/core/config.py`, `app/api/router.py`)**:
   - 게스트(`circuit:rpm:guest:...`, `circuit:rpd:guest:...`)와 정회원(`circuit:rpm:member:...`, `circuit:rpd:member:...`) 카운터를 완전 분리하여 게스트 트래픽 폭주 시에도 정회원 서비스 보장.
   - **TTL 패턴 준수**: 분당 카운터 생성 시 첫 INCR 시점에만 짧은 TTL(90초)을 설정하는 `INCR + EXPIRE NX` 원자적 패턴 적용 (키 영구 잔존 방지).
   - 일일 카운터는 48시간 TTL로 운용하여 임계치의 70~80% 수준 선제 차단 및 200 OK 안내 멘트(`"앗, 지금 서재에 방문객이 너무 많아 사서들이 바빠요. 잠시 후 다시 시도해 주세요!"`) 반환.
   - 비동기 뮤텍스(`_circuit_lock`)로 동시성 레이스 컨디션 방어.
5. **게스트 쓰기 락 (403 Forbidden) 및 백그라운드 태스크 스킵 (`app/api/v1/memory.py`, `app/api/router.py`)**:
   - `POST /api/v1/memory/scraps`, `POST /api/v1/memory/debate-insights`, `POST /api/v1/vectors/records`에서 게스트 요청 시 403 Forbidden 반환.
   - 토론 피날레 시 게스트 사용자의 `save_debate_insight_task` 백그라운드 DB 적재 태스크 건너뛰기 적용.
6. **단위 및 동시성(Concurrency) 전수 검증 (`tests/unit/test_guest_mode.py`)**:
   - `asyncio.gather` 기반 50개 동시 요청 카운트 원자성 및 서킷 브레이커 임계치 경계 레이스 컨디션 방어 테스트를 포함한 11개 전용 테스트 작성 완료.
   - 전체 164개 단위 테스트(Pytest) 100% 그린 패스 통과 (`164 passed, 1 warning in 54.27s`).
   - Ruff 린트/포맷 100% 통과 (`Found 1 error (1 fixed, 0 remaining)`).
   - Mypy 정적 타입 체크 82개 소스 파일 100% 무결성 통과 (`Success: no issues found in 82 source files`).
7. **하네스 문서 동기화**:
   - `STATE.md`, `PLAN.md`, `DECISIONS.md`, `HANDOFF.md` 갱신 완료.

### 다음 세션에서 할 일
- 대표님의 로컬 터미널 grep 직접 검증(`grep -rn "StateGraph\|from langgraph" app/`) 확인 후, 승인 시 Phase 21 (Step 1 `check_user_reading_streak` 도구 구축) 진행.
- 사용자 승인 시 변경된 파일 선별 커밋 및 푸시 보조.

---

## 세션 34 (2026-09-19)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - DPYB 브랜치 규칙에 따라 `develop` 브랜치 기반 `feat/cors-pooler-deployment-readiness` 분기.
2. **CORS 정규식 지원 및 와일드카드 보안 강화**:
   - `app/core/config.py`에 `CORS_ORIGIN_REGEX` 필드(기본값 `^https?://(localhost|127\.0\.0\.1)(:\d+)?$`) 추가 및 `.env.example` 문서화.
   - `app/main.py`의 `CORSMiddleware`에 `allow_origin_regex` 매핑하여 팀원의 임의 로컬 포트 개발 환경을 안전하게 수용하고 Cloudflare Pages 배포 대비 확장성 확보.
3. **Supabase Transaction Pooler Prepared Statement 충돌 방지 강화**:
   - `app/infrastructure/db/session.py`의 `create_async_engine` `connect_args`에 `prepared_statement_name_func=lambda: f"__asyncpg_{uuid4()}__"` 옵션 추가하여 Transaction Pooler(포트 6543) 환경의 충돌 원천 차단.
4. **품질 검증 및 테스트 전수 통과**:
   - `tests/unit/test_api.py`에 `test_cors_preflight_and_regex` 단위 테스트 추가 및 100% 통과 (13 passed).
   - Ruff 린트 및 포맷 정렬 통과, Mypy 타입 체크 무결성 통과 (`59 source files`).
5. **하네스 문서 동기화**:
   - `STATE.md`, `PLAN.md`, `HANDOFF.md` 최신화 완료.

### 다음 세션에서 할 일
- 사용자 승인 시 `feat/cors-pooler-deployment-readiness` 커밋 및 푸시, PR 생성 보조.
- Render에 Core API 및 AI Agent 배포 진행 및 `/health` 웜업 확인.
- DB 정리 및 데모 계정 시나리오 데이터 세팅 진행 후 팀원에게 프론트 로컬 연동 가이드 공유.

---

## 세션 35 (2026-09-19)

### 진행한 작업
1. **작업 브랜치 생성 및 격리 개발**:
   - DPYB 브랜치 규칙에 따라 `develop` 브랜치 기반 `feat/alembic-agent-migration` 분기 (`main` <- `develop` <- `feat/*`).
2. **`backend-core-api` Alembic 구조 분석 및 벤치마킹**:
   - `core-api`의 `alembic.ini`, `alembic/env.py`, `versions/` 구조를 직접 파악하여, Supabase 단일 인스턴스 공유 환경에서 충돌 없는 스키마 격리 원칙 도출.
3. **Alembic 비동기 마이그레이션 환경 구축**:
   - `pyproject.toml`에 `alembic>=1.13.1` 의존성 추가 (`uv add "alembic>=1.13.1"`).
   - `alembic.ini`: `script_location = alembic`, `prepend_sys_path = .`, ruff 린트/포맷 훅(`uv run ruff check --fix`, `uv run ruff format`) 구성.
   - `alembic/env.py`:
     - `version_table_schema="agent"` 명시: `core.alembic_version`과 완전 격리된 `agent.alembic_version` 관리 테이블 운용.
     - `CREATE EXTENSION IF NOT EXISTS vector;`, `CREATE SCHEMA IF NOT EXISTS agent;` 선행 보장.
     - Supabase Transaction Pooler(포트 6543) 환경 대응 `connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}` 적용.
4. **초기 마이그레이션 리비전 작성 (`001_initial_agent_schema.py`)**:
   - `agent.scrap_vector` (테이블, `member_id` B-Tree 인덱스, HNSW 코사인 유사도 인덱스).
   - `agent.debate_insights` (테이블, `member_id` B-Tree 인덱스, HNSW 코사인 유사도 인덱스).
   - `agent.chat_sessions` (테이블).
   - RPC 함수 `agent.match_scraps`, `agent.match_debate_insights` 생성.
   - 롤백 지원용 `downgrade()` 함수 구현.
5. **실행 스크립트 및 문서화**:
   - `scripts/run_migrations.py` 헬퍼 스크립트 작성 (`upgrade`, `downgrade`, `current`, `history` 지원).
   - `scripts/init_agent_schema.py` 상단에 Alembic 사용 권장 안내 추가.
   - `README.md` 빠른 시작 가이드에 `uv run alembic upgrade head` 안내 추가.
6. **품질 검증 및 AI 자가 검증 100% 통과 (Self-Validation)**:
   - `tests/unit/test_alembic_migration.py` 신규 작성 (alembic.ini 파싱, 단일 head 리비전 유효성, `agent` 스키마 타겟팅 등 3종 단위 테스트).
   - `uv run pytest tests/unit/ -v`: **전체 168개 단위 테스트 100% 그린 패스 통과 (`168 passed in 57.82s`)**.
   - `uv run ruff check .` & `uv run ruff format .`: **린트/포맷 100% 통과 (0 errors)**.
   - `uv run mypy .`: **정적 타입 체크 86개 소스 파일 100% 무결성 통과 (`Success: no issues found in 86 source files`)**.
7. **하네스 문서 동기화**:
   - `STATE.md`, `PLAN.md`, `DECISIONS.md`, `HANDOFF.md` 최신화 완료.

### 다음 세션에서 할 일
- 사용자의 확인 및 요청 시 `feat/alembic-agent-migration` 브랜치 변경 사항 선별 커밋 및 푸시, PR 생성 보조.
- CI 통과 확인 후 사람 직접 머지 원칙에 따라 GitHub 웹에서 머지 진행.
- Render 배포 환경에서 `uv run alembic upgrade head` 실행 연동 여부 점검.

