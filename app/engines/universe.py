from __future__ import annotations

from typing import List

from app.config import UniverseConfig
from app.models.snapshot import MarketData


def filter_universe(candidates: List[MarketData], config: UniverseConfig) -> List[MarketData]:
    accepted: List[MarketData] = []
    for md in candidates:
        if md.is_otc_or_pink_sheet:
            continue
        if config.exclude_leveraged_products and md.is_leveraged_product:
            continue
        if md.exchange not in config.allowed_exchanges:
            continue
        if md.last_price > config.max_share_price:
            continue
        if md.avg_daily_volume < config.min_avg_daily_volume:
            continue
        if md.avg_daily_dollar_volume < config.min_avg_daily_dollar_volume:
            continue
        if md.relative_volume is not None and md.relative_volume < config.min_relative_volume:
            continue
        accepted.append(md)
    return accepted
