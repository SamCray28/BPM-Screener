from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db_models import RankingResult, RankingRun

router = APIRouter(tags=["history"])


class RankingResultSummaryOut(BaseModel):
    run_at: str
    rank: int
    symbol: str
    opportunity_score: float
    behavior_score: float
    confidence: float


@router.get("/history", response_model=List[RankingResultSummaryOut])
async def history(
    symbol: str | None = None,
    limit: int = Query(50, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> List[RankingResultSummaryOut]:
    stmt = select(RankingResult, RankingRun).join(RankingRun, RankingResult.run_id == RankingRun.id)
    if symbol:
        stmt = stmt.where(RankingResult.symbol == symbol.upper())
    stmt = stmt.order_by(RankingRun.run_at.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()
    return [
        RankingResultSummaryOut(
            run_at=run.run_at.isoformat(), rank=res.rank, symbol=res.symbol,
            opportunity_score=res.opportunity_score, behavior_score=res.behavior_score, confidence=res.confidence,
        )
        for res, run in rows
    ]


@router.get("/history/{symbol}/full")
async def history_full(symbol: str, limit: int = Query(20, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    """Full explainable RankedSymbol JSON (as persisted at ranking time),
    not just the summary columns — for research/audit drill-down."""
    stmt = (
        select(RankingResult, RankingRun)
        .join(RankingRun, RankingResult.run_id == RankingRun.id)
        .where(RankingResult.symbol == symbol.upper())
        .order_by(RankingRun.run_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        {"run_at": run.run_at.isoformat(), "result": json.loads(res.full_result_json)}
        for res, run in result.all()
    ]
