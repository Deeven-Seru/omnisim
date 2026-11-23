"""Automated Regression Test for Google MCP Toolbox Multi-Release Historical Validation."""

import unittest
from benchmarks.mcp_toolbox_historical_validation import (
    GoogleMCPToolboxHistoricalValidator,
    MultiReleaseMCPToolboxValidator,
)


class TestGoogleMCPToolboxHistoricalValidation(unittest.TestCase):
    """Verifies OmniSim's blind foresight against Google's real-world MCP Toolbox incidents across releases."""

    def test_blind_foresight_on_unpatched_mcp_toolbox(self):
        report = GoogleMCPToolboxHistoricalValidator.run_validation()

        # 1. Must catch the vulnerability in the prior unpatched version
        self.assertTrue(report.vulnerability_detected)
        self.assertEqual(report.breached_metric, "open_file_descriptors")
        self.assertLessEqual(report.step_of_first_breach, 4)
        self.assertGreater(report.peak_file_descriptors_status_quo, 1000.0)

        # 2. Must synthesize the exact mitigation matching Google's future fix
        self.assertTrue(report.remediation_is_exact_match_to_future_fix)
        self.assertEqual(
            report.remediation_action_chosen,
            "Release Handle on Connect Failure (pool.Close / db.Close)"
        )
        self.assertEqual(report.mitigated_violations_count, 0)
        self.assertLess(report.execution_time_ms, 50.0)

    def test_multi_release_historical_suite(self):
        suite_report = MultiReleaseMCPToolboxValidator.run_all()

        self.assertEqual(suite_report.incidents_tested, 4)
        self.assertEqual(suite_report.incidents_caught, 4)
        self.assertEqual(suite_report.exact_mitigations_matched, 4)
        self.assertLess(suite_report.total_runtime_ms, 100.0)

        for res in suite_report.results:
            self.assertTrue(res.vulnerability_caught)
            self.assertTrue(res.matches_future_google_fix)
            self.assertEqual(res.mitigated_violations_count, 0)


if __name__ == "__main__":
    unittest.main()
