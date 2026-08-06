"""Deterministic architecture collectors (#133).

The orchestrator (`orchestrator.py`) scans repository source, merges Python
AST and TypeScript compiler facts into one ArchitectureSurvey, and invokes the
#131 pure reconciliation engine — it never reimplements rule semantics.

Tier model:
- Tier 1 — direct syntax sinks (filesystem writes, atomic replace, SQL
  mutation, subprocess spawn).
- Tier 2 — versioned wrapper-summary registry entries matched at callsites.
- Tier 3 — dynamic/unresolved calls recorded as UnresolvedFact, never guessed.

No Agent, MCP, LSP, network, vault, credential, OCR, Memory, or Embedding
operation is invoked by deterministic collection.
"""
from __future__ import annotations

from paperforge.architecture_audit.collectors.orchestrator import collect

__all__ = ["collect"]
