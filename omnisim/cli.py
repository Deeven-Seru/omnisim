"""Command Line Interface for OmniSim.

Execute counterfactual simulations, launch REST gateways,
and benchmark high-throughput rollouts directly from the terminal.
"""

from __future__ import annotations

import argparse
import json
import sys
from omnisim.core.action import Action, InterventionType
from omnisim.core.trajectory import ConsequenceReport
from omnisim.domains.cyber import build_cyber_resilience_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.supply_chain import build_supply_chain_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.engine.batched_simulator import BatchedSimulator
from omnisim.ingest.k8s import KubernetesManifestIngester
from omnisim.models.search import CounterfactualMCTS
from omnisim.server import run_api_server


def run_simulation_cmd(domain: str, horizon: int) -> None:
    if domain == "systems":
        state, dynamics = build_cloud_systems_scenario(traffic_scale=1.2)
        candidate_actions = [
            Action(
                name="Autoscale Gateway (+4 instances)",
                intervention_type=InterventionType.PARAM_TUNE,
                target_entity="api_gateway",
                parameters={"active_instances": 8.0},
                cost=250.0,
            ),
            Action(
                name="Scale DB Connection Pool (+50%)",
                intervention_type=InterventionType.SCALE,
                target_entity="database_cluster",
                parameters={"metric": "capacity", "factor": 1.5},
                cost=120.0,
            ),
            Action(
                name="Proactive Proportional Scaling (Gateway + DB)",
                intervention_type=InterventionType.PARAM_TUNE,
                target_entity="api_gateway",
                parameters={"active_instances": 8.0},
                cost=370.0,
            ),
        ]
    elif domain == "cyber":
        state, dynamics = build_cyber_resilience_scenario()
        candidate_actions = [
            Action(
                name="Immediate DMZ Microsegmentation & Isolation",
                intervention_type=InterventionType.PARAM_TUNE,
                target_entity="dmz_ingress",
                parameters={"isolated": 1.0},
                cost=50.0,
            )
        ]
    elif domain == "supply_chain":
        state, dynamics = build_supply_chain_scenario()
        candidate_actions = [
            Action(
                name="Secondary Supplier Routing",
                intervention_type=InterventionType.PARAM_TUNE,
                target_entity="supplier_fab",
                parameters={"operational_health": 0.95, "lead_time_days": 12.0},
                cost=80_000.0,
            )
        ]
    else:
        state, dynamics = build_enterprise_strategy_scenario()
        candidate_actions = [
            Action(
                name="Price Hike +20%",
                intervention_type=InterventionType.PRICE_CHANGE,
                target_entity="saas_product",
                parameters={"delta_pct": 0.20},
                cost=0.0,
            )
        ]

    planner = CounterfactualMCTS(dynamics, candidate_actions, horizon=horizon)
    baseline_plan = [Action.no_op()] * horizon
    baseline_traj = planner.simulate_trajectory(state, baseline_plan, name="Status Quo (No Action)")

    candidate_trajs = []
    for act in candidate_actions:
        traj = planner.simulate_trajectory(state, [act] + [Action.no_op()] * (horizon - 1), name=act.name)
        candidate_trajs.append(traj)

    best_viable = next((t for t in candidate_trajs if t.is_valid), None)
    recommendation = (
        f"Optimal intervention: Deploy '{best_viable.name}' ($ {best_viable.total_cost:,.2f})."
        if best_viable else "All standard interventions breached critical operational boundaries."
    )

    report = ConsequenceReport(
        baseline_trajectory=baseline_traj,
        counterfactual_trajectories=candidate_trajs,
        horizon=horizon,
        recommendation=recommendation
    )
    print(report.generate_executive_summary())


def run_benchmark_cmd(domain: str, rollouts: int, horizon: int) -> None:
    print(f"\n⚡ Benchmarking OmniSim High-Throughput Rollouts ({rollouts} parallel trajectories)...")
    if domain == "systems":
        state, dynamics = build_cloud_systems_scenario(traffic_scale=1.3)
    elif domain == "cyber":
        state, dynamics = build_cyber_resilience_scenario()
    elif domain == "supply_chain":
        state, dynamics = build_supply_chain_scenario()
    else:
        state, dynamics = build_enterprise_strategy_scenario()

    sim = BatchedSimulator(dynamics, horizon=horizon)
    action = Action.no_op()
    res = sim.run_batched(state, action, num_rollouts=rollouts)

    print(f"✔ Completed {res.num_rollouts} rollouts.")
    print(f"  Invariant Violation Probability: {res.violation_probability * 100:.1f}%")
    print(f"  95% Confidence Interval: [{res.confidence_interval_95[0]*100:.1f}%, {res.confidence_interval_95[1]*100:.1f}%]")
    print(f"  Failure Distribution across Steps: {res.all_violations_by_step}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniSim: Universal Counterfactual Simulation Engine")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run counterfactual timeline simulation")
    sim_parser.add_argument("--domain", choices=["systems", "enterprise", "supply_chain", "cyber"], default="systems")
    sim_parser.add_argument("--horizon", type=int, default=6)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Launch REST & Web Visualizer Gateway")
    serve_parser.add_argument("--port", type=int, default=8088)

    # benchmark command
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark parallel stochastic rollouts")
    bench_parser.add_argument("--domain", choices=["systems", "enterprise", "supply_chain", "cyber"], default="systems")
    bench_parser.add_argument("--rollouts", type=int, default=500)
    bench_parser.add_argument("--horizon", type=int, default=6)

    args = parser.parse_args()

    if args.command == "serve":
        run_api_server(port=args.port)
    elif args.command == "benchmark":
        run_benchmark_cmd(args.domain, args.rollouts, args.horizon)
    elif args.command == "simulate" or args.command is None:
        domain = getattr(args, "domain", "systems")
        horizon = getattr(args, "horizon", 6)
        run_simulation_cmd(domain, horizon)


if __name__ == "__main__":
    main()
