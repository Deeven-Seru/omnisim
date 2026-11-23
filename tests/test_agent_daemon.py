"""Unit test for the OmniSim Real-Time Sync Daemon."""

import unittest
from omnisim.agent.daemon import AgentConfig, OmniSimAgentDaemon
from omnisim.domains.systems import build_cloud_systems_scenario


class TestOmniSimAgentDaemon(unittest.TestCase):

    def test_daemon_sync_and_spike_detection(self):
        state, _ = build_cloud_systems_scenario()
        config = AgentConfig(
            poll_interval_seconds=0.01,
            enable_simulation_on_spike=True,
            spike_threshold_pct=0.20
        )
        daemon = OmniSimAgentDaemon(state, config)

        # Run 2 test cycles
        daemon.start(max_cycles=2)
        self.assertFalse(daemon.is_running)

        # Simulate a traffic spike
        state.entities["api_gateway"].metrics["load"] = 2500.0
        daemon.start(max_cycles=1)
        self.assertEqual(state.entities["api_gateway"].metrics["load"], 2500.0)


if __name__ == "__main__":
    unittest.main()
