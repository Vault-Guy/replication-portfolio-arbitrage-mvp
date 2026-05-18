"""
Summarize crypto_parameter_grid_results.csv into reports and CSV summaries.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sarb.universe import CRYPTO_EXCLUDED_TOKENS, normalize_ticker_for_comparison  # noqa: E402

INPUT_PATH = PROJECT_ROOT / "results" / "crypto_parameter_grid" / "crypto_parameter_grid_results.csv"
OUT_DIR = PROJECT_ROOT / "results" / "crypto_parameter_grid"

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

PARAM_COLS = [
    "train_window",
    "rebalance_frequency",
    "entry_z",
    "exit_z",
    "zscore_lookback",
    "pca_explained_variance",
    "universe_size_requested",
    "universe_selection_method",
    "min_asset_coverage",
    "min_universe_assets",
    "min_train_observations",
    "max_holding_period",
    "stop_loss_z",
    "pca_component_selection_method",
    "fixed_n_components",
    "regression_type",
    "ridge_alpha",
    "transaction_cost_bps",
]


def _md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_Empty._"
    cols = [str(c) for c in frame.columns]

    def cell(v: object) -> str:
        return str(v).replace("|", "\\|")

    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(cell(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


def _top_mask(df: pd.DataFrame, col: str, frac: float) -> pd.Series:
    q = 1.0 - frac
    thresh = df[col].quantile(q)
    return df[col] >= thresh


def _validate(df: pd.DataFrame) -> None:
    for c in METRIC_COLS:
        if c not in df.columns:
            raise ValueError(f"missing column {c}")
        if not pd.api.types.is_numeric_dtype(df[c]):
            raise TypeError(f"metric {c} must be numeric")
        if df[c].astype(str).str.contains(",").any():
            raise ValueError(f"metric {c} appears to use comma decimals")

    for _, row in df.iterrows():
        tgt = str(row["target"])
        tk = normalize_ticker_for_comparison(tgt)
        assets = str(row.get("universe_assets", "")).split(",") if pd.notna(row.get("universe_assets")) else []
        for a in assets:
            if not a.strip():
                continue
            if normalize_ticker_for_comparison(a.strip()) == tk:
                raise ValueError(f"target {tgt} found in universe_assets")
        excl = {normalize_ticker_for_comparison(x) for x in CRYPTO_EXCLUDED_TOKENS}
        for a in assets:
            if normalize_ticker_for_comparison(a.strip()) in excl:
                raise ValueError(f"excluded token {a!r} in universe_assets")

    if "SOL" in df["target"].astype(str).values:
        sol = df.loc[df["target"].astype(str) == "SOL"]
        if (sol["valid_rebalance_windows"] <= 0).any():
            raise ValueError("SOL rows must have valid_rebalance_windows > 0")


def _summarize_by_stage_param(df: pd.DataFrame, param: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for stage in sorted(df["stage"].unique()):
        sub = df.loc[df["stage"] == stage]
        if param not in sub.columns:
            continue
        top10 = _top_mask(sub, "sharpe_ratio", 0.10)
        for val in sorted(sub[param].dropna().unique(), key=lambda x: (str(type(x)), str(x))):
            s = sub.loc[sub[param] == val]
            if s.empty:
                continue
            m = top10.reindex(s.index).fillna(False).astype(bool)
            t10 = s.loc[m]
            freq = float(len(t10) / len(s)) if len(s) else 0.0
            rows.append(
                {
                    "stage": stage,
                    "parameter": param,
                    "value": val,
                    "median_sharpe_ratio": float(s["sharpe_ratio"].median()),
                    "median_total_return": float(s["total_return"].median()),
                    "median_max_drawdown": float(s["max_drawdown"].median()),
                    "median_number_of_trades": float(s["number_of_trades"].median()),
                    "top10_sharpe_freq": freq,
                    "count": int(len(s)),
                }
            )
    return pd.DataFrame(rows)


def _robust_combos(df: pd.DataFrame) -> pd.DataFrame:
    combo_cols = [c for c in PARAM_COLS if c in df.columns]
    top10 = _top_mask(df, "sharpe_ratio", 0.10)
    rows: list[dict[str, object]] = []
    for key, grp in df.groupby(combo_cols, dropna=False):
        key_t = key if isinstance(key, tuple) else (key,)
        combo_dict = dict(zip(combo_cols, key_t))
        combo_str = "|".join(f"{k}={combo_dict[k]}" for k in combo_cols)
        in_top = grp.loc[top10.reindex(grp.index).fillna(False).astype(bool)]
        rows.append(
            {
                "param_combo": combo_str,
                "n_targets_top10_sharpe": int(in_top["target"].nunique()),
                "median_sharpe_ratio": float(grp["sharpe_ratio"].median()),
                "median_total_return": float(grp["total_return"].median()),
                "median_max_drawdown": float(grp["max_drawdown"].median()),
                "median_turnover": float(grp["turnover"].median()),
                "median_number_of_trades": float(grp["number_of_trades"].median()),
                "mean_valid_rebalance_share": float(grp["valid_rebalance_share"].mean()),
                "count": int(len(grp)),
            }
        )
    out = pd.DataFrame(rows).sort_values("median_sharpe_ratio", ascending=False)
    return out


def _suspicious(df: pd.DataFrame) -> pd.DataFrame:
    t95 = float(df["turnover"].quantile(0.95))
    tr_hi = float(df["total_return"].quantile(0.95))
    out = df.copy()
    flags: list[str] = []
    for _, r in out.iterrows():
        fl: list[str] = []
        if r["max_drawdown"] <= -0.70:
            fl.append("deep_dd")
        if r["number_of_trades"] < 10:
            fl.append("few_trades")
        if r["turnover"] > t95:
            fl.append("high_turnover")
        if r["valid_rebalance_share"] < 0.50:
            fl.append("low_rebalance_share")
        if r["total_return"] >= tr_hi and r["max_drawdown"] <= -0.55:
            fl.append("high_return_deep_dd")
        flags.append(";".join(fl))
    out["suspicious_flags"] = flags
    return out.loc[out["suspicious_flags"] != ""].copy()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    args = parser.parse_args()
    path = args.input
    if not path.is_file():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError("results CSV is empty")
    _validate(df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    summaries: list[pd.DataFrame] = []
    for p in PARAM_COLS:
        if p not in df.columns:
            continue
        summaries.append(_summarize_by_stage_param(df, p))
    by_stage = pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()
    by_stage.to_csv(OUT_DIR / "crypto_parameter_summary_by_stage.csv", index=False)

    tgt_rows: list[dict[str, object]] = []
    for tgt in sorted(df["target"].unique()):
        sub = df.loc[df["target"] == tgt]
        tgt_rows.append(
            {
                "target": tgt,
                "median_sharpe_ratio": float(sub["sharpe_ratio"].median()),
                "median_total_return": float(sub["total_return"].median()),
                "median_max_drawdown": float(sub["max_drawdown"].median()),
                "count": int(len(sub)),
            }
        )
    pd.DataFrame(tgt_rows).to_csv(OUT_DIR / "crypto_parameter_summary_by_target.csv", index=False)

    best_t = (
        df.sort_values(["target", "sharpe_ratio"], ascending=[True, False])
        .groupby("target", as_index=False)
        .first()
    )
    best_t.to_csv(OUT_DIR / "crypto_best_by_target.csv", index=False)

    best_s = (
        df.sort_values(["stage", "sharpe_ratio"], ascending=[True, False])
        .groupby("stage", as_index=False)
        .first()
    )
    best_s.to_csv(OUT_DIR / "crypto_best_by_stage.csv", index=False)

    robust = _robust_combos(df)
    robust.to_csv(OUT_DIR / "crypto_robust_parameter_zones.csv", index=False)

    susp = _suspicious(df)
    susp.to_csv(OUT_DIR / "crypto_suspicious_results.csv", index=False)

    # Report
    tw = df.groupby("stage")["train_window"].median().to_dict()
    zl = df.groupby("stage")["zscore_lookback"].median().to_dict()
    pe = df.groupby("stage")["pca_explained_variance"].median().to_dict()

    risk = df.loc[df["max_holding_period"].notna() | df["stop_loss_z"].notna()]
    risk_dd_med = float(risk["max_drawdown"].median()) if len(risk) else float("nan")
    base_dd_med = float(df.loc[df["max_holding_period"].isna() & df["stop_loss_z"].isna(), "max_drawdown"].median())

    agg = df.groupby("stage")["sharpe_ratio"].agg(["median", "std"]).reset_index()
    lines = [
        "# Crypto parameter grid analysis",
        "",
        f"- Rows: {len(df)} from `{path.relative_to(PROJECT_ROOT)}`.",
        "",
        "## Median train_window by stage",
        "",
        str(tw),
        "",
        "## Median zscore_lookback by stage",
        "",
        str(zl),
        "",
        "## Median pca_explained_variance by stage",
        "",
        str(pe),
        "",
        "## Universe size / method",
        "",
        _md_table(
            df.groupby(["universe_size_requested", "universe_selection_method"])["sharpe_ratio"]
            .median()
            .reset_index(name="median_sharpe")
            .sort_values("median_sharpe", ascending=False)
            .head(20)
        ),
        "",
        "## Risk controls vs baseline (median max_drawdown)",
        "",
        f"- Rows with any time/stop control: median max_drawdown **{risk_dd_med:.3f}** (n={len(risk)}).",
        f"- Rows without max_holding_period and without stop_loss_z: median max_drawdown **{base_dd_med:.3f}**.",
        "",
        "## Aggressive slice (exit_z == 0)",
        "",
    ]
    ag = df.loc[df["exit_z"] == 0]
    if len(ag):
        lines.append(
            f"- Median Sharpe **{float(ag['sharpe_ratio'].median()):.3f}**, "
            f"median max_drawdown **{float(ag['max_drawdown'].median()):.3f}** (n={len(ag)})."
        )
    else:
        lines.append("_No exit_z=0 rows._")
    lines.extend(
        [
            "",
            "## Stability across targets (Sharpe)",
            "",
            _md_table(pd.DataFrame(tgt_rows).sort_values("median_sharpe_ratio", ascending=False)),
            "",
            "## Sharpe dispersion by stage",
            "",
            _md_table(agg),
            "",
            "## Caveat",
            "",
            "**In-sample grid search does not prove out-of-sample profitability or future performance.**",
            "",
        ]
    )
    (OUT_DIR / "crypto_parameter_analysis_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote summaries to {OUT_DIR}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
