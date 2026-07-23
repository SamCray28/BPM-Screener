from __future__ import annotations

from typing import List, Optional

from app.config import HistoricalConfig, ScoringWeights, UniverseConfig
from app.engines.behavioral import score_behavioral
from app.engines.historical import score_historical
from app.engines.liquidity import score_liquidity
from app.engines.market_structure import score_market_structure
from app.engines.scoring import combine_overall_score
from app.engines.sentiment import score_sentiment
from app.engines.trend import score_trend
from app.engines.universe import filter_universe
from app.models.ranking import RankedSymbol
from app.models.snapshot import SymbolSnapshot, describe_insider_transaction
from app.providers.base import (
    BehavioralDataProvider,
    CorporateEventsProvider,
    HistoricalStatsProvider,
    MarketDataProvider,
    NewsProvider,
)
from app.safeguards import validate_ranked_symbol


def _condition_key(snapshot: SymbolSnapshot) -> str:
    b = snapshot.behavioral
    return f"{b.confirmed_state}|{b.confirmed_direction}|{b.bes_scenario}"


def build_ranking(
    market_provider: MarketDataProvider,
    behavioral_provider: BehavioralDataProvider,
    news_provider: NewsProvider,
    historical_provider: HistoricalStatsProvider,
    universe_config: UniverseConfig,
    historical_config: HistoricalConfig,
    scoring_weights: ScoringWeights,
    corporate_events_provider: Optional[CorporateEventsProvider] = None,
) -> List[RankedSymbol]:
    candidates = filter_universe(market_provider.get_universe(), universe_config)

    ranked: List[RankedSymbol] = []
    for md in candidates:
        behavioral = behavioral_provider.get_behavioral_data(md.symbol)
        if behavioral is None:
            continue  # no BPM behavioral read for this symbol — nothing to rank

        news = news_provider.get_news(md.symbol)
        snapshot = SymbolSnapshot(market=md, behavioral=behavioral, news=news)

        historical = historical_provider.get_historical_stats(md.symbol, _condition_key(snapshot))
        snapshot.historical = historical

        behavior_score = score_behavioral(behavioral, historical, historical_config)
        market_score = score_market_structure(md)
        liquidity_score = score_liquidity(md)
        historical_score = score_historical(historical, historical_config)
        trend_score = score_trend(md)
        sentiment_score = score_sentiment(news)

        overall = combine_overall_score(
            behavior_score, market_score, historical_score, trend_score, sentiment_score, scoring_weights,
        )

        expectancy_text = None
        sample_size = historical_score.sample_size
        if (
            historical
            and historical.occurrences >= historical_config.min_sample_size
            and historical.win_rate is not None
            and historical.avg_r is not None
        ):
            expectancy_text = (
                f"{historical.win_rate:.0%} historical win rate, avg R {historical.avg_r:.2f} "
                f"across {historical.occurrences} tracked occurrences of this behavioral condition."
            )

        capital_efficiency_text = (
            f"Spread {md.spread:.3f} vs price {md.last_price:.2f}; ATR {md.atr:.3f}."
            if md.spread and md.atr else "Insufficient market data for a capital efficiency estimate."
        )

        hold_duration_text = (
            f"~{historical.avg_hold_bars:.0f} bars historically for this condition."
            if historical and historical.avg_hold_bars else "No sample-supported hold duration available."
        )

        risks: List[str] = []
        if historical_score.sample_size is not None and historical_score.sample_size < historical_config.min_sample_size:
            risks.append(
                "Historical sample size is below the configured minimum — treat expectancy as unknown, not favorable."
            )
        if md.relative_volume is not None and md.relative_volume < 1.0:
            risks.append("Relative volume is below its own baseline, which can widen effective spread under size.")
        if any(n.estimated_behavioral_impact == "Conflicting" for n in news):
            risks.append("At least one recent news item conflicts with the current behavioral read.")

        corporate_evidence: List[str] = []
        if corporate_events_provider is not None:
            earnings = corporate_events_provider.get_earnings_events(md.symbol)
            if earnings:
                risks.append("A recent or upcoming earnings event was found — behavioral read may not persist through the event.")
                corporate_evidence.append(
                    f"Earnings: surprise {earnings[0].surprise_pct:+.1f}%, reaction {earnings[0].reaction_pct:+.1f}%."
                    if earnings[0].surprise_pct is not None and earnings[0].reaction_pct is not None
                    else "Recent earnings event on record."
                )
            insiders = corporate_events_provider.get_insider_transactions(md.symbol)
            for txn in insiders:
                # Neutral language deliberately — see describe_insider_transaction()
                # docstring for why this avoids the literal words buy/sell.
                corporate_evidence.append(describe_insider_transaction(txn))
            revisions = corporate_events_provider.get_analyst_revisions(md.symbol)
            for rev in revisions:
                if rev.action == "Downgrade":
                    risks.append(f"{rev.firm} issued a recent analyst downgrade.")
                corporate_evidence.append(f"{rev.firm}: {rev.action.lower()} action on record.")

        if not risks:
            risks.append("No elevated risk flags identified from current evidence; absence of flags is not a guarantee.")

        reasons = [
            f"{f.name}: {f.value:.1f} (weight {f.weight:.2f}) — {f.description}"
            for f in overall.contributing_factors
        ]

        supporting_evidence = [
            f"Behavioral: {behavioral.confirmed_state}/{behavioral.confirmed_direction}, "
            f"BO {behavioral.bo_status}, MC {behavioral.mc_status}, acceptance {behavioral.acceptance_status}.",
            f"Market structure score {market_score.value:.1f} (confidence {market_score.confidence:.2f}).",
            f"Liquidity score {liquidity_score.value:.1f} (confidence {liquidity_score.confidence:.2f}).",
        ]
        if historical_score.historical_support:
            supporting_evidence.append(historical_score.historical_support)
        supporting_evidence.extend(corporate_evidence)

        behavioral_context = (
            f"{behavioral.confirmed_state} state, {behavioral.confirmed_direction} direction, "
            f"currently in {behavioral.bes_scenario}, acceptance is {behavioral.acceptance_status}."
        )

        candidate = RankedSymbol(
            symbol=md.symbol,
            behavioral_opportunity_rank=0,  # assigned after sort, below
            overall_score=overall,
            sub_scores=[behavior_score, market_score, liquidity_score, historical_score, trend_score, sentiment_score],
            historical_expectancy=expectancy_text,
            supporting_evidence=supporting_evidence,
            confidence=overall.confidence,
            historical_sample_size=sample_size,
            capital_efficiency=capital_efficiency_text,
            estimated_hold_duration=hold_duration_text,
            behavioral_context=behavioral_context,
            primary_risks=risks,
            reasons_for_ranking=reasons,
        )
        validate_ranked_symbol(candidate)
        ranked.append(candidate)

    ranked.sort(key=lambda r: r.overall_score.value, reverse=True)
    for i, r in enumerate(ranked, start=1):
        r.behavioral_opportunity_rank = i

    return ranked
