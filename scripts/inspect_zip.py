from __future__ import annotations

import argparse
import json
import zipfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

DATE_COLUMN_HINTS = frozenset(
    {
        "datetime",
        "date",
        "time",
        "timestamp",
        "dt",
        "open time",
        "close time",
    }
)
PRICE_COLUMN_HINTS = frozenset(
    {
        "close",
        "adj close",
        "adjusted close",
        "adj_close",
        "price",
        "last",
    }
)


@dataclass(frozen=True)
class AssetInspection:
    member: str
    symbol: str
    columns: tuple[str, ...]
    dtypes: dict[str, str]
    row_count: int
    missing_by_column: dict[str, int]
    first_timestamp: str | None
    last_timestamp: str | None
    duplicate_timestamps: int
    primary_frequency: str | None
    frequency_mode_share: float | None
    non_primary_gap_count: int
    irregular_gap_examples: dict[str, int]


@dataclass
class ZipInspectionReport:
    archive: str
    member_count: int
    members: list[str] = field(default_factory=list)
    extension_counts: dict[str, int] = field(default_factory=dict)
    detected_schemas: dict[str, int] = field(default_factory=dict)
    detected_date_columns: list[str] = field(default_factory=list)
    detected_price_columns: list[str] = field(default_factory=list)
    layout: str = "unknown"
    assets: list[AssetInspection] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def list_zip_members(archive: str | Path) -> list[str]:
    with zipfile.ZipFile(archive) as handle:
        return [
            name
            for name in handle.namelist()
            if not name.endswith("/") and "__MACOSX" not in name
        ]


def _symbol_from_member(member: str) -> str:
    return Path(member).stem


def _detect_date_columns(columns: Iterable[str]) -> list[str]:
    detected: list[str] = []
    for column in columns:
        normalized = column.strip().lower()
        if normalized in DATE_COLUMN_HINTS or normalized.endswith("_at"):
            detected.append(column)
    return detected


def _detect_price_columns(columns: Iterable[str]) -> list[str]:
    detected: list[str] = []
    for column in columns:
        normalized = column.strip().lower()
        if normalized in PRICE_COLUMN_HINTS:
            detected.append(column)
    return detected


def _infer_layout(members: list[str], assets: list[AssetInspection]) -> str:
    if not members:
        return "empty"
    if len(members) == 1 and members[0].lower().endswith(".csv"):
        frame_columns = set(assets[0].columns) if assets else set()
        if len(frame_columns) > 3 and any(
            column.lower() not in DATE_COLUMN_HINTS and column.lower() not in PRICE_COLUMN_HINTS
            for column in frame_columns
        ):
            return "wide_single_table"
    if all(member.lower().endswith(".csv") for member in members):
        return "long_one_file_per_asset"
    return "mixed_or_unknown"


def _frequency_summary(timestamps: pd.Series) -> tuple[str | None, float | None, int, dict[str, int]]:
    if timestamps.empty:
        return None, None, 0, {}

    ordered = timestamps.sort_values()
    deltas = ordered.diff().dropna()
    if deltas.empty:
        return None, None, 0, {}

    counts = deltas.value_counts()
    primary = deltas.mode().iloc[0]
    primary_count = int(counts.loc[primary])
    mode_share = primary_count / len(deltas)
    irregular = deltas[deltas != primary]
    examples = {str(key): int(value) for key, value in irregular.value_counts().head(5).items()}
    return str(primary), float(mode_share), int(len(irregular)), examples


def inspect_member(member: str, payload: bytes) -> AssetInspection:
    frame = pd.read_csv(BytesIO(payload))
    columns = tuple(frame.columns.astype(str))
    dtypes = {column: str(frame[column].dtype) for column in frame.columns}

    date_columns = _detect_date_columns(columns)
    timestamp_column = date_columns[0] if date_columns else None
    missing_by_column = {column: int(frame[column].isna().sum()) for column in frame.columns}

    first_timestamp: str | None = None
    last_timestamp: str | None = None
    duplicate_timestamps = 0
    primary_frequency: str | None = None
    frequency_mode_share: float | None = None
    non_primary_gap_count = 0
    irregular_gap_examples: dict[str, int] = {}

    if timestamp_column is not None:
        timestamps = pd.to_datetime(frame[timestamp_column], errors="coerce")
        valid = timestamps.dropna()
        if not valid.empty:
            first_timestamp = valid.min().isoformat(sep=" ")
            last_timestamp = valid.max().isoformat(sep=" ")
        duplicate_timestamps = int(timestamps.duplicated().sum())
        (
            primary_frequency,
            frequency_mode_share,
            non_primary_gap_count,
            irregular_gap_examples,
        ) = _frequency_summary(valid)

    return AssetInspection(
        member=member,
        symbol=_symbol_from_member(member),
        columns=columns,
        dtypes=dtypes,
        row_count=len(frame),
        missing_by_column=missing_by_column,
        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,
        duplicate_timestamps=duplicate_timestamps,
        primary_frequency=primary_frequency,
        frequency_mode_share=frequency_mode_share,
        non_primary_gap_count=non_primary_gap_count,
        irregular_gap_examples=irregular_gap_examples,
    )


def inspect_zip_archive(archive: str | Path) -> ZipInspectionReport:
    archive_path = Path(archive)
    members = list_zip_members(archive_path)
    extension_counts = Counter(Path(member).suffix.lower().lstrip(".") or "no_extension" for member in members)

    assets: list[AssetInspection] = []
    schema_counter: Counter[tuple[str, ...]] = Counter()
    date_columns_counter: Counter[str] = Counter()
    price_columns_counter: Counter[str] = Counter()

    with zipfile.ZipFile(archive_path) as handle:
        for member in members:
            if not member.lower().endswith(".csv"):
                continue
            assets.append(inspect_member(member, handle.read(member)))

    for asset in assets:
        schema_counter[asset.columns] += 1
        for column in _detect_date_columns(asset.columns):
            date_columns_counter[column] += 1
        for column in _detect_price_columns(asset.columns):
            price_columns_counter[column] += 1

    detected_date_columns = [column for column, _ in date_columns_counter.most_common()]
    detected_price_columns = [column for column, _ in price_columns_counter.most_common()]
    detected_schemas = {" | ".join(columns): count for columns, count in schema_counter.items()}

    return ZipInspectionReport(
        archive=str(archive_path),
        member_count=len(members),
        members=members,
        extension_counts=dict(extension_counts),
        detected_schemas=detected_schemas,
        detected_date_columns=detected_date_columns,
        detected_price_columns=detected_price_columns,
        layout=_infer_layout(members, assets),
        assets=assets,
    )


def format_report(report: ZipInspectionReport) -> str:
    lines = [
        f"Archive: {report.archive}",
        f"Members: {report.member_count}",
        f"Extensions: {report.extension_counts}",
        f"Layout: {report.layout}",
        f"Detected schemas: {report.detected_schemas}",
        f"Date columns: {report.detected_date_columns}",
        f"Price columns: {report.detected_price_columns}",
        "",
        "Per-asset summary:",
    ]

    for asset in report.assets:
        missing_total = sum(asset.missing_by_column.values())
        lines.append(
            "  "
            + " | ".join(
                [
                    asset.symbol,
                    f"rows={asset.row_count}",
                    f"missing={missing_total}",
                    f"first={asset.first_timestamp}",
                    f"last={asset.last_timestamp}",
                    f"freq={asset.primary_frequency}",
                    f"freq_mode={asset.frequency_mode_share:.3f}" if asset.frequency_mode_share is not None else "freq_mode=na",
                    f"irregular_gaps={asset.non_primary_gap_count}",
                    f"dup_ts={asset.duplicate_timestamps}",
                ]
            )
        )
        if missing_total:
            lines.append(f"    missing_by_column={asset.missing_by_column}")
        if asset.irregular_gap_examples:
            lines.append(f"    irregular_gap_examples={asset.irregular_gap_examples}")

    return "\n".join(lines)


def inspect_archives(archives: Iterable[str | Path]) -> list[ZipInspectionReport]:
    return [inspect_zip_archive(path) for path in archives]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect raw market zip archives.")
    parser.add_argument("archives", nargs="+", help="Paths to zip archives")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    args = parser.parse_args(argv)

    reports = inspect_archives(args.archives)
    if args.json:
        print(json.dumps([report.to_dict() for report in reports], indent=2))
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
