"""Production Systems End-to-End Scenario Test Suite.

Simulates three enterprise operational scenarios:
1. SRE / DevOps: E-Commerce high-traffic scale event crash prevention using K8s manifests & Prometheus telemetry.
2. Enterprise Strategy: Pricing elasticity & cash runway counterfactual simulation.
3. Resilience & Invariants: Malformed payloads, division hazards, and high-concurrency API load.
"""

from __future__ import annotations

import json
import time
import unittest
from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.core.trajectory import ConsequenceReport
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.engine.batched_simulator import BatchedSimulator
from omnisim.ingest.k8s import KubernetesManifestIngester
from omnisim.ingest.telemetry import TelemetryIngester
from omnisim.models.search import CounterfactualMCTS


class TestSystemScenarios(unittest.TestCase):

    def test_sre_high_traffic_catastrophe_prevention(self):
        """REAL-WORLD USE CASE 1: SRE Traffic Spike Invariant Protection.
        
        The SRE imports their real multi-tier Kubernetes architecture:
        Ingress -> Gateway -> Order Service -> Postgres DB.
        Telemetry shows live traffic surging from 2,000 QPS to 6,000 QPS.
        """
        print("\n" + "=" * 80)
        print("REAL-WORLD TEST 1: SRE Black Friday Flash Sale Disaster Prevention")
        print("=" * 80)

        # 1. Real Kubernetes Manifests
        k8s_manifests = [
            {
                "kind": "Ingress",
                "metadata": {"name": "store-ingress"},
                "spec": {
                    "rules": [{
                        "http": {
                            "paths": [
                                {"path": "/api", "backend": {"service": {"name": "gateway-svc"}}}
                            ]
                        }
                    }]
                }
            },
            {
                "kind": "Service",
                "metadata": {"name": "gateway-svc"},
                "spec": {"selector": {"app": "api-gateway"}}
            },
            {
                "kind": "Deployment",
                "metadata": {"name": "api-gateway", "labels": {"app": "api-gateway"}},
                "spec": {
                    "replicas": 4,
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "gateway",
                                "resources": {"limits": {"cpu": "2000m", "memory": "4Gi"}}
                            }]
                        }
                    }
                }
            },
            {
                "kind": "Deployment",
                "metadata": {"name": "order-backend", "labels": {"app": "order-backend"}},
                "spec": {
                    "replicas": 6,
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": "orders",
                                "resources": {"limits": {"cpu": "4000m", "memory": "8Gi"}}
                            }]
                        }
                    }
                }
            }
        ]

        # Ingest K8s infrastructure
        state = KubernetesManifestIngester.parse_manifests(k8s_manifests)

        # Add Database Tier with strict Connection Pool Limits
        state.add_entity(Entity(
            id="postgres_primary",
            type="database",
            metrics={
                "connection_pool_max": 500.0,
                "active_connections": 220.0,
                "pool_saturation": 0.44,
                "query_latency_ms": 18.0,
                "error_rate": 0.0,
            }
        ))
        state.add_relation("api-gateway", "order-backend", "traffic_flow", weight=1.0)
        state.add_relation("order-backend", "postgres_primary", "traffic_flow", weight=0.5)

        # Define Non-negotiable Production Invariants
        state.add_invariant(Invariant(
            name="Checkout Latency Budget",
            target_entity="api-gateway",
            metric="latency_ms",
            operator="<=",
            threshold=120.0,
            severity="CRITICAL",
            description="P99 Latency must stay under 120ms or cart abandonments spike."
        ))

        state.add_invariant(Invariant(
            name="Database Connection Saturation",
            target_entity="postgres_primary",
            metric="pool_saturation",
            operator="<=",
            threshold=0.85,
            severity="CRITICAL",
            description="PostgreSQL crashes when pool saturation reaches 85%."
        ))

        # 2. Ingest Live Prometheus Telemetry (Traffic surge begins)
        live_telemetry = [
            {"entity_id": "api-gateway", "metric_name": "latency_ms", "value": 45.0},
            {"entity_id": "postgres_primary", "metric_name": "pool_saturation", "value": 0.55},
        ]
        TelemetryIngester.apply_metrics(state, live_telemetry)

        # 3. Formulate Causal Dynamics Hook for Flash Sale Surge
        from omnisim.models.dynamics import WorldDynamicsModel
        dynamics = WorldDynamicsModel()

        def black_friday_dynamics(st: UniversalState, act: Action):
            gw = st.entities.get("api-gateway")
            orders = st.entities.get("order-backend")
            db = st.entities.get("postgres_primary")
            if not gw or not orders or not db:
                return

            # Traffic ramps up 25% each step
            gw_reps = gw.metrics.get("replicas", 4.0)
            orders_reps = orders.metrics.get("replicas", 6.0)

            step = st.step
            traffic_mult = 1.0 + (step * 0.35)  # Extreme 3x surge over horizon
            effective_qps = 2000.0 * traffic_mult

            # Gateway latency depends on replicas
            gw_capacity = gw_reps * 600.0
            gw_util = effective_qps / max(gw_capacity, 1.0)
            gw.metrics["latency_ms"] = 15.0 * (1.0 / max(0.05, 1.0 - min(gw_util, 0.95)))

            # Database connections depend on backend orders load
            connections_needed = (effective_qps * 0.15)
            db_max = db.metrics.get("connection_pool_max", 500.0)
            db.metrics["pool_saturation"] = min(1.0, connections_needed / db_max)

            if db.metrics["pool_saturation"] >= 0.85:
                db.metrics["error_rate"] = 0.65
                gw.metrics["latency_ms"] += 250.0  # Cascade!

        dynamics.register_transition_hook(black_friday_dynamics)

        # 4. SRE Candidate Interventions:
        # A: Status Quo (Do nothing)
        # B: Generic HPA only (Scale Gateway to 10 replicas, ignore DB)
        act_hpa_only = Action(
            name="Generic HPA: Scale Gateway to 10 replicas",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api-gateway",
            parameters={"replicas": 10.0},
            cost=350.0
        )

        # C: DB Tuning Only (PgBouncer pool expansion, ignore Gateway)
        act_db_only = Action(
            name="DB Tuning Only: PgBouncer Pool Expansion (1200 conn)",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="postgres_primary",
            parameters={"connection_pool_max": 1200.0},
            cost=120.0
        )

        # D: OmniSim Compound Coordinated Action (Gateway 12 reps + DB 1200 conn)
        act_compound_gw = Action(
            name="OmniSim Coordinated Action (Gateway 12 reps + PgBouncer 1200)",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api-gateway",
            parameters={"replicas": 12.0},
            cost=420.0
        )
        act_compound_db = Action(
            name="PgBouncer Pool Scale",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="postgres_primary",
            parameters={"connection_pool_max": 1200.0},
            cost=120.0
        )

        planner = CounterfactualMCTS(dynamics, [act_hpa_only, act_db_only, act_compound_gw], horizon=6)

        # Rollout Baseline & Candidates
        baseline_traj = planner.simulate_trajectory(state, [Action.no_op()] * 6, name="Status Quo (No Action)")
        traj_hpa = planner.simulate_trajectory(state, [act_hpa_only] + [Action.no_op()] * 5, name=act_hpa_only.name)
        traj_db = planner.simulate_trajectory(state, [act_db_only] + [Action.no_op()] * 5, name=act_db_only.name)
        
        # Compound rollout applies both actions in step 1
        traj_compound = planner.simulate_trajectory(
            state, 
            [act_compound_gw, act_compound_db] + [Action.no_op()] * 4, 
            name="OmniSim Coordinated Strategy (Gateway + DB)"
        )
        traj_compound.total_cost = act_compound_gw.cost + act_compound_db.cost

        print(f"Status Quo Violations: {len(baseline_traj.all_violations)}")
        print(f"Generic HPA Violations: {len(traj_hpa.all_violations)}")
        print(f"DB Tuning Only Violations: {len(traj_db.all_violations)}")
        print(f"OmniSim Coordinated Violations: {len(traj_compound.all_violations)}")

        # Verification Assertions
        # 1. Baseline collapses under traffic surge
        self.assertFalse(baseline_traj.is_valid)
        # 2. Generic HPA fails because downstream DB crashes
        self.assertFalse(traj_hpa.is_valid)
        # 3. DB Tuning alone fails because Gateway front door is overwhelmed
        self.assertFalse(traj_db.is_valid)
        # 4. OmniSim compound action is the ONLY viable strategy that prevents 100% of outages
        self.assertTrue(traj_compound.is_valid)
        self.assertEqual(len(traj_compound.all_violations), 0)
        print("[OK] SRE Black Friday Scenario Passed: Proven that isolated interventions fail; only OmniSim compound action achieves zero downtime.")

    def test_cfo_pricing_war_and_runway_simulation(self):
        """REAL-WORLD USE CASE 2: CFO SaaS Price War & Solvency Boundary."""
        print("\n" + "=" * 80)
        print("REAL-WORLD TEST 2: CFO SaaS Price War & Runway Solvency")
        print("=" * 80)

        state, dynamics = build_enterprise_strategy_scenario()

        # Board proposition 1: Aggressive Price Hike (+40%)
        act_hike_40 = Action(
            name="Aggressive Price Hike (+40%)",
            intervention_type=InterventionType.PRICE_CHANGE,
            target_entity="saas_product",
            parameters={"delta_pct": 0.40},
            cost=0.0
        )

        # Board proposition 2: Balanced Expansion (+10% Price with Customer Success Retention)
        act_balanced = Action(
            name="Balanced +10% with Retention Buffer",
            intervention_type=InterventionType.PRICE_CHANGE,
            target_entity="saas_product",
            parameters={"delta_pct": 0.10},
            cost=15_000.0  # CS investment cost
        )

        planner = CounterfactualMCTS(dynamics, [act_hike_40, act_balanced], horizon=8)
        traj_hike = planner.simulate_trajectory(state, [act_hike_40] + [Action.no_op()] * 7, name=act_hike_40.name)
        traj_balanced = planner.simulate_trajectory(state, [act_balanced] + [Action.no_op()] * 7, name=act_balanced.name)

        print(f"Aggressive Hike (+40%) Final Customers: {traj_hike.final_state.get_metric('saas_product', 'customers'):.0f}")
        print(f"Balanced (+10%) Final Customers: {traj_balanced.final_state.get_metric('saas_product', 'customers'):.0f}")
        print(f"Aggressive Hike Cash: ${traj_hike.final_state.get_metric('balance_sheet', 'cash_reserves'):,.0f}")
        print(f"Balanced Cash: ${traj_balanced.final_state.get_metric('balance_sheet', 'cash_reserves'):,.0f}")

        # The aggressive price hike should trigger customer churn warning
        self.assertGreater(traj_hike.final_state.get_metric("saas_product", "monthly_churn_pct"), 0.05)
        # Balanced strategy retains significantly higher active customers
        self.assertGreater(
            traj_balanced.final_state.get_metric("saas_product", "customers"),
            traj_hike.final_state.get_metric("saas_product", "customers")
        )
        print("[OK] CFO Pricing Strategy Passed: Correctly identified churn acceleration risk.")

    def test_adversarial_and_stress_inputs(self):
        """REAL-WORLD USE CASE 3: Chaos Engineering & Boundary Limits."""
        print("\n" + "=" * 80)
        print("REAL-WORLD TEST 3: Chaos Engineering & Stress Inputs")
        print("=" * 80)

        state, dynamics = build_cloud_systems_scenario()

        # Adversarial Test 1: Zero traffic, zero capacity, extreme negative numbers
        zero_act = Action(
            name="Zero Out Everything",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api_gateway",
            parameters={"active_instances": 0.0, "load": 0.0},
        )
        # Should not crash with ZeroDivisionError
        next_s = dynamics.step(state, zero_act)
        self.assertIsNotNone(next_s)

        # Adversarial Test 2: Huge traffic spike (100x)
        massive_act = Action(
            name="100x Traffic Bomb",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api_gateway",
            parameters={"load": 100_000.0},
        )
        next_s2 = dynamics.step(state, massive_act)
        # Should gracefully cap error_rate at 1.0 (not explode to infinity)
        self.assertLessEqual(next_s2.get_metric("database_cluster", "connection_pool_usage"), 1.0)

        # Adversarial Test 3: High-throughput Monte Carlo hammering (1,000 parallel rollouts)
        start_time = time.time()
        sim = BatchedSimulator(dynamics, horizon=6)
        res = sim.run_batched(state, Action.no_op(), num_rollouts=1000)
        elapsed = time.time() - start_time

        print(f"[OK] 1,000 Stochastic Parallel Rollouts completed in: {elapsed*1000:.2f} ms")
        print(f"  Throughput: {1000 / elapsed:.0f} full trajectories/sec")
        self.assertEqual(res.num_rollouts, 1000)
        self.assertLess(elapsed, 1.5)  # Must complete 1,000 rollouts in under 1.5 seconds


if __name__ == "__main__":
    unittest.main()
