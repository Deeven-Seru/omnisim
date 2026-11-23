"""Domain models and persistence schemas for OmniSim SaaS Platform."""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PlanTier(str, Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


TIER_LIMITS = {
    PlanTier.FREE: {
        "monthly_simulations": 50,
        "max_horizon": 6,
        "max_rollouts": 100,
        "rate_limit_per_min": 20,
        "custom_dynamics": False,
        "sla_guarantee": "None (Community)",
    },
    PlanTier.PRO: {
        "monthly_simulations": 10_000,
        "max_horizon": 15,
        "max_rollouts": 5_000,
        "rate_limit_per_min": 600,
        "custom_dynamics": True,
        "sla_guarantee": "99.9% Availability",
    },
    PlanTier.ENTERPRISE: {
        "monthly_simulations": 1_000_000,
        "max_horizon": 50,
        "max_rollouts": 100_000,
        "rate_limit_per_min": 10_000,
        "custom_dynamics": True,
        "sla_guarantee": "99.99% Availability + Dedicated High-Throughput Compute",
    },
}


@dataclass
class Tenant:
    """An organization or customer account in the OmniSim SaaS platform."""
    id: str
    name: str
    tier: PlanTier = PlanTier.PRO
    created_at: float = field(default_factory=time.time)
    monthly_usage_count: int = 0
    quota_reset_epoch: float = field(default_factory=lambda: time.time() + 30 * 86400)
    settings: Dict[str, Any] = field(default_factory=dict)

    def can_simulate(self) -> Tuple[bool, str]:
        limits = TIER_LIMITS[self.tier]
        max_sims = limits["monthly_simulations"]
        if self.monthly_usage_count >= max_sims:
            return False, f"Monthly quota exceeded ({self.monthly_usage_count}/{max_sims} simulations for tier {self.tier.value}). Upgrade required."
        return True, ""

    def record_simulation(self) -> None:
        self.monthly_usage_count += 1


@dataclass
class APIKey:
    """Authentication credential for programmatic API and CI/CD access."""
    key_hash: str
    tenant_id: str
    name: str
    prefix: str
    created_at: float = field(default_factory=time.time)
    last_used_at: Optional[float] = None
    scopes: List[str] = field(default_factory=lambda: ["simulations:write", "telemetry:write", "webhooks:write"])
    expires_at: Optional[float] = None
    revoked: bool = False

    @classmethod
    def generate(
        cls,
        tenant_id: str,
        name: str = "Production CI Key",
        scopes: Optional[List[str]] = None,
        expires_at: Optional[float] = None,
    ) -> Tuple[APIKey, str]:
        raw_token = f"os_live_{secrets.token_hex(24)}"
        prefix = raw_token[:12]
        key_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        resolved_scopes = scopes if scopes is not None else ["simulations:write", "telemetry:write", "webhooks:write"]
        return cls(
            key_hash=key_hash,
            tenant_id=tenant_id,
            name=name,
            prefix=prefix,
            scopes=resolved_scopes,
            expires_at=expires_at,
        ), raw_token


@dataclass
class SimulationRecord:
    """Audit and telemetry log of a counterfactual simulation run."""
    id: str
    tenant_id: str
    domain: str
    horizon: int
    status: str  # 'COMPLETED', 'BLOCKED', 'FAILED'
    critical_violations_count: int = 0
    optimal_action_name: str = ""
    optimal_action_cost: float = 0.0
    recommendation: str = ""
    execution_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    traffic_scale: float = 1.0


@dataclass
class GitHubPRAudit:
    """Record of a pre-flight GitHub PR check run."""
    id: str
    tenant_id: str
    repo: str
    pr_number: int
    commit_sha: str
    verdict: str  # 'PASS' or 'BLOCKED'
    critical_breaches: int
    recommended_fix: str
    audit_summary: str
    created_at: float = field(default_factory=time.time)
