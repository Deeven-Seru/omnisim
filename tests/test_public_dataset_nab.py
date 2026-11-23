"""Automated Test Suite for Public Dataset Benchmark (NAB AWS CloudWatch)."""

import unittest
from benchmarks.public_dataset_nab_benchmark import PublicDatasetNABBenchmark


class TestPublicDatasetNABBenchmark(unittest.TestCase):
    """Verifies OmniSim on real AWS CloudWatch time-series data."""

    @classmethod
    def setUpClass(cls):
        cls.bench = PublicDatasetNABBenchmark()
        cls.report = cls.bench.run_benchmark()

    def test_streaming_ingestion_and_dataset_integrity(self):
        self.assertGreaterEqual(self.report.total_data_points, 8000)
        self.assertEqual(self.report.ec2_points_evaluated, 4032)
        self.assertEqual(self.report.elb_points_evaluated, 4032)
        self.assertGreater(self.report.streaming_throughput_points_per_sec, 50000)

    def test_proactive_failure_detection_and_lead_time(self):
        self.assertTrue(self.report.cpu_spike_detected_early)
        self.assertGreaterEqual(self.report.lead_time_minutes, 10)
        self.assertGreaterEqual(self.report.peak_unmitigated_cpu, 90.0)

    def test_counterfactual_remediation_zero_violations(self):
        self.assertEqual(self.report.mitigated_sla_violations, 0)
        self.assertLess(self.report.mitigated_counterfactual_cpu, 50.0)

    def test_elb_real_world_surge_verification(self):
        self.assertTrue(self.report.elb_surge_detected)

    def test_overall_public_benchmark_pass(self):
        self.assertTrue(self.report.benchmark_passed)


if __name__ == "__main__":
    unittest.main()