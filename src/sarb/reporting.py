from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import pandas as pd

from sarb.run import UnifiedPipelineResult, metrics_dataframe
from sarb.utils.io import format_dataframe_for_display_eu

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def plot_pipeline_dashboard(result: UnifiedPipelineResult) -> Figure:
    backtest = result.backtest
    config = result.run_config
    target_log = result.replication.target_log_prices.reindex(backtest.spread.index)
    synthetic_log = result.replication.synthetic_log_prices.reindex(backtest.spread.index)

    fig, axes = plt.subplots(5, 1, figsize=(12, 14), sharex=True)

    axes[0].plot(target_log.index, target_log, label="target log-price", linewidth=1.0)
    axes[0].plot(synthetic_log.index, synthetic_log, label="synthetic log-price", linewidth=1.0)
    axes[0].set_ylabel("log price")
    axes[0].legend(loc="upper left")
    axes[0].set_title(f"{result.target} vs synthetic replication")

    axes[1].plot(backtest.spread.index, backtest.spread, color="tab:purple", linewidth=1.0)
    axes[1].set_ylabel("spread")
    axes[1].set_title("Spread")

    axes[2].plot(backtest.zscore.index, backtest.zscore, color="tab:orange", linewidth=1.0)
    axes[2].axhline(config.entry_z, color="red", linestyle="--", linewidth=0.8, label="entry")
    axes[2].axhline(-config.entry_z, color="red", linestyle="--", linewidth=0.8)
    axes[2].axhline(config.exit_z, color="green", linestyle=":", linewidth=0.8, label="exit")
    axes[2].axhline(-config.exit_z, color="green", linestyle=":", linewidth=0.8)
    axes[2].set_ylabel("z-score")
    axes[2].legend(loc="upper left")
    axes[2].set_title("Z-score with entry/exit bands")

    axes[3].step(
        backtest.positions.index,
        backtest.positions,
        where="post",
        color="tab:blue",
        linewidth=1.0,
    )
    axes[3].set_ylabel("position")
    axes[3].set_title("Positions")

    cumulative_pnl = backtest.equity_curve - 1.0
    axes[4].plot(cumulative_pnl.index, cumulative_pnl, color="tab:green", linewidth=1.0)
    axes[4].set_ylabel("cumulative P&L")
    axes[4].set_xlabel("time")
    axes[4].set_title("Cumulative P&L")

    fig.tight_layout()
    return fig


def compare_metrics_table(results: dict[str, UnifiedPipelineResult]) -> pd.DataFrame:
    frames = []
    for market, result in results.items():
        frame = metrics_dataframe(result.backtest.metrics)
        frame.insert(0, "market", market)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def display_metrics_table(df: pd.DataFrame, digits: int = 6) -> pd.DataFrame:
    return format_dataframe_for_display_eu(df, digits=digits)
