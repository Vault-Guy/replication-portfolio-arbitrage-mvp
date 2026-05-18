import pandas as pd

from sarb.strategy.signals import apply_signal_shift, generate_ou_signals


def test_apply_signal_shift_moves_execution_forward():
    signals = pd.Series([0, 1, -1], index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]))
    shifted = apply_signal_shift(signals, shift_bars=1)
    assert pd.isna(shifted.iloc[0])
    assert shifted.iloc[1:].tolist() == [0, 1]


def test_generate_ou_signals_respects_thresholds():
    zscores = pd.Series([-1.5, 1.5, 0.0], index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]))
    signals = generate_ou_signals(
        zscores,
        open_long=-1.25,
        open_short=1.25,
        close_long=-0.5,
        close_short=0.75,
    )
    assert signals.iloc[0] == -1
    assert signals.iloc[1] == 1
    assert signals.iloc[2] == 0
