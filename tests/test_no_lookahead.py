import pandas as pd
import pytest

from sarb.walkforward.rolling_fit import RollingFitPipeline
from sarb.utils.validation import assert_no_future_rows


def test_assert_no_future_rows_rejects_leakage():
    frame = pd.DataFrame({"x": [1.0]}, index=pd.to_datetime(["2020-01-02"]))
    with pytest.raises(ValueError):
        assert_no_future_rows(frame, as_of=pd.Timestamp("2020-01-01"))


def test_rolling_fit_uses_only_past_window():
    index = pd.date_range("2020-01-01", periods=10, freq="D")
    returns = pd.DataFrame(
        {
            "AAA": [0.01, -0.02, 0.015, 0.0, 0.01, -0.01, 0.02, 0.0, -0.005, 0.01],
            "BBB": [0.02, -0.01, 0.01, 0.005, -0.02, 0.01, 0.0, 0.015, -0.01, 0.02],
            "CCC": [-0.01, 0.02, 0.0, 0.01, 0.015, -0.02, 0.01, 0.0, 0.02, -0.01],
        },
        index=index,
    )
    pipeline = RollingFitPipeline(
        pca_components=2,
        estimation_window=5,
        signal_shift=1,
        dt_per_year=252.0,
        thresholds={
            "open_long": -1.25,
            "open_short": 1.25,
            "close_long": -0.5,
            "close_short": 0.75,
        },
    )
    window = next(pipeline.iter_windows(returns))
    result = pipeline.fit_window(window, asset="AAA", full_returns=returns)
    assert window.decision_index == returns.index[4]
    assert result["decision_index"] == returns.index[4]
    assert window.history.index.max() <= window.decision_index
