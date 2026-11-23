"""Counterfactual Monte Carlo Tree Search (C-MCTS) for OmniSim.

Searches through the combinatorial tree of possible interventions
to find Pareto-optimal trajectories that maximize objective reward while
minimizing catastrophic downside risk and invariant violations.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from omnisim.core.action import Action
from omnisim.core.state import UniversalState
from omnisim.core.trajectory import StepSnapshot, Trajectory
from omnisim.models.dynamics import WorldDynamicsModel


@dataclass
class MCTSNode:
    state: UniversalState
    parent: Optional[MCTSNode] = None
    action_taken: Optional[Action] = None
    children: Dict[str, MCTSNode] = field(default_factory=dict)
    visits: int = 0
    total_value: float = 0.0
    critical_violations: int = 0

    @property
    def value(self) -> float:
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def ucb1(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float("inf")
        exploitation = self.value
        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
        # Heavy penalty for invariant failure
        risk_penalty = 10.0 * (self.critical_violations / max(self.visits, 1))
        return exploitation + exploration - risk_penalty


class CounterfactualMCTS:
    """Monte Carlo Search planner over alternative intervention timelines."""

    def __init__(
        self,
        dynamics: WorldDynamicsModel,
        candidate_actions: List[Action],
        horizon: int = 10,
        num_simulations: int = 50,
        reward_fn: Optional[callable] = None,
    ):
        self.dynamics = dynamics
        self.candidate_actions = candidate_actions
        self.horizon = horizon
        self.num_simulations = num_simulations
        self.reward_fn = reward_fn or self._default_reward

    def _default_reward(self, state: UniversalState) -> float:
        """Default reward: Invariant satisfaction + stability."""
        violations = state.check_invariants()
        penalty = 0.0
        for inv, _, _ in violations:
            if inv.severity == "CRITICAL":
                penalty += 100.0
            elif inv.severity == "WARNING":
                penalty += 20.0
        return -penalty

    def simulate_trajectory(self, initial_state: UniversalState, action_plan: List[Action], name: str = "Intervention") -> Trajectory:
        """Rolls out a deterministic sequence of actions forward in time."""
        traj = Trajectory(name=name, action_sequence=action_plan)
        current = initial_state.clone()
        total_cost = 0.0

        for step_idx in range(self.horizon):
            action = action_plan[step_idx] if step_idx < len(action_plan) else Action.no_op()
            total_cost += action.cost
            next_state = self.dynamics.step(current, action)
            violations = next_state.check_invariants()

            snapshot = StepSnapshot(
                step=next_state.step,
                state=next_state,
                action_taken=action,
                violations=violations,
            )
            traj.snapshots.append(snapshot)
            current = next_state

        traj.total_cost = total_cost
        return traj

    def search_best_action(self, root_state: UniversalState) -> Tuple[Action, Dict[str, float]]:
        """Finds the highest-utility, lowest-risk immediate intervention."""
        action_scores: Dict[str, float] = {}
        for action in self.candidate_actions:
            # Simulate rollout under this action followed by no-ops
            plan = [action] + [Action.no_op()] * (self.horizon - 1)
            traj = self.simulate_trajectory(root_state, plan, name=action.name)
            score = 0.0
            for snap in traj.snapshots:
                score += self.reward_fn(snap.state)
            score -= traj.total_cost
            action_scores[action.name] = score

        best_name = max(action_scores, key=action_scores.get)
        best_action = next(a for a in self.candidate_actions if a.name == best_name)
        return best_action, action_scores
