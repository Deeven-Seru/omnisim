"""Automated Test Suite for OmniSim Discovery of Unreported Latent Defects in TensorFlow."""

import unittest
from benchmarks.tensorflow_unreported_latent_audit import TensorFlowLatentVulnerabilityAuditor


class TestTensorFlowLatentAudit(unittest.TestCase):
    """Verifies that OmniSim catches unreported dark debt and latent failure modes."""

    def test_latent_audit_findings(self):
        report = TensorFlowLatentVulnerabilityAuditor.run_latent_audit()

        self.assertEqual(report.vulnerabilities_uncovered, 2)
        self.assertTrue(report.all_zero_day_latent)
        self.assertGreater(report.total_compute_waste_prevented_usd, 0.0)
        self.assertLess(report.audit_latency_ms, 50.0)

        for f in report.findings:
            self.assertFalse(f.is_reported_on_github)
            self.assertEqual(f.status, "UNREPORTED_DARK_DEBT")
            self.assertLessEqual(f.first_breach_step, 3)
            self.assertEqual(f.mitigated_violations_count, 0)


if __name__ == "__main__":
    unittest.main()
