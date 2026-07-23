from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.engines.behavioral import score_behavioral
from app.engines.weights import HistoricalConfig
from app.models.api_schemas import ScoreExplanationOut, score_to_api
from app.providers.factory import build_behavioral_data_provider, build_historical_stats_provider

router = APIRouter(prefix="/behavior", tags=["behavior"])


class BehavioralDataOut(BaseModel):
    confirmed_state: str
    confirmed_direction: str
    bo_status: str
    mc_status: str
    pressure_efficiency: float
    acceptance_status: str
    bes_scenario: str
    forecast_bias: str | None = None


class BehaviorResponse(BaseModel):
    symbol: str
    behavioral_data: BehavioralDataOut
    behavior_score: ScoreExplanationOut


@router.get("/{symbol}", response_model=BehaviorResponse)
async def get_behavior(
    symbol: str,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> BehaviorResponse:
    behavioral_provider = build_behavioral_data_provider(settings, db)
    historical_provider = build_historical_stats_provider(settings, db)

    data = await behavioral_provider.get_behavioral_data(symbol.upper())
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail=f"No confirmed BPM telemetry found yet for '{symbol}'.")

    condition_key = f"{data.confirmed_state}|{data.confirmed_direction}|{data.bes_scenario}"
    historical = await historical_provider.get_historical_stats(symbol.upper(), condition_key)
    score = score_behavioral(data, historical, HistoricalConfig(min_sample_size=settings.HISTORICAL_MIN_SAMPLE_SIZE))

    return BehaviorResponse(
        symbol=symbol.upper(),
        behavioral_data=BehavioralDataOut(
            confirmed_state=data.confirmed_state, confirmed_direction=data.confirmed_direction,
            bo_status=data.bo_status, mc_status=data.mc_status, pressure_efficiency=data.pressure_efficiency,
            acceptance_status=data.acceptance_status, bes_scenario=data.bes_scenario, forecast_bias=data.forecast_bias,
        ),
        behavior_score=score_to_api(score),
    )
