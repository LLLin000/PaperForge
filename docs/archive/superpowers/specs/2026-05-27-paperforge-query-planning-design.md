# PaperForge Query Planning and Skill Trigger Design

**Date:** 2026-05-27
**Status:** Proposed
**Audience:** Maintainers, CLI contributors, skill authors, agent implementers

---

## 1. Summary

PaperForge's current literature retrieval flow is too dependent on agent-side judgment about how to write queries for `search`, when to prefer `retrieve`, and when a zero-result search means "not found" versus "query was malformed for this command".

This design introduces a new CLI planning layer:

- `paperforge query-plan`

It becomes the truth source for:

1. query classification
2. retrieval mode selection
3. query writing guidance
4. zero-result fallback policy
5. user-interactive fallback suggestions when content lookup cannot safely degrade automatically

This design also proposes a minimal skill-layer improvement:

- keep the current top-level compound routing order intact
- improve the skill trigger contract so agents are more reliably forced into the `paperforge` skill for literature retrieval, paper reading, and evidence lookup tasks
- make molecule-level retrieval execution depend on `query-plan` rather than freeform agent improvisation

The goal is to make paper lookup and content lookup reliable without destabilizing the existing PaperForge skill graph.

---

## 2. Problems Observed

### 2.1 `search` is easy for agents to misuse

Agents currently write natural-language or mixed-structure queries such as:

- `Lin 2024 Electrical Stimulation`

This is unreliable for `paperforge search` because `search` behaves like metadata retrieval, not semantic fulltext discovery.

In practice, the query should be decomposed before execution:

- first-pass: `author + year`
- second-pass narrowing: human-visible candidate inspection, optionally using title words

### 2.2 Zero results are semantically ambiguous

A zero-result `search` currently does not distinguish between:

1. the paper is probably not in the library
2. the query was poorly formed for metadata search
3. the user is actually asking for content lookup rather than paper lookup

Agents then incorrectly conclude:

- `库里没有`

This is a contract failure.

### 2.3 `retrieve` is not just a low-confidence fallback

For content lookup tasks such as:

- finding where a method, parameter, term, or claim appears inside papers

`retrieve` should be the primary path, not the last step in a generic paper-discovery ladder.

### 2.4 Metadata search and fulltext search have different query-writing rules

The current system does not expose this clearly enough to agents.

As a result:

1. agents write retrieval-style queries for metadata search
2. agents write metadata-style queries for content retrieval
3. agents use one tool's output count to reason about another tool's scope

This causes both false negatives and unstable fallback behavior.

### 2.5 Skill triggering is still too phrase-fragile

The current `paperforge` skill frontmatter `description` contains many examples, but it still behaves like a keyword bucket rather than an explicit intent contract.

For high-value tasks such as:

1. paper discovery
2. known-paper reading
3. evidence lookup
4. deep reading
5. literature collection inspection

the skill should be treated as mandatory, not optional.

---

## 3. Design Goals

### 3.1 Primary Goals

1. Move query decomposition and retrieval planning into the CLI.
2. Prevent agents from interpreting zero-result search as library absence without additional reasoning.
3. Make `retrieve` the default for content lookup intent.
4. Make query-writing rules explicit per retrieval strategy.
5. Improve skill-trigger reliability without replacing the current skill graph.

### 3.2 Secondary Goals

1. Reduce prompt-only retrieval rules that can drift from implementation.
2. Preserve the existing compound routing order in `SKILL.md`.
3. Make testing easier with deterministic planning output.

### 3.3 Non-Goals

1. No redesign of the five top-level research intents.
2. No replacement of `/pf-paper` or `/pf-deep`.
3. No silent auto-reading of source files outside current safety rules.
4. No attempt to make `search` itself become semantic fulltext retrieval.

---

## 4. Design Principle

PaperForge retrieval should separate two user jobs:

### 4.1 Paper Lookup

The user wants to identify which paper(s) to inspect.

Examples:

- `找 Lin 2024 那篇`
- `找几篇关于 electrical stimulation 的文章`
- `这个 collection 里有什么`

### 4.2 Content Lookup

The user wants to find where some concept, parameter, method, or claim appears in paper content.

Examples:

- `找 galvanotaxis`
- `找 75 Hz`
- `找这句话的支持`
- `看看哪些文章正文里提到了某个方法`

These two jobs must not share the same first-pass query contract.

---

## 5. New CLI Command: `paperforge query-plan`

### 5.1 Purpose

`query-plan` is a planning command, not a retrieval command.

It does not search the library directly. It tells the agent:

1. what kind of query this is
2. which command should be used first
3. how the query should be rewritten
4. what fallback sequence should apply

### 5.2 Example CLI

```bash
paperforge query-plan "<query>" --intent discover --json
paperforge query-plan "<query>" --intent content --json
paperforge query-plan "<query>" --intent known-paper --json
```

### 5.3 Intent Values

Allowed planning intents:

- `discover`
- `content`
- `known-paper`

These map onto existing molecules without replacing them:

- `discover` -> `discover-papers`
- `content` -> `find-supporting-evidence`
- `known-paper` -> `read-known-paper`

### 5.4 Output Contract

Recommended shape:

```json
{
  "ok": true,
  "command": "query-plan",
  "version": "1.5.x",
  "data": {
    "intent": "discover",
    "query_class": "mixed_query",
    "signals": {
      "doi": null,
      "zotero_key": null,
      "citation_key": null,
      "author_tokens": ["Lin"],
      "year_tokens": [2024],
      "title_like_tokens": ["Electrical", "Stimulation"],
      "content_terms": []
    },
    "signal_priority": [
      "doi",
      "zotero_key",
      "citation_key",
      "author",
      "year",
      "title",
      "topic"
    ],
    "recommended_primary": {
      "command": "search",
      "args": {
        "query": "Lin",
        "year_from": 2024,
        "year_to": 2024,
        "limit": 10
      }
    },
    "query_writing_rules": [
      "For metadata search, prefer author and year over mixed natural-language query strings.",
      "Do not include title words in first-pass author+year lookup."
    ],
    "fallback_plan": [
      {
        "when": "zero_results",
        "action": "report_noncanonical_query_risk"
      },
      {
        "when": "multiple_results",
        "action": "let_user_or_agent_visually_narrow"
      }
    ]
  }
}
```

---

## 6. Query Classification

`query-plan` should classify input into stable, agent-facing categories.

### 6.1 `identifier_exact`

Used when the input contains:

- DOI
- zotero key
- citation key

Primary route:

- `paper-context`

No freeform search should happen first.

### 6.2 `author_year`

Used when the input contains a plausible author token and a year.

Primary route:

- `search "<author>" --year-from YYYY --year-to YYYY`

Title words must not be included in first-pass execution.

### 6.3 `metadata_topic`

Used when the user is discovering papers by topic, title-like words, domain, or collection.

Primary route:

- `search`
- or `context --collection` / `context --domain` when scope terms are explicit

### 6.4 `content_term`

Used when the user wants to find content inside papers:

- parameter
- method
- exact term
- evidence support

Primary route:

- `retrieve`

### 6.5 `mixed_query`

Used when the query mixes multiple signal types into one string.

Example:

- `Lin 2024 Electrical Stimulation`

For `discover`, mixed queries should be normalized into structured metadata lookup.

For `content`, mixed queries should be split into content-bearing terms only if the user is searching inside papers.

---

## 7. Signal Reliability Hierarchy

The CLI should expose a stable signal hierarchy so the agent stops guessing.

### 7.1 High-Reliability Signals

These should dominate routing:

1. `doi`
2. `zotero_key`
3. `citation_key`
4. `author`
5. `year`

### 7.2 Medium-Reliability Signals

1. short title phrase
2. explicit domain
3. explicit collection

### 7.3 Lower-Reliability Signals

1. broad topic phrase
2. natural-language description
3. long mixed query strings

### 7.4 Rule

When a high-reliability signal exists, lower-reliability tokens must not corrupt the first-pass query.

Example:

- if author + year are present, title words do not belong in first-pass `search`

---

## 8. Query Writing Rules by Command

These rules should appear both in `query-plan` output and in skill prose.

### 8.1 `paper-context`

Use when:

- DOI
- zotero key
- citation key
- already-locked single paper

Writing rule:

- use exact identifier, no query rewriting

### 8.2 `search`

Use when:

- paper lookup
- paper discovery
- collection/domain inspection

Writing rules:

1. prefer author and year for first-pass known-paper lookup
2. prefer short metadata-facing terms
3. do not mix long title fragments into first-pass author+year lookup
4. treat titles as a manual narrowing aid after candidate generation, not as mandatory first-pass input

### 8.3 `retrieve`

Use when:

- content lookup
- evidence lookup
- in-paper term finding
- method/parameter/claim search

Writing rules:

1. prefer content-bearing terminology
2. use terms as they are likely to appear in正文
3. completeness matters more than metadata neatness
4. do not treat `retrieve` as final evidence without later verification when exact quoting matters

### 8.4 `rg` / `grep`

Use when:

- exact fulltext verification is needed
- `retrieve` is unavailable or insufficient

Writing rules:

1. prefer literal strings, units, abbreviations, parameter patterns, and stable terms
2. do not use long conversational questions as grep queries

---

## 9. Zero-Result Semantics

### 9.1 Problem

A zero-result `search` should not automatically mean:

- `库里没有`

### 9.2 New Contract

When `query-plan` classifies the query as noncanonical for the chosen command, the CLI should distinguish:

1. `no_match_after_normalization`
2. `noncanonical_query_for_command`
3. `likely_wrong_intent_for_command`

### 9.3 Recommended Behavior

For known-paper and discover flows:

1. `query-plan` rewrites the first pass
2. the molecule executes the recommended primary command
3. if zero results remain after normalized first pass, the response may say the library likely lacks a match
4. before that point, the response must not treat raw zero results as absence

### 9.4 Why Planning Is Better Than Silent Auto-Retry in `search`

This design intentionally keeps the retry logic visible at the planning layer.

That preserves:

1. transparency
2. deterministic testing
3. compatibility with existing molecules

---

## 10. Content Lookup Contract

### 10.1 Primary Rule

If the user's intent is to find something inside paper content, the first retrieval command should be:

- `retrieve`

This is true even if paper discovery would also be possible.

### 10.2 `retrieve` Is Not a Mere Late Fallback

For content lookup, `retrieve` is the primary route, not a low-priority optional add-on.

### 10.3 Fallback When `retrieve` Is Unavailable or Returns 0

Do not automatically conclude failure.

Instead, return a structured fallback mode suggestion. The preferred fallback family is:

- fulltext exact search (`rg` / `grep`)

### 10.4 User-Interactive Fallback

When `retrieve` is unavailable or insufficient, the CLI should support returning:

- `interactive_fallback_required: true`
- `suggested_modes`

Example modes:

1. limit to a collection/domain and run `rg`
2. run broader fulltext grep now
3. use metadata search first to narrow paper candidates

This preserves user control when exact fulltext search could be expensive or noisy.

---

## 11. Scope Assessment Rules

### 11.1 Important Constraint

Metadata search result count must not be treated as the truth source for fulltext grep scope.

This is because:

1. metadata and正文 have different recall behavior
2. a term absent from abstract/title may still be common in methods or results
3. a term common in metadata may still be rare in正文

### 11.2 Recommended Scope Sources

Scope estimation should prefer:

1. explicit collection/domain restriction
2. inventory-level counts from `context`
3. fulltext-ready counts from runtime/index data
4. only then metadata search counts, and only as weak hints

### 11.3 CLI Output Suggestion

When relevant, `query-plan` may return:

```json
"scope_assessment": {
  "source": "collection_inventory",
  "estimated_paper_count": 42,
  "fulltext_ready_count": 39,
  "confidence": "medium",
  "recommended_mode": "ask_user_before_broad_grep"
}
```

This lets the skill ask the user with evidence rather than guesswork.

---

## 12. Skill Routing Changes: Minimal and Safe

### 12.1 Keep the Current Compound Order

The current top-level routing order in `SKILL.md` should remain intact:

1. mechanical commands
2. aliases
3. capture
4. known paper
5. discover papers
6. supporting evidence
7. clarify
8. post-action capture

This design does not change the compound graph.

### 12.2 Insert `query-plan` Only Inside Molecules

Recommended insertion points:

- `read-known-paper.md`
- `discover-papers.md`
- `find-supporting-evidence.md`

The compound should not call `query-plan` globally.

Instead:

1. compound decides the molecule
2. molecule calls `query-plan`
3. molecule executes the recommended retrieval command

This keeps routing simple and avoids top-level drift.

### 12.3 Molecule-Specific Use

#### `read-known-paper`

Use `query-plan --intent known-paper`

Expected outcomes:

- identifier -> `paper-context`
- author+year -> normalized `search`
- vague title/topic -> `search` or `paper-status`

#### `discover-papers`

Use `query-plan --intent discover`

Expected outcomes:

- collection/domain inventory route
- metadata search route
- normalized mixed-query route

#### `find-supporting-evidence`

Use `query-plan --intent content`

Expected outcomes:

- primary `retrieve`
- interactive fallback suggestion when vector retrieval is unavailable or returns poor signal

---

## 13. Skill Trigger Improvements

### 13.1 Problem

The current `description` lists many example phrases, but it does not strongly encode the idea that certain intents must always load the PaperForge skill.

### 13.2 Proposed Direction

Revise the skill frontmatter description and top prose so the trigger is intent-driven, not just phrase-driven.

### 13.3 Target Trigger Semantics

The `paperforge` skill must be invoked whenever the user is asking for any of the following:

1. literature retrieval from the vault/library
2. identifying or reading a specific paper in the library
3. finding evidence, parameters, methods, or terms inside stored papers
4. inspecting collections or domains in the literature vault
5. deep reading or structured discussion of a stored paper
6. saving paper-derived research knowledge into PaperForge logs

### 13.4 Description Direction

The description should speak in terms of user intents, for example:

- mandatory for paper lookup, paper discovery, evidence lookup, deep reading, and PaperForge research-memory capture

This is preferable to relying only on examples like:

- `找文献`
- `找支持`
- `collection`

### 13.5 Why This Helps

Intent-driven trigger wording:

1. generalizes better to unseen phrasing
2. reduces accidental non-use of the skill
3. aligns better with the AGENTS.md rule that literature retrieval and reading must go through PaperForge

---

## 14. CLI and Documentation Consistency Fixes

The current system must also fix misleading terminology.

### 14.1 `search` Description Fix

`search` should no longer be described as:

- full-text search across the library

It should be described as:

- metadata/FTS search across indexed paper fields such as title, abstract, author, journal, domain, and collection

### 14.2 `retrieve` Description Fix

`retrieve` should be described as:

- semantic content retrieval across OCR fulltext

### 14.3 Agent Context Rules

`agent-context` should explicitly state:

1. `search` and `retrieve` have different query-writing contracts
2. content lookup should begin with `retrieve`
3. author+year first-pass lookup should exclude title words
4. raw zero-result search is not enough to conclude absence

---

## 15. Versioning and Compatibility Model

### 15.1 Problem

The current skill preflight expects the skill frontmatter version to match the plugin/package version.

This is too coarse and creates ambiguity:

1. plugin code may change while the skill contract does not
2. the skill contract may change while plugin packaging changes are unrelated
3. maintainers cannot tell whether a mismatch means a real incompatibility or only a release-version drift

### 15.2 Design Rule

PaperForge should distinguish:

1. release/package version
2. skill contract version
3. compatibility level

These are not the same thing and should not be forced into one shared version string.

### 15.3 Proposed Fields

Recommended model:

- `plugin_version`
- `skill_version`
- `skill_api_version`

#### `plugin_version`

Meaning:

- the released PaperForge package/plugin version

Used for:

- manifest
- installer/update flow
- git tag / release tracking
- package-level changelog

Example:

- `1.5.14`

#### `skill_version`

Meaning:

- the concrete shipped version of the `paperforge` skill bundle

Used for:

- skill deployment identity
- debugging whether the vault has the latest skill copy
- distinguishing skill-only updates from package-only updates

Example:

- `2026-05-27.1`

#### `skill_api_version`

Meaning:

- the compatibility contract version between CLI planning/runtime outputs and the skill's expectations

Used for:

- preflight compatibility checks
- determining whether the currently deployed skill can safely interpret the current CLI outputs

Example:

- `2`

### 15.4 Compatibility Principle

Agents should care primarily about:

- `skill_api_version`

Maintainers may also inspect:

- `skill_version`

Package release tooling should care primarily about:

- `plugin_version`

### 15.5 Preflight Rule Change

The current rule:

- skill frontmatter version must equal package version

should be removed.

Replace it with:

1. confirm the skill exists and is readable
2. confirm the deployed skill reports `skill_api_version` compatible with the CLI
3. report `plugin_version` and `skill_version` for debugging
4. if `skill_api_version` mismatches, tell the user to run `paperforge update`

### 15.6 Bootstrap Contract Change

`pf_bootstrap.py` should return all three fields when available:

```json
{
  "plugin_version": "1.5.14",
  "skill_version": "2026-05-27.1",
  "skill_api_version": 2
}
```

This should replace the current weaker pattern where the skill version may be inferred only from the skill file's frontmatter.

### 15.7 Example Scenarios

#### Scenario A: package update, skill unchanged

- `plugin_version` changes
- `skill_version` unchanged
- `skill_api_version` unchanged

Interpretation:

- safe; the skill contract did not change

#### Scenario B: skill routing update, package release also happens

- `plugin_version` changes
- `skill_version` changes
- `skill_api_version` may or may not change

Interpretation:

- if `skill_api_version` unchanged, this is a compatible skill refinement
- if `skill_api_version` changes, the deployed skill and CLI must be updated together

#### Scenario C: local vault still has old deployed skill

- installed CLI/package is newer
- deployed skill in vault is older
- `skill_api_version` mismatch

Interpretation:

- this is a real compatibility problem and the user should update/redeploy the skill

### 15.8 Frontmatter Direction

The `paperforge` skill frontmatter should no longer overload a single `version` field to mean package release compatibility.

Recommended direction:

- keep `source: paperforge`
- add `skill_version`
- add `skill_api_version`

If a plain `version` field is still required by tooling, it should be documented as the skill bundle version, not the package version.

---

## 16. Testing Focus

### 15.1 CLI Query Planning Tests

Add tests for:

1. DOI -> `paper-context`
2. zotero key -> `paper-context`
3. `Lin 2024 Electrical Stimulation` with `discover` intent -> normalized `search(author + year)`
4. `galvanotaxis` with `content` intent -> `retrieve`
5. content lookup without vector availability -> interactive fallback plan

### 15.2 Skill Contract Tests

Add tests to assert:

1. molecules reference `query-plan`
2. content molecule makes `retrieve` the primary route
3. known-paper molecule prioritizes identifiers and author+year
4. skill description contains intent-level trigger language

### 15.3 Regression Target

The key regression to prevent is:

- raw mixed query -> zero results -> agent claims the paper is absent

---

## 17. Implementation Sequence

Recommended order:

1. add `paperforge query-plan` CLI command
2. add query classification and planning logic
3. update `agent-context` and command help text
4. introduce `plugin_version` / `skill_version` / `skill_api_version` contract in bootstrap and skill metadata
5. revise skill `description` and top trigger prose
6. update `read-known-paper.md`
7. update `discover-papers.md`
8. update `find-supporting-evidence.md`
9. add tests for CLI planning, version compatibility, and skill contracts

---

## 18. Final Principle

The agent should not be responsible for inventing PaperForge retrieval syntax.

The agent's job should be:

1. route to the correct molecule
2. ask the CLI how to search
3. execute the recommended command
4. interpret the result honestly

The CLI's job should be:

1. classify the query
2. expose signal strength
3. recommend the correct retrieval strategy
4. prevent false "not found" conclusions from malformed first-pass queries

This preserves the current skill graph while making retrieval behavior far more stable.
