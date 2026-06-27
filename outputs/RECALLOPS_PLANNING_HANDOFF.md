# RecallOps Planning Handoff

Planning is complete for the approved Cognee hackathon submission.

## Product

RecallOps is an AI incident commander with auditable, self-improving memory. Its
judge demo uses a synthetic checkout outage to show all four Cognee lifecycle
operations:

- remember permanent evidence and short-lived incident observations;
- recall a prior incident with graph-backed references;
- forget one stale permanent runbook item and verify its absence;
- improve memory from a human-verified resolution and recall it in a clean
  session.

## Locked decisions

- React/TypeScript application and FastAPI backend.
- SQLite for local application metadata; Cognee Cloud for AI memory.
- Application dataset: `recallops_evidence_v1`.
- Build-memory dataset: `recallops_build_memory`.
- Deterministic fake adapter for normal tests.
- Live Cognee calls require `RUN_COGNEE_INTEGRATION=1`.
- Hard supply: 14,000,000 Cognee tokens.
- Protected final reserve: 6,000,000 tokens.
- Free Hugging Face Docker Space target; local Docker fallback.
- `/app` is the stable product entry point.
- The marketing landing page is excluded and will be added by the user later.

## Source documents

- Approved design:
  `docs/superpowers/specs/2026-06-28-recallops-design.md`
- Executable 21-task plan:
  `docs/superpowers/plans/2026-06-28-recallops-implementation-plan.md`
- Ready-to-paste coding prompt:
  `START_CODING_PROMPT.md`

## Next action

Open a new Codex chat in this folder and paste the complete contents of
`START_CODING_PROMPT.md`. Plan mode is not required; the next chat should
execute the approved plan immediately.
