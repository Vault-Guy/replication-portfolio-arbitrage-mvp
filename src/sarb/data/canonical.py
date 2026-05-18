from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from sarb.types import CanonicalPricePanel


def build_canonical_panel(
    frames: dict[str, pd.Series],
    *,
    market: str,
    frequency: str,
    metadata: dict | None = None,
) -> CanonicalPricePanel:
    """Merge per-symbol close series into a wide, time-sorted price panel."""
    if not frames:
        raise ValueError("frames must contain at least one symbol series")

    prices = pd.DataFrame(frames)
    prices.index = pd.DatetimeIndex(prices.index)
    prices = prices.sort_index()
    prices = prices[~prices.index.duplicated(keep="last")]
    prices.columns = prices.columns.astype(str)

    return CanonicalPricePanel(
        prices=prices,
        market=market,
        frequency=frequency,
        metadata=metadata or {},
    )


def save_canonical_panel(panel: CanonicalPricePanel, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    panel.prices.to_parquet(target)
    return target


def load_canonical_panel(
    path: str | Path,
    *,
    market: str,
    frequency: str,
    metadata: dict | None = None,
) -> CanonicalPricePanel:
    prices = pd.read_parquet(path)
    prices.index = pd.DatetimeIndex(prices.index)
    return CanonicalPricePanel(
        prices=prices.sort_index(),
        market=market,
        frequency=frequency,
        metadata=metadata or {},
    )


def clip_panel_to_range(
    panel: CanonicalPricePanel,
    start: str | None = None,
    end: str | None = None,
) -> CanonicalPricePanel:
    prices = panel.prices
    if start is not None:
        prices = prices.loc[prices.index >= pd.Timestamp(start)]
    if end is not None:
        prices = prices.loc[prices.index < pd.Timestamp(end)]
    return CanonicalPricePanel(
        prices=prices,
        market=panel.market,
        frequency=panel.frequency,
        metadata=panel.metadata,
    )


def list_symbols(panel: CanonicalPricePanel) -> list[str]:
    return list(panel.prices.columns.astype(str))
