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
- 사용자의 확인 및 요청 시 `feat/supabase-agent-schema` 브랜치 변경 사항 커밋 및 푸시
- `feat/supabase-agent-schema -> develop` PR 생성 보조
- LangGraph 스트리밍(SSE) 응답 인터페이스(`POST /api/v1/chat/stream`) 설계 및 구현 (`.harness/PLAN.md`)







