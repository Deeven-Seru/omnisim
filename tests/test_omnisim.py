"""Unit and Regression Test Suite for OmniSim."""

import unittest
from omnisim.core.state import UniversalState, Entity, Invariant
from omnisim.core.action import Action, InterventionType
from omnisim.core.trajectory import Trajectory, ConsequenceReport
from omnisim.models.dynamics import WorldDynamicsModel
from omnisim.models.search import CounterfactualMCTS
from omnisim.verifiers.evaluator import InvariantEvaluator
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario


class TestOmniSimCore(unittest.TestCase):

    def test_state_creation_and_cloning(self):
        state = UniversalState(step=0)
        entity = Entity(id="node1", type="compute", metrics={"cpu": 45.0})
        state.add_entity(entity)

        clone = state.clone()
        clone.set_metric("node1", "cpu", 90.0)

        self.assertEqual(state.get_metric("node1", "cpu"), 45.0)
        self.assertEqual(clone.get_metric("node1", "cpu"), 90.0)

    def test_invariant_evaluation(self):
        state = UniversalState(step=0)
        state.add_entity(Entity(id="gateway", type="gw", metrics={"latency": 120.0}))
        inv = Invariant(
            name="Max Latency",
            target_entity="gateway",
            metric="latency",
            operator="<=",
            threshold=100.0,
            severity="CRITICAL"
        )
        state.add_invariant(inv)

        violations = state.check_invariants()
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0][0].name, "Max Latency")

    def test_relational_dynamics_propagation(self):
        state = UniversalState(step=0)
        state.add_entity(Entity(id="src", type="service", metrics={"load": 500.0}))
        state.add_entity(Entity(id="tgt", type="service", metrics={"capacity": 600.0, "base_latency_ms": 10.0}))
        state.add_relation("src", "tgt", "traffic_flow", weight=1.0)

        dynamics = WorldDynamicsModel()
        next_state = dynamics.step(state, Action.no_op())

        # Load should propagate from src to tgt
        self.assertIn("load", next_state.entities["tgt"].metrics)
        self.assertEqual(next_state.entities["tgt"].metrics["load"], 500.0)

    def test_cloud_systems_simulation_and_mcts(self):
        state, dynamics = build_cloud_systems_scenario(traffic_scale=1.2)
        scale_act = Action(
            name="Autoscale Gateway",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api_gateway",
            parameters={"active_instances": 8.0},
            cost=100.0
        )
        planner = CounterfactualMCTS(dynamics, [scale_act, Action.no_op()], horizon=5)
        traj = planner.simulate_trajectory(state, [scale_act] + [Action.no_op()] * 4)

        self.assertEqual(len(traj.snapshots), 5)
        self.assertEqual(traj.total_cost, 100.0)

    def test_enterprise_scenario(self):
        state, dynamics = build_enterprise_strategy_scenario()
        hike_act = Action(
            name="Price Hike +20%",
            intervention_type=InterventionType.PRICE_CHANGE,
            target_entity="saas_product",
            parameters={"delta_pct": 0.20},
            cost=0.0
        )
        planner = CounterfactualMCTS(dynamics, [hike_act, Action.no_op()], horizon=4)
        traj = planner.simulate_trajectory(state, [hike_act] + [Action.no_op()] * 3)

        self.assertEqual(len(traj.snapshots), 4)
        final_price = traj.final_state.get_metric("saas_product", "price")
        self.assertEqual(final_price, 120.0)


if __name__ == "__main__":
    unittest.main()
