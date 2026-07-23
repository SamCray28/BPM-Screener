"""Research Engine.

Every metric the screener produces should be traceable to: a plain
definition, the research field(s) it draws on (if any), how it's
actually calculated, what evidence currently backs it, how confident
that evidence should make you, and its known limitations. "Nothing
hidden" — including the parts that are weak.

Two honesty rules this module follows:

1. Research basis names established FIELDS and, where a specific
   theory is genuinely famous and uncontroversial, the researcher
   associated with it (e.g. Kahneman & Tversky's Prospect Theory,
   Kyle's model of market impact, Steidlmayer's Market Profile /
   Auction Market Theory). It does not fabricate specific empirical
   findings, sample sizes, or p-values — this codebase has no
   published-literature database attached, so it can't verify a
   citation's details, only name the field it's drawing on.
2. Metrics original to BPM (not drawn from an established field) are
   marked `is_original_to_bpm=True` and their research_basis says so
   explicitly, per Rule 3 in the BIS spec.

`evidence` fields here describe what evidence WOULD/DOES support the
metric and its current status in this build — they do not invent
backtest statistics. Once the Behavioral Database (app/db/) is
populated with real history, `evidence` should be replaced with an
actual computed statistic and its confidence interval.
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


# ---------------------------------------------------------------------------
# Behavior Score sub-factors
# ---------------------------------------------------------------------------

_register(ResearchCard(
    metric_name="Acceptance",
    definition=(
        "How firmly the market has established value at or through a given "
        "BPM Fibonacci level: measured by closes on the accepted side, "
        "successful retests, defense count, and time held."
    ),
    research_basis=["Auction Market Theory (Steidlmayer's Market Profile — value area acceptance/rejection)"],
    calculation=(
        "Rolling-window count of closes on the accepted side (3/6/10-bar "
        "windows) plus ATR-normalized penetration depth, per the level "
        "acceptance engine in BPM_v3.0.1.pine section 12 and the "
        "bpm-python receiver's acceptance_status field."
    ),
    evidence=(
        "Currently sourced live from Pine's confirmed acceptance_status "
        "string only (Strong/Moderate/Weak/Testing/Failed). No independent "
        "backtested win-rate-by-acceptance-tier statistic exists yet in "
        "this build — that requires the Behavioral Database to accumulate "
        "outcomes tagged by acceptance tier."
    ),
    confidence_notes="High confidence in the *measurement* (it's a direct rule-based read), low confidence in its predictive value until the Behavioral Database has enough tagged outcomes.",
    limitations="Acceptance strength describes present market behavior, not future behavior. It says nothing about what happens next on its own.",
    is_original_to_bpm=False,
))

_register(ResearchCard(
    metric_name="Pressure",
    definition="How much directional behavioral commitment was produced per unit of market effort expended.",
    research_basis=["Market Microstructure (price-impact/effort-vs-result framing, related to Kyle's (1985) model of informed trading and market impact)"],
    calculation=(
        "Weighted blend of directional efficiency, ATR efficiency, ribbon "
        "expansion, MACD acceleration, RSI deviation, body quality, volume, "
        "and a friction penalty — see BPM_v3.0.1.pine section 3 (Pressure "
        "Efficiency Engine)."
    ),
    evidence="Directly read from Pine's confirmed pressure_efficiency telemetry field. No independent validation study yet — same Behavioral Database gap as Acceptance.",
    confidence_notes="The formula's individual components are each independently well-established measurement techniques; the specific weighted blend combining them is BPM's own construction and has not itself been separately validated.",
    limitations="A high pressure reading describes effort efficiency at this moment, not durability — it does not by itself say whether that pressure will continue.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Structure",
    definition="How structurally mature the current behavioral cycle is: how confirmed the Behavioral Origin (BO) is, how developed Maximum Commitment (MC) is, and how mature the confirmed state itself is.",
    research_basis=["BPM's own Behavioral Origin / Maximum Commitment framework (an original construct, not drawn from prior literature)"],
    calculation="Weighted blend of confirmed-state maturity, BO confirmation status, and MC maturity (Confirmed/Locked scoring highest, Candidate/Provisional scoring lower, no cycle scoring zero).",
    evidence="Read directly from Pine's confirmed (non-repainting) bo_status/mc_status/confirmed_state fields — this is a structural read of the current chart, not a statistical claim.",
    confidence_notes="High confidence as a description of the current cycle's maturity; it says nothing on its own about whether this maturity level historically preceded favorable outcomes — that's the Historical Similarity factor's job.",
    limitations="A structurally mature cycle (Confirmed BO, Locked MC) can still fail; structure describes where the cycle is, not where it's going.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Forecast Reliability",
    definition="How much weight the current BPM forecast bias (Continuation/Compression/Negotiation/Neutral) deserves, given how much historical calibration actually backs it.",
    research_basis=["Statistical Learning / Probability Theory (calibration of a forecast against realized outcomes)"],
    calculation=(
        "A forecast bias with no historical sample behind it (below the "
        "configured minimum sample size) scores low regardless of which "
        "bias Pine reports; a forecast bias backed by a sufficient tracked "
        "sample scores higher, scaled by sample depth."
    ),
    evidence="No calibrated forecast-accuracy statistic exists in this build yet — Pine's own forecast engine explicitly outputs a diagnostic bias label, not a calibrated probability (see BPM_v3.0.1.pine section 13), and this factor is built to respect that same distinction rather than launder an uncalibrated label into a confident-looking number.",
    confidence_notes="Deliberately low until the Behavioral Database can show forecast_bias predicted realized outcomes at a rate better than chance, with a stated sample size.",
    limitations="This factor actively suppresses itself when uncalibrated — that's intentional, not a bug, per the BIS governing rule that insufficient evidence should produce lower confidence, not stronger conviction.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Behavioral Stability",
    definition="How long the current confirmed behavioral state has held without reverting, as a proxy for how settled (vs. volatile) the current behavioral read is.",
    research_basis=["Cognitive Psychology / Decision Science (state persistence as a proxy for reliability of a classification)"],
    calculation="Scaled from bars held in the current confirmed state (via BehavioralData.bars_in_confirmed_state), capped at a reference duration.",
    evidence="Requires bars_in_confirmed_state to be populated by the caller (e.g. from a running history in the Behavioral Database); defaults to a neutral-low value with reduced confidence when unavailable, rather than guessing.",
    confidence_notes="Confidence is capped at moderate even when the input is present, since duration-held is a weak proxy for true stability on its own.",
    limitations="A state that has held for a long time is not guaranteed to keep holding — this factor describes the past, not the future.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Transition Risk",
    definition="Estimated risk that the current confirmed behavioral state reverses in the near term, inverted so higher displayed value = lower risk (consistent with every other factor being higher-is-better).",
    research_basis=["Behavioral Finance / Decision Science (regime-change risk framing)"],
    calculation="Heuristic combination of current state (Negotiation/Compression carry more reversal risk than Expansion), acceptance weakness, and recent_transition_count when available; displayed as (100 - estimated risk).",
    evidence="Heuristic only — not yet validated against actual transition-frequency statistics. The Behavioral Database's BehavioralTransition table (app/db/models.py) is designed to eventually supply real transition-frequency evidence for this factor.",
    confidence_notes="Low-to-moderate. This is explicitly a heuristic placeholder, not a calibrated risk model, until real transition-frequency data exists.",
    limitations="Does not currently incorporate real transition-frequency statistics; will overstate confidence in stable-looking states if the true regime is more volatile than this snapshot suggests.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Historical Similarity",
    definition="How many historically tracked occurrences of this exact behavioral condition (state + direction + BES scenario) exist to draw on.",
    research_basis=["Statistical Learning / Probability Theory (sample size as a precondition for any inferential claim)"],
    calculation="Scaled from HistoricalStats.occurrences relative to a reference sample depth; zero when no historical provider data is available.",
    evidence="Directly reflects whatever the connected HistoricalStatsProvider returns. In this build that's app/providers/mock_provider.py's synthetic data — not real trade history.",
    confidence_notes="Confidence rises only with real sample size; a high occurrence count from mock data does not indicate real predictive power.",
    limitations="Similarity of the labeled condition does not guarantee similarity of underlying market dynamics — two occurrences of 'Expansion/Bullish/BES-2' are not identical situations.",
    is_original_to_bpm=True,
))

# ---------------------------------------------------------------------------
# Top-level scores
# ---------------------------------------------------------------------------

_register(ResearchCard(
    metric_name="Overall Behavioral Opportunity Score",
    definition="A single weighted blend of Behavior, Market Structure, Historical Confidence, Trend, and News Impact scores, used only to rank symbols relative to each other.",
    research_basis=["Portfolio Theory / Decision Science (combining independent evidence sources under uncertainty)"],
    calculation="Weighted sum of the five component scores (weights configurable via ScoringWeights); overall confidence blends weighted-average component confidence with the single lowest component confidence.",
    evidence="Purely a combination rule over the component scores above — carries no independent evidence beyond what each component already states.",
    confidence_notes="Bounded by its weakest well-weighted component by design — see app/engines/scoring.py.",
    limitations="A rank, not a probability of any specific outcome. Never treat the numeric value as a percentage likelihood of anything.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="Market Structure Score",
    definition="Composite of spread quality, relative volume, range expansion, VWAP relationship, and gap quality.",
    research_basis=["Market Microstructure", "Auction Market Theory"],
    calculation="See app/engines/market_structure.py for the exact weighted formula.",
    evidence="Computed directly from the live/mock market data snapshot; each sub-component is an established microstructure measurement, not a BPM invention.",
    confidence_notes="High when spread/relative-volume/VWAP data are all present; reduced otherwise.",
    limitations="Describes current execution conditions, not future price direction.",
    is_original_to_bpm=False,
))

_register(ResearchCard(
    metric_name="Liquidity Score",
    definition="Composite of average dollar volume, average share volume, and float size.",
    research_basis=["Market Microstructure"],
    calculation="See app/engines/liquidity.py.",
    evidence="Computed directly from market data; standard liquidity proxies.",
    confidence_notes="High when float data is available; moderate otherwise.",
    limitations="Liquidity can change abruptly around catalysts (earnings, news) faster than average-volume figures reflect.",
    is_original_to_bpm=False,
))

_register(ResearchCard(
    metric_name="Historical Confidence Score",
    definition="Composite of historical win rate, profit factor, and sample depth for the current behavioral condition, hard-gated by a minimum sample size.",
    research_basis=["Statistical Learning / Probability Theory", "Risk Management (profit factor, drawdown framing)"],
    calculation="See app/engines/historical.py — zeroed out entirely below the configured minimum sample size.",
    evidence="Directly reflects whatever HistoricalStatsProvider returns; in this build, synthetic mock data only.",
    confidence_notes="Explicitly zero below the sample threshold — this is the sharpest implementation of the BIS governing rule in the whole codebase.",
    limitations="A profit factor or win rate computed from a small or non-representative sample can look favorable purely by chance.",
    is_original_to_bpm=False,
))

_register(ResearchCard(
    metric_name="Trend Score",
    definition="Single-timeframe proxy for trend using price-vs-VWAP position and gap persistence.",
    research_basis=["Auction Market Theory", "Market Microstructure"],
    calculation="See app/engines/trend.py.",
    evidence="Computed directly from market data; deliberately confidence-capped at 0.35.",
    confidence_notes="Capped low by design — this is not multi-timeframe trend analysis, just a same-session proxy.",
    limitations="Says nothing about higher-timeframe trend alignment, persistence, maturity, or exhaustion, which the BIS spec calls for but this build does not yet have the data feeds to compute.",
    is_original_to_bpm=True,
))

_register(ResearchCard(
    metric_name="News Impact Score",
    definition="Relevance- and confidence-weighted average of recent news items' estimated behavioral impact.",
    research_basis=["Behavioral Finance (attention/sentiment effects on price)"],
    calculation="See app/engines/sentiment.py.",
    evidence="Computed from whatever NewsProvider returns; in this build, synthetic mock headlines only, not real news.",
    confidence_notes="Confidence scales with the relevance/confidence values a real news provider would supply — currently synthetic.",
    limitations="News supports the behavioral assessment; it must never override it, per the BIS spec's explicit instruction.",
    is_original_to_bpm=False,
))
