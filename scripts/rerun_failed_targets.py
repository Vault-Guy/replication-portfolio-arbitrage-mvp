from __future__ import annotations

import argparse
import importlib.util
import sys
import time
import traceback
from dataclasses import replace
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sarb.run import (  # noqa: E402
    load_market_prices,
    load_run_config,
    run_unified_pipeline,
)
from sarb.universe import (  # noqa: E402
    normalize_ticker_for_comparison,
    strip_universe_of_target_equivalents,
)
from sarb.utils.io import (  # noqa: E402
    RESULT_METRIC_COLUMNS,
    load_results_table,
    save_table,
    validate_results_numeric_columns,
    validate_results_row_count,
)

OUTPUT_DIR = PROJECT_ROOT / "results" / "grid_search"
BACKUP_DIR = OUTPUT_DIR / "backups"
RESULTS_PATH = OUTPUT_DIR / "grid_search_results.csv"
FAILURES_PATH = OUTPUT_DIR / "grid_search_failures.csv"
BEST_BY_MARKET_PATH = OUTPUT_DIR / "best_by_market.csv"
BEST_BY_TARGET_PATH = OUTPUT_DIR / "best_by_target.csv"
SUMMARY_BY_MARKET_PATH = OUTPUT_DIR / "summary_by_market.csv"
SUMMARY_BY_TARGET_PATH = OUTPUT_DIR / "summary_by_target.csv"
TOP_ROBUST_PARAMS_PATH = OUTPUT_DIR / "top_robust_params.csv"
PARTIAL_RESULTS_PATH = OUTPUT_DIR / "repair_partial_results.csv"
PARTIAL_FAILURES_PATH = OUTPUT_DIR / "repair_partial_failures.csv"

ALL_REPAIR_TARGETS: list[tuple[str, str]] = [
    ("usa", "BRK.B"),
    ("crypto", "SOL"),
]

ENTRY_Z_VALUES = [1.0, 1.5, 2.0, 2.5, 3.0]
EXIT_Z_VALUES = [0.0, 0.25, 0.5, 0.75, 1.0]
UNIVERSE_SIZE_REQUESTED = 30

MIN_GRID_SEARCH_RESULTS_ROWS = 100


def _load_grid_search_module():
    path = PROJECT_ROOT / "scripts" / "grid_search.py"
    spec = importlib.util.spec_from_file_location("grid_search_repair", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_analyze_module():
    path = PROJECT_ROOT / "scripts" / "analyze_grid_search.py"
    spec = importlib.util.spec_from_file_location("analyze_grid_search_repair", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def valid_zscore_pairs() -> list[tuple[float, float]]:
    pairs: list[tuple[float, float]] = []
    for entry_z, exit_z in product(ENTRY_Z_VALUES, EXIT_Z_VALUES):
        if exit_z >= entry_z:
            continue
        pairs.append((entry_z, exit_z))
    return pairs


def repair_targets_for_args(market: str, target: str) -> list[tuple[str, str]]:
    pairs = list(ALL_REPAIR_TARGETS)
    if market != "all":
        pairs = [p for p in pairs if p[0] == market]
    if target != "all":
        pairs = [p for p in pairs if p[1] == target]
    return pairs


def iter_repair_jobs(gs, repair_pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for market, tgt in repair_pairs:
        base_config = load_run_config(market)
        train_window = gs.TRAIN_WINDOWS[market]
        for rebalance_frequency in gs.REBALANCE_FREQUENCIES[market]:
            for entry_z, exit_z in valid_zscore_pairs():
                jobs.append(
                    {
                        "market": market,
                        "target": tgt,
                        "base_config": base_config,
                        "train_window": train_window,
                        "rebalance_frequency": rebalance_frequency,
                        "entry_z": entry_z,
                        "exit_z": exit_z,
                    }
                )
    return jobs


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_file(src: Path, stamp: str) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest = BACKUP_DIR / f"{src.stem}_{stamp}{src.suffix}"
    if src.is_file():
        dest.write_bytes(src.read_bytes())
    else:
        pd.DataFrame().to_csv(dest, index=False)
    return dest


def _target_in_universe_assets(universe_assets: str, target: str) -> bool:
    if pd.isna(universe_assets) or not str(universe_assets).strip():
        return False
    tkey = normalize_ticker_for_comparison(target)
    for part in str(universe_assets).split(","):
        part = part.strip()
        if not part:
            continue
        if normalize_ticker_for_comparison(part) == tkey:
            return True
    return False


def _assert_universe_excludes_target(resolved_target: str, assets: list[str]) -> None:
    tkey = normalize_ticker_for_comparison(resolved_target)
    keys = {normalize_ticker_for_comparison(x) for x in assets}
    assert tkey not in keys, "target must not appear in PCA universe (normalized)"


def _sanitize_universe_selection(
    universe: Any,
    *,
    resolved_target: str,
    gs: Any,
    prices: pd.DataFrame,
    market: str,
) -> Any:
    """Assert universe excludes target (normalized); on failure reselect; then strip aliases."""
    try:
        _assert_universe_excludes_target(resolved_target, list(universe.assets))
    except AssertionError:
        universe = gs.select_market_universe(
            prices,
            market=market,
            target=resolved_target,
            requested_size=UNIVERSE_SIZE_REQUESTED,
        )
        _assert_universe_excludes_target(resolved_target, list(universe.assets))

    assets = strip_universe_of_target_equivalents(list(universe.assets), resolved_target)
    _assert_universe_excludes_target(resolved_target, assets)
    if len(assets) < 2:
        raise ValueError("universe has fewer than two assets after excluding the target")
    if len(assets) != len(universe.assets):
        universe = replace(universe, assets=assets, universe_size_actual=len(assets))
    return universe


def _append_partial_row(path: Path, row: dict[str, Any], columns: list[str], *, first: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([row], columns=columns)
    frame.to_csv(path, mode="w" if first else "a", index=False, header=first)


def regenerate_summaries(results: pd.DataFrame) -> None:
    analyze = _load_analyze_module()
    if len(results) >= MIN_GRID_SEARCH_RESULTS_ROWS:
        validate_results_row_count(results, MIN_GRID_SEARCH_RESULTS_ROWS, path=RESULTS_PATH)
    market_summary = analyze.build_market_summary(results)
    target_summary = analyze.build_target_summary(results)
    robust_params = analyze.build_robust_params(results)
    best_by_market = analyze.build_best_by_market(results)
    best_by_target = analyze.build_best_by_target(results)
    save_table(market_summary, SUMMARY_BY_MARKET_PATH)
    save_table(target_summary, SUMMARY_BY_TARGET_PATH)
    save_table(robust_params, TOP_ROBUST_PARAMS_PATH)
    save_table(best_by_market, BEST_BY_MARKET_PATH)
    save_table(best_by_target, BEST_BY_TARGET_PATH)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerun grid search for BRK.B and/or SOL repair jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing.")
    parser.add_argument(
        "--market",
        choices=["usa", "crypto", "all"],
        default="all",
        help="Which market(s) to repair.",
    )
    parser.add_argument(
        "--target",
        choices=["BRK.B", "SOL", "all"],
        default="all",
        help="Which target(s) to repair.",
    )
    parser.add_argument("--max-runs", type=int, default=None, help="Cap number of executed jobs.")
    parser.add_argument("--verbose", action="store_true", help="Print extra diagnostics.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gs = _load_grid_search_module()
    repair_pairs = repair_targets_for_args(args.market, args.target)
    if not repair_pairs:
        print("No repair targets match filters.", flush=True)
        return 1

    jobs = iter_repair_jobs(gs, repair_pairs)
    if args.max_runs is not None:
        jobs = jobs[: args.max_runs]

    print(
        f"Planned runs: {len(jobs)} for {repair_pairs} (market={args.market}, target={args.target})",
        flush=True,
    )

    if args.dry_run:
        for i, job in enumerate(jobs, 1):
            print(
                f"  {i}/{len(jobs)} market={job['market']} target={job['target']} "
                f"rebalance_frequency={job['rebalance_frequency']} entry_z={job['entry_z']} exit_z={job['exit_z']}",
                flush=True,
            )
        return 0

    stamp = _timestamp()
    paths_to_backup = [
        RESULTS_PATH,
        FAILURES_PATH,
        BEST_BY_TARGET_PATH,
        BEST_BY_MARKET_PATH,
    ]
    backup_paths: list[Path] = []
    for p in paths_to_backup:
        backup_paths.append(_backup_file(p, stamp))

    for p in (PARTIAL_RESULTS_PATH, PARTIAL_FAILURES_PATH):
        if p.exists():
            p.unlink()

    results_before = load_results_table(RESULTS_PATH) if RESULTS_PATH.is_file() else pd.DataFrame()
    n_results_before = len(results_before)

    failures_before = load_results_table(FAILURES_PATH) if FAILURES_PATH.is_file() else pd.DataFrame()

    mask_results_remove = pd.Series(False, index=results_before.index)
    for mkt, tgt in repair_pairs:
        if not results_before.empty and "market" in results_before.columns:
            mask_results_remove |= (results_before["market"] == mkt) & (results_before["target"] == tgt)

    mask_failures_remove = pd.Series(False, index=failures_before.index)
    for mkt, tgt in repair_pairs:
        if not failures_before.empty and "market" in failures_before.columns:
            mask_failures_remove |= (failures_before["market"] == mkt) & (failures_before["target"] == tgt)

    results_kept = results_before.loc[~mask_results_remove].reset_index(drop=True)
    failures_kept = failures_before.loc[~mask_failures_remove].reset_index(drop=True)

    market_prices: dict[str, pd.DataFrame] = {}
    market_universes: dict[tuple[str, str], Any] = {}
    failures_new: list[dict[str, Any]] = []
    results_new: list[dict[str, Any]] = []
    total_skipped_windows = 0
    partial_res_first = True
    partial_fail_first = True

    for market, target in repair_pairs:
        prices = gs.prepare_market_prices(market, load_market_prices(market))
        market_prices[market] = prices
        try:
            resolved_target = gs.resolve_target_symbol(prices, target)
        except KeyError as exc:
            failures_new.append(
                gs.failure_row(
                    {
                        "market": market,
                        "target": target,
                        "train_window": gs.TRAIN_WINDOWS[market],
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
            universe = gs.select_market_universe(
                prices,
                market=market,
                target=resolved_target,
                requested_size=UNIVERSE_SIZE_REQUESTED,
            )
            universe = _sanitize_universe_selection(
                universe,
                resolved_target=resolved_target,
                gs=gs,
                prices=prices,
                market=market,
            )
        except Exception as exc:
            failures_new.append(
                gs.failure_row(
                    {
                        "market": market,
                        "target": target,
                        "train_window": gs.TRAIN_WINDOWS[market],
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
    for i, job in enumerate(jobs, 1):
        market = job["market"]
        target = job["target"]
        universe = market_universes.get((market, target))
        if universe is None:
            continue

        resolved_target = gs.resolve_target_symbol(market_prices[market], target)
        try:
            universe_run = _sanitize_universe_selection(
                universe,
                resolved_target=resolved_target,
                gs=gs,
                prices=market_prices[market],
                market=market,
            )
        except Exception as exc:
            print(f"[{i}/{len(jobs)}] SKIP universe sanitize failed: {exc}", flush=True)
            continue

        print(
            f"[{i}/{len(jobs)}] START market={market} target={target} "
            f"rebalance={job['rebalance_frequency']} entry_z={job['entry_z']} exit_z={job['exit_z']} "
            f"universe_size={universe_run.universe_size_actual}",
            flush=True,
        )
        t0 = time.perf_counter()
        try:
            run_config = gs.build_run_config(job)
            result = run_unified_pipeline(
                market_prices[market],
                target=resolved_target,
                universe=universe_run.assets,
                run_config=run_config,
            )
            diag = result.replication.diagnostics
            total_skipped_windows += int(diag.get("skipped_rebalance_windows", 0) or 0)
            row = gs.result_row(
                market=market,
                target=target,
                universe=universe_run,
                run_config=run_config,
                metrics=result.backtest.metrics,
            )
            results_new.append(row)
            _append_partial_row(PARTIAL_RESULTS_PATH, row, gs.RESULT_COLUMNS, first=partial_res_first)
            partial_res_first = False
            elapsed = time.perf_counter() - t0
            m = result.backtest.metrics
            print(
                f"[{i}/{len(jobs)}] SUCCESS sharpe={m.sharpe_ratio:.4f} total_return={m.total_return:.4f} "
                f"elapsed={elapsed:.2f}s",
                flush=True,
            )
            if args.verbose:
                print(f"    skipped_rebalance_windows={diag.get('skipped_rebalance_windows')}", flush=True)
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            frow = gs.failure_row(
                job,
                universe=universe_run,
                error=f"{exc.__class__.__name__}: {exc}",
            )
            failures_new.append(frow)
            _append_partial_row(PARTIAL_FAILURES_PATH, frow, gs.FAILURE_COLUMNS, first=partial_fail_first)
            partial_fail_first = False
            print(f"[{i}/{len(jobs)}] FAILED error={exc} elapsed={elapsed:.2f}s", flush=True)
            traceback.print_exc()

    results_added = pd.DataFrame(results_new, columns=gs.RESULT_COLUMNS)
    failures_appended = pd.DataFrame(failures_new, columns=gs.FAILURE_COLUMNS)

    results_merged = pd.concat([results_kept, results_added], ignore_index=True)
    failures_merged = pd.concat([failures_kept, failures_appended], ignore_index=True)

    save_table(results_merged, RESULTS_PATH, validate_metrics=True)
    save_table(failures_merged, FAILURES_PATH)

    regenerate_summaries(results_merged)

    results_after = load_results_table(RESULTS_PATH)
    if len(results_after) <= n_results_before and not results_added.empty:
        print("Warning: row count did not increase despite new successful rows.", flush=True)

    validate_results_numeric_columns(results_after)

    for mkt, tgt in repair_pairs:
        sub = results_after[(results_after["market"] == mkt) & (results_after["target"] == tgt)]
        for _, row in sub.iterrows():
            if _target_in_universe_assets(str(row.get("universe_assets", "")), tgt):
                raise ValueError(f"{tgt} must not appear in its own universe_assets")
            for col in RESULT_METRIC_COLUMNS:
                if col in row and pd.isna(row[col]):
                    raise ValueError(f"successful row missing metric {col}")

    n_brk_new = len(results_added[(results_added["market"] == "usa") & (results_added["target"] == "BRK.B")])
    n_sol_new = len(results_added[(results_added["market"] == "crypto") & (results_added["target"] == "SOL")])
    f_brk = failures_merged[(failures_merged["market"] == "usa") & (failures_merged["target"] == "BRK.B")]
    f_sol = failures_merged[(failures_merged["market"] == "crypto") & (failures_merged["target"] == "SOL")]

    print("\n=== Repair report ===", flush=True)
    print(f"Repair pairs: {repair_pairs}", flush=True)
    print(f"Old result rows removed (matched pairs): {int(mask_results_remove.sum())}", flush=True)
    print(f"Old failure rows removed (matched pairs): {int(mask_failures_remove.sum())}", flush=True)
    print(f"New BRK.B successful rows added: {n_brk_new}", flush=True)
    print(f"New SOL successful rows added: {n_sol_new}", flush=True)
    print(f"Remaining BRK.B failure rows: {len(f_brk)}", flush=True)
    print(f"Remaining SOL failure rows: {len(f_sol)}", flush=True)
    print(f"Total skipped rebalance windows (sum over successful runs): {total_skipped_windows}", flush=True)
    print(f"Updated results: {RESULTS_PATH}", flush=True)
    print(f"Updated failures: {FAILURES_PATH}", flush=True)
    print(f"Partial results: {PARTIAL_RESULTS_PATH}", flush=True)
    print(f"Partial failures: {PARTIAL_FAILURES_PATH}", flush=True)
    print(f"Regenerated summaries under: {OUTPUT_DIR}", flush=True)
    print("Backups:", flush=True)
    for bp in backup_paths:
        print(f"  {bp}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
