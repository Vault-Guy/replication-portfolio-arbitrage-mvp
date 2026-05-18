from __future__ import annotations

import pandas as pd


def align_price_panel(
    prices: pd.DataFrame,
    *,
    method: str = "inner",
) -> pd.DataFrame:
    """Align asset columns on a shared timestamp index."""
    if method not in {"inner", "outer"}:
        raise ValueError("method must be 'inner' or 'outer'")

    aligned = prices.sort_index()
    aligned.index = pd.DatetimeIndex(aligned.index)
    if method == "inner":
        aligned = aligned.dropna(how="any")
    return aligned


def drop_symbols_with_sparse_history(
    prices: pd.DataFrame,
    *,
    min_observations: int,
) -> pd.DataFrame:
    counts = prices.notna().sum(axis=0)
    keep = counts[counts >= min_observations].index
    return prices.loc[:, keep]


def forward_fill_prices(prices: pd.DataFrame, *, limit: int | None = None) -> pd.DataFrame:
    return prices.sort_index().ffill(limit=limit)


def mask_future_observations(prices: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    """Zero out observations strictly after as_of to guard walk-forward code paths."""
    masked = prices.copy()
    masked.loc[masked.index > as_of] = pd.NA
    return masked
