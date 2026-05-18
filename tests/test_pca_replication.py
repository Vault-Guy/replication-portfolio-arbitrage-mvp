import numpy as np
import pandas as pd
import pytest

from sarb.pca_replication import (
    PCAReplicationConfig,
    _oos_frame,
    apply_pca_synthetic_etf,
    fit_pca_synthetic_etf,
    replicate_segment,
    select_component_count,
    to_log_prices,
)
from sarb.pipeline import run_pca_synthetic_etf_pipeline


def _synthetic_prices(rows: int = 400, assets: int = 5, seed: int = 0) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=rows, freq="D")
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(0.0005, 0.02, size=(rows, assets))
    prices = 100.0 * np.exp(np.cumsum(log_returns, axis=0))
    columns = [f"A{i}" for i in range(assets)]
    return pd.DataFrame(prices, index=index, columns=columns)


def test_select_component_count_uses_smallest_covering_threshold():
    ratios = np.array([0.5, 0.3, 0.2])
    assert select_component_count(ratios, 0.80) == 2
    assert select_component_count(ratios, 0.95) == 3


def test_replicate_segment_uses_training_window_only():
    prices = _synthetic_prices()
    config = PCAReplicationConfig(
        train_window=60,
        rebalance_frequency=10,
        pca_explained_variance=0.80,
        min_train_observations=60,
        min_universe_assets=5,
        min_asset_coverage=0.80,
        market="usa",
    )
    log_prices = to_log_prices(prices)
    train = log_prices.iloc[60:120]
    oos = log_prices.iloc[120:130]
    segment, meta = replicate_segment(
        train,
        oos,
        target="A0",
        universe=["A1", "A2", "A3", "A4"],
        config=config,
        rebalance_date=log_prices.index[120],
    )
    assert segment is not None
    assert meta.segment_status == "ok"
    assert segment.metadata.train_start == train.index[0]
    assert segment.metadata.train_end == train.index[-1]
    assert segment.metadata.train_end < segment.metadata.rebalance_date
    assert segment.metadata.n_components >= 1
    assert segment.metadata.explained_variance >= config.pca_explained_variance - 1e-12
    assert len(segment.spread) == len(oos)


def test_apply_does_not_refit_on_out_of_sample_data():
    prices = _synthetic_prices()
    config = PCAReplicationConfig(
        train_window=60,
        rebalance_frequency=10,
        pca_explained_variance=0.80,
        min_train_observations=60,
        min_universe_assets=5,
        min_asset_coverage=0.80,
        market="usa",
    )
    log_prices = to_log_prices(prices)
    train = log_prices.iloc[60:120]
    oos = log_prices.iloc[120:130]
    model = fit_pca_synthetic_etf(
        train,
        target="A0",
        universe=["A1", "A2", "A3", "A4"],
        config=config,
    )
    assert model is not None
    baseline = apply_pca_synthetic_etf(oos, model)
    tampered = oos.copy()
    tampered["A0"] = tampered["A0"] + 5.0
    transformed = apply_pca_synthetic_etf(tampered, model)
    pd.testing.assert_series_equal(
        baseline["synthetic_log_price"],
        transformed["synthetic_log_price"],
        check_names=False,
    )


def test_pipeline_future_changes_do_not_alter_past_outputs():
    prices = _synthetic_prices()
    config = PCAReplicationConfig(
        train_window=60,
        rebalance_frequency=10,
        pca_explained_variance=0.80,
        min_train_observations=60,
        min_universe_assets=5,
        min_asset_coverage=0.80,
        market="usa",
    )
    cutoff = 200
    baseline_prices = prices.iloc[:cutoff]
    result_a = run_pca_synthetic_etf_pipeline(
        baseline_prices,
        target="A0",
        universe=["A1", "A2", "A3", "A4"],
        config=config,
    )

    tampered_prices = prices.copy()
    tampered_prices.iloc[cutoff:] = tampered_prices.iloc[cutoff:] * 3.0
    result_b = run_pca_synthetic_etf_pipeline(
        tampered_prices.iloc[:cutoff],
        target="A0",
        universe=["A1", "A2", "A3", "A4"],
        config=config,
    )
    result_c = run_pca_synthetic_etf_pipeline(
        tampered_prices,
        target="A0",
        universe=["A1", "A2", "A3", "A4"],
        config=config,
    )

    pd.testing.assert_series_equal(result_a.spreads, result_b.spreads)
    pd.testing.assert_series_equal(result_a.synthetic_log_prices, result_b.synthetic_log_prices)
    pd.testing.assert_frame_equal(result_a.metadata, result_b.metadata)

    overlap = result_c.spreads.index[result_c.spreads.index < prices.index[cutoff]]
    pd.testing.assert_series_equal(result_a.spreads, result_c.spreads.loc[overlap])
    pd.testing.assert_series_equal(
        result_a.synthetic_log_prices,
        result_c.synthetic_log_prices.loc[overlap],
    )


def test_pipeline_rejects_target_in_universe():
    prices = _synthetic_prices(rows=120)
    config = PCAReplicationConfig(
        train_window=30,
        rebalance_frequency=10,
        pca_explained_variance=0.80,
        min_train_observations=30,
        min_universe_assets=5,
        min_asset_coverage=0.80,
        market="usa",
    )
    with pytest.raises(ValueError, match="must not be included"):
        run_pca_synthetic_etf_pipeline(
            prices,
            target="A0",
            universe=["A0", "A1", "A2"],
            config=config,
        )


def test_crypto_like_late_target_skips_then_runs_without_empty_scaler():
    """Late-listed target: early rebalance windows skip; later windows fit PCA."""
    rows = 400
    index = pd.date_range("2020-01-01", periods=rows, freq="h")
    rng = np.random.default_rng(42)
    prices = pd.DataFrame(index=index)
    for sym in ["BTC", "ETH", "XRP", "BNB", "ADA"]:
        prices[sym] = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.002, rows)))
    sol = np.full(rows, np.nan)
    sol[250:] = 100.0 * np.exp(np.cumsum(rng.normal(0.0001, 0.002, rows - 250)))
    prices["SOL"] = sol

    universe = ["BTC", "ETH", "XRP", "BNB", "ADA"]
    config = PCAReplicationConfig(
        train_window=80,
        rebalance_frequency=30,
        pca_explained_variance=0.80,
        min_train_observations=max(50, int(0.25 * 80)),
        min_universe_assets=5,
        min_asset_coverage=0.60,
        market="crypto",
    )
    logp = to_log_prices(prices)
    train_bad = logp.iloc[80:160]
    seg_none, meta_bad = replicate_segment(
        train_bad,
        logp.iloc[160:190],
        target="SOL",
        universe=universe,
        config=config,
        rebalance_date=logp.index[160],
    )
    assert seg_none is None
    assert meta_bad.segment_status == "skipped"

    result = run_pca_synthetic_etf_pipeline(
        prices,
        target="SOL",
        universe=universe,
        config=config,
    )
    assert not result.spreads.empty
    assert result.diagnostics["valid_rebalance_windows"] >= 1
    assert "SOL" not in ",".join(universe)


def test_oos_frame_uses_row_mask_not_full_frame_dropna():
    idx = pd.date_range("2020-01-01", periods=6, freq="h")
    logp = pd.DataFrame(
        {
            "T": [1.0, 1.1, np.nan, 1.3, 1.4, 1.5],
            "U1": [2.0, np.nan, 2.2, 2.3, 2.4, 2.5],
            "U2": [3.0] * 6,
        },
        index=idx,
    )
    uf, tv = _oos_frame(logp, universe=["U1", "U2"], target="T")
    assert len(uf) == 4
    assert set(uf.index) == {idx[0], idx[3], idx[4], idx[5]}


def test_oos_frame_returns_empty_when_no_valid_rows():
    idx = pd.date_range("2020-01-01", periods=4, freq="h")
    logp = pd.DataFrame({"T": [np.nan] * 4, "U1": [1.0] * 4}, index=idx)
    uf, tv = _oos_frame(logp, universe=["U1"], target="T")
    assert uf.shape[0] == 0
    assert tv.shape[0] == 0


def test_apply_pca_returns_empty_without_scaler_on_empty_oos():
    idx = pd.date_range("2020-01-01", periods=20, freq="D")
    train = pd.DataFrame({f"A{i}": np.linspace(1.0, 2.0, len(idx)) for i in range(4)}, index=idx)
    config = PCAReplicationConfig(
        train_window=15,
        rebalance_frequency=5,
        pca_explained_variance=0.80,
        min_train_observations=15,
        min_universe_assets=2,
        min_asset_coverage=0.80,
        market="usa",
    )
    model = fit_pca_synthetic_etf(
        train.iloc[:15],
        target="A0",
        universe=["A1", "A2", "A3"],
        config=config,
    )
    assert model is not None
    oos = train.iloc[15:18].copy()
    oos["A1"] = np.nan
    oos["A2"] = np.nan
    oos["A3"] = np.nan
    out = apply_pca_synthetic_etf(oos, model)
    assert out.empty
