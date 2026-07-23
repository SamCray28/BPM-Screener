from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.models.api_schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health_check(settings: Settings = Depends(get_settings)) -> HealthOut:
    return HealthOut(status="ok", app_name=settings.APP_NAME, app_version=settings.APP_VERSION, app_env=settings.APP_ENV)
