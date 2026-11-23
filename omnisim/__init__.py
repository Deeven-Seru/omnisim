"""OmniSim: The Universal Counterfactual Simulation Engine.

Moving AI from passive autoregressive text prediction to active
action-conditioned world modeling and counterfactual simulation.
"""

from omnisim.core.state import UniversalState, Entity, Invariant
from omnisim.core.action import Action, InterventionType
from omnisim.core.trajectory import Trajectory, ConsequenceReport
from omnisim.models.dynamics import WorldDynamicsModel
from omnisim.models.search import CounterfactualMCTS
from omnisim.verifiers.evaluator import InvariantEvaluator

__version__ = "0.1.0"
__all__ = [
    "UniversalState",
    "Entity",
    "Invariant",
    "Action",
    "InterventionType",
    "Trajectory",
    "ConsequenceReport",
    "WorldDynamicsModel",
    "CounterfactualMCTS",
    "InvariantEvaluator",
]
