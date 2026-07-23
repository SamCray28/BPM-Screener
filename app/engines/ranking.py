from __future__ import annotations

from typing import List, Optional

from app.engines.behavioral import score_behavioral
from app.engines.capital_efficiency import score_capital_efficiency
from app.engines.confidence import score_confidence
from app.engines.historical import score_historical
from app.engines.liquidity import score_liquidity
from app.engines.multi_timeframe import score_multi_timeframe_trend
from app.engines.news_score import score_news
from app.engines.scoring import combine_opportunity_score
from app.engines.structure import score_structure
from app.engines.universe import filter_universe
from app.engines.weights import HistoricalConfig, OpportunityWeights, UniverseConfig
from app.models.ranking import RankedSymbol
from app.models.snapshot import MultiTimeframeSnapshot, SymbolSnapshot, TimeframeSeries, describe_insider_transaction
from app.providers.base import (
    BehavioralDataProvider,
    CorporateEventsProvider,
    HistoricalStatsProvider,
    MarketDataProvider,
    NewsProvider,
)
from app.safeguards import validate_ranked_symbol

_MTF_TIMEFRAMES = ["D", "240", "60", "15", "5", "1"]


def _condition_key(snapshot: SymbolSnapshot) -> str:
    b = snapshot.behavioral
    return f"{b.confirmed_state}|{b.confirmed_direction}|{b.bes_scenario}"


async def _fetch_multi_timeframe(market_provider: MarketDataProvider, symbol: str) -> Optional[MultiTimeframeSnapshot]:
    series_by_tf = {}
    for tf in _MTF_TIMEFRAMES:
        try:
            series: TimeframeSeries = await market_provider.get_bars(symbol, tf, limit=60)
            if series.bars:
                series_by_tf[tf] = series
        except Exception:  # noqa: BLE001 — a missing timeframe degrades the Trend Score, it must not abort ranking
            continue
    if not series_by_tf:
        return None
    return MultiTimeframeSnapshot(symbol=symbol, series_by_timeframe=series_by_tf)


async def build_ranking(
    market_provider: MarketDataProvider,
    behavioral_provider: BehavioralDataProvider,
    news_provider: NewsProvider,
    historical_provider: HistoricalStatsProvider,
    universe_config: UniverseConfig,
    historical_config: HistoricalConfig,
    opportunity_weights: OpportunityWeights,
    corporate_events_provider: Optional[CorporateEventsProvider] = None,
    fetch_multi_timeframe: bool = True,
) -> List[RankedSymbol]:
    candidates = filter_universe(await market_provider.get_universe(), universe_config)

    ranked: List[RankedSymbol] = []
    for md in candidates:
        behavioral = await behavioral_provider.get_behavioral_data(md.symbol)
        if behavioral is None:
            continue  # no confirmed BPM behavioral read for this symbol — nothing to rank

        news = await news_provider.get_news(md.symbol)
        snapshot = SymbolSnapshot(market=md, behavioral=behavioral, news=news)

        historical = await historical_provider.get_historical_stats(md.symbol, _condition_key(snapshot))
        snapshot.historical = historical

        mtf_snapshot = await _fetch_multi_timeframe(market_provider, md.symbol) if fetch_multi_timeframe else None
        snapshot.multi_timeframe = mtf_snapshot

        behavior_score = score_behavioral(behavioral, historical, historical_config)
        structure_score = score_structure(md)
        liquidity_score = score_liquidity(md)
        historical_score = score_historical(historical, historical_config)
        trend_score = score_multi_timeframe_trend(mtf_snapshot, behavioral.confirmed_direction)
        news_score = score_news(news)
        capital_efficiency_score = score_capital_efficiency(md)

        opportunity = combine_opportunity_score(
            behavior_score, structure_score, liquidity_score, historical_score, trend_score, news_score,
            opportunity_weights,
        )
        confidence_score = score_confidence(
            [behavior_score, structure_score, liquidity_score, historical_score, trend_score, news_score]
        )

        expectancy_text = None
        sample_size = historical_score.sample_size
        if (
            historical and historical.occurrences >= historical_config.min_sample_size
            and historical.win_rate is not None and historical.avg_r is not None
        ):
            expectancy_text = (
                f"{historical.win_rate:.0%} historical win rate, avg R {historical.avg_r:.2f} "
                f"across {historical.occurrences} tracked occurrences of this behavioral condition."
            )

        capital_efficiency_text = (
            f"Spread {md.spread:.3f} vs price {md.last_price:.2f}; ATR {md.atr:.3f} "
            f"(Capital Efficiency Score {capital_efficiency_score.value:.1f})."
            if md.spread and md.atr else "Insufficient market data for a capital efficiency estimate."
        )

        hold_duration_text = (
            f"~{historical.avg_hold_bars:.0f} bars historically for this condition."
            if historical and historical.avg_hold_bars else "No sample-supported hold duration available."
        )

        risks: List[str] = []
        if historical_score.sample_size is not None and historical_score.sample_size < historical_config.min_sample_size:
            risks.append("Historical sample size is below the configured minimum — treat expectancy as unknown, not favorable.")
        if md.relative_volume is not None and md.relative_volume < 1.0:
            risks.append("Relative volume is below its own baseline, which can widen effective spread under size.")
        if any(n.estimated_behavioral_impact == "Conflicting" for n in news):
            risks.append("At least one recent news item conflicts with the current behavioral read.")
        if md.halt_status not in (None, "Trading"):
            risks.append(f"Symbol halt status is currently reported as '{md.halt_status}'.")
        if trend_score.confidence < 0.3:
            risks.append("Trend Score has low confidence — insufficient multi-timeframe data was available.")

        corporate_evidence: List[str] = []
        if corporate_events_provider is not None:
            earnings = await corporate_events_provider.get_earnings_events(md.symbol)
            if earnings:
                risks.append("A recent or upcoming earnings event was found — behavioral read may not persist through the event.")
                e = earnings[0]
                corporate_evidence.append(
                    f"Earnings: surprise {e.surprise_pct:+.1f}%, reaction {e.reaction_pct:+.1f}%."
                    if e.surprise_pct is not None and e.reaction_pct is not None
                    else "Recent earnings event on record."
                )
            for txn in await corporate_events_provider.get_insider_transactions(md.symbol):
                corporate_evidence.append(describe_insider_transaction(txn))  # neutral language — see docstring
            for rev in await corporate_events_provider.get_analyst_revisions(md.symbol):
                if rev.action == "Downgrade":
                    risks.append(f"{rev.firm} issued a recent analyst downgrade.")
                corporate_evidence.append(f"{rev.firm}: {rev.action.lower()} action on record.")

        if not risks:
            risks.append("No elevated risk flags identified from current evidence; absence of flags is not a guarantee.")

        reasons = [
            f"{f.name}: {f.value:.1f} (weight {f.weight:.2f}) — {f.description}"
            for f in opportunity.contributing_factors
        ]
        supporting_evidence = [
            f"Behavioral: {behavioral.confirmed_state}/{behavioral.confirmed_direction}, "
            f"BO {behavioral.bo_status}, MC {behavioral.mc_status}, acceptance {behavioral.acceptance_status}.",
            f"Structure score {structure_score.value:.1f} (confidence {structure_score.confidence:.2f}).",
            f"Liquidity score {liquidity_score.value:.1f} (confidence {liquidity_score.confidence:.2f}).",
            f"Confidence Score {confidence_score.value:.1f} (evidence-quality meta-score, not part of the ranking blend).",
        ]
        if historical_score.historical_support:
            supporting_evidence.append(historical_score.historical_support)
        supporting_evidence.extend(corporate_evidence)

        news_headlines = [n.headline for n in news[:5]]

        candidate = RankedSymbol(
            rank=0,  # assigned after sort
            symbol=md.symbol,
            behavior_score=behavior_score,
            opportunity_score=opportunity,
            sub_scores=[structure_score, liquidity_score, historical_score, trend_score, news_score,
                        confidence_score, capital_efficiency_score],
            historical_expectancy=expectancy_text,
            confidence=opportunity.confidence,
            historical_sample_size=sample_size,
            behavior_state=behavioral.confirmed_state,
            acceptance=behavioral.acceptance_status,
            pressure=behavioral.pressure_efficiency,
            trend_summary=f"{trend_score.value:.1f}/100 (confidence {trend_score.confidence:.2f})",
            liquidity_summary=f"{liquidity_score.value:.1f}/100 (confidence {liquidity_score.confidence:.2f})",
            recent_news=news_headlines,
            estimated_hold_duration=hold_duration_text,
            capital_efficiency=capital_efficiency_text,
            primary_risks=risks,
            reasons_for_ranking=reasons,
            supporting_evidence=supporting_evidence,
        )
        validate_ranked_symbol(candidate)
        ranked.append(candidate)

    ranked.sort(key=lambda r: r.opportunity_score.value, reverse=True)
    for i, r in enumerate(ranked, start=1):
        r.rank = i

    return ranked
