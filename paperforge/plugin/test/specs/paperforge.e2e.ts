/**
 * Real-task end-to-end coverage for the PaperForge frontend.
 *
 * Runs against a SANDBOXED real Obsidian with the repo plugin installed from
 * "." and a disposable vault built by `test/fixtures/build_e2e_vault.py`
 * (real BBT export + real OCR fixture → real `paperforge sync` → real index,
 * workspace, OCR lineage, version manifest, legacy backup).
 *
 * Exercised through the UI:
 *  1. plugin load + client → real Python backend
 *  2. Sync Library button → real mutation → fresh read model in the panel
 *  3. Base/collection mode → search box → real FTS results
 *  4. OCR Workspace view → real lineage rows
 *  5. paper mode → Version History modal → restore → durable file change
 *  6. action execution through the client (memory.build)
 *  7. client trace records the real boundary traffic
 *  8. candidate binding: the loaded bundle is the built artifact, and the
 *     sandbox vault is a copy that cannot write back into the fixture
 *
 * NOTE: `executeObsidian` serializes its callback into the Obsidian window,
 * so callbacks must be self-contained and return serializable data.
 */
import { browser } from "@wdio/globals";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import * as path from "node:path";

const PAPER_KEY = "TSTONE001";
const NOTE_PATH =
  "Resources/Literature/骨科/TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair/TSTONE001.md";
const BASE_PATH = "Bases/骨科.base";

/**
 * The suite must run from the plugin directory: every artifact hash below is
 * resolved from it, so a wrong cwd would silently bind a different bundle.
 * Fail loudly instead of reporting a green run against the wrong artifact.
 */
function resolvePluginDir(): string {
  const dir = process.cwd();
  const manifestPath = path.join(dir, "manifest.json");
  if (!existsSync(manifestPath)) {
    throw new Error(
      `run the e2e suite from the plugin directory — ${dir} has no manifest.json`
    );
  }
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as {
    id?: string;
  };
  if (manifest.id !== "paperforge") {
    throw new Error(
      `unexpected plugin manifest in ${dir}: id=${String(manifest.id)}`
    );
  }
  return dir;
}

const PLUGIN_DIR = resolvePluginDir();
const FIXTURE_VAULT = path.resolve(PLUGIN_DIR, "test", "vaults", "e2e");
const EVIDENCE_DIR = path.resolve(PLUGIN_DIR, "test", "evidence");

/** Version of the artifact under test (plugin manifest is version-synced). */
const CANDIDATE_VERSION = (
  JSON.parse(readFileSync(path.join(PLUGIN_DIR, "manifest.json"), "utf8")) as {
    version: string;
  }
).version;

/** sha256 of a file's bytes — artifact identity, not its path. */
function sha256(file: string): string {
  return createHash("sha256").update(readFileSync(file)).digest("hex");
}

const BYSTANDER_NOTE =
  "Resources/Literature/骨科/TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair/TSTONE001.md";
const NEW_PAPER_KEY = "TSTONE002";
const NEW_PAPER_NOTE =
  "Resources/Literature/骨科/TSTONE002 - Second Paper/TSTONE002.md";
const EXPORT_REL = "System/PaperForge/exports/骨科.json";
const INDEX_REL = "System/PaperForge/indexes/formal-library.json";

/** One frontmatter field of a sandbox note, trimmed ("" when absent). */
function readFrontmatterFlag(base: string, rel: string, field: string): string {
  const match = readNote(base, rel).match(
    new RegExp(`^${field}:\\s*(.+)$`, "m")
  );
  return match ? match[1].trim() : "";
}

function readNote(base: string, rel: string): string {
  return readFileSync(path.join(base, rel), "utf8");
}

function newNoteExists(base: string): boolean {
  return existsSync(path.join(base, NEW_PAPER_NOTE));
}

function readIndex(base: string): { paper_count: number; keys: string[] } {
  const raw = JSON.parse(readFileSync(path.join(base, INDEX_REL), "utf8")) as {
    paper_count?: number;
    items?: { zotero_key?: string }[];
  };
  const items = raw.items ?? [];
  return {
    paper_count: raw.paper_count ?? items.length,
    keys: items.map((entry) => String(entry.zotero_key ?? "")),
  };
}

/**
 * Append one library item to the sandbox export, so Sync has exactly one
 * change to reconcile and the assertion can be a real data diff.
 */
function addExportItem(
  base: string,
  item: { key: string; title: string; doi: string }
): void {
  const file = path.join(base, EXPORT_REL);
  const doc = JSON.parse(readFileSync(file, "utf8")) as {
    items: Record<string, unknown>[];
    collections: Record<string, { items: string[] }>;
  };
  const template: Record<string, unknown> = { ...doc.items[0] };
  Object.assign(template, {
    key: item.key,
    itemKey: item.key,
    title: item.title,
    DOI: item.doi,
    attachments: [
      {
        path: `storage:${item.key}/${item.key}.pdf`,
        contentType: "application/pdf",
      },
    ],
  });
  doc.items.push(template);
  for (const collection of Object.values(doc.collections)) {
    collection.items.push(item.key);
  }
  writeFileSync(file, JSON.stringify(doc));
}

/** Newest mtime under `src/` — the built bundle must be at least this fresh. */
function newestSourceMtime(dir: string): number {
  let newest = 0;
  const walk = (current: string): void => {
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith(".ts"))
        newest = Math.max(newest, statSync(full).mtimeMs);
    }
  };
  walk(path.join(dir, "src"));
  return newest;
}

/** True when the worktree carries uncommitted changes (plan §4.3). */
function worktreeDirty(): boolean {
  return (
    execFileSync("git", ["status", "--porcelain"], { cwd: PLUGIN_DIR })
      .toString()
      .trim().length > 0
  );
}

/**
 * Live backend processes still referencing this sandbox.
 *
 * Matched on the sandbox directory *name* (a unique temp id) so no path
 * quoting is involved. A backend that outlives its request is invisible to
 * every other assertion in this file: the suite would report clean while a
 * `paperforge` child keeps running against a deleted vault.
 */
function sandboxBackendProcesses(base: string): number {
  const marker = path.basename(base);
  const command =
    process.platform === "win32"
      ? `powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*${marker}*' -and $_.Name -like '*python*' }).Count"`
      : `pgrep -fa '${marker}' | grep -c python || true`;
  const output = execFileSync(command, { shell: true }).toString().trim();
  return Number(output.split(/\s+/).pop() ?? "0") || 0;
}

async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

/**
 * Acceptance evidence record (plan §4.3). Runs are appended, never replaced:
 * a first failure must stay visible after a later green re-run.
 */
function appendEvidence(name: string, payload: Record<string, unknown>): void {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const file = path.join(EVIDENCE_DIR, name);
  const parsed: unknown = existsSync(file)
    ? JSON.parse(readFileSync(file, "utf8"))
    : [];
  // Older runs used a single-object record; carry it over instead of dropping it.
  const runs = Array.isArray(parsed) ? parsed : [parsed];
  runs.push(payload);
  writeFileSync(file, JSON.stringify(runs, null, 2));
}

/**
 * Click an element identified by its stable test id.
 *
 * The dashboard panel is taller than the window, and a row that lands in the
 * bottom band is covered by Obsidian's status bar — WebDriver then refuses the
 * click ("element click intercepted"). `scrollIntoView` does not help because
 * the element's nearest *scrollable* ancestor is the panel, not the document;
 * this scrolls that ancestor instead, which is what a user does with the wheel.
 */
async function clickTestId(testid: string): Promise<void> {
  const element = await browser.$(`[data-pf-testid='${testid}']`);
  await element.waitForExist({ timeout: 60000 });
  await browser.execute((id: string) => {
    const el = document.querySelector(
      `[data-pf-testid='${id}']`
    ) as HTMLElement | null;
    if (!el) return;
    let scroller: HTMLElement | null = el.parentElement;
    while (scroller && scroller !== document.body) {
      const style = getComputedStyle(scroller);
      if (/(auto|scroll)/.test(style.overflowY)) {
        const row = el.getBoundingClientRect();
        const box = scroller.getBoundingClientRect();
        scroller.scrollTop +=
          row.top - box.top - box.height / 2 + row.height / 2;
        return;
      }
      scroller = scroller.parentElement;
    }
  }, testid);
  await element.click();
}

async function openVaultFile(filePath: string): Promise<void> {
  // New tab + explicit activation: a programmatic openFile() alone does not
  // fire active-leaf-change, so the panel would never re-resolve its mode.
  await browser.executeObsidian(async ({ app }, filePath) => {
    const file = app.vault.getAbstractFileByPath(filePath);
    if (!file) throw new Error(`file not found: ${filePath}`);
    if (!("extension" in file)) throw new Error(`not a file: ${filePath}`);
    const leaf = app.workspace.getLeaf("tab");
    await leaf.openFile(file);
    app.workspace.setActiveLeaf(leaf, { focus: true });
  }, filePath);
}

/** Obsidian modals (release notes, confirmations) block clicks — close them. */
async function dismissModals(): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const open = await browser.$$(".modal-bg");
    if (open.length === 0) return;
    await browser.keys("Escape");
    await browser.pause(200);
  }
}

async function openPanel(): Promise<void> {
  await browser.executeObsidianCommand("paperforge:paperforge-status-panel");
  await (
    await browser.$(".paperforge-status-panel")
  ).waitForExist({
    timeout: 60000,
  });
}

async function traceContains(needle: string): Promise<boolean> {
  return await browser.executeObsidian(async ({ app }, text) => {
    const plugin = app.plugins.plugins["paperforge"];
    if (!plugin || typeof plugin.getDebugTrace !== "function") return false;
    return plugin.getDebugTrace().includes(text);
  }, needle);
}

async function operationActive(): Promise<boolean> {
  return await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"];
    if (!plugin || typeof plugin.getClient !== "function") return true;
    return plugin.getClient().isOperationActive();
  });
}

/**
 * Wait until no operation is in flight. Fails with a readable reason well
 * before mocha's suite timeout, and leaves first-failure evidence — a bare
 * "Timeout" tells the next reader nothing (plan §4.3).
 */
async function waitForIdle(caseId: string, step: string): Promise<void> {
  try {
    await browser.waitUntil(async () => !(await operationActive()), {
      timeout: 90000,
      timeoutMsg: "an operation was still active (startup sync never settled)",
    });
  } catch (error) {
    let traceTail = "(unavailable)";
    try {
      traceTail = await browser.executeObsidian(async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"];
        if (!plugin || typeof plugin.getDebugTrace !== "function")
          return "(no trace)";
        return plugin
          .getDebugTrace()
          .split("\n")
          .filter(Boolean)
          .slice(-5)
          .join(" | ");
      });
    } catch {
      traceTail = "(trace unreadable)";
    }
    appendEvidence("b02-sync-diff.json", {
      case_id: caseId,
      step,
      status: "FAILED",
      detail: String(error),
      trace_tail: traceTail,
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      recorded_at: new Date().toISOString(),
    });
    throw error;
  }
}

describe("PaperForge real-task e2e", function () {
  beforeEach(async function () {
    // Full isolation: every test starts from a fresh sandbox copy.
    await browser.reloadObsidian({ vault: "./test/vaults/e2e" });
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin) throw new Error("paperforge plugin not loaded");
      const settings = plugin.settings as {
        language?: string;
        last_seen_version?: string;
      };
      settings.language = "en";
      settings.last_seen_version = plugin.manifest.version;
      await plugin.saveSettings();
    });
    await dismissModals();
  });

  it("loads the plugin and reaches the real Python backend", async function () {
    const info = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const client = plugin.getClient();
      const probe = await client.probe("installation");
      return {
        id: plugin.manifest.id,
        plugin_version: plugin.manifest.version,
        backend: await client.backendVersion(),
        capability_state: probe.capability_state,
      };
    });
    expect(info.id).toBe("paperforge");
    // Candidate binding: plugin and backend must be the artifact under test,
    // never a stale install or an older editable Python.
    expect(info.plugin_version).toBe(CANDIDATE_VERSION);
    expect(info.backend).toBe(CANDIDATE_VERSION);
    expect(info.capability_state).toBe("ready");
  });

  it("binds the loaded bundle to the built artifact and isolates the sandbox", async function () {
    const bundlePath = path.join(PLUGIN_DIR, "main.js");
    const builtBundle = sha256(bundlePath);
    const builtManifestSha = sha256(path.join(PLUGIN_DIR, "manifest.json"));

    // Teeth for "build before WDIO": hash equality alone would also hold when
    // both the installed copy and the working tree are a stale bundle, so the
    // artifact must additionally be at least as fresh as the newest source.
    expect(statSync(bundlePath).mtimeMs).toBeGreaterThanOrEqual(
      newestSourceMtime(PLUGIN_DIR)
    );

    const base = await sandboxBasePath();
    expect(base.length).toBeGreaterThan(0);
    // reloadObsidian copies the vault: the running instance must never be the
    // fixture source directory.
    expect(path.resolve(base)).not.toBe(FIXTURE_VAULT);

    const sandboxPlugin = path.join(base, ".obsidian", "plugins", "paperforge");
    expect(sha256(path.join(sandboxPlugin, "main.js"))).toBe(builtBundle);
    expect(sha256(path.join(sandboxPlugin, "manifest.json"))).toBe(
      builtManifestSha
    );

    // Isolation: a write inside the sandbox never reaches the fixture source.
    const sentinel = `.pf-e2e-sentinel-${Date.now()}`;
    writeFileSync(path.join(base, sentinel), "sentinel");
    expect(existsSync(path.join(FIXTURE_VAULT, sentinel))).toBe(false);
    rmSync(path.join(base, sentinel), { force: true });

    const backend = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return await plugin.getClient().backendVersion();
    });

    appendEvidence("w01-candidate-binding.json", {
      case_id: "X11",
      variant: "bundle-binding+isolation",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      artifact_sha256: {
        "main.js": builtBundle,
        "manifest.json": builtManifestSha,
      },
      plugin_version: CANDIDATE_VERSION,
      backend_version: backend,
      obsidian_version: String(await browser.getObsidianVersion()),
      sandbox_base: base,
      fixture_vault: FIXTURE_VAULT,
      recorded_at: new Date().toISOString(),
    });
  });

  it("syncs exactly the changed export entry and preserves the bystander paper", async function () {
    // Attribution: an unrelated convergence tick would produce the same data
    // effect, so this test requires the background cadence to be far outside
    // its own window (a tick would make "the button did it" unprovable).
    const cadence = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      return plugin.settings.autoSyncIntervalSeconds ?? 120;
    });
    expect(cadence).toBeGreaterThanOrEqual(120);

    await openPanel();

    // Wait out the startup sync so the click below is the only writer left.
    await waitForIdle("B02", "startup-sync-settle");

    const base = await sandboxBasePath();
    const bystanderBefore = sha256(path.join(base, BYSTANDER_NOTE));
    const indexBefore = readIndex(base);
    expect(newNoteExists(base)).toBe(false);

    addExportItem(base, {
      key: "TSTONE002",
      title: "Second Paper",
      doi: "10.1016/j.jse.2024.01.999",
    });

    const syncBtn = await browser.$("[data-pf-testid='sync-library']");
    await expect(syncBtn).toExist();
    await syncBtn.click();

    // Wait on the strongest data effect, never on a trace string: the startup
    // autosync can satisfy a trace assertion without the button doing anything,
    // and the note appears before the index is rebuilt.
    await browser.waitUntil(
      () => {
        try {
          return readIndex(base).paper_count === indexBefore.paper_count + 1;
        } catch {
          return false; // the index is being rewritten
        }
      },
      {
        timeout: 180000,
        timeoutMsg: "clicking Sync never rebuilt the index for the new paper",
      }
    );
    expect(newNoteExists(base)).toBe(true);

    const indexAfter = readIndex(base);
    expect(indexAfter.paper_count).toBe(indexBefore.paper_count + 1);
    expect(indexAfter.keys).toContain("TSTONE002");
    // The bystander paper is untouched: same bytes, same status, same link.
    expect(sha256(path.join(base, BYSTANDER_NOTE))).toBe(bystanderBefore);
    expect(readNote(base, BYSTANDER_NOTE)).toContain('ocr_status: "done"');

    const panelText = (await browser.$(".paperforge-content-area").getText())
      .toLowerCase()
      .replace(/\s+/g, " ");
    expect(panelText).toContain("library snapshot");
    expect(panelText).toMatch(/\d+ papers/);

    appendEvidence("b02-sync-diff.json", {
      case_id: "B02",
      variant: "export-add -> UI Sync",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      added_key: "TSTONE002",
      paper_count_before: indexBefore.paper_count,
      paper_count_after: indexAfter.paper_count,
      bystander_note: BYSTANDER_NOTE,
      bystander_sha256_before: bystanderBefore,
      bystander_sha256_after: sha256(path.join(base, BYSTANDER_NOTE)),
      volatile_allowlist: ["Bases/*.base", "*/paper-meta.json", "indexes/*"],
      observed_at: new Date().toISOString(),
    });
  });

  it("searches through the collection-mode search box", async function () {
    await openPanel();
    await openVaultFile(BASE_PATH);
    const input = await browser.$(".paperforge-search-input");
    await input.waitForExist({ timeout: 60000 });
    await input.setValue("suture");
    await browser.keys("Enter");

    // The search result renders asynchronously; assert on the section text
    // (stable across card/virtual-list implementations).
    const section = await browser.$(".paperforge-search-section");
    await browser.waitUntil(
      async () => (await section.getText()).includes("Suture Anchor"),
      { timeout: 60000, timeoutMsg: "search results never rendered" }
    );
  });

  it("lists OCR papers in the real workspace view", async function () {
    await browser.executeObsidianCommand("paperforge:paperforge-ocr-workspace");
    const viewport = await browser.$(".pf-ocr-ws-viewport");
    await viewport.waitForExist({ timeout: 60000 });
    await browser.waitUntil(
      async () => (await viewport.getText()).includes("Biomechanical"),
      { timeout: 60000, timeoutMsg: "OCR workspace rows never rendered" }
    );
  });

  it("restores a display version through the Version History modal", async function () {
    await openPanel();
    await openVaultFile(NOTE_PATH);
    const versionBtn = await browser.$("[data-pf-testid='version-history']");
    await versionBtn.waitForExist({ timeout: 60000 });
    await versionBtn.click();

    await (await browser.$(".pf-vr-layout")).waitForExist({ timeout: 60000 });
    const labels = await browser.execute(() =>
      Array.from(document.querySelectorAll(".pf-vr-entry-label")).map((el) =>
        (el.textContent ?? "").trim()
      )
    );
    expect(labels).toContain("v1");
    expect(labels).toContain("v2");

    // Restore the oldest version (v1) → confirmation → Python performs the
    // copy AND persists provenance.
    const restoreBtn = await browser.$("[data-pf-testid='version-restore']");
    await restoreBtn.waitForExist({ timeout: 30000 });
    await restoreBtn.click();
    const confirmBtn = await browser.$(
      "[data-pf-testid='version-restore-confirm']"
    );
    await confirmBtn.waitForExist({ timeout: 30000 });
    await confirmBtn.click();

    await browser.waitUntil(
      async () => await traceContains("versions restore"),
      {
        timeout: 60000,
        timeoutMsg: "restore never reached the backend",
      }
    );

    // Durable state: the current render fulltext now holds the v1 body.
    const content = await browser.executeObsidian(async ({ app }, key) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const paths = await plugin.getClient().versionsPaths(key);
      const adapter = app.vault.adapter as unknown as {
        basePath?: string;
        read(path: string): Promise<string>;
      };
      const base = adapter.basePath ?? "";
      const relative = paths.current_path
        .slice(base.length)
        .replace(/^[/\\]+/, "");
      return await adapter.read(relative);
    }, PAPER_KEY);
    expect(content).toContain("first body");
  });

  it("executes an action through the client (memory.build)", async function () {
    const ok = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const result = await plugin.getClient().runAction({
        action_id: "memory.build",
        scope: { kind: "all" },
      });
      return result.ok === true;
    });
    expect(ok).toBe(true);
  });

  it("records the boundary traffic and backend timing in the client trace", async function () {
    // Each test runs in a fresh app, so this test produces its own traffic.
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      await plugin.setDebugTrace(true);
      await plugin.getClient().sync();
      await plugin.getClient().versionsShow("TSTONE001");
    });
    const trace = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getDebugTrace !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return plugin.getDebugTrace();
    });
    expect(trace).toContain("sync --json");
    expect(trace).toContain("versions show");
    expect(trace).toMatch(/timing detail=.*reconcile/);
  });

  it("binds the backend artifact, not only its version", async function () {
    // A version number cannot tell a worktree source from an installed
    // artifact, so a run claiming to test this checkout could be served by a
    // different one. Record which artifact actually answered.
    const health = (await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return await plugin.getClient().runtimeHealth();
    })) as {
      runtime?: {
        interpreter?: string;
        python_version?: string;
        package_path?: string;
        package_version?: string;
      };
    };

    const runtime = health.runtime ?? {};
    expect(runtime.package_version).toBe(CANDIDATE_VERSION);
    expect(String(runtime.package_path ?? "")).toMatch(/paperforge$/);
    expect(String(runtime.interpreter ?? "").length).toBeGreaterThan(0);

    // cwd is <repo>/paperforge/plugin, so the package source is two levels up.
    const sourcePath = path.resolve(PLUGIN_DIR, "..", "..", "paperforge");
    const backendKind =
      path.resolve(String(runtime.package_path)) === sourcePath
        ? "worktree-source"
        : "installed-artifact";

    appendEvidence("w01-backend-artifact.json", {
      case_id: "X11",
      variant: "backend-artifact-binding",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      backend_kind: backendKind,
      package_path: runtime.package_path,
      package_version: runtime.package_version,
      interpreter: runtime.interpreter,
      python_version: runtime.python_version,
      source_path_expected: sourcePath,
      observed_at: new Date().toISOString(),
    });
  });

  it("keeps a durable change across a restart of the same sandbox", async function () {
    const before = await sandboxBasePath();
    await openPanel();

    // Durable mutation through the client, read back from the file rather than
    // the UI. A version restore is used instead of setNoteFlag because
    // `note set-flag` currently resolves a stale flat path and fails for every
    // workspace-layout paper (#230) — that path has its own case (B07).
    const restored = (await browser.executeObsidian(async ({ app }, key) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return await plugin.getClient().versionsRestore(key, "v1");
    }, PAPER_KEY)) as { target_path?: string; provenance_persisted?: boolean };

    const targetPath = String(restored.target_path ?? "");
    expect(targetPath.length).toBeGreaterThan(0);
    expect(readFileSync(targetPath, "utf8")).toContain("first body");

    // Restart with NO vault argument: reboot the current vault, not a fresh
    // copy — otherwise the assertion would "pass" against the fixture.
    await browser.reloadObsidian();
    const after = await sandboxBasePath();
    expect(path.resolve(after)).toBe(path.resolve(before));
    expect(readFileSync(targetPath, "utf8")).toContain("first body");

    appendEvidence("w01-restart-persistence.json", {
      case_id: "X11",
      variant: "same-sandbox-restart-persistence",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      sandbox_base: before,
      sandbox_base_after_restart: after,
      durable_artifact: targetPath,
      observed_at: new Date().toISOString(),
    });
  });

  it("does not inherit the developer's credentials and leaves no backend behind", async function () {
    const base = await sandboxBasePath();

    const credentials = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const client = plugin.getClient();
      return {
        ocr: await client.credentialAvailable("ocr"),
        embedding: await client.credentialAvailable("embedding"),
      };
    });

    // A pristine sandbox has no credentials. If this machine's real keyring
    // leaked in, every "fails closed without credentials" assertion elsewhere
    // would be meaningless.
    expect(credentials.ocr).toBe(false);
    expect(credentials.embedding).toBe(false);

    await openPanel();
    await browser.waitUntil(async () => !(await operationActive()), {
      timeout: 60000,
      timeoutMsg: "an operation was still active",
    });

    // A backend that outlives its request is invisible to every other
    // assertion here: the vault is a temp copy and its process would keep
    // running against a directory the harness is about to discard.
    let leftovers = sandboxBackendProcesses(base);
    if (leftovers > 0) {
      // Give a just-settled child a moment to exit before calling it a leak.
      await browser.pause(2000);
      leftovers = sandboxBackendProcesses(base);
    }

    appendEvidence("w01-isolation.json", {
      case_id: "X11",
      variant: "developer-state-isolation",
      required_layer: "H",
      status: leftovers === 0 ? "VERIFIED" : "FAILED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      credentials_ocr: credentials.ocr,
      credentials_embedding: credentials.embedding,
      lingering_backend_processes: leftovers,
      sandbox_base: base,
      observed_at: new Date().toISOString(),
    });

    expect(leftovers).toBe(0);
  });
  it("persists a workflow flag toggled in the UI, across a restart", async function () {
    // Case B07. The dashboard toggles go client → NodeProcessTransport →
    // `note set-flag` → the note; until #230 that command resolved a stale
    // flat path, so this path could not succeed for a synced paper. The
    // assertion is the note Python wrote, never the checkbox state.
    const before = await sandboxBasePath();
    await openPanel();
    await openVaultFile(NOTE_PATH);

    const disclosure = await browser.$(".paperforge-technical-details-toggle");
    await disclosure.waitForExist({ timeout: 60000 });
    await disclosure.click();

    const checkbox = await browser.$("[data-pf-testid='flag-analyze']");
    await checkbox.waitForDisplayed({ timeout: 60000 });
    expect(await checkbox.isSelected()).toBe(false);

    await clickTestId("flag-analyze");
    await browser.waitUntil(
      () => readFrontmatterFlag(before, BYSTANDER_NOTE, "analyze") === "true",
      {
        timeout: 60000,
        timeoutMsg: "the UI toggle never reached the note",
      }
    );

    // Durable on disk is not the same as durable across a host restart.
    await browser.reloadObsidian();
    const after = await sandboxBasePath();
    expect(path.resolve(after)).toBe(path.resolve(before));
    expect(readFrontmatterFlag(after, BYSTANDER_NOTE, "analyze")).toBe("true");

    appendEvidence("b07-note-flag.json", {
      case_id: "B07",
      variant: "UI toggle -> note frontmatter -> restart",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      field: "analyze",
      note: BYSTANDER_NOTE,
      sandbox_base: before,
      sandbox_base_after_restart: after,
      observed_at: new Date().toISOString(),
    });
  });
});
