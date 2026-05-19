from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: float
    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float
    max_drawdown: float
    turnover: float
    number_of_trades: int
    average_holding_period: float
    hit_rate: float


def compute_equity_curve(strategy_returns: pd.Series) -> pd.Series:
    clean = strategy_returns.fillna(0.0)
    return (1.0 + clean).cumprod()


def compute_drawdown(equity_curve: pd.Series) -> pd.Series:
    running_max = equity_curve.cummax()
    return equity_curve / running_max - 1.0


def count_trades(execution_positions: pd.Series) -> int:
    changes = execution_positions.fillna(0.0).diff().fillna(0.0)
    return int((changes != 0.0).sum())


def average_holding_period(execution_positions: pd.Series) -> float:
    active = execution_positions.fillna(0.0) != 0.0
    if not active.any():
        return 0.0

    groups = (active != active.shift(fill_value=False)).cumsum()
    run_lengths = active.groupby(groups).sum()
    holding_lengths = run_lengths[run_lengths > 0]
    if holding_lengths.empty:
        return 0.0
    return float(holding_lengths.mean())


def hit_rate(strategy_returns: pd.Series, execution_positions: pd.Series) -> float:
    active = execution_positions.fillna(0.0) != 0.0
    active_returns = strategy_returns[active].dropna()
    if active_returns.empty:
        return 0.0
    return float((active_returns > 0.0).mean())


def compute_performance_metrics(
    strategy_returns: pd.Series,
    execution_positions: pd.Series,
    *,
    annualization_factor: float,
) -> PerformanceMetrics:
    clean = strategy_returns.dropna()
    if clean.empty:
        raise ValueError("strategy returns must not be empty")

    equity = compute_equity_curve(clean)
    total_return = float(equity.iloc[-1] - 1.0)
    periods = len(clean)
    annualized_return = float((1.0 + total_return) ** (annualization_factor / periods) - 1.0)
    annualized_volatility = float(clean.std(ddof=0) * np.sqrt(annualization_factor))
    sharpe_ratio = (
        0.0 if annualized_volatility == 0.0 else float(annualized_return / annualized_volatility)
    )
    drawdown = compute_drawdown(equity)
    turnover = float(execution_positions.fillna(0.0).diff().abs().fillna(0.0).sum() / periods)
    trades = count_trades(execution_positions)
    holding_period = average_holding_period(execution_positions)
    hit = hit_rate(clean, execution_positions)

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=float(drawdown.min()),
        turnover=turnover,
        number_of_trades=trades,
        average_holding_period=holding_period,
        hit_rate=hit,
    )
