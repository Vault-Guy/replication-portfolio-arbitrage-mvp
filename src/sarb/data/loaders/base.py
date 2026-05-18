from __future__ import annotations

import importlib
import zipfile
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

import pandas as pd

from sarb.types import CanonicalPricePanel, MarketConfig


class BaseMarketLoader(ABC):
    """Convert a market-specific raw archive into the canonical price panel."""

    def __init__(self, config: MarketConfig) -> None:
        self.config = config

    @abstractmethod
    def load(self) -> CanonicalPricePanel:
        """Read raw files and return a canonical wide price panel."""

    def iter_archive_csvs(self) -> list[tuple[str, bytes]]:
        archive = Path(self.config.raw_archive)
        subdir = self.config.settings.get("archive_subdir")
        members: list[tuple[str, bytes]] = []
        with zipfile.ZipFile(archive) as handle:
            for name in handle.namelist():
                if not name.endswith(".csv"):
                    continue
                if "__MACOSX" in name:
                    continue
                if subdir and not name.startswith(f"{subdir}/"):
                    continue
                members.append((name, handle.read(name)))
        return members

    @staticmethod
    def read_csv_bytes(payload: bytes) -> pd.DataFrame:
        return pd.read_csv(BytesIO(payload))

    def symbol_from_path(self, member_name: str) -> str:
        symbol = Path(member_name).stem
        prefix = self.config.settings.get("symbol_prefix_strip")
        suffix = self.config.settings.get("symbol_suffix_strip")
        if prefix and symbol.startswith(prefix):
            symbol = symbol[len(prefix) :]
        if suffix and symbol.endswith(suffix):
            symbol = symbol[: -len(suffix)]
        return symbol


def get_loader(config: MarketConfig) -> BaseMarketLoader:
    module_name, _, class_name = config.loader.rpartition(".")
    module = importlib.import_module(module_name)
    loader_cls = getattr(module, class_name)
    return loader_cls(config)
