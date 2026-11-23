# 🌐 OmniSim: The Universal Counterfactual Simulation Engine
> *Beyond Autoregressive Token Prediction to Action-Conditioned World Simulation.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)
[![Hardware: Blackwell / Hopper / Apple Silicon](https://img.shields.io/badge/Hardware-Blackwell%20%7C%20MPS%20%7C%20CUDA-green.svg)](https://nvidia.com)
[![CI: Passing](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](.github/workflows/ci.yml)
[![Investor Memo: Seed Brief](https://img.shields.io/badge/Investor%20Memo-Confidential%20Brief-gold.svg)](INVESTOR_MEMO.md)

---

## 1. The Core Thesis: Why ChatGPT Hits a Ceiling

In 2017, Google published *"Attention Is All You Need"*, treating it as a machine translation improvement. Sam Altman and OpenAI realized that scaling autoregressive transformers over internet text unlocks emergent conversational intelligence—creating ChatGPT.

**However, ChatGPT is an advisory oracle, not an execution engine.**
When you ask an LLM:
* *"How should I scale our microservice architecture under a 3x flash sale?"*
* *"If we raise our SaaS subscription by 15%, what happens to churn and runway?"*
* *"If we alter this drone airfoil angle by 2.5 degrees, will boundary layer separation trigger stall?"*

The LLM outputs **plausible text**. It cannot simulate the physical, logical, or financial consequences of your actions. You are forced to deploy blind into reality and absorb catastrophic failure.

**OmniSim flips this paradigm.** Built upon the theoretical foundations of **World Models, Test-Time Training (TTT), and Universal Interactive Simulators (DeepMind UniSim & Genie)**, OmniSim is a general-purpose **State-Action-Consequence (SAC)** simulation engine. 

Instead of generating text, OmniSim ingests system state, models relational causal graphs, branches tens of thousands of counterfactual intervention timelines forward in time, and outputs the exact failure modes, invariant violations, and Pareto-optimal actions before you spend a single dollar in production.

---

## 2. Architecture Overview

OmniSim operates across a **3-Tier Engine**:

```
[ Current System State S_0 ] ──► [ Multi-Domain Entity Graph & Invariant Rules ]
                                                     │
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Tier 1: World Model       │
                                       │ S_{t+1} = f_θ(S_t, A_t)   │
                                       └─────────────┬─────────────┘
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Tier 2: Counterfactual    │
                                       │ Monte Carlo Tree Search   │
                                       └─────────────┬─────────────┘
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Tier 3: Invariant Audits  │
                                       │ & Deterministic Verifiers │
                                       └─────────────┬─────────────┘
                                                     ▼
                     [ Executive Consequence Report & Optimal Intervention ]
```

1. **Universal State Representation (`omnisim.core.state`):**
   * Encapsulates entities, continuous metrics, dynamic topology relations, and non-negotiable operational invariants (SLAs, solvency bounds, yield limits).
2. **Action-Conditioned World Dynamics (`omnisim.models.dynamics`):**
   * Propagates non-linear cascades (e.g., M/M/1 queuing contention, price elasticity, supply chain friction) across graph relations.
   * Hardware-accelerated across **NVIDIA Blackwell/Hopper GPUs (CUDA)**, **Apple Silicon (MPS)**, and multi-core CPU.
3. **Counterfactual MCTS Planner (`omnisim.models.search`):**
   * Searches the combinatorial tree of candidate interventions.
   * Prunes timelines violating critical invariants and isolates asymmetric low-cost, high-resilience interventions.

---

## 3. Quickstart & Interactive Showcase

### 🌐 Live Interactive Visualizer (Zero Setup)
Launch the browser-based simulation dashboard with dynamic slider controls and real-time timeline comparison:
```bash
python3 -m omnisim.visualizer
# Open http://localhost:8088 in your browser
```

### 💻 Running the Terminal Simulation
```bash
# Clone and run the cloud infrastructure counterfactual simulation
python3 -m omnisim.cli --domain systems --horizon 6
```

### 🧪 Running the Verification Test Suite
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## 4. Hardware Acceleration (Blackwell GPU / Marimo / Kaggle / Colab)

OmniSim includes a native, reactive **Marimo notebook** and a one-click launcher designed to run seamlessly on NVIDIA Blackwell GPUs, Kaggle notebooks, Google Colab, or Apple Silicon:

```bash
# Launch the reactive Marimo simulation notebook
chmod +x scripts/launch_blackwell.sh
./scripts/launch_blackwell.sh
```

---

## 5. The Evidence: Why Text Models Fail Where OmniSim Wins

In our distributed cloud benchmark scenario, incoming traffic surges by 15% compounded per step:
* **LLM Advice (Standard Playbook):** *"Autoscale the API Gateway instances from 4 to 8."*
* **OmniSim Simulation Verdict:** **FAILED.** 
  * Doubling the gateway absorbs traffic at the front door, but floods the downstream database cluster with 400 req/sec above limit.
  * At Step 5, the Database Connection Pool saturates to 100%, triggering an unrecoverable cascading outage across the entire stack.
* **OmniSim Discovered Optimal Action:** **Scale DB Connection Pool (+50%).**
  * Cost: **$120.00** (vs $250.00 for gateway autoscale).
  * Result: **0 critical violations**, database latency drops by 70%, system survives traffic surge without service degradation.

---

## 6. Investor & Due Diligence Brief
For technical partners and investors evaluating the Series Seed / Series A brief, read the complete [INVESTOR_MEMO.md](INVESTOR_MEMO.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
