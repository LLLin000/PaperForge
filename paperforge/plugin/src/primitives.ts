/**
 * PaperForge shared UI primitives (#85).
 *
 * Shallow, concrete DOM helpers matching paperforge/plugin/DESIGN.md.
 * All functions use Obsidian's createEl pattern and theme variables.
 * No framework, no global store, no generic component library.
 */

import {
  type ActionPrimary,
  type UserState,
  type ProbeEnvelope,
  type MaintenanceItem,
} from "./constants";

// ██████████████████████████████████████████████████████████████████████
// 1. Status Badge — 6 user-state variants (DESIGN.md §5)
// ██████████████████████████████████████████████████████████████████████

const BADGE_CLASS: Record<UserState, string> = {
  checking: "pf-badge pf-badge--checking",
  ready: "pf-badge pf-badge--ready",
  not_enabled: "pf-badge pf-badge--not-enabled",
  setup_required: "pf-badge pf-badge--setup-required",
  action_required: "pf-badge pf-badge--action-required",
  detection_failed: "pf-badge pf-badge--detection-failed",
};

const BADGE_LABEL_DEFAULT: Record<UserState, string> = {
  checking: "Checking",
  ready: "Ready",
  not_enabled: "Not Enabled",
  setup_required: "Setup Required",
  action_required: "Action Required",
  detection_failed: "Detection Failed",
};

/** Render a six-state badge on the given parent element. */
export function renderStatusBadge(
  parent: HTMLElement,
  state: UserState,
  label?: string
): HTMLElement {
  const el = parent.createEl("span", {
    cls: BADGE_CLASS[state],
    text: label ?? BADGE_LABEL_DEFAULT[state],
    attr: { role: "status" },
  });
  return el;
}

// ██████████████████████████████████████████████████████████████████████
// 2. Activity Row — separate from Module Status (DESIGN.md §5)
// ██████████████████████████████████████████████████████████████████████

export interface ActivityRowConfig {
  label: string;
  /** Bounded progress: {current, total}. Omit for indeterminate (spinner). */
  progress?: { current: number; total: number } | null;
  scope?: string | null;
  stopLabel?: string;
  onStop?: () => void;
}

/** Render an activity row with optional progress bar and stop button. */
export function renderActivityRow(
  parent: HTMLElement,
  config: ActivityRowConfig
): HTMLElement {
  const row = parent.createEl("div", { cls: "pf-activity-row" });

  const label = row.createEl("span", {
    cls: "pf-activity-label",
    text: config.label,
  });

  if (config.progress && config.progress.total > 0) {
    const bar = row.createEl("div", { cls: "pf-activity-bar" });
    const pct = Math.round(
      (config.progress.current / config.progress.total) * 100
    );
    bar.createEl("div", {
      cls: "pf-activity-bar-fill",
      attr: {
        style: `width: ${pct}%`,
        role: "progressbar",
        "aria-valuenow": String(config.progress.current),
        "aria-valuemin": "1",
        "aria-valuemax": String(config.progress.total),
      },
    });
    row.createEl("span", {
      cls: "pf-activity-count",
      text: `${config.progress.current}/${config.progress.total}`,
    });
  } else {
    // Indeterminate spinner
    const spinner = row.createEl("span", { cls: "pf-activity-spinner" });
    spinner.setAttr("aria-label", "In progress");
  }

  if (config.scope) {
    row.createEl("span", {
      cls: "pf-activity-scope",
      text: config.scope,
    });
  }

  if (config.stopLabel && config.onStop) {
    const stop = row.createEl("button", {
      cls: "pf-activity-stop",
      text: config.stopLabel,
    });
    stop.addEventListener("click", config.onStop);
    stop.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        config.onStop?.();
      }
    });
  }

  return row;
}

// ██████████████████████████████████████████████████████████████████████
// 3. Action Button — state-aware primary action (DESIGN.md §5)
// ██████████████████████████████████████████████████████████████████████

export interface ActionButtonConfig {
  label: string;
  disabled?: boolean;
  loading?: boolean;
  onClick: () => void;
}

/** Render a state-aware action button. */
export function renderActionButton(
  parent: HTMLElement,
  config: ActionButtonConfig
): HTMLElement {
  const btn = parent.createEl("button", {
    cls: "pf-action-btn",
    text: config.loading ? "…" : config.label,
  });
  if (config.disabled || config.loading) {
    btn.setAttr("disabled", "true");
    btn.classList.add("pf-action-btn--disabled");
  }
  if (config.loading) {
    btn.classList.add("pf-action-btn--loading");
  }
  if (!config.disabled && !config.loading) {
    btn.addEventListener("click", config.onClick);
    btn.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        config.onClick();
      }
    });
  }
  return btn;
}

// ██████████████████████████████████████████████████████████████████████
// 4. Disclosure — collapsible section (DESIGN.md §5)
// ██████████████████████████████████████████████████████████████████████

export interface DisclosureConfig {
  title: string;
  initiallyOpen?: boolean;
  /** Content builder called with the body element. */
  renderBody: (body: HTMLElement) => void;
}

/** Render a collapsible disclosure section. */
export function renderDisclosure(
  parent: HTMLElement,
  config: DisclosureConfig
): HTMLElement {
  const container = parent.createEl("div", { cls: "pf-disclosure" });

  const header = container.createEl("button", {
    cls: "pf-disclosure-header",
    attr: {
      "aria-expanded": String(config.initiallyOpen ?? false),
      type: "button",
    },
  });
  header.createEl("span", { cls: "pf-disclosure-icon", text: "▶" });
  header.createEl("span", {
    cls: "pf-disclosure-title",
    text: config.title,
  });

  const body = container.createEl("div", {
    cls: `pf-disclosure-body${config.initiallyOpen ? " pf-disclosure-body--open" : ""}`,
  });
  config.renderBody(body);

  header.addEventListener("click", () => {
    const isOpen = header.getAttribute("aria-expanded") === "true";
    header.setAttribute("aria-expanded", String(!isOpen));
    body.classList.toggle("pf-disclosure-body--open", !isOpen);
    const icon = header.querySelector(".pf-disclosure-icon");
    if (icon) icon.textContent = isOpen ? "▶" : "▼";
  });

  return container;
}

// ██████████████████████████████████████████████████████████████████████
// 5. Error Anatomy — User-visible Problem (DESIGN.md §5, PRD §5)
// ██████████████████████████████████████████████████████████████████████

export interface ErrorAnatomyConfig {
  whatHappened: string;
  impact: string;
  nextStep: string;
  reasonCode?: string;
  onCopyDiagnostic?: () => void;
  /** Override default labels (for i18n). */
  impactLabel?: string;
  nextLabel?: string;
  copyLabel?: string;
}

/** Render a structured user-visible problem. */
export function renderErrorAnatomy(
  parent: HTMLElement,
  config: ErrorAnatomyConfig
): HTMLElement {
  const container = parent.createEl("div", { cls: "pf-error-anatomy" });

  container.createEl("div", {
    cls: "pf-error-title",
    text: config.whatHappened,
  });

  const impact = container.createEl("div", { cls: "pf-error-impact" });
  impact.createEl("span", {
    cls: "pf-error-impact-label",
    text: "Impact: ",
  });
  impact.createEl("span", { text: config.impact });

  if (config.reasonCode) {
    container.createEl("div", {
      cls: "pf-error-code",
      text: config.reasonCode,
    });
  }

  const next = container.createEl("div", { cls: "pf-error-next" });
  next.createEl("span", {
    cls: "pf-error-next-label",
    text: (config.nextLabel || "Next:") + " ",
  });
  next.createEl("span", { text: config.nextStep });

  if (config.onCopyDiagnostic) {
    const btn = container.createEl("button", {
      cls: "pf-error-copy-diagnostic",
      text: config.copyLabel || "Copy Diagnostic Information",
    });
    btn.addEventListener("click", config.onCopyDiagnostic);
  }

  return container;
}

// ██████████████████████████████████████████████████████████████████████
// 6. Configuration Summary (DESIGN.md §5)
// ██████████████████████████████████████████████████████████████████████

export interface ConfigSummaryItem {
  label: string;
  value: string;
  /** If true, value is a credential; render "Configured"/"Not configured". */
  isCredential?: boolean;
}

export interface ConfigSummaryConfig {
  items: ConfigSummaryItem[];
  onChangeLabel: string;
  onChange: () => void;
}

/** Render a read-only configuration summary with a Change action. */
export function renderConfigurationSummary(
  parent: HTMLElement,
  config: ConfigSummaryConfig
): HTMLElement {
  const container = parent.createEl("div", { cls: "pf-config-summary" });

  for (const item of config.items) {
    const row = container.createEl("div", { cls: "pf-config-row" });
    row.createEl("span", {
      cls: "pf-config-label",
      text: item.label,
    });
    const displayValue = item.isCredential
      ? item.value
        ? "Configured"
        : "Not configured"
      : item.value;
    row.createEl("span", {
      cls: `pf-config-value${item.isCredential ? (item.value ? " pf-config-value--ok" : " pf-config-value--muted") : ""}`,
      text: displayValue,
    });
  }

  const changeBtn = container.createEl("button", {
    cls: "pf-config-change-btn",
    text: config.onChangeLabel,
  });
  changeBtn.addEventListener("click", config.onChange);

  return container;
}

// ██████████████████████████████████████████████████████████████████████
// 7. Impact Confirmation (DESIGN.md §5, PRD §6)
// ██████████████████████████████████████████████████████████████████████

export interface ImpactConfirmationConfig {
  affectedScope: string;
  scopeCount: number;
  replacedOutputs: string[];
  preservedData: string[];
  interruptible: boolean;
  confirmLabel: string;
  cancelLabel: string;
  replacedLabel?: string;
  preservedLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Render an impact confirmation panel. */
export function renderImpactConfirmation(
  parent: HTMLElement,
  config: ImpactConfirmationConfig
): HTMLElement {
  const container = parent.createEl("div", {
    cls: "pf-impact-confirm",
    attr: { role: "alertdialog", "aria-modal": "true" },
  });

  container.createEl("div", {
    cls: "pf-impact-confirm-title",
    text: `${config.confirmLabel} ${config.affectedScope}`,
  });

  if (config.replacedOutputs.length > 0) {
    const section = container.createEl("div", { cls: "pf-impact-section" });
    section.createEl("div", {
      cls: "pf-impact-label",
      text: config.replacedLabel || "Will be replaced:",
    });
    for (const item of config.replacedOutputs) {
      section.createEl("div", { cls: "pf-impact-item", text: item });
    }
  }

  if (config.preservedData.length > 0) {
    const section = container.createEl("div", { cls: "pf-impact-section" });
    section.createEl("div", {
      cls: "pf-impact-label",
      text: config.preservedLabel || "Will be preserved:",
    });
    for (const item of config.preservedData) {
      section.createEl("div", { cls: "pf-impact-item", text: item });
    }
  }

  if (!config.interruptible) {
    container.createEl("div", {
      cls: "pf-impact-interruptible",
      text: "This action cannot be stopped once started.",
    });
  }

  const actions = container.createEl("div", { cls: "pf-impact-actions" });
  const cancel = actions.createEl("button", {
    cls: "pf-impact-cancel",
    text: config.cancelLabel,
  });
  cancel.addEventListener("click", config.onCancel);
  const confirm = actions.createEl("button", {
    cls: "pf-impact-confirm-btn",
    text: config.confirmLabel,
  });
  confirm.addEventListener("click", config.onConfirm);

  return container;
}

// ██████████████████████████████████████████████████████████████████████
// 8. Support Diagnostic builder (PRD §5)
// ██████████████████████████████████████████████████████████████████████

export interface DiagnosticInput {
  pluginVersion: string;
  backendVersion?: string;
  modules: Array<{
    module: string;
    userState: UserState;
    lastSuccessAt?: string | null;
    reasonCode?: string;
    actionId?: string;
    errorExcerpt?: string;
  }>;
}

/** Build a privacy-safe Support Diagnostic text block. */
export function buildSupportDiagnostic(input: DiagnosticInput): string {
  const lines: string[] = [];
  lines.push("=== PaperForge Support Diagnostic ===");
  lines.push(`Time: ${new Date().toISOString()}`);
  lines.push(`Plugin: ${input.pluginVersion}`);
  if (input.backendVersion) {
    lines.push(`Backend: ${input.backendVersion}`);
  }

  lines.push("");
  lines.push("--- Module Status ---");
  for (const mod of input.modules) {
    lines.push(`${mod.module}: ${mod.userState}`);
    if (mod.reasonCode) lines.push(`  reason: ${mod.reasonCode}`);
    if (mod.actionId) lines.push(`  action: ${mod.actionId}`);
    if (mod.lastSuccessAt) lines.push(`  last-success: ${mod.lastSuccessAt}`);
    if (mod.errorExcerpt) lines.push(`  error: ${mod.errorExcerpt}`);
  }

  lines.push("");
  lines.push("=== End ===");
  return lines.join("\n");
}

/** Copy Support Diagnostic to clipboard and announce. */
export function copySupportDiagnostic(
  diagnostic: string,
  onSuccess?: () => void
): void {
  navigator.clipboard
    .writeText(diagnostic)
    .then(() => {
      onSuccess?.();
    })
    .catch((err: unknown) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", err);
    });
}

// ██████████████████████████████████████████████████████████████████████
// 9. Refresh + Last Known Status helpers
// ██████████████████████████████████████████████████████████████████████

export interface LastKnownState {
  /** The last successful ProbeEnvelope for this module. */
  envelope: ProbeEnvelope;
  /** ISO timestamp of when it was captured. */
  capturedAt: string;
}

/**
 * Capture a successful envelope as Last Known State.
 * Returns the input with a captured_at timestamp (stored in user_impact
 * won't persist across calls — caller must store externally).
 */
export function captureLastKnown(envelope: ProbeEnvelope): LastKnownState {
  return {
    envelope,
    capturedAt: new Date().toISOString(),
  };
}

/** Check if a new envelope should replace Last Known (only on Ready or better). */
export function shouldUpdateLastKnown(
  current: ProbeEnvelope | null | undefined,
  candidate: ProbeEnvelope
): boolean {
  if (!current) return true;
  // Ready always updates
  if (candidate.user_state === "ready") return true;
  // Detection Failed never replaces a successful last known
  if (candidate.user_state === "detection_failed") return false;
  // If current is ready and candidate isn't, keep current
  if (current.user_state === "ready") return false;
  return true;
}

/**
 * Collect diagnostic data from capability state for Support Diagnostic.
 */
export function collectDiagnosticModules(
  capabilityState: Record<string, ProbeEnvelope>,
  lastKnown: Map<string, LastKnownState>
): DiagnosticInput["modules"] {
  const modules: DiagnosticInput["modules"] = [];
  for (const [mod, env] of Object.entries(capabilityState)) {
    const lk = lastKnown.get(mod);
    modules.push({
      module: mod,
      userState: env.user_state,
      lastSuccessAt: lk?.capturedAt ?? null,
      reasonCode: env.reason?.code,
      actionId: env.action?.primary?.action_id,
      errorExcerpt: env.reason?.text?.slice(0, 200) ?? undefined,
    });
  }
  return modules;
}
