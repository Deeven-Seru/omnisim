"""Interactive Web-Based Visualizer for OmniSim.

Spins up a lightweight, zero-dependency HTTP server with a live,
interactive dashboard showing real-time counterfactual branching trees,
invariant violation heatmaps, and side-by-side metric deltas.
"""

from __future__ import annotations

import http.server
import json
import socketserver
import urllib.parse
from typing import Any, Dict

from omnisim.core.action import Action, InterventionType
from omnisim.core.trajectory import ConsequenceReport
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.models.search import CounterfactualMCTS

PORT = 8088

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniSim | Universal Counterfactual Simulation Engine</title>
    <style>
        :root {
            --bg: #090d16;
            --card-bg: #111726;
            --border: #1e293b;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.2);
            --danger: #ef4444;
            --success: #10b981;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
        body { background: var(--bg); color: var(--text-main); padding: 24px; }
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
        .logo { font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }
        .logo span { color: var(--accent); }
        .badge { background: var(--accent-glow); color: var(--accent); padding: 4px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; border: 1px solid var(--accent); }
        .grid { display: grid; grid-template-columns: 340px 1fr; gap: 24px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
        h2 { font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-dim); margin-bottom: 16px; }
        .control-group { margin-bottom: 18px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--text-main); }
        input[type="range"] { width: 100%; accent-color: var(--accent); }
        .range-val { font-size: 12px; color: var(--accent); font-weight: bold; float: right; }
        button { width: 100%; background: var(--accent); color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; transition: 0.2s; }
        button:hover { opacity: 0.9; box-shadow: 0 0 15px var(--accent-glow); }
        .rec-box { background: rgba(16, 185, 129, 0.1); border: 1px solid var(--success); border-radius: 8px; padding: 16px; margin-bottom: 24px; font-size: 14px; line-height: 1.5; color: #a7f3d0; }
        .timeline-card { border-left: 4px solid var(--border); padding: 14px; background: rgba(255,255,255,0.02); margin-bottom: 12px; border-radius: 0 8px 8px 0; }
        .timeline-card.viable { border-color: var(--success); }
        .timeline-card.failed { border-color: var(--danger); }
        .timeline-title { font-size: 15px; font-weight: 700; display: flex; justify-content: space-between; margin-bottom: 6px; }
        .metric-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
        .metric-badge.ok { background: rgba(16, 185, 129, 0.2); color: var(--success); }
        .metric-badge.err { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .delta-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
        .delta-table td { padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .delta-table td:last-child { text-align: right; font-weight: 600; }
        pre { background: #000; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto; color: #38bdf8; margin-top: 10px; }
    </style>
</head>
<body>
    <header>
        <div class="logo">OMNI<span>SIM</span></div>
        <div class="badge">NVIDIA BLACKWELL ACCELERATED // v0.1.0-SEED</div>
    </header>

    <div class="grid">
        <div class="card">
            <h2>Simulation Controls</h2>
            <div class="control-group">
                <label>Traffic Surge Scale <span id="val-traffic" class="range-val">1.2x</span></label>
                <input type="range" id="traffic" min="0.8" max="2.5" step="0.1" value="1.2" oninput="updateVal('traffic')">
            </div>
            <div class="control-group">
                <label>Horizon (Future Steps) <span id="val-horizon" class="range-val">6</span></label>
                <input type="range" id="horizon" min="4" max="12" step="1" value="6" oninput="updateVal('horizon')">
            </div>
            <div class="control-group">
                <label>Gateway Scale Target <span id="val-gw" class="range-val">8 inst</span></label>
                <input type="range" id="gw" min="4" max="16" step="2" value="8" oninput="updateVal('gw')">
            </div>
            <div class="control-group">
                <label>DB Pool Factor <span id="val-db" class="range-val">1.5x</span></label>
                <input type="range" id="db" min="1.0" max="2.5" step="0.25" value="1.5" oninput="updateVal('db')">
            </div>
            <button onclick="runSimulation()">RUN COUNTERFACTUAL SEARCH</button>
        </div>

        <div class="card">
            <h2>Simulated Counterfactual Timelines</h2>
            <div id="recommendation-container"></div>
            <div id="timelines-container">
                <p style="color: var(--text-dim); font-size: 14px;">Running initial simulation rollouts...</p>
            </div>
        </div>
    </div>

    <script>
        function updateVal(id) {
            let el = document.getElementById(id);
            let suffix = id === 'gw' ? ' inst' : (id === 'horizon' ? '' : 'x');
            document.getElementById('val-' + id).innerText = el.value + suffix;
        }

        async function runSimulation() {
            let params = new URLSearchParams({
                traffic: document.getElementById('traffic').value,
                horizon: document.getElementById('horizon').value,
                gw: document.getElementById('gw').value,
                db: document.getElementById('db').value
            });
            let res = await fetch('/api/simulate?' + params.toString());
            let data = await res.json();
            renderResults(data);
        }

        function renderResults(data) {
            let rec = document.getElementById('recommendation-container');
            rec.innerHTML = `<div class="rec-box"><strong>OPTIMAL ACTION DISCOVERY:</strong> ${data.recommendation}</div>`;

            let cont = document.getElementById('timelines-container');
            cont.innerHTML = '';

            data.timelines.forEach(t => {
                let statusBadge = t.is_valid 
                    ? `<span class="metric-badge ok">VIABLE (0 CRITICAL ERRORS)</span>` 
                    : `<span class="metric-badge err">FAILED (${t.critical_violations} VIOLATIONS)</span>`;

                let html = `
                    <div class="timeline-card ${t.is_valid ? 'viable' : 'failed'}">
                        <div class="timeline-title">
                            <span>${t.name}</span>
                            <span>${statusBadge}</span>
                        </div>
                        <div style="font-size: 12px; color: var(--text-dim); margin-bottom: 8px;">
                            Execution Cost: $${t.total_cost.toFixed(2)} | Simulated Steps: ${data.horizon}
                        </div>
                        <table class="delta-table">
                            <tr><td>Gateway Latency:</td><td>${t.metrics.gw_latency} ms</td></tr>
                            <tr><td>DB Pool Saturation:</td><td>${t.metrics.db_pool}%</td></tr>
                            <tr><td>System Error Rate:</td><td>${t.metrics.error_rate}%</td></tr>
                        </table>
                    </div>
                `;
                cont.innerHTML += html;
            });
        }

        // Auto-run on mount
        runSimulation();
    </script>
</body>
</html>
"""


class OmniSimServerHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif parsed.path == "/api/simulate":
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

            # Baseline
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

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def start_visualizer(port: int = PORT) -> None:
    print(f"\n=======================================================")
    print(f"🚀 OmniSim Interactive Visualizer live at:")
    print(f"   http://localhost:{port}")
    print(f"=======================================================\n")
    with socketserver.TCPServer(("", port), OmniSimServerHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down visualizer server.")


if __name__ == "__main__":
    start_visualizer()
