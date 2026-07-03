# Cloudflare outage on November 18, 2025 — public postmortem summary

Case-study status: derived from an official public postmortem  
Publisher: Cloudflare  
Official source: https://blog.cloudflare.com/18-november-2025-outage/

## Impact

At 11:20 UTC, Cloudflare's network began experiencing significant failures in
core traffic delivery. Core traffic was largely restored by 14:30 UTC and all
systems were reported normal at 17:06 UTC.

## Root cause

A database-permission change caused a query to produce duplicate entries in a
Bot Management feature file. The file doubled in size and exceeded a software
limit before being distributed across the network. Because the file was
regenerated every five minutes while a ClickHouse cluster update was rolling
out, good and bad files alternated for a period. Those fluctuations initially
looked like a possible attack.

## Recovery

Cloudflare stopped generation and propagation of the oversized file, inserted
a known-good file into the distribution queue, and restarted the core proxy.

## Relationship to December 5

The November and December incidents had different immediate bugs, but both
showed the blast-radius risk of configuration artifacts propagating globally
without software-release-style rollout gates.

This file is a concise RecallOps case-study summary, not raw Cloudflare data.
