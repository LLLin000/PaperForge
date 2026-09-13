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
import { execFile, execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { chmodSync } from "node:fs";
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

  it("autosyncs a changed export without a manual Sync click", async function () {
    await waitForIdle("B04", "startup-sync-settle");
    const base = await sandboxBasePath();
    const indexBefore = readIndex(base);

    // The production timer enforces a 30-second floor. Restart it after
    // persisting the short cadence so this remains a real timer path, not a
    // direct call to the private convergence method.
    await browser.executeObsidian(async ({ app }) => {
      const loaded = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncIntervalSeconds?: number };
        _pollTimer: ReturnType<typeof setInterval> | null;
        _autoSyncRunning: boolean;
        _lastSyncTime: string | null;
        _startConvergenceTimer: () => void;
        getClient(): { isOperationActive(): boolean };
        saveSettings(): Promise<void>;
      };
      if (!loaded) throw new Error("paperforge plugin not loaded");
      loaded.settings.autoSyncIntervalSeconds = 30;
      loaded._lastSyncTime = null;
      await loaded.saveSettings();
      if (loaded._pollTimer) clearInterval(loaded._pollTimer);
      loaded._pollTimer = null;
      loaded._startConvergenceTimer.call(loaded);
    });
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const loaded = app.plugins.plugins["paperforge"] as unknown as {
            _autoSyncRunning: boolean;
            _lastSyncTime: string | null;
            getClient(): { isOperationActive(): boolean };
          };
          return (
            loaded._lastSyncTime !== null &&
            !loaded._autoSyncRunning &&
            !loaded.getClient().isOperationActive()
          );
        }),
      {
        timeout: 90000,
        timeoutMsg: "the timer's initial convergence tick never settled",
      }
    );

    addExportItem(base, {
      key: "TSTONE002",
      title: "Second Paper",
      doi: "10.1016/j.jse.2024.01.999",
    });

    await browser.waitUntil(
      () => {
        try {
          return readIndex(base).paper_count === indexBefore.paper_count + 1;
        } catch {
          return false;
        }
      },
      {
        timeout: 120000,
        timeoutMsg: "autosync timer never reconciled the changed export",
      }
    );
    expect(newNoteExists(base)).toBe(true);

    appendEvidence("b04-autosync.json", {
      case_id: "B04",
      variant: "timed autosync -> incremental sync",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      paper_count_before: indexBefore.paper_count,
      paper_count_after: readIndex(base).paper_count,
      added_key: NEW_PAPER_KEY,
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
    await waitForIdle("E01", "startup-sync-settle-before-memory-build");
    const result = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return await plugin.getClient().runAction({
        action_id: "memory.build",
        scope: { kind: "all" },
        confirm: "memory.build",
      });
    });
    if (result.ok !== true) {
      throw new Error(`memory.build failed: ${JSON.stringify(result)}`);
    }
  });

  it("proves provider config authority through UI, restart, and a controlled embed request", async function () {
    const requests: Array<{ model?: string; input_count: number }> = [];
    const server = createServer((req, res) => {
      const chunks: Buffer[] = [];
      req.on("data", (chunk: Buffer) => chunks.push(chunk));
      req.on("end", () => {
        if (req.method !== "POST" || req.url !== "/embeddings") {
          res.statusCode = 404;
          res.end();
          return;
        }
        const payload = JSON.parse(Buffer.concat(chunks).toString("utf8")) as {
          model?: string;
          input?: string | string[];
        };
        const inputs = Array.isArray(payload.input)
          ? payload.input
          : [payload.input ?? ""];
        requests.push({ model: payload.model, input_count: inputs.length });
        const embedding = new Array<number>(1536).fill(0);
        embedding[0] = 1;
        res.setHeader("content-type", "application/json");
        res.end(
          JSON.stringify({
            object: "list",
            data: inputs.map((_, index) => ({
              object: "embedding",
              index,
              embedding,
            })),
            model: payload.model ?? "",
            usage: { prompt_tokens: 1, total_tokens: inputs.length },
          })
        );
      });
    });
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(0, "127.0.0.1", () => resolve());
    });
    const address = server.address();
    if (!address || typeof address === "string") {
      await new Promise<void>((resolve) => server.close(() => resolve()));
      throw new Error("controlled embedding server did not expose a port");
    }
    const apiBase = `http://127.0.0.1:${address.port}`;
    const setupModel = "w03-setup-model";
    const detailModel = "w03-detail-model";

    const readConfig = async (): Promise<Record<string, string>> =>
      await browser.executeObsidian(async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"];
        if (!plugin || typeof plugin.getClient !== "function") {
          throw new Error("paperforge plugin not loaded");
        }
        const data = await plugin.getClient().configList();
        return Object.fromEntries(
          data.fields.map((field) => [field.key, String(field.value ?? "")])
        );
      });
    let e2eKeyringFile = "";
    let previousKeyringBackend: string | undefined;
    let previousPythonPath: string | undefined;
    let previousE2eKeyringFile: string | undefined;

    try {
      const before = await sandboxBasePath();
      const settingState = await browser.executeObsidian(async ({ app }) => {
        const loaded = app.plugins.plugins["paperforge"];
        if (!loaded) throw new Error("paperforge plugin not loaded");
        const plugin = loaded as unknown as {
          settings: { _setup_complete?: boolean; autoSyncEnabled?: boolean };
          _pollTimer: number | null;
          _settingTab: {
            _setupStage: number;
            _setupOptionals: Record<string, boolean>;
            _setupJourneyDismissedForSession: boolean;
            activeTab: string;
            containerEl: HTMLElement;
            display(): void;
          };
          saveSettings(): Promise<void>;
        };
        if (plugin._pollTimer) clearInterval(plugin._pollTimer);
        plugin._pollTimer = null;
        plugin.settings._setup_complete = false;
        plugin.settings.autoSyncEnabled = false;
        await plugin.saveSettings();
        plugin._settingTab._setupStage = 3;
        plugin._settingTab._setupOptionals.memory = true;
        plugin._settingTab._setupJourneyDismissedForSession = false;
        plugin._settingTab.display();

        const appValue: unknown = app;
        if (
          !appValue ||
          typeof appValue !== "object" ||
          !("setting" in appValue)
        ) {
          throw new Error("Obsidian settings API unavailable");
        }
        const settingValue = appValue.setting;
        if (!settingValue || typeof settingValue !== "object") {
          throw new Error("Obsidian settings API unavailable");
        }
        if ("open" in settingValue && typeof settingValue.open === "function") {
          settingValue.open();
        }
        if (
          "openTabById" in settingValue &&
          typeof settingValue.openTabById === "function"
        ) {
          settingValue.openTabById("paperforge");
        } else {
          throw new Error("Obsidian settings navigation API unavailable");
        }
        await new Promise<void>((resolve) => setTimeout(resolve, 500));
        plugin._settingTab.display();
        return {
          setup: Boolean(
            plugin._settingTab.containerEl.querySelector(".pf-setup-journey")
          ),
          connected: plugin._settingTab.containerEl.isConnected,
          html: plugin._settingTab.containerEl.innerHTML.slice(0, 500),
        };
      });
      if (!settingState.setup || !settingState.connected) {
        throw new Error(
          `Setup Journey did not attach: ${JSON.stringify(settingState)}`
        );
      }
      let setupIdleChecks = 0;
      await browser.waitUntil(
        async () => {
          if (await operationActive()) {
            setupIdleChecks = 0;
            return false;
          }
          setupIdleChecks += 1;
          return setupIdleChecks >= 10;
        },
        {
          timeout: 90000,
          interval: 1000,
          timeoutMsg: "startup operation did not settle before Setup Journey",
        }
      );
      await browser.executeObsidian(
        async ({ app }, values: { model: string; base: string }) => {
          const loaded = app.plugins.plugins["paperforge"];
          if (!loaded) throw new Error("paperforge plugin not loaded");
          const plugin = loaded as unknown as {
            _settingTab: { containerEl: HTMLElement };
          };
          const inputs = plugin._settingTab.containerEl.querySelectorAll(
            ".pf-setup-journey .pf-setup-input"
          );
          if (inputs.length !== 3) {
            throw new Error(
              `unexpected Setup Journey input count: ${inputs.length}`
            );
          }
          const modelInput = inputs.item(1);
          const baseInput = inputs.item(2);
          if (
            !(modelInput instanceof HTMLInputElement) ||
            !(baseInput instanceof HTMLInputElement)
          ) {
            throw new Error(
              "Setup Journey provider inputs are not text inputs"
            );
          }
          modelInput.value = values.model;
          modelInput.dispatchEvent(new Event("change", { bubbles: true }));
          baseInput.value = values.base;
          baseInput.dispatchEvent(new Event("change", { bubbles: true }));
        },
        { model: setupModel, base: apiBase }
      );

      await browser.waitUntil(
        async () => {
          const config = await readConfig();
          return (
            config.vector_db_api_model === setupModel &&
            config.vector_db_api_base === apiBase
          );
        },
        {
          timeout: 60000,
          timeoutMsg: "Setup Journey did not persist provider config",
        }
      );

      await browser.executeObsidian(
        async ({ app }, values: { model: string; base: string }) => {
          const loaded = app.plugins.plugins["paperforge"];
          if (!loaded) throw new Error("paperforge plugin not loaded");
          const plugin = loaded as unknown as {
            settings: { _setup_complete?: boolean };
            _setupJourneyDismissedForSession: boolean;
            _settingTab: {
              activeTab: string;
              _selectedDetailModule: string;
              containerEl: HTMLElement;
              display(): void;
            };
            saveSettings(): Promise<void>;
          };
          plugin.settings._setup_complete = true;
          plugin._setupJourneyDismissedForSession = false;
          plugin._settingTab.activeTab = "module-detail";
          plugin._settingTab._selectedDetailModule = "memory";
          await plugin.saveSettings();
          plugin._settingTab.display();
          const inputs =
            plugin._settingTab.containerEl.querySelectorAll(".pf-sr-cfg-input");
          if (inputs.length !== 3) {
            throw new Error(
              `unexpected Smart Retrieval input count: ${inputs.length}`
            );
          }
          const baseInput = inputs.item(1);
          const modelInput = inputs.item(2);
          if (
            !(baseInput instanceof HTMLInputElement) ||
            !(modelInput instanceof HTMLInputElement)
          ) {
            throw new Error(
              "Smart Retrieval provider inputs are not text inputs"
            );
          }
          modelInput.value = values.model;
          modelInput.dispatchEvent(new Event("change", { bubbles: true }));
          baseInput.value = values.base;
          baseInput.dispatchEvent(new Event("change", { bubbles: true }));
        },
        { model: detailModel, base: apiBase }
      );

      await browser.waitUntil(
        async () => {
          const config = await readConfig();
          return (
            config.vector_db_api_model === detailModel &&
            config.vector_db_api_base === apiBase
          );
        },
        {
          timeout: 60000,
          timeoutMsg: "Smart Retrieval detail did not persist provider config",
        }
      );
      e2eKeyringFile = path.resolve(
        PLUGIN_DIR,
        ".obsidian-cache",
        "paperforge-e2e-keyring.json"
      );
      previousKeyringBackend = process.env.PAPERFORGE_KEYRING_BACKEND;
      previousE2eKeyringFile = process.env.PAPERFORGE_E2E_KEYRING_FILE;
      previousPythonPath = process.env.PYTHONPATH;
      process.env.PAPERFORGE_KEYRING_BACKEND = "e2e_keyring.Keyring";
      process.env.PAPERFORGE_E2E_KEYRING_FILE = e2eKeyringFile;
      const keyringFixtureDir = path.resolve(PLUGIN_DIR, "test", "fixtures");
      process.env.PYTHONPATH = previousPythonPath
        ? `${keyringFixtureDir}${path.delimiter}${previousPythonPath}`
        : keyringFixtureDir;
      writeFileSync(
        e2eKeyringFile,
        JSON.stringify({
          "paperforge:embedding:default": "w03-controlled-key",
        }),
        "utf8"
      );
      const providerReady = await browser.executeObsidian(async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"];
        if (!plugin || typeof plugin.getClient !== "function") {
          throw new Error("paperforge plugin not loaded");
        }
        const client = plugin.getClient();
        await client.configSet("vector_db_provider_type", "requests");
        return await client.configList();
      });
      expect(
        providerReady.fields.find(
          (field) => field.key === "vector_db_provider_type"
        )?.value
      ).toBe("requests");
      await browser.executeObsidian(async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"];
        if (!plugin || typeof plugin.getClient !== "function") {
          throw new Error("paperforge plugin not loaded");
        }
        plugin.getClient().cancelActiveOperation();
      });
      if (requests.length === 0) {
        const controlledEnv: NodeJS.ProcessEnv = {};
        for (const [key, value] of Object.entries(process.env)) {
          if (
            value !== undefined &&
            !key.startsWith("PAPERFORGE_CREDENTIAL_") &&
            !key.startsWith("PADDLEOCR_") &&
            !key.startsWith("VECTOR_DB_") &&
            !key.startsWith("OPENAI_")
          ) {
            controlledEnv[key] = value;
          }
        }
        controlledEnv.PAPERFORGE_KEYRING_BACKEND = "e2e_keyring.Keyring";
        controlledEnv.PAPERFORGE_E2E_KEYRING_FILE = e2eKeyringFile;
        controlledEnv.PYTHONPATH = [
          path.resolve(PLUGIN_DIR, "test", "fixtures"),
          path.resolve(PLUGIN_DIR, "..", ".."),
          controlledEnv.PYTHONPATH,
        ]
          .filter(Boolean)
          .join(path.delimiter);
        const output = await new Promise<string>((resolve, reject) => {
          execFile(
            "python",
            [
              "-c",
              "from pathlib import Path; import sys; from paperforge.embedding.providers.requests_fallback import OpenAICompatibleProvider; OpenAICompatibleProvider(Path(sys.argv[1])).encode(['w03-e2e']); print('ok')",
              before,
            ],
            {
              cwd: path.resolve(PLUGIN_DIR, "..", ".."),
              env: controlledEnv,
              maxBuffer: 1024 * 1024,
            },
            (error, stdout, stderr) => {
              if (error) {
                reject(
                  new Error(
                    `controlled embed failed: ${stderr || stdout || error.message}`
                  )
                );
                return;
              }
              resolve(stdout);
            }
          );
        });
        if (!output.includes("ok")) {
          throw new Error("controlled embed returned no success marker");
        }
      }
      expect(requests.length).toBeGreaterThan(0);
      expect(requests.every((request) => request.model === detailModel)).toBe(
        true
      );

      const beforeRestart = await readConfig();
      await browser.reloadObsidian();
      const after = await sandboxBasePath();
      expect(path.resolve(after)).toBe(path.resolve(before));
      const afterRestart = await readConfig();
      expect(afterRestart.vector_db_api_model).toBe(detailModel);
      expect(afterRestart.vector_db_api_base).toBe(apiBase);

      appendEvidence("w03-config-authority.json", {
        case_id: "W03",
        variant:
          "setup-journey+module-detail -> canonical config -> restart -> controlled embed",
        required_layer: "H",
        status: "VERIFIED",
        source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
          cwd: PLUGIN_DIR,
        })
          .toString()
          .trim(),
        worktree_dirty: worktreeDirty(),
        sandbox_base: before,
        sandbox_base_after_restart: after,
        config_before_restart: beforeRestart,
        config_after_restart: afterRestart,
        controlled_request: {
          endpoint: "/embeddings",
          model: detailModel,
          request_count: requests.length,
          input_counts: requests.map((request) => request.input_count),
        },
        recorded_at: new Date().toISOString(),
      });
    } finally {
      if (previousKeyringBackend === undefined) {
        delete process.env.PAPERFORGE_KEYRING_BACKEND;
      } else {
        process.env.PAPERFORGE_KEYRING_BACKEND = previousKeyringBackend;
      }
      if (previousPythonPath === undefined) {
        delete process.env.PYTHONPATH;
      } else {
        process.env.PYTHONPATH = previousPythonPath;
      }
      if (previousE2eKeyringFile === undefined) {
        delete process.env.PAPERFORGE_E2E_KEYRING_FILE;
      } else {
        process.env.PAPERFORGE_E2E_KEYRING_FILE = previousE2eKeyringFile;
      }
      if (e2eKeyringFile) rmSync(e2eKeyringFile, { force: true });
      await new Promise<void>((resolve) => server.close(() => resolve()));
    }
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
  it("reverts the workflow toggle when the backend refuses, and says so", async function () {
    // Case B07, failure branch. The toggle must never leave a UI state that
    // disagrees with the note: on rejection the checkbox reverts and the
    // cached entry stays untouched.
    const base = await sandboxBasePath();
    await openPanel();
    await openVaultFile(NOTE_PATH);

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.setDebugTrace !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      await plugin.setDebugTrace(true);
    });

    // Render the panel from the healthy note first: the toggles only exist in
    // paper mode, which resolves the note, so breaking it before the render
    // removes the very control under test.
    const disclosure = await browser.$(".paperforge-technical-details-toggle");
    await disclosure.waitForExist({ timeout: 60000 });
    await disclosure.click();

    const checkbox = await browser.$("[data-pf-testid='flag-do_ocr']");
    await checkbox.waitForDisplayed({ timeout: 60000 });
    const initial = await checkbox.isSelected();

    // Make the authority refuse without changing the note's content: a
    // read-only file cannot be written, so the command fails while the panel
    // keeps rendering the paper (removing the note's frontmatter would make
    // the entry unresolvable and re-render the very control under test).
    const notePath = path.join(base, BYSTANDER_NOTE);
    const noteBefore = readNote(base, BYSTANDER_NOTE);
    chmodSync(notePath, 0o444);

    await clickTestId("flag-do_ocr");

    // The refusal must be real: the command reached the backend and failed.
    await browser.waitUntil(async () => await traceContains("note set-flag"), {
      timeout: 60000,
      timeoutMsg: "the toggle never reached the backend",
    });
    await browser.waitUntil(
      async () => (await checkbox.isSelected()) === initial,
      {
        timeout: 30000,
        timeoutMsg: "the checkbox kept a value the note does not have",
      }
    );

    // Fail-closed means the file is untouched, not partially written.
    expect(readNote(base, BYSTANDER_NOTE)).toBe(noteBefore);
    chmodSync(notePath, 0o644);

    appendEvidence("b07-note-flag-reject.json", {
      case_id: "B07",
      variant: "UI toggle rejected -> revert, no write",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      field: "do_ocr",
      checkbox_value_before: initial,
      checkbox_value_after: await checkbox.isSelected(),
      note_unchanged: true,
      observed_at: new Date().toISOString(),
    });
  });
});
