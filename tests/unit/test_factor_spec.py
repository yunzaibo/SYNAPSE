import tempfile
from pathlib import Path

from synapse.factor.spec import FactorSpec


def _make_spec(**overrides) -> FactorSpec:
    defaults = dict(
        factor_id="test-factor",
        name="Test Factor",
        description="A test factor",
        domain="cross_sectional_equity",
        inputs=["close"],
        formula="close / close.shift(20) - 1",
        frequency="daily",
        direction="positive",
        universe="sample",
        created_by="human",
        version="1.0",
    )
    defaults.update(overrides)
    return FactorSpec(**defaults)


def test_create_factor_spec():
    spec = _make_spec()
    assert spec.factor_id == "test-factor"
    assert spec.version == "1.0"
    assert spec.domain == "cross_sectional_equity"


def test_yaml_roundtrip():
    spec = _make_spec()
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "spec.yaml"
        spec.to_yaml(path)
        loaded = FactorSpec.from_yaml(path)
        assert loaded.factor_id == spec.factor_id
        assert loaded.name == spec.name
        assert loaded.formula == spec.formula
        assert loaded.version == spec.version


def test_next_version():
    spec = _make_spec(version="1.0")
    new_spec = spec.next_version()
    assert new_spec.version == "1.1"
    assert new_spec.factor_id == spec.factor_id


def test_next_version_major():
    spec = _make_spec(version="2.9")
    new_spec = spec.next_version()
    assert new_spec.version == "2.10"
