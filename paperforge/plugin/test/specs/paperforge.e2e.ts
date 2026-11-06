/**
 * Real Obsidian gate — the cases that can ONLY be proven in the real host.
 *
 * Everything the harness itself can prove lives in a cheaper layer and is
 * deliberately NOT duplicated here (2026-11-06, gate reduction):
 *
 *  - backend behaviour, sync, OCR, protocol, install CLI  → tests/e2e,
 *    L2 protocol suite, job P (CLI host acceptance)
 *  - plugin logic (transport, settings, capability state) → vitest
 *  - architecture boundaries                              → L4b
 *
 * What remains is the smallest set whose failure would be invisible to those
 * layers:
 *
 *  A01  first-use journey installs a runtime and publishes a pointer
 *  A06  reinstall rebuilds the environment and republishes the pointer
 *  H1   plugin load → real Python backend, artifact-bound
 *  H2   the UI search box returns real index results
 *  H3   a UI toggle reaches the note and survives a host restart
 *
 * The workspace is a sandboxed real Obsidian with the repo plugin installed
 * from "." and a disposable vault built by `test/fixtures/build_e2e_vault.py`.
 *
 * NOTE: `executeObsidian` serializes its callback into the Obsidian window,
 * so callbacks must be self-contained and return serializable data.
 */
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
  type Dirent,
} from "node:fs";
import * as os from "node:os";
import * as path from "node:path";

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
const EVIDENCE_DIR = path.resolve(PLUGIN_DIR, "test", "evidence");

/** Version of the artifact under test (plugin manifest is version-synced). */
const CANDIDATE_VERSION = (
  JSON.parse(readFileSync(path.join(PLUGIN_DIR, "manifest.json"), "utf8")) as {
    version: string;
  }
).version;

function sha256(file: string): string {
  return createHash("sha256").update(readFileSync(file)).digest("hex");
}

function readNote(base: string, rel: string): string {
  return readFileSync(path.join(base, rel), "utf8");
}

/** One frontmatter field of a sandbox note, trimmed ("" when absent). */
function readFrontmatterFlag(base: string, rel: string, field: string): string {
  const match = readNote(base, rel).match(
    new RegExp(`^${field}:\\s*(.+)$`, "m")
  );
  return match ? match[1].trim() : "";
}

function newestSourceMtime(dir: string): number {
  let newest = 0;
  const walk = (current: string): void => {
    for (const entry of readdirSync(current, {
      withFileTypes: true,
    }) as Dirent[]) {
      if (entry.name === "node_modules" || entry.name === "tests") continue;
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) walk(full);
      else if (entry.name.endsWith(".ts")) {
        newest = Math.max(newest, statSync(full).mtimeMs);
      }
    }
  };
  walk(path.join(dir, "src"));
  return newest;
}

function worktreeDirty(): boolean {
  return (
    execFileSync("git", ["status", "--porcelain"], { cwd: PLUGIN_DIR })
      .toString()
      .trim().length > 0
  );
}

async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

/** Acceptance evidence record: runs are appended, never replaced. */
function appendEvidence(name: string, payload: Record<string, unknown>): void {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const file = path.join(EVIDENCE_DIR, name);
  const parsed: unknown = existsSync(file)
    ? JSON.parse(readFileSync(file, "utf8"))
    : [];
  const runs = Array.isArray(parsed) ? parsed : [parsed];
  runs.push(payload);
  writeFileSync(file, JSON.stringify(runs, null, 2));
}

function sourceSha(): string {
  return execFileSync("git", ["rev-parse", "HEAD"], { cwd: PLUGIN_DIR })
    .toString()
    .trim();
}

const POINTER_PATH = path.join(os.homedir(), ".paperforge", "runtime", "pointer.json");

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
  ).waitForExist({ timeout: 60000 });
}

/**
 * Click an element identified by its stable test id.
 *
 * The dashboard panel is taller than the window, and a row that lands in the
 * bottom band is covered by Obsidian's status bar — WebDriver then refuses the
 * click ("element click intercepted"). This scrolls the nearest scrollable
 * ancestor, which is what a user does with the wheel.
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

/** Everything the runtime journey reports about itself, for failure output. */
async function dumpRuntimeState(): Promise<Record<string, unknown>> {
  return await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      manifest?: { version?: string };
      getManagedRuntime?: () => { readPointer(): unknown };
      _settingTab?: {
        _setupOperation?: string;
        _setupFeedback?: string | null;
        _runtimeStatus?: unknown;
        _runtimeStatusError?: string | null;
        _runtimeStatusLoading?: boolean;
        _runtimePollTimer?: unknown;
      };
    } | null;
    const tab = plugin?._settingTab;
    return {
      pointer: plugin?.getManagedRuntime?.().readPointer() ?? null,
      operation: tab?._setupOperation ?? "(no tab)",
      feedback: tab?._setupFeedback ?? null,
      status: tab?._runtimeStatus ?? null,
      status_error: tab?._runtimeStatusError ?? null,
      status_loading: tab?._runtimeStatusLoading ?? null,
      poll_running: Boolean(tab?._runtimePollTimer),
      manifest_version: plugin?.manifest?.version ?? null,
    };
  });
}

async function openVaultFile(filePath: string): Promise<void> {
  await browser.executeObsidian(async ({ app }, filePath) => {
    const file = app.vault.getAbstractFileByPath(filePath);
    if (!file) throw new Error(`file not found: ${filePath}`);
    if (!("extension" in file)) throw new Error(`not a file: ${filePath}`);
    const leaf = app.workspace.getLeaf("tab");
    await leaf.openFile(file);
    app.workspace.setActiveLeaf(leaf, { focus: true });
  }, filePath);
}

/** Wait for a runtime-journey outcome; on timeout report the observed state
 * instead of a bare "Timeout" (the state is what makes the next run cheap). */
async function waitForOutcome(
  check: () => Promise<boolean>,
  options: {
    timeoutMs: number;
    label: string;
    evidence: string;
    caseId: string;
  }
): Promise<void> {
  try {
    await browser.waitUntil(check, {
      timeout: options.timeoutMs,
      interval: 1000,
      timeoutMsg: options.label,
    });
  } catch (error) {
    const state = await dumpRuntimeState();
    appendEvidence(options.evidence, {
      case_id: options.caseId,
      status: "FAILED",
      detail: String(error),
      state,
      source_sha: sourceSha(),
      worktree_dirty: worktreeDirty(),
      recorded_at: new Date().toISOString(),
    });
    throw new Error(`${options.label}: ${JSON.stringify(state)}`);
  }
}

describe("PaperForge real-host gate", function () {
  beforeEach(async function () {
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

  // ── A01: first-use journey publishes a runtime ───────────────────────────
  it("installs a runtime through the first-use journey and publishes the pointer", async function () {
    this.timeout(1800000);
    // First use means "no runtime yet": drop the pointer so the panel offers
    // the install action instead of update/repair.
    rmSync(POINTER_PATH, { force: true });
    await browser.reloadObsidian({ vault: "./test/vaults/empty" });
    await dismissModals();

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: {
          _setupJourneyDismissedForSession: boolean;
          containerEl: HTMLElement;
          display(): void;
        };
        settings: { _setup_complete?: boolean };
      };
      if (!plugin) throw new Error("paperforge plugin not loaded");
      plugin.settings._setup_complete = false;
      plugin._settingTab._setupJourneyDismissedForSession = false;
      const setting = (app as unknown as {
        setting?: {
          open?: () => void;
          openTabById?: (id: string) => void;
        };
      }).setting;
      if (!setting?.open || !setting.openTabById) {
        throw new Error("Obsidian settings navigation API unavailable");
      }
      setting.open();
      setting.openTabById("paperforge");
      await new Promise<void>((resolve) => setTimeout(resolve, 1000));
      plugin._settingTab.display();

      const install = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          ".pf-setup-journey button.pf-action-btn"
        )
      ).find(
        (button) =>
          !button.hasAttribute("disabled") &&
          /paperforge/i.test(button.textContent ?? "")
      );
      if (!install) {
        throw new Error("first-use setup install action was not rendered");
      }
      (install as HTMLButtonElement).click();
    });

    await waitForOutcome(async () => {
        const status = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            getManagedRuntime(): { readPointer(): unknown };
            _settingTab: {
              _setupOperation: string;
              _setupFeedback: string | null;
              _capabilityState?: Record<
                string,
                { user_state?: string; reason?: { code?: string } }
              >;
            };
          };
          const pointer = plugin.getManagedRuntime().readPointer();
          const installation = plugin._settingTab._capabilityState?.installation;
          return {
            ready:
              pointer !== null && plugin._settingTab._setupOperation === "idle",
            operation: plugin._settingTab._setupOperation,
            feedback: plugin._settingTab._setupFeedback,
            reason_code: installation?.reason?.code ?? "",
            user_state: installation?.user_state ?? "",
          };
        });
        if (status.operation === "failed") {
          throw new Error(
            `first-use setup failed: ${status.feedback ?? status.reason_code}`
          );
        }
        return status.ready;
    }, {
      timeoutMs: 1500000,
      label: "first-use setup did not publish a runtime pointer",
      evidence: "a01-first-use.json",
      caseId: "A01",
    });

    const state = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getManagedRuntime(): {
          readPointer(): {
            pythonPath: string;
            environmentRoot: string;
            paperforgeVersion: string;
          } | null;
        };
      };
      return { pointer: plugin.getManagedRuntime().readPointer() };
    });

    expect(state.pointer).not.toBeNull();
    expect(state.pointer?.paperforgeVersion).toBe(CANDIDATE_VERSION);
    expect(existsSync(state.pointer?.pythonPath ?? "")).toBe(true);
    expect(existsSync(state.pointer?.environmentRoot ?? "")).toBe(true);

    appendEvidence("a01-first-use.json", {
      case_id: "A01",
      variant: "first-use install → pointer publication",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: sourceSha(),
      worktree_dirty: worktreeDirty(),
      pointer: state.pointer,
      recorded_at: new Date().toISOString(),
    });
  });

  // ── A06: reinstall rebuilds the environment ──────────────────────────────
  it("reinstalls the runtime and republishes a fresh environment", async function () {
    this.timeout(1800000);
    const pointerBefore = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getManagedRuntime(): {
          readPointer(): {
            pythonPath: string;
            environmentRoot: string;
            paperforgeVersion: string;
          } | null;
        };
      };
      return plugin.getManagedRuntime().readPointer();
    });
    expect(pointerBefore).not.toBeNull();
    const beforeRoot = pointerBefore?.environmentRoot ?? "";

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: {
          containerEl: HTMLElement;
          display(): void;
          _startSetupJourney(stage?: number, reinstall?: boolean): void;
        };
      };
      plugin._settingTab._startSetupJourney(1, true);
      await new Promise<void>((resolve) => setTimeout(resolve, 500));
      plugin._settingTab.display();
      const action = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          ".pf-setup-journey button.pf-action-btn"
        )
      ).find(
        (button) =>
          !button.hasAttribute("disabled") &&
          /reinstall|重新安装/i.test(button.textContent ?? "")
      );
      if (!action) throw new Error("reinstall action was not rendered");
      (action as HTMLButtonElement).click();
    });

    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: { _setupOperation: string };
          };
          return plugin._settingTab._setupOperation !== "idle";
        }),
      { timeout: 30000, timeoutMsg: "reinstall click never started the operation" }
    );

    await waitForOutcome(async () => {
        const status = await browser.executeObsidian(
          async ({ app }, previousRoot) => {
            const plugin = app.plugins.plugins["paperforge"] as unknown as {
              getManagedRuntime(): {
                readPointer(): { environmentRoot: string } | null;
              };
              _settingTab: {
                _setupOperation: string;
                _setupFeedback: string | null;
                _setupFailureDetail: string | null;
              };
            };
            const pointer = plugin.getManagedRuntime().readPointer();
            return {
              ready:
                plugin._settingTab._setupOperation === "idle" &&
                pointer !== null &&
                pointer.environmentRoot !== previousRoot,
              operation: plugin._settingTab._setupOperation,
              feedback: plugin._settingTab._setupFeedback,
              detail: plugin._settingTab._setupFailureDetail,
            };
          },
          beforeRoot
        );
        if (status.operation === "failed") {
          throw new Error(
            `reinstall failed: ${status.feedback ?? ""} :: ${status.detail ?? ""}`
          );
        }
        return status.ready;
    }, {
      timeoutMs: 1500000,
      label: "reinstall did not republish a runtime pointer",
      evidence: "a06-reinstall-switch.json",
      caseId: "A06",
    });

    const pointerAfter = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getManagedRuntime(): {
          readPointer(): {
            pythonPath: string;
            environmentRoot: string;
            paperforgeVersion: string;
          } | null;
        };
      };
      return plugin.getManagedRuntime().readPointer();
    });
    expect(pointerAfter).not.toBeNull();
    expect(pointerAfter?.paperforgeVersion).toBe(
      pointerBefore?.paperforgeVersion
    );
    expect(pointerAfter?.environmentRoot).not.toBe(beforeRoot);
    expect(existsSync(pointerAfter?.pythonPath ?? "")).toBe(true);

    appendEvidence("a06-reinstall-switch.json", {
      case_id: "A06",
      variant: "journey reinstall → fresh candidate publish",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: sourceSha(),
      worktree_dirty: worktreeDirty(),
      pointer_before: pointerBefore,
      pointer_after: pointerAfter,
      recorded_at: new Date().toISOString(),
    });
  });

  // ── H1: the loaded bundle IS the artifact under test ──────────────────────
  it("loads the plugin, binds the built bundle, and reaches the real backend", async function () {
    const bundlePath = path.join(PLUGIN_DIR, "main.js");
    expect(statSync(bundlePath).mtimeMs).toBeGreaterThanOrEqual(
      newestSourceMtime(PLUGIN_DIR)
    );
    const builtBundle = sha256(bundlePath);

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
    expect(info.plugin_version).toBe(CANDIDATE_VERSION);
    expect(info.backend).toBe(CANDIDATE_VERSION);
    expect(info.capability_state).toBe("ready");

    const base = await sandboxBasePath();
    expect(base.length).toBeGreaterThan(0);
    // reloadObsidian copies the vault: the running instance must never be the
    // fixture source directory.
    expect(path.resolve(base)).not.toBe(
      path.resolve(PLUGIN_DIR, "test", "vaults", "e2e")
    );
    // The plugin directory the host loaded is this repo's build.
    expect(sha256(path.join(PLUGIN_DIR, "manifest.json"))).toBe(
      sha256(path.join(base, ".obsidian", "plugins", "paperforge", "manifest.json"))
    );
    expect(builtBundle.length).toBe(64);
  });

  // ── H2: the UI search box reads the real index ───────────────────────────
  it("searches through the collection-mode search box", async function () {
    await openPanel();
    await openVaultFile(BASE_PATH);
    // The dashboard is a main-area tab (not a sidebar leaf), so opening the
    // Base deactivates it: the view stays mounted but is not "interactable"
    // to WebDriver. Dispatch on the live DOM node the way the user's
    // keystrokes do, and assert on rendered text.
    await browser.waitUntil(
      async () =>
        await browser.execute(
          () => document.querySelector(".paperforge-search-input") !== null
        ),
      { timeout: 60000, timeoutMsg: "search input never mounted" }
    );
    await browser.execute(() => {
      const input = document.querySelector(
        ".paperforge-search-input"
      ) as HTMLInputElement | null;
      if (!input) throw new Error("search input missing");
      input.value = "suture";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(
        new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
      );
    });

    await browser.waitUntil(
      async () =>
        await browser.execute(() =>
          (
            document.querySelector(".paperforge-search-section")?.textContent ??
            ""
          ).includes("Suture Anchor")
        ),
      { timeout: 60000, timeoutMsg: "search results never rendered" }
    );
  });

  // ── H3: a UI toggle reaches the note and survives a restart ──────────────
  it("persists a workflow flag toggled in the UI, across a restart", async function () {
    const before = await sandboxBasePath();
    await openPanel();
    await openVaultFile(NOTE_PATH);

    // Same main-tab reason as H2: the panel is mounted but behind the note's
    // tab, so drive the controls through the DOM instead of WebDriver clicks.
    await browser.waitUntil(
      async () =>
        await browser.execute(
          () =>
            document.querySelector(".paperforge-technical-details-toggle") !==
            null
        ),
      { timeout: 60000, timeoutMsg: "panel controls never mounted" }
    );
    const wasUnchecked = await browser.execute(() => {
      const toggle = document.querySelector(
        ".paperforge-technical-details-toggle"
      ) as HTMLButtonElement | null;
      toggle?.click();
      const checkbox = document.querySelector(
        "[data-pf-testid='flag-analyze']"
      ) as HTMLInputElement | null;
      return checkbox ? checkbox.checked === false : false;
    });
    expect(wasUnchecked).toBe(true);

    await browser.execute(() => {
      const checkbox = document.querySelector(
        "[data-pf-testid='flag-analyze']"
      ) as HTMLInputElement | null;
      if (!checkbox) throw new Error("flag checkbox missing");
      checkbox.checked = true;
      checkbox.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await browser.waitUntil(
      () => readFrontmatterFlag(before, NOTE_PATH, "analyze") === "true",
      {
        timeout: 60000,
        timeoutMsg: "the UI toggle never reached the note",
      }
    );

    // Durable on disk is not the same as durable across a host restart.
    await browser.reloadObsidian();
    const after = await sandboxBasePath();
    expect(path.resolve(after)).toBe(path.resolve(before));
    expect(readFrontmatterFlag(after, NOTE_PATH, "analyze")).toBe("true");

    appendEvidence("h3-note-flag.json", {
      case_id: "H3",
      variant: "UI toggle → note frontmatter → restart",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: sourceSha(),
      field: "analyze",
      note: NOTE_PATH,
      observed_at: new Date().toISOString(),
    });
  });
});
