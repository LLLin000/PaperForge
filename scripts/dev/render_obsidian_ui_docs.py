#!/usr/bin/env python3
"""Render PaperForge Obsidian UI all-states & Base design screenshots from live TS components.

Usage:
    python scripts/dev/render_obsidian_ui_docs.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_DIR = REPO_ROOT / "paperforge" / "plugin"
SHIM_PATH = REPO_ROOT / "scripts" / "dev" / "_obsidian_browser_shim.ts"
ENTRY_PATH = REPO_ROOT / "scripts" / "dev" / "_obsidian_ui_showcase.ts"
STYLES_CSS = PLUGIN_DIR / "styles.css"
OUT_DIR = REPO_ROOT / "docs" / "images" / "ui-states"

SCENES = [
    "01-base-workbench-all-states",
    "02-base-empty-and-filtered-states",
    "03-dashboard-global-modes",
    "04-dashboard-collection-mode",
    "05-dashboard-paper-mode-living-memory",
    "06-dashboard-search-and-recovery-states",
    "07-pdf-annotator-human-and-ai-layers",
    "08-pdf-annotator-provenance-and-empty-states",
    "09-settings-control-center-six-states",
    "10-settings-setup-wizard-four-stages",
    "11-settings-ocr-and-memory-details",
    "12-ocr-workspace-and-modals",
    "13-express-onboarding-and-domain-preview",
]


def _find_browser_executable() -> str | None:
    for cmd in ("google-chrome", "chromium", "chrome", "msedge"):
        found = shutil.which(cmd)
        if found:
            return found
    prog_files = [
        os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    ]
    candidates = [
        ("Google", "Chrome", "Application", "chrome.exe"),
        ("Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for root in prog_files:
        for parts in candidates:
            p = Path(root).joinpath(*parts)
            if p.exists():
                return str(p)
    return None


def _bundle_showcase(build_dir: Path) -> Path:
    bundle_js = build_dir / "showcase.js"
    builder_cjs = build_dir / "build.cjs"

    path_shim = build_dir / "shim_path.js"
    path_shim.write_text(
        r"""
const sep = "/";
function join(...parts) {
  return parts.filter(Boolean).join("/").replace(/\\+/g, "/").replace(/\/+/g, "/");
}
function resolve(...parts) { return join(...parts); }
function basename(p) { return String(p || "").split(/[\\/]/).pop() || ""; }
function dirname(p) {
  const s = String(p || "").replace(/\\+/g, "/").split("/");
  s.pop();
  return s.join("/") || ".";
}
function extname(p) {
  const b = basename(p);
  const i = b.lastIndexOf(".");
  return i > 0 ? b.slice(i) : "";
}
function isAbsolute(p) { return /^([A-Za-z]:[\\/]|\/)/.test(String(p || "")); }
function relative(_a, b) { return String(b || ""); }
module.exports = { sep, join, resolve, basename, dirname, extname, isAbsolute, relative };
""",
        encoding="utf-8",
    )

    fs_shim = build_dir / "shim_fs.js"
    fs_shim.write_text(
        r"""
module.exports = {
  existsSync: (p) => !String(p || "").includes("missing"),
  readdirSync: (p) => (String(p || "").includes("exports") ? ["library.json", "骨科.json"] : []),
  readFileSync: (p) => {
    const s = String(p || "");
    if (s.includes("pointer.json")) {
      return JSON.stringify({ python_path: "python", paperforge_version: "2.2.0" });
    }
    if (s.includes("versions/v1")) {
      return "# 3.1 Results\n\nPEMF stimulation at 75 Hz improved early osteogenesis (p<0.05).\n\nDiscussion draft v1.";
    }
    if (s.includes("versions/v2") || s.includes("render/fulltext.md")) {
      return "# 3.1 Results\n\nPEMF stimulation at 75 Hz ± 5 µM markedly enhanced osteogenesis via L-type Ca2+ influx (p=0.003).\n\nValidated against Figure 1B and Nifedipine blockade.";
    }
    return "";
  },
  statSync: () => ({ isDirectory: () => false, isFile: () => true, size: 4200, mtimeMs: Date.now() }),
  watch: () => ({ close: () => {} }),
};
""",
        encoding="utf-8",
    )

    os_shim = build_dir / "shim_os.js"
    os_shim.write_text(
        'module.exports = { homedir: () => "C:/Users/Researcher", platform: () => "win32", tmpdir: () => "/tmp" };\n',
        encoding="utf-8",
    )

    empty_shim = build_dir / "shim_empty.js"
    empty_shim.write_text("module.exports = {};\n", encoding="utf-8")

    node_modules = (PLUGIN_DIR / "node_modules").as_posix()
    entry_posix = ENTRY_PATH.as_posix()
    shim_posix = SHIM_PATH.as_posix()
    out_posix = bundle_js.as_posix()
    path_p = path_shim.as_posix()
    fs_p = fs_shim.as_posix()
    os_p = os_shim.as_posix()
    empty_p = empty_shim.as_posix()

    builder_cjs.write_text(
        f"""
const esbuild = require("{node_modules}/esbuild");

const browserShims = {{
  name: "pf-browser-shims",
  setup(build) {{
    build.onResolve({{ filter: /^obsidian$/ }}, () => ({{ path: "{shim_posix}" }}));
    build.onResolve({{ filter: /^(node:)?path$/ }}, () => ({{ path: "{path_p}" }}));
    build.onResolve({{ filter: /^(node:)?fs$/ }}, () => ({{ path: "{fs_p}" }}));
    build.onResolve({{ filter: /^(node:)?os$/ }}, () => ({{ path: "{os_p}" }}));
    build.onResolve({{ filter: /^(node:)?(https|child_process)$/ }}, () => ({{ path: "{empty_p}" }}));
  }},
}};

esbuild.build({{
  entryPoints: ["{entry_posix}"],
  bundle: true,
  platform: "browser",
  target: ["chrome120"],
  outfile: "{out_posix}",
  nodePaths: ["{node_modules}"],
  plugins: [browserShims],
  define: {{
    "process.env.NODE_ENV": '"production"',
    "process.platform": '"win32"',
  }},
}}).catch((e) => {{
  console.error(e);
  process.exit(1);
}});
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        ["node", str(builder_cjs)],
        cwd=str(PLUGIN_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"esbuild showcase bundle failed:\n{proc.stderr}\n{proc.stdout}")
    return bundle_js


def _write_host_html(build_dir: Path, bundle_js: Path) -> Path:
    html_path = build_dir / "index.html"
    styles_uri = STYLES_CSS.as_uri()
    bundle_uri = bundle_js.as_uri()
    html_path.write_text(
        f"""<!doctype html>
<html class="theme-light" lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>PaperForge Obsidian UI & Base Design Showcase</title>
<link rel="stylesheet" href="{styles_uri}" />
<style>
  :root {{
    --background-primary: #ffffff;
    --background-primary-alt: #f5f6f8;
    --background-secondary: #f5f6f8;
    --background-secondary-alt: #ededf0;
    --background-modifier-border: #e5e7ec;
    --background-modifier-border-hover: #cfd4de;
    --background-modifier-hover: rgba(20, 21, 26, 0.05);
    --text-normal: #14151a;
    --text-muted: #525766;
    --text-faint: #848b9c;
    --interactive-normal: #f5f6f8;
    --interactive-hover: #ededf0;
    --interactive-accent: #6c5ce7;
    --interactive-accent-hover: #5848d6;
    --text-on-accent: #ffffff;
    --text-success: #2f7a4f;
    --text-warning: #7a6233;
    --text-error: #c4383b;
    --color-green: #2f7a4f;
    --color-red: #c4383b;
    --color-orange: #7a6233;
    --color-purple: #6c5ce7;
    --color-blue: #3b6fd8;
    --font-interface: "Microsoft YaHei UI", "PingFang SC", "Segoe UI", Inter, system-ui, sans-serif;
    --font-monospace-theme: "Cascadia Code", Consolas, ui-monospace, monospace;
    --font-ui-large: 18px;
    --font-ui-medium: 15px;
    --font-ui-small: 13px;
    --font-ui-smaller: 11.5px;
    --font-ui-smallest: 10.5px;
    --font-semibold: 600;
    --radius-s: 6px;
    --radius-m: 10px;
    --radius-l: 12px;
    --input-radius: 6px;
    --button-radius: 6px;
    --modal-radius: 12px;
    --size-4-1: 4px;
    --size-4-2: 8px;
    --size-4-3: 12px;
    --size-4-4: 16px;
    --shadow-s: 0 8px 24px rgba(28, 27, 24, 0.08);
  }}
  .theme-dark {{
    --background-primary: #1e1d1a;
    --background-primary-alt: #171614;
    --background-secondary: #1e1d1a;
    --background-secondary-alt: #242320;
    --background-modifier-border: #37352f;
    --background-modifier-border-hover: #4a473f;
    --background-modifier-hover: #2b2925;
    --text-normal: #f2efe9;
    --text-muted: #a9a49a;
    --text-faint: #78736a;
    --interactive-normal: #242320;
    --interactive-hover: #2b2925;
    --interactive-accent: #a996ff;
    --interactive-accent-hover: #bcabff;
    --text-on-accent: #1b1533;
    --shadow-s: 0 10px 28px rgba(0, 0, 0, 0.45);
    color-scheme: dark;
    color: #f2efe9;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 24px;
    background: #efede8;
    color: var(--text-normal);
    font-family: var(--font-interface);
    font-size: var(--font-ui-small);
    line-height: 1.5;
  }}
  :where(button) {{
    font-family: inherit;
    font-size: 12px;
    padding: 5px 10px;
    border-radius: var(--radius-s);
    border: 1px solid var(--background-modifier-border);
    background: var(--interactive-normal);
    color: var(--text-normal);
    cursor: pointer;
  }}
  :where(button.mod-cta) {{
    background: var(--interactive-accent);
    border-color: var(--interactive-accent);
    color: var(--text-on-accent);
  }}
  :where(button.mod-warning) {{
    background: #cf222e;
    border-color: #cf222e;
    color: #fff;
  }}
  :where(input[type="text"], input[type="password"], input[type="number"], select, textarea) {{
    font-family: inherit;
    font-size: 12px;
    padding: 5px 8px;
    border: 1px solid var(--background-modifier-border);
    border-radius: var(--radius-s);
    background: var(--background-primary);
    color: var(--text-normal);
  }}
  .setting-item {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 10px 0;
    border-top: 1px solid var(--background-modifier-border);
  }}
  .setting-item-heading {{ font-weight: 600; border-top: none; padding-top: 4px; }}
  .setting-item-info {{ flex: 1; }}
  .setting-item-name {{ font-weight: 500; font-size: 13px; }}
  .setting-item-description {{ font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }}
  .setting-item-control {{ display: flex; align-items: center; gap: 8px; }}
  .checkbox-container {{
    width: 36px; height: 20px; border-radius: 10px;
    background: #cbd5e1; position: relative; transition: 0.15s;
  }}
  .checkbox-container.is-enabled {{ background: var(--interactive-accent); }}
  .checkbox-container::after {{
    content: ""; position: absolute; width: 16px; height: 16px; border-radius: 50%;
    background: #fff; top: 2px; left: 2px; transition: 0.15s;
  }}
  .checkbox-container.is-enabled::after {{ left: 18px; }}

  /* Scene framing (AsterLab calm paper editorial) */
  .pf-doc-scene {{
    margin: 0 0 36px 0;
    background: #f7f6f3;
    border: 1px solid #d6d0c5;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(28, 27, 24, 0.08);
  }}
  .pf-doc-scene-banner {{
    padding: 11px 16px;
    background: #1e1d1a;
    border-bottom: 1px solid #37352f;
    color: #f2efe9;
  }}
  .pf-doc-scene-title {{ font-weight: 600; font-size: 14px; color: #f2efe9; }}
  .pf-doc-scene-sub {{ font-size: 11.5px; color: #a9a49a; margin-top: 2px; }}
  .pf-doc-scene-body {{ padding: 14px; background: #f7f6f3; }}

  /* Obsidian Workspace Chrome */
  .pf-ob-window {{
    background: var(--pf-surface, var(--background-primary));
    border: 1px solid var(--pf-border, #e7e3db);
    border-radius: 10px;
    overflow: hidden;
  }}
  .pf-ob-titlebar {{
    height: 30px; padding: 0 12px;
    background: var(--pf-rail, #f1efea);
    border-bottom: 1px solid var(--pf-border, #e7e3db);
    display: flex; align-items: center; gap: 12px;
    font-size: 11.5px; color: var(--pf-text-muted, #5f5a52); font-weight: 500;
  }}
  .pf-ob-titlebar-dots {{ display: flex; gap: 6px; }}
  .pf-ob-titlebar-dots .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
  .pf-ob-titlebar-dots .red {{ background: #ef4444; }}
  .pf-ob-titlebar-dots .yellow {{ background: #f59e0b; }}
  .pf-ob-titlebar-dots .green {{ background: #22c55e; }}
  .pf-ob-workbench {{ display: flex; align-items: stretch; }}
  .pf-ob-ribbon {{
    width: 40px; flex-shrink: 0;
    background: var(--pf-rail, #f1efea);
    border-right: 1px solid var(--pf-border, var(--background-modifier-border));
    padding: 10px 0; display: flex; flex-direction: column; align-items: center; gap: 10px;
  }}
  .pf-ob-ribbon-icon {{
    width: 28px; height: 28px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    color: var(--pf-text-muted, #5f5a52);
  }}
  .pf-ob-ribbon-icon.is-active {{
    background: var(--pf-accent-soft, rgba(91, 69, 201, 0.12));
    color: var(--pf-accent, var(--interactive-accent));
  }}
  .pf-ob-main-leaf {{
    flex: 1; min-width: 0;
    background: var(--pf-surface, var(--background-primary));
  }}
  .pf-ob-right-sidebar {{
    width: 370px; flex-shrink: 0;
    background: var(--pf-canvas, var(--background-secondary));
    border-left: 1px solid var(--pf-border, var(--background-modifier-border));
  }}
  .pf-doc-grid-pdf-bounds {{ display: grid; grid-template-columns: minmax(0, 2.35fr) minmax(0, 1fr); gap: 14px; align-items: start; }}
  .pf-doc-modal-host .modal {{
    position: static; width: 100% !important; max-width: none !important; box-shadow: none;
    border: 1px solid var(--pf-border, var(--background-modifier-border)); border-radius: 10px;
  }}
  .pf-ob-tab-header {{
    height: 34px; background: var(--pf-rail, #f1efea);
    border-bottom: 1px solid var(--pf-border, var(--background-modifier-border));
    display: flex; align-items: flex-end; padding: 0 10px;
  }}
  .pf-ob-tab {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 12px;
    background: var(--pf-surface, var(--background-primary));
    color: var(--pf-text, var(--text-normal));
    border: 1px solid var(--pf-border, var(--background-modifier-border));
    border-bottom: none; border-radius: 6px 6px 0 0;
    font-size: 12px; font-weight: 500;
  }}
  .pf-ob-tab-icon {{ display: inline-flex; color: var(--pf-accent, var(--interactive-accent)); }}
  .pf-ob-leaf-content {{ padding: 12px 14px; }}
  .pf-ob-sidebar-content {{ padding: 8px; }}

  /* Authentic Obsidian 1.12 Bases Toolbar Simulation */
  .pf-ob-bases-container {{
    border: 1px solid var(--pf-border, var(--background-modifier-border));
    border-radius: 10px; overflow: hidden;
    background: var(--pf-surface, var(--background-primary));
  }}
  .pf-ob-bases-toolbar {{
    display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 6px 8px;
    min-height: 38px; padding: 5px 12px;
    background: var(--pf-elevated, #faf9f7);
    border-bottom: 1px solid var(--pf-border, var(--background-modifier-border));
  }}
  .pf-ob-bases-views, .pf-ob-bases-controls {{
    display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
  }}
  .pf-ob-bases-view-dropdown {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px; border-radius: 6px; font-size: 12.5px; font-weight: 600;
    color: var(--pf-text, var(--text-normal));
    background: var(--pf-surface, var(--background-primary));
    border: 1px solid var(--pf-border, var(--background-modifier-border));
  }}
  .pf-ob-bases-chip {{
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 8px; border-radius: 6px; font-size: 11.5px;
    background: transparent; border: 1px solid transparent;
    color: var(--pf-text-muted, var(--text-muted));
  }}
  .pf-ob-bases-chip.is-primary-btn {{
    background: var(--pf-accent, #5b45c9);
    color: var(--pf-accent-text, #ffffff);
    font-weight: 500;
  }}
  .pf-ob-chip-icon {{ display: inline-flex; }}
  .pf-ob-bases-view-mount {{ padding: 10px 12px; }}

  /* AsterLab Dark preview wrapper */
  .theme-dark .pf-doc-dark-frame {{
    background: #171614;
    color: #f2efe9;
    border-radius: 10px;
    padding: 10px;
    border: 1px solid #37352f;
  }}
  .theme-dark .pf-doc-dark-frame .pf-doc-panel-label {{
    color: #a996ff;
    border-bottom-color: #37352f;
  }}

  /* Grid helpers */
  .pf-doc-grid-2 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: start; }}
  .pf-doc-grid-3 {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr); gap: 12px; align-items: start; }}
  .pf-doc-panel {{
    min-width: 0;
    overflow: hidden;
    background: var(--pf-surface, var(--background-primary));
    border: 1px solid var(--pf-border, var(--background-modifier-border));
    border-radius: 10px;
    padding: 10px 12px;
  }}
  .pf-doc-panel-label {{
    font-size: 12px; font-weight: 600; color: var(--pf-accent, var(--interactive-accent));
    padding-bottom: 6px; margin-bottom: 8px;
    border-bottom: 1px solid var(--pf-border, var(--background-modifier-border));
  }}
  .pf-doc-subbox {{
    margin-bottom: 10px; border: 1px solid var(--pf-border, var(--background-modifier-border));
    border-radius: 6px; padding: 6px; background: var(--pf-canvas, var(--background-primary-alt));
  }}
  .pf-doc-sidebar-shell .paperforge-status-panel {{ max-height: none; overflow: visible; }}
  .pf-doc-maint-sample {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--pf-border, var(--background-modifier-border)); }}

  /* PDF viewer showcase sizing — overlay colors come cleanly from plugin styles.css */
  .pf-pdf-body {{ max-height: 760px; overflow: hidden; }}
  .pf-pdf-scroll {{ overflow: hidden; }}
  .pf-pdf-page {{ position: relative; margin: 0 auto 12px auto; box-shadow: var(--shadow-s); }}

  /* Modal showcase embedding */
  .pf-doc-modal-host .modal-container {{
    position: static; width: 100%; height: auto; background: transparent;
  }}
  .pf-doc-modal-host .modal {{
    position: static; width: 100%; max-width: none; box-shadow: none;
    border: 1px solid var(--background-modifier-border); border-radius: 6px;
  }}
  .pf-doc-modal-host .modal-content {{ padding: 10px; max-height: 440px; overflow: hidden; }}
</style>
</head>
<body>
<script src="{bundle_uri}"></script>
</body>
</html>
""",
        encoding="utf-8",
    )
    return html_path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    browser_exe = _find_browser_executable()
    with tempfile.TemporaryDirectory(prefix="pf-ui-docs-") as tmp:
        build_dir = Path(tmp)
        bundle_js = _bundle_showcase(build_dir)
        html_path = _write_host_html(build_dir, bundle_js)

        with sync_playwright() as pw:
            launch_kwargs: dict[str, object] = {"headless": True}
            if browser_exe:
                launch_kwargs["executable_path"] = browser_exe
            browser = pw.chromium.launch(**launch_kwargs)
            try:
                page = browser.new_page(
                    viewport={"width": 1440, "height": 2200},
                    device_scale_factor=2,
                )
                page.set_default_timeout(15000)
                errors: list[str] = []
                logs: list[str] = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
                page.goto(html_path.as_uri(), wait_until="domcontentloaded", timeout=15000)
                try:
                    page.wait_for_function(
                        "() => window.__PF_SHOWCASE_READY__ === true || Boolean(window.__PF_SHOWCASE_ERROR__)",
                        timeout=12000,
                    )
                except Exception as exc:
                    stage = page.evaluate("() => window.__PF_STAGE__ || 'init'")
                    raise RuntimeError(
                        f"Timed out at stage={stage!r}; errors={errors}; logs={logs[-15:]}"
                    ) from exc
                showcase_err = page.evaluate("() => window.__PF_SHOWCASE_ERROR__ || ''")
                if showcase_err:
                    raise RuntimeError(f"Showcase JS error:\n{showcase_err}")
                if errors:
                    raise RuntimeError("Uncaught page errors:\n" + "\n".join(errors))

                dom_audit = page.evaluate(
                    """() => {
                      const text = document.body.innerText || "";
                      const hasLegacyPrefix = text.includes("[!!]") || text.includes("[OK]");
                      const emptyStrips = Array.from(
                        document.querySelectorAll(".pf-global-activity-strip")
                      ).filter((el) => el.children.length === 0);
                      const zeroIdleOk = emptyStrips.every(
                        (el) => el.getBoundingClientRect().height === 0
                      );
                      const narrowPdf = Array.from(
                        document.querySelectorAll(".pf-pdf-view.is-narrow .pf-pdf-toolbar")
                      );
                      const narrowToolbarOk = narrowPdf.every(
                        (el) => el.scrollWidth <= el.clientWidth + 2
                      );
                      return { hasLegacyPrefix, zeroIdleOk, narrowToolbarOk };
                    }"""
                )
                if dom_audit.get("hasLegacyPrefix"):
                    raise RuntimeError("Rendered UI leaked [!!] or [OK] log prefixes")
                if not dom_audit.get("zeroIdleOk", False):
                    raise RuntimeError("Empty .pf-global-activity-strip did not collapse to 0px")
                if not dom_audit.get("narrowToolbarOk", False):
                    raise RuntimeError("Narrow .pf-pdf-view.is-narrow toolbar overflowed horizontally")

                for slug in SCENES:
                    loc = page.locator(f"#scene-{slug}")
                    loc.wait_for(state="visible", timeout=10000)
                    out_png = OUT_DIR / f"v4-{slug}.png"
                    loc.screenshot(path=str(out_png))
                    print(f"rendered: {out_png.relative_to(REPO_ROOT).as_posix()} ({out_png.stat().st_size} bytes)")
            finally:
                browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
