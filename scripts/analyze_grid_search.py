"""
Анализ результатов грид-сёрча: сводки, лучшие параметры, robust-комбинации.

Вход:  results/grid_search/grid_search_results.csv (можно переопределить флагом --results).
Что делает: строит сводки по рынку и таргету, находит наиболее устойчивые комбинации
            параметров (top-10% по Sharpe), помечает подозрительные результаты
            (мало сделок, большая просадка, высокий оборот), выводит отчёт в консоль.
Результат: results/grid_search/summary_by_market.csv,
           results/grid_search/summary_by_target.csv,
           results/grid_search/top_robust_params.csv,
           results/grid_search/best_by_market.csv,
           results/grid_search/best_by_target.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sarb.utils.io import (  # noqa: E402
    format_dataframe_for_display_eu,
    load_results_table,
    save_table,
    validate_results_row_count,
)
OUTPUT_DIR = PROJECT_ROOT / "results" / "grid_search"
RESULTS_PATH = OUTPUT_DIR / "grid_search_results.csv"
SUMMARY_BY_MARKET_PATH = OUTPUT_DIR / "summary_by_market.csv"
SUMMARY_BY_TARGET_PATH = OUTPUT_DIR / "summary_by_target.csv"
TOP_ROBUST_PARAMS_PATH = OUTPUT_DIR / "top_robust_params.csv"
BEST_BY_MARKET_PATH = OUTPUT_DIR / "best_by_market.csv"
BEST_BY_TARGET_PATH = OUTPUT_DIR / "best_by_target.csv"

PARAM_COLUMNS = ["rebalance_frequency", "entry_z", "exit_z"]
METRIC_COLUMNS = [
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
CONFIG_COLUMNS = [
    "market",
    "target",
    "universe_size_requested",
    "universe_size_actual",
    "universe_assets",
    "train_window",
    "rebalance_frequency",
    "pca_explained_variance",
    "zscore_lookback",
    "entry_z",
    "exit_z",
    "transaction_cost_bps",
    "annualization_factor",
]

MIN_GRID_SEARCH_RESULTS_ROWS = 100
MIN_TRADES_THRESHOLD = 20
HIGH_TURNOVER_THRESHOLD = 0.08
LARGE_DRAWDOWN_THRESHOLD = -0.5
COST_STRESS_BPS = 5.0


def load_results(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Grid search results not found: {path}")
    return load_results_table(path)


def build_best_by_market(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values(["market", "sharpe_ratio"], ascending=[True, False], kind="mergesort")
        .groupby("market", as_index=False)
        .head(1)
    )


def build_best_by_target(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values(
            ["market", "target", "sharpe_ratio"],
            ascending=[True, True, False],
            kind="mergesort",
        )
        .groupby(["market", "target"], as_index=False)
        .head(1)
    )


def best_rows(df: pd.DataFrame, group_cols: list[str], metric: str) -> pd.DataFrame:
    ordered = df.sort_values(metric, ascending=False, kind="mergesort")
    return ordered.groupby(group_cols, as_index=False).head(1)


def add_suspicion_flags(df: pd.DataFrame) -> pd.DataFrame:
    flagged = df.copy()
    flagged["flag_few_trades"] = flagged["number_of_trades"] < MIN_TRADES_THRESHOLD
    flagged["flag_high_turnover"] = flagged["turnover"] >= HIGH_TURNOVER_THRESHOLD
    flagged["flag_large_drawdown"] = flagged["max_drawdown"] <= LARGE_DRAWDOWN_THRESHOLD
    flagged["flag_cost_fragile"] = (
        (flagged["total_return"] > 0)
        & (flagged["turnover"] * COST_STRESS_BPS / 10_000.0 >= flagged["total_return"] * 0.25)
    )
    flagged["suspicion_flags"] = flagged.apply(_format_suspicion_flags, axis=1)
    return flagged


def _format_suspicion_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if row["flag_few_trades"]:
        flags.append("few_trades")
    if row["flag_high_turnover"]:
        flags.append("high_turnover")
    if row["flag_large_drawdown"]:
        flags.append("large_drawdown")
    if row["flag_cost_fragile"]:
        flags.append("cost_fragile")
    return ";".join(flags)


def build_market_summary(df: pd.DataFrame) -> pd.DataFrame:
    best_sharpe = best_rows(df, ["market"], "sharpe_ratio").copy()
    best_sharpe["selection_metric"] = "sharpe_ratio"
    best_sharpe["selection_value"] = best_sharpe["sharpe_ratio"]

    best_return = best_rows(df, ["market"], "total_return").copy()
    best_return["selection_metric"] = "total_return"
    best_return["selection_value"] = best_return["total_return"]

    summary = pd.concat([best_sharpe, best_return], ignore_index=True)
    summary = add_suspicion_flags(summary)

    market_stats = (
        df.groupby("market", as_index=False)
        .agg(
            runs=("sharpe_ratio", "size"),
            targets=("target", "nunique"),
            median_sharpe=("sharpe_ratio", "median"),
            median_total_return=("total_return", "median"),
            median_max_drawdown=("max_drawdown", "median"),
            median_turnover=("turnover", "median"),
            median_trades=("number_of_trades", "median"),
            positive_sharpe_share=("sharpe_ratio", lambda s: float((s > 0).mean())),
            positive_return_share=("total_return", lambda s: float((s > 0).mean())),
            transaction_cost_bps=("transaction_cost_bps", "first"),
        )
        .rename(columns={"targets": "target_count"})
    )
    return summary.merge(market_stats, on="market", how="left", suffixes=("", "_market"))


def build_target_summary(df: pd.DataFrame) -> pd.DataFrame:
    best_sharpe = best_rows(df, ["market", "target"], "sharpe_ratio").copy()
    best_sharpe["selection_metric"] = "sharpe_ratio"
    best_sharpe["selection_value"] = best_sharpe["sharpe_ratio"]

    best_return = best_rows(df, ["market", "target"], "total_return").copy()
    best_return["selection_metric"] = "total_return"
    best_return["selection_value"] = best_return["total_return"]

    summary = pd.concat([best_sharpe, best_return], ignore_index=True)
    summary = add_suspicion_flags(summary)

    target_stats = (
        df.groupby(["market", "target"], as_index=False)
        .agg(
            runs=("sharpe_ratio", "size"),
            median_sharpe=("sharpe_ratio", "median"),
            median_total_return=("total_return", "median"),
            best_sharpe=("sharpe_ratio", "max"),
            best_total_return=("total_return", "max"),
            positive_sharpe_share=("sharpe_ratio", lambda s: float((s > 0).mean())),
        )
    )
    return summary.merge(target_stats, on=["market", "target"], how="left", suffixes=("", "_target"))


def build_robust_params(df: pd.DataFrame) -> pd.DataFrame:
    top_rows: list[pd.DataFrame] = []
    for (_, _), group in df.groupby(["market", "target"], sort=False):
        group = group.sort_values("sharpe_ratio", ascending=False, kind="mergesort")
        top_n = max(1, int(np.ceil(len(group) * 0.10)))
        top_rows.append(group.head(top_n))

    top_decile = pd.concat(top_rows, ignore_index=True)
    counts = (
        top_decile.groupby(["market", *PARAM_COLUMNS], as_index=False)
        .agg(
            top_decile_appearances=("sharpe_ratio", "size"),
            targets_represented=("target", "nunique"),
            median_sharpe_in_decile=("sharpe_ratio", "median"),
            median_total_return_in_decile=("total_return", "median"),
        )
    )

    opportunities = (
        top_decile.groupby("market", as_index=False)
        .agg(top_decile_slots=("sharpe_ratio", "size"))
    )
    counts = counts.merge(opportunities, on="market", how="left")
    counts["appearance_rate"] = counts["top_decile_appearances"] / counts["top_decile_slots"]
    return counts.sort_values(
        ["market", "top_decile_appearances", "median_sharpe_in_decile"],
        ascending=[True, False, False],
        kind="mergesort",
    )


def detect_target_concentration(df: pd.DataFrame, market_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for market, group in df.groupby("market"):
        best_target = group.loc[group["sharpe_ratio"].idxmax(), "target"]
        target_medians = group.groupby("target")["sharpe_ratio"].median()
        top_target = target_medians.idxmax()
        top_median = float(target_medians.max())
        second_median = float(target_medians.nlargest(2).iloc[-1]) if len(target_medians) > 1 else np.nan
        spread = top_median - second_median if len(target_medians) > 1 else np.nan
        rows.append(
            {
                "market": market,
                "best_sharpe_target": best_target,
                "top_median_sharpe_target": top_target,
                "top_median_sharpe": top_median,
                "second_median_sharpe": second_median,
                "median_sharpe_spread": spread,
                "concentrated_in_one_target": bool(
                    len(target_medians) > 1 and spread >= 0.25 and top_median > 0
                ),
            }
        )
    return pd.DataFrame(rows)


def _print_table(frame: pd.DataFrame) -> None:
    print(format_dataframe_for_display_eu(frame).to_string(index=False))


def print_report(
    df: pd.DataFrame,
    market_summary: pd.DataFrame,
    target_summary: pd.DataFrame,
    robust_params: pd.DataFrame,
    concentration: pd.DataFrame,
) -> None:
    print("Grid search analysis")
    print(f"Loaded {len(df)} successful runs from {RESULTS_PATH}")

    print("\nBest parameter sets by market (Sharpe):")
    sharpe_market = market_summary[market_summary["selection_metric"] == "sharpe_ratio"]
    _print_table(
        sharpe_market[
            [
                "market",
                "target",
                "rebalance_frequency",
                "entry_z",
                "exit_z",
                "sharpe_ratio",
                "total_return",
                "number_of_trades",
                "turnover",
                "suspicion_flags",
            ]
        ]
    )

    print("\nBest parameter sets by market (total return):")
    return_market = market_summary[market_summary["selection_metric"] == "total_return"]
    _print_table(
        return_market[
            [
                "market",
                "target",
                "rebalance_frequency",
                "entry_z",
                "exit_z",
                "total_return",
                "sharpe_ratio",
                "number_of_trades",
                "turnover",
                "suspicion_flags",
            ]
        ]
    )

    print("\nBest parameter sets by target (Sharpe):")
    sharpe_target = target_summary[target_summary["selection_metric"] == "sharpe_ratio"]
    _print_table(
        sharpe_target[
            [
                "market",
                "target",
                "rebalance_frequency",
                "entry_z",
                "exit_z",
                "sharpe_ratio",
                "total_return",
                "suspicion_flags",
            ]
        ]
    )

    print("\nCross-market comparison:")
    comparison = market_summary[market_summary["selection_metric"] == "sharpe_ratio"][
        [
            "market",
            "runs",
            "target_count",
            "median_sharpe",
            "median_total_return",
            "median_max_drawdown",
            "median_turnover",
            "positive_sharpe_share",
            "transaction_cost_bps",
        ]
    ]
    _print_table(comparison)

    print("\nTop robust parameter combinations (top 10% by target Sharpe):")
    _print_table(
        robust_params.head(15)[
            [
                "market",
                "rebalance_frequency",
                "entry_z",
                "exit_z",
                "top_decile_appearances",
                "appearance_rate",
                "targets_represented",
                "median_sharpe_in_decile",
            ]
        ]
    )

    print("\nSuspicious-result flags:")
    flagged = add_suspicion_flags(df)
    flagged = flagged[flagged["suspicion_flags"] != ""]
    print(f"Runs with at least one flag: {len(flagged)} / {len(df)}")
    print(
        flagged.groupby(["market", "suspicion_flags"], dropna=False)
        .size()
        .head(12)
        .to_string()
    )

    print("\nTarget concentration:")
    _print_table(concentration)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize grid search results.")
    parser.add_argument(
        "--results",
        type=Path,
        default=RESULTS_PATH,
        help="Path to grid_search_results.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    df = load_results(args.results)
    validate_results_row_count(
        df,
        MIN_GRID_SEARCH_RESULTS_ROWS,
        path=args.results,
    )

    market_summary = build_market_summary(df)
    target_summary = build_target_summary(df)
    robust_params = build_robust_params(df)
    concentration = detect_target_concentration(df, market_summary)
    best_by_market = build_best_by_market(df)
    best_by_target = build_best_by_target(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_table(market_summary, SUMMARY_BY_MARKET_PATH)
    save_table(target_summary, SUMMARY_BY_TARGET_PATH)
    save_table(robust_params, TOP_ROBUST_PARAMS_PATH)
    save_table(best_by_market, BEST_BY_MARKET_PATH)
    save_table(best_by_target, BEST_BY_TARGET_PATH)

    print_report(df, market_summary, target_summary, robust_params, concentration)
    print(
        f"\nSaved {SUMMARY_BY_MARKET_PATH.name}, "
        f"{SUMMARY_BY_TARGET_PATH.name}, {TOP_ROBUST_PARAMS_PATH.name}, "
        f"{BEST_BY_MARKET_PATH.name}, and {BEST_BY_TARGET_PATH.name} "
        f"to {OUTPUT_DIR}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
