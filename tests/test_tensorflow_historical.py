"""Automated Test Suite for TensorFlow Blind Historical Validation."""

import unittest
from benchmarks.tensorflow_historical import TensorFlowHistoricalValidator


class TestTensorFlowHistoricalValidation(unittest.TestCase):
    """Verifies OmniSim's blind foresight against TensorFlow canonical runtime incidents."""

    def test_tensorflow_suite(self):
        report = TensorFlowHistoricalValidator.run_all()

        self.assertEqual(report.incidents_tested, 2)
        self.assertEqual(report.incidents_caught, 2)
        self.assertEqual(report.exact_mitigations_matched, 2)
        self.assertLess(report.total_runtime_ms, 50.0)

        for res in report.results:
            self.assertTrue(res.vulnerability_caught)
            self.assertTrue(res.matches_official_fix)
            self.assertEqual(res.mitigated_violations_count, 0)


if __name__ == "__main__":
    unittest.main()
