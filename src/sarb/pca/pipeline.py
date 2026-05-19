from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sarb.core.universe import normalize_ticker_for_comparison
from sarb.pca.model import (
    PCAReplicationConfig,
    ReplicationSegmentMetadata,
    replicate_segment,
    to_log_prices,
)


@dataclass(frozen=True)
class PCAReplicationPipelineResult:
    spreads: pd.Series
    synthetic_log_prices: pd.Series
    target_log_prices: pd.Series
    metadata: pd.DataFrame
    diagnostics: dict[str, object]


def iter_rebalance_starts(index: pd.DatetimeIndex, config: PCAReplicationConfig) -> list[int]:
    if len(index) < config.train_window + 1:
        return []
    return list(range(config.train_window, len(index), config.rebalance_frequency))


def run_pca_synthetic_etf_pipeline(
    prices: pd.DataFrame,
    *,
    target: str,
    universe: list[str],
    config: PCAReplicationConfig,
) -> PCAReplicationPipelineResult:
    if target not in prices.columns:
        raise ValueError(f"target asset {target!r} is not present in prices")
    missing = [asset for asset in universe if asset not in prices.columns]
    if missing:
        raise ValueError(f"universe assets missing from prices: {missing}")
    target_key = normalize_ticker_for_comparison(target)
    if any(normalize_ticker_for_comparison(str(u)) == target_key for u in universe):
        raise ValueError("target asset must not be included in the PCA universe")

    log_prices = to_log_prices(prices)
    spreads: list[pd.Series] = []
    synthetic: list[pd.Series] = []
    target_log: list[pd.Series] = []
    metadata_rows: list[ReplicationSegmentMetadata] = []

    for start_idx in iter_rebalance_starts(log_prices.index, config):
        train = log_prices.iloc[start_idx - config.train_window : start_idx]
        end_idx = min(start_idx + config.rebalance_frequency, len(log_prices))
        oos = log_prices.iloc[start_idx:end_idx]
        if oos.empty:
            continue

        segment, seg_meta = replicate_segment(
            train,
            oos,
            target=target,
            universe=universe,
            config=config,
            rebalance_date=log_prices.index[start_idx],
        )
        metadata_rows.append(seg_meta)
        if segment is None:
            continue
        spreads.append(segment.spread)
        synthetic.append(segment.synthetic_log_price)
        target_log.append(oos[target].loc[segment.spread.index])

    if not spreads:
        raise ValueError("no out-of-sample replication segments were produced")

    spread_series = pd.concat(spreads).sort_index()
    if spread_series.index.has_duplicates:
        spread_series = spread_series[~spread_series.index.duplicated(keep="last")]

    synthetic_series = pd.concat(synthetic).sort_index()
    if synthetic_series.index.has_duplicates:
        synthetic_series = synthetic_series[~synthetic_series.index.duplicated(keep="last")]

    target_series = pd.concat(target_log).sort_index()
    if target_series.index.has_duplicates:
        target_series = target_series[~target_series.index.duplicated(keep="last")]

    skipped = sum(1 for row in metadata_rows if row.segment_status == "skipped")
    valid = sum(1 for row in metadata_rows if row.segment_status == "ok")
    metadata = pd.DataFrame(
        [
            {
                "rebalance_date": row.rebalance_date,
                "train_start": row.train_start,
                "train_end": row.train_end,
                "n_components": row.n_components,
                "explained_variance": row.explained_variance,
                "universe_size": row.universe_size,
                "universe_assets_used": row.universe_assets_used,
                "segment_status": row.segment_status,
                "skip_reason": row.skip_reason,
                "oos_start": row.oos_start,
                "oos_end": row.oos_end,
                "valid_train_rows": row.valid_train_rows,
                "valid_oos_rows": row.valid_oos_rows,
                "valid_universe_size": row.valid_universe_size,
            }
            for row in metadata_rows
        ]
    )
    diagnostics: dict[str, object] = {
        "skipped_rebalance_windows": skipped,
        "valid_rebalance_windows": valid,
        "min_train_observations": config.min_train_observations,
        "min_universe_assets": config.min_universe_assets,
        "min_asset_coverage": config.min_asset_coverage,
        "market": config.market,
        "universe_assets_used": ",".join(universe),
    }
    return PCAReplicationPipelineResult(
        spreads=spread_series,
        synthetic_log_prices=synthetic_series,
        target_log_prices=target_series,
        metadata=metadata,
        diagnostics=diagnostics,
    )
