"""Sync plugin manifest.json version from paperforge.__version__."""
import json
from pathlib import Path
from paperforge import __version__

manifest_path = Path(__file__).resolve().parent.parent / "paperforge" / "plugin" / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest["version"] != __version__:
    manifest["version"] = __version__
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest.json: {manifest['version']} -> {__version__}")
else:
    print(f"manifest.json in sync (v{__version__})")
