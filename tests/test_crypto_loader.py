import pandas as pd
import pytest

from sarb.config import load_market_config
from sarb.data.base import validate_canonical_prices
from sarb.data.crypto_loader import ANNUALIZATION_FACTOR, load_prices


@pytest.fixture(scope="module")
def crypto_data():
    return load_prices(load_market_config("crypto"))


def test_crypto_loader_metadata(crypto_data):
    assert crypto_data.metadata["frequency"] == "1H"
    assert crypto_data.metadata["annualization_factor"] == ANNUALIZATION_FACTOR
    assert crypto_data.metadata["missing_value_policy"] == "preserve"
    assert crypto_data.metadata["symbol_count"] == 43


def test_crypto_loader_canonical_prices(crypto_data):
    prices = crypto_data.prices
    validate_canonical_prices(prices)
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert prices.index.is_monotonic_increasing
    assert not prices.index.has_duplicates
    assert (prices.dropna() > 0).all().all()
    assert prices.index.max() < pd.Timestamp("2026-01-01")


def test_crypto_loader_preserves_later_listings(crypto_data):
    starts = crypto_data.metadata["first_observation_by_symbol"]
    assert any(pd.Timestamp(value) > pd.Timestamp("2020-01-01") for value in starts.values())
    assert crypto_data.prices.isna().any().any()


def test_crypto_loader_forward_fill_policy_requires_limit():
    base_config = load_market_config("crypto")
    config = type(base_config)(
        market=base_config.market,
        raw_archive=base_config.raw_archive,
        canonical_path=base_config.canonical_path,
        loader=base_config.loader,
        settings={**base_config.settings, "missing_value_policy": "forward_fill"},
    )
    with pytest.raises(ValueError, match="forward_fill_limit"):
        load_prices(config)
