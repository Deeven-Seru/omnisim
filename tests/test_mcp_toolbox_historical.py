"""Automated Regression Test for Google MCP Toolbox Blind Historical Validation."""

import unittest
from benchmarks.mcp_toolbox_historical_validation import GoogleMCPToolboxHistoricalValidator


class TestGoogleMCPToolboxHistoricalValidation(unittest.TestCase):
    """Verifies OmniSim's blind foresight against Google's real-world MCP Toolbox incident."""

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


if __name__ == "__main__":
    unittest.main()
