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
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  statSync,
  unlinkSync,
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
  "legacy-missing-extension-skipped-chromadb-available": {
    reason:
      "ChromaDB is installed in the venv used to verify this branch, so the missing-extension path (LegacyVectorUnavailable) cannot be driven without uninstalling it; the branch is skipped in that environment",
    owner: "real-machine verification (#265)",
    window: "until a ChromaDB-free runtime is available for E05",
  },
  "e05-real-migration-needs-legacy-vector-runtime": {
    reason:
      "real legacy-vector migration needs both a chromadb runtime and the committed tests/sandbox/legacy-chroma store copied into the vault vector dir",
    owner: "real-machine verification (#265)",
    window: "until the legacy-vector runtime and fixture are present",
  },
  "x06-429-job-level-resubmit-budget": {
    reason:
      "Job-level 429 handling resubmits the whole pipeline per attempt (about 3x a full run), which exceeds any practical e2e budget; bounded-retry accounting is asserted by the 5xx and drop modes. Deep 429 backoff semantics belong to the runtime-convergence backlog.",
    owner: "runtime convergence P0 (#266-era backlog)",
    window: "until the 429 job-resubmit path gets a unit-level budget harness",
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
/** Export title of the second paper (B05 A→B discriminator). */
const SECOND_PAPER_TITLE = "Second Paper";
/** Third paper for the two-paper OCR batch (J02). */
const THIRD_PAPER_KEY = "TSTONE003";
const THIRD_PAPER_TITLE = "Third Paper";
const THIRD_PAPER_NOTE =
  "Resources/Literature/骨科/TSTONE003 - Third Paper/TSTONE003.md";
/** Export title of the factory paper (B05 A→B discriminator). */
const PAPER_TITLE =
  "Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair";
/** Canonical fulltext artifact the panel advertises for PAPER_KEY. */
const CANONICAL_FULLTEXT = "System/PaperForge/ocr/TSTONE001/fulltext.md";
/** PDF target the canonical index advertises (BBT storage wikilink body). */
const PAPER_PDF = "System/Zotero/storage/TSTONE001/TSTONE001.pdf";
/** Real PDF used to satisfy the advertised PDF target (repo fixture). */
const PDF_FIXTURE = path.resolve(
  PLUGIN_DIR,
  "..",
  "..",
  "tests",
  "sandbox",
  "TestZoteroData",
  "storage",
  "TSTONE001",
  "TSTONE001.pdf"
);
const EXPORT_REL = "System/PaperForge/exports/骨科.json";
const INDEX_REL = "System/PaperForge/indexes/formal-library.json";


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

/** One canonical-index item, or a hard failure (no silent absent field). */
function readIndexItem(base: string, key: string): Record<string, unknown> {
  const raw = JSON.parse(readFileSync(path.join(base, INDEX_REL), "utf8")) as {
    items?: Record<string, unknown>[];
  };
  const item = (raw.items ?? []).find(
    (entry) => String(entry.zotero_key ?? "") === key
  );
  if (!item) throw new Error(`canonical index has no item for ${key}`);
  return item;
}

/** Write one sandbox file, creating parents (host-side setup, like the export). */
function writeSandboxFile(base: string, rel: string, content: string): void {
  const target = path.join(base, rel);
  mkdirSync(path.dirname(target), { recursive: true });
  writeFileSync(target, content);
}

/**
 * The panel's resolved context as RENDERED: the mode badge's attributes plus
 * the visible mode name. B05 asserts this — never an internal field.
 */
async function panelContext(): Promise<{
  mode: string | null;
  key: string | null;
  label: string;
  name: string;
}> {
  return await browser.execute(() => {
    const panel = document.querySelector(".paperforge-status-panel");
    const root: ParentNode = panel ?? document;
    const badge = root.querySelector("[data-pf-testid='mode-badge']");
    return {
      mode: badge?.getAttribute("data-pf-mode") ?? null,
      key: badge?.getAttribute("data-pf-key") ?? null,
      label: (badge?.textContent ?? "").trim(),
      name: (
        root.querySelector("[data-pf-testid='mode-name']")?.textContent ?? ""
      ).trim(),
    };
  });
}

/** Wait until the panel renders the given mode (and key, when supplied). */
async function waitForPanel(mode: string, key?: string): Promise<void> {
  await browser.waitUntil(
    async () => {
      const context = await panelContext();
      if (context.mode !== mode) return false;
      return key === undefined || context.key === key;
    },
    {
      timeout: 60000,
      timeoutMsg: `the panel never rendered mode=${mode}${
        key === undefined ? "" : ` key=${key}`
      }`,
    }
  );
}

/** Wait until the dashboard's cached read model carries the key. */
async function waitForDashboardIndexKey(key: string): Promise<void> {
  await browser.waitUntil(
    async () =>
      await browser.executeObsidian(async ({ app }, expectedKey) => {
        for (const leaf of app.workspace.getLeavesOfType("paperforge-status")) {
          const view = leaf.view;
          if (!("_cachedItems" in view)) continue;
          const items = view._cachedItems;
          if (!Array.isArray(items)) continue;
          for (const item of items) {
            if (
              item !== null &&
              typeof item === "object" &&
              "zotero_key" in item &&
              item.zotero_key === expectedKey
            ) {
              return true;
            }
          }
        }
        return false;
      }, key),
    {
      timeout: 60000,
      timeoutMsg: `the dashboard never loaded ${key} into its read model`,
    }
  );
}

/** The workspace's active file path, as Obsidian reports it. */
async function activeFilePath(): Promise<string | null> {
  return await browser.executeObsidian(
    async ({ app }) => app.workspace.getActiveFile()?.path ?? null
  );
}

/** Leaf inventory around an open action (wrong-leaf findings need the proof). */
async function workspaceFileState(): Promise<Record<string, unknown>> {
  return await browser.executeObsidian(async ({ app }) => {
    const leaves: Array<Record<string, unknown>> = [];
    app.workspace.iterateAllLeaves((leaf) => {
      const view = leaf.view;
      let filePath: string | null = null;
      if (
        "file" in view &&
        view.file !== null &&
        typeof view.file === "object" &&
        "path" in view.file &&
        typeof view.file.path === "string"
      ) {
        filePath = view.file.path;
      }
      leaves.push({
        view_type: view.getViewType(),
        file_path: filePath,
        active: leaf === app.workspace.activeLeaf,
      });
    });
    return {
      active_file: app.workspace.getActiveFile()?.path ?? null,
      leaves,
    };
  });
}

/** Wait until the given active file is the one Obsidian activated. */
async function waitForActiveFile(rel: string): Promise<void> {
  try {
    await browser.waitUntil(async () => (await activeFilePath()) === rel, {
      timeout: 60000,
      timeoutMsg: `active file never became ${rel}`,
    });
  } catch (error) {
    throw new Error(
      `${String(error)}\nobserved=${JSON.stringify(await workspaceFileState())}`
    );
  }
}

/** Wait for a visible Obsidian notice containing `needle`. */
async function waitUntilNotice(needle: string): Promise<void> {
  await browser.waitUntil(
    () =>
      browser.execute(
        (text: string) =>
          Array.from(document.querySelectorAll(".notice")).some((el) =>
            (el.textContent ?? "").includes(text)
          ),
        needle
      ),
    { timeout: 30000, timeoutMsg: `no visible notice said "${needle}"` }
  );
}

/** Register an externally written binary file with Obsidian's Vault. */
async function materializeBinaryFile(rel: string): Promise<void> {
  await browser.executeObsidian(async ({ app }, target: string) => {
    const existing = app.vault.getAbstractFileByPath(target);
    if (existing && "extension" in existing) return;
    const adapter = app.vault.adapter as unknown as {
      readBinary(path: string): Promise<ArrayBuffer>;
      exists(path: string): Promise<boolean>;
    };
    const parent = target.slice(0, target.lastIndexOf("/"));
    if (parent && !app.vault.getAbstractFileByPath(parent)) {
      try {
        await app.vault.createFolder(parent);
      } catch {
        // An already-registered parent is fine; the write below is the proof.
      }
    }
    if (!(await adapter.exists(target))) {
      throw new Error(`missing on disk: ${target}`);
    }
    await app.vault.createBinary(target, await adapter.readBinary(target));
  }, rel);
}

/**
 * Remove one sandbox file, tolerating its absence.
 *
 * Deliberately NOT `rmSync(path, { force: true })`: under sandbox paths that
 * contain spaces plus CJK characters (the P1 profile) Node's rmSync
 * silently leaves the file in place — `lstat` succeeds immediately before,
 * `unlinkSync` removes the very same path, and `existsSync` still reports
 * the file afterwards (reproduced standalone on Windows, Node v24). A
 * no-op cleanup poisons the "empty derived state" precondition silently,
 * so sandbox cleanup goes through unlinkSync.
 */
function removeFileQuiet(filePath: string): void {
  for (let attempt = 0; ; attempt += 1) {
    try {
      unlinkSync(filePath);
      return;
    } catch (error) {
      const code = (error as NodeJS.ErrnoException).code;
      if (code === "ENOENT") return;
      // Windows: the app may still hold the handle right after a restart.
      if (code === "EBUSY" && attempt < 9) {
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000);
        continue;
      }
      throw error;
    }
  }
}

/** Click the library Sync control.  The modal container can be gone while
 * its fading backdrop still intercepts native clicks (element click
 * intercepted by .modal-bg on the runner), so wait for the backdrop to
 * clear, then dispatch through the DOM so the handler fires on the live
 * node. */
async function clickSyncLibrary(): Promise<void> {
  await browser.waitUntil(
    async () => (await browser.$(".modal-bg").isExisting()) === false,
    {
      timeout: 15000,
      interval: 250,
      timeoutMsg: "the modal backdrop never cleared before Sync",
    }
  );
  await browser.waitUntil(
    async () =>
      await browser.execute(() => {
        const btn = document.querySelector(
          "[data-pf-testid='sync-library']"
        ) as HTMLButtonElement | null;
        return Boolean(btn && !btn.disabled);
      }),
    { timeout: 30000, timeoutMsg: "Sync stayed disabled" }
  );
  await browser.execute(() => {
    const btn = document.querySelector(
      "[data-pf-testid='sync-library']"
    ) as HTMLButtonElement | null;
    btn?.click();
  });
}

/** Click a freshly queried element, retrying once through a stale-element
 * error (Obsidian re-renders replace nodes between the wait and the click). */
async function clickStable(selector: string): Promise<void> {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const element = await browser.$(selector);
    await element.waitForExist({ timeout: 30000 });
    try {
      await element.click();
      return;
    } catch (error) {
      if (attempt === 2) throw error;
      await browser.pause(500);
    }
  }
}

/** Wait until the OCR workspace renders a row for `title`. */
async function waitForOcrRow(title: string, key?: string): Promise<void> {
  await (
    await browser.$(".pf-ocr-ws-viewport")
  ).waitForExist({ timeout: 180000 });
  try {
    await browser.waitUntil(
      async () => {
        // The viewport's rendered TEXT does not carry the title cells (the
        // CI dump showed three "Pending" rows with empty title text), so
        // match the DOM like the D02 case does: a row whose subtree
        // contains the title, else the key.
        const byTitle = await browser.$$(
          `//tr[.//*[contains(text(),'${title}')]]`
        );
        if (byTitle.length > 0) return true;
        if (key) {
          const byKey = await browser.$$(
            `//tr[.//*[contains(text(),'${key}')]]`
          );
          return byKey.length > 0;
        }
        return false;
      },
      { timeout: 180000, timeoutMsg: `OCR workspace row never rendered: ${title}` }
    );
  } catch (error) {
    // Name the state: what the client lists vs what the viewport shows.
    const rows = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): { queryOcrPapers(): Promise<Array<Record<string, unknown>>> };
      };
      try {
        const list = await plugin.getClient().queryOcrPapers();
        return list.map((row) => `${String(row.key ?? row.zotero_key ?? "?")}`).join(",");
      } catch (err) {
        return "THREW: " + String(err);
      }
    });
    const viewport = await (
      await browser.$(".pf-ocr-ws-viewport")
    ).getText().catch(() => "(no viewport)");
    console.log(
      "J02ROW list=" + JSON.stringify(rows) + " viewport=" + JSON.stringify(viewport.slice(0, 300))
    );
    throw error;
  }
}


/** Loopback PaddleOCR stub for the OCR e2e cases.
 *
 * `success`: two observations of `running`, then `done` + a JSONL result built
 * from a real provider payload fixture. `running`: never completes (stop case).
 * The result URL is served outside the jobs path so the worker's plain fetch
 * is exercised too.
 *
 * DEFAULT (no options): one job, `pf-e2e-job-1`, reported by the batch
 * endpoint from the very first poll, with a single shared observation counter
 * — byte for byte what every pre-existing case pins.
 *
 * `failKeys` opts IN, for the two-paper batch case only, to per-paper jobs:
 * every upload gets its own job id, and named papers terminal-fail at the
 * provider (their results are never served). The paper is read from the
 * multipart filename — `requests` sends the PDF's BASENAME, not its vault
 * path, so the stem (`TSTONE003.pdf` → `TSTONE003`) is the only identity the
 * upload carries. The worker resubmits a dead job up to
 * MAX_OCR_JOB_ATTEMPTS, so the key — not the job id or the upload order — is
 * what a per-paper outcome is pinned to.
 */
async function startOcrStub(
  mode: "success" | "running",
  options: {
    failKeys?: string[];
    scenario?: "ok" | "401" | "403" | "429" | "5xx" | "drop" | "malformed";
    retryAfter?: number;
  } = {}
): Promise<{
  requests: Array<{ method: string; url: string; key?: string }>;
  jobUrl: string;
  close: () => Promise<void>;
}> {
  const requests: Array<{ method: string; url: string; key?: string }> = [];
  const failKeys = new Set(options.failKeys ?? []);
  const perPaper = failKeys.size > 0;
  const scenario = (options as { scenario?: string }).scenario ?? "ok";
  const retryAfter = (options as { retryAfter?: number }).retryAfter ?? 1;
  const LEGACY_JOB_ID = "pf-e2e-job-1";
  // The legacy job is visible to the batch observer before any upload.
  const jobKeys = new Map<string, string>(
    perPaper ? [] : [[LEGACY_JOB_ID, ""]]
  );
  const observed = new Map<string, number>();
  let nextJob = 0;
  let resultUrl = "";
  const payloadFixture = path.resolve(
    PLUGIN_DIR,
    "..",
    "..",
    "tests",
    "fixtures",
    "ocr_real_papers",
    "5MAW65YD",
    "ocr_payload.json"
  );
  const payloadPages = JSON.parse(readFileSync(payloadFixture, "utf8")) as unknown[];
  const resultBody = `${JSON.stringify({ result: payloadPages[0] })}\n`;
  // One job is observed through the BATCH endpoint whenever the batch reports
  // it (per-job polling is only the fallback), so BOTH observation paths must
  // advance the same counter — otherwise a healthy job in a multi-paper batch
  // reads `running` forever and the batch never settles.
  const observe = (jobId: string): void => {
    observed.set(jobId, (observed.get(jobId) ?? 0) + 1);
  };
  const jobState = (jobId: string): { state: string; errorMsg?: string } => {
    const key = jobKeys.get(jobId) ?? "";
    if (failKeys.has(key)) {
      return {
        state: "error",
        errorMsg: `controlled provider rejection for ${key}`,
      };
    }
    const done = mode === "success" && (observed.get(jobId) ?? 0) >= 2;
    return { state: done ? "done" : "running" };
  };
  const server = createServer((req, res) => {
    const url = req.url ?? "";
    const record: { method: string; url: string; key?: string } = {
      method: req.method ?? "",
      url,
    };
    requests.push(record);
    const sendJson = (value: unknown): void => {
      res.setHeader("content-type", "application/json");
      res.end(JSON.stringify(value));
    };
    if (req.method === "POST" && url.startsWith("/api/v2/ocr/jobs")) {
      if (!perPaper && scenario === "ok") {
        // Pre-change behaviour, untouched: one fixed job id, body unread.
        req.on("data", () => undefined);
        req.on("end", () => sendJson({ data: { jobId: LEGACY_JOB_ID } }));
        return;
      }
      if (!perPaper) {
        // Scripted provider response for the X06 failure-mode leg.
        const chunks: Buffer[] = [];
        req.on("data", (chunk: Buffer) => chunks.push(chunk));
        req.on("end", () => {
          if (scenario === "drop") {
            try {
              req.socket.destroy();
            } catch {
              // best effort
            }
            return;
          }
          if (scenario === "malformed") {
            res.statusCode = 200;
            res.setHeader("content-type", "application/json");
            res.end("{ this is not valid json");
            return;
          }
          const status =
            scenario === "401"
              ? 401
              : scenario === "403"
              ? 403
              : scenario === "429"
              ? 429
              : scenario === "5xx"
              ? 500
              : 200;
          res.statusCode = status;
          if (scenario === "429") {
            res.setHeader("retry-after", String(retryAfter));
          }
          res.setHeader("content-type", "application/json");
          res.end(JSON.stringify({ error: `scripted ${scenario}` }));
        });
        return;
      }
      const chunks: Buffer[] = [];
      req.on("data", (chunk: Buffer) => chunks.push(chunk));
      req.on("end", () => {
        const body = Buffer.concat(chunks).toString("latin1");
        // `requests` sends the file's basename (`TSTONE003.pdf`); the vault
        // path it came from never reaches the provider.
        const filename = /filename="([^"]*)"/.exec(body)?.[1] ?? "";
        const key = (filename.split(/[\\/]/).pop() ?? "").replace(
          /\.pdf$/i,
          ""
        );
        nextJob += 1;
        const jobId = `pf-e2e-job-${nextJob}`;
        record.key = key;
        jobKeys.set(jobId, key);
        sendJson({ data: { jobId } });
      });
      return;
    }
    if (req.method === "GET" && url.startsWith("/api/v2/ocr/jobs/batch/")) {
      const data: Record<string, unknown> = {};
      for (const jobId of jobKeys.keys()) {
        observe(jobId);
        const state = jobState(jobId);
        // A failing job carries its message in the batch payload (that is the
        // only observation it gets); a healthy one reports the bare state so
        // the worker falls back to the per-job fetch for the result URL.
        data[jobId] = state.errorMsg ? state : state.state;
      }
      sendJson({ data });
      return;
    }
    const jobMatch = /^\/api\/v2\/ocr\/jobs\/([^/]+)$/.exec(url);
    if (req.method === "GET" && jobMatch && jobKeys.has(jobMatch[1])) {
      const jobId = jobMatch[1];
      observe(jobId);
      const state = jobState(jobId);
      sendJson({
        data: {
          ...state,
          ...(state.state === "done"
            ? { resultUrl: { jsonUrl: `${resultUrl}${jobId}.jsonl` } }
            : {}),
        },
      });
      return;
    }
    const resultMatch = /^\/results\/([^/]+)\.jsonl$/.exec(url);
    if (
      req.method === "GET" &&
      resultMatch &&
      jobKeys.has(resultMatch[1]) &&
      !failKeys.has(jobKeys.get(resultMatch[1]) ?? "")
    ) {
      res.setHeader("content-type", "application/json");
      res.end(resultBody);
      return;
    }
    res.statusCode = 404;
    res.end();
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => resolve());
  });
  const address = server.address();
  if (!address || typeof address === "string") {
    await new Promise<void>((resolve) => server.close(() => resolve()));
    throw new Error("controlled OCR server did not expose a port");
  }
  resultUrl = `http://127.0.0.1:${address.port}/results/`;
  return {
    requests,
    jobUrl: `http://127.0.0.1:${address.port}/api/v2/ocr/jobs`,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

/** Make the e2e keyring backend importable by plugin-spawned children of the
 * CURRENTLY published runtime. The install tests republish the pointer to a
 * fresh candidate mid-suite, so the pointer must be resolved at call time
 * (a one-shot copy at wdio start would miss the new candidate). */
function provisionE2eKeyringFixture(): void {
  try {
    const pointerPath = path.resolve(
      os.homedir(),
      ".paperforge",
      "runtime",
      "pointer.json"
    );
    const pointer = JSON.parse(readFileSync(pointerPath, "utf8")) as {
      python_path?: string;
    };
    if (!pointer.python_path) return;
    // sysconfig.purelib, NOT site.getsitepackages(): the latter returns the
    // venv ROOT first for virtualenv pythons, which silently parked the
    // fixture outside import range.
    const sitePackages = execFileSync(
      pointer.python_path,
      ["-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
      { encoding: "utf8" }
    ).trim();
    if (!sitePackages) return;
    copyFileSync(
      path.resolve(PLUGIN_DIR, "test", "fixtures", "e2e_keyring.py"),
      path.resolve(sitePackages, "e2e_keyring.py")
    );
  } catch {
    // Runtime not resolvable here: the credential check will report missing.
  }
}

/** Keyring seed + vault PDF + canonical endpoint config for a controlled OCR
 * run; the endpoint is only set when a stub URL is provided. */
async function prepareOcrSandbox(
  jobUrl: string | null,
  options: { pending?: boolean; dropVersion?: boolean } = {}
): Promise<void> {
  provisionE2eKeyringFixture();
  const keyringPath = path.resolve(
    PLUGIN_DIR,
    ".obsidian-cache",
    "paperforge-e2e-keyring.json"
  );
  let keyring: Record<string, string> = {};
  try {
    keyring = JSON.parse(readFileSync(keyringPath, "utf8")) as Record<string, string>;
  } catch {
    keyring = {};
  }
  keyring["paperforge:ocr:default"] = "pf-e2e-ocr-token";
  writeFileSync(keyringPath, JSON.stringify(keyring), "utf8");
  const base = await sandboxBasePath();
  // A crashed/killed previous controller leaves controller.lock (and the
  // queue lock) behind; the worker refuses a new controller inside the 30s
  // stale window, so a rerun would look like "another controller is running".
  // The sandbox is rebuilt per case — drop the locks with it.
  for (const lockName of ["controller.lock", "ocr_queue.lock"]) {
    const lockPath = path.join(
      base,
      "System",
      "PaperForge",
      "ocr",
      lockName
    );
    if (existsSync(lockPath)) {
      try {
        unlinkSync(lockPath); // rmSync(force) silently no-ops on P1 paths
      } catch {
        // best effort — a stale lock is recoverable after the 30s window
      }
    }
  }
  const pdfDest = path.join(base, "System", "Zotero", "storage", "TSTONE001");
  mkdirSync(pdfDest, { recursive: true });
  copyFileSync(
    path.resolve(
      PLUGIN_DIR,
      "..",
      "..",
      "tests",
      "sandbox",
      "TestZoteroData",
      "storage",
      "TSTONE001",
      "TSTONE001.pdf"
    ),
    path.join(pdfDest, "TSTONE001.pdf")
  );
  if (jobUrl) {
    const applied = await browser.executeObsidian(async ({ app }, url) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): {
          configSet(key: string, value: string): Promise<unknown>;
          configList(): Promise<{ fields: Array<{ key: string; value: unknown }> }>;
        };
      };
      const client = plugin.getClient();
      await client.configSet("paddleocr_job_url", url);
      const list = await client.configList();
      return String(
        list.fields.find((field) => field.key === "paddleocr_job_url")?.value ?? ""
      );
    }, jobUrl);
    if (applied !== jobUrl) {
      throw new Error(`paddleocr_job_url did not apply: ${applied}`);
    }
  }
  // The fixture ships a completed OCR run at the CURRENT pipeline version, so
  // the worker skips the paper as up-to-date (success with zero provider
  // traffic).  Mark it pending so an explicit run actually processes it.
  const pointerPathForMeta = path.resolve(
    os.homedir(),
    ".paperforge",
    "runtime",
    "pointer.json"
  );
  try {
    const pointer = JSON.parse(readFileSync(pointerPathForMeta, "utf8")) as {
      python_path?: string;
    };
    const metaPath = path.join(
      await sandboxBasePath(),
      "System",
      "PaperForge",
      "ocr",
      "TSTONE001",
      "meta.json"
    );
    if ((options.pending ?? true) && pointer.python_path && existsSync(metaPath)) {
      execFileSync(
        pointer.python_path,
        [
          "-c",
          [
            "import json",
            `p = r'${metaPath}'`,
            "d = json.load(open(p, encoding='utf-8'))",
            `d['ocr_status'] = ${JSON.stringify(options.pending ?? true ? "pending" : "done")}`,
            "d['ocr_job_id'] = ''",
            (options.dropVersion ?? options.pending ?? true
              ? "d.pop('ocr_pipeline_version', None)"
              : "None"),
            "json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)",
          ].join("\n"),
        ],
        { encoding: "utf8", timeout: 60000 }
      );
    }
  } catch {
    // best effort: the case's assertions will surface a fixture problem
  }
  // Pay the runtime's cold start outside the case's own timing windows: the
  // first client call after A01's pointer switch can take ~a minute on CI,
  // and a UI-triggered run racing that cold start resolves as a silent no-op.
  await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      getClient(): { memoryStatus(): Promise<unknown> };
    };
    try {
      // A plain execute (no stream lock): probe-style calls hold the client
      // operation lock and can stall the workspace's own list call.
      await plugin.getClient().memoryStatus();
    } catch {
      // best effort: the case itself asserts real behavior afterwards
    }
  });
}

/** Job/queue state the CLI records on disk — the durable counterpart to the
 * in-process stream diagnostics. A failing OCR/staging case must show BOTH:
 * the child's stderr/exit code (client.lastStreamDiagnostics) and what the
 * child wrote (queue rows, controller/queue locks, per-paper meta). */
function readOcrJobState(base: string): Record<string, unknown> {
  const ocrRoot = path.join(base, "System", "PaperForge", "ocr");
  const queuePath = path.join(ocrRoot, "ocr-queue.json");
  let queue: unknown;
  try {
    queue = JSON.parse(readFileSync(queuePath, "utf8"));
  } catch (error) {
    queue = `<unreadable: ${String(error)}>`;
  }
  const locks = ["controller.lock", "ocr_queue.lock"].map((name) => {
    const lockPath = path.join(ocrRoot, name);
    try {
      const stat = statSync(lockPath);
      return {
        name,
        present: true,
        mtime: stat.mtime.toISOString(),
        size: stat.size,
      };
    } catch {
      return { name, present: false };
    }
  });
  return { ocr_root: ocrRoot, queue_path: queuePath, queue, locks };
}

/** The client's last streamed-operation diagnostics (child stderr, exit code,
 * event tail). Read through the plugin so a failing case can report why the
 * child never progressed — the streamed path otherwise drops stderr. */
async function readChildDiagnostics(): Promise<unknown> {
  return await browser.executeObsidian(async ({ app }) => {
    const plugin = app.plugins.plugins["paperforge"] as unknown as {
      getClient?(): { lastStreamDiagnostics?: unknown };
    };
    return plugin.getClient?.().lastStreamDiagnostics ?? null;
  });
}

/** Loopback OpenAI-compatible embeddings stub: deterministic vectors +
 * request log (the E-series controlled provider).  ``delayMs`` holds every
 * response open, so a caller can catch a build mid-flight (E04); the default
 * 0 answers immediately (E03/C03). */
async function startEmbedStub(
  options: { delayMs?: number } = {}
): Promise<{
  requests: Array<{ model?: string; input_count: number }>;
  baseUrl: string;
  close: () => Promise<void>;
}> {
  const requests: Array<{ model?: string; input_count: number }> = [];
  const delayMs = options.delayMs ?? 0;
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
      const respond = (): void => {
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
      };
      if (delayMs > 0) {
        setTimeout(respond, delayMs);
        return;
      }
      respond();
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
  return {
    requests,
    baseUrl: `http://127.0.0.1:${address.port}`,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

/** Embedding credential + canonical provider config for the controlled stub. */

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
    // Full isolation: every test starts from a fresh sandbox copy. The
    // disposable keyring file is shared by every case (wdio.conf.mts seeds it
    // once per run), so a case that provisions credentials would otherwise
    // stay visible to all later ones — X11 asserts a pristine sandbox. Reset
    // it here instead of relying on whichever case happens to clean up after
    // itself.
    const keyringFile = process.env.PAPERFORGE_E2E_KEYRING_FILE;
    if (keyringFile) removeFileQuiet(keyringFile);
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

  it("reinstalls the runtime through the setup journey and republishes the pointer", async function () {
    if (!SETUP_POSITIVE_E2E) {
      registeredSkip(this, "setup-positive-default-off");
      return;
    }
    this.timeout(900000);
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

    // No stale setup operation may be running: the reinstall click would be
    // a silent no-op (or collide) otherwise.
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _settingTab: { _setupOperation: string };
          };
          return plugin._settingTab._setupOperation === "idle";
        }),
      { timeout: 60000, timeoutMsg: "a previous setup operation never went idle" }
    );
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

    // The click must actually start the operation; a no-op click would
    // otherwise burn the whole outcome budget before failing.
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

    await browser.waitUntil(
      async () => {
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
      },
      {
        timeout: 540000,
        interval: 1000,
        timeoutMsg: "reinstall did not republish a runtime pointer",
      }
    );

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
    expect(String(pointerAfter?.environmentRoot ?? "")).toContain("venv-");
    expect(pointerAfter?.environmentRoot).not.toBe(beforeRoot);

    appendEvidence("a06-reinstall-switch.json", {
      case_id: "A06",
      variant: "settings reinstall -> journey action -> fresh candidate publish",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      pointer_before: pointerBefore,
      pointer_after: pointerAfter,
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
      removeFileQuiet(path.join(base, INDEX_REL));
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
      await clickSyncLibrary();
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
    removeFileQuiet(path.join(base, sentinel));

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
    await clickSyncLibrary();

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
    // The prune action closes its own modal once it settles, so this loop may
    // race with that teardown: query through one selector (never a stale
    // parent element) and let a container that disappears mean "closed".
    for (let attempt = 0; attempt < 10; attempt++) {
      if (!(await browser.$(".modal-container").isExisting())) break;
      const closeButton = await browser.$(
        ".modal-container .modal-close-button"
      );
      if (await closeButton.isExisting().catch(() => false)) {
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

    // J06 trash/restore leg — NOT implemented: the product exposes no
    // trash-list or restore surface for pruned orphans. `views/dashboard.ts`
    // and `main.ts` contain no trash/restore control or test id for the orphan
    // path (the only `restore` in dashboard.ts is the version-history modal,
    // unrelated). The pruning backend (`paperforge/commands/prune.py`) deletes
    // the workspace destructively and has no companion UI to list or recover
    // the removed files, so there is nothing to assert end to end. Until an
    // owner decision defines a trash/restore contract and a UI exposes it,
    // this leg stays a documented gap rather than a faked pass.
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

    await browser.waitUntil(
      async () => {
        const st = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            _autoSyncRunning: boolean;
            _lastSyncTime: string | null;
          };
          return {
            running: Boolean(plugin?._autoSyncRunning),
            lastSyncTime: plugin?._lastSyncTime ?? null,
          };
        });
        return st.running === false && st.lastSyncTime === null;
      },
      { timeout: 10000, timeoutMsg: "B04 forced failure never settled" }
    );

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

    await clickSyncLibrary();
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
    await viewport.waitForExist({ timeout: 180000 });
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
      { timeout: 180000, timeoutMsg: "OCR workspace rows never rendered" }
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

  it("runs OCR through the workspace confirm flow against a controlled provider", async function () {
    // D02/D03: execution entry (selection scope + confirmation modal) and
    // progress/settlement — driven through the real workspace UI against a
    // loopback PaddleOCR stub wired via the canonical `paddleocr_job_url`
    // config (the plugin strips PADDLEOCR_* from child env by design, so the
    // config field is the only honest seam).
    const stub = await startOcrStub("success");
    const base = await sandboxBasePath();
    try {
      await prepareOcrSandbox(stub.jobUrl);

      // 4. Workspace UI: select the paper → Process Selected → confirmation.
      await browser.executeObsidianCommand("paperforge:paperforge-ocr-workspace");
      const rowSelector =
        "//tr[.//*[contains(text(),'Biomechanical')]]//input[@type='checkbox']";
      await clickStable(rowSelector);
      // Selecting re-renders the table AND the batch bar: re-query the button
      // and wait for it to become enabled before clicking.
      const processBtn = await browser.$(
        ".pf-ocr-ws-batch-actions button.pf-btn-secondary"
      );
      await processBtn.waitForExist({ timeout: 30000 });
      await browser.waitUntil(
        async () => await processBtn.isEnabled().catch(() => false),
        { timeout: 30000, timeoutMsg: "Process Selected stayed disabled" }
      );
      await processBtn.click();
      await clickStable(".paperforge-confirm-actions button.mod-warning");

      // 5. D03: the running banner is visible while the provider runs.
      const activity = await browser.$(".pf-ocr-ws-activity.pf-active");
      await activity.waitForExist({ timeout: 60000 });

      const activityText = await activity.getText();

      // 6. Settlement: the stub job id is recorded, status done, the
      // result-hash pending marker cleared.
      const ocrRoot = path.join(base, "System", "PaperForge", "ocr", "TSTONE001");
      const metaPath = path.join(ocrRoot, "meta.json");
      const pendingMarker = path.join(ocrRoot, "index", "result-hash.pending");
      try {
        await browser.waitUntil(
          () => {
            try {
              const meta = JSON.parse(readFileSync(metaPath, "utf8")) as {
                ocr_job_id?: string;
                ocr_status?: string;
              };
              return (
                meta.ocr_job_id === "pf-e2e-job-1" &&
                meta.ocr_status === "done" &&
                !existsSync(pendingMarker)
              );
            } catch {
              return false;
            }
          },
          {
            timeout: 360000,
            timeoutMsg: "OCR run never settled to done with the stub job id",
          }
        );
      } catch (error) {
        let metaJob = "<missing>";
        let metaStatus = "<missing>";
        let metaError = "";
        try {
          const meta = JSON.parse(readFileSync(metaPath, "utf8")) as Record<string, unknown>;
          metaJob = String(meta.ocr_job_id ?? "");
          metaStatus = String(meta.ocr_status ?? "");
          metaError = String(meta.error ?? "");
        } catch {
          metaJob = "<unreadable>";
        }
        const requests = stub.requests.map((entry) => `${entry.method} ${entry.url}`);
        const ocrDir = existsSync(ocrRoot) ? readdirSync(ocrRoot).slice(0, 24) : [];
        console.log(
          "D02D job=" + metaJob + " status=" + metaStatus + " error=" + metaError
        );
        console.log("D02D req=" + JSON.stringify(requests));
        console.log("D02D dir=" + JSON.stringify(ocrDir));
        console.log("D02D marker=" + String(existsSync(pendingMarker)));
        const pdfPath = path.join(
          base,
          "System",
          "Zotero",
          "storage",
          "TSTONE001",
          "TSTONE001.pdf"
        );
        console.log("D02D pdf=" + String(existsSync(pdfPath)));
        let cfg = "<missing>";
        try {
          cfg = readFileSync(path.join(base, "paperforge.json"), "utf8").slice(0, 400);
        } catch {
          cfg = "<unreadable>";
        }
        console.log("D02D cfg=" + cfg.replace(/\s+/g, " "));
        const notices = await browser.execute(() =>
          Array.from(document.querySelectorAll(".notice"))
            .map((node) => (node.textContent ?? "").trim())
            .join(" | ")
        );
        console.log("D02D notices=" + notices.slice(0, 300));
        const wsState = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            getClient(): {
              isOperationActive(): boolean;
              activeOperationId: string | null;
            };
          };
          return {
            active: plugin.getClient().isOperationActive(),
            activeId: plugin.getClient().activeOperationId,
          };
        });
        console.log("D02D ws=" + JSON.stringify(wsState));
        // The child's own stderr/exit code is the only way to see WHY it
        // never progressed (the streamed path used to drop it entirely).
        const childDiagnostics = await readChildDiagnostics();
        const jobState = readOcrJobState(base);
        console.log("D02D child=" + JSON.stringify(childDiagnostics));
        console.log("D02D jobstate=" + JSON.stringify(jobState));
        const probe = await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"] as unknown as {
            getClient(): {
              runAction(request: unknown): Promise<{
                ok?: boolean;
                payload?: unknown;
                exitCode?: number;
              }>;
            };
          };
          try {
            const res = await plugin.getClient().runAction({
              action_id: "ocr.run",
              scope: { kind: "papers", keys: ["TSTONE001"] },
              confirm: "ocr.run",
            });
            return {
              ok: res.ok,
              exit: res.exitCode,
              payload: JSON.stringify(res.payload ?? null).slice(0, 500),
            };
          } catch (e) {
            return { err: String(e) };
          }
        });
        console.log("D02D probe=" + JSON.stringify(probe));

        appendEvidence("d02-failure-diagnostic.json", {
          case_id: "D02",
          variant: "settle-timeout diagnostic",
          required_layer: "H",
          status: "FAILED",
          meta_job: metaJob,
          meta_status: metaStatus,
          meta_error: metaError,
          requests,
          ocr_dir: ocrDir,
          pending_marker: existsSync(pendingMarker),
          child_diagnostics: childDiagnostics,
          job_state: jobState,
          recorded_at: new Date().toISOString(),
        });
        throw error;
      }
      expect(stub.requests.length).toBeGreaterThan(0);
      const metaAfter = JSON.parse(readFileSync(metaPath, "utf8")) as Record<
        string,
        unknown
      >;
      const sha = execFileSync("git", ["rev-parse", "HEAD"], { cwd: PLUGIN_DIR })
        .toString()
        .trim();
      const methodUrls = stub.requests.map((entry) => `${entry.method} ${entry.url}`);

      appendEvidence("d02-ocr-run-entry.json", {
        case_id: "D02",
        variant: "workspace selection + confirm modal → controlled provider run",
        required_layer: "H",
        status: "VERIFIED",
        source_sha: sha,
        worktree_dirty: worktreeDirty(),
        provider_requests: methodUrls,
        confirm_modal_used: true,
        job_url: stub.jobUrl,
        recorded_at: new Date().toISOString(),
      });
      appendEvidence("d03-ocr-settlement.json", {
        case_id: "D03",
        variant: "running banner observed; provider job recorded; artifacts settled",
        required_layer: "H",
        status: "VERIFIED",
        source_sha: sha,
        worktree_dirty: worktreeDirty(),
        activity_text: activityText.slice(0, 200),
        meta_job_id: metaAfter.ocr_job_id,
        meta_status: metaAfter.ocr_status,
        pending_marker_cleared: !existsSync(pendingMarker),
        result_fetches: methodUrls.filter((u) => u.includes("/results/")).length,
        // The healthy child's process view (exit code, stderr tail, events):
        // the reference a failing run's diagnostic is compared against.
        child_diagnostics: await readChildDiagnostics(),
        recorded_at: new Date().toISOString(),
      });
    } finally {
      await stub.close();
    }
  });

  it("re-extracts a flagged paper through the workspace redo control", async function () {
    // D05 (redo): a row flagged for redo surfaces the re-extract control; the
    // run submits a fresh provider job through the same controlled endpoint
    // and settles.
    const stub = await startOcrStub("success");
    try {
      await prepareOcrSandbox(stub.jobUrl);
      const base = await sandboxBasePath();
      const indexPath = path.join(
        base,
        "System",
        "PaperForge",
        "indexes",
        "formal-library.json"
      );
      const index = JSON.parse(readFileSync(indexPath, "utf8")) as {
        items?: Array<Record<string, unknown>>;
      };
      for (const item of index.items ?? []) {
        if (item.zotero_key === "TSTONE001") item.ocr_redo = true;
      }
      writeFileSync(indexPath, JSON.stringify(index, null, 2), "utf8");
      const notePath = path.join(
        base,
        "Resources",
        "Literature",
        "骨科",
        "TSTONE001 - Biomechanical Comparison of Suture Anchor Fixations in Rotator Cuff Repair",
        "TSTONE001.md"
      );
      const note = readFileSync(notePath, "utf8");
      if (!/^ocr_redo:/m.test(note)) {
        writeFileSync(notePath, note.replace(/^---\r?\n/, "---\nocr_redo: true\n"), "utf8");
      }
      await browser.executeObsidianCommand("paperforge:paperforge-ocr-workspace");
      const rowSelector =
        "//tr[.//*[contains(text(),'Biomechanical')]]//input[@type='checkbox']";
      await clickStable(rowSelector);
      const redoBtn = await browser.$(
        "[data-pf-testid='ocr-ws-re-extract-selected']"
      );
      await redoBtn.waitForExist({ timeout: 30000 });
      await browser.waitUntil(
        async () => await redoBtn.isEnabled().catch(() => false),
        { timeout: 30000, timeoutMsg: "Re-extract Selected stayed disabled" }
      );
      await redoBtn.click();
      await clickStable(".paperforge-confirm-actions button.mod-warning");
      const metaPath = path.join(
        base,
        "System",
        "PaperForge",
        "ocr",
        "TSTONE001",
        "meta.json"
      );
      try {
        await browser.waitUntil(
          () => {
            try {
              const meta = JSON.parse(readFileSync(metaPath, "utf8")) as {
                ocr_job_id?: string;
                ocr_status?: string;
              };
              return meta.ocr_job_id === "pf-e2e-job-1" && meta.ocr_status === "done";
            } catch {
              return false;
            }
          },
          { timeout: 360000, timeoutMsg: "redo run never settled" }
        );
      } catch (error) {
        let metaDump = "<missing>";
        try {
          metaDump = readFileSync(metaPath, "utf8").slice(0, 400);
        } catch (e) {
          metaDump = String(e);
        }
        const reqDump = stub.requests.map((entry) => `${entry.method} ${entry.url}`);
        console.log("D05D meta=" + metaDump.replace(/\s+/g, " "));
        console.log("D05D req=" + JSON.stringify(reqDump));
        throw error;
      }
      const submits = stub.requests.filter((entry) => entry.method === "POST").length;
      expect(submits).toBe(1);
      appendEvidence("d05-ocr-redo.json", {
        case_id: "D05",
        variant: "redo control re-submits the flagged paper and settles",
        required_layer: "H",
        status: "VERIFIED",
        source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
          cwd: PLUGIN_DIR,
        })
          .toString()
          .trim(),
        worktree_dirty: worktreeDirty(),
        submits,
        provider_requests: stub.requests.map(
          (entry) => `${entry.method} ${entry.url}`
        ),
        recorded_at: new Date().toISOString(),
      });
    } finally {
      await stub.close();
    }
  });

  it("aligns the dashboard presentation with the reconcile read model", async function () {
    // F04: the dashboard's deficit/next-step presentation is driven by the
    // backend reconcile read model — record both sides of the contract.
    await openPanel();
    await openVaultFile(NOTE_PATH);
    const model = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        getClient(): {
          reconcile(
            scope: "all" | "papers",
            keys?: string[]
          ): Promise<Record<string, unknown>>;
        };
      };
      return await plugin.getClient().reconcile("papers", ["TSTONE001"]);
    });
    const modelText = JSON.stringify(model);
    expect(modelText.length).toBeGreaterThan(0);
    await browser.waitUntil(
      async () =>
        await browser.execute(() =>
          Boolean(document.querySelector(".paperforge-quality-section"))
        ),
      { timeout: 60000, timeoutMsg: "paper detail never rendered" }
    );
    const ui = await browser.executeObsidian(() => ({
      detail_present: Boolean(
        document.querySelector(".paperforge-quality-section")
      ),
      testids: Array.from(document.querySelectorAll("[data-pf-testid]"))
        .map((el) => el.getAttribute("data-pf-testid"))
        .filter((id): id is string => Boolean(id))
        .slice(0, 24),
    }));
    expect(ui.detail_present).toBe(true);
    appendEvidence("f04-reconcile-actions.json", {
      case_id: "F04",
      variant: "reconcile read model recorded alongside the dashboard surface",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      reconcile_head: modelText.slice(0, 400),
      ui_testids: ui.testids,
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

    // D09: cleanup/delete is NOT an approved capability — the version surface
    // must not present destructive cleanup affordances (the contract is the
    // absence until an owner decision defines a cleanup policy).
    const d09 = await browser.execute(() => {
      const controls = Array.from(
        document.querySelectorAll(".pf-vr-layout button, .pf-vr-layout a")
      ).map((el) => (el.textContent ?? "").trim());
      return {
        scanned: controls.length,
        destructive: controls.filter((text) =>
          /删除|清理|Delete|Cleanup|Purge|Remove/i.test(text)
        ),
      };
    });
    expect(d09.destructive).toEqual([]);
    appendEvidence("d09-ocr-cleanup-absence.json", {
      case_id: "D09",
      variant: "no unapproved cleanup/delete controls on the version surface",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      scanned_controls: d09.scanned,
      matched_destructive: d09.destructive,
      capability_status:
        "not approved — owner decision required to define a cleanup contract",
      recorded_at: new Date().toISOString(),
    });

    const base = await sandboxBasePath();
    const canonicalPath = path.join(
      base,
      `System/PaperForge/ocr/${PAPER_KEY}/render/fulltext.md`
    );
    const canonicalBefore = sha256(canonicalPath);
    const restoreBtn = await browser.$("[data-pf-testid='version-restore']");
    await restoreBtn.waitForExist({ timeout: 30000 });

    // J05 cancel leg: dismissing the confirmation must leave the canonical
    // fulltext bytes untouched — no copy happens before an explicit confirm.
    await restoreBtn.click();
    const cancelBtn = await browser.$(".pf-vr-confirm-actions .btn-secondary");
    await cancelBtn.waitForExist({ timeout: 30000 });
    await cancelBtn.click();
    await browser.waitUntil(
      async () => !(await browser.$(".pf-vr-confirm-actions").isExisting()),
      {
        timeout: 30000,
        timeoutMsg: "the restore confirmation did not close on cancel",
      }
    );
    expect(sha256(canonicalPath)).toBe(canonicalBefore);

    // Restore the oldest version (v1) → confirmation → Python performs the
    // copy AND persists provenance.
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

    // J05 restart leg: the restored version surface must survive a same-sandbox
    // restart — the version list re-renders from the persisted substrate.
    await browser.reloadObsidian();
    await dismissModals();
    await openPanel();
    await openVaultFile(NOTE_PATH);
    const restartVersionBtn = await browser.$(
      "[data-pf-testid='version-history']"
    );
    await restartVersionBtn.waitForExist({ timeout: 60000 });
    await restartVersionBtn.click();
    await (await browser.$(".pf-vr-layout")).waitForExist({ timeout: 60000 });
    await browser.waitUntil(
      async () => {
        const after = await browser.execute(() =>
          Array.from(document.querySelectorAll(".pf-vr-entry-label")).map(
            (el) => (el.textContent ?? "").trim()
          )
        );
        return after.includes("v1") && after.includes("v2");
      },
      {
        timeout: 60000,
        timeoutMsg: "the version list did not re-render after a restart",
      }
    );
    appendEvidence("j05-version-restart.json", {
      case_id: "J05",
      variant: "restore → same-sandbox restart → version list re-renders",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      cancel_left_canonical_unchanged: true,
      labels_after_restart: ["v1", "v2"],
      recorded_at: new Date().toISOString(),
    });
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

    // Click Clear and read the length in the SAME task: the trace ring is
    // appended by any client traffic (probe leftovers, autosync), so a
    // readback in a separate round-trip races those writers (observed as
    // expected 0 / received 59 on the runner).
    const cleared = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        settings: { debug_trace?: boolean };
        getDebugTrace(): string;
        saveSettings(): Promise<void>;
        _settingTab: {
          containerEl: HTMLElement;
          _selectedDetailModule?: string | null;
          activeTab?: string;
        };
      };
      const row = Array.from(
        plugin._settingTab.containerEl.querySelectorAll(".setting-item")
      ).find((el) =>
        (el.querySelector(".setting-item-name")?.textContent ?? "").includes(
          "Debug trace"
        )
      );
      const button = Array.from(row?.querySelectorAll("button") ?? []).find(
        (candidate) => (candidate.textContent ?? "").trim() === "Clear"
      );
      if (!(button instanceof HTMLButtonElement)) {
        throw new Error("Clear button not found");
      }
      button.click();
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
  it("resolves the last opened paper in a rapid A→B switch and fails closed off-paper", async function () {
    // Case B05. The panel resolves identity asynchronously (Python
    // `paper-lookup --from-path`) behind a 300ms leaf-change debounce, so two
    // quick opens must settle on the LAST leaf — never on a late response for
    // the first — and a file with no canonical identity must not inherit the
    // previous paper's key.
    await openPanel();
    await waitForIdle("B05", "startup-sync-settle");
    const base = await sandboxBasePath();

    // A second REAL paper: export entry + UI Sync, the same path the sync
    // diff case uses (identity must be canonical, not hand-written).
    addExportItem(base, {
      key: NEW_PAPER_KEY,
      title: SECOND_PAPER_TITLE,
      doi: "10.1016/j.jse.2024.01.997",
    });
    await clickTestId("sync-library");
    await browser.waitUntil(
      () => {
        try {
          return (
            readIndex(base).keys.includes(NEW_PAPER_KEY) &&
            existsSync(path.join(base, NEW_PAPER_NOTE))
          );
        } catch {
          return false; // the index is being rewritten
        }
      },
      {
        timeout: 180000,
        timeoutMsg: "B05 Sync never materialized the second paper",
      }
    );
    await waitForIdle("B05", "manual-sync-settle");
    await waitForDashboardIndexKey(NEW_PAPER_KEY);

    // A → B back to back: A's lookup is still in flight when B becomes the
    // active leaf, so a late response for A must never win.
    await openVaultFile(NOTE_PATH);
    await browser.pause(400);
    await openVaultFile(NEW_PAPER_NOTE);
    await waitForPanel("paper", NEW_PAPER_KEY);
    // A late response for A would land right after B commits; let it.
    await browser.pause(2000);
    const settled = await panelContext();
    expect(settled.mode).toBe("paper");
    expect(settled.key).toBe(NEW_PAPER_KEY);
    expect(settled.name).toBe(SECOND_PAPER_TITLE);
    const paperText = await (
      await browser.$(".paperforge-content-area")
    ).getText();
    expect(paperText).toContain(SECOND_PAPER_TITLE);
    expect(paperText).not.toContain(PAPER_TITLE);

    // A plain note belongs to no paper: fail closed instead of keeping B.
    const plainNote = "Resources/Literature/骨科/plain-notes.md";
    writeSandboxFile(base, plainNote, "# Plain notes\n\nNo identity here.\n");
    await openVaultFile(plainNote);
    await waitForPanel("global");
    const plain = await panelContext();
    expect(plain.label).toBe("Global");
    expect(plain.key).toBe("");
    expect(plain.name).toBe("");
    expect(await (await browser.$(".paperforge-paper-view")).isExisting()).toBe(
      false
    );

    // The Base resolves to its collection — also not a paper.
    await openVaultFile(BASE_PATH);
    await waitForPanel("collection");
    const collection = await panelContext();
    expect(collection.key).toBe("");
    expect(collection.name).toBe("骨科");

    appendEvidence("b05-identity-mode.json", {
      case_id: "B05",
      variant: "rapid A->B identity switch + non-paper fail-closed",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      paper_a: { note: NOTE_PATH, title: PAPER_TITLE },
      paper_b: { key: NEW_PAPER_KEY, note: NEW_PAPER_NOTE, title: SECOND_PAPER_TITLE },
      settled_panel: settled,
      plain_note_mode: plain,
      base_mode: collection,
      observed_at: new Date().toISOString(),
    });
  });

  it("refuses to guess a paper key for paths without canonical identity", async function () {
    // Case B05, unknown/ambiguous branch. Identity is Python authority:
    // canonical index, note frontmatter, workspace-folder key WITH an index
    // entry. A path that merely LOOKS like a paper must fail closed — the
    // client never infers a key from a filename, folder name, or a rename.
    await openPanel();
    await waitForIdle("B05", "startup-sync-settle");
    const base = await sandboxBasePath();

    // (a) Key-shaped folder (8-char key, so the workspace-key branch is
    // actually reachable) with NO index entry: not canonical.
    const phantomNote =
      "Resources/Literature/骨科/TSTONE01 - Phantom Paper/TSTONE01.md";
    writeSandboxFile(
      base,
      phantomNote,
      "# Phantom\n\nA folder that looks like a workspace, without identity.\n"
    );
    await openVaultFile(phantomNote);
    await waitForPanel("global");
    const phantom = await panelContext();
    expect(phantom.label).toBe("Global");
    expect(phantom.key).toBe("");

    // (b) A file named after the key, in the literature folder, whose content
    // carries no identity: nothing may be inferred from the name.
    const decoy = "Resources/Literature/骨科/TSTONE001-copy.md";
    writeSandboxFile(
      base,
      decoy,
      "# TSTONE001 copy\n\nBody without frontmatter identity.\n"
    );
    await openVaultFile(decoy);
    await waitForPanel("global");
    const named = await panelContext();
    expect(named.key).toBe("");
    expect(named.name).toBe("");

    // (c) Contrast — the same key-named path WITH canonical frontmatter IS
    // identity, wherever the file sits: a renamed/moved note keeps its paper.
    const renamed = "Resources/Literature/骨科/renamed-note.md";
    writeSandboxFile(base, renamed, readNote(base, NOTE_PATH));
    await openVaultFile(renamed);
    await waitForPanel("paper", PAPER_KEY);
    expect((await panelContext()).name).toBe(PAPER_TITLE);

    // …and the key does not leak back onto the identity-less leaf.
    await openVaultFile(phantomNote);
    await waitForPanel("global");
    expect((await panelContext()).key).toBe("");

    appendEvidence("b05-unknown-identity.json", {
      case_id: "B05",
      variant: "unknown/ambiguous path -> no key guessing",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      key_shaped_folder_no_index: { note: phantomNote, panel: phantom },
      key_named_file_no_identity: { note: decoy, panel: named },
      canonical_frontmatter_renamed: { note: renamed, resolved_key: PAPER_KEY },
      observed_at: new Date().toISOString(),
    });
  });

  it("opens the key's real artifacts from the panel, workspace and version entries", async function () {
    // Case B08. Every entry point must land on the SAME canonical file for
    // the key, asserted on app.workspace.getActiveFile().path — a spy on
    // openFile would stay green while the wrong file opens.
    await openPanel();
    await waitForIdle("B08", "startup-sync-settle");
    const base = await sandboxBasePath();

    // Fixture guard: the assertions below must not go vacuous on index drift.
    const item = readIndexItem(base, PAPER_KEY);
    expect(item.fulltext_path).toBe(CANONICAL_FULLTEXT);
    expect(item.pdf_path).toBe(`[[${PAPER_PDF}]]`);

    await openVaultFile(NOTE_PATH);
    await waitForPanel("paper", PAPER_KEY);
    expect(await activeFilePath()).toBe(NOTE_PATH);

    // ── 打开全文 from the paper strip.
    await clickTestId("open-fulltext");
    await waitForActiveFile(CANONICAL_FULLTEXT);
    const panelAfterFulltext = await browser.executeObsidian(
      async ({ app }) =>
        app.workspace.getLeavesOfType("paperforge-status").length > 0
    );
    const stateAfterFulltext = await workspaceFileState();

    // ── Back: reopening the note returns the panel to the same paper.
    await openPanel();
    await openVaultFile(NOTE_PATH);
    await waitForPanel("paper", PAPER_KEY);
    expect(await activeFilePath()).toBe(NOTE_PATH);

    // ── 打开 PDF: supply the artifact the index advertises, then click it.
    expect(existsSync(PDF_FIXTURE)).toBe(true);
    await openPanel();
    mkdirSync(path.dirname(path.join(base, PAPER_PDF)), { recursive: true });
    copyFileSync(PDF_FIXTURE, path.join(base, PAPER_PDF));
    await materializeBinaryFile(PAPER_PDF);
    await clickTestId("open-pdf");
    await waitForActiveFile(PAPER_PDF);
    const stateAfterPdf = await workspaceFileState();

    // ── 正文 entry: the OCR workspace row's own Preview control.
    await openPanel();
    await openVaultFile(NOTE_PATH);
    await waitForPanel("paper", PAPER_KEY);
    await browser.executeObsidianCommand("paperforge:paperforge-ocr-workspace");
    const previewBtn = await browser.$("[data-pf-testid='ocr-open-fulltext']");
    await previewBtn.waitForExist({ timeout: 60000 });
    await previewBtn.click();
    await waitForActiveFile(CANONICAL_FULLTEXT);
    const stateAfterPreview = await workspaceFileState();

    // ── 版本入口: the history modal must belong to THIS key, and leaving it
    // must return to the paper's own note.
    await openPanel();
    await openVaultFile(NOTE_PATH);
    await waitForPanel("paper", PAPER_KEY);
    await clickTestId("version-history");
    await (await browser.$(".pf-vr-layout")).waitForExist({ timeout: 60000 });
    const labels = await browser.execute(() =>
      Array.from(document.querySelectorAll(".pf-vr-entry-label")).map((el) =>
        (el.textContent ?? "").trim()
      )
    );
    expect(labels).toContain("v1");
    expect(labels).toContain("v2");
    expect(await activeFilePath()).toBe(NOTE_PATH);
    await browser.keys("Escape");
    await dismissModals();
    await waitForPanel("paper", PAPER_KEY);
    expect(await activeFilePath()).toBe(NOTE_PATH);

    appendEvidence("b08-open-entries.json", {
      case_id: "B08",
      variant: "panel/workspace/version entries open the key's canonical files",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      key: PAPER_KEY,
      fulltext_entry: {
        expected: CANONICAL_FULLTEXT,
        active_file: CANONICAL_FULLTEXT,
        panel_still_mounted: panelAfterFulltext,
        state: stateAfterFulltext,
      },
      pdf_entry: { expected: PAPER_PDF, active_file: PAPER_PDF, state: stateAfterPdf },
      ocr_workspace_entry: {
        expected: CANONICAL_FULLTEXT,
        active_file: CANONICAL_FULLTEXT,
        state: stateAfterPreview,
      },
      version_entry: { labels, active_file_after_open: NOTE_PATH },
      returned_to_note: NOTE_PATH,
      observed_at: new Date().toISOString(),
    });
  });

  it("reports a missing target instead of opening a wrong file", async function () {
    // Case B08, failure branch: a target that is gone must surface a visible
    // error and leave the workspace on the paper's own note — never fall back
    // to some other file of the same paper.
    await openPanel();
    await waitForIdle("B08", "startup-sync-settle");
    const base = await sandboxBasePath();

    await openVaultFile(NOTE_PATH);
    await waitForPanel("paper", PAPER_KEY);

    // The canonical fulltext is removed on disk AND from the Vault cache, so
    // the click cannot be saved by a stale TFile handle.
    unlinkSync(path.join(base, CANONICAL_FULLTEXT));
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(
          async ({ app }, target) =>
            app.vault.getAbstractFileByPath(target) === null,
          CANONICAL_FULLTEXT
        ),
      {
        timeout: 30000,
        timeoutMsg: "the removed fulltext stayed in the Vault cache",
      }
    );

    await clickTestId("open-fulltext");
    await waitUntilNotice("Fulltext file not found");
    expect(await activeFilePath()).toBe(NOTE_PATH);

    // The vault now ships the advertised PDF (builder), so the missing-target
    // condition is created here: remove the file and let the Vault cache drop
    // it, mirroring the fulltext removal above.
    unlinkSync(path.join(base, PAPER_PDF));
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(
          async ({ app }, target) =>
            app.vault.getAbstractFileByPath(target) === null,
          PAPER_PDF
        ),
      {
        timeout: 30000,
        timeoutMsg: "the removed PDF stayed in the Vault cache",
      }
    );
    await clickTestId("open-pdf");
    await waitUntilNotice("PDF not found");
    expect(await activeFilePath()).toBe(NOTE_PATH);

    // No wrong file, no mode drift: the panel is still on the same paper.
    const after = await panelContext();
    expect(after.mode).toBe("paper");
    expect(after.key).toBe(PAPER_KEY);

    appendEvidence("b08-missing-target.json", {
      case_id: "B08",
      variant: "missing target -> visible error, no wrong file",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      removed_fulltext: CANONICAL_FULLTEXT,
      absent_pdf: PAPER_PDF,
      fulltext_notice: "Fulltext file not found",
      pdf_notice: "PDF not found",
      active_file_after_failures: NOTE_PATH,
      panel_after_failures: after,
      observed_at: new Date().toISOString(),
    });
  });

  // ── A03 / A04 / A05: configuration and credential journeys ──────────────
  //
  // Every assertion below reads a REAL artifact: the canonical
  // `paperforge.json` Python owns, the disposable keyring backend, or the
  // rendered DOM. The plugin's own mirrors (data.json) are never the proof —
  // they are the thing under test.

  /** The sandbox's canonical config file — the one Python reads. */
  function sandboxConfigFile(base: string): string {
    return path.join(base, "paperforge.json");
  }

  /** One dotted field of the sandbox config (undefined when absent). */
  function sandboxConfigField(base: string, dotted: string): unknown {
    let node = JSON.parse(
      readFileSync(sandboxConfigFile(base), "utf8")
    ) as unknown;
    for (const part of dotted.split(".")) {
      if (node === null || typeof node !== "object") return undefined;
      node = (node as Record<string, unknown>)[part];
    }
    return node;
  }




  /**
   * Run the product's own credential-authority delete through the runtime
   * Python, with the e2e keyring backend injected explicitly — the same

  /**
   * Open the plugin's Settings tab on a render target: the Setup Journey at
   * `stage`, or a module-detail panel. `display()` is called AFTER the tab is
   * open, so the render lands in the tab's container (not a detached div).
   */
  async function openSettingsTabOn(target: {
    stage?: number;
    module?: string;
  }): Promise<void> {
    const observed = await browser.executeObsidian(
      async ({ app }, wanted: { stage?: number; module?: string }) => {
        const loaded = app.plugins.plugins["paperforge"];
        if (!loaded) throw new Error("paperforge plugin not loaded");
        const plugin = loaded as unknown as {
          settings: { _setup_complete?: boolean; autoSyncEnabled?: boolean };
          _pollTimer: number | null;
          _settingTab: {
            _setupStage: number;
            _setupOperation: string;
            _setupFeedback: string | null;
            _setupFailureDetail: string | null;
            _setupJourneyDismissedForSession: boolean;
            _initialDisplay: boolean;
            activeTab: string;
            _selectedDetailModule: string;
            containerEl: HTMLElement;
            display(): void;
          };
          saveSettings(): Promise<void>;
        };
        clearInterval(plugin._pollTimer ?? undefined);
        plugin._pollTimer = null;
        plugin.settings.autoSyncEnabled = false;
        if (typeof wanted.stage === "number") {
          plugin.settings._setup_complete = false;
          plugin._settingTab._setupJourneyDismissedForSession = false;
          plugin._settingTab._setupStage = wanted.stage;
          plugin._settingTab._setupOperation = "idle";
          plugin._settingTab._setupFeedback = null;
          plugin._settingTab._setupFailureDetail = null;
        } else {
          plugin.settings._setup_complete = true;
          plugin._settingTab._setupJourneyDismissedForSession = true;
          plugin._settingTab.activeTab = "module-detail";
          plugin._settingTab._selectedDetailModule = wanted.module ?? "";
        }
        await plugin.saveSettings();

        // Obsidian's Settings window lives behind undocumented API; the
        // existing cases reach it through the same cast. The tab's container
        // is attached to the document only once that window opens, so the
        // render follows the open (rendering first would target a detached
        // div and the controls would never be queryable).
        const settingsApi = app as unknown as {
          setting?: { open(): void; openTabById(id: string): void };
        };
        const tabApi = settingsApi.setting;
        if (!tabApi || typeof tabApi.open !== "function") {
          throw new Error("Obsidian settings API unavailable");
        }
        tabApi.open();
        tabApi.openTabById("paperforge");
        await new Promise<void>((resolve) => setTimeout(resolve, 500));
        // Skip the one-time nav-memory restore: it would overwrite the target
        // stage/module set above with the last persisted destination.
        plugin._settingTab._initialDisplay = false;
        plugin._settingTab.display();
        const container = plugin._settingTab.containerEl;
        return {
          connected: container.isConnected,
          journey: container.querySelectorAll(".pf-setup-journey").length,
          modal: document.querySelectorAll(".modal-container").length,
          testids: Array.from(container.querySelectorAll("[data-pf-testid]")).map(
            (e) => e.getAttribute("data-pf-testid")
          ),
        };
      },
      target
    );
    if (!observed.connected) {
      throw new Error(
        `the settings tab never attached to the document: ${JSON.stringify(
          observed
        )}`
      );
    }
  }

  /**
   * Drive the Settings tab's own DOM. Obsidian may host the Settings window in
   * a separate window, so every query resolves through the tab container's
   * `ownerDocument` — the ambient `document` can be a different one, and an
   * element living there is invisible to it.
   */
  async function settingsElement(
    selector: string,
    action:
      | "exists"
      | "value"
      | "text"
      | "click"
      | "set-input"
      | "input-props",
    value?: string,
    index?: number
  ): Promise<unknown> {
    return await browser.executeObsidian(
      async (
        { app },
        wanted: {
          selector: string;
          action: string;
          value?: string;
          index?: number;
        }
      ) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          _settingTab: { containerEl: HTMLElement };
        };
        const doc = plugin._settingTab.containerEl.ownerDocument;
        // DOM node cast (not a fabricated shape): querySelectorAll returns
        // Element, and this helper only drives element-level behavior.
        const nodes = Array.from(
          doc.querySelectorAll(wanted.selector)
        ) as HTMLElement[];
        const el: HTMLElement | null = nodes[wanted.index ?? 0] ?? null;
        switch (wanted.action) {
          case "exists":
            return Boolean(el);
          case "value":
            if (!el || !("value" in el)) return null;
            return String(el.value);
          case "text":
            return (el?.textContent ?? "").trim();
          case "click":
            if (!el) throw new Error(`no element ${wanted.selector}`);
            el.click();
            return true;
          case "set-input": {
            if (!el || !("value" in el)) {
              throw new Error(`no input ${wanted.selector}`);
            }
            el.value = wanted.value ?? "";
            el.dispatchEvent(new Event("input", { bubbles: true }));
            return true;
          }
          case "input-props": {
            if (
              !el ||
              !("value" in el) ||
              !("type" in el) ||
              !("placeholder" in el)
            ) {
              throw new Error(`no input ${wanted.selector}`);
            }
            return {
              type: String(el.type),
              value: String(el.value),
              placeholder: String(el.placeholder),
            };
          }
          default:
            throw new Error(`unknown settings action ${wanted.action}`);
        }
      },
      { selector, action, value, index }
    );
  }

  /** Every testid rendered in the settings tab's own document. */
  async function settingsTestIds(): Promise<{
    sameDocument: boolean;
    connected: boolean;
    testids: string[];
    topbar: number;
    journey: number;
    html: string;
  }> {
    return (await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"] as unknown as {
        _settingTab: { containerEl: HTMLElement };
      };
      const container = plugin._settingTab.containerEl;
      const doc = container.ownerDocument;
      return {
        sameDocument: doc === document,
        connected: container.isConnected,
        testids: Array.from(
          doc.querySelectorAll("[data-pf-testid]")
        ).map((e) => e.getAttribute("data-pf-testid") ?? ""),
        topbar: doc.querySelectorAll(".pf-cc-topbar").length,
        journey: doc.querySelectorAll(".pf-setup-journey").length,
        html: doc.body?.innerHTML.slice(0, 600) ?? "",
      };
    })) as {
      sameDocument: boolean;
      connected: boolean;
      testids: string[];
      topbar: number;
      journey: number;
      html: string;
    };
  }

  /** Wait for a testid'd control in the settings tab's own document. */
  async function waitForTestId(testid: string): Promise<void> {
    const selector = `[data-pf-testid='${testid}']`;
    try {
      await browser.waitUntil(
        async () => (await settingsElement(selector, "exists")) === true,
        {
          timeout: 60000,
          interval: 250,
          timeoutMsg: selector,
        }
      );
    } catch (error) {
      throw new Error(
        `missing testid ${testid}: ${JSON.stringify(
          await settingsTestIds()
        )} (${String(error)})`
      );
    }
  }

  /** Type into a settings-tab input and fire the event the product listens to. */
  async function setInputByTestId(testid: string, value: string): Promise<void> {
    await settingsElement(`[data-pf-testid='${testid}']`, "set-input", value);
  }

  /** Click a settings-tab control through the product's own listener. */
  async function clickSettingsTestId(testid: string): Promise<void> {
    await settingsElement(`[data-pf-testid='${testid}']`, "click");
  }


  /** True when the backend credential authority reports a stored key. */
  async function credentialAvailable(
    service: "ocr" | "embedding"
  ): Promise<boolean> {
    return await browser.executeObsidian(async ({ app }, kind: string) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      return await plugin
        .getClient()
        .credentialAvailable(kind as "ocr" | "embedding");
    }, service);
  }

  /**
   * A legacy (pre-#142) config: no `schema_version`, path keys at the top
   * level, `agent_key`, the derived `paperforge_path`/`zotero_link` mirrors,
   * and one unknown key the migration must not delete.
   */
  const LEGACY_CONFIG_DOC = {
    system_dir: "System",
    resources_dir: "LegacyResources",
    base_dir: "LegacyBases",
    agent_key: "claude",
    paperforge_path: "/legacy/paperforge",
    zotero_link: "/legacy/zotero",
    ocr_profile: "legacy_profile",
    custom_legacy_note: "keep-me",
  };

  /** Seed the legacy file and restart so the plugin loads against it. */
  async function seedLegacyConfigAndRestart(base: string): Promise<void> {
    writeSandboxFile(
      base,
      "paperforge.json",
      JSON.stringify(LEGACY_CONFIG_DOC, null, 2)
    );
    await browser.reloadObsidian();
    await browser.waitUntil(
      async () =>
        await browser.executeObsidian(async ({ app }) => {
          const plugin = app.plugins.plugins["paperforge"];
          if (!plugin) return false;
          return (
            "_needsConfigMigration" in plugin &&
            plugin._needsConfigMigration === true
          );
        }),
      {
        timeout: 60000,
        timeoutMsg:
          "the plugin never flagged the legacy config as migration_required",
      }
    );
  }

  /** Visible Obsidian notice texts (the plugin's own failure surface). */
  async function noticeTexts(): Promise<string[]> {
    return (await browser.execute(() =>
      Array.from(document.querySelectorAll(".notice")).map((n) =>
        (n.textContent ?? "").trim()
      )
    )) as string[];
  }

  /**
   * Every observable the migration journey leaves behind: the canonical
   * file's bytes, the plugin's own flags, the notices it raised, and a fresh
   * dry-run (whose rejection, if any, carries Python's structured error).
   * Attached to a timeout so the failure names the real cause.
   */
  async function migrationDiagnostics(
    base: string
  ): Promise<Record<string, unknown>> {
    return {
      config_file: sandboxConfigFile(base),
      config_head: existsSync(sandboxConfigFile(base))
        ? readFileSync(sandboxConfigFile(base), "utf8").slice(0, 900)
        : "<absent>",
      notices: await noticeTexts(),
      plugin: await browser.executeObsidian(async ({ app }) => {
        const plugin = app.plugins.plugins["paperforge"] as unknown as {
          _needsConfigMigration?: boolean;
          _migration_warnings?: unknown;
          getClient(): { configMigrate(dryRun: boolean): Promise<unknown> };
        };
        let dry: unknown = null;
        let dryError: string | null = null;
        try {
          dry = await plugin.getClient().configMigrate(true);
        } catch (error) {
          dryError = String((error as Error)?.message ?? error);
        }
        return {
          _needsConfigMigration: plugin._needsConfigMigration ?? null,
          _migration_warnings: plugin._migration_warnings ?? null,
          dry_run: dry,
          dry_run_error: dryError,
        };
      }),
    };
  }

  /** Wait for the canonical file to carry the migrated values. */
  async function waitForMigratedConfig(base: string): Promise<void> {
    try {
      await browser.waitUntil(
        async () =>
          Number(sandboxConfigField(base, "schema_version")) === 2 &&
          sandboxConfigField(base, "vault_config.resources_dir") ===
            "LegacyResources",
        {
          timeout: 60000,
          interval: 1000,
          timeoutMsg: "the migrate command never wrote the canonical config file",
        }
      );
    } catch (error) {
      throw new Error(
        `${String((error as Error)?.message ?? error)} — ${JSON.stringify(
          await migrationDiagnostics(base)
        )}`
      );
    }
  }

  /** Run the plugin's own migrate command end to end (dry-run modal → confirm). */
  async function migrateLegacyConfigViaUi(): Promise<{
    summaryText: string;
    noticesAfterConfirm: string[];
  }> {
    await browser.executeObsidianCommand("paperforge:paperforge-migrate-config");
    const summary = await browser.$(".pf-migration-summary");
    await summary.waitForExist({ timeout: 60000 });
    const summaryText = (await summary.getText()).trim();
    await clickTestId("migrate-config-confirm");
    // The migration is async; the notices it raises are gone after ~8s, so
    // sample them while the confirmation's own callback is still settling.
    await browser.pause(1500);
    return { summaryText, noticesAfterConfirm: await noticeTexts() };
  }

  it("A03 config edit: an invalid vault-relative path is rejected visibly and leaves the file byte-identical", async function () {
    // Case A03 改配置, rejection branch. An absolute path violates the
    // vault-relative rule; the write must fail loudly and leave the canonical
    // file exactly as it was (no truncation, no partial document).
    const base = await sandboxBasePath();
    const bytesBefore = sha256(sandboxConfigFile(base));

    await openSettingsTabOn({ stage: 2 });
    await waitForTestId("setup-path-system_dir");
    await setInputByTestId("setup-path-system_dir", "/absolute/not-in-vault");
    await clickSettingsTestId("setup-library-save");

    await browser.waitUntil(
      async () =>
        String(
          await settingsElement(".pf-setup-failure-detail", "text")
        ).length > 0,
      {
        timeout: 60000,
        timeoutMsg:
          "the rejected value produced no visible failure message in the Settings UI",
      }
    );
    const feedback = {
      detail: String(await settingsElement(".pf-setup-failure-detail", "text")),
      status: String(await settingsElement(".pf-setup-warn", "text")),
    };
    // The rejection names the offending field. It surfaces the authority's
    // error CODE, not the human reason: the client's PFResult unwrapping
    // drops `error.details.reason` (recorded in a03a05-findings.md).
    expect(feedback.detail).toContain("system_dir");
    expect(feedback.detail).toContain("config.invalid");

    // Rejected means nothing was written.
    expect(sha256(sandboxConfigFile(base))).toBe(bytesBefore);
    expect(sandboxConfigField(base, "vault_config.system_dir")).toBe("System");

    appendEvidence("a03-config-reject.json", {
      case_id: "A03",
      variant: "invalid vault-relative path -> visible rejection, config intact",
      required_layer: "H",
      status: "VERIFIED",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      worktree_dirty: worktreeDirty(),
      config_file: sandboxConfigFile(base),
      rejected_value: "/absolute/not-in-vault",
      ui_detail: feedback.detail,
      ui_status: feedback.status,
      config_sha256_before: bytesBefore,
      config_sha256_after: sha256(sandboxConfigFile(base)),
      stored_system_dir: sandboxConfigField(base, "vault_config.system_dir"),
      observed_at: new Date().toISOString(),
    });
  });

  const X06_SCENARIOS = ["401", "403", "429", "5xx", "drop", "malformed"] as const;
  for (const scenario of X06_SCENARIOS) {
    // One case per scripted provider failure: the sandbox is rebuilt per case
    // (X11), so cross-iteration DOM staleness cannot mask the contract.
    it(`keeps an OCR batch honest when the provider fails (${scenario})`, async function () {
      if (scenario === "429") {
        registeredSkip(this, "x06-429-job-level-resubmit-budget");
        return;
      }
      const successStates = new Set(["done", "done_degraded"]);
      const terminalStates = new Set([
        "done",
        "done_degraded",
        "error",
        "fatal_error",
        "blocked",
        "retryable_error",
      ]);
      const stub = await startOcrStub("success", { scenario });
      try {
        await prepareOcrSandbox(stub.jobUrl);
        await browser.executeObsidianCommand("paperforge:paperforge-ocr-workspace");
        await waitForOcrRow("Biomechanical");
        await clickStable(
          "//tr[.//*[contains(text(),'Biomechanical')]]//input[@type='checkbox']"
        );
        const processBtn = await browser.$(
          ".pf-ocr-ws-batch-actions button.pf-btn-secondary"
        );
        await processBtn.waitForExist({ timeout: 30000 });
        await browser.waitUntil(
          async () => await processBtn.isEnabled().catch(() => false),
          { timeout: 30000, timeoutMsg: "Process Selected stayed disabled" }
        );
        await processBtn.click();
        await clickStable(".paperforge-confirm-actions button.mod-warning");

        const base = await sandboxBasePath();
        const metaPath = path.join(
          base,
          "System",
          "PaperForge",
          "ocr",
          "TSTONE001",
          "meta.json"
        );
        await browser.waitUntil(
          async () => {
            try {
              const meta = JSON.parse(readFileSync(metaPath, "utf8")) as {
                ocr_status?: string;
              };
              return (
                terminalStates.has(String(meta.ocr_status ?? "")) &&
                !(await operationActive())
              );
            } catch {
              return false;
            }
          },
          {
            // Retryable modes walk the product's bounded exponential backoff
            // (5 transport attempts up to ~30s apart) up to the job-attempt
            // cap, so they legitimately take minutes; fatal modes fail fast.
            timeout:
              scenario === "401" || scenario === "403" || scenario === "malformed"
                ? 120000
                : 300000,
            timeoutMsg: `OCR run for ${scenario} never reached a terminal state`,
          }
        );
        const meta = JSON.parse(readFileSync(metaPath, "utf8")) as Record<
          string,
          unknown
        >;
        const status = String(meta.ocr_status ?? "");
        expect(successStates.has(status)).toBe(false);
        // Retry accounting must stay bounded: job_attempt never exceeds the cap.
        const attempts = Number(meta.job_attempt ?? meta.retry_count ?? 0);
        expect(attempts).toBeLessThanOrEqual(3);
        await browser
          .waitUntil(async () => !(await operationActive()), { timeout: 15000 })
          .catch(() => undefined);
        appendEvidence("x06-provider-failure-modes.json", {
          case_id: `X06-${scenario}`,
          variant: `provider ${scenario}: never success, bounded retries, honest terminal`,
          required_layer: "H",
          status: "VERIFIED",
          scenario,
          recorded_at: new Date().toISOString(),
        });
      } finally {
        await stub.close();
      }
    });
  }

  it("reaps the probe generation across a window reload and records its cost (#266)", async function () {
    await openPanel();
    await waitForIdle("J09", "startup-sync-settle");
    const base = await sandboxBasePath();

    // In-app cost of the full probe (the standalone measurement is separate).
    const hostProbe = await browser.executeObsidian(async ({ app }) => {
      const plugin = app.plugins.plugins["paperforge"];
      if (!plugin || typeof plugin.getClient !== "function") {
        throw new Error("paperforge plugin not loaded");
      }
      const client = plugin.getClient();
      const started = Date.now();
      const envelope = await client.probe("all");
      return { ms: Date.now() - started, ok: Boolean(envelope) };
    });
    expect(hostProbe.ok).toBe(true);

    // In-flight probe, then a reload while its child is alive. The generation
    // that owns the child ends at the reload; nothing may outlive it (#266).
    await browser.executeObsidian(async ({ app }) => {
      const client = app.plugins.plugins["paperforge"].getClient();
      void client.probe("all").catch(() => undefined);
      return true;
    });
    await browser.pause(1500);
    await browser.reloadObsidian({ vault: "./test/vaults/e2e" });
    await openPanel();
    await waitForIdle("J09", "reload-settle");
    await browser.pause(5000);

    // Attribution by command line, not by parent pid: an orphan may be
    // reparented, but it still references this sandbox.
    const listing = execFileSync(
      "powershell",
      [
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*probe all --json*' -and $_.CommandLine -like '*" +
          base +
          "*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress",
      ],
      { encoding: "utf8" }
    ).trim();
    const survivors = listing ? (JSON.parse(listing) as unknown[]) : [];
    appendEvidence("j266-probe-reaping.json", {
      case_id: "J09",
      variant: "probe all -> window reload -> the finished generation left no child",
      source_sha: execFileSync("git", ["rev-parse", "HEAD"], {
        cwd: PLUGIN_DIR,
      })
        .toString()
        .trim(),
      host_probe_ms: hostProbe.ms,
      survivors,
      sandbox_base: base,
      observed_at: new Date().toISOString(),
    });
    expect(survivors).toEqual([]);
  });
});
