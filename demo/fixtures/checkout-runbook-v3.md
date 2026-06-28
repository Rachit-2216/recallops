# Synthetic Checkout Session Runbook v3

Updated: 2026-06-20

## Redis session regression after a deployment

1. Compare the deployed `SESSION_TTL_MS` value with the seconds-based value
   expected by the checkout session adapter.
2. Roll back the TTL configuration if units were passed without conversion.
3. Reissue only affected checkout sessions.
4. Verify checkout p95 is below 450 ms for five minutes.
5. Verify Redis session misses have returned to baseline.

Do not flush the complete Redis cache. A global flush increases login churn and
does not correct a TTL-unit mismatch.
