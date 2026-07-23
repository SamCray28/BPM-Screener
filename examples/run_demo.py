"""Runs the full BIS pipeline against synthetic mock data end-to-end and
prints the ranked output.

THIS USES NO REAL MARKET DATA, NEWS, OR TRADE HISTORY — see
app/providers/mock_provider.py. Swap in real provider implementations
(app/providers/base.py) to go from demo to production.
"""
from __future__ import annotations

from app.config import HistoricalConfig, ScoringWeights, UniverseConfig
from app.engines.ranking import build_ranking
from app.research import get_research_card
from app.providers.mock_provider import (
    MockBehavioralDataProvider,
    MockCorporateEventsProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
)


def main() -> None:
    ranking = build_ranking(
        market_provider=MockMarketDataProvider(),
        behavioral_provider=MockBehavioralDataProvider(),
        news_provider=MockNewsProvider(),
        historical_provider=MockHistoricalStatsProvider(),
        universe_config=UniverseConfig(),
        historical_config=HistoricalConfig(min_sample_size=20),
        scoring_weights=ScoringWeights(),
        corporate_events_provider=MockCorporateEventsProvider(),
    )

    print("(SYNTHETIC MOCK DATA — not a real market screen)\n")
    print(f"{'Rank':<5}{'Symbol':<8}{'Overall':<10}{'Confidence':<12}Behavioral Context")
    print("-" * 100)
    for r in ranking:
        print(
            f"{r.behavioral_opportunity_rank:<5}{r.symbol:<8}{r.overall_score.value:<10.1f}"
            f"{r.confidence:<12.2f}{r.behavioral_context}"
        )

    if not ranking:
        print("\nNo symbols passed the universe filter.")
        return

    top = ranking[0]
    print("\n--- Detail for top-ranked symbol ---")
    print(f"Symbol: {top.symbol}  (Rank {top.behavioral_opportunity_rank})")
    print(f"Overall score: {top.overall_score.value} (confidence {top.overall_score.confidence})")
    print("\nReasons for ranking:")
    for reason in top.reasons_for_ranking:
        print(f"  - {reason}")
    print("\nSupporting evidence:")
    for ev in top.supporting_evidence:
        print(f"  - {ev}")
    print("\nPrimary risks:")
    for risk in top.primary_risks:
        print(f"  - {risk}")
    print(f"\nHistorical expectancy: {top.historical_expectancy}")
    print(f"Capital efficiency: {top.capital_efficiency}")
    print(f"Estimated hold duration: {top.estimated_hold_duration}")

    print("\n--- Behavior Score sub-factor breakdown (top symbol) ---")
    behavior_score = next(s for s in top.sub_scores if s.score_name == "Behavior Score")
    for f in behavior_score.contributing_factors:
        print(f"  {f.name:<24} {f.value:>6.1f}  (weight {f.weight:.0%})  {f.description}")

    print("\n--- Research Card example: Pressure ---")
    card = get_research_card("Pressure")
    if card:
        print(f"Definition:       {card.definition}")
        print(f"Research basis:   {', '.join(card.research_basis)}")
        print(f"Calculation:      {card.calculation}")
        print(f"Evidence:         {card.evidence}")
        print(f"Confidence notes: {card.confidence_notes}")
        print(f"Limitations:      {card.limitations}")
        print(f"Original to BPM:  {card.is_original_to_bpm}")


if __name__ == "__main__":
    main()
