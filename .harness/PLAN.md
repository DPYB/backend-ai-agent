# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 본 레포(`backend-ai-agent`) 작업 체크리스트만 유지합니다.
> 타 레포 작업은 해당 레포의 `PLAN.md`에서 관리하며, 완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제합니다.

---

### 📌 Phase 60: 국립도서관 KDC 부재 시 EA_ADD_CODE 5자리 다중 폴백 및 분류 체계 SSOT 강화

- [ ] **`app/infrastructure/national_library_client.py` KDC 다중 폴백 및 5자리 부가기호 연동**:
  - `search_book` 및 `search_by_isbn`에서 KDC 필드가 누락/공백(`""`)인 경우, `EA_ADD_CODE`(예: `"03320"`)의 5자리 부가기호에서 뒤 3자리(`"320"`)를 추출하여 `raw_kdc`로 폴백
  - `map_kdc_to_genre`:
    - `extract_kdc_code`를 거쳐 추출된 `raw_code`가 KDC `513.8`(미술치료/심리치료/임상요법)인 경우 즉시 `PHILOSOPHY`로 승격
    - `SUBJECT`에 `"3"` 같은 1자리 KDC 대분류 숫자만 오는 경우와 실제 주제어 텍스트(예: `"미술치료"`, `"심리"`)가 오는 경우를 엄격히 분기하여, 텍스트 주제어일 때 키워드 매핑을 우선 수행
    - 반환 딕셔너리에 `subject` 및 `display_genre`를 명시적으로 채워 프론트엔드/추천 카드 전달 보장
- [ ] **`app/api/router.py` `classify_genre` 엔드포인트 응답 확장**:
  - `ClassifyGenreResponse`에 `subject`, `display_genre`를 함께 반환하여 프론트엔드 도서 등록 폼의 자동 채움 지원
- [ ] **단위 테스트 작성 및 AI 자가 검증 (Self-Validation)**:
  - `tests/unit/test_recommend_metadata.py`:
    - `EA_ADD_CODE: "03320"` 기반 KDC 추출 및 장르 판별 단위 테스트
    - KDC가 비어있고 `SUBJECT`가 단일 숫자이거나 비어있을 때의 다중 폴백 단위 테스트
    - 순수 KDC `513.8` 및 주제어 기반 `PHILOSOPHY` 승격 회귀 테스트
  - `uv run pytest tests/unit/test_recommend_metadata.py`, `uv run ruff check .`, `uv run mypy .` 무결점 검증

---

### 📌 Milestone 4 (E2E 연동 스모크 테스트 준비)
> **본 레포 AI 서빙 API 상태 점검 항목**

- [ ] **도서 추천 카드 응답 규격 점검**:
  - `### 📖 {도서명}` 헤딩, 표지 이미지(`cover_url`), 장르, 총 쪽수(`page_count`) 구조 정합성
- [ ] **서재 도서 조회 분기 점검**:
  - `### 📚 {도서명}` 헤딩 및 `library_books` 객체 규격 유지 확인
- [ ] **토론 모드 팩트 그라운딩 및 페르소나 정합성**:
  - 페르소나 전환 시 어조 소거 및 도서 메타데이터 기반 대화 검증
