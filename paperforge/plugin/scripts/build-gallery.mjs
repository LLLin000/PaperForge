import esbuild from "esbuild";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pluginRoot = path.resolve(__dirname, "..");
const outDir = path.join(pluginRoot, "prototypes");
const outHtml = path.join(outDir, "ui-gallery.html");
const stylesPath = path.join(pluginRoot, "styles.css");

const nodeShimPath = path.join(pluginRoot, "src/uikit/gallery-node-shim.ts");
const obsidianShimPath = path.join(
  pluginRoot,
  "src/uikit/gallery-obsidian-shim.ts"
);

const nodeBuiltins = new Set([
  "fs",
  "path",
  "os",
  "https",
  "http",
  "child_process",
  "crypto",
  "stream",
  "url",
  "util",
  "events",
  "buffer",
]);

const shimPlugin = {
  name: "pf-gallery-browser-shims",
  setup(build) {
    build.onResolve({ filter: /^obsidian$/ }, () => ({
      path: obsidianShimPath,
    }));
    build.onResolve({ filter: /^(node:)?[a-z_]+$/ }, (args) => {
      const clean = args.path.replace(/^node:/, "");
      if (nodeBuiltins.has(clean)) {
        return { path: nodeShimPath };
      }
      return undefined;
    });
  },
};

const result = await esbuild.build({
  entryPoints: [path.join(pluginRoot, "src/uikit/gallery-standalone.ts")],
  bundle: true,
  write: false,
  format: "iife",
  target: "es2022",
  minify: true,
  plugins: [shimPlugin],
});

const jsCode = result.outputFiles[0].text;
const cssCode = fs.readFileSync(stylesPath, "utf8");

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>PaperForge UIKit · 设计系统与全组件画廊</title>
<style>
:root {
  --font-interface: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-text: var(--font-interface);
  --font-monospace: ui-monospace, SFMono-Regular, "JetBrains Mono", Consolas, monospace;
  --font-monospace-theme: var(--font-monospace);
  --font-ui-smaller: 11.5px;
  --font-ui-small: 12.5px;
  --font-ui-medium: 14px;
  --font-ui-large: 16px;
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  --line-height-tight: 1.35;
  --size-2-1: 2px;
  --size-2-2: 4px;
  --size-2-3: 6px;
  --size-4-1: 4px;
  --size-4-2: 8px;
  --size-4-3: 12px;
  --size-4-4: 16px;
  --size-4-5: 20px;
  --size-4-6: 24px;
  --background-primary: #ffffff;
  --background-secondary: #f6f7f9;
  --background-primary-alt: #f1f3f5;
  --background-secondary-alt: #eef0f4;
  --background-modifier-hover: rgba(0, 0, 0, 0.045);
  --background-modifier-border: rgba(0, 0, 0, 0.10);
  --background-modifier-border-hover: rgba(0, 0, 0, 0.18);
  --background-modifier-form-field: #ffffff;
  --background-modifier-error: rgba(196, 56, 59, 0.12);
  --interactive-normal: #ffffff;
  --interactive-hover: #f3f4f6;
  --text-normal: #1f2328;
  --text-muted: #5f6368;
  --text-faint: #8c959f;
  --text-accent: #5b45c9;
  --text-on-accent: #ffffff;
  --text-success: #2f7a4f;
  --text-warning: #a16207;
  --text-error: #c4383b;
  --interactive-accent: #5b45c9;
  --interactive-accent-hover: #4936a8;
  --color-green: #2f7a4f;
  --color-red: #c4383b;
  --color-orange: #c47f17;
  --color-yellow: #ca8a04;
  --color-yellow-rgb: 202, 138, 4;
  --color-red-rgb: 196, 56, 59;
  --radius-s: 6px;
  --radius-m: 10px;
  --radius-l: 12px;
  --input-radius: 6px;
  --button-radius: 6px;
  --modal-radius: 12px;
  --setting-items-background: #ffffff;
  --setting-items-radius: 10px;
  --setting-group-heading-size: 13px;
  --setting-group-heading-weight: 600;
  --setting-group-heading-color: #1f2328;
}
body {
  margin: 0;
  padding: 0;
  font-family: var(--font-interface);
  background: var(--background-primary);
  color: var(--text-normal);
  -webkit-font-smoothing: antialiased;
}
body.theme-dark {
  --background-primary: #141518;
  --background-secondary: #1b1d21;
  --background-primary-alt: #22252b;
  --background-secondary-alt: #252930;
  --background-modifier-hover: rgba(255, 255, 255, 0.06);
  --background-modifier-border: rgba(255, 255, 255, 0.12);
  --background-modifier-border-hover: rgba(255, 255, 255, 0.22);
  --background-modifier-form-field: #1b1d21;
  --background-modifier-error: rgba(248, 113, 113, 0.14);
  --interactive-normal: #22252b;
  --interactive-hover: #2c3038;
  --text-normal: #e8e9ec;
  --text-muted: #a1a5ad;
  --text-faint: #6c727d;
  --text-accent: #a596ff;
  --text-on-accent: #141518;
  --text-success: #4ade80;
  --text-warning: #fbbf24;
  --text-error: #f87171;
  --interactive-accent: #a596ff;
  --interactive-accent-hover: #b8acff;
  --color-green: #4ade80;
  --color-red: #f87171;
  --color-orange: #fbbf24;
  --color-yellow: #facc15;
  --color-yellow-rgb: 250, 204, 21;
  --color-red-rgb: 248, 113, 113;
  --setting-items-background: #1b1d21;
  --setting-group-heading-color: #e8e9ec;
  background: #141518;
  color: #e8e9ec;
}
${cssCode}
</style>
</head>
<body data-pf-standalone="1" class="theme-light pf-theme-obsidian pf-density-default">
<div id="pf-gallery-app"></div>
<script>${jsCode}</script>
</body>
</html>`;

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(outHtml, html, "utf8");
const kb = (Buffer.byteLength(html, "utf8") / 1024).toFixed(1);
console.log(
  `Built standalone UI Gallery: ${path.relative(pluginRoot, outHtml)} (${kb} KB)`
);
