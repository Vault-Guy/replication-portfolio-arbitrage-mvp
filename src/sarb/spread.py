from __future__ import annotations

import pandas as pd


def compute_spread(
    real_log_price: pd.Series,
    synthetic_log_price: pd.Series,
) -> pd.Series:
    """Spread between target and synthetic replication in log-price space."""
    aligned = pd.concat(
        [real_log_price.rename("real"), synthetic_log_price.rename("synthetic")],
        axis=1,
    )
    spread = aligned["real"] - aligned["synthetic"]
    spread.name = "spread"
    return spread


def rolling_zscore(spread: pd.Series, lookback: int) -> pd.Series:
    """Causal z-score: at time t, mean and std use only prior spread values."""
    if lookback < 1:
        raise ValueError("lookback must be at least 1")

    history = spread.shift(1)
    rolling_mean = history.rolling(lookback, min_periods=lookback).mean()
    rolling_std = history.rolling(lookback, min_periods=lookback).std(ddof=0)
    zscore = (spread - rolling_mean) / rolling_std
    zscore.name = "zscore"
    return zscore
