from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import pandas as pd

from sarb.strategy.ou import fit_ou_parameters, normalized_ou_signal
from sarb.strategy.pca import PCAFactorModel
from sarb.strategy.residuals import compute_residuals, cumulative_residual_state
from sarb.strategy.signals import apply_signal_shift, generate_ou_signals
from sarb.utils.validation import assert_no_future_rows


@dataclass(frozen=True)
class WalkForwardWindow:
    history: pd.DataFrame
    decision_index: pd.Timestamp


class RollingFitPipeline:
    """Market-agnostic walk-forward estimation and signal generation."""

    def __init__(
        self,
        *,
        pca_components: int,
        estimation_window: int,
        signal_shift: int,
        dt_per_year: float,
        thresholds: dict[str, float],
        standardize: bool = True,
    ) -> None:
        self.pca = PCAFactorModel(n_components=pca_components, standardize=standardize)
        self.estimation_window = estimation_window
        self.signal_shift = signal_shift
        self.dt_per_year = dt_per_year
        self.thresholds = thresholds

    def iter_windows(self, returns: pd.DataFrame) -> Iterator[WalkForwardWindow]:
        for end_idx in range(self.estimation_window, len(returns)):
            history = returns.iloc[end_idx - self.estimation_window : end_idx]
            decision_index = returns.index[end_idx - 1]
            yield WalkForwardWindow(history=history, decision_index=decision_index)

    def fit_window(self, window: WalkForwardWindow, asset: str, full_returns: pd.DataFrame) -> dict:
        assert_no_future_rows(window.history, as_of=window.decision_index)
        fit_history = window.history.iloc[:-1]
        if fit_history.empty:
            raise ValueError("history must contain at least two rows for walk-forward fitting")
        factor_returns, loadings = self.pca.fit_transform_window(fit_history)
        betas = loadings.loc[asset]
        asset_returns = full_returns.loc[window.history.index, asset]
        residual_increments = compute_residuals(asset_returns, factor_returns, betas)
        ou_params = fit_ou_parameters(residual_increments, dt_per_year=self.dt_per_year)
        state = float(cumulative_residual_state(residual_increments).iloc[-1])
        zscore = normalized_ou_signal(state, ou_params)
        raw_signal = generate_ou_signals(
            pd.Series([zscore], index=[window.decision_index]),
            open_long=self.thresholds["open_long"],
            open_short=self.thresholds["open_short"],
            close_long=self.thresholds["close_long"],
            close_short=self.thresholds["close_short"],
        )
        shifted = apply_signal_shift(raw_signal, shift_bars=self.signal_shift)
        return {
            "decision_index": window.decision_index,
            "zscore": zscore,
            "signal": int(shifted.fillna(0.0).iloc[0]),
            "ou_params": ou_params,
        }
