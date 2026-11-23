"""Supply Chain & Geopolitical Disruption Domain for OmniSim.

Simulates the downstream impact of shipping delays, supplier insolvency,
raw material price spikes, and inventory stockouts.
"""

from __future__ import annotations

from typing import Tuple
from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.models.dynamics import WorldDynamicsModel


def build_supply_chain_scenario() -> Tuple[UniversalState, WorldDynamicsModel]:
    state = UniversalState(step=0)

    # 1. Tier 1 Semiconductor Supplier
    state.add_entity(Entity(
        id="supplier_fab",
        type="manufacturing_supplier",
        metrics={
            "output_units_per_day": 50_000.0,
            "lead_time_days": 14.0,
            "defect_rate": 0.002,
            "operational_health": 1.0,
        }
    ))

    # 2. Central Assembly Plant
    state.add_entity(Entity(
        id="assembly_plant",
        type="manufacturing_plant",
        metrics={
            "inventory_buffer_days": 10.0,
            "production_rate_daily": 45_000.0,
            "operating_cost_daily": 350_000.0,
            "backlog_units": 0.0,
        }
    ))

    # 3. Finished Goods Distribution Network
    state.add_entity(Entity(
        id="distribution_network",
        type="logistics",
        metrics={
            "customer_order_demand": 42_000.0,
            "fulfillment_rate": 1.0,
            "stockout_penalty_daily": 0.0,
        }
    ))

    # Relational Causal Flow
    state.add_relation("supplier_fab", "assembly_plant", "supply_input", weight=1.0)
    state.add_relation("assembly_plant", "distribution_network", "distribution_flow", weight=1.0)

    # Invariants
    state.add_invariant(Invariant(
        name="Zero Assembly Plant Stoppage",
        target_entity="assembly_plant",
        metric="inventory_buffer_days",
        operator=">=",
        threshold=2.0,
        severity="CRITICAL",
        description="Assembly plant shuts down if buffer drops below 2 days."
    ))

    state.add_invariant(Invariant(
        name="Order Fulfillment SLA",
        target_entity="distribution_network",
        metric="fulfillment_rate",
        operator=">=",
        threshold=0.95,
        severity="WARNING",
        description="Order fulfillment must stay above 95%."
    ))

    dynamics = WorldDynamicsModel()

    def supply_chain_physics(st: UniversalState, act: Action):
        fab = st.entities.get("supplier_fab")
        plant = st.entities.get("assembly_plant")
        dist = st.entities.get("distribution_network")
        if not fab or not plant or not dist:
            return

        # Lead time delays burn through inventory buffer
        fab_health = fab.metrics.get("operational_health", 1.0)
        lead_time = fab.metrics.get("lead_time_days", 14.0)

        daily_burn = 1.0  # Burns 1 day of inventory per day
        daily_replenish = (fab_health * 14.0) / max(lead_time, 1.0)
        net_buffer_change = daily_replenish - daily_burn

        plant.metrics["inventory_buffer_days"] = max(0.0, plant.metrics["inventory_buffer_days"] + net_buffer_change)

        # If inventory reaches zero, fulfillment drops
        if plant.metrics["inventory_buffer_days"] <= 0.0:
            dist.metrics["fulfillment_rate"] = 0.2
            dist.metrics["stockout_penalty_daily"] = 500_000.0
        elif plant.metrics["inventory_buffer_days"] < 3.0:
            dist.metrics["fulfillment_rate"] = 0.75
        else:
            dist.metrics["fulfillment_rate"] = 1.0

    dynamics.register_transition_hook(supply_chain_physics)
    return state, dynamics
