from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SignalConfig:
    zscore_lookback: int
    entry_z: float
    exit_z: float
    transaction_cost_bps: float
    annualization_factor: float


def generate_positions(
    zscore: pd.Series,
    *,
    entry_z: float,
    exit_z: float,
    max_holding_period: int | None = None,
    stop_loss_z: float | None = None,
) -> tuple[pd.Series, int, int]:
    """Mean-reversion positions on the spread with hysteresis and optional risk exits.

    Returns ``(positions, stop_loss_exits, time_stop_exits)``. Risk exits are counted when
    a bar ends with a forced flat due to max holding length or adverse z beyond ``stop_loss_z``.
    """
    if entry_z <= 0 or exit_z < 0:
        raise ValueError("entry_z must be positive and exit_z must be non-negative")
    if exit_z == 0.0:
        raise ValueError(
            "exit_z=0.0 is not supported: abs(value) < 0.0 is always False, so the "
            "position never exits. Use exit_z > 0 (e.g. 0.25) for partial mean-reversion "
            "exit, or remove exit_z=0.0 from the grid search parameter list."
        )
    if exit_z > entry_z:
        raise ValueError("exit_z must not exceed entry_z")

    positions = pd.Series(0.0, index=zscore.index, dtype=float)
    current = 0.0
    held = 0
    stop_exits = 0
    time_exits = 0
    for timestamp in zscore.index:
        value = zscore.loc[timestamp]
        if pd.isna(value):
            positions.loc[timestamp] = current
            continue
        if abs(value) < exit_z:
            current = 0.0
        elif value > entry_z:
            current = -1.0
        elif value < -entry_z:
            current = 1.0

        if current == 0.0:
            held = 0
        else:
            held += 1
            if max_holding_period is not None and held > max_holding_period:
                current = 0.0
                held = 0
                time_exits += 1

        if current != 0.0 and stop_loss_z is not None and not pd.isna(value):
            if current > 0.0 and value < -stop_loss_z:
                current = 0.0
                held = 0
                stop_exits += 1
            elif current < 0.0 and value > stop_loss_z:
                current = 0.0
                held = 0
                stop_exits += 1

        positions.loc[timestamp] = current
    positions.name = "position"
    return positions, stop_exits, time_exits


def shift_positions_for_execution(positions: pd.Series, *, shift_bars: int = 1) -> pd.Series:
    """Delay positions so bar t P&L does not use the same-bar signal."""
    if shift_bars < 1:
        raise ValueError("shift_bars must be at least 1")
    shifted = positions.shift(shift_bars)
    shifted.name = "execution_position"
    return shifted
