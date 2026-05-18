from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd

from sarb.backtest import BacktestResult, run_spread_backtest
from sarb.data.loader import load_prices as _load_prices
from sarb.config import CONFIG_ROOT, load_market_config, load_yaml
from sarb.pca_replication import PCAReplicationConfig
from sarb.pipeline import PCAReplicationPipelineResult, run_pca_synthetic_etf_pipeline
from sarb.signals import SignalConfig
from sarb.universe import normalize_ticker_for_comparison
from sarb.utils.time import expected_annualization_factor

USA_UNIVERSE_SELECTION_BIAS = (
    "Universe membership may reflect 2026 top-100 information and can introduce "
    "future-selection bias in historical research."
)
CRYPTO_CALENDAR_CAVEAT = (
    "Crypto uses a 24/7 hourly calendar; do not reuse daily session assumptions."
)


@dataclass(frozen=True)
class RunConfig:
    market: str
    frequency: str
    annualization_factor: float
    train_window: int
    rebalance_frequency: int
    pca_explained_variance: float
    zscore_lookback: int
    entry_z: float
    exit_z: float
    transaction_cost_bps: float

    @classmethod
    def from_mapping(cls, payload: dict[str, Any]) -> RunConfig:
        config = cls(
            market=payload["market"],
            frequency=payload["frequency"],
            annualization_factor=float(payload["annualization_factor"]),
            train_window=int(payload["train_window"]),
            rebalance_frequency=int(payload["rebalance_frequency"]),
            pca_explained_variance=float(payload["pca_explained_variance"]),
            zscore_lookback=int(payload["zscore_lookback"]),
            entry_z=float(payload["entry_z"]),
            exit_z=float(payload["exit_z"]),
            transaction_cost_bps=float(payload["transaction_cost_bps"]),
        )
        config.validate()
        return config

    def validate(self) -> None:
        expected = expected_annualization_factor(self.frequency)
        if self.annualization_factor != expected:
            raise ValueError(
                f"annualization_factor {self.annualization_factor} does not match "
                f"frequency {self.frequency!r} (expected {expected})"
            )


@dataclass(frozen=True)
class UnifiedPipelineResult:
    run_config: RunConfig
    target: str
    universe: tuple[str, ...]
    prices: pd.DataFrame
    coverage: pd.DataFrame
    replication: PCAReplicationPipelineResult
    backtest: BacktestResult
    caveats: tuple[str, ...]


def load_run_config(market: str) -> RunConfig:
    return RunConfig.from_mapping(load_yaml(CONFIG_ROOT / f"{market}.yaml"))


def load_market_prices(market: str) -> pd.DataFrame:
    market_config = load_market_config(market)
    return _load_prices(market_config).prices


def coverage_summary(prices: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for symbol in prices.columns.astype(str):
        series = prices[symbol]
        rows.append(
            {
                "symbol": symbol,
                "first_valid": series.first_valid_index(),
                "last_valid": series.last_valid_index(),
                "observations": int(series.notna().sum()),
                "missing_pct": float(series.isna().mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("symbol").reset_index(drop=True)


def metrics_dataframe(metrics: object) -> pd.DataFrame:
    return pd.DataFrame([asdict(metrics)])


def point_in_time_universe(
    prices: pd.DataFrame,
    candidates: list[str],
    *,
    as_of: pd.Timestamp,
) -> list[str]:
    eligible: list[str] = []
    for symbol in candidates:
        if symbol not in prices.columns:
            continue
        first_valid = prices[symbol].first_valid_index()
        if first_valid is not None and first_valid <= as_of:
            eligible.append(symbol)
    return eligible


def min_train_observations_for_market(market: str, train_window: int) -> int:
    if market == "crypto":
        return max(50, int(0.25 * train_window))
    return max(60, int(0.25 * train_window))


def pipeline_caveats(run_config: RunConfig) -> tuple[str, ...]:
    caveats: list[str] = []
    if run_config.market == "usa":
        caveats.append(USA_UNIVERSE_SELECTION_BIAS)
    if run_config.market == "crypto":
        caveats.append(CRYPTO_CALENDAR_CAVEAT)
    return tuple(caveats)


def run_unified_pipeline(
    prices: pd.DataFrame,
    *,
    target: str,
    universe: list[str],
    run_config: RunConfig,
    min_asset_coverage: float | None = None,
    min_universe_assets: int | None = None,
    min_train_observations: int | None = None,
    pca_component_selection_method: str = "explained_variance",
    fixed_n_components: int | None = None,
    regression_type: str = "OLS",
    ridge_alpha: float = 1.0,
    max_holding_period: int | None = None,
    stop_loss_z: float | None = None,
) -> UnifiedPipelineResult:
    target_key = normalize_ticker_for_comparison(target)
    universe_keys = {normalize_ticker_for_comparison(x) for x in universe}
    if target_key in universe_keys:
        raise ValueError("target asset must not be included in the PCA universe")

    min_train = (
        int(min_train_observations)
        if min_train_observations is not None
        else min_train_observations_for_market(run_config.market, run_config.train_window)
    )
    min_asset_cov = (
        float(min_asset_coverage)
        if min_asset_coverage is not None
        else (0.60 if run_config.market == "crypto" else 0.80)
    )
    min_univ = int(min_universe_assets) if min_universe_assets is not None else 5
    pca_config = PCAReplicationConfig(
        train_window=run_config.train_window,
        rebalance_frequency=run_config.rebalance_frequency,
        pca_explained_variance=run_config.pca_explained_variance,
        min_train_observations=min_train,
        min_universe_assets=min_univ,
        min_asset_coverage=min_asset_cov,
        market=run_config.market,
        pca_component_selection_method=pca_component_selection_method,
        fixed_n_components=fixed_n_components,
        regression_type=regression_type,
        ridge_alpha=ridge_alpha,
    )
    replication = run_pca_synthetic_etf_pipeline(
        prices,
        target=target,
        universe=universe,
        config=pca_config,
    )
    signal_config = SignalConfig(
        zscore_lookback=run_config.zscore_lookback,
        entry_z=run_config.entry_z,
        exit_z=run_config.exit_z,
        transaction_cost_bps=run_config.transaction_cost_bps,
        annualization_factor=run_config.annualization_factor,
    )
    backtest = run_spread_backtest(
        real_log_price=replication.target_log_prices,
        synthetic_log_price=replication.synthetic_log_prices,
        config=signal_config,
        max_holding_period=max_holding_period,
        stop_loss_z=stop_loss_z,
    )
    diag = replication.diagnostics
    diag_note = (
        f"PCA replication diagnostics: valid_rebalance_windows={diag['valid_rebalance_windows']}, "
        f"skipped_rebalance_windows={diag['skipped_rebalance_windows']}, "
        f"min_train_observations={diag['min_train_observations']}, "
        f"min_universe_assets={diag['min_universe_assets']}, "
        f"min_asset_coverage={diag['min_asset_coverage']}, market={diag['market']}, "
        f"universe_assets_used={diag['universe_assets_used']}"
    )
    caveats = tuple([*pipeline_caveats(run_config), diag_note])
    return UnifiedPipelineResult(
        run_config=run_config,
        target=target,
        universe=tuple(universe),
        prices=prices,
        coverage=coverage_summary(prices),
        replication=replication,
        backtest=backtest,
        caveats=caveats,
    )
