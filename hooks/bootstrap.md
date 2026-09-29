# Bootstrap Hook
Executed when the agent runtime starts up.
- Verify environment variables (GEMINI_API_KEY, GOOGLE_CLOUD_PROJECT).
- Load agent.yaml, SOUL.md, RULES.md, and DUTIES.md into system instructions.
- Initialize working memory from `memory/runtime/context.md`.
