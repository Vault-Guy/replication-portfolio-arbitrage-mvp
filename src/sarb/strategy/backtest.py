from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sarb.strategy.metrics import PerformanceMetrics, compute_equity_curve, compute_performance_metrics
from sarb.strategy.signals import SignalConfig, generate_positions, shift_positions_for_execution
from sarb.strategy.spread import compute_spread, rolling_zscore


@dataclass(frozen=True)
class BacktestResult:
    spread: pd.Series
    zscore: pd.Series
    positions: pd.Series
    execution_positions: pd.Series
    spread_returns: pd.Series
    strategy_returns: pd.Series
    equity_curve: pd.Series
    metrics: PerformanceMetrics
    stop_loss_exits: int = 0
    time_stop_exits: int = 0


def compute_spread_returns(spread: pd.Series) -> pd.Series:
    returns = spread.diff()
    returns.name = "spread_return"
    return returns


def apply_transaction_costs(
    gross_returns: pd.Series,
    execution_positions: pd.Series,
    *,
    transaction_cost_bps: float,
    valid_observation: pd.Series | None = None,
) -> pd.Series:
    turnover = execution_positions.fillna(0.0).diff().abs().fillna(0.0)
    if valid_observation is not None:
        turnover = turnover.where(valid_observation, 0.0)
    cost_rate = transaction_cost_bps / 10_000.0
    net = gross_returns - turnover * cost_rate
    net.name = "strategy_return"
    return net


def run_spread_backtest(
    *,
    real_log_price: pd.Series,
    synthetic_log_price: pd.Series,
    config: SignalConfig,
    max_holding_period: int | None = None,
    stop_loss_z: float | None = None,
) -> BacktestResult:
    spread = compute_spread(real_log_price, synthetic_log_price)
    zscore = rolling_zscore(spread, config.zscore_lookback)
    positions, stop_loss_exits, time_stop_exits = generate_positions(
        zscore,
        entry_z=config.entry_z,
        exit_z=config.exit_z,
        max_holding_period=max_holding_period,
        stop_loss_z=stop_loss_z,
    )
    execution_positions = shift_positions_for_execution(positions, shift_bars=1)
    spread_returns = compute_spread_returns(spread)

    valid_observation = spread.notna() & spread_returns.notna()
    gross_returns = (execution_positions * spread_returns).where(valid_observation)

    strategy_returns = apply_transaction_costs(
        gross_returns,
        execution_positions,
        transaction_cost_bps=config.transaction_cost_bps,
        valid_observation=valid_observation,
    )

    equity_curve = compute_equity_curve(strategy_returns.fillna(0.0))
    metrics = compute_performance_metrics(
        strategy_returns.dropna(),
        execution_positions,
        annualization_factor=config.annualization_factor,
    )
    return BacktestResult(
        spread=spread,
        zscore=zscore,
        positions=positions,
        execution_positions=execution_positions,
        spread_returns=spread_returns,
        strategy_returns=strategy_returns,
        equity_curve=equity_curve,
        metrics=metrics,
        stop_loss_exits=stop_loss_exits,
        time_stop_exits=time_stop_exits,
    )
