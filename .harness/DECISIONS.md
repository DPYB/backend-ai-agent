# DECISIONS.md — 아키텍처 및 정책 결정 히스토리

> 중요한 기술 스택, 아키텍처, 비즈니스 정책 결정의 이유를 기록합니다. (최신 결정이 맨 위로 오는 append-only)

---

| 날짜 | 결정 내용 | 이유 |
| **2026-09-14** | **전사 중앙 인증(`core-api` JWT_SECRET 공유 서명 검증), 게스트 모드 바이패스 및 MSA Token Relay 채택** | `verify_signature=False`로 인한 심각한 보안 취약점(BOLA/토큰 위조)을 원천 차단하고, `core-api`의 `JWT_SECRET_KEY`를 공유받아 0ms 로컬 서명 검증을 수행하며, 비로그인 시 무작위 UUID 생성을 중단하고 게스트 모드(`member_id=None`)로 DB 조회를 스킵(Bypass)하여 비용과 일관성을 지키고, 서재 조회는 Token Relay로 `core-api`의 `GET /api/v1/library/books`를 호출하여 불필요한 내부 무인증 API 신설 없이 MSA 보안 경계를 일치시키기 위함. |
| **2026-09-14** | **4단계 다중 방어 보안 가드레일(0차 Auth ➔ 1차 Safety ➔ 2차 Input ➔ 3차 Security) 구축 및 8종 페르소나/SSE 구조로의 현대적 재구성** | 레거시(`backend-discovery`의 Bedrock 2종 사서)를 단순 복제하지 않고, 본 레포의 구조(8종 페르소나, LangGraph, SSE 스트리밍, $0 무과금)에 맞게 파이썬 고속 정규식 게이트(0ms 무지연) 및 `app/domain/guardrails/` 모듈로 재설계하여 LLM 비용 $0 원천 방어, 109 핫라인 공감 안내, 자모/숫자/이모지 처리, 탈옥/PII 사전 차단을 달성하기 위함. |
| **2026-09-14** | **국립도서관 표지 누락 시 교보문고 고화질 CDN(458px) 0ms 무지연 자동 폴백 및 서지 메타데이터 정제 채택** | 서버 측 추가 HTTP HEAD/GET 유효성 검사로 인한 레이턴시(50~150ms)를 원천 차단하고 순수 ISBN 문자열 조합(0ms)으로 프론트에 즉시 전달하며, 복잡한 도서관 저자 표기('저자 : 헤세;역자 : 서상원;')를 순수 저자명으로 정제하고 KDC/PAGE를 파싱하여 프론트엔드 원클릭 서재 등록 완성도를 극대화하기 위함. |
| **2026-09-14** | **Supabase 공용 DB MSA 스키마 격리(`agent`) 및 Transaction Pooler(포트 6543) 연동** | 전사 $0 무과금 단일 Supabase Postgres 인스턴스 공유 정책 준수, 타 스키마(`core`/`record`) 직접 쿼리 원천 차단(REST API 원칙), Transaction Pooler prepared statement 충돌 방지(`statement_cache_size: 0`), pgvector 코사인 유사도 검색 최적화를 위함. |
| **2026-09-13** | **도서 추천 의도 감지 시 사서 노드에서 큐레이터 서브에이전트로 선위임 및 메시지 정제** | 사서 노드에서 불필요한 1차 LLM 호출(비용/지연 2~3초)을 제거하고, `tool_calls` 생성 후 `ToolMessage` 부재로 인한 LLM API의 400 Bad Request 에러를 원천 차단하기 위함. |
| **2026-09-12** | **DPYB 중앙 Reusable Workflow 연동 및 Git/PR 머지 표준 확정** | 조직 전체 CI/CD 일관성 유지(Python 3.12 CI, PR Lint) 및 `feat/*` 단일화, `[scope]` 대괄호 규격, 사람에 의한 안전한 최종 머지 원칙을 보장하기 위함. |
| **2026-09-12** | **바이브 코딩 하네스 표준 구축** | 복수의 AI 코딩 툴(Antigravity, Claude Code, Codex, Kiro) 간 컨텍스트 동기화 및 단일 책임 문서 관리 원칙을 준수하기 위함. |
| **2026-09-12** | **도서 바코드 스캔 및 Clova OCR을 `backend-ai-agent`에서 무상태(Stateless)로 전담** | `pyzbar`, `Pillow`, `libzbar0` 등 무거운 C-익스텐션 의존성을 `backend-core-api`로부터 격리하여 비즈니스 코어 서버를 가볍고 안전하게 유지하기 위함. |
| **2026-09-12** | **Dockerfile 동적 `$PORT` 바인딩 및 핫리로드 활성화** | Render(임의 포트) 및 Google Cloud Run(포트 8080 주입)의 제로비용 무과금 배포 정책을 단일 Dockerfile로 만족시키기 위함. |
| **2026-09-11** | **사서 페르소나 4종을 `backend-core-api` DB ENUM(`core.librarian_type`)과 1:1 일치** | 사서 종류(고양이, 슈빌, 바다달팽이, 게코)를 DB 스키마와 완벽 일치시키고, 사용자가 지어준 애칭(`librarian_name`)으로 호칭할 수 있게 유연성을 부여하기 위함. |
| **2026-09-11** | **Handoff 시 `summarizer_node`를 통한 어조 오염 방지** | 이전 페르소나의 강한 어조(사서의 귀여움/강사의 박력 등)가 다음 페르소나에게 누적 전이되는 프롬프트 오염 현상을 차단하고 핵심 질문/팩트만 전달하기 위함. |
| **2026-09-11** | **Supabase pgvector `scrap_vector`를 개인화 독서 기억 전용으로 한정** | 도서 추천은 메타데이터 기반이 적합하며, 벡터 DB는 사용자가 직접 남긴 문장/메모에 대한 의미론적 회상에 집중하여 토큰 및 검색 비용을 최소화하기 위함. |
| **2026-09-11** | **LangGraph 기반 8-Node 멀티 페르소나 아키텍처 채택** | 단일 LLM 프롬프트 분기 대비 상태 전이, 도구 호출 제어, 페르소나 간 인수인계(Handoff)의 결정론적 제어가 용이하기 때문. |
