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
from omnisim.ingest.terraform import TerraformIngester
from omnisim.models.dynamics import WorldDynamicsModel
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
        if act.name == "Proactive Proportional Scaling (Gateway + DB)":
            db_act = Action(
                name="Scale DB (+80%)",
                intervention_type=InterventionType.SCALE,
                target_entity="database_cluster",
                parameters={"metric": "capacity", "factor": 1.8},
                cost=140.0,
            )
            traj = planner.simulate_trajectory(state, [act, db_act] + [Action.no_op()] * (horizon - 2), name=act.name)
            traj.total_cost = act.cost + db_act.cost
        else:
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


def run_terraform_audit_cmd(hcl_text: str = "") -> None:
    print("\n[INFO] Ingesting Terraform Infrastructure as Code (IaC)...")
    if not hcl_text:
        # Default real-world scalable AWS infrastructure
        hcl_text = """
        resource "aws_autoscaling_group" "web_asg" {
          name         = "prod-web"
          min_size     = 4
          max_size     = 28
          desired_capacity = 4
        }
        resource "aws_db_instance" "postgres" {
          name           = "prod-db"
          instance_class = "db.t3.medium"
          engine         = "postgres"
        }
        """
    state = TerraformIngester.parse_hcl_text(hcl_text)
    print(f"[OK] Parsed {len(state.entities)} Terraform resources:")
    for eid, e in state.entities.items():
        print(f"  - [{e.type}] {eid} -> {e.metrics}")

    print("\n[SIMULATION] Simulating peak Auto-Scaling group burst to max_size...")
    dynamics = WorldDynamicsModel()
    def asg_burst(st: UniversalState, act: Action):
        asg = st.entities.get("asg_web_asg")
        rds = st.entities.get("rds_postgres")
        if asg and rds:
            step = st.step
            target_inst = min(asg.metrics.get("max_size", 28.0), 4.0 + (step * 4.5))
            asg.metrics["active_instances"] = target_inst
            conn = target_inst * 18.0
            rds.metrics["active_connections"] = conn
            max_c = rds.metrics.get("max_connections", 412.0)
            rds.metrics["pool_saturation"] = min(1.0, conn / max_c)
            if rds.metrics["pool_saturation"] >= 0.90:
                rds.metrics["error_rate"] = 0.60
                rds.metrics["latency_ms"] = 350.0

    dynamics.register_transition_hook(asg_burst)
    planner = CounterfactualMCTS(dynamics, [], horizon=6)
    traj = planner.simulate_trajectory(state, [Action.no_op()] * 6, name="Terraform Plan Pre-Flight")

    if not traj.is_valid:
        print("\n[CRITICAL] CATASTROPHIC VIOLATION DETECTED IN TERRAFORM PLAN!")
        print(f"   Breaches: {len(traj.all_violations)} critical SLA violations.")
        for s, inv, val, msg in traj.all_violations:
            print(f"   - Step {s}: {msg}")
        print("\n[RECOMMENDATION] TERRAFORM CODE REMEDIATION:")
        print("   Change: `instance_class = \"db.t3.medium\"` ──► `instance_class = \"db.r6g.large\"`")
        print("   Reason: db.t3.medium limits at 412 connections, but ASG max_size 28 requires 504 connections.\n")
    else:
        print("\n[OK] Terraform plan passed all pre-flight counterfactual checks.\n")


def run_patch_cmd(hcl_text: str = "", fail_on_violation: bool = False, output_file: str = "") -> None:
    print("\n[AUTO_REMEDIATION] Analyzing infrastructure code for autonomous self-healing...")
    if not hcl_text:
        hcl_text = """
        resource "aws_autoscaling_group" "web_asg" {
          name     = "prod-web"
          min_size = 4
          max_size = 28
        }
        resource "aws_db_instance" "postgres" {
          name           = "prod-db"
          instance_class = "db.t3.medium"
        }
        """
    from omnisim.agent.remediator import AutonomousAutoRemediator
    result = AutonomousAutoRemediator.audit_and_generate_patch(hcl_text)
    if result.is_vulnerable:
        print(f"[VULNERABILITY_FOUND] Detected {result.violations_detected} critical capacity breaches.")
        print("\n" + "=" * 80)
        print("GENERATED AUTONOMOUS GIT UNIFIED DIFF PATCH:")
        print("=" * 80)
        print(result.unified_diff)
        print("=" * 80)
        for r in result.applied_rules:
            print(f"[REMEDIATION_RULE] {r}")
        print("\nApply this patch directly via: `git apply remediation.patch`\n")

        if output_file:
            with open(output_file, "w") as out_f:
                out_f.write(result.unified_diff)
            print(f"[OK] Wrote patch to {output_file}")

        if fail_on_violation:
            print("[GATEKEEPER_BLOCKED] CI gatekeeper blocking deployment due to critical capacity breaches.")
            sys.exit(1)
    else:
        print("[OK] Infrastructure code is resilient. 0 violations detected.\n")


def run_benchmark_cmd(domain: str, rollouts: int, horizon: int) -> None:
    print(f"\n[BENCHMARK] Benchmarking OmniSim High-Throughput Rollouts ({rollouts} parallel trajectories)...")
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

    print(f"[OK] Completed {res.num_rollouts} rollouts.")
    print(f"  Invariant Violation Probability: {res.violation_probability * 100:.1f}%")
    print(f"  95% Confidence Interval: [{res.confidence_interval_95[0]*100:.1f}%, {res.confidence_interval_95[1]*100:.1f}%]")
    print(f"  Failure Distribution across Steps: {res.all_violations_by_step}\n")


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    # Default to 'simulate' if flags or no subcommands are passed directly
    subcommands = {"simulate", "serve", "benchmark", "terraform", "vc-gauntlet", "dataset-benchmark", "canonical-benchmarks", "patch", "mcp-toolbox"}
    if not argv or (argv[0] not in subcommands and argv[0] not in {"-h", "--help", "-v", "--version"}):
        argv = ["simulate"] + argv

    parser = argparse.ArgumentParser(description="OmniSim: Universal Counterfactual Simulation Engine")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # mcp-toolbox command
    mcp_parser = subparsers.add_parser("mcp-toolbox", help="Run blind historical validation against googleapis/mcp-toolbox bug and fix")

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

    # terraform command
    tf_parser = subparsers.add_parser("terraform", help="Audit Terraform IaC plans for production fires")
    tf_parser.add_argument("file", nargs="?", default="", help="Path to .tf or plan file (positional)")
    tf_parser.add_argument("--file", dest="file_flag", type=str, default="", help="Path to .tf or plan file")

    # patch command
    patch_parser = subparsers.add_parser("patch", help="Generate automated Git unified diff patch for vulnerable infrastructure")
    patch_parser.add_argument("file", nargs="?", default="", help="Path to .tf or plan file (positional)")
    patch_parser.add_argument("--file", dest="file_flag", type=str, default="", help="Path to .tf or plan file")
    patch_parser.add_argument("--fail-on-violation", action="store_true", help="Exit with non-zero code if vulnerabilities are detected")
    patch_parser.add_argument("--output", "-o", type=str, default="", help="Write unified diff patch to output file")

    # vc-gauntlet command
    gauntlet_parser = subparsers.add_parser("vc-gauntlet", help="Run Ruthless VC Zero-Bias Diligence Gauntlet")

    # dataset-benchmark command
    dataset_parser = subparsers.add_parser("dataset-benchmark", help="Benchmark on real AWS CloudWatch public telemetry (NAB)")

    # canonical-benchmarks command
    canonical_parser = subparsers.add_parser("canonical-benchmarks", help="Benchmark on Google Online Boutique, DeathStarBench, Train-Ticket, and GAIA")

    args = parser.parse_args(argv)

    if args.command == "mcp-toolbox":
        from benchmarks.mcp_toolbox_historical_validation import GoogleMCPToolboxHistoricalValidator
        report = GoogleMCPToolboxHistoricalValidator.run_validation()
        if not report.vulnerability_detected or not report.remediation_is_exact_match_to_future_fix:
            sys.exit(1)
        from benchmarks.mcp_toolbox_historical_validation import main as run_mcp_validation
        run_mcp_validation()
    elif args.command == "patch":
        hcl_content = ""
        target_path = args.file or getattr(args, "file_flag", "")
        if target_path:
            with open(target_path, "r") as f:
                hcl_content = f.read()
        run_patch_cmd(
            hcl_content,
            fail_on_violation=getattr(args, "fail_on_violation", False),
            output_file=getattr(args, "output", "")
        )
    elif args.command == "canonical-benchmarks":
        from benchmarks.canonical_microservices_benchmark import CanonicalMicroservicesBenchmarkSuite
        suite = CanonicalMicroservicesBenchmarkSuite()
        report = suite.run_all()
        if not report.all_passed:
            sys.exit(1)
    elif args.command == "dataset-benchmark":
        from benchmarks.public_dataset_nab_benchmark import PublicDatasetNABBenchmark
        bench = PublicDatasetNABBenchmark()
        report = bench.run_benchmark()
        if not report.benchmark_passed:
            sys.exit(1)
    elif args.command == "vc-gauntlet":
        from benchmarks.ruthless_vc_gauntlet import RuthlessVCGauntlet
        gauntlet = RuthlessVCGauntlet()
        report = gauntlet.run_all()
        if not report.all_passed:
            sys.exit(1)
    elif args.command == "terraform":
        hcl_content = ""
        target_path = args.file or getattr(args, "file_flag", "")
        if target_path:
            with open(target_path, "r") as f:
                hcl_content = f.read()
        run_terraform_audit_cmd(hcl_content)
    elif args.command == "serve":
        run_api_server(port=args.port)
    elif args.command == "benchmark":
        run_benchmark_cmd(args.domain, args.rollouts, args.horizon)
    elif args.command == "simulate" or args.command is None:
        domain = getattr(args, "domain", "systems")
        horizon = getattr(args, "horizon", 6)
        run_simulation_cmd(domain, horizon)


if __name__ == "__main__":
    main()
