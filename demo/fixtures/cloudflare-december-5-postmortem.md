# Cloudflare outage on December 5, 2025 — public postmortem summary

Case-study status: derived from an official public postmortem  
Publisher: Cloudflare  
Official source: https://blog.cloudflare.com/5-december-2025-outage/

## Impact

At 08:47 UTC, a portion of Cloudflare's network began returning HTTP 500
errors. Cloudflare reported that the affected customer configurations
accounted for approximately 28 percent of the HTTP traffic it served. The
incident ended at 09:12 UTC, for roughly 25 minutes of total impact.

## Change and failure

Cloudflare was increasing a WAF request-body buffer from 128 KB to 1 MB while
responding to an industry-wide React Server Components vulnerability. That
change used a gradual deployment system. A second change disabled an internal
WAF testing tool through a global configuration system that propagated within
seconds rather than gradually.

On the older FL1 proxy, applying a killswitch to a ruleset action of `execute`
skipped creation of an expected object. Later Lua code attempted to use that
missing object and raised:

`attempt to index field 'execute' (a nil value)`

Affected requests returned HTTP 500 errors.

## Recovery and verification

Cloudflare identified the configuration change, reverted it at 09:11 UTC, and
reported that the revert was fully propagated with all traffic restored at
09:12 UTC.

This file is a concise RecallOps case-study summary. It is not a raw Cloudflare
log, internal runbook, or complete reproduction of the source article.
