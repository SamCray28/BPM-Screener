import unittest

from app.engines.universe import filter_universe
from app.engines.weights import UniverseConfig
from app.models.snapshot import MarketData


def _md(**overrides) -> MarketData:
    base = dict(
        symbol="TEST", exchange="NASDAQ", last_price=20.0, volume=1_000_000,
        avg_daily_volume=1_000_000, avg_daily_dollar_volume=20_000_000, relative_volume=1.5,
    )
    base.update(overrides)
    return MarketData(**base)


class TestUniverseFilter(unittest.TestCase):
    def test_qualifying_symbol_passes(self):
        result = filter_universe([_md()], UniverseConfig())
        self.assertEqual(len(result), 1)

    def test_price_over_max_excluded(self):
        result = filter_universe([_md(last_price=75.0)], UniverseConfig(max_share_price=50.0))
        self.assertEqual(result, [])

    def test_wrong_exchange_excluded(self):
        result = filter_universe([_md(exchange="OTC")], UniverseConfig())
        self.assertEqual(result, [])

    def test_halted_excluded_by_default(self):
        result = filter_universe([_md(halt_status="Halted")], UniverseConfig())
        self.assertEqual(result, [])

    def test_halted_included_when_configured_off(self):
        result = filter_universe([_md(halt_status="Halted")], UniverseConfig(exclude_halted=False))
        self.assertEqual(len(result), 1)

    def test_bankrupt_excluded(self):
        result = filter_universe([_md(is_bankrupt=True)], UniverseConfig())
        self.assertEqual(result, [])

    def test_otc_excluded(self):
        result = filter_universe([_md(is_otc_or_pink_sheet=True)], UniverseConfig())
        self.assertEqual(result, [])

    def test_low_relative_volume_excluded(self):
        result = filter_universe([_md(relative_volume=0.5)], UniverseConfig(min_relative_volume=1.0))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
