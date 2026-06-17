# Research: annotation v0.1 Pitfalls

**Date:** 2026-06-17
**Milestone:** annotation v0.1 - PDF Annotation Backend & CLI Foundation

## Pitfall 1: Single-Paper Import Deletes Other Papers

The old branch importer soft-deletes stale rows by source, not by import scope. If a user imports only one paper, annotations from other papers can look stale and get marked deleted.

**Prevention:** require explicit import scope and limit stale deletion to that scope.

## Pitfall 2: Weak Zotero Identity

Zotero keys are not globally unique across all libraries and group contexts.

**Prevention:** track source, library ID, annotation key, attachment key, and parent paper key. Do not use bare annotation key as the only imported identity.

## Pitfall 3: Reading Live Zotero SQLite

Zotero may lock or cache its SQLite database while running.

**Prevention:** copy `zotero.sqlite` to a temp file by default, read the copy, and clean it up.

## Pitfall 4: Annotation DB Gets Treated Like Rebuildable Memory

PaperForge already has rebuildable indexes. Annotation data is different: users may treat it as evidence.

**Prevention:** keep `annotations.db` independent and document that memory rebuilds must not drop it.

## Pitfall 5: Plugin Overlay Too Early

The old branch modifies `paperforge/plugin/main.js` by more than 1,000 lines and depends on private Obsidian/PDF.js internals.

**Prevention:** defer overlay to v0.2. v0.1 should prove backend import/list/export first.

## Pitfall 6: Hardcoded Vault Paths

The old branch had hardcoded assumptions around Zotero storage and PaperForge system directories.

**Prevention:** use current PaperForge config/path resolver and add hardcoded-path regression checks.

## Pitfall 7: JSON Contract Drift

Future plugin code will call annotation CLI commands. If output is unstable, the plugin will become brittle.

**Prevention:** snapshot/shape tests for `--json` output of import/list/status/export.
