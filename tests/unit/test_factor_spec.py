import tempfile
from pathlib import Path
from typing import Optional

import pandas as pd
import pytest

from synapse.factor.spec import FactorSpec
from synapse.factor.base import BaseFactor
from synapse.factor.registry import FactorRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(**overrides) -> FactorSpec:
    defaults = dict(
        factor_id="momentum_6m_1m",
        name="6M-1M Momentum",
        description="Price momentum over 6 months minus 1 month",
        category="momentum",
        inputs=["close"],
        lookback_days=120,
        data_source="eastmoney",
        publication_lag=1,
        version="1.0.0",
    )
    defaults.update(overrides)
    return FactorSpec(**defaults)


# ---------------------------------------------------------------------------
# FactorSpec creation
# ---------------------------------------------------------------------------

class TestFactorSpecCreation:
    def test_all_fields(self):
        spec = _make_spec()
        assert spec.factor_id == "momentum_6m_1m"
        assert spec.name == "6M-1M Momentum"
        assert spec.category == "momentum"
        assert spec.inputs == ["close"]
        assert spec.lookback_days == 120
        assert spec.data_source == "eastmoney"
        assert spec.publication_lag == 1
        assert spec.version == "1.0.0"
        assert spec.compute_fn is None

    def test_defaults(self):
        spec = FactorSpec(
            factor_id="test_factor",
            name="Test",
            description="desc",
            category="value",
            inputs=["close"],
            lookback_days=20,
            data_source="akshare",
            publication_lag=0,
        )
        assert spec.version == "1.0.0"
        assert spec.compute_fn is None

    def test_empty_factor_id_raises(self):
        with pytest.raises(ValueError, match="factor_id must not be empty"):
            FactorSpec(
                factor_id="",
                name="Bad",
                description="desc",
                category="value",
                inputs=["close"],
                lookback_days=20,
                data_source="akshare",
                publication_lag=0,
            )

    def test_compute_fn_optional(self):
        def my_fn(data: pd.DataFrame) -> pd.Series:
            return data["close"]

        spec = _make_spec(compute_fn=my_fn)
        assert spec.compute_fn is my_fn


# ---------------------------------------------------------------------------
# FactorSpec YAML round-trip
# ---------------------------------------------------------------------------

class TestFactorSpecYaml:
    def test_yaml_roundtrip(self):
        spec = _make_spec()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "spec.yaml"
            spec.to_yaml(path)
            loaded = FactorSpec.from_yaml(path)
            assert loaded.factor_id == spec.factor_id
            assert loaded.name == spec.name
            assert loaded.lookback_days == spec.lookback_days
            assert loaded.version == spec.version
            assert loaded.compute_fn is None  # not serialized

    def test_next_version(self):
        spec = _make_spec(version="1.0.0")
        new_spec = spec.next_version()
        assert new_spec.version == "1.0.1"
        assert new_spec.factor_id == spec.factor_id

    def test_next_version_minor(self):
        spec = _make_spec(version="1.0.9")
        new_spec = spec.next_version()
        assert new_spec.version == "1.0.10"


# ---------------------------------------------------------------------------
# BaseFactor ABC
# ---------------------------------------------------------------------------

class TestBaseFactor:
    def test_subclass_implementation(self):
        class Momentum6M1M(BaseFactor):
            @classmethod
            def factor_id(cls) -> str:
                return "momentum_6m_1m"

            @classmethod
            def spec(cls) -> FactorSpec:
                return _make_spec()

            def compute(self, data: pd.DataFrame) -> pd.Series:
                return data["close"]

        factor = Momentum6M1M()
        assert factor.factor_id() == "momentum_6m_1m"
        assert isinstance(factor.spec(), FactorSpec)
        assert factor.spec().category == "momentum"

    def test_required_columns_default(self):
        class TestFactor(BaseFactor):
            @classmethod
            def factor_id(cls) -> str:
                return "test_f"

            @classmethod
            def spec(cls) -> FactorSpec:
                return _make_spec(inputs=["close", "volume"])

            def compute(self, data: pd.DataFrame) -> pd.Series:
                return data["close"]

        assert TestFactor.required_columns() == ["close", "volume"]

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseFactor()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# FactorRegistry
# ---------------------------------------------------------------------------

class TestFactorRegistry:
    def _make_factor_cls(self, fid: str = "test_factor", category: str = "momentum"):
        """Create a concrete BaseFactor subclass for testing."""
        _fid = fid
        _category = category

        class _Factor(BaseFactor):
            @classmethod
            def factor_id(cls) -> str:
                return _fid

            @classmethod
            def spec(cls) -> FactorSpec:
                return _make_spec(factor_id=_fid, category=_category)

            def compute(self, data: pd.DataFrame) -> pd.Series:
                return data["close"]

        return _Factor

    def test_register_and_get(self):
        registry = FactorRegistry()
        cls = self._make_factor_cls("momentum_6m_1m")
        registry.register(cls)
        assert registry.get_factor("momentum_6m_1m") is cls

    def test_register_duplicate_raises(self):
        registry = FactorRegistry()
        cls = self._make_factor_cls("momentum_6m_1m")
        registry.register(cls)
        with pytest.raises(ValueError, match="Duplicate factor_id"):
            registry.register(cls)

    def test_register_empty_id_raises(self):
        registry = FactorRegistry()
        cls = self._make_factor_cls(fid="")
        with pytest.raises(ValueError, match="factor_id is empty"):
            registry.register(cls)

    def test_unregister(self):
        registry = FactorRegistry()
        cls = self._make_factor_cls("momentum_6m_1m")
        registry.register(cls)
        removed = registry.unregister("momentum_6m_1m")
        assert removed is cls
        assert registry.get_factor("momentum_6m_1m") is None

    def test_unregister_nonexistent(self):
        registry = FactorRegistry()
        assert registry.unregister("nonexistent") is None

    def test_list_factors(self):
        registry = FactorRegistry()
        cls_a = self._make_factor_cls("factor_a")
        cls_b = self._make_factor_cls("factor_b")
        registry.register(cls_a)
        registry.register(cls_b)
        factors = registry.list_factors()
        assert len(factors) == 2
        assert "factor_a" in factors
        assert "factor_b" in factors

    def test_list_by_category(self):
        registry = FactorRegistry()
        cls_mom = self._make_factor_cls("momentum_6m", category="momentum")
        cls_val = self._make_factor_cls("pe_ratio", category="value")
        registry.register(cls_mom)
        registry.register(cls_val)
        momentum_factors = registry.list_by_category("momentum")
        assert len(momentum_factors) == 1
        assert "momentum_6m" in momentum_factors
        assert "pe_ratio" not in momentum_factors

    def test_list_by_category_empty(self):
        registry = FactorRegistry()
        assert registry.list_by_category("nonexistent") == {}
