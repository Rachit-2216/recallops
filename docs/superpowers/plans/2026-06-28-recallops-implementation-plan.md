# RecallOps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents unless the
> user explicitly authorizes them.

**Goal:** Build and ship RecallOps, an incident-command application that visibly
demonstrates Cognee's remember, recall, improve, and item-level forget lifecycle
in a deterministic 90-second judge flow.

**Architecture:** A React/TypeScript single-page application calls a same-origin
FastAPI service. FastAPI owns incident state, evidence metadata, audit records,
credit controls, and a narrow `CogneeMemoryPort`; Cognee Cloud owns permanent
graph memory and short-lived incident session memory. Offline tests use a
deterministic fake adapter, while live calls are opt-in and isolated.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic,
`cognee==1.2.2`, SQLite, React 19, TypeScript, Vite, React Router, TanStack
Query, Zustand, React Hook Form, Zod, `@xyflow/react`, Vitest, Playwright,
Docker, Hugging Face Docker Spaces.

**Approved design:** `docs/superpowers/specs/2026-06-28-recallops-design.md`

---

## 0. Execution Rules

These rules are requirements, not suggestions.

1. Work in plan order. Mark a checkbox only after its stated verification
   succeeds.
2. Use test-driven development for domain behavior, services, API routes, and
   frontend state.
3. Make the small commit named at the end of each task.
4. Never print, store, screenshot, commit, or send `COGNEE_API_KEY`.
5. Never run a live Cognee test unless `RUN_COGNEE_INTEGRATION=1`.
6. Never call `cognee.forget(everything=True)` or delete the complete account
   dataset.
7. The application dataset is `recallops_evidence_v1`. Codex build memory is
   `recallops_build_memory`. Never mix them.
8. Do not implement the marketing landing page. `/` only redirects to `/app`.
9. Do not buy hosting, credits, hardware, storage, a domain, or any other
   service.
10. Preserve at least 6,000,000 of the supplied 14,000,000 Cognee tokens for
    rehearsal and the final demo.
11. Treat the seeded demo as a product feature. It must be deterministic,
    idempotent, restart-safe, and visibly marked synthetic.
12. If a live Cognee response differs from the recorded contract, update only
    the adapter and recorded contract fixture. Do not leak SDK-specific shapes
    into services or routes.

## 1. Locked File Map

The implementation must use this layout.

```text
.
├── .env.example
├── .github/workflows/ci.yml
├── Dockerfile
├── README.md
├── compose.yaml
├── pyproject.toml
├── uv.lock
├── backend/
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/0001_initial.py
│   ├── src/recallops/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── errors.py
│   │   ├── api/
│   │   │   ├── dependencies.py
│   │   │   ├── demo.py
│   │   │   ├── evidence.py
│   │   │   ├── health.py
│   │   │   └── incidents.py
│   │   ├── domain/
│   │   │   ├── enums.py
│   │   │   ├── models.py
│   │   │   └── schemas.py
│   │   ├── memory/
│   │   │   ├── contract.py
│   │   │   ├── fake.py
│   │   │   ├── cognee_cloud.py
│   │   │   └── normalize.py
│   │   ├── repositories/
│   │   │   ├── audit.py
│   │   │   ├── evidence.py
│   │   │   ├── incidents.py
│   │   │   └── recalls.py
│   │   └── services/
│   │       ├── credit_guard.py
│   │       ├── demo.py
│   │       ├── evidence.py
│   │       ├── incidents.py
│   │       ├── lifecycle.py
│   │       └── recall.py
│   └── tests/
│       ├── conftest.py
│       ├── contract/test_memory_contract.py
│       ├── integration/test_cognee_live.py
│       ├── unit/
│       └── api/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── playwright.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── router.tsx
│   │   ├── styles.css
│   │   ├── api/client.ts
│   │   ├── app/AppShell.tsx
│   │   ├── components/
│   │   ├── features/demo/
│   │   ├── features/evidence/
│   │   ├── features/incidents/
│   │   ├── features/memory/
│   │   └── test/
│   └── e2e/
│       ├── judge-flow.spec.ts
│       └── degraded-flow.spec.ts
├── demo/
│   ├── fixtures/
│   │   ├── postmortem-inc-1842.md
│   │   ├── checkout-runbook-v3.md
│   │   ├── stale-cache-reset-rule.md
│   │   ├── deploy-418.json
│   │   ├── checkout-errors.log
│   │   ├── incident-2048-timeline.json
│   │   └── expected-retrieval.json
│   └── demo-script.md
├── scripts/
│   ├── cognee_contract_probe.py
│   ├── evaluate_retrieval.py
│   └── preflight.py
└── docs/
    ├── architecture.md
    ├── cognee-lifecycle.md
    └── submission-checklist.md
```

Files stay focused:

- `memory/*` is the only package allowed to import `cognee`.
- `services/*` depends on `CogneeMemoryPort`, never on Cognee response objects.
- `api/*` translates HTTP only; business rules remain in services/domain.
- React features call `src/api/client.ts`, never `fetch` directly.
- Demo content lives only in `demo/fixtures`, not in service constants.

## 2. Delivery Milestones

| Milestone | Tasks | Proof |
|---|---|---|
| Offline vertical slice | 1-10 | Fake-adapter API can seed, recall, forget, improve. |
| Judgeable application | 11-16 | Cockpit and Memory Inspector complete the flow. |
| Shippable build | 17-20 | E2E, security, Docker, CI, docs pass. |
| Live Cognee proof | 21 | Controlled cloud run validates real lifecycle. |

---

### Task 1: Initialize the repository and quality gates

**Files:**

- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `backend/src/recallops/__init__.py`
- Create: `backend/tests/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/test/setup.ts`

- [x] **Step 1: Initialize Git if `git status` says this is not a repository**

Run:

```powershell
git init
git branch -M main
git status --short
```

Expected: `git status` succeeds and lists only planning files as untracked.

- [x] **Step 2: Create the Python project metadata**

Create `pyproject.toml` with these dependency groups and commands:

```toml
[project]
name = "recallops"
version = "0.1.0"
description = "Auditable self-improving incident memory powered by Cognee"
requires-python = ">=3.13,<3.14"
dependencies = [
  "alembic>=1.14,<2",
  "cognee==1.2.2",
  "fastapi>=0.115,<1",
  "httpx>=0.28,<1",
  "pydantic-settings>=2.7,<3",
  "python-multipart>=0.0.20,<1",
  "sqlalchemy>=2.0.36,<3",
  "structlog>=25.1,<26",
  "uvicorn[standard]>=0.34,<1",
]

[dependency-groups]
dev = [
  "mypy>=1.14,<2",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<1",
  "pytest-cov>=6,<7",
  "ruff>=0.9,<1",
]

[tool.pytest.ini_options]
addopts = "-q --strict-markers"
asyncio_mode = "auto"
pythonpath = ["backend/src"]
testpaths = ["backend/tests"]
markers = [
  "integration: requires explicitly enabled external services",
]

[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP", "ASYNC", "S"]
ignore = ["S101"]

[tool.mypy]
python_version = "3.13"
strict = true
packages = ["recallops"]
mypy_path = "backend/src"
```

- [x] **Step 3: Create the safe environment template**

Create `.env.example`:

```dotenv
APP_ENV=local
APP_DATABASE_URL=sqlite+aiosqlite:///./recallops.db
APP_PUBLIC_ORIGIN=http://localhost:5173
APP_DEMO_MODE=true
APP_DEMO_ADMIN_TOKEN=change-this-local-token
APP_COGNEE_MODE=fake
APP_COGNEE_DATASET=recallops_evidence_v1
APP_COGNEE_TOKEN_SUPPLY=14000000
APP_COGNEE_PROTECTED_RESERVE=6000000
COGNEE_BASE_URL=
COGNEE_API_KEY=
RUN_COGNEE_INTEGRATION=0
```

Add `aiosqlite>=0.20,<1` to the main dependencies because the application uses
the async SQLite driver.

- [x] **Step 4: Scaffold the frontend manifest**

Create `frontend/package.json`:

```json
{
  "name": "recallops-web",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint . --max-warnings=0",
    "test": "vitest run",
    "test:watch": "vitest",
    "e2e": "playwright test"
  },
  "dependencies": {
    "@hookform/resolvers": "^4.1.0",
    "@tanstack/react-query": "^5.66.0",
    "@xyflow/react": "^12.4.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.475.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-hook-form": "^7.54.0",
    "react-router-dom": "^7.1.0",
    "zod": "^3.24.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.19.0",
    "@playwright/test": "^1.50.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@testing-library/react": "^16.2.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^9.19.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.18",
    "jsdom": "^26.0.0",
    "prettier": "^3.4.0",
    "typescript": "~5.7.0",
    "typescript-eslint": "^8.22.0",
    "vite": "^6.1.0",
    "vitest": "^3.0.0"
  }
}
```

Create strict `frontend/tsconfig.json`, Vite React configuration, ESLint flat
configuration, and Vitest setup with `@testing-library/jest-dom/vitest`.

- [x] **Step 5: Install and lock dependencies**

Run:

```powershell
uv sync --group dev
npm --prefix frontend install
```

Expected: `uv.lock` and `frontend/package-lock.json` exist; neither command
reports a resolution error.

- [x] **Step 6: Verify clean empty-suite tooling**

Run:

```powershell
uv run ruff check backend
uv run pytest
npm --prefix frontend run test
```

Expected: Ruff passes; Pytest and Vitest report no collection/import failures.

- [x] **Step 7: Commit**

```powershell
git add .gitignore .env.example pyproject.toml uv.lock backend frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts
git commit -m "chore: scaffold RecallOps workspace"
```

---

### Task 2: Configuration, app factory, and safe health endpoint

**Files:**

- Create: `backend/src/recallops/config.py`
- Create: `backend/src/recallops/main.py`
- Create: `backend/src/recallops/api/health.py`
- Create: `backend/tests/unit/test_config.py`
- Create: `backend/tests/api/test_health.py`

- [x] **Step 1: Write failing configuration tests**

Create `backend/tests/unit/test_config.py`:

```python
from recallops.config import Settings


def test_defaults_use_fake_memory_and_protect_reserve() -> None:
    settings = Settings(_env_file=None)
    assert settings.cognee_mode == "fake"
    assert settings.cognee_dataset == "recallops_evidence_v1"
    assert settings.cognee_token_supply == 14_000_000
    assert settings.cognee_protected_reserve == 6_000_000


def test_settings_repr_does_not_expose_api_key() -> None:
    settings = Settings(cognee_api_key="super-secret", _env_file=None)
    assert "super-secret" not in repr(settings)
```

- [x] **Step 2: Run the tests and verify the import failure**

Run:

```powershell
uv run pytest backend/tests/unit/test_config.py -v
```

Expected: FAIL because `recallops.config` does not exist.

- [x] **Step 3: Implement typed settings**

Implement `Settings` with `env_prefix="APP_"`, `SecretStr` for the key, literal
`cognee_mode` values `fake|live`, `database_url`, origin, demo token, dataset,
token supply, protected reserve, and these validators:

```python
@model_validator(mode="after")
def validate_budget(self) -> "Settings":
    if self.cognee_protected_reserve >= self.cognee_token_supply:
        raise ValueError("protected reserve must be smaller than token supply")
    if self.cognee_mode == "live" and (
        not self.cognee_base_url or self.cognee_api_key is None
    ):
        raise ValueError("live Cognee mode requires base URL and API key")
    return self
```

Map unprefixed cloud environment variables explicitly:

```python
cognee_base_url: str | None = Field(default=None, validation_alias="COGNEE_BASE_URL")
cognee_api_key: SecretStr | None = Field(default=None, validation_alias="COGNEE_API_KEY")
```

- [x] **Step 4: Write the failing health API test**

Create `backend/tests/api/test_health.py`:

```python
from fastapi.testclient import TestClient

from recallops.main import create_app


def test_health_is_safe_and_reports_fake_mode() -> None:
    response = TestClient(create_app()).get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["memory"]["mode"] == "fake"
    assert body["demo_mode"] is True
    assert "api_key" not in response.text.lower()
    assert "secret" not in response.text.lower()
```

Run:

```powershell
uv run pytest backend/tests/api/test_health.py -v
```

Expected: FAIL because the app factory does not exist.

- [x] **Step 5: Implement the app factory and health route**

`create_app(settings: Settings | None = None)` must store settings in
`app.state.settings`, add a UUID request ID to response header `X-Request-ID`,
mount an `/api/health` router, and return:

```json
{
  "status": "ok",
  "database": "ok",
  "memory": {"mode": "fake", "reachable": true, "dataset_ready": true},
  "demo_mode": true,
  "credit_guard": {"protected_reserve": 6000000}
}
```

Do not include configured URLs, tokens, or credential presence flags.

- [x] **Step 6: Run quality checks**

Run:

```powershell
uv run pytest backend/tests/unit/test_config.py backend/tests/api/test_health.py -v
uv run ruff check backend
uv run mypy
```

Expected: all commands pass.

- [x] **Step 7: Commit**

```powershell
git add backend
git commit -m "feat: add safe application configuration and health"
```

---

### Task 3: Database schema and domain state machines

**Files:**

- Create: `backend/src/recallops/db.py`
- Create: `backend/src/recallops/domain/enums.py`
- Create: `backend/src/recallops/domain/models.py`
- Create: `backend/src/recallops/domain/schemas.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`
- Create: `backend/tests/unit/test_domain.py`
- Create: `backend/tests/unit/test_database.py`

- [x] **Step 1: Write failing domain transition tests**

Create tests that assert:

```python
def test_incident_can_only_resolve_with_complete_resolution() -> None:
    incident = IncidentRecord.active_demo()
    with pytest.raises(InvalidTransition, match="root cause"):
        incident.resolve(
            root_cause="",
            mitigation="Rolled back TTL configuration.",
            verification="Checkout p95 recovered.",
            reference_count=2,
        )


def test_verified_candidate_can_be_promoted() -> None:
    assert MemoryCandidateState.VERIFIED.can_transition_to(
        MemoryCandidateState.PROMOTED
    )


def test_rejected_session_hypothesis_cannot_be_marked_forgotten() -> None:
    assert not MemoryCandidateState.REJECTED.can_transition_to(
        MemoryCandidateState.FORGOTTEN
    )
```

Run:

```powershell
uv run pytest backend/tests/unit/test_domain.py -v
```

Expected: FAIL because domain types do not exist.

- [x] **Step 2: Implement domain enums and transition policy**

Define string enums for:

- `IncidentSeverity`: `SEV1`, `SEV2`, `SEV3`
- `IncidentStatus`: `draft`, `active`, `mitigated`, `resolved`
- `EvidenceKind`: `runbook`, `postmortem`, `deploy`, `log`, `note`, `url`,
  `memory_candidate`
- `EvidenceStatus`: `queued`, `processing`, `ready`, `failed`, `forgotten`
- `ObservationSource`: `human`, `system`, `recallops`
- `MemoryCandidateState`: `proposed`, `pinned`, `verified`, `promoted`,
  `rejected`, `forgotten`, `superseded`
- `VerificationState`: `referenced`, `unverified`, `contradicted`
- `PromotionState`: `not_requested`, `promotion_pending`, `promoted`,
  `promotion_failed`

Encode allowed candidate transitions as an immutable mapping. Raise
`InvalidTransition` for invalid incident resolution or candidate movement.

- [x] **Step 3: Write failing persistence tests**

Use an async in-memory SQLite engine and assert:

```python
async def test_initial_schema_persists_incident_and_evidence(session: AsyncSession) -> None:
    incident = Incident(id="INC-2048", title="Checkout outage", severity="SEV1",
                        service="checkout-api", status="active",
                        session_id="incident:INC-2048", started_at=DEMO_START)
    evidence = EvidenceItem(data_id=STALE_DATA_ID, dataset="recallops_evidence_v1",
                            name="stale-cache-reset-rule.md", kind="runbook",
                            status="ready", content_hash="sha256:fixture")
    session.add_all([incident, evidence])
    await session.commit()
    assert await session.get(Incident, "INC-2048") is not None
    assert await session.get(EvidenceItem, STALE_DATA_ID) is not None
```

- [x] **Step 4: Implement SQLAlchemy models and migration**

Create tables:

- `incidents`
- `evidence_items`
- `observations`
- `memory_candidates`
- `recall_traces`
- `recall_references`
- `feedback`
- `resolutions`
- `memory_operations`
- `credit_ledger`

Use UUID strings for portable SQLite behavior. Add unique constraints for
`evidence_items(dataset, content_hash)` and `incidents(session_id)`. Use UTC
timestamps and explicit relationships with cascade only for local dependent
records. The migration must create all tables from an empty database.

- [x] **Step 5: Verify the migration and tests**

Run:

```powershell
uv run alembic -c backend/alembic.ini upgrade head
uv run pytest backend/tests/unit/test_domain.py backend/tests/unit/test_database.py -v
uv run alembic -c backend/alembic.ini downgrade base
uv run alembic -c backend/alembic.ini upgrade head
```

Expected: migration succeeds in both directions; tests pass.

- [x] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: add incident memory domain and persistence"
```

---

### Task 4: Memory contract, normalization, and deterministic fake

**Files:**

- Create: `backend/src/recallops/memory/contract.py`
- Create: `backend/src/recallops/memory/normalize.py`
- Create: `backend/src/recallops/memory/fake.py`
- Create: `backend/tests/contract/test_memory_contract.py`
- Create: `backend/tests/unit/test_recall_normalize.py`
- Create: `backend/tests/fixtures/cognee/graph-recall.json`

- [x] **Step 1: Write the adapter contract test**

The same async test suite must run against any `CogneeMemoryPort`. Required
behavior:

```python
async def exercise_memory_contract(memory: CogneeMemoryPort) -> None:
    receipt = await memory.remember_evidence(
        EvidencePayload(
            data_id="11111111-1111-4111-8111-111111111111",
            name="postmortem-inc-1842.md",
            content="INC-1842 was caused by a seconds-to-milliseconds TTL mismatch.",
            dataset="recallops_evidence_v1",
        )
    )
    assert receipt.status == "completed"

    await memory.remember_observation(
        session_id="incident:INC-2048",
        content="Redis session misses rose after deploy-418.",
    )
    results = await memory.recall(
        RecallRequest(
            query="How is deploy-418 related to the Redis incident?",
            dataset="recallops_evidence_v1",
            session_id="incident:INC-2048",
            include_trace=True,
        )
    )
    assert results[0].references[0].document_name == "postmortem-inc-1842.md"

    improved = await memory.improve_session(
        dataset="recallops_evidence_v1",
        session_ids=["incident:INC-2048"],
    )
    assert improved.status == "completed"

    forgotten = await memory.forget_evidence_item(
        dataset="recallops_evidence_v1",
        data_id="11111111-1111-4111-8111-111111111111",
    )
    assert forgotten.status == "deleted"
```

Run it against `FakeCogneeAdapter`; expect an import failure first.

- [x] **Step 2: Define SDK-independent dataclasses and protocol**

`contract.py` must define concrete frozen dataclasses:

- `EvidencePayload`
- `RememberReceipt`
- `RecallRequest`
- `RecallReference`
- `RecallEntry`
- `ImproveReceipt`
- `ForgetReceipt`
- `DatasetStatus`
- `MemoryHealth`

Define `CogneeMemoryPort` with the seven methods approved in the design. Use
plain Python values only; no Cognee classes may appear in signatures.

- [x] **Step 3: Implement recall normalization from a recorded response**

Record a representative verbose graph response in
`backend/tests/fixtures/cognee/graph-recall.json`, with `_source`, answer,
search type, and one reference containing `data_id`, `chunk_id`,
`document_name`, and snippet. Implement:

```python
def normalize_recall(raw: object) -> list[RecallEntry]:
    rows = raw if isinstance(raw, list) else [raw]
    entries: list[RecallEntry] = []
    for row in rows:
        if isinstance(row, str):
            entries.append(
                RecallEntry(
                    answer=row,
                    source="graph",
                    search_type="unknown",
                    references=(),
                    raw_kind="string",
                )
            )
            continue
        if not isinstance(row, dict):
            raise RecallContractError(f"unsupported recall row: {type(row).__name__}")
        entries.append(normalize_recall_dict(row))
    return entries
```

Tests must cover a string, a dictionary, a list, absent references, malformed
rows, and alternate reference key names.

- [x] **Step 4: Implement the deterministic fake adapter**

The fake must:

- Store evidence by dataset and stable ID.
- Store observations by session.
- Return the historical `INC-1842` answer for the relationship query.
- Include the stale runbook reference before deletion.
- Exclude it after `forget_evidence_item`.
- Bridge the verified `INC-2048` resolution after `improve_session`.
- Return that resolution in a new session.
- Expose configurable failures for remember, recall, improve, and forget.
- Count operations but never estimate real billing.

- [x] **Step 5: Run contract and normalization tests**

Run:

```powershell
uv run pytest backend/tests/contract/test_memory_contract.py backend/tests/unit/test_recall_normalize.py -v
uv run ruff check backend
uv run mypy
```

Expected: all tests pass and only `memory/cognee_cloud.py` remains allowed to
import Cognee later.

- [x] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: define portable Cognee memory contract"
```

---

### Task 5: Credit guard and memory-operation audit log

**Files:**

- Create: `backend/src/recallops/services/credit_guard.py`
- Create: `backend/src/recallops/repositories/audit.py`
- Create: `backend/tests/unit/test_credit_guard.py`
- Create: `backend/tests/unit/test_audit_log.py`

- [x] **Step 1: Write failing budget policy tests**

Create exact cases:

```python
def test_heavy_operation_is_blocked_at_reserve_boundary() -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)
    guard.record_estimate("remember", 7_800_000)
    with pytest.raises(CreditBudgetExceeded):
        guard.authorize("improve", estimated_tokens=300_000, essential=False)


def test_final_demo_operation_can_use_rehearsal_allowance_not_reserve() -> None:
    guard = CreditGuard(supply=14_000_000, protected_reserve=6_000_000)
    guard.record_estimate("remember", 7_000_000)
    decision = guard.authorize("recall", estimated_tokens=10_000, essential=True)
    assert decision.allowed is True
    assert decision.remaining_after == 6_990_000
```

The second assertion means an essential action is allowed only while the result
remains above the reserve.

- [x] **Step 2: Implement fail-closed authorization**

`authorize()` returns a decision with `allowed`, `reason`,
`remaining_before`, and `remaining_after`. Reject negative estimates, unknown
operation names, and every action that crosses the protected reserve. Define
default estimates:

```python
DEFAULT_ESTIMATES = {
    "remember": 250_000,
    "recall": 20_000,
    "improve": 300_000,
    "forget": 10_000,
}
```

These are conservative internal accounting values, not claims about Cognee
billing.

- [x] **Step 3: Write and implement audit repository tests**

Every memory operation record must include:

- request correlation ID
- incident ID when applicable
- trace ID when applicable
- operation
- dataset
- safe target ID
- started/finished timestamp
- duration
- success
- safe error category
- estimated token charge

Test that a key-like string passed as error detail is redacted to
`[REDACTED]`. Never persist raw request headers or response payloads.

- [x] **Step 4: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_credit_guard.py backend/tests/unit/test_audit_log.py -v
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```powershell
git add backend
git commit -m "feat: protect Cognee credits and audit memory actions"
```

---

### Task 6: Live Cognee Cloud contract probe and adapter

**Files:**

- Create: `scripts/cognee_contract_probe.py`
- Create: `backend/src/recallops/memory/cognee_cloud.py`
- Create: `backend/tests/integration/test_cognee_live.py`
- Create: `backend/tests/fixtures/cognee/live-contract.json`

- [ ] **Step 1: Build a zero-mutation connectivity probe**

The default probe must only call:

```python
import cognee

cognee.serve(url=settings.cognee_base_url, api_key=settings.api_key)
datasets = await cognee.datasets.list_datasets()
print(json.dumps({"connected": True, "dataset_count": len(datasets)}))
```

It must obtain the key via `SecretStr.get_secret_value()` and never print
settings or exceptions containing request headers. Running without
`RUN_COGNEE_INTEGRATION=1` must exit with:

```text
Live Cognee probe skipped: set RUN_COGNEE_INTEGRATION=1
```

- [ ] **Step 2: Run the read-only probe once**

Run:

```powershell
$env:RUN_COGNEE_INTEGRATION='1'
uv run python scripts/cognee_contract_probe.py --read-only
Remove-Item Env:RUN_COGNEE_INTEGRATION
```

Expected: JSON containing `"connected": true`; no API key appears.

- [ ] **Step 3: Write live adapter integration tests behind a hard gate**

At module level:

```python
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_COGNEE_INTEGRATION") != "1",
        reason="live Cognee integration is opt-in",
    ),
]
```

Use one small, versioned contract item in `recallops_evidence_v1`. Never create
a random dataset per run. The test order is remember one tiny item, recall it,
forget that exact item, and verify it is absent. The test must not run improve;
the full improve proof happens once in Task 21.

- [ ] **Step 4: Implement `CogneeCloudAdapter`**

Initialize once:

```python
cognee.serve(url=base_url, api_key=api_key)
```

Map port methods to:

```python
await cognee.remember(
    data_items,
    dataset_name=payload.dataset,
    self_improvement=False,
    run_in_background=False,
)

await cognee.remember(
    content,
    session_id=session_id,
    self_improvement=False,
)

await cognee.recall(
    query_text=request.query,
    datasets=[request.dataset],
    session_id=request.session_id,
    verbose=request.include_trace,
)

await cognee.improve(dataset=dataset, session_ids=session_ids)

await cognee.forget(dataset=dataset, data_id=data_id)
```

Construct Cognee `DataItem` objects with stable UUIDs after confirming the
installed 1.2.2 import path in the read-only introspection command:

```powershell
uv run python -c "import inspect,cognee; print(inspect.signature(cognee.remember)); print(inspect.signature(cognee.recall)); print(inspect.signature(cognee.improve)); print(inspect.signature(cognee.forget))"
```

Record only field names and redacted response shapes in `live-contract.json`.
If installed signatures differ from the official v1.0 operation names, keep the
port unchanged and adapt here.

- [ ] **Step 5: Verify offline behavior does not touch the network**

Run:

```powershell
uv run pytest backend/tests/integration/test_cognee_live.py -v
```

Expected: SKIPPED with the opt-in reason.

- [ ] **Step 6: Run one controlled live adapter contract**

First inspect the Cognee billing dashboard and proceed only if at least
13,000,000 tokens remain. Then run:

```powershell
$env:RUN_COGNEE_INTEGRATION='1'
uv run pytest backend/tests/integration/test_cognee_live.py -v -s
Remove-Item Env:RUN_COGNEE_INTEGRATION
```

Expected: remember, recall, item-level forget, and absence verification pass;
the test deletes only its own stable item.

- [ ] **Step 7: Commit**

```powershell
git add scripts backend
git commit -m "feat: connect isolated Cognee Cloud adapter"
```

---

### Task 7: Synthetic demo fixtures and idempotent seeding

**Files:**

- Create: all seven files under `demo/fixtures/`
- Create: `backend/src/recallops/services/demo.py`
- Create: `backend/src/recallops/api/demo.py`
- Create: `backend/tests/unit/test_demo_service.py`
- Create: `backend/tests/api/test_demo_api.py`

- [ ] **Step 1: Write the complete fixture narrative**

Use stable IDs in `incident-2048-timeline.json`:

```json
{
  "incident": {
    "id": "INC-2048",
    "title": "Checkout latency and session failures after deploy-418",
    "severity": "SEV1",
    "service": "checkout-api",
    "status": "active",
    "session_id": "incident:INC-2048",
    "started_at": "2026-06-28T08:10:00Z"
  },
  "observations": [
    {
      "timestamp": "2026-06-28T08:10:00Z",
      "source": "system",
      "content": "Checkout p95 latency exceeded 4 seconds."
    },
    {
      "timestamp": "2026-06-28T08:12:00Z",
      "source": "system",
      "content": "Redis session misses increased 640 percent."
    },
    {
      "timestamp": "2026-06-28T08:14:00Z",
      "source": "human",
      "content": "Symptoms began within ten minutes of deploy-418."
    }
  ]
}
```

Fixture facts:

- `postmortem-inc-1842.md`: previous TTL unit mismatch.
- `checkout-runbook-v3.md`: valid rollback and session-reissue procedure.
- `stale-cache-reset-rule.md`: obsolete flush-all/reset rule, explicitly dated.
- `deploy-418.json`: `SESSION_TTL_MS=1800000` replaced a seconds-based field
  without conversion in the checkout session adapter.
- `checkout-errors.log`: Redis session miss and latency lines.
- Include evidence against the payment-gateway hypothesis.
- `expected-retrieval.json`: ten golden questions with expected documents,
  required concepts, and forbidden claims.

- [ ] **Step 2: Write failing idempotency tests**

Assert two calls to `DemoService.seed()`:

- Produce the same stable data IDs.
- Create one local row per fixture.
- Call fake `remember_evidence` once per fixture total.
- Never delete unrelated evidence.

Derive IDs with UUIDv5:

```python
DEMO_NAMESPACE = UUID("3d1d4c42-7e30-5e58-9e85-301ea55efcc1")
data_id = str(uuid5(DEMO_NAMESPACE, fixture_relative_path))
```

- [ ] **Step 3: Implement reset and seed**

`reset()` restores local demo incident, observations, candidates, and trace
state, but never calls Cognee forget. `seed()` hashes fixture bytes, reuses
matching evidence rows, ingests only missing/changed items, and returns:

```json
{
  "dataset": "recallops_evidence_v1",
  "seeded": 6,
  "reused": 0,
  "failed": 0,
  "ready": true
}
```

The timeline metadata file is local-only and is not remembered as evidence.

- [ ] **Step 4: Protect mutation endpoints**

`POST /api/demo/reset` is available in local/demo mode. `POST /api/demo/seed`
requires header `X-Demo-Admin-Token` matching the configured token. Compare
tokens with `secrets.compare_digest`. Return 401 without saying which part was
wrong.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_demo_service.py backend/tests/api/test_demo_api.py -v
```

Expected: all idempotency and auth tests pass.

- [ ] **Step 6: Commit**

```powershell
git add demo backend
git commit -m "feat: add deterministic checkout outage demo"
```

---

### Task 8: Evidence library and verified item-level forgetting

**Files:**

- Create: `backend/src/recallops/repositories/evidence.py`
- Create: `backend/src/recallops/services/evidence.py`
- Create: `backend/src/recallops/services/lifecycle.py`
- Create: `backend/src/recallops/api/evidence.py`
- Create: `backend/tests/unit/test_evidence_service.py`
- Create: `backend/tests/unit/test_forget_lifecycle.py`
- Create: `backend/tests/api/test_evidence_api.py`

- [ ] **Step 1: Write upload validation tests**

Cover:

- accepted `.md`, `.txt`, `.json`, `.log`, `.pdf`
- rejected executable and double-extension filenames
- 5 MB local limit
- 1 MB public-demo limit
- arbitrary upload rejected in public demo
- identical hash returns existing item without a memory call
- filename is display-only and cannot control a filesystem path

- [ ] **Step 2: Implement evidence ingestion**

Read uploads into bounded memory, sanitize the name with `Path(name).name`,
validate content type and extension independently, calculate SHA-256, create a
stable UUIDv5 from dataset plus hash, and pass bytes/text through the memory
port. State progression:

```text
queued -> processing -> ready
                    `-> failed
```

Never store uploaded content under the repository root. Public demo accepts
only seeded fixtures.

- [ ] **Step 3: Write verified-forget tests**

Required request:

```json
{
  "confirmation": "FORGET stale-cache-reset-rule.md",
  "verification_query": "\"flush all Redis cache\""
}
```

Test success only when:

1. Item is permanent and `ready`.
2. Confirmation matches exactly.
3. `forget_evidence_item` returns deleted.
4. Follow-up recall contains no reference with that `data_id`.
5. Local state becomes `forgotten`.

Test that failure at steps 3 or 4 leaves the item visible and records a failed
audit event.

- [ ] **Step 4: Implement evidence routes**

Implement:

- `POST /api/evidence`
- `GET /api/evidence`
- `GET /api/evidence/{data_id}`
- `GET /api/evidence/{data_id}/status`
- `DELETE /api/evidence/{data_id}`

Use 404 for missing IDs, 409 for state conflicts, 413 for size, 415 for type,
422 for confirmation mismatch, and 503 for memory-provider failures.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_evidence_service.py backend/tests/unit/test_forget_lifecycle.py backend/tests/api/test_evidence_api.py -v
```

Expected: all tests pass, including before/after recall proof.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: manage evidence and verify selective forgetting"
```

---

### Task 9: Incident lifecycle and session observations

**Files:**

- Create: `backend/src/recallops/repositories/incidents.py`
- Create: `backend/src/recallops/services/incidents.py`
- Create: `backend/src/recallops/api/incidents.py`
- Create: `backend/tests/unit/test_incident_service.py`
- Create: `backend/tests/api/test_incidents_api.py`

- [ ] **Step 1: Write incident creation tests**

Assert:

- supplied ID must match `INC-[0-9]{1,8}`
- session ID is always server-generated as `incident:<id>`
- title and service are stripped and length-bounded
- duplicate ID returns conflict
- status starts `active`

- [ ] **Step 2: Implement create, list, and detail**

Routes:

- `POST /api/incidents`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`

The detail response contains incident, ordered observations, latest recalls,
candidate states, resolution state, and safe budget status.

- [ ] **Step 3: Write observation failure/retry tests**

When memory succeeds, persist `session_stored`. When memory is unavailable,
persist observation locally as `pending` and return 202 with
`memory_status="pending"`; a retry must reuse the same observation ID and avoid
creating a duplicate.

- [ ] **Step 4: Implement session remember**

`POST /api/incidents/{incident_id}/observe` validates 1-4000 characters and
calls:

```python
await memory.remember_observation(
    session_id=incident.session_id,
    content=observation.content,
)
```

It must explicitly rely on the adapter's `self_improvement=False` policy. An
observation is not permanent and the UI/API must not describe it as promoted.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_incident_service.py backend/tests/api/test_incidents_api.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: add incidents and short-term session observations"
```

---

### Task 10: Evidence-backed recall traces

**Files:**

- Create: `backend/src/recallops/repositories/recalls.py`
- Create: `backend/src/recallops/services/recall.py`
- Modify: `backend/src/recallops/api/incidents.py`
- Create: `backend/tests/unit/test_recall_service.py`
- Create: `backend/tests/api/test_recall_api.py`

- [ ] **Step 1: Write verification policy tests**

Cases:

```python
assert verification_for(entries_with_reference) == VerificationState.REFERENCED
assert verification_for(entries_without_reference) == VerificationState.UNVERIFIED
assert verification_for(entries_with_contradiction) == VerificationState.CONTRADICTED
```

Also assert an unverified trace cannot be selected as resolution evidence.

- [ ] **Step 2: Implement scoped recall**

`RecallService.ask()` must authorize the credit estimate, call the memory port
with exact dataset and incident session, normalize entries, create one trace
UUID, persist references, and return:

```json
{
  "answer": "INC-1842 is the closest prior incident because both outages followed a checkout deployment that changed Redis session TTL behavior.",
  "verification": "referenced",
  "source": "graph",
  "search_type": "GRAPH_COMPLETION_CONTEXT_EXTENSION",
  "references": [
    {
      "data_id": "stable-uuid",
      "chunk_id": "chunk-uuid",
      "document_name": "postmortem-inc-1842.md",
      "snippet": "The checkout session TTL changed from seconds to milliseconds without conversion."
    }
  ],
  "trace_id": "trace-uuid",
  "why_recalled": [
    "same service: checkout-api",
    "same dependency: Redis",
    "same symptom: session misses",
    "same timing: immediately after deployment"
  ]
}
```

`why_recalled` is derived only from returned graph/reference facts or the
deterministic fixture contract; do not invent graph paths.

- [ ] **Step 3: Implement no-result and provider-error behavior**

- Empty recall -> 200, `answer=null`, `verification="unverified"`,
  `no_result=true`.
- Indexing in progress -> 202, `partial_memory=true`.
- Provider unavailable -> 503 with safe error code
  `MEMORY_PROVIDER_UNAVAILABLE`.
- Missing references -> answer shown but promotion disabled.

- [ ] **Step 4: Add recall route and trace lookup**

Implement:

- `POST /api/incidents/{incident_id}/recall`
- `GET /api/incidents/{incident_id}/recalls/{trace_id}`

Query length is 3-1000 characters. Public demo permits at most 20 recalls per
browser demo session; return 429 with reset guidance after the limit.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_recall_service.py backend/tests/api/test_recall_api.py -v
```

Expected: relationship query returns referenced evidence; error tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: provide auditable graph-backed incident recall"
```

---

### Task 11: Feedback, resolution validation, and controlled improve

**Files:**

- Modify: `backend/src/recallops/services/lifecycle.py`
- Modify: `backend/src/recallops/api/incidents.py`
- Create: `backend/tests/unit/test_resolution_lifecycle.py`
- Create: `backend/tests/api/test_resolution_api.py`

- [ ] **Step 1: Write feedback tests**

`POST /api/incidents/{id}/feedback` accepts:

```json
{
  "trace_id": "trace-uuid",
  "score": 1,
  "explanation": "The Redis relationship and cited postmortem were correct."
}
```

Score is `-1`, `0`, or `1`; explanation is 5-500 characters. A trace must
belong to the incident. Store local feedback and write a session observation
that Cognee can bridge during improve.

- [ ] **Step 2: Write resolution gate tests**

Reject unless all exist:

- non-empty root cause
- non-empty mitigation
- non-empty verification
- at least one referenced trace
- explicit `confirmed_by_human=true`

On improve failure, resolution remains stored with
`promotion_state="promotion_failed"`. On success it becomes `promoted`.

- [ ] **Step 3: Implement controlled resolution**

Request:

```json
{
  "root_cause": "deploy-418 passed millisecond TTL values to a seconds-based Redis adapter.",
  "mitigation": "Rolled back the TTL configuration and reissued affected sessions.",
  "verification": "Checkout p95 returned below 450 ms and session misses returned to baseline.",
  "trace_ids": ["trace-uuid"],
  "confirmed_by_human": true
}
```

Before improve, remember a compact verified resolution in the incident session.
Then call:

```python
await memory.improve_session(
    dataset=settings.cognee_dataset,
    session_ids=[incident.session_id],
)
```

Update incident to resolved only after the improve succeeds. If improve fails,
keep it mitigated so the UI tells the truth.

- [ ] **Step 4: Prove clean-session recall with the fake**

After resolution, ask from `incident:INC-2099`:

```text
What verified mitigation fixed INC-2048?
```

Assert the response mentions TTL rollback and session reissue, comes from
permanent graph memory, and has the promoted resolution reference.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest backend/tests/unit/test_resolution_lifecycle.py backend/tests/api/test_resolution_api.py -v
uv run pytest backend/tests -m "not integration"
```

Expected: all offline backend tests pass.

- [ ] **Step 6: Commit**

```powershell
git add backend
git commit -m "feat: improve memory from human-verified resolutions"
```

---

### Task 12: Frontend foundation and typed API client

**Files:**

- Create: `frontend/src/main.tsx`
- Create: `frontend/src/router.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/app/AppShell.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/app/AppShell.test.tsx`
- Create: `frontend/src/components/StatusBadge.tsx`
- Create: `frontend/src/components/OperationBanner.tsx`

- [ ] **Step 1: Write the failing shell test**

```tsx
it("reserves root and exposes the application navigation", async () => {
  renderWithRouter(<AppShell />);
  expect(screen.getByRole("link", { name: /incidents/i })).toHaveAttribute(
    "href",
    "/app",
  );
  expect(screen.getByRole("link", { name: /evidence/i })).toHaveAttribute(
    "href",
    "/app/evidence",
  );
  expect(screen.getByText(/synthetic demo/i)).toBeVisible();
});
```

Run:

```powershell
npm --prefix frontend run test -- AppShell.test.tsx
```

Expected: FAIL because the shell does not exist.

- [ ] **Step 2: Implement routing and provider setup**

Routes:

```tsx
<Route path="/" element={<Navigate to="/app" replace />} />
<Route path="/app" element={<DemoHome />} />
<Route path="/app/evidence" element={<EvidenceLibrary />} />
<Route path="/app/incidents/:incidentId" element={<IncidentCockpit />} />
<Route path="/app/memory" element={<MemoryExplorer />} />
<Route path="/app/resolutions/:incidentId" element={<ResolutionReport />} />
```

Wrap Router with `QueryClientProvider`. Configure TanStack Query with one retry
for reads and zero automatic retries for mutations.

- [ ] **Step 3: Implement a runtime-validated API client**

All responses must pass Zod schemas. `ApiError` contains HTTP status,
application code, safe message, and request ID. `request()` sets JSON headers,
includes credentials, accepts `AbortSignal`, and never logs response bodies.

- [ ] **Step 4: Implement the application visual system**

This is the operational product UI, not the marketing landing page.

- Dark neutral canvas.
- Warm white primary text.
- Amber for investigating/partial.
- Cyan for session memory.
- Violet for permanent graph memory.
- Green only for verified/promoted.
- Red only for destructive/error states.
- Dense but readable 12-column grid.
- Monospace IDs and timestamps.
- Visible focus rings, keyboard navigation, reduced-motion support.
- No gradients as decoration and no generic chat-bubble layout.

- [ ] **Step 5: Verify**

Run:

```powershell
npm --prefix frontend run test
npm --prefix frontend run build
```

Expected: tests pass and Vite production build succeeds.

- [ ] **Step 6: Commit**

```powershell
git add frontend
git commit -m "feat: establish RecallOps application shell"
```

---

### Task 13: Demo home and evidence library UI

**Files:**

- Create: `frontend/src/features/demo/DemoHome.tsx`
- Create: `frontend/src/features/demo/DemoHome.test.tsx`
- Create: `frontend/src/features/evidence/EvidenceLibrary.tsx`
- Create: `frontend/src/features/evidence/EvidenceCard.tsx`
- Create: `frontend/src/features/evidence/EvidenceLibrary.test.tsx`

- [ ] **Step 1: Write the demo-start test**

Mock `/api/demo/reset`, then verify **Load Checkout Outage Demo** navigates to
`/app/incidents/INC-2048`. If reset succeeds but seed is required, show one
admin-token seed action in local mode; public mode shows contact/setup guidance
instead of exposing a token field.

- [ ] **Step 2: Implement the demo home**

Show:

- one-sentence problem
- one synthetic-data badge
- checkout demo card
- dataset readiness
- remaining internal budget estimate
- **Load Checkout Outage Demo**
- link to evidence library

Do not build hero marketing content here.

- [ ] **Step 3: Write evidence-state tests**

Render `queued`, `processing`, `ready`, `failed`, and `forgotten`. A forgotten
item remains in audit history but is visually excluded from active evidence.
Public demo shows no upload control.

- [ ] **Step 4: Implement evidence library**

Each card displays document name, kind, stable short ID, ingestion state,
source date, and memory layer. The stale fixture has a visible **Stale** marker
only because fixture metadata explicitly says it is obsolete.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm --prefix frontend run test -- DemoHome.test.tsx EvidenceLibrary.test.tsx
npm --prefix frontend run build
git add frontend
git commit -m "feat: add demo launcher and evidence library"
```

Expected: tests and build pass before commit.

---

### Task 14: Incident cockpit and observation timeline

**Files:**

- Create: `frontend/src/features/incidents/IncidentCockpit.tsx`
- Create: `frontend/src/features/incidents/IncidentHeader.tsx`
- Create: `frontend/src/features/incidents/ObservationTimeline.tsx`
- Create: `frontend/src/features/incidents/ObservationComposer.tsx`
- Create: `frontend/src/features/incidents/RecallComposer.tsx`
- Create: `frontend/src/features/incidents/IncidentCockpit.test.tsx`

- [ ] **Step 1: Write the cockpit rendering test**

Given seeded API data, assert the screen shows:

- `INC-2048`
- `SEV1`
- `checkout-api`
- deploy-418
- 4-second p95
- 640-percent Redis miss increase
- observation composer
- recall question input
- Memory Inspector region

- [ ] **Step 2: Implement the three-column cockpit**

Desktop:

```text
240px navigation | minmax(0, 1fr) incident stream | 380px inspector
```

Below 1100px, inspector becomes a right drawer. Below 760px, navigation
collapses and content remains fully operable. Keep the judge flow above the
fold at 1440x900.

- [ ] **Step 3: Implement optimistic observation behavior**

Add observation immediately as `pending`, replace with `session_stored` on
success, keep pending with a retry button on 202/degraded response, and never
label it permanent.

- [ ] **Step 4: Implement recall input**

Pre-fill the judge query when `?demo=checkout`:

```text
How is deploy-418 related to the previous Redis incident?
```

Submit on button or Ctrl/Cmd+Enter. Display an in-progress operation row instead
of an indefinite spinner. Cancel stale requests on route change.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm --prefix frontend run test -- IncidentCockpit.test.tsx
npm --prefix frontend run build
git add frontend
git commit -m "feat: build the live incident cockpit"
```

Expected: tests and build pass.

---

### Task 15: Recall result and Memory Inspector

**Files:**

- Create: `frontend/src/features/memory/RecallResult.tsx`
- Create: `frontend/src/features/memory/MemoryInspector.tsx`
- Create: `frontend/src/features/memory/ReferenceList.tsx`
- Create: `frontend/src/features/memory/MemoryInspector.test.tsx`
- Create: `frontend/src/features/memory/ForgetDialog.tsx`
- Create: `frontend/src/features/memory/ForgetDialog.test.tsx`

- [ ] **Step 1: Write provenance rendering tests**

For a referenced trace, assert visible:

- graph source
- search type
- document name
- chunk ID
- snippet
- four `why_recalled` reasons
- `referenced` status

For missing references, assert `unverified` and no promote action.

- [ ] **Step 2: Implement RecallResult and inspector**

Answer content must be plain rendered text, not raw HTML. Reference buttons
open the inspector at the exact document/chunk. Use semantic `<aside>`,
`<details>`, and accessible tabs for **Evidence**, **Path**, and **Lifecycle**.

- [ ] **Step 3: Write destructive-action tests**

The forget dialog must:

- show exact item name and data ID
- show that graph/vector representations are affected
- require typing `FORGET <filename>`
- call delete only when exact
- show a two-step progress state: deleting, verifying
- show before/after reference result
- remain open with error if verification fails

- [ ] **Step 4: Implement item-level forget UI**

Only permanent `ready` evidence exposes **Forget memory**. Session hypotheses
expose **Reject hypothesis**, which is a local/session lifecycle action and does
not call the forget endpoint. This distinction must be visible in copy.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm --prefix frontend run test -- MemoryInspector.test.tsx ForgetDialog.test.tsx
npm --prefix frontend run build
git add frontend
git commit -m "feat: expose memory provenance and truthful forgetting"
```

Expected: tests and build pass.

---

### Task 16: Memory relationship graph and verified resolution flow

**Files:**

- Create: `frontend/src/features/memory/MemoryExplorer.tsx`
- Create: `frontend/src/features/memory/MemoryGraph.tsx`
- Create: `frontend/src/features/memory/MemoryGraph.test.tsx`
- Create: `frontend/src/features/incidents/ResolutionPanel.tsx`
- Create: `frontend/src/features/incidents/ResolutionPanel.test.tsx`
- Create: `frontend/src/features/incidents/ResolutionReport.tsx`

- [ ] **Step 1: Define the graph view model**

Use explicit node types:

```ts
type MemoryNodeKind =
  | "incident"
  | "service"
  | "deployment"
  | "dependency"
  | "symptom"
  | "evidence"
  | "resolution";

type MemoryEdge = {
  id: string;
  source: string;
  target: string;
  label: string;
  evidenceDataId: string;
};
```

Every rendered edge must point to a stored evidence data ID. No decorative or
model-invented relationships.

- [ ] **Step 2: Write graph tests**

Assert seeded path:

```text
deploy-418 -> changed -> session TTL configuration
session TTL configuration -> affects -> Redis sessions
Redis sessions -> caused -> session misses
session misses -> resembles -> INC-1842
```

Clicking an edge opens its evidence reference. Removing the stale item removes
only its associated edge/reference, not unrelated shared nodes.

- [ ] **Step 3: Implement resolution form tests**

Form requires root cause, mitigation, verification, one referenced trace, and
human confirmation. On submit:

- `promotion_pending` disables duplicate submit
- success shows `promoted`
- failure shows `promotion_failed` and retry
- never says learned before success

- [ ] **Step 4: Implement resolution report**

Show verified facts, evidence citations, human confirmation time, improve
operation result, and a **Prove in clean session** action that asks the fixed
question from a new session and displays the resulting permanent-memory source.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
npm --prefix frontend run test -- MemoryGraph.test.tsx ResolutionPanel.test.tsx
npm --prefix frontend run build
git add frontend
git commit -m "feat: visualize causal memory and verified learning"
```

Expected: tests and build pass.

---

### Task 17: Degraded, partial, no-result, and accessibility states

**Files:**

- Create: `frontend/src/components/ErrorBoundary.tsx`
- Create: `frontend/src/components/EmptyState.tsx`
- Create: `frontend/src/features/incidents/IncidentStates.test.tsx`
- Create: `backend/src/recallops/errors.py`
- Create: `backend/tests/api/test_error_contract.py`

- [ ] **Step 1: Lock the backend error envelope**

All non-2xx API responses:

```json
{
  "error": {
    "code": "MEMORY_PROVIDER_UNAVAILABLE",
    "message": "Memory is temporarily unavailable. Your observation is saved locally.",
    "retryable": true,
    "request_id": "uuid"
  }
}
```

Write tests for 401, 404, 409, 413, 415, 422, 429, and 503. Assert stack
traces, URLs, headers, and keys never appear.

- [ ] **Step 2: Implement frontend state tests**

Cover:

- dataset indexing -> partial-memory banner
- Cognee unavailable -> degraded banner plus local observation retry
- no result -> explicit no-memory state and evidence link
- unverified answer -> promotion disabled
- improve failure -> retry without false success
- forget failure -> evidence remains visible

- [ ] **Step 3: Run automated accessibility checks in component tests**

Add `vitest-axe` and assert no violations on AppShell, IncidentCockpit,
MemoryInspector, ForgetDialog, and ResolutionPanel. Test keyboard focus return
after dialogs and `aria-live` for operation completion.

- [ ] **Step 4: Verify and commit**

Run:

```powershell
uv run pytest backend/tests/api/test_error_contract.py -v
npm --prefix frontend run test
npm --prefix frontend run build
git add backend frontend
git commit -m "feat: handle memory failures without false claims"
```

Expected: all commands pass.

---

### Task 18: Browser-level 90-second judge flow

**Files:**

- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/judge-flow.spec.ts`
- Create: `frontend/e2e/degraded-flow.spec.ts`
- Modify: backend test/development dependency injection for fake mode

- [ ] **Step 1: Configure deterministic browser testing**

Playwright starts:

```text
backend: uv run uvicorn recallops.main:app --app-dir backend/src --port 8000
frontend: npm run dev -- --host 127.0.0.1 --port 5173
```

Vite proxies `/api` to port 8000. Browser tests use fake Cognee and a temporary
SQLite file. Enable trace on first retry and screenshot only on failure.

- [ ] **Step 2: Write the complete judge-flow test**

The test must:

1. Open `/app?demo=checkout`.
2. Load/reset the demo.
3. Open `INC-2048`.
4. Submit the relationship question.
5. Assert `INC-1842`, Redis, deployment, and references.
6. Open Memory Inspector and assert the causal path.
7. Forget `stale-cache-reset-rule.md` with typed confirmation.
8. Assert before/after proof.
9. Fill and confirm the correct resolution.
10. Assert promoted state.
11. Run clean-session proof.
12. Assert the verified mitigation is recalled from graph memory.

Use role/label locators, not CSS implementation selectors.

- [ ] **Step 3: Write the degraded-flow test**

Configure fake adapter recall failure, submit an observation, and assert:

- observation remains visible
- degraded mode is explicit
- no recalled answer is fabricated
- retry control appears
- health status reports memory degraded without secrets

- [ ] **Step 4: Verify browser flow**

Run:

```powershell
npx --prefix frontend playwright install chromium
npm --prefix frontend run e2e
```

Expected: both tests pass in Chromium.

- [ ] **Step 5: Commit**

```powershell
git add backend frontend
git commit -m "test: prove the complete RecallOps judge journey"
```

---

### Task 19: Security, logging, and preflight enforcement

**Files:**

- Modify: `backend/src/recallops/main.py`
- Modify: API dependencies and upload handling
- Create: `scripts/preflight.py`
- Create: `backend/tests/unit/test_redaction.py`
- Create: `backend/tests/api/test_security.py`

- [ ] **Step 1: Write security tests**

Assert:

- CORS accepts only configured origin.
- `X-Content-Type-Options: nosniff`.
- `Referrer-Policy: no-referrer`.
- `Content-Security-Policy` allows only the built application needs.
- `X-Frame-Options: DENY`.
- public demo blocks arbitrary upload and URL.
- unsafe URL schemes and private network destinations are rejected in local
  URL mode.
- rate limit blocks excessive recall/mutation.
- request logs redact `authorization`, `x-api-key`, and Cognee key patterns.

- [ ] **Step 2: Implement structured safe logs**

Log JSON with request ID, route template, method, status, duration, incident ID,
trace ID, operation, and safe error category. Never log bodies, full query
text, headers, secrets, or raw Cognee responses.

- [ ] **Step 3: Implement repository preflight**

`scripts/preflight.py` must fail if:

- tracked content contains a value matching configured Cognee key prefix or
  `COGNEE_API_KEY=` with non-empty value
- `.env` is tracked
- live tests lack the opt-in gate
- `forget(everything=True)` appears outside tests that assert prohibition
- application source imports Cognee outside `memory/cognee_cloud.py`
- dataset constants differ from `recallops_evidence_v1`
- landing route `/app` is absent

- [ ] **Step 4: Verify and commit**

Run:

```powershell
uv run pytest backend/tests/unit/test_redaction.py backend/tests/api/test_security.py -v
uv run python scripts/preflight.py
git grep -n "COGNEE_API_KEY=" -- ':!*.example'
```

Expected: tests and preflight pass; Git grep has no output.

Commit:

```powershell
git add backend scripts
git commit -m "security: harden public demo and secret handling"
```

---

### Task 20: Docker, free Hugging Face deployment, CI, and documentation

**Files:**

- Create: `Dockerfile`
- Create: `compose.yaml`
- Create: `.dockerignore`
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `docs/architecture.md`
- Create: `docs/cognee-lifecycle.md`
- Create: `docs/submission-checklist.md`
- Create: `demo/demo-script.md`

- [ ] **Step 1: Build the single production image**

Docker stages:

1. Node stage installs locked frontend dependencies and builds.
2. Python stage installs locked `uv` dependencies.
3. Copy backend and frontend `dist`.
4. Run as non-root user.
5. Listen on `${PORT:-7860}`.
6. Serve frontend assets and SPA fallback from FastAPI.
7. Healthcheck `/api/health`.

`compose.yaml` exposes `7860`, uses fake mode by default, mounts a named SQLite
volume, and reads an optional untracked `.env`.

- [ ] **Step 2: Verify local production deployment**

Run:

```powershell
docker compose up --build -d
Invoke-RestMethod http://127.0.0.1:7860/api/health
docker compose logs --no-color
docker compose down
```

Expected: health returns `status=ok`; logs contain no key or stack trace.

- [ ] **Step 3: Add offline CI**

GitHub Actions must run:

```text
uv sync --frozen --group dev
uv run ruff check backend scripts
uv run mypy
uv run pytest -m "not integration"
npm ci --prefix frontend
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
docker build .
uv run python scripts/preflight.py
```

Do not configure Cognee credentials in pull-request CI.

- [ ] **Step 4: Write the documentation**

README sections:

- problem and impact
- why Cognee is essential
- memory lifecycle diagram
- architecture
- deterministic demo
- local setup
- environment variables without values
- test commands
- deployment
- screenshots
- 90-second video
- known limitations
- synthetic-data disclosure
- AI-assistance disclosure

`docs/cognee-lifecycle.md` must explicitly map UI actions to remember, recall,
improve, and forget and state the limits of session deletion. `demo-script.md`
uses the approved 90-second script exactly.

- [ ] **Step 5: Prepare the Hugging Face Docker Space without paying**

The Space README front matter:

```yaml
---
title: RecallOps
emoji: 🧠
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
---
```

Set only server-side Space secrets `COGNEE_BASE_URL`,
`COGNEE_API_KEY`, and `APP_DEMO_ADMIN_TOKEN`. Keep hardware at free
`cpu-basic`. Do not enable persistent paid storage. The app must regenerate
local demo state from fixtures after a cold start.

- [ ] **Step 6: Verify and commit**

Run:

```powershell
uv run python scripts/preflight.py
uv run pytest -m "not integration"
npm --prefix frontend run test
npm --prefix frontend run build
docker build -t recallops:local .
git diff --check
```

Expected: every command passes.

Commit:

```powershell
git add Dockerfile compose.yaml .dockerignore .github README.md docs demo
git commit -m "docs: package RecallOps for judging and deployment"
```

---

### Task 21: Retrieval evaluation and one controlled live lifecycle proof

**Files:**

- Create: `scripts/evaluate_retrieval.py`
- Create: `backend/tests/integration/test_live_judge_flow.py`
- Create: `outputs/evaluation-report.json` only as an ignored/generated artifact
- Modify: `docs/submission-checklist.md`

- [ ] **Step 1: Implement the offline golden-question evaluator**

Read `demo/fixtures/expected-retrieval.json`, run each question through the fake
adapter, and score:

- expected document present
- required concept present
- forbidden claim absent
- reference parsed

Exit nonzero below:

```text
document recall: 10/10
required concepts: 10/10
forbidden claims: 10/10
reference parsing: 10/10
```

- [ ] **Step 2: Add the gated live judge-flow test**

The live test uses the actual demo dataset and:

1. Verifies fixtures already exist; seeds only missing fixture hashes.
2. Records the three current observations into `incident:INC-2048`.
3. Runs the relationship recall and validates references.
4. Forgets the stable stale-item ID and verifies absence.
5. Records the verified resolution.
6. Calls improve exactly once.
7. Recalls from clean session `incident:INC-2048-proof`.
8. Validates the new resolution.

The test writes a redacted result report containing timings, statuses, document
names, and pass/fail assertions—never answer payloads that might include
unexpected sensitive data.

- [ ] **Step 3: Run offline evaluation**

Run:

```powershell
uv run python scripts/evaluate_retrieval.py --adapter fake
```

Expected: all four metrics are 10/10.

- [ ] **Step 4: Check the Cognee dashboard before the live proof**

Proceed only if remaining credits are comfortably above 8,000,000 tokens. If
not, do not run the live proof; use the already-recorded adapter contract and
preserve the 6,000,000 reserve.

- [ ] **Step 5: Run the live proof once**

Run:

```powershell
$env:RUN_COGNEE_INTEGRATION='1'
uv run pytest backend/tests/integration/test_live_judge_flow.py -v -s
Remove-Item Env:RUN_COGNEE_INTEGRATION
```

Expected: one complete remember/recall/forget/improve/clean-recall lifecycle
passes. Do not repeat solely to improve timing.

- [ ] **Step 6: Rehearse from the deployed URL**

Wake the free Space, then manually follow `demo/demo-script.md`. Confirm:

- cold start is understood
- dataset ready
- references render
- stale item is present before forget
- forget proof renders
- improve completes
- clean-session proof renders
- browser console has no uncaught error
- no secret appears in network responses

- [ ] **Step 7: Final verification**

Run:

```powershell
uv run python scripts/preflight.py
uv run ruff check backend scripts
uv run mypy
uv run pytest -m "not integration"
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
npm --prefix frontend run e2e
docker build -t recallops:final .
git status --short
git diff --check
```

Expected: all automated checks pass; Git status contains only deliberately
uncommitted generated screenshots/video artifacts, if any.

- [ ] **Step 8: Final commit**

```powershell
git add scripts backend/tests/integration docs/submission-checklist.md
git commit -m "test: validate RecallOps retrieval and live memory lifecycle"
```

---

## 3. Requirement-to-Task Traceability

| Design requirement | Implemented by |
|---|---|
| Stable permanent evidence and session observations | 4, 7, 8, 9 |
| Graph recall with references | 4, 6, 10, 15 |
| Truthful item-level forget | 8, 15, 21 |
| Human-controlled improve | 11, 16, 21 |
| Clean-session learning proof | 11, 16, 18, 21 |
| Memory Inspector and graph | 15, 16 |
| Deterministic judge demo | 7, 13, 18 |
| Credit ceiling and protected reserve | 5, 6, 21 |
| Error/degraded behavior | 9, 10, 11, 17 |
| Security and secret safety | 2, 7, 8, 19 |
| Docker and free public deployment | 20 |
| Offline CI and live-test gate | 1, 6, 20 |
| Landing-page boundary | 12, 18, 19 |
| Submission docs and 90-second script | 20, 21 |

## 4. Final Definition of Done

Do not call the project complete until all statements are true:

- `uv run pytest -m "not integration"` passes.
- `npm --prefix frontend run test` passes.
- `npm --prefix frontend run build` passes.
- `npm --prefix frontend run e2e` passes.
- `docker build .` passes.
- `scripts/preflight.py` passes.
- Fake-adapter golden retrieval scores 10/10 in all four categories.
- One controlled live Cognee lifecycle has been demonstrated or intentionally
  skipped to protect the hard reserve, with the reason recorded.
- The public free deployment or local Docker fallback completes the full judge
  flow.
- The stale item is absent after item-level forget and the new resolution is
  available from a clean session after improve.
- No credential exists in Git history, logs, responses, screenshots, or docs.
- At least 6,000,000 supplied Cognee tokens remain protected for the final
  demonstration.
- `/app` remains stable for the user's later landing-page integration.
