from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from sarb.universe import normalize_ticker_for_comparison


@dataclass(frozen=True)
class PCAReplicationConfig:
    train_window: int
    rebalance_frequency: int
    pca_explained_variance: float
    min_train_observations: int
    min_universe_assets: int = 5
    min_asset_coverage: float = 0.80
    market: str = "usa"
    pca_component_selection_method: str = "explained_variance"
    fixed_n_components: int | None = None
    regression_type: str = "OLS"
    ridge_alpha: float = 1.0


@dataclass(frozen=True)
class PCASyntheticETFModel:
    scaler: StandardScaler
    pca: PCA
    intercept: float
    coefficients: np.ndarray
    universe: tuple[str, ...]
    target: str
    n_components: int
    explained_variance: float
    n_aligned_train_rows: int = 0


@dataclass(frozen=True)
class ReplicationSegmentMetadata:
    rebalance_date: pd.Timestamp
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    n_components: int
    explained_variance: float
    universe_size: int
    universe_assets_used: str = ""
    segment_status: str = "ok"
    skip_reason: str | None = None
    oos_start: pd.Timestamp | None = None
    oos_end: pd.Timestamp | None = None
    valid_train_rows: int | None = None
    valid_oos_rows: int | None = None
    valid_universe_size: int | None = None


@dataclass(frozen=True)
class ReplicationSegmentResult:
    synthetic_log_price: pd.Series
    spread: pd.Series
    metadata: ReplicationSegmentMetadata


def to_log_prices(prices: pd.DataFrame) -> pd.DataFrame:
    if (prices <= 0).any().any():
        raise ValueError("prices must be strictly positive before log transformation")
    return np.log(prices.astype(float))


def select_component_count(explained_variance_ratio: np.ndarray, threshold: float) -> int:
    if explained_variance_ratio.size == 0:
        raise ValueError("explained variance ratios must not be empty")
    cumulative = np.cumsum(explained_variance_ratio)
    selected = int(np.searchsorted(cumulative, threshold, side="left") + 1)
    return max(1, min(selected, explained_variance_ratio.size))


def universe_eligible_for_window(window: pd.DataFrame, universe: list[str]) -> list[str]:
    """Keep only assets with a complete history over the supplied window."""
    eligible: list[str] = []
    for symbol in universe:
        if symbol not in window.columns:
            continue
        if window[symbol].notna().all():
            eligible.append(symbol)
    return eligible


def _universe_keys(universe: list[str]) -> set[str]:
    return {normalize_ticker_for_comparison(x) for x in universe}


def _rowwise_all_finite_2d(values: np.ndarray) -> np.ndarray:
    """Boolean mask: True where the row has all finite values (no NaN/inf)."""
    return np.isfinite(values).all(axis=1)


def _oos_frame(
    log_prices: pd.DataFrame,
    *,
    universe: list[str],
    target: str,
) -> tuple[pd.DataFrame, pd.Series]:
    available = [c for c in universe if c in log_prices.columns]
    if target not in log_prices.columns:
        raise ValueError(f"target asset {target!r} is not present in log prices")
    if not available:
        empty_idx = log_prices.index[:0]
        return pd.DataFrame(index=empty_idx), pd.Series(dtype=float, index=empty_idx)

    u_block = log_prices.loc[:, available].to_numpy(dtype=np.float64, copy=False)
    t_vec = log_prices.loc[:, target].to_numpy(dtype=np.float64, copy=False)
    valid = _rowwise_all_finite_2d(u_block) & np.isfinite(t_vec)
    if not valid.any():
        empty_idx = log_prices.index[:0]
        return pd.DataFrame(index=empty_idx, columns=available), pd.Series(dtype=float, index=empty_idx)

    idx = log_prices.index[valid]
    universe_frame = pd.DataFrame(
        u_block[valid],
        index=idx,
        columns=available,
    )
    target_values = pd.Series(t_vec[valid], index=idx, name=target)
    return universe_frame, target_values


def _effective_min_train_rows(config: PCAReplicationConfig, train_rows: int) -> int:
    return min(config.min_train_observations, train_rows)


def _coverage_on_target_rows(train_log_prices: pd.DataFrame, target: str, asset: str) -> float:
    t_mask = train_log_prices[target].notna()
    if not bool(t_mask.any()):
        return 0.0
    sub = train_log_prices.loc[t_mask, asset]
    return float(sub.notna().mean())


def _filter_universe_by_min_coverage(
    train_log_prices: pd.DataFrame,
    target: str,
    working: list[str],
    min_coverage: float,
) -> list[str]:
    scored = [(u, _coverage_on_target_rows(train_log_prices, target, u)) for u in working]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [u for u, cov in scored if cov >= min_coverage]


def _prepare_training_arrays(
    train_log_prices: pd.DataFrame,
    *,
    target: str,
    universe: list[str],
    config: PCAReplicationConfig,
) -> tuple[list[str], np.ndarray, np.ndarray] | None:
    if target not in train_log_prices.columns:
        return None
    target_key = normalize_ticker_for_comparison(target)
    if target_key in _universe_keys(universe):
        return None

    working = [
        str(u)
        for u in universe
        if u in train_log_prices.columns and normalize_ticker_for_comparison(str(u)) != target_key
    ]
    if not working:
        return None

    working = [u for u in working if train_log_prices[u].notna().any()]
    if len(working) < 2:
        return None

    working = _filter_universe_by_min_coverage(
        train_log_prices,
        target,
        working,
        config.min_asset_coverage,
    )
    if len(working) < 2:
        return None

    required_rows = _effective_min_train_rows(config, len(train_log_prices))

    def nan_counts() -> dict[str, int]:
        return {u: int(train_log_prices[u].isna().sum()) for u in working}

    while True:
        required_universe = min(config.min_universe_assets, max(2, len(working)))
        cols = [target] + working
        block = train_log_prices.reindex(columns=cols)
        block = block.dropna(axis=1, how="all")
        if target not in block.columns:
            return None
        working = [c for c in block.columns if c != target]
        if len(working) < 2:
            return None

        sub = block[[target] + working]
        arr = sub.to_numpy(dtype=np.float64, copy=False)
        valid = _rowwise_all_finite_2d(arr)
        n_complete = int(valid.sum())
        if n_complete >= required_rows and len(working) >= required_universe:
            aligned = sub.loc[valid]
            u_frame = aligned[working]
            tgt = aligned[target]
            if u_frame.shape[0] == 0 or tgt.shape[0] == 0:
                return None
            return working, u_frame.to_numpy(dtype=float), tgt.to_numpy(dtype=float)

        if len(working) > max(2, required_universe):
            counts = nan_counts()
            worst = max(working, key=lambda u: counts.get(u, 0))
            working = [u for u in working if u != worst]
            continue

        if len(working) > 2 and n_complete < required_rows:
            counts = nan_counts()
            worst = max(working, key=lambda u: counts.get(u, 0))
            working = [u for u in working if u != worst]
            continue

        return None


def fit_pca_synthetic_etf(
    train_log_prices: pd.DataFrame,
    *,
    target: str,
    universe: list[str],
    config: PCAReplicationConfig,
) -> PCASyntheticETFModel | None:
    target_key = normalize_ticker_for_comparison(target)
    if target_key in _universe_keys(universe):
        raise ValueError("target asset must not be included in the PCA universe")
    if target not in train_log_prices.columns:
        raise ValueError(f"target asset {target!r} is not present in training prices")
    missing = [asset for asset in universe if asset not in train_log_prices.columns]
    if missing:
        raise ValueError(f"universe assets missing from training prices: {missing}")
    if len(train_log_prices) < config.train_window:
        raise ValueError("training window is shorter than config.train_window")

    prepared = _prepare_training_arrays(
        train_log_prices,
        target=target,
        universe=universe,
        config=config,
    )
    if prepared is None:
        return None

    pruned_universe, universe_values, target_values = prepared
    if universe_values.size == 0 or target_values.size == 0:
        return None

    scaler = StandardScaler()
    scaled_universe = scaler.fit_transform(universe_values)

    pca_full = PCA()
    pca_full.fit(scaled_universe)
    n_full = int(scaled_universe.shape[1])
    if config.pca_component_selection_method == "fixed_n_components":
        if config.fixed_n_components is None:
            raise ValueError("fixed_n_components is required when pca_component_selection_method is fixed_n_components")
        n_components = max(1, min(int(config.fixed_n_components), n_full))
    elif config.pca_component_selection_method == "explained_variance":
        n_components = select_component_count(
            pca_full.explained_variance_ratio_,
            config.pca_explained_variance,
        )
    else:
        raise ValueError(
            f"unknown pca_component_selection_method {config.pca_component_selection_method!r}; "
            "expected explained_variance or fixed_n_components"
        )
    scores = pca_full.transform(scaled_universe)[:, :n_components]
    design = np.column_stack([np.ones(len(scores)), scores])
    if config.regression_type == "Ridge":
        ridge = Ridge(alpha=float(config.ridge_alpha), fit_intercept=False, random_state=0)
        ridge.fit(design, target_values)
        coef_vec = np.asarray(ridge.coef_, dtype=float).ravel()
        intercept = float(coef_vec[0])
        coefficients = np.asarray(coef_vec[1:], dtype=float)
    elif config.regression_type == "OLS":
        coef_lstsq, _, _, _ = np.linalg.lstsq(design, target_values, rcond=None)
        intercept = float(coef_lstsq[0])
        coefficients = np.asarray(coef_lstsq[1:], dtype=float)
    else:
        raise ValueError(f"unknown regression_type {config.regression_type!r}; expected OLS or Ridge")
    explained_variance = float(np.sum(pca_full.explained_variance_ratio_[:n_components]))
    n_aligned = int(universe_values.shape[0])

    return PCASyntheticETFModel(
        scaler=scaler,
        pca=pca_full,
        intercept=intercept,
        coefficients=coefficients,
        universe=tuple(pruned_universe),
        target=target,
        n_components=n_components,
        explained_variance=explained_variance,
        n_aligned_train_rows=n_aligned,
    )


def apply_pca_synthetic_etf(
    oos_log_prices: pd.DataFrame,
    model: PCASyntheticETFModel,
) -> pd.DataFrame:
    oos_universe, target_values = _oos_frame(
        oos_log_prices,
        universe=list(model.universe),
        target=model.target,
    )
    if oos_universe.shape[0] == 0:
        return pd.DataFrame(
            columns=["target_log_price", "synthetic_log_price"],
            index=oos_log_prices.index[:0],
        )

    scaled_universe = model.scaler.transform(oos_universe.to_numpy(dtype=float))
    scores = model.pca.transform(scaled_universe)[:, : model.n_components]
    synthetic = model.intercept + scores @ model.coefficients
    return pd.DataFrame(
        {
            "target_log_price": target_values,
            "synthetic_log_price": synthetic,
        },
        index=oos_universe.index,
    )


def _skip_metadata(
    *,
    rebalance_date: pd.Timestamp,
    train_log_prices: pd.DataFrame,
    oos_log_prices: pd.DataFrame,
    reason: str,
    valid_train_rows: int | None = None,
    valid_oos_rows: int | None = None,
    valid_universe_size: int | None = None,
) -> ReplicationSegmentMetadata:
    oos_start = oos_log_prices.index[0] if len(oos_log_prices) > 0 else None
    oos_end = oos_log_prices.index[-1] if len(oos_log_prices) > 0 else None
    return ReplicationSegmentMetadata(
        rebalance_date=rebalance_date,
        train_start=train_log_prices.index[0],
        train_end=train_log_prices.index[-1],
        n_components=0,
        explained_variance=0.0,
        universe_size=valid_universe_size or 0,
        universe_assets_used="",
        segment_status="skipped",
        skip_reason=reason,
        oos_start=oos_start,
        oos_end=oos_end,
        valid_train_rows=valid_train_rows,
        valid_oos_rows=valid_oos_rows,
        valid_universe_size=valid_universe_size,
    )


def replicate_segment(
    train_log_prices: pd.DataFrame,
    oos_log_prices: pd.DataFrame,
    *,
    target: str,
    universe: list[str],
    config: PCAReplicationConfig,
    rebalance_date: pd.Timestamp,
) -> tuple[ReplicationSegmentResult | None, ReplicationSegmentMetadata]:
    model = fit_pca_synthetic_etf(
        train_log_prices,
        target=target,
        universe=universe,
        config=config,
    )
    if model is None:
        meta = _skip_metadata(
            rebalance_date=rebalance_date,
            train_log_prices=train_log_prices,
            oos_log_prices=oos_log_prices,
            reason="insufficient_training_overlap",
            valid_train_rows=0,
            valid_oos_rows=0,
            valid_universe_size=0,
        )
        return None, meta

    applied = apply_pca_synthetic_etf(oos_log_prices, model)
    if applied.empty or len(applied) == 0:
        oos_n = 0
        try:
            u_mat = oos_log_prices.loc[:, list(model.universe)].to_numpy(dtype=np.float64, copy=False)
            t_vec = oos_log_prices.loc[:, model.target].to_numpy(dtype=np.float64, copy=False)
            oos_n = int((_rowwise_all_finite_2d(u_mat) & np.isfinite(t_vec)).sum())
        except Exception:
            oos_n = 0
        meta = _skip_metadata(
            rebalance_date=rebalance_date,
            train_log_prices=train_log_prices,
            oos_log_prices=oos_log_prices,
            reason="empty_oos_after_alignment",
            valid_train_rows=model.n_aligned_train_rows,
            valid_oos_rows=oos_n,
            valid_universe_size=len(model.universe),
        )
        return None, meta

    spread = applied["target_log_price"] - applied["synthetic_log_price"]
    meta = ReplicationSegmentMetadata(
        rebalance_date=rebalance_date,
        train_start=train_log_prices.index[0],
        train_end=train_log_prices.index[-1],
        n_components=model.n_components,
        explained_variance=model.explained_variance,
        universe_size=len(model.universe),
        universe_assets_used=",".join(model.universe),
        segment_status="ok",
        skip_reason=None,
        oos_start=oos_log_prices.index[0],
        oos_end=oos_log_prices.index[-1],
        valid_train_rows=model.n_aligned_train_rows,
        valid_oos_rows=len(applied),
        valid_universe_size=len(model.universe),
    )
    return (
        ReplicationSegmentResult(
            synthetic_log_price=applied["synthetic_log_price"],
            spread=spread,
            metadata=meta,
        ),
        meta,
    )
