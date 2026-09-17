# AGENTS.md — 개발 하네스 지침

> DPYB `backend-ai-agent` 서비스 레포지토리의 AI 코딩 에이전트(Antigravity, Claude Code, Codex, Kiro 등) 공용 워크플로우 및 개발 규칙집입니다.

---

## 1. 세션 시작 시 필수 읽기 순서
어떤 AI 도구로 세션을 시작하든 아래 순서대로 먼저 읽고 컨텍스트를 동기화한다:
1. `.harness/HANDOFF.md` — 직전 세션이 어디서 멈췄는지
2. `.harness/STATE.md` — 지금까지 무엇이 완료되었는지
3. `.harness/ARCHITECTURE.md` — 기술 스택/폴더 구조/컨벤션
4. `.harness/PLAN.md` — 현재 진행 중이거나 제안된 계획
5. 필요 시 `.harness/DECISIONS.md`(과거 결정 이유), `.harness/BACKLOG.md`(미해결 부채)

---

## 2. 문서별 책임 (중복 기록 금지)

| 문서 | 반드시 담아야 하는 내용 (단일 소유) | 절대 담지 말아야 하는 내용 |
| :--- | :--- | :--- |
| **`HANDOFF.md`** | 세션마다 무엇을 했는지 (append-only 서술형 로그) | 단계별 완료 요약(`STATE` 몫), 결정 이유(`DECISIONS` 몫) |
| **`STATE.md`** | 지금까지 끝난 것의 단계 단위 요약 스냅샷 | 세션별 서술(`HANDOFF` 몫). 사소한 커밋/이슈를 로그처럼 쌓지 않음 |
| **`ARCHITECTURE.md`** | 지금 시점의 기술 스택/폴더 구조/컨벤션 (현재 상태) | 왜 그렇게 정했는지(`DECISIONS` 몫), 진행 중인 계획(`PLAN` 몫) |
| **`DECISIONS.md`** | 결정 내용과 이유의 역사 (최신 결정이 맨 위로, append-only) | 단순 구현 여부나 진행 상황(`STATE` 몫) |
| **`PLAN.md`** | 아직 안 끝난 계획과 체크리스트만 | 완료된 항목 (체크만 남겨두지 말고 `STATE`로 옮긴 뒤 제거) |
| **`BACKLOG.md`** | 지금 하지 않지만 나중에 할 것 (버그, 기술부채, 아이디어) | 현재 진행 중인 계획(`PLAN` 몫) |

---

## 3. 작업 워크플로우 (필수)
- **계획 수립 우선**: 새로운 기능/변경 요청을 받으면 바로 코드를 고치지 말고 `.harness/PLAN.md`에 계획 초안을 작성해 사용자에게 제시한다. (단순 질의응답, 사소한 오탈자 수정은 계획 없이 바로 가능)
- **사용자 승인 후 구현**: 사용자가 명시적으로 컨펌하면 구현을 시작한다.
- **점진적 반영**: `PLAN.md`의 세부 체크리스트가 완료될 때마다 즉시 `.harness/STATE.md`에 한 줄로 반영하고 `PLAN.md`에서 제거한다.
- **세션 종료/인수인계**: 작업을 중단하거나 세션을 종료할 때 반드시 `.harness/HANDOFF.md`에 다음 세션을 위한 인수인계 서술을 남긴다.
- **중요 결정 기록**: 아키텍처나 정책의 중요한 결정은 `.harness/DECISIONS.md` 표 최상단에 이유와 함께 기록한다.
- **커밋 및 푸시**: 사용자가 명시적으로 요청했을 때만 수행하며, 변경된 파일만 선별해 스테이징한다 (`git add .` 지양). AI는 절대 임의로 Git 커밋/푸시를 실행하지 않는다.
- **PR 생성 및 머지**: AI는 브랜치 작업 및 PR 생성 보조까지만 담당하며, **develop/main 브랜치 PR 머지는 에이전트가 실행하지 않고 사람이 직접 클릭**하여 머지한다. AI가 자의적으로 PR을 머지하는 행위는 엄격히 금지된다.

---

## 4. 이 레포 고유 정책 (`backend-ai-agent`)

### 4.1 도메인 역할 & 책임 분리
- DPYB의 **지능형 AI 페르소나, 개인화 독서 기억 RAG(LangGraph, pgvector)**와 함께 **ISBN 바코드 스캔, 문장 스크랩 Clova OCR 등 독서 수집 기능 구현**을 전담합니다.
- **역할 분리 원칙**: 무거운 이미지 처리 및 AI 추론은 본 마이크로서비스에서 무상태(Stateless)로 수행하며, **도서/스크랩 등 모든 정형 데이터의 순수 DB 영속화(RDBMS CRUD 및 영구 보관)는 `backend-core-api`에 위임**합니다.
- **2-Track 모드 (8개 페르소나)**:
  - **사서 모드 (`LIBRARIAN`)**: 동물 사서 4종 (`CAT`=블루, `SHOEBILL`=슈빌, `SEA_SLUG`=바다달팽이, `GECKO`=게코) — `backend-core-api`의 DB ENUM `core.librarian_type`과 1:1 일치하며, 사용자 정의 사서 닉네임(`librarian_name`)을 지원합니다.
  - **토론 모드 (`DEBATE`)**: 심층 독서 토론 파트너 4종 (`DEBATE_CRITIC`=이동진 톤, `DEBATE_STORYTELLER`=설민석 톤, `DEBATE_COUNSELOR`=오은영 톤, `DEBATE_OBSERVER`=강형욱 톤).
- **페르소나 오염 방지 (`summarizer_node`)**: 페르소나 전환 시 이전 대화의 어조를 소거하고 사용자 질의와 독서 팩트만 정제하여 전달합니다.

### 4.2 도구 및 스토리지 연동 규격
- **`search_my_library`**: `backend-core-api`와 연동하여 사용자의 서재 도서 및 독서 상태(`READING`, `COMPLETED`, `WISH`)를 조회합니다.
- **`search_recent_books`**: Tavily 경량 REST 탐색을 통해 최신 화제작 및 웹 트렌드 신간 도서를 실시간 검색합니다. (일반 도서 추천은 `curator_node`가 Yes24 RSS 오픈북 캐시 및 국립중앙도서관 4단계 검증 체인으로 신구 하이브리드 페어링을 전담합니다.)
- **Vision API**: `pyzbar`, `Pillow`, `libzbar0`를 통한 바코드(ISBN-13) 스캔 및 Naver Cloud Clova OCR General API V2 연동을 무상태(Stateless)로 제공하여 `core-api`를 무거운 C-익스텐션 의존성으로부터 보호합니다.

### 4.3 제로비용(Zero-cost) 및 인프라 정책
- **포트 바인딩**: Render 및 Google Cloud Run 동적 환경변수 `${PORT:-8000}`를 바인딩합니다.
- **로컬 개발**: `docker-compose.yml` 볼륨 마운트 기반 핫리로드(`--reload`)를 지원합니다.
- **슬립 방지**: `/api/v1/health` 헬스체크 엔드포인트 호출 시 Supabase 핑(`scrap_vector` 1행 조회)을 수행하여 Render(15분) 및 Supabase(7일 미사용) 동시 활성화를 유지합니다.
- **메모리 한도 준수**: Render 무료 티어(512MB RAM) 제약을 고려하여 불필요한 모델 로컬 적재를 피하고 API 호출 기반(Gemini Flash/Embedding)을 유지합니다.

### 4.4 AI 자가 검증 필수 (Self-Validation)
- **AI 자가 검증 필수**: 코드 수정 직후 반드시 `ruff check --fix .`, `mypy .`, `pytest`를 터미널에서 실행하고, 에러나 타입 경고가 0개가 될 때까지 스스로 터미널 로그를 보고 코드를 고칠 것.

---

## 5. 브랜치 & 커밋/PR 컨벤션

DPYB 최신 공통 개발 표준([02-git-conventions.md](https://github.com/DPYB/.github/blob/main/docs/02-git-conventions.md))을 엄격히 준수한다.

### 5.1 브랜치 전략 (`feat/*` 단일화)
- **브랜치 흐름**: `main` <- `develop` <- `feat/*`
- **단일 접두사 원칙**: 기능 개발, 버그 수정, 리팩토링 등 작업 유형에 관계없이 **모든 작업 브랜치는 `feat/*`로 단일화**한다.
  - 예시: `feat/AI-12-chat-flow`, `feat/vision-barcode-scan`, `feat/fix-rag-dimension`
  - 금지: `feature/*`, `fix/*`, `refactor/*`, `chore/*` 등의 별도 접두사 생성 금지

### 5.2 커밋 & PR 제목 컨벤션 (`[scope]` 대괄호 표준)
- 커밋 메시지와 PR 제목은 반드시 **`type[scope]: description`** 대괄호 표준 형식을 따른다.
- **형식**: `<type>[<scope>]: <description>`
  - `feat[agent]: 동물 사서 4종 페르소나 및 프롬프트 구현`
  - `feat[vision]: 도서 바코드 EAN13 ISBN 스캔 엔드포인트 추가`
  - `fix[rag]: Gemini 임베딩 벡터 768차원 일치 오류 수정`
  - `test[vision]: Clova OCR 줄바꿈 복원 단위 테스트 추가`
  - `ci[workflow]: 중앙 Reusable CI 및 PR Lint 워크플로우 연동`
- **주요 Type**: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`
- **주요 Scope**: `[agent]`, `[persona]`, `[chat]`, `[rag]`, `[vision]`, `[infra]`, `[harness]`, `[ci]` 등

### 5.3 PR 머지 규칙 (사람 직접 클릭)
- **develop/main 브랜치 PR 머지는 에이전트가 실행하지 않고 사람이 직접 클릭**: CI(`reusable-python-ci.yml`, `reusable-pr-lint.yml`) 통과 후, 반드시 인간 팀원이 코드 리뷰 및 승인(Approve)을 완료하고 **직접 머지(Squash and merge) 버튼을 클릭**한다.
- AI 코딩 에이전트는 절대 PR 머지를 자의적으로 실행하지 않는다.

### 5.4 PR 본문 표준 템플릿 (항상 필수 준수)
모든 AI 에이전트는 PR 생성 시 임의의 형식으로 작성하지 말고, 반드시 아래 DPYB 표준 마크다운 템플릿의 4대 섹션을 모두 채워서 작성해야 한다:
> **⚠️ 린터 준수 주의**: `- **목적**:` 및 `- **주요 변경사항**:` 뒤 동일한 줄에 실제 설명 텍스트를 반드시 채워야 중앙 PR Lint CI(`reusable-pr-lint.yml`)의 빈 플레이스홀더 검사를 안전하게 통과한다.

```markdown
## 🎯 작업 요약
- **목적**: [작업 목적 한 줄 요약]
- **주요 변경사항**: [주요 변경사항 한 줄 요약]

### 세부 내용
1. 

## 🌐 적용 범위
- 영향받는 도메인/컴포넌트/API: 

## 💬 고려사항 & 리뷰 포인트
- 

## ✅ 체크리스트
- [x] 로컬 단위 테스트 통과 (Pytest)
- [x] Ruff 린트 및 포맷 검사 통과
- [x] Mypy 정적 타입 체크 통과
- [x] 하네스 문서 갱신 완료 (STATE.md, PLAN.md, HANDOFF.md, DECISIONS.md)
```



---

## 6. 배포
[DPYB `.github` 레포의 04-deployment-policy.md](https://github.com/DPYB/.github/blob/main/docs/04-deployment-policy.md)를 따른다.
- 1단계: 로컬 도커 개발 (`docker-compose.yml`)
- 2단계: Render 무료 티어 우선 배포
- 3단계: GCP Cloud Run 무료 크레딧 폴백

