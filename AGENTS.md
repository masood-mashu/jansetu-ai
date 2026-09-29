# AGENTS.md - Framework-Agnostic Fallback Instructions

When running in environments without native OpenGAP harness (e.g. standard LLM chat interfaces, Claude Code, Cursor, Copilot):

1. **System Persona:** Always adopt the persona defined in [SOUL.md](SOUL.md).
2. **Behavioral Invariants:** Strictly adhere to the prohibitions and mandates in [RULES.md](RULES.md).
3. **Segregation of Duties:** Comply with [DUTIES.md](DUTIES.md). If performing actions that require Checker sign-off, simulate dual-role validation or route to the `verifier` sub-agent.
4. **Tool Execution:** Ground all quantitative statements using tools declared in [tools/](tools/).
5. **Memory Continuity:** Reference [memory/runtime/context.md](memory/runtime/context.md) for current execution state.
