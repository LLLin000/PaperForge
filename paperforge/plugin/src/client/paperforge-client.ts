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
  type StreamDiagnostics,
  type DaemonPushEvent,
  AsyncEventQueue,
} from "./transport";
import type { ProbeAllEnvelope, ProbeEnvelope } from "./probe-types";
import type {
  ActionRequest,
  ActionRunResult,
  ActionScope,
} from "./action-contract";
import { buildActionArgv } from "./action-contract";
import {
  commandIdentity,
  isTraceEnabled,
  rejectionCode,
  traceConsoleError,
  traceRecord,
} from "./trace";

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
export interface RuntimeStatus {
  runtime_ready: boolean;
  runtime_state: "ready" | "attention" | "missing" | string;
  pointer_path: string;
  pointer_version: string | null;
  python_path: string | null;
  python_exists: boolean;
  paperforge_version: string | null;
  version_matches_expected: boolean;
  compatible?: boolean;
  min_engine_version?: string | null;
  deps_lock_matches?: boolean;
  uv_path?: string | null;
  vector_ready: boolean;
  installer: string;
}

export interface OcrPaperRow {
  key: string;
  title?: string;
  title_full?: string;
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

/** Structured authority rejection/acceptance (render R/P exits rc=1 with a
 * structured JSON body — the reason must survive as data, never as an
 * exception). */
export interface AuthorityMutationResult {
  ok?: boolean;
  reason?: string;
  error?: { code?: string; message?: string } | null;
  [key: string]: unknown;
}

export interface RenderAuditIssue {
  code?: string;
  severity?: string;
  message?: string;
  [key: string]: unknown;
}

export type AnnotationKind =
  | "highlight"
  | "underline"
  | "strikethrough"
  | "area"
  | "note"
  | "textbox"
  | "shape"
  | "ink"
  | "margin";
export type AnnotationColor =
  | "yellow"
  | "green"
  | "blue"
  | "pink"
  | "red"
  | "purple"
  | "ink"
  | "gray"
  | "transparent";
export type AnnotationIntent =
  | "evidence"
  | "question"
  | "method"
  | "quote"
  | "general";

export interface AnnotationStyleDto {
  shape_type?: "rect" | "ellipse" | "arrow" | "line";
  stroke_color?: string;
  fill_color?: string;
  stroke_width?: number;
  font_size?: number;
  points?: number[][];
  opacity?: number;
}

export interface PdfAnnotationDto {
  ann_id: string;
  paper_id: string;
  page: number;
  kind: AnnotationKind;
  color: AnnotationColor | string;
  intent: AnnotationIntent | string;
  author?: "user" | "agent" | string;
  lens?: string;
  grounding_tier?: string;
  exact_text: string;
  comment: string;
  tags: string[];
  rects: number[][];
  style?: AnnotationStyleDto;
  section_path: string;
  block_id: string;
  figure_id: string;
  crop_asset_rel: string;
  embed_wikilink: string;
  pdf_sha256: string;
  created_at: string;
  updated_at: string;
  provenance_status?: "verified" | "changed" | "unknown" | string;
}

export interface MemoryFacetDto {
  facet: string;
  label: string;
  content: string;
  revision: number;
  updated_at: string;
}

export interface PaperMemoryCardDto {
  paper_id: string;
  updated_at: string;
  facet_count: number;
  facets: MemoryFacetDto[];
}

export interface MemoryHistoryEntryDto {
  facet: string;
  label: string;
  content: string;
  revision: number;
  created_at: string;
}

export interface ClearMemoryFacetResultDto {
  paper_id: string;
  facet: string;
  removed: number;
}

export interface VersionsResetLiveResultDTO {
  intent: string;
  key: string;
  source_path: string;
  target_path: string;
  provenance_cleared: boolean;
}

export interface ZoteroCollectionInfoDto {
  key: string;
  name: string;
  parent_key?: string | null;
  path: string;
  direct_item_count: number;
  item_count: number;
  top_level: boolean;
}

export interface ZoteroDetectDto {
  found: boolean;
  zotero_dir: string;
  total_papers: number;
  collections: ZoteroCollectionInfoDto[];
}

export interface BasePaperRowDto {
  zotero_key: string;
  title: string;
  first_author: string;
  year: string;
  journal: string;
  impact_factor: string;
  impact_factor_source?: string;
  journal_partition?: string;
  domain: string;
  collections?: string[];
  has_pdf: boolean;
  do_ocr: boolean;
  analyze: boolean;
  ocr_status: string;
  deep_reading_status: string;
  main_note_path: string;
  user_ann_count: number;
  agent_ann_count: number;
  memory_facet_count: number;
  memory_updated_at: string;
  needs_diagnostic: boolean;
}

export interface BaseTableSnapshotDto {
  seq: number;
  updated_at: string;
  state_authority?: "sqlite" | "legacy_json_fallback" | string;
  rows: Record<string, BasePaperRowDto>;
}

export interface ClearAgentAnnotationsResultDto {
  paper_id: string;
  deleted_count: number;
  deleted_ids: string[];
}

export interface PaperPdfContextDto {
  paper_id: string;
  title: string;
  pdf_abs_path: string;
  pdf_vault_rel: string;
  pdf_locator: string;
  is_vault_relative: boolean;
  pdf_sha256: string;
  page_count: number;
  workspace_rel: string;
  note_rel_path: string;
  annotations: PdfAnnotationDto[];
}

export interface DiagnosticFulltextDto {
  paper_id: string;
  content: string;
  truncated: boolean;
  total_lines: number;
  total_chars: number;
}

export interface RenderAuditPaper {
  paper_key?: string;
  issues?: RenderAuditIssue[];
  [key: string]: unknown;
}

export interface RenderAuditDTO {
  state?: string;
  papers?: RenderAuditPaper[];
  summary?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface VaultProvenanceDto {
  state:
    | "fresh_or_foreign"
    | "standard_current"
    | "veteran_legacy"
    | "veteran_rescue"
    | string;
  needs_upgrade: boolean;
  confidence: "high" | "medium" | "none" | string;
  signals: string[];
  legacy_engine_dir?: string | null;
}

export interface VaultUpgradeItemDto {
  id: string;
  area: string;
  title: string;
  detail: string;
  count?: number;
  fast_cutover?: boolean;
  impact?: "experience_critical" | "minor" | string;
  remediation?: string;
  keys?: string[];
}

export interface VaultCleanupCandidateDto {
  id: string;
  path: string;
  bytes: number;
  reason: string;
}

export interface VaultUpgradePlanDto {
  vault: string;
  provenance: VaultProvenanceDto;
  census: Record<string, unknown>;
  manifest: Record<string, unknown> | null;
  rollback_available: boolean;
  category_a_auto: VaultUpgradeItemDto[];
  category_b_reconfig: VaultUpgradeItemDto[];
  category_c_tamper: VaultUpgradeItemDto[];
  cleanup_candidates: VaultCleanupCandidateDto[];
  summary: {
    auto_count: number;
    fast_cutover_count?: number;
    progressive_heal_count?: number;
    reconfig_critical_count: number;
    reconfig_minor_count: number;
    tamper_count: number;
    cleanup_candidate_count: number;
    ocr_atoms: {
      total: number;
      current: number;
      rebuild_derived_local: number;
      backfill_from_result_json: number;
      re_ocr_needed: number;
    };
  };
}

export interface VaultUpgradeApplyResultDto {
  dry_run: boolean;
  applied: boolean;
  status?: "completed" | "partial_success" | "failed" | string;
  fast_cutover?: boolean;
  backup_dir?: string;
  executed_steps: Array<Record<string, unknown>>;
  errors: Array<{ step: string; error: string }>;
  post_check?: VaultUpgradePlanDto;
}

export interface VaultUpgradeHealResultDto {
  processed_workspaces: number;
  paper_meta_cleaned: number;
  legacy_notes_renamed: number;
  visual_assets_synced: number;
  ocr_backfilled: number;
  workspace_registry_upserted: number;
  ocr_catalog_total: number;
  skipped_isolated: Array<{ key: string; reason: string }>;
}

export interface VaultUpgradeRollbackResultDto {
  rolled_back: boolean;
  reason?: string;
  backup_dir?: string;
  restored?: string[];
}

export interface DaemonJobDto {
  job_id: string;
  trace_id?: string;
  vault: string;
  kind: "sync" | "ocr" | "embed" | "upgrade.heal" | string;
  scope_key?: string;
  source?: "background" | "stream" | string;
  stream_id?: string | null;
  status:
    | "queued"
    | "running"
    | "cancelling"
    | "succeeded"
    | "failed"
    | "cancelled"
    | string;
  current: number;
  total: number;
  phase: string;
  item_id: string;
  priority_key?: string | null;
  started_at: number;
  finished_at?: number | null;
  duration_ms?: number;
  exit_code?: number | null;
  error?: string;
  pid?: number | null;
}

export interface DaemonNoticeDto {
  notice_id: string;
  trace_id?: string;
  level: "info" | "success" | "warning" | "error" | string;
  code: string;
  title: string;
  detail: string;
  vault: string | null;
  created_at: number;
  acked: boolean;
}

export interface DaemonHealthDto {
  ok: boolean;
  backend?: string;
  pid: number;
  parent_pid: number | null;
  uptime_sec: number;
  rss_bytes: number;
  rss_mb: number;
  heavy_modules_loaded: string[];
  active_jobs: DaemonJobDto[];
  unacked_notice_count: number;
  cached_vaults: Array<Record<string, unknown>>;
}

export interface PaperStatusDTO {
  [key: string]: unknown;
}

export interface ActionPreflightDTO {
  action_id?: string;
  availability?: string;
  preflight?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface VersionEntryDTO {
  label: string;
  created_at: string;
  source: string;
  renderer_version?: string;
  structured_content_hash?: string;
  fulltext_size: number;
  /** Canonical artifact path constructed by Python — the UI reads ONLY this. */
  source_path?: string;
}

export interface PaperVersionInfoDTO {
  key: string;
  title: string;
  versions: VersionEntryDTO[];
  current_label: string;
  current_path?: string;
  total_size: number;
}

export interface VersionShowDTO {
  versions: VersionEntryDTO[];
  current_label: string;
  current_path: string;
}

export interface VersionPathsDTO {
  label: string;
  kind: "version" | "legacy_backup";
  source_path: string;
  current_path: string;
}

export interface DashboardStatsData {
  stats?: Record<string, unknown>;
  permissions?: Record<string, boolean>;
  items?: PaperIndexItem[];
  [key: string]: unknown;
}

export interface ResearchSource {
  path: string;
  physical_page: number;
  printed_page?: string;
  basis: "recorded" | "user_confirmed" | "exact_text";
  anchor?: string;
  sha256?: string;
}
export interface ResearchProvenance {
  status: string;
  basis: string;
  reason?: string;
  evidence?: Record<string, unknown>;
}
export interface ResearchRecord {
  id: string;
  paper_id: string;
  created_at: string;
  excerpt: string;
  usage: string;
  context: string;
  section: string;
  note: string;
  record_status: "active" | "corrected";
  verified: boolean;
  source?: ResearchSource;
  provenance: ResearchProvenance;
  matched_fields: string[];
  corrections: Array<{ id: string; correction: string; reason: string }>;
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

/** Machine fields a structured PFResult rejection carries on its Error.
 * Only the backend `error.code` and PFResult `data` (e.g. vector_state) —
 * never argv/stdout/stderr/query/text. Narrow with `in` before reading. */
export interface PfRejectionExtras {
  code?: unknown;
  data?: unknown;
  stdout?: unknown;
  exitCode?: unknown;
}

/** Real exit code from a transport rejection: rc0 authority rejection is
 * exit=0, a failed process carries its rc. Never parsed from user text. */
function transportExitCode(transportError: unknown): number | null {
  if (
    transportError !== null &&
    typeof transportError === "object" &&
    "exitCode" in transportError
  ) {
    const rc: unknown = transportError.exitCode;
    if (typeof rc === "number") return rc;
  }
  return transportError === null ? 0 : null;
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

  /** Evict cached reads scoped to a single paper without clearing global probes. */
  invalidatePaperScope(paperKey: string): void {
    const clean = paperKey.trim();
    if (!clean) {
      this.invalidateCache();
      return;
    }
    const candidates = new Set<string>([
      `paper-status:${clean}`,
      `paper-context:${clean}`,
    ]);
    for (const key of [...this._cache.keys()]) {
      if (candidates.has(key) || key.includes(`:${clean}:`)) {
        this._cache.delete(key);
      }
    }
    for (const key of [...this._inFlightReads.keys()]) {
      if (candidates.has(key) || key.includes(`:${clean}:`)) {
        this._inFlightReads.delete(key);
      }
    }
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

  /** Last completed streamed operation (child stderr/exit code/events), for
   * failure diagnostics. Null until the first streamed operation finishes.
   * The CLI's job files are the durable record; this is the process view. */
  lastStreamDiagnostics: StreamDiagnostics | null = null;

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

    const streamStartedAt = Date.now();
    traceRecord({
      ts: Date.now(),
      kind: "stream",
      op: `${operationId} ${commandIdentity(argv)}`,
      ok: undefined,
      epoch: this._epoch,
      detail: "start",
    });
    const wrappedOutcome = (async (): Promise<LongTaskOutcome> => {
      try {
        const outcome = await rawHandle.outcome;
        this.lastStreamDiagnostics = {
          operationId,
          argv,
          ok: outcome.ok,
          exitCode: outcome.exitCode,
          cancelled: outcome.cancelled,
          protocolFailure: outcome.protocolFailure,
          stderr: outcome.stderr ?? "",
          eventCount: outcome.events.length,
          lastEvent: outcome.events[outcome.events.length - 1] ?? null,
          finishedAt: Date.now(),
        };
        traceRecord({
          ts: Date.now(),
          kind: "stream",
          op: `${operationId} ${commandIdentity(argv)}`,
          ok: outcome.ok,
          ms: Date.now() - streamStartedAt,
          epoch: this._epoch,
          code: outcome.cancelled
            ? "cancelled"
            : outcome.protocolFailure
              ? "protocol_failure"
              : undefined,
          detail: `exit=${outcome.exitCode} events=${outcome.events.length}`,
        });
        if (!outcome.ok && !outcome.cancelled) {
          traceConsoleError({
            op: `${operationId} ${commandIdentity(argv)}`,
            stage: "stream",
            code: outcome.protocolFailure
              ? "protocol_failure"
              : "backend_error",
            exitCode: outcome.exitCode,
          });
        }
        return outcome;
      } catch (err: unknown) {
        const code = rejectionCode(err) ?? "transport_error";
        // The transport-level promise can reject (spawn/stream teardown).
        // Keep the failure reachable from the diagnostics surface, and emit
        // the single stream terminal record (fixed metadata only; a
        // user-cancelled stream is an expected state, never an error).
        this.lastStreamDiagnostics = {
          operationId,
          argv,
          ok: false,
          exitCode: null,
          cancelled: false,
          protocolFailure:
            err instanceof Error ? err.message : String(err ?? "unknown"),
          stderr: "",
          eventCount: 0,
          lastEvent: null,
          finishedAt: Date.now(),
        };
        traceRecord({
          ts: Date.now(),
          kind: "stream",
          op: `${operationId} ${commandIdentity(argv)}`,
          ok: false,
          ms: Date.now() - streamStartedAt,
          epoch: this._epoch,
          code,
          detail: "exit=? events=0",
        });
        traceConsoleError({
          op: `${operationId} ${commandIdentity(argv)}`,
          stage: "stream",
          code,
          exitCode: null,
        });
        throw err;
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
    options?: {
      expectedVersion?: string;
      minEngineVersion?: string;
      lastOperationExitCode?: number;
    }
  ): Promise<ProbeEnvelope> {
    const extraArgs: string[] = [];
    if (options?.expectedVersion) {
      extraArgs.push("--expected-version", options.expectedVersion);
    }
    if (options?.minEngineVersion) {
      extraArgs.push("--min-engine-version", options.minEngineVersion);
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
    const cacheKey = `probe:${module}:${options?.expectedVersion ?? ""}:${options?.minEngineVersion ?? ""}:${options?.lastOperationExitCode ?? ""}`;
    return this._cachedRead(cacheKey, 60000, async () => {
      return this._executePfResult<ProbeEnvelope>(
        ["probe", module, "--json", ...extraArgs],
        // A module probe walks every paper's lineage (measured: 25s on a
        // 969-paper vault, plus cold-import cost on the first run after an
        // install) — the 120s default reported a false failure there.
        { timeoutMs: 300000 }
      );
    });
  }

  async probeAll(options?: {
    expectedVersion?: string;
    minEngineVersion?: string;
  }): Promise<ProbeAllEnvelope> {
    const extraArgs: string[] = [];
    if (options?.expectedVersion) {
      extraArgs.push("--expected-version", options.expectedVersion);
    }
    if (options?.minEngineVersion) {
      extraArgs.push("--min-engine-version", options.minEngineVersion);
    }
    const cacheKey = `probe:all:${options?.expectedVersion ?? ""}:${options?.minEngineVersion ?? ""}`;
    return this._cachedRead(cacheKey, 60000, async () => {
      return this._executePfResult<ProbeAllEnvelope>(
        ["probe", "all", "--json", ...extraArgs],
        // `probe all` walks every module's lineage in one process.  Measured
        // 145s on a 969-paper vault with a fresh venv (bytecode compilation
        // dominates), so the old 120s default reported a false "检测失败"
        // for every module — the module probe got this budget already.
        { timeoutMs: 300000 }
      );
    });
  }
  /** Read managed runtime health without resolving or reading a Vault.
   *
   * One retry: the first status call after a fresh publish can fail on a cold
   * venv (bytecode compilation, an antivirus scan), and painting a working
   * runtime as broken is worse than a 500 ms delay.
   */
  async runtimeStatus(
    expectedVersion: string,
    options?: { minEngineVersion?: string }
  ): Promise<RuntimeStatus> {
    const argv = [
      "runtime",
      "status",
      "--expected-version",
      expectedVersion,
      ...(options?.minEngineVersion
        ? ["--min-engine-version", options.minEngineVersion]
        : []),
      "--json",
    ];
    try {
      return JSON.parse(
        await this._executeRaw(argv, { timeoutMs: 30000 })
      ) as RuntimeStatus;
    } catch (first) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      try {
        return JSON.parse(
          await this._executeRaw(argv, { timeoutMs: 30000 })
        ) as RuntimeStatus;
      } catch {
        throw first;
      }
    }
  }

  /** Open the external installer in a terminal. The plugin does not install
   * anything itself — the installer owns creation, verification and the
   * pointer; the UI only polls `runtimeStatus` afterwards. */
  launchRuntimeInstaller(
    action: "install" | "update" | "repair",
    version: string,
    options?: {
      allowUvDownload?: boolean;
      proxyUrl?: string;
      preferCnMirror?: boolean;
    }
  ): { ok: boolean; python?: string; error?: string; logPath?: string } {
    if (typeof this._transport.launchRuntimeInstaller !== "function") {
      return {
        ok: false,
        error: "This transport cannot launch the external installer.",
      };
    }
    return options
      ? this._transport.launchRuntimeInstaller(action, version, options)
      : this._transport.launchRuntimeInstaller(action, version);
  }

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
        const raw = await this._executeRaw(argv);
        return JSON.parse(raw);
      }
    );
  }

  // ── 3. Policy & Action Contract (action registry) ─────────────────────────

  /**
   * Execute a command expecting a PFResult envelope and unwrap data.
   */
  /** EVERY backend exec funnels through here — one trace point that sees
   * all frontend↔backend traffic (metadata only; see client/trace.ts). */
  private async _executeRaw(
    argv: string[],
    options?: ExecuteOptions
  ): Promise<string> {
    const startedAt = Date.now();
    const op = commandIdentity(argv);
    try {
      const raw = await this._transport.execute(argv, options);
      traceRecord({
        ts: Date.now(),
        kind: "exec",
        op,
        ok: true,
        ms: Date.now() - startedAt,
        epoch: this._epoch,
      });
      // Backend phase timing (sync attaches data.timing): surface WHERE the
      // time went, not just the round trip. Parsed only while tracing.
      if (isTraceEnabled()) {
        try {
          const timing = (
            JSON.parse(raw) as { data?: { timing?: Record<string, number> } }
          )?.data?.timing;
          if (timing && typeof timing === "object") {
            const compact = Object.entries(timing)
              .map(
                ([k, v]) =>
                  `${k.replace(/^sync\./, "")}=${Math.round(Number(v))}ms`
              )
              .join(" ");
            traceRecord({
              ts: Date.now(),
              kind: "exec",
              op: `${op} timing`,
              detail: compact.slice(0, 400),
            });
          }
        } catch {
          // stdout was not JSON (text mode) — nothing to surface.
        }
      }
      return raw;
    } catch (err: unknown) {
      const exitOf: unknown =
        err !== null && typeof err === "object" && "exitCode" in err
          ? err.exitCode
          : undefined;
      const exitCode = typeof exitOf === "number" ? exitOf : undefined;
      const codeOf: unknown =
        err !== null && typeof err === "object" && "code" in err
          ? err.code
          : undefined;
      traceRecord({
        ts: Date.now(),
        kind: "exec",
        op,
        ok: false,
        ms: Date.now() - startedAt,
        epoch: this._epoch,
        code:
          typeof codeOf === "string"
            ? codeOf
            : exitCode != null
              ? `rc${exitCode}`
              : "transport_error",
      });
      throw err;
    }
  }

  private async _executePfResult<T>(
    argv: string[],
    options?: ExecuteOptions,
    unwrapData = true
  ): Promise<T> {
    // Layer split: the Transport owns process/exit semantics (rejects
    // non-zero exits), this client owns PFResult machine-protocol
    // semantics. The Python config contract emits a STRUCTURED ok:false
    // PFResult on stdout together with rc=1/2 — so on a transport
    // rejection, recover the authority reason from err.stdout instead of
    // losing it to a generic "exit code 1" error (legacy config-client
    // behavior, preserved here).
    const startedAt = Date.now();
    const op = commandIdentity(argv);
    let raw: string;
    let transportError: unknown = null;
    try {
      raw = await this._executeRaw(argv, options);
    } catch (err: unknown) {
      const outOf: unknown =
        err instanceof Error && "stdout" in err ? err.stdout : null;
      const stdout = typeof outOf === "string" ? outOf : null;
      if (stdout === null || !stdout.trim()) {
        const code =
          err !== null &&
          typeof err === "object" &&
          "code" in err &&
          typeof err.code === "string"
            ? err.code
            : "transport_error";
        traceConsoleError({
          op,
          stage: "process",
          code,
          exitCode: transportExitCode(err),
        });
        throw err;
      }
      transportError = err;
      raw = stdout;
    }
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw) as unknown;
    } catch {
      // No valid authority payload: report the process failure only once.
      if (transportError) {
        traceConsoleError({
          op,
          stage: "process",
          code: "transport_error",
          exitCode: transportExitCode(transportError),
        });
        throw transportError;
      }
      traceRecord({
        ts: Date.now(),
        kind: "error",
        op,
        ok: false,
        ms: Date.now() - startedAt,
        epoch: this._epoch,
        code: "protocol_error",
      });
      traceConsoleError({
        op,
        stage: "protocol",
        code: "protocol_error",
        exitCode: 0,
      });
      throw new Error("Failed to parse PFResult JSON");
    }
    // PFResult recognition MUST catch ok:false even when `data` is absent
    // (bare rejection without a data key still carries code/message).
    if (parsed && typeof parsed === "object" && "ok" in parsed) {
      const envelope: { ok?: unknown; error?: unknown; data?: unknown } =
        parsed;
      const errCode: unknown =
        envelope.error !== null &&
        typeof envelope.error === "object" &&
        "code" in envelope.error
          ? envelope.error.code
          : undefined;
      const errMsg: unknown =
        envelope.error !== null &&
        typeof envelope.error === "object" &&
        "message" in envelope.error
          ? envelope.error.message
          : undefined;
      // Fail closed: a structured ok:false PFResult is an authority
      // rejection, never a null payload.
      if (envelope.ok === false) {
        const code = String(errCode || "backend_error");
        traceRecord({
          ts: Date.now(),
          kind: "error",
          op,
          ok: false,
          ms: Date.now() - startedAt,
          epoch: this._epoch,
          code,
        });
        // A completed diagnosis (doctor: ok:false, error null, data.checks
        // present) is a normal report the caller consumes — not a failure to
        // surface on the Console. search+PATH_NOT_FOUND is the expected
        // empty-DB state: trace ring keeps the machine code and the UI keeps
        // its card, no red log. Only other authority rejections log, with
        // the real exit code from the transport error (rc0 is exit=0).
        const hasAuthorityError =
          envelope.error !== null && envelope.error !== undefined;
        const isExpectedEmptyDb = op === "search" && code === "PATH_NOT_FOUND";
        const vectorState =
          envelope.data !== null &&
          typeof envelope.data === "object" &&
          "vector_state" in envelope.data
            ? envelope.data.vector_state
            : undefined;
        const isExpectedVectorState =
          op === "retrieve" &&
          code === "PRECONDITION_FAILED" &&
          (vectorState === "not_built" || vectorState === "stale");
        if (hasAuthorityError && !isExpectedEmptyDb && !isExpectedVectorState)
          traceConsoleError({
            op,
            stage: "pfresult",
            code,
            exitCode: transportExitCode(transportError),
          });
        const rejection = new Error(
          String(errMsg || errCode || "backend_error")
        );
        // Machine contract for structured rejections: the code and the
        // PFResult data (e.g. vector_state) survive on the thrown Error so
        // UI mapping can classify without scraping message text or stdout.
        // Never argv/stdout/stderr/query — only code + data.
        const extras: PfRejectionExtras =
          rejection as unknown as PfRejectionExtras;
        extras.code = code;
        extras.data = ("data" in envelope ? envelope.data : null) ?? null;
        extras.exitCode = transportExitCode(transportError);
        // Keep the raw PFResult so a caller that knows its command's
        // contract (doctor) can still read a completed report.
        extras.stdout = raw;
        throw rejection;
      }
      if (transportError) {
        // rc != 0 but the PFResult claims ok — protocol contradiction;
        // the process-level failure wins. Log ONCE at the outermost
        // terminal with the protocol code (D fix); the catch below must
        // not re-log a downgraded transport_error for the same operation.
        traceRecord({
          ts: Date.now(),
          kind: "error",
          op,
          ok: false,
          ms: Date.now() - startedAt,
          epoch: this._epoch,
          code: "protocol_contradiction",
        });
        traceConsoleError({
          op,
          stage: "protocol",
          code: "protocol_contradiction",
          exitCode: transportExitCode(transportError),
        });
        throw transportError;
      }
      // PFResult data is unwrapped; minimal envelopes retain their shape.
      if (unwrapData && "data" in envelope) return envelope.data as T;
      return parsed as T;
    }
    // Preflight and other legacy surfaces return valid bare JSON.
    if (transportError) {
      traceConsoleError({
        op,
        stage: "process",
        code: "transport_error",
        exitCode: transportExitCode(transportError),
      });
      throw transportError;
    }
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
  async credentialAvailable(
    service: "embedding" | "ocr" | "easyscholar"
  ): Promise<boolean> {
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
    kind: "ocr" | "embedding" | "easyscholar",
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

  /** #174 RC: ChromaDB -> sqlite-vec backend migration. */
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

  // ── Display-fulltext version authority (Ticket 07 step 6 item 6) ──────
  /** Version discovery + manifest interpretation + canonical artifact
   * paths — Python authority. The UI renders these DTOs and may read the
   * returned `source_path` for presentation/diff only. */
  async versionsList(): Promise<PaperVersionInfoDTO[]> {
    const data = await this._executePfResult<{
      papers?: PaperVersionInfoDTO[];
    }>(["versions", "list", "--json"]);
    return Array.isArray(data?.papers) ? data.papers : [];
  }

  /** One paper's manifest. A paper with no manifest is a legitimate empty
   * state (Python returns ok with empty lists). */
  async versionsShow(key: string): Promise<VersionShowDTO> {
    const data = await this._executePfResult<VersionShowDTO>([
      "versions",
      "show",
      "--key",
      key,
      "--json",
    ]);
    return {
      versions: Array.isArray(data?.versions) ? data.versions : [],
      current_label: data?.current_label ?? "",
      current_path: data?.current_path ?? "",
    };
  }

  /** Legacy pre-rebuild backup recognition (filename + timestamp semantics
   * are Python-owned). */
  async versionsBackups(key: string): Promise<VersionEntryDTO[]> {
    const data = await this._executePfResult<{
      backups?: VersionEntryDTO[];
    }>(["versions", "backups", "--key", key, "--json"]);
    return Array.isArray(data?.backups) ? data.backups : [];
  }

  /** Canonical artifact paths for a label (current label when omitted). */
  async versionsPaths(key: string, label?: string): Promise<VersionPathsDTO> {
    const argv = ["versions", "paths", "--key", key];
    if (label) argv.push("--label", label);
    argv.push("--json");
    return this._executePfResult<VersionPathsDTO>(argv);
  }

  /** Display-only restore: Python performs the copy AND persists
   * restore_provenance (authority mutation → epoch invalidation). */
  async versionsRestore(
    key: string,
    label: string
  ): Promise<{
    target_path: string;
    label: string;
    provenance_persisted: boolean;
  }> {
    try {
      const data = await this._executePfResult<{
        target_path?: string;
        label?: string;
        provenance_persisted?: boolean;
      }>(["versions", "restore", "--key", key, "--label", label, "--json"]);
      if (data?.provenance_persisted === false) {
        traceConsoleError({
          op: "versions.restore.provenance",
          stage: "result",
          code: "restore.provenance_not_persisted",
          exitCode: 0,
        });
      }
      return {
        target_path: data?.target_path ?? "",
        label: data?.label ?? label,
        // restored BYTES are authoritative; provenance is best-effort
        // metadata and this flag reports the truth.
        provenance_persisted: data?.provenance_persisted === true,
      };
    } finally {
      this.invalidateCache();
    }
  }

  /** Reset live display fulltext back to canonical fulltext and clear restore_provenance. */
  async versionsResetLive(key: string): Promise<VersionsResetLiveResultDTO> {
    try {
      const data = await this._executePfResult<
        Partial<VersionsResetLiveResultDTO>
      >(["versions", "reset-live", "--key", key, "--json"]);
      return {
        intent: data?.intent ?? "versions-reset-live",
        key: data?.key ?? key,
        source_path: data?.source_path ?? "",
        target_path: data?.target_path ?? "",
        provenance_cleared: data?.provenance_cleared === true,
      };
    } finally {
      this.invalidateCache();
    }
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
    try {
      const data = await this._executePfResult<{ changed?: boolean }>([
        "note",
        "set-flag",
        "--key",
        key,
        "--field",
        field,
        "--value",
        value ? "true" : "false",
        "--json",
      ]);
      return { changed: data?.changed === true };
    } finally {
      // Frozen client-core invariant: an authority mutation settles by
      // advancing the epoch — stale in-flight reads (probe/reconcile/
      // action descriptors) can never resurrect across the boundary.
      this.invalidateCache();
    }
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
    const raw = await this._executeRaw(["--version"]);
    return raw.trim().replace(/^paperforge\s+/, "");
  }

  /** Explicit diagnostic read (`doctor --json`). No cache — a user-invoked
   * check must always hit the authority. */
  async doctor(): Promise<Record<string, unknown>> {
    // `doctor` exits 1 with ok:false and NO error whenever any check fails:
    // that is a completed diagnosis, not an authority rejection. Return the
    // report (flagged ok:false) instead of discarding it as "backend_error".
    try {
      return await this._executePfResult(["doctor", "--json"]);
    } catch (err: unknown) {
      const stdout = (err as { stdout?: unknown } | null)?.stdout;
      const report = parseDoctorReport(
        typeof stdout === "string" ? stdout : null
      );
      if (report) return report;
      throw err;
    }
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

  async listActions(): Promise<ActionDescriptor[]> {
    return this._cachedRead("action:list", 300000, async () => {
      const data = await this._executePfResult<{
        actions?: ActionDescriptor[];
      }>(["action", "list", "--json"]);
      return Array.isArray(data?.actions) ? data.actions : [];
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
  ): Promise<ActionPreflightDTO> {
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
    const localBusy =
      desc?.execution_mode === "stream" && this.isOperationActive();
    if (
      localBusy ||
      (desc?.availability && desc.availability !== ACTION_AVAILABLE)
    ) {
      const availability = localBusy ? "busy" : desc!.availability;
      const reason = localBusy
        ? "Another operation is already active"
        : desc?.availability_reason;
      traceRecord({
        ts: Date.now(),
        kind: "error",
        op: `action.${req.action_id}`,
        ok: false,
        code: availability === "busy" ? "action.busy" : "action.unavailable",
      });
      return {
        ok: false,
        payload: {
          ok: false,
          action_id: req.action_id,
          availability,
          availability_reason: reason,
          error: {
            code:
              availability === "busy" ? "action.busy" : "action.unavailable",
            message: reason || availability,
            details: {},
          },
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
      try {
        const handle = this.streamOperation(
          `action.${req.action_id}`,
          argv,
          streamOptions
        );
        const outcome = await handle.outcome;
        // streamOperation owns the single Console terminal; this adapter only
        // preserves a safe machine-readable rejection for action consumers.
        const terminalEv = outcome.events.find((event) =>
          ["result", "error", "cancelled"].includes(event.event)
        );
        let payload =
          (terminalEv?.result as Record<string, unknown> | null) ?? null;
        if (!outcome.ok && (outcome.protocolFailure || !payload)) {
          const code = outcome.cancelled
            ? "action.cancelled"
            : outcome.protocolFailure
              ? "protocol_failure"
              : "transport_error";
          payload = {
            ok: false,
            error: {
              code,
              message: outcome.cancelled
                ? "Operation cancelled"
                : "Backend operation ended without a valid terminal result",
            },
          };
        }
        return {
          ok: outcome.ok,
          payload,
          exitCode: outcome.exitCode ?? (outcome.ok ? 0 : 1),
          cancelled: outcome.cancelled,
        };
      } catch (err) {
        return {
          ok: false,
          payload: {
            ok: false,
            error: {
              code: rejectionCode(err) ?? "transport_error",
              message:
                err instanceof Error
                  ? err.message
                  : "Operation failed to start",
            },
          },
          exitCode: transportExitCode(err) ?? 1,
        };
      }
    }

    let raw: string;
    let exitCode = 0;
    try {
      try {
        raw = await this._executeRaw(argv);
      } catch (err: unknown) {
        const failureOut: unknown =
          err !== null && typeof err === "object" && "stdout" in err
            ? err.stdout
            : undefined;
        const failureExit: unknown =
          err !== null && typeof err === "object" && "exitCode" in err
            ? err.exitCode
            : undefined;
        if (typeof failureOut !== "string" || !failureOut.trim()) {
          throw err;
        }
        raw = failureOut;
        exitCode = typeof failureExit === "number" ? failureExit : 1;
      }
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(raw);
        if (
          !payload ||
          typeof payload !== "object" ||
          typeof payload.ok !== "boolean"
        ) {
          throw new Error("Expected a PFResult with boolean ok");
        }
      } catch {
        traceConsoleError({
          op: `action.${actionReq.action_id}`,
          stage: "result",
          code: "protocol_error",
          exitCode,
        });
        return {
          ok: false,
          payload: {
            ok: false,
            error: {
              code: "protocol_error",
              message: "Invalid action PFResult JSON",
            },
          },
          exitCode,
        };
      }
      if (exitCode !== 0 && payload.ok) {
        // Single terminal: the inner throw is caught below, which logs the
        // outermost failure once with the protocol code — never re-log here
        // and never downgrade to transport_error (D fix).
        throw Object.assign(
          new Error("Action reported success after a non-zero exit"),
          { exitCode, protocolContradiction: true }
        );
      }
      if (payload.ok !== true) {
        const perrCode: unknown =
          payload.error !== null &&
          typeof payload.error === "object" &&
          "code" in payload.error
            ? payload.error.code
            : undefined;
        traceConsoleError({
          op: `action.${actionReq.action_id}`,
          stage: "result",
          code: String(perrCode || "backend_error"),
          exitCode,
        });
      }
      return { ok: payload.ok === true, payload, exitCode };
    } catch (err: unknown) {
      const exitOf: unknown =
        err !== null && typeof err === "object" && "exitCode" in err
          ? err.exitCode
          : undefined;
      const exitNum = typeof exitOf === "number" ? exitOf : 1;
      const isContradiction: unknown =
        err !== null &&
        typeof err === "object" &&
        "protocolContradiction" in err
          ? err.protocolContradiction
          : undefined;
      const errCodeOf: unknown =
        err !== null && typeof err === "object" && "code" in err
          ? err.code
          : undefined;
      // NO_PYTHON is the expected setup state (no published runtime), not a
      // failure: keep the machine code, suppress the Console, no new registry.
      const isExpectedSetup = errCodeOf === "NO_PYTHON";
      if (!isExpectedSetup) {
        traceConsoleError({
          op: `action.${actionReq.action_id}`,
          stage: "result",
          code: isContradiction ? "protocol_contradiction" : "transport_error",
          exitCode: exitNum,
        });
      }
      return {
        ok: false,
        payload: isContradiction
          ? {
              ok: false,
              error: {
                code: "protocol_contradiction",
                message: err instanceof Error ? err.message : String(err),
              },
            }
          : isExpectedSetup
            ? {
                ok: false,
                error: {
                  code: "NO_PYTHON",
                  message: err instanceof Error ? err.message : String(err),
                },
              }
            : {
                ok: false,
                error: {
                  code: "transport_error",
                  message: err instanceof Error ? err.message : String(err),
                },
              },
        exitCode: exitNum,
      };
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
    try {
      return await this._executePfResult(argv, undefined, false);
    } finally {
      this.invalidateCache();
    }
  }

  // ── 5. Queries & Search Gateway ───────────────────────────────────────────

  /** JSONL is read on every call; independent of metadata/vector caches. */
  async readingRecords(
    query: string,
    includeHistory = false
  ): Promise<{ matches: ResearchRecord[] }> {
    const argv = ["reading-log", "--search", query, "--json"];
    if (includeHistory) argv.push("--include-history");
    return this._executePfResult(argv);
  }

  async saveReadingRecord(
    paper: string,
    fields: Record<string, string>,
    source?: ResearchSource
  ): Promise<{ id: string; provenance: ResearchProvenance }> {
    const argv = ["reading-log", "--write", paper, "--json"];
    for (const field of ["excerpt", "usage", "context", "section", "note"]) {
      if (fields[field]) argv.push("--" + field, fields[field]);
    }
    if (source) argv.push("--source-json", JSON.stringify(source));
    return this._executePfResult(argv);
  }

  async correctReadingRecord(
    record: ResearchRecord,
    correction: string,
    reason: string
  ): Promise<{ jsonl_id: string }> {
    return this._executePfResult([
      "reading-log",
      "--correct",
      record.id,
      "--paper",
      record.paper_id,
      "--correction",
      correction,
      "--reason",
      reason,
      "--json",
    ]);
  }

  async readingRecordSource(
    record: ResearchRecord
  ): Promise<ResearchSource & { provenance: ResearchProvenance }> {
    return this._executePfResult([
      "reading-log",
      "--source-check",
      record.id,
      "--paper",
      record.paper_id,
      "--json",
    ]);
  }

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
      // Structured path: PFResult rejections keep code/data for the
      // dashboard card mapping; unwrapMatches still parses the data shape.
      const data = await this._executePfResult<unknown>([
        "search",
        cleanQuery,
        "--limit",
        String(limit),
        "--json",
      ]);
      return unwrapMatches({ data });
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
      const data = await this._executePfResult<unknown>(argv);
      return unwrapMatches({ data });
    });
  }

  /** `read` prints TEXT (no `--json`): the matched passage verbatim. */
  async read(
    key: string,
    find: string,
    source: "auto" | "fulltext" | "pdf" = "auto"
  ): Promise<string> {
    const raw = await this._executeRaw([
      "read",
      key,
      "--find",
      find,
      "--source",
      source,
    ]);
    return raw;
  }

  async paperStatus(query: string): Promise<PaperStatusDTO> {
    return this._cachedRead(`paper-status:${query}`, 30000, async () => {
      const raw = await this._executeRaw(["paper-status", query, "--json"]);
      return JSON.parse(raw) as PaperStatusDTO;
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
      return ocrRowsFromPayload(await this._executePfResult(argv));
    });
  }

  // ── 6. Authority Actions (Render Quality) ──────────────────────────────────

  /** #06 corrective C: Render authority exits rc=1 with a STRUCTURED JSON
   * rejection on stdout (FAILED audit, R_GATE_FAILED, STALE_PROPOSAL,
   * STALE_REVIEWED_PLAN, …). The transport rejects non-zero exits, but the
   * Python decision must survive as a normal authority response — only a
   * genuine spawn/protocol failure may surface as an exception. */
  private async _executeStructuredJson<T>(argv: string[]): Promise<T> {
    let raw: string;
    let exitCode: number | null = 0;
    let transportFailed = false;
    try {
      raw = await this._executeRaw(argv);
    } catch (err: unknown) {
      transportFailed = true;
      exitCode = transportExitCode(err);
      const stdout =
        err !== null && typeof err === "object" && "stdout" in err
          ? err.stdout
          : null;
      if (typeof stdout !== "string" || !stdout.trim()) {
        traceConsoleError({
          op: commandIdentity(argv),
          stage: "process",
          code: rejectionCode(err) ?? "transport_error",
          exitCode,
        });
        throw err;
      }
      raw = stdout;
    }
    let parsed: unknown;
    let code: string | null = null;
    try {
      parsed = JSON.parse(raw);
      if (
        parsed === null ||
        typeof parsed !== "object" ||
        Array.isArray(parsed)
      ) {
        code = "protocol_error";
      }
    } catch {
      code = "protocol_error";
    }
    if (
      !code &&
      transportFailed &&
      parsed &&
      typeof parsed === "object" &&
      "ok" in parsed &&
      parsed.ok === true
    ) {
      code = "protocol_contradiction";
    }
    if (code) {
      traceConsoleError({
        op: commandIdentity(argv),
        stage: "protocol",
        code,
        exitCode,
      });
      throw Object.assign(
        new Error("Backend returned invalid or contradictory authority JSON"),
        {
          code,
          exitCode,
        }
      );
    }
    // Negative audit reports and mutation rejections are authority values,
    // not PFResult failures; preserve them, including nonzero-exit reports.
    return parsed as T;
  }

  async renderAudit(key?: string): Promise<RenderAuditDTO> {
    const argv = ["render", "audit"];
    if (key) argv.push(key);
    argv.push("--json");
    return this._executeStructuredJson<RenderAuditDTO>(argv);
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

  async promoteR(
    key: string,
    objectIds: string[] = []
  ): Promise<AuthorityMutationResult> {
    const argv = ["render", "promote-r", key, ...objectIds, "--json"];
    try {
      return await this._executeStructuredJson<AuthorityMutationResult>(argv);
    } finally {
      this.invalidateCache();
    }
  }

  async acceptProposal(
    key: string,
    label: string,
    planHash: string
  ): Promise<AuthorityMutationResult> {
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

  // ── 7. Non-destructive Sidecar PDF Annotations & Diagnostic Read ───────

  async getPdfContext(paperKey: string): Promise<PaperPdfContextDto> {
    return this._executePfResult<PaperPdfContextDto>(
      ["annotations", "pdf-info", paperKey, "--json"],
      { timeoutMs: 30000 }
    );
  }

  async listAnnotations(paperKey: string): Promise<PdfAnnotationDto[]> {
    const data = await this._executePfResult<{
      annotations?: PdfAnnotationDto[];
    }>(["annotations", "list", paperKey, "--json"]);
    return Array.isArray(data?.annotations) ? data.annotations : [];
  }

  async addAnnotation(
    paperKey: string,
    input: {
      page: number;
      rects: number[][];
      kind?: AnnotationKind;
      color?: AnnotationColor | string;
      intent?: AnnotationIntent | string;
      exact_text?: string;
      comment?: string;
      tags?: string[];
      style?: AnnotationStyleDto;
    }
  ): Promise<PdfAnnotationDto> {
    const argv: string[] = [
      "annotations",
      "add",
      paperKey,
      "--page",
      String(input.page),
      "--rects-json",
      JSON.stringify(input.rects),
      "--kind",
      input.kind ?? "highlight",
      "--color",
      input.color ?? "yellow",
      "--intent",
      input.intent ?? "general",
      "--exact-text",
      input.exact_text ?? "",
      "--comment",
      input.comment ?? "",
      "--tags-json",
      JSON.stringify(input.tags ?? []),
    ];
    if (input.style && Object.keys(input.style).length > 0) {
      argv.push("--style-json", JSON.stringify(input.style));
    }
    argv.push("--json");
    try {
      return await this._executePfResult<PdfAnnotationDto>(argv, {
        timeoutMs: 30000,
      });
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async updateAnnotation(
    paperKey: string,
    annId: string,
    patch: {
      color?: AnnotationColor | string;
      intent?: AnnotationIntent | string;
      comment?: string;
      tags?: string[];
      style?: AnnotationStyleDto;
      rects?: number[][];
    }
  ): Promise<PdfAnnotationDto> {
    const argv: string[] = ["annotations", "update", paperKey, annId];
    if (patch.color !== undefined) argv.push("--color", patch.color);
    if (patch.intent !== undefined) argv.push("--intent", patch.intent);
    if (patch.comment !== undefined) argv.push("--comment", patch.comment);
    if (patch.tags !== undefined)
      argv.push("--tags-json", JSON.stringify(patch.tags));
    if (patch.style !== undefined)
      argv.push("--style-json", JSON.stringify(patch.style));
    if (patch.rects !== undefined)
      argv.push("--rects-json", JSON.stringify(patch.rects));
    argv.push("--json");
    try {
      return await this._executePfResult<PdfAnnotationDto>(argv);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async deleteAnnotation(
    paperKey: string,
    annId: string
  ): Promise<{ deleted: boolean; ann_id: string; paper_id: string }> {
    try {
      return await this._executePfResult<{
        deleted: boolean;
        ann_id: string;
        paper_id: string;
      }>(["annotations", "delete", paperKey, annId, "--json"]);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async promoteAnnotation(
    paperKey: string,
    annId: string,
    opts?: { usage?: string; project?: string }
  ): Promise<Record<string, unknown>> {
    const argv: string[] = ["annotations", "promote", paperKey, annId];
    if (opts?.usage) argv.push("--usage", opts.usage);
    if (opts?.project) argv.push("--project", opts.project);
    argv.push("--json");
    try {
      return await this._executePfResult<Record<string, unknown>>(argv);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async readDiagnosticFulltext(
    paperKey: string,
    maxChars = 80000
  ): Promise<DiagnosticFulltextDto> {
    return this._executePfResult<DiagnosticFulltextDto>(
      [
        "annotations",
        "fulltext-preview",
        paperKey,
        "--max-chars",
        String(maxChars),
        "--json",
      ],
      { timeoutMs: 30000 }
    );
  }

  async adoptAnnotation(
    paperKey: string,
    annId: string
  ): Promise<PdfAnnotationDto> {
    try {
      return await this._executePfResult<PdfAnnotationDto>([
        "annotations",
        "adopt",
        paperKey,
        annId,
        "--json",
      ]);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async clearAgentAnnotations(
    paperKey: string,
    lens?: string
  ): Promise<ClearAgentAnnotationsResultDto> {
    const argv: string[] = ["annotations", "clear-agent", paperKey];
    if (lens) argv.push("--lens", lens);
    argv.push("--json");
    try {
      return await this._executePfResult<ClearAgentAnnotationsResultDto>(argv);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  // ── 8. Living Paper Memory & Base Table Snapshots ────────────────────────

  async getMemoryCard(paperKey: string): Promise<PaperMemoryCardDto> {
    return this._executePfResult<PaperMemoryCardDto>([
      "memory-card",
      "get",
      paperKey,
      "--json",
    ]);
  }

  async refineMemoryCard(
    paperKey: string,
    facet: string,
    content: string
  ): Promise<PaperMemoryCardDto> {
    try {
      const data = await this._executePfResult<
        { card?: PaperMemoryCardDto } & PaperMemoryCardDto
      >([
        "memory-card",
        "refine",
        paperKey,
        "--facet",
        facet,
        "--content",
        content,
        "--json",
      ]);
      return data.card ?? data;
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async getMemoryCardHistory(
    paperKey: string,
    facet?: string
  ): Promise<MemoryHistoryEntryDto[]> {
    const argv = ["memory-card", "history", paperKey];
    if (facet) {
      argv.push("--facet", facet);
    }
    argv.push("--json");
    const data = await this._executePfResult<{
      history?: MemoryHistoryEntryDto[];
    }>(argv);
    return Array.isArray(data?.history) ? data.history : [];
  }

  async clearMemoryFacet(
    paperKey: string,
    facet: string
  ): Promise<ClearMemoryFacetResultDto> {
    try {
      return await this._executePfResult<ClearMemoryFacetResultDto>([
        "memory-card",
        "clear",
        paperKey,
        "--facet",
        facet,
        "--json",
      ]);
    } finally {
      this.invalidatePaperScope(paperKey);
    }
  }

  async getBaseTableSnapshot(): Promise<BaseTableSnapshotDto> {
    return this._executePfResult<BaseTableSnapshotDto>([
      "memory-card",
      "base-snapshot",
      "--json",
    ]);
  }

  // ── 9. Unified Vault Upgrade & Low-Memory ControlDaemon (ADR-018) ────────

  async vaultUpgradePlan(): Promise<VaultUpgradePlanDto> {
    return this._executePfResult<VaultUpgradePlanDto>([
      "upgrade",
      "--plan",
      "--json",
    ]);
  }

  async vaultUpgradeApply(opts?: {
    fastCutover?: boolean;
    backfillOcr?: boolean;
    quarantineResiduals?: boolean;
    quarantineIds?: string[];
    noRebuildDb?: boolean;
  }): Promise<VaultUpgradeApplyResultDto> {
    const argv = ["upgrade", "--apply", "--json"];
    if (opts?.fastCutover) argv.push("--fast-cutover");
    if (opts?.backfillOcr) argv.push("--backfill-ocr");
    if (opts?.quarantineResiduals) argv.push("--quarantine-residuals");
    if (opts?.quarantineIds?.length) {
      argv.push("--quarantine-ids", opts.quarantineIds.join(","));
    }
    if (opts?.noRebuildDb) argv.push("--no-rebuild-db");
    try {
      return await this._executePfResult<VaultUpgradeApplyResultDto>(argv, {
        timeoutMs: 180000,
      });
    } finally {
      this.invalidateCache();
    }
  }

  async vaultUpgradeHeal(opts?: {
    priorityKey?: string;
    limit?: number;
    backfillOcr?: boolean;
  }): Promise<VaultUpgradeHealResultDto> {
    const argv = ["upgrade", "--heal", "--json"];
    if (opts?.priorityKey) argv.push("--priority-key", opts.priorityKey);
    if (typeof opts?.limit === "number" && opts.limit > 0) {
      argv.push("--limit", String(opts.limit));
    }
    if (opts?.backfillOcr) argv.push("--backfill-ocr");
    try {
      return await this._executePfResult<VaultUpgradeHealResultDto>(argv, {
        timeoutMs: 300000,
      });
    } finally {
      this.invalidateCache();
    }
  }

  async vaultUpgradeRollback(): Promise<VaultUpgradeRollbackResultDto> {
    try {
      return await this._executePfResult<VaultUpgradeRollbackResultDto>(
        ["upgrade", "--rollback", "--json"],
        { timeoutMs: 120000 }
      );
    } finally {
      this.invalidateCache();
    }
  }

  onDaemonEvent(listener: (event: DaemonPushEvent) => void): () => void {
    if (typeof this._transport.onDaemonEvent === "function") {
      return this._transport.onDaemonEvent(listener);
    }
    return () => {};
  }

  async daemonHealth(): Promise<DaemonHealthDto | null> {
    if (typeof this._transport.rpc !== "function") return null;
    const raw = await this._transport.rpc({ op: "daemon.health" });
    return JSON.parse(raw) as DaemonHealthDto;
  }

  async daemonSubmitJob(
    kind: "sync" | "ocr" | "embed" | "upgrade.heal",
    opts?: { priorityKey?: string; backfillOcr?: boolean; argv?: string[] }
  ): Promise<{
    accepted: boolean;
    coalesced?: boolean;
    reason?: string;
    job?: DaemonJobDto;
  }> {
    if (typeof this._transport.rpc !== "function") {
      return { accepted: false, reason: "rpc_unavailable" };
    }
    const raw = await this._transport.rpc({
      op: "job.submit",
      kind,
      priority_key: opts?.priorityKey ?? null,
      backfill_ocr: opts?.backfillOcr ?? false,
      argv: opts?.argv ?? null,
    });
    return JSON.parse(raw);
  }

  async daemonListJobs(includeRecent = true): Promise<{
    active: DaemonJobDto[];
    recent: DaemonJobDto[];
  }> {
    if (typeof this._transport.rpc !== "function") {
      return { active: [], recent: [] };
    }
    const raw = await this._transport.rpc({
      op: "job.list",
      include_recent: includeRecent,
    });
    return JSON.parse(raw);
  }

  async daemonCancelJob(
    jobId: string
  ): Promise<{ ok: boolean; status?: string; reason?: string }> {
    if (typeof this._transport.rpc !== "function") {
      return { ok: false, reason: "rpc_unavailable" };
    }
    const raw = await this._transport.rpc({
      op: "job.cancel",
      job_id: jobId,
    });
    return JSON.parse(raw);
  }

  async daemonListNotices(
    includeAcked = false
  ): Promise<{ notices: DaemonNoticeDto[] }> {
    if (typeof this._transport.rpc !== "function") {
      return { notices: [] };
    }
    const raw = await this._transport.rpc({
      op: "notice.list",
      include_acked: includeAcked,
    });
    return JSON.parse(raw);
  }

  async daemonAckNotice(noticeId: string): Promise<boolean> {
    if (typeof this._transport.rpc !== "function") return false;
    const raw = await this._transport.rpc({
      op: "notice.ack",
      notice_id: noticeId,
    });
    const parsed = JSON.parse(raw) as { acked?: boolean };
    return Boolean(parsed?.acked);
  }

  shutdownTransport(): void {
    (
      this._transport as unknown as { shutdownDaemon?: () => void }
    )?.shutdownDaemon?.();
  }

  async shutdownTransportAsync(): Promise<void> {
    const t = this._transport as unknown as {
      shutdownDaemonAsync?: () => Promise<void>;
      shutdownDaemon?: () => void;
    };
    if (typeof t?.shutdownDaemonAsync === "function") {
      await t.shutdownDaemonAsync();
    } else {
      t?.shutdownDaemon?.();
    }
  }

  async daemonSubmitRuntimeUpdate(
    version: string
  ): Promise<{ accepted: boolean; coalesced?: boolean; reason?: string }> {
    if (typeof this._transport.rpc !== "function") {
      return { accepted: false, reason: "rpc_unavailable" };
    }
    const raw = await this._transport.rpc({
      op: "job.submit",
      kind: "runtime.update",
      version,
    });
    return JSON.parse(raw);
  }

  /** Fast Zero-Python Zotero data directory + collections detector (`zotero detect --json`). */
  async zoteroDetect(customPath?: string): Promise<ZoteroDetectDto> {
    const argv = ["zotero", "detect"];
    if (customPath && customPath.trim()) {
      argv.push("--path", customPath.trim());
    }
    argv.push("--json");
    const data = await this._executePfResult<Partial<ZoteroDetectDto>>(argv, {
      timeoutMs: 15000,
    });
    return {
      found: Boolean(data?.found),
      zotero_dir: String(data?.zotero_dir ?? ""),
      total_papers: Number(data?.total_papers ?? 0),
      collections: Array.isArray(data?.collections) ? data!.collections : [],
    };
  }

  /** Live provider probe returning detected dimension & latency (`embed test-connection --json`). */
  async embedTestConnection(): Promise<{
    model: string;
    base_url: string;
    dimension: number;
    latency_ms: number;
  }> {
    return this._executePfResult(["embed", "test-connection", "--json"], {
      timeoutMs: 35000,
    });
  }

  /** Quick OCR token & endpoint connectivity probe (`ocr test-connection --json`). */
  async ocrTestConnection(): Promise<{
    passed: boolean;
    level: number;
    error?: string;
    fix?: string;
  }> {
    return this._executePfResult(["ocr", "test-connection", "--json"], {
      timeoutMs: 35000,
    });
  }
}

/** A doctor PFResult that ran to completion but found failing checks:
 *  ok:false, no error, data.checks present. Anything else is not a report. */
function parseDoctorReport(raw: string | null): Record<string, unknown> | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as {
      ok?: unknown;
      error?: unknown;
      data?: { checks?: unknown } | null;
    };
    if (
      parsed.ok === false &&
      (parsed.error === null || parsed.error === undefined) &&
      parsed.data &&
      Array.isArray(parsed.data.checks)
    ) {
      return { ...(parsed.data as Record<string, unknown>), ok: false };
    }
  } catch {
    /* not JSON */
  }
  return null;
}
