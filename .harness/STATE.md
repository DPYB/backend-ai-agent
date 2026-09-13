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


