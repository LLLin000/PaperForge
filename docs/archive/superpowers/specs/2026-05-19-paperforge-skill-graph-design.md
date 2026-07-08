# PaperForge Skill Graph 2.0 Design

**Date:** 2026-05-19
**Status:** Proposed
**Audience:** Maintainers, contributors, agentic implementers

---

## 1. Summary

PaperForge's current skill structure mixes user intents, workflow orchestration, retrieval strategy, and persistence side effects in one layer. This makes routing harder to reason about and makes the skill harder to extend safely.

This design restructures the PaperForge skill into a three-layer model:

- **Compound:** one top-level router (`SKILL.md`)
- **Molecules:** user-intent workflows
- **Atoms:** narrow retrieval, clarification, and persistence primitives

The core goal is to make the agent reliably answer two questions in order:

1. What does the user want?
2. Which workflow should handle it with the least ambiguity?

This design does **not** remove the existing mechanical command layer. `/pf-sync`, `/pf-ocr`, and `/pf-status` remain explicit non-molecule command routes handled before research intent classification.

This design also makes vector retrieval optional, prefers `rg` for evidence search when available, and separates lightweight structured paper notes from rich project-level reading logs.

---

## 2. Problems in the Current Structure

The current `paperforge` skill has several structural issues:

1. Files in `workflows/` are not the same kind of thing.
2. Some files represent user-intent workflows (`paper-search`, `paper-qa`, `deep-reading`).
3. Some files represent persistence actions or side-effect routines (`reading-log`, `project-log`).
4. Some files represent secondary extraction work (`methodology`).
5. Retrieval method choice is not skill-ized; it is embedded implicitly or not present.
6. Search currently behaves mainly like metadata lookup rather than a retrieval router.
7. Vector retrieval exists in the CLI but is not integrated as an optional strategy with explicit degradation rules.

The result is a skill that works, but whose layering is unclear. This increases routing mistakes and makes future modification harder.

---

## 3. Design Goals

### 3.1 Primary Goals

1. Rebuild the skill around clear user intents.
2. Separate compounds, molecules, and atoms by directory and responsibility.
3. Make top-level routing deterministic and explainable.
4. Make retrieval strategy explicit and capability-aware.
5. Treat vector retrieval as optional, never required.
6. Support both lightweight structured note capture and rich project-level evidence capture.

### 3.2 Secondary Goals

1. Reduce cognitive load for future maintainers.
2. Make skill files easier for agents to understand and edit.
3. Prevent routing drift as more retrieval modes are added.
4. Preserve explicit mechanical command ownership outside the research intent graph.

### 3.3 Non-Goals

1. No broad Python CLI redesign in this phase.
2. No vector-first architecture.
3. No attempt to unify every persistence format into one file.
4. No changes to deep-reading methodology itself beyond relocation/renaming.

---

## 4. Layer Model

### 4.1 Compound

`paperforge/SKILL.md`

The compound only does five jobs:

1. dispatch explicit mechanical commands
2. run bootstrap
3. inspect capabilities
4. identify top-level user intent
5. route to one molecule

It does not contain detailed retrieval ladders or long workflow internals.

### 4.2 Molecules

Molecules are the main user-facing workflows. They represent tasks the user actually intends to accomplish.

### 4.3 Atoms

Atoms are narrow, reusable instructions or action patterns. They include clarification behavior, retrieval strategy rules, and persistence actions.

Atoms are not user entry points.

### 4.4 Mechanical Command Layer

Mechanical slash commands remain outside the research intent graph.

They are handled directly by the compound before molecule routing:

- `/pf-sync`
- `/pf-ocr`
- `/pf-status`

These are execution routes, not research molecules.

---

## 5. Top-Level Research Intents

After mechanical command handling, the system should recognize only five top-level **research** intents.

### 5.1 `read_known_paper`

Use when the user already points to a specific paper or effectively means a specific paper.

Examples:

- `读一下 Smith 2024`
- `帮我看 ABC12345`
- `这篇讲了什么` when context already contains one unique paper

### 5.2 `discover_papers`

Use when the user wants a set of papers, not evidence passages.

Examples:

- `找骨科里关于支架的文章`
- `这个 collection 里有什么`
- `找标题里有 SOX9 的文献`

### 5.3 `find_supporting_evidence`

Use when the user wants exact evidence, terms, parameters, markers, or support for a claim.

Examples:

- `找 75 Hz`
- `找 SOX9 和 COL2A1`
- `找支持这句话的依据`
- `找 2.2 conductive scaffold 的证据`

### 5.4 `deep_analyze_paper`

Use when the user explicitly wants structured deep reading.

Examples:

- `/pf-deep`
- `精读这篇`
- `做三阶段阅读`

### 5.5 `capture_project_knowledge`

Use when the user wants to save, summarize, or archive research progress or evidence.

Examples:

- `记一下`
- `保存这次讨论`
- `整理成 reading log`
- `提取方法论`

This intent can appear in two modes:

1. **primary intent** — the user directly asks to save/archive/extract from already-established context
2. **post-action** — the user asks to save/archive after another molecule finishes work

### 5.6 Explicit Exclusion: `concept_discovery`

`concept_discovery` should **not** be a top-level intent.

It is an internal retrieval strategy that may appear inside retrieval routing, especially for evidence-oriented search. Users do not naturally express this as a first-class task, so it should remain a lower-layer strategy rather than a top-level route.

### 5.7 Primary Intent + Post-Action Model

Research intents are not fully exclusive. To keep routing deterministic while still supporting mixed user requests, the compound should use:

1. **one primary research intent**
2. **zero or more post-actions**

Examples:

- `找 75 Hz 的证据并记下来`
  - primary intent: `find_supporting_evidence`
  - post-action: `capture_project_knowledge`

- `读这篇然后提取方法论`
  - primary intent: `read_known_paper`
  - post-action: `capture_project_knowledge`

The compound always routes into one molecule first. Post-actions are triggered only after the primary molecule has produced usable output.

Exception:

- if the user is primarily asking to save/archive/extract from already-established session context, `capture_project_knowledge` may be the primary molecule directly

---

## 6. Molecules

### 6.1 `molecules/read-known-paper.md`

Handles `read_known_paper`.

Responsibilities:

1. resolve a specific paper
2. load paper context and fulltext if available
3. answer questions about that paper
4. maintain continuity for single-paper reading/Q&A
5. hand off to capture flow if the user explicitly asks to save or extract knowledge

Typical output:

- a uniquely identified paper
- a single-paper Q&A context

### 6.2 `molecules/discover-papers.md`

Handles `discover_papers`.

Responsibilities:

1. search for papers as paper-level objects
2. show candidates and readiness state
3. let the user refine or choose one paper
4. optionally hand off a chosen paper into single-paper reading or deep analysis

Typical output:

- candidate paper list

### 6.3 `molecules/find-supporting-evidence.md`

Handles `find_supporting_evidence`.

Responsibilities:

1. find evidence across papers
2. group hits by paper
3. support transitions into richer project capture or single-paper expansion
4. optionally hand off verified evidence into capture flow

Typical output:

- evidence hits grouped by paper

### 6.4 `molecules/deep-analyze-paper.md`

Handles `deep_analyze_paper`.

Responsibilities:

1. prepare scaffold
2. run pass 1/2/3 reading flow
3. run postprocess and validation

Typical output:

- formal note deep-reading section

### 6.5 `molecules/capture-project-knowledge.md`

Handles `capture_project_knowledge`.

Responsibilities:

1. append rich evidence to project reading log markdown
2. write lightweight per-paper JSONL summaries when appropriate
3. write project-log entries
4. optionally extract reusable methodology

Typical output:

- project reading log markdown
- reading-log JSONL entries
- project-log entries

---

## 7. Atoms

### 7.1 Intent and Bootstrap Atoms

- `bootstrap`
- `clarify-user-intent`

### 7.2 Retrieval Atoms

- `resolve-paper`
- `metadata-search`
- `rg-search`
- `grep-search`
- `semantic-retrieve`
- `paper-context`
- `read-fulltext`
- `read-fulltext-snippet`

### 7.3 Persistence Atoms

- `write-project-reading-log`
- `write-reading-log-jsonl`
- `write-project-log`
- `extract-methodology-card`

### 7.4 Retrieval Strategy Atom

- `retrieval-routing`

This atom encodes retrieval ladders and degradation rules. It is not a workflow and should not live alongside user-facing molecules.

---

## 8. Routing Order

Top-level routing in `SKILL.md` should follow a fixed order.

```text
0. handle explicit mechanical commands (/pf-sync /pf-ocr /pf-status)
0.1 handle explicit research workflow aliases (/pf-deep /pf-paper)
1. bootstrap
2. inspect capabilities and runtime health
3. can intent be determined confidently?
   - no -> clarify-user-intent
   - yes -> continue
4. does user already point to a single paper?
   - yes -> read_known_paper or deep_analyze_paper
5. otherwise, is the user asking for papers or evidence?
   - papers -> discover_papers
   - evidence/support/parameter/term -> find_supporting_evidence
6. if the primary ask is save/archive/extract from existing context
   - capture_project_knowledge as the primary molecule
7. detect post-actions
   - save/summarize/archive/extract -> capture_project_knowledge after primary molecule output exists
```

This routing order prevents several common failures:

1. treating `这篇里 75 Hz 怎么写的` as cross-library evidence search
2. treating `找支持这句话的文献` as simple paper browsing
3. treating `保存一下` as a reading task rather than a capture task

### 8.1 Output-Shape Test for `discover_papers` vs `find_supporting_evidence`

The compound should decide between these two by the **desired output shape**:

- route to `discover_papers` when the user wants a **candidate paper list**
- route to `find_supporting_evidence` when the user wants **quoted or snippet-level support**

Examples:

- `找骨科里关于支架的文章` -> `discover_papers`
- `找支持这句话的依据` -> `find_supporting_evidence`
- `给我几篇支持这个观点的文献` -> `discover_papers` first if the user wants papers; `find_supporting_evidence` if the user wants snippets or verified support passages

### 8.2 Explicit Research Workflow Aliases

The compound should recognize explicit research workflow commands before normal language classification:

- `/pf-deep` -> `deep_analyze_paper`
- `/pf-paper` -> `read_known_paper`

These aliases short-circuit normal language intent guessing, but still require object clarification if no paper is uniquely identified.

---

## 9. Clarify Intent Atom

### 9.1 Purpose

`clarify-user-intent` is a real atom, not an ad hoc conversational fallback.

Its job is to:

1. explain what PaperForge can do
2. ask one minimal clarifying question
3. return one clarified top-level intent

### 9.2 Trigger Conditions

Use it when any of the following is true:

1. user input is too short
2. input plausibly matches multiple top-level intents
3. a required object is missing
4. the user says `这篇` but context does not lock one unique paper

### 9.3 Interaction Rules

- ask at most two rounds
- do not loop indefinitely
- do not start retrieval before the intent is stable

### 9.4 Fixed Question Style

The atom should steer the user with a constrained explanation, for example:

```text
我可以帮你：
1. 找某篇文章
2. 找一批相关论文
3. 找支持某个观点/参数/术语的证据
4. 精读一篇文章
5. 记录到项目阅读笔记

你现在更想做哪一种？
如果你已经有 paper key / DOI / 标题，也可以直接发给我。
```

---

## 10. Capability Model

Bootstrap should return an explicit capability block. This removes guesswork from the agent.

Example target shape:

```json
"capabilities": {
  "rg": true,
  "metadata_search": true,
  "paper_context": true,
  "semantic_enabled": false,
  "semantic_ready": false
}
```

### 10.1 Required Meanings

- `rg`: whether `rg` is callable in the environment
- `metadata_search`: whether `paperforge search` can be used normally
- `paper_context`: whether `paperforge paper-context` is available
- `semantic_enabled`: whether vector search is enabled by configuration
- `semantic_ready`: whether vector search is actually usable now

### 10.2 Why Both Semantic Flags Are Needed

The vector database can be turned on or off. Even if the feature is enabled in configuration, the runtime may still not be ready. The agent needs both states to avoid false assumptions.

### 10.3 Authority Rule

`runtime-health` remains the runtime truth source.

- bootstrap may expose convenience capability fields for routing
- bootstrap must not invent an independent readiness model
- `semantic_ready` must derive from runtime-health semantics, not from a parallel bootstrap-only check

Design rule:

- bootstrap = discovery convenience
- runtime-health = runtime authority

---

## 11. Vector On/Off Rules

Vector retrieval is optional. It is never a top-level intent and never a hard dependency.

### 11.1 Rules

If either of these is false:

- `semantic_enabled`
- `semantic_ready`

Then:

1. semantic retrieval must not be used as the primary path
2. the workflow must degrade to metadata search + `rg`/`grep` + paper-context

If semantic retrieval is available:

1. it may be used for candidate expansion
2. it must not be treated as final evidence
3. every semantic hit must be verified by `rg`, fulltext, or paper-context before use

### 11.2 Design Principle

Semantic search is a supplementary atom, not a default backbone.

---

## 12. `rg` Strategy

`rg` is preferred but not mandatory.

### 12.1 Rules

1. prefer `rg` for evidence-oriented fulltext search
2. if `rg` is not available, the agent may try an installation path appropriate to the environment
3. if installation is not practical, degrade automatically to `grep`/`findstr`/CLI search
4. lack of `rg` must not block the workflow

### 12.2 Installation Policy

Do not assume `cargo` exists.

The skill should instruct the agent more generally:

- if `rg` is missing, choose a suitable installation approach for the user's environment
- otherwise degrade safely

This keeps the skill flexible across Windows/macOS/Linux and across user setups.

---

## 13. Retrieval Routing Atom

`atoms/retrieval-routing.md` should contain the detailed retrieval method logic.

It should not be a workflow. It should act as a reusable rulebook for molecules that need retrieval.

### 13.1 Responsibilities

1. classify lower-level retrieval mode inside a molecule
2. decide between metadata search, `rg`, semantic expansion, and paper-context
3. define degradation rules when capabilities are missing

### 13.3 Evidence Fallback Ladder

When `find_supporting_evidence` cannot rely on vector retrieval, it should use a concrete fallback ladder:

1. generate paper candidates with metadata search
2. narrow to papers whose OCR/fulltext is available where possible
3. run `rg` on the resolved fulltext set
4. if `rg` is unavailable, degrade to `grep`/`findstr`/CLI search
5. verify top hits with paper-context and local snippet reads

Recommended default limits:

- metadata candidate set: top 10-20 papers
- fulltext snippet verification: top 3-5 papers before expanding further

If no OCR/fulltext exists for any candidate, the molecule should report that exact evidence verification is limited and fall back to metadata-level support only.

### 13.2 Example Internal Strategies

The internal retrieval layer may still use distinctions like:

- exact evidence lookup
- paper discovery refinement
- concept expansion
- writing support expansion

But these are **internal retrieval modes**, not top-level user intents.

---

## 14. Search Output Contracts

Molecules must produce outputs that make the next transition obvious.

### 14.1 `discover-papers` Output Contract

Return paper candidates such as:

- zotero key
- title
- author
- year
- domain
- OCR/deep-reading state

Expected follow-ups:

- choose one paper
- refine search
- route into single-paper read or deep analysis

### 14.2 `find-supporting-evidence` Output Contract

Return grouped evidence hits such as:

- paper identity
- section or page reference
- matched text snippet
- short context

Expected follow-ups:

- append to project reading log markdown
- write lightweight per-paper JSONL summary
- choose one paper for deeper reading

The output should not be treated as a final prose artifact by default.

---

## 15. Reading Log Dual Model

This design keeps two parallel knowledge capture formats.

### 15.1 `reading-log.jsonl`

Purpose:

- lightweight structured capture
- per-paper summaries
- searchable by paper, tag, and verification state

Use it for:

- what was found in this paper
- how it is being used

It should remain concise.

### 15.2 Project Reading Log Markdown

Purpose:

- rich evidence workspace for the project
- detailed excerpts, context, and writing material
- directly editable and readable in Obsidian

Use it for:

- full paragraphs
- claim-oriented evidence organization
- writing support notes

It is written directly by the agent and is **not** rendered from JSONL.

### 15.3 Design Principle

- JSONL = card/index layer
- project reading log markdown = rich working layer

This avoids forcing detailed evidence into overly compressed structured fields while still preserving a machine-friendly lightweight index.

---

## 16. Directory Structure

The skill should be reorganized by layer, not by a generic `workflows/` bucket.

Target structure:

```text
paperforge/
├── SKILL.md
├── molecules/
│   ├── read-known-paper.md
│   ├── discover-papers.md
│   ├── find-supporting-evidence.md
│   ├── deep-analyze-paper.md
│   └── capture-project-knowledge.md
├── atoms/
│   ├── clarify-user-intent.md
│   ├── retrieval-routing.md
│   ├── write-project-reading-log.md
│   ├── write-reading-log-jsonl.md
│   ├── write-project-log.md
│   ├── extract-methodology-card.md
│   └── chart-reading/
└── scripts/
    ├── pf_bootstrap.py
    └── pf_deep.py
```

### 16.1 Why Directory-by-Layer Is Preferred

1. The layer is visible from the path itself.
2. Future maintainers do not need to guess whether a file is a workflow or a primitive.
3. It reduces structural drift over time.
4. Business-readable filenames still preserve domain meaning.

This is preferred over keeping everything in `workflows/`.

---

## 17. Migration Guidance from Current Files

Recommended mapping from current skill files:

- `paper-qa.md` -> `molecules/read-known-paper.md` (rename)
- `paper-search.md` -> split into:
  - `molecules/discover-papers.md`
  - `molecules/find-supporting-evidence.md`
- `deep-reading.md` -> `molecules/deep-analyze-paper.md` (rename)
- `reading-log.md` -> `atoms/write-reading-log-jsonl.md` (refocus as structured capture atom)
- `project-log.md` -> `atoms/write-project-log.md` (refocus as project-log atom)
- `methodology.md` -> `atoms/extract-methodology-card.md` (refocus as extraction atom)

Shared resources:

- `references/chart-reading/*` -> `atoms/chart-reading/*`

### 17.1 Naming Rule

The design standardizes on verb-led atom filenames for persistence and extraction actions:

- `write-project-reading-log`
- `write-reading-log-jsonl`
- `write-project-log`
- `extract-methodology-card`

This naming should be used consistently in both prose and file paths.

`project-engineering.md` should remain separate from the literature skill graph. It belongs to repository engineering support, not the literature intent graph.

---

## 18. Testing and Validation Focus

This design should be considered successful when:

1. the agent can classify ambiguous user inputs more reliably
2. molecules align with user-facing tasks rather than mixed responsibilities
3. vector on/off state no longer causes retrieval confusion
4. evidence search can degrade without failure when `rg` or vector retrieval is unavailable
5. maintainers can understand the skill structure by reading the directory layout alone

---

## 19. Implementation Sequence

Recommended order:

1. update `pf_bootstrap.py` to return capabilities
2. introduce new layered directories (`molecules/`, `atoms/`)
3. rewrite `SKILL.md` as compound router only
4. create `clarify-user-intent.md`
5. create `retrieval-routing.md`
6. split `paper-search` into the two new molecules
7. migrate reading/project/methodology instructions into atoms/internal references
8. validate routing examples and user prompts

---

## 20. Final Design Principle

The key shift is this:

```text
user language
  -> top-level intent
  -> molecule
  -> retrieval/persistence atoms
```

This replaces the current flatter structure where user intent, workflow orchestration, and persistence actions are mixed together.

The design aims to make PaperForge easier for both humans and agents to reason about, while preserving flexibility for richer retrieval in future phases.
