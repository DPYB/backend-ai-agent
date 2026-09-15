# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 다음 착수 예정 작업 (토론 파트너 프롬프트 고도화 및 가드레일)

- [ ] **Phase 14.2: 토론 파트너 4종 오마주 프롬프트 고도화 및 마무리 도서 추천 연계**:
  - [ ] **1. 토론자 4종 표시명 `(오마주)` 형식 적용 (`app/domain/personas/` 및 `PERSONA_REGISTRY`)**:
    - `DEBATE_CRITIC`: `"평론가(이동진 오마주)"`
    - `DEBATE_STORYTELLER`: `"이야기꾼(설민석 오마주)"`
    - `DEBATE_COUNSELOR`: `"상담사(오은영 오마주)"`
    - `DEBATE_OBSERVER`: `"관찰가(강형욱 오마주)"`
  - [ ] **2. 4대 토론자 고유 어조 및 필수 답변 포맷 시스템 프롬프트 반영**:
    - `debate_critic.py`: 서사 구조/복선/메타포 분석, 문어체/정교한 어휘, 단정 지양(다만, 그럼에도 불구하고), 답변 말미 별점 + 한 줄 총평 + 화두(질문) 필수
    - `debate_storyteller.py`: 시대적/역사적 격류 소환, "독자님!" 하이텐션, 반전 예고/의성어/느낌표, 답변 말미 현대의 교훈 + 가치관 질문 필수
    - `debate_counselor.py`: 결핍/방어기제/관계 역동 분석, 깊은 공감 후 핵심 통찰, 진단명 금지, 답변 말미 독자 마음 돌봄 질문 + 109 핫라인 지침
    - `debate_observer.py`: 쉼표 호흡, 감상 배제, 환경적 조건화/행동 시그널 직시, 답변 말미 현실 관찰 질문 필수
  - [ ] **3. 토론 마무리 시 도서 추천 연계 지침 추가**:
    - 토론 마무리 시점(사용자의 감사/종료 발화 또는 심화 논의 종료 시)에 토론 주제와 이어지는 다음 책을 권하며 자연스럽게 추천 도서 카드로 이어지도록 프롬프트 지침 연동
  - [ ] **4. 정적 타입 및 문법 점검 (Ruff/py_compile)**

- [ ] **Phase 15: 4단계 다중 방어 가드레일 파이프라인 (0차 인증 ~ 1차 Safety ~ 2차 Input ~ 3차 Security/Jailbreak) 구축**:
  - [ ] **1. 가드레일 도메인 모듈 신설 (`app/domain/guardrails/`)**:
    - `safety_gate.py`: 자해/자살 위기 발화 정규식(`CRISIS_KEYWORDS_PATTERN`), 도서명 예외 처리(`BOOK_TITLE_EXCLUSIONS_PATTERN`, '자살론' 등 오탐 방지), 8개 페르소나별 109 핫라인 맞춤 공감 응답 구현 (0ms 무지연, LLM 비용 $0)
    - `input_gate.py`: 자모 난타(`ㅋㅋㅋㅋ`), 숫자 단독(`12345`), 이모지 단독(`🐱🐾`) 비정상 입력 정규식 감지 및 8개 페르소나별 즉각적인 되묻기/안내 응답 (LLM 토큰 낭비 방지)
    - `security_gate.py`: 시스템 프롬프트 유출 시도, 탈옥(Jailbreak / DAN / Ignore instructions), PII(주민등록번호 등) 사전 차단 게이트 구현 및 선택적 AWS Bedrock Guardrails 어댑터 인터페이스 마련
    - `shared_rules.py`: 시스템 프롬프트 레벨 공통 가드레일 (날씨 팩트 엄수, 도서 서비스 범위 밖 질문 정중 거절, 내부 메타데이터 노출 방지)
  - [ ] **2. API 엔드포인트(`POST /api/v1/chat`, `POST /api/v1/chat/stream`) 4단계 게이트 연동**:
    - 0차: 인증 확인 (`evaluate_auth_gate`) - Bearer 토큰 검증 및 `sub` 추출 (정책에 따른 401 반환 또는 게스트 지원)
    - 1차: `evaluate_safety_gate` (위기 발화 시 즉각 핫라인 반환)
    - 2차: `evaluate_input_gate` (무의미 입력 시 즉각 안내 반환)
    - 3차: `evaluate_security_gate` (탈옥/인젝션/PII 시 즉각 차단 반환)
    - 통과 시에만 LangGraph LLM 실행. 일반 `/chat`과 실시간 SSE `/chat/stream` 모두 4단계 게이트 일관성 100% 보장
  - [ ] **3. 단위 테스트 작성 및 전수 검증 (`tests/unit/test_guardrails.py`)**:
    - Safety Gate: 위기 발화 감지, '자살론' 등 도서명 정상 통과, 페르소나별 핫라인 검증
    - Input Gate: 자모/숫자/이모지 감지 및 응답 검증
    - Security Gate: 프롬프트 탈취, 탈옥 패턴, PII 감지 및 차단 검증
    - API 게이트 통합 테스트: `/chat` 및 `/chat/stream`에서 LLM 호출 없이 즉시 응답되는지 검증
  - [ ] **4. 하네스 문서 및 CI 점검**:
    - `STATE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `HANDOFF.md` 최신화
    - Ruff lint/format, Mypy 타입 체크, Pytest 100% 그린 확인

---

## 대기 중인 통합 검증 작업

- [ ] **로컬 3대 서비스(코어 API + AI 에이전트 + 프론트엔드) 풀스택 통합 테스트 및 연동 검증**:
  - `backend-core-api` 신규 인증 엔드포인트(`POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`) 구현 완료 확인
  - `backend-ai-agent` 로컬 Uvicorn 서버 기동 (`uv run uvicorn app.main:app --port 8000 --reload`)
  - `frontend-reader-web` 로컬 Vite 개발 서버 기동 (`npm run dev`)
  - 프론트엔드 브라우저 접속 후:
    1. 로그인 및 기본 사서(CAT) 활성화 확인
    2. 사서 채팅창에서 자연어 도서 추천 요청 (예: "오늘 비 오는데 읽을 만한 따뜻한 책 추천해줘")
    3. 추천된 도서 카드(표지, 쪽수, 장르, 저자) 확인 및 **[등록 ➔]** 원클릭 클릭 시 `/register` 폼 100% 자동 채움 검증
    4. 내 서재 등록 완료 및 `backend-core-api` DB 영속화 확인
