// ── View type, icon, SVG ──

export const VIEW_TYPE_PAPERFORGE = "paperforge-status";
export const VIEW_TYPE_OCR_WORKSPACE = "paperforge-ocr-workspace";
export const PF_ICON_ID = "paperforge";
export const PF_RIBBON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`;

// ── Action definitions ──

export interface ActionDef {
  id: string;
  title: string;
  desc?: string;
  icon?: string;
  /** T8 (#169): `cmd` renamed — the field is a dashboard tool command id,
   * never an action-policy table (registry owns action dispatch). */
  commandId: string;
  args?: string[];
  needsKey?: boolean;
  needsFilter?: boolean;
  okMsg?: string;
  disabled?: boolean;
  disabledMsg?: string;
  /**
   * Spawn timeout in ms. Defaults are derived from needsKey/needsFilter
   * (30s/60s), otherwise 600s. OCR runs one full poll cycle of up to
   * 15 minutes (60 x 15s), so it must exceed that or the child is killed
   * mid-queue and every run only completes a couple of papers.
   */
  timeoutMs?: number;
}

export const ACTIONS: ActionDef[] = [
  {
    id: "paperforge-sync",
    title: "Sync Library",
    desc: "Pull new references from Zotero and generate literature notes",
    icon: "\u21BB",
    commandId: "sync",
    okMsg: "Sync complete",
  },
  {
    id: "paperforge-ocr",
    title: "Run OCR",
    desc: "Extract full text and figures from PDFs via PaddleOCR",
    icon: "\u229E",
    commandId: "ocr",
    okMsg: "OCR started",
    // One full poll cycle runs up to 15 minutes (60 x 15s); per-paper
    // timeouts are enforced inside run_ocr, so the spawn timeout must cover
    // the whole batch, not one paper.
    timeoutMs: 1_800_000,
  },
  {
    id: "paperforge-doctor",
    title: "Run Doctor",
    desc: "Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health",
    icon: "\u2695",
    commandId: "doctor",
    okMsg: "Doctor complete",
  },
  {
    id: "paperforge-repair",
    title: "Repair Issues",
    desc: "Fix three-way state divergence, path errors, and rebuild index",
    icon: "\u21BA",
    commandId: "repair",
    args: ["--fix", "--fix-paths"],
    okMsg: "Repair complete",
  },
  {
    id: "paperforge-ocr-redo",
    title: "Redo OCR",
    desc: "Re-run OCR for papers marked ocr_redo: true",
    icon: "\u21BA",
    commandId: "ocr",
    args: ["redo"],
    okMsg: "OCR redo started",
  },
];

// ── Settings ──

export interface PaperForgeSettings {
  python_path: string;
  vault_path: string;
  features: Record<string, boolean>;
  frozen_skills: Record<string, string>;
  system_dir: string;
  resources_dir: string;
  literature_dir: string;
  base_dir: string;
  agent_platform: string;
  language: string;
  paddleocr_api_key: string;
  zotero_data_dir: string;
  vector_db_api_key: string;
  vector_db_api_base: string;
  vector_db_api_model: string;
  last_seen_version: string;
  capabilityState: Record<string, ProbeEnvelope>;
  autoSyncEnabled?: boolean;
  autoSyncIntervalSeconds?: number;
  _python_path_stale?: boolean;
  _migrated_keys?: string[];
  _migration_warnings?: string[];
  _paddleocr_configured?: boolean;
  _vector_db_configured?: boolean;
  [key: string]: unknown;
}

export const DEFAULT_SETTINGS: PaperForgeSettings = {
  vault_path: "",
  frozen_skills: {},
  language: "",
  paddleocr_api_key: "",
  zotero_data_dir: "",
  agent_platform: "opencode",
  python_path: "",
  features: {
    memory_layer: true,
    vector_db: false,
  },
  vector_db_api_key: "",
  vector_db_api_base: "",
  vector_db_api_model: "text-embedding-3-small",
  system_dir: "",
  resources_dir: "",
  literature_dir: "",
  base_dir: "",
  capabilityState: {},
  last_seen_version: "",
  _migrated_keys: [],
  _migration_warnings: [],
  autoSyncEnabled: true,
  autoSyncIntervalSeconds: 120,
  _paddleocr_configured: false,
  _vector_db_configured: false,
  _setup_complete: false,
};

// ── Workflow state helpers ──

export interface WorkflowState {
  [key: string]: unknown;
}

export function overlayEntryWorkflowState(app: any, entry: any): WorkflowState {
  if (!entry || !entry.note_path) return entry;
  const noteFile = app.vault.getAbstractFileByPath(entry.note_path);
  if (!noteFile) return entry;
  const cache = app.metadataCache.getFileCache(noteFile);
  const fm = cache && cache.frontmatter;
  if (!fm) return entry;
  const merged = { ...entry };
  for (const key of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ]) {
    if (Object.prototype.hasOwnProperty.call(fm, key)) merged[key] = fm[key];
  }
  return merged;
}

export function patchEntryWorkflowState(
  entry: any,
  patch: Partial<WorkflowState>
): any {
  return entry ? { ...entry, ...patch } : entry;
}

// ── Capability probe types (schema-v2, #84) ──

export const SCHEMA_VERSION = 2;
declare function __omp_shell(expr: string): boolean;

export type CapabilityModule =
  | "installation"
  | "help"
  | "library"
  | "ocr"
  | "memory"
  | "maintenance";

export const CAPABILITY_MODULES: readonly CapabilityModule[] = [
  "installation",
  "library",
  "ocr",
  "memory",
  "maintenance",
  "help",
] as const;

export type CapabilityState =
  | "unknown"
  | "unavailable"
  | "missing_input"
  | "needs_action"
  | "limited"
  | "ready";
export type ActivityState = "idle" | "running";
export type Severity = "unknown" | "ok" | "warning" | "error";

// #84: Six user-facing states (PRD §2.3)
export type UserState =
  | "checking"
  | "ready"
  | "not_enabled"
  | "setup_required"
  | "action_required"
  | "detection_failed";

const _VALID_USER_STATES_SET = new Set<UserState>([
  "checking",
  "ready",
  "not_enabled",
  "setup_required",
  "action_required",
  "detection_failed",
]);

export type CapabilityKind = "required" | "optional";
export type SafetyClass = "safe" | "destructive" | "irreversible";

export interface ActionPrimary {
  action_id: string;
  verb: string;
  label: string;
  availability: string;
  safety_class: SafetyClass;
  preservation_facts: string[];
  replacement_facts: string[];
  interruptible: boolean;
  confirmation_required: boolean;
  confirmation_prompt: string | null;
  command: string;
  scope: string;
  scope_count: number;
}

export interface ProbeReason {
  code: string;
  text: string;
}

export interface ProbeAction {
  primary: ActionPrimary | null;
}

export interface ProbeNotice {
  level: string;
  message: string;
}

export interface ProbeActivityProgress {
  current: number;
  total: number;
}

export interface MaintenanceItem {
  module: string;
  capability_state: CapabilityState;
  severity: Severity;
  activity_state: ActivityState;
  activity_label: string | null;
  activity_progress: ProbeActivityProgress | null;
  reason_code: string;
  reason_text: string;
  action: ActionPrimary | null;
  /* #84: optional user-facing fields on maintenance items */
  user_state?: UserState;
  user_impact?: string | null;
  maintenance_eligible?: boolean;
}

export interface ProbeEnvelope {
  schema_version: number;
  module: string;
  capability_state: CapabilityState;
  activity_state: ActivityState;
  activity_label: string | null;
  activity_progress: ProbeActivityProgress | null;
  severity: Severity;
  reason: ProbeReason;
  action: ProbeAction;
  notices: ProbeNotice[];
  /* #84: user-facing presentation fields */
  user_state: UserState;
  capability_kind: CapabilityKind;
  maintenance_eligible: boolean;
  user_visible_failure: boolean;
  user_impact: string | null;
  updated_at: string;
  ttl_seconds: number;
  /* #97: OCR pipeline version fields (from Python backend) */
  pipeline_version?: string;
  last_pipeline_version?: string;
  pipeline_version_summary?: { stale?: number };
  items?: MaintenanceItem[];
}

const _VALID_CAPABILITY_STATES = new Set<string>([
  "unknown",
  "unavailable",
  "missing_input",
  "needs_action",
  "limited",
  "ready",
]);
const _VALID_SEVERITIES = new Set<string>([
  "unknown",
  "ok",
  "warning",
  "error",
]);
const _VALID_ACTIVITY_STATES = new Set<string>(["idle", "running"]);
const _VALID_SAFETY_CLASSES = new Set<string>([
  "safe",
  "destructive",
  "irreversible",
]);

function isValidActionPrimary(p: unknown): p is ActionPrimary {
  if (!p || typeof p !== "object" || Array.isArray(p)) return false;
  const a = p as Record<string, unknown>;
  if (typeof a.action_id !== "string" || !a.action_id) return false;
  if (typeof a.verb !== "string") return false;
  if (typeof a.label !== "string") return false;
  if (typeof a.availability !== "string") return false;
  if (
    typeof a.safety_class !== "string" ||
    !_VALID_SAFETY_CLASSES.has(a.safety_class as string)
  )
    return false;
  if (!Array.isArray(a.preservation_facts)) return false;
  if (!Array.isArray(a.replacement_facts)) return false;
  if (typeof a.interruptible !== "boolean") return false;
  if (typeof a.confirmation_required !== "boolean") return false;
  if (
    a.confirmation_prompt !== null &&
    typeof a.confirmation_prompt !== "string"
  )
    return false;
  if (typeof a.command !== "string") return false;
  if (typeof a.scope !== "string") return false;
  if (typeof a.scope_count !== "number") return false;
  return true;
}

export function probeAction(module: string): ActionPrimary {
  return {
    action_id: module + ".probe",
    verb: "probe",
    label: "Retry",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: true,
    confirmation_required: false,
    confirmation_prompt: null,
    command: "probe " + module,
    scope: module,
    scope_count: 1,
  };
}

export function setupAction(): ActionPrimary {
  return {
    action_id: "foundation.setup",
    verb: "setup",
    label: "Open Setup Wizard",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: true,
    confirmation_required: false,
    confirmation_prompt: null,
    command: "setup",
    scope: "installation",
    scope_count: 1,
  };
}

export function isValidEnvelope(
  raw: unknown,
  expectedModule?: string
): raw is ProbeEnvelope {
  if (!raw || typeof raw !== "object") return false;
  const e = raw as Record<string, unknown>;

  if (e.schema_version !== SCHEMA_VERSION) return false;
  if (typeof e.module !== "string" || !e.module) return false;
  if (!CAPABILITY_MODULES.includes(e.module as CapabilityModule)) return false;
  if (expectedModule !== undefined && e.module !== expectedModule) return false;
  if (
    typeof e.capability_state !== "string" ||
    !_VALID_CAPABILITY_STATES.has(e.capability_state as string)
  )
    return false;
  if (
    typeof e.activity_state !== "string" ||
    !_VALID_ACTIVITY_STATES.has(e.activity_state as string)
  )
    return false;
  if (
    typeof e.user_state !== "string" ||
    !_VALID_USER_STATES_SET.has(e.user_state as UserState)
  )
    return false;
  if (typeof e.capability_kind !== "string") return false;
  if (typeof e.maintenance_eligible !== "boolean") return false;
  if (typeof e.user_visible_failure !== "boolean") return false;
  if (e.user_impact !== null && typeof e.user_impact !== "string") return false;
  if (e.activity_label !== null && typeof e.activity_label !== "string")
    return false;
  if (e.activity_progress !== null) {
    if (typeof e.activity_progress !== "object") return false;
    const ap = e.activity_progress as Record<string, unknown>;
    if (typeof ap.current !== "number" || typeof ap.total !== "number")
      return false;
  }
  if (!Array.isArray(e.notices)) return false;
  if (!e.reason || typeof e.reason !== "object") return false;
  const r = e.reason as Record<string, unknown>;
  if (typeof r.code !== "string" || typeof r.text !== "string") return false;
  if (!e.action || typeof e.action !== "object") return false;
  const a = e.action as Record<string, unknown>;
  if (a.primary !== null && !isValidActionPrimary(a.primary)) return false;
  if (typeof e.updated_at !== "string" || !e.updated_at) return false;
  if (typeof e.ttl_seconds !== "number") return false;

  if (e.module === "maintenance") {
    if (a.primary !== null) return false;
    if (!Array.isArray(e.items)) return false;
    for (const item of e.items) {
      if (!item || typeof item !== "object") return false;
      const it = item as Record<string, unknown>;
      const validMods = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof it.capability_state !== "string" ||
        !_VALID_CAPABILITY_STATES.has(it.capability_state as string)
      )
        return false;
      if (
        typeof it.severity !== "string" ||
        !_VALID_SEVERITIES.has(it.severity as string)
      )
        return false;
      if (
        typeof it.activity_state !== "string" ||
        !_VALID_ACTIVITY_STATES.has(it.activity_state as string)
      )
        return false;
      if (it.activity_label !== null && typeof it.activity_label !== "string")
        return false;
      if (it.activity_progress !== null) {
        if (typeof it.activity_progress !== "object") return false;
        const iap = it.activity_progress as Record<string, unknown>;
        if (typeof iap.current !== "number" || typeof iap.total !== "number")
          return false;
      }
      if (typeof it.reason_code !== "string" || !it.reason_code) return false;
      if (typeof it.reason_text !== "string") return false;
      if (it.action !== null && !isValidActionPrimary(it.action)) return false;
    }
  }
  return true;
}

export function createUnknownEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION,
    module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: module + ".no_probe",
      text: module + " has not been probed yet.",
    },
    action: { primary: module === "maintenance" ? null : probeAction(module) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: false,
    user_visible_failure: false,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}

export function createStaleEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION,
    module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: module + ".stale",
      text: "Cached probe data for " + module + " is stale.",
    },
    action: { primary: module === "maintenance" ? null : probeAction(module) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: false,
    user_visible_failure: false,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}

export function createInvalidEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION,
    module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: module + ".invalid_response",
      text: "Probe response for " + module + " was invalid.",
    },
    action: { primary: module === "maintenance" ? null : probeAction(module) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: false,
    user_visible_failure: false,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}

export function isEnvelopeStale(e: ProbeEnvelope): boolean {
  // Running state is always fresh — don't erase in-progress probes
  if (e.activity_state === "running") return false;
  if (e.ttl_seconds <= 0) return true;
  const updated = new Date(e.updated_at).getTime();
  if (isNaN(updated)) return true;
  return Date.now() - updated > e.ttl_seconds * 1000;
}

export function isReadyEnvelope(e: ProbeEnvelope): boolean {
  return e.capability_state === "ready" && e.action.primary === null;
}

/**
 * Classify a capability envelope's primary action.
 * - 'set_config' and 'update' verbs → 'setup' kind (dispatch to setup flow)
 * - 'probe' verb → 'probe' kind (trigger a re-probe)
 * - all others → 'action' kind (execute the action directly)
 */
export function classifyCapabilityAction(envelope: ProbeEnvelope): {
  kind: "setup" | "probe" | "action";
  verb: string;
  label: string;
} {
  const primary = envelope.action?.primary;
  const verb = primary?.verb ?? "probe";
  const label = primary?.label ?? verb;
  if (verb === "setup" || verb === "set_config" || verb === "update") {
    return { kind: "setup", verb, label };
  }
  if (verb === "probe") {
    return { kind: "probe", verb, label };
  }
  return { kind: "action", verb, label };
}

/**
 * Compute a summary from a capability-state map.
 * Returns { coreReady: true } when all REAL_PROBED_MODULES are 'ready',
 * otherwise { coreReady: false, attentionModules: [...] } with unknown
 * degraded modules counted as attention.
 */
export function computeModuleSummary(
  stateMap: Record<string, ProbeEnvelope>,
  realModules: readonly string[]
): { coreReady: boolean; attentionModules: string[] } {
  const attentionModules: string[] = [];
  for (const mod of realModules) {
    const env = stateMap[mod];
    if (!env || !isReadyEnvelope(env)) {
      attentionModules.push(mod);
    }
  }
  return {
    coreReady: attentionModules.length === 0,
    attentionModules,
  };
}

/**
 * Validate a persisted capability-state map before render.
 * - Missing required modules → replaced with unknown envelope
 * - Malformed entries (failing isValidEnvelope) → replaced with invalid envelope
 * - Stale entries (past TTL) → replaced with stale envelope via createStaleEnvelope
 * Valid entries pass through unchanged.
 */
export function validatePersistedEnvelopes(
  stateMap: Record<string, unknown>,
  allModules: readonly string[]
): Record<string, ProbeEnvelope> {
  const result: Record<string, ProbeEnvelope> = {};

  for (const mod of allModules) {
    const raw = stateMap[mod];

    if (!raw || typeof raw !== "object") {
      result[mod] = createUnknownEnvelope(mod as CapabilityModule);
      continue;
    }

    if (!isValidEnvelope(raw, mod)) {
      result[mod] = createInvalidEnvelope(mod as CapabilityModule);
      continue;
    }

    if (isEnvelopeStale(raw as ProbeEnvelope)) {
      result[mod] = createStaleEnvelope(mod as CapabilityModule);
      continue;
    }

    result[mod] = raw as ProbeEnvelope;
  }

  return result;
}
