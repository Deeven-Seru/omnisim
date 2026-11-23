"""Real-World Terraform Infrastructure Simulation & Fire Detection Test.

Validates that OmniSim accurately ingests real Terraform HCL architectures,
simulates operational scaling dynamics, and catches architectural fires
(such as the classic AWS ASG vs. RDS max_connections mismatch) before 'terraform apply'.
"""

from __future__ import annotations

import unittest
from omnisim.core.action import Action, InterventionType
from omnisim.core.state import UniversalState
from omnisim.ingest.terraform import TerraformIngester
from omnisim.models.dynamics import WorldDynamicsModel
from omnisim.models.search import CounterfactualMCTS

# Realistic production Terraform HCL defining a scalable web tier + RDS backend
REAL_WORLD_TERRAFORM_HCL = """
resource "aws_lb" "main_alb" {
  name               = "app-load-balancer"
  load_balancer_type = "application"
}

resource "aws_autoscaling_group" "web_cluster" {
  name                 = "production-web-asg"
  min_size             = 4
  max_size             = 28
  desired_capacity     = 4
  health_check_type    = "ELB"
}

resource "aws_db_instance" "primary_rds" {
  identifier        = "production-postgres-db"
  instance_class    = "db.t3.medium"    # AWS hard limit: ~412 max_connections
  allocated_storage = 100
  engine            = "postgres"
}
"""


class TestTerraformCatchFireSimulation(unittest.TestCase):

    def test_terraform_ingestion_and_limits(self):
        """Step 1: Test that Terraform HCL parses correctly and calculates AWS hardware limits."""
        state = TerraformIngester.parse_hcl_text(REAL_WORLD_TERRAFORM_HCL)

        self.assertIn("asg_web_cluster", state.entities)
        self.assertIn("rds_primary_rds", state.entities)
        self.assertIn("alb_main_alb", state.entities)

        # Check that AWS RDS db.t3.medium calculated max_connections = 412.0
        db = state.entities["rds_primary_rds"]
        self.assertEqual(db.metrics["max_connections"], 412.0)
        self.assertEqual(len(state.invariants), 1)
        self.assertIn("Connection Exhaustion", state.invariants[0].name)

    def test_terraform_simulation_catches_fire(self):
        """Step 2: Simulate traffic ramp-up on the Terraform infrastructure.
        
        The ASG automatically scales up from 4 instances to 26 instances under traffic surge.
        Each web instance opens 18 database connections (26 * 18 = 468 connection demand).
        The Terraform infrastructure MUST CATCH FIRE because 468 > 412 max_connections!
        """
        state = TerraformIngester.parse_hcl_text(REAL_WORLD_TERRAFORM_HCL)

        # Dynamics hook simulating AWS Auto Scaling under traffic load
        dynamics = WorldDynamicsModel()

        def aws_cloud_dynamics(st: UniversalState, act: Action):
            asg = st.entities.get("asg_web_cluster")
            rds = st.entities.get("rds_primary_rds")
            if not asg or not rds:
                return

            # Simulate traffic-driven ASG scale-out (4 -> 8 -> 14 -> 20 -> 24 -> 26 instances)
            step = st.step
            target_instances = min(asg.metrics.get("max_size", 28.0), 4.0 + (step * 4.5))
            asg.metrics["active_instances"] = target_instances

            # Connection demand: instances * 18 connections each
            conn_demand = target_instances * 18.0
            rds.metrics["active_connections"] = conn_demand
            max_limit = rds.metrics.get("max_connections", 412.0)
            saturation = min(1.0, conn_demand / max_limit)
            rds.metrics["pool_saturation"] = saturation

            # When saturation breaches 90%, RDS enters thread starvation
            if saturation >= 0.90:
                rds.metrics["error_rate"] = 0.55
                rds.metrics["latency_ms"] = 350.0  # Massive query latency spike

        dynamics.register_transition_hook(aws_cloud_dynamics)

        # Candidate Interventions to test:
        # A: Status Quo (Run with current Terraform HCL)
        # B: Terraform Remediation 1: Resize RDS to db.r6g.large (1,365 max_connections)
        act_resize_rds = Action(
            name="Terraform Fix: Upgrade RDS to db.r6g.large (1,365 conn)",
            intervention_type=InterventionType.PARAM_TUNE,
            target_entity="rds_primary_rds",
            parameters={"max_connections": 1365.0},
            cost=180.0
        )

        planner = CounterfactualMCTS(dynamics, [act_resize_rds], horizon=6)

        # Rollout Status Quo
        baseline_traj = planner.simulate_trajectory(state, [Action.no_op()] * 6, name="Terraform Status Quo (db.t3.medium)")
        remediated_traj = planner.simulate_trajectory(state, [act_resize_rds] + [Action.no_op()] * 5, name=act_resize_rds.name)

        print("\n" + "=" * 80)
        print("TERRAFORM CATCH FIRE SIMULATION AUDIT")
        print("=" * 80)
        print(f"Status Quo Baseline Violations: {len(baseline_traj.all_violations)}")
        for step, inv, val, msg in baseline_traj.all_violations:
            print(f"  [VIOLATION] Step {step}: {msg}")

        print(f"\nRemediated Terraform Violations: {len(remediated_traj.all_violations)}")
        print(f"Remediated RDS Saturation at peak ASG: {remediated_traj.final_state.get_metric('rds_primary_rds', 'pool_saturation')*100:.1f}%")

        # ASSERTIONS:
        # 1. Baseline Terraform HCL MUST CATCH FIRE (fail with critical violations)
        self.assertFalse(baseline_traj.is_valid)
        self.assertGreaterEqual(len(baseline_traj.all_violations), 1)

        # 2. Check the exact step where fire caught:
        # At Step 5: target_instances = 4 + (5 * 4.5) = 26.5 -> 26.5 * 18 = 477 connections > 412 limit!
        first_fire_step = baseline_traj.all_violations[0][0]
        self.assertIn(first_fire_step, [4, 5])

        # 3. Remediated Terraform plan with db.r6g.large MUST SURVIVE with 0 violations
        self.assertTrue(remediated_traj.is_valid)
        self.assertEqual(len(remediated_traj.all_violations), 0)
        self.assertLess(remediated_traj.final_state.get_metric("rds_primary_rds", "pool_saturation"), 0.40)
        print("[OK] Terraform Catch Fire Test Passed: OmniSim caught the exact AWS RDS max_connections fire before deployment!")


if __name__ == "__main__":
    unittest.main()
