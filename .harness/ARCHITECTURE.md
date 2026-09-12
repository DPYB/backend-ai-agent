# ARCHITECTURE.md — 시스템 구조 및 기술 명세

> 현재 시점의 서비스 아키텍처, 디렉토리 구조, 기술 스택, 인터페이스 규격을 기술합니다.

---

## 1. 시스템 개요 및 도메인 역할

`backend-ai-agent`는 DPYB(Don't Paw-get Your Book) 시스템에서 **지능형 AI 페르소나 대화, 개인화 독서 기억 RAG(LangGraph, pgvector)**와 함께 **ISBN 바코드 스캔, 문장 스크랩 Clova OCR 등 독서 수집 기능 구현**을 전담하는 무상태(Stateless) 마이크로서비스입니다.

> **💡 책임 분리 원칙**: 무거운 이미지 처리(바코드 디코딩, OCR) 및 AI 추론은 본 레포에서 전담하되, 회원/도서/스크랩 등 모든 정형 데이터의 **순수 DB 영속화(RDBMS CRUD 및 영구 저장)는 `backend-core-api`에 전적으로 위임**합니다.

```text
[ Frontend (Web / PWA) ]
         │
         ├── POST /api/v1/chat ───────────▶ [ backend-ai-agent ]
         ├── POST /api/v1/vision/scan-barcode ───┤  ├── LangGraph (8-Node Personas)
         ├── POST /api/v1/vision/ocr ────────────┤  ├── Supabase pgvector (scrap_vector)
         ├── GET  /health (중앙 킵얼라이브) ────────┤  ├── Redis (Session & TTL Cache)
                                                 │  ├── Google Gemini (LLM & Embedding)
                                                 │  └── Naver Clova OCR API V2
                                                 ▼
                                     [ backend-core-api ] (순수 DB 영속화 위임)
```

---

## 2. 기술 스택 (Tech Stack)

| 레이어 | 기술 | 설명 |
| :--- | :--- | :--- |
| **Runtime & Language** | Python 3.12, `uv` | 경량 패키지 관리 및 초고속 실행 환경 |
| **Web Framework** | FastAPI, Uvicorn | 비동기 고성능 REST API 서버, 자동 OpenAPI Docs |
| **Agent Orchestration** | LangGraph, LangChain Core | 8개 페르소나 상태 관리, 도구 바인딩 및 Handoff |
| **LLM & Embedding** | Google Gemini 1.5 Flash, `text-embedding-004` (768차원) | 대화 생성 및 텍스트 임베딩 벡터화 |
| **Vector Database** | Supabase pgvector (`scrap_vector`) | 회원별(`member_id`) 스크랩 문장/메모 코사인 유사도 검색 |
| **Cache & Session** | Redis / Upstash Redis | 다회 대화 컨텍스트 유지 및 추천 결과 TTL 캐싱 |
| **Computer Vision** | `pyzbar`, `Pillow`, `libzbar0` | 13자리 도서 바코드(EAN13/ISBN-13) 스캔 |
| **External OCR** | Naver Cloud Clova OCR General API V2 | 책 문장 이미지에서 행 단위 텍스트 추출 |
| **Web Search** | Tavily Python SDK | 최신 도서 및 트렌드 실시간 검색 |

---

## 3. 디렉토리 구조 (Directory Layout)

```text
backend-ai-agent/
├── .github/
│   └── workflows/
│       ├── ci.yml              # 중앙 reusable-python-ci.yml (Python 3.12)
│       └── lint-pr.yml         # 중앙 reusable-pr-lint.yml
├── AGENTS.md                  # [필수] 에이전트 워크플로우 및 개발 규칙집
├── CLAUDE.md                   # Claude Code용 어댑터
├── .kiro/                      # Kiro용 어댑터
├── .harness/                   # 하네스 상태 관리 문서군
│   ├── HANDOFF.md
│   ├── STATE.md
│   ├── ARCHITECTURE.md
│   ├── PLAN.md
│   ├── DECISIONS.md
│   └── BACKLOG.md
├── app/
│   ├── main.py                 # FastAPI 인스턴스, 수명주기 및 라우터 등록
│   ├── core/
│   │   └── config.py           # Pydantic Settings 환경변수 정의
│   ├── domain/
│   │   ├── personas/           # 8개 페르소나 정의 및 중앙 레지스트리
│   │   ├── memory/             # RAG (scrap_vector) 및 내 서재 도구
│   │   ├── recommend/          # Tavily + Redis 도서 추천 도구
│   │   └── graph/              # LangGraph 노드, 상태, 워크플로우
│   ├── vision/                 # 바코드 스캐너 및 Clova OCR 클라이언트
│   ├── infrastructure/         # Supabase, Redis, core-api 클라이언트
│   └── api/                    # API 스키마 및 REST 엔드포인트 라우터
├── scripts/
│   └── seed_supabase_scrap_vector.py # Supabase pgvector DDL 및 시딩
├── tests/
│   └── unit/                   # 단위 테스트 (Pytest)
├── Dockerfile                  # $PORT 동적 주입 및 libzbar0 포함
├── docker-compose.yml          # 로컬 개발용 핫리로드 구성
└── pyproject.toml              # 프로젝트 및 의존성 정의
```

---

## 4. Git 및 CI/CD 워크플로우 규격

- **브랜치 전략**: `main` <- `develop` <- `feat/*` 단일화 (`feature/*`, `fix/*` 등 사용 금지)
- **커밋/PR 제목**: `type[scope]: description` 대괄호 표준 형식 준수
- **CI/CD 파이프라인**:
  - `ci.yml`: `DPYB/.github` 중앙 `reusable-python-ci.yml` 호출 (Python 3.12, ruff 린트 및 pytest 테스트 자동 실행)
  - `lint-pr.yml`: `DPYB/.github` 중앙 `reusable-pr-lint.yml` 호출 (PR 제목 규격 검증)
- **머지 권한**: CI 통과 후 **develop/main 브랜치 PR 머지는 에이전트가 실행하지 않고 사람이 직접 클릭**하여 머지 (AI 임의 머지 엄격 금지)

---

## 5. 핵심 엔드포인트 규격

| Method | Path | 설명 |
| :--- | :--- | :--- |
| `GET` | `/health` | **중앙 .github 킵얼라이브(10분 주기)** 전용 루트 헬스체크 (Render 슬립 방지 및 200 OK) |
| `GET` | `/api/v1/health` | 서비스 헬스체크 및 Supabase/Redis 연결 확인 (Supabase 7일 슬립 방지 ping 포함) |
| `GET` | `/api/v1/personas` | 사서(4종) 및 토론(4종) 페르소나 목록 조회 (모드 필터링 지원) |
| `POST` | `/api/v1/chat` | AI 사서/토론자와의 대화 (커스텀 사서 이름, RAG 도구 자동 호출) |
| `POST` | `/api/v1/vision/scan-barcode` | 책 바코드 이미지 업로드 -> 13자리 ISBN 반환 |
| `POST` | `/api/v1/vision/ocr` | 책 문장 이미지 업로드 -> Clova OCR 텍스트 반환 |

---

## 6. 환경변수 규격 (`.env`)

```env
APP_ENV=development
PORT=8000

# Google Gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/text-embedding-004

# Supabase (pgvector)
SUPABASE_URL=
SUPABASE_KEY=

# Redis
REDIS_URL=redis://localhost:6379/0

# Tavily & Core API
TAVILY_API_KEY=
CORE_API_URL=http://localhost:8080

# Naver Cloud Clova OCR
NAVER_CLOVA_API_URL=
NAVER_CLOVA_SECRET_KEY=
```
