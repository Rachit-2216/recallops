# RecallOps Product and Technical Design

**Status:** Approved

**Date:** 2026-06-28

**Submission type:** Solo hackathon project

**Primary objective:** Maximize winning probability

**Infrastructure budget:** $0 beyond the 14,000,000 Cognee tokens supplied by the `COGNEE-35` voucher

**Landing page:** Explicitly excluded; the user will design it later against the integration contract in this document

## 1. Executive Summary

RecallOps is an AI incident commander with auditable, self-improving memory. It helps engineering teams investigate production incidents by remembering past failures, connecting current symptoms to previous root causes, showing why a memory was recalled, and learning only from resolutions that a human verifies.

The winning differentiator is not a generic chat interface. RecallOps makes the entire Cognee memory lifecycle visible:

- `remember()` stores permanent evidence and fast session observations.
- `recall()` retrieves graph-backed context with stable source references.
- `improve()` promotes verified session knowledge and applies feedback.
- `forget()` removes a specific stale or incorrect permanent evidence item.

The judge demo uses a deterministic checkout outage. A new deployment produces timeouts and Redis session misses. RecallOps connects those symptoms to a previous TTL-unit incident, shows the graph relationship and source evidence, forgets a stale runbook rule, confirms the real fix, improves memory, and recalls that verified resolution from a clean session.

## 2. Product Positioning

### Problem

Incident responders repeatedly rediscover knowledge that already exists across postmortems, runbooks, deployment notes, chat transcripts, and individual memory. Generic search retrieves documents but does not maintain a live episodic incident memory, connect causal relationships, distinguish verified facts from hypotheses, or improve after human feedback.

### Solution

RecallOps provides:

1. A curated evidence library backed by Cognee graph memory.
2. A live incident session backed by Cognee session memory.
3. Graph-aware recall with explicit references and retrieval explanations.
4. Human-controlled promotion of verified resolutions.
5. Selective forgetting of stale or incorrect permanent evidence.
6. A Memory Inspector that exposes provenance, relationship paths, and lifecycle actions.

### Why Cognee is essential

Replacing Cognee with ordinary chat history would remove:

- Cross-session permanent graph memory.
- Relationship-aware retrieval.
- Automatic query routing.
- Feedback-weighted improvement.
- Session-to-graph promotion.
- Data-item-level graph/vector deletion.

Cognee is therefore a core product capability, not a badge or incidental API call.

## 3. Judging Strategy

| Criterion | RecallOps response |
|---|---|
| Potential Impact | Reduces incident resolution time and prevents repeated operational failures. |
| Creativity and Innovation | Combines incident command, memory provenance, controlled learning, and selective forgetting. |
| Technical Excellence | Typed domain model, adapter boundaries, background ingestion, deterministic state machines, automated tests, evaluation corpus, containerized deployment. |
| Best Use of Cognee | Demonstrates permanent and session memory, graph recall, references, feedback, session bridging, improvement, and item-level forgetting. |
| User Experience | One operational cockpit, evidence-backed answers, visible states, deterministic seeded demo, graceful failures. |
| Presentation Quality | A concise before/after narrative with a visible memory transformation and reproducible evidence. |

## 4. Target User and Core Scenario

### Primary user

An on-call engineer or incident commander handling a production outage.

### Seeded judge scenario

- Service: `checkout-api`
- Current incident: `INC-2048`
- Trigger: `deploy-418`
- Symptoms:
  - Checkout p95 latency above 4 seconds.
  - Redis session misses increased by more than 600%.
  - Failures began within 10 minutes of deployment.
- Relevant historical incident: `INC-1842`
- Historical root cause: Redis TTL values changed from seconds to milliseconds without conversion.
- Deliberate stale item: a runbook rule recommending an obsolete cache-reset procedure.
- Deliberate false hypothesis: payment-gateway rate limiting.
- Correct mitigation: roll back the TTL configuration and reissue affected sessions.

### Required demo result

RecallOps must:

1. Recall `INC-1842` when asked about the new symptoms.
2. Explain the connection through service, timing, dependency, and symptom relationships.
3. Cite exact evidence.
4. Show the stale runbook item.
5. Forget that exact permanent item.
6. Verify the stale item is no longer retrievable.
7. Record the real resolution in session memory.
8. Improve the permanent graph using the verified session.
9. Recall the new resolution from a clean incident session.

## 5. Scope

### Core scope

- Seeded demo loader.
- Incident creation and lifecycle.
- Evidence ingestion for text, Markdown, JSON, logs, PDFs, and safe URLs.
- Ingestion status.
- Session observations.
- Graph-backed recall.
- Stable references to source documents and chunks.
- Memory Inspector.
- Hypothesis and memory-candidate state.
- Feedback recording.
- Resolution verification.
- Explicit improvement.
- Item-level forgetting.
- Retrieval evaluation suite.
- Dockerized local deployment.
- One public free-tier deployment.
- README, architecture documentation, demo script, and submission materials.

### Stretch scope

Stretch work is attempted only after every core acceptance criterion passes:

- Read-only GitHub deployment-note import.
- Simulated Slack or PagerDuty event feed.
- Graph visualization enhancements.
- Exported incident report.
- Lightweight responsive mobile view.

### Explicit non-goals

- Landing-page design or marketing-page implementation.
- Enterprise authentication, billing, role management, or multi-tenancy.
- Autonomous production remediation.
- Production OAuth integrations.
- Unrestricted public uploads.
- Training or fine-tuning a model.
- Rebuilding Cognee internals.
- A general-purpose document chatbot.

## 6. User Journeys

### Journey A: Load the deterministic demo

1. User enters the application at `/app`.
2. User selects **Load Checkout Outage Demo**.
3. Application resets local demo state with stable IDs.
4. Backend verifies the seeded Cognee dataset is ready.
5. If the dataset is absent, the backend offers a controlled seed operation.
6. User opens `INC-2048`.

### Journey B: Investigate an incident

1. User records a live observation.
2. Backend stores it in session memory with `self_improvement=False`.
3. User asks a relationship or temporal question.
4. Backend calls graph-backed recall scoped to the evidence dataset and incident session.
5. Response contains answer text, source type, retrieval mode, data IDs, chunk IDs, document names, and evidence snippets.
6. UI shows answer, citations, and Memory Inspector trace.
7. Unsupported answers remain unverified and cannot become a confirmed resolution.

### Journey C: Reject stale memory

1. Memory Inspector opens a permanent evidence item with a stable `data_id`.
2. User selects **Forget memory**.
3. UI shows exact deletion scope and requires confirmation.
4. Backend calls `forget(dataset=..., data_id=...)`.
5. Backend verifies the deletion response.
6. Backend repeats a reference-targeted recall check.
7. UI shows before/after retrieval state.

### Journey D: Resolve and improve

1. User records the mitigation and verification evidence.
2. User selects **Confirm resolution**.
3. Backend validates that a root cause, mitigation, verification, and referenced evidence exist.
4. Backend stores feedback for the relevant recall result.
5. Backend calls `improve(dataset=..., session_ids=[incident_session_id])`.
6. Resolution state changes to `promoted` only after success.
7. A clean session recalls the promoted resolution.

## 7. System Architecture

### High-level architecture

```text
Browser
  |
  v
React + TypeScript application
  |
  v
FastAPI orchestration service
  |-- Incident service
  |-- Evidence service
  |-- Recall service
  |-- Memory lifecycle service
  |-- Demo seeding service
  |-- Credit guard
  |-- Audit log
  |
  v
Cognee adapter
  |
  v
Cognee Cloud
  |-- Permanent evidence dataset
  |-- Incident session memory
  |-- Hybrid graph/vector retrieval
  |-- Improvement and feedback weights
  `-- Item-level forget
```

### Deployment shape

- One Docker image.
- Multi-stage build compiles the React application.
- FastAPI serves the application and API from one origin.
- Cognee Cloud stores AI memory.
- SQLite stores application metadata and audit state.
- Demo state is reproducible from versioned fixtures.
- Public deployment uses constrained demo mode.
- Local Docker is the guaranteed fallback.

### Hosting decision

The public deployment target is a Hugging Face Docker Space on the free
`cpu-basic` tier. The image must listen on port `7860`, keep SQLite under
`/data` when persistent storage is available, and rebuild demo metadata from
versioned fixtures when storage is ephemeral. Free Spaces can sleep, so the
submission checklist includes a pre-demo wake-up check.

Local Docker plus a recorded walkthrough is the guaranteed fallback. No
deployment step may upgrade hardware, attach a paid service, or trigger a paid
plan.

## 8. Technology Stack

### Backend

- Python 3.13.
- FastAPI.
- Pydantic v2.
- SQLAlchemy 2.
- Alembic.
- `cognee==1.2.2`.
- `httpx`.
- `structlog`.
- Pytest and pytest-asyncio.

### Frontend application

- React.
- TypeScript.
- Vite.
- React Router.
- TanStack Query.
- Zustand for transient UI state.
- React Hook Form and Zod.
- `@xyflow/react` for the memory relationship graph.
- Playwright for browser tests.

### Tooling

- `uv` for Python dependency management.
- npm for frontend dependencies.
- Ruff for Python formatting and linting.
- ESLint and Prettier for TypeScript.
- Docker and Docker Compose.
- GitHub Actions for offline tests and builds.

## 9. Component Boundaries

### `IncidentService`

Responsibilities:

- Create and update incidents.
- Generate stable Cognee session IDs.
- Validate incident state transitions.
- Close incidents only after resolution validation.

Does not call Cognee directly.

### `EvidenceService`

Responsibilities:

- Validate uploads and safe URLs.
- Create stable data IDs.
- Track ingestion jobs.
- Map Cognee references to local evidence metadata.

Calls Cognee only through `CogneeMemoryPort`.

### `RecallService`

Responsibilities:

- Formulate scoped recall requests.
- Parse normalized recall objects.
- Extract source references.
- Assign verification status.
- Persist recall traces.

Does not own UI formatting.

### `MemoryLifecycleService`

Responsibilities:

- Store session observations.
- Record feedback.
- Promote verified sessions through `improve()`.
- Forget one permanent data item.
- Verify lifecycle changes through follow-up retrieval.

### `DemoService`

Responsibilities:

- Load stable fixture IDs.
- Seed the dataset idempotently.
- Reset local state without uncontrolled Cognee deletion.
- Expose one-click judge flows.

### `CreditGuard`

Responsibilities:

- Count live Cognee operations.
- Separate estimated heavy and light operations.
- Block nonessential rebuilds at the configured internal ceiling.
- Preserve a final-demo reserve.

### `CogneeMemoryPort`

Interface:

```python
class CogneeMemoryPort(Protocol):
    async def remember_evidence(self, payload: EvidencePayload) -> RememberReceipt: ...
    async def remember_observation(
        self, session_id: str, content: str
    ) -> RememberReceipt: ...
    async def recall(self, request: RecallRequest) -> list[RecallEntry]: ...
    async def improve_session(
        self, dataset: str, session_ids: list[str]
    ) -> ImproveReceipt: ...
    async def forget_evidence_item(
        self, dataset: str, data_id: str
    ) -> ForgetReceipt: ...
    async def dataset_status(self, dataset: str) -> DatasetStatus: ...
    async def health(self) -> MemoryHealth: ...
```

Implementations:

- `CogneeCloudAdapter` for production and live integration tests.
- `FakeCogneeAdapter` for deterministic unit/API tests.
- Recorded JSON fixtures for contract regression tests.

## 10. Domain Model

### Incident

| Field | Type | Rules |
|---|---|---|
| `id` | string | Stable format such as `INC-2048`. |
| `title` | string | Required. |
| `severity` | enum | `SEV1`, `SEV2`, `SEV3`. |
| `service` | string | Required. |
| `status` | enum | `draft`, `active`, `mitigated`, `resolved`. |
| `session_id` | string | `incident:<incident_id>`. Immutable. |
| `started_at` | datetime | Required. |
| `resolved_at` | datetime/null | Required for resolved state. |

### EvidenceItem

| Field | Type | Rules |
|---|---|---|
| `data_id` | UUID | Stable Cognee data ID. |
| `dataset` | string | `recallops_evidence_v1`. |
| `name` | string | Display and citation name. |
| `kind` | enum | `runbook`, `postmortem`, `deploy`, `log`, `note`, `url`, `memory_candidate`. |
| `source_uri` | string/null | Sanitized. |
| `status` | enum | `queued`, `processing`, `ready`, `failed`, `forgotten`. |
| `content_hash` | string | Idempotency. |

### Observation

| Field | Type | Rules |
|---|---|---|
| `id` | UUID | Local stable ID. |
| `incident_id` | string | Required. |
| `timestamp` | datetime | Required. |
| `source` | enum | `human`, `system`, `recallops`. |
| `content` | string | Maximum configured length. |
| `memory_status` | enum | `pending`, `session_stored`, `failed`. |

### MemoryCandidate

State machine:

```text
proposed -> pinned -> verified -> promoted
    |          |          |
    v          v          v
 rejected   forgotten   superseded
```

Only a pinned candidate has a permanent `data_id`. A rejected session-only hypothesis is not falsely represented as individually forgotten from Cognee.

### RecallTrace

Stores:

- Query.
- Query type.
- Cognee source.
- Search type.
- Dataset ID/name.
- Data ID.
- Chunk ID/index.
- Document name.
- Evidence snippet.
- Raw trace fixture reference.
- Verification state.
- Latency.

## 11. Cognee Memory Design

### Dataset

Permanent evidence uses:

```text
recallops_evidence_v1
```

Build-session memory for Codex uses a separate dataset:

```text
recallops_build_memory
```

These datasets must never be mixed.

### Session IDs

```text
incident:<incident_id>
```

The demo incident uses:

```text
incident:INC-2048
```

### Ingestion

- Batch evidence whenever possible.
- Use stable `DataItem.data_id` values.
- Set `self_improvement=False` during initial batch ingestion.
- Run one explicit controlled improvement pass after the batch.
- Avoid repeated full-dataset rebuilds.
- Use background ingestion and poll dataset status.

### Session memory

- Live observations use `remember(..., session_id=..., self_improvement=False)`.
- Unverified hypotheses remain session-only.
- No automatic bridge runs during an active incident.

### Recall

- Default to auto-routing.
- Scope graph recall to `recallops_evidence_v1`.
- Include incident session context.
- Request references.
- Use verbose results for the Memory Inspector.
- Use `only_context=True` only for retrieval debugging and evaluation.
- Persist normalized references, never raw secrets.

### Improve

Run only after human resolution confirmation:

```python
await cognee.improve(
    dataset="recallops_evidence_v1",
    session_ids=["incident:INC-2048"],
)
```

The resolution remains `promotion_pending` until this succeeds.

### Forget

Forget is truthful and item-scoped:

```python
await cognee.forget(
    dataset="recallops_evidence_v1",
    data_id=stale_item_id,
)
```

After deletion, RecallOps performs a retrieval verification query. The UI does not claim success from an HTTP status alone.

## 12. Backend API

### Demo

#### `POST /api/demo/reset`

Resets local state to stable fixture IDs. Does not wipe the Cognee account.

#### `POST /api/demo/seed`

Idempotently ingests missing fixture data. Protected by demo/admin token outside local mode.

### Evidence

#### `POST /api/evidence`

Accepts:

- Multipart upload.
- Plain text.
- Safe HTTPS URL when enabled.

Limits:

- Maximum 5 MB per file in local mode.
- Maximum 1 MB and allowlisted fixtures in public demo mode.
- No arbitrary URLs in public demo mode.

#### `GET /api/evidence`

Lists evidence and ingestion state.

#### `GET /api/evidence/{data_id}`

Returns metadata and reference-safe preview.

#### `GET /api/evidence/{data_id}/status`

Returns local and Cognee indexing state.

#### `DELETE /api/evidence/{data_id}`

Requires typed confirmation payload and performs verified Cognee forgetting.

### Incidents

#### `POST /api/incidents`

Creates incident and session ID.

#### `GET /api/incidents`

Lists local incidents.

#### `GET /api/incidents/{incident_id}`

Returns cockpit state.

#### `POST /api/incidents/{incident_id}/observe`

Writes session observation.

#### `POST /api/incidents/{incident_id}/recall`

Request:

```json
{
  "query": "How is deploy 418 related to the previous Redis incident?",
  "include_trace": true
}
```

Response:

```json
{
  "answer": "INC-1842 is the closest prior incident because both outages followed a checkout deployment that changed Redis session TTL behavior.",
  "verification": "referenced",
  "source": "graph",
  "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
  "references": [
    {
      "data_id": "11111111-1111-4111-8111-111111111111",
      "chunk_id": "22222222-2222-4222-8222-222222222222",
      "document_name": "postmortem-1842.md",
      "snippet": "The checkout session TTL changed from seconds to milliseconds without conversion."
    }
  ],
  "trace_id": "33333333-3333-4333-8333-333333333333"
}
```

#### `POST /api/incidents/{incident_id}/feedback`

Records score and explanation against a recall trace.

#### `POST /api/incidents/{incident_id}/resolve`

Validates and promotes the verified resolution.

### Health

#### `GET /api/health`

Returns:

- Application status.
- Database status.
- Cognee reachability.
- Dataset readiness.
- Demo mode.
- Credit guard state.

Never returns credentials.

## 13. Application UI

The application UI is in scope. The marketing landing page is not.

### Routes

| Route | Purpose |
|---|---|
| `/` | Redirect boundary to `/app`; reserved for the later landing page. |
| `/app` | Demo home and incident overview. |
| `/app/evidence` | Evidence library and ingestion state. |
| `/app/incidents/:id` | Live incident cockpit. |
| `/app/memory` | Memory graph and inspector. |
| `/app/resolutions/:id` | Verified resolution report. |

### Incident cockpit

Three-column operational layout:

1. Navigation and budget indicator.
2. Incident timeline, recalled answers, and observation composer.
3. Memory Inspector with provenance, graph path, and lifecycle actions.

### Memory Inspector requirements

- Display session/graph/trace source.
- Display retrieval type.
- Display document and chunk references.
- Display why recalled.
- Display memory state.
- Show only valid lifecycle actions.
- Require confirmation for forget.
- Show before/after retrieval evidence.

### Landing-page integration contract

The user-owned landing page must:

- Preserve the application under `/app`.
- Link its primary CTA to `/app?demo=checkout`.
- Reuse environment configuration and build pipeline.
- Not move or rename backend API routes.
- Not expose the Cognee API key.
- Pass the existing application browser tests.

## 14. Error Handling

### Indexing in progress

- Display `partial_memory`.
- Do not phrase answers as definitive.
- Poll with bounded exponential backoff.
- Let the user continue recording observations.

### Cognee unavailable

- Display degraded mode.
- Preserve unsent observations locally.
- Offer explicit retry.
- Never fabricate a recalled answer.

### No relevant result

- State that no relevant prior incident was found.
- Show dataset and session scope.
- Suggest evidence ingestion.

### Missing references

- Mark answer `unverified`.
- Prevent direct promotion into a verified resolution.

### Improve failure

- Keep resolution state `promotion_failed`.
- Preserve user-entered resolution.
- Offer retry.
- Do not state that the system learned.

### Forget failure

- Keep item visible.
- Record failure in audit log.
- Do not run a success animation.
- Offer retry.

### Duplicate ingestion

- Compare content hash.
- Reuse existing evidence item when appropriate.
- Never spend credits re-ingesting identical fixtures without explicit force.

## 15. Security and Privacy

- Store secrets only in environment variables or hosting secret storage.
- Never return secrets through APIs.
- Redact authorization headers and API keys from logs.
- Do not ingest `.env`, credentials, private keys, or arbitrary local repositories.
- Public demo mode disables arbitrary URL fetches.
- Validate MIME type and filename independently.
- Apply request size limits.
- Apply per-IP or per-session rate limits.
- Apply strict CORS to the deployed origin.
- Add security headers.
- Escape rendered source content.
- Use parameterized database access.
- Log all forget and improve operations.
- Display that demo data is synthetic.

## 16. Credit Budget

Hard supply:

```text
14,000,000 Cognee tokens
```

Allocation:

| Category | Budget |
|---|---:|
| API and schema experiments | 2,000,000 |
| Seed ingestion and controlled graph tuning | 3,000,000 |
| Retrieval evaluation and regression checks | 2,000,000 |
| Rehearsals and final live demo | 1,000,000 |
| Protected reserve | 6,000,000 |

Guardrails:

- Default tests use the fake adapter.
- Live tests require `RUN_COGNEE_INTEGRATION=1`.
- Seed operations are idempotent.
- Full rebuild requires an explicit force flag.
- Public demo has query and action limits.
- Nonessential live evaluation stops before the protected reserve is touched.
- No paid top-up is permitted.

## 17. Seed Data

Versioned fixture files:

```text
demo/fixtures/
  postmortem-inc-1842.md
  checkout-runbook-v3.md
  stale-cache-reset-rule.md
  deploy-418.json
  checkout-errors.log
  incident-2048-timeline.json
  expected-retrieval.json
```

Fixtures must:

- Be synthetic.
- Contain no real company data.
- Include stable entities and exact phrases.
- Include one contradiction.
- Include one stale evidence item.
- Support relationship, temporal, summary, and lexical queries.

## 18. Evaluation Plan

### Golden questions

At least 10:

1. Which previous incident resembles the current checkout outage?
2. How is deploy 418 connected to Redis session misses?
3. What changed immediately before latency increased?
4. What was the root cause of INC-1842?
5. Which runbook instruction is now stale?
6. What evidence contradicts payment-gateway rate limiting?
7. Summarize the incident timeline.
8. Which services depend on the affected Redis path?
9. What mitigation was verified?
10. What did RecallOps learn after INC-2048 was resolved?

### Evaluation assertions

- Expected evidence document present.
- Expected relationship present.
- Unsupported claim absent.
- Source references parse correctly.
- Improve changes clean-session recall.
- Forget removes stale-item retrieval.
- Latency remains acceptable for a demo.

## 19. Testing Strategy

### Backend unit tests

- Domain state transitions.
- Content-hash idempotency.
- Trace parsing.
- Reference normalization.
- Credit guard.
- Public-demo restrictions.
- Error mapping.

### Adapter contract tests

Run the same contract against:

- Fake adapter.
- Recorded fixtures.
- Live Cognee adapter when explicitly enabled.

### API tests

- Demo reset and seed.
- Evidence ingestion.
- Incident observations.
- Recall with references.
- Feedback.
- Resolution validation.
- Improve success/failure.
- Forget success/failure.
- Health response secret safety.

### Frontend tests

- Component states.
- Incident cockpit interactions.
- Memory Inspector trace rendering.
- Indexing/degraded/unverified states.
- Forget confirmation.
- Resolution workflow.

### Browser tests

- Complete 90-second judge journey.
- Clean-session memory proof.
- No-result journey.
- Cognee outage journey.
- Responsive application shell.
- Landing-page boundary remains intact.

### CI

Default CI runs without Cognee credentials:

- Lint.
- Type checks.
- Unit tests.
- Fake-adapter API tests.
- Frontend tests.
- Production build.
- Docker build.

Live integration is manual and protected.

## 20. Observability

- Structured JSON logs.
- Correlation ID per HTTP request.
- Incident ID and trace ID on memory operations.
- Operation name, duration, success, and safe error category.
- No raw credentials.
- Local audit table for remember/recall/improve/forget operations.
- Health endpoint.
- Visible application operation states.

## 21. Deployment

### Docker

- Multi-stage Node build.
- Python runtime stage.
- Non-root container user.
- Health check.
- Environment-based configuration.
- Persistent local volume for SQLite when supported.

### Public demo mode

- Fixed synthetic scenario.
- No arbitrary uploads.
- No arbitrary URLs.
- Limited query length.
- Limited memory-mutating actions.
- Resettable local state.
- Server-side Cognee credentials.

### Local fallback

One command starts the complete application:

```bash
docker compose up --build
```

The fallback must be verified before public deployment work begins.

## 22. Demo Script

Target: 90 seconds.

1. **0–10s:** “Incident responders lose the reasoning behind yesterday’s fixes.”
2. **10–20s:** Open `INC-2048`; show deployment, latency, and Redis symptoms.
3. **20–35s:** Ask how the new incident relates to prior outages.
4. **35–48s:** Open Memory Inspector; show relationship path and exact references.
5. **48–60s:** Select stale runbook evidence and forget it.
6. **60–68s:** Re-run recall and show stale guidance is gone.
7. **68–78s:** Confirm the real resolution and run improve.
8. **78–88s:** Open a clean session and recall the newly verified fix.
9. **88–90s:** “RecallOps does not merely remember more; it remembers what the team verified.”

## 23. Acceptance Criteria

### Functional

- Seed operation is idempotent.
- Permanent evidence is retrievable.
- Session observations are available immediately.
- Graph recall returns source-tagged results.
- At least one response exposes stable document/chunk references.
- Memory Inspector renders provenance.
- Verified resolution triggers improve.
- Clean session recalls the promoted resolution.
- Item-level forget removes one stale evidence item.
- Follow-up recall proves the stale item is absent.

### Quality

- Offline tests pass.
- Production frontend build passes.
- Docker image builds.
- Complete judge journey passes in Playwright.
- No secrets appear in repository, logs, or health output.
- Public demo restrictions are enforced.
- Application operates within supplied credits.

### Presentation

- README contains problem, solution, architecture, setup, Cognee lifecycle, screenshots, demo link, and AI-assistance disclosure.
- Demo video follows the approved script.
- Submission clearly distinguishes real integrations from simulated fixtures.
- Landing page links to `/app?demo=checkout`.

## 24. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Cognee Cloud API changes | Pin `cognee==1.2.2`; isolate adapter; record contracts. |
| Ingestion latency | Seed early, poll status, pre-warm demo dataset. |
| Credit exhaustion | Fake adapter by default, idempotent seed, live-test gate, protected reserve. |
| Free host sleeps | Pre-warm, provide local Docker fallback, record stable video. |
| Retrieval nondeterminism | Curated fixtures, stable IDs, evaluation corpus, explicit scopes. |
| False hypotheses promoted | Disable automatic improvement during active incidents. |
| Forget semantics overstated | Forget only stable permanent data items and verify afterward. |
| Landing page breaks app | Preserve `/app` and API integration contract; browser regression tests. |
| Solo scope expansion | Stretch features blocked until all core acceptance criteria pass. |

## 25. Definition of Done

RecallOps is done only when:

1. The application satisfies every core acceptance criterion.
2. The complete judge flow succeeds from a clean setup.
3. Tests and production build pass.
4. Docker fallback works.
5. A live or reliably recorded demo exists.
6. Documentation and AI-assistance disclosure are complete.
7. Remaining Cognee credits include the protected final-demo reserve.
