from __future__ import annotations

import pandas as pd


def assert_no_future_rows(frame: pd.DataFrame, *, as_of: pd.Timestamp) -> None:
    if (frame.index > as_of).any():
        raise ValueError("history contains rows after the decision timestamp")
