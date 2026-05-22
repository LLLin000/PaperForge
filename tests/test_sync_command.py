from pathlib import Path

from paperforge.commands.sync import _write_orphan_state
from paperforge.core.result import PFResult


def test_write_orphan_state_uses_configured_system_dir(tmp_path: Path) -> None:
    (tmp_path / "paperforge.json").write_text(
        '{"vault_config": {"system_dir": "02_文献管理/System"}}',
        encoding="utf-8",
    )
    result = PFResult(
        ok=True,
        command="sync",
        version="1.0.0",
        data={"prune": {"preview": [{"key": "K1"}]}}
    )

    _write_orphan_state(tmp_path, result)

    expected = tmp_path / "02_文献管理" / "System" / "PaperForge" / "indexes" / "sync-orphan-state.json"
    wrong = tmp_path / "System" / "PaperForge" / "indexes" / "sync-orphan-state.json"
    assert expected.exists()
    assert not wrong.exists()
