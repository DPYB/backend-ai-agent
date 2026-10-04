# STATE.md — 단계 단위 완료 스냅샷

> 지금까지 완료된 기능과 작업 단계를 마일스톤 단위로 요약 기록합니다.
> **관리 규칙**: 본 문서에는 **본 레포(`backend-ai-agent`)의 핵심 마일스톤 완료 상태만 간결하게(1~3줄 요약)** 유지합니다. 타 레포 상세 구현이나 장황한 코드 diff는 기록하지 않습니다.

---

### 🏛️ 핵심 도메인 아키텍처 완성 현황

- [x] **2-Track 8개 페르소나 오케스트레이션 (`app/domain/graph/`)**:
  - 사서 모드 4종(`CAT`, `SHOEBILL`, `SEA_SLUG`, `GECKO`) 및 토론 모드 4종(`CRITIC`, `STORYTELLER`, `COUNSELOR`, `OBSERVER`).
  - 페르소나 전환 시 어조 오염을 물리적으로 차단하는 `summarizer_node` 및 Redis 세션 네임스페이스(`{member_id}:{uuid}:{persona}`) 격리 완료.
  - SSE 실시간 스트리밍 엔드포인트(`POST /api/v1/chat/stream`) 구축.

- [x] **도서 큐레이션 & 실서지 검증 엔진 (`app/domain/curator/`, `app/infrastructure/`)**:
  - 국립중앙도서관 정식 서지 API(`SearchApi.do`) 연동 및 4단계 실전 검증 체인(제목 정제, 표지 생존 검증, 실서지 바인딩).
  - 깨진 이미지 방지를 위한 교보 CDN/국립도서관 검증 및 `DEFAULT_BOOK_COVER_URL` 고화질 폴백 SSOT 구축.
  - KDC 십진분류 기반 장르 매핑(`map_kdc_to_genre`) 및 `513.8`(심리요법) 철학 승격 라우팅.

- [x] **개인화 RAG & 독서 리포트 (`app/domain/reports/`, `app/domain/memory/`)**:
  - Gemini 임베딩(`text-embedding-004`, 768차원) + Supabase pgvector(`agent.scrap_vector`) 독서 기록/스크랩 벡터화 수신.
  - 사서 월간 독서 리포트(`GET /api/v1/reports/monthly`): 코어 API 통신 실패 시 가짜 목데이터 배제 및 정직한 0건 스켈레톤/사서 격려 멘트 반환.
  - 두 백엔드 서버 간 연결성 진단 필드(`core_api_connected`, `core_api_url`) 연동.

- [x] **무상태 Vision API (`app/domain/vision/`)**:
  - `pyzbar` 기반 13자리 바코드(ISBN-13, EAN13) 스캔 (`POST /api/v1/vision/scan-barcode`).
  - Gemini Flash Vision / Clova OCR 스마트 라우팅 및 5자리 부가기호(KDC) 추출.

- [x] **프로덕션 인프라 & 제로비용 정책 (`app/core/`, Docker, CI/CD)**:
  - Google Cloud Run(서울 `asia-northeast3` 리전) 프로덕션 마이그레이션 및 Render 레거시 배포 제거.
  - Upstash Serverless Redis(`rediss://...`) 연동을 통한 멀티 인스턴스 세션 보존.
  - Tiered Verification(Tier 1 린트 0.2s ➔ Tier 2 로컬 단위회귀 10s ➔ Tier 3 GitHub Actions CI) 구축.

---

### 📌 최근 마일스톤 완료 내역

- [x] **Phase 64: 도구 바인딩 분리 및 member_id ContextVar 주입 (P1 보안 IDOR 차단 & 게스트 매핑)**
  - 메모리 도구(`search_scrap_memory`, `search_debate_memory`, `search_my_library`) 인자에서 `member_id` 완전 제거 및 `current_member_id` ContextVar 주입 고정.
  - LLM 도구 스키마 및 프롬프트에서 `member_id` 노출 전면 제거, 비동기 요청 간 ContextVar 격리 및 fail-closed 거부 반환 구현.
  - 사서 모드(`LIBRARIAN_TOOLS`)와 토론 모드(`DEBATE_TOOLS`) 도구 분리 바인딩 및 전용 보안 테스트 suite(`test_tool_security.py`) 구축.
  - 코어 API 단일 공용 방과 일치하는 `settings.guest_member_id`(`00000000-0000-0000-0000-000000000003`) 매핑 및 게스트 토론 인사이트 쓰기 방지/요청 바디 ID 완전 무시 보안 테스트 15종 100% 그린 검증.
- [x] **Phase 63: 월간 독서 리포트 정직한 0건 스켈레톤 및 코어 API 헬스체크 연결성 진단**
  - 통신 실패 시 하드코딩 3권/832쪽 목데이터 전면 제거 (`_empty_monthly_stats` 스켈레톤 교체).
  - 활동 0건 시 억지 LLM 호출 방지 및 사서 격려 멘트 반환, `GET /api/v1/health`에 `core_api_connected` 진단 필드 추가.
- [x] **Phase 62: Google Cloud Run 이전 및 Render 레거시 정리**
  - Render Deploy Hook 워크플로우 삭제, 아키텍처 및 환경변수 명세를 Cloud Run / Upstash Redis로 정렬.
- [x] **Phase 61: 테스트 검증 계층화 (Tiered Verification)**
  - `pyproject.toml` 테스트 옵션 최적화 (`-q --tb=short`), 외부 LLM 모킹을 통한 단위 회귀 10초 이내 달성 (중앙값 9.92s).
- [x] **Phase 59: 국립중앙도서관 표지 생존 판본 최우선 선별 및 디폴트 커버 방어**
  - HTTP 200 및 교보 플레이스홀더 배제 판본 우선 채택, `DEFAULT_BOOK_COVER_URL` 안전 폴백.
- [x] **Phase 58: 큐레이터 타임아웃 현실화(15초) 및 비상 폴백 도서 100% 실서지 바인딩**
  - 타임아웃 넉넉하게 확장, 비상 명작 8종에 대해 국립도서관 API를 호출하여 13자리 ISBN/실제 쪽수/표지 완성형 제공.
- [x] **Phase 57: KDC 513.8(미술치료/심리요법) 철학(PHILOSOPHY) 라우팅 SSOT 확립**
  - `map_kdc_to_genre`에 순수 KDC 코드 `513.8` 감지 시 `PHILOSOPHY` 승격 규칙 추가.
- [x] **Phase 50~52: 세션 보안 강화, UUID 정규화 및 바코드 KDC 추출 확장**
  - 회원 네임스페이스 격리, `{member_id}:{uuid}:{persona}` 복합 포맷 파싱 및 바코드 응답 스키마 확장.
