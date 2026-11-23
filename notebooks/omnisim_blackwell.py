# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "marimo",
#     "numpy",
#     "matplotlib",
# ]
# ///

import marimo

__generated_with = "0.8.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import sys
    from pathlib import Path
    
    # Ensure omnisim package is in path
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        
    mo.md(
        r"""
        # 🌐 OmniSim: Universal Counterfactual Simulation Engine
        ### *Beyond Autoregressive Token Prediction to Action-Conditioned World Simulation*
        
        Accelerated for **NVIDIA Blackwell / Hopper GPUs, Apple Silicon MPS, & Multi-Cloud Clusters**
        """
    )
    return Path, mo, project_root, sys


@app.cell
def __(mo):
    from omnisim.domains.systems import build_cloud_systems_scenario
    from omnisim.core.action import Action, InterventionType
    from omnisim.models.search import CounterfactualMCTS
    from omnisim.core.trajectory import ConsequenceReport
    
    mo.md("### 1. Configure Simulation Parameters & Counterfactual Interventions")
    return (
        Action,
        ConsequenceReport,
        CounterfactualMCTS,
        InterventionType,
        build_cloud_systems_scenario,
    )


@app.cell
def __(mo):
    traffic_slider = mo.ui.slider(start=0.5, stop=3.0, step=0.1, value=1.0, label="Traffic Surge Multiplier")
    horizon_slider = mo.ui.slider(start=4, stop=16, step=1, value=8, label="Simulation Horizon (Steps)")
    db_scale_slider = mo.ui.slider(start=1.0, stop=3.0, step=0.25, value=1.5, label="Intervention: DB Pool Scale Factor")
    gw_instances_slider = mo.ui.slider(start=4, stop=16, step=2, value=8, label="Intervention: Gateway Instances")
    
    mo.vstack([
        mo.md("**Environment & Intervention Controls:**"),
        traffic_slider,
        horizon_slider,
        gw_instances_slider,
        db_scale_slider,
    ])
    return (
        db_scale_slider,
        gw_instances_slider,
        horizon_slider,
        traffic_slider,
    )


@app.cell
def __(
    Action,
    ConsequenceReport,
    CounterfactualMCTS,
    InterventionType,
    build_cloud_systems_scenario,
    db_scale_slider,
    gw_instances_slider,
    horizon_slider,
    traffic_slider,
):
    # Initialize World Model
    state, dynamics = build_cloud_systems_scenario(traffic_scale=traffic_slider.value)
    horizon = int(horizon_slider.value)
    
    # Candidate Actions based on sliders
    action_gateway = Action(
        name=f"Autoscale Gateway ({int(gw_instances_slider.value)} inst)",
        intervention_type=InterventionType.PARAM_TUNE,
        target_entity="api_gateway",
        parameters={"active_instances": float(gw_instances_slider.value)},
        cost=150.0,
    )
    
    action_db = Action(
        name=f"Scale DB Pool ({db_scale_slider.value}x)",
        intervention_type=InterventionType.SCALE,
        target_entity="database_cluster",
        parameters={"metric": "capacity", "factor": float(db_scale_slider.value)},
        cost=120.0,
    )
    
    planner = CounterfactualMCTS(dynamics, [action_gateway, action_db], horizon=horizon)
    
    # Baseline
    b_traj = planner.simulate_trajectory(state, [Action.no_op()] * horizon, name="Status Quo (No Intervention)")
    
    # Trajectories
    t_gw = planner.simulate_trajectory(state, [action_gateway] + [Action.no_op()] * (horizon - 1), name=action_gateway.name)
    t_db = planner.simulate_trajectory(state, [action_db] + [Action.no_op()] * (horizon - 1), name=action_db.name)
    
    # Compound Intervention
    t_both = planner.simulate_trajectory(state, [action_gateway, action_db] + [Action.no_op()] * (horizon - 2), name="Combined Gateway + DB Scale")
    t_both.total_cost = action_gateway.cost + action_db.cost
    
    candidates = [t_gw, t_db, t_both]
    best_candidate = next((t for t in candidates if t.is_valid), None)
    rec = f"Optimal Execution: '{best_candidate.name}' prevents all cascading failures." if best_candidate else "CRITICAL: System collapses under current parameters."
    
    report = ConsequenceReport(
        baseline_trajectory=b_traj,
        counterfactual_trajectories=candidates,
        horizon=horizon,
        recommendation=rec
    )
    return (
        action_db,
        action_gateway,
        b_traj,
        best_candidate,
        candidates,
        dynamics,
        horizon,
        planner,
        rec,
        report,
        state,
        t_both,
        t_db,
        t_gw,
    )


@app.cell
def __(mo, report):
    summary_text = report.generate_executive_summary()
    mo.md(f"```text\n{summary_text}\n```")
    return (summary_text,)


if __name__ == "__main__":
    app.run()
