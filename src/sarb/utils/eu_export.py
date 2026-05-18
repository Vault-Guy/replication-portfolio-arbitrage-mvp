from __future__ import annotations

from pathlib import Path

import pandas as pd

EU_CSV_ENCODING = "utf-8-sig"
EU_CSV_SEPARATOR = ";"
EU_DECIMAL_SEPARATOR = ","
RAW_RESULTS_DIR_NAME = "grid_search"


def export_eu_csv(input_path: str, output_path: str) -> tuple[int, int]:
    input_file = Path(input_path).resolve()
    output_file = Path(output_path).resolve()
    if input_file == output_file:
        raise ValueError("export_eu_csv must not overwrite the input file")

    if (
        output_file.parent.name == RAW_RESULTS_DIR_NAME
        and output_file.parent.parent.name == "results"
    ):
        raise ValueError("EU exports must not write into results/grid_search/")

    if not input_file.is_file():
        raise FileNotFoundError(f"Input CSV not found: {input_file}")

    frame = pd.read_csv(input_file)
    input_rows = len(frame)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(
        output_file,
        index=False,
        sep=EU_CSV_SEPARATOR,
        decimal=EU_DECIMAL_SEPARATOR,
        encoding=EU_CSV_ENCODING,
    )

    exported = pd.read_csv(
        output_file,
        sep=EU_CSV_SEPARATOR,
        decimal=EU_DECIMAL_SEPARATOR,
        encoding=EU_CSV_ENCODING,
    )
    output_rows = len(exported)
    return input_rows, output_rows
