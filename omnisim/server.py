"""Enterprise REST & Headless Agent Gateway for OmniSim.

Exposes OmniSim's counterfactual simulation engine via production-grade REST APIs
for CI/CD pipelines, Kubernetes controllers, and enterprise monitoring stacks.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import urllib.parse
from typing import Any, Dict, List, Optional, Tuple

from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.domains.cyber import build_cyber_resilience_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.supply_chain import build_supply_chain_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.engine.batched_simulator import BatchedSimulator
from omnisim.ingest.k8s import KubernetesManifestIngester
from omnisim.models.search import CounterfactualMCTS
from omnisim.saas.engine import OmniSimSaaSPlatform, VALID_DOMAINS
from omnisim.saas.models import APIKey, PlanTier, TIER_LIMITS, Tenant
from omnisim.saas.portal import SAAS_PORTAL_HTML
from omnisim.visualizer import HTML_TEMPLATE

DEFAULT_PORT = 8088
DEFAULT_HOST = "127.0.0.1"
MAX_REQUEST_BODY_BYTES = 5 * 1024 * 1024  # 5 MB
SERVER_VERSION = "1.0.0"

# Global SaaS Platform Instance
saas_platform = OmniSimSaaSPlatform()


class OmniSimAPIServer(http.server.SimpleHTTPRequestHandler):
    """Production HTTP Request Handler with strict authentication, RBAC, and boundary enforcement."""

    server_version = f"OmniSim/{SERVER_VERSION}"

    def end_headers(self) -> None:
        # Standard security headers across all responses
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;")
        super().end_headers()

    def _authenticate(self, required_scope: Optional[str] = None) -> Optional[Tuple[Tenant, APIKey]]:
        """Authenticates request via Bearer token. Returns (tenant, api_key) or sends 401/403 and returns None."""
        auth_hdr = self.headers.get("Authorization", "").strip()
        if not auth_hdr:
            self._send_error(
                status=401,
                title="Unauthorized",
                detail="Missing Authorization header. Provide 'Authorization: Bearer <api_key>'.",
            )
            return None

        auth_result = saas_platform.authenticate_token(auth_hdr)
        if not auth_result:
            self._send_error(
                status=401,
                title="Unauthorized",
                detail="Invalid, revoked, or expired API key.",
            )
            return None

        tenant, api_key = auth_result

        # RBAC Scope Check
        if required_scope:
            if "admin" not in api_key.scopes and required_scope not in api_key.scopes:
                self._send_error(
                    status=403,
                    title="Forbidden",
                    detail=f"API key '{api_key.prefix}...' lacks required scope '{required_scope}'.",
                )
                return None

        return tenant, api_key

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_error(self, status: int, title: str, detail: str) -> None:
        """Emits RFC 7807 problem details JSON."""
        error_doc = {
            "type": f"https://omnisim.io/errors/{title.lower().replace(' ', '-')}",
            "title": title,
            "status": status,
            "detail": detail,
        }
        self._send_json(error_doc, status=status)

    def _read_json_payload(self) -> Optional[Dict[str, Any]]:
        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self._send_error(status=400, title="Bad Request", detail="Missing Content-Length header.")
            return None

        try:
            content_length = int(content_length_str)
        except ValueError:
            self._send_error(status=400, title="Bad Request", detail="Invalid Content-Length header.")
            return None

        if content_length > MAX_REQUEST_BODY_BYTES:
            self._send_error(
                status=413,
                title="Payload Too Large",
                detail=f"Request body exceeds maximum size limit of {MAX_REQUEST_BODY_BYTES} bytes.",
            )
            return None

        try:
            body_bytes = self.rfile.read(content_length)
            return json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            self._send_error(status=400, title="Bad Request", detail=f"Malformed JSON: {str(e)}")
            return None

    # --------------------------------------------------------------------------
    # GET Handlers
    # --------------------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        # Static Local Dashboard Views (Loopback presentation)
        if parsed.path in ["/", "/index.html", "/dashboard"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(SAAS_PORTAL_HTML.encode("utf-8"))
            return

        elif parsed.path == "/visualizer":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
            return

        elif parsed.path == "/health":
            self._send_json({
                "status": "HEALTHY",
                "version": SERVER_VERSION,
                "engine": "OmniSim Counterfactual World Model",
                "platform": "OmniSim Cloud Multi-Tenant SaaS",
            })
            return

        # Protected Tenant Operations
        elif parsed.path == "/api/v1/tenants/me":
            auth = self._authenticate()
            if not auth:
                return
            tenant, _ = auth
            limits = TIER_LIMITS[tenant.tier]
            self._send_json({
                "tenant_id": tenant.id,
                "name": tenant.name,
                "tier": tenant.tier.value,
                "monthly_usage": tenant.monthly_usage_count,
                "monthly_quota": limits["monthly_simulations"],
                "quota_remaining": max(0, limits["monthly_simulations"] - tenant.monthly_usage_count),
                "limits": limits,
            })
            return

        elif parsed.path == "/api/v1/billing/usage":
            auth = self._authenticate()
            if not auth:
                return
            tenant, _ = auth
            limits = TIER_LIMITS[tenant.tier]
            self._send_json({
                "tenant_id": tenant.id,
                "tier": tenant.tier.value,
                "monthly_usage": tenant.monthly_usage_count,
                "monthly_quota": limits["monthly_simulations"],
                "quota_remaining": max(0, limits["monthly_simulations"] - tenant.monthly_usage_count),
                "sla_guarantee": limits["sla_guarantee"],
            })
            return

        elif parsed.path == "/api/v1/pr-audits":
            auth = self._authenticate()
            if not auth:
                return
            tenant, _ = auth
            # Tenancy Isolation: Only return audits for authenticated tenant
            audits = saas_platform.db.list_pr_audits_for_tenant(tenant.id)
            self._send_json({
                "tenant_id": tenant.id,
                "audits_count": len(audits),
                "audits": [
                    {
                        "id": a.id,
                        "repo": a.repo,
                        "pr_number": a.pr_number,
                        "commit_sha": a.commit_sha,
                        "verdict": a.verdict,
                        "critical_breaches": a.critical_breaches,
                        "recommended_fix": a.recommended_fix,
                        "audit_summary": a.audit_summary,
                    }
                    for a in audits
                ]
            })
            return

        elif parsed.path == "/api/v1/auth/keys":
            auth = self._authenticate(required_scope="admin")
            if not auth:
                return
            tenant, _ = auth
            keys = saas_platform.list_api_keys(tenant.id)
            self._send_json({"tenant_id": tenant.id, "keys": keys})
            return

        else:
            self._send_error(status=404, title="Not Found", detail=f"No route found for GET {parsed.path}")

    # --------------------------------------------------------------------------
    # POST Handlers
    # --------------------------------------------------------------------------
    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)

        # 1. Public Signup (Enforces FREE tier entitlement)
        if parsed.path == "/api/v1/tenants":
            payload = self._read_json_payload()
            if payload is None:
                return

            name = payload.get("name", "").strip() or "New Organization"
            # Security Control: Public signups cannot self-assign PRO or ENTERPRISE
            tenant, raw_token = saas_platform.create_tenant(name=name, tier="FREE", is_admin_request=False)
            self._send_json({
                "tenant_id": tenant.id,
                "name": tenant.name,
                "tier": tenant.tier.value,
                "api_key": raw_token,
                "status": "PROVISIONED",
                "notice": "Self-service registration assigned to FREE tier (100 simulations/month).",
            }, status=201)
            return

        # 2. Key Lifecycle: Mint Key (Requires authenticated admin)
        elif parsed.path == "/api/v1/auth/keys":
            auth = self._authenticate(required_scope="admin")
            if not auth:
                return
            tenant, _ = auth
            payload = self._read_json_payload()
            if payload is None:
                return

            key_name = payload.get("name", "CI Deployment Key")
            scopes = payload.get("scopes", ["simulations:write", "telemetry:write", "webhooks:write"])
            expires_days = payload.get("expires_in_days")

            api_key, raw_token = saas_platform.create_api_key(
                tenant_id=tenant.id,
                name=key_name,
                scopes=scopes,
                expires_in_days=int(expires_days) if expires_days else None,
            )
            self._send_json({
                "tenant_id": tenant.id,
                "key_name": key_name,
                "prefix": api_key.prefix,
                "token": raw_token,
                "scopes": api_key.scopes,
                "notice": "Store this token securely; it cannot be retrieved again.",
            }, status=201)
            return

        # 3. Simulations Dispatch (Requires authenticated tenant with simulations:write)
        elif parsed.path == "/api/v1/simulations":
            auth = self._authenticate(required_scope="simulations:write")
            if not auth:
                return
            tenant, _ = auth
            payload = self._read_json_payload()
            if payload is None:
                return

            domain = payload.get("domain", "systems")
            try:
                horizon = int(payload.get("horizon", 6))
                traffic_scale = float(payload.get("traffic_scale", 1.2))
            except (ValueError, TypeError):
                self._send_error(status=400, title="Bad Request", detail="Invalid horizon or traffic_scale format.")
                return

            try:
                result = saas_platform.execute_simulation(
                    tenant=tenant,
                    domain=domain,
                    horizon=horizon,
                    traffic_scale=traffic_scale,
                )
                self._send_json(result)
            except ValueError as ve:
                self._send_error(status=400, title="Bad Request", detail=str(ve))
            except PermissionError as pe:
                self._send_error(status=429, title="Quota Exceeded", detail=str(pe))
            return

        # 4. GitHub PR Webhook with Signature & Replay Verification
        elif parsed.path == "/api/v1/webhooks/github":
            # Webhook signature verification
            webhook_secret = os.environ.get("OMNISIM_WEBHOOK_SECRET", "")
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            if webhook_secret:
                sig_header = self.headers.get("X-Hub-Signature-256", "")
                if not OmniSimSaaSPlatform.verify_github_webhook_signature(webhook_secret, raw_body, sig_header):
                    self._send_error(
                        status=401,
                        title="Unauthorized",
                        detail="Invalid or missing X-Hub-Signature-256 webhook signature.",
                    )
                    return

            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except Exception as e:
                self._send_error(status=400, title="Bad Request", detail=f"Malformed webhook JSON: {str(e)}")
                return

            delivery_id = self.headers.get("X-GitHub-Delivery")

            # Route to tenant (via Authorization or default enterprise in demo mode)
            auth_hdr = self.headers.get("Authorization", "")
            auth_res = saas_platform.authenticate_token(auth_hdr)
            tenant = auth_res[0] if auth_res else (saas_platform.db.get_tenant("org_enterprise_acme") if saas_platform.enable_demo_mode else None)

            if not tenant:
                self._send_error(status=401, title="Unauthorized", detail="Missing tenant authentication for webhook integration.")
                return

            try:
                audit_result = saas_platform.process_github_pr_webhook(tenant, payload, delivery_id=delivery_id)
                self._send_json(audit_result)
            except ValueError as ve:
                # Replay attack / duplicate delivery ID
                self._send_error(status=409, title="Conflict", detail=str(ve))
            return

        # 5. Ingest Telemetry
        elif parsed.path == "/api/v1/ingest/telemetry":
            auth = self._authenticate(required_scope="telemetry:write")
            if not auth:
                return
            tenant, _ = auth
            payload = self._read_json_payload()
            if payload is None:
                return

            metrics = payload.get("metrics", [])
            telemetry_res = saas_platform.ingest_telemetry_stream(tenant, metrics)
            self._send_json(telemetry_res)
            return

        # 6. Ingest Kubernetes Manifests
        elif parsed.path == "/api/v1/ingest/k8s":
            auth = self._authenticate(required_scope="simulations:write")
            if not auth:
                return
            payload = self._read_json_payload()
            if payload is None:
                return

            manifests = payload.get("manifests", [])
            state = KubernetesManifestIngester.parse_manifests(manifests)
            self._send_json({
                "status": "SUCCESS",
                "entities_parsed": len(state.entities),
                "invariants_established": len(state.invariants),
                "relations_wired": len(state.relations),
                "entity_ids": list(state.entities.keys()),
            })
            return

        # 7. Batch Simulation
        elif parsed.path == "/api/v1/simulate/batch":
            auth = self._authenticate(required_scope="simulations:write")
            if not auth:
                return
            payload = self._read_json_payload()
            if payload is None:
                return

            domain = payload.get("domain", "systems")
            if domain not in VALID_DOMAINS:
                self._send_error(status=400, title="Bad Request", detail=f"Invalid domain '{domain}'. Must be one of {sorted(list(VALID_DOMAINS))}")
                return

            try:
                num_rollouts = int(payload.get("num_rollouts", 100))
                horizon = int(payload.get("horizon", 6))
            except (ValueError, TypeError):
                self._send_error(status=400, title="Bad Request", detail="Invalid rollouts or horizon format.")
                return

            # Enforce compute boundaries
            if num_rollouts < 1 or num_rollouts > 1000:
                self._send_error(status=400, title="Bad Request", detail="num_rollouts must be between 1 and 1000.")
                return
            if horizon < 1 or horizon > 20:
                self._send_error(status=400, title="Bad Request", detail="horizon must be between 1 and 20.")
                return

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
            return

        else:
            self._send_error(status=404, title="Not Found", detail=f"No route found for POST {parsed.path}")

    # --------------------------------------------------------------------------
    # DELETE Handlers (Key Revocation)
    # --------------------------------------------------------------------------
    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/v1/auth/keys/"):
            auth = self._authenticate(required_scope="admin")
            if not auth:
                return
            tenant, _ = auth
            key_identifier = parsed.path[len("/api/v1/auth/keys/"):]
            revoked = saas_platform.revoke_api_key(tenant.id, key_identifier)
            if revoked:
                self._send_json({"status": "REVOKED", "key_identifier": key_identifier})
            else:
                self._send_error(status=404, title="Not Found", detail=f"API key '{key_identifier}' not found for tenant.")
            return

        self._send_error(status=404, title="Not Found", detail=f"No route found for DELETE {parsed.path}")


def run_api_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, demo_mode: bool = False) -> None:
    global saas_platform
    if demo_mode:
        saas_platform.enable_demo_mode = True
        saas_platform._bootstrap_demo_accounts()

    print(f"[ONLINE] OmniSim Enterprise API Gateway v{SERVER_VERSION}")
    print(f"[SECURITY] Bound to {host}:{port} | Demo Mode: {saas_platform.enable_demo_mode}")
    with socketserver.TCPServer((host, port), OmniSimAPIServer) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down OmniSim API Server.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniSim Enterprise API Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default: 8088)")
    parser.add_argument("--demo", action="store_true", help="Enable local demo mode with mock accounts")
    args = parser.parse_args()
    run_api_server(host=args.host, port=args.port, demo_mode=args.demo)
