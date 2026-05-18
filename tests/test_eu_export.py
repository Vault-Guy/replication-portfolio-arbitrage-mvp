from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from sarb.utils.eu_export import export_eu_csv


def test_export_eu_csv_preserves_rows_and_formats_output(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.csv"
    frame = pd.DataFrame(
        {
            "metric": [1.25, 2.5, 3.75],
            "count": [10, 20, 30],
            "label": ["alpha", "beta", "gamma"],
        }
    )
    frame.to_csv(input_path, index=False)
    original_text = input_path.read_text(encoding="utf-8")

    output_path = tmp_path / "sample_eu.csv"
    input_rows, output_rows = export_eu_csv(input_path, output_path)

    assert input_rows == 3
    assert output_rows == 3
    assert input_path.read_text(encoding="utf-8") == original_text

    text = output_path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    assert lines[0] == "metric;count;label"
    assert lines[1] == "1,25;10;alpha"
    assert lines[2] == "2,5;20;beta"
    assert lines[3] == "3,75;30;gamma"


def test_export_eu_csv_rejects_writing_into_grid_search_raw_dir(tmp_path: Path) -> None:
    input_path = tmp_path / "results" / "grid_search" / "sample.csv"
    input_path.parent.mkdir(parents=True)
    pd.DataFrame({"metric": [1.0]}).to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="must not write into results/grid_search/"):
        export_eu_csv(input_path, input_path.parent / "sample_eu.csv")


def test_export_eu_csv_rejects_overwriting_input(tmp_path: Path) -> None:
    input_path = tmp_path / "sample.csv"
    pd.DataFrame({"metric": [1.0]}).to_csv(input_path, index=False)

    try:
        export_eu_csv(input_path, input_path)
    except ValueError as exc:
        assert "must not overwrite" in str(exc)
    else:
        raise AssertionError("expected ValueError when output path matches input path")
