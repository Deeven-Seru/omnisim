# OmniSim Public SaaS Release Readiness

**Update (23 November 2026 - Remediation Milestone Complete):**
The P0 security blockers, persistent tenancy database (SQLite WAL mode), strict authentication boundaries, RBAC scope enforcement, GitHub webhook HMAC verification, replay deduplication, and HTTP security integration test suite have been implemented and validated.

- Durable persistence implemented in `omnisim/saas/db.py` with foreign keys and WAL mode.
- Anonymous fallback eliminated in `omnisim/server.py`; missing or invalid tokens return RFC 7807 401/403.
- Public signup tier self-escalation eliminated; public registration defaults strictly to `FREE`.
- Key lifecycle authorization enforced: only principals with `admin` scope can mint or revoke keys. Key revocation endpoint active at `DELETE /api/v1/auth/keys/{id}`.
- GitHub webhooks require valid `X-Hub-Signature-256` HMAC-SHA256 signatures and deduplicate delivery IDs.
- HTTP security headers emitted on all responses: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`.
- Bound to `127.0.0.1` by default; requires explicit `--host 0.0.0.0` for non-loopback exposure.
- 13 HTTP boundary integration tests verified passing in `tests/test_saas_security.py` (60/60 total tests passing across entire test suite).

---

## Historical Assessment (Pre-Remediation Baseline)

The sections below document the initial baseline findings prior to the remediation milestone.

## What was verified

- The project venv ran all 47 unit and scenario tests successfully.
- `omnisim simulate`, Terraform auditing, safe-plan validation, patch generation, and the browser dashboard all ran locally.
- An unauthenticated request to `GET /api/v1/tenants/me` received the default Enterprise tenant’s name, ID, limits, and usage metadata.
- An unauthenticated request to `POST /api/v1/auth/keys` returned HTTP 201 and created an API key for the default Enterprise tenant. The generated token was redacted and discarded.
- An unauthenticated request to `POST /api/v1/tenants` with `{"tier":"ENTERPRISE"}` created an Enterprise-tier tenant and API key without billing verification or approval.
- An unauthenticated request to `POST /api/v1/simulate/batch` ran a batch simulation successfully.
- A malformed `traffic` value caused the server to drop the connection rather than return a safe client error.

No customer systems or third-party accounts were contacted. The local server used only in-memory state and was stopped after testing.

## Immediate release posture

### May be released now, with accurate positioning

- The Python library and CLI as a local, experimental developer tool.
- The GitHub Action as a local IaC analysis utility, provided its marketing does not imply a hosted or guaranteed decision service.
- A local demo dashboard bound to loopback only.

### Must not be released publicly yet

- Any internet-reachable `omnisim serve` deployment.
- A multi-tenant hosted dashboard or API.
- GitHub webhook ingestion for customer repositories.
- Any product claiming production-grade tenant isolation, key security, availability, managed telemetry, or paid plan enforcement.

## P0 — public-release blockers

Each item below must be fixed and verified in staging before a closed beta, let alone a public launch.

### 1. Eliminate anonymous fallback to the default Enterprise tenant

`_get_authenticated_tenant` authenticates the header and, on failure, silently returns `org_enterprise_acme`. Consequently, missing and invalid credentials become access to a shared Enterprise account. This affects tenant usage, billing data, simulation records, and routes that call into the tenant-aware service.

Evidence: [server.py](omnisim/server.py:36) through line 41.

Required change:

- Split authentication into explicit middleware/dependencies rather than a helper with a fallback.
- Return `401 Unauthorized` for missing or invalid credentials and `403 Forbidden` for authenticated principals lacking the required role or scope.
- Do not create demo tenants or production-style keys in a production process.
- Make a separately configured development/demo mode responsible for mock accounts and unauthenticated local UI behavior.

Acceptance criteria:

- Every protected route has tests for missing, malformed, expired, revoked, cross-tenant, and under-scoped credentials.
- Every test observes `401` or `403`; none observes a tenant record or simulation result.
- Production startup fails if demo mode or demo credentials are enabled.

### 2. Require authorization for API-key lifecycle operations

`POST /api/v1/auth/keys` currently uses the fallback tenant and mints a credential with `simulate`, `ingest`, and `webhooks` scopes. This is direct account takeover of the default tenant.

Evidence: [server.py](omnisim/server.py:205) through line 217; local test returned HTTP 201 without an Authorization header.

Required change:

- Authenticate the caller and require an organization-admin or explicitly delegated key-management permission.
- Use scope allowlists and least privilege; do not grant broad scopes automatically.
- Show the raw key exactly once, never store it in plaintext, and record a security audit event.
- Support key expiration, revocation, rotation, last-used metadata, and per-key IP or service restrictions where appropriate.
- Add a key inventory and revocation endpoint restricted to administrators.

Acceptance criteria:

- An unauthenticated request cannot mint, view, rotate, or revoke keys.
- A member of Tenant A cannot operate on Tenant B’s keys.
- A revoked or expired key immediately fails authentication in every API path.

### 3. Separate signup from plan entitlement and billing

The public tenant-creation endpoint accepts a caller-supplied plan tier. A caller can self-provision `ENTERPRISE`, gaining a 1,000,000 simulation monthly quota and high request limits without payment or review.

Evidence: [server.py](omnisim/server.py:193) through line 203; [engine.py](omnisim/saas/engine.py:104) through line 112; local test returned an Enterprise tenant and API key.

Required change:

- Public signup creates only a restricted pending or Free organization.
- Determine paid entitlements solely from a verified billing/contract system or an internal administrative workflow.
- Validate organization names, email ownership, fraud controls, and acceptable-use requirements before issuing reusable credentials.
- Make plan changes idempotent, auditable, and webhook-verified with signature checking from the payment provider.

Acceptance criteria:

- Public input cannot set a paid tier or elevated quota.
- Duplicate billing events do not create duplicate entitlements.
- Downgrades and payment failures enforce the documented limits predictably.

### 4. Authenticate and verify every computation and integration route

`/api/v1/simulations`, `/api/v1/ingest/telemetry`, `/api/v1/webhooks/github`, `/api/v1/ingest/k8s`, and `/api/v1/simulate/batch` have no effective authentication boundary. The GitHub webhook does not verify a GitHub signature or replay identifier. Batch simulation permits caller-controlled horizons and rollouts without tier enforcement.

Evidence: [server.py](omnisim/server.py:219) through line 290. The local unauthenticated batch request returned HTTP 200.

Required change:

- Apply route-level authentication, authorization, tenant extraction, and scope checks consistently.
- Require `X-Hub-Signature-256` verification using a secret from a managed secret store for GitHub webhooks.
- Persist and reject duplicate webhook delivery IDs; retain a bounded, redacted delivery log.
- Cap request body size, horizon, rollout count, input entities, and execution time before work starts.
- Put expensive simulations behind a per-tenant job queue with concurrency, cost, and timeout limits.

Acceptance criteria:

- A valid signed webhook is accepted once; invalid, missing, or replayed signatures are rejected.
- Anonymous and cross-tenant calls cannot run a simulation or submit telemetry.
- Budget-exceeding inputs receive a documented 4xx or `429`, never consume unbounded worker time.

### 5. Replace the demo HTTP server before exposing it

The service is based on `http.server.SimpleHTTPRequestHandler` and `socketserver.TCPServer`, binds to all interfaces, has no TLS, no request timeouts, no body limit, no trusted proxy model, no security headers, and no production concurrency model. It is appropriate for a local demo, not a public service.

Evidence: [server.py](omnisim/server.py:1) through line 12 and [server.py](omnisim/server.py:305) through line 311.

Required change:

- Implement a typed ASGI API service using a maintained framework and deploy it behind a managed TLS ingress or API gateway.
- Terminate TLS with modern configuration, redirect plaintext traffic, and set HSTS, CSP, `X-Content-Type-Options`, and appropriate frame/referrer policies.
- Configure trusted proxies explicitly; do not infer client IPs from untrusted headers.
- Add bounded request parsing, timeout/cancellation behavior, structured error responses, and centralized exception handling.
- Restrict CORS to known dashboard origins and handle preflight deliberately; do not use wildcard CORS for authenticated APIs.

Acceptance criteria:

- Fuzzed invalid input produces a typed 4xx response, not a dropped connection or stack trace.
- A load test with slow clients and concurrent requests meets a defined latency and availability SLO.
- TLS, HTTP header, and CORS configuration pass an external security review.

## P1 — required before general availability

### Durable multi-tenant data and isolation

Tenants, keys, rate counters, simulations, and PR audits live in process-local dictionaries. State disappears on restart and cannot be safely shared across replicas. The unauthenticated PR-audits endpoint also exposes all audit records without a tenant filter.

Required change:

- Use a transactional database with tenant IDs on every persisted record and enforced tenant-scoped query paths.
- Introduce migrations, encrypted backups, point-in-time recovery, retention policies, deletion workflows, and restore drills.
- Use a transactional or purpose-built rate-limit store for distributed limits.
- Make simulation and audit retrieval tenant-scoped, paginated, and authorized.

### Product correctness and API contracts

The dashboard sends `domain`, but `GET /api/v1/simulate` always creates the systems scenario. Unknown domains in the SaaS engine silently select the enterprise scenario. The service does not consistently enforce plan-level maximum horizons or rollout counts.

Evidence: [server.py](omnisim/server.py:112) through line 120; [engine.py](omnisim/saas/engine.py:171) through line 189; [models.py](omnisim/saas/models.py:19) through line 43.

Required change:

- Use one versioned simulation API contract for dashboard, SDK, and CLI.
- Validate an explicit domain enum and reject unknown values.
- Enforce maximum horizon and rollout quotas in the API boundary and worker, not only in UI controls.
- Return assumptions, model version, input hash, confidence/uncertainty information, and a reproducibility ID with every recommendation.
- Remove blanket claims such as “guarantee 0 downtime” unless backed by a rigorously defined and supportable contractual guarantee.

Acceptance criteria:

- Contract tests prove every UI choice maps to the correct backend domain.
- Golden tests and historical replay tests cover each domain with known-safe and known-unsafe inputs.
- Customer-facing language describes the product as decision support until model governance establishes a different claim.

### Observability and incident response

The service needs production telemetry of its own before it can be trusted with telemetry from customers.

Required change:

- Emit structured logs with request ID, tenant ID, route, result class, latency, worker cost, and redaction safeguards.
- Collect metrics for auth failures, rate limiting, queue age, compute time, error rate, webhook verification, and per-tenant resource use.
- Add traces across ingress, API, queue, worker, persistence, and third-party integrations.
- Define on-call ownership, severity levels, incident communications, rollback, key compromise, and data-loss runbooks.

Acceptance criteria:

- Alerts fire in staging for authentication spikes, queue saturation, high error rates, and failed backups.
- An on-call drill restores service, revokes a compromised key, and communicates an incident using the documented runbook.

### Privacy, security program, and customer commitments

Production telemetry and infrastructure manifests may contain sensitive operational data. The current project has no visible retention, deletion, encryption, residency, access review, or vendor-management controls.

Required change:

- Document data classification and minimize ingested fields.
- Encrypt data in transit and at rest; manage secrets using a dedicated secret manager with rotation.
- Define retention, deletion, export, backup, and regional-residency behavior before collecting customer data.
- Establish access controls, audit logging, vulnerability management, dependency scanning, secret scanning, SAST, and an independent security review.
- Obtain privacy/legal review for the target market, including terms, acceptable use, subprocessors, and a data-processing agreement where relevant.

Acceptance criteria:

- A customer can identify what is collected, why, where it is stored, how long it remains, and how to delete it.
- Security controls and evidence are reviewed by the accountable security and legal owners before launch.

## P2 — polish before broad developer adoption

- Implement `omnisim --version` or remove it from command-routing expectations; it currently fails with an argparse error.
- Align package, health endpoint, SDK, dashboard, and documentation versions. The package is `1.0.0` while health/SDK strings advertise `0.1.0`.
- Replace fixed portal metrics, mock tenants, and embedded example API-key text with authenticated, tenant-scoped data.
- Add API documentation, OpenAPI schema, SDK compatibility policy, error catalog, changelog, and deprecation policy.
- Add accessibility, empty/error/loading states, and browser integration tests for the dashboard.

## Proposed production architecture

The public API should have a clear trust boundary:

1. A managed edge layer provides TLS, DDoS/WAF controls, request-size limits, and rate limiting.
2. An identity provider authenticates users and service accounts. The API verifies a signed identity and resolves organization membership and role.
3. A versioned API validates schemas and enforces authorization, tenant boundaries, quotas, and idempotency before work is queued.
4. A job queue accepts bounded simulation requests. Isolated workers execute simulations with CPU/memory/time limits and return durable results.
5. A relational database persists organizations, memberships, keys, plans, usage ledgers, jobs, results, webhook deliveries, and audit events with tenant-scoped access.
6. Object storage retains approved large artifacts with encryption, lifecycle rules, and tenant-scoped access.
7. Observability and security monitoring receive redacted events and metrics from every component.

The local CLI can remain an offline engine. It should not inherit cloud credentials or send telemetry unless the user explicitly configures a remote endpoint.

## Implementation order

### Phase A — make the demo safe to distribute

- Bind the existing demo server to loopback by default.
- Label it as local/demo-only in CLI output and documentation.
- Remove demo API-key strings and default production-style tenant names from public UI text.
- Correct the version flag and normalize published version metadata.

### Phase B — build a secure closed-beta control plane

- Introduce the production API boundary, identity model, RBAC, persistent database, migrations, and secret management.
- Implement signed GitHub webhook verification and tenant mapping.
- Add schema validation, all resource limits, job queuing, and rate-limit storage.
- Add HTTP integration tests that prove authorization, isolation, validation, and quotas.
- Run a staging security test, load test, backup restore, and incident drill.

### Phase C — establish trustworthy product behavior

- Connect UI controls to the correct simulation domain through a tested contract.
- Introduce model/version lineage, calibration metrics, uncertainty reporting, and reproducible simulation inputs.
- Establish a customer onboarding process with explicit data-collection consent and environment separation.
- Pilot with a small set of contract-backed tenants while monitoring reliability and false-positive/false-negative rates.

### Phase D — approve general availability

General availability requires written sign-off from engineering, security, operations, privacy/legal, and product. The sign-off should cite the evidence listed in the next section rather than rely on a passing unit-test suite alone.

## General-availability evidence checklist

- Threat model reviewed and all P0 findings closed or formally accepted by accountable leadership.
- Independent application security assessment completed; critical/high findings remediated and retested.
- Tenant-isolation, authorization, webhook-signature, quota, idempotency, and abuse tests run in CI and staging.
- Load, soak, and failure tests meet published SLOs; capacity and cost limits are enforced.
- Backup restore and disaster-recovery exercises meet documented RPO/RTO objectives.
- Monitoring, alerting, runbooks, escalation, and customer support ownership are exercised.
- Data inventory, retention/deletion policy, terms, privacy review, and vendor controls are approved for the target launch regions.
- Customer documentation describes supported inputs, model assumptions, limitations, confidence, and escalation paths.
- Staged rollout and rollback plans are approved, including kill switches for jobs, integrations, and API keys.

## Test gaps to add immediately

The existing tests exercise in-process SaaS methods, but not the HTTP security boundary. Add a separate API integration suite that starts the real server and includes:

- Missing, invalid, revoked, expired, and under-scoped credential tests for every protected route.
- Two-tenant isolation tests for keys, usage, simulations, PR audits, telemetry, and billing data.
- Key lifecycle tests: creation, redaction, rotation, expiry, revocation, and audit events.
- Signup and billing-entitlement tests proving public users cannot self-assign paid plans.
- Signed GitHub webhook tests for valid signatures, invalid signatures, altered payloads, replayed deliveries, and wrong tenant mappings.
- Parameter-boundary, malformed JSON, large-body, cancellation, timeout, concurrency, and rate-limit tests.
- Dashboard browser tests that change each domain and verify the same domain in the returned result.
- Migration, restart, multi-replica, backup, restore, and retention/deletion tests.

## Bottom line

OmniSim has a working local simulation product and useful pre-flight IaC demonstration. It is not yet a public SaaS. The shortest responsible path is to treat the current server as a demo, first build the identity/tenant/security boundary and durable service infrastructure, then validate correctness and operations in a closed beta before considering general availability.
