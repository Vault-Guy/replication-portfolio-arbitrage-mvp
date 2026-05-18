from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sarb.types import MarketConfig, StrategyConfig

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "configs"


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
    payload = load_yaml(CONFIG_ROOT / "markets" / f"{name}.yaml")
    return MarketConfig(
        market=payload["market"],
        raw_archive=_resolve_path(payload["raw_archive"], PROJECT_ROOT),
        canonical_path=_resolve_path(payload["canonical_path"], PROJECT_ROOT),
        loader=payload["loader"],
        settings=payload,
    )


def load_strategy_config(name: str = "pca_default") -> StrategyConfig:
    payload = load_yaml(CONFIG_ROOT / "strategy" / f"{name}.yaml")
    return StrategyConfig(name=payload["strategy"], settings=payload)
