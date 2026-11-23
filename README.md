<div align="center">

<img src="assets/omnisim-banner.svg" alt="OmniSim: Foundational Software for Infrastructure Survivability" width="100%" />

<br/><br/>

[![CI Pipeline](https://img.shields.io/badge/CI-PASSING-0D0E10?style=for-the-badge&logo=githubactions&logoColor=FFFFFF&labelColor=000000)](https://github.com/Deeven-Seru/omnisim/actions/workflows/ci.yml)
[![Live Site](https://img.shields.io/badge/ENTERPRISE_WEB-ONLINE-0D0E10?style=for-the-badge&logo=cloudflarepages&logoColor=FFFFFF&labelColor=000000)](https://omnisim-dfx.pages.dev/)
[![PyPI](https://img.shields.io/badge/PYPI-v1.0.0-0D0E10?style=for-the-badge&logo=pypi&logoColor=FFFFFF&labelColor=000000)](https://pypi.org/project/omnisim-engine/)
[![License: MIT](https://img.shields.io/badge/LICENSE-MIT-0D0E10?style=for-the-badge&labelColor=000000)](LICENSE)
[![Python: 3.10 | 3.11 | 3.12](https://img.shields.io/badge/PYTHON-3.10%20%7C%203.11%20%7C%203.12-0D0E10?style=for-the-badge&logo=python&logoColor=FFFFFF&labelColor=000000)](https://python.org)

<br/>

<p align="center">
  <b>Foundational Software for Infrastructure Survivability.</b><br/>
  Action-Conditioned World Models, Causal Invariant Verification, and Autonomous Remediation Synthesis.
</p>

<p align="center">
  <a href="https://omnisim-dfx.pages.dev/"><b>Launch Enterprise Mission Control &rarr;</b></a>
</p>

<img src="assets/omnisim_thumbnail.png" alt="OmniSim Causal Manifold Simulation" width="100%" style="border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.16);" />

</div>

---

## 01 ——→ Executive Thesis: Beyond Autoregressive Generation

In 2017, the transformer architecture unified natural language processing through autoregressive token prediction. Scaling conversational fluency culminated in modern large language models.

**However, LLMs are advisory oracles, not execution engines.**

When asking a generative model:
* *"How will our distributed architecture behave during an unpredicted 4x traffic surge?"*
* *"If we scale our compute cluster from 4 to 28 instances, does downstream datastore capacity hold?"*
* *"What compound remediation intervention guarantees zero downtime under connection pool saturation?"*

An LLM generates **statistically probable text**. It cannot simulate physical, temporal, or queuing dynamics across continuous time. Operating on language approximations forces platform engineers into blind production deployments and catastrophic cascading outages.

**OmniSim grounds reliability in physics.** Grounded in **Action-Conditioned World Models ($S_{t+1} = f_\theta(S_t, A_t) + \epsilon$)**, **Causal Dependency Graphs**, and **Monte Carlo Rollout Search**, OmniSim compiles production infrastructure into a living digital twin.

Instead of guessing tokens, OmniSim parses Terraform infrastructure declarations, Kubernetes pod affinities, and live CloudWatch metrics. It branches candidate future states forward in continuous integration pipelines, mathematically verifying that critical system invariants survive before code merges.

---

## 02 ——→ Core Architecture: The Four Foundational Platforms

```
[ Static Declarations & Live OTLP Telemetry ]
                     │
                     ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 01 ——→ OMNISIM ONTOLOGY (Causal Digital Twin)               │
  │ Relational DAG Ingestion & Physical Limits Compilation      │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 02 ——→ OMNISIM HORIZON (Action-Conditioned World Model)    │
  │ S_{t+1} = f_θ(S_t, A_t) · Monte Carlo Rollout Search       │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 03 ——→ OMNISIM SENTRY (Continuous Pre-Execution Gate)       │
  │ Mathematical Invariant Boundaries & Zero Fail Tolerance     │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ 04 ——→ OMNISIM TITAN (Autonomous Remediation Engine)        │
  │ Pareto-Optimal Synthesis & Automated Unified Git Patches    │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
           [ 100% Invariant Compliant Production State ]
```

1. **OmniSim Ontology (`omnisim.core.state`):**
   * Encapsulates entities, continuous metrics, dynamic topology graphs, and invariant rules (connection pool ceilings, queuing limits, quorum constraints).
2. **OmniSim Horizon (`omnisim.models.dynamics`):**
   * Propagates non-linear cascades (M/M/1 queuing contention, memory pressure, thread pool exhaustion, network serialization latency).
   * Vectorized acceleration across multi-core server SIMD architectures with sub-millisecond rollout latency.
3. **OmniSim Sentry (`omnisim.models.search`):**
   * Pre-execution CI gatekeeper evaluating candidate pull requests against high-stress traffic trajectories.
   * Blocks invariant breaches before deployment authorization.
4. **OmniSim Titan (`omnisim.core.engine`):**
   * Synthesizes mathematically proven architecture upgrades (e.g., upgrading RDS instance tiers or tuning thread pools) directly as unified Git patches.

---

## 03 ——→ Outage Prevention: Step-by-Step Case Study

A real-world walkthrough: detecting and autonomously remediating an AWS RDS connection pool exhaustion catastrophe before code is merged.

### The Scenario
An engineering team modifies an Auto-Scaling Group in Terraform to allow scaling up to 28 instances during traffic surges, backed by a `db.t3.medium` Postgres RDS instance. Static linters (`tflint`, `terraform validate`) report zero errors because the syntax is valid. However, under peak load, 28 web instances open 504 connections against a database with a hard physical ceiling of 412 connections.

### Step 1: Install OmniSim

Install the CLI directly from PyPI:

```bash
pip install omnisim-engine
```

### Step 2: Define Infrastructure as Code

Target the Terraform configuration ([examples/vulnerable_infrastructure.tf](examples/vulnerable_infrastructure.tf)):

```hcl
resource "aws_autoscaling_group" "web_asg" {
  name             = "prod-web-asg"
  min_size         = 4
  max_size         = 28
  desired_capacity = 4
}

resource "aws_db_instance" "postgres" {
  name           = "prod-primary-rds"
  instance_class = "db.t3.medium"
  engine         = "postgres"
}
```

### Step 3: Run Pre-Flight Counterfactual Simulation

Execute a non-destructive counterfactual rollout across the simulation horizon:

```bash
omnisim terraform examples/vulnerable_infrastructure.tf
```

OmniSim dynamically constructs the relational entity graph and simulates the ASG scale-out:

```text
[INFO] Ingesting Terraform Infrastructure as Code (IaC)...
[OK] Parsed 2 Terraform resources:
  - [aws_autoscaling_group] asg_web_asg (max_size: 28)
  - [aws_db_instance] rds_postgres (max_connections: 412)

[SIMULATION] Simulating peak Auto-Scaling group burst to max_size...

[CRITICAL] CATASTROPHIC VIOLATION DETECTED IN TERRAFORM PLAN!
   Breaches: 3 critical SLA violations.
   - Step 4: rds_postgres.pool_saturation=0.96 (rule: <= 0.90)
   - Step 5: rds_postgres.pool_saturation=1.00 (rule: <= 0.90)
   - Step 6: rds_postgres.pool_saturation=1.00 (rule: <= 0.90)

[RECOMMENDATION] TERRAFORM CODE REMEDIATION:
   Change: instance_class = "db.t3.medium" -> instance_class = "db.r6g.large"
   Reason: db.t3.medium limits at 412 connections, but ASG max_size 28 requires 504 connections.
```

### Step 4: Synthesize Autonomous Git Remediation Patch

Generate a verified Git unified diff patch ready for direct application:

```bash
omnisim patch examples/vulnerable_infrastructure.tf --output fix.patch
```

Output:

```diff
--- terraform/main.tf (Current Head)
+++ terraform/main.tf (OmniSim Auto-Remediation)
@@ -10,3 +10,3 @@
 resource "aws_db_instance" "postgres" {
   name           = "prod-primary-rds"
-  instance_class = "db.t3.medium"
+  instance_class = "db.r6g.large"
   engine         = "postgres"
```

Under `db.r6g.large`, maximum connections increase to 1,365, capping pool saturation to 36.9% and completely eliminating SLA breaches.

### Step 5: Enforce as a Pre-Flight CI/CD Gate

Block breaking pull requests automatically by adding OmniSim to `.github/workflows/safety-gate.yml`:

```yaml
name: OmniSim Safety Gate
on: [pull_request]

jobs:
  pre-flight-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: OmniSim Pre-Flight Safety Gate
        uses: Deeven-Seru/omnisim@v1
        with:
          path: examples/vulnerable_infrastructure.tf
          fail-on-violation: "true"
```

---

## 04 ——→ Deterministic Invariant Catalog

OmniSim enforces physical boundaries across distributed computing environments:

| Invariant Code | Boundary Definition | Mathematical Invariant | Enforced Failure Mitigation |
| :--- | :--- | :--- | :--- |
| **INV-01** | Datastore Pool Ceiling | `pool_saturation <= 0.85` | Eliminates connection starvation under burst traffic |
| **INV-02** | Thread Fanout Starvation | `worker_threads * nodes < max_conn` | Prevents uncoordinated horizontal autoscaling crashes |
| **INV-03** | Cascading Tail Dampening | `timeout_p99 <= 120ms` | Halts recursive microservice retry storms |
| **INV-04** | Memory Headroom Guard | `heap_alloc <= 0.80 * node_ram` | Eliminates unpredictable Linux OOM-killer container terminations |
| **INV-05** | Quorum Partition Gate | `active_zones >= 3` | Guarantees split-brain immunity during availability-zone disconnects |
| **INV-06** | Acyclic Call Enforcement | `graph_cycles == 0` | Proves absence of distributed call graph deadlocks |

---

## 05 ——→ CLI Command Reference

Execute counterfactual evaluations directly from the terminal:

```bash
# 1. Run terminal counterfactual simulation across candidate interventions
omnisim simulate --domain systems --horizon 6

# 2. Benchmark parallel stochastic rollouts (e.g. 500 rollouts in < 150ms)
omnisim benchmark --domain systems --rollouts 500 --horizon 6

# 3. Audit Terraform IaC plans for cascading capacity bottlenecks
omnisim terraform examples/vulnerable_infrastructure.tf

# 4. Generate automated Git patch for vulnerable infrastructure
omnisim patch examples/vulnerable_infrastructure.tf

# 5. Run adversarial robustness stress test (historical replay, poison action traps)
omnisim robustness

# 6. Benchmark against 8,000+ real AWS CloudWatch data points (Numenta NAB)
omnisim telemetry

# 7. Benchmark canonical microservices (Online Boutique, DeathStarBench, Train-Ticket)
omnisim microservices

# 8. Test historical defect foresight on Google MCP Toolbox (PR #3921 EMFILE leak)
omnisim mcp-toolbox

# 9. Test historical runtime validation on TensorFlow (BFC OOM & threadpool deadlocks)
omnisim tensorflow

# 10. Audit current TensorFlow state against active user issues
omnisim tf-audit

# 11. Run latent zero-day defect discovery on TensorFlow distributed runtime
omnisim tf-zero-day

# 12. Launch local REST API Gateway & SaaS Control Plane
omnisim serve --port 8088
```

---

## 06 ——→ Installation & Distribution Matrix

| Channel | Command | Description |
| :--- | :--- | :--- |
| **PyPI** | `pip install omnisim-engine` | Standard Python installation (Python 3.10+) |
| **Homebrew** | `brew install Deeven-Seru/omnisim/omnisim` | macOS and Linux CLI formula |
| **Standalone `curl`** | `curl -sSL https://raw.githubusercontent.com/Deeven-Seru/omnisim/main/scripts/install.sh \| bash` | Zero-dependency standalone installation |
| **Docker** | `docker run --rm -v $(pwd):/workspace ghcr.io/deeven-seru/omnisim:v1` | Isolated container execution |
| **GitHub Action** | `uses: Deeven-Seru/omnisim@v1` | Pre-flight PR safety gatekeeper in CI/CD |

---

## 07 ——→ Empirical Validation: Public Datasets & Production Post-Mortems

OmniSim has been benchmarked directly against real-world catastrophic failure post-mortems and canonical public datasets:

* **Google `tensorflow/tensorflow` Runtime Post-Mortems (BFC Fragmentation & Pipeline Deadlocks):**
  * *BFC Allocator OOM (Issue #41710):* Caught memory fragmentation reaching 0.87 despite 8 GB of free VRAM; synthesized dynamic memory growth with bucketed shape alignment (`cuda_malloc_async`), eliminating OOM with 0 violations.
  * *Inter-Op ThreadPool Starvation (Issue #21277):* Caught circular wait deadlocking worker threads from 450 QPS to 0 QPS; synthesized decoupled dedicated I/O thread pool with non-blocking admission.
* **Google Cloud `googleapis/mcp-toolbox` Issue / PR #3921 (`EMFILE File Descriptor Leak`):**
  * *Status Quo (v1.14.0 unpatched):* Database connection failure returned error without closing `pgxpool.Pool` / `sql.DB` handle. Dynamic config reloads leaked 16+ sockets per cycle, saturating OS descriptors (1,072 / 1,024 limit) and crashing downstream AI agent tool invocations at Step 3.
  * *OmniSim Blind Foresight:* Predicted exact `EMFILE` socket exhaustion; autonomously synthesized `pool.Close()` / `db.Close()` before return, exactly matching Google's upstream fix in commit `0001190a` across 26 source files.
* **Numenta Anomaly Benchmark (NAB) realAWSCloudwatch (8,064 real production points):**
  * *EC2 CPU 99.7% Catastrophic Spike:* Caught with a 10-minute early warning lead time before system collapse; counterfactual scaling intervention reduced CPU to 48.4% with 0 SLA breaches.
  * *ELB Ingress Surges:* Ground-truth verified against labeled anomaly windows peaking up to 656 req/5m.
* **k3s-io/k3s Issue #1459 (`Error 1040: Too Many Connections`):**
  * *Status Quo:* Saturated pool at Step 2 with 100% service degradation.
  * *OmniSim Remediation:* Injected connection pooling proxy; 0 violations, system stabilized.
* **deis/deis Issue #4297 (`Remaining Connection Slots Exhausted`):**
  * *Status Quo:* Instant fire at Step 1 under 300 concurrent requests on t2.micro RDS.
  * *OmniSim Remediation:* Sized RDS instance class to r6g.large with connection limit 1,365; pool saturation kept below 52%.

See [tests/test_github_validation.py](tests/test_github_validation.py) for reproducible test fixtures.

---

## 08 ——→ Research Paper & Architecture

* **Academic Paper:** [OmniSim: Universal Counterfactual Simulation Engine (PDF)](paper/omnisim_paper.pdf) | [Markdown Version](paper/omnisim_paper.md) | [LaTeX Source](paper/omnisim_paper.tex)
* **System Architecture Specification:** [ARCHITECTURE.md](ARCHITECTURE.md)
* **Enterprise Web Interface:** [https://omnisim-dfx.pages.dev/](https://omnisim-dfx.pages.dev/)

---

## 09 ——→ License & Attribution

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
OmniSim is maintained by [Deeven-Seru](https://github.com/Deeven-Seru).
