from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml


@dataclass
class FactorSpec:
    factor_id: str
    name: str
    description: str
    domain: str  # cross_sectional_equity
    inputs: list[str]
    formula: str
    frequency: str  # daily | intraday
    direction: str  # positive | negative | unknown
    universe: str
    created_by: str  # human | ai | mixed
    version: str = "1.0"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "FactorSpec":
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def to_yaml(self, path: str | Path) -> None:
        with open(path, "w") as f:
            yaml.dump(asdict(self), f, default_flow_style=False)

    def next_version(self) -> "FactorSpec":
        major, minor = self.version.split(".")
        new = FactorSpec(**asdict(self))
        new.version = f"{major}.{int(minor) + 1}"
        return new
