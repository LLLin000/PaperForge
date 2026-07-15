// ── View type, icon, SVG ──

export const VIEW_TYPE_PAPERFORGE = "paperforge-status";
export const PF_ICON_ID = "paperforge";
export const PF_RIBBON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>`;

// ── Action definitions ──

export interface ActionDef {
  id: string;
  title: string;
  desc?: string;
  icon?: string;
  cmd: string;
  args?: string[];
  needsKey?: boolean;
  needsFilter?: boolean;
  okMsg?: string;
  disabled?: boolean;
  disabledMsg?: string;
}

export const ACTIONS: ActionDef[] = [
  {
    id: "paperforge-sync",
    title: "Sync Library",
    desc: "Pull new references from Zotero and generate literature notes",
    icon: "\u21BB",
    cmd: "sync",
    okMsg: "Sync complete",
  },
  {
    id: "paperforge-ocr",
    title: "Run OCR",
    desc: "Extract full text and figures from PDFs via PaddleOCR",
    icon: "\u229E",
    cmd: "ocr",
    okMsg: "OCR started",
  },
  {
    id: "paperforge-doctor",
    title: "Run Doctor",
    desc: "Verify PaperForge setup \u2014 check configs, Zotero, paths, and index health",
    icon: "\u2695",
    cmd: "doctor",
    okMsg: "Doctor complete",
  },
  {
    id: "paperforge-repair",
    title: "Repair Issues",
    desc: "Fix three-way state divergence, path errors, and rebuild index",
    icon: "\u21BA",
    cmd: "repair",
    args: ["--fix", "--fix-paths"],
    okMsg: "Repair complete",
  },
  {
    id: "paperforge-ocr-redo",
    title: "Redo OCR",
    desc: "Re-run OCR for papers marked ocr_redo: true",
    icon: "\u21BA",
    cmd: "ocr",
    args: ["redo"],
    okMsg: "OCR redo started",
  },
];

// ── Settings ──

export interface PaperForgeSettings {
  python_path: string;
  vault_path: string;
  setup_complete: boolean;
  auto_update: boolean;
  auto_update_on_startup: boolean;
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
  selected_skill_platform: string;
  vector_db_api_key: string;
  vector_db_api_base: string;
  vector_db_api_model: string;
  last_seen_version: string;
  capabilityState: Record<string, ProbeEnvelope>;
  _python_path_stale?: boolean;
  [key: string]: unknown;
}

export const DEFAULT_SETTINGS: PaperForgeSettings = {
  vault_path: "",
  setup_complete: false,
  auto_update: true,
  auto_update_on_startup: true,
  agent_platform: "opencode",
  language: "",
  paddleocr_api_key: "",
  zotero_data_dir: "",
  python_path: "",
  features: {
    memory_layer: true,
    vector_db: false,
  },
  selected_skill_platform: "opencode",
  vector_db_api_key: "",
  vector_db_api_base: "",
  vector_db_api_model: "text-embedding-3-small",
  frozen_skills: {},
  system_dir: "",
  resources_dir: "",
  literature_dir: "",
  base_dir: "",
  capabilityState: {},
  last_seen_version: "",
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
  for (const key of ["do_ocr", "analyze", "ocr_status", "ocr_redo", "deep_reading_status"]) {
    if (Object.prototype.hasOwnProperty.call(fm, key)) merged[key] = fm[key];
  }
  return merged;
}

export function patchEntryWorkflowState(entry: any, patch: Partial<WorkflowState>): any {
  return entry ? { ...entry, ...patch } : entry;
}

// ── Capability probe types (schema-v1) ──

export const SCHEMA_VERSION = 1;

export type CapabilityModule = "installation" | "help" | "library" | "ocr" | "memory" | "maintenance";

export const CAPABILITY_MODULES: readonly CapabilityModule[] = [
  "installation",
  "library",
  "ocr",
  "memory",
  "maintenance",
  "help",
] as const;

export type CapabilityState = "unknown" | "unavailable" | "missing_input" | "needs_action" | "limited" | "ready";
export type ActivityState = "idle" | "running";
export type Severity = "unknown" | "ok" | "warning" | "error";

export interface ActionPrimary {
  verb: string;
  label: string;
  destructive: boolean;
  destructive_scope: string | null;
  destructive_effect: string | null;
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
  updated_at: string;
  ttl_seconds: number;
}

const VALID_CAPABILITY_STATES: readonly string[] = ["unknown", "unavailable", "missing_input", "needs_action", "limited", "ready"];
const VALID_SEVERITIES: readonly string[] = ["unknown", "ok", "warning", "error"];
const VALID_ACTIVITY_STATES: readonly string[] = ["idle", "running"];

function isValidActionPrimary(p: unknown): p is ActionPrimary {
  if (!p || typeof p !== "object" || Array.isArray(p)) return false;
  const a = p as Record<string, unknown>;
  if (typeof a.verb !== "string") return false;
  if (typeof a.label !== "string") return false;
  if (typeof a.destructive !== "boolean") return false;
  if (a.destructive_scope !== null && typeof a.destructive_scope !== "string") return false;
  if (a.destructive_effect !== null && typeof a.destructive_effect !== "string") return false;
  if (typeof a.confirmation_required !== "boolean") return false;
  if (a.confirmation_prompt !== null && typeof a.confirmation_prompt !== "string") return false;
  if (typeof a.command !== "string") return false;
  if (typeof a.scope !== "string") return false;
  if (typeof a.scope_count !== "number") return false;
  return true;
}

/** Build a full probe action (non-destructive, probe verb). */
export function probeAction(module: string): ActionPrimary {
  return {
    verb: "probe",
    label: "Check",
    destructive: false,
    destructive_scope: null,
    destructive_effect: null,
    confirmation_required: false,
    confirmation_prompt: null,
    command: `probe ${module}`,
    scope: module,
    scope_count: 1,
  };
}

/** Build a full setup action. */
export function setupAction(): ActionPrimary {
  return {
    verb: "setup",
    label: "Open Setup Wizard",
    destructive: false,
    destructive_scope: null,
    destructive_effect: null,
    confirmation_required: false,
    confirmation_prompt: null,
    command: "setup",
    scope: "installation",
    scope_count: 1,
  };
}

/**
 * Validate that a parsed JSON value is a valid ProbeEnvelope.
 * When expectedModule is supplied, also checks module field matches.
 * Never reconstructs or coerces — passes validated object through unchanged.
 */
export function isValidEnvelope(raw: unknown, expectedModule?: string): raw is ProbeEnvelope {
  if (!raw || typeof raw !== "object") return false;
  const e = raw as Record<string, unknown>;

  if (e.schema_version !== 1) return false;
  if (typeof e.module !== "string" || !e.module) return false;
  if (!CAPABILITY_MODULES.includes(e.module as CapabilityModule)) return false;
  if (expectedModule !== undefined && e.module !== expectedModule) return false;
  if (typeof e.capability_state !== "string" || !VALID_CAPABILITY_STATES.includes(e.capability_state)) return false;
  if (typeof e.severity !== "string" || !VALID_SEVERITIES.includes(e.severity)) return false;
  if (typeof e.activity_state !== "string" || !VALID_ACTIVITY_STATES.includes(e.activity_state)) return false;

  // activity_label: null or string (required)
  if (e.activity_label !== null && typeof e.activity_label !== "string") return false;

  // activity_progress: null or {current:number, total:number} (required)
  if (e.activity_progress !== null) {
    if (typeof e.activity_progress !== "object") return false;
    const ap = e.activity_progress as Record<string, unknown>;
    if (typeof ap.current !== "number" || typeof ap.total !== "number") return false;
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

  return true;
}

/** Unknown envelope — all modules get verb=probe; setup verb is backend-only. */
export function createUnknownEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION, module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: `${module}.no_probe`, text: `${module} has not been probed yet.` },
    action: { primary: probeAction(module) },
    notices: [],
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}

export function createStaleEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION, module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: `${module}.stale`, text: `Cached probe data for ${module} is stale.` },
    action: { primary: probeAction(module) },
    notices: [],
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}

export function createInvalidEnvelope(module: CapabilityModule): ProbeEnvelope {
  return {
    schema_version: SCHEMA_VERSION, module,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: `${module}.invalid_response`, text: `Probe response for ${module} was invalid.` },
    action: { primary: probeAction(module) },
    notices: [],
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
export function classifyCapabilityAction(
  envelope: ProbeEnvelope
): { kind: 'setup' | 'probe' | 'action'; verb: string; label: string } {
  const primary = envelope.action?.primary;
  const verb = primary?.verb ?? 'probe';
  const label = primary?.label ?? verb;
  if (verb === 'setup' || verb === 'set_config' || verb === 'update') {
    return { kind: 'setup', verb, label };
  }
  if (verb === 'probe') {
    return { kind: 'probe', verb, label };
  }
  return { kind: 'action', verb, label };
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

    if (!raw || typeof raw !== 'object') {
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
