"""Distributed Cloud & Systems Domain for OmniSim.

Simulates cascading failures across API Gateways, Microservices,
Distributed Caches, and DB connection pools under stress and interventions.
"""

from __future__ import annotations

from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.models.dynamics import WorldDynamicsModel


def build_cloud_systems_scenario(traffic_scale: float = 1.0) -> Tuple[UniversalState, WorldDynamicsModel]:
    """Constructs a distributed cloud microservices system."""
    state = UniversalState(step=0)

    # 1. API Gateway
    state.add_entity(Entity(
        id="api_gateway",
        type="gateway",
        metrics={
            "load": 1000.0 * traffic_scale,  # req/sec
            "capacity": 2000.0,
            "latency_ms": 12.0,
            "base_latency_ms": 10.0,
            "error_rate": 0.0,
            "active_instances": 4.0,
        }
    ))

    # 2. Auth Service
    state.add_entity(Entity(
        id="auth_service",
        type="microservice",
        metrics={
            "load": 1000.0 * traffic_scale,
            "capacity": 1500.0,
            "latency_ms": 8.0,
            "base_latency_ms": 5.0,
            "error_rate": 0.0,
            "active_instances": 3.0,
        }
    ))

    # 3. Core Database Cluster
    state.add_entity(Entity(
        id="database_cluster",
        type="database",
        metrics={
            "load": 400.0 * traffic_scale,
            "capacity": 800.0,
            "latency_ms": 25.0,
            "base_latency_ms": 15.0,
            "error_rate": 0.0,
            "connection_pool_usage": 0.50 * traffic_scale,  # 0.0 - 1.0
        }
    ))

    # Relations (Dependency Network)
    state.add_relation("api_gateway", "auth_service", "traffic_flow", weight=1.0)
    state.add_relation("auth_service", "database_cluster", "traffic_flow", weight=0.4)

    # Invariants (Non-negotiable operational SLAs)
    state.add_invariant(Invariant(
        name="Gateway Latency SLA",
        target_entity="api_gateway",
        metric="latency_ms",
        operator="<=",
        threshold=150.0,
        severity="CRITICAL",
        description="P99 Gateway latency must remain under 150ms."
    ))

    state.add_invariant(Invariant(
        name="Database Pool Saturation",
        target_entity="database_cluster",
        metric="connection_pool_usage",
        operator="<=",
        threshold=0.90,
        severity="CRITICAL",
        description="DB connection pool cannot exceed 90% without exhausting sockets."
    ))

    state.add_invariant(Invariant(
        name="System Zero Error Rate",
        target_entity="api_gateway",
        metric="error_rate",
        operator="<=",
        threshold=0.01,
        severity="CRITICAL",
        description="Error rate must remain below 1%."
    ))

    # Dynamics Model with Traffic Surge Physics
    dynamics = WorldDynamicsModel()

    def cloud_physics(st: UniversalState, act: Action):
        # Background organic traffic progression (e.g. flash-sale ramp up)
        gw = st.entities.get("api_gateway")
        db = st.entities.get("database_cluster")
        if gw:
            # Load grows by 15% every step unless capped
            gw.metrics["load"] *= 1.15
            # Active instances determine capacity
            inst = gw.metrics.get("active_instances", 4.0)
            gw.metrics["capacity"] = inst * 500.0

        if db and gw:
            # DB connection pool scales with gateway traffic / db capacity
            gw_load = gw.metrics.get("load", 1000.0)
            db_cap = db.metrics.get("capacity", 800.0)
            db.metrics["connection_pool_usage"] = min(1.0, (gw_load * 0.4) / db_cap)
            if db.metrics["connection_pool_usage"] >= 0.95:
                db.metrics["error_rate"] = 0.8  # Connection timeout cascade!

    dynamics.register_transition_hook(cloud_physics)
    return state, dynamics
