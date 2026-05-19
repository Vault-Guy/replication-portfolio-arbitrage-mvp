"""
Детальный анализ диапазонов параметров из результатов грид-сёрча.

Вход:  results/grid_search/grid_search_results.csv (только чтение).
Что делает: строит частотные таблицы параметров в топ-5/10/20% по Sharpe,
            считает медианные метрики по каждому значению rebalance_frequency,
            entry_z, exit_z и их комбинациям, выявляет наиболее robust-комбинации
            и подозрительные строки (мало сделок, глубокая просадка, высокий оборот),
            генерирует Markdown-отчёт.
Результат: results/parameter_analysis/top10_parameter_frequencies_global.csv,
           results/parameter_analysis/top10_parameter_frequencies_by_market.csv,
           results/parameter_analysis/top10_parameter_frequencies_by_target.csv,
           results/parameter_analysis/parameter_frequencies_all_top_groups_*.csv,
           results/parameter_analysis/median_performance_by_*.csv,
           results/parameter_analysis/robust_parameter_combos.csv,
           results/parameter_analysis/suspicious_top_results.csv,
           results/parameter_analysis/parameter_analysis_report.md.
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = PROJECT_ROOT / "results" / "grid_search" / "grid_search_results.csv"
OUT_DIR = PROJECT_ROOT / "results" / "parameter_analysis"

METRIC_COLS = [
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


def _md_table(frame: pd.DataFrame, *, index: bool = False) -> str:
    """GitHub-flavored markdown pipe table without optional tabulate dependency."""

    def _cell(v: object) -> str:
        s = str(v).replace("|", "\\|")
        return s

    if frame.empty and not index:
        return "_Empty table._"
    show = frame.reset_index() if index else frame.copy()
    if show.empty:
        return "_Empty table._"
    cols = [str(c) for c in show.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in show.iterrows():
        lines.append("| " + " | ".join(_cell(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


def _ensure_out_dir() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def _save_csv(df: pd.DataFrame, name: str) -> Path:
    path = OUT_DIR / name
    df.to_csv(path, index=False)
    return path


def _validate(df: pd.DataFrame) -> None:
    for col in METRIC_COLS:
        if col not in df.columns:
            raise ValueError(f"Missing metric column: {col}")
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise TypeError(f"Column {col!r} must be numeric, got {df[col].dtype}")


def _top_mask(df: pd.DataFrame, col: str, frac: float, *, high: bool = True) -> pd.Series:
    """Top frac of distribution (e.g. frac=0.1 => best 10%)."""
    q = 1.0 - frac if high else frac
    thresh = df[col].quantile(q)
    return df[col] >= thresh if high else df[col] <= thresh


def _pair_col(df: pd.DataFrame, a: str, b: str, sep: str = "|") -> pd.Series:
    return df[a].astype(str) + sep + df[b].astype(str)


def _triple_col(df: pd.DataFrame) -> pd.Series:
    return (
        df["rebalance_frequency"].astype(str)
        + "|"
        + df["entry_z"].astype(str)
        + "|"
        + df["exit_z"].astype(str)
    )


def _frequency_table(sub: pd.DataFrame, col: str) -> pd.DataFrame:
    vc = sub[col].value_counts().sort_index()
    return pd.DataFrame({col: vc.index, "count": vc.values, "share": (vc.values / len(sub)).astype(float)})


def _frequency_tables_for_subset(sub: pd.DataFrame, label: str) -> dict[str, pd.DataFrame]:
    if sub.empty:
        return {}
    out: dict[str, pd.DataFrame] = {}
    for dim, col in [
        ("rebalance_frequency", "rebalance_frequency"),
        ("entry_z", "entry_z"),
        ("exit_z", "exit_z"),
        ("entry_exit_pair", "_pair_e_e"),
        ("rebalance_entry_pair", "_pair_r_e"),
        ("full_combo", "_triple"),
    ]:
        if col.startswith("_"):
            if col == "_pair_e_e":
                s = _pair_col(sub, "entry_z", "exit_z")
            elif col == "_pair_r_e":
                s = _pair_col(sub, "rebalance_frequency", "entry_z")
            else:
                s = _triple_col(sub)
            t = s.value_counts().sort_index()
            out[dim] = pd.DataFrame({"value": t.index, "count": t.values, "share": (t.values / len(sub)).astype(float)})
        else:
            out[dim] = _frequency_table(sub, col)
        out[dim].insert(0, "group", label)
    return out


def _stack_freq_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for dim, frame in tables.items():
        f = frame.copy()
        f.insert(0, "dimension", dim)
        rows.append(f)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _build_top10_frequency_exports(df: pd.DataFrame) -> None:
    """Top 10% by sharpe_ratio — global, by market, by target (required filenames)."""
    m = _top_mask(df, "sharpe_ratio", 0.10, high=True)
    sub = df.loc[m]
    g = _stack_freq_tables(_frequency_tables_for_subset(sub, "top10_sharpe"))
    _save_csv(g, "top10_parameter_frequencies_global.csv")

    parts: list[pd.DataFrame] = []
    for market, grp in sub.groupby("market"):
        t = _stack_freq_tables(_frequency_tables_for_subset(grp, f"top10_sharpe|{market}"))
        t.insert(1, "market", market)
        parts.append(t)
    _save_csv(pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(), "top10_parameter_frequencies_by_market.csv")

    parts = []
    for (market, target), grp in sub.groupby(["market", "target"]):
        t = _stack_freq_tables(_frequency_tables_for_subset(grp, f"top10_sharpe|{market}|{target}"))
        t.insert(1, "market", market)
        t.insert(2, "target", target)
        parts.append(t)
    _save_csv(pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(), "top10_parameter_frequencies_by_target.csv")


def _all_groups_frequency_supplement(df: pd.DataFrame) -> None:
    """Steps 4–5: all top groups — global, by market, by target (stacked long CSV)."""
    groups: list[tuple[str, pd.Series]] = [
        ("top5_sharpe", _top_mask(df, "sharpe_ratio", 0.05, high=True)),
        ("top10_sharpe", _top_mask(df, "sharpe_ratio", 0.10, high=True)),
        ("top20_sharpe", _top_mask(df, "sharpe_ratio", 0.20, high=True)),
        ("top10_total_return", _top_mask(df, "total_return", 0.10, high=True)),
    ]
    stacks: list[pd.DataFrame] = []
    stacks_mkt: list[pd.DataFrame] = []
    stacks_tgt: list[pd.DataFrame] = []
    for name, mask in groups:
        sub = df.loc[mask]
        stacks.append(_stack_freq_tables(_frequency_tables_for_subset(sub, name)))
        for market, grp in sub.groupby("market"):
            t = _stack_freq_tables(_frequency_tables_for_subset(grp, f"{name}|{market}"))
            t.insert(1, "market", market)
            stacks_mkt.append(t)
        for (market, target), grp in sub.groupby(["market", "target"]):
            t = _stack_freq_tables(_frequency_tables_for_subset(grp, f"{name}|{market}|{target}"))
            t.insert(1, "market", market)
            t.insert(2, "target", target)
            stacks_tgt.append(t)
    if stacks:
        _save_csv(pd.concat(stacks, ignore_index=True), "parameter_frequencies_all_top_groups_global.csv")
    if stacks_mkt:
        _save_csv(pd.concat(stacks_mkt, ignore_index=True), "parameter_frequencies_all_top_groups_by_market.csv")
    if stacks_tgt:
        _save_csv(pd.concat(stacks_tgt, ignore_index=True), "parameter_frequencies_all_top_groups_by_target.csv")


def _agg_median_block(
    df: pd.DataFrame,
    group_cols: list[str],
    out_name: str,
) -> None:
    g = df.groupby(group_cols, dropna=False)
    out = g.agg(
        mean_total_return=("total_return", "mean"),
        median_total_return=("total_return", "median"),
        mean_sharpe_ratio=("sharpe_ratio", "mean"),
        median_sharpe_ratio=("sharpe_ratio", "median"),
        median_max_drawdown=("max_drawdown", "median"),
        median_turnover=("turnover", "median"),
        median_number_of_trades=("number_of_trades", "median"),
        count=("sharpe_ratio", "size"),
    ).reset_index()
    rename_map: dict[str, str] = {}
    for c in out.columns:
        if c == "_entry_exit":
            rename_map[c] = "entry_exit_pair"
        elif c == "_full":
            rename_map[c] = "rebalance_entry_exit"
        elif c.startswith("_"):
            rename_map[c] = c[1:]
    if rename_map:
        out = out.rename(columns=rename_map)
    _save_csv(out, out_name)


def _median_performance_exports(df: pd.DataFrame) -> None:
    for col, fname in [
        ("rebalance_frequency", "median_performance_by_rebalance.csv"),
        ("entry_z", "median_performance_by_entry_z.csv"),
        ("exit_z", "median_performance_by_exit_z.csv"),
    ]:
        _agg_median_block(df, ["market", col], fname)

    df = df.copy()
    df["_entry_exit"] = _pair_col(df, "entry_z", "exit_z")
    _agg_median_block(df, ["market", "_entry_exit"], "median_performance_by_entry_exit_pair.csv")

    df["_full"] = _triple_col(df)
    _agg_median_block(df, ["market", "_full"], "median_performance_by_full_param_combo.csv")


def _ranks(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["rank_sharpe"] = d["sharpe_ratio"].rank(ascending=False, method="average")
    d["rank_return"] = d["total_return"].rank(ascending=False, method="average")
    return d


def _robust_combos(df: pd.DataFrame) -> pd.DataFrame:
    d = _ranks(df)
    top10 = _top_mask(d, "sharpe_ratio", 0.10, high=True)
    d["_combo"] = _triple_col(d)

    rows: list[dict[str, float | int | str]] = []
    for combo, grp in d.groupby("_combo"):
        in_top = grp.loc[top10.loc[grp.index]]
        targets_hit = in_top.groupby(["market", "target"]).ngroups
        markets_hit = in_top["market"].nunique()
        tgt_only = in_top.groupby("target").ngroups
        mkt_only = in_top["market"].nunique()
        rows.append(
            {
                "rebalance_entry_exit": combo,
                "n_rows_total": len(grp),
                "n_distinct_targets_top10_sharpe": tgt_only,
                "n_distinct_markets_top10_sharpe": mkt_only,
                "n_distinct_market_target_pairs_top10_sharpe": targets_hit,
                "mean_rank_sharpe": float(grp["rank_sharpe"].mean()),
                "median_rank_sharpe": float(grp["rank_sharpe"].median()),
                "mean_rank_total_return": float(grp["rank_return"].mean()),
                "median_max_drawdown": float(grp["max_drawdown"].median()),
                "median_turnover": float(grp["turnover"].median()),
                "median_sharpe_ratio": float(grp["sharpe_ratio"].median()),
                "median_total_return": float(grp["total_return"].median()),
            }
        )
    out = pd.DataFrame(rows).sort_values("median_sharpe_ratio", ascending=False)
    return out


def _suspicious(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    top_sh = df.loc[_top_mask(df, "sharpe_ratio", 0.10, high=True)].copy()
    t95 = float(df["turnover"].quantile(0.95))

    flags: list[str] = []
    suspicious_mask = pd.Series(False, index=top_sh.index)
    if (top_sh["number_of_trades"] < 10).any():
        suspicious_mask |= top_sh["number_of_trades"] < 10
        flags.append("few_trades_lt_10")
    if (top_sh["max_drawdown"] < -0.70).any():
        suspicious_mask |= top_sh["max_drawdown"] < -0.70
        flags.append("deep_drawdown_lt_-0.70")
    if (top_sh["turnover"] > t95).any():
        suspicious_mask |= top_sh["turnover"] > t95
        flags.append(f"high_turnover_gt_p95_{t95:.6f}")

    suspicious = top_sh.loc[suspicious_mask].copy()
    suspicious["flags"] = ""
    for i in suspicious.index:
        fl: list[str] = []
        if top_sh.loc[i, "number_of_trades"] < 10:
            fl.append("few_trades")
        if top_sh.loc[i, "max_drawdown"] < -0.70:
            fl.append("deep_drawdown")
        if top_sh.loc[i, "turnover"] > t95:
            fl.append("high_turnover_p95")
        suspicious.loc[i, "flags"] = ";".join(fl)

    # Concentration: best single row sharpe — which market/target
    best_idx = df["sharpe_ratio"].idxmax()
    best_row = df.loc[best_idx]
    top_mkt = df.nlargest(int(max(1, len(df) * 0.01)), "sharpe_ratio")["market"].value_counts()
    top_tgt = df.nlargest(int(max(1, len(df) * 0.01)), "sharpe_ratio")["target"].value_counts()

    diag = {
        "turnover_p95": t95,
        "best_sharpe_market": str(best_row["market"]),
        "best_sharpe_target": str(best_row["target"]),
        "top1pct_sharpe_rows_market_concentration": top_mkt.head(5).to_dict(),
        "top1pct_sharpe_rows_target_concentration": top_tgt.head(5).to_dict(),
        "suspicious_flag_types": flags,
    }
    return suspicious, diag


def _interpret_frequencies(freq_csv: Path) -> str:
    if not freq_csv.is_file():
        return ""
    g = pd.read_csv(freq_csv)
    if g.empty:
        return "_No data._\n"
    # rebalance row in dimension rebalance_frequency, group top10_sharpe
    sub = g[(g["dimension"] == "rebalance_frequency") & (g["group"] == "top10_sharpe")]
    lines = []
    if not sub.empty:
        sub = sub.sort_values("count", ascending=False)
        col = "rebalance_frequency" if "rebalance_frequency" in sub.columns else "value"
        parts = [f"{row[col]} ({row['share']:.1%})" for _, row in sub.iterrows()]
        lines.append("**Rebalance (top 10% Sharpe, global):** " + ", ".join(parts) + "\n")
    return "\n".join(lines) if lines else ""


def _write_report(
    df: pd.DataFrame,
    robust: pd.DataFrame,
    suspicious: pd.DataFrame,
    diag: dict[str, object],
) -> Path:
    # Summaries for markdown
    rb_med = df.groupby("rebalance_frequency")["sharpe_ratio"].median().sort_values(ascending=False)
    ez_med = df.groupby("entry_z")["sharpe_ratio"].median().sort_values(ascending=False)
    xz_med = df.groupby("exit_z")["sharpe_ratio"].median().sort_values(ascending=False)

    mkt_stab = df.groupby("market")["sharpe_ratio"].agg(["median", "mean", "std"])
    tgt_stab = df.groupby("target")["sharpe_ratio"].agg(["median", "mean", "std"])

    top10 = df.loc[_top_mask(df, "sharpe_ratio", 0.10, high=True)]
    med_trades_top10 = float(top10["number_of_trades"].median())
    med_dd_top10 = float(top10["max_drawdown"].median())
    mkt_share_top10 = top10["market"].value_counts(normalize=True)
    tgt_share_top10 = top10["target"].value_counts(normalize=True)
    freq_blurb = _interpret_frequencies(OUT_DIR / "top10_parameter_frequencies_global.csv")

    lines = [
        "# Parameter range analysis (grid search)",
        "",
        f"- Source: `{RESULTS_PATH.relative_to(PROJECT_ROOT)}` ({len(df)} rows).",
        f"- Outputs: `{OUT_DIR.relative_to(PROJECT_ROOT)}/`.",
        "",
        "## Rebalance frequency (median Sharpe, full sample)",
        "",
        _md_table(rb_med.rename("median_sharpe_ratio").reset_index()),
        "",
        "## Entry z (median Sharpe, full sample)",
        "",
        _md_table(ez_med.rename("median_sharpe_ratio").reset_index()),
        "",
        "## Exit z (median Sharpe, full sample)",
        "",
        _md_table(xz_med.rename("median_sharpe_ratio").reset_index()),
        "",
        "## Top 10% Sharpe — global parameter frequencies",
        "",
        "See `top10_parameter_frequencies_global.csv` for full tables. "
        "Rebalance / entry / exit / pair / triple frequencies describe which settings dominate the best decile.",
        "",
        freq_blurb,
        "",
        "### Concentration (top 10% Sharpe slice)",
        "",
        f"- Largest single-market share of rows in this slice: **{float(mkt_share_top10.max()):.1%}** ({mkt_share_top10.idxmax()}).",
        f"- Largest single-target share: **{float(tgt_share_top10.max()):.1%}** ({tgt_share_top10.idxmax()}).",
        "",
        "## Robust combinations (triple)",
        "",
        "File `robust_parameter_combos.csv` ranks `rebalance|entry|exit` by median Sharpe and counts how often each combo "
        "appears in the top 10% Sharpe slice across distinct targets and markets.",
        "",
        _md_table(robust.head(20), index=False),
        "",
        "## Stability across markets",
        "",
        _md_table(mkt_stab.reset_index()),
        "",
        "## Stability across targets (Sharpe dispersion)",
        "",
        "Higher `std` means more target-specific luck; lower spread suggests more homogeneous parameter luck.",
        "",
        _md_table(tgt_stab.sort_values("std", ascending=False).head(15).reset_index()),
        "",
        "## Top-decile Sharpe — trade and drawdown context",
        "",
        f"- Median `number_of_trades` in top 10% Sharpe rows: **{med_trades_top10:.1f}**.",
        f"- Median `max_drawdown` in top 10% Sharpe rows: **{med_dd_top10:.3f}**.",
        "",
        "## Suspicious flags (within top 10% Sharpe)",
        "",
        f"- Turnover 95th percentile (full sample): **{diag['turnover_p95']:.6f}**.",
        f"- Best Sharpe row: market **{diag['best_sharpe_market']}**, target **{diag['best_sharpe_target']}**.",
        "",
        _md_table(suspicious.head(25), index=False) if len(suspicious) else "_No rows flagged._",
        "",
        "## Plain-language takeaways",
        "",
        "1. **Rebalance:** higher median Sharpe at certain horizons (see table) suggests those horizons align better with "
        "this PCA + z-score setup on average; verify per market in `median_performance_by_rebalance.csv`.",
        "2. **Entry z:** tighter entries (higher `entry_z`) often reduce trade count but can improve Sharpe when spreads mean-revert cleanly; "
        "the median-Sharpe-by-entry table shows which entries are favored on average.",
        "3. **Exit z:** larger exit bands (higher `exit_z`) can clip winners or reduce turnover; the exit-z table summarizes average ranking.",
        "4. **Robust combos:** combinations that appear in many targets' top-10% Sharpe sets are less likely to be one-off target luck; "
        "see `robust_parameter_combos.csv` columns `n_distinct_targets_top10_sharpe` and `n_distinct_markets_top10_sharpe`.",
        "5. **Cross-market:** if market medians diverge strongly, the same parameters behave differently by calendar and microstructure.",
        "6. **Cross-target:** wide `std` in per-target Sharpe means parameter quality is not portable blindly across names.",
        "7. **Trades / drawdowns:** if top-decile rows often have very few trades or very deep drawdowns, headline Sharpe may be fragile.",
        "",
        "## Caveat",
        "",
        "**Grid search is in-sample on this dataset.** It does **not** prove out-of-sample profitability or future performance.",
        "",
    ]
    path = OUT_DIR / "parameter_analysis_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    _ensure_out_dir()
    if not RESULTS_PATH.is_file():
        raise FileNotFoundError(RESULTS_PATH)
    df = pd.read_csv(RESULTS_PATH)
    _validate(df)

    _build_top10_frequency_exports(df)
    _all_groups_frequency_supplement(df)
    _median_performance_exports(df)

    robust = _robust_combos(df)
    _save_csv(robust, "robust_parameter_combos.csv")

    suspicious, diag = _suspicious(df)
    _save_csv(suspicious, "suspicious_top_results.csv")

    _write_report(df, robust, suspicious, diag)

    print(f"Wrote analysis to {OUT_DIR}")
    print("Files:", ", ".join(sorted(p.name for p in OUT_DIR.iterdir() if p.suffix in (".csv", ".md"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
