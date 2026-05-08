feat(agent-trigger): split channel trigger envelope and body

- Build persistent trigger envelopes with message, thread, actor, and agent indexes
- Enqueue visible trigger body separately from the legacy SDK context prompt
- Reduce legacy channel context to lightweight message and artifact indexes
- Update backend trigger tests and mark Phase 1 plan tasks complete
