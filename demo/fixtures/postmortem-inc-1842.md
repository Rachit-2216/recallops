# Synthetic Postmortem: INC-1842

- Incident: INC-1842
- Service: checkout-api
- Date: 2026-05-14
- Dependency: Redis session store
- Status: resolved and verified

## Summary

Checkout requests began timing out nine minutes after deploy-377. Checkout p95
rose above 4 seconds while Redis session misses increased 610 percent. Payment
gateway latency and rate-limit metrics stayed at baseline.

## Root cause

The checkout session configuration changed from a seconds-based field to a
millisecond field. The Redis session adapter still interpreted the supplied
value as seconds. The missing seconds-to-milliseconds conversion caused
session TTL behavior to diverge, session lookups to miss, and repeated session
recreation to amplify checkout latency.

## Verified mitigation

The team rolled back the TTL configuration, restored the seconds-based adapter
value, and reissued affected checkout sessions. Checkout p95 returned below
450 ms and Redis session misses returned to baseline within seven minutes.

## Prevention

Validate TTL units at the configuration boundary. Alert on a deployment that
coincides with both session-miss growth and checkout latency.
