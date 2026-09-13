# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 1. LangGraph 스트리밍(SSE) 응답 인터페이스 지원

프론트엔드 채팅 경험 향상을 위해 청크 단위 실시간 텍스트 스트리밍을 지원합니다.

- [ ] `/api/v1/chat/stream` Server-Sent Events (SSE) 엔드포인트 프로토타입 설계
- [ ] LangGraph `astream_events` 기반 토큰 스트리밍 연동

