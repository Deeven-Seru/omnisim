"""Automated Unit & Integration Test for Adversarial Robustness Benchmark Suite."""

import unittest
from benchmarks.robustness import RobustnessBenchmarkSuite, RuthlessVCGauntlet


class TestRobustnessBenchmark(unittest.TestCase):
    """Test suite validating OmniSim against adversarial robustness and invariant boundaries."""

    @classmethod
    def setUpClass(cls):
        cls.gauntlet = RobustnessBenchmarkSuite()
        cls.report = cls.gauntlet.run_all()

    def test_tier_1_blind_replay_recall_and_precision(self):
        # Recall must be >= 90%
        self.assertGreaterEqual(
            self.report.test_1_recall,
            0.90,
            f"Recall was {self.report.test_1_recall*100:.1f}%, expected >= 90%",
        )
        # False alarm rate on benign deployments must be <= 3%
        self.assertLessEqual(
            self.report.test_1_false_alarm_rate,
            0.03,
            f"False alarm rate was {self.report.test_1_false_alarm_rate*100:.1f}%, expected <= 3%",
        )

    def test_tier_2_epistemic_uncertainty_handling(self):
        # Must detect dark debt / unmonitored dependencies
        self.assertTrue(self.report.test_2_unmonitored_flagged)
        # Confidence score must decay under unmonitored tail risk (< 70%)
        self.assertLess(self.report.test_2_confidence_score, 0.70)

    def test_tier_3_adversarial_sre_trap_rejection(self):
        # 100% of adversarial poison traps must be ruthlessly rejected
        self.assertEqual(
            self.report.test_3_traps_rejected,
            self.report.test_3_traps_evaluated,
            "Engine failed to reject one or more poison action traps",
        )

    def test_tier_4_zero_consulting_automated_ingestion(self):
        self.assertTrue(self.report.test_4_zero_consulting_pass)
        self.assertLess(self.report.test_4_ingestion_time_ms, 50.0)

    def test_tier_5_asymmetry_of_being_wrong(self):
        self.assertTrue(self.report.test_5_risk_penalty_enforced)
        self.assertIn("Deterministic", self.report.test_5_selected_plan)

    def test_overall_diligence_verdict(self):
        self.assertTrue(self.report.all_passed, "Overall VC Diligence Gauntlet did not pass 100%")


if __name__ == "__main__":
    unittest.main()