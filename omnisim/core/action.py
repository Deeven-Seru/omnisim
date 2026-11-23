"""Action & Intervention Definitions for OmniSim.

In a counterfactual simulation, an Action is not text: it is a structured
intervention that modifies system parameters, state variables, or network topology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class InterventionType(str, Enum):
    SCALE = "SCALE"                    # Scale compute, bandwidth, capacity, or budget
    PRICE_CHANGE = "PRICE_CHANGE"      # Adjust commercial pricing, margin, discount
    INJECT_FAULT = "INJECT_FAULT"      # Network drop, node crash, supply chain delay
    REFACTOR = "REFACTOR"              # Architectural or structural topology modification
    PARAM_TUNE = "PARAM_TUNE"          # Continuous parameter optimization
    NO_OP = "NO_OP"                    # Status-quo baseline action


@dataclass
class Action:
    """A proposed intervention to be applied to the world state."""
    name: str
    intervention_type: InterventionType
    target_entity: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0                  # Direct cost or resource overhead of taking this action
    description: str = ""

    @classmethod
    def no_op(cls) -> Action:
        return cls(
            name="Status Quo (No Action)",
            intervention_type=InterventionType.NO_OP,
            target_entity="system",
            parameters={},
            cost=0.0,
            description="Baseline timeline without intervention."
        )

    def summary(self) -> str:
        param_str = ", ".join(f"{k}={v}" for k, v in self.parameters.items())
        return f"[{self.intervention_type.value}] {self.name} on '{self.target_entity}' ({param_str})"
