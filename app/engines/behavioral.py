from __future__ import annotations

from typing import Optional, Tuple

from app.engines.weights import HistoricalConfig
from app.models.evidence import EvidenceFactor, ScoreExplanation
from app.models.snapshot import BehavioralData, HistoricalStats

_STATE_MATURITY = {"Expansion": 85.0, "Negotiation": 55.0, "Compression": 40.0}
_ACCEPTANCE_STRENGTH = {"Strong": 95.0, "Moderate": 70.0, "Weak": 40.0, "Testing": 25.0, "Failed": 5.0}
_BO_CONFIRMATION = {"Confirmed": 100.0, "Confirming": 55.0, "Candidate": 30.0, "Rejected": 10.0, "NO_CYCLE": 0.0}
_MC_MATURITY = {"Locked": 90.0, "Provisional": 60.0, "None": 0.0}

_W_ACCEPTANCE = 0.22
_W_PRESSURE = 0.18
_W_STRUCTURE = 0.19
_W_FORECAST_RELIABILITY = 0.14
_W_STABILITY = 0.09
_W_TRANSITION_RISK = 0.08
_W_HISTORICAL_SIMILARITY = 0.10

_STABILITY_REFERENCE_BARS = 20.0
_TRANSITION_RISK_BASE = {"Expansion": 15.0, "Negotiation": 45.0, "Compression": 55.0}
_HISTORICAL_SIMILARITY_REFERENCE = 100.0


def _structure_value(data: BehavioralData) -> float:
    state_val = _STATE_MATURITY.get(data.confirmed_state, 50.0)
    bo_val = _BO_CONFIRMATION.get(data.bo_status, 20.0)
    mc_val = _MC_MATURITY.get(data.mc_status, 0.0)
    return 0.30 * state_val + 0.40 * bo_val + 0.30 * mc_val


def _forecast_reliability(
    data: BehavioralData, historical: Optional[HistoricalStats], historical_config: HistoricalConfig
) -> Tuple[float, str]:
    if not data.forecast_bias or data.forecast_bias == "Neutral":
        return 30.0, "No distinguishing forecast bias reported for this snapshot."
    sufficient = historical is not None and historical.occurrences >= historical_config.min_sample_size
    if not sufficient:
        occ = historical.occurrences if historical else 0
        return (
            25.0,
            f"Forecast bias '{data.forecast_bias}' is present but uncalibrated — only {occ} "
            f"historical occurrence(s) tracked against the {historical_config.min_sample_size}-sample minimum.",
        )
    depth_bonus = min(30.0, (historical.occurrences / (historical_config.min_sample_size * 4)) * 30.0)
    return (
        70.0 + depth_bonus,
        f"Forecast bias '{data.forecast_bias}' is backed by {historical.occurrences} tracked occurrences "
        f"(minimum required: {historical_config.min_sample_size}).",
    )


def _stability_value(data: BehavioralData) -> Tuple[float, str]:
    if data.bars_in_confirmed_state is None:
        return 40.0, "bars_in_confirmed_state not supplied — defaulting to a neutral-low value."
    value = min(100.0, (data.bars_in_confirmed_state / _STABILITY_REFERENCE_BARS) * 100.0)
    return value, f"Confirmed state has held for {data.bars_in_confirmed_state} bar(s)."


def _transition_risk_value(data: BehavioralData) -> Tuple[float, str]:
    base_risk = _TRANSITION_RISK_BASE.get(data.confirmed_state, 40.0)
    acceptance_penalty = {"Strong": -10.0, "Moderate": 0.0, "Weak": 10.0, "Testing": 15.0, "Failed": 20.0}
    risk = base_risk + acceptance_penalty.get(data.acceptance_status, 10.0)
    detail = f"Base risk for state '{data.confirmed_state}' adjusted for acceptance '{data.acceptance_status}'"
    if data.recent_transition_count is not None:
        risk += min(20.0, data.recent_transition_count * 4.0)
        detail += f" and {data.recent_transition_count} recent transition(s)"
    risk = max(0.0, min(100.0, risk))
    return 100.0 - risk, detail + f" — estimated risk {risk:.0f}/100 (displayed inverted)."


def _historical_similarity_value(historical: Optional[HistoricalStats]) -> Tuple[float, str]:
    if historical is None or historical.occurrences == 0:
        return 0.0, "No historical occurrences of this condition are tracked yet."
    value = min(100.0, (historical.occurrences / _HISTORICAL_SIMILARITY_REFERENCE) * 100.0)
    return value, f"{historical.occurrences} historically tracked occurrence(s) of this exact condition."


def score_behavioral(
    data: BehavioralData,
    historical: Optional[HistoricalStats] = None,
    historical_config: Optional[HistoricalConfig] = None,
) -> ScoreExplanation:
    historical_config = historical_config or HistoricalConfig()

    acceptance_val = _ACCEPTANCE_STRENGTH.get(data.acceptance_status, 30.0)
    pressure_val = max(0.0, min(100.0, data.pressure_efficiency))
    structure_val = _structure_value(data)
    forecast_val, forecast_note = _forecast_reliability(data, historical, historical_config)
    stability_val, stability_note = _stability_value(data)
    transition_val, transition_note = _transition_risk_value(data)
    similarity_val, similarity_note = _historical_similarity_value(historical)

    factors = [
        EvidenceFactor("Acceptance", round(acceptance_val, 1), _W_ACCEPTANCE,
                        f"Level acceptance status is '{data.acceptance_status}'.",
                        "Auction Market Theory", research_key="Acceptance"),
        EvidenceFactor("Pressure", round(pressure_val, 1), _W_PRESSURE,
                        "Directional commitment produced per unit of behavioral effort expended.",
                        "Market Microstructure", research_key="Pressure"),
        EvidenceFactor("Structure", round(structure_val, 1), _W_STRUCTURE,
                        f"Confirmed state '{data.confirmed_state}', BO {data.bo_status}, MC {data.mc_status}.",
                        "BPM Original", research_key="Structure"),
        EvidenceFactor("Forecast Reliability", round(forecast_val, 1), _W_FORECAST_RELIABILITY,
                        forecast_note, "Statistical Learning", research_key="Forecast Reliability"),
        EvidenceFactor("Behavioral Stability", round(stability_val, 1), _W_STABILITY,
                        stability_note, "Decision Science", research_key="Behavioral Stability"),
        EvidenceFactor("Transition Risk", round(transition_val, 1), _W_TRANSITION_RISK,
                        transition_note, "Behavioral Finance", research_key="Transition Risk"),
        EvidenceFactor("Historical Similarity", round(similarity_val, 1), _W_HISTORICAL_SIMILARITY,
                        similarity_note, "Probability Theory", research_key="Historical Similarity"),
    ]

    value = sum(f.value * f.weight for f in factors)

    lifecycle_conf = 0.3 + 0.7 * (_BO_CONFIRMATION.get(data.bo_status, 0.0) / 100.0) * (
        0.5 + 0.5 * (_MC_MATURITY.get(data.mc_status, 0.0) / 100.0)
    )
    optional_inputs_present = sum(
        1 for v in (data.forecast_bias, data.bars_in_confirmed_state, data.recent_transition_count, historical)
        if v is not None
    )
    data_completeness = 0.5 + 0.5 * (optional_inputs_present / 4.0)
    confidence = min(1.0, lifecycle_conf * 0.6 + data_completeness * 0.4)

    return ScoreExplanation(
        score_name="Behavior Score",
        value=round(value, 1),
        confidence=round(confidence, 2),
        methodology=(
            "Weighted blend of seven sub-factors: Acceptance (22%), Pressure "
            "(18%), Structure (19%), Forecast Reliability (14%), Behavioral "
            "Stability (9%), Transition Risk (8%, displayed inverted), and "
            "Historical Similarity (10%). Each factor has a Research Card "
            "(app/research.py)."
        ),
        contributing_factors=factors,
        is_original_to_bpm=True,
    )
