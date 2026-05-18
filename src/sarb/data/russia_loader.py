from __future__ import annotations

import pandas as pd

from sarb.data.base import (
    MarketData,
    build_prices_panel,
    clip_prices,
    iter_archive_csv_members,
    read_long_csv,
    symbol_from_member,
)
from sarb.types import MarketConfig

ANNUALIZATION_FACTOR = 252.0


def load_prices(config: MarketConfig) -> MarketData:
    settings = config.settings
    timestamp_column = settings["timestamp_column"]
    price_column = settings["price_column"]
    archive_subdir = settings.get("archive_subdir")

    series_by_symbol: dict[str, pd.Series] = {}
    for member, payload in iter_archive_csv_members(
        config.raw_archive,
        archive_subdir=archive_subdir,
    ):
        symbol = symbol_from_member(
            member,
            prefix_strip=settings.get("symbol_prefix_strip"),
            suffix_strip=settings.get("symbol_suffix_strip"),
        )
        if "," in symbol:
            symbol = symbol.split(",", 1)[0].strip()
        series_by_symbol[symbol] = read_long_csv(
            payload,
            timestamp_column=timestamp_column,
            price_column=price_column,
        )

    prices = build_prices_panel(series_by_symbol)
    prices = clip_prices(
        prices,
        start=settings.get("start"),
        end=settings.get("end"),
    )

    metadata = {
        "market": config.market,
        "frequency": settings.get("frequency", "1D"),
        "annualization_factor": ANNUALIZATION_FACTOR,
        "price_field": price_column,
        "symbols": list(prices.columns),
        "symbol_count": int(prices.shape[1]),
        "start": str(prices.index.min()),
        "end": str(prices.index.max()),
    }
    return MarketData(prices=prices, metadata=metadata)
