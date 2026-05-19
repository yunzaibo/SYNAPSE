from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from synapse.factor.spec import FactorSpec


class BaseFactor(ABC):
    """Abstract base class for all factor implementations.

    Subclasses must implement factor_id(), spec(), and compute().
    """

    @classmethod
    @abstractmethod
    def factor_id(cls) -> str:
        """Return the unique factor identifier."""
        ...

    @classmethod
    @abstractmethod
    def spec(cls) -> FactorSpec:
        """Return the FactorSpec for this factor."""
        ...

    @abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """Compute factor values from input data."""
        ...

    @classmethod
    def required_columns(cls) -> list[str]:
        """Return required DataFrame columns. Default: spec.inputs."""
        return cls.spec().inputs
