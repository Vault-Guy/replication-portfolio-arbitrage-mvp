from __future__ import annotations

import pandas as pd


def generate_ou_signals(
    zscores: pd.Series,
    *,
    open_long: float,
    open_short: float,
    close_long: float,
    close_short: float,
) -> pd.Series:
    """Map normalized residual z-scores to {-1, 0, 1} position intents."""
    signals = pd.Series(0, index=zscores.index, dtype=int)
    signals = signals.mask(zscores < open_long, -1)
    signals = signals.mask(zscores > open_short, 1)
    signals = signals.mask((zscores > close_long) & (zscores < open_long), 0)
    signals = signals.mask((zscores < close_short) & (zscores > open_short), 0)
    return signals.fillna(0).astype(int)


def apply_signal_shift(signals: pd.Series, *, shift_bars: int) -> pd.Series:
    """Shift signals so bar t decisions are applied on bar t + shift_bars."""
    if shift_bars < 0:
        raise ValueError("shift_bars must be non-negative")
    return signals.shift(shift_bars)
