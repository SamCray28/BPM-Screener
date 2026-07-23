from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.db_models import TelemetryEvent, WebhookAuditLog
from app.models.telemetry_schemas import TelemetryIn
from app.security import verify_formula_version, verify_schema_version, verify_webhook_secret

logger = logging.getLogger("bpm.telemetry")

router = APIRouter(prefix="/webhook", tags=["telemetry"])


@router.post("/telemetry")
async def receive_telemetry(
    payload: TelemetryIn,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    try:
        verify_webhook_secret(payload.webhook_secret, settings)
        verify_schema_version(payload.schema_version, settings)
        verify_formula_version(payload.formula_version, settings)
    except Exception:
        db.add(WebhookAuditLog(outcome="rejected_auth", symbol=payload.symbol, event_id=payload.event_id))
        await db.commit()
        raise

    existing = await db.execute(select(TelemetryEvent).where(TelemetryEvent.event_id == payload.event_id))
    if existing.scalar_one_or_none() is not None:
        db.add(WebhookAuditLog(outcome="duplicate", symbol=payload.symbol, event_id=payload.event_id))
        await db.commit()
        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "duplicate", "event_id": payload.event_id})

    event = TelemetryEvent(
        event_id=payload.event_id, schema_version=payload.schema_version, formula_version=payload.formula_version,
        configuration_id=payload.configuration_id, symbol=payload.symbol, exchange=payload.exchange,
        timeframe=payload.timeframe, bpm_mode=payload.bpm_mode, bar_open_time=payload.bar_open_time,
        bar_close_time=payload.bar_close_time, confirmed_state=payload.confirmed_state,
        confirmed_direction=payload.confirmed_direction, bo_status=payload.bo_status,
        active_bo_price=payload.active_bo_price, mc_status=payload.mc_status,
        active_mc_price=payload.active_mc_price, pressure_efficiency=payload.pressure_efficiency,
        acceptance_status=payload.acceptance_status, bes_scenario=payload.bes_scenario,
        raw_payload=json.dumps(payload.model_dump(exclude={"webhook_secret"})),
    )
    db.add(event)
    db.add(WebhookAuditLog(outcome="accepted", symbol=payload.symbol, event_id=payload.event_id))
    await db.commit()
    await db.refresh(event)

    logger.info("telemetry accepted event_id=%s symbol=%s bo_status=%s mc_status=%s",
                payload.event_id, payload.symbol, payload.bo_status, payload.mc_status)
    return JSONResponse(status_code=status.HTTP_201_CREATED,
                         content={"status": "accepted", "event_id": event.event_id, "id": event.id})
