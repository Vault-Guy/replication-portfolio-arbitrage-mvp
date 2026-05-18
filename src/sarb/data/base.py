from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Literal

import numpy as np
import pandas as pd

MissingValuePolicy = Literal["preserve", "forward_fill"]


@dataclass(frozen=True)
class MarketData:
    prices: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


def iter_archive_csv_members(
    archive: Path,
    *,
    archive_subdir: str | None = None,
) -> Iterable[tuple[str, bytes]]:
    with zipfile.ZipFile(archive) as handle:
        for member in handle.namelist():
            if not member.endswith(".csv") or "__MACOSX" in member:
                continue
            if archive_subdir and not member.startswith(f"{archive_subdir}/"):
                continue
            yield member, handle.read(member)


def symbol_from_member(
    member: str,
    *,
    prefix_strip: str | None = None,
    suffix_strip: str | None = None,
) -> str:
    symbol = Path(member).stem
    if prefix_strip and symbol.startswith(prefix_strip):
        symbol = symbol[len(prefix_strip) :]
    if suffix_strip and symbol.endswith(suffix_strip):
        symbol = symbol[: -len(suffix_strip)]
    return symbol


def read_long_csv(
    payload: bytes,
    *,
    timestamp_column: str,
    price_column: str,
) -> pd.Series:
    frame = pd.read_csv(BytesIO(payload))
    if timestamp_column not in frame.columns or price_column not in frame.columns:
        raise ValueError(f"expected columns {timestamp_column!r} and {price_column!r}")

    series = frame.set_index(timestamp_column)[price_column]
    series.index = pd.to_datetime(series.index, errors="coerce")
    series = series[~series.index.isna()]
    series = series.sort_index()
    if series.index.has_duplicates:
        series = series[~series.index.duplicated(keep="last")]
    return series.astype(float)


def build_prices_panel(series_by_symbol: dict[str, pd.Series]) -> pd.DataFrame:
    if not series_by_symbol:
        raise ValueError("series_by_symbol must not be empty")

    prices = pd.DataFrame(series_by_symbol)
    prices.index = pd.DatetimeIndex(prices.index)
    prices = prices.sort_index()
    if prices.index.has_duplicates:
        prices = prices[~prices.index.duplicated(keep="last")]
    prices.columns = prices.columns.astype(str)
    prices = prices.loc[:, ~prices.isna().all(axis=0)]
    validate_canonical_prices(prices)
    return prices


def clip_prices(
    prices: pd.DataFrame,
    *,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    clipped = prices
    if start is not None:
        clipped = clipped.loc[clipped.index >= pd.Timestamp(start)]
    if end is not None:
        clipped = clipped.loc[clipped.index < pd.Timestamp(end)]
    clipped = clipped.loc[:, ~clipped.isna().all(axis=0)]
    if clipped.empty or clipped.shape[1] == 0:
        raise ValueError("price panel is empty after clipping")
    validate_canonical_prices(clipped)
    return clipped


def apply_missing_value_policy(
    prices: pd.DataFrame,
    policy: MissingValuePolicy,
    *,
    forward_fill_limit: int | None = None,
) -> pd.DataFrame:
    if policy == "preserve":
        return prices
    if policy == "forward_fill":
        if forward_fill_limit is None:
            raise ValueError("forward_fill_limit must be set when using forward_fill policy")
        filled = prices.sort_index().ffill(limit=forward_fill_limit)
        filled = filled.loc[:, ~filled.isna().all(axis=0)]
        validate_canonical_prices(filled)
        return filled
    raise ValueError(f"unsupported missing value policy: {policy!r}")


def validate_canonical_prices(prices: pd.DataFrame) -> None:
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise ValueError("prices index must be a DatetimeIndex")
    if prices.index.empty:
        raise ValueError("prices index must not be empty")
    if not prices.index.is_monotonic_increasing:
        raise ValueError("prices index must be sorted ascending")
    if prices.index.has_duplicates:
        raise ValueError("prices index must not contain duplicate timestamps")
    if prices.columns.empty:
        raise ValueError("prices must include at least one asset column")
    if prices.columns.astype(str).duplicated().any():
        raise ValueError("prices columns must be unique asset symbols")
    if prices.isna().all(axis=0).any():
        raise ValueError("prices must not contain all-null asset columns")

    observed = prices.to_numpy(dtype=float)
    finite_mask = np.isfinite(observed)
    if finite_mask.any() and np.any(observed[finite_mask] <= 0):
        raise ValueError("observed prices must be strictly positive")
