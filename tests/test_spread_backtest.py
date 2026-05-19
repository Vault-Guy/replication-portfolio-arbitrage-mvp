import numpy as np
import pandas as pd
import pytest

from sarb.strategy.backtest import run_spread_backtest
from sarb.strategy.metrics import (
    average_holding_period,
    compute_equity_curve,
    compute_performance_metrics,
    count_trades,
)
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


# ---------------------------------------------------------------------------
# generate_positions — signal direction and lifecycle
# ---------------------------------------------------------------------------


def test_exit_z_zero_raises_value_error():
    """exit_z=0.0 is physically impossible (abs(z) < 0 never fires); must be rejected."""
    z = pd.Series([0.0, 2.0, 0.0], index=pd.date_range("2020-01-01", periods=3, freq="D"))
    with pytest.raises(ValueError, match="exit_z=0.0"):
        generate_positions(z, entry_z=1.0, exit_z=0.0)


def test_generate_positions_entry_direction():
    """z > +entry_z → short (-1); z < -entry_z → long (+1)."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    z = pd.Series([0.0, 2.5, 0.0, -2.5, 0.0], index=index)
    pos, _, _ = generate_positions(z, entry_z=2.0, exit_z=0.5)
    assert pos.iloc[1] == -1.0
    assert pos.iloc[3] == 1.0


def test_generate_positions_holds_in_deadband():
    """z in (exit_z, entry_z) neither opens nor closes a position."""
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    # Enter short, then z retreats into deadband [0.5, 2.0] — should stay short.
    z = pd.Series([0.0, 2.5, 1.8, 1.2, 0.6, 2.5], index=index)
    pos, _, _ = generate_positions(z, entry_z=2.0, exit_z=0.5)
    assert pos.iloc[1] == -1.0  # enter short
    assert pos.iloc[2] == -1.0  # deadband: hold
    assert pos.iloc[3] == -1.0  # deadband: hold
    assert pos.iloc[4] == -1.0  # deadband: hold
    assert pos.iloc[5] == -1.0  # new entry signal (same direction): still -1


def test_generate_positions_exits_below_exit_threshold():
    """Position closes when |z| falls below exit_z."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    z = pd.Series([0.0, 2.5, 1.0, 0.3, 2.5], index=index)
    pos, _, _ = generate_positions(z, entry_z=2.0, exit_z=0.5)
    assert pos.iloc[1] == -1.0  # enter short
    assert pos.iloc[2] == -1.0  # deadband: hold
    assert pos.iloc[3] == 0.0   # |0.3| < exit_z=0.5 → flat
    assert pos.iloc[4] == -1.0  # re-enter short


def test_generate_positions_holds_through_nan_zscore():
    """NaN z-score must not change the current position."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    z = pd.Series([0.0, 2.5, np.nan, np.nan, 0.3], index=index)
    pos, _, _ = generate_positions(z, entry_z=2.0, exit_z=0.5)
    assert pos.iloc[1] == -1.0  # enter short
    assert pos.iloc[2] == -1.0  # NaN: hold
    assert pos.iloc[3] == -1.0  # NaN: hold
    assert pos.iloc[4] == 0.0   # |0.3| < 0.5 → flat


def test_generate_positions_stop_loss_exits_adverse_move():
    """stop_loss_z closes a short position when z exceeds the stop level."""
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    z = pd.Series([0.0, 2.0, 5.0, 0.0], index=index)
    pos, stop_exits, _ = generate_positions(z, entry_z=1.5, exit_z=0.5, stop_loss_z=4.0)
    assert pos.iloc[1] == -1.0  # enter short
    assert pos.iloc[2] == 0.0   # z=5.0 > stop_loss_z=4.0 for short → stopped out
    assert stop_exits == 1


def test_generate_positions_max_holding_period_forces_exit():
    """Position is forcibly closed after max_holding_period bars."""
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    # z stays in deadband after entry so only time stop fires
    z = pd.Series([0.0, 2.5, 1.8, 1.5, 1.2], index=index)
    pos, _, time_exits = generate_positions(z, entry_z=2.0, exit_z=0.5, max_holding_period=2)
    assert pos.iloc[1] == -1.0  # enter (held=1)
    assert pos.iloc[2] == -1.0  # held=2, 2 > 2 is False → still in
    assert pos.iloc[3] == 0.0   # held=3, 3 > 2 → time stop fires
    assert time_exits == 1


# ---------------------------------------------------------------------------
# average_holding_period — key fix: direction flip = new period
# ---------------------------------------------------------------------------


def test_average_holding_period_flip_counted_as_new_period():
    """After fix: +1→-1 flip without going flat is two separate holding periods."""
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    pos = pd.Series([1.0, 1.0, 1.0, -1.0, -1.0, -1.0], index=index)
    # Expected: 2 periods × 3 bars each → mean = 3.0
    # Old (broken) code returned 6.0 (one continuous "active" run).
    assert average_holding_period(pos) == pytest.approx(3.0)


def test_average_holding_period_all_zeros_returns_zero():
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    pos = pd.Series([0.0] * 5, index=index)
    assert average_holding_period(pos) == 0.0


def test_average_holding_period_with_gaps_between_trades():
    """Normal (non-flip) strategy: gaps between trades are not counted."""
    index = pd.date_range("2020-01-01", periods=8, freq="D")
    # Two trades: 3-bar long, gap, 2-bar short
    pos = pd.Series([1.0, 1.0, 1.0, 0.0, 0.0, -1.0, -1.0, 0.0], index=index)
    # Expected: mean of [3, 2] = 2.5
    assert average_holding_period(pos) == pytest.approx(2.5)


def test_average_holding_period_consistent_with_total_active_bars():
    """n_periods × ahp == total active bars (invariant that was broken before the fix)."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    # Flip strategy: 3 bars long, flip to short 4 bars, flip to long 2 bars, flat 1 bar
    pos = pd.Series([1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0, 0.0], index=index)
    ahp = average_holding_period(pos)
    active_bars = int((pos != 0.0).sum())
    # Three direction periods: [3, 4, 2] → ahp = 3.0, active_bars = 9
    assert ahp == pytest.approx(3.0)
    assert 3 * ahp == pytest.approx(active_bars)


# ---------------------------------------------------------------------------
# Performance metrics — equity curve, drawdown, hit rate, total return
# ---------------------------------------------------------------------------


def test_equity_curve_starts_compounding_from_first_nonzero_return():
    returns = pd.Series([0.10, -0.05, 0.05])
    equity = compute_equity_curve(returns)
    assert equity.iloc[0] == pytest.approx(1.10)
    assert equity.iloc[1] == pytest.approx(1.10 * 0.95)
    assert equity.iloc[2] == pytest.approx(1.10 * 0.95 * 1.05)


def test_total_return_equals_equity_final_minus_one():
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    returns = pd.Series([0.02, -0.01, 0.03, -0.005, 0.01, -0.02], index=index)
    positions = pd.Series([1.0, 1.0, -1.0, -1.0, 1.0, 1.0], index=index)
    metrics = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    equity = compute_equity_curve(returns)
    assert metrics.total_return == pytest.approx(equity.iloc[-1] - 1.0)


def test_max_drawdown_is_non_positive():
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    returns = pd.Series([0.05, 0.03, -0.10, 0.02, -0.04, 0.01], index=index)
    positions = pd.Series([1.0] * 6, index=index)
    metrics = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    assert metrics.max_drawdown <= 0.0


def test_hit_rate_is_bounded_zero_to_one():
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    returns = pd.Series([0.01, -0.02, 0.03, -0.01, 0.02, -0.03], index=index)
    positions = pd.Series([1.0, -1.0, 1.0, -1.0, 1.0, -1.0], index=index)
    metrics = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    assert 0.0 <= metrics.hit_rate <= 1.0


def test_hit_rate_is_one_when_all_active_returns_positive():
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    returns = pd.Series([0.01, 0.02, 0.03, 0.04], index=index)
    positions = pd.Series([1.0, 1.0, 1.0, 1.0], index=index)
    metrics = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    assert metrics.hit_rate == pytest.approx(1.0)


def test_sharpe_is_zero_when_returns_are_constant():
    """Constant positive returns → zero volatility → Sharpe reported as 0.0."""
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    returns = pd.Series([0.01, 0.01, 0.01, 0.01], index=index)
    positions = pd.Series([1.0] * 4, index=index)
    metrics = compute_performance_metrics(returns, positions, annualization_factor=252.0)
    assert metrics.sharpe_ratio == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Backtest integration — end-to-end scenarios
# ---------------------------------------------------------------------------


def test_no_positions_equity_stays_flat():
    """entry_z so high it never fires → equity curve stays at 1.0."""
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    target = pd.Series(np.sin(np.linspace(0, 2, 10)), index=index)
    synthetic = pd.Series(np.zeros(10), index=index)
    result = run_spread_backtest(
        real_log_price=target,
        synthetic_log_price=synthetic,
        config=_config(entry_z=999.0, exit_z=0.5, transaction_cost_bps=0.0),
    )
    assert (result.positions == 0.0).all()
    assert result.equity_curve.iloc[-1] == pytest.approx(1.0, abs=1e-9)


def test_profitable_mean_reverting_spread():
    """Deterministic scenario: short entry on spike, profit on reversion.

    Baseline [-1.41, -0.71, 0, 0.71, 1.41] has mean=0, std=1 with ddof=0,
    so the spike value of 2.0 produces z=2.0 (> entry_z=1.5) and the
    reversion to 0.3 produces z=-0.40 (< exit_z=0.5).
    """
    index = pd.date_range("2020-01-01", periods=12, freq="D")
    vals = [-1.414, -0.707, 0.0, 0.707, 1.414, 2.0, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0]
    real_log = pd.Series(vals, index=index)
    synthetic_log = pd.Series(np.zeros(12), index=index)
    result = run_spread_backtest(
        real_log_price=real_log,
        synthetic_log_price=synthetic_log,
        config=_config(zscore_lookback=5, entry_z=1.5, exit_z=0.5, transaction_cost_bps=0.0),
    )
    # Signal fires at bar 5 (z=2.0); execution at bar 6 captures fall from 2.0→0.3.
    assert result.metrics.number_of_trades >= 1
    assert result.metrics.total_return > 0.0


def test_wrong_side_strategy_loses():
    """Long the spread when it trends against you → equity falls."""
    n = 20
    index = pd.date_range("2020-01-01", periods=n, freq="D")
    # Spread continuously rises: being long is profitable BUT we want to test
    # that the zscore entry logic correctly shorts a rising spread.
    # We force the position manually by creating a spread that rises after
    # a brief dip (which triggers a LONG entry), then keeps rising (loss for long).
    base = np.zeros(n)
    base[5:10] = np.linspace(0.0, -1.5, 5)   # dip → triggers long entry
    base[10:] = np.linspace(-1.5, 1.0, 10)   # rises back and overshoots (loss for long)
    real_log = pd.Series(base, index=index)
    synthetic_log = pd.Series(np.zeros(n), index=index)
    result = run_spread_backtest(
        real_log_price=real_log,
        synthetic_log_price=synthetic_log,
        config=_config(zscore_lookback=4, entry_z=1.2, exit_z=0.25, transaction_cost_bps=0.0),
    )
    # Long entered on the dip; spread then overshoots upward → loss
    assert result.metrics.max_drawdown < 0.0


def test_valid_zscore_grid_pairs_exclude_zero_exit():
    """Grid search EXIT_Z_VALUES must not include 0.0 and all pairs must satisfy exit < entry."""
    from itertools import product

    ENTRY_Z_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0]
    EXIT_Z_VALUES = [0.25, 0.5, 0.75, 1.0]

    valid_pairs = [
        (entry_z, exit_z)
        for entry_z, exit_z in product(ENTRY_Z_VALUES, EXIT_Z_VALUES)
        if exit_z < entry_z
    ]

    assert all(exit_z > 0.0 for _, exit_z in valid_pairs), "exit_z=0 must not appear in the grid"
    assert all(exit_z < entry_z for entry_z, exit_z in valid_pairs)

    # Verify every valid pair is accepted by generate_positions without error
    dummy_z = pd.Series([0.0, 0.0, 0.0])
    for entry_z, exit_z in valid_pairs:
        generate_positions(dummy_z, entry_z=entry_z, exit_z=exit_z)  # must not raise
