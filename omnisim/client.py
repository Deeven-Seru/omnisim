"""Official Python Client SDK for OmniSim and OmniSim Cloud.

Provides high-level programmatic interfaces for running counterfactual simulations,
auditing infrastructure PRs, auto-generating Git patches, and ingesting telemetry.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

from omnisim.agent.remediator import AutonomousAutoRemediator, RemediationPatchResult


class OmniSimClient:
    """Developer and Enterprise SDK client for OmniSim Cloud."""

    def __init__(
        self,
        api_key: str = "local",
        base_url: str = "http://localhost:8088",
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.is_local = (api_key == "local")

    # --------------------------------------------------------------------------
    # Health & Diagnostics
    # --------------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        """Checks the availability of the OmniSim API Gateway."""
        if self.is_local:
            return {"status": "HEALTHY", "mode": "IN_PROCESS", "version": "0.1.0"}
        return self._request("GET", "/health")

    # --------------------------------------------------------------------------
    # Counterfactual Simulation
    # --------------------------------------------------------------------------
    def simulate(
        self,
        domain: str = "systems",
        horizon: int = 6,
        traffic_scale: float = 1.2,
    ) -> Dict[str, Any]:
        """Dispatches an action-conditioned counterfactual simulation."""
        if self.is_local:
            from omnisim.saas.engine import OmniSimSaaSPlatform
            platform = OmniSimSaaSPlatform()
            tenant = platform.tenants["org_enterprise_acme"]
            return platform.execute_simulation(
                tenant=tenant,
                domain=domain,
                horizon=horizon,
                traffic_scale=traffic_scale,
            )

        payload = {"domain": domain, "horizon": horizon, "traffic_scale": traffic_scale}
        return self._request("POST", "/api/v1/simulations", payload)

    # --------------------------------------------------------------------------
    # Autonomous Infrastructure Auto-Remediation
    # --------------------------------------------------------------------------
    def auto_remediate(self, hcl_code: str) -> RemediationPatchResult:
        """Audits Terraform HCL code and returns an automated unified diff patch."""
        return AutonomousAutoRemediator.audit_and_generate_patch(hcl_code)

    # --------------------------------------------------------------------------
    # GitHub PR Audit Gatekeeper
    # --------------------------------------------------------------------------
    def audit_pull_request(
        self,
        repo: str,
        pr_number: int,
        diff_hcl: str,
        commit_sha: str = "head",
    ) -> Dict[str, Any]:
        """Audits a proposed GitHub PR diff and returns passing/blocking verdicts."""
        payload = {
            "repository": {"full_name": repo},
            "pull_request": {"number": pr_number, "head": {"sha": commit_sha}},
            "diff_hcl": diff_hcl,
        }
        if self.is_local:
            from omnisim.saas.engine import OmniSimSaaSPlatform
            platform = OmniSimSaaSPlatform()
            tenant = platform.tenants["org_enterprise_acme"]
            return platform.process_github_pr_webhook(tenant, payload)

        return self._request("POST", "/api/v1/webhooks/github", payload)

    # --------------------------------------------------------------------------
    # Telemetry Stream Ingestion
    # --------------------------------------------------------------------------
    def ingest_telemetry(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Streams live metrics and auto-triggers proactive simulations on acceleration."""
        payload = {"metrics": metrics}
        if self.is_local:
            from omnisim.saas.engine import OmniSimSaaSPlatform
            platform = OmniSimSaaSPlatform()
            tenant = platform.tenants["org_enterprise_acme"]
            return platform.ingest_telemetry_stream(tenant, metrics)

        return self._request("POST", "/api/v1/ingest/telemetry", payload)

    # --------------------------------------------------------------------------
    # Billing & Quotas
    # --------------------------------------------------------------------------
    def get_billing_usage(self) -> Dict[str, Any]:
        """Fetches the current tenant plan, monthly quota, and usage counters."""
        if self.is_local:
            return {
                "tenant_id": "org_local",
                "tier": "ENTERPRISE",
                "monthly_usage": 0,
                "monthly_quota": 1_000_000,
                "quota_remaining": 1_000_000,
                "sla_guarantee": "Unlimited Local Mode",
            }
        return self._request("GET", "/api/v1/billing/usage")

    # --------------------------------------------------------------------------
    # HTTP Transport Helper
    # --------------------------------------------------------------------------
    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "OmniSim-Python-SDK/0.1.0",
        }
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                return json.loads(err_body)
            except Exception:
                raise RuntimeError(f"OmniSim API Error ({e.code}): {err_body}")
        except Exception as e:
            raise ConnectionError(f"Failed to communicate with OmniSim Cloud at {url}: {str(e)}")
