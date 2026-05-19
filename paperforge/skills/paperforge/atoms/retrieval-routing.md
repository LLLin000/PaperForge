# retrieval-routing

Route between vector and memory retrievers based on query type.

## 1. Authority principles

- **bootstrap** provides convenience capability fields only; it is not the runtime truth source
- **runtime-health** is the runtime truth source; always check it before making retrieval decisions
- **Semantic/vector retrieval is optional and supplementary** -- metadata and fulltext search are the primary retrieval path

## 2. Retrieval ladders

### Ladder A -- Paper Discovery (for discover-papers molecule)

1. Use `paperforge search` (metadata FTS) to find candidate papers
2. Enrich top hits with `paperforge paper-context`
3. Show candidate list to user

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

## 4. Recommended default limits

- Metadata candidate set: top 10-20 papers
- Fulltext/snippet verification: top 3-5 papers

## 5. Semantic degradation rule

```text
If semantic_enabled=false or semantic_ready=false:
- Do not call retrieve as primary path
- Fall back to metadata + rg/grep + paper-context

If semantic is available:
- Use only for candidate expansion
- Every semantic hit must be verified by rg/fulltext/paper-context before use
```

## 6. Commit convention

```
feat(skill): add retrieval-routing atom
```
