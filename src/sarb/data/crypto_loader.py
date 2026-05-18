from __future__ import annotations

import pandas as pd

from sarb.data.base import (
    MarketData,
    MissingValuePolicy,
    apply_missing_value_policy,
    build_prices_panel,
    clip_prices,
    iter_archive_csv_members,
    read_long_csv,
    symbol_from_member,
)
from sarb.types import MarketConfig

ANNUALIZATION_FACTOR = 24.0 * 365.0


def load_prices(config: MarketConfig) -> MarketData:
    settings = config.settings
    timestamp_column = settings["timestamp_column"]
    price_column = settings["price_column"]
    archive_subdir = settings.get("archive_subdir")
    missing_value_policy: MissingValuePolicy = settings.get("missing_value_policy", "preserve")

    series_by_symbol: dict[str, pd.Series] = {}
    for member, payload in iter_archive_csv_members(
        config.raw_archive,
        archive_subdir=archive_subdir,
    ):
        symbol = symbol_from_member(
            member,
            suffix_strip=settings.get("symbol_suffix_strip"),
        )
        series_by_symbol[symbol] = read_long_csv(
            payload,
            timestamp_column=timestamp_column,
            price_column=price_column,
        )

    prices = build_prices_panel(series_by_symbol)
    prices = clip_prices(prices, start=None, end=settings.get("end"))
    if settings.get("start") is not None:
        prices = prices.loc[prices.index >= pd.Timestamp(settings["start"])]

    prices = apply_missing_value_policy(
        prices,
        missing_value_policy,
        forward_fill_limit=settings.get("forward_fill_limit"),
    )

    metadata = {
        "market": config.market,
        "frequency": settings["frequency"],
        "annualization_factor": ANNUALIZATION_FACTOR,
        "price_field": price_column,
        "adjusted": bool(settings.get("adjusted", False)),
        "allow_partial_histories": bool(settings.get("allow_partial_histories", True)),
        "missing_value_policy": missing_value_policy,
        "symbols": list(prices.columns),
        "symbol_count": int(prices.shape[1]),
        "start": str(prices.index.min()),
        "end": str(prices.index.max()),
        "first_observation_by_symbol": {
            symbol: str(prices[symbol].first_valid_index())
            for symbol in prices.columns
            if prices[symbol].first_valid_index() is not None
        },
    }
    return MarketData(prices=prices, metadata=metadata)
