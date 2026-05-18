"""Thesis Evolution Analyzer — Track revision chains and confidence trajectories.

Walks parent_thesis_id chains to compute revision depth, velocity,
confidence transitions, and lineage trees for a set of theses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from synapse.core.schemas.thesis import Thesis


@dataclass
class EvolutionReport:
    """Output of thesis evolution analysis."""

    revision_depth: int
    revision_velocity_per_month: float
    confidence_trajectory: list[str]
    lineage_tree: dict
    total_theses_in_chain: int

    def to_dict(self) -> dict:
        return {
            "revision_depth": self.revision_depth,
            "revision_velocity_per_month": self.revision_velocity_per_month,
            "confidence_trajectory": self.confidence_trajectory,
            "lineage_tree": self.lineage_tree,
            "total_theses_in_chain": self.total_theses_in_chain,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EvolutionReport:
        return cls(
            revision_depth=int(data["revision_depth"]),
            revision_velocity_per_month=float(data["revision_velocity_per_month"]),
            confidence_trajectory=list(data["confidence_trajectory"]),
            lineage_tree=data["lineage_tree"],
            total_theses_in_chain=int(data["total_theses_in_chain"]),
        )


class ThesisEvolutionAnalyzer:
    """Analyzes revision chains across a collection of theses."""

    def analyze(self, theses: list[Thesis]) -> EvolutionReport:
        """Analyze the evolution of theses based on parent_thesis_id chains.

        Args:
            theses: List of Thesis objects to analyze.

        Returns:
            EvolutionReport with revision metrics and lineage info.
        """
        if not theses:
            return EvolutionReport(
                revision_depth=0,
                revision_velocity_per_month=0.0,
                confidence_trajectory=[],
                lineage_tree={},
                total_theses_in_chain=0,
            )

        by_id: dict[str, Thesis] = {t.id: t for t in theses}

        # Find root theses (no parent_thesis_id)
        roots = [t for t in theses if t.parent_thesis_id is None]

        # If no roots found, pick the thesis with earliest created_at as root
        if not roots:
            roots = [min(theses, key=lambda t: t.created_at)]

        # Walk chains from each root, tracking visited IDs to prevent cycles
        all_chains: list[list[Thesis]] = []
        visited_global: set[str] = set()

        for root in roots:
            chain = self._walk_chain(root, by_id, visited_global)
            all_chains.append(chain)

        # Pick the longest chain for primary metrics
        longest_chain = max(all_chains, key=len) if all_chains else []

        depth = max(len(chain) for chain in all_chains) if all_chains else 0
        total = sum(len(chain) for chain in all_chains)

        velocity = self._compute_velocity(longest_chain)
        trajectory = self._compute_confidence_trajectory(longest_chain)
        tree = self._build_lineage_tree(all_chains)

        return EvolutionReport(
            revision_depth=depth,
            revision_velocity_per_month=velocity,
            confidence_trajectory=trajectory,
            lineage_tree=tree,
            total_theses_in_chain=total,
        )

    def _walk_chain(
        self,
        start: Thesis,
        by_id: dict[str, Thesis],
        visited: set[str],
    ) -> list[Thesis]:
        """Walk parent_thesis_id chain from a root thesis to its deepest child.

        Uses depth-first traversal to find the longest chain. Tracks visited
        IDs to prevent infinite loops from circular references.
        """
        chain: list[Thesis] = []
        current: Optional[Thesis] = start

        while current is not None:
            if current.id in visited:
                # Circular reference detected — stop traversal
                break
            visited.add(current.id)
            chain.append(current)

            # Find children of current thesis
            children = [
                t for t in by_id.values()
                if t.parent_thesis_id == current.id and t.id not in visited
            ]

            if not children:
                break

            # Follow the child with the highest revision number (latest)
            current = max(children, key=lambda t: t.revision)

        return chain

    def _compute_velocity(self, chain: list[Thesis]) -> float:
        """Compute revision velocity (revisions per month) for a chain.

        Velocity = (chain length - 1) / months between first and last creation.
        """
        if len(chain) < 2:
            return 0.0

        timestamps = sorted(t.created_at for t in chain)
        delta = timestamps[-1] - timestamps[0]
        months = delta.days / 30.0

        if months <= 0:
            # All created at the same time — velocity is revisions per 0 months
            # Return number of revisions as velocity if same month
            return float(len(chain) - 1) if len(chain) > 1 else 0.0

        return (len(chain) - 1) / months

    def _compute_confidence_trajectory(self, chain: list[Thesis]) -> list[str]:
        """Extract confidence transitions along a chain."""
        return [t.confidence.value for t in chain]

    def _build_lineage_tree(self, chains: list[list[Thesis]]) -> dict:
        """Build a nested dict representing the thesis lineage tree.

        Format: {root_id: {child_id: {grandchild_id: ...}}}
        """
        tree: dict = {}

        for chain in chains:
            if not chain:
                continue

            current_level = tree
            for i, thesis in enumerate(chain):
                if thesis.id not in current_level:
                    current_level[thesis.id] = {}
                current_level = current_level[thesis.id]

        return tree
