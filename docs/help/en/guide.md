# Feature Guide

## Typical Workflow

A common day-to-day pattern for using PaperForge:

1. **Sync** your library from the Overview to pull in new Zotero items.
2. **OCR** — Open OCR Workspace, filter by "Not Processed", and run OCR on new papers.
3. **Review** — Processed papers show "Processed" when complete.
4. **Search** — Use Smart Retrieval from the Dashboard for full-text search.
5. **Cite** — Use your Zotero + Better BibTeX workflow as usual. PaperForge does not interfere with your citation manager.

The Overview shows you at a glance what needs attention: OCR papers to process, a stale vector index, or library items awaiting sync.

---

## Library

Sync your Zotero library to build a searchable index of your literature. The Library module connects to your Zotero data directory and reads the BBT JSON export to create a formal library index. Once configured, you can browse, search, and manage your papers from the Overview and OCR Workspace.

**Requirements:** Zotero desktop with Better BibTeX plugin installed, and a valid BBT JSON export file placed in the vault configuration directory.

---

## OCR Engine

Extract full text and figures from PDFs using OCR. The OCR pipeline processes each paper through a multi-stage pipeline: page analysis, figure/table detection, text extraction, and structural role assignment.

Open the OCR Workspace from the ribbon icon or `Ctrl+P → Open OCR Workspace`. Select papers by status filter, use the search box to find specific papers, and batch-process selections with the toolbar buttons.

**OCR status badges:** Processed, Update Available, Not Processed, Failed, Pending.

---

## Smart Retrieval

Semantic search across your paper collection. Smart Retrieval builds a vector index of your papers' full text using an embedding model, then enables natural-language queries that go beyond keyword matching.

To use: configure an API key and model in Smart Retrieval settings, then click "Build Index". Once built, you can search from the Dashboard search bar.

**Requires:** an OpenAI-compatible API endpoint and an embedding model.

---

## Agent Integration

Deploy PaperForge Skills to your preferred AI agent platform. Skills give your agent access to paper search, OCR status, and literature management commands directly from the chat interface.

**Supported platforms:** Claude Code, OpenCode, and other OpenMP-compatible agents. Select your platform in settings and the Skills are deployed automatically.
