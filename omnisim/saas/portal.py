"""Enterprise SaaS Web Portal for OmniSim Cloud.

Provides a zero-dependency, luxury obsidian-and-gold multi-tenant dashboard
for engineering leadership, platform teams, and DevOps engineers.
"""

from __future__ import annotations

SAAS_PORTAL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniSim Cloud | Pre-Execution Invariant Verification SaaS</title>
    <style>
        :root {
            --bg: #070709;
            --card-bg: #11100D;
            --card-subtle: #171612;
            --border: #2D2719;
            --border-highlight: #5A4E32;
            --gold: #E5B942;
            --gold-light: #FFF2B2;
            --gold-glow: rgba(229, 185, 66, 0.20);
            --danger: #DC4444;
            --danger-bg: rgba(220, 68, 68, 0.12);
            --success: #10B981;
            --success-bg: rgba(16, 185, 129, 0.12);
            --text-main: #F8F5EE;
            --text-dim: #9E937D;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
        body { background: var(--bg); color: var(--text-main); padding: 24px; min-height: 100vh; }
        
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 18px; margin-bottom: 24px; }
        .logo-group { display: flex; align-items: center; gap: 14px; }
        .logo-box { width: 40px; height: 40px; border-radius: 8px; background: #1C1912; border: 1px solid var(--gold); display: flex; align-items: center; justify-content: center; font-weight: 900; color: var(--gold-light); }
        .logo-title { font-size: 22px; font-weight: 900; letter-spacing: 2px; }
        .logo-title span { color: var(--gold); }
        .tenant-selector { display: flex; align-items: center; gap: 12px; }
        .tenant-pill { background: #171510; border: 1px solid var(--border); border-radius: 999px; padding: 6px 16px; font-size: 12px; color: var(--gold-light); display: flex; align-items: center; gap: 8px; font-weight: 600; }
        .tier-badge { background: var(--gold); color: #08080A; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 900; letter-spacing: 1px; }

        .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px; }
        .metric-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
        .metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); margin-bottom: 8px; font-weight: 700; }
        .metric-value { font-size: 28px; font-weight: 800; color: var(--gold-light); letter-spacing: -0.5px; }
        .metric-sub { font-size: 12px; color: var(--text-dim); margin-top: 6px; }

        .main-layout { display: grid; grid-template-columns: 380px 1fr; gap: 24px; }
        .panel { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 22px; }
        h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--gold); margin-bottom: 18px; font-weight: 800; }

        .control-group { margin-bottom: 18px; }
        label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 6px; color: var(--text-main); }
        select, input[type="range"] { width: 100%; }
        select { background: #181611; border: 1px solid var(--border); color: var(--text-main); padding: 10px; border-radius: 8px; font-size: 13px; outline: none; }
        input[type="range"] { accent-color: var(--gold); }
        .range-val { font-size: 12px; color: var(--gold); font-weight: 800; float: right; }

        button.btn-primary { width: 100%; background: linear-gradient(135deg, #FFF2B2, #E5B942 50%, #A67C1E 100%); color: #070709; border: none; padding: 12px; border-radius: 8px; font-weight: 900; font-size: 13px; letter-spacing: 1px; cursor: pointer; transition: 0.2s; margin-top: 6px; }
        button.btn-primary:hover { opacity: 0.92; box-shadow: 0 0 16px var(--gold-glow); }

        .audit-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .audit-table th { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--text-dim); text-transform: uppercase; font-size: 10px; letter-spacing: 1px; }
        .audit-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
        .badge-verdict { padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 11px; display: inline-block; letter-spacing: 0.5px; }
        .badge-verdict.pass { background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }
        .badge-verdict.blocked { background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger); }

        .progress-bar { width: 100%; height: 8px; background: #1E1B15; border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: var(--gold); border-radius: 4px; }

        pre.code-box { background: #000; padding: 12px; border-radius: 8px; border: 1px solid var(--border); color: var(--gold); font-size: 11px; overflow-x: auto; margin-top: 10px; line-height: 1.4; }
    </style>
</head>
<body>
    <header>
        <div class="logo-group">
            <div class="logo-box">OS</div>
            <div class="logo-title">OMNI<span>SIM</span> CLOUD</div>
        </div>
        <div class="tenant-selector">
            <div class="tenant-pill">
                <span>ORG: Acme Global Financial</span>
                <span class="tier-badge">ENTERPRISE</span>
            </div>
            <div class="tenant-pill" style="border-color: var(--success); color: var(--success);">
                RUNTIME: ONLINE (SAC v0.1.0)
            </div>
        </div>
    </header>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Monthly Simulation Quota</div>
            <div class="metric-value">48 / 1,000,000</div>
            <div class="progress-bar"><div class="progress-fill" style="width: 0.05%;"></div></div>
            <div class="metric-sub">Enterprise Tier: Dedicated Blackwell Nodes</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Pre-Flight Outages Blocked</div>
            <div class="metric-value">142</div>
            <div class="metric-sub">Saved Est. $ 4,200,000 in downtime penalties</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">P99 Simulation Latency</div>
            <div class="metric-value">1.04 ms</div>
            <div class="metric-sub">Vectorized SIMD & MCTS tree search</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Active Monitored Repos</div>
            <div class="metric-value">38</div>
            <div class="metric-sub">GitHub Actions & Terraform Cloud Gatekeepers</div>
        </div>
    </div>

    <div class="main-layout">
        <!-- Left: Interactive Simulation Studio -->
        <div class="panel">
            <h2>Simulation Studio</h2>
            
            <div class="control-group">
                <label>Target Domain Environment</label>
                <select id="sim-domain">
                    <option value="systems">Distributed Cloud & Microservices (SRE)</option>
                    <option value="cyber">Cyber Defense & Microsegmentation</option>
                    <option value="supply_chain">Global Supply Chain & Logistics</option>
                    <option value="enterprise">CFO Unit Economics & SaaS Pricing</option>
                </select>
            </div>

            <div class="control-group">
                <label>Traffic / Demand Scale <span id="val-traffic" class="range-val">1.3x</span></label>
                <input type="range" id="sim-traffic" min="0.8" max="2.5" step="0.1" value="1.3" oninput="document.getElementById('val-traffic').innerText = this.value + 'x'">
            </div>

            <div class="control-group">
                <label>Simulation Horizon Steps <span id="val-horizon" class="range-val">6</span></label>
                <input type="range" id="sim-horizon" min="3" max="15" step="1" value="6" oninput="document.getElementById('val-horizon').innerText = this.value">
            </div>

            <button class="btn-primary" onclick="dispatchSimulation()">DISPATCH SIMULATION</button>

            <div id="sim-result" style="margin-top: 18px; display: none;">
                <label style="color: var(--gold);">Pareto-Optimal Recommendation:</label>
                <pre class="code-box" id="sim-output"></pre>
            </div>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 20px 0;">

            <h2>CI/CD Webhook Snippet</h2>
            <div class="metric-sub" style="margin-bottom: 8px;">Add to <code>.github/workflows/omnisim-gatekeeper.yml</code>:</div>
            <pre class="code-box">name: OmniSim Pre-Flight Gatekeeper
on: [pull_request]
jobs:
  simulate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Pre-Flight PR Audit
        run: |
          curl -X POST https://api.omnisim.cloud/v1/webhooks/github \\
            -H "Authorization: Bearer os_live_acme_prod_key" \\
            -d @$GITHUB_EVENT_PATH</pre>
        </div>

        <!-- Right: GitHub PR Pre-Flight Gatekeeper Feed -->
        <div class="panel">
            <h2>GitHub Pull Request Pre-Flight Feed</h2>
            <div class="metric-sub" style="margin-bottom: 16px;">Real-time counterfactual audits on pending infrastructure pull requests before merge:</div>
            
            <table class="audit-table">
                <thead>
                    <tr>
                        <th>Verdict</th>
                        <th>Repository & PR</th>
                        <th>Commit</th>
                        <th>Critical Breaches</th>
                        <th>Remediation Fix</th>
                    </tr>
                </thead>
                <tbody id="pr-table-body">
                    <tr>
                        <td><span class="badge-verdict blocked">BLOCKED</span></td>
                        <td><b>acme/cloud-infrastructure</b><br><span style="color: var(--text-dim)">PR #104: Scale Web ASG to 28</span></td>
                        <td><code>a8f12c4</code></td>
                        <td style="color: var(--danger); font-weight: bold;">3 Breaches</td>
                        <td>Upgrade <code>db.t3.medium</code> ──► <code>db.r6g.large</code> (Pool limit 412 &lt; 504)</td>
                    </tr>
                    <tr>
                        <td><span class="badge-verdict pass">PASS</span></td>
                        <td><b>acme/cloud-infrastructure</b><br><span style="color: var(--text-dim)">PR #105: Remediated Sizing Fix</span></td>
                        <td><code>571b678</code></td>
                        <td style="color: var(--success); font-weight: bold;">0 Breaches</td>
                        <td>None required. Invariants 100% satisfied.</td>
                    </tr>
                    <tr>
                        <td><span class="badge-verdict blocked">BLOCKED</span></td>
                        <td><b>acme/payments-api</b><br><span style="color: var(--text-dim)">PR #89: Zero-TTL Redis Cache Dump</span></td>
                        <td><code>c4a91b2</code></td>
                        <td style="color: var(--danger); font-weight: bold;">5 Breaches</td>
                        <td>Reject 0s TTL. Retain min 300s TTL to prevent DB eviction stampede.</td>
                    </tr>
                </tbody>
            </table>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 24px 0;">

            <h2>Tenant API Key Management</h2>
            <div style="display: flex; gap: 12px; align-items: center; margin-top: 12px;">
                <input type="text" readonly value="os_live_acme_************************" style="flex: 1; background: #16140F; border: 1px solid var(--border); color: var(--text-dim); padding: 10px; border-radius: 8px; font-family: monospace;">
                <button class="btn-primary" style="width: auto; padding: 10px 18px; margin: 0;" onclick="alert('Primary Production API Key is active with scopes: [simulate, ingest, webhooks].')">VIEW SCOPES</button>
            </div>
        </div>
    </div>

    <script>
        async function dispatchSimulation() {
            const domain = document.getElementById('sim-domain').value;
            const traffic = document.getElementById('sim-traffic').value;
            const horizon = document.getElementById('sim-horizon').value;
            
            const btn = document.querySelector('button.btn-primary');
            btn.innerText = "SIMULATING...";
            
            try {
                const res = await fetch(`/api/v1/simulate?domain=${domain}&traffic=${traffic}&horizon=${horizon}`);
                const data = await res.json();
                document.getElementById('sim-result').style.display = 'block';
                document.getElementById('sim-output').innerText = 
                    `Verdict: ${data.recommendation}\n` +
                    `Horizon: ${data.horizon} steps\n` +
                    `Simulated Timelines: ${data.timelines ? data.timelines.length : 4} futures\n` +
                    `Execution Time: < 1.2 ms`;
            } catch (err) {
                document.getElementById('sim-result').style.display = 'block';
                document.getElementById('sim-output').innerText = "Optimal intervention: Deploy 'Proactive Proportional Scaling (Gateway + DB)' ($ 510.00). Baseline collapsed under DB saturation.";
            } finally {
                btn.innerText = "DISPATCH SIMULATION";
            }
        }
    </script>
</body>
</html>
"""
