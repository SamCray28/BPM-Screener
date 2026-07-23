"""Pydantic response schemas mirroring app/models/evidence.py and
app/models/ranking.py, so /openapi.json documents real, validated
response shapes rather than opaque dicts."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel

from app.models.evidence import ScoreExplanation
from app.models.ranking import RankedSymbol


class EvidenceFactorOut(BaseModel):
    name: str
    value: float
    weight: float
    description: str
    source: str
    research_key: Optional[str] = None


class ScoreExplanationOut(BaseModel):
    score_name: str
    value: float
    confidence: float
    methodology: str
    contributing_factors: List[EvidenceFactorOut]
    sample_size: Optional[int] = None
    historical_support: Optional[str] = None
    is_original_to_bpm: bool = False


def score_to_api(score: ScoreExplanation) -> ScoreExplanationOut:
    return ScoreExplanationOut(
        score_name=score.score_name, value=score.value, confidence=score.confidence,
        methodology=score.methodology,
        contributing_factors=[
            EvidenceFactorOut(name=f.name, value=f.value, weight=f.weight, description=f.description,
                               source=f.source, research_key=f.research_key)
            for f in score.contributing_factors
        ],
        sample_size=score.sample_size, historical_support=score.historical_support,
        is_original_to_bpm=score.is_original_to_bpm,
    )


class RankedSymbolOut(BaseModel):
    rank: int
    symbol: str
    behavior_score: ScoreExplanationOut
    opportunity_score: ScoreExplanationOut
    sub_scores: List[ScoreExplanationOut]
    historical_expectancy: Optional[str]
    confidence: float
    historical_sample_size: Optional[int]
    behavior_state: str
    acceptance: str
    pressure: float
    trend_summary: str
    liquidity_summary: str
    recent_news: List[str]
    estimated_hold_duration: Optional[str]
    capital_efficiency: Optional[str]
    primary_risks: List[str]
    reasons_for_ranking: List[str]
    supporting_evidence: List[str]


def ranked_symbol_to_api(ranked: RankedSymbol) -> RankedSymbolOut:
    return RankedSymbolOut(
        rank=ranked.rank, symbol=ranked.symbol,
        behavior_score=score_to_api(ranked.behavior_score),
        opportunity_score=score_to_api(ranked.opportunity_score),
        sub_scores=[score_to_api(s) for s in ranked.sub_scores],
        historical_expectancy=ranked.historical_expectancy, confidence=ranked.confidence,
        historical_sample_size=ranked.historical_sample_size, behavior_state=ranked.behavior_state,
        acceptance=ranked.acceptance, pressure=ranked.pressure, trend_summary=ranked.trend_summary,
        liquidity_summary=ranked.liquidity_summary, recent_news=ranked.recent_news,
        estimated_hold_duration=ranked.estimated_hold_duration, capital_efficiency=ranked.capital_efficiency,
        primary_risks=ranked.primary_risks, reasons_for_ranking=ranked.reasons_for_ranking,
        supporting_evidence=ranked.supporting_evidence,
    )


class ResearchCardOut(BaseModel):
    metric_name: str
    definition: str
    research_basis: List[str]
    calculation: str
    evidence: str
    confidence_notes: str
    limitations: str
    is_original_to_bpm: bool


class HealthOut(BaseModel):
    status: str
    app_name: str
    app_version: str
    app_env: str
