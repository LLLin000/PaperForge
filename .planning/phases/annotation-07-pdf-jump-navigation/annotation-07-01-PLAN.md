---
phase: annotation-07-pdf-jump-navigation
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - paperforge/plugin/src/testable.js
  - paperforge/plugin/tests/annotation-navigation.test.mjs
autonomous: true
requirements:
  - OVLY-01

must_haves:
  truths:
    - "D-04: Navigation resolves the annotation's preserved source attachment identity before choosing a PDF."
    - "D-05: Only canonical vault-relative PaperForge PDF metadata is accepted; raw external paths and annotation-key-derived guesses are rejected."
    - "D-06: The main PDF is selected only after identity confirmation, or when an identity-free annotation has exactly one unambiguous candidate."
    - "D-07: An unmatched or ambiguous attachment identity returns an unavailable result and never silently falls back to the main PDF."
    - "D-08: A valid non-negative integer pageIndex is converted to the one-based page number pageIndex + 1; pageLabel is display-only."
    - "D-11: Missing or invalid page data still yields a plain-PDF target when the PDF identity is confidently resolved."
  artifacts:
    - path: "paperforge/plugin/src/testable.js"
      provides: "Pure canonical PDF candidate extraction and annotation jump-target resolution"
      exports: ["extractVaultPdfPath", "buildPaperPdfCandidates", "resolveAnnotationPdfTarget"]
    - path: "paperforge/plugin/tests/annotation-navigation.test.mjs"
      provides: "Focused helper coverage for identity, canonical paths, ambiguity, and zero-to-one-based page conversion"
  key_links:
    - from: "paperforge/plugin/src/testable.js"
      to: "normalized annotation row pdfLocation"
      via: "pdfLocation.sourceAttachmentKey and pdfLocation.pageIndex"
      pattern: "sourceAttachmentKey|pageIndex"
    - from: "paperforge/plugin/src/testable.js"
      to: "current paper entry PDF metadata"
      via: "pdf_path plus any canonical supplementary candidates present on the entry"
      pattern: "pdf_path|supplementary|zotero_storage_key"
---

<objective>
Define and prove the conservative PDF jump-target contract for OVLY-01, implementing D-04 through D-08 and D-11 before runtime wiring.

Purpose: Make attachment identity correctness the first gate so a supplementary annotation can never be misdirected to an unrelated main PDF.
Output: Exported pure navigation helpers and focused Vitest coverage.
</objective>

<execution_context>
@C:/Users/tan/.codex/gsd-core/workflows/execute-plan.md
@C:/Users/tan/.codex/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md
@.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-PATTERNS.md
@.planning/phases/annotation-06-annotation-sidebar-and-list-view/annotation-06-04-SUMMARY.md
@paperforge/plugin/src/testable.js
@paperforge/plugin/tests/annotation-bridge.test.mjs
@paperforge/plugin/tests/annotation-list-viewmodel.test.mjs
@paperforge/adapters/zotero_paths.py
@paperforge/pdf_resolver.py

<interfaces>
The normalized annotation row already exposes `pdfLocation.sourceAttachmentKey`, `pdfLocation.pageIndex`, and `pdfLocation.pageLabel`. The current paper entry exposes canonical `pdf_path`; candidate extraction may also consume canonical `supplementary` and `zotero_storage_key` fields when present. Pure helpers return structured data only and must not receive `app`, `vault`, or `workspace`.
</interfaces>
</context>

## Artifacts this phase produces

- A fail-closed attachment-to-PDF resolution contract in `paperforge/plugin/src/testable.js`.
- Focused helper tests in `paperforge/plugin/tests/annotation-navigation.test.mjs`.

<tasks>

<task type="tdd" tdd="true">
  <name>Task 1: Write failing navigation helper contract tests</name>
  <files>
    paperforge/plugin/tests/annotation-navigation.test.mjs
  </files>
  <read_first>
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-CONTEXT.md` decisions D-04 through D-08 and D-11.
    - `paperforge/plugin/src/testable.js` normalization helpers and `module.exports` block.
    - `paperforge/plugin/tests/annotation-bridge.test.mjs` preserved `pdfLocation` contract.
    - `paperforge/adapters/zotero_paths.py` canonical vault-relative wikilink output.
  </read_first>
  <behavior>
    - Exact attachment identity selects the matching canonical candidate and never another candidate.
    - A supplied identity with no exact candidate returns `ok: false` with a stable non-sensitive reason and no path.
    - An identity-free annotation resolves only when exactly one canonical PDF candidate exists; zero or multiple candidates fail closed.
    - Wikilinks are unwrapped to vault-relative `.pdf` paths; absolute paths, URI schemes, traversal, non-PDF values, malformed wikilinks, and raw `storage:` values are rejected per D-05.
    - `pageIndex` 0 becomes page 1 and `pageIndex` 2 becomes page 3; negative, fractional, string, null, and missing values produce a plain-PDF target without arithmetic from `pageLabel`.
    - Candidate attachment keys may come from explicit canonical metadata or the canonical `/storage/{attachmentKey}/` path segment, but never from the annotation key.
  </behavior>
  <action>
    Create a dedicated Vitest file that imports the three planned exports and asserts the complete structured result, including `ok`, `path`, `page`, `linkText`, and a stable `reason` for unavailable or page-degraded cases. Use fixtures for main and supplementary candidates, duplicate/ambiguous identity, identity-free single candidate, unsafe paths, and zero-based page boundaries. Preserve existing annotation normalization tests; navigation conversion belongs only in this helper suite.
  </action>
  <verify>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs</automated>
    Expected RED state: the test command fails because the planned helper exports do not exist yet; failures must be assertion/import failures for these helpers, not syntax or environment failures.
  </verify>
  <acceptance_criteria>
    The failing tests enumerate every allowed resolution path and every fail-closed case required by D-04 through D-08 and D-11, without depending on Obsidian runtime APIs.
  </acceptance_criteria>
  <done>The RED suite fails only for the missing navigation helper contract.</done>
</task>

<task type="tdd" tdd="true">
  <name>Task 2: Implement pure fail-closed PDF target resolution</name>
  <files>
    paperforge/plugin/src/testable.js
    paperforge/plugin/tests/annotation-navigation.test.mjs
  </files>
  <read_first>
    - `paperforge/plugin/tests/annotation-navigation.test.mjs` RED expectations from Task 1.
    - `paperforge/plugin/src/testable.js` existing pure helper style and export ordering.
    - `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-PATTERNS.md` pure-helper and mirroring conventions.
  </read_first>
  <action>
    Implement `extractVaultPdfPath(value)`, `buildPaperPdfCandidates(entry)`, and `resolveAnnotationPdfTarget(row, entry)` as side-effect-free helpers, then export them. Normalize only canonical vault-relative PDF paths. Deduplicate candidates by path while retaining a provable attachment key from explicit metadata or a canonical storage segment. Resolve `pdfLocation.sourceAttachmentKey` first, use the D-06 identity-free single-candidate rule only when no attachment identity exists, and return no path for ambiguity or mismatch per D-07.

    For a confidently resolved PDF, accept only a non-negative integer `pdfLocation.pageIndex`; set `page` to `pageIndex + 1` and `linkText` to the Obsidian PDF page form `{path}#page={page}`. For invalid page data, keep `ok: true`, return the plain path as `linkText`, set `page` to null, and expose a stable page-degraded reason. Never use `pageLabel` for arithmetic and never include raw input values in reasons.
  </action>
  <verify>
    <automated>node --check paperforge/plugin/src/testable.js</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs</automated>
    <automated>npm.cmd --prefix paperforge/plugin test -- tests/annotation-bridge.test.mjs</automated>
  </verify>
  <acceptance_criteria>
    All helper tests pass; exact identity, unambiguous identity-free fallback, canonical path validation, fail-closed ambiguity, and pageIndex conversion are deterministic and do not mutate their inputs.
  </acceptance_criteria>
  <done>The pure resolver provides the tested contract consumed by the runtime plan.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Imported annotation metadata -> resolver | Source attachment identity and page data are untrusted imported values. |
| Paper index metadata -> vault path | Candidate paths must remain canonical vault-relative PDF paths. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-annotation-07-01 | Tampering | attachment candidate selection | mitigate | Require exact identity or the D-06 identity-free single-candidate rule; ambiguity and mismatch return no path. |
| T-annotation-07-02 | Information Disclosure | PDF path normalization | mitigate | Reject absolute paths, URIs, traversal, malformed wikilinks, and raw external/storage paths before runtime use. |
| T-annotation-07-03 | Tampering | page conversion | mitigate | Accept only non-negative integer pageIndex and derive one-based page exclusively with `pageIndex + 1`. |
| T-annotation-07-SC | Tampering | package supply chain | accept | No package-manager install occurs; tests use dependencies already declared in `paperforge/plugin/package.json`. |
</threat_model>

<verification>
- `node --check paperforge/plugin/src/testable.js`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-navigation.test.mjs`
- `npm.cmd --prefix paperforge/plugin test -- tests/annotation-bridge.test.mjs`
</verification>

<success_criteria>
- [ ] OVLY-01 has a pure, exported PDF target contract.
- [ ] D-04 through D-07 fail closed for uncertain attachment identity.
- [ ] D-05 rejects non-canonical/external path input.
- [ ] D-08 converts only valid pageIndex values to one-based pages.
- [ ] D-11 preserves a plain-PDF target for invalid page data after identity is proven.
</success_criteria>

<output>
After completion, create `.planning/phases/annotation-07-pdf-jump-navigation/annotation-07-01-SUMMARY.md`.
</output>
