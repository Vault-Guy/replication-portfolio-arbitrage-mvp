from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


@dataclass(frozen=True)
class MarketConfig:
    """Market-specific settings loaded from YAML."""

    market: str
    raw_archive: Path
    canonical_path: Path
    loader: str
    settings: Mapping[str, Any]

    @property
    def frequency(self) -> str:
        return str(self.settings.get("frequency", "1D"))


@dataclass(frozen=True)
class StrategyConfig:
    """Strategy parameters shared across markets."""

    name: str
    settings: Mapping[str, Any]


@dataclass(frozen=True)
class CanonicalPricePanel:
    """Wide price panel in the common research format."""

    prices: pd.DataFrame
    market: str
    frequency: str
    metadata: Mapping[str, Any]

    def copy(self) -> CanonicalPricePanel:
        return CanonicalPricePanel(
            prices=self.prices.copy(),
            market=self.market,
            frequency=self.frequency,
            metadata=dict(self.metadata),
        )
