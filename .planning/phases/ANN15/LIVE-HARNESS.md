# ANN15 Live Obsidian Harness Record

**Phase:** ANN15 - Canvas Verification Gate and Live Harness Record  
**Generated:** 2026-07-08  
**Status vocabulary:** `PASS`, `FAIL`, `PENDING`, `NOT APPLICABLE`

---

## Environment

| Property | Value |
|----------|-------|
| **OS** | Windows 11 |
| **Node version** | v24.16.0 |
| **Obsidian availability** | **Not available** — this document was produced in an automated CLI environment that cannot launch the Obsidian GUI. All live Obsidian statuses are `PENDING` as a result. |
| **Automation environment** | OpenCode CLI agent (non-GUI) |

## Sample Paper

A recognized active paper with the following frontmatter properties is required to run this harness:

- `has_pdf: true`
- `do_ocr: true`
- `analyze: true`
- `ocr_status: done`

The specific Zotero key is determined by the operator at execution time. This harness does not prescribe a particular paper; any paper meeting the above criteria is sufficient.

## Execution Status

| Status | |
|--------|-|
| **Overall status** | `PENDING - not executed in this environment` |

All steps below are marked `PENDING - not executed in this environment` because the current environment cannot run Obsidian. This is an honest pending record, not a failure and not a pass.

---

## Canvas-First Manual Checklist

| # | Step | Expected observation | Actual observation | Status | Evidence |
|---|------|---------------------|--------------------|--------|----------|
| 1 | Open a recognized active paper in Obsidian | The paper's formal note opens with frontmatter fields visible (zotero_key, has_pdf, do_ocr, analyze, ocr_status). | `PENDING - not executed in this environment` | `PENDING` | |
| 2 | Open PaperForge Reading Canvas (command palette or button) | The Reading Canvas view opens. The Obsidian workspace transitions to show the canvas layout. | `PENDING - not executed in this environment` | `PENDING` | |
| 3 | Verify central reading surface renders | The full-text markdown content of the paper is displayed in the central column. Text is readable and pagination markers (`<!-- page N -->`) are present if applicable. | `PENDING - not executed in this environment` | `PENDING` | |
| 4 | Verify left/right card lanes contain annotation cards | Annotation cards appear in the left or right side lanes. Each card shows a snippet or title. Multiple cards may be present if annotations exist. | `PENDING - not executed in this environment` | `PENDING` | |
| 5 | Select a card → source surface scrolls to/focuses the corresponding source block | Clicking an annotation card causes the central reading surface to scroll to the source block that the card references. The source block is visually focused/highlighted. | `PENDING - not executed in this environment` | `PENDING` | |
| 6 | Select a source block → card lane scrolls to/focuses the corresponding card | Clicking or selecting a source block in the central reading surface causes the card lane to scroll to the annotation card that references that block. The card is visually focused/highlighted. | `PENDING - not executed in this environment` | `PENDING` | |
| 7 | Verify focused connector behavior (connector visible for focused pair only) | When a card-source pair is focused, a visual connector (line, bezier, or highlight) is drawn between them. When the focus changes to a different pair, the previous connector disappears and only the new pair's connector is visible. | `PENDING - not executed in this environment` | `PENDING` | |
| 8 | Verify the explicit fallback button/path exists when no source is available | When an annotation card has no resolvable source block, a fallback action (button, link, or status indicator) is displayed instead of a broken or empty state. The fallback is explicit and actionable (e.g., "Open PDF at page N" or "Source not available"). | `PENDING - not executed in this environment` | `PENDING` | |
| 9 | Verify refresh/stale handling (reload preserves state, stale shows warning) | Refreshing the canvas (e.g., via the refresh action) preserves the current state (open cards, scroll position, active focus). If data is stale, a visual warning or indicator is shown rather than silently displaying outdated content. | `PENDING - not executed in this environment` | `PENDING` | |
| 10 | Verify teardown or paper-change clears transient state | Closing the Reading Canvas or switching to a different paper clears transient canvas state (focused pairs, scroll positions, connectors). No stale DOM artifacts remain from the previous session. | `PENDING - not executed in this environment` | `PENDING` | |

---

## Observations

*No observations recorded — live execution has not occurred in this environment.*

---

## Native/Live Split

**This section documents the deliberate separation of confidence layers.**

1. **Automated tests and jsdom results do not prove live Obsidian behavior.**  
   The Vitest suite runs in a jsdom environment that simulates browser APIs. jsdom is not a real browser and does not replicate Obsidian's plugin runtime, DOM layout engine, or user interaction model. A passing test suite is necessary but not sufficient for live confidence.

2. **v0.3 PaperForge Reading Canvas confidence does not prove v0.2 native PDF overlay harness.**  
   The v0.3 canvas is a PaperForge-owned surface that renders markdown content in a controlled DOM layout. The v0.2 native PDF overlay harness operates inside the PDF viewer's DOM, using selectors like `pdf-viewer`, `pdf-embed`, and `data-page-number`. These are separate surfaces with separate DOM contracts and separate risk profiles. Passing v0.3 canvas verification does not imply v0.2 overlay correctness in a live Obsidian/PDF viewer environment.

3. **Native PDF overlay status: `PENDING`**  
   The v0.2 native PDF overlay harness has not been tested in live Obsidian during ANN15. It remains `PENDING` and is explicitly not merged into any v0.3 canvas confidence claim.

4. **Reporting rule**  
   Any future verification report or milestone summary must keep these confidence layers separate. Do not write "canvas passes" to mean "native overlay passes." Do not write "automated tests pass" to mean "live Obsidian verified."

---

## Limitations

| Limitation | Description |
|------------|-------------|
| No Obsidian GUI | This environment (OpenCode CLI agent on Windows 11) cannot launch Obsidian. All live interaction steps are `PENDING` by necessity. |
| jsdom vs real DOM | Vitest tests use jsdom, which does not replicate Obsidian's Electron/Chromium rendering engine, plugin lifecycle hooks, or real user interaction events (click, scroll, keyboard). |
| No video/screenshots | The plan explicitly makes screenshots and video optional. This document contains no visual evidence. |
| Single-environment scope | Only one OS (Windows 11) is documented. Behavior on macOS or Linux is not recorded. |
| Paper selection | The harness requires a recognized active paper. The specific paper affects which annotations and source blocks are available, which may influence step outcomes. |

---

## Final Conclusion

The live Obsidian harness record exists and is audit-ready. However, **all live steps are `PENDING - not executed in this environment`** because this automation environment cannot run Obsidian.

- The checklist is complete as a template and can be executed by any future operator with Obsidian access.
- The native/live split is explicitly documented.
- No pending live item is described as "done", "verified", or "passed" in this document.
- Conditional milestone confidence must carry the caveat that live Obsidian behavior is unproven in this session.
