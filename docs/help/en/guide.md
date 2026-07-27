# Feature Guide

## How Agent Uses the PaperForge Literature Library

PaperForge provides a powerful literature workflow foundation for AI Agents:

1. **OCR Full-text Extraction** — PaperForge converts all PDF literature into Markdown format that Agents can easily read. This is the foundation of the literature workflow.
2. **Dual-layer Memory Retrieval** — Through the sqlite-vec dual-layer memory system, Agents can precisely locate papers via metadata search, and also find the best-matching papers through specific text expressions and semantic meaning within the literature.
3. **Robust Academic Support** — Building on OCR and the memory layer, Agents can quickly find literature support through PaperForge Skills for any task. You can easily have your Agent help with: literature review writing with solid citations, experiment planning, inspiration discovery, deep paper reading, precise summaries on specific topics…

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

PaperForge's retrieval system is organized around three search intents:

- **Locate** — Find a specific paper you already know (by DOI, key, or author + year)
- **Discover** — Find relevant papers on a topic
- **Content** — Find specific facts, parameters, methods, or evidence within papers

A **planner** (`paperforge query-plan`) classifies your question and recommends the best command:

- `paper-context` for paper location and structure
- `search` for metadata discovery across titles, abstracts, and authors
- `retrieve` for body-text evidence retrieval within OCR fulltext

Smart Retrieval builds a vector index of paper full text using an embedding model.
When vectors are available, `retrieve --deep` adds semantic search on top of keyword matching.
The system automatically falls back to metadata search when vectors are not available.

**Requires:** an OpenAI-compatible API endpoint and an embedding model for vector features.
Metadata search works without any API key.
---

## Agent Integration

Deploy PaperForge Skills to your preferred AI agent platform. Skills give your agent access to paper search, OCR status, and literature management commands directly from the chat interface.

**Supported platforms:** Claude Code, OpenCode, and other OpenMP-compatible agents. Select your platform in settings and the Skills are deployed automatically.
