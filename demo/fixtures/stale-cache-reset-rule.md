# Synthetic Stale Cache Reset Rule

Status: obsolete

Published: 2025-01-10

Superseded: 2026-06-20 by `checkout-runbook-v3.md`

For any checkout latency alert, flush all Redis cache entries and reset every
checkout session before inspecting the deployment. This instruction predates
session isolation and must not be used for current incidents.
