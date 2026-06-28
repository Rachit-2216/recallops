# Submission checklist

## Offline verification

- [ ] `uv sync --frozen --group dev`
- [x] `uv run ruff check backend scripts`
- [x] `uv run mypy`
- [x] `uv run pytest -m "not integration"`
- [ ] `npm ci --prefix frontend`
- [x] `npm --prefix frontend run lint`
- [x] `npm --prefix frontend run test`
- [x] `npm --prefix frontend run build`
- [x] `npm --prefix frontend run e2e`
- [x] `uv run python scripts/preflight.py`
- [x] `docker build -t recallops:local .`

## Credit and live-memory gate

- [x] Offline fake evaluation scores 10/10 for documents, concepts, forbidden
  claims, and reference parsing.
- [x] Live proof status: intentionally not run until both the dashboard shows
  more than 8,000,000 credits and valid live configuration is available.
- [x] Verify Cognee configuration without printing values; the configured base
  URL is structurally invalid, so no live request was made.
- [ ] Open the Cognee dashboard and record remaining credits privately.
- [ ] Confirm the protected reserve is at least 6,000,000 tokens.
- [ ] Set `RUN_COGNEE_INTEGRATION=1` only for the controlled proof.
- [ ] Run the live judge lifecycle once, not repeatedly.
- [ ] Recheck the dashboard and stop if projected reserve would be crossed.

## Free deployment

- [x] Local Docker fallback passes health and the complete Chromium judge flow.

- [ ] Hugging Face Space uses Docker SDK and port 7860.
- [ ] Hardware remains free `cpu-basic`.
- [ ] Paid persistent storage is disabled.
- [ ] Secrets exist only in Space secret storage.
- [ ] `/api/health` contains no credentials or provider detail.
- [ ] Cold start restores the synthetic demo.
- [ ] Deployed judge flow finishes in under 90 seconds.

## Submission assets

- [ ] Five application screenshots contain no secrets.
- [ ] 90-second video follows `demo/demo-script.md`.
- [ ] Public URL works in a signed-out browser.
- [ ] Repository URL and commit SHA are recorded.
- [ ] Synthetic-data and AI-assistance disclosures are visible.
- [ ] Known limitations match actual behavior.
