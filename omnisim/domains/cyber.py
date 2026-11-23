"""Cyber-Resilience & Attack Blast-Radius Domain for OmniSim.

Simulates cyberattack lateral movement (ransomware, credential theft, zero-day)
and evaluates counterfactual defensive responses (microsegmentation, quarantine).
"""

from __future__ import annotations

from typing import Tuple
from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.models.dynamics import WorldDynamicsModel


def build_cyber_resilience_scenario() -> Tuple[UniversalState, WorldDynamicsModel]:
    state = UniversalState(step=0)

    # 1. DMZ / Edge Web Ingress
    state.add_entity(Entity(
        id="dmz_ingress",
        type="network_zone",
        metrics={
            "compromise_level": 0.85,  # Breach detected at edge!
            "active_connections": 1200.0,
            "isolated": 0.0,
        }
    ))

    # 2. Internal Microservice Cluster
    state.add_entity(Entity(
        id="internal_cluster",
        type="network_zone",
        metrics={
            "compromise_level": 0.0,
            "lateral_vulnerability": 0.65,
            "isolated": 0.0,
        }
    ))

    # 3. Core Customer Data Vault
    state.add_entity(Entity(
        id="customer_vault",
        type="data_vault",
        metrics={
            "compromise_level": 0.0,
            "encryption_lockout": 0.0,
            "data_exfiltration_rate": 0.0,
        }
    ))

    # Attack Vectors (Lateral Paths)
    state.add_relation("dmz_ingress", "internal_cluster", "network_path", weight=0.8)
    state.add_relation("internal_cluster", "customer_vault", "network_path", weight=0.6)

    # Invariant: Zero Data Vault Exfiltration or Compromise
    state.add_invariant(Invariant(
        name="Customer Data Vault Integrity",
        target_entity="customer_vault",
        metric="compromise_level",
        operator="<=",
        threshold=0.01,
        severity="CRITICAL",
        description="Customer Data Vault cannot suffer compromise or ransomware encryption."
    ))

    dynamics = WorldDynamicsModel()

    def attack_propagation(st: UniversalState, act: Action):
        dmz = st.entities.get("dmz_ingress")
        cluster = st.entities.get("internal_cluster")
        vault = st.entities.get("customer_vault")
        if not dmz or not cluster or not vault:
            return

        # If DMZ is not isolated, attack jumps to internal cluster
        if dmz.metrics.get("isolated", 0.0) == 0.0:
            jump_rate = dmz.metrics.get("compromise_level", 0.0) * 0.45
            cluster.metrics["compromise_level"] = min(1.0, cluster.metrics.get("compromise_level", 0.0) + jump_rate)

        # If internal cluster is compromised and not isolated, jumps to vault
        if cluster.metrics.get("isolated", 0.0) == 0.0 and cluster.metrics.get("compromise_level", 0.0) > 0.3:
            vault_jump = cluster.metrics.get("compromise_level", 0.0) * 0.5
            vault.metrics["compromise_level"] = min(1.0, vault.metrics.get("compromise_level", 0.0) + vault_jump)
            if vault.metrics["compromise_level"] > 0.5:
                vault.metrics["data_exfiltration_rate"] = 1000.0  # MB/s

    dynamics.register_transition_hook(attack_propagation)
    return state, dynamics
