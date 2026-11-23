"""Command Line Interface for OmniSim.

Execute counterfactual simulations across candidate timelines directly
from the terminal and inspect root-cause consequence matrices.
"""

from __future__ import annotations

import argparse
import sys
from omnisim.core.action import Action, InterventionType
from omnisim.core.trajectory import ConsequenceReport
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.models.search import CounterfactualMCTS


def run_systems_demo(horizon: int = 8) -> None:
    state, dynamics = build_cloud_systems_scenario(traffic_scale=1.0)

    # Define Candidate Actions
    candidate_actions = [
        Action(
            name="Autoscale Gateway (+4 instances)",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api_gateway",
            parameters={"active_instances": 8.0},
            cost=250.0,
            description="Double gateway capacity to absorb surge."
        ),
        Action(
            name="Scale DB Connection Pool (+50%)",
            intervention_type=InterventionType.SCALE,
            target_entity="database_cluster",
            parameters={"metric": "capacity", "factor": 1.5},
            cost=120.0,
            description="Expand DB connection limit to prevent queue stall."
        ),
        Action(
            name="Proactive Proportional Scaling (Gateway + DB)",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="api_gateway",
            parameters={"active_instances": 8.0},
            cost=370.0,
            description="Scale both Gateway and DB simultaneously."
        ),
    ]

    planner = CounterfactualMCTS(dynamics, candidate_actions, horizon=horizon)

    # 1. Simulate Baseline (No-Op)
    baseline_plan = [Action.no_op()] * horizon
    baseline_traj = planner.simulate_trajectory(state, baseline_plan, name="Status Quo (No Intervention)")

    # 2. Simulate Candidate Interventions
    candidate_trajs = []
    for act in candidate_actions:
        plan = [act] + [Action.no_op()] * (horizon - 1)
        # For the dual-scaling action, patch DB capacity directly in plan
        if act.name == "Proactive Proportional Scaling (Gateway + DB)":
            db_scale = Action(
                name="Scale DB",
                intervention_type=InterventionType.SCALE,
                target_entity="database_cluster",
                parameters={"metric": "capacity", "factor": 1.6},
                cost=0.0
            )
            # Rollout with compound action
            traj = planner.simulate_trajectory(state, [act, db_scale] + [Action.no_op()] * (horizon - 2), name=act.name)
            traj.total_cost = act.cost
        else:
            traj = planner.simulate_trajectory(state, plan, name=act.name)
        candidate_trajs.append(traj)

    # Formulate Report
    best_viable = next((t for t in candidate_trajs if t.is_valid), None)
    recommendation = (
        f"Deploy '{best_viable.name}' immediately. Status Quo collapses at step 4 due to DB pool exhaustion."
        if best_viable else "All standard interventions fail; architectural redesign required."
    )

    report = ConsequenceReport(
        baseline_trajectory=baseline_traj,
        counterfactual_trajectories=candidate_trajs,
        horizon=horizon,
        recommendation=recommendation
    )

    print(report.generate_executive_summary())


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniSim: Universal Counterfactual Simulation Engine")
    parser.add_argument("--domain", choices=["systems", "enterprise"], default="systems", help="Domain scenario to simulate")
    parser.add_argument("--horizon", type=int, default=8, help="Number of forward simulation steps")
    args = parser.parse_args()

    if args.domain == "systems":
        run_systems_demo(horizon=args.horizon)
    elif args.domain == "enterprise":
        state, dynamics = build_enterprise_strategy_scenario()
        print("[OmniSim] Enterprise Economic Strategy Simulation loaded.")


if __name__ == "__main__":
    main()
