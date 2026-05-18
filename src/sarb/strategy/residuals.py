from __future__ import annotations

import pandas as pd


def compute_residuals(
    asset_returns: pd.Series,
    factor_returns: pd.DataFrame,
    betas: pd.Series,
    *,
    alpha: float = 0.0,
) -> pd.Series:
    """Idiosyncratic return increments dI_t from a multi-factor replication."""
    explained = alpha + factor_returns.mul(betas, axis=1).sum(axis=1)
    return asset_returns - explained


def cumulative_residual_state(residual_increments: pd.Series) -> pd.Series:
    return residual_increments.cumsum()
