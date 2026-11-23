"""Universal State Representation for OmniSim.

Represents arbitrary complex environments (computational architectures,
financial systems, engineering assemblies) as a dynamic graph of entities,
continuous metrics, relational edges, and explicit domain invariants.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class Invariant:
    """A hard or soft constraint that the world state must satisfy."""
    name: str
    target_entity: str
    metric: str
    operator: str  # '<=', '>=', '<', '>', '==', '!='
    threshold: float
    severity: str = "CRITICAL"  # 'CRITICAL', 'WARNING', 'INFO'
    description: str = ""

    def evaluate(self, state: UniversalState) -> Tuple[bool, float, str]:
        """Returns (is_satisfied, current_value, explanation)."""
        entity = state.entities.get(self.target_entity)
        if not entity:
            return False, 0.0, f"Entity '{self.target_entity}' not found in state."
        val = entity.metrics.get(self.metric)
        if val is None:
            return False, 0.0, f"Metric '{self.metric}' missing on entity '{self.target_entity}'."

        satisfied = False
        if self.operator == "<=":
            satisfied = val <= self.threshold
        elif self.operator == ">=":
            satisfied = val >= self.threshold
        elif self.operator == "<":
            satisfied = val < self.threshold
        elif self.operator == ">":
            satisfied = val > self.threshold
        elif self.operator == "==":
            satisfied = abs(val - self.threshold) < 1e-6
        elif self.operator == "!=":
            satisfied = abs(val - self.threshold) >= 1e-6

        msg = f"{self.target_entity}.{self.metric}={val:.2f} (rule: {self.operator} {self.threshold:.2f})"
        return satisfied, val, msg


@dataclass
class Entity:
    """An actor, subsystem, resource, or node within the world state."""
    id: str
    type: str  # e.g., 'service', 'database', 'financial_account', 'sensor'
    metrics: Dict[str, float] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)

    def clone(self) -> Entity:
        return Entity(
            id=self.id,
            type=self.type,
            metrics=dict(self.metrics),
            properties=copy.deepcopy(self.properties),
        )


@dataclass
class UniversalState:
    """The complete snapshot of a system at time step t."""
    step: int
    entities: Dict[str, Entity] = field(default_factory=dict)
    relations: List[Tuple[str, str, str, float]] = field(default_factory=list)  # (source, target, rel_type, weight)
    invariants: List[Invariant] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def clone(self) -> UniversalState:
        return UniversalState(
            step=self.step,
            entities={k: v.clone() for k, v in self.entities.items()},
            relations=list(self.relations),
            invariants=list(self.invariants),
            metadata=copy.deepcopy(self.metadata),
        )

    def add_entity(self, entity: Entity) -> UniversalState:
        self.entities[entity.id] = entity
        return self

    def add_relation(self, source: str, target: str, rel_type: str, weight: float = 1.0) -> UniversalState:
        self.relations.append((source, target, rel_type, weight))
        return self

    def add_invariant(self, invariant: Invariant) -> UniversalState:
        self.invariants.append(invariant)
        return self

    def check_invariants(self) -> List[Tuple[Invariant, float, str]]:
        """Returns list of violated invariants along with actual value and message."""
        violations = []
        for inv in self.invariants:
            satisfied, val, msg = inv.evaluate(self)
            if not satisfied:
                violations.append((inv, val, msg))
        return violations

    def to_feature_vector(self) -> List[float]:
        """Flattens numerical metrics into a consistent continuous vector for neural dynamics."""
        features = []
        for entity_id in sorted(self.entities.keys()):
            entity = self.entities[entity_id]
            for metric_key in sorted(entity.metrics.keys()):
                features.append(float(entity.metrics[metric_key]))
        return features

    def get_metric(self, entity_id: str, metric_name: str, default: float = 0.0) -> float:
        entity = self.entities.get(entity_id)
        if not entity:
            return default
        return entity.metrics.get(metric_name, default)

    def set_metric(self, entity_id: str, metric_name: str, value: float) -> None:
        if entity_id in self.entities:
            self.entities[entity_id].metrics[metric_name] = value
