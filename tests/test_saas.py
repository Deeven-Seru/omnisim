"""Automated Test Suite for OmniSim Multi-Tenant SaaS Platform."""

import json
import unittest
from omnisim.saas.engine import OmniSimSaaSPlatform
from omnisim.saas.models import APIKey, PlanTier, TIER_LIMITS, Tenant


class TestOmniSimSaaSPlatform(unittest.TestCase):
    """Verifies multi-tenancy, auth, quotas, PR audits, and telemetry streams."""

    def setUp(self):
        self.saas = OmniSimSaaSPlatform()

    def test_tenant_creation_and_api_keys(self):
        tenant, raw_token = self.saas.create_tenant("Vercel Edge Tech", tier="PRO")
        self.assertTrue(tenant.id.startswith("org_"))
        self.assertEqual(tenant.name, "Vercel Edge Tech")
        self.assertEqual(tenant.tier, PlanTier.PRO)
        self.assertTrue(raw_token.startswith("os_live_"))

        # Verify authentication
        auth_tenant = self.saas.authenticate_token(raw_token)
        self.assertIsNotNone(auth_tenant)
        self.assertEqual(auth_tenant.id, tenant.id)

        # Verify invalid token rejected
        bad_tenant = self.saas.authenticate_token("os_live_invalid_fake_token")
        self.assertIsNone(bad_tenant)

    def test_tier_quota_enforcement(self):
        free_tenant, _ = self.saas.create_tenant("Hobby Developer", tier="FREE")
        self.assertEqual(free_tenant.tier, PlanTier.FREE)

        # Free tier limit is 50
        free_tenant.monthly_usage_count = 50
        can_run, reason = free_tenant.can_simulate()
        self.assertFalse(can_run)
        self.assertIn("Monthly quota exceeded", reason)

        # Pro tier limit is 10,000
        pro_tenant, _ = self.saas.create_tenant("Series A Startup", tier="PRO")
        pro_tenant.monthly_usage_count = 50
        can_run_pro, _ = pro_tenant.can_simulate()
        self.assertTrue(can_run_pro)

    def test_counterfactual_simulation_dispatch(self):
        tenant = self.saas.tenants["org_enterprise_acme"]
        initial_usage = tenant.monthly_usage_count

        result = self.saas.execute_simulation(
            tenant=tenant,
            domain="systems",
            horizon=6,
            traffic_scale=1.3,
        )

        self.assertIn("simulation_id", result)
        self.assertEqual(result["domain"], "systems")
        self.assertEqual(result["tenant_id"], tenant.id)
        self.assertIn("recommendation", result)
        self.assertGreater(len(result["timelines"]), 0)
        self.assertEqual(tenant.monthly_usage_count, initial_usage + 1)
        self.assertLess(result["execution_time_ms"], 50.0)

    def test_github_pr_webhook_pre_flight_audit(self):
        tenant = self.saas.tenants["org_enterprise_acme"]

        # 1. Unsafe PR with ASG 28 and db.t3.medium
        unsafe_payload = {
            "repository": {"full_name": "acme/cloud-infrastructure"},
            "pull_request": {"number": 142, "head": {"sha": "c0604f15b4"}},
            "diff_hcl": """
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
        }
        res_unsafe = self.saas.process_github_pr_webhook(tenant, unsafe_payload)
        self.assertEqual(res_unsafe["verdict"], "BLOCKED")
        self.assertGreaterEqual(res_unsafe["critical_breaches"], 1)
        self.assertIn("db.r6g.large", res_unsafe["recommended_fix"])
        self.assertIn("BLOCKED", res_unsafe["github_comment_markdown"])

        # 2. Safe PR with remediated db.r6g.large
        safe_payload = {
            "repository": {"full_name": "acme/cloud-infrastructure"},
            "pull_request": {"number": 143, "head": {"sha": "571b678"}},
            "diff_hcl": """
            resource "aws_autoscaling_group" "web_asg" {
              name     = "prod-web"
              min_size = 4
              max_size = 28
            }
            resource "aws_db_instance" "postgres" {
              name           = "prod-db"
              instance_class = "db.r6g.large"
            }
            """
        }
        res_safe = self.saas.process_github_pr_webhook(tenant, safe_payload)
        self.assertEqual(res_safe["verdict"], "PASS")
        self.assertEqual(res_safe["critical_breaches"], 0)
        self.assertIn("PASS", res_safe["github_comment_markdown"])

    def test_streaming_telemetry_proactive_detection(self):
        tenant = self.saas.tenants["org_enterprise_acme"]

        telemetry_stream = [
            {"metric": "api_gateway.load", "value": 1000.0, "prev_value": 1000.0},
            {"metric": "api_gateway.load", "value": 1450.0, "prev_value": 1000.0},  # +45% spike
        ]

        res = self.saas.ingest_telemetry_stream(tenant, telemetry_stream)
        self.assertEqual(res["points_ingested"], 2)
        self.assertEqual(res["spikes_detected"], 1)
        self.assertEqual(len(res["proactive_counterfactual_simulations"]), 1)
        proactive_sim = res["proactive_counterfactual_simulations"][0]
        self.assertEqual(proactive_sim["delta_pct"], 45.0)
        self.assertIn("Proactive", proactive_sim["optimal_remediation"])


if __name__ == "__main__":
    unittest.main()