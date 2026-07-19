# retrieval-routing

Route between vector and memory retrievers based on query type.

## 1. Authority principles

- **bootstrap** provides convenience capability fields only; it is not the runtime truth source
- **runtime-health** is the runtime truth source; always check it before making retrieval decisions
- **Semantic/vector retrieval is optional and supplementary** -- metadata and fulltext search are the primary retrieval path

## 2. Retrieval ladders

### Ladder A -- Paper Discovery (multi-arm strategy for discover-papers)

**Prerequisite: check `retrieve` availability**

Before any discovery arm, check if semantic/vector search is available:

```bash
$PYTHON -m paperforge --vault "$VAULT" embed status --json
```

If `data.db_exists == true` and `data.chunk_count > 0`, `retrieve` is usable.
Otherwise, skip Arm 1 and Arm 3 below.

**Strategy: choose discovery method based on user query type**

| User says...                          | Use arms                         |
|---------------------------------------|----------------------------------|
| Specific technical term, method, parameter ("bipolar pulses", "galvanotaxis chamber") | **Arm 1** (fulltext) + **Arm 2** (metadata) in parallel |
| Author name + year, topic title       | **Arm 2** (metadata) + optionally **Arm 1** |
| "collection X里有什么" / "collection里有什么" | **Arm 3** (collection inventory) |
| Vague / broad topic                   | **Arm 1** first, then **Arm 2** to supplement |

#### Arm 1 — Fulltext semantic search (if `retrieve` available)

```bash
$PYTHON -m paperforge --vault "$VAULT" retrieve "<query>" --json --limit 30
```

- Searches OCR fulltext chunks via vector embedding
- Catches concepts that appear only in Methods/Results/Discussion (not in title/abstract)
- Returns up to 30 chunk hits across papers; each hit includes `paper_id`, `section`, page
- If `ok: false` → skip this arm, proceed with Arm 2

#### Arm 2 — Metadata FTS search (always available)

```bash
$PYTHON -m paperforge --vault "$VAULT" search "<query>" --json --limit 30
    [--domain "<domain>"] \
    [--year-from <N>] [--year-to <N>] \
    [--ocr done|pending] \
    [--lifecycle <lifecycle>]
```

- Uses FTS5 on title, abstract, authors, journal, domain, collection_path
- Fast, always works
- Limit 30 by default; user can request more
- **Author+year search**: put author name in `<query>`, year in `--year-from`/`--year-to` (e.g. `search "Brighton" --year-from 1983 --year-to 1983`)

#### Arm 3 — Collection/domain inventory (full list, no truncation)

When the user wants to know what's in a collection or domain:

```bash
$PYTHON -m paperforge --vault "$VAULT" context --collection "<collection_path>" --json
$PYTHON -m paperforge --vault "$VAULT" context --domain "<domain>" --json
```

- Returns **every** paper in the collection/domain (no truncation)
- `context --collection` does prefix match on collection path
- `context --domain` does exact match on domain field
- If the list is very large (50+), summarize by year/author and ask user if they want to narrow

#### Result deduplication

- Collect all results from used arms into a single list
- Deduplicate by `zotero_key` (keep first occurrence)
- If `Arm 1` was used: prefer the Arm 1 entry (has fulltext match signal)
- After dedup, enrich top hits with `paper-context`

#### Large result set handling

- If any arm returns > 20 results, tell the user the total count
- Offer options: increase limit, narrow by year/domain/author, or show top N
- The `search` default limit is 20; `retrieve` default is 5 (increase to 30 for discovery)
- `context --collection` already returns all — no pagination needed

#### Fallback: when `retrieve` is unavailable

If `embed status` shows no vector index, skip Arm 1 entirely:

> Semantic fulltext search unavailable (vector index not built). Falling back to metadata search only. Run `paperforge embed build` to enable fulltext discovery.

Then proceed with Arm 2 only (or Arm 3 if collection/domain query).

### Ladder B -- Evidence Retrieval with rg

1. Generate metadata candidates via `paperforge search`
2. Narrow to papers with OCR/fulltext available (check runtime-health or paper-context)
3. Run `rg` over resolved fulltext set to locate exact evidence
4. Verify top hits with `paperforge paper-context` and local snippet reads

### Ladder C -- Evidence Retrieval without rg

1. Same metadata generation as Ladder B
2. Fallback to `grep` / `findstr` / system search
3. If agent environment supports, try installing rg (not assumed by default)
4. If no fulltext search tool is available, degrade to metadata-only evidence

### Ladder D -- Semantic Candidate Expansion (if `semantic_enabled` && `semantic_ready`)

1. Use `paperforge retrieve <query>` to expand candidate set
2. Never treat semantic hits as final evidence
3. Verify every semantic hit with rg / fulltext / paper-context before use

## 3. Fallback behavior when no OCR/fulltext exists

When runtime-health indicates no papers have OCR or fulltext available:

> Exact evidence verification is limited -- degrading to metadata-level support

Present a candidate paper list only; no snippet verification is performed.

## 4. Recommended limits

| Phase | Default limit | Why |
|-------|---------------|-----|
| Discovery — `search` | 30 | Catch papers beyond top 20 |
| Discovery — `retrieve` | 30 | Cover fulltext body matches |
| Discovery — `context --collection` | no limit | Must list everything |
| Enrichment — `paper-context` | top 10 | Enough for user to decide |
| Evidence snippets | top 5 | Deep verification is expensive |

## 5. Semantic degradation rule

```text
Retrieve availability check (run before any discovery):
  paperforge embed status --json  →  db_exists == true && chunk_count > 0

If retrieve is NOT available (no vector index):
- Skip all retrieve calls in every molecule
- Fall back to metadata-only strategy (search + context --collection)
- Inform user: "Fulltext semantic search unavailable. Run 'paperforge embed build' to enable body-text discovery."

If retrieve IS available:
- Use as primary discovery arm for technical/method queries
- Every semantic hit should be verified by paper-context before presenting as evidence
- Retrieve is a discovery tool, not a verification tool
```

