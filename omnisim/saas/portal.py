"""Enterprise SaaS Web Portal for OmniSim Cloud.

Provides a zero-dependency, luxury obsidian-and-gold multi-tenant dashboard
for engineering leadership, platform teams, and DevOps engineers.
Connected dynamically to the durable OmniSim persistence and authentication APIs.
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
        
        header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 18px; margin-bottom: 24px; flex-wrap: wrap; gap: 14px; }
        .logo-group { display: flex; align-items: center; gap: 14px; }
        .logo-box { width: 40px; height: 40px; border-radius: 8px; background: #1C1912; border: 1px solid var(--gold); display: flex; align-items: center; justify-content: center; font-weight: 900; color: var(--gold-light); }
        .logo-title { font-size: 22px; font-weight: 900; letter-spacing: 2px; }
        .logo-title span { color: var(--gold); }
        .tenant-selector { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
        .tenant-pill { background: #171510; border: 1px solid var(--border); border-radius: 999px; padding: 6px 16px; font-size: 12px; color: var(--gold-light); display: flex; align-items: center; gap: 8px; font-weight: 600; }
        .tier-badge { background: var(--gold); color: #08080A; padding: 2px 8px; border-radius: 6px; font-size: 10px; font-weight: 900; letter-spacing: 1px; }

        .auth-bar { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 14px 20px; margin-bottom: 24px; display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
        .auth-input-group { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 300px; }
        .auth-input { flex: 1; background: #16140F; border: 1px solid var(--border); color: var(--text-main); padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 12px; }

        .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-bottom: 24px; }
        .metric-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }
        .metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: var(--text-dim); margin-bottom: 8px; font-weight: 700; }
        .metric-value { font-size: 26px; font-weight: 800; color: var(--gold-light); letter-spacing: -0.5px; }
        .metric-sub { font-size: 12px; color: var(--text-dim); margin-top: 6px; }

        .main-layout { display: grid; grid-template-columns: 380px 1fr; gap: 24px; }
        @media (max-width: 900px) { .main-layout { grid-template-columns: 1fr; } }
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
        button.btn-secondary { background: #1C1912; color: var(--gold-light); border: 1px solid var(--border); padding: 8px 14px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; transition: 0.2s; }
        button.btn-secondary:hover { border-color: var(--gold); }

        .audit-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .audit-table th { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--text-dim); text-transform: uppercase; font-size: 10px; letter-spacing: 1px; }
        .audit-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }
        .badge-verdict { padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 11px; display: inline-block; letter-spacing: 0.5px; }
        .badge-verdict.pass { background: var(--success-bg); color: var(--success); border: 1px solid var(--success); }
        .badge-verdict.blocked { background: var(--danger-bg); color: var(--danger); border: 1px solid var(--danger); }

        .progress-bar { width: 100%; height: 8px; background: #1E1B15; border-radius: 4px; overflow: hidden; margin-top: 8px; }
        .progress-fill { height: 100%; background: var(--gold); border-radius: 4px; width: 0%; transition: width 0.3s; }

        pre.code-box { background: #000; padding: 12px; border-radius: 8px; border: 1px solid var(--border); color: var(--gold); font-size: 11px; overflow-x: auto; margin-top: 10px; line-height: 1.4; white-space: pre-wrap; }
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
                <span id="header-tenant-name">ORGANIZATION: CONNECTING...</span>
                <span id="header-tier-badge" class="tier-badge">AUTHENTICATING</span>
            </div>
            <div class="tenant-pill" style="border-color: var(--success); color: var(--success);">
                RUNTIME: ONLINE (v1.0.0)
            </div>
        </div>
    </header>

    <div class="auth-bar">
        <div class="auth-input-group">
            <label style="margin: 0; white-space: nowrap;">API Key:</label>
            <input type="password" id="auth-token-input" class="auth-input" placeholder="Enter Bearer Token (os_live_...)" onchange="saveToken(this.value)">
            <button class="btn-secondary" onclick="saveToken(document.getElementById('auth-token-input').value)">Authenticate</button>
            <button class="btn-secondary" onclick="provisionNewWorkspace()">Create Workspace</button>
        </div>
        <div id="auth-status" style="font-size: 12px; color: var(--text-dim);">Ready</div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-label">Monthly Simulation Quota</div>
            <div class="metric-value" id="metric-quota">- / -</div>
            <div class="progress-bar"><div class="progress-fill" id="metric-quota-bar"></div></div>
            <div class="metric-sub" id="metric-tier-sub">Durable SQLite Storage</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Pre-Flight PR Audits</div>
            <div class="metric-value" id="metric-audits-count">0</div>
            <div class="metric-sub">Recorded Invariant Checks</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Critical Invariant Violations</div>
            <div class="metric-value" id="metric-breaches-count" style="color: var(--danger);">0</div>
            <div class="metric-sub">Catastrophes Blocked Pre-Merge</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Active API Keys</div>
            <div class="metric-value" id="metric-keys-count">0</div>
            <div class="metric-sub">Scoped Tenant Credentials</div>
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
                <label style="color: var(--gold);">Action-Conditioned Verdict:</label>
                <pre class="code-box" id="sim-output"></pre>
            </div>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 20px 0;">

            <h2>CI/CD Webhook Integration</h2>
            <div class="metric-sub" style="margin-bottom: 8px;">Add to <code>.github/workflows/omnisim.yml</code>:</div>
            <pre class="code-box">name: OmniSim PR Pre-Flight
on: [pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Verify Invariants
        uses: Deeven-Seru/omnisim@v1
        with:
          api-key: ${{ secrets.OMNISIM_API_KEY }}</pre>
        </div>

        <!-- Right: Real Pull Request Pre-Flight Feed & Key Management -->
        <div class="panel">
            <h2>GitHub Pull Request Pre-Flight Feed</h2>
            <div class="metric-sub" style="margin-bottom: 16px;">Real-time counterfactual invariant audits recorded for this tenant:</div>
            
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
                        <td colspan="5" style="text-align: center; color: var(--text-dim); padding: 24px;">
                            Loading pull request audit feed...
                        </td>
                    </tr>
                </tbody>
            </table>

            <hr style="border: 0; border-top: 1px solid var(--border); margin: 24px 0;">

            <h2>Active Tenant API Keys</h2>
            <div id="keys-list" style="margin-top: 12px;">
                <div style="color: var(--text-dim); font-size: 12px;">Loading active keys...</div>
            </div>
            
            <div style="margin-top: 14px; display: flex; gap: 10px;">
                <input type="text" id="new-key-name" class="auth-input" placeholder="New Key Name (e.g. Production CI)" style="flex: 1;">
                <button class="btn-secondary" onclick="mintNewKey()">Mint API Key</button>
            </div>
        </div>
    </div>

    <script>
        function getToken() {
            return localStorage.getItem('omnisim_token') || '';
        }

        function saveToken(token) {
            token = token.trim();
            if (token) {
                localStorage.setItem('omnisim_token', token);
                document.getElementById('auth-token-input').value = token;
                document.getElementById('auth-status').innerText = 'Authenticated';
                document.getElementById('auth-status').style.color = 'var(--success)';
            } else {
                localStorage.removeItem('omnisim_token');
                document.getElementById('auth-status').innerText = 'Unauthenticated';
                document.getElementById('auth-status').style.color = 'var(--danger)';
            }
            refreshDashboard();
        }

        async function provisionNewWorkspace() {
            const orgName = prompt('Enter Organization or Workspace Name:', 'Acme Engineering');
            if (!orgName) return;
            try {
                const res = await fetch('/api/v1/tenants', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: orgName })
                });
                const data = await res.json();
                if (res.ok && data.token) {
                    alert('Workspace Created Successfully!\\n\\nAPI Key: ' + data.token + '\\n\\nSave this key securely. It will now be activated in your session.');
                    saveToken(data.token);
                } else {
                    alert('Provisioning failed: ' + (data.detail || data.title || 'Unknown error'));
                }
            } catch (err) {
                alert('Connection error: ' + err.message);
            }
        }

        async function refreshDashboard() {
            const token = getToken();
            const headers = token ? { 'Authorization': 'Bearer ' + token } : {};

            // 1. Fetch Tenant Metadata & Quota
            try {
                const res = await fetch('/api/v1/tenants/me', { headers });
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('header-tenant-name').innerText = 'ORG: ' + data.name.toUpperCase();
                    document.getElementById('header-tier-badge').innerText = data.tier;
                    document.getElementById('metric-quota').innerText = `${data.monthly_usage} / ${data.monthly_quota}`;
                    const pct = Math.min(100, (data.monthly_usage / Math.max(1, data.monthly_quota)) * 100);
                    document.getElementById('metric-quota-bar').style.width = pct + '%';
                    document.getElementById('metric-tier-sub').innerText = `${data.tier} Tier Plan`;
                } else if (res.status === 401) {
                    document.getElementById('header-tenant-name').innerText = 'UNAUTHENTICATED';
                    document.getElementById('header-tier-badge').innerText = 'NO TOKEN';
                    document.getElementById('metric-quota').innerText = 'N/A';
                    document.getElementById('metric-quota-bar').style.width = '0%';
                }
            } catch (err) {
                console.warn('Failed to load tenant info', err);
            }

            // 2. Fetch Real PR Audits
            try {
                const res = await fetch('/api/v1/pr-audits', { headers });
                const tbody = document.getElementById('pr-table-body');
                if (res.ok) {
                    const data = await res.json();
                    const audits = data.audits || [];
                    document.getElementById('metric-audits-count').innerText = audits.length;
                    
                    let criticalCount = 0;
                    audits.forEach(a => { criticalCount += (a.critical_breaches || 0); });
                    document.getElementById('metric-breaches-count').innerText = criticalCount;

                    if (audits.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 24px;">No pull requests audited yet for this tenant. Trigger the OmniSim GitHub Action to record live verification traces.</td></tr>`;
                    } else {
                        tbody.innerHTML = audits.map(a => {
                            const isPass = a.verdict === 'PASS';
                            return `<tr>
                                <td><span class="badge-verdict ${isPass ? 'pass' : 'blocked'}">${a.verdict}</span></td>
                                <td><b>${escapeHtml(a.repo)}</b><br><span style="color: var(--text-dim)">PR #${a.pr_number}</span></td>
                                <td><code>${escapeHtml(a.commit_sha.substring(0, 7))}</code></td>
                                <td style="color: ${a.critical_breaches > 0 ? 'var(--danger)' : 'var(--success)'}; font-weight: bold;">${a.critical_breaches} Breaches</td>
                                <td style="font-size: 11px;">${escapeHtml(a.recommended_fix || 'Invariants fully satisfied.')}</td>
                            </tr>`;
                        }).join('');
                    }
                } else {
                    tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--text-dim); padding: 24px;">Provide an active API key above to view pull request audits.</td></tr>`;
                }
            } catch (err) {
                console.warn('Failed to load PR audits', err);
            }

            // 3. Fetch Real API Keys
            try {
                const res = await fetch('/api/v1/auth/keys', { headers });
                const container = document.getElementById('keys-list');
                if (res.ok) {
                    const data = await res.json();
                    const keys = data.keys || [];
                    document.getElementById('metric-keys-count').innerText = keys.length;
                    if (keys.length === 0) {
                        container.innerHTML = `<div style="color: var(--text-dim); font-size: 12px;">No active API keys found.</div>`;
                    } else {
                        container.innerHTML = keys.map(k => `
                            <div style="display: flex; justify-content: space-between; align-items: center; background: #15130E; border: 1px solid var(--border); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                                <div>
                                    <span style="font-weight: 700; color: var(--gold);">${escapeHtml(k.name)}</span>
                                    <span style="font-family: monospace; color: var(--text-dim); margin-left: 8px;">${escapeHtml(k.prefix)}...</span>
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">Scopes: [${(k.scopes || []).join(', ')}]</div>
                                </div>
                                <button class="btn-secondary" style="color: var(--danger); border-color: rgba(220,68,68,0.3); padding: 4px 10px;" onclick="revokeKey('${k.prefix}')">Revoke</button>
                            </div>
                        `).join('');
                    }
                } else {
                    container.innerHTML = `<div style="color: var(--text-dim); font-size: 12px;">Provide an admin API key to manage credentials.</div>`;
                }
            } catch (err) {
                console.warn('Failed to load keys', err);
            }
        }

        async function mintNewKey() {
            const token = getToken();
            const nameInput = document.getElementById('new-key-name');
            const name = nameInput.value.trim() || 'Production Key';
            try {
                const res = await fetch('/api/v1/auth/keys', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ name: name, scopes: ['admin', 'simulations:write', 'telemetry:write', 'webhooks:write'] })
                });
                const data = await res.json();
                if (res.ok && data.token) {
                    alert('API Key Generated!\\n\\nToken: ' + data.token + '\\n\\nStore this token immediately; it cannot be viewed again.');
                    nameInput.value = '';
                    refreshDashboard();
                } else {
                    alert('Failed to mint key: ' + (data.detail || data.title || 'Unauthorized'));
                }
            } catch (err) {
                alert('Network error: ' + err.message);
            }
        }

        async function revokeKey(prefix) {
            if (!confirm(`Revoke key starting with prefix ${prefix}? This action is immediate and cannot be undone.`)) return;
            const token = getToken();
            try {
                const res = await fetch(`/api/v1/auth/keys/${prefix}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                if (res.ok) {
                    refreshDashboard();
                } else {
                    const err = await res.json();
                    alert('Revocation failed: ' + (err.detail || err.title || 'Error'));
                }
            } catch (err) {
                alert('Network error: ' + err.message);
            }
        }

        async function dispatchSimulation() {
            const token = getToken();
            if (!token) {
                alert('Please provide or create an API Key before dispatching simulations.');
                return;
            }

            const domain = document.getElementById('sim-domain').value;
            const traffic = parseFloat(document.getElementById('sim-traffic').value);
            const horizon = parseInt(document.getElementById('sim-horizon').value);
            
            const btn = document.querySelector('button.btn-primary');
            btn.innerText = "SIMULATING...";
            btn.disabled = true;
            
            try {
                const res = await fetch('/api/v1/simulations', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify({ domain: domain, traffic_scale: traffic, horizon: horizon })
                });
                const data = await res.json();
                document.getElementById('sim-result').style.display = 'block';
                if (res.ok) {
                    document.getElementById('sim-output').innerText = 
                        `Status: ${data.status}\n` +
                        `Simulation ID: ${data.simulation_id}\n` +
                        `Domain: ${data.domain} | Horizon: ${data.horizon} steps\n` +
                        `Recommendation: ${data.recommendation}\n` +
                        `Candidate Futures Evaluated: ${data.timelines ? data.timelines.length : 0}\n` +
                        `Execution Time: ${data.execution_time_ms.toFixed(2)} ms`;
                    refreshDashboard();
                } else {
                    document.getElementById('sim-output').innerText = 
                        `Simulation Rejected (${res.status}):\n${data.title || 'Error'}: ${data.detail || JSON.stringify(data)}`;
                }
            } catch (err) {
                document.getElementById('sim-result').style.display = 'block';
                document.getElementById('sim-output').innerText = `Network Transport Error: ${err.message}`;
            } finally {
                btn.innerText = "DISPATCH SIMULATION";
                btn.disabled = false;
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>"']/g, function(m) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
            });
        }

        // Initialize on page load
        document.addEventListener('DOMContentLoaded', () => {
            const saved = getToken();
            if (saved) {
                document.getElementById('auth-token-input').value = saved;
                document.getElementById('auth-status').innerText = 'Session Active';
                document.getElementById('auth-status').style.color = 'var(--success)';
            }
            refreshDashboard();
        });
    </script>
</body>
</html>
"""
