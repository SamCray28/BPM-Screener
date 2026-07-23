from __future__ import annotations

import secrets

from fastapi import HTTPException, status

from app.config import Settings


def verify_webhook_secret(provided_secret: str, settings: Settings) -> None:
    expected = settings.BPM_WEBHOOK_SECRET
    if not expected:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                             detail="Webhook secret is not configured on the server.")
    if not provided_secret or not secrets.compare_digest(provided_secret, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")


def verify_schema_version(schema_version: str, settings: Settings) -> None:
    allowed = settings.allowed_schema_versions
    if allowed and schema_version not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail=f"Unsupported schema_version '{schema_version}'.")


def verify_formula_version(formula_version: str, settings: Settings) -> None:
    allowed = settings.allowed_formula_versions
    if allowed and formula_version not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                             detail=f"Unsupported formula_version '{formula_version}'.")
