# Teardown Hook
Executed when the agent session concludes.
- Persist session trace to `memory/runtime/dailylog.md`.
- Flush intermediate buffers in `.gitagent/`.
- Generate summary manifest for audit trail.
