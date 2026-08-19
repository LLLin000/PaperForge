---
name: paperforge
description: >
  Use PaperForge for research-memory work: locate papers, read a known paper,
  find supporting evidence, deep-read a paper, or save a verified note/log.
  Trigger on pf-paper, pf-deep, pf-sync, pf-ocr, pf-status, "找文献",
  "读一下", "精读", "找证据", "记录阅读", "记录工作", or "记一下".
source: paperforge
skill_version: 2026-08-17.2
skill_api_version: 2
---
# PaperForge — thin research-memory router

PaperForge owns paper lookup, source-grounded reading, evidence retrieval, and
explicitly requested memory writes. Keep this file as the route and safety
contract; command details belong to the CLI and workflow files.

## Start once

Run bootstrap before the first PaperForge operation:

```bash
python $SKILL_DIR/scripts/pf_bootstrap.py --vault "$VAULT"
```

If `ok` is false, report the error and stop. Use `vault_root`,
`python_candidate`, and `paths.literature_dir` from the JSON; do not construct
paths by hand. If `skill_api_version` is incompatible, ask the user to run
`paperforge update`.

Run `agent-context` or `runtime-health` only when the user asks for status,
diagnostics, or a workflow explicitly needs that information. They are not
mandatory startup steps.

## Route

Handle explicit mechanical commands first:

| Input | Action |
|---|---|
| `/pf-sync` | Run `paperforge sync` and report the structured result. |
| `/pf-ocr` | Run the requested OCR command; do not infer completion from process exit alone. |
| `/pf-status` | Run `paperforge status --json` or `runtime-health --json`. |
| `/pf-deep` | Open `molecules/deep-analyze-paper.md`. |
| `/pf-paper` | Open `molecules/read-known-paper.md`. |

For natural-language requests choose one workflow:

| Intent | Workflow |
|---|---|
| locate/read one named paper or answer a paper-scoped question | `read-known-paper.md` |
| discover a set of papers or inspect a collection | `discover-papers.md` |
| find evidence for a claim, parameter, or term | `find-supporting-evidence.md` |
| perform a full structured read | `deep-analyze-paper.md` |
| save a note, reading record, project log, or method card | `capture-project-knowledge.md` |

Use `atoms/clarify-user-intent.md` only when two intents are genuinely
ambiguous. If the user asks to save after another workflow, route to
`capture-project-knowledge.md` without rerunning the reading workflow.

## Retrieval

When a workflow searches or retrieves, open `atoms/retrieval-routing.md`.
That file is the single retrieval protocol: planner first, one primary command,
at most one declared fallback, and no library fallback for a paper-scoped
question. Do not reproduce its command matrix in another workflow.

## Source and write safety

- Treat `paper-context`, `retrieve`, and the paper itself as factual sources.
  Reading logs are leads for re-checking, never evidence by themselves.
- Separate author statements, extracted evidence, and agent inference. Cite
  the paper key plus section/node/page when available; say when the paper does
  not state something.
- Use PaperForge CLI for vault search and paper context. Use workflow-provided
  paths for reading and writing; never scan or mutate the vault by guessed
  paths.
- Never write a reading log, project log, or method card without the user's
  explicit request and a concise preview/confirmation.
- Do not claim OCR, retrieval, or embedding success from a zero exit code alone;
  inspect the structured result and relevant state.

## Extension rule

Add a workflow only for a distinct user intent, and add an atom only when at
least two workflows share the same protocol. New CLI behavior belongs in the
PaperForge package first; the skill should route to it, not mirror its state
machine or add another preflight layer.

## Completion

Return the answer, evidence boundary, and any saved path. If no write was
requested, leave the vault unchanged. If a command fails, report its structured
error and repair action instead of silently switching tools.
