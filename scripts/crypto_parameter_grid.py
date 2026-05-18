"""
Crypto-only staged parameter grid. Writes under results/crypto_parameter_grid/ only.

Does not modify results/grid_search/*.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Iterator

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
from sarb.universe import (  # noqa: E402
    UniverseSelectionResult,
    normalize_ticker_for_comparison,
    select_crypto_coverage_universe,
    select_priority_then_correlation_universe,
    select_priority_universe,
    strip_universe_of_target_equivalents,
)

OUT_DIR = PROJECT_ROOT / "results" / "crypto_parameter_grid"
PARTIAL_RESULTS = OUT_DIR / "partial_results.csv"
PARTIAL_FAILURES = OUT_DIR / "partial_failures.csv"
AGG_RESULTS = OUT_DIR / "crypto_parameter_grid_results.csv"
AGG_FAILURES = OUT_DIR / "crypto_parameter_grid_failures.csv"

CRYPTO_TARGETS = ["BTC", "ETH", "SOL", "XRP", "BNB"]

RESULT_COLUMNS = [
    "fingerprint",
    "stage",
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
    "pca_component_selection_method",
    "fixed_n_components",
    "zscore_lookback",
    "entry_z",
    "exit_z",
    "transaction_cost_bps",
    "annualization_factor",
    "min_asset_coverage",
    "min_universe_assets",
    "min_train_observations",
    "valid_rebalance_windows",
    "skipped_rebalance_windows",
    "valid_rebalance_share",
    "max_holding_period",
    "stop_loss_z",
    "stop_loss_exits",
    "time_stop_exits",
    "regression_type",
    "ridge_alpha",
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
    "fingerprint",
    "stage",
    "market",
    "target",
    "universe_selection_method",
    "universe_size_requested",
    "train_window",
    "rebalance_frequency",
    "pca_explained_variance",
    "pca_component_selection_method",
    "fixed_n_components",
    "zscore_lookback",
    "entry_z",
    "exit_z",
    "transaction_cost_bps",
    "min_asset_coverage",
    "min_universe_assets",
    "min_train_observations",
    "max_holding_period",
    "stop_loss_z",
    "regression_type",
    "ridge_alpha",
    "error_type",
    "error_message",
    "traceback_short",
]


def _expand(grid: dict[str, list[Any]]) -> Iterator[dict[str, Any]]:
    keys = list(grid.keys())
    for combo in product(*[grid[k] for k in keys]):
        yield dict(zip(keys, combo))


def _iter_core_jobs() -> Iterator[dict[str, Any]]:
    g = {
        "rebalance_frequency": [24, 72],
        "entry_z": [2.0, 2.5, 3.0],
        "exit_z": [0.25, 0.5],
        "train_window": [720, 1440, 2880],
        "zscore_lookback": [336, 720, 1440],
        "pca_explained_variance": [0.70, 0.80, 0.90],
        "transaction_cost_bps": [10],
        "universe_size": [30],
        "universe_selection_method": ["priority_with_coverage_fallback"],
        "min_asset_coverage": [0.60],
        "min_universe_assets": [5],
        "min_train_observations": [480],
        "pca_component_selection_method": ["explained_variance"],
        "fixed_n_components": [None],
        "regression_type": ["OLS"],
        "ridge_alpha": [1.0],
        "max_holding_period": [None],
        "stop_loss_z": [None],
    }
    yield from _expand(g)


def _iter_universe_jobs() -> Iterator[dict[str, Any]]:
    g = {
        "rebalance_frequency": [24, 72],
        "entry_z": [2.5, 3.0],
        "exit_z": [0.25, 0.5],
        "train_window": [1440, 2880],
        "zscore_lookback": [336, 720],
        "pca_explained_variance": [0.80],
        "transaction_cost_bps": [10],
        "universe_size": [20, 30, 40],
        "universe_selection_method": [
            "priority_with_coverage_fallback",
            "priority_then_correlation",
            "coverage",
        ],
        "min_asset_coverage": [0.50, 0.60, 0.70],
        "min_universe_assets": [5, 10],
        "min_train_observations": [480],
        "pca_component_selection_method": ["explained_variance"],
        "fixed_n_components": [None],
        "regression_type": ["OLS"],
        "ridge_alpha": [1.0],
        "max_holding_period": [None],
        "stop_loss_z": [None],
    }
    yield from _expand(g)


def _iter_risk_jobs() -> Iterator[dict[str, Any]]:
    g = {
        "rebalance_frequency": [24, 72],
        "entry_z": [2.5, 3.0],
        "exit_z": [0.25, 0.5],
        "train_window": [1440, 2880],
        "zscore_lookback": [336, 720],
        "pca_explained_variance": [0.80],
        "transaction_cost_bps": [10, 20, 50],
        "universe_size": [30],
        "universe_selection_method": ["priority_with_coverage_fallback"],
        "min_asset_coverage": [0.60],
        "min_universe_assets": [5],
        "min_train_observations": [480],
        "pca_component_selection_method": ["explained_variance"],
        "fixed_n_components": [None],
        "regression_type": ["OLS"],
        "ridge_alpha": [1.0],
        "max_holding_period": [168, 336, 720, None],
        "stop_loss_z": [3.5, 4.0, 5.0, None],
    }
    yield from _expand(g)


def _iter_model_jobs() -> Iterator[dict[str, Any]]:
    base = {
        "rebalance_frequency": [24, 72],
        "entry_z": [2.5],
        "exit_z": [0.25, 0.5],
        "train_window": [1440, 2880],
        "zscore_lookback": [336, 720],
        "transaction_cost_bps": [10],
        "universe_size": [30],
        "universe_selection_method": ["priority_with_coverage_fallback"],
        "min_asset_coverage": [0.60],
        "min_universe_assets": [5],
        "min_train_observations": [480],
        "max_holding_period": [None],
        "stop_loss_z": [None],
    }
    for rb, ez, xz, tw, zl, tc, us, um, mac, mua, mtr, mhp, sl in product(
        base["rebalance_frequency"],
        base["entry_z"],
        base["exit_z"],
        base["train_window"],
        base["zscore_lookback"],
        base["transaction_cost_bps"],
        base["universe_size"],
        base["universe_selection_method"],
        base["min_asset_coverage"],
        base["min_universe_assets"],
        base["min_train_observations"],
        base["max_holding_period"],
        base["stop_loss_z"],
    ):
        for pca_method in ["explained_variance", "fixed_n_components"]:
            if pca_method == "explained_variance":
                for ev in [0.70, 0.80, 0.90]:
                    for reg in ["OLS", "Ridge"]:
                        for ra in ([None] if reg == "OLS" else [0.1, 1.0, 10.0]):
                            yield {
                                "rebalance_frequency": rb,
                                "entry_z": ez,
                                "exit_z": xz,
                                "train_window": tw,
                                "zscore_lookback": zl,
                                "pca_component_selection_method": pca_method,
                                "pca_explained_variance": ev,
                                "fixed_n_components": None,
                                "regression_type": reg,
                                "ridge_alpha": ra,
                                "transaction_cost_bps": tc,
                                "universe_size": us,
                                "universe_selection_method": um,
                                "min_asset_coverage": mac,
                                "min_universe_assets": mua,
                                "min_train_observations": mtr,
                                "max_holding_period": mhp,
                                "stop_loss_z": sl,
                            }
            else:
                for ncomp in [3, 5, 10]:
                    for reg in ["OLS", "Ridge"]:
                        for ra in ([None] if reg == "OLS" else [0.1, 1.0, 10.0]):
                            yield {
                                "rebalance_frequency": rb,
                                "entry_z": ez,
                                "exit_z": xz,
                                "train_window": tw,
                                "zscore_lookback": zl,
                                "pca_component_selection_method": pca_method,
                                "pca_explained_variance": 0.80,
                                "fixed_n_components": ncomp,
                                "regression_type": reg,
                                "ridge_alpha": ra,
                                "transaction_cost_bps": tc,
                                "universe_size": us,
                                "universe_selection_method": um,
                                "min_asset_coverage": mac,
                                "min_universe_assets": mua,
                                "min_train_observations": mtr,
                                "max_holding_period": mhp,
                                "stop_loss_z": sl,
                            }


def _iter_aggressive_jobs() -> Iterator[dict[str, Any]]:
    g = {
        "rebalance_frequency": [24],
        "entry_z": [2.0, 2.5],
        "exit_z": [0.0],
        "train_window": [720, 1440, 2880],
        "zscore_lookback": [336, 720],
        "pca_explained_variance": [0.70, 0.80, 0.90],
        "transaction_cost_bps": [10, 20, 50],
        "max_holding_period": [168, 336, None],
        "stop_loss_z": [3.5, 4.0, None],
        "universe_size": [30],
        "universe_selection_method": ["priority_with_coverage_fallback"],
        "min_asset_coverage": [0.60],
        "min_universe_assets": [5],
        "min_train_observations": [480],
        "pca_component_selection_method": ["explained_variance"],
        "fixed_n_components": [None],
        "regression_type": ["OLS"],
        "ridge_alpha": [1.0],
    }
    yield from _expand(g)


STAGE_JOB_BUILDERS: dict[str, Any] = {
    "core": _iter_core_jobs,
    "universe": _iter_universe_jobs,
    "risk": _iter_risk_jobs,
    "model": _iter_model_jobs,
    "aggressive_crypto": _iter_aggressive_jobs,
}


def fingerprint_for_job(stage: str, target: str, params: dict[str, Any]) -> str:
    payload = {"stage": stage, "target": target, **{k: params[k] for k in sorted(params)}}
    return json.dumps(payload, sort_keys=True, default=str)


def prepare_crypto_prices(prices: pd.DataFrame) -> pd.DataFrame:
    return prices


def resolve_target_symbol(prices: pd.DataFrame, target: str) -> str:
    if target in prices.columns:
        return str(target)
    alternate = target.replace(".", "-")
    if alternate in prices.columns:
        return alternate
    raise KeyError(f"target asset {target!r} is not present in loaded prices")


def select_universe(
    prices: pd.DataFrame,
    coverage: pd.DataFrame,
    *,
    target: str,
    requested_size: int,
    method: str,
    train_window: int,
) -> UniverseSelectionResult:
    available_assets = coverage.loc[
        (coverage["observations"] > 0) & (coverage["missing_pct"] < 1.0),
        "symbol",
    ].astype(str).tolist()
    if method == "priority_with_coverage_fallback":
        return select_priority_universe(
            available_assets,
            target,
            "crypto",
            requested_size=requested_size,
            fallback_by_coverage=True,
            coverage=coverage,
            reference_prices=prices,
        )
    if method == "priority_then_correlation":
        return select_priority_then_correlation_universe(
            available_assets,
            target,
            requested_size=requested_size,
            prices=prices,
            train_window=train_window,
            coverage=coverage,
        )
    if method == "coverage":
        return select_crypto_coverage_universe(
            available_assets,
            target,
            requested_size=requested_size,
            coverage=coverage,
        )
    raise ValueError(f"unknown universe_selection_method {method!r}")


def build_run_config(base: RunConfig, params: dict[str, Any]) -> RunConfig:
    pca_ev = float(params.get("pca_explained_variance", base.pca_explained_variance))
    cfg = replace(
        base,
        train_window=int(params["train_window"]),
        rebalance_frequency=int(params["rebalance_frequency"]),
        pca_explained_variance=pca_ev,
        zscore_lookback=int(params["zscore_lookback"]),
        entry_z=float(params["entry_z"]),
        exit_z=float(params["exit_z"]),
        transaction_cost_bps=float(params["transaction_cost_bps"]),
    )
    cfg.validate()
    return cfg


def _append_row(path: Path, row: dict[str, Any], columns: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([{c: row.get(c) for c in columns}])
    write_header = not path.is_file()
    frame.to_csv(path, mode="a", index=False, header=write_header)


def _load_completed_fingerprints(path: Path) -> set[str]:
    if not path.is_file() or path.stat().st_size == 0:
        return set()
    df = pd.read_csv(path)
    if df.empty or "fingerprint" not in df.columns:
        return set()
    return set(df["fingerprint"].astype(str).tolist())


def _merged_done_fingerprints() -> set[str]:
    return _load_completed_fingerprints(PARTIAL_RESULTS) | _load_completed_fingerprints(PARTIAL_FAILURES)


def _save_stage_and_aggregate(stage: str, verbose: bool) -> None:
    """Write stage-specific CSV and refresh aggregate results from partial."""
    if not PARTIAL_RESULTS.is_file():
        return
    full = pd.read_csv(PARTIAL_RESULTS)
    if full.empty:
        return
    stage_df = full.loc[full["stage"] == stage].copy()
    stage_path = OUT_DIR / f"{stage}_results.csv"
    stage_df.to_csv(stage_path, index=False)
    if verbose:
        print(f"Wrote {stage_path.name} ({len(stage_df)} rows).", flush=True)

    agg = full.drop_duplicates(subset=["fingerprint"], keep="last")
    agg.to_csv(AGG_RESULTS, index=False)

    if PARTIAL_FAILURES.is_file():
        fails = pd.read_csv(PARTIAL_FAILURES)
        fails.drop_duplicates(subset=["fingerprint"], keep="last").to_csv(AGG_FAILURES, index=False)


def success_row(
    *,
    fingerprint: str,
    stage: str,
    target: str,
    universe: UniverseSelectionResult,
    run_config: RunConfig,
    params: dict[str, Any],
    diag: dict[str, Any],
    metrics: object,
    stop_loss_exits: int,
    time_stop_exits: int,
) -> dict[str, Any]:
    valid = int(diag["valid_rebalance_windows"])
    skipped = int(diag["skipped_rebalance_windows"])
    denom = valid + skipped
    share = float(valid / denom) if denom > 0 else float("nan")
    u_assets = strip_universe_of_target_equivalents(list(universe.assets), target)
    ra = params.get("ridge_alpha")
    if params.get("regression_type") == "OLS" or ra is None or (isinstance(ra, float) and pd.isna(ra)):
        ra_out = float("nan")
    else:
        ra_out = float(ra)
    fnc = params.get("fixed_n_components")
    return {
        "fingerprint": fingerprint,
        "stage": stage,
        "market": "crypto",
        "target": target,
        "universe_selection_method": universe.selection_method,
        "universe_size_requested": universe.universe_size_requested,
        "universe_size_actual": universe.universe_size_actual,
        "universe_assets": ",".join(u_assets),
        "missing_priority_assets": ",".join(universe.missing_priority_assets),
        "filled_from_fallback": ",".join(universe.filled_from_fallback),
        "train_window": run_config.train_window,
        "rebalance_frequency": run_config.rebalance_frequency,
        "pca_explained_variance": run_config.pca_explained_variance,
        "pca_component_selection_method": params.get("pca_component_selection_method", "explained_variance"),
        "fixed_n_components": fnc if fnc is not None else float("nan"),
        "zscore_lookback": run_config.zscore_lookback,
        "entry_z": run_config.entry_z,
        "exit_z": run_config.exit_z,
        "transaction_cost_bps": run_config.transaction_cost_bps,
        "annualization_factor": run_config.annualization_factor,
        "min_asset_coverage": float(params["min_asset_coverage"]),
        "min_universe_assets": int(params["min_universe_assets"]),
        "min_train_observations": int(params["min_train_observations"]),
        "valid_rebalance_windows": valid,
        "skipped_rebalance_windows": skipped,
        "valid_rebalance_share": share,
        "max_holding_period": params.get("max_holding_period"),
        "stop_loss_z": params.get("stop_loss_z"),
        "stop_loss_exits": int(stop_loss_exits),
        "time_stop_exits": int(time_stop_exits),
        "regression_type": params.get("regression_type", "OLS"),
        "ridge_alpha": ra_out,
        "total_return": float(getattr(metrics, "total_return")),
        "annualized_return": float(getattr(metrics, "annualized_return")),
        "annualized_volatility": float(getattr(metrics, "annualized_volatility")),
        "sharpe_ratio": float(getattr(metrics, "sharpe_ratio")),
        "max_drawdown": float(getattr(metrics, "max_drawdown")),
        "turnover": float(getattr(metrics, "turnover")),
        "number_of_trades": int(getattr(metrics, "number_of_trades")),
        "average_holding_period": float(getattr(metrics, "average_holding_period")),
        "hit_rate": float(getattr(metrics, "hit_rate")),
    }


def failure_row_dict(
    *,
    fingerprint: str,
    stage: str,
    target: str,
    params: dict[str, Any],
    method: str | None,
    requested_size: int | None,
    exc: BaseException,
) -> dict[str, Any]:
    tb = traceback.format_exc()
    if len(tb) > 4000:
        tb = tb[:4000] + "\n... (truncated)"
    ra = params.get("ridge_alpha")
    return {
        "fingerprint": fingerprint,
        "stage": stage,
        "market": "crypto",
        "target": target,
        "universe_selection_method": method,
        "universe_size_requested": requested_size,
        "train_window": params.get("train_window"),
        "rebalance_frequency": params.get("rebalance_frequency"),
        "pca_explained_variance": params.get("pca_explained_variance"),
        "pca_component_selection_method": params.get("pca_component_selection_method"),
        "fixed_n_components": params.get("fixed_n_components"),
        "zscore_lookback": params.get("zscore_lookback"),
        "entry_z": params.get("entry_z"),
        "exit_z": params.get("exit_z"),
        "transaction_cost_bps": params.get("transaction_cost_bps"),
        "min_asset_coverage": params.get("min_asset_coverage"),
        "min_universe_assets": params.get("min_universe_assets"),
        "min_train_observations": params.get("min_train_observations"),
        "max_holding_period": params.get("max_holding_period"),
        "stop_loss_z": params.get("stop_loss_z"),
        "regression_type": params.get("regression_type"),
        "ridge_alpha": ra,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "traceback_short": tb,
    }


def iter_stage_targets(stage: str, target_filter: str) -> list[str]:
    if target_filter == "all":
        return list(CRYPTO_TARGETS)
    if target_filter not in CRYPTO_TARGETS:
        raise ValueError(f"target must be one of {CRYPTO_TARGETS} or all")
    return [target_filter]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crypto-only staged parameter grid.")
    p.add_argument(
        "--stage",
        choices=["core", "universe", "risk", "model", "aggressive_crypto", "all"],
        default="core",
    )
    p.add_argument("--target", choices=[*CRYPTO_TARGETS, "all"], default="all")
    p.add_argument("--max-runs", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    stages = list(STAGE_JOB_BUILDERS.keys()) if args.stage == "all" else [args.stage]

    planned: list[tuple[str, str, dict[str, Any]]] = []
    for st in stages:
        for tgt in iter_stage_targets(st, args.target):
            for params in STAGE_JOB_BUILDERS[st]():
                planned.append((st, tgt, params))

    total = len(planned)
    if args.dry_run:
        print(f"Dry run: {total} planned runs.", flush=True)
        for i, (st, tgt, pr) in enumerate(planned[:50], start=1):
            print(f"{i}: stage={st} target={tgt} rebalance={pr['rebalance_frequency']} entry={pr['entry_z']}", flush=True)
        if total > 50:
            print(f"... ({total - 50} more)", flush=True)
        return 0

    prices = prepare_crypto_prices(load_market_prices("crypto"))
    coverage = coverage_summary(prices)
    base = load_run_config("crypto")

    done = _merged_done_fingerprints() if args.resume else set()
    executed = 0

    for idx, (stage, target, params) in enumerate(planned, start=1):
        if args.max_runs is not None and executed >= args.max_runs:
            break
        fp = fingerprint_for_job(stage, target, params)
        if fp in done:
            continue

        t0 = time.perf_counter()
        print(f"[{idx}/{total}] START target={target} stage={stage} ...", flush=True)
        universe = None
        try:
            resolved = resolve_target_symbol(prices, target)
            method = str(params["universe_selection_method"])
            universe = select_universe(
                prices,
                coverage,
                target=resolved,
                requested_size=int(params["universe_size"]),
                method=method,
                train_window=int(params["train_window"]),
            )
            u_assets = strip_universe_of_target_equivalents(list(universe.assets), resolved)
            if any(normalize_ticker_for_comparison(u) == normalize_ticker_for_comparison(resolved) for u in u_assets):
                raise ValueError("target leaked into universe after selection")
            run_config = build_run_config(base, params)
            ridge = params.get("ridge_alpha")
            ridge_f = 1.0 if ridge is None else float(ridge)
            res = run_unified_pipeline(
                prices,
                target=resolved,
                universe=u_assets,
                run_config=run_config,
                min_asset_coverage=float(params["min_asset_coverage"]),
                min_universe_assets=int(params["min_universe_assets"]),
                min_train_observations=int(params["min_train_observations"]),
                pca_component_selection_method=str(params.get("pca_component_selection_method", "explained_variance")),
                fixed_n_components=(
                    int(params["fixed_n_components"])
                    if params.get("fixed_n_components") is not None
                    and not (isinstance(params.get("fixed_n_components"), float) and pd.isna(params["fixed_n_components"]))
                    else None
                ),
                regression_type=str(params.get("regression_type", "OLS")),
                ridge_alpha=ridge_f,
                max_holding_period=params.get("max_holding_period"),
                stop_loss_z=params.get("stop_loss_z"),
            )
            diag = res.replication.diagnostics
            m = res.backtest.metrics
            elapsed = time.perf_counter() - t0
            row = success_row(
                fingerprint=fp,
                stage=stage,
                target=target,
                universe=universe,
                run_config=run_config,
                params=params,
                diag=diag,
                metrics=m,
                stop_loss_exits=res.backtest.stop_loss_exits,
                time_stop_exits=res.backtest.time_stop_exits,
            )
            _append_row(PARTIAL_RESULTS, row, RESULT_COLUMNS)
            print(
                f"[{idx}/{total}] SUCCESS sharpe={m.sharpe_ratio:.4f} total_return={m.total_return:.4f} elapsed={elapsed:.1f}s",
                flush=True,
            )
            done.add(fp)
            executed += 1
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            frow = failure_row_dict(
                fingerprint=fp,
                stage=stage,
                target=target,
                params=params,
                method=universe.selection_method if universe is not None else str(params.get("universe_selection_method")),
                requested_size=int(params["universe_size"]) if "universe_size" in params else None,
                exc=exc,
            )
            _append_row(PARTIAL_FAILURES, frow, FAILURE_COLUMNS)
            print(f"[{idx}/{total}] FAILED error={exc!r} elapsed={elapsed:.1f}s", flush=True)
            if args.verbose:
                traceback.print_exc()
            done.add(fp)
            executed += 1

    for st in stages:
        _save_stage_and_aggregate(st, args.verbose)

    print(f"Done. Outputs under {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
