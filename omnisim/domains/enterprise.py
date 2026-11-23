"""Enterprise Economics & Strategy Domain for OmniSim.

Simulates the causal downstream impact of pricing interventions,
customer acquisition cost (CAC), churn rate, and runway.
"""

from __future__ import annotations

from typing import Tuple
from omnisim.core.action import Action, InterventionType
from omnisim.core.state import Entity, Invariant, UniversalState
from omnisim.models.dynamics import WorldDynamicsModel


def build_enterprise_strategy_scenario() -> Tuple[UniversalState, WorldDynamicsModel]:
    """Constructs a high-growth SaaS business model."""
    state = UniversalState(step=0)

    # 1. Product Pricing & Demand
    state.add_entity(Entity(
        id="saas_product",
        type="commercial_offering",
        metrics={
            "price": 100.0,              # Monthly price per seat ($)
            "customers": 2000.0,
            "monthly_churn_pct": 0.03,    # 3% baseline monthly churn
            "nps_satisfaction": 65.0,
        },
        properties={
            "base_price": 100.0,
        }
    ))

    # 2. Financial Balance Sheet
    state.add_entity(Entity(
        id="balance_sheet",
        type="finance",
        metrics={
            "cash_reserves": 1_200_000.0, # $1.2M cash
            "monthly_burn_rate": 80_000.0,
            "mrr": 200_000.0,             # 2000 * 100
            "runway_months": 15.0,
        }
    ))

    # Relations
    state.add_relation("saas_product", "balance_sheet", "price_elasticity", weight=-1.2)

    # Invariants
    state.add_invariant(Invariant(
        name="Solvency Runway Floor",
        target_entity="balance_sheet",
        metric="cash_reserves",
        operator=">=",
        threshold=250_000.0,
        severity="CRITICAL",
        description="Cash reserves must not breach safety buffer of $250k."
    ))

    state.add_invariant(Invariant(
        name="Max Customer Churn",
        target_entity="saas_product",
        metric="monthly_churn_pct",
        operator="<=",
        threshold=0.08,
        severity="WARNING",
        description="Monthly churn should not exceed 8%."
    ))

    dynamics = WorldDynamicsModel()

    def economics_hook(st: UniversalState, act: Action):
        prod = st.entities.get("saas_product")
        fin = st.entities.get("balance_sheet")
        if not prod or not fin:
            return

        # Price elasticity dynamic
        price = prod.metrics["price"]
        base_p = prod.properties.get("base_price", 100.0)
        p_ratio = price / base_p

        # Price hikes increase churn
        if p_ratio > 1.0:
            hike = p_ratio - 1.0
            prod.metrics["monthly_churn_pct"] = 0.03 + (hike * 0.15)
        else:
            prod.metrics["monthly_churn_pct"] = max(0.015, 0.03 + (p_ratio - 1.0) * 0.05)

        # Churn reduces customer base, new organic adds 5%
        churn = prod.metrics["monthly_churn_pct"]
        net_cust = prod.metrics["customers"] * (1.0 - churn + 0.04)
        prod.metrics["customers"] = max(0.0, net_cust)

        # Recalculate MRR and cash balance
        mrr = prod.metrics["customers"] * price
        fin.metrics["mrr"] = mrr
        net_burn = fin.metrics["monthly_burn_rate"] - (mrr * 0.3)  # Net contribution
        fin.metrics["cash_reserves"] -= net_burn

    dynamics.register_transition_hook(economics_hook)
    return state, dynamics
