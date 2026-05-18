from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from sarb.types import CanonicalPricePanel, StrategyConfig


@dataclass
class BacktestEngine:
    """Placeholder backtest runner; PnL accounting comes in a later step."""

    strategy_config: StrategyConfig

    def run(self, panel: CanonicalPricePanel, signals: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("Backtest execution will be implemented in a later step.")
