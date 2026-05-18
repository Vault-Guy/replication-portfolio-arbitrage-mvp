from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sarb.pca_replication import PCAReplicationConfig, replicate_segment, to_log_prices
from sarb.pipeline import iter_rebalance_starts
from sarb.run import RunConfig, run_unified_pipeline
from sarb.signals import generate_positions
from sarb.universe import (
    CRYPTO_EXCLUDED_TOKENS,
    normalize_ticker_for_comparison,
    select_crypto_coverage_universe,
    strip_universe_of_target_equivalents,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CRYPTO_ZIP = PROJECT_ROOT / "data" / "raw" / "crypto_data.zip"


def test_crypto_grid_dry_run_cli() -> None:
    script = PROJECT_ROOT / "scripts" / "crypto_parameter_grid.py"
    proc = subprocess.run(
        [sys.executable, "-u", str(script), "--stage", "core", "--target", "all", "--dry-run"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Dry run" in proc.stdout


def test_target_excluded_from_universe_strings() -> None:
    u = ["BTC", "ETH", "SOL"]
    assert strip_universe_of_target_equivalents(u, "SOL") == ["BTC", "ETH"]


def test_stablecoins_not_in_coverage_universe() -> None:
    cols = ["BTC", "ETH", "USDT", "ADA"]
    idx = pd.date_range("2020-01-01", periods=50, freq="h")
    rng = np.random.default_rng(0)
    prices = pd.DataFrame(
        {c: np.exp(np.cumsum(rng.normal(0, 0.01, size=len(idx)))) for c in cols},
        index=idx,
    )
    cov = pd.DataFrame(
        {
            "symbol": cols,
            "observations": [50, 50, 50, 50],
            "missing_pct": [0.0, 0.0, 0.0, 0.0],
        }
    )
    res = select_crypto_coverage_universe(cols, "BTC", requested_size=3, coverage=cov)
    keys = {normalize_ticker_for_comparison(x) for x in res.assets}
    assert normalize_ticker_for_comparison("USDT") not in keys
    assert "BTC" not in res.assets


@pytest.mark.skipif(not CRYPTO_ZIP.is_file(), reason="crypto_data.zip not present")
def test_crypto_max_runs_small_smoke() -> None:
    script = PROJECT_ROOT / "scripts" / "crypto_parameter_grid.py"
    proc = subprocess.run(
        [sys.executable, "-u", str(script), "--stage", "core", "--target", "SOL", "--max-runs", "1"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    partial = PROJECT_ROOT / "results" / "crypto_parameter_grid" / "partial_results.csv"
    assert partial.is_file()


def test_partial_results_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.crypto_parameter_grid as cpg

    monkeypatch.setattr(cpg, "OUT_DIR", tmp_path)
    monkeypatch.setattr(cpg, "PARTIAL_RESULTS", tmp_path / "partial_results.csv")
    row = {c: None for c in cpg.RESULT_COLUMNS}
    row.update(
        {
            "fingerprint": "test-fp",
            "stage": "core",
            "market": "crypto",
            "target": "BTC",
            "universe_selection_method": "priority",
            "universe_size_requested": 2,
            "universe_size_actual": 2,
            "universe_assets": "ETH,SOL",
            "missing_priority_assets": "",
            "filled_from_fallback": "",
            "train_window": 100,
            "rebalance_frequency": 24,
            "pca_explained_variance": 0.8,
            "pca_component_selection_method": "explained_variance",
            "fixed_n_components": float("nan"),
            "zscore_lookback": 50,
            "entry_z": 2.0,
            "exit_z": 0.25,
            "transaction_cost_bps": 10.0,
            "annualization_factor": 8760.0,
            "min_asset_coverage": 0.6,
            "min_universe_assets": 5,
            "min_train_observations": 50,
            "valid_rebalance_windows": 1,
            "skipped_rebalance_windows": 0,
            "valid_rebalance_share": 1.0,
            "max_holding_period": None,
            "stop_loss_z": None,
            "stop_loss_exits": 0,
            "time_stop_exits": 0,
            "regression_type": "OLS",
            "ridge_alpha": float("nan"),
            "total_return": 0.1,
            "annualized_return": 0.05,
            "annualized_volatility": 0.2,
            "sharpe_ratio": 0.5,
            "max_drawdown": -0.1,
            "turnover": 0.01,
            "number_of_trades": 20,
            "average_holding_period": 5.0,
            "hit_rate": 0.5,
        }
    )
    cpg._append_row(cpg.PARTIAL_RESULTS, row, cpg.RESULT_COLUMNS)
    df = pd.read_csv(cpg.PARTIAL_RESULTS)
    assert len(df) == 1
    assert df.loc[0, "sharpe_ratio"] == 0.5


def test_late_listed_asset_pipeline_does_not_crash() -> None:
    idx = pd.date_range("2020-01-01", periods=400, freq="h")
    rng = np.random.default_rng(1)
    btc = np.exp(np.cumsum(rng.normal(0, 0.002, size=len(idx))))
    eth = np.exp(np.cumsum(rng.normal(0, 0.002, size=len(idx))))
    sol = btc.copy()
    sol[:280] = np.nan
    prices = pd.DataFrame({"BTC": btc, "ETH": eth, "SOL": sol}, index=idx)
    base = RunConfig(
        market="crypto",
        frequency="1H",
        annualization_factor=8760.0,
        train_window=120,
        rebalance_frequency=24,
        pca_explained_variance=0.85,
        zscore_lookback=48,
        entry_z=2.0,
        exit_z=0.5,
        transaction_cost_bps=10.0,
    )
    out = run_unified_pipeline(
        prices,
        target="SOL",
        universe=["BTC", "ETH"],
        run_config=base,
        min_asset_coverage=0.50,
        min_universe_assets=2,
        min_train_observations=40,
    )
    assert out.replication.diagnostics["valid_rebalance_windows"] >= 1


def test_skipped_rebalance_windows_not_fatal() -> None:
    idx = pd.date_range("2020-01-01", periods=200, freq="h")
    rng = np.random.default_rng(2)
    prices = pd.DataFrame(
        {
            "A0": np.exp(np.cumsum(rng.normal(0, 0.01, size=len(idx)))),
            "A1": np.exp(np.cumsum(rng.normal(0, 0.01, size=len(idx)))),
            "A2": np.exp(np.cumsum(rng.normal(0, 0.01, size=len(idx)))),
            "A3": np.exp(np.cumsum(rng.normal(0, 0.01, size=len(idx)))),
        },
        index=idx,
    )
    logp = to_log_prices(prices)
    cfg = PCAReplicationConfig(
        train_window=80,
        rebalance_frequency=10,
        pca_explained_variance=0.90,
        min_train_observations=80,
        min_universe_assets=3,
        min_asset_coverage=0.80,
        market="usa",
    )
    starts = iter_rebalance_starts(logp.index, cfg)
    assert len(starts) > 1
    skipped = 0
    ok = 0
    for start_idx in starts:
        train = logp.iloc[start_idx - cfg.train_window : start_idx]
        oos = logp.iloc[start_idx : start_idx + 5]
        _seg, meta = replicate_segment(
            train,
            oos,
            target="A0",
            universe=["A1", "A2", "A3"],
            config=cfg,
            rebalance_date=logp.index[start_idx],
        )
        if meta.segment_status == "skipped":
            skipped += 1
        else:
            ok += 1
    assert skipped >= 0 and ok >= 1


def test_csv_numeric_dot_format(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    pd.DataFrame({"a": [1.25], "b": [2.5]}).to_csv(p, index=False)
    raw = p.read_text(encoding="utf-8")
    assert "," in raw
    assert "1.25" in raw
    assert "1,25" not in raw


def test_analyze_flags_deep_drawdown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.analyze_crypto_parameter_grid as ac

    monkeypatch.setattr(ac, "OUT_DIR", tmp_path)
    df = pd.DataFrame(
        [
            {
                "target": "BTC",
                "universe_assets": "ETH,SOL",
                "valid_rebalance_windows": 5,
                "skipped_rebalance_windows": 1,
                "valid_rebalance_share": 5 / 6,
                "train_window": 100,
                "rebalance_frequency": 24,
                "entry_z": 2.0,
                "exit_z": 0.25,
                "zscore_lookback": 50,
                "pca_explained_variance": 0.8,
                "universe_size_requested": 30,
                "universe_selection_method": "priority_with_coverage_fallback",
                "min_asset_coverage": 0.6,
                "min_universe_assets": 5,
                "min_train_observations": 50,
                "max_holding_period": None,
                "stop_loss_z": None,
                "pca_component_selection_method": "explained_variance",
                "fixed_n_components": np.nan,
                "regression_type": "OLS",
                "ridge_alpha": np.nan,
                "transaction_cost_bps": 10,
                "stage": "core",
                "total_return": 1.0,
                "annualized_return": 0.5,
                "annualized_volatility": 0.3,
                "sharpe_ratio": 1.0,
                "max_drawdown": -0.85,
                "turnover": 0.5,
                "number_of_trades": 3,
                "average_holding_period": 4.0,
                "hit_rate": 0.4,
            }
        ]
    )
    susp = ac._suspicious(df)
    assert not susp.empty
    assert "deep_dd" in susp.iloc[0]["suspicious_flags"]
    assert "few_trades" in susp.iloc[0]["suspicious_flags"]


def test_time_stop_increments_counter() -> None:
    z = pd.Series([0.0, -3.0, -3.0, -3.0, -3.0])
    pos, se, te = generate_positions(z, entry_z=2.0, exit_z=0.5, max_holding_period=1, stop_loss_z=None)
    assert te >= 1
    assert float(pos.iloc[-1]) == 0.0


def test_excluded_token_set_contains_stablecoins() -> None:
    assert "USDT" in CRYPTO_EXCLUDED_TOKENS
