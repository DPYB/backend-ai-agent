# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 다음 착수 예정 작업 (PR 머지 및 통합 테스트 준비)

- [ ] **로컬 3대 서비스(코어 API + AI 에이전트 + 프론트엔드) 풀스택 통합 테스트 및 연동 검증**:
  - `backend-core-api` 신규 인증 엔드포인트(`POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`) 구현 완료 확인
  - `backend-ai-agent` 로컬 Uvicorn 서버 기동 (`uv run uvicorn app.main:app --port 8000 --reload`)
  - `frontend-reader-web` 로컬 Vite 개발 서버 기동 (`npm run dev`)
  - 프론트엔드 브라우저 접속 후:
    1. 로그인 및 기본 사서(CAT) 활성화 확인
    2. 사서 채팅창에서 자연어 도서 추천 요청 (예: "오늘 비 오는데 읽을 만한 따뜻한 책 추천해줘")
    3. 추천된 도서 카드(표지, 쪽수, 장르, 저자) 확인 및 **[등록 ➔]** 원클릭 클릭 시 `/register` 폼 100% 자동 채움 검증
    4. 내 서재 등록 완료 및 `backend-core-api` DB 영속화 확인
