# Unsafe global killswitch assumption — derived anti-pattern

Case-study status: RecallOps-created unsafe assumption for lifecycle testing  
Source context: https://blog.cloudflare.com/5-december-2025-outage/

## Unsafe assumption

Any WAF rule can be disabled through the global configuration killswitch
without a gradual rollout because the killswitch has a well-established
operating procedure.

## Why this must be forgotten

Cloudflare's public postmortem says the killswitch had not previously been
applied to a rule whose action was `execute`. In the FL1 proxy, skipping that
action left an expected object absent and later code dereferenced it. The
resulting Lua error caused affected requests to return HTTP 500 responses.

The safe replacement is controlled rollout with health validation, rapid
rollback, and known-good fallback behavior.

This document is not a Cloudflare-authored instruction. RecallOps created it as
an explicit anti-pattern so the item-level forget lifecycle can be demonstrated
without misrepresenting private operational material.
