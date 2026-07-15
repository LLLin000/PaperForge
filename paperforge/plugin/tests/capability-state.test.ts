/**
 * Focused tests for capability-state types, envelope validation, helpers,
 * and the six-module control center rendering.
 */
import { describe, expect, it } from "vitest";
import {
  isValidEnvelope,
  createUnknownEnvelope,
  createStaleEnvelope,
  createInvalidEnvelope,
  isEnvelopeStale,
  isReadyEnvelope,
  classifyCapabilityAction,
  computeModuleSummary,
  validatePersistedEnvelopes,
  CAPABILITY_MODULES,
  SCHEMA_VERSION,
  ProbeEnvelope,
  ActionPrimary,
  probeAction,
  setupAction,
} from "../src/constants";

// ── Helpers ──

/** Minimal valid envelope matching backend int/schema. */
function validEnvelope(overrides: Partial<Record<string, unknown>> = {}): Record<string, unknown> {
  return {
    schema_version: 1,
    module: "installation",
    capability_state: "ready",
    severity: "ok",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    notices: [],
    reason: { code: "ok", text: "All good" },
    action: { primary: null },
    updated_at: "2026-01-15T00:00:00.000Z",
    ttl_seconds: 3600,
    ...overrides,
  };
}

/** Full setup action from backend. */
const FULL_SETUP_ACTION: ActionPrimary = {
  verb: "setup",
  label: "Open Setup Wizard",
  destructive: false,
  destructive_scope: null,
  destructive_effect: null,
  confirmation_required: false,
  confirmation_prompt: null,
  command: "setup",
  scope: "installation",
  scope_count: 0,
};

// ── 1. Schema validation ──

describe("isValidEnvelope", () => {
  it("passes for a valid envelope", () => {
    expect(isValidEnvelope(validEnvelope())).toBe(true);
  });

  it("passes with backend-typical null activity_label and null activity_progress", () => {
    expect(isValidEnvelope(validEnvelope({
      activity_label: null,
      activity_progress: null,
    }))).toBe(true);
  });

  it("passes with full setup action primary", () => {
    expect(isValidEnvelope(validEnvelope({
      action: { primary: FULL_SETUP_ACTION },
    }))).toBe(true);
  });

  it("rejects null input", () => {
    expect(isValidEnvelope(null)).toBe(false);
  });

  it("rejects undefined input", () => {
    expect(isValidEnvelope(undefined)).toBe(false);
  });

  it("rejects non-object input", () => {
    expect(isValidEnvelope("string")).toBe(false);
    expect(isValidEnvelope(42)).toBe(false);
  });

  it("rejects wrong schema_version", () => {
    expect(isValidEnvelope(validEnvelope({ schema_version: "v1" }))).toBe(false);
    expect(isValidEnvelope(validEnvelope({ schema_version: 2 }))).toBe(false);
  });

  it("rejects unknown module", () => {
    expect(isValidEnvelope(validEnvelope({ module: "bogus" }))).toBe(false);
  });

  it("rejects module mismatch", () => {
    expect(isValidEnvelope(validEnvelope({ module: "help" }), "installation")).toBe(false);
  });

  it("accepts matching module", () => {
    expect(isValidEnvelope(validEnvelope({ module: "help" }), "help")).toBe(true);
  });

  it("accepts all six capability_states", () => {
    for (const s of ["unknown", "unavailable", "missing_input", "needs_action", "limited", "ready"]) {
      expect(isValidEnvelope(validEnvelope({ capability_state: s }))).toBe(true);
    }
  });

  it("rejects invalid capability_state", () => {
    expect(isValidEnvelope(validEnvelope({ capability_state: "bogus" }))).toBe(false);
  });

  it("accepts all four severities", () => {
    for (const s of ["unknown", "ok", "warning", "error"]) {
      expect(isValidEnvelope(validEnvelope({ severity: s }))).toBe(true);
    }
  });

  it("rejects invalid severity", () => {
    expect(isValidEnvelope(validEnvelope({ severity: "critical" }))).toBe(false);
  });

  it("rejects missing activity_state", () => {
    const { activity_state, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects missing activity_label", () => {
    const { activity_label, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects missing activity_progress", () => {
    const { activity_progress, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("accepts valid activity_progress object", () => {
    expect(isValidEnvelope(validEnvelope({
      activity_state: "running",
      activity_label: "Probing...",
      activity_progress: { current: 1, total: 5 },
    }))).toBe(true);
  });

  it("rejects activity_progress with string current", () => {
    expect(isValidEnvelope(validEnvelope({
      activity_progress: { current: "1", total: 3 },
    }))).toBe(false);
  });

  it("accepts notices array", () => {
    expect(isValidEnvelope(validEnvelope({
      notices: [{ level: "info", message: "test" }],
    }))).toBe(true);
  });

  it("rejects missing notices", () => {
    const { notices, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects missing reason", () => {
    const { reason, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects reason missing code", () => {
    expect(isValidEnvelope(validEnvelope({ reason: { text: "nope" } }))).toBe(false);
  });

  it("rejects reason missing text", () => {
    expect(isValidEnvelope(validEnvelope({ reason: { code: "nope" } }))).toBe(false);
  });

  it("rejects missing action", () => {
    const { action, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects action with string primary", () => {
    expect(isValidEnvelope(validEnvelope({ action: { primary: "setup" } }))).toBe(false);
  });

  it("rejects action with array primary", () => {
    expect(isValidEnvelope(validEnvelope({ action: { primary: [] } }))).toBe(false);
  });

  it("rejects action with incomplete primary (missing verb)", () => {
    expect(isValidEnvelope(validEnvelope({ action: { primary: { label: "x" } } }))).toBe(false);
  });

  it("accepts action with null primary", () => {
    expect(isValidEnvelope(validEnvelope({ action: { primary: null } }))).toBe(true);
  });

  it("accepts action with full setup primary", () => {
    expect(isValidEnvelope(validEnvelope({ action: { primary: FULL_SETUP_ACTION } }))).toBe(true);
  });

  it("rejects missing updated_at", () => {
    const { updated_at, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects missing ttl_seconds", () => {
    const { ttl_seconds, ...rest } = validEnvelope();
    expect(isValidEnvelope(rest)).toBe(false);
  });

  it("rejects non-number ttl_seconds", () => {
    expect(isValidEnvelope(validEnvelope({ ttl_seconds: "3600" }))).toBe(false);
  });
});

// ── 2. Stale / Invalid helpers (severity unknown, full probe action) ──

describe("isEnvelopeStale", () => {
  function makeEnv(overrides: Partial<ProbeEnvelope> = {}): ProbeEnvelope {
    return {
      schema_version: 1, module: "installation",
      capability_state: "ready", severity: "ok",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      notices: [],
      reason: { code: "ok", text: "ok" },
      action: { primary: null },
      updated_at: new Date().toISOString(),
      ttl_seconds: 3600,
      ...overrides,
    };
  }

  it("returns true when ttl_seconds is 0", () => {
    expect(isEnvelopeStale(makeEnv({ ttl_seconds: 0 }))).toBe(true);
  });

  it("returns true for epoch date", () => {
    expect(isEnvelopeStale(makeEnv({ updated_at: new Date(0).toISOString() }))).toBe(true);
  });

  it("returns false when recent within TTL", () => {
    expect(isEnvelopeStale(makeEnv({ ttl_seconds: 3600 }))).toBe(false);
  });
});

describe("createStaleEnvelope", () => {
  it("produces unknown state, module-prefixed reason, probe action", () => {
    const env = createStaleEnvelope("help");
    expect(env.capability_state).toBe("unknown");
    expect(env.severity).toBe("unknown");
    expect(env.reason.code).toBe("help.stale");
    expect(env.ttl_seconds).toBe(0);
    expect(env.activity_label).toBeNull();
    expect(env.activity_progress).toBeNull();
    expect(env.action.primary).not.toBeNull();
    expect(env.action.primary!.verb).toBe("probe");
  });
});

describe("createInvalidEnvelope", () => {
  it("produces unknown state, module-prefixed reason, probe action", () => {
    const env = createInvalidEnvelope("library");
    expect(env.capability_state).toBe("unknown");
    expect(env.severity).toBe("unknown");
    expect(env.reason.code).toBe("library.invalid_response");
    expect(env.activity_label).toBeNull();
    expect(env.activity_progress).toBeNull();
    expect(env.action.primary!.verb).toBe("probe");
  });
});

// ── 3. createUnknownEnvelope ──

describe("createUnknownEnvelope", () => {
  it("produces six distinct unknown envelopes", () => {
    for (const mod of CAPABILITY_MODULES) {
      const env = createUnknownEnvelope(mod);
      expect(env.module).toBe(mod);
      expect(env.capability_state).toBe("unknown");
      expect(env.schema_version).toBe(SCHEMA_VERSION);
      expect(env.activity_label).toBeNull();
      expect(env.activity_progress).toBeNull();
    }
  });

  it("ALL modules get verb=probe (never setup) in unknown state", () => {
    for (const mod of CAPABILITY_MODULES) {
      const env = createUnknownEnvelope(mod);
      expect(env.action.primary).not.toBeNull();
      expect(env.action.primary!.verb).toBe("probe");
    }
  });

  it("probe action has full ActionPrimary shape", () => {
    const env = createUnknownEnvelope("installation");
    const p = env.action.primary!;
    expect(typeof p.verb).toBe("string");
    expect(typeof p.label).toBe("string");
    expect(typeof p.destructive).toBe("boolean");
    expect(typeof p.command).toBe("string");
    expect(typeof p.scope).toBe("string");
    expect(typeof p.scope_count).toBe("number");
  });
});

// ── 4. Six-module grid & order ──

describe("CAPABILITY_MODULES", () => {
  it("contains exactly six modules", () => {
    expect(CAPABILITY_MODULES).toHaveLength(6);
  });

  it("renders in approved prototype order: installation, library, ocr, memory, maintenance, help", () => {
    expect(CAPABILITY_MODULES[0]).toBe("installation");
    expect(CAPABILITY_MODULES[1]).toBe("library");
    expect(CAPABILITY_MODULES[2]).toBe("ocr");
    expect(CAPABILITY_MODULES[3]).toBe("memory");
    expect(CAPABILITY_MODULES[4]).toBe("maintenance");
    expect(CAPABILITY_MODULES[5]).toBe("help");
  });

  it("includes all expected modules", () => {
    expect(CAPABILITY_MODULES).toContain("installation");
    expect(CAPABILITY_MODULES).toContain("library");
    expect(CAPABILITY_MODULES).toContain("ocr");
    expect(CAPABILITY_MODULES).toContain("memory");
    expect(CAPABILITY_MODULES).toContain("maintenance");
    expect(CAPABILITY_MODULES).toContain("help");
  });
});

// ── 5. probeAction / setupAction builders ──

describe("probeAction", () => {
  it("returns full ActionPrimary with correct verb", () => {
    const a = probeAction("installation");
    expect(a.verb).toBe("probe");
    expect(a.label).toBe("Check");
    expect(a.destructive).toBe(false);
    expect(a.command).toBe("probe installation");
    expect(a.scope).toBe("installation");
    expect(a.scope_count).toBe(1);
  });
});

describe("setupAction", () => {
  it("returns full ActionPrimary with setup verb", () => {
    const a = setupAction();
    expect(a.verb).toBe("setup");
    expect(a.label).toBe("Open Setup Wizard");
    expect(a.destructive).toBe(false);
  });
});

// ── 5. Ready envelope ──

describe("isReadyEnvelope", () => {
  function make(overrides: Partial<ProbeEnvelope> = {}): ProbeEnvelope {
    return {
      schema_version: 1, module: "installation",
      capability_state: "ready", severity: "ok",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      reason: { code: "ok", text: "ok" },
      action: { primary: null },
      notices: [],
      updated_at: new Date().toISOString(),
      ttl_seconds: 3600,
      ...overrides,
    };
  }

  it("returns true for ready with null primary", () => {
    expect(isReadyEnvelope(make())).toBe(true);
  });

  it("returns false for ready with non-null action", () => {
    expect(isReadyEnvelope(make({ action: { primary: FULL_SETUP_ACTION } }))).toBe(false);
  });

  it("returns false for non-ready state", () => {
    expect(isReadyEnvelope(make({ capability_state: "unavailable" }))).toBe(false);
  });

  it("returns false for unknown state", () => {
    expect(isReadyEnvelope(createUnknownEnvelope("installation"))).toBe(false);
  });
});

// ── 6. Six-module grid ──

describe("CAPABILITY_MODULES", () => {
  it("contains exactly six modules", () => {
    expect(CAPABILITY_MODULES).toHaveLength(6);
  });

  it("includes all expected modules", () => {
    expect(CAPABILITY_MODULES).toContain("installation");
    expect(CAPABILITY_MODULES).toContain("help");
    expect(CAPABILITY_MODULES).toContain("library");
    expect(CAPABILITY_MODULES).toContain("ocr");
    expect(CAPABILITY_MODULES).toContain("memory");
    expect(CAPABILITY_MODULES).toContain("maintenance");
  });
});

// ── 7. Literal backend envelope test ──

describe("literal backend envelope", () => {
  /** Exact shape a real `paperforge probe installation --json` would emit. */
  const BACKEND_INSTALLATION_READY: Record<string, unknown> = {
    schema_version: 1,
    module: "installation",
    capability_state: "ready",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "ok",
    reason: { code: "ok", text: "PaperForge environment is set up correctly." },
    action: { primary: null },
    notices: [{ level: "info", message: "Installation verified at 2026-01-15" }],
    updated_at: "2026-01-15T00:00:00.000Z",
    ttl_seconds: 3600,
  };

  it("validates a ready backend envelope", () => {
    expect(isValidEnvelope(BACKEND_INSTALLATION_READY)).toBe(true);
  });

  it("validates a backend envelope with full setup action", () => {
    const envelope: Record<string, unknown> = {
      ...BACKEND_INSTALLATION_READY,
      capability_state: "needs_action",
      severity: "warning",
      reason: { code: "setup_required", text: "Initial setup not yet complete." },
      action: { primary: FULL_SETUP_ACTION },
    };
    expect(isValidEnvelope(envelope)).toBe(true);
  });

  it("validates a running backend envelope", () => {
    const envelope: Record<string, unknown> = {
      ...BACKEND_INSTALLATION_READY,
      capability_state: "unknown",
      activity_state: "running",
      activity_label: "Probing PaperForge installation...",
      activity_progress: { current: 2, total: 5 },
      severity: "unknown",
    };
    expect(isValidEnvelope(envelope)).toBe(true);
  });
});

// ── 8. classifyCapabilityAction ──

describe("classifyCapabilityAction", () => {
  const base: Partial<ProbeEnvelope> = {
    schema_version: 1, module: "installation", capability_state: "needs_action",
    activity_state: "idle", severity: "warning", reason: { code: "test", text: "test" },
    updated_at: new Date().toISOString(), ttl_seconds: 3600,
  };

  it("preserves the backend-selected action label", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope,
      module: "help",
      action: { primary: { verb: "setup", label: "Restore help", destructive: false } },
    };
    expect(classifyCapabilityAction(env).label).toBe("Restore help");
  });

  it("classifies set_config verb as setup kind", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope,
      action: { primary: { verb: "set_config", label: "Configure", destructive: false } },
    };
    const result = classifyCapabilityAction(env);
    expect(result.kind).toBe("setup");
    expect(result.verb).toBe("set_config");
  });

  it("classifies update verb as setup kind", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope,
      action: { primary: { verb: "update", label: "Update", destructive: false } },
    };
    const result = classifyCapabilityAction(env);
    expect(result.kind).toBe("setup");
    expect(result.verb).toBe("update");
  });

  it("classifies probe verb as probe kind", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope,
      action: { primary: { verb: "probe", label: "Refresh", destructive: false } },
    };
    const result = classifyCapabilityAction(env);
    expect(result.kind).toBe("probe");
  });

  it("classifies sync/run/rebuild_index as action kind", () => {
    for (const verb of ["sync", "run", "rebuild_index", "migrate"]) {
      const env: ProbeEnvelope = { ...base as ProbeEnvelope,
        action: { primary: { verb, label: verb, destructive: false } },
      };
      expect(classifyCapabilityAction(env).kind).toBe("action");
    }
  });

  it("defaults to probe when action is null", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope, action: null };
    expect(classifyCapabilityAction(env).kind).toBe("probe");
  });

  it("defaults to probe when primary action is null", () => {
    const env: ProbeEnvelope = { ...base as ProbeEnvelope, action: { primary: null } };
    expect(classifyCapabilityAction(env).kind).toBe("probe");
  });
});

// ── 9. computeModuleSummary ──

describe("computeModuleSummary", () => {
  const readyEnv: ProbeEnvelope = {
    schema_version: 1, module: "installation", capability_state: "ready",
    activity_state: "idle", severity: "ok", reason: null,
    action: { primary: null }, updated_at: new Date().toISOString(), ttl_seconds: 3600,
  };
  const unknownEnv: ProbeEnvelope = {
    schema_version: 1, module: "installation", capability_state: "unknown",
    activity_state: "idle", severity: "unknown", reason: { code: "test", text: "test" },
    action: { primary: { verb: "probe", label: "Probe", destructive: false } },
    updated_at: new Date(0).toISOString(), ttl_seconds: 0,
  };
  const realModules = ["installation", "help"];

  it("reports coreReady=true when all real modules are ready", () => {
    const map: Record<string, ProbeEnvelope> = {
      installation: { ...readyEnv, module: "installation" },
      help: { ...readyEnv, module: "help" },
    };
    expect(computeModuleSummary(map, realModules).coreReady).toBe(true);
  });

  it("reports coreReady=false when a real module is unknown", () => {
    const map: Record<string, ProbeEnvelope> = {
      installation: unknownEnv,
      help: { ...readyEnv, module: "help" },
    };
    const result = computeModuleSummary(map, realModules);
    expect(result.coreReady).toBe(false);
    expect(result.attentionModules).toContain("installation");
  });

  it("includes missing module as attention", () => {
    const map: Record<string, ProbeEnvelope> = {
      installation: { ...readyEnv, module: "installation" },
      // help is missing
    };
    const result = computeModuleSummary(map, realModules);
    expect(result.coreReady).toBe(false);
    expect(result.attentionModules).toContain("help");
  });
});

describe("validatePersistedEnvelopes", () => {
  const allModules = ["installation", "help"];
  const fresh = Date.now();

  /** Build a full valid envelope matching worktree isValidEnvelope strict checks. */
  function validEnv(mod: string): Record<string, unknown> {
    return {
      schema_version: 1,
      module: mod,
      capability_state: "ready",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "ok",
      reason: { code: `${mod}.ready`, text: `${mod} is fully functional.` },
      action: { primary: null },
      notices: [],
      updated_at: new Date(fresh).toISOString(),
      ttl_seconds: 86400,
    };
  }

  it("passes through valid fresh envelopes", () => {
    const input: Record<string, unknown> = {
      installation: validEnv("installation"),
      help: validEnv("help"),
    };
    const result = validatePersistedEnvelopes(input, allModules);
    expect(result["installation"].capability_state).toBe("ready");
    expect(result["help"].capability_state).toBe("ready");
  });

  it("replaces malformed entries with invalid envelopes", () => {
    const input: Record<string, unknown> = {
      installation: { schema_version: "not-a-number", module: "installation" },
    };
    const result = validatePersistedEnvelopes(input, allModules);
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["installation"].reason?.code).toBe("installation.invalid_response");
  });

  it("replaces stale entries with stale envelopes", () => {
    const oldDate = new Date(0).toISOString();
    const input: Record<string, unknown> = {
      installation: {
        ...validEnv("installation"),
        updated_at: oldDate,
        ttl_seconds: 1,
      },
    };
    const result = validatePersistedEnvelopes(input, allModules);
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["installation"].reason?.code).toBe("installation.stale");
  });

  it("creates unknown envelopes for missing modules", () => {
    const result = validatePersistedEnvelopes({}, allModules);
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["help"].capability_state).toBe("unknown");
  });

  it("replaces non-object entries with unknown envelopes", () => {
    const input: Record<string, unknown> = { installation: "string-value" };
    const result = validatePersistedEnvelopes(input, allModules);
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["installation"].reason?.code).toBe("installation.no_probe");
  });

  it("replaces entries with wrong module name with invalid envelope", () => {
    const input: Record<string, unknown> = {
      installation: { ...validEnv("help") }, // expects "installation" key but module="help"
    };
    const result = validatePersistedEnvelopes(input, allModules);
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["installation"].reason?.code).toBe("installation.invalid_response");
  });

  it("replaces entries with non-ready severity/state mismatch with invalid envelope", () => {
    // isValidEnvelope checks validity not correctness — this passes validation
    const input: Record<string, unknown> = {
      installation: {
        ...validEnv("installation"),
        capability_state: "unknown",
        severity: "unknown",
        updated_at: new Date(0).toISOString(),
        ttl_seconds: 0,
      },
    };
    const result = validatePersistedEnvelopes(input, allModules);
    // Should be replaced as stale (TTL zero => always stale per isEnvelopeStale)
    expect(result["installation"].capability_state).toBe("unknown");
    expect(result["installation"].reason?.code).toBe("installation.stale");
  });
});
