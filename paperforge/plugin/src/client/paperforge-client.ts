/**
 * PaperForgeClient — The unified, host-independent TypeScript client for PaperForge.
 *
 * Implements the 5 backend contracts above an abstract Transport seam:
 * - Observation (probe) with generation-aware TTL caching
 * - Deficit (reconcile) read models
 * - Policy & Actions (action registry)
 * - Operations (NDJSON streaming) gated by OperationLock
 * - Authority-write mutations
 */

import {
  type Transport,
  type StreamOptions,
  type ExecuteOptions,
  type StreamHandle,
  type LongTaskOutcome,
  AsyncEventQueue,
} from "./transport";
import type { ProbeEnvelope } from "../constants";
import type {
  ActionRequest,
  ActionRunResult,
  ActionScope,
} from "../services/action-client";
import { buildActionArgv } from "../services/action-client";

export interface PaperForgeClientOptions {
  transport: Transport;
  clock?: () => number;
}
export interface ActionDescriptor {
  action_id: string;
  availability?: "available" | "unavailable" | "busy" | string;
  availability_reason?: string;
  execution_mode?: "result" | "stream";
  label_code?: string;
  confirmation?: "none" | "required" | string;
}

export interface OcrPaperRow {
  key: string;
  title?: string;
  status?: string;
  health?: string;
  version?: string;
  finished_at?: string;
  rebuild_finished_at?: string;
  pages?: number;
  blocks?: number;
  figures?: number;
  tables?: number;
  model?: string;
  can_redo?: boolean;
  can_rebuild?: boolean;
  recommended_action?: string;
  fulltext_path?: string;
  authors?: string;
  year?: string | number;
  [key: string]: unknown;
}

export interface ConfigField {
  key: string;
  value: string | boolean;
  stored_value: string | boolean | null;
  source: "default" | "file" | "environment" | "override";
  is_set: boolean;
  type: string;
  default: string | boolean;
  environment: string | null;
  choices: string[];
  writable: boolean;
  allow_empty: boolean;
  vault_relative: boolean;
}

export interface ConfigListData {
  schema_version: number;
  revision: string;
  unknown_keys: string[];
  fields: ConfigField[];
}

export interface ConfigSetData {
  schema_version: number;
  revision: string;
  unknown_keys: string[];
  changed: boolean;
  field: ConfigField;
}

/** Python `config migrate` wire: snapshot meta + changed/dry_run/warnings.
 * It never carries `field` — a per-field DTO is the `config set` shape. */
export interface ConfigMigrateData {
  schema_version: number;
  revision: string;
  unknown_keys: string[];
  changed: boolean;
  dry_run: boolean;
  warnings: string[];
}

export interface ConfigValidateData {
  state: string;
  revision: string | null;
  errors: Array<Record<string, unknown>>;
  warnings: Array<Record<string, unknown>>;
  migration: Record<string, unknown> | null;
}

export interface ProbeAllEnvelope {
  schema_version: number;
  module: "all";
  updated_at: string;
  modules: Record<string, ProbeEnvelope>;
}

export interface DashboardStatsData {
  stats?: Record<string, unknown>;
  permissions?: Record<string, boolean>;
  items?: PaperIndexItem[];
  [key: string]: unknown;
}

export interface PaperIndexItem {
  zotero_key?: string;
  title?: string;
  domain?: string;
  note_path?: string;
  pdf_path?: string;
  ocr_status?: string;
  deep_reading_status?: string;
  [key: string]: unknown;
}

/** Canonical paper identity, resolved by Python from the active path. */
export interface PaperIdentity {
  kind: "paper" | "domain" | "unknown";
  zotero_key?: string;
  domain?: string;
  entry?: PaperIndexItem | null;
}

export interface MemoryDetailData {
  paper_count_db?: number;
  fresh?: boolean;
  needs_rebuild?: boolean;
  [key: string]: unknown;
}

export interface EmbedStatusData {
  model?: string;
  mode?: string;
  deps_installed?: boolean;
  body_chunk_count?: number;
  object_chunk_count?: number;
  chunk_count?: number;
  total_chunks?: number;
  build_state?: Record<string, unknown>;
  [key: string]: unknown;
}

const ACTION_AVAILABLE = "available";

function ocrRowsFromPayload(payload: unknown): OcrPaperRow[] {
  if (Array.isArray(payload)) return payload as OcrPaperRow[];
  if (!payload || typeof payload !== "object") return [];
  const object = payload as Record<string, unknown>;
  const data = object.data;
  if (Array.isArray(data)) return data as OcrPaperRow[];
  if (data && typeof data === "object") {
    const rows = (data as Record<string, unknown>).rows;
    if (Array.isArray(rows)) return rows as OcrPaperRow[];
  }
  return Array.isArray(object.rows) ? (object.rows as OcrPaperRow[]) : [];
}

interface CacheEntry<T> {
  data: T;
  expiresAt: number;
  epoch: number;
}

interface InFlightRead<T> {
  promise: Promise<T>;
  epoch: number;
}

interface ActiveOperation {
  operationId: string;
  stop: () => void;
  outcome: Promise<LongTaskOutcome>;
}

export interface SetupArgs {
  systemDir?: string;
  resourcesDir?: string;
  literatureDir?: string;
  baseDir?: string;
  zoteroData?: string;
  agent?: string;
  skipChecks?: boolean;
  modular?: boolean;
  headless?: boolean;
}
export interface SearchOptions {
  limit?: number;
}

export interface RetrieveOptions {
  limit?: number;
  deep?: boolean;
  paper?: string;
  expand?: boolean;
}

export interface SearchResult {
  [key: string]: unknown;
}

export function unwrapMatches(raw: unknown): SearchResult[] {
  let parsed: unknown = raw;
  if (typeof raw === "string") {
    try {
      parsed = JSON.parse(raw);
    } catch {
      return [];
    }
  }
  if (!parsed || typeof parsed !== "object") return [];
  const obj = parsed as Record<string, unknown>;
  if (obj.data && typeof obj.data === "object") {
    const d = obj.data as Record<string, unknown>;
    if (Array.isArray(d.matches)) return d.matches as SearchResult[];
    if (Array.isArray(d.results)) return d.results as SearchResult[];
  }
  if (Array.isArray(obj.matches)) return obj.matches as SearchResult[];
  if (Array.isArray(obj.results)) return obj.results as SearchResult[];
  if (Array.isArray(parsed)) return parsed as SearchResult[];
  return [];
}
export class PaperForgeClient {
  private readonly _transport: Transport;
  private readonly _clock: () => number;

  private _epoch = 0;
  private readonly _cache = new Map<string, CacheEntry<unknown>>();
  private readonly _inFlightReads = new Map<string, InFlightRead<unknown>>();

  private _activeOperation: ActiveOperation | null = null;

  constructor(options: PaperForgeClientOptions) {
    this._transport = options.transport;
    this._clock = options.clock ?? Date.now;
  }

  // ── Cache & Epoch Management ──────────────────────────────────────────────

  /** Current generation epoch. Incremented on every mutation. */
  getEpoch(): number {
    return this._epoch;
  }

  /** Invalidate memory cache and advance epoch to discard in-flight reads. */
  invalidateCache(): void {
    this._epoch++;
    this._cache.clear();
    this._inFlightReads.clear();
  }

  /**
   * Internal cached read engine:
   * 1. Returns fresh cached value if epoch matches and not expired.
   * 2. Merges concurrent in-flight reads for the same key and epoch.
   * 3. Anti-resurrection guard: discards late reads that cross an epoch boundary.
   */
  private async _cachedRead<T>(
    key: string,
    ttlMs: number,
    fetcher: () => Promise<T>
  ): Promise<T> {
    const now = this._clock();

    // 1. Check memory cache
    const cached = this._cache.get(key) as CacheEntry<T> | undefined;
    if (cached && cached.epoch === this._epoch && cached.expiresAt > now) {
      return cached.data;
    }

    // 2. Check in-flight read
    const inFlight = this._inFlightReads.get(key) as
      | InFlightRead<T>
      | undefined;
    if (inFlight && inFlight.epoch === this._epoch) {
      return inFlight.promise;
    }

    // 3. Initiate fresh read tagged with request epoch
    const reqEpoch = this._epoch;
    let inFlightEntry: InFlightRead<T> | undefined = undefined;
    const promise = (async (): Promise<T> => {
      try {
        const data = await fetcher();
        // Anti-resurrection guard: only cache if no mutation occurred during fetch
        if (this._epoch === reqEpoch) {
          this._cache.set(key, {
            data,
            expiresAt: this._clock() + ttlMs,
            epoch: reqEpoch,
          });
        }
        return data;
      } finally {
        if (inFlightEntry && this._inFlightReads.get(key) === inFlightEntry) {
          this._inFlightReads.delete(key);
        }
      }
    })();

    inFlightEntry = { promise, epoch: reqEpoch };
    this._inFlightReads.set(key, inFlightEntry);
    return promise;
  }

  // ── Operation Lock & Execution Ownership ──────────────────────────────────

  /** Whether this client instance currently owns an active streaming operation. */
  isOperationActive(): boolean {
    return this._activeOperation !== null;
  }

  /** Operation ID of the currently active long task, or null if idle. */
  get activeOperationId(): string | null {
    return this._activeOperation?.operationId ?? null;
  }

  /** Send cooperative cancellation signal to the active operation. */
  cancelActiveOperation(): void {
    if (this._activeOperation) {
      this._activeOperation.stop();
    }
  }

  /**
   * Start a long-running streaming operation with mutual-exclusion lock.
   * Lock releases on all terminal states (result, error, cancelled, EOF, exception).
   */
  streamOperation(
    operationId: string,
    argv: string[],
    options?: StreamOptions
  ): StreamHandle {
    if (this._activeOperation) {
      throw new Error(
        `Another operation is already active: ${this._activeOperation.operationId}`
      );
    }

    const rawHandle = this._transport.stream(argv, options);
    const queue = new AsyncEventQueue<any>();

    // Forward events through wrapped queue
    (async () => {
      try {
        for await (const ev of rawHandle.events) {
          queue.push(ev);
        }
        queue.finish();
      } catch (err: any) {
        queue.fail(err);
      }
    })();

    const wrappedOutcome = (async (): Promise<LongTaskOutcome> => {
      try {
        const outcome = await rawHandle.outcome;
        return outcome;
      } finally {
        // Deterministic release across all outcomes!
        this._activeOperation = null;
        // Mutations bump epoch and clear cache
        this.invalidateCache();
      }
    })();

    this._activeOperation = {
      operationId,
      stop: rawHandle.stop,
      outcome: wrappedOutcome,
    };

    return {
      events: queue,
      stop: rawHandle.stop,
      outcome: wrappedOutcome,
    };
  }

  // ── 1. Observation Contract (probe) ───────────────────────────────────────

  async probe(
    module: string,
    options?: { expectedVersion?: string; lastOperationExitCode?: number }
  ): Promise<ProbeEnvelope> {
    const extraArgs: string[] = [];
    if (options?.expectedVersion) {
      extraArgs.push("--expected-version", options.expectedVersion);
    }
    if (
      options?.lastOperationExitCode != null &&
      options.lastOperationExitCode !== 0
    ) {
      extraArgs.push(
        "--last-operation-exit-code",
        String(options.lastOperationExitCode)
      );
    }
    const cacheKey = `probe:${module}:${options?.expectedVersion ?? ""}:${options?.lastOperationExitCode ?? ""}`;
    return this._cachedRead(cacheKey, 60000, async () => {
      const raw = await this._transport.execute([
        "probe",
        module,
        "--json",
        ...extraArgs,
      ]);
      return JSON.parse(raw) as ProbeEnvelope;
    });
  }

  async probeAll(): Promise<ProbeAllEnvelope> {
    return this._cachedRead("probe:all", 60000, async () => {
      const raw = await this._transport.execute(["probe", "all", "--json"]);
      return JSON.parse(raw) as ProbeAllEnvelope;
    });
  }
  // ── 2. Deficit Contract (reconcile) ───────────────────────────────────────

  async reconcile(
    scope: "all" | "papers" = "all",
    keys?: string[]
  ): Promise<Record<string, unknown>> {
    const keyPart = keys ? [...keys].sort().join(",") : "";
    return this._cachedRead(
      `reconcile:${scope}:${keyPart}`,
      10000,
      async () => {
        const argv = ["reconcile", "--scope", scope];
        for (const k of keys ?? []) {
          argv.push("--key", k);
        }
        argv.push("--json");
        const raw = await this._transport.execute(argv);
        return JSON.parse(raw);
      }
    );
  }

  // ── 3. Policy & Action Contract (action registry) ─────────────────────────

  /**
   * Execute a command expecting a PFResult envelope and unwrap data.
   */
  private async _executePfResult<T>(
    argv: string[],
    options?: ExecuteOptions
  ): Promise<T> {
    // Layer split: the Transport owns process/exit semantics (rejects
    // non-zero exits), this client owns PFResult machine-protocol
    // semantics. The Python config contract emits a STRUCTURED ok:false
    // PFResult on stdout together with rc=1/2 — so on a transport
    // rejection, recover the authority reason from err.stdout instead of
    // losing it to a generic "exit code 1" error (legacy config-client
    // behavior, preserved here).
    let raw: string;
    let transportError: unknown = null;
    try {
      raw = await this._transport.execute(argv, options);
    } catch (err: unknown) {
      const stdout =
        err instanceof Error
          ? ((err as unknown as { stdout?: unknown }).stdout ?? null)
          : null;
      if (typeof stdout !== "string" || !stdout.trim()) {
        throw err;
      }
      transportError = err;
      raw = stdout;
    }
    let parsed: any;
    try {
      parsed = JSON.parse(raw);
    } catch {
      if (transportError) throw transportError;
      throw new Error(`Failed to parse PFResult JSON: ${raw.slice(0, 100)}`);
    }
    if (parsed && typeof parsed === "object" && "data" in parsed) {
      // Fail closed: a structured ok:false PFResult is an authority
      // rejection, never a null payload.
      if (parsed.ok === false) {
        const err = parsed.error ?? {};
        throw new Error(String(err.message || err.code || "backend_error"));
      }
      if (transportError) {
        // rc != 0 but the PFResult claims ok — protocol contradiction;
        // the process-level failure wins.
        throw transportError;
      }
      return parsed.data as T;
    }
    if (transportError) throw transportError;
    return parsed as T;
  }

  // ── 3b. Configuration & Read-Model Contract (config/auth authority) ──────
  // Ticket 07 Stage 2 step 2: typed surfaces replace config-client.ts. The
  // plugin never builds config argv or touches PFResult `.data` outside this
  // class; every read/mutation routes through the Python authority.

  async configList(): Promise<ConfigListData> {
    return this._executePfResult<ConfigListData>(["config", "list", "--json"]);
  }

  async configValidate(): Promise<ConfigValidateData> {
    return this._executePfResult<ConfigValidateData>([
      "config",
      "validate",
      "--json",
    ]);
  }

  async configMigrate(dryRun = false): Promise<ConfigMigrateData> {
    const argv = ["config", "migrate"];
    if (dryRun) argv.push("--dry-run");
    argv.push("--json");
    try {
      return await this._executePfResult<ConfigMigrateData>(argv);
    } finally {
      this.invalidateCache();
    }
  }

  async configSet(
    key: string,
    value: string | boolean
  ): Promise<ConfigSetData> {
    try {
      return await this._executePfResult<ConfigSetData>([
        "config",
        "set",
        key,
        String(value),
        "--json",
      ]);
    } finally {
      this.invalidateCache();
    }
  }

  async embedStatus(): Promise<EmbedStatusData> {
    return this._cachedRead("embed:status", 30000, async () =>
      this._executePfResult<EmbedStatusData>(["embed", "status", "--json"])
    );
  }

  async memoryStatus(): Promise<MemoryDetailData> {
    return this._cachedRead("memory:status", 30000, async () =>
      this._executePfResult<MemoryDetailData>(["memory", "status", "--json"])
    );
  }

  /** Credential presence from the authority (`auth status`), never from
   * SecretStorage or settings flags (#173/C1). */
  async credentialAvailable(service: "embedding" | "ocr"): Promise<boolean> {
    return this._cachedRead(`auth-status:${service}`, 60000, async () => {
      const data = await this._executePfResult<{
        credentials?: Array<{ state?: string }>;
      }>(["auth", "status", service, "--json"]);
      return data.credentials?.some((c) => c.state === "available") ?? false;
    });
  }

  /** #173/C1: `paperforge auth set <kind> --stdin` — the secret travels
   * only via child stdin, never argv, env, files, or settings; the
   * NodeProcessTransport owns the sanitized env. Mutation: bumps the
   * cache epoch so stale `credentialAvailable`/`describeAction` reads
   * (e.g. a cached `unavailable` before the key was saved) never survive
   * it. `replace` defaults to true (user Save); the legacy SecretStorage
   * migration passes `{replace: false}` so a stale host copy can never
   * overwrite a live keyring value. */
  async authSetSecret(
    kind: "ocr" | "embedding",
    secret: string,
    options?: { replace?: boolean }
  ): Promise<boolean> {
    const argv = ["auth", "set", kind, "--stdin"];
    if (options?.replace !== false) argv.push("--replace");
    argv.push("--json");
    try {
      await this._executePfResult(argv, { stdin: secret + "\n" });
      return true;
    } finally {
      this.invalidateCache();
    }
  }

  async memoryRestoreBackup(): Promise<unknown> {
    try {
      return await this._executePfResult(
        ["memory", "restore-backup", "--json"],
        { timeoutMs: 30000 }
      );
    } finally {
      this.invalidateCache();
    }
  }

  async embedMigrate(): Promise<unknown> {
    try {
      return await this._executePfResult(["embed", "migrate", "--json"], {
        timeoutMs: 600000,
      });
    } finally {
      this.invalidateCache();
    }
  }

  /** On-demand diagnostic read (`runtime-health --json`); output is a
   * warm-up side effect — status text comes from probe envelopes. */
  async runtimeHealth(): Promise<unknown> {
    return this._executePfResult(["runtime-health", "--json"], {
      timeoutMs: 30000,
    });
  }

  /** Dashboard stats DTO — the canonical index item list travels INSIDE
   * this payload (Python is the only reader of its own canonical index);
   * the UI never inspects canonical files. */
  async dashboardStats(): Promise<DashboardStatsData> {
    return this._executePfResult<DashboardStatsData>(["dashboard", "--json"], {
      timeoutMs: 30000,
    });
  }

  /** Python-authoritative note workflow flag mutation
   * (`note set-flag`). The dashboard workflow toggles (do_ocr/analyze)
   * must NEVER write Obsidian frontmatter client-side — the note is
   * Python's own literature note; the client passes key/field/value
   * only. Unknown fields fail closed backend-side. */
  async setNoteFlag(
    key: string,
    field: "do_ocr" | "analyze",
    value: boolean
  ): Promise<{ changed: boolean }> {
    return this._executePfResult<{ changed?: boolean }>([
      "note",
      "set-flag",
      "--key",
      key,
      "--field",
      field,
      "--value",
      value ? "true" : "false",
      "--json",
    ]).then((data) => ({ changed: data?.changed === true }));
  }

  /** Canonical paper identity resolver (`paper-lookup --from-path`). The
   * plugin passes ONLY the host fact (the active vault-relative path);
   * frontmatter, the canonical index, and workspace-key derivation are
   * Python authority — never inferred from files client-side. */
  async resolvePaperContext(
    vaultRelativePath: string
  ): Promise<PaperIdentity | null> {
    const data = await this._executePfResult<{
      identity?: PaperIdentity | null;
    }>(["paper-lookup", "--from-path", vaultRelativePath, "--json"]);
    return data?.identity ?? null;
  }

  /** Backend version (`paperforge --version`). argparse fires the version
   * action during parse (before --vault validation), printing a plain
   * `paperforge X.Y.Z` line — not a PFResult. */
  async backendVersion(): Promise<string> {
    const raw = await this._transport.execute(["--version"]);
    return raw.trim().replace(/^paperforge\s+/, "");
  }

  /** Explicit diagnostic read (`doctor --json`). No cache — a user-invoked
   * check must always hit the authority. */
  async doctor(): Promise<Record<string, unknown>> {
    return this._executePfResult(["doctor", "--json"]);
  }

  /** Authority repair mutation (`repair --fix --fix-paths --json`). */
  async repair(): Promise<Record<string, unknown>> {
    try {
      return await this._executePfResult(
        ["repair", "--fix", "--fix-paths", "--json"],
        { timeoutMs: 600000 }
      );
    } finally {
      this.invalidateCache();
    }
  }

  async listActions(): Promise<any[]> {
    return this._cachedRead("action:list", 300000, async () => {
      const data = await this._executePfResult<any>([
        "action",
        "list",
        "--json",
      ]);
      return data?.actions ?? (Array.isArray(data) ? data : []);
    });
  }

  async describeAction(actionId: string): Promise<ActionDescriptor> {
    return this._cachedRead(`action:describe:${actionId}`, 300000, async () => {
      return this._executePfResult<ActionDescriptor>([
        "action",
        "describe",
        actionId,
        "--json",
      ]);
    });
  }

  async preflightAction(
    actionId: string,
    scope: ActionScope = { kind: "all" }
  ): Promise<any> {
    const argv = ["action", "preflight", actionId, "--scope", scope.kind];
    for (const k of scope.keys ?? []) {
      argv.push("--key", k);
    }
    argv.push("--json");
    return this._executePfResult(argv);
  }

  /**
   * Execute an action dynamically based on its backend execution_mode:
   * - execution_mode === "result" -> executes single JSON via transport.execute.
   * - execution_mode === "stream" -> routes to streamAction (OperationLock gated).
   *
   * Uses buildActionArgv(req) as the single authoritative argv constructor,
   * preserving scope, keys, confirm, and follow flags across both branches.
   *
   * Mutation: NEVER deduplicated. Bumps epoch on completion.
   */
  async runAction(
    req: ActionRequest,
    streamOptions?: StreamOptions
  ): Promise<ActionRunResult> {
    const desc = await this.describeAction(req.action_id);
    if (desc?.availability && desc.availability !== ACTION_AVAILABLE) {
      return {
        ok: false,
        payload: {
          ok: false,
          action_id: req.action_id,
          availability: desc.availability,
          availability_reason: desc.availability_reason,
        },
        exitCode: 1,
      };
    }
    const actionReq: ActionRequest = {
      ...req,
      scope: req.scope ?? { kind: "all" },
    };
    const argv = buildActionArgv(actionReq);

    if (desc?.execution_mode === "stream") {
      const handle = this.streamOperation(
        `action.${req.action_id}`,
        argv,
        streamOptions
      );
      const outcome = await handle.outcome;
      const terminalEv = outcome.events.find(
        (e) =>
          e.event === "result" || e.event === "error" || e.event === "cancelled"
      );
      const payload =
        (terminalEv?.result as Record<string, unknown> | null) ?? null;
      return {
        ok: outcome.ok,
        payload,
        exitCode: outcome.exitCode ?? (outcome.ok ? 0 : 1),
        cancelled: outcome.cancelled,
      };
    }

    try {
      const raw = await this._transport.execute(argv);
      let payload: Record<string, unknown> | null = null;
      try {
        payload = JSON.parse(raw);
      } catch {
        // non-JSON stdout
      }
      return { ok: true, payload, exitCode: 0 };
    } catch (err: any) {
      return { ok: false, payload: null, exitCode: err.exitCode ?? 1 };
    } finally {
      this.invalidateCache();
    }
  }

  streamAction(
    req: ActionRequest | string,
    scope: ActionScope = { kind: "all" },
    options?: StreamOptions
  ): StreamHandle {
    const actionReq: ActionRequest =
      typeof req === "string" ? { action_id: req, scope } : req;
    const argv = buildActionArgv(actionReq);
    return this.streamOperation(`action.${actionReq.action_id}`, argv, options);
  }

  // ── 4. Operation Contract (Setup, Sync, Maintenance) ──────────────────────

  setup(args: SetupArgs, options?: StreamOptions): StreamHandle {
    const argv = ["setup", "--json"];
    if (args.modular || !args.headless) argv.push("--modular");
    if (args.systemDir) argv.push("--system-dir", args.systemDir);
    if (args.resourcesDir) argv.push("--resources-dir", args.resourcesDir);
    if (args.literatureDir) argv.push("--literature-dir", args.literatureDir);
    if (args.baseDir) argv.push("--base-dir", args.baseDir);
    if (args.zoteroData) argv.push("--zotero-data", args.zoteroData);
    if (args.agent) argv.push("--agent", args.agent);
    if (args.skipChecks) argv.push("--skip-checks");

    return this.streamOperation("foundation.setup", argv, options);
  }

  async sync(dryRun = false): Promise<Record<string, unknown>> {
    const argv = ["sync", "--json"];
    if (dryRun) argv.push("--dry-run");
    const raw = await this._transport.execute(argv);
    this.invalidateCache();
    return JSON.parse(raw);
  }

  // ── 5. Queries & Search Gateway ───────────────────────────────────────────

  async search(
    query: string,
    options?: number | SearchOptions
  ): Promise<SearchResult[]> {
    const opts: SearchOptions =
      typeof options === "number" ? { limit: options } : (options ?? {});
    const limit = opts.limit ?? 20;
    const cleanQuery = query.trim();
    const cacheKey = `search:${cleanQuery}:${limit}`;
    return this._cachedRead(cacheKey, 30000, async () => {
      const raw = await this._transport.execute([
        "search",
        cleanQuery,
        "--limit",
        String(limit),
        "--json",
      ]);
      return unwrapMatches(raw);
    });
  }

  async retrieve(
    query: string,
    options?: number | RetrieveOptions
  ): Promise<SearchResult[]> {
    const opts: RetrieveOptions =
      typeof options === "number" ? { limit: options } : (options ?? {});
    const limit = opts.limit ?? 5;
    const deep = Boolean(opts.deep);
    const paper = opts.paper?.trim() || "";
    const expand = opts.expand !== false;
    const cleanQuery = query.trim();
    const cacheKey = `retrieve:${cleanQuery}:${limit}:${deep}:${paper}:${expand}`;
    return this._cachedRead(cacheKey, 30000, async () => {
      const argv = ["retrieve", cleanQuery, "--limit", String(limit)];
      if (deep) argv.push("--deep");
      if (paper) argv.push("--paper", paper);
      if (!expand) argv.push("--no-expand");
      argv.push("--json");
      const raw = await this._transport.execute(argv);
      return unwrapMatches(raw);
    });
  }

  async read(
    key: string,
    find: string,
    source: "auto" | "fulltext" | "pdf" = "auto"
  ): Promise<any> {
    const raw = await this._transport.execute([
      "read",
      key,
      "--find",
      find,
      "--source",
      source,
    ]);
    return raw;
  }

  async paperStatus(query: string): Promise<any> {
    return this._cachedRead(`paper-status:${query}`, 30000, async () => {
      const raw = await this._transport.execute([
        "paper-status",
        query,
        "--json",
      ]);
      return JSON.parse(raw);
    });
  }

  async queryOcrPapers(keys?: string[]): Promise<OcrPaperRow[]> {
    const sortedKeys = keys ? [...keys].sort() : [];
    const keyPart = sortedKeys.join(",");
    return this._cachedRead(`ocr-papers:${keyPart}`, 10000, async () => {
      const argv = ["ocr", "list", "--json"];
      if (sortedKeys.length > 0) {
        argv.push("--keys", ...sortedKeys);
      }
      const raw = await this._transport.execute(argv);
      return ocrRowsFromPayload(JSON.parse(raw));
    });
  }

  // ── 6. Authority Actions (Render Quality) ──────────────────────────────────

  /** #06 corrective C: Render authority exits rc=1 with a STRUCTURED JSON
   * rejection on stdout (FAILED audit, R_GATE_FAILED, STALE_PROPOSAL,
   * STALE_REVIEWED_PLAN, …). The transport rejects non-zero exits, but the
   * Python decision must survive as a normal authority response — only a
   * genuine spawn/protocol failure may surface as an exception. */
  private async _executeStructuredJson<T>(argv: string[]): Promise<T> {
    try {
      const raw = await this._transport.execute(argv);
      return JSON.parse(raw) as T;
    } catch (err: unknown) {
      const stdout =
        err instanceof Error
          ? ((err as unknown as { stdout?: unknown }).stdout ?? null)
          : null;
      if (typeof stdout === "string" && stdout.trim()) {
        try {
          return JSON.parse(stdout) as T;
        } catch {
          // fall through — stdout was not JSON
        }
      }
      throw err;
    }
  }

  async renderAudit(key?: string): Promise<any> {
    const argv = ["render", "audit"];
    if (key) argv.push(key);
    argv.push("--json");
    return this._executeStructuredJson(argv);
  }

  /** Ticket 06: R/P staging preview for one paper (isolated tmp root; never
   * writes production). Surfaces `p_details[].final_plan_hash` — the exact
   * SHA-256 token `accept-proposal` requires — and `r_details[].object_id`
   * candidates for `promote-r`. */
  async renderReconcileStaging(key: string): Promise<Record<string, unknown>> {
    // `render reconcile` takes POSITIONAL keys — never `--keys` (#06 corrective B).
    const raw = await this._executeStructuredJson<Record<string, unknown>>([
      "render",
      "reconcile",
      key,
      "--json",
    ]);
    const parsed = raw as { papers?: Record<string, unknown>[] };
    return parsed.papers?.find((p) => p.paper_key === key) ?? {};
  }

  async promoteR(key: string, objectIds: string[] = []): Promise<any> {
    const argv = ["render", "promote-r", key, ...objectIds, "--json"];
    try {
      return await this._executeStructuredJson(argv);
    } finally {
      this.invalidateCache();
    }
  }

  async acceptProposal(
    key: string,
    label: string,
    planHash: string
  ): Promise<any> {
    const argv = [
      "render",
      "accept-proposal",
      key,
      label,
      "--plan-hash",
      planHash,
      "--json",
    ];
    try {
      return await this._executeStructuredJson(argv);
    } finally {
      this.invalidateCache();
    }
  }
}
