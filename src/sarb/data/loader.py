from __future__ import annotations

from typing import Any

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


def load_prices(config: MarketConfig) -> MarketData:
    settings = config.settings
    timestamp_column = settings["timestamp_column"]
    price_column = settings["price_column"]
    archive_subdir = settings.get("archive_subdir")
    missing_value_policy: MissingValuePolicy = settings.get("missing_value_policy", "preserve")

    series_by_symbol: dict[str, pd.Series] = {}
    for member, payload in iter_archive_csv_members(config.raw_archive, archive_subdir=archive_subdir):
        symbol = symbol_from_member(
            member,
            prefix_strip=settings.get("symbol_prefix_strip"),
            suffix_strip=settings.get("symbol_suffix_strip"),
        )
        # Some sources embed extra info after a comma (e.g. "GMKN, 1D_abc"); keep only the ticker part.
        if "," in symbol:
            symbol = symbol.split(",", 1)[0].strip()
        series_by_symbol[symbol] = read_long_csv(
            payload,
            timestamp_column=timestamp_column,
            price_column=price_column,
        )

    prices = build_prices_panel(series_by_symbol)
    prices = clip_prices(prices, start=settings.get("start"), end=settings.get("end"))
    prices = apply_missing_value_policy(
        prices,
        missing_value_policy,
        forward_fill_limit=settings.get("forward_fill_limit"),
    )

    metadata: dict[str, Any] = {
        "market": config.market,
        "frequency": settings.get("frequency", "1D"),
        "annualization_factor": float(settings["annualization_factor"]),
        "price_field": price_column,
        "missing_value_policy": missing_value_policy,
        "allow_partial_histories": bool(settings.get("allow_partial_histories", True)),
        "symbols": list(prices.columns),
        "symbol_count": int(prices.shape[1]),
        "start": str(prices.index.min()),
        "end": str(prices.index.max()),
        "first_observation_by_symbol": {
            sym: str(prices[sym].first_valid_index())
            for sym in prices.columns
            if prices[sym].first_valid_index() is not None
        },
    }
    return MarketData(prices=prices, metadata=metadata)
