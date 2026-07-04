# Retrieval Layer

This context defines how PaperForge finds papers and fetches evidence from them. It covers lookup intents, retrieval units, and navigation concepts specific to paper-native retrieval.

## Language

### Retrieval Unit
The smallest typed paper-native object that can be indexed, recalled, and shown to a user or agent.
_Avoid_: chunk, text blob, paragraph group

### Body Unit
A retrieval unit built from section-aware body content and used for corpus-level evidence recall.
_Avoid_: paragraph trio, generic chunk

### Object Unit
A retrieval unit built from a figure or table plus its grounded local evidence.
_Avoid_: asset, image chunk, caption blob

### Structure Tree
The navigable section and object outline of one paper. It is the primary surface for in-paper navigation after a paper has been located.
_Avoid_: TOC dump, outline text

### Paper Manifest
The per-paper build control record for retrieval outputs, including hashes, versions, and unit counts.
_Avoid_: vector index, chunk cache

## Intents

### Paper Lookup
The task of locating a specific paper identity from title, author, year, DOI, citation key, or incomplete bibliographic evidence.
_Avoid_: search, retrieve

### Content Discovery
The task of finding which papers discuss a concept, method, comparison, or phenomenon across the corpus.
_Avoid_: paper lookup, title search

### Paper Navigation
The task of understanding a located paper's structure before fetching a specific section or evidence block.
_Avoid_: semantic retrieval, full-library search

### Scoped Fetch
The task of pulling exact content from a known paper, section path, node id, or narrow local scope.
_Avoid_: global search, blind retrieval

## Retrieval Semantics

### Structure-first
The rule that retrieval boundaries should be derived from paper structure and object boundaries before text chunk sizing concerns.
_Avoid_: regex-first, paragraph-first

### Trust-neutral
The rule that OCR health does not apply a paper-level retrieval penalty. OCR diagnostics may veto local junk units but must not hide an otherwise important paper.
_Avoid_: low-quality paper, degraded paper penalty

### Local Junk Veto
The rule that only clearly bad local units such as reference pollution, empty fragments, garbled text, or repeated header/footer noise are excluded from retrieval.
_Avoid_: quality filter, paper-level exclusion
