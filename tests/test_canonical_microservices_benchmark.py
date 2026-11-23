"""Automated Test Suite for Canonical Microservice Reference Benchmarks."""

import unittest
from benchmarks.canonical_microservices_benchmark import CanonicalMicroservicesBenchmarkSuite


class TestCanonicalMicroservicesBenchmark(unittest.TestCase):
    """Verifies OmniSim on Google Online Boutique, DeathStarBench, Train-Ticket, and GAIA."""

    @classmethod
    def setUpClass(cls):
        cls.suite = CanonicalMicroservicesBenchmarkSuite()
        cls.report = cls.suite.run_all()

    def test_all_benchmarks_passed(self):
        self.assertTrue(self.report.all_passed)
        self.assertEqual(self.report.benchmarks_passed, 4)

    def test_total_microservices_modeled(self):
        self.assertEqual(self.report.total_microservices_simulated, 29)

    def test_cascading_violations_caught(self):
        self.assertGreaterEqual(self.report.total_sla_violations_caught, 10)

    def test_individual_benchmarks(self):
        for r in self.report.results:
            self.assertTrue(r.passed, f"Benchmark {r.benchmark_name} failed")
            self.assertEqual(r.mitigated_violations, 0, f"Remediated run for {r.benchmark_name} had violations")
            self.assertGreater(r.latency_savings_pct, 60.0, f"Latency savings for {r.benchmark_name} was low: {r.latency_savings_pct}%")


if __name__ == "__main__":
    unittest.main()