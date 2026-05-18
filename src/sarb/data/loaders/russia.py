from __future__ import annotations

import pandas as pd

from sarb.data.canonical import build_canonical_panel, clip_panel_to_range
from sarb.data.loaders.base import BaseMarketLoader


class RussiaLoader(BaseMarketLoader):
    """Load Russian equity daily OHLC exports with TradingView-style filenames."""

    def load(self) -> object:
        timestamp_column = self.config.settings["timestamp_column"]
        price_column = self.config.settings["price_column"]
        frames: dict[str, pd.Series] = {}

        for member_name, payload in self.iter_archive_csvs():
            frame = self.read_csv_bytes(payload)
            symbol = self.symbol_from_path(member_name)
            series = frame.set_index(timestamp_column)[price_column]
            series.index = pd.to_datetime(series.index, utc=False)
            frames[symbol] = series.astype(float)

        panel = build_canonical_panel(
            frames,
            market=self.config.market,
            frequency=self.config.settings.get("frequency", "1D"),
            metadata={"source": "tradingview_export"},
        )
        return clip_panel_to_range(
            panel,
            start=self.config.settings.get("start"),
            end=self.config.settings.get("end"),
        )
