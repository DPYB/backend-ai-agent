# DPYB `backend-ai-agent` 🐾📚

> **Don't Paw-get Your Book (DPYB)** — AI 사서 및 독서 토론 RAG 마이크로서비스

---

## 🏛️ DPYB 4-Tier 아키텍처 내 역할

```text
[ frontend-reader-web ] (사용자 웹 / PWA 바코드 스캔)
          │
          ├──▶ [ backend-auth-api ] (인증, JWT)
          │
          ├──▶ [ backend-core-api ] (도서/회원/서재/스크랩 CRUD RDBMS, 국립중앙도서관 연동)
          │             ▲
          │             │ REST API (Phase 1 계약)
          └──▶ [ backend-ai-agent ] 👈 (현재 서버)
                        ├── LangGraph 8-Node Head Personas (사서 4 + 토론 4)
                        ├── Supabase pgvector: scrap_vector (개인화 독서 기억 전용)
                        ├── My Library: search_my_library (core-api 내 서재/독서상태 조회)
                        └── Book Curator: curator_node (오픈북 신간 + 고전 하이브리드 페어링)
```

---

## 💡 핵심 아키텍처 및 2-Track 모드

### 1. 2-Track 모드 및 8개 페르소나 (LangGraph)

#### 📚 사서 모드 (`LIBRARIAN`)
사용자의 서재 관리, 취향 파악, 맞춤 도서 추천을 전담하는 동물 사서들 (core-api DB ENUM `core.librarian_type`과 1:1 일치):
1. **고양이 사서 (`CAT`)**: 기본 표시명 **'블루'** (차분하고 지적인 평론가 어조, 깊이 있는 통찰, 호환 별칭: `BLUE`)
2. **넓적부리황새 사서 (`SHOEBILL`)**: 기본 표시명 **'슈빌'** (흡입력 있고 에너지 넘치는 1타 강사 어조, 핵심 요약과 동기부여)
3. **바다달팽이 사서 (`SEA_SLUG`)**: 기본 표시명 **'바다달팽이'** (깊은 바닷속 고요함과 다채로운 색감, 몽환적인 심해 힐링 어조)
4. **게코 도마뱀 사서 (`GECKO`)**: 기본 표시명 **'게코'** (책장 벽과 구석구석을 누비며 숨겨진 보물을 찾는 위트 넘치는 호기심 탐구 어조)

> **💡 사용자 커스텀 사서 이름 지원**: 사용자가 직접 사서 이름을 개명한 경우(`librarian_name`), AI 사서가 본인을 기본 표시명 대신 사용자가 지어준 애칭으로 칭하며 친근하게 대화합니다.

#### 🎙️ 토론 모드 (`DEBATE`)
책의 주제, 인물의 선택, 딜레마에 대해 심층 독서 토론을 나누는 전문 파트너들:
5. **평론가 (`DEBATE_CRITIC`)**: 미학적 구조, 복선과 은유 분석, 영화적 통찰 (이동진 톤)
6. **이야기꾼 (`DEBATE_STORYTELLER`)**: 극적 서사 전개, 역사적 맥락과 생생한 몰입감 유도 (설민석 톤)
7. **상담사 (`DEBATE_COUNSELOR`)**: 인물의 심리 메커니즘 분석, 상처와 공감, 내면 치유 (오은영 톤)
8. **관찰가 (`DEBATE_OBSERVER`)**: 본능과 환경의 상호작용, 현실 직시 및 행동 관찰 (강형욱 톤)

### 2. 페르소나 오염 방지 (`summarizer_node`)
8개 페르소나 간 전환(Handoff) 발생 시, 이전 대화에서 사서/토론자의 고유 어조를 완전히 소거하고 **사용자의 질문과 독서 팩트만 정제**하여 다음 페르소나에게 전달합니다.

### 3. 도구(Tools) 레이어
- **`search_my_library`**: `core-api`와 연동하여 사용자가 서재에 등록한 도서 및 독서 상태(`READING`, `COMPLETED`, `WISH`) 조회.
- **`search_scrap_memory`**: Supabase pgvector 기반으로 사용자의 문장/메모를 `member_id`(UUID)로 엄격히 격리 검색 (개인화 전용).
- **`search_recent_books`**: Tavily 실시간 웹 검색 기반 최신 화제작 탐색 도구 (도서 추천은 큐레이터 노드가 전담).

---

## 📂 프로젝트 구조

```text
backend-ai-agent/
├── app/
│   ├── main.py                     # FastAPI 진입점, Swagger UI (/docs), 수명주기 관리
│   ├── core/
│   │   └── config.py               # Pydantic Settings 환경설정
│   ├── domain/
│   │   ├── personas/               # 8개 페르소나 정의 및 중앙 레지스트리
│   │   │   ├── blue.py
│   │   │   ├── shoebill.py
│   │   │   ├── librarian_3.py
│   │   │   ├── librarian_4.py
│   │   │   ├── debate_critic.py
│   │   │   ├── debate_storyteller.py
│   │   │   ├── debate_counselor.py
│   │   │   └── debate_observer.py
│   │   ├── memory/
│   │   │   ├── rag_tool.py          # 개인화 전용 scrap_vector RAG 도구
│   │   │   └── my_library_tool.py   # 내 서재 도서 및 독서상태 조회 도구
│   │   ├── tools/
│   │   │   └── search_books_tool.py # Tavily 경량 웹검색 신간 탐색 도구
│   │   └── graph/
│   │       ├── state.py            # LangGraph State & switch_suggestion 정의
│   │       ├── tools.py            # 공통 범용 도구 레지스트리
│   │       ├── nodes.py            # 8개 페르소나 노드 및 summarizer_node
│   │       └── workflow.py         # 8-Node StateGraph 워크플로우 동적 라우팅
│   ├── infrastructure/
│   │   ├── redis_session.py        # Redis 세션 및 캐시 매니저 (Fallback 지원)
│   │   ├── supabase_client.py      # Supabase pgvector match_scraps 연동
│   │   └── core_api_client.py       # backend-core-api 비동기 REST 클라이언트
│   └── api/
│       ├── schemas.py              # Pydantic 요청/응답 스키마
│       └── router.py               # /chat, /personas, /health 라우터
├── scripts/
│   └── seed_supabase_scrap_vector.py # Supabase pgvector DDL 및 시딩 스크립트
├── tests/
│   └── unit/                       # 단위 테스트 스위트
├── Dockerfile                      # uv 기반 경량 컨테이너
├── docker-compose.yml              # backend-ai-agent + Redis
├── .env.example
├── pyproject.toml
└── README.md
```

---

## 🚀 빠른 시작 (Quick Start)

```bash
# 1. 의존성 설치
uv sync

# 2. 코드 스타일 및 린트 검사
uv run ruff check .

# 3. 단위 테스트 실행
uv run pytest tests/unit -v

# 4. 로컬 개발 서버 실행
uv run uvicorn app.main:app --reload --port 8000
```

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- 헬스 체크: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- 페르소나 목록: [http://localhost:8000/api/v1/personas](http://localhost:8000/api/v1/personas)