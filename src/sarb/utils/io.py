from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RAW_CSV_SEPARATOR = ","
RAW_DECIMAL_SEPARATOR = "."
RAW_CSV_ENCODING = "utf-8"

RESULT_METRIC_COLUMNS = [
    "total_return",
    "annualized_return",
    "annualized_volatility",
    "sharpe_ratio",
    "max_drawdown",
    "turnover",
    "number_of_trades",
    "average_holding_period",
    "hit_rate",
]


def format_float_eu(value: Any, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, (float, np.floating)) and pd.isna(value):
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}".replace(".", ",")
    return str(value)


def format_dataframe_for_display_eu(df: pd.DataFrame, digits: int = 6) -> pd.DataFrame:
    display = df.copy()
    for column in display.columns:
        if pd.api.types.is_float_dtype(display[column]):
            display[column] = display[column].map(
                lambda value: format_float_eu(value, digits=digits)
            )
    return display


def validate_results_numeric_columns(
    df: pd.DataFrame,
    metric_columns: list[str] | None = None,
) -> None:
    columns = RESULT_METRIC_COLUMNS if metric_columns is None else metric_columns
    for column in columns:
        if column not in df.columns:
            continue
        series = df[column]
        if not pd.api.types.is_numeric_dtype(series):
            raise TypeError(
                f"Column {column!r} must be numeric before saving, got {series.dtype}"
            )


def validate_results_row_count(
    df: pd.DataFrame,
    minimum: int,
    *,
    path: str | Path | None = None,
) -> None:
    if len(df) >= minimum:
        return

    message = f"Expected at least {minimum} rows, got {len(df)}"
    if path is not None:
        message = f"{path}: {message}"
    raise ValueError(message)


def save_table(
    df: pd.DataFrame,
    path: str | Path,
    *,
    index: bool = False,
    validate_metrics: bool = False,
    min_rows: int | None = None,
) -> None:
    if validate_metrics:
        validate_results_numeric_columns(df)
    if min_rows is not None:
        validate_results_row_count(df, min_rows, path=path)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(
        output_path,
        index=index,
        sep=RAW_CSV_SEPARATOR,
        decimal=RAW_DECIMAL_SEPARATOR,
        encoding=RAW_CSV_ENCODING,
    )


def load_results_table(path: str | Path) -> pd.DataFrame:
    table_path = Path(path)
    if not table_path.is_file():
        raise FileNotFoundError(f"Results table not found: {table_path}")
    return pd.read_csv(table_path)
