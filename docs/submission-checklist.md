# Submission checklist

## Offline verification

- [x] `uv sync --frozen --group dev`
- [x] `uv run ruff check backend scripts`
- [x] `uv run mypy`
- [x] `uv run pytest -m "not integration"`
- [x] `npm ci --prefix frontend`
- [x] `npm --prefix frontend run lint`
- [x] `npm --prefix frontend run test`
- [x] `npm --prefix frontend run build`
- [x] `npm --prefix frontend run e2e`
- [x] `uv run python scripts/preflight.py`
- [x] `docker build -t recallops:local .`

## Credit and live-memory gate

- [x] Offline fake evaluation scores 10/10 for documents, concepts, forbidden
  claims, and reference parsing.
- [x] Cognee configuration was verified without printing values.
- [x] Read-only dataset connectivity passed against Cognee Cloud.
- [x] The operator privately confirmed 14,000,000 credits before the proof.
- [x] The protected reserve was at least 6,000,000 tokens before the proof.
- [x] `RUN_COGNEE_INTEGRATION=1` was used only for controlled checks.
- [x] One tiny adapter-contract item was ingested, recalled, and then deleted
  by its exact provider ID; post-cleanup verification found no matching item.
- [ ] The live adapter contract passes. Cognee graph recall omitted document
  references, so RecallOps correctly rejected the result as unverified.
- [ ] Run the complete live judge lifecycle. It was not attempted after the
  contract failure, avoiding further credit use.
- [ ] Recheck the dashboard and stop if projected reserve would be crossed.

## Free deployment

- [x] Local Docker fallback passes health and the complete Chromium judge flow.

- [x] Hugging Face Space uses Docker SDK and port 7860.
- [x] Hardware remains free `cpu-basic`.
- [x] Paid persistent storage is disabled.
- [x] Secrets exist only in Space secret storage.
- [x] `/api/health` contains no credentials or provider detail.
- [x] Cold start restores the synthetic demo.
- [x] Deployed judge flow finishes in under 90 seconds (9.9 seconds).

## Submission assets

- [x] Five application screenshots contain no secrets. The verified captures
  are in ignored `output/playwright/`.
- [ ] 90-second video follows `demo/demo-script.md`.
- [x] Public URL works in a signed-out Chromium browser:
  <https://rachitr-recallops.hf.space>.
- [x] Repository URLs and deployed commits are recorded:
  <https://github.com/Rachit-2216/recallops>,
  source commit `10efb76`; and
  <https://huggingface.co/spaces/rachitr/recallops>,
  Space commit `be78620e1cc04a27defd558a8dfa891fbb8ad8e7`.
- [x] Synthetic-data and AI-assistance disclosures are visible.
- [x] Known limitations match actual behavior.
