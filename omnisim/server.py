"""Enterprise REST & Headless Agent Gateway for OmniSim.

Exposes OmniSim's counterfactual simulation engine via REST APIs
for CI/CD pipelines, Kubernetes controllers, and enterprise monitoring stacks.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import urllib.parse
from typing import Any, Dict, List

from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.domains.cyber import build_cyber_resilience_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.supply_chain import build_supply_chain_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.engine.batched_simulator import BatchedSimulator
from omnisim.ingest.k8s import KubernetesManifestIngester
from omnisim.models.search import CounterfactualMCTS
from omnisim.visualizer import HTML_TEMPLATE

DEFAULT_PORT = 8088


class OmniSimAPIServer(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path in ["/", "/index.html", "/dashboard"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/health":
            self._send_json({"status": "HEALTHY", "version": "0.1.0", "engine": "OmniSim SAC World Model"})

        elif parsed.path == "/api/v1/domains":
            domains = [
                {"id": "systems", "name": "Distributed Cloud & Microservices", "status": "AVAILABLE"},
                {"id": "enterprise", "name": "Enterprise Economics & SaaS Pricing", "status": "AVAILABLE"},
                {"id": "supply_chain", "name": "Global Supply Chain & Logistics", "status": "AVAILABLE"},
                {"id": "cyber", "name": "Cyber-Resilience & Attack Blast Radius", "status": "AVAILABLE"},
            ]
            self._send_json({"domains": domains})

        elif parsed.path == "/api/v1/simulate":
            # Delegate to query-parameter simulation for quick web UI queries
            query = urllib.parse.parse_qs(parsed.query)
            traffic = float(query.get("traffic", [1.2])[0])
            horizon = int(query.get("horizon", [6])[0])
            gw_inst = float(query.get("gw", [8.0])[0])
            db_factor = float(query.get("db", [1.5])[0])

            state, dynamics = build_cloud_systems_scenario(traffic_scale=traffic)

            action_gw = Action(
                name=f"Autoscale Gateway ({int(gw_inst)} instances)",
                intervention_type=InterventionType.PARAM_TUNE,
                target_entity="api_gateway",
                parameters={"active_instances": gw_inst},
                cost=250.0,
            )

            action_db = Action(
                name=f"Scale DB Pool ({db_factor:.2f}x)",
                intervention_type=InterventionType.SCALE,
                target_entity="database_cluster",
                parameters={"metric": "capacity", "factor": db_factor},
                cost=120.0,
            )

            planner = CounterfactualMCTS(dynamics, [action_gw, action_db], horizon=horizon)
            b_traj = planner.simulate_trajectory(state, [Action.no_op()] * horizon, name="Status Quo (No Action)")
            t_gw = planner.simulate_trajectory(state, [action_gw] + [Action.no_op()] * (horizon - 1), name=action_gw.name)
            t_db = planner.simulate_trajectory(state, [action_db] + [Action.no_op()] * (horizon - 1), name=action_db.name)
            t_both = planner.simulate_trajectory(state, [action_gw, action_db] + [Action.no_op()] * (horizon - 2), name="Dual Scaling (Gateway + DB)")
            t_both.total_cost = action_gw.cost + action_db.cost

            candidates = [b_traj, t_gw, t_db, t_both]
            best = next((t for t in candidates[1:] if t.is_valid), None)
            rec = f"Deploy '{best.name}' ($ {best.total_cost:.2f}). Baseline and partial actions collapse from downstream resource starvation." if best else "All interventions breached SLA thresholds."

            response_data = {
                "horizon": horizon,
                "recommendation": rec,
                "timelines": []
            }

            for t in candidates:
                fs = t.final_state
                gw_lat = fs.get_metric("api_gateway", "latency_ms", 0.0) if fs else 0.0
                db_pool = (fs.get_metric("database_cluster", "connection_pool_usage", 0.0) * 100) if fs else 0.0
                err_rate = (fs.get_metric("api_gateway", "error_rate", 0.0) * 100) if fs else 0.0

                response_data["timelines"].append({
                    "name": t.name,
                    "is_valid": t.is_valid,
                    "critical_violations": len([v for v in t.all_violations if v[1].severity == "CRITICAL"]),
                    "total_cost": t.total_cost,
                    "metrics": {
                        "gw_latency": f"{gw_lat:.1f}",
                        "db_pool": f"{db_pool:.1f}",
                        "error_rate": f"{err_rate:.2f}"
                    }
                })

            self._send_json(response_data)

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self.send_response(400)
            self._send_json({"error": f"Invalid JSON payload: {str(e)}"})
            return

        if parsed.path == "/api/v1/ingest/k8s":
            manifests = payload.get("manifests", [])
            state = KubernetesManifestIngester.parse_manifests(manifests)
            self._send_json({
                "status": "SUCCESS",
                "entities_parsed": len(state.entities),
                "invariants_established": len(state.invariants),
                "relations_wired": len(state.relations),
                "entity_ids": list(state.entities.keys()),
            })

        elif parsed.path == "/api/v1/simulate/batch":
            # High-throughput batch Monte Carlo simulation endpoint
            domain = payload.get("domain", "systems")
            num_rollouts = int(payload.get("num_rollouts", 100))
            horizon = int(payload.get("horizon", 6))

            if domain == "systems":
                state, dynamics = build_cloud_systems_scenario(traffic_scale=1.2)
            elif domain == "supply_chain":
                state, dynamics = build_supply_chain_scenario()
            elif domain == "cyber":
                state, dynamics = build_cyber_resilience_scenario()
            else:
                state, dynamics = build_enterprise_strategy_scenario()

            action_data = payload.get("action", {})
            action = Action(
                name=action_data.get("name", "Test Intervention"),
                intervention_type=InterventionType(action_data.get("type", "NO_OP")),
                target_entity=action_data.get("target_entity", "system"),
                parameters=action_data.get("parameters", {}),
                cost=float(action_data.get("cost", 0.0)),
            )

            sim = BatchedSimulator(dynamics, horizon=horizon)
            result = sim.run_batched(state, action, num_rollouts=num_rollouts)

            self._send_json({
                "action_name": result.action_name,
                "num_rollouts": result.num_rollouts,
                "violation_probability": round(result.violation_probability, 4),
                "confidence_interval_95": [round(result.confidence_interval_95[0], 4), round(result.confidence_interval_95[1], 4)],
                "mean_cost": result.mean_cost,
                "failure_distribution_by_step": result.all_violations_by_step,
            })

        else:
            self.send_response(404)
            self.end_headers()

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))


def run_api_server(port: int = DEFAULT_PORT) -> None:
    print(f"[ONLINE] OmniSim Enterprise API Gateway online at http://localhost:{port}")
    with socketserver.TCPServer(("", port), OmniSimAPIServer) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down OmniSim API Server.")


if __name__ == "__main__":
    run_api_server()
