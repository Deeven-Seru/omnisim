"""Automated Test Suite for Autonomous Auto-Remediator and Client SDK."""

import unittest
from omnisim.agent.remediator import AutonomousAutoRemediator
from omnisim.client import OmniSimClient
from omnisim.ingest.terraform import TerraformIngester


class TestAutoRemediatorAndSDK(unittest.TestCase):
    """Verifies autonomous Git patch synthesis and Python SDK client."""

    def setUp(self):
        self.vulnerable_hcl = """
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

    def test_auto_remediation_patch_generation(self):
        result = AutonomousAutoRemediator.audit_and_generate_patch(self.vulnerable_hcl)

        self.assertTrue(result.is_vulnerable)
        self.assertGreater(result.violations_detected, 0)
        self.assertIn("db.r6g.large", result.remediated_code)
        self.assertNotIn("db.t3.medium", result.remediated_code)
        self.assertIn("-          instance_class = \"db.t3.medium\"", result.unified_diff)
        self.assertIn("+          instance_class = \"db.r6g.large\"", result.unified_diff)
        self.assertGreater(len(result.applied_rules), 0)

        # Ingest remediated code to confirm it parses and satisfies invariants
        state = TerraformIngester.parse_hcl_text(result.remediated_code)
        rds = state.entities["rds_postgres"]
        self.assertEqual(rds.metrics["max_connections"], 1365.0)

    def test_safe_hcl_patch_no_op(self):
        safe_hcl = """
        resource "aws_autoscaling_group" "web_asg" {
          name     = "prod-web"
          min_size = 2
          max_size = 4
        }
        resource "aws_db_instance" "postgres" {
          name           = "prod-db"
          instance_class = "db.r6g.large"
        }
        """
        result = AutonomousAutoRemediator.audit_and_generate_patch(safe_hcl)
        self.assertFalse(result.is_vulnerable)
        self.assertEqual(result.violations_detected, 0)
        self.assertEqual(result.unified_diff, "")

    def test_python_client_sdk_local_execution(self):
        client = OmniSimClient(api_key="local")

        # Health
        health = client.health()
        self.assertEqual(health["status"], "HEALTHY")

        # Simulation
        sim_res = client.simulate(domain="systems", horizon=6, traffic_scale=1.2)
        self.assertIn("simulation_id", sim_res)
        self.assertEqual(sim_res["domain"], "systems")

        # Auto Remediate
        patch_res = client.auto_remediate(self.vulnerable_hcl)
        self.assertTrue(patch_res.is_vulnerable)
        self.assertIn("db.r6g.large", patch_res.remediated_code)

        # Pull Request Audit
        pr_audit = client.audit_pull_request(
            repo="acme/infra",
            pr_number=99,
            diff_hcl=self.vulnerable_hcl,
        )
        self.assertEqual(pr_audit["verdict"], "BLOCKED")
        self.assertIn("db.r6g.large", pr_audit["recommended_fix"])


if __name__ == "__main__":
    unittest.main()