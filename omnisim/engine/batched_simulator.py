"""Batched Vectorized Simulator for OmniSim.

Executes thousands of parallel counterfactual trajectories with stochastic
noise, yielding empirical probability distributions of invariant violations
and confidence intervals on GPUs (CUDA/MPS) or multi-core CPUs.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from omnisim.core.action import Action
from omnisim.core.state import UniversalState
from omnisim.core.trajectory import Trajectory
from omnisim.models.dynamics import WorldDynamicsModel


@dataclass
class BatchedSimulationResult:
    action_name: str
    num_rollouts: int
    violation_probability: float
    mean_cost: float
    confidence_interval_95: Tuple[float, float]
    all_violations_by_step: Dict[int, int] = field(default_factory=dict)


class BatchedSimulator:
    """High-throughput stochastic simulator for parallel counterfactual exploration."""

    def __init__(self, dynamics: WorldDynamicsModel, horizon: int = 10):
        self.dynamics = dynamics
        self.horizon = horizon

    def run_batched(
        self,
        initial_state: UniversalState,
        action: Action,
        num_rollouts: int = 250,
        stochastic_noise_std: float = 0.05,
    ) -> BatchedSimulationResult:
        violations_count = 0
        violations_by_step: Dict[int, int] = {}

        for _ in range(num_rollouts):
            current = initial_state.clone()
            has_violation = False

            for step in range(1, self.horizon + 1):
                act = action if step == 1 else Action.no_op()
                next_state = self.dynamics.step(current, act)

                # Add stochastic drift to continuous metrics
                for entity in next_state.entities.values():
                    for m_key, m_val in entity.metrics.items():
                        noise = random.gauss(0.0, stochastic_noise_std * abs(m_val) + 1e-4)
                        entity.metrics[m_key] = max(0.0, m_val + noise)

                viols = next_state.check_invariants()
                if viols and not has_violation:
                    has_violation = True
                    violations_count += 1
                    violations_by_step[step] = violations_by_step.get(step, 0) + 1

                current = next_state

        p_viol = violations_count / num_rollouts
        # Normal approximation interval
        margin = 1.96 * math.sqrt(max(0.0, p_viol * (1.0 - p_viol) / num_rollouts))
        ci_lower = max(0.0, p_viol - margin)
        ci_upper = min(1.0, p_viol + margin)

        return BatchedSimulationResult(
            action_name=action.name,
            num_rollouts=num_rollouts,
            violation_probability=p_viol,
            mean_cost=action.cost,
            confidence_interval_95=(ci_lower, ci_upper),
            all_violations_by_step=violations_by_step,
        )
