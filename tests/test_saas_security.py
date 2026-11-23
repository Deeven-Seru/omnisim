"""Automated Integration Test Suite for OmniSim Production SaaS HTTP Security Boundaries."""

from __future__ import annotations

import hashlib
import hmac
import http.client
import json
import os
import threading
import time
import unittest
from socketserver import TCPServer

import omnisim.server
from omnisim.saas.db import Database
from omnisim.saas.engine import OmniSimSaaSPlatform
from omnisim.server import OmniSimAPIServer


class TestSaaSSecurityBoundaries(unittest.TestCase):
    """Verifies that OmniSim enforces authentication, RBAC, input boundaries, and tenancy isolation."""

    @classmethod
    def setUpClass(cls):
        # Configure in-memory database and test platform
        cls.db = Database(":memory:")
        cls.platform = OmniSimSaaSPlatform(db=cls.db, enable_demo_mode=False)

        # Wire global platform instance for server
        omnisim.server.saas_platform = cls.platform

        # Create two isolated test tenants
        cls.tenant_a, cls.token_a = cls.platform.create_tenant("Tenant Alpha", tier="FREE")
        cls.tenant_b, cls.token_b = cls.platform.create_tenant("Tenant Beta", tier="FREE")

        # Create an admin key for Tenant A
        cls.admin_key_a, cls.admin_token_a = cls.platform.create_api_key(
            tenant_id=cls.tenant_a.id,
            name="Admin Key A",
            scopes=["admin", "simulations:write", "telemetry:write", "webhooks:write"],
        )

        # Create a restricted (read-only / simulations only) key for Tenant A
        cls.sim_key_a, cls.sim_token_a = cls.platform.create_api_key(
            tenant_id=cls.tenant_a.id,
            name="Sim Only Key A",
            scopes=["simulations:write"],
        )

        # Bind test server to loopback on ephemeral port
        cls.httpd = TCPServer(("127.0.0.1", 0), OmniSimAPIServer)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        headers: dict | None = None,
        raw_body: bytes | None = None,
    ) -> tuple[int, dict, dict]:
        conn = http.client.HTTPConnection("127.0.0.1", self.port)
        req_headers = headers.copy() if headers else {}
        req_body = None

        if body is not None:
            req_body = json.dumps(body).encode("utf-8")
            req_headers["Content-Type"] = "application/json"
            req_headers["Content-Length"] = str(len(req_body))
        elif raw_body is not None:
            req_body = raw_body
            req_headers["Content-Length"] = str(len(req_body))

        conn.request(method, path, body=req_body, headers=req_headers)
        res = conn.getresponse()
        res_data = res.read()
        res_headers = {k.lower(): v for k, v in res.getheaders()}

        parsed_json = {}
        content_type = res_headers.get("content-type", "").lower()
        if res_data and "application/json" in content_type:
            try:
                parsed_json = json.loads(res_data.decode("utf-8"))
            except Exception:
                pass

        conn.close()
        return res.status, parsed_json, res_headers

    # --------------------------------------------------------------------------
    # 1. Authentication & Security Headers
    # --------------------------------------------------------------------------
    def test_security_headers_present(self):
        status, _, headers = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(headers.get("x-frame-options"), "DENY")
        self.assertIn("strict-origin", headers.get("referrer-policy", ""))

    def test_health_version(self):
        status, data, _ = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(data.get("version"), "1.0.0")

    def test_unauthenticated_request_rejected(self):
        status, data, _ = self._request("GET", "/api/v1/tenants/me")
        self.assertEqual(status, 401)
        self.assertEqual(data.get("title"), "Unauthorized")

    def test_invalid_bearer_token_rejected(self):
        headers = {"Authorization": "Bearer os_live_badtoken_12345"}
        status, data, _ = self._request("GET", "/api/v1/tenants/me", headers=headers)
        self.assertEqual(status, 401)
        self.assertEqual(data.get("title"), "Unauthorized")

    def test_authenticated_tenant_succeeds(self):
        headers = {"Authorization": f"Bearer {self.token_a}"}
        status, data, _ = self._request("GET", "/api/v1/tenants/me", headers=headers)
        self.assertEqual(status, 200)
        self.assertEqual(data.get("tenant_id"), self.tenant_a.id)

    # --------------------------------------------------------------------------
    # 2. RBAC & Key Lifecycle Management
    # --------------------------------------------------------------------------
    def test_key_minting_requires_admin_scope(self):
        # A key without 'admin' scope must be rejected with 403 Forbidden
        headers = {"Authorization": f"Bearer {self.sim_token_a}"}
        payload = {"name": "Unauthorized Key"}
        status, data, _ = self._request("POST", "/api/v1/auth/keys", body=payload, headers=headers)
        self.assertEqual(status, 403)
        self.assertEqual(data.get("title"), "Forbidden")

    def test_admin_can_mint_and_revoke_key(self):
        headers = {"Authorization": f"Bearer {self.admin_token_a}"}
        payload = {"name": "Deploy Bot Key", "scopes": ["simulations:write"]}
        status, data, _ = self._request("POST", "/api/v1/auth/keys", body=payload, headers=headers)
        self.assertEqual(status, 201)
        new_token = data.get("token")
        prefix = data.get("prefix")
        self.assertTrue(new_token.startswith("os_live_"))

        # Verify new key can authenticate
        sim_headers = {"Authorization": f"Bearer {new_token}"}
        status_sim, _, _ = self._request("GET", "/api/v1/tenants/me", headers=sim_headers)
        self.assertEqual(status_sim, 200)

        # Revoke the key using prefix
        del_status, del_data, _ = self._request("DELETE", f"/api/v1/auth/keys/{prefix}", headers=headers)
        self.assertEqual(del_status, 200)
        self.assertEqual(del_data.get("status"), "REVOKED")

        # Verify revoked key is immediately rejected
        status_after_revoke, _, _ = self._request("GET", "/api/v1/tenants/me", headers=sim_headers)
        self.assertEqual(status_after_revoke, 401)

    # --------------------------------------------------------------------------
    # 3. Public Signup Plan Entitlement Protection
    # --------------------------------------------------------------------------
    def test_public_signup_cannot_self_escalate_tier(self):
        # Public attacker attempts to self-grant ENTERPRISE
        payload = {"name": "Attacker Org", "tier": "ENTERPRISE"}
        status, data, _ = self._request("POST", "/api/v1/tenants", body=payload)
        self.assertEqual(status, 201)
        # Must be capped to FREE tier
        self.assertEqual(data.get("tier"), "FREE")

    # --------------------------------------------------------------------------
    # 4. Multi-Tenant Data Isolation
    # --------------------------------------------------------------------------
    def test_tenancy_isolation_pr_audits(self):
        # Inject PR audit for Tenant A
        from omnisim.saas.models import GitHubPRAudit
        audit_a = GitHubPRAudit(
            id="audit_secret_a",
            tenant_id=self.tenant_a.id,
            repo="tenant-a/secret-repo",
            pr_number=101,
            commit_sha="a1b2c3d",
            verdict="PASS",
            critical_breaches=0,
            recommended_fix="None",
            audit_summary="Secret Tenant A summary",
        )
        self.db.save_pr_audit(audit_a)

        # Tenant B queries PR audits
        headers_b = {"Authorization": f"Bearer {self.token_b}"}
        status, data, _ = self._request("GET", "/api/v1/pr-audits", headers=headers_b)
        self.assertEqual(status, 200)
        # Tenant B must NOT see Tenant A's audit
        audit_ids = [a["id"] for a in data.get("audits", [])]
        self.assertNotIn("audit_secret_a", audit_ids)

        # Tenant A queries PR audits
        headers_a = {"Authorization": f"Bearer {self.token_a}"}
        status_a, data_a, _ = self._request("GET", "/api/v1/pr-audits", headers=headers_a)
        self.assertEqual(status_a, 200)
        audit_ids_a = [a["id"] for a in data_a.get("audits", [])]
        self.assertIn("audit_secret_a", audit_ids_a)

    # --------------------------------------------------------------------------
    # 5. Input Boundaries & Validation
    # --------------------------------------------------------------------------
    def test_invalid_simulation_domain_rejected(self):
        headers = {"Authorization": f"Bearer {self.sim_token_a}"}
        payload = {"domain": "unknown_fantasy_domain", "horizon": 6}
        status, data, _ = self._request("POST", "/api/v1/simulations", body=payload, headers=headers)
        self.assertEqual(status, 400)
        self.assertEqual(data.get("title"), "Bad Request")

    def test_excessive_horizon_rejected(self):
        headers = {"Authorization": f"Bearer {self.sim_token_a}"}
        payload = {"domain": "systems", "horizon": 100}  # Cap is 20
        status, data, _ = self._request("POST", "/api/v1/simulations", body=payload, headers=headers)
        self.assertEqual(status, 400)
        self.assertIn("between 1 and 20", data.get("detail", ""))

    def test_excessive_batch_rollouts_rejected(self):
        headers = {"Authorization": f"Bearer {self.sim_token_a}"}
        payload = {"domain": "systems", "num_rollouts": 50000, "horizon": 6}
        status, data, _ = self._request("POST", "/api/v1/simulate/batch", body=payload, headers=headers)
        self.assertEqual(status, 400)
        self.assertIn("between 1 and 1000", data.get("detail", ""))

    # --------------------------------------------------------------------------
    # 6. GitHub Webhook Security & Replay Prevention
    # --------------------------------------------------------------------------
    def test_github_webhook_signature_and_replay_protection(self):
        secret = "super_secret_webhook_key_2026"
        os.environ["OMNISIM_WEBHOOK_SECRET"] = secret

        payload_obj = {
            "repository": {"full_name": "acme/repo"},
            "pull_request": {"number": 55, "head": {"sha": "1234567"}},
        }
        raw_body = json.dumps(payload_obj).encode("utf-8")
        valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

        # 1. Missing signature -> 401
        headers_no_sig = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
        }
        status, _, _ = self._request("POST", "/api/v1/webhooks/github", raw_body=raw_body, headers=headers_no_sig)
        self.assertEqual(status, 401)

        # 2. Invalid signature -> 401
        headers_bad_sig = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalid_hash_signature",
        }
        status, _, _ = self._request("POST", "/api/v1/webhooks/github", raw_body=raw_body, headers=headers_bad_sig)
        self.assertEqual(status, 401)

        # 3. Valid signature -> 200
        headers_valid = {
            "Authorization": f"Bearer {self.token_a}",
            "Content-Type": "application/json",
            "X-Hub-Signature-256": valid_sig,
            "X-GitHub-Delivery": "delivery_uuid_test_1",
        }
        status, res_valid, _ = self._request("POST", "/api/v1/webhooks/github", raw_body=raw_body, headers=headers_valid)
        self.assertEqual(status, 200)
        self.assertIn("verdict", res_valid)

        # 4. Replay attack with same delivery ID -> 409 Conflict
        status_replay, res_replay, _ = self._request("POST", "/api/v1/webhooks/github", raw_body=raw_body, headers=headers_valid)
        self.assertEqual(status_replay, 409)
        self.assertEqual(res_replay.get("title"), "Conflict")


if __name__ == "__main__":
    unittest.main()
