"""Research Engine — every metric gets a Definition / Research Basis /
Calculation / Evidence / Confidence Notes / Limitations card. Two
honesty rules: research basis names established fields (and, where
genuinely famous and uncontroversial, the associated researcher —
Kahneman & Tversky, Kyle, Steidlmayer) rather than fabricated specific
citations; and `evidence` describes the CURRENT status of what backs a
metric in this build, not invented backtest statistics. Metrics
original to BPM are marked `is_original_to_bpm=True` rather than
presented as established science.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ResearchCard:
    metric_name: str
    definition: str
    research_basis: List[str]
    calculation: str
    evidence: str
    confidence_notes: str
    limitations: str
    is_original_to_bpm: bool


_CARDS: Dict[str, ResearchCard] = {}


def _register(card: ResearchCard) -> None:
    _CARDS[card.metric_name] = card


def get_research_card(metric_name: str) -> Optional[ResearchCard]:
    return _CARDS.get(metric_name)


def all_research_cards() -> Dict[str, ResearchCard]:
    return dict(_CARDS)


# --- Behavior Score sub-factors -------------------------------------------

_register(ResearchCard(
    "Acceptance",
    "How firmly the market has established value at or through a BPM Fibonacci level: closes on the accepted side, successful retests, defense count, time held.",
    ["Auction Market Theory (Steidlmayer's Market Profile — value area acceptance/rejection)"],
    "Rolling-window count of closes on the accepted side (3/6/10-bar windows) plus ATR-normalized penetration depth (BPM_v3.0.1.pine section 12).",
    "Sourced live from Pine's confirmed acceptance_status field only. No independent backtested win-rate-by-tier statistic exists yet — requires the Behavioral Database to accumulate outcomes tagged by acceptance tier.",
    "High confidence in the measurement; low confidence in predictive value until the Behavioral Database has enough tagged outcomes.",
    "Describes present market behavior, not future behavior, on its own.",
    False,
))

_register(ResearchCard(
    "Pressure",
    "How much directional behavioral commitment was produced per unit of market effort expended.",
    ["Market Microstructure (effort-vs-result framing, related to Kyle's (1985) model of informed trading and market impact)"],
    "Weighted blend of directional efficiency, ATR efficiency, ribbon expansion, MACD acceleration, RSI deviation, body quality, volume, and a friction penalty (BPM_v3.0.1.pine section 3).",
    "Read directly from Pine's confirmed pressure_efficiency field. No independent validation study yet.",
    "Individual components are established measurement techniques; the specific weighted blend is BPM's own construction and unvalidated as a blend.",
    "Describes effort efficiency at this moment, not durability.",
    True,
))

_register(ResearchCard(
    "Structure",
    "How structurally mature the current behavioral cycle is: BO confirmation, MC maturity, confirmed-state maturity.",
    ["BPM's own Behavioral Origin / Maximum Commitment framework"],
    "Weighted blend of confirmed-state maturity, BO confirmation status, and MC maturity.",
    "Read directly from Pine's confirmed (non-repainting) bo_status/mc_status/confirmed_state fields.",
    "High confidence as a description of current cycle maturity; says nothing on its own about historical outcomes (see Historical Similarity).",
    "A structurally mature cycle can still fail.",
    True,
))

_register(ResearchCard(
    "Forecast Reliability",
    "How much weight the current BPM forecast bias deserves, given how much historical calibration backs it.",
    ["Statistical Learning / Probability Theory (calibration against realized outcomes)"],
    "A forecast bias below the minimum historical sample size scores low regardless of which bias is reported; scores rise with sample depth once sufficient.",
    "No calibrated forecast-accuracy statistic exists yet in this build — Pine's own forecast engine outputs a diagnostic bias label, not a calibrated probability, and this factor respects that distinction.",
    "Deliberately low until the Behavioral Database shows forecast_bias predicting realized outcomes better than chance, with a stated sample size.",
    "Actively suppresses itself when uncalibrated — intentional, not a bug.",
    True,
))

_register(ResearchCard(
    "Behavioral Stability",
    "How long the current confirmed state has held without reverting, as a proxy for how settled the current read is.",
    ["Cognitive Psychology / Decision Science (state persistence as a proxy for classification reliability)"],
    "Scaled from bars held in the current confirmed state, capped at a reference duration.",
    "Requires bars_in_confirmed_state to be populated from a running history; defaults to neutral-low with reduced confidence when absent.",
    "Capped at moderate even when present — duration-held is a weak proxy for true stability alone.",
    "A state that has held does not guarantee it keeps holding.",
    True,
))

_register(ResearchCard(
    "Transition Risk",
    "Estimated risk the current confirmed state reverses soon, inverted so higher displayed value = lower risk.",
    ["Behavioral Finance / Decision Science (regime-change risk framing)"],
    "Heuristic combining current state, acceptance weakness, and recent transition count when available; displayed as (100 - estimated risk).",
    "Heuristic only. app/models/db_models.py's BehavioralTransition table is designed to eventually supply real transition-frequency evidence.",
    "Low-to-moderate — an explicit placeholder, not a calibrated risk model.",
    "Does not yet incorporate real transition-frequency statistics.",
    True,
))

_register(ResearchCard(
    "Historical Similarity",
    "How many historically tracked occurrences of this exact behavioral condition exist to draw on.",
    ["Statistical Learning / Probability Theory (sample size as a precondition for inference)"],
    "Scaled from occurrence count relative to a reference sample depth; zero without historical data.",
    "Reflects whatever the connected HistoricalStatsProvider returns.",
    "Rises only with real sample size.",
    "Condition-label similarity does not guarantee similarity of underlying market dynamics.",
    True,
))

# --- Top-level scores -------------------------------------------------------

_register(ResearchCard(
    "Behavior Score",
    "Weighted blend of Acceptance, Pressure, Structure, Forecast Reliability, Behavioral Stability, Transition Risk, and Historical Similarity.",
    ["Composite — see each sub-factor's own card"],
    "See app/engines/behavioral.py for exact weights (22/18/19/14/9/8/10).",
    "Composite of the seven sub-factor evidence bases above.",
    "Bounded by data completeness across the optional, database-backed sub-factors.",
    "A behavioral-maturity read, not a probability of any outcome.",
    True,
))

_register(ResearchCard(
    "Structure Score",
    "Composite of spread quality, relative volume, range expansion, VWAP relationship, and gap quality.",
    ["Market Microstructure", "Auction Market Theory"],
    "See app/engines/structure.py.",
    "Computed directly from the live/mock market data snapshot.",
    "High when spread/relative-volume/VWAP data are all present.",
    "Describes current execution conditions, not future price direction.",
    False,
))

_register(ResearchCard(
    "Liquidity Score",
    "Composite of average dollar volume, average share volume, and float size.",
    ["Market Microstructure"],
    "See app/engines/liquidity.py.",
    "Computed directly from market data.",
    "High when float data is available.",
    "Can change abruptly around catalysts faster than average-volume figures reflect.",
    False,
))

_register(ResearchCard(
    "Historical Score",
    "Composite of historical win rate, profit factor, and sample depth, hard-gated by a minimum sample size.",
    ["Statistical Learning / Probability Theory", "Risk Management (profit factor, drawdown framing)"],
    "See app/engines/historical.py — zeroed entirely below the configured minimum sample size.",
    "Reflects whatever HistoricalStatsProvider returns.",
    "Explicitly zero below the sample threshold.",
    "A ratio from a small or unrepresentative sample can look favorable by chance.",
    False,
))

_register(ResearchCard(
    "Trend Score",
    "Multi-timeframe alignment, persistence, acceleration, and exhaustion across Daily/4H/1H/15m/5m/1m.",
    ["Auction Market Theory", "Market Microstructure"],
    "See app/engines/multi_timeframe.py.",
    "Computed from bar series per timeframe when the market data provider supplies them; falls back to a same-session VWAP/gap proxy with capped confidence when it doesn't.",
    "Confidence scales with how many timeframes actually have data.",
    "Alignment across timeframes describes current structure, not guaranteed continuation.",
    True,
))

_register(ResearchCard(
    "News Score",
    "Relevance-, confidence-, and source-reliability-weighted average of recent news items' estimated behavioral impact.",
    ["Behavioral Finance (attention/sentiment effects on price)"],
    "See app/engines/news_score.py.",
    "Computed from whatever NewsProvider returns.",
    "Scales with the relevance/confidence/reliability values the provider supplies.",
    "News supports the behavioral assessment; it must never override it.",
    False,
))

_register(ResearchCard(
    "Confidence Score",
    "A meta-score describing how much evidence backs the Behavioral Opportunity Score overall — not a component of that score, a description of it.",
    ["Decision Science (confidence-in-a-judgment as distinct from the judgment itself)"],
    "See app/engines/confidence.py — combines data completeness across every component score.",
    "Directly derived from the same component scores' own confidence values.",
    "By construction, cannot exceed the weakest well-weighted component's confidence.",
    "A high Confidence Score means the evidence is solid, not that the opportunity is good — those are different claims.",
    True,
))

_register(ResearchCard(
    "Capital Efficiency Score",
    "How much behavioral opportunity is available per unit of execution cost (spread, ATR-implied slippage).",
    ["Market Microstructure", "Portfolio Theory (risk-adjusted capital allocation framing)"],
    "See app/engines/capital_efficiency.py.",
    "Computed directly from spread and ATR in the market data snapshot.",
    "High when spread/ATR data are both present.",
    "Says nothing about position sizing or portfolio-level risk — that remains the user's decision.",
    True,
))

_register(ResearchCard(
    "Behavioral Opportunity Score",
    "A single weighted blend of Behavior, Structure, Liquidity, Historical, Trend, and News scores, used only to rank symbols relative to each other.",
    ["Portfolio Theory / Decision Science (combining independent evidence sources under uncertainty)"],
    "Weighted sum of component scores; overall confidence blends weighted-average component confidence with the lowest single component confidence.",
    "Purely a combination rule — carries no independent evidence beyond its components.",
    "Bounded by its weakest well-weighted component by design.",
    "A rank, not a probability of any specific outcome. Never a percentage likelihood of anything.",
    True,
))
