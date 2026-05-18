from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from sarb.run import coverage_summary
from sarb.utils.io import load_results_table
from sarb.universe import (
    CRYPTO_EXCLUDED_TOKENS,
    CRYPTO_PRIORITY_UNIVERSE,
    USA_PRIORITY_UNIVERSE,
    normalize_ticker_for_comparison,
    select_priority_universe,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _coverage_frame(symbols: list[str], observations: int = 100) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": symbols,
            "first_valid": pd.Timestamp("2020-01-01"),
            "last_valid": pd.Timestamp("2024-01-01"),
            "observations": observations,
            "missing_pct": 0.0,
        }
    )


def test_target_is_never_in_selected_universe() -> None:
    available = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META"]
    result = select_priority_universe(
        available,
        "AAPL",
        "usa",
        requested_size=3,
        coverage=_coverage_frame(available),
    )
    assert "AAPL" not in result.assets


def test_usa_universe_has_thirty_assets_when_available() -> None:
    available = list(USA_PRIORITY_UNIVERSE)
    available[available.index("BRK.B")] = "BRK-B"
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "AAPL",
        "usa",
        requested_size=30,
        coverage=coverage,
    )
    assert len(result.assets) == 30
    assert result.assets[0] == "NVDA"
    assert "AAPL" not in result.assets


def test_crypto_universe_excludes_stablecoins_and_wrapped_tokens() -> None:
    available = list(CRYPTO_PRIORITY_UNIVERSE) + sorted(CRYPTO_EXCLUDED_TOKENS)
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "BTC",
        "crypto",
        requested_size=30,
        coverage=coverage,
    )
    assert not set(result.assets) & CRYPTO_EXCLUDED_TOKENS
    assert "BTC" not in result.assets


def test_usa_universe_excludes_brk_alias_when_target_is_brk_dot():
    available = [s if s != "BRK.B" else "BRK-B" for s in USA_PRIORITY_UNIVERSE]
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "BRK.B",
        "usa",
        requested_size=30,
        coverage=coverage,
    )
    keys = {normalize_ticker_for_comparison(x) for x in result.assets}
    assert "BRKB" not in keys


def test_usa_universe_excludes_brk_dot_when_target_uses_brk_dash():
    available = [s if s != "BRK.B" else "BRK-B" for s in USA_PRIORITY_UNIVERSE]
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "BRK-B",
        "usa",
        requested_size=30,
        coverage=coverage,
    )
    keys = {normalize_ticker_for_comparison(x) for x in result.assets}
    assert "BRKB" not in keys


def test_universe_never_includes_both_brk_aliases_when_both_listed():
    base = [s for s in USA_PRIORITY_UNIVERSE if s not in ("BRK.B", "BRK-B")]
    available = base[:25] + ["BRK.B", "BRK-B", "JPM", "V"]
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "BRK.B",
        "usa",
        requested_size=15,
        coverage=coverage,
    )
    keys = {normalize_ticker_for_comparison(x) for x in result.assets}
    assert "BRKB" not in keys


def test_normalize_ticker_maps_brk_variants():
    assert normalize_ticker_for_comparison("BRK.B") == normalize_ticker_for_comparison("BRK-B")
    assert normalize_ticker_for_comparison("BRK_B") == "BRKB"
    assert normalize_ticker_for_comparison("BRK/B") == "BRKB"


def test_fallback_fills_missing_priority_assets() -> None:
    available = ["BTC", "ETH", "SOL", "XRP", "BNB", "ADA", "DOGE", "LINK", "FALLBACK1", "FALLBACK2"]
    coverage = _coverage_frame(available)
    result = select_priority_universe(
        available,
        "BTC",
        "crypto",
        requested_size=8,
        coverage=coverage,
    )
    assert len(result.assets) == 8
    assert "FALLBACK1" in result.filled_from_fallback
    assert result.selection_method == "priority_with_coverage_fallback"


@pytest.mark.skipif(
    not (PROJECT_ROOT / "data" / "raw" / "usa_data.zip").is_file(),
    reason="USA raw archive is required for grid-search integration test",
)
def test_grid_search_results_include_universe_assets() -> None:
    output_dir = PROJECT_ROOT / "results" / "grid_search"
    results_path = output_dir / "grid_search_results.csv"
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "grid_search.py"),
        "--market",
        "usa",
        "--max-runs",
        "1",
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
    results = load_results_table(results_path)
    assert not results.empty
    assert "universe_assets" in results.columns
    assert "universe_selection_method" in results.columns
    assert results.loc[0, "universe_assets"]
    assert int(results.loc[0, "universe_size_actual"]) >= 2


def test_russia_uses_coverage_selection() -> None:
    available = ["AFKS", "AFLT", "LKOH", "CHMF", "GAZP", "SBER", "VTBR"]
    coverage = coverage_summary(
        pd.DataFrame(
            {
                symbol: range(len(available))
                for symbol in available
            },
            index=pd.date_range("2020-01-01", periods=len(available), freq="D"),
        )
    )
    result = select_priority_universe(
        available,
        "AFKS",
        "russia",
        requested_size=30,
        coverage=coverage,
    )
    assert result.selection_method == "coverage"
    assert "AFKS" not in result.assets
    assert len(result.assets) == len(available) - 1
