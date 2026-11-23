"""Invariant Evaluator and Sandbox Verification for OmniSim."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from omnisim.core.state import Invariant, UniversalState
from omnisim.core.trajectory import Trajectory


class InvariantEvaluator:
    """Verifies that trajectories comply with non-negotiable operational boundaries."""

    @staticmethod
    def audit_trajectory(trajectory: Trajectory) -> Dict[str, Any]:
        critical_count = 0
        warning_count = 0
        first_failure_step: Optional[int] = None
        failure_log: List[str] = []

        for snap in trajectory.snapshots:
            for inv, val, msg in snap.violations:
                if inv.severity == "CRITICAL":
                    critical_count += 1
                    if first_failure_step is None:
                        first_failure_step = snap.step
                    failure_log.append(f"Step {snap.step} [CRITICAL]: {msg}")
                elif inv.severity == "WARNING":
                    warning_count += 1
                    failure_log.append(f"Step {snap.step} [WARNING]: {msg}")

        return {
            "trajectory_name": trajectory.name,
            "is_valid": critical_count == 0,
            "critical_violations": critical_count,
            "warning_violations": warning_count,
            "first_failure_step": first_failure_step,
            "failure_log": failure_log,
        }
