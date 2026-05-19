import numpy as np
import pandas as pd
import pytest

from sarb.strategy.backtest import run_spread_backtest
from sarb.strategy.metrics import compute_performance_metrics
from sarb.strategy.signals import SignalConfig, generate_positions, shift_positions_for_execution
from sarb.strategy.spread import compute_spread, rolling_zscore


def _config(**overrides) -> SignalConfig:
    defaults = {
        "zscore_lookback": 3,
        "entry_z": 1.0,
        "exit_z": 0.25,
        "transaction_cost_bps": 5.0,
        "annualization_factor": 252.0,
    }
    defaults.update(overrides)
    return SignalConfig(**defaults)


def test_no_same_bar_execution():
    index = pd.date_range("2020-01-01", periods=8, freq="D")
    target = pd.Series(np.linspace(0.0, 0.7, len(index)), index=index)
    synthetic = pd.Series(np.linspace(0.0, 0.2, len(index)), index=index)
    result = run_spread_backtest(
        real_log_price=target,
        synthetic_log_price=synthetic,
        config=_config(),
    )
    shifted = shift_positions_for_execution(result.positions, shift_bars=1)
    pd.testing.assert_series_equal(
        result.execution_positions.dropna(),
        shifted.dropna(),
        check_names=False,
    )


def test_transaction_costs_reduce_returns():
    index = pd.date_range("2020-01-01", periods=12, freq="D")
    target = pd.Series(np.sin(np.linspace(0.0, 4.0, len(index))), index=index)
    synthetic = pd.Series(np.sin(np.linspace(0.0, 4.0, len(index))) * 0.5, index=index)

    no_cost = run_spread_backtest(
        real_log_price=target,
        synthetic_log_price=synthetic,
        config=_config(transaction_cost_bps=0.0),
    )
    with_cost = run_spread_backtest(
        real_log_price=target,
        synthetic_log_price=synthetic,
        config=_config(transaction_cost_bps=50.0),
    )
    assert with_cost.equity_curve.iloc[-1] <= no_cost.equity_curve.iloc[-1]


def test_annualization_factor_is_read_from_config():
    returns = pd.Series([0.01, -0.005, 0.008, 0.004], index=pd.date_range("2020-01-01", periods=4, freq="D"))
    positions = pd.Series([1.0, 1.0, -1.0, -1.0], index=returns.index)
    daily = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    hourly = compute_performance_metrics(returns, positions, annualization_factor=8760.0)
    assert hourly.annualized_volatility > daily.annualized_volatility


def test_missing_prices_do_not_create_artificial_trades():
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    target = pd.Series(np.linspace(0.0, 0.9, len(index)), index=index)
    synthetic = pd.Series(np.linspace(0.0, 0.3, len(index)), index=index)
    target.iloc[5] = np.nan

    result = run_spread_backtest(
        real_log_price=target,
        synthetic_log_price=synthetic,
        config=_config(zscore_lookback=2),
    )
    assert pd.isna(result.spread_returns.iloc[5])
    assert pd.isna(result.strategy_returns.iloc[5])
    assert result.positions.iloc[4] == result.positions.iloc[5]


def test_rolling_zscore_does_not_use_future_spreads():
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    spread = pd.Series(np.arange(10, dtype=float), index=index)
    baseline = rolling_zscore(spread, lookback=3)

    modified = spread.copy()
    modified.iloc[7:] = 1_000.0
    updated = rolling_zscore(modified, lookback=3)

    overlap = baseline.index[:7]
    pd.testing.assert_series_equal(baseline.loc[overlap], updated.loc[overlap])


def test_generate_positions_hysteresis():
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    zscore = pd.Series([2.0, 0.4, -2.0, -0.4], index=index)
    positions, _stop, _time = generate_positions(zscore, entry_z=1.0, exit_z=0.5)
    assert positions.tolist() == [-1.0, 0.0, 1.0, 0.0]


def test_compute_spread_matches_log_difference():
    index = pd.date_range("2020-01-01", periods=3, freq="D")
    target = pd.Series([1.0, 1.1, 1.2], index=index)
    synthetic = pd.Series([0.9, 1.0, 1.05], index=index)
    spread = compute_spread(target, synthetic)
    pd.testing.assert_series_equal(spread, target - synthetic, check_names=False)
