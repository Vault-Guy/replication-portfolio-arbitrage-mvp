from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OUParameters:
    kappa: float
    mu: float
    sigma: float
    phi0: float
    phi1: float


def fit_ou_parameters(
    residual_increments: pd.Series,
    *,
    dt_per_year: float = 252.0,
) -> OUParameters:
    """Estimate OU parameters from residual increments via AR(1) on cumulative state."""
    state = residual_increments.cumsum()
    lagged = state.shift(1)
    aligned = pd.concat([state, lagged], axis=1, keys=["current", "lag"]).dropna()
    if len(aligned) < 3:
        raise ValueError("not enough observations to fit OU parameters")

    y = aligned["current"].to_numpy(dtype=float)
    x = aligned["lag"].to_numpy(dtype=float)
    design = np.column_stack([np.ones_like(x), x])
    phi0, phi1 = np.linalg.lstsq(design, y, rcond=None)[0]

    fitted = design @ np.array([phi0, phi1])
    innovation_var = float(np.var(y - fitted, ddof=1))
    dt = 1.0 / dt_per_year
    kappa = max(-np.log(phi1) * dt_per_year, 0.0) if 0.0 < phi1 < 1.0 else 0.0
    mu = phi0 / (1.0 - phi1) if phi1 != 1.0 else float(np.mean(y))
    sigma = np.sqrt(max(innovation_var * 2.0 * kappa / (1.0 - phi1**2), 0.0)) if phi1 != 1.0 else 0.0
    return OUParameters(kappa=kappa, mu=mu, sigma=sigma, phi0=float(phi0), phi1=float(phi1))


def normalized_ou_signal(state: float, params: OUParameters) -> float:
    denom = np.sqrt(max(params.sigma**2 / (2.0 * params.kappa), 1e-12)) if params.kappa > 0 else 1.0
    return (state - params.mu) / denom
