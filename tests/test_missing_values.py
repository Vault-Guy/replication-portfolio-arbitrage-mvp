import pandas as pd

from sarb.data.canonical import build_canonical_panel
from sarb.features.alignment import align_price_panel, forward_fill_prices


def test_canonical_panel_preserves_missing_values():
    panel = build_canonical_panel(
        {
            "AAA": pd.Series([100.0, pd.NA], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
            "BBB": pd.Series([50.0, 51.0], index=pd.to_datetime(["2020-01-01", "2020-01-02"])),
        },
        market="test",
        frequency="1D",
    )
    assert pd.isna(panel.prices.loc["2020-01-02", "AAA"])
    outer = align_price_panel(panel.prices, method="outer")
    assert len(outer) == 2


def test_forward_fill_is_monotone_in_time():
    prices = pd.DataFrame(
        {"AAA": [100.0, pd.NA, pd.NA, 103.0]},
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]),
    )
    filled = forward_fill_prices(prices)
    assert filled.loc["2020-01-03", "AAA"] == 100.0
