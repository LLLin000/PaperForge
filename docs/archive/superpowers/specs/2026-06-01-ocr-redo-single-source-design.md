# OCR Redo Single-Source Fulltext Design

> **Status:** Approved
> **Date:** 2026-06-01

## Goal

Make OCR redo a one-command closed loop and remove the duplicated workspace `fulltext.md` as a truth source.

## Decisions

1. Canonical OCR fulltext lives only at `System/PaperForge/ocr/<key>/fulltext.md`.
2. Workspace `Resources/.../fulltext.md` is deleted and no longer regenerated.
3. `paperforge ocr redo` immediately reruns OCR instead of only resetting state.
4. `ocr_redo` is a one-shot trigger:
   - stays `true` while redo is still pending/failed
   - flips to `false` only after successful OCR completion

## Workflow

For each note with `ocr_redo: true`:

1. Delete stale workspace `fulltext.md` if present.
2. Delete old OCR output directory under `System/PaperForge/ocr/<key>/`.
3. Force note frontmatter to:
   - `do_ocr: true`
   - `ocr_status: pending`
   - `fulltext_md_path: ""`
   - `ocr_redo: true`
4. Invoke OCR code immediately for the selected keys only.
5. After OCR returns:
   - success -> `ocr_status: done`, `ocr_redo: false`
   - pending/failed -> keep `ocr_redo: true`

## Single-Source Fulltext Contract

- `asset_index` advertises canonical OCR `fulltext.md` as `fulltext_path`
- sync/migration no longer bridges OCR fulltext into workspace
- stale workspace copies should be deleted opportunistically when encountered

## Non-Goals

- No soft links
- No workspace proxy `fulltext.md`
- No background redo queue separate from the command
