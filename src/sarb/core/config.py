from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_ROOT = PROJECT_ROOT / "configs"


@dataclass(frozen=True)
class MarketConfig:
    """Market-specific settings loaded from YAML."""

    market: str
    raw_archive: Path
    canonical_path: Path
    settings: Mapping[str, Any]

    @property
    def frequency(self) -> str:
        return str(self.settings.get("frequency", "1D"))


def _resolve_path(value: str | Path, base: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = CONFIG_ROOT / config_path
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_market_config(name: str) -> MarketConfig:
    payload = load_yaml(CONFIG_ROOT / f"{name}.yaml")
    return MarketConfig(
        market=payload["market"],
        raw_archive=_resolve_path(payload["raw_archive"], PROJECT_ROOT),
        canonical_path=PROJECT_ROOT / "data" / "canonical" / f"{name}_prices.parquet",
        settings=payload,
    )
