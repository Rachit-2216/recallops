# Code Orange: Fail Small — derived operational guidance

Case-study status: RecallOps guidance derived from an official Cloudflare plan  
Publisher of source facts: Cloudflare  
Official source: https://blog.cloudflare.com/fail-small-resilience-plan-uk-ua/

After the November 18 and December 5 incidents, Cloudflare described a
resilience program organized around three controls:

1. Treat globally propagated configuration like software: use controlled,
   progressive rollouts with explicit success metrics.
2. Continuously test failure modes at service boundaries and fall back to
   validated defaults or safe traffic handling when configuration is invalid.
3. Maintain break-glass and rollback paths that remain usable during control
   plane or dependency failures.

For this case study, a safe configuration-change procedure is:

1. Define health indicators and rollback thresholds before rollout.
2. Start with employee or narrowly scoped traffic.
3. Increase exposure only while health gates remain green.
4. Roll back automatically when an anomaly appears.
5. For corrupt or out-of-range configuration, use a known-good state instead
   of dropping traffic.

This is a RecallOps-authored operational summary. It is not represented as an
internal Cloudflare runbook.
