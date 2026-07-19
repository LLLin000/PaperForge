"""Sync plugin manifest.json, root manifest.json, and versions.json from paperforge.__version__.

Keeps plugin metadata in sync with the single version source in __init__.py.
"""
import json
from pathlib import Path
from paperforge import __version__

ROOT = Path(__file__).resolve().parent.parent
plugin_dir = ROOT / "paperforge" / "plugin"

# plugin/manifest.json
manifest_path = plugin_dir / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest["version"] != __version__:
    manifest["version"] = __version__
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"plugin/manifest.json: {manifest['version']} -> {__version__}")
else:
    print(f"plugin/manifest.json: OK (v{__version__})")

# root manifest.json (Obsidian community plugin registry)
root_manifest_path = ROOT / "manifest.json"
root_manifest = json.loads(root_manifest_path.read_text(encoding="utf-8"))
if root_manifest["version"] != __version__:
    root_manifest["version"] = __version__
    root_manifest_path.write_text(json.dumps(root_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"manifest.json (root): {root_manifest['version']} -> {__version__}")
else:
    print(f"manifest.json (root): OK (v{__version__})")

# versions.json
vers_path = plugin_dir / "versions.json"
versions = json.loads(vers_path.read_text(encoding="utf-8"))
if __version__ not in versions:
    versions[__version__] = "1.0.0"
    vers_path.write_text(json.dumps(versions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"versions.json: added v{__version__}")
else:
    print(f"versions.json: OK (v{__version__})")
