"""Durable SQLite storage and tenant data isolation layer for OmniSim Cloud."""

from __future__ import annotations

import os
import sqlite3
import time
import tempfile
from typing import Any, Dict, List, Optional, Tuple
from omnisim.saas.models import PlanTier, Tenant, APIKey, GitHubPRAudit, SimulationRecord, TIER_LIMITS


def get_default_db_path() -> str:
    env_path = os.environ.get("OMNISIM_DB_PATH")
    if env_path:
        return env_path
    home_dir = os.path.expanduser("~/.omnisim")
    try:
        os.makedirs(home_dir, exist_ok=True)
        return os.path.join(home_dir, "omnisim.db")
    except (OSError, PermissionError):
        return os.path.join(tempfile.gettempdir(), "omnisim.db")


DEFAULT_DB_PATH = get_default_db_path()


class Database:
    """Thread-safe, durable SQLite storage for multi-tenant control plane."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_default_db_path()
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path != ":memory:":
            try:
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            except (OSError, PermissionError):
                self.db_path = ":memory:"
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", timeout=10.0, check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row
            self._mem_conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                monthly_usage_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS api_keys (
                key_hash TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                prefix TEXT NOT NULL,
                scopes TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL,
                revoked INTEGER DEFAULT 0,
                last_used_at REAL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS pr_audits (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                repo TEXT NOT NULL,
                pr_number INTEGER NOT NULL,
                commit_sha TEXT NOT NULL,
                verdict TEXT NOT NULL,
                critical_breaches INTEGER NOT NULL,
                recommended_fix TEXT NOT NULL,
                audit_summary TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS simulations (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                horizon INTEGER NOT NULL,
                traffic_scale REAL NOT NULL,
                status TEXT NOT NULL,
                optimal_action TEXT,
                optimal_cost REAL,
                execution_time_ms REAL,
                created_at REAL NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS webhook_deliveries (
                delivery_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_pr_audits_tenant ON pr_audits(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_simulations_tenant ON simulations(tenant_id);
            """)

    # --------------------------------------------------------------------------
    # Tenants
    # --------------------------------------------------------------------------
    def save_tenant(self, tenant: Tenant) -> None:
        now = time.time()
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO tenants (id, name, tier, monthly_usage_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                tier = excluded.tier,
                monthly_usage_count = excluded.monthly_usage_count,
                updated_at = excluded.updated_at
            """, (tenant.id, tenant.name, tenant.tier.value, tenant.monthly_usage_count, tenant.created_at, now))

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
            if not row:
                return None
            tenant = Tenant(
                id=row["id"],
                name=row["name"],
                tier=PlanTier(row["tier"]),
                created_at=row["created_at"],
            )
            tenant.monthly_usage_count = row["monthly_usage_count"]
            return tenant

    def increment_tenant_usage(self, tenant_id: str) -> int:
        with self._get_connection() as conn:
            conn.execute("""
            UPDATE tenants SET monthly_usage_count = monthly_usage_count + 1, updated_at = ? WHERE id = ?
            """, (time.time(), tenant_id))
            row = conn.execute("SELECT monthly_usage_count FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
            return row["monthly_usage_count"] if row else 0

    # --------------------------------------------------------------------------
    # API Keys
    # --------------------------------------------------------------------------
    def save_api_key(self, api_key: APIKey) -> None:
        scopes_str = ",".join(api_key.scopes)
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO api_keys (key_hash, tenant_id, name, prefix, scopes, created_at, expires_at, revoked, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key_hash) DO UPDATE SET
                name = excluded.name,
                scopes = excluded.scopes,
                revoked = excluded.revoked,
                last_used_at = excluded.last_used_at
            """, (
                api_key.key_hash, api_key.tenant_id, api_key.name, api_key.prefix,
                scopes_str, api_key.created_at, api_key.expires_at, 1 if api_key.revoked else 0,
                api_key.last_used_at
            ))

    def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,)).fetchone()
            if not row:
                return None
            return APIKey(
                key_hash=row["key_hash"],
                tenant_id=row["tenant_id"],
                name=row["name"],
                prefix=row["prefix"],
                scopes=row["scopes"].split(",") if row["scopes"] else [],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                revoked=bool(row["revoked"]),
                last_used_at=row["last_used_at"],
            )

    def list_api_keys_for_tenant(self, tenant_id: str) -> List[APIKey]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM api_keys WHERE tenant_id = ? AND revoked = 0 ORDER BY created_at DESC", (tenant_id,)).fetchall()
            return [
                APIKey(
                    key_hash=r["key_hash"],
                    tenant_id=r["tenant_id"],
                    name=r["name"],
                    prefix=r["prefix"],
                    scopes=r["scopes"].split(",") if r["scopes"] else [],
                    created_at=r["created_at"],
                    expires_at=r["expires_at"],
                    revoked=bool(r["revoked"]),
                    last_used_at=r["last_used_at"],
                )
                for r in rows
            ]

    def revoke_api_key(self, tenant_id: str, prefix_or_hash: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("""
            UPDATE api_keys SET revoked = 1 WHERE tenant_id = ? AND (key_hash = ? OR prefix = ?)
            """, (tenant_id, prefix_or_hash, prefix_or_hash))
            return cursor.rowcount > 0

    def update_key_last_used(self, key_hash: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE api_keys SET last_used_at = ? WHERE key_hash = ?", (time.time(), key_hash))

    # --------------------------------------------------------------------------
    # PR Audits
    # --------------------------------------------------------------------------
    def save_pr_audit(self, audit: GitHubPRAudit) -> None:
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO pr_audits (id, tenant_id, repo, pr_number, commit_sha, verdict, critical_breaches, recommended_fix, audit_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (audit.id, audit.tenant_id, audit.repo, audit.pr_number, audit.commit_sha, audit.verdict, audit.critical_breaches, audit.recommended_fix, audit.audit_summary, audit.created_at))

    def list_pr_audits_for_tenant(self, tenant_id: str, limit: int = 50) -> List[GitHubPRAudit]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM pr_audits WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?", (tenant_id, limit)).fetchall()
            return [
                GitHubPRAudit(
                    id=r["id"],
                    tenant_id=r["tenant_id"],
                    repo=r["repo"],
                    pr_number=r["pr_number"],
                    commit_sha=r["commit_sha"],
                    verdict=r["verdict"],
                    critical_breaches=r["critical_breaches"],
                    recommended_fix=r["recommended_fix"],
                    audit_summary=r["audit_summary"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # --------------------------------------------------------------------------
    # Simulations
    # --------------------------------------------------------------------------
    def save_simulation(self, record: SimulationRecord) -> None:
        opt_name = getattr(record, "optimal_action_name", getattr(record, "optimal_action", ""))
        opt_cost = getattr(record, "optimal_action_cost", getattr(record, "optimal_cost", 0.0))
        with self._get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO simulations (id, tenant_id, domain, horizon, traffic_scale, status, optimal_action, optimal_cost, execution_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (record.id, record.tenant_id, record.domain, record.horizon, record.traffic_scale, record.status, opt_name, opt_cost, record.execution_time_ms, record.created_at))

    def list_simulations_for_tenant(self, tenant_id: str, limit: int = 50) -> List[SimulationRecord]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM simulations WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?", (tenant_id, limit)).fetchall()
            return [
                SimulationRecord(
                    id=r["id"],
                    tenant_id=r["tenant_id"],
                    domain=r["domain"],
                    horizon=r["horizon"],
                    traffic_scale=r["traffic_scale"],
                    status=r["status"],
                    optimal_action_name=r["optimal_action"] or "",
                    optimal_action_cost=r["optimal_cost"] or 0.0,
                    execution_time_ms=r["execution_time_ms"] or 0.0,
                    created_at=r["created_at"],
                )
                for r in rows
            ]

    # --------------------------------------------------------------------------
    # Webhooks Deduplication
    # --------------------------------------------------------------------------
    def record_webhook_delivery(self, delivery_id: str, tenant_id: str, event_type: str) -> bool:
        """Returns True if delivery_id is new, False if it is a duplicate replay."""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                INSERT INTO webhook_deliveries (delivery_id, tenant_id, event_type, created_at)
                VALUES (?, ?, ?, ?)
                """, (delivery_id, tenant_id, event_type, time.time()))
                return True
            except sqlite3.IntegrityError:
                return False
