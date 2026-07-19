# Project Management Archive Structure Rollout

> Completed: 2026-06-17
> Type: documentation workflow change

## Problem

`PROJECT-MANAGEMENT.md` had become a combined index, archive, session log, decision log, and handoff record. It was too large to function as the active control surface for OCR-v2 work.

## Decision

Adopt a hybrid structure:

```text
PROJECT-MANAGEMENT.md
project/
  current/
  archive/
```

Rules introduced by this rollout:

1. `PROJECT-MANAGEMENT.md` becomes the root index.
2. active unresolved topics live in `project/current/*.md`.
3. completed records move into `project/archive/YYYY-MM-DD-<topic>.md`.
4. only the currently active problem stays detailed in the root file.

## Changes Applied

- created `project/current/ocr-v2-generalization-boundary.md`
- created `project/archive/2026-06-17-ocr-v2-project-management-history-snapshot.md`
- rewrote `PROJECT-MANAGEMENT.md` as a summary + link index
- updated `AGENTS.md` section 9 to enforce the new maintenance workflow

## Result

The project now has:

- a short root management file
- one detailed current-topic file
- an archive path for completed records
- explicit agent rules to keep the split stable over future sessions

## Follow-Up Expectation

Future completed topics should be moved from `project/current/` into `project/archive/` instead of being left inside `PROJECT-MANAGEMENT.md`.
