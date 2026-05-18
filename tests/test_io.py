from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sarb.utils.io import (
    RESULT_METRIC_COLUMNS,
    format_float_eu,
    load_results_table,
    save_table,
    validate_results_numeric_columns,
    validate_results_row_count,
)


def test_format_float_eu_uses_comma_decimal() -> None:
    assert format_float_eu(0.123456) == "0,123456"
    assert format_float_eu(1.25) == "1,250000"


def test_save_table_writes_comma_separated_dot_decimal_csv(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "total_return": [1.25, 2.5],
            "sharpe_ratio": [0.5, 1.1],
            "count": [3, 4],
        }
    )
    output_path = tmp_path / "results.csv"
    save_table(frame, output_path, validate_metrics=True)

    text = output_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    assert lines[0] == "total_return,sharpe_ratio,count"
    assert lines[1] == "1.25,0.5,3"
    assert lines[2] == "2.5,1.1,4"
    assert "1,25" not in text

    loaded = pd.read_csv(output_path)
    for column in ("total_return", "sharpe_ratio", "count"):
        assert pd.api.types.is_numeric_dtype(loaded[column])


def test_load_results_table_reads_standard_csv(tmp_path: Path) -> None:
    output_path = tmp_path / "legacy.csv"
    save_table(pd.DataFrame({"value": [1.25], "count": [1]}), output_path)
    loaded = load_results_table(output_path)
    assert loaded.iloc[0]["value"] == 1.25
    assert pd.api.types.is_numeric_dtype(loaded["value"])


def test_validate_results_numeric_columns_rejects_string_metrics() -> None:
    frame = pd.DataFrame({column: ["1.25"] for column in RESULT_METRIC_COLUMNS[:2]})
    with pytest.raises(TypeError, match="total_return"):
        validate_results_numeric_columns(frame)


def test_validate_results_row_count_raises_when_too_small() -> None:
    frame = pd.DataFrame({"total_return": [1.0]})
    with pytest.raises(ValueError, match="Expected at least 100 rows"):
        validate_results_row_count(frame, 100, path="grid_search_results.csv")
