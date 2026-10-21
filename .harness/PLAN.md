# PLAN.md — 미완료 작업 계획

> 현재 진행 중이거나 사용자 컨펌 후 바로 착수할 본 레포(`backend-ai-agent`) 작업 체크리스트만 유지합니다.
> 타 레포 작업은 해당 레포의 `PLAN.md`에서 관리하며, 완료된 작업은 `STATE.md`로 이동 후 본 문서에서 삭제합니다.

---

### 📌 Phase 70-3: Core API 추천 도서 서지 장르 누락 수정 (구현 완료 / PR 대기)
- [x] **1. `app/infrastructure/core_api_client.py` 정규화 보존**:
  - `search_books`에서 Core API 응답의 `genre`, `kdc`, `subject`를 딕셔너리에 보존
- [x] **2. `app/domain/graph/curator_node.py` 장르 바인딩 고도화**:
  - `_verify_single_candidate`의 Core API 검증 성공 경로에서 3단계 장르 바인딩 적용:
    - 1순위: `item.get("genre")` 유효 및 `"NONE"` 아닐 시 `_normalize_to_core_genre` 표준 변환
    - 2순위: `item.get("kdc")` 기반 `map_kdc_to_genre` KDC 폴백 변환
    - 3순위: 서지 정보 부재 시 `cand.get("genre")` 또는 `None` 유지 (억지 추론 배제)
- [x] **3. 단위 테스트 작성 및 품질 검증 (`tests/unit/test_hierarchical_curator_verification.py`)**:
  - Core API 성공 경로 표준 장르 보존, KDC 매핑, 부재 시 `None` 유지, 국립도서관 폴백 회귀 테스트 4종 추가
  - 이전 실행 기준 단위 회귀 308개 100% 그린, Ruff, Mypy, 하네스 규격 통과
- [ ] **4. 커밋 및 PR 생성 (사용자 컨펌 대기)**:
  - 브랜치 `feat/fix-core-api-genre-curation` 변경 사항 최종 검토 및 사용자 승인 후 PR 생성

---

### 📌 Phase 70-2: 도서 추천 카드 응답 규격 점검 (분석 완료)
- [x] **추천 카드 응답 규격 정적 점검**:
  - 큐레이터 응답 ➔ 프론트엔드 카드 렌더링 ➔ 도서 등록 폼(`/register`) 전체 데이터 흐름 점검 완료
  - `### 📖 {도서명}`, `cover_url`, `page_count` 규격 일치 확인
  - Core API 1차 서지 검증 성공 경로에서 `genre`가 `None`으로 누락되는 유일한 결함 식별 (Phase 70-3으로 분리 해결)

---

### 📌 Milestone 4: E2E 연동 스모크 테스트 및 계약 검증 (미완료 보존)
> **본 레포 AI 서빙 API 상태 점검 및 남은 E2E 검증 항목**

- [ ] **추천 카드 마커 및 카드 메타데이터 프론트엔드 E2E 실연동 검증**:
  - `### 📖 {도서명}` 마커 파싱 및 도서 등록 폼 연동 시 실제 메타데이터 누락 여부 점검
  - 추천 카드 UI 계약을 엔드투엔드로 고정하는 통합/E2E 테스트 공백 보완
- [ ] **서재 도서 조회 분기 점검**:
  - `### 📚 {도서명}` 헤딩 및 `library_books` 객체 규격 유지 확인
- [ ] **토론 모드 팩트 그라운딩 및 페르소나 정합성**:
  - 페르소나 전환 시 어조 소거 및 도서 메타데이터 기반 대화 검증
