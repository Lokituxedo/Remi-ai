# Additional considerations and research notes

Below are items we included during the design and additional areas to
investigate or which we may be missing at this stage.

1) Consent & privacy
- Ensure opt-in consent persisted in meta:{session_id} (we default to True for testing). In prod, require explicit opt-in during onboarding.
- GDPR/CCPA: store consent timestamps and allow deletion of personal data.

2) Moderation & safety
- Current blocklist is naive. Integrate a dedicated moderation API (local or cloud) for text safety.
- For NSFW/age-restricted contexts, implement age verification and stricter controls.

3) Rate limiting & backoff
- We record per-day counters. Consider backoff strategies and exponential cooldowns when users ignore reengages.

4) UX & transparency
- UI must clearly label automated messages. Provide a toggle to disable reengage.
- Provide Do-Not-Disturb windows.

5) Personalization & model tradeoffs
- Use a lightweight local model for microcopy to reduce latency and cost.
- Reserve heavy models for longer completions or complex personalization.

6) Observability & metrics
- Add metrics for reengage_sent, reengage_reply_rate, time_to_reply, reengage_abandon_rate.
- Add logging and tracing (structured logs) for each reengage decision.

7) Edge cases
- Short sessions, multi-device sessions, offline users, rate-limits from push providers.

8) Security
- Sanitize inputs to avoid injection-like attacks in model prompts.

9) Research references & industry patterns
- Proactive chat systems use presence heartbeats, visibility API, and push permissions.
- Best practice: keep reengage short, transparent and rate-limited.
- Consider pre-generating variants to respond faster.

10) Next steps
- Integrate model endpoint and an automated moderation step.
- Add graceful shutdown and reconnection logic for the agent CLI.
- Add tests that simulate 1 user + 2 agents and validate metrics.
