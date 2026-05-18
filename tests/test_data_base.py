import pandas as pd
import pytest

from sarb.data.base import (
    apply_missing_value_policy,
    build_prices_panel,
    validate_canonical_prices,
)


def test_validate_canonical_prices_rejects_duplicate_index():
    prices = pd.DataFrame(
        {"AAA": [100.0, 101.0]},
        index=pd.to_datetime(["2020-01-01", "2020-01-01"]),
    )
    with pytest.raises(ValueError, match="duplicate timestamps"):
        validate_canonical_prices(prices)


def test_validate_canonical_prices_rejects_non_positive_values():
    prices = pd.DataFrame(
        {"AAA": [100.0, 0.0]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02"]),
    )
    with pytest.raises(ValueError, match="strictly positive"):
        validate_canonical_prices(prices)


def test_build_prices_panel_outer_join_preserves_partial_histories():
    prices = build_prices_panel(
        {
            "AAA": pd.Series(
                [100.0, 101.0],
                index=pd.to_datetime(["2020-01-01", "2020-01-02"]),
            ),
            "BBB": pd.Series(
                [50.0],
                index=pd.to_datetime(["2020-01-02"]),
            ),
        }
    )
    assert pd.isna(prices.loc["2020-01-01", "BBB"])
    assert prices.loc["2020-01-02", "BBB"] == 50.0


def test_apply_missing_value_policy_forward_fill():
    prices = pd.DataFrame(
        {
            "AAA": [100.0, pd.NA, pd.NA],
            "BBB": [50.0, 51.0, pd.NA],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )
    filled = apply_missing_value_policy(prices, "forward_fill", forward_fill_limit=2)
    assert filled.loc["2020-01-03", "AAA"] == 100.0
    assert filled.loc["2020-01-03", "BBB"] == 51.0
