/**
 * Probe / capability wire DTOs (schema-v2, #84).
 *
 * Ticket 07 follow-up (frontend interface completion): these are CLIENT-layer
 * wire types, not Obsidian-plugin constants. The client owns them so any
 * host (Obsidian today, other thin clients later) can consume the same
 * contract; `constants.ts` re-exports them for plugin-internal imports.
 */

export type CapabilityState =
  | "unknown"
  | "unavailable"
  | "missing_input"
  | "needs_action"
  | "limited"
  | "ready";
export type ActivityState = "idle" | "running";
export type Severity = "unknown" | "ok" | "warning" | "error";

export type UserState =
  | "checking"
  | "ready"
  | "not_enabled"
  | "setup_required"
  | "action_required"
  | "detection_failed";

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
  // T8 (#169): `command` DELETED — no backend command strings.
  scope: string;
  scope_count: number;
  execution_mode?: "result" | "stream";
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
  /* #135: structured module facts for the settings panel — the single
     source of truth for info-card rows (api key, db, build progress). */
  details?: {
    api_key_configured?: boolean;
    paper_count_db?: number;
    paper_count_index?: number;
    build_state?: { status?: string; current?: number; total?: number };
  };
}

export interface ProbeAllEnvelope {
  schema_version: number;
  module: "all";
  updated_at: string;
  modules: Record<string, ProbeEnvelope>;
}
