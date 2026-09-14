# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 작업 체크리스트만 유지합니다. (완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제)

---

## 다음 착수 예정 작업 (PR 머지 후 진행)

- [ ] **도서 추천 상세 메타데이터 수집 및 프론트 서재 등록 자동화**:
  - `RecommendedBook` 스키마 확장 (`category`: 대분류, `subject`: 주제, `page_count`: 쪽수, `cover_url`: 고화질 표지 URL 등)
  - 국립중앙도서관 Open API(`SearchApi.do`) 응답 파싱 항목 확장 (KDC 대분류, 주제 키워드, 페이지 수)
  - 신간 및 표지 누락 시 교보문고 고화질 CDN URL(`https://contents.kyobobook.co.kr/sih/fit-in/458x0/pdt/{isbn}.jpg`) 자동 폴백
  - `/api/v1/chat` 응답 및 `/api/v1/chat/stream` SSE 이벤트(`event: done` 및 메타데이터)에 추천 도서 상세 정보 포함
  - 프론트엔드(`frontend-reader-web`) `LibrarianChat.jsx` 추천 카드에서 원클릭 서재 등록 시 모든 필드가 자동 반영되도록 연동 지원
