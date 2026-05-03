# Feature Landscape

**Domain:** AI-ready literature asset management on top of Obsidian + Zotero
**Researched:** 2026-05-03
**Confidence:** HIGH

## Framing

This milestone should treat PaperForge as a durable literature asset platform, not a bundle of one-off reading prompts. In this ecosystem, users already expect Zotero to remain the bibliographic source of truth, Obsidian to remain the knowledge workspace, and any AI layer to be grounded in traceable local assets rather than opaque summaries.

For v1.6, the highest-value features are the ones that make the library legible, repairable, standardized, and reusable by both humans and AI. The strongest differentiators are not "more extraction buttons"; they are reliable lifecycle state, health visibility, and reusable context packaging.

## Table Stakes

Features users will expect from the new milestone direction. Missing these makes the product feel like a collection of scripts rather than a literature asset manager.

| Category | Feature | Why Expected | Complexity | Existing Dependencies | Notes |
|---------|---------|--------------|------------|------------------------|-------|
| Lifecycle management | **Canonical asset index** | Long-lived libraries need one place to answer: what exists, what is missing, what is usable | High | `paperforge sync`, library-records, formal notes, OCR `meta.json`, `paperforge.json` | This is the foundation. Dashboard and AI entry points should read this, not recompute state separately. |
| Lifecycle management | **Explicit lifecycle state model** | Researchers need stable states like imported, indexed, OCR-ready, fulltext-ready, deep-read, AI-ready | Medium | Existing queue fields, OCR status, deep-reading status | Separate user intent from machine facts and derived readiness. |
| Health diagnostics | **Library health surfaces** | Large libraries inevitably drift; users expect to see broken PDFs, OCR failures, path drift, template drift | Medium | `doctor`, `repair`, path normalization, OCR pipeline | Should be visible per paper and aggregated per collection/library. |
| Asset standardization | **Stable per-asset schema** | AI workflows only scale when metadata, links, fulltext, and notes are predictably shaped | Medium | library-record frontmatter, formal note frontmatter, path normalization | Standardize identifiers, asset paths, provenance fields, and readiness flags. |
| Workflow progression | **Queue and next-step views driven by derived state** | Users expect actionable progression, not raw status fields | Medium | Existing Base views, canonical index, lifecycle model | "What should I do next?" is a table-stakes question for a maintained library. |
| Workflow progression | **Idempotent rebuild / refresh behavior** | Asset managers must safely recompute views after fixes without corrupting notes | Medium | current workers, repair flows, config single source of truth | Essential for trust in long-term use. |

## Differentiators

These are the features that can make PaperForge notably better than a generic Zotero-to-Obsidian sync.

| Category | Feature | Value Proposition | Complexity | Existing Dependencies | Notes |
|---------|---------|-------------------|------------|------------------------|-------|
| AI context entry points | **Ask-this-paper context pack** | Turns one paper into a reusable, grounded AI entry point with metadata, fulltext, figures, note links, and provenance | Medium | canonical index, OCR fulltext, figure-map, formal note, PDF link | Strong differentiator because it packages existing assets instead of inventing new extraction schemas. |
| AI context entry points | **Ask-this-collection / copy-context-pack** | Lets users move from single-paper workflows to collection-scale synthesis while staying source-grounded | Medium | collection metadata from Zotero, canonical index, note links | Aligns with NotebookLM-style source-grounded workflows, but stays local-first and reusable. |
| Workflow progression | **Library maturity / workflow level scoring** | Gives researchers a simple, motivating signal: how usable is this paper or collection for AI and downstream writing? | Medium | lifecycle model, health diagnostics, canonical index | Valuable if transparent and rule-based; bad if gamified or opaque. |
| Health diagnostics | **Actionable diagnostics with fix paths** | Better than just saying "broken"; tells the user exactly whether to sync, OCR, repair paths, or regenerate a note | Medium | `doctor`, `repair`, queue logic | This converts diagnostics from reporting into workflow guidance. |
| Asset standardization | **Traceable provenance bundle** | Every AI-facing output can point back to PDF, OCR text, notes, and source identifiers | Medium | normalized paths, formal notes, OCR artifacts | Important differentiator for research trust and reuse. |
| Lifecycle management | **Thin-shell plugin dashboard over canonical index** | Keeps UX polished without creating a second business-logic implementation | High | plugin shell, CLI, canonical index, `paperforge.json` | This is product-quality differentiation, not just engineering cleanliness. |

## Anti-Features

These are attractive distractions for this milestone. Avoid them.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Productizing discipline-specific extraction outputs** (PICO tables, mechanism tables, parameter tables, etc.) | High maintenance, domain-specific, and fights the platform direction | Ship reusable context packs and templates that specialized prompts can consume |
| **Replacing Zotero as the primary reference manager** | Zotero already owns collections, tags, duplicates, attachments, and citation workflows well | Treat Zotero metadata and attachment relationships as upstream truth |
| **Auto-running deep-reading agents from workers** | Breaks the worker/agent boundary and creates opaque automation | Keep agents user-invoked; improve readiness and context packaging instead |
| **A second lifecycle engine inside the Obsidian plugin** | Creates config drift and inconsistent state calculations | Plugin should read canonical index produced by Python logic |
| **"AI organizes everything" black-box features** | Researchers need traceability and repairability, not magic states they cannot audit | Use explicit states, rule-based maturity, and provenance-preserving outputs |
| **Feature explosion of per-prompt buttons** | Hard to maintain, quickly becomes UX clutter, and turns platform capabilities into brittle one-offs | Support a few generic entry points: ask-paper, ask-collection, copy-context-pack |
| **Cloud-hosted collaboration / sync for this milestone** | Expands scope far beyond the asset-foundation problem and conflicts with local-first constraints | Keep single-user, local-first architecture |
| **Full literature discovery graph product** (Litmaps/ResearchRabbit clone) | Discovery maps are valuable, but they are adjacent to asset reliability and curation, not the current foundation gap | Integrate with external discovery workflows through clean collections/tags/context packs |

## Feature Dependencies

```text
Single configuration truth (`paperforge.json`)
    -> enables canonical asset index

Canonical asset index
    -> enables lifecycle state model
    -> enables health dashboards
    -> enables queue views
    -> enables maturity scoring
    -> enables AI context packs

Stable per-asset schema
    -> enables trustworthy index derivation
    -> enables reusable AI entry points

Health diagnostics
    -> feeds workflow progression
    -> feeds maturity scoring

AI context packs
    -> require canonical index
    -> require provenance fields
    -> benefit from OCR/fulltext/figure readiness
```

## Milestone Scoping by Requested Category

### 1. Lifecycle management
- Must include: canonical index, explicit state model, recomputation rules
- Should defer: complicated branching workflows or multi-user orchestration

### 2. Health diagnostics
- Must include: PDF health, OCR health, path health, note/template/base health
- Should defer: speculative ML-based anomaly detection

### 3. Asset standardization
- Must include: canonical identifiers, normalized paths, provenance fields, consistent frontmatter contract
- Should defer: discipline-specific metadata taxonomies as built-ins

### 4. AI context entry points
- Must include: ask-this-paper, ask-this-collection, copy-context-pack
- Should defer: fully embedded chat platform, vector DB, or provider-specific lock-in as milestone-defining work

### 5. Workflow progression
- Must include: readiness views, next-step recommendations, maturity score/rules
- Should defer: complex automation that removes user control

### 6. What not to productize
- Do not turn every successful prompt into a first-class feature
- Do not hardcode scholarly extraction schemas into core product logic
- Do not duplicate Zotero or NotebookLM product surfaces

## Reusable Platform Capabilities vs One-Off Workflows

### Reusable platform capabilities to build
- Canonical index
- Lifecycle and health derivation
- Provenance-preserving asset schema
- Context pack generation
- Dashboard and queue views
- Rule-based maturity / next-step guidance

### One-off scholarly workflows to keep optional
- Medical evidence extraction tables
- Domain-specific summary formats
- Prompt-specific synthesis buttons
- Special-case manuscript scaffolds tied to one discipline

## MVP Recommendation

Prioritize:
1. **Canonical asset index + lifecycle state model**
2. **Library health surfaces + actionable next-step guidance**
3. **Generic AI context packs for paper and collection scopes**

Defer: **Domain-specific extraction products** — they should consume the platform, not define it.

## Sources

- Project direction and scope guardrails: `.planning/PROJECT.md` — HIGH confidence
- Zotero official docs: Collections and Tags (updated 2025-07-29) — https://www.zotero.org/support/collections_and_tags — HIGH confidence
- Zotero official docs: Adding Files to your Zotero Library (updated 2025-09-11) — https://www.zotero.org/support/attaching_files — HIGH confidence
- Zotero official docs: Duplicate Detection — https://www.zotero.org/support/duplicate_detection — MEDIUM confidence (older doc, still aligned with current product model)
- Obsidian official help: Bases / Bases syntax / Properties — via Context7 official help mirror — HIGH confidence
- Google official help: NotebookLM grounded chat with inline citations — https://support.google.com/notebooklm/answer/16164461?hl=en — HIGH confidence
- ResearchRabbit product positioning (discovery/visualization/organization) — https://www.researchrabbit.ai/ — MEDIUM confidence
- Litmaps product positioning (discover/visualize/monitor) — https://www.litmaps.com/ — MEDIUM confidence
- SciSpace product positioning (chat with PDF / literature review / extract data) — https://www.scispace.com/ — MEDIUM confidence
