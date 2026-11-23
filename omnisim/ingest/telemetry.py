"""OpenTelemetry & Prometheus Metrics Ingestion for OmniSim."""

from __future__ import annotations

from typing import Any, Dict, List
from omnisim.core.state import UniversalState


class TelemetryIngester:
    """Ingests live Prometheus or OpenTelemetry metric vectors into the active world state."""

    @staticmethod
    def apply_metrics(state: UniversalState, metrics_payload: List[Dict[str, Any]]) -> UniversalState:
        """Applies real-time telemetry updates to match live production state."""
        for metric in metrics_payload:
            metric_name = metric.get("metric_name", "")
            entity_id = metric.get("entity_id", "")
            value = float(metric.get("value", 0.0))

            if entity_id in state.entities:
                state.entities[entity_id].metrics[metric_name] = value

        return state
