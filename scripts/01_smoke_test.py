"""
Smoke-тест основного пайплайна.

Вход:  конфиги рынков (configs/*.yaml) и сырые архивы с ценами (указаны в конфигах).
Что делает: запускает полный пайплайн (загрузка → PCA-репликация → бэктест → метрики)
            на трёх рынках (usa, crypto, russia) с фиксированными таргетами и небольшой
            вселенной; проверяет ассертами, что результат непустой и корректный.
Результат: только вывод в консоль; файлы не записываются. Ненулевой код возврата
           означает ошибку.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import sarb  # noqa: E402
from sarb.config import load_market_config  # noqa: E402
from sarb.run import (  # noqa: E402
    RunConfig,
    UnifiedPipelineResult,
    coverage_summary,
    load_market_prices,
    load_run_config,
    metrics_dataframe,
    run_unified_pipeline,
)


def missing_value_summary(prices: pd.DataFrame) -> dict[str, float | int]:
    total_cells = int(prices.size)
    missing_cells = int(prices.isna().sum().sum())
    missing_pct = 0.0 if total_cells == 0 else missing_cells / total_cells
    return {
        "total_cells": total_cells,
        "missing_cells": missing_cells,
        "missing_pct": missing_pct,
    }


def select_target_and_universe(
    prices: pd.DataFrame,
    *,
    target: str | None = None,
    universe_size: int = 5,
) -> tuple[str, list[str]]:
    columns = [str(column) for column in prices.columns]
    if not columns:
        raise ValueError("price panel has no assets")
    chosen_target = target if target is not None else columns[0]
    if chosen_target not in columns:
        raise ValueError(f"target asset {chosen_target!r} is not present in prices")

    ranked = (
        coverage_summary(prices)
        .loc[lambda frame: frame["symbol"] != chosen_target]
        .sort_values(["missing_pct", "observations", "symbol"], ascending=[True, False, True])
    )
    universe = ranked.head(universe_size)["symbol"].astype(str).tolist()
    if len(universe) < 2:
        raise ValueError("at least two universe assets are required for PCA replication")
    return chosen_target, universe


def assert_annualization_factor(run_config: RunConfig) -> None:
    if run_config.market == "crypto":
        assert run_config.annualization_factor == 8760.0
        return
    if run_config.frequency == "1D":
        assert run_config.annualization_factor == 252.0
        return
    raise AssertionError(f"unsupported annualization check for market {run_config.market!r}")


def assert_pipeline_outputs(result: UnifiedPipelineResult) -> None:
    assert result.target not in result.universe
    assert not result.backtest.spread.dropna().empty
    assert not result.backtest.zscore.dropna().empty
    assert not result.backtest.positions.dropna().empty
    assert not result.backtest.equity_curve.dropna().empty
    metrics = metrics_dataframe(result.backtest.metrics)
    assert not metrics.empty


def print_market_summary(market: str, prices: pd.DataFrame) -> None:
    missing = missing_value_summary(prices)
    print(f"market: {market}")
    print(f"shape: {prices.shape}")
    print(f"date_range: {prices.index.min()} -> {prices.index.max()}")
    print(f"assets: {prices.shape[1]}")
    print(
        "missing_values: "
        f"cells={missing['missing_cells']} "
        f"pct={missing['missing_pct']:.6f}"
    )


def print_pipeline_summary(result: UnifiedPipelineResult) -> None:
    print("result_keys:", sorted(result.__dataclass_fields__.keys()))
    print("backtest_keys:", sorted(result.backtest.__dataclass_fields__.keys()))
    print("metrics:")
    print(metrics_dataframe(result.backtest.metrics).to_string(index=False))


def run_market_smoke(
    market: str,
    *,
    target: str | None = None,
    universe_size: int = 5,
) -> UnifiedPipelineResult:
    print(f"\n=== {market.upper()} ===")
    run_config = load_run_config(market)
    data_path = load_market_config(market).raw_archive
    if not data_path.is_file():
        raise FileNotFoundError(f"missing raw archive: {data_path}")

    prices = load_market_prices(market)
    if market == "russia":
        prices = prices.dropna(how="any")
    print_market_summary(market, prices)
    coverage = coverage_summary(prices)
    print(f"coverage_rows: {len(coverage)}")

    chosen_target, universe = select_target_and_universe(
        prices,
        target=target,
        universe_size=universe_size,
    )
    print(f"target: {chosen_target}")
    print(f"universe: {universe}")

    assert chosen_target not in universe
    assert_annualization_factor(run_config)

    result = run_unified_pipeline(
        prices,
        target=chosen_target,
        universe=universe,
        run_config=run_config,
    )
    print_pipeline_summary(result)
    assert_pipeline_outputs(result)
    return result


def main() -> int:
    print(f"sarb version: {sarb.__version__}")
    print(f"project_root: {PROJECT_ROOT}")

    run_market_smoke("usa", target="CSCO", universe_size=5)
    run_market_smoke("crypto", target="BTC", universe_size=5)
    run_market_smoke("russia", universe_size=5)

    print("\nSmoke test passed for usa, crypto, and russia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
