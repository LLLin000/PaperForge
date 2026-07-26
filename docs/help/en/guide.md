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

Semantic search across your paper collection. Smart Retrieval builds a vector index of your papers' full text using an embedding model, then enables natural-language queries that go beyond keyword matching.

To use: configure an API key and model in Smart Retrieval settings, then click "Build Index". Once built, you can search from the Dashboard search bar.

**Requires:** an OpenAI-compatible API endpoint and an embedding model.

---

## Agent Integration

Deploy PaperForge Skills to your preferred AI agent platform. Skills give your agent access to paper search, OCR status, and literature management commands directly from the chat interface.

**Supported platforms:** Claude Code, OpenCode, and other OpenMP-compatible agents. Select your platform in settings and the Skills are deployed automatically.
