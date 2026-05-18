from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


@dataclass
class PCAFactorModel:
    """Rolling PCA factor model for normalized return panels."""

    n_components: int
    standardize: bool = True

    def fit(self, returns: pd.DataFrame) -> PCAFactorModel:
        raise NotImplementedError("PCA fitting will be implemented in a later step.")

    def transform(self, returns: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError("PCA transform will be implemented in a later step.")

    def fit_transform_window(self, returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Fit on a historical window and return factor returns and loadings."""
        if returns.empty:
            raise ValueError("returns window is empty")

        values = returns.to_numpy(dtype=float)
        if self.standardize:
            scaler = StandardScaler()
            scaled = scaler.fit_transform(values)
        else:
            scaled = values

        model = PCA(n_components=self.n_components)
        factors = model.fit_transform(scaled)
        factor_index = returns.index
        factor_columns = [f"PC{i + 1}" for i in range(model.n_components_)]
        factor_returns = pd.DataFrame(factors, index=factor_index, columns=factor_columns)
        loadings = pd.DataFrame(
            model.components_.T,
            index=returns.columns,
            columns=factor_columns,
        )
        return factor_returns, loadings
