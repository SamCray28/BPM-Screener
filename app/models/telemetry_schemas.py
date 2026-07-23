"""Pydantic v2 schema for the TradingView webhook. Mirrors the JSON
block Pine builds in BPM_v3.0.1.pine section 17 exactly — Pine is the
source of truth for this schema. Ported from the bpm-python receiver
with no changes to field names or semantics."""
from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TelemetryIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    webhook_secret: str
    schema_version: str = Field(min_length=1)
    formula_version: str = Field(min_length=1)
    configuration_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    exchange: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    bpm_mode: Literal["Micro", "Structural"]

    bar_open_time: int = Field(ge=0)
    bar_close_time: int = Field(ge=0)

    confirmed_state: str = Field(min_length=1)
    confirmed_direction: Literal["Bullish", "Bearish", "Neutral"]

    bo_status: str = Field(min_length=1)
    active_bo_price: float

    mc_status: str = Field(min_length=1)
    active_mc_price: float

    pressure_efficiency: float = Field(ge=0.0, le=100.0)
    acceptance_status: str = Field(min_length=1)
    bes_scenario: str = Field(min_length=1)

    @field_validator(
        "event_id", "symbol", "exchange", "timeframe",
        "confirmed_state", "bo_status", "mc_status",
        "acceptance_status", "bes_scenario",
    )
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("active_bo_price", "active_mc_price", "pressure_efficiency")
    @classmethod
    def _must_be_finite(cls, value: float) -> float:
        if value is None or not math.isfinite(value):
            raise ValueError("must be a finite number (no NaN/Infinity)")
        return value

    @model_validator(mode="after")
    def _bar_times_ordered(self) -> "TelemetryIn":
        if self.bar_close_time < self.bar_open_time:
            raise ValueError("bar_close_time must be >= bar_open_time")
        return self


class TelemetryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    received_at: datetime
    event_id: str
    schema_version: str
    formula_version: str
    configuration_id: str
    symbol: str
    exchange: str
    timeframe: str
    bpm_mode: str
    bar_open_time: int
    bar_close_time: int
    confirmed_state: str
    confirmed_direction: str
    bo_status: str
    active_bo_price: float
    mc_status: str
    active_mc_price: float
    pressure_efficiency: float
    acceptance_status: str
    bes_scenario: str
