from __future__ import annotations

_ANNUALIZATION_FACTORS = {
    "1D": 252.0,
    "1H": 24.0 * 365.0,
}


def expected_annualization_factor(frequency: str) -> float:
    if frequency not in _ANNUALIZATION_FACTORS:
        raise ValueError(f"unsupported frequency: {frequency}")
    return _ANNUALIZATION_FACTORS[frequency]
