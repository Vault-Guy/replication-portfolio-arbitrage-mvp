import numpy as np
import pandas as pd
import pytest

from sarb.data.base import apply_missing_value_policy
from sarb.pca_replication import (
    PCAReplicationConfig,
    fit_pca_synthetic_etf,
    replicate_segment,
    to_log_prices,
    universe_eligible_for_window,
)
from sarb.run import RunConfig, load_run_config, point_in_time_universe, run_unified_pipeline
from sarb.signals import shift_positions_for_execution


def test_run_config_annualization_matches_market_calendar():
    usa = load_run_config("usa")
    crypto = load_run_config("crypto")
    assert usa.annualization_factor == 252.0
    assert crypto.annualization_factor == 8760.0


def test_run_config_rejects_mismatched_annualization():
    with pytest.raises(ValueError, match="annualization_factor"):
        RunConfig.from_mapping(
            {
                "market": "crypto",
                "data_file": "data/raw/crypto_data.zip",
                "frequency": "1H",
                "annualization_factor": 252,
                "price_field": "close",
                "train_window": 100,
                "rebalance_frequency": 10,
                "pca_explained_variance": 0.8,
                "zscore_lookback": 10,
                "entry_z": 2.0,
                "exit_z": 0.5,
                "transaction_cost_bps": 10,
            }
        )


def test_fit_rejects_target_inside_pca_universe():
    index = pd.date_range("2020-01-01", periods=40, freq="D")
    prices = pd.DataFrame(
        {
            "A0": np.linspace(100.0, 120.0, len(index)),
            "A1": np.linspace(90.0, 110.0, len(index)),
            "A2": np.linspace(80.0, 100.0, len(index)),
        },
        index=index,
    )
    config = PCAReplicationConfig(
        train_window=20,
        rebalance_frequency=5,
        pca_explained_variance=0.80,
        min_train_observations=20,
        min_universe_assets=5,
        min_asset_coverage=0.80,
        market="usa",
    )
    with pytest.raises(ValueError, match="must not be included"):
        fit_pca_synthetic_etf(
            to_log_prices(prices),
            target="A0",
            universe=["A0", "A1", "A2"],
            config=config,
        )


def test_universe_eligibility_excludes_late_listed_asset_from_training():
    index = pd.date_range("2020-01-01", periods=6, freq="D")
    frame = pd.DataFrame(
        {
            "A1": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            "A2": [1.0, 1.1, 1.2, 1.3, 1.4, 1.5],
            "LATE": [np.nan, np.nan, 1.2, 1.3, 1.4, 1.5],
        },
        index=index,
    )
    eligible = universe_eligible_for_window(frame, ["A1", "A2", "LATE"])
    assert eligible == ["A1", "A2"]


def test_point_in_time_universe_excludes_future_listings():
    index = pd.date_range("2020-01-01", periods=5, freq="D")
    prices = pd.DataFrame(
        {
            "EARLY": [100.0, 101.0, 102.0, 103.0, 104.0],
            "LATE": [np.nan, np.nan, 102.0, 103.0, 104.0],
        },
        index=index,
    )
    eligible = point_in_time_universe(
        prices,
        ["EARLY", "LATE"],
        as_of=pd.Timestamp("2020-01-01"),
    )
    assert eligible == ["EARLY"]


def test_forward_fill_requires_explicit_limit():
    prices = pd.DataFrame({"AAA": [100.0, np.nan]}, index=pd.to_datetime(["2020-01-01", "2020-01-02"]))
    with pytest.raises(ValueError, match="forward_fill_limit"):
        apply_missing_value_policy(prices, "forward_fill")


def test_forward_fill_respects_limit():
    prices = pd.DataFrame(
        {"AAA": [100.0, np.nan, np.nan, np.nan]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
    )
    filled = apply_missing_value_policy(prices, "forward_fill", forward_fill_limit=1)
    assert filled.loc["2020-01-02", "AAA"] == 100.0
    assert pd.isna(filled.loc["2020-01-03", "AAA"])


def test_shifted_positions_do_not_execute_on_signal_bar():
    index = pd.date_range("2020-01-01", periods=4, freq="D")
    positions = pd.Series([0.0, 1.0, 1.0, -1.0], index=index)
    shifted = shift_positions_for_execution(positions, shift_bars=1)
    assert pd.isna(shifted.iloc[0])
    assert shifted.iloc[1] == positions.iloc[0]
    assert shifted.iloc[2] == positions.iloc[1]


def test_run_unified_pipeline_rejects_target_in_universe():
    index = pd.date_range("2020-01-01", periods=80, freq="D")
    prices = pd.DataFrame(
        {f"A{i}": np.linspace(100 + i, 120 + i, len(index)) for i in range(4)},
        index=index,
    )
    config = RunConfig.from_mapping(
        {
            "market": "usa",
            "data_file": "data/raw/usa_data.zip",
            "frequency": "1D",
            "annualization_factor": 252,
            "price_field": "adjusted_close",
            "train_window": 20,
            "rebalance_frequency": 5,
            "pca_explained_variance": 0.8,
            "zscore_lookback": 5,
            "entry_z": 2.0,
            "exit_z": 0.5,
            "transaction_cost_bps": 5,
        }
    )
    with pytest.raises(ValueError, match="must not be included"):
        run_unified_pipeline(
            prices,
            target="A0",
            universe=["A0", "A1", "A2"],
            run_config=config,
        )


def test_usa_pipeline_surfaces_universe_selection_caveat():
    index = pd.date_range("2020-01-01", periods=80, freq="D")
    prices = pd.DataFrame(
        {f"A{i}": np.linspace(100 + i, 120 + i, len(index)) for i in range(4)},
        index=index,
    )
    config = RunConfig.from_mapping(
        {
            "market": "usa",
            "data_file": "data/raw/usa_data.zip",
            "frequency": "1D",
            "annualization_factor": 252,
            "price_field": "adjusted_close",
            "train_window": 20,
            "rebalance_frequency": 5,
            "pca_explained_variance": 0.8,
            "zscore_lookback": 5,
            "entry_z": 2.0,
            "exit_z": 0.5,
            "transaction_cost_bps": 5,
        }
    )
    result = run_unified_pipeline(
        prices,
        target="A0",
        universe=["A1", "A2", "A3"],
        run_config=config,
    )
    assert any("future-selection bias" in caveat for caveat in result.caveats)


def test_late_listed_asset_does_not_expand_early_segment():
    index = pd.date_range("2020-01-01", periods=40, freq="D")
    prices = pd.DataFrame(
        {
            "A0": np.linspace(100.0, 140.0, len(index)),
            "A1": np.linspace(90.0, 130.0, len(index)),
            "A2": np.linspace(80.0, 120.0, len(index)),
            "LATE": [np.nan] * 20 + list(np.linspace(110.0, 130.0, 20)),
        },
        index=index,
    )
    config = PCAReplicationConfig(
        train_window=10,
        rebalance_frequency=5,
        pca_explained_variance=0.80,
        min_train_observations=10,
        min_universe_assets=2,
        min_asset_coverage=0.50,
        market="usa",
    )
    train = to_log_prices(prices).iloc[10:20]
    oos = to_log_prices(prices).iloc[20:25]
    early, meta = replicate_segment(
        train,
        oos,
        target="A0",
        universe=["A1", "A2", "LATE"],
        config=config,
        rebalance_date=index[20],
    )
    assert early is not None
    assert early.metadata.universe_size == 2
