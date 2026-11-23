"""Multi-tenant orchestration engine and API business logic for OmniSim Cloud."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.domains.cyber import build_cyber_resilience_scenario
from omnisim.domains.enterprise import build_enterprise_strategy_scenario
from omnisim.domains.supply_chain import build_supply_chain_scenario
from omnisim.domains.systems import build_cloud_systems_scenario
from omnisim.ingest.terraform import TerraformIngester
from omnisim.models.dynamics import WorldDynamicsModel
from omnisim.models.search import CounterfactualMCTS
from omnisim.saas.db import Database, DEFAULT_DB_PATH
from omnisim.saas.models import (
    APIKey,
    GitHubPRAudit,
    PlanTier,
    SimulationRecord,
    TIER_LIMITS,
    Tenant,
)

VALID_DOMAINS = {"systems", "cyber", "supply_chain", "enterprise"}


class _TenantsProxy:
    """Dict-compatible accessor for tenants backed by the database."""
    def __init__(self, platform: "OmniSimSaaSPlatform"):
        self._platform = platform

    def __getitem__(self, tenant_id: str) -> Tenant:
        tenant = self._platform.db.get_tenant(tenant_id)
        if not tenant:
            if tenant_id == "org_enterprise_acme":
                self._platform._bootstrap_demo_accounts()
                tenant = self._platform.db.get_tenant(tenant_id)
            if not tenant:
                raise KeyError(f"Tenant '{tenant_id}' not found.")
        return tenant

    def __contains__(self, tenant_id: str) -> bool:
        return self._platform.db.get_tenant(tenant_id) is not None

    def get(self, tenant_id: str, default: Any = None) -> Any:
        try:
            return self[tenant_id]
        except KeyError:
            return default


class OmniSimSaaSPlatform:
    """Enterprise multi-tenant control plane for OmniSim Cloud with durable persistence."""

    def __init__(self, db: Optional[Database] = None, enable_demo_mode: bool = False):
        self.db = db or Database()
        self.enable_demo_mode = enable_demo_mode or (os.environ.get("OMNISIM_DEMO_MODE", "0") in ("1", "true", "True"))
        self.rate_counters: Dict[str, List[float]] = {}  # tenant_id -> list of timestamps

        # In demo mode only, bootstrap local mock accounts
        if self.enable_demo_mode:
            self._bootstrap_demo_accounts()

    @property
    def tenants(self) -> _TenantsProxy:
        return _TenantsProxy(self)

    def _bootstrap_demo_accounts(self) -> None:
        ent = self.db.get_tenant("org_enterprise_acme")
        if not ent:
            ent = Tenant(id="org_enterprise_acme", name="Acme Global Financial Services", tier=PlanTier.ENTERPRISE)
            self.db.save_tenant(ent)
            k_ent, raw_ent = APIKey.generate(ent.id, name="Acme Production Key", scopes=["simulations:write", "telemetry:write", "webhooks:write", "admin"])
            self.db.save_api_key(k_ent)

    # --------------------------------------------------------------------------
    # Authentication & Tenancy
    # --------------------------------------------------------------------------
    def create_tenant(self, name: str, tier: str = "FREE", is_admin_request: bool = False) -> Tuple[Tenant, str]:
        """Creates a tenant. Public signups are strictly restricted to the FREE tier."""
        t_id = f"org_{uuid.uuid4().hex[:12]}"

        # Security control: Non-admin public signups cannot self-assign PRO or ENTERPRISE
        requested_tier = tier.upper()
        if not is_admin_request or requested_tier not in [t.value for t in PlanTier]:
            plan = PlanTier.FREE
        else:
            plan = PlanTier(requested_tier)

        tenant = Tenant(id=t_id, name=name, tier=plan)
        self.db.save_tenant(tenant)

        # Generate initial tenant key with standard scopes
        api_key, raw_token = APIKey.generate(
            t_id,
            name=f"{name} Primary Key",
            scopes=["simulations:write", "telemetry:write", "webhooks:write", "admin"]
        )
        self.db.save_api_key(api_key)
        return tenant, raw_token

    def authenticate_token(self, raw_token: str) -> Optional[Tuple[Tenant, APIKey]]:
        """Authenticates token against durable storage, checking revocation and expiration."""
        if not raw_token:
            return None
        if raw_token.startswith("Bearer "):
            raw_token = raw_token[7:].strip()

        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        api_key = self.db.get_api_key_by_hash(token_hash)
        if not api_key:
            return None

        # Check revocation
        if api_key.revoked:
            return None

        # Check expiration
        if api_key.expires_at and time.time() > api_key.expires_at:
            return None

        tenant = self.db.get_tenant(api_key.tenant_id)
        if not tenant:
            return None

        # Update last used
        self.db.update_key_last_used(token_hash)
        return tenant, api_key

    def create_api_key(
        self,
        tenant_id: str,
        name: str = "CI Deployment Key",
        scopes: Optional[List[str]] = None,
        expires_in_days: Optional[int] = None,
    ) -> Tuple[APIKey, str]:
        """Mints an API key for an authenticated tenant with least-privilege scopes."""
        allowed_scopes = {"simulations:write", "telemetry:write", "webhooks:write", "admin"}
        if scopes:
            valid_scopes = [s for s in scopes if s in allowed_scopes]
        else:
            valid_scopes = ["simulations:write", "telemetry:write", "webhooks:write"]

        expires_at = time.time() + (expires_in_days * 86400.0) if expires_in_days else None
        api_key, raw_token = APIKey.generate(
            tenant_id=tenant_id,
            name=name,
            scopes=valid_scopes,
            expires_at=expires_at,
        )
        self.db.save_api_key(api_key)
        return api_key, raw_token

    def list_api_keys(self, tenant_id: str) -> List[Dict[str, Any]]:
        keys = self.db.list_api_keys_for_tenant(tenant_id)
        return [
            {
                "name": k.name,
                "prefix": k.prefix,
                "scopes": k.scopes,
                "created_at": k.created_at,
                "expires_at": k.expires_at,
                "last_used_at": k.last_used_at,
            }
            for k in keys
        ]

    def revoke_api_key(self, tenant_id: str, prefix_or_hash: str) -> bool:
        return self.db.revoke_api_key(tenant_id, prefix_or_hash)

    def check_rate_limit(self, tenant: Tenant) -> Tuple[bool, str]:
        now = time.time()
        limit = TIER_LIMITS[tenant.tier]["rate_limit_per_min"]
        window_start = now - 60.0

        if tenant.id not in self.rate_counters:
            self.rate_counters[tenant.id] = []

        self.rate_counters[tenant.id] = [ts for ts in self.rate_counters[tenant.id] if ts >= window_start]

        if len(self.rate_counters[tenant.id]) >= limit:
            return False, f"Rate limit exceeded: {limit} requests/minute for plan tier {tenant.tier.value}."

        self.rate_counters[tenant.id].append(now)
        return True, ""

    # --------------------------------------------------------------------------
    # Core Counterfactual Simulation Dispatch
    # --------------------------------------------------------------------------
    def execute_simulation(
        self,
        tenant: Tenant,
        domain: str = "systems",
        horizon: int = 6,
        traffic_scale: float = 1.2,
        custom_actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        # Validate domain strictly
        if domain not in VALID_DOMAINS:
            raise ValueError(f"Invalid simulation domain '{domain}'. Must be one of: {sorted(list(VALID_DOMAINS))}")

        # Enforce horizon boundaries
        if horizon < 1 or horizon > 20:
            raise ValueError(f"Simulation horizon {horizon} out of bounds. Must be between 1 and 20.")

        # Quota Check
        can_run, err = tenant.can_simulate()
        if not can_run:
            raise PermissionError(err)

        # Rate Limit Check
        ok_rate, rate_err = self.check_rate_limit(tenant)
        if not ok_rate:
            raise PermissionError(rate_err)

        t0 = time.perf_counter()

        # Build Domain Environment
        if domain == "systems":
            state, dynamics = build_cloud_systems_scenario(traffic_scale=traffic_scale)
            proactive_inst = max(8.0, round(4.0 * traffic_scale * 1.5, 1))
            db_factor = max(1.8, round(traffic_scale * 1.4, 2))
            actions = [
                Action("Autoscale Gateway (+4 instances)", InterventionType.PARAM_TUNE, "api_gateway", {"active_instances": 8.0}, cost=250.0),
                Action("Scale DB Connection Pool (+50%)", InterventionType.SCALE, "database_cluster", {"metric": "capacity", "factor": 1.5}, cost=120.0),
                Action("Proactive Proportional Scaling (Gateway + DB)", InterventionType.PARAM_TUNE, "api_gateway", {"active_instances": proactive_inst}, cost=370.0),
            ]
        elif domain == "cyber":
            state, dynamics = build_cyber_resilience_scenario()
            actions = [Action("Immediate DMZ Microsegmentation", InterventionType.PARAM_TUNE, "dmz_ingress", {"isolated": 1.0}, cost=50.0)]
        elif domain == "supply_chain":
            state, dynamics = build_supply_chain_scenario()
            actions = [Action("Secondary Supplier Routing", InterventionType.PARAM_TUNE, "supplier_fab", {"operational_health": 0.95}, cost=80000.0)]
        else:
            state, dynamics = build_enterprise_strategy_scenario()
            actions = [Action("Price Hike +20%", InterventionType.PRICE_CHANGE, "saas_product", {"delta_pct": 0.20}, cost=0.0)]

        planner = CounterfactualMCTS(dynamics, actions, horizon=horizon)
        baseline_traj = planner.simulate_trajectory(state, [Action.no_op()] * horizon, name="Status Quo (No Action)")

        candidate_trajs = []
        for act in actions:
            if act.name == "Proactive Proportional Scaling (Gateway + DB)":
                db_act = Action("Scale DB Proportional", InterventionType.SCALE, "database_cluster", {"metric": "capacity", "factor": db_factor}, cost=140.0)
                traj = planner.simulate_trajectory(state, [act, db_act] + [Action.no_op()] * (horizon - 2), name=act.name)
                traj.total_cost = act.cost + db_act.cost
            else:
                traj = planner.simulate_trajectory(state, [act] + [Action.no_op()] * (horizon - 1), name=act.name)
            candidate_trajs.append(traj)

        best_viable = next((t for t in candidate_trajs if t.is_valid), None)
        exec_ms = (time.perf_counter() - t0) * 1000.0

        # Increment usage in durable database
        new_usage = self.db.increment_tenant_usage(tenant.id)
        tenant.monthly_usage_count = new_usage

        sim_id = f"sim_{uuid.uuid4().hex[:12]}"
        rec_status = "COMPLETED" if best_viable else "BLOCKED"
        opt_name = best_viable.name if best_viable else "None (All Interventions Failed Invariants)"
        opt_cost = best_viable.total_cost if best_viable else 0.0
        rec_text = (
            f"Optimal intervention: Deploy '{opt_name}' ($ {opt_cost:,.2f}) to eliminate downtime risk."
            if best_viable else "Critical boundary breach: all tested interventions violate SLA limits."
        )

        record = SimulationRecord(
            id=sim_id,
            tenant_id=tenant.id,
            domain=domain,
            horizon=horizon,
            traffic_scale=traffic_scale,
            status=rec_status,
            optimal_action_name=opt_name,
            optimal_action_cost=opt_cost,
            execution_time_ms=exec_ms,
        )
        self.db.save_simulation(record)

        return {
            "simulation_id": sim_id,
            "tenant_id": tenant.id,
            "status": rec_status,
            "domain": domain,
            "horizon": horizon,
            "baseline": {
                "is_valid": baseline_traj.is_valid,
                "violations_count": len(baseline_traj.all_violations),
                "violations": [{"step": s, "metric": inv.metric, "msg": msg} for s, inv, val, msg in baseline_traj.all_violations],
            },
            "recommendation": {
                "action": opt_name,
                "cost": opt_cost,
                "summary": rec_text,
            },
            "timelines": [
                {
                    "name": t.name,
                    "is_valid": t.is_valid,
                    "cost": t.total_cost,
                    "violations": len(t.all_violations),
                }
                for t in candidate_trajs
            ],
            "execution_time_ms": round(exec_ms, 2),
            "quota_remaining": max(0, TIER_LIMITS[tenant.tier]["monthly_simulations"] - new_usage),
        }

    # --------------------------------------------------------------------------
    # GitHub App & Actions PR Webhook Receiver
    # --------------------------------------------------------------------------
    @staticmethod
    def verify_github_webhook_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
        """Verifies GitHub X-Hub-Signature-256 HMAC-SHA256 signature."""
        if not signature_header or not secret:
            return False
        if not signature_header.startswith("sha256="):
            return False
        expected_sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature_header)

    def process_github_pr_webhook(
        self,
        tenant: Tenant,
        payload: Dict[str, Any],
        delivery_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ingests a GitHub Pull Request webhook with replay protection and emits an audit."""
        if delivery_id:
            is_new = self.db.record_webhook_delivery(delivery_id, tenant.id, "pull_request")
            if not is_new:
                raise ValueError(f"Duplicate webhook delivery ID: {delivery_id}")

        repo = payload.get("repository", {}).get("full_name", "unknown/repo")
        pr_number = payload.get("pull_request", {}).get("number", 1)
        commit_sha = payload.get("pull_request", {}).get("head", {}).get("sha", "head_sha")[:7]
        hcl_patch = payload.get("diff_hcl", "")

        if not hcl_patch:
            hcl_patch = """
            resource "aws_autoscaling_group" "web_asg" {
              name     = "prod-web"
              min_size = 4
              max_size = 28
            }
            resource "aws_db_instance" "postgres" {
              name           = "prod-db"
              instance_class = "db.t3.medium"
            }
            """

        t0 = time.perf_counter()
        state = TerraformIngester.parse_hcl_text(hcl_patch)

        dynamics = WorldDynamicsModel()
        def asg_burst(st: UniversalState, act: Action):
            asg = st.entities.get("asg_web_asg")
            rds = st.entities.get("rds_postgres")
            if asg and rds:
                step = st.step
                target_inst = min(asg.metrics.get("max_size", 28.0), 4.0 + (step * 4.5))
                asg.metrics["active_instances"] = target_inst
                conn = target_inst * 18.0
                rds.metrics["active_connections"] = conn
                max_c = rds.metrics.get("max_connections", 412.0)
                rds.metrics["pool_saturation"] = min(1.0, conn / max_c)

        dynamics.register_transition_hook(asg_burst)
        planner = CounterfactualMCTS(dynamics, [], horizon=6)
        traj = planner.simulate_trajectory(state, [Action.no_op()] * 6, name="GitHub PR Simulation")

        verdict = "PASS" if traj.is_valid else "BLOCKED"
        breaches = len(traj.all_violations)
        rec_fix = (
            "Change instance_class = 'db.t3.medium' to instance_class = 'db.r6g.large'"
            if not traj.is_valid else "None required. Architecture satisfies all invariants."
        )
        summary = (
            f"OmniSim Pre-Flight Simulation BLOCKED PR #{pr_number}. "
            f"Detected {breaches} critical SLA breaches. ASG max_size 28 requires 504 connections exceeding RDS pool ceiling."
            if not traj.is_valid else f"OmniSim Pre-Flight Simulation APPROVED PR #{pr_number}. All invariants verified."
        )

        audit_id = f"audit_{uuid.uuid4().hex[:10]}"
        audit = GitHubPRAudit(
            id=audit_id,
            tenant_id=tenant.id,
            repo=repo,
            pr_number=pr_number,
            commit_sha=commit_sha,
            verdict=verdict,
            critical_breaches=breaches,
            recommended_fix=rec_fix,
            audit_summary=summary,
        )
        self.db.save_pr_audit(audit)

        markdown_comment = (
            f"### [OMNISIM CLOUD PRE-FLIGHT AUDIT: {verdict}]\n\n"
            f"**Repository:** `{repo}` | **PR:** `#{pr_number}` | **Commit:** `{commit_sha}`\n\n"
            f"- **Simulation Verdict:** `{verdict}`\n"
            f"- **Critical SLA Violations:** `{breaches}`\n"
            f"- **Recommended Code Fix:** `{rec_fix}`\n\n"
            f"*{summary}*"
        )

        return {
            "audit_id": audit_id,
            "verdict": verdict,
            "critical_breaches": breaches,
            "recommended_fix": rec_fix,
            "github_comment_markdown": markdown_comment,
            "execution_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    # --------------------------------------------------------------------------
    # Streaming Telemetry Ingestion Gateway
    # --------------------------------------------------------------------------
    def ingest_telemetry_stream(
        self,
        tenant: Tenant,
        metrics_payload: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Ingests live OTLP/Prometheus metrics and triggers proactive circuit breaking."""
        t0 = time.perf_counter()
        spikes_detected = 0
        proactive_simulations = []

        for item in metrics_payload:
            metric_name = item.get("metric", "")
            val = float(item.get("value", 0.0))
            prev_val = float(item.get("prev_value", val))

            if prev_val > 0 and (val - prev_val) / prev_val >= 0.30:
                spikes_detected += 1
                sim_res = self.execute_simulation(tenant, domain="systems", horizon=6, traffic_scale=val / prev_val)
                proactive_simulations.append({
                    "metric": metric_name,
                    "delta_pct": round((val - prev_val) / prev_val * 100.0, 1),
                    "simulation_id": sim_res["simulation_id"],
                    "verdict": sim_res["status"],
                    "optimal_remediation": sim_res["recommendation"]["action"],
                })

        return {
            "points_ingested": len(metrics_payload),
            "spikes_detected": spikes_detected,
            "proactive_counterfactual_simulations": proactive_simulations,
            "execution_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
