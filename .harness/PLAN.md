# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 1. 독서 기록/스크랩 벡터화 수신 엔드포인트 구현

`backend-record-api`에서 독서 기록/스크랩 생성 시 `trigger_ai_vectorization`으로 호출할 비동기 REST 엔드포인트를 열어 `SupabaseVectorClient.insert_scrap_vector`와 연동합니다.

- [ ] 스크랩 벡터화 요청 스키마(`ScrapVectorizeRequest`) 및 응답 스키마 정의
- [ ] `POST /api/v1/memory/scraps` (또는 `/api/v1/vectorize`) 라우트 구현
- [ ] 수신된 문장과 메모를 `generate_query_embedding`으로 임베딩 후 Supabase `scrap_vector`에 적재
- [ ] 단위 테스트 작성 및 검증

---

## 2. LangGraph 스트리밍(SSE) 응답 인터페이스 지원

프론트엔드 채팅 경험 향상을 위해 청크 단위 실시간 텍스트 스트리밍을 지원합니다.

- [ ] `/api/v1/chat/stream` Server-Sent Events (SSE) 엔드포인트 프로토타입 설계
- [ ] LangGraph `astream_events` 기반 토큰 스트리밍 연동
