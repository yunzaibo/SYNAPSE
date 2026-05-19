from __future__ import annotations

from synapse.factor.base import BaseFactor


class FactorRegistry:
    """Central registry for factor classes.

    Maps factor_id -> factor class. Provides lookup, listing, and category filtering.
    """

    def __init__(self) -> None:
        self._factors: dict[str, type[BaseFactor]] = {}

    def register(self, factor_cls: type[BaseFactor]) -> None:
        """Register a factor class. Validates factor_id non-empty and unique."""
        fid = factor_cls.factor_id()
        if not fid:
            raise ValueError(f"Cannot register {factor_cls.__name__}: factor_id is empty")
        if fid in self._factors:
            raise ValueError(
                f"Duplicate factor_id '{fid}': "
                f"already registered as {self._factors[fid].__name__}"
            )
        self._factors[fid] = factor_cls

    def unregister(self, factor_id: str) -> type[BaseFactor] | None:
        """Remove and return factor class, or None if not found."""
        return self._factors.pop(factor_id, None)

    def get_factor(self, factor_id: str) -> type[BaseFactor] | None:
        """Look up factor class by factor_id."""
        return self._factors.get(factor_id)

    def list_factors(self) -> dict[str, type[BaseFactor]]:
        """Return all registered factors."""
        return dict(self._factors)

    def list_by_category(self, category: str) -> dict[str, type[BaseFactor]]:
        """Return factors filtered by category."""
        return {
            fid: cls
            for fid, cls in self._factors.items()
            if cls.spec().category == category
        }
