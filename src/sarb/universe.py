from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


USA_PRIORITY_UNIVERSE = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AVGO",
    "ORCL",
    "AMD",
    "CSCO",
    "QCOM",
    "TXN",
    "IBM",
    "ACN",
    "ADI",
    "GOOGL",
    "META",
    "NFLX",
    "DIS",
    "TMUS",
    "CMCSA",
    "VZ",
    "AMZN",
    "TSLA",
    "HD",
    "MCD",
    "BKNG",
    "SBUX",
    "LOW",
    "WMT",
    "COST",
    "PG",
    "KO",
    "PEP",
    "PM",
    "BRK.B",
    "JPM",
    "V",
    "MA",
    "BAC",
    "GS",
    "MS",
    "WFC",
    "AXP",
    "BLK",
    "LLY",
    "JNJ",
    "UNH",
    "ABBV",
    "MRK",
    "AMGN",
    "TMO",
    "ABT",
    "DHR",
    "PFE",
    "CAT",
    "RTX",
    "HON",
    "LMT",
    "UNP",
    "DE",
    "BA",
    "XOM",
    "CVX",
    "COP",
    "LIN",
    "NEM",
    "NEE",
    "SO",
    "PLD",
    "AMT",
]

CRYPTO_PRIORITY_UNIVERSE = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "BNB",
    "TRX",
    "ADA",
    "AVAX",
    "TON",
    "SUI",
    "DOT",
    "NEAR",
    "ATOM",
    "ALGO",
    "ICP",
    "DOGE",
    "BCH",
    "LTC",
    "XLM",
    "ETC",
    "LINK",
    "UNI",
    "AAVE",
    "MKR",
    "INJ",
    "FIL",
    "RENDER",
    "RNDR",
    "ARB",
    "OP",
    "MATIC",
    "POL",
    "APT",
    "SEI",
    "VET",
    "FET",
    "GRT",
    "THETA",
    "EOS",
    "XTZ",
    "SAND",
    "MANA",
]

CRYPTO_EXCLUDED_TOKENS = {
    "USDT",
    "USDC",
    "DAI",
    "TUSD",
    "FDUSD",
    "BUSD",
    "USDE",
    "WBTC",
    "WETH",
    "STETH",
    "WSTETH",
}


def normalize_ticker_for_comparison(ticker: str) -> str:
    """Normalize ticker strings for equivalence checks (e.g. BRK.B vs BRK-B)."""
    s = str(ticker).strip().upper()
    for ch in ".-_/":
        s = s.replace(ch, "")
    return s


@dataclass(frozen=True)
class UniverseSelectionResult:
    assets: list[str]
    selection_method: str
    universe_size_requested: int
    universe_size_actual: int
    missing_priority_assets: list[str]
    filled_from_fallback: list[str]


def resolve_symbol(available_assets: Iterable[str], symbol: str) -> str | None:
    available = {str(asset) for asset in available_assets}
    if symbol in available:
        return symbol
    alternate = symbol.replace(".", "-")
    if alternate in available:
        return alternate
    reverse = symbol.replace("-", ".")
    if reverse in available:
        return reverse
    return None


def _strip_target_equivalents(assets: list[str], resolved_target: str) -> list[str]:
    key = normalize_ticker_for_comparison(resolved_target)
    return [a for a in assets if normalize_ticker_for_comparison(a) != key]


def strip_universe_of_target_equivalents(universe: list[str], target: str) -> list[str]:
    """Remove any universe name that compares equal to target after normalization."""
    return _strip_target_equivalents(list(universe), target)


def _coverage_ranked_assets(
    coverage: pd.DataFrame,
    *,
    resolved_target: str,
    excluded_symbols: set[str],
    limit: int,
    overlap_scores: dict[str, float] | None = None,
) -> list[str]:
    target_key = normalize_ticker_for_comparison(resolved_target)
    excluded_keys = {normalize_ticker_for_comparison(x) for x in excluded_symbols}
    mask = (
        (coverage["symbol"].astype(str).map(normalize_ticker_for_comparison) != target_key)
        & (~coverage["symbol"].astype(str).map(normalize_ticker_for_comparison).isin(excluded_keys))
        & (coverage["observations"] > 0)
        & (coverage["missing_pct"] < 1.0)
    )
    eligible = coverage.loc[mask].copy()
    if overlap_scores is not None and not eligible.empty:
        eligible["_overlap"] = eligible["symbol"].astype(str).map(lambda s: overlap_scores.get(s, 0.0))
        eligible = eligible.sort_values(
            ["_overlap", "missing_pct", "observations", "symbol"],
            ascending=[False, True, False, True],
        )
    else:
        eligible = eligible.sort_values(
            ["missing_pct", "observations", "symbol"],
            ascending=[True, False, True],
        )
    return eligible.head(limit)["symbol"].astype(str).tolist()


def _overlap_fraction(prices: pd.DataFrame, target_col: str, asset: str) -> float:
    if target_col not in prices.columns or asset not in prices.columns:
        return 0.0
    target_idx = prices[target_col].dropna().index
    if len(target_idx) == 0:
        return 0.0
    return float(prices.loc[target_idx, asset].notna().mean())


def _overlap_scores_for_symbols(
    prices: pd.DataFrame,
    target_col: str,
    symbols: Iterable[str],
) -> dict[str, float]:
    return {str(s): _overlap_fraction(prices, target_col, str(s)) for s in symbols}


def _crypto_enrich_universe_with_overlap(
    selected: list[str],
    *,
    resolved_target: str,
    prices: pd.DataFrame,
    available: list[str],
    requested_size: int,
    coverage: pd.DataFrame,
    excluded_tokens: set[str],
    min_overlap: float = 0.2,
) -> tuple[list[str], list[str]]:
    """Drop low-overlap names and refill toward requested_size; returns (assets, extra_fallback)."""
    if resolved_target not in prices.columns:
        return selected, []

    scores = _overlap_scores_for_symbols(prices, resolved_target, available)
    extra: list[str] = []
    cleaned = _strip_target_equivalents(selected, resolved_target)
    cleaned = [s for s in cleaned if scores.get(s, 0.0) >= min_overlap]
    cleaned = _strip_target_equivalents(cleaned, resolved_target)

    if len(cleaned) < 2:
        cleaned = _strip_target_equivalents(selected, resolved_target)
        cleaned = [s for s in cleaned if scores.get(s, 0.0) >= 0.05]

    while len(cleaned) < requested_size:
        remaining = requested_size - len(cleaned)
        excluded_for_fallback = excluded_tokens | set(cleaned) | {resolved_target}
        excluded_for_fallback |= {
            sym for sym in available if normalize_ticker_for_comparison(sym) == normalize_ticker_for_comparison(resolved_target)
        }
        fallback_assets = _coverage_ranked_assets(
            coverage,
            resolved_target=resolved_target,
            excluded_symbols=excluded_for_fallback,
            limit=remaining + 10,
            overlap_scores=scores,
        )
        added_any = False
        for asset in fallback_assets:
            if asset in cleaned:
                continue
            if scores.get(asset, 0.0) < 0.05:
                continue
            cleaned.append(asset)
            extra.append(asset)
            added_any = True
            if len(cleaned) >= requested_size:
                break
        if not added_any:
            break

    cleaned = cleaned[:requested_size]
    cleaned = _strip_target_equivalents(cleaned, resolved_target)
    return cleaned, extra


def _priority_list_for_market(market: str) -> list[str]:
    if market == "usa":
        return USA_PRIORITY_UNIVERSE
    if market == "crypto":
        return CRYPTO_PRIORITY_UNIVERSE
    raise ValueError(f"no priority universe configured for market {market!r}")


def _refill_universe(
    selected: list[str],
    *,
    resolved_target: str,
    available: list[str],
    requested_size: int,
    coverage: pd.DataFrame,
    excluded_tokens: set[str],
    overlap_scores: dict[str, float] | None,
    extra_filled: list[str],
) -> list[str]:
    selected = _strip_target_equivalents(list(dict.fromkeys(selected)), resolved_target)
    while len(selected) < requested_size:
        remaining = requested_size - len(selected)
        excluded_for_fallback = excluded_tokens | set(selected) | {resolved_target}
        excluded_for_fallback |= {
            sym
            for sym in available
            if normalize_ticker_for_comparison(sym) == normalize_ticker_for_comparison(resolved_target)
        }
        fallback_assets = _coverage_ranked_assets(
            coverage,
            resolved_target=resolved_target,
            excluded_symbols=excluded_for_fallback,
            limit=remaining + 20,
            overlap_scores=overlap_scores,
        )
        added = False
        for asset in fallback_assets:
            if asset in selected:
                continue
            if normalize_ticker_for_comparison(asset) == normalize_ticker_for_comparison(resolved_target):
                continue
            selected.append(asset)
            extra_filled.append(asset)
            added = True
            if len(selected) >= requested_size:
                break
        if not added:
            break
    return _strip_target_equivalents(selected, resolved_target)[:requested_size]


def select_priority_universe(
    available_assets: Iterable[str],
    target: str,
    market: str,
    requested_size: int = 30,
    fallback_by_coverage: bool = True,
    coverage: pd.DataFrame | None = None,
    reference_prices: pd.DataFrame | None = None,
) -> UniverseSelectionResult:
    available = [str(asset) for asset in available_assets]
    resolved_target = resolve_symbol(available, target)
    if resolved_target is None:
        raise KeyError(f"target asset {target!r} is not present in available assets")

    if market == "russia":
        return _select_coverage_universe(
            available,
            resolved_target,
            requested_size=requested_size,
            coverage=coverage,
        )

    priority_list = _priority_list_for_market(market)
    excluded_tokens = set(CRYPTO_EXCLUDED_TOKENS) if market == "crypto" else set()
    target_key = normalize_ticker_for_comparison(resolved_target)

    selected: list[str] = []
    missing_priority: list[str] = []
    for priority_symbol in priority_list:
        if normalize_ticker_for_comparison(priority_symbol) == target_key:
            continue
        if priority_symbol in excluded_tokens:
            continue
        resolved = resolve_symbol(available, priority_symbol)
        if resolved is None:
            missing_priority.append(priority_symbol)
            continue
        if normalize_ticker_for_comparison(resolved) == target_key:
            continue
        if resolved in selected:
            continue
        selected.append(resolved)
        if len(selected) >= requested_size:
            break

    selected = _strip_target_equivalents(selected, resolved_target)

    filled_from_fallback: list[str] = []
    overlap_scores: dict[str, float] | None = None
    if market == "crypto" and reference_prices is not None:
        overlap_scores = _overlap_scores_for_symbols(reference_prices, resolved_target, available)

    if len(selected) < requested_size and fallback_by_coverage:
        if coverage is None:
            raise ValueError("coverage is required when fallback_by_coverage is True")
        selected = _refill_universe(
            selected,
            resolved_target=resolved_target,
            available=available,
            requested_size=requested_size,
            coverage=coverage,
            excluded_tokens=excluded_tokens,
            overlap_scores=overlap_scores,
            extra_filled=filled_from_fallback,
        )

    selected = _strip_target_equivalents(selected, resolved_target)

    if market == "crypto" and reference_prices is not None and coverage is not None:
        enriched, extra_overlap = _crypto_enrich_universe_with_overlap(
            selected,
            resolved_target=resolved_target,
            prices=reference_prices,
            available=available,
            requested_size=requested_size,
            coverage=coverage,
            excluded_tokens=excluded_tokens,
        )
        selected = _strip_target_equivalents(enriched, resolved_target)
        for name in extra_overlap:
            if name not in filled_from_fallback:
                filled_from_fallback.append(name)

    if len(selected) < requested_size and fallback_by_coverage and coverage is not None:
        selected = _refill_universe(
            selected,
            resolved_target=resolved_target,
            available=available,
            requested_size=requested_size,
            coverage=coverage,
            excluded_tokens=excluded_tokens,
            overlap_scores=overlap_scores,
            extra_filled=filled_from_fallback,
        )

    selected = _strip_target_equivalents(selected, resolved_target)

    if len(selected) < 2:
        raise ValueError("at least two universe assets are required for PCA replication")

    assert normalize_ticker_for_comparison(resolved_target) not in {
        normalize_ticker_for_comparison(x) for x in selected
    }, "target must not appear in universe after selection"

    if filled_from_fallback:
        method = "priority_with_coverage_fallback"
    else:
        method = "priority"

    return UniverseSelectionResult(
        assets=selected,
        selection_method=method,
        universe_size_requested=requested_size,
        universe_size_actual=len(selected),
        missing_priority_assets=missing_priority,
        filled_from_fallback=filled_from_fallback,
    )


def _select_coverage_universe(
    available: list[str],
    resolved_target: str,
    *,
    requested_size: int,
    coverage: pd.DataFrame | None,
) -> UniverseSelectionResult:
    if coverage is None:
        raise ValueError("coverage is required for Russia universe selection")
    effective_size = min(requested_size, max(len(available) - 1, 0))
    assets = _coverage_ranked_assets(
        coverage,
        resolved_target=resolved_target,
        excluded_symbols={resolved_target},
        limit=effective_size,
    )
    assets = _strip_target_equivalents(assets, resolved_target)
    if len(assets) < 2:
        raise ValueError("at least two universe assets are required for PCA replication")
    return UniverseSelectionResult(
        assets=assets,
        selection_method="coverage",
        universe_size_requested=requested_size,
        universe_size_actual=len(assets),
        missing_priority_assets=[],
        filled_from_fallback=[],
    )


def select_crypto_coverage_universe(
    available_assets: Iterable[str],
    target: str,
    *,
    requested_size: int,
    coverage: pd.DataFrame,
) -> UniverseSelectionResult:
    """Coverage-ranked crypto universe excluding stablecoins, wrapped, and staked tokens."""
    available = [str(a) for a in available_assets]
    resolved_target = resolve_symbol(available, target)
    if resolved_target is None:
        raise KeyError(f"target asset {target!r} is not present in available assets")
    excluded = {resolved_target, *CRYPTO_EXCLUDED_TOKENS}
    effective_size = min(requested_size, max(len(available) - 1, 0))
    assets = _coverage_ranked_assets(
        coverage,
        resolved_target=resolved_target,
        excluded_symbols=excluded,
        limit=effective_size,
    )
    assets = _strip_target_equivalents(assets, resolved_target)
    if len(assets) < 2:
        raise ValueError("at least two universe assets are required for PCA replication")
    return UniverseSelectionResult(
        assets=assets,
        selection_method="coverage",
        universe_size_requested=requested_size,
        universe_size_actual=len(assets),
        missing_priority_assets=[],
        filled_from_fallback=[],
    )


def select_priority_then_correlation_universe(
    available_assets: Iterable[str],
    target: str,
    *,
    requested_size: int,
    prices: pd.DataFrame,
    train_window: int,
    coverage: pd.DataFrame,
) -> UniverseSelectionResult:
    """Rank crypto priority candidates by absolute log-return correlation to the target.

    Correlations use only the last ``train_window`` rows of ``prices`` (no future data beyond
    that slice). Ranking is by ``abs(correlation)`` descending, then raw correlation descending.
    ``selection_method`` is set to ``priority_then_correlation_abs_rank`` to document this rule.
    If too few names pass the minimum overlap threshold, remaining slots are filled like
    ``priority_with_coverage_fallback`` (recorded in ``filled_from_fallback``).
    """
    available = [str(a) for a in available_assets]
    resolved_target = resolve_symbol(available, target)
    if resolved_target is None:
        raise KeyError(f"target asset {target!r} is not present in available assets")
    if resolved_target not in prices.columns:
        raise ValueError("prices must include the resolved target column")

    excluded_tokens = set(CRYPTO_EXCLUDED_TOKENS)
    priority_list = _priority_list_for_market("crypto")
    missing_priority: list[str] = []
    candidates: list[str] = []
    target_key = normalize_ticker_for_comparison(resolved_target)
    for sym in priority_list:
        if normalize_ticker_for_comparison(sym) == target_key:
            continue
        if sym in excluded_tokens:
            continue
        resolved = resolve_symbol(available, sym)
        if resolved is None:
            missing_priority.append(sym)
            continue
        if normalize_ticker_for_comparison(resolved) == target_key:
            continue
        if resolved not in prices.columns:
            missing_priority.append(sym)
            continue
        candidates.append(resolved)
    candidates = list(dict.fromkeys(_strip_target_equivalents(candidates, resolved_target)))

    tw = max(2, int(train_window))
    window = prices.iloc[-tw:] if len(prices) >= tw else prices
    lp = np.log(window.astype(float))
    lr = lp.diff().iloc[1:]

    scored: list[tuple[str, float, float]] = []
    if resolved_target in lr.columns:
        rt = lr[resolved_target]
        for asset in candidates:
            if asset == resolved_target or asset not in lr.columns:
                continue
            pair = pd.concat([rt, lr[asset]], axis=1, copy=False).dropna()
            if len(pair) < 30:
                continue
            raw_c = float(pair.iloc[:, 0].corr(pair.iloc[:, 1]))
            if not np.isfinite(raw_c):
                continue
            scored.append((asset, abs(raw_c), raw_c))
    scored.sort(key=lambda x: (-x[1], -x[2]))
    selected = [a for a, _, _ in scored[:requested_size]]
    selected = _strip_target_equivalents(selected, resolved_target)

    filled_from_fallback: list[str] = []
    overlap_scores = _overlap_scores_for_symbols(prices, resolved_target, available)
    if len(selected) < requested_size:
        selected = _refill_universe(
            selected,
            resolved_target=resolved_target,
            available=available,
            requested_size=requested_size,
            coverage=coverage,
            excluded_tokens=excluded_tokens,
            overlap_scores=overlap_scores,
            extra_filled=filled_from_fallback,
        )
    selected = _strip_target_equivalents(selected, resolved_target)[:requested_size]

    if len(selected) < 2:
        raise ValueError("at least two universe assets are required for PCA replication")

    return UniverseSelectionResult(
        assets=selected,
        selection_method="priority_then_correlation_abs_rank",
        universe_size_requested=requested_size,
        universe_size_actual=len(selected),
        missing_priority_assets=missing_priority,
        filled_from_fallback=filled_from_fallback,
    )
