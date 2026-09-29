# Multi-Step Execution Playbook

1. **Ingest & Validate:** Receive multimodal/text input from citizen or authority stream.
2. **Context Resolution:** Enrich request with local geographical, demographic, or meteorological context from `knowledge/`.
3. **Reasoning & Tool Execution:** Model executes registered tools (calculators, geospatial queries, triage engines).
4. **Segregation of Duties Verification:** Sub-agent `verifier` reviews proposed action plan against `RULES.md` and `DUTIES.md`.
5. **Dispatch & Audit Logging:** Deliver synthesized, actionable response and record cryptographic audit log in `memory/runtime/dailylog.md`.
