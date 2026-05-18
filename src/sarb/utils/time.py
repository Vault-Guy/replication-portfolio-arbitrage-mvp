from __future__ import annotations


def bars_per_year(frequency: str) -> float:
    mapping = {
        "1D": 252.0,
        "1H": 24.0 * 365.0,
    }
    if frequency not in mapping:
        raise ValueError(f"unsupported frequency: {frequency}")
    return mapping[frequency]


def expected_annualization_factor(frequency: str) -> float:
    return bars_per_year(frequency)
