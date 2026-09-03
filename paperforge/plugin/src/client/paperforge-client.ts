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

  async probeAll(): Promise<Record<string, ProbeEnvelope>> {
    return this._cachedRead("probe:all", 60000, async () => {
      const raw = await this._transport.execute(["probe", "all", "--json"]);
      return JSON.parse(raw) as Record<string, ProbeEnvelope>;
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
  private async _executePfResult<T>(argv: string[]): Promise<T> {
    const raw = await this._transport.execute(argv);
    let parsed: any;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new Error(`Failed to parse PFResult JSON: ${raw.slice(0, 100)}`);
    }
    if (parsed && typeof parsed === "object" && "data" in parsed) {
      return parsed.data as T;
    }
    return parsed as T;
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
    const argv = buildActionArgv(req);

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

  async search(query: string, limit = 20): Promise<any> {
    return this._cachedRead(`search:${query}:${limit}`, 30000, async () => {
      const raw = await this._transport.execute([
        "search",
        query,
        "--limit",
        String(limit),
        "--json",
      ]);
      return JSON.parse(raw);
    });
  }

  async retrieve(query: string, limit = 5): Promise<any> {
    return this._cachedRead(`retrieve:${query}:${limit}`, 30000, async () => {
      const raw = await this._transport.execute([
        "retrieve",
        query,
        "--limit",
        String(limit),
        "--json",
      ]);
      return JSON.parse(raw);
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

  async renderAudit(key?: string): Promise<any> {
    const argv = ["render", "audit"];
    if (key) argv.push(key);
    argv.push("--json");
    const raw = await this._transport.execute(argv);
    return JSON.parse(raw);
  }

  async promoteR(key: string, objectIds: string[] = []): Promise<any> {
    const argv = ["render", "promote-r", key, ...objectIds, "--json"];
    try {
      const raw = await this._transport.execute(argv);
      return JSON.parse(raw);
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
      const raw = await this._transport.execute(argv);
      return JSON.parse(raw);
    } finally {
      this.invalidateCache();
    }
  }
}
