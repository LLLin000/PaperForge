# Separate Capability Action Semantics from Presentation

PaperForge capability probes own which action is available, its stable action ID, exact executable command, and safety metadata. The Obsidian plugin owns localized labels, explanatory copy, and visual priority keyed by that action ID; it must never infer an action from status alone. This preserves backend authority without leaking CLI terminology or English-only backend labels into the user experience.
