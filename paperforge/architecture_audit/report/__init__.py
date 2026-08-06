"""Architecture report projection and CI gate (#134).

- `render_html.py` — self-contained HTML projection from DeterministicAudit
  plus optional ArchitectureReview. Read-only composition: it never mutates,
  reclassifies, or persists canonical facts. Deterministic and review layers
  keep separate visual labels and provenance.
- `gate.py` — fast, bounded CI gate consumed by the existing consistency
  audit. It reads DeterministicAudit only; ArchitectureReview and the HTML
  never determine exit status.
"""
