# Manual review addendum (user, 2026-11-09)

The user reviewed the smoke set visually. These findings override/extend the
`agent-visual-v1` rows and are recorded for the next Figure Quality iteration.
They are not pipeline fixes yet.

## 3QYCST4E — Figure 1A/1B split

| Item | Evidence |
|---|---|
| 1A detected | `figure_001`: caption block 4, asset block 3, page 2 |
| 1B missing | caption block 9 (`Figure 1B. Anatomical grading…`), asset block 8 bbox `[648,173,1101,1180]`, page 2; no separate figure object |
| Issue | two figures on one page; the replay emits one figure and drops 1B instead of splitting the composite |

## 28JLIHLS — crop, caption and page-merge gaps

| Figure | Finding |
|---|---|
| Figure 2 (p3) | crop omits the time annotations `24h`/`72h`; inner text belongs in the figure image. Agent label `crop_ok=true` is overridden to **false**. |
| Figure 5 (p4) | caption block 3 is still unassociated. Old claims: blocks 0/2 (left panels) and 6 (right panel, likely Figure 6); needs owner arbitration, not a blind merge. |
| Figure 6 (p4→p5) | image/panel continues on the next page but only p4 block 6 is claimed; cross-page merge missing. |
| Figure 9 | figure spans multiple pages; not merged and absent from the replay inventory. |

## SRNJDAA2 — deferred

Marked as a difficult item for a later pass; no action in this round.

## Q7 evidence follow-up (2026-11-09)

Read-only review of the supplied 7-page PDF (`10.1115/1.429661`) found:

- Figure 5 owners: p4/b0 + p4/b2; p4/b6 is a two-panel polar-plot asset directly above the Figure 6 caption, so it belongs to **Figure 6**, not Figure 5.
- Figure 6: no p5 continuation exists in this PDF; the supported asset set is p4/b6 only.
- Figure 9: no caption or image on any of the 7 pages; **HOLD** until a source page/PDF is supplied.
- The manual notes about a Figure 6 p5 continuation and a Figure 9 multi-page figure could not be reproduced against this source. See `docs/evidence/figure-quality/q7/REPORT.md`.

## Next use

These rows are the seed for the dev-set checks: composite split, figure-inner
text/crop expansion, caption owner arbitration, and cross-page/multi-page
merging. See `manual_findings.jsonl` for the machine-readable list.
