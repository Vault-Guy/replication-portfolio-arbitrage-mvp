"""
Перебор параметров (грид-сёрч) по всем рынкам и таргетам.

Вход:  конфиги рынков (configs/*.yaml) и сырые архивы с ценами.
Что делает: для каждой комбинации рынок × таргет × rebalance_frequency × (entry_z, exit_z)
            запускает полный пайплайн и собирает метрики бэктеста.
            Поддерживает флаги --market, --max-runs, --dry-run.
Результат: results/grid_search/grid_search_results.csv  — все успешные запуски,
           results/grid_search/grid_search_failures.csv  — упавшие запуски,
           results/grid_search/best_by_market.csv        — лучший набор параметров по рынку,
           results/grid_search/best_by_target.csv        — лучший набор параметров по таргету.
"""
from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sarb.run import (  # noqa: E402
    RunConfig,
    coverage_summary,
    load_market_prices,
    load_run_config,
    run_unified_pipeline,
)
from sarb.universe import UniverseSelectionResult, select_priority_universe  # noqa: E402
from sarb.utils.io import format_dataframe_for_display_eu, save_table  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "results" / "grid_search"
RESULTS_PATH = OUTPUT_DIR / "grid_search_results.csv"
FAILURES_PATH = OUTPUT_DIR / "grid_search_failures.csv"
BEST_BY_MARKET_PATH = OUTPUT_DIR / "best_by_market.csv"
BEST_BY_TARGET_PATH = OUTPUT_DIR / "best_by_target.csv"

MARKET_TARGETS: dict[str, list[str]] = {
    "usa": ["AAPL", "BRK.B", "MSFT", "AMZN", "NVDA"],
    "crypto": ["BTC", "ETH", "SOL", "XRP", "BNB"],
    "russia": ["AFKS", "AFLT", "LKOH", "CHMF", "GAZP"],
}

TRAIN_WINDOWS: dict[str, int] = {
    "usa": 252,
    "russia": 252,
    "crypto": 1440,
}

REBALANCE_FREQUENCIES: dict[str, list[int]] = {
    "usa": [5, 10, 21, 63],
    "russia": [5, 10, 21, 63],
    "crypto": [24, 72, 168, 336],
}

ENTRY_Z_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0]
EXIT_Z_VALUES = [0.0, 0.25, 0.5, 0.75, 1.0]
UNIVERSE_SIZE_REQUESTED = 30

RESULT_COLUMNS = [
    "market",
    "target",
    "universe_selection_method",
    "universe_size_requested",
    "universe_size_actual",
    "universe_assets",
    "missing_priority_assets",
    "filled_from_fallback",
    "train_window",
    "rebalance_frequency",
    "pca_explained_variance",
    "zscore_lookback",
    "entry_z",
    "exit_z",
    "transaction_cost_bps",
    "annualization_factor",
    "total_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
    "max_drawdown",
    "turnover",
    "number_of_trades",
    "average_holding_period",
    "hit_rate",
]

FAILURE_COLUMNS = [
    "market",
    "target",
    "universe_selection_method",
    "universe_size_requested",
    "universe_size_actual",
    "universe_assets",
    "missing_priority_assets",
    "filled_from_fallback",
    "train_window",
    "rebalance_frequency",
    "entry_z",
    "exit_z",
    "error",
]


def prepare_market_prices(market: str, prices: pd.DataFrame) -> pd.DataFrame:
    if market == "russia":
        return prices.dropna(how="any")
    return prices


def resolve_target_symbol(prices: pd.DataFrame, target: str) -> str:
    if target in prices.columns:
        return str(target)
    alternate = target.replace(".", "-")
    if alternate in prices.columns:
        return alternate
    raise KeyError(f"target asset {target!r} is not present in loaded prices")


def select_market_universe(
    prices: pd.DataFrame,
    *,
    market: str,
    target: str,
    requested_size: int,
) -> UniverseSelectionResult:
    coverage = coverage_summary(prices)
    available_assets = coverage.loc[
        (coverage["observations"] > 0) & (coverage["missing_pct"] < 1.0),
        "symbol",
    ].astype(str).tolist()
    ref_prices = prices if market == "crypto" else None
    return select_priority_universe(
        available_assets,
        target,
        market,
        requested_size=requested_size,
        fallback_by_coverage=True,
        coverage=coverage,
        reference_prices=ref_prices,
    )


def valid_zscore_pairs() -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for entry_z, exit_z in product(ENTRY_Z_VALUES, EXIT_Z_VALUES):
        if exit_z >= entry_z:
            continue
        pairs.append((entry_z, exit_z))
    return pairs


def iter_grid_jobs(markets: Iterable[str]) -> Iterable[dict[str, Any]]:
    for market in markets:
        base_config = load_run_config(market)
        for target in MARKET_TARGETS[market]:
            for rebalance_frequency in REBALANCE_FREQUENCIES[market]:
                for entry_z, exit_z in valid_zscore_pairs():
                    yield {
                        "market": market,
                        "target": target,
                        "base_config": base_config,
                        "train_window": TRAIN_WINDOWS[market],
                        "rebalance_frequency": rebalance_frequency,
                        "entry_z": entry_z,
                        "exit_z": exit_z,
                    }


def build_run_config(job: dict[str, Any]) -> RunConfig:
    base: RunConfig = job["base_config"]
    config = replace(
        base,
        train_window=job["train_window"],
        rebalance_frequency=job["rebalance_frequency"],
        entry_z=job["entry_z"],
        exit_z=job["exit_z"],
    )
    config.validate()
    return config


def result_row(
    *,
    market: str,
    target: str,
    universe: UniverseSelectionResult,
    run_config: RunConfig,
    metrics: object,
) -> dict[str, Any]:
    row = {
        "market": market,
        "target": target,
        "universe_selection_method": universe.selection_method,
        "universe_size_requested": universe.universe_size_requested,
        "universe_size_actual": universe.universe_size_actual,
        "universe_assets": ",".join(universe.assets),
        "missing_priority_assets": ",".join(universe.missing_priority_assets),
        "filled_from_fallback": ",".join(universe.filled_from_fallback),
        "train_window": run_config.train_window,
        "rebalance_frequency": run_config.rebalance_frequency,
        "pca_explained_variance": run_config.pca_explained_variance,
        "zscore_lookback": run_config.zscore_lookback,
        "entry_z": run_config.entry_z,
        "exit_z": run_config.exit_z,
        "transaction_cost_bps": run_config.transaction_cost_bps,
        "annualization_factor": run_config.annualization_factor,
    }
    for field in RESULT_COLUMNS:
        if field in row:
            continue
        row[field] = getattr(metrics, field)
    return row


def failure_row(
    job: dict[str, Any],
    *,
    universe: UniverseSelectionResult | None,
    error: str,
) -> dict[str, Any]:
    return {
        "market": job["market"],
        "target": job["target"],
        "universe_selection_method": universe.selection_method if universe is not None else None,
        "universe_size_requested": UNIVERSE_SIZE_REQUESTED,
        "universe_size_actual": universe.universe_size_actual if universe is not None else None,
        "universe_assets": ",".join(universe.assets) if universe is not None else None,
        "missing_priority_assets": ",".join(universe.missing_priority_assets)
        if universe is not None
        else None,
        "filled_from_fallback": ",".join(universe.filled_from_fallback)
        if universe is not None
        else None,
        "train_window": job["train_window"],
        "rebalance_frequency": job["rebalance_frequency"],
        "entry_z": job["entry_z"],
        "exit_z": job["exit_z"],
        "error": error,
    }


def write_dataframe(
    path: Path,
    frame: pd.DataFrame,
    *,
    require_full_grid_search: bool = False,
) -> None:
    validate_metrics = path.name == "grid_search_results.csv"
    min_rows = 100 if require_full_grid_search else None
    save_table(
        frame,
        path,
        validate_metrics=validate_metrics,
        min_rows=min_rows,
    )


def print_best_results(results: pd.DataFrame) -> None:
    if results.empty:
        print("No successful grid-search runs to summarize.")
        return

    best_by_market = (
        results.sort_values(["market", "sharpe_ratio"], ascending=[True, False])
        .groupby("market", as_index=False)
        .first()
    )
    best_by_target = (
        results.sort_values(["market", "target", "sharpe_ratio"], ascending=[True, True, False])
        .groupby(["market", "target"], as_index=False)
        .first()
    )
    write_dataframe(BEST_BY_MARKET_PATH, best_by_market)
    write_dataframe(BEST_BY_TARGET_PATH, best_by_target)

    print("\nBest by market:")
    print(format_dataframe_for_display_eu(best_by_market).to_string(index=False))
    print("\nBest by target:")
    print(format_dataframe_for_display_eu(best_by_target).to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grid search over PCA stat-arb parameters.")
    parser.add_argument(
        "--market",
        choices=["usa", "crypto", "russia", "all"],
        default="all",
        help="Market or markets to search.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Limit the number of executed runs for quick testing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned runs without executing the pipeline.",
    )
    return parser.parse_args()


def selected_markets(args: argparse.Namespace) -> list[str]:
    if args.market == "all":
        return list(MARKET_TARGETS.keys())
    return [args.market]


def main() -> int:
    args = parse_args()
    markets = selected_markets(args)
    jobs = list(iter_grid_jobs(markets))

    if args.dry_run:
        print(f"Planned runs: {len(jobs)}")
        for index, job in enumerate(jobs, start=1):
            print(
                f"{index}: market={job['market']} target={job['target']} "
                f"train_window={job['train_window']} rebalance_frequency={job['rebalance_frequency']} "
                f"entry_z={job['entry_z']} exit_z={job['exit_z']}"
            )
        return 0

    market_prices: dict[str, pd.DataFrame] = {}
    market_universes: dict[tuple[str, str], UniverseSelectionResult] = {}
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for market in markets:
        prices = prepare_market_prices(market, load_market_prices(market))
        market_prices[market] = prices
        for target in MARKET_TARGETS[market]:
            try:
                resolved_target = resolve_target_symbol(prices, target)
            except KeyError as exc:
                failures.append(
                    failure_row(
                        {
                            "market": market,
                            "target": target,
                            "train_window": TRAIN_WINDOWS[market],
                            "rebalance_frequency": None,
                            "entry_z": None,
                            "exit_z": None,
                        },
                        universe=None,
                        error=str(exc),
                    )
                )
                continue
            try:
                universe = select_market_universe(
                    prices,
                    market=market,
                    target=resolved_target,
                    requested_size=UNIVERSE_SIZE_REQUESTED,
                )
            except Exception as exc:
                failures.append(
                    failure_row(
                        {
                            "market": market,
                            "target": target,
                            "train_window": TRAIN_WINDOWS[market],
                            "rebalance_frequency": None,
                            "entry_z": None,
                            "exit_z": None,
                        },
                        universe=None,
                        error=str(exc),
                    )
                )
                continue
            market_universes[(market, target)] = universe

    executed = 0
    for index, job in enumerate(jobs, start=1):
        if args.max_runs is not None and executed >= args.max_runs:
            break

        market = job["market"]
        target = job["target"]
        universe = market_universes.get((market, target))
        if universe is None:
            continue

        resolved_target = resolve_target_symbol(market_prices[market], target)
        print(
            f"[{index}/{len(jobs)}] market={market} target={target} "
            f"universe_method={universe.selection_method} "
            f"rebalance_frequency={job['rebalance_frequency']} "
            f"entry_z={job['entry_z']} exit_z={job['exit_z']}"
        )
        try:
            run_config = build_run_config(job)
            result = run_unified_pipeline(
                market_prices[market],
                target=resolved_target,
                universe=universe.assets,
                run_config=run_config,
            )
            results.append(
                result_row(
                    market=market,
                    target=target,
                    universe=universe,
                    run_config=run_config,
                    metrics=result.backtest.metrics,
                )
            )
            executed += 1
        except Exception as exc:
            failures.append(
                failure_row(
                    job,
                    universe=universe,
                    error=f"{exc.__class__.__name__}: {exc}",
                )
            )
            traceback.print_exc()

    results_frame = pd.DataFrame(results, columns=RESULT_COLUMNS)
    failures_frame = pd.DataFrame(failures, columns=FAILURE_COLUMNS)
    write_dataframe(RESULTS_PATH, results_frame, require_full_grid_search=args.max_runs is None)
    write_dataframe(FAILURES_PATH, failures_frame)
    print_best_results(results_frame)
    print(
        f"\nSaved {len(results_frame)} successful runs to {RESULTS_PATH} "
        f"and {len(failures_frame)} failures to {FAILURES_PATH}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
