import pandas as pd

from sarb.features.alignment import align_price_panel, drop_symbols_with_sparse_history


def test_align_price_panel_inner_drops_misaligned_rows():
    prices = pd.DataFrame(
        {
            "AAA": [100.0, 101.0, pd.NA],
            "BBB": [50.0, pd.NA, 52.0],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )
    aligned = align_price_panel(prices, method="inner")
    assert len(aligned) == 1
    assert aligned.index[0] == pd.Timestamp("2020-01-01")


def test_drop_symbols_with_sparse_history():
    prices = pd.DataFrame(
        {
            "AAA": [1.0, 2.0, 3.0],
            "BBB": [1.0, pd.NA, pd.NA],
        },
        index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
    )
    trimmed = drop_symbols_with_sparse_history(prices, min_observations=3)
    assert list(trimmed.columns) == ["AAA"]
