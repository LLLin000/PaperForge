# Regression 100 independent acceptance

## Decision

**GO — corrected manifest-level delivery gate passes.** The previous three gaps were caused by comparing old/source figure IDs with the replay's renamed or split IDs. No replay manifest delivery gaps remain.

## Corrected structural gates

| Gate | Result |
|---|---:|
| Replay errors | 0 — PASS |
| Unique IDs | 100/100 papers — PASS |
| Manifest-scheduled figure assets missing | 0 — PASS |
| Manifest-scheduled figure renders missing | 0 — PASS |
| Dangling fulltext targets | 0 — PASS |
| Text decrease | 0 papers — PASS |
| New replay pending inventory markers | 4 across 3 papers — inventory-only; not a publication start or delivery failure |
| Table claim changes vs source | 2 in `64AWS4SU`, `G5QGQ9PB` — unchanged; report only |

Delivery is checked against the replay manifest's scheduled figure IDs and its `assets/figures` / `render/figures` paths. This is a dry-run manifest check, not a claim that replay wrote files to the read-only vault.

## Reclassified delivery records

- `6QNRHRKX`: the replay schedules `assets/figures/figure_main_p002_b7.jpg` and `render/figures/figure_main_p002_b7.md` for old `figure_unknown_000`. Old `figure_unknown_001` is split by its source asset claims across replay figures `figure_004` and `figure_006`, each with its own asset/render pair. The old IDs are absent by design; all four replay figure IDs are present in the manifest. This is an old-ID mapping/split diagnostic mismatch, not a delivery gap.
- `M36WA39N`: old `figure_005_continued_p010_b19` maps to replay `figure_005`, scheduled as `assets/figures/figure_005.jpg` and `render/figures/figure_005.md`. This is a rename, not a delivery gap.

The delivery gate now compares manifest IDs to scheduled figure asset/render paths, rather than treating removed old-ID paths as missing new outputs.

## Pending-marker classification

The four markers are replay inventory `unresolved_clusters`, not unpublished starts: `6GB9I9KG` has one (`unresolved_cluster_001`, page 4), `8K39NHUQ` has one (`unresolved_cluster_001`, page 15), and `AT99P8YS` has two (`unresolved_cluster_001` page 9 and `unresolved_cluster_002` page 10). No held figures were present in these replay inventories. They are separately counted as inventory state and do not fail the manifest delivery gate; each cluster is scheduled in the replay manifest.

## Smoke

Smoke replay: 9/10 passed. The sole failure remains `55EKJRBC` with one dangling fulltext target; no new manifest asset/render gaps, text decrease, or duplicate IDs were observed.

## Read-only safety

`extract_and_write_objects(..., dry_run=True)` now skips journal recovery, so a dry-run cannot mutate a stale materialization journal. A post-run audit found no `.materialization-journal.json` in the 100 regression paper folders. Because the earlier replay was run before this guard and recovery could remove a stale journal, the pre-run journal state cannot be established from that post-run audit.
