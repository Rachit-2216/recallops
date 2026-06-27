# RecallOps Coding Chat Prompt

Copy everything below the divider into a new Codex chat opened in this exact
folder:

`C:\Users\Rachit Shrivastava\Documents\Codex\2026-06-27\https-www-wemakedevs-org-hackathons-cognee`

---

You are the implementation owner for RecallOps, my solo Cognee hackathon
submission. Begin coding now and carry the project from the current planning
state to a verified, deployable application.

The product, architecture, scope, Cognee lifecycle, UX, stack, deployment
target, budget, and implementation sequence are already approved. Do not reopen
brainstorming or ask me to approve routine technical decisions. Read these two
files completely before editing code:

1. `docs/superpowers/specs/2026-06-28-recallops-design.md`
2. `docs/superpowers/plans/2026-06-28-recallops-implementation-plan.md`

Then execute the implementation plan in order, starting with Task 1. Update its
checkboxes as each stated verification passes. Continue autonomously through
all tasks while safe work remains. Stop only for a genuine external blocker,
missing authority for a paid/destructive action, or a required secret that is
not already configured.

## Required working method

- Invoke and follow `superpowers:executing-plans`.
- Use `superpowers:test-driven-development` for every feature and bug fix.
- Use `superpowers:systematic-debugging` for any unexpected failure.
- Use `superpowers:verification-before-completion` before claiming a milestone
  or the project complete.
- Use the relevant Cognee skill when making or diagnosing live Cognee calls.
- Do not use subagents unless I explicitly authorize subagents in this chat.
- Make the small commits specified in the plan.
- Give concise progress updates at least once per task or every 30-60 minutes.
- Preserve any unrelated user changes already in the worktree.

## Product target

Build RecallOps: an AI incident commander with auditable, self-improving
memory. The deterministic checkout-outage demo must visibly prove:

1. permanent evidence remembered in `recallops_evidence_v1`;
2. live observations stored in session `incident:INC-2048`;
3. graph/session recall with exact document and chunk references;
4. a causal explanation connecting deploy-418, Redis session misses, and
   historical incident INC-1842;
5. truthful item-level forgetting of `stale-cache-reset-rule.md`, followed by a
   recall-based absence check;
6. human confirmation of the real resolution;
7. one explicit improve operation that bridges the verified session;
8. recall of the promoted resolution from a clean session.

This is not a generic chatbot. The incident cockpit, provenance, relationship
path, memory state, feedback, verified learning, and selective forgetting are
the product.

## Scope boundary

Implement the complete application UI and backend, including `/app`, the
incident cockpit, evidence library, Memory Inspector, graph, resolution flow,
tests, Docker packaging, documentation, evaluation, and deployment support.

Do not design or implement the marketing landing page. Keep `/` as a redirect
boundary to `/app`. I will build the landing page after the application is
finished; do not rename `/app` or any approved API route.

## Cognee and spending constraints

- There are 14,000,000 Cognee tokens from the `COGNEE-35` voucher.
- Spending beyond those supplied credits is forbidden.
- Preserve at least 6,000,000 tokens for final rehearsal/demo.
- Offline tests must use `FakeCogneeAdapter`.
- Every live test must require `RUN_COGNEE_INTEGRATION=1`.
- Seed operations must be idempotent.
- Never run repeated full-dataset ingestion to chase nondeterministic output.
- Never call `cognee.forget(everything=True)`.
- Never delete the complete account dataset.
- The application dataset is `recallops_evidence_v1`.
- Codex build memory is `recallops_build_memory`; never mix it with application
  evidence.
- Use the existing `COGNEE_BASE_URL` and `COGNEE_API_KEY` only from environment
  variables. Never echo, print, log, screenshot, commit, or return them.
- Do not buy Cognee credits, hosting, hardware, storage, a domain, or any other
  service.
- Before each controlled live mutation phase, check the budget gate described
  in the plan. If remaining credit cannot be confirmed, continue with the fake
  and recorded contract instead of risking the reserve.

## Implementation priorities

Use this priority order when tradeoffs arise:

1. A reliable 90-second judge flow.
2. Deep, truthful Cognee lifecycle use.
3. Visible provenance and clean-session learning proof.
4. Deterministic offline behavior and graceful cloud failure.
5. Technical quality, security, and documentation.
6. Visual polish of the application UI.
7. Stretch integrations only after every core acceptance criterion passes.

Do not add Slack, PagerDuty, GitHub OAuth, billing, enterprise auth,
multi-tenancy, autonomous remediation, or another AI framework before the core
definition of done. YAGNI applies.

## Execution expectations

Start by checking `git status`, the Python/Node/Docker toolchain, and whether
Git needs initialization. Do not treat missing generated application files as a
problem; this folder intentionally begins with the approved design and plan.

For each task:

1. write the failing test;
2. run it and confirm the expected failure;
3. implement the smallest complete behavior;
4. run the focused tests;
5. run the task's broader verification;
6. update the plan checkbox;
7. commit with the specified message;
8. move immediately to the next task.

When an installed package version makes a planned snippet invalid, preserve the
approved public interface and behavior, verify the installed official API, and
confine adaptation to the relevant boundary. In particular, all Cognee SDK
shape differences belong in
`backend/src/recallops/memory/cognee_cloud.py`; they must not leak into services
or API responses.

Use the official Cognee operations:

- `remember(..., self_improvement=False)` for controlled permanent ingestion;
- `remember(..., session_id=..., self_improvement=False)` for active incident
  observations;
- `recall(..., datasets=[...], session_id=..., verbose=True)` for scoped hybrid
  recall;
- `improve(dataset=..., session_ids=[...])` only after human verification;
- `forget(dataset=..., data_id=...)` only for one stable permanent evidence
  item.

Do not claim an answer is verified without references. Do not claim forgetting
succeeded until follow-up retrieval proves the stale data ID is absent. Do not
claim the system learned until improve succeeds and a clean session recalls the
new resolution.

## Completion gate

Do not say "done" until all core checks pass:

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
git diff --check
```

Also prove the fake-adapter retrieval evaluation is 10/10, verify the complete
judge flow, verify no secret exposure, and either complete the one controlled
live Cognee lifecycle or record that it was skipped to protect the hard credit
reserve. A successful local Docker demo is mandatory even if public deployment
is temporarily unavailable.

Begin now: read both documents, report the first execution batch in one concise
update, and implement Task 1.
