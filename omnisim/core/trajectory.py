"""Trajectory and Consequence Reporting for OmniSim.

Captures multi-step rollout timelines and aggregates counterfactual comparisons
between baseline realities and proposed intervention timelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from omnisim.core.action import Action
from omnisim.core.state import Invariant, UniversalState


@dataclass
class StepSnapshot:
    step: int
    state: UniversalState
    action_taken: Action
    violations: List[Tuple[Invariant, float, str]]
    delta_vs_baseline: Dict[str, float] = field(default_factory=dict)


@dataclass
class Trajectory:
    name: str
    action_sequence: List[Action]
    snapshots: List[StepSnapshot] = field(default_factory=list)
    total_cost: float = 0.0

    @property
    def final_state(self) -> UniversalState:
        return self.snapshots[-1].state if self.snapshots else None

    @property
    def all_violations(self) -> List[Tuple[int, Invariant, float, str]]:
        results = []
        for snap in self.snapshots:
            for v in snap.violations:
                results.append((snap.step, v[0], v[1], v[2]))
        return results

    @property
    def is_valid(self) -> bool:
        """True if zero CRITICAL invariants were violated during rollout."""
        for snap in self.snapshots:
            for inv, _, _ in snap.violations:
                if inv.severity == "CRITICAL":
                    return False
        return True


@dataclass
class ConsequenceReport:
    """Formal executive analysis comparing a baseline future against counterfactual interventions."""
    baseline_trajectory: Trajectory
    counterfactual_trajectories: List[Trajectory]
    horizon: int
    recommendation: str = ""
    analysis_details: Dict[str, Any] = field(default_factory=dict)

    def generate_executive_summary(self) -> str:
        lines = []
        lines.append("=" * 80)
        lines.append("OMNISIM COUNTERFACTUAL CONSEQUENCE REPORT")
        lines.append(f"Simulation Horizon: {self.horizon} steps | Candidate Timelines: {len(self.counterfactual_trajectories) + 1}")
        lines.append("=" * 80)

        # Baseline Status
        b_viols = len(self.baseline_trajectory.all_violations)
        lines.append(f"\n[BASELINE TIMELINE: {self.baseline_trajectory.name}]")
        lines.append(f"  Critical Invariant Violations: {b_viols}")
        if b_viols > 0:
            for step, inv, val, msg in self.baseline_trajectory.all_violations[:3]:
                lines.append(f"    - Step {step}: {inv.name} [{inv.severity}] -> {msg}")
            if b_viols > 3:
                lines.append(f"    ... and {b_viols - 3} more violations.")
        else:
            lines.append("    Status: Stable under baseline trajectory.")

        # Counterfactual Comparison
        lines.append("\n[COUNTERFACTUAL TIMELINES COMPARISON]")
        for traj in self.counterfactual_trajectories:
            c_viols = len(traj.all_violations)
            validity = "VIABLE" if traj.is_valid else "FAILED"
            lines.append(f"\n  Timeline: '{traj.name}' [{validity}]")
            lines.append(f"    Total Action Cost: ${traj.total_cost:,.2f}")
            lines.append(f"    Critical Violations: {c_viols}")

            # Highlight delta metrics from final state
            if self.baseline_trajectory.final_state and traj.final_state:
                lines.append("    Key Final State Deltas vs Baseline:")
                for e_id in sorted(traj.final_state.entities.keys()):
                    b_entity = self.baseline_trajectory.final_state.entities.get(e_id)
                    c_entity = traj.final_state.entities.get(e_id)
                    if b_entity and c_entity:
                        for m_key in sorted(c_entity.metrics.keys()):
                            b_val = b_entity.metrics.get(m_key, 0.0)
                            c_val = c_entity.metrics.get(m_key, 0.0)
                            diff = c_val - b_val
                            if abs(diff) > 1e-4:
                                pct = (diff / abs(b_val) * 100) if abs(b_val) > 1e-6 else 0.0
                                lines.append(f"      * {e_id}.{m_key}: {c_val:.2f} (delta: {diff:+.2f}, {pct:+.1f}%)")

            if c_viols > 0:
                lines.append("    Violations encountered:")
                for step, inv, val, msg in traj.all_violations[:3]:
                    lines.append(f"      - Step {step}: {inv.name} -> {msg}")

        lines.append("\n" + "-" * 80)
        lines.append(f"EXECUTIVE RECOMMENDATION: {self.recommendation}")
        lines.append("-" * 80)
        return "\n".join(lines)
