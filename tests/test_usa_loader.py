import pandas as pd
import pytest

from sarb.config import load_market_config
from sarb.data.base import validate_canonical_prices
from sarb.data.usa_loader import ANNUALIZATION_FACTOR, load_prices


@pytest.fixture(scope="module")
def usa_data():
    return load_prices(load_market_config("usa"))


def test_usa_loader_metadata(usa_data):
    assert usa_data.metadata["frequency"] == "1D"
    assert usa_data.metadata["annualization_factor"] == ANNUALIZATION_FACTOR
    assert usa_data.metadata["symbol_count"] == 142
    assert "future-selection bias" in usa_data.metadata["universe_selection_bias"]


def test_usa_loader_canonical_prices(usa_data):
    prices = usa_data.prices
    validate_canonical_prices(prices)
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert (prices.dropna() > 0).all().all()
    assert prices.index.min() >= pd.Timestamp("2016-01-01")
    assert prices.index.max() < pd.Timestamp("2026-01-01")
