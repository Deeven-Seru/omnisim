"""Automated Test Suite for OmniSim Blind Audit of Current TensorFlow State."""

import unittest
from benchmarks.tensorflow_audit import TensorFlowCurrentStateAuditor


class TestTensorFlowCurrentStateAudit(unittest.TestCase):
    """Verifies that OmniSim catches current active failure modes in TensorFlow and confirms user matches."""

    def test_current_audit_findings(self):
        report = TensorFlowCurrentStateAuditor.run_current_audit()

        self.assertEqual(report.subsystems_evaluated, 2)
        self.assertEqual(report.critical_breaches_predicted, 2)
        self.assertLess(report.audit_runtime_ms, 50.0)

        for f in report.findings:
            self.assertTrue(f.reported_by_real_users)
            self.assertGreater(len(f.matching_github_issues), 0)
            self.assertLessEqual(f.breach_step, 4)
            self.assertLessEqual(f.mitigated_value, f.threshold_limit)


if __name__ == "__main__":
    unittest.main()
