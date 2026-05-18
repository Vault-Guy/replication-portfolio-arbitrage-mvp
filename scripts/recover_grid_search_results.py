"""One-off recovery: restore grid_search_results from current baseline + backup BRK + partial SOL."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from sarb.universe import normalize_ticker_for_comparison  # noqa: E402
from sarb.utils.io import (  # noqa: E402
    RESULT_METRIC_COLUMNS,
    save_table,
    validate_results_numeric_columns,
)

OUTPUT = PROJECT_ROOT / "results" / "grid_search"
MAIN = OUTPUT / "grid_search_results.csv"
PARTIAL = OUTPUT / "repair_partial_results.csv"
CORRUPTED_SNAPSHOT = OUTPUT / "grid_search_results_corrupted_backup.csv"
BACKUPS = OUTPUT / "backups"

METRIC_COLS = list(RESULT_METRIC_COLUMNS)
DEDUPE_COLS = [
    "market",
    "target",
    "train_window",
    "rebalance_frequency",
    "entry_z",
    "exit_z",
    "universe_selection_method",
]


def _load_analyze():
    path = PROJECT_ROOT / "scripts" / "analyze_grid_search.py"
    spec = importlib.util.spec_from_file_location("analyze_gs", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _print_csv_report(path: Path) -> None:
    print("---")
    print(f"path: {path}")
    if not path.is_file():
        print("  (missing)")
        return
    print(f"  size_bytes: {path.stat().st_size}")
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        print(f"  read_error: {exc}")
        return
    print(f"  rows: {len(df)}")
    print(f"  columns: {list(df.columns)}")
    if "market" in df.columns:
        print(f"  market value_counts:\n{df['market'].value_counts().to_string()}")
    if "target" in df.columns:
        print(f"  target value_counts (top 25):\n{df['target'].value_counts().head(25).to_string()}")


def _is_valid_full_results(df: pd.DataFrame) -> bool:
    required = {"market", "target", "rebalance_frequency", "entry_z", "exit_z"}
    if len(df) <= 100:
        return False
    if not required.issubset(df.columns):
        return False
    if df["market"].nunique() < 2:
        return False
    if df["target"].nunique() < 3:
        return False
    for col in METRIC_COLS:
        if col in df.columns and not pd.api.types.is_numeric_dtype(df[col]):
            return False
    return True


def _pick_latest_results_backup() -> Path | None:
    candidates = sorted(BACKUPS.glob("grid_search_results_*.csv"), reverse=True)
    best: tuple[int, Path] | None = None
    for p in candidates:
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if _is_valid_full_results(df):
            return p
        if len(df) > (best[0] if best else -1):
            best = (len(df), p)
    return best[1] if best else None


def _target_in_universe(row: pd.Series, target: str) -> bool:
    ua = row.get("universe_assets", "")
    if pd.isna(ua):
        return False
    tkey = normalize_ticker_for_comparison(target)
    for part in str(ua).split(","):
        part = part.strip()
        if part and normalize_ticker_for_comparison(part) == tkey:
            return True
    return False


def main() -> int:
    paths = [MAIN, PARTIAL, OUTPUT / "repair_partial_failures.csv"]
    paths += sorted(BACKUPS.glob("*.csv"))
    print("=== CSV inspection ===")
    for p in paths:
        _print_csv_report(Path(p))

    current = pd.read_csv(MAIN) if MAIN.is_file() else pd.DataFrame()
    print("\n=== Recovery logic ===")

    backup_path = _pick_latest_results_backup()
    print(f"Latest grid_search_results backup (by name): {backup_path}")
    if backup_path is not None:
        bdf = pd.read_csv(backup_path)
        print(f"  rows={len(bdf)}, valid_full_by_rule={_is_valid_full_results(bdf)}")

    # Preserve current file as user-requested snapshot name
    if MAIN.is_file():
        CORRUPTED_SNAPSHOT.write_bytes(MAIN.read_bytes())
        print(f"Saved snapshot of current main file to: {CORRUPTED_SNAPSHOT}")

    # Baseline: prefer strict full backup; else use current table if it is the largest valid body
    if backup_path is not None and _is_valid_full_results(pd.read_csv(backup_path)):
        restored = pd.read_csv(backup_path)
        print("Restored from valid full backup.")
    else:
        restored = current.copy()
        print(
            "No backup with >100 rows and full multi-market structure; "
            "using current grid_search_results.csv as baseline (13-target successful grid)."
        )

    brk_src = None
    if backup_path is not None:
        bdf = pd.read_csv(backup_path)
        m = (bdf["market"] == "usa") & (bdf["target"] == "BRK.B")
        if m.any():
            brk_src = bdf.loc[m].copy()
            print(f"BRK.B rows from backup {backup_path.name}: {len(brk_src)}")

    if PARTIAL.is_file():
        pdf = pd.read_csv(PARTIAL)
        sol_src = pdf.loc[(pdf["market"] == "crypto") & (pdf["target"] == "SOL")].copy()
        print(f"SOL rows from repair_partial_results.csv: {len(sol_src)}")
    else:
        sol_src = pd.DataFrame(columns=restored.columns)

    # Drop existing BRK / SOL from restored before merge
    mask_drop = pd.Series(False, index=restored.index)
    if "market" in restored.columns and "target" in restored.columns:
        mask_drop |= (restored["market"] == "usa") & (restored["target"] == "BRK.B")
        mask_drop |= (restored["market"] == "crypto") & (restored["target"] == "SOL")
    restored = restored.loc[~mask_drop].reset_index(drop=True)

    pieces = [restored]
    if brk_src is not None and not brk_src.empty:
        pieces.append(brk_src)
    if not sol_src.empty:
        pieces.append(sol_src)

    merged = pd.concat(pieces, ignore_index=True)
    dedupe_subset = [c for c in DEDUPE_COLS if c in merged.columns]
    if dedupe_subset:
        merged = merged.drop_duplicates(subset=dedupe_subset, keep="last")

    save_table(merged, MAIN, validate_metrics=True)

    analyze = _load_analyze()
    save_table(analyze.build_market_summary(merged), OUTPUT / "summary_by_market.csv")
    save_table(analyze.build_target_summary(merged), OUTPUT / "summary_by_target.csv")
    save_table(analyze.build_robust_params(merged), OUTPUT / "top_robust_params.csv")
    save_table(analyze.build_best_by_market(merged), OUTPUT / "best_by_market.csv")
    save_table(analyze.build_best_by_target(merged), OUTPUT / "best_by_target.csv")

    # --- Final validation ---
    final = pd.read_csv(MAIN)
    assert len(final) > 100, f"expected >100 rows, got {len(final)}"
    n_brk = int(((final["market"] == "usa") & (final["target"] == "BRK.B")).sum())
    n_sol = int(((final["market"] == "crypto") & (final["target"] == "SOL")).sum())
    if brk_src is not None and len(brk_src) > 0:
        assert n_brk == 96, f"expected 96 BRK.B rows, got {n_brk}"
    if len(sol_src) > 0:
        assert n_sol == 96, f"expected 96 SOL rows, got {n_sol}"
    for sym, mkt in [("BRK.B", "usa"), ("SOL", "crypto")]:
        sub = final[(final["market"] == mkt) & (final["target"] == sym)]
        for _, row in sub.iterrows():
            assert not _target_in_universe(row, sym), f"{sym} in own universe"
    for col in METRIC_COLS:
        if col in final.columns:
            assert pd.api.types.is_numeric_dtype(final[col]), col

    print("\n=== FINAL RECOVERY REPORT ===")
    print(f"Restored main file: {MAIN}")
    print(f"Final row count: {len(final)}")
    print(f"BRK.B rows: {n_brk}")
    print(f"SOL rows: {n_sol}")
    print(f"markets: {final['market'].value_counts().to_dict()}")
    print(f"Snapshot of pre-recovery file: {CORRUPTED_SNAPSHOT}")
    print(f"BRK source: {backup_path if brk_src is not None else 'none'}")
    print(f"SOL source: {PARTIAL if len(sol_src) else 'none'}")
    print("Regenerated: best_by_*, summary_by_*, top_robust_params.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
