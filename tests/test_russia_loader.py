import pandas as pd
import pytest

from sarb.core.config import load_market_config
from sarb.data.base import validate_canonical_prices
from sarb.data.loader import load_prices


@pytest.fixture(scope="module")
def russia_data():
    return load_prices(load_market_config("russia"))


def test_russia_loader_metadata(russia_data):
    assert russia_data.metadata["frequency"] == "1D"
    assert russia_data.metadata["annualization_factor"] == 252.0
    assert russia_data.metadata["symbol_count"] >= 2


def test_russia_loader_canonical_prices(russia_data):
    prices = russia_data.prices
    validate_canonical_prices(prices)
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert (prices.dropna() > 0).all().all()
