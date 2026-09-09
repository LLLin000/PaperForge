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
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import * as path from "node:path";

const PAPER_KEY = "TSTONE001";
const NOTE_PATH =
  "Resources/Literature/骨科/TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair/TSTONE001.md";
const BASE_PATH = "Bases/骨科.base";

const PLUGIN_DIR = process.cwd();
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

async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

/** Acceptance evidence record (plan §4.3): one JSON per case variant. */
function writeEvidence(name: string, payload: Record<string, unknown>): void {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  writeFileSync(
    path.join(EVIDENCE_DIR, name),
    JSON.stringify(payload, null, 2)
  );
}

async function openVaultFile(path: string): Promise<void> {
  // New tab + explicit activation: a programmatic openFile() alone does not
  // fire active-leaf-change, so the panel would never re-resolve its mode.
  await browser.executeObsidian(async ({ app }, filePath) => {
    const file = app.vault.getAbstractFileByPath(filePath);
    if (!file) throw new Error(`file not found: ${filePath}`);
    if (!("extension" in file)) throw new Error(`not a file: ${filePath}`);
    const leaf = app.workspace.getLeaf("tab");
    await leaf.openFile(file);
    app.workspace.setActiveLeaf(leaf, { focus: true });
  }, path);
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
    const builtBundle = sha256(path.join(PLUGIN_DIR, "main.js"));
    const builtManifestSha = sha256(path.join(PLUGIN_DIR, "manifest.json"));

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

    writeEvidence("w01-candidate-binding.json", {
      case_id: "X11",
      variant: "bundle-binding+isolation",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
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

  it("runs Sync Library through the UI and refreshes the read model", async function () {
    await openPanel();
    const syncBtn = await browser.$("[data-pf-testid='sync-library']");
    await expect(syncBtn).toExist();
    await syncBtn.click();

    // Real mutation must settle and appear in the boundary trace.
    await browser.waitUntil(
      async () => await traceContains("sync --json ok=true"),
      {
        timeout: 180000,
        timeoutMsg: "sync never completed through the client",
      }
    );
    const panelText = (await browser.$(".paperforge-content-area").getText())
      .toLowerCase()
      .replace(/\s+/g, " ");
    expect(panelText).toContain("library snapshot");
    expect(panelText).toMatch(/\d+ papers/);
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
});
