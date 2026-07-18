# Matt Workflow Guardrails

- Ask Matt owns the engineering lifecycle: route with `/ask-matt`, implement one agent-ready issue with `/implement`, then run `/review`. Do not introduce a second orchestration workflow.
- One implementation session handles one issue in one authoritative worktree. Start a fresh session before changing issues; use `/handoff` only when context must cross sessions.
- Before editing, pin the issue, parent PRD, issue `updated_at`, base SHA, worktree root, scope, acceptance criteria, and verification commands. If the issue changes, stop and refresh this contract.
- Use one writer. Parallel `task` batches may contain only read-only `scout`, `reviewer`, or `librarian` agents. Never let parallel agents edit shared files or the same worktree.
- Never copy implementation files between the main checkout and a worktree. All reads, writes, tests, reviews, and commits for an issue use its authoritative worktree.
- Follow Matt `/tdd` at pre-agreed seams. Run focused checks while implementing and the issue-specific final gate once after the last mutation; UI work also needs a real-browser smoke test.
- Review exactly once on Matt's two axes. Consolidate findings into one repair pass and one re-review. If an important defect remains, return to the acceptance contract or split the issue; do not create repeated Final/Definitive review loops.
- Commit, merge, push, create/merge a PR, or close an issue only after verification succeeds after the last mutation. Update `PROJECT-MANAGEMENT.md` and the active queue according to project rules before closeout.
- The removed Superpowers workflows are not part of this project. Do not reinstall, invoke, emulate, or delegate through them.
