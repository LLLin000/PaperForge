from __future__ import annotations

import json
from pathlib import Path

from paperforge.memory.state_snapshot import write_vector_runtime
from tests.conftest import canonical_test_config


def test_vector_runtime_records_object_chunks(tmp_path: Path) -> None:
    canonical_test_config(tmp_path)
    write_vector_runtime(
        tmp_path,
        enabled=True,
        mode="openai_sdk",
        model="test-model",
        deps_installed=True,
        deps_missing=[],
        py_version="3.11",
        db_exists=True,
        chunk_count=1,
        body_chunk_count=2,
        object_chunk_count=3,
        build_state=None,
    )

    snapshot = json.loads(
        (tmp_path / "System" / "PaperForge" / "indexes" / "vector-runtime-state.json").read_text()
    )
    assert snapshot["object_chunk_count"] == 3
    assert snapshot["total_chunks"] == 6
