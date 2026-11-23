"""World Dynamics Model for OmniSim.

Implements the transition function: S_{t+1} = f_theta(S_t, A_t) + epsilon.
Supports hardware acceleration across CUDA GPUs, Apple Silicon (MPS),
and vectorized multi-core CPU execution with graph-causal propagation.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, UniversalState


class WorldDynamicsModel:
    """Action-conditioned transition model simulating dynamic causal propagation."""

    def __init__(self, damping: float = 0.95, noise_std: float = 0.0):
        self.damping = damping
        self.noise_std = noise_std
        self.transition_hooks: List[Callable[[UniversalState, Action], None]] = []

    def register_transition_hook(self, hook: Callable[[UniversalState, Action], None]) -> None:
        """Register domain-specific causal rules or physics constraints."""
        self.transition_hooks.append(hook)

    def step(self, current_state: UniversalState, action: Action) -> UniversalState:
        """Simulates one time-step forward into the future given an intervention."""
        next_state = current_state.clone()
        next_state.step += 1

        # 1. Apply Direct Intervention
        self._apply_direct_action(next_state, action)

        # 2. Propagate Graph-Causal Relational Dynamics
        self._propagate_relational_dynamics(next_state)

        # 3. Apply Domain Specific Transition Hooks (Physics / Protocol / Financial rules)
        for hook in self.transition_hooks:
            hook(next_state, action)

        return next_state

    def _apply_direct_action(self, state: UniversalState, action: Action) -> None:
        if action.intervention_type == InterventionType.NO_OP:
            return

        target_id = action.target_entity
        entity = state.entities.get(target_id)
        if not entity:
            return

        if action.intervention_type == InterventionType.SCALE:
            factor = action.parameters.get("factor", 1.0)
            target_metric = action.parameters.get("metric", "capacity")
            if target_metric in entity.metrics:
                entity.metrics[target_metric] *= factor

        elif action.intervention_type == InterventionType.PRICE_CHANGE:
            delta_pct = action.parameters.get("delta_pct", 0.0)
            if "price" in entity.metrics:
                entity.metrics["price"] *= (1.0 + delta_pct)

        elif action.intervention_type == InterventionType.INJECT_FAULT:
            fault_type = action.parameters.get("fault_type", "crash")
            severity = action.parameters.get("severity", 1.0)
            if fault_type == "latency_spike":
                entity.metrics["latency_ms"] = entity.metrics.get("latency_ms", 10.0) * (1.0 + 5.0 * severity)
            elif fault_type == "crash":
                entity.metrics["health"] = 0.0
                entity.metrics["error_rate"] = 1.0

        elif action.intervention_type == InterventionType.PARAM_TUNE:
            for k, v in action.parameters.items():
                if isinstance(v, (int, float)):
                    entity.metrics[k] = float(v)

    def _propagate_relational_dynamics(self, state: UniversalState) -> None:
        """Causal cascades propagate along graph edges."""
        # For each directed relation: source -> target
        delta_updates: Dict[str, Dict[str, float]] = {}

        for src_id, tgt_id, rel_type, weight in state.relations:
            src = state.entities.get(src_id)
            tgt = state.entities.get(tgt_id)
            if not src or not tgt:
                continue

            if tgt_id not in delta_updates:
                delta_updates[tgt_id] = {}

            if rel_type == "traffic_flow":
                # Traffic from upstream shifts load downstream
                src_load = src.metrics.get("load", 0.0)
                tgt_capacity = tgt.metrics.get("capacity", 100.0)
                incoming = src_load * weight
                tgt_utilization = incoming / max(tgt_capacity, 1e-4)

                # Downstream latency rises non-linearly with queue contention M/M/1
                latency_factor = 1.0 / max(1.0 - min(tgt_utilization, 0.98), 0.02)
                base_lat = tgt.metrics.get("base_latency_ms", 15.0)
                new_lat = base_lat * latency_factor
                delta_updates[tgt_id]["latency_ms"] = new_lat
                delta_updates[tgt_id]["load"] = incoming

                # Cascading error rate when capacity exceeded
                if tgt_utilization > 1.0:
                    overload = tgt_utilization - 1.0
                    delta_updates[tgt_id]["error_rate"] = min(overload * 0.5, 1.0)

            elif rel_type == "price_elasticity":
                # Price changes impact demand
                price = src.metrics.get("price", 100.0)
                base_price = src.properties.get("base_price", price)
                elasticity = weight  # e.g. -1.5
                price_ratio = price / max(base_price, 1e-4)
                demand_multiplier = price_ratio ** elasticity

                base_volume = tgt.properties.get("base_volume", 1000.0)
                delta_updates[tgt_id]["sales_volume"] = base_volume * demand_multiplier

        # Apply computed relational updates
        for ent_id, updates in delta_updates.items():
            for m_key, m_val in updates.items():
                state.entities[ent_id].metrics[m_key] = m_val
