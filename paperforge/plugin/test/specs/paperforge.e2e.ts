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
import * as os from "node:os";

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
const SETUP_POSITIVE_E2E = process.env.PF_E2E_SETUP_POSITIVE === "1";
const NO_POINTER_E2E =
  process.env.PF_E2E_NO_POINTER === "1" && !SETUP_POSITIVE_E2E;
/**
 * First-use journey gate (#263): the dedicated gating job sets BOTH switches.
 * While the gate is on, a would-be skip of the required journey is a FAILURE.
 * Every env-gated skip in this suite is registered below with a reason, an
 * owner and an applicability window — a skip without an entry throws instead
 * of passing quietly.
 */
const JOURNEY_GATE = process.env.PF_E2E_JOURNEY_GATE === "1";
const JOURNEY_VARIANT =
  "first-use journey: install(A01) → library → first sync → open → restart → reopen";
const E2E_SKIP_REGISTRY: Record<
  string,
  { reason: string; owner: string; window: string }
> = {
  "plugin-load-requires-pointer": {
    reason: "positive-pointer run of the suite (PF_E2E_NO_POINTER unset)",
    owner: "release-acceptance (#263)",
    window: "until the no-pointer negative suite gets its own job",
  },
  "pointer-negative-requires-no-pointer": {
    reason: "only meaningful in the PF_E2E_NO_POINTER=1 negative run",
    owner: "release-acceptance (#263)",
    window: "until the no-pointer negative suite gets its own job",
  },
  "setup-positive-default-off": {
    reason:
      "the first-use install mutates the machine-local runtime; ordinary runs do not opt in",
    owner: "release-acceptance (#263)",
    window: "enabled by the H matrix job via PF_E2E_SETUP_POSITIVE=1",
  },
};

/** Skip through the registry: an unknown or incomplete id is a failure. */
function registeredSkip(ctx: { skip(): void }, id: string): void {
  const entry = E2E_SKIP_REGISTRY[id];
  if (!entry || !entry.reason || !entry.owner || !entry.window) {
    throw new Error(`unregistered or incomplete e2e skip: ${id}`);
  }
  ctx.skip();
}

/** Gate policy: enabled → run; disabled → fail under the gate, skip otherwise. */
function journeyRunPolicy(
  gate: boolean,
  enabled: boolean
): "run" | "skip" | "fail" {
  if (enabled) return "run";
  return gate ? "fail" : "skip";
}



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

/** Remove one item from the sandbox export to create a real residual paper. */
function removeExportItem(base: string, key: string): void {
  const file = path.join(base, EXPORT_REL);
  const doc = JSON.parse(readFileSync(file, "utf8")) as {
    items: Array<Record<string, unknown>>;
    collections: Record<string, { items: string[] }>;
  };
  doc.items = doc.items.filter(
    (item) => String(item.key ?? item.itemKey ?? "") !== key
  );
  for (const collection of Object.values(doc.collections)) {
    collection.items = collection.items.filter((itemKey) => itemKey !== key);
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

function sandboxBackendProcessDetails(base: string): string {
  const marker = path.basename(base);
  if (process.platform !== "win32") return "";
  return execFileSync(
    `powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*${marker}*' -and $_.Name -like '*python*' } | Select-Object ProcessId,ParentProcessId,CreationDate,Name,CommandLine | ConvertTo-Json -Compress)"`,
    { shell: true }
  )
    .toString()
    .trim();
}

/** PIDs of backend processes referencing this sandbox right now. */
function sandboxBackendPids(base: string): number[] {
  const marker = path.basename(base);
  if (process.platform !== "win32") return [];
  const out = execFileSync(
    `powershell -NoProfile -Command "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*${marker}*' -and $_.Name -like '*python*' } | Select-Object -ExpandProperty ProcessId) -join ','"`,
    { shell: true }
  )
    .toString()
    .trim();
  return out
    ? out
        .split(",")
        .map((value) => Number(value.trim()))
        .filter((value) => Number.isFinite(value))
    : [];
}

/**
 * Assert every backend process observed within the window exits promptly.
 *
 * Samples repeatedly for at least `observationMs` so a quiet start still
 * observes the next background wave, tracks each PID's first sighting, and
 * fails when a process stays alive longer than `stragglerMs` or when the
 * window ends with one still alive. Healthy one-shot waves pass; a leak
 * cannot slip through a quiet sample, and waves spawned after a quiet
 * moment are observed rather than ignored (see #266).
 */
async function assertBackendGenerationExits(
  base: string,
  graceMs = 120000,
  observationMs = 10000,
  stragglerMs = 30000
): Promise<void> {
  const firstSeen = new Map<number, number>();
  const started = Date.now();
  for (;;) {
    const now = Date.now();
    const current = sandboxBackendPids(base);
    for (const pid of current) {
      if (!firstSeen.has(pid)) firstSeen.set(pid, now);
    }
    const stale = current.filter(
      (pid) => now - (firstSeen.get(pid) ?? now) > stragglerMs
    );
    if (stale.length > 0) {
      throw new Error(
        `backend processes outlived their operation (>${stragglerMs / 1000}s): ${stale.join(",")}\n${sandboxBackendProcessDetails(base)}`
      );
    }
    if (now - started >= observationMs && current.length === 0) return;
    if (now - started >= graceMs) {
      throw new Error(
        `backend processes kept the sandbox busy past the grace window (${graceMs / 1000}s): ${current.join(",")}\n${sandboxBackendProcessDetails(base)}`
      );
    }
    const { promise, resolve } = Promise.withResolvers<void>();
    setTimeout(resolve, 1000);
    await promise;
  }
}

/**
 * Wait until no backend process still references this sandbox.
 *
 * Used where a quiet hand-off is the contract (journey settle, pre-reset
 * barriers). The backend legitimately runs `probe all` chains with a 300s
 * transport budget, so a just-settled child can still be draining long after
 * the UI state reads idle; the drain window matches that budget and the
 * failure carries full command lines. Instantaneous "zero" assertions race
 * the plugin's background probe cadence — those sites use
 * {@link assertBackendGenerationExits} instead.
 */
async function waitForBackendDrain(
  base: string,
  timeoutMs = 300000
): Promise<void> {
  try {
    await browser.waitUntil(() => sandboxBackendProcesses(base) === 0, {
      timeout: timeoutMs,
      interval: 1000,
      timeoutMsg: "backend processes outlived their operation",
    });
  } catch (error) {
    throw new Error(
      `${String(error)}\nremaining=${sandboxBackendProcesses(base)}\n${sandboxBackendProcessDetails(base)}`
    );
  }
}


async function sandboxBasePath(): Promise<string> {
  return await browser.executeObsidian(async ({ app }) => {
    const adapter = app.vault.adapter as unknown as { basePath?: string };
    return adapter.basePath ?? "";
  });
}

/**
 * Host-profile context for every evidence record (standard §6): declared
 * `host_profile`, `runner_kind`, and a minimal `machine` block. Owner runs
 * can inject the full host-probe output via PF_E2E_MACHINE_JSON; fields that
 * are not known stay "unknown" — unknown beats wrong.
 */
const EVIDENCE_CONTEXT = (() => {
  const hosted = process.env.CI === "true";
  const machine: Record<string, unknown> = {
    os_build: String(os.release()),
    arch: String(os.arch()),
    username_ascii: /^[\x20-\x7E]*$/.test(os.userInfo().username),
    path_has_space: /\s/.test(process.env.USERPROFILE ?? ""),
    python_source: "unknown",
    network_kind: "unknown",
    defender_only: "unknown",
  };
  if (process.env.PF_E2E_MACHINE_JSON) {
    try {
      Object.assign(
        machine,
        JSON.parse(process.env.PF_E2E_MACHINE_JSON) as Record<string, unknown>
      );
    } catch {
      // keep the observed defaults
    }
  }
  return {
    host_profile:
      process.env.PF_E2E_HOST_PROFILE ??
      (hosted ? "CI<P0近似>" : "unclassified"),
    runner_kind:
      process.env.PF_E2E_RUNNER_KIND ?? (hosted ? "hosted" : "owner-machine"),
    machine,
  };
})();

/**
 * Acceptance evidence record (plan §4.3, standard §6). Runs are appended,
 * never replaced: a first failure must stay visible after a later green
 * re-run, and every record carries the host-profile context.
 */
function appendEvidence(name: string, payload: Record<string, unknown>): void {
  mkdirSync(EVIDENCE_DIR, { recursive: true });
  const file = path.join(EVIDENCE_DIR, name);
  const parsed: unknown = existsSync(file)
    ? JSON.parse(readFileSync(file, "utf8"))
    : [];
  // Older runs used a single-object record; carry it over instead of dropping it.
  const runs = Array.isArray(parsed) ? parsed : [parsed];
  runs.push({ ...EVIDENCE_CONTEXT, ...payload });
  writeFileSync(file, JSON.stringify(runs, null, 2));
}

/**
 * Scroll a panel control's nearest scrollable ancestor away from Obsidian's
 * status bar before using a real WebDriver click.
 */
async function scrollPanelElement(selector: string): Promise<void> {
  await browser.execute((selector: string) => {
    const el = document.querySelector(selector) as HTMLElement | null;
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
  }, selector);
}

async function clickPanelElement(selector: string): Promise<void> {
  const element = await browser.$(selector);
  await element.waitForExist({ timeout: 60000 });
  await scrollPanelElement(selector);
  await element.click();
}

async function clickTestId(testid: string): Promise<void> {
  await clickPanelElement(`[data-pf-testid='${testid}']`);
}

async function clickTechnicalDetails(): Promise<void> {
  await clickPanelElement(
    ".paperforge-technical-details > .paperforge-technical-details-toggle"
  );
}

async function openVaultFile(filePath: string): Promise<void> {
  // New tab + explicit activation: a programmatic openFile() alone does not
  // fire active-leaf-change, so the panel would never re-resolve its mode.
  await browser.executeObsidian(async ({ app }, filePath) => {
    let file = app.vault.getAbstractFileByPath(filePath);
    if (!file && (await app.vault.adapter.exists(filePath))) {
      // Mirrors the product repair for externally delivered notes
      // (`_materializeExternalNote`): a file written by the Python backend is
      // physically present but not yet in the Vault cache until the fs watcher
      // fires. Register it with the same read → remove → create sequence and
      // restore the bytes if registration fails.
      const content = await app.vault.adapter.read(filePath);
      await app.vault.adapter.remove(filePath);
      try {
        file = await app.vault.create(filePath, content);
      } catch (error) {
        await app.vault.adapter.write(filePath, content);
        throw error;
      }
    }
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
    if (NO_POINTER_E2E) {
      registeredSkip(this, "plugin-load-requires-pointer");
      return;
    }
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

  it("fails closed and exposes setup recovery without a runtime pointer", async function () {
    if (!NO_POINTER_E2E) {
      registeredSkip(this, "pointer-negative-requires-no-pointer");
      return;
    }
    const state = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _getPythonCommand(): { path: string; args: string[] } | null;
        getManagedRuntime(): { readPointer(): unknown };
        settings: { _setup_complete?: boolean };
        _settingTab: {
          _capabilityState?: Record<
            string,
            { user_state?: string; reason?: { code?: string } }
          >;
          _setupJourneyDismissedForSession: boolean;
          containerEl: HTMLElement;
          display(): void;
        };
      };
      if (!plugin) throw new Error("paperforge plugin not loaded");
      plugin._settingTab._setupJourneyDismissedForSession = false;
      plugin.settings._setup_complete = false;
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
      await new Promise<void>((resolve) => setTimeout(resolve, 1000));
      const journey = plugin._settingTab.containerEl.querySelector(
        ".pf-setup-journey"
      );
      const badge = plugin._settingTab.containerEl.querySelector(
        ".pf-setup-journey [role='status']"
      );
      const actionButtons = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(
          ".pf-setup-journey button.pf-action-btn"
        )
      ).map((button) => ({
        text: button.textContent ?? "",
        disabled: button.hasAttribute("disabled"),
      }));
      const envelope = plugin._settingTab._capabilityState?.installation;
      return {
        pointer: plugin.getManagedRuntime().readPointer(),
        python_command: plugin._getPythonCommand(),
        setup_complete: plugin.settings._setup_complete,
        journey: Boolean(journey),
        badge: badge?.textContent ?? "",
        action_buttons: actionButtons,
        user_state: envelope?.user_state ?? "",
        reason_code: envelope?.reason?.code ?? "",
      };
    });
    expect(state.pointer).toBeNull();
    expect(state.python_command).toBeNull();
    expect(state.setup_complete).toBe(false);
    expect(state.journey).toBe(true);
    expect(state.user_state).not.toBe("ready");
    expect(state.reason_code).toBe("installation.no_python");
    expect(state.badge).not.toBe("Ready");
    expect(
      state.action_buttons.filter((button) => !button.disabled).length
    ).toBeGreaterThanOrEqual(2);
    appendEvidence("a02-pointer-negative.json", {
      case_id: "A02",
      variant: "cold-open-without-runtime-pointer",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      pointer: null,
      user_state: state.user_state,
      reason_code: state.reason_code,
      setup_journey: state.journey,
      action_buttons: state.action_buttons,
      recorded_at: new Date().toISOString(),
    });
  });

  it("installs and publishes the runtime through the first-use setup journey", async function () {
    if (!SETUP_POSITIVE_E2E) {
      registeredSkip(this, "setup-positive-default-off");
      return;
    }
    this.timeout(600000);
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
      install.click();
    });
    await browser.waitUntil(
      async () => {
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
              pointer !== null &&
              plugin._settingTab._setupOperation === "idle" &&
              installation?.user_state === "ready",
            operation: plugin._settingTab._setupOperation,
            feedback: plugin._settingTab._setupFeedback,
            reason_code: installation?.reason?.code ?? "",
          };
        });
        if (status.operation === "failed") {
          throw new Error(
            `first-use setup failed: ${status.feedback ?? status.reason_code}`
          );
        }
        return status.ready;
      },
      {
        timeout: 540000,
        interval: 1000,
        timeoutMsg: "first-use setup did not publish a ready runtime pointer",
      }
    );
    const state = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getManagedRuntime(): {
          readPointer(): {
            pythonPath: string;
            environmentRoot: string;
            paperforgeVersion: string;
          } | null;
        };
        settings: { _setup_complete?: boolean };
        _settingTab: {
          _setupOperation: string;
          _setupFeedback: string | null;
          _capabilityState?: Record<string, { user_state?: string }>;
        };
      };
      return {
        pointer: plugin.getManagedRuntime().readPointer(),
        setup_complete: plugin.settings._setup_complete,
        operation: plugin._settingTab._setupOperation,
        feedback: plugin._settingTab._setupFeedback,
        user_state:
          plugin._settingTab._capabilityState?.installation?.user_state ?? "",
      };
    });
    expect(state.pointer).not.toBeNull();
    expect(state.pointer?.paperforgeVersion).toBe(CANDIDATE_VERSION);
    expect(existsSync(state.pointer?.pythonPath ?? "")).toBe(true);
    expect(existsSync(state.pointer?.environmentRoot ?? "")).toBe(true);
    expect(state.operation).toBe("idle");
    const setupBase = await sandboxBasePath();
    for (const relative of [
      "paperforge.json",
      "System",
      "Resources",
      "Resources/Literature",
      "Resources/LiteratureControl",
      "Bases",
    ]) {
      expect(existsSync(path.join(setupBase, relative))).toBe(true);
    }
    expect(state.user_state).toBe("ready");
    expect(state.setup_complete).toBe(false);
    appendEvidence("a01-first-use.json", {
      case_id: "A01",
      variant: "first-use-install-setup-pointer-publication",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      pointer: state.pointer,
      setup_operation: state.operation,
      installation_user_state: state.user_state,
      setup_complete: state.setup_complete,
      recorded_at: new Date().toISOString(),
    });
  });

  it("journey gate contract: registered skips and the run policy stay explicit", function () {
    const ids = Object.keys(E2E_SKIP_REGISTRY);
    expect(ids.length).toBeGreaterThanOrEqual(3);
    for (const id of ids) {
      const entry = E2E_SKIP_REGISTRY[id];
      expect(entry.reason.length).toBeGreaterThan(0);
      expect(entry.owner.length).toBeGreaterThan(0);
      expect(entry.window.length).toBeGreaterThan(0);
    }
    expect(journeyRunPolicy(true, false)).toBe("fail");
    expect(journeyRunPolicy(true, true)).toBe("run");
    expect(journeyRunPolicy(false, false)).toBe("skip");
    expect(journeyRunPolicy(false, true)).toBe("run");
  });

  it("first-use journey gate: library → first sync → open paper → restart → reopen", async function () {
    const policy = journeyRunPolicy(JOURNEY_GATE, SETUP_POSITIVE_E2E);
    if (policy === "fail") {
      throw new Error(
        "PF_E2E_JOURNEY_GATE=1 requires PF_E2E_SETUP_POSITIVE=1 — the first-use journey must run, not skip"
      );
    }
    if (policy === "skip") {
      registeredSkip(this, "setup-positive-default-off");
      return;
    }
    this.timeout(1500000);
    const steps: Array<{ name: string; ok: boolean; ms: number }> = [];
    const runStep = async (
      name: string,
      fn: () => Promise<void>
    ): Promise<void> => {
      const started = Date.now();
      try {
        await fn();
        steps.push({ name, ok: true, ms: Date.now() - started });
      } catch (error) {
        steps.push({ name, ok: false, ms: Date.now() - started });
        appendEvidence("first-use-journey.json", {
          case_id: "GATE-01",
          variant: JOURNEY_VARIANT,
          required_layer: "H",
          gate: true,
          status: "FAILED",
          failed_step: name,
          steps,
          error: String(error),
          source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
            cwd: PLUGIN_DIR,
          })
            .toString()
            .trim(),
          worktree_dirty: worktreeDirty(),
          recorded_at: new Date().toISOString(),
        });
        throw error;
      }
    };

    // The install step ran in A01 directly above; the gate asserts it really
    // produced a fresh candidate runtime in THIS run before continuing.
    const installed = await browser.executeObsidian(async ({ app }) => {
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
    expect(installed).not.toBeNull();
    expect(installed?.paperforgeVersion).toBe(CANDIDATE_VERSION);
    // #260 semantics: a fresh install lands in a candidate directory.
    expect(String(installed?.environmentRoot ?? "")).toContain("venv-");

    await runStep("connect-library", async () => {
      await browser.reloadObsidian({ vault: "./test/vaults/e2e" });
      await dismissModals();
      const base = await sandboxBasePath();
      expect(existsSync(path.join(base, EXPORT_REL))).toBe(true);
      await openPanel();
    });

    let noteSha = "";
    await runStep("first-sync", async () => {
      const base = await sandboxBasePath();
      // First sync means: empty derived state → export → index + note.
      rmSync(path.join(base, INDEX_REL), { force: true });
      await browser.executeObsidian(async ({ app }, notePath) => {
        const file = app.vault.getAbstractFileByPath(notePath);
        if (file) await app.vault.delete(file);
      }, NOTE_PATH);
      await browser.waitUntil(() => !existsSync(path.join(base, NOTE_PATH)), {
        timeout: 30000,
        timeoutMsg:
          "first-use journey: could not clear the existing canonical note",
      });
      expect(existsSync(path.join(base, INDEX_REL))).toBe(false);
      const exportPath = path.join(base, EXPORT_REL);
      const exportBefore = sha256(exportPath);
      await openPanel();
      const syncBtn = await browser.$("[data-pf-testid='sync-library']");
      await expect(syncBtn).toExist();
      await syncBtn.click();
      await browser.waitUntil(
        () => {
          try {
            const index = readIndex(base);
            return (
              index.paper_count > 0 &&
              index.keys.includes(PAPER_KEY) &&
              existsSync(path.join(base, NOTE_PATH))
            );
          } catch {
            return false;
          }
        },
        {
          timeout: 180000,
          timeoutMsg:
            "first-use journey: initial sync never materialized the library",
        }
      );
      expect(sha256(exportPath)).toBe(exportBefore);
      noteSha = sha256(path.join(base, NOTE_PATH));
    });

    await runStep("open-paper", async () => {
      await openVaultFile(NOTE_PATH);
      await browser.waitUntil(
        async () =>
          await browser.executeObsidian(
            async ({ app }, notePath) =>
              app.workspace.getActiveFile()?.path === notePath,
            NOTE_PATH
          ),
        {
          timeout: 30000,
          timeoutMsg: "first-use journey: the note did not open",
        }
      );
    });

    await runStep("restart-obsidian", async () => {
      await browser.reloadObsidian();
      await dismissModals();
      await openPanel();
    });

    await runStep("reopen-paper-after-restart", async () => {
      const base = await sandboxBasePath();
      expect(sha256(path.join(base, NOTE_PATH))).toBe(noteSha);
      await openVaultFile(NOTE_PATH);
      await browser.waitUntil(
        async () =>
          await browser.executeObsidian(
            async ({ app }, notePath) =>
              app.workspace.getActiveFile()?.path === notePath,
            NOTE_PATH
          ),
        {
          timeout: 30000,
          timeoutMsg:
            "first-use journey: the note did not reopen after restart",
        }
      );
    });

    // The app-level restart above can leave backend children draining; the
    // next suite test asserts no backend process outlives this sandbox, so the
    // journey must hand over a settled state (probe chains have a 300s budget).
    await runStep("backend-settled", async () => {
      const base = await sandboxBasePath();
      await waitForBackendDrain(base);
    });

    appendEvidence("first-use-journey.json", {
      case_id: "GATE-01",
      variant: JOURNEY_VARIANT,
      required_layer: "H",
      gate: true,
      status: "VERIFIED",
      steps,
      total_ms: steps.reduce((sum, step) => sum + step.ms, 0),
      pointer: installed,
      artifact_sha256: {
        bundle: sha256(path.join(PLUGIN_DIR, "main.js")),
        // Hash of the wheel OFFERED to pip via PIP_FIND_LINKS; the install
        // resolves `paperforge==<version>` from that link or the index (same
        // version either way), so this is provenance for the offer, not proof
        // of which equal-version artifact pip chose.
        wheel_offered: process.env.PF_E2E_WHEEL_SHA256 ?? null,
      },
      obsidian_version: String(await browser.getObsidianVersion()),
      fixture_vault: FIXTURE_VAULT,
      sandbox_base: await sandboxBasePath(),
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      recorded_at: new Date().toISOString(),
    });
  });

  it("disables and restarts autosync without duplicate timers or orphan processes", async function () {
    const base = await sandboxBasePath();
    await waitForIdle("A07", "startup-sync-settle");
    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        saveSettings(): Promise<void>;
      };
      plugin.settings.autoSyncEnabled = false;
      await plugin.saveSettings();
    });
    await browser.reloadObsidian();
    const disabled = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        _pollTimer: ReturnType<typeof setInterval> | null;
        getClient(): { isOperationActive(): boolean };
      };
      return {
        enabled: plugin.settings.autoSyncEnabled,
        timer: plugin._pollTimer !== null,
        operation_active: plugin.getClient().isOperationActive(),
      };
    });
    expect(disabled.enabled).toBe(false);
    expect(disabled.timer).toBe(false);
    expect(disabled.operation_active).toBe(false);

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        saveSettings(): Promise<void>;
      };
      plugin.settings.autoSyncEnabled = true;
      await plugin.saveSettings();
    });
    await browser.reloadObsidian();
    await waitForIdle("A07", "restart-with-autosync-enabled");
    const enabled = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        _pollTimer: ReturnType<typeof setInterval> | null;
        getClient(): { isOperationActive(): boolean };
      };
      return {
        enabled: plugin.settings.autoSyncEnabled,
        timer: plugin._pollTimer !== null,
        operation_active: plugin.getClient().isOperationActive(),
      };
    });
    expect(enabled.enabled).toBe(true);
    expect(enabled.timer).toBe(true);
    expect(enabled.operation_active).toBe(false);
    await assertBackendGenerationExits(base);
    appendEvidence("a07-disable-restart.json", {
      case_id: "A07",
      variant: "disable-reload-enable-reload",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      sandbox_base: base,
      disabled_timer: disabled.timer,
      resumed_timer: enabled.timer,
      backend_processes_after_idle: sandboxBackendProcesses(base),
      recorded_at: new Date().toISOString(),
    });
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

  it("performs an initial sync from the export into empty derived state", async function () {
    let base = await sandboxBasePath();
    await waitForIdle("B01", "startup-sync-settle");
    expect(existsSync(path.join(base, EXPORT_REL))).toBe(true);

    await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        saveSettings(): Promise<void>;
      };
      plugin.settings.autoSyncEnabled = false;
      await plugin.saveSettings();
    });
    await browser.reloadObsidian();
    base = await sandboxBasePath();
    const exportPath = path.join(base, EXPORT_REL);
    const exportBefore = sha256(exportPath);
    await dismissModals();
    const disabled = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        _pollTimer: ReturnType<typeof setInterval> | null;
      };
      return {
        enabled: plugin.settings.autoSyncEnabled,
        timer: plugin._pollTimer !== null,
      };
    });
    expect(disabled.enabled).toBe(false);
    expect(disabled.timer).toBe(false);
    await waitForBackendDrain(base);
    rmSync(path.join(base, INDEX_REL), { force: true });
    await browser.executeObsidian(async ({ app }, notePath) => {
      const file = app.vault.getAbstractFileByPath(notePath);
      if (file) await app.vault.delete(file);
    }, NOTE_PATH);
    await browser.waitUntil(() => !existsSync(path.join(base, NOTE_PATH)), {
      timeout: 30000,
      timeoutMsg: "B01 could not clear the existing canonical note",
    });
    expect(existsSync(path.join(base, INDEX_REL))).toBe(false);
    expect(existsSync(path.join(base, NOTE_PATH))).toBe(false);

    await openPanel();
    const syncBtn = await browser.$("[data-pf-testid='sync-library']");
    await expect(syncBtn).toExist();
    await syncBtn.click();
    await browser.waitUntil(
      () => {
        try {
          const index = readIndex(base);
          return (
            index.paper_count > 0 &&
            index.keys.includes(PAPER_KEY) &&
            existsSync(path.join(base, NOTE_PATH))
          );
        } catch {
          return false;
        }
      },
      {
        timeout: 180000,
        timeoutMsg: "initial Sync never rebuilt the canonical library",
      }
    );

    const indexAfter = readIndex(base);
    expect(indexAfter.keys).toContain(PAPER_KEY);
    expect(sha256(exportPath)).toBe(exportBefore);
    appendEvidence("b01-initial-sync.json", {
      case_id: "B01",
      variant: "empty-derived-state -> UI Sync",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      fixture_vault: FIXTURE_VAULT,
      sandbox_base: base,
      input_export: EXPORT_REL,
      input_export_sha256_before: exportBefore,
      input_export_sha256_after: sha256(exportPath),
      paper_count_after: indexAfter.paper_count,
      asserted_key: PAPER_KEY,
      canonical_index: INDEX_REL,
      canonical_note: NOTE_PATH,
      autosync_disabled: true,
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
  it("exposes and completes destructive orphan pruning from the real UI", async function () {
    await waitForIdle("J06", "startup-sync-settle");
    const base = await sandboxBasePath();
    const workspace = path.dirname(NOTE_PATH);
    expect(existsSync(path.join(base, workspace))).toBe(true);
    const exportPath = path.join(base, EXPORT_REL);

    removeExportItem(base, PAPER_KEY);
    await openPanel();
    const staleModal = await browser.$(".modal-container");
    if (await staleModal.isExisting()) {
      await browser.keys("Escape");
      await browser.waitUntil(
        async () => !(await browser.$(".modal-container").isExisting()),
        {
          timeout: 10000,
          interval: 500,
          timeoutMsg: "a previous orphan modal did not close before Sync",
        }
      );
    }
    const syncBtn = await browser.$("[data-pf-testid='sync-library']");
    await expect(syncBtn).toExist();
    await syncBtn.click();

    await browser.waitUntil(
      async () => (await browser.$(".modal-container").isExisting()) === true,
      {
        timeout: 180000,
        interval: 1000,
        timeoutMsg: "orphan residual modal was not exposed after Sync",
      }
    );
    const modal = await browser.$(".modal-container");
    const modalText = (await modal.getText()).toLowerCase();
    expect(modalText).toContain(PAPER_KEY.toLowerCase());
    expect(modalText).toContain("delete 1 selected");

    const deleteButton = await modal.$("button.mod-cta");
    await deleteButton.click();
    await browser.waitUntil(() => !existsSync(path.join(base, workspace)), {
      timeout: 120000,
      interval: 500,
      timeoutMsg: "destructive orphan prune did not remove the workspace",
    });
    // The residual modal's close action is separate from deletion: close it
    // through its own control (falling back to Escape), retry while the
    // container lingers, and fail with the modal text if it never goes away.
    for (let attempt = 0; attempt < 10; attempt++) {
      if (!(await browser.$(".modal-container").isExisting())) break;
      const container = await browser.$(".modal-container");
      const closeButton = await container.$(".modal-close-button");
      if (await closeButton.isExisting()) {
        await closeButton.click().catch(() => undefined);
      } else {
        await browser.keys("Escape");
      }
      await browser.pause(500);
    }
    if (await browser.$(".modal-container").isExisting()) {
      const lingering = await browser.$(".modal-container");
      const text = await lingering.getText().catch(() => "");
      throw new Error(
        `orphan prune modal did not close after deletion; text=${text.slice(0, 300)}`
      );
    }
    expect(existsSync(path.join(base, workspace))).toBe(false);
    expect(existsSync(exportPath)).toBe(true);
    appendEvidence("j06-destructive-prune.json", {
      case_id: "J06",
      variant: "export-remove -> Sync -> residual modal -> confirmed prune",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      fixture_vault: FIXTURE_VAULT,
      sandbox_base: base,
      removed_key: PAPER_KEY,
      exported_carrier: EXPORT_REL,
      deleted_workspace: workspace,
      recorded_at: new Date().toISOString(),
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

  it("does not re-enter or leave autosync running after a failed tick", async function () {
    await waitForIdle("B04", "boundary-startup-settle");
    const base = await sandboxBasePath();
    const boundary = await browser.executeObsidian(async ({ app }, vaultPath) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { autoSyncEnabled?: boolean };
        _pollTimer: ReturnType<typeof setInterval> | null;
        _autoSyncRunning: boolean;
        _lastSyncTime: string | null;
        _autoSync: (path: string) => void;
        _startConvergenceTimer: () => void;
        getClient: () => { sync: () => Promise<unknown> };
        saveSettings(): Promise<void>;
      };
      if (!plugin) throw new Error("paperforge plugin not loaded");
      if (plugin._pollTimer) clearInterval(plugin._pollTimer);
      plugin._pollTimer = null;
      plugin.settings.autoSyncEnabled = false;
      await plugin.saveSettings();
      plugin._startConvergenceTimer.call(plugin);
      const disabledTimer = plugin._pollTimer !== null;

      plugin._autoSyncRunning = true;
      plugin._lastSyncTime = null;
      plugin._autoSync(vaultPath);
      const reentryBlocked =
        plugin._autoSyncRunning === true && plugin._lastSyncTime === null;
      plugin._autoSyncRunning = false;

      const originalGetClient = plugin.getClient;
      plugin.getClient = () => ({
        sync: async () => {
          throw new Error("forced B04 failure");
        },
      });
      plugin._lastSyncTime = null;
      plugin._autoSync(vaultPath);
      const deadline = Date.now() + 3000;
      while (plugin._autoSyncRunning && Date.now() < deadline) {
        const { promise, resolve } = Promise.withResolvers<void>();
        setTimeout(resolve, 25);
        await promise;
      }
      plugin.getClient = originalGetClient;
      return {
        disabledTimer,
        reentryBlocked,
        failureSettled: !plugin._autoSyncRunning,
        lastSyncTime: plugin._lastSyncTime,
      };
    }, base);

    expect(boundary.disabledTimer).toBe(false);
    expect(boundary.reentryBlocked).toBe(true);
    expect(boundary.failureSettled).toBe(true);
    expect(boundary.lastSyncTime).toBe(null);
    await assertBackendGenerationExits(base);
    appendEvidence("b04-autosync-boundaries.json", {
      case_id: "B04",
      variant: "disabled + reentry + forced failure cleanup",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      sandbox_base: base,
      disabled_timer: boundary.disabledTimer,
      reentry_blocked: boundary.reentryBlocked,
      failure_settled: boundary.failureSettled,
      last_sync_time_after_failure: boundary.lastSyncTime,
      backend_processes_after_failure: sandboxBackendProcesses(base),
      recorded_at: new Date().toISOString(),
    });
  });

  it("carries a new synced paper through memory search and opens it", async function () {
    const cadence = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      return plugin.settings.autoSyncIntervalSeconds ?? 120;
    });
    expect(cadence).toBeGreaterThanOrEqual(120);

    await openPanel();
    await waitForIdle("J01", "startup-sync-settle");
    const base = await sandboxBasePath();
    const key = "J01MEM001";
    const title = "J01 Memory Marker";
    const notePath = `Resources/Literature/骨科/${key} - ${title}/${key}.md`;
    const bystanderBefore = sha256(path.join(base, BYSTANDER_NOTE));
    addExportItem(base, {
      key,
      title,
      doi: "10.1016/j.jse.2024.01.998",
    });

    const syncBtn = await browser.$("[data-pf-testid='sync-library']");
    await expect(syncBtn).toExist();
    await syncBtn.click();
    await browser.waitUntil(
      () => {
        try {
          const index = readIndex(base);
          return (
            index.keys.includes(key) && existsSync(path.join(base, notePath))
          );
        } catch {
          return false;
        }
      },
      {
        timeout: 180000,
        timeoutMsg: "J01 Sync never materialized the new paper",
      }
    );
    await waitForIdle("J01", "manual-sync-settle");
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(
          async ({ app }, expectedKey) =>
            app.workspace.getLeavesOfType("paperforge-status").some((leaf) => {
              const items = (leaf.view as { _cachedItems?: unknown[] })
                ._cachedItems;
              return (
                Array.isArray(items) &&
                items.some(
                  (item) =>
                    item &&
                    typeof item === "object" &&
                    (item as { zotero_key?: unknown }).zotero_key ===
                      expectedKey
                )
              );
            }),
          key
        ),
      {
        timeout: 60000,
        timeoutMsg: "J01 dashboard did not refresh its synced read model",
      }
    );
    expect(sha256(path.join(base, BYSTANDER_NOTE))).toBe(bystanderBefore);

    const memoryResult = await browser.executeObsidian(async ({ app }) => {
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
    if (memoryResult.ok !== true) {
      throw new Error(`J01 memory.build failed: ${JSON.stringify(memoryResult)}`);
    }

    await openPanel();
    await openVaultFile(BASE_PATH);
    const input = await browser.$(".paperforge-search-input");
    await input.waitForExist({ timeout: 60000 });
    await input.setValue(title);
    await browser.keys("Enter");
    const card = await browser.$(".paperforge-search-result-card");
    await browser.waitUntil(
      async () => {
        try {
          return (await card.getText()).includes(title);
        } catch {
          return false;
        }
      },
      { timeout: 60000, timeoutMsg: "J01 M search never found the synced paper" }
    );
    await card.click();
    const j01OpenState = await browser.executeObsidian(
      async ({ app }, expectedPath) => {
        const leaves: Array<Record<string, unknown>> = [];
        app.workspace.iterateAllLeaves((leaf) => {
          leaves.push({
            view_type: leaf.view.getViewType(),
            file_path: leaf.view.file?.path ?? null,
            active: leaf === app.workspace.activeLeaf,
          });
        });
        const target = app.vault.getAbstractFileByPath(expectedPath);
        return {
          expected_path: expectedPath,
          adapter_exists: await app.vault.adapter.exists(expectedPath),
          target_path: target?.path ?? null,
          active_file: app.workspace.getActiveFile()?.path ?? null,
          most_recent_file:
            app.workspace.getMostRecentLeaf()?.view.file?.path ?? null,
          search_results: app.workspace
            .getLeavesOfType("paperforge-status")
            .map((leaf) => (leaf.view as { _searchResults?: unknown })._searchResults),
          leaves,
        };
      },
      notePath
    );
    console.log(`J01 open state: ${JSON.stringify(j01OpenState)}`);
    appendEvidence("j01-open-debug.json", j01OpenState);
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(
          async ({ app }, expectedPath) =>
            app.workspace.getActiveFile()?.path === expectedPath,
          notePath
        ),
      {
        timeout: 60000,
        timeoutMsg: "J01 search result did not open the synced paper",
      }
    );

    appendEvidence("j01-sync-memory-search.json", {
      case_id: "J01",
      variant: "new-export -> UI Sync -> memory.build -> M search -> open",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      sandbox_base: base,
      key,
      title,
      note_path: notePath,
      bystander_note: BYSTANDER_NOTE,
      bystander_sha256_before: bystanderBefore,
      bystander_sha256_after: sha256(path.join(base, BYSTANDER_NOTE)),
      memory_action: "memory.build",
      search_mode: "M",
      opened_active_file: notePath,
      recorded_at: new Date().toISOString(),
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
    let workspaceText = "";
    await browser.waitUntil(
      async () => {
        const text = await (await browser.$(".pf-ocr-ws-viewport"))
          .getText()
          .catch(() => "");
        if (!text.includes("Biomechanical")) return false;
        workspaceText = text;
        return true;
      },
      { timeout: 60000, timeoutMsg: "OCR workspace rows never rendered" }
    );
    appendEvidence("d01-ocr-workspace.json", {
      case_id: "D01",
      variant: "ocr-workspace rows render from real lineage",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      matched_row: "Biomechanical",
      viewport_text_head: workspaceText.slice(0, 300),
      recorded_at: new Date().toISOString(),
    });
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

    // Use a vault-relative path for the read. Windows Obsidian can expose the
    // adapter base via its 8.3 form while Python returns the long absolute
    // path; slicing absolute strings by length then invents a suffix such as
    // `...\hR9\System/...`.
    const content = await browser.executeObsidian(async ({ app }, key) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const paths = await plugin.getClient().versionsPaths(key);
      const expected = `System/PaperForge/ocr/${key}/render/fulltext.md`;
      const returned = String(paths.current_path ?? "")
        .replaceAll("\\", "/")
        .toLowerCase();
      if (!returned.endsWith(`/${expected.toLowerCase()}`)) {
        throw new Error(
          `unexpected current_path: ${String(paths.current_path)}`
        );
      }
      const file = app.vault.getAbstractFileByPath(expected);
      if (!file || !("extension" in file)) {
        throw new Error(`render file not found: ${expected}`);
      }
      return await app.vault.adapter.read(expected);
    }, PAPER_KEY);
    expect(content).toContain("first body");
    appendEvidence("d07-version-restore.json", {
      case_id: "D07",
      variant: "version-history modal -> restore v1 -> body readback",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      labels,
      restored_contains: "first body",
      trace_marker: "versions restore",
      recorded_at: new Date().toISOString(),
    });
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
    appendEvidence("e01-memory-build.json", {
      case_id: "E01",
      variant: "client memory.build through the real backend",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      action_ok: true,
      recorded_at: new Date().toISOString(),
    });
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

      try {
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
            interval: 2000,
            timeoutMsg: "Setup Journey did not persist provider config",
          }
        );
      } catch (error) {
        const snapshot = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: {
              _setupFeedback: string | null;
              _setupOperation: string;
            };
            getClient(): { isOperationActive(): boolean };
          };
          return {
            feedback: plugin._settingTab._setupFeedback,
            operation: plugin._settingTab._setupOperation,
            operation_active: plugin.getClient().isOperationActive(),
          };
        });
        const config = await readConfig().catch(() => null);
        throw new Error(
          `${String(error)}\nsnapshot=${JSON.stringify(snapshot)} config=${JSON.stringify(config)}`
        );
      }

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

  it("toggles, copies and clears the client debug trace from the settings UI", async function () {
    // F06 UI face: the diagnostics section ships a toggle, Copy and Clear for
    // the in-memory client trace. Drive the real controls and read plugin
    // state back; the Copy notice proves the clipboard path ran.
    const openRow = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { debug_trace?: boolean };
        _settingTab: {
          containerEl: HTMLElement;
          display(): void;
          _selectedDetailModule?: string | null;
          activeTab?: string;
          _initialDisplay?: boolean;
          _setupJourneyDismissedForSession?: boolean;
        };
      };
      if (!plugin) throw new Error("paperforge plugin not loaded");
      const appWithSetting = app as unknown as {
        setting?: { open?: () => void; openTabById?: (id: string) => void };
      };
      const setting = appWithSetting.setting;
      if (!setting?.open || !setting.openTabById) {
        throw new Error("Obsidian settings navigation API unavailable");
      }
      setting.open();
      setting.openTabById("paperforge");
      await new Promise<void>((resolve) => setTimeout(resolve, 500));
      // The debug trace lives in the memory module detail's diagnostics
      // section ("Advanced Status"/Details). Skip the one-time nav-memory
      // restore (it would overwrite the tab state) and any first-run journey.
      plugin._settingTab._initialDisplay = false;
      plugin._settingTab._setupJourneyDismissedForSession = true;
      plugin._settingTab._selectedDetailModule = "memory";
      plugin._settingTab.activeTab = "module-detail";
      plugin._settingTab.display();
      const details = plugin._settingTab.containerEl.querySelector(
        ".pf-sr-diagnostics"
      );
      if (!(details instanceof HTMLDetailsElement)) {
        throw new Error("diagnostics section not rendered");
      }
      details.open = true;
      const rows = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(".setting-item")
      );
      const row = rows.find((el) =>
        (el.querySelector(".setting-item-name")?.textContent ?? "").includes(
          "Debug trace"
        )
      );
      if (!row) throw new Error("Debug trace row not found");
      const toggle = row.querySelector("input[type=checkbox]");
      if (!(toggle instanceof HTMLInputElement)) {
        throw new Error("Debug trace toggle not found");
      }
      if (!toggle.checked) toggle.click();
      return { rowFound: true };
    });
    expect(openRow.rowFound).toBe(true);

    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            settings: { debug_trace?: boolean };
          };
          return plugin.settings.debug_trace === true;
        }),
      { timeout: 10000, timeoutMsg: "debug trace toggle did not persist" }
    );

    // Generate a record through the real client, then Copy (the notice proves
    // the clipboard path ran) and Clear (the readback proves the reset).
    const before = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): { probeAll(): Promise<unknown> };
        getDebugTrace(): string;
      };
      await plugin.getClient().probeAll();
      return plugin.getDebugTrace().length;
    });
    expect(before).toBeGreaterThan(0);

    const pressButton = async (label: string): Promise<void> => {
      await browser.executeObsidian(async ({ app }, text) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          _settingTab: { containerEl: HTMLElement };
        };
        const row = Array.from(
          plugin._settingTab.containerEl.querySelectorAll(".setting-item")
        ).find((el) =>
          (el.querySelector(".setting-item-name")?.textContent ?? "").includes(
            "Debug trace"
          )
        );
        const button = Array.from(row?.querySelectorAll("button") ?? []).find(
          (candidate) => (candidate.textContent ?? "").trim() === text
        );
        if (!(button instanceof HTMLButtonElement)) {
          throw new Error(`${text} button not found`);
        }
        button.click();
      }, label);
    };
    const copySmoke = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const row = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(".setting-item")
      ).find((el) =>
        (el.querySelector(".setting-item-name")?.textContent ?? "").includes(
          "Debug trace"
        )
      );
      const button = Array.from(row?.querySelectorAll("button") ?? []).find(
        (candidate) => (candidate.textContent ?? "").trim() === "Copy"
      );
      if (!(button instanceof HTMLButtonElement)) {
        throw new Error("Copy button not found");
      }
      // The clipboard write is platform-dependent in the renderer
      // (navigator.clipboard is non-configurable and may be absent under
      // file://), so the contract here is the click smoke: the real control
      // runs its handler without error and the trace stays intact. The
      // Copy notice is recorded opportunistically, not asserted.
      button.click();
      await new Promise<void>((resolve) => setTimeout(resolve, 300));
      return true;
    });
    expect(copySmoke).toBe(true);
    const noticeSeen = await browser.execute(() =>
      Array.from(document.querySelectorAll(".notice")).some((el) =>
        (el.textContent ?? "").includes("Copied")
      )
    );
    const traceAfterCopy = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getDebugTrace(): string;
      };
      return plugin.getDebugTrace().length;
    });
    expect(traceAfterCopy).toBeGreaterThan(0);

    await pressButton("Clear");
    const cleared = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { debug_trace?: boolean };
        getDebugTrace(): string;
        saveSettings(): Promise<void>;
        _settingTab: {
          _selectedDetailModule?: string | null;
          activeTab?: string;
        };
      };
      const length = plugin.getDebugTrace().length;
      // leave the machine off and the settings view back on its default for
      // the following tests
      plugin.settings.debug_trace = false;
      plugin._settingTab._selectedDetailModule = null;
      plugin._settingTab.activeTab = "overview";
      await plugin.saveSettings();
      return length;
    });
    expect(cleared).toBe(0);

    appendEvidence("f06-trace-ui.json", {
      case_id: "F06",
      variant: "settings UI: debug trace toggle / copy(click smoke) / clear",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      trace_lines_before_clear: before,
      trace_lines_after_clear: cleared,
      copy_notice_seen: noticeSeen,
      recorded_at: new Date().toISOString(),
    });
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
    // running against a directory the harness is about to discard. The
    // contract is `assertBackendGenerationExits` above (every observed
    // process must exit promptly); the sample below is informational.
    await assertBackendGenerationExits(base);

    appendEvidence("w01-isolation.json", {
      case_id: "X11",
      variant: "developer-state-isolation",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      credentials_ocr: credentials.ocr,
      credentials_embedding: credentials.embedding,
      lingering_backend_processes: sandboxBackendProcesses(base),
      sandbox_base: base,
      observed_at: new Date().toISOString(),
    });
  });
  it("persists a workflow flag toggled in the UI, across a restart", async function () {
    // Case B07. The dashboard toggles go client → NodeProcessTransport →
    // `note set-flag` → the note; until #230 that command resolved a stale
    // flat path, so this path could not succeed for a synced paper. The
    // assertion is the note Python wrote, never the checkbox state.
    const before = await sandboxBasePath();
    await openPanel();
    await openVaultFile(NOTE_PATH);

    await clickTechnicalDetails();

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
    await clickTechnicalDetails();

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
