from __future__ import annotations

import numpy as np
import pandas as pd


def compute_simple_returns(prices: pd.DataFrame) -> pd.DataFrame:
    returns = prices.pct_change()
    return returns.iloc[1:]


def compute_log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    log_prices = np.log(prices.astype(float))
    returns = log_prices.diff()
    return returns.iloc[1:]
