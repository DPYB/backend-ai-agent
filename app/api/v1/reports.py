"""FastAPI router for Monthly Reading Reports orchestration."""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query, status

from app.api.router import extract_member_id_from_auth
from app.domain.reports.generator import build_monthly_report
from app.infrastructure.core_api_client import get_core_api_client
from app.schemas.report import MonthlyReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/monthly",
    response_model=MonthlyReportResponse,
    summary="사서 월간 독서 리포트 조회 (Core API 통계 + AI LLM 성향 분석 & 다음 달 처방)",
)
async def get_monthly_report(
    year: int = Query(..., ge=2020, le=2100, description="조회 연도 (예: 2026)"),
    month: int = Query(..., ge=1, le=12, description="조회 월 (1~12)"),
    authorization: Optional[str] = Header(default=None, description="Bearer JWT Token"),
    x_member_id: Optional[str] = Header(
        default=None, alias="X-Member-Id", description="Direct Member UUID"
    ),
) -> MonthlyReportResponse:
    """Fetch complete Monthly Reading Report combining Core API 01~05 and AI Agent 06~07.

    1. Retrieves 01~05 statistics from backend-core-api using Token Relay.
    2. Enriches 03. preferences with AI Agent debate keywords from agent.debate_insights / traces.
    3. Synthesizes 06. AI Analysis and 07. Prescription using Gemini LLM with librarian persona.
    4. Enriches recommended book cards with National Library verified metadata and Kyobo covers.
    """
    try:
        # Extract authenticated user UUID and raw token if provided
        auth_mid, raw_token = extract_member_id_from_auth(authorization)
        effective_mid = auth_mid or x_member_id or "00000000-0000-0000-0000-000000000001"

        # 1. Fetch raw stats from backend-core-api
        core_client = get_core_api_client()
        raw_stats = await core_client.get_monthly_report_stats(
            year=year,
            month=month,
            token=raw_token,
            member_id=effective_mid,
        )

        # 2. Build full monthly report response
        report = await build_monthly_report(
            raw_stats=raw_stats,
            token=raw_token,
            member_id=effective_mid,
        )
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error orchestrating monthly reading report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"월간 독서 리포트 생성 중 오류가 발생했습니다: {str(e)}",
        ) from e
