"""Comprehensive End-to-End Integration Tests for OmniSim."""

import json
import unittest
from omnisim.core.action import Action, InterventionType
from omnisim.domains.cyber import build_cyber_resilience_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.supply_chain import build_supply_chain_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.engine.batched_simulator import BatchedSimulator
from omnisim.ingest.k8s import KubernetesManifestIngester
from omnisim.ingest.telemetry import TelemetryIngester
from omnisim.models.search import CounterfactualMCTS


class TestOmniSimEndToEnd(unittest.TestCase):

    def test_kubernetes_manifest_ingestion(self):
        manifests = [
            {
                "kind": "Deployment",
                "metadata": {"name": "order-service", "labels": {"app": "orders"}},
                "spec": {
                    "replicas": 5,
                    "template": {
                        "spec": {
                            "containers": [
                                {
                                    "name": "app",
                                    "resources": {"limits": {"cpu": "2000m", "memory": "4Gi"}}
                                }
                            ]
                        }
                    }
                }
            },
            {
                "kind": "Service",
                "metadata": {"name": "order-service"},
                "spec": {"selector": {"app": "order-service"}, "ports": [{"port": 8080}]}
            }
        ]

        state = KubernetesManifestIngester.parse_manifests(manifests)
        self.assertIn("order-service", state.entities)
        self.assertEqual(state.entities["order-service"].metrics["replicas"], 5.0)
        self.assertEqual(state.entities["order-service"].metrics["cpu_limit"], 2.0)
        self.assertEqual(state.entities["order-service"].metrics["memory_limit_mb"], 4096.0)
        # Check automatic invariant creation
        self.assertEqual(len(state.invariants), 1)

    def test_telemetry_live_update(self):
        state, _ = build_cloud_systems_scenario()
        updates = [
            {"entity_id": "api_gateway", "metric_name": "load", "value": 4500.0},
            {"entity_id": "database_cluster", "metric_name": "connection_pool_usage", "value": 0.88}
        ]
        TelemetryIngester.apply_metrics(state, updates)
        self.assertEqual(state.get_metric("api_gateway", "load"), 4500.0)
        self.assertEqual(state.get_metric("database_cluster", "connection_pool_usage"), 0.88)

    def test_supply_chain_disruption_scenario(self):
        state, dynamics = build_supply_chain_scenario()
        # Supplier suffers 50% health degradation (disruption)
        disruption = Action(
            name="Supplier Bottleneck",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="supplier_fab",
            parameters={"operational_health": 0.3},
        )
        planner = CounterfactualMCTS(dynamics, [disruption], horizon=6)
        traj = planner.simulate_trajectory(state, [disruption] + [Action.no_op()] * 5)

        # Inventory buffer should decline over time
        initial_buffer = state.get_metric("assembly_plant", "inventory_buffer_days")
        final_buffer = traj.final_state.get_metric("assembly_plant", "inventory_buffer_days")
        self.assertLess(final_buffer, initial_buffer)

    def test_cyber_attack_blast_radius_and_mitigation(self):
        state, dynamics = build_cyber_resilience_scenario()
        # Unmitigated attack timeline
        planner = CounterfactualMCTS(dynamics, [], horizon=5)
        unmitigated_traj = planner.simulate_trajectory(state, [Action.no_op()] * 5)
        # Customer vault should show compromise in unmitigated baseline
        self.assertGreater(unmitigated_traj.final_state.get_metric("customer_vault", "compromise_level"), 0.0)

        # Mitigated timeline: Isolate DMZ at step 1
        isolate_action = Action(
            name="Microsegment & Isolate DMZ",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="dmz_ingress",
            parameters={"isolated": 1.0},
            cost=50.0
        )
        mitigated_traj = planner.simulate_trajectory(state, [isolate_action] + [Action.no_op()] * 4)
        # Vault must remain completely clean (0.0 compromise)
        self.assertEqual(mitigated_traj.final_state.get_metric("customer_vault", "compromise_level"), 0.0)

    def test_batched_stochastic_simulation(self):
        state, dynamics = build_cloud_systems_scenario(traffic_scale=1.3)
        sim = BatchedSimulator(dynamics, horizon=5)
        action = Action(
            name="Scale DB (+50%)",
            intervention_type=InterventionType.SCALE,
            target_entity="database_cluster",
            parameters={"metric": "capacity", "factor": 1.5},
            cost=120.0
        )
        res = sim.run_batched(state, action, num_rollouts=100)
        self.assertEqual(res.num_rollouts, 100)
        self.assertGreaterEqual(res.violation_probability, 0.0)
        self.assertLessEqual(res.violation_probability, 1.0)


if __name__ == "__main__":
    unittest.main()
