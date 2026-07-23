"""Runs the full ranking pipeline against synthetic mock data end-to-end.
THIS USES NO REAL MARKET DATA, NEWS, OR CORPORATE EVENTS — see
app/providers/mock/mock_providers.py. Swap in real providers
(app/providers/factory.py, driven by *_PROVIDER env vars) once API
keys are configured.
"""
from __future__ import annotations

import asyncio

from app.engines.ranking import build_ranking
from app.engines.weights import HistoricalConfig, OpportunityWeights, UniverseConfig
from app.providers.mock.mock_providers import (
    MockBehavioralDataProvider,
    MockCorporateEventsProvider,
    MockHistoricalStatsProvider,
    MockMarketDataProvider,
    MockNewsProvider,
)
from app.research import get_research_card


async def main() -> None:
    ranking = await build_ranking(
        market_provider=MockMarketDataProvider(),
        behavioral_provider=MockBehavioralDataProvider(),
        news_provider=MockNewsProvider(),
        historical_provider=MockHistoricalStatsProvider(),
        universe_config=UniverseConfig(),
        historical_config=HistoricalConfig(min_sample_size=20),
        opportunity_weights=OpportunityWeights(),
        corporate_events_provider=MockCorporateEventsProvider(),
    )

    print("(SYNTHETIC MOCK DATA — not a real market scan)\n")
    print(f"{'Rank':<5}{'Symbol':<8}{'Opportunity':<12}{'Confidence':<12}Behavior State")
    print("-" * 90)
    for r in ranking:
        print(f"{r.rank:<5}{r.symbol:<8}{r.opportunity_score.value:<12.1f}{r.confidence:<12.2f}{r.behavior_state}")

    if not ranking:
        print("\nNo symbols passed the universe filter.")
        return

    top = ranking[0]
    print(f"\n--- Detail: {top.symbol} (Rank {top.rank}) ---")
    print(f"Opportunity Score: {top.opportunity_score.value} (confidence {top.opportunity_score.confidence})")
    print(f"Behavior Score: {top.behavior_score.value} (confidence {top.behavior_score.confidence})")

    print("\nBehavior Score sub-factors:")
    for f in top.behavior_score.contributing_factors:
        print(f"  {f.name:<24} {f.value:>6.1f}  (weight {f.weight:.0%})")

    print("\nAll component scores:")
    for s in top.sub_scores:
        print(f"  {s.score_name:<26} {s.value:>6.1f}  (confidence {s.confidence:.2f})")

    print("\nSupporting evidence:")
    for ev in top.supporting_evidence:
        print(f"  - {ev}")
    print("\nPrimary risks:")
    for risk in top.primary_risks:
        print(f"  - {risk}")

    print("\n--- Research Card: Behavioral Opportunity Score ---")
    card = get_research_card("Behavioral Opportunity Score")
    if card:
        print(f"Definition:  {card.definition}")
        print(f"Limitations: {card.limitations}")


if __name__ == "__main__":
    asyncio.run(main())
