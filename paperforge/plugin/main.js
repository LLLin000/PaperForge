"use strict";
var sn = Object.create;
var st = Object.defineProperty;
var on = Object.getOwnPropertyDescriptor;
var ln = Object.getOwnPropertyNames;
var cn = Object.getPrototypeOf,
  pn = Object.prototype.hasOwnProperty;
var er = (d, i) => () => (d && (i = d((d = 0))), i);
var dn = (d, i) => () => (i || d((i = { exports: {} }).exports, i), i.exports),
  xt = (d, i) => {
    for (var e in i) st(d, e, { get: i[e], enumerable: !0 });
  },
  tr = (d, i, e, t) => {
    if ((i && typeof i == "object") || typeof i == "function")
      for (let r of ln(i))
        !pn.call(d, r) &&
          r !== e &&
          st(d, r, {
            get: () => i[r],
            enumerable: !(t = on(i, r)) || t.enumerable,
          });
    return d;
  };
var V = (d, i, e) => (
    (e = d != null ? sn(cn(d)) : {}),
    tr(
      i || !d || !d.__esModule
        ? st(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  rr = (d) => tr(st({}, "__esModule", { value: !0 }), d);
var _r = {};
xt(_r, {
  isAllowlistedCommand: () => mn,
  legacyEmbeddingSecretIds: () => ur,
  migrateLegacySecret: () => vn,
  stripCredentialEnv: () => Ft,
});
function Ft(d) {
  let i = {};
  for (let [e, t] of Object.entries(d))
    gn.some((r) => e.startsWith(r)) || (i[e] = t);
  return i;
}
function mn(d) {
  return hn.has(d);
}
async function ur(d, i) {
  let e = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(
      `${d.trim()}\0${i.trim() || "text-embedding-3-small"}`
    )
  );
  return [
    `vector-db-api-key-v2-${[...new Uint8Array(e)]
      .map((r) => r.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 40)}`,
    bn,
  ];
}
async function vn(d, i, e, t) {
  var n, a;
  if (!i || typeof i.getSecret != "function")
    return { migrated: [], warnings: ["SecretStorage unavailable"] };
  let r =
    d === "embedding"
      ? await ur(
          (n = t == null ? void 0 : t.baseUrl) != null ? n : "",
          (a = t == null ? void 0 : t.model) != null ? a : ""
        )
      : [yn];
  for (let o of r) {
    let l = await i.getSecret(o);
    if (!l) continue;
    if (!(await xn(d, l, e)))
      return {
        migrated: [],
        warnings: [
          "Keyring write failed \u2014 the legacy SecretStorage value was kept. Run `paperforge auth set " +
            d +
            " --stdin` manually.",
        ],
      };
    try {
      await i.setSecret(o, "");
    } catch (p) {
      return {
        migrated: [o],
        warnings: [
          "Credential migrated and verified, but the old SecretStorage value could not be cleared \u2014 delete it manually in Obsidian.",
        ],
      };
    }
    return { migrated: [o], warnings: [] };
  }
  return { migrated: [], warnings: [] };
}
function xn(d, i, e) {
  return new Promise((t) => {
    let r = e.spawn(
        e.pythonPath,
        [
          ...e.pythonArgs,
          "-m",
          "paperforge",
          "--vault",
          e.vaultPath,
          "auth",
          "set",
          d,
          "--stdin",
          "--json",
        ],
        {
          cwd: e.vaultPath,
          env: e.env,
          windowsHide: !0,
          stdio: ["pipe", "pipe", "pipe"],
        }
      ),
      n = "";
    (r.stdout.on("data", (a) => (n += String(a))),
      r.on("error", () => t(!1)),
      r.on("close", (a) => {
        try {
          let o = JSON.parse(n);
          t(a === 0 && (o == null ? void 0 : o.ok) === !0);
        } catch (o) {
          t(!1);
        }
      }),
      r.stdin.write(i),
      r.stdin.end());
  });
}
var gn,
  hn,
  yn,
  bn,
  At = er(() => {
    "use strict";
    gn = ["PAPERFORGE_CREDENTIAL_", "PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
    hn = new Set(["ocr", "memory", "embed"]);
    ((yn = "paddleocr-api-key"), (bn = "vector-db-api-key"));
  });
var Mt = dn((ia, En) => {
  En.exports = {
    versions: [
      {
        version: "1.5.15",
        date: "2026-06-01",
        title:
          "\u5168\u6587\u5B58\u50A8\u91CD\u6784 + OCR \u9605\u8BFB\u987A\u5E8F\u4FEE\u590D + Redo \u4E00\u952E\u91CD\u505A",
        breaking_or_migration: [
          "\u5168\u6587\u6587\u4EF6\u73B0\u5728\u7EDF\u4E00\u5B58\u653E\u4E8E System/PaperForge/ocr/ \u4E0B\uFF0C\u4E0D\u518D\u5728\u5DE5\u4F5C\u533A\u4FDD\u7559\u526F\u672C",
          "Redo OCR \u73B0\u5728\u4F1A\u7ACB\u5373\u6267\u884C\uFF08\u4E00\u952E\u5B8C\u6210\uFF09\uFF0C\u4E0D\u518D\u9700\u8981\u624B\u52A8\u518D\u8DD1\u4E00\u6B21",
        ],
        new_features: [
          "Redo OCR \u4E00\u952E\u95ED\u73AF\uFF1A\u52FE\u9009 \u2192 \u70B9\u6309\u94AE \u2192 \u81EA\u52A8\u5B8C\u6210\u5168\u90E8\u6D41\u7A0B",
          "\u8BBE\u7F6E\u9875\u65B0\u589E\u300C\u66F4\u65B0\u4E0E\u624B\u518C\u300D\u6807\u7B7E\u9875\uFF0C\u53EF\u968F\u65F6\u67E5\u770B\u7248\u672C\u66F4\u65B0\u8BB0\u5F55\u548C\u4F7F\u7528\u624B\u518C",
          "\u63D2\u4EF6\u66F4\u65B0\u540E\u81EA\u52A8\u5F39\u51FA\u66F4\u65B0\u8BF4\u660E",
        ],
        fixes: [
          "\u4FEE\u590D\u5168\u6587\u9605\u8BFB\u987A\u5E8F\u6DF7\u4E71\uFF0C\u4F18\u5316\u6574\u4F53\u6392\u7248\u4F53\u9A8C",
          "\u4FEE\u590D\u7AE0\u8282\u6807\u9898\u548C\u6B63\u6587\u6BB5\u843D\u9519\u4F4D\u65AD\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u56FE\u8868\u548C\u5BF9\u5E94\u56FE\u6CE8\u88AB\u5206\u5F00\u7684\u95EE\u9898",
          "\u4FEE\u590D\u9996\u9875\u6458\u8981\u533A\u5757\u6392\u5E8F\u5F02\u5E38",
          "\u4FEE\u590D\u5E76\u6392\u56FE\u7247\u672A\u80FD\u81EA\u52A8\u5408\u5E76\u7684\u95EE\u9898",
          "Dashboard \u73B0\u5728\u80FD\u6B63\u786E\u8BC6\u522B\u65B0\u7684\u5168\u6587\u6587\u4EF6\u4F4D\u7F6E",
        ],
        recommended_actions: [
          "\u65E7\u7248 OCR \u5168\u6587\u53EF\u80FD\u5B58\u5728\u9605\u8BFB\u987A\u5E8F\u95EE\u9898\uFF0C\u5EFA\u8BAE\u5BF9\u91CD\u8981\u8BBA\u6587\u6267\u884C\u4E00\u6B21 Redo OCR",
          "\u6253\u5F00\u5168\u6587\u8BF7\u76F4\u63A5\u4F7F\u7528 Dashboard \u7684\u300C\u6253\u5F00\u5168\u6587\u300D\u6309\u94AE",
        ],
      },
    ],
  };
});
var Jr = {};
xt(Jr, {
  isConfigHydrated: () => zt,
  readPathConfig: () => Ur,
  resolveVaultPaths: () => we,
  setPathConfigSource: () => gt,
});
function gt(d) {
  et = d;
}
function zt() {
  return et !== null;
}
function Ur(d, i) {
  var e;
  return et
    ? { ...et, _warning: (e = et._warning) != null ? e : null }
    : {
        system_dir: "",
        resources_dir: "",
        literature_dir: "",
        base_dir: "",
        _warning:
          "config authority not hydrated; paths unavailable \u2014 no semantic work may run",
      };
}
function we(d, i) {
  let e = Ur(d, i),
    t = xe.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: xe.join(t, "indexes"),
    logsDir: xe.join(t, "logs"),
    dbPath: xe.join(t, "indexes", "paperforge.db"),
    orphanStatePath: xe.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: xe.join(t, "exports"),
    ocrDir: xe.join(t, "ocr"),
    configWarning: e._warning,
  };
}
var xe,
  et,
  Ke = er(() => {
    "use strict";
    ((xe = V(require("path"))), (et = null));
  });
var Qn = {};
xt(Qn, { default: () => vt });
module.exports = rr(Qn);
var q = require("obsidian"),
  an = V(require("fs")),
  Vt = require("child_process");
var Pe = "paperforge-status",
  De = "paperforge-ocr-workspace",
  Je = "paperforge",
  sr =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  ge = [
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
      timeoutMs: 18e5,
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
function ot(d) {
  switch (d) {
    case "paperforge-sync":
      return ["sync"];
    case "paperforge-ocr":
      return ["ocr", "run"];
    case "paperforge-doctor":
      return ["doctor"];
    case "paperforge-repair":
      return ["repair", "--fix", "--fix-paths"];
    case "paperforge-ocr-redo":
      return ["ocr", "redo"];
    default:
      return null;
  }
}
var We = {
  vault_path: "",
  frozen_skills: {},
  language: "",
  paddleocr_api_key: "",
  zotero_data_dir: "",
  agent_platform: "opencode",
  python_path: "",
  features: { memory_layer: !0, vector_db: !1 },
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
  autoSyncEnabled: !0,
  autoSyncIntervalSeconds: 120,
  _paddleocr_configured: !1,
  _vector_db_configured: !1,
  _setup_complete: !1,
};
function or(d, i) {
  if (!i || !i.note_path) return i;
  let e = d.vault.getAbstractFileByPath(i.note_path);
  if (!e) return i;
  let t = d.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return i;
  let n = { ...i };
  for (let a of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, a) && (n[a] = r[a]);
  return n;
}
function wt(d, i) {
  return d && { ...d, ...i };
}
var lt = 2,
  Le = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  un = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  nr = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  _n = new Set(["unknown", "ok", "warning", "error"]),
  ar = new Set(["idle", "running"]),
  fn = new Set(["safe", "destructive", "irreversible"]);
function ir(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let i = d;
  return !(
    typeof i.action_id != "string" ||
    !i.action_id ||
    typeof i.verb != "string" ||
    typeof i.label != "string" ||
    typeof i.availability != "string" ||
    typeof i.safety_class != "string" ||
    !fn.has(i.safety_class) ||
    !Array.isArray(i.preservation_facts) ||
    !Array.isArray(i.replacement_facts) ||
    typeof i.interruptible != "boolean" ||
    typeof i.confirmation_required != "boolean" ||
    (i.confirmation_prompt !== null &&
      typeof i.confirmation_prompt != "string") ||
    typeof i.scope != "string" ||
    typeof i.scope_count != "number" ||
    (i.execution_mode !== void 0 &&
      i.execution_mode !== "result" &&
      i.execution_mode !== "stream")
  );
}
function Ze(d) {
  return {
    action_id: d + ".probe",
    verb: "probe",
    label: "Retry",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: !0,
    confirmation_required: !1,
    confirmation_prompt: null,
    scope: d,
    scope_count: 1,
  };
}
function Et() {
  return {
    action_id: "foundation.setup",
    verb: "setup",
    label: "Open Setup Wizard",
    availability: "available",
    safety_class: "safe",
    preservation_facts: [],
    replacement_facts: [],
    interruptible: !0,
    confirmation_required: !1,
    confirmation_prompt: null,
    scope: "installation",
    scope_count: 1,
  };
}
function ct(d, i) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== lt ||
    typeof e.module != "string" ||
    !e.module ||
    !Le.includes(e.module) ||
    (i !== void 0 && e.module !== i) ||
    typeof e.capability_state != "string" ||
    !nr.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !ar.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !un.has(e.user_state) ||
    typeof e.capability_kind != "string" ||
    typeof e.maintenance_eligible != "boolean" ||
    typeof e.user_visible_failure != "boolean" ||
    (e.user_impact !== null && typeof e.user_impact != "string") ||
    (e.activity_label !== null && typeof e.activity_label != "string")
  )
    return !1;
  if (e.activity_progress !== null) {
    if (typeof e.activity_progress != "object") return !1;
    let n = e.activity_progress;
    if (typeof n.current != "number" || typeof n.total != "number") return !1;
  }
  if (!Array.isArray(e.notices) || !e.reason || typeof e.reason != "object")
    return !1;
  let t = e.reason;
  if (
    typeof t.code != "string" ||
    typeof t.text != "string" ||
    !e.action ||
    typeof e.action != "object"
  )
    return !1;
  let r = e.action;
  if (
    (r.primary !== null && !ir(r.primary)) ||
    typeof e.updated_at != "string" ||
    !e.updated_at ||
    typeof e.ttl_seconds != "number"
  )
    return !1;
  if (e.module === "maintenance") {
    if (r.primary !== null || !Array.isArray(e.items)) return !1;
    for (let n of e.items) {
      if (!n || typeof n != "object") return !1;
      let a = n,
        o = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof a.capability_state != "string" ||
        !nr.has(a.capability_state) ||
        typeof a.severity != "string" ||
        !_n.has(a.severity) ||
        typeof a.activity_state != "string" ||
        !ar.has(a.activity_state) ||
        (a.activity_label !== null && typeof a.activity_label != "string")
      )
        return !1;
      if (a.activity_progress !== null) {
        if (typeof a.activity_progress != "object") return !1;
        let l = a.activity_progress;
        if (typeof l.current != "number" || typeof l.total != "number")
          return !1;
      }
      if (
        typeof a.reason_code != "string" ||
        !a.reason_code ||
        typeof a.reason_text != "string" ||
        (a.action !== null && !ir(a.action))
      )
        return !1;
    }
  }
  return !0;
}
function Y(d) {
  return {
    schema_version: lt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: d + ".no_probe", text: d + " has not been probed yet." },
    action: { primary: d === "maintenance" ? null : Ze(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function kt(d) {
  return {
    schema_version: lt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: d + ".stale",
      text: "Cached probe data for " + d + " is stale.",
    },
    action: { primary: d === "maintenance" ? null : Ze(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function Ge(d) {
  return {
    schema_version: lt,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: d + ".invalid_response",
      text: "Probe response for " + d + " was invalid.",
    },
    action: { primary: d === "maintenance" ? null : Ze(d) },
    notices: [],
    user_state: "detection_failed",
    capability_kind: "required",
    maintenance_eligible: !1,
    user_visible_failure: !1,
    user_impact: null,
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function St(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let i = new Date(d.updated_at).getTime();
  return isNaN(i) ? !0 : Date.now() - i > d.ttl_seconds * 1e3;
}
function lr(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function cr(d) {
  var r, n, a;
  let i = (r = d.action) == null ? void 0 : r.primary,
    e = (n = i == null ? void 0 : i.verb) != null ? n : "probe",
    t = (a = i == null ? void 0 : i.label) != null ? a : e;
  return e === "setup" || e === "set_config" || e === "update"
    ? { kind: "setup", verb: e, label: t }
    : e === "probe"
      ? { kind: "probe", verb: e, label: t }
      : { kind: "action", verb: e, label: t };
}
function pr(d, i) {
  let e = {};
  for (let t of i) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = Y(t);
      continue;
    }
    if (!ct(r, t)) {
      e[t] = Ge(t);
      continue;
    }
    if (St(r)) {
      e[t] = kt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var Ct = {
    en: {
      action_running: "Running ",
      api_key_missing: "Missing",
      api_key_set: "Entered",
      btn_install: "Open Setup Wizard",
      btn_install_desc:
        "Check whether the environment is ready, then open the step-by-step setup wizard",
      btn_reconfig: "Reconfigure",
      btn_reconfig_desc:
        "Open the setup wizard again to change directories, platform, or API keys",
      btn_validate: "Validate",
      check_bbt_fail: "Not detected",
      check_bbt_ok: "Installed",
      check_python_fail: "Not found",
      check_python_ok: "Ready",
      check_zotero_fail: "Not detected",
      check_zotero_ok: "Found",
      complete_export_path: "Save Better BibTeX JSON exports into:",
      complete_next: "Recommended next steps",
      complete_step1: "Open Dashboard",
      complete_step1_desc:
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
      complete_step2: "Sync Literature",
      complete_step2_desc:
        "In the main panel, click Sync Library to bring papers from Zotero into Obsidian and generate notes.",
      complete_step3: "Run OCR",
      complete_step3_desc:
        "In the Obsidian Base view, mark do_ocr:true on papers, then run OCR in the main panel.",
      complete_step4: "Configure Better BibTeX Auto-export",
      complete_step4_desc:
        'In Zotero, right-click the library or collection you want to sync -> Export -> Better BibTeX JSON -> enable "Keep updated".',
      complete_summary: "Saved Configuration",
      complete_title: "Setup Complete",
      copied: "Copied!",
      copy_pf_deep_cmd: "Copy /pf-deep Command",
      dashboard_drift_warning:
        "PaperForge CLI (v{0}) differs from plugin (v{1}). Open Settings \u2192 Runtime Health to sync.",
      deep_reading_not_found: "Deep reading file not found",
      desc: "Obsidian + Zotero literature pipeline. Sync papers, generate notes, run OCR, and read deeply in one place.",
      dir_base: "Base Dir",
      dir_index: "Index Dir",
      dir_notes: "Notes Dir",
      dir_resources: "Resource Dir",
      dir_system: "System Dir",
      ocr_ws_search_placeholder: "Search papers by title, author, year...",
      dir_vault: "Vault Path",
      error_copied: "Copied!",
      error_copy_diagnostic: "Copy diagnostic",
      feat_agent_platform: "Agent Platform",
      feat_agent_platform_desc:
        "Select which agent platform to manage skills for.",
      feat_api_base_url: "API Base URL",
      feat_api_base_url_desc:
        "Custom OpenAI-compatible API endpoint. Leave empty for default.",
      feat_api_model: "API Model",
      feat_api_model_desc: "Embedding model name for this endpoint.",
      feat_build_btn: "Build",
      feat_building: "Building...",
      feat_cache_remove_failed: "Failed: {0}",
      feat_cache_removed: "Model cache removed.",
      feat_checking: "Checking...",
      feat_checking_btn: "Checking...",
      feat_deps_missing:
        "Dependencies not installed. Required: chromadb, openai.",
      feat_key_rejected: "API key rejected.",
      feat_memory_desc:
        "The Memory Layer is the core data engine of PaperForge, powered by SQLite. It integrates literature metadata (papers, assets, aliases, reading events), provides FTS5 metadata search across titles, abstracts, authors, domains, and collections, and powers agent-context and paper-status. Always active \u2014 no toggle needed.",
      feat_memory_rebuild_btn: "Rebuild",
      feat_memory_rebuild_done: "Memory DB rebuilt.",
      feat_memory_rebuild_failed: "Rebuild failed.",
      feat_memory_rebuilding: "Rebuilding...",
      feat_model: "Model",
      feat_model_changed_warn:
        "Model changed ({0} -> {1}). Existing vectors are incompatible \u2014 rebuild required.",
      feat_network_error: "Network error: ",
      feat_not_cached: "Not cached",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "Used for API embedding calls. Model is defined below.",
      feat_output_copied: "Output copied to clipboard.",
      feat_rebuild_btn: "Rebuild",
      feat_rebuild_vectors: "Rebuild Vectors",
      feat_rebuild_vectors_changed:
        "Model changed \u2014 rebuild to update all vectors.",
      feat_rebuild_vectors_desc:
        "Rebuild all OCR fulltext vectors. Required after model or mode change.",
      feat_removing: "Removing...",
      feat_skills_desc:
        "Manage and enable/disable agent skills installed in your vault. Each row corresponds to a SKILL.md file \u2014 toggle off to prevent the agent from auto-invoking that skill.",
      feat_skills_system:
        "System Skills ship with PaperForge and are updated alongside PaperForge.",
      feat_skills_user:
        "User Skills are custom skills you install from community or create yourself.",
      feat_uninstall_btn: "Uninstall",
      feat_valid_key: "API key valid.",
      field_paddleocr: "PaddleOCR API Key",
      field_python_custom: "Custom Path",
      field_python_interp: "Python Interpreter",
      field_zotero_data: "Zotero Data Dir",
      field_zotero_placeholder:
        "Required. Path to Zotero data directory for PDF attachment resolution.",
      guide_ocr: "Run OCR",
      guide_ocr_desc:
        "In the main panel, click Run OCR to extract full text and figures from PDFs for later reading and analysis.",
      guide_open: "Open Main Panel",
      guide_open_desc:
        "Open the main PaperForge panel to manage your literature.",
      guide_sync: "Sync Literature",
      guide_sync_desc:
        "After Better BibTeX JSON export is configured, click Sync Library to import papers from Zotero into Obsidian and generate notes automatically.",
      header_title: "PaperForge",
      install_bootstrapping:
        "PaperForge Python package not found. Installing automatically...",
      install_btn: "Start Install",
      install_btn_retry: "Retry",
      install_btn_running: "Installing...",
      install_complete: "Installation complete!",
      install_failed: "Installation failed: ",
      install_validating: "Validating setup...",
      jump_to_deep_reading: "Open Deep Reading",
      label_agent: "Agent Platform",
      nav_close: "Close",
      nav_next: "Next",
      no_pending_ocr: "All OCR tasks complete",
      nav_prev: "Back",
      not_set: "Not entered",
      notice_check_fail: "Missing: ",
      notice_python_missing:
        "Python was not detected. Install Python 3.11+ and add it to PATH.",
      ocr_privacy_title: "OCR Privacy Notice",
      ocr_privacy_warning:
        "OCR will upload PDFs to the PaddleOCR API. Do not upload sensitive or confidential documents.",
      ocr_queue_add: "Add to OCR Queue",
      ocr_queue_added: "Added to OCR queue",
      ocr_queue_remove: "Remove from OCR Queue",
      ocr_queue_removed: "Removed from OCR queue",
      ocr_understand: "I understand, continue",
      optional_later: "(can be set later in Settings)",
      orphan_delete_failed: "Prune failed",
      orphan_delete_selected: "Delete {count} selected",
      orphan_deleted: "Deleted {count} orphan workspace(s)",
      orphan_desc: "These papers are no longer in your Zotero library.",
      orphan_deselect_all: "Deselect all",
      orphan_explain: "Removed from Zotero. Workspace files remain on disk.",
      orphan_keep_all: "Keep all",
      orphan_none_selected: "No papers selected for deletion",
      orphan_select_all: "Select all",
      orphan_title: "Found {count} orphan paper(s)",
      panel_actions: "Quick Actions",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc: "In Zotero: Tools -> Add-ons -> install Better BibTeX.",
      prep_export: "Better BibTeX Auto-export",
      prep_export_desc:
        'In Zotero, right-click the collection you want to sync -> Export Collection -> BetterBibTeX JSON -> enable "Keep updated" -> save the JSON file into the exports folder shown below. Obsidian Base views will use the JSON filename as the Base name:',
      prep_export_path_label: "Save the exported JSON file into this folder:",
      prep_key: "PaddleOCR Key",
      prep_key_desc:
        "Get your API key from https://aistudio.baidu.com/paddleocr",
      prep_python: "Python 3.11+",
      prep_python_desc:
        "Python must be available from the command line. If you are not sure, click below to auto-detect.",
      prep_zotero: "Zotero Desktop",
      prep_zotero_desc: "Install Zotero from https://www.zotero.org",
      run_in_agent: "Run in {0}",
      runtime_health: "Runtime Health",
      runtime_health_checking: "Checking...",
      runtime_health_desc:
        "Check whether the installed paperforge Python package matches the plugin version and whether the deployed skill contract is current.",
      runtime_health_match: "Match",
      runtime_health_mismatch: "Mismatch",
      runtime_health_package_ver: "Python package v{0}",
      runtime_health_plugin_ver: "Plugin v{0}",
      runtime_health_sync: "Sync Runtime",
      runtime_health_sync_done: "Runtime synced to v{0}",
      runtime_health_sync_fail: "Sync failed: {0}",
      runtime_health_syncing: "Syncing...",
      section_config: "Current Configuration",
      section_guide: "How To Use",
      section_prep: "Preparation",
      section_prep_desc:
        "Before first use, finish these 4 preparation items. Better BibTeX auto-export is configured after setup:",
      setup_done: "PaperForge environment is ready",
      setup_pending:
        "Not installed yet. Finish the preparation items below, then open the wizard.",
      tab_overview: "Overview",
      tab_modules: "Module Detail",
      tab_help: "Help",
      tab_setup: "Installation",
      tab_features: "Features",
      tab_maintenance: "Maintenance",
      validate_base: "Base directory is required",
      validate_fail: "Please complete the required fields below",
      validate_index: "Index directory is required",
      validate_key: "PaddleOCR API key (optional, needed for OCR)",
      validate_notes: "Notes directory is required",
      validate_resources: "Resources directory is required",
      validate_system: "System directory is required",
      validate_vault: "Vault path is required",
      validate_zotero:
        "Zotero data directory (optional, needed for PDF linking)",
      wizard_agent_hint:
        "Choose the AI agent platform you use most often. PaperForge will place the matching command and skill files in the correct location.",
      wizard_dir_hint:
        "PaperForge stores user-facing literature data under the resources directory. These folders will live there:",
      wizard_dir_sub_hint: "Resolved folder preview based on the names below:",
      wizard_intro:
        "This wizard walks you through the full setup. In most cases, the default values are fine to keep.",
      wizard_keys_hint:
        "Enter your PaddleOCR API key below. If you want PaperForge to auto-locate Zotero PDFs, you can also fill in the Zotero data directory.",
      wizard_preview:
        "After installation, system files stay at the vault root while literature data stays under the resources directory.",
      wizard_safety:
        "Safety: if the selected folders already contain files, setup preserves existing files and only creates missing PaperForge folders and files.",
      wizard_step1: "Overview",
      wizard_step2: "Directory Setup",
      wizard_step3: "Platform & Keys",
      wizard_step4: "Install",
      wizard_step5: "Done",
      wizard_skip_ocr_desc:
        "OCR will not be available until you configure a valid PaddleOCR API key. You can continue setup now and configure it later in Settings.",
      wizard_skip_ocr_continue: "Continue without OCR key",
      wizard_skip_ocr_back: "Back to configure",
      wizard_api_hint_skip:
        "OCR key is optional \u2014 you may skip it and configure later.",
      wizard_sys_hint:
        "These folders live at the vault root, outside the resources directory:",
      wizard_title: "PaperForge Setup Wizard",
      ocr_maint_no_action: "No Action Needed",
      ocr_maint_rebuild: "Rebuild Recommended",
      ocr_maint_failed: "OCR Failed",
      ocr_maint_limited: "Result Limited",
      ocr_maint_needs_attention: "Needs Attention",
      ocr_maint_limitations: "Result Limitations",
      ocr_maint_hero_ok: "OCR looks usable overall.",
      ocr_maint_hero_warn:
        "OCR needs attention: {rebuild} rebuild recommended, {failed} failed.",
      ocr_maint_hero_note:
        "This page only promotes issues where maintenance is likely to help. Some papers may have limitations that maintenance will not improve.",
      ocr_maint_limitations_intro:
        "These papers look less certain, but PaperForge does not currently have a high-confidence maintenance action to recommend.",
      ocr_maint_all_papers: "All Papers",
      ocr_maint_rebuild_btn: "Rebuild results",
      ocr_maint_redo_btn: "Rerun OCR",
      ocr_maint_redo_confirm:
        "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced.",
      maintenance_group_retry: "Needs Retry",
      maintenance_group_rebuild: "Can Rebuild",
      maintenance_group_legacy: "Upgrade Available (Optional)",
      maintenance_btn_retry: "Retry",
      maintenance_btn_rebuild: "Rebuild",
      maintenance_btn_upgrade: "Upgrade",
      maintenance_refresh_spinning: "Updating\u2026",
      maintenance_all_good: "\u2705 All good \u2014 no action needed",
      maintenance_n_pending: "{n} need attention",
      maintenance_filter_all: "All",
      maintenance_filter_recommended: "Recommended",
      maintenance_batch_rebuild: "\u25B6 Rebuild selected",
      maintenance_batch_redo: "\u25B6 Full OCR redo selected",
      maintenance_stop: "Stop",
      maintenance_batch_complete:
        "Batch operation complete \u2014 {n} papers processed.",
      maintenance_progress_label: "{current}/{total} papers",
      version_panel_title: "Version History",
      version_panel_back: "Back",
      version_filter_placeholder: "Filter papers...",
      version_papers_count: "{n} papers",
      version_current: "current",
      version_restore_btn: "Restore",
      version_compare_btn: "Compare",
      version_restore_selected: "Restore selected",
      version_clear_old: "Clear old versions (free {size})",
      version_no_backups: "No version history available",
      version_restore_confirm: "Restore {label} for {paper}?",
      version_restore_done: "Restored {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} paragraphs changed",
      version_error_read: "Cannot read version data",
      retrieval_search_placeholder: "Search papers... (@ for deep search)",
      retrieval_search_placeholder_deep: "Search paper content...",
      retrieval_search_idle_hint: "Type a keyword or @ to search paper content",
      retrieval_searching_metadata: "Searching metadata...",
      retrieval_searching_deep: "Deep searching...",
      retrieval_search_cancel: "Cancel",
      retrieval_results_count: "{n} result(s)",
      retrieval_empty: "No matching papers found.",
      retrieval_empty_tips: "Try broader terms or use @ deep search.",
      retrieval_vectors_not_built: "Vector index not built",
      retrieval_vectors_not_built_desc:
        "Build vectors to enable @ deep search with semantic matching.",
      retrieval_open_vector_settings: "Open Vector Settings",
      retrieval_backend_unavailable: "Search backend unavailable",
      retrieval_backend_unavailable_desc:
        "The Python CLI search backend is not responding correctly.",
      retrieval_run_doctor: "Run Doctor",
      retrieval_retry: "Retry",
      retrieval_timeout_title: "Search timed out",
      retrieval_timeout_desc:
        "The search took too long. Try a more specific query.",
      retrieval_model_changed: "Model changed",
      retrieval_model_changed_desc:
        "The embedding model has changed since vectors were built. Rebuild to use deep search.",
      retrieval_rebuild_vectors: "Rebuild Vectors",
      retrieval_build_idle: "Vector database ready",
      retrieval_build_ready: "{n} vector(s) built",
      retrieval_build_stopping: "Stopping...",
      retrieval_build_stopped: "Build stopped ({n}/{t} papers)",
      retrieval_build_failed: "Build failed",
      retrieval_build_deps_missing:
        "Dependencies missing. Install chromadb and openai.",
      retrieval_stop: "Stop",
      retrieval_no_python: "Python not found",
      retrieval_internal_error: "An internal error occurred",
      retrieval_force_rebuild: "Force Rebuild",
      retrieval_rebuild_warning:
        "Rebuild will replace {n} existing chunk(s). Continue?",
      md_select_installation: "Foundation",
      md_select_library: "Library",
      md_select_ocr: "OCR",
      md_select_memory: "Smart Retrieval",
      md_select_agent: "Agent Integration",
      installation_detail_heading: "Foundation",
      library_detail_heading: "Library",
      ocr_detail_heading: "OCR",
      memory_detail_heading: "Smart Retrieval",
      agent_detail_heading: "Agent Integration",
      btn_back_to_overview: "\u2190 Back to Overview",
      agent_integration_section: "Agent Integration",
      module_detail_open_installation: "Open Foundation",
      module_detail_open_help: "Help",
      module_detail_open_maintenance: "Maintenance",
      module_detail_open_library: "Open Library",
      module_detail_open_ocr: "Open OCR",
      module_detail_open_memory: "Open Smart Retrieval",
      action_unknown_pair: "Unknown action: {verb}",
      update_python_manual:
        "Python 3.11+ upgrade requires a manual install (python.org or your package manager).",
      update_done: "PaperForge updated",
      update_failed: "Update failed",
      migrate_done: "Backend migrated to sqlite-vec",
      migrate_failed: "Backend migration failed",
      ocr_stop_batch: "Stop OCR batch",
      runtime_not_available: "Environment unavailable",
      md_unavailable_module: "Not available yet",
      managed_runtime_status: "Runtime Status",
      managed_runtime_install: "Install Runtime",
      managed_runtime_repair: "Repair Runtime",
      managed_runtime_update: "Update Runtime",
      managed_runtime_check_status: "Check Status",
      managed_runtime_refresh: "Refresh Status",
      managed_runtime_manual_setup: "Manual Setup",
      managed_runtime_stop: "Stop",
      managed_runtime_unknown_state: "Unknown",
      managed_runtime_ok_state: "Ready",
      managed_runtime_not_installed: "Not Installed",
      managed_runtime_needs_repair: "Needs Repair",
      managed_runtime_unavailable: "Unavailable",
      managed_runtime_last_verified: "Last verified: {time}",
      managed_runtime_running: "Runtime operation in progress...",
      managed_runtime_action_complete: "Runtime operation completed.",
      managed_runtime_action_failed: "Runtime operation failed: {error}",
      managed_runtime_action_cancelled: "Runtime operation cancelled.",
      cc_module_foundation: "Foundation",
      cc_module_agent: "Agent Integration",
      cc_badge_checking: "Checking",
      cc_badge_ready: "Ready",
      cc_badge_not_enabled: "Not Enabled",
      cc_badge_setup_required: "Setup Required",
      cc_badge_action_required: "Action Required",
      cc_badge_detection_failed: "Detection Failed",
      cc_summary_ready: "PaperForge is ready",
      cc_summary_incomplete: "Setup incomplete",
      cc_summary_ready_body: "Foundation and Library are operational.",
      cc_summary_incomplete_body:
        "Complete Foundation and Library setup to use PaperForge.",
      cc_summary_checking: "Checking PaperForge",
      cc_summary_checking_body: "Checking Foundation and Library status\u2026",
      cc_refresh_btn: "Refresh Status",
      cc_last_checked: "Last checked: ",
      cc_needs_attention: "item needs attention",
      cc_checked_pending: "Not checked yet",
      cc_eyebrow: "control center",
      cc_modules_header: "modules",
      cc_five_capabilities: "Five capabilities",
      cc_optional_note: "Optional modules do not affect core readiness.",
      cc_title: "Your literature pipeline",
      cc_lede:
        "See what is working, what needs you, and the single next action for every PaperForge capability.",
      cc_modules_label: "modules",
      cc_modules_title: "Five capabilities",
      cc_modules_caption: "Optional modules do not affect core readiness.",
      cc_maintenance_count: "{n} items need attention",
      cc_card_retry: "Retry",
      cc_action_rebuild_derived: "Rebuild",
      ocr_progress: "{current}/{total} papers",
      cc_operational_modules: "Operational modules",
      cc_consequence_default: "Status is not available yet.",
      cc_consequence_checking: "Checking the latest status\u2026",
      cc_consequence_detection_failed:
        "PaperForge could not determine the current status.",
      cc_consequence_setup_required: "Configuration is required before use.",
      cc_consequence_action_required: "A problem needs your attention.",
      cc_consequence_installation_ready: "PaperForge is ready on this device.",
      cc_consequence_library_ready:
        "Your Zotero library is connected and current.",
      cc_consequence_ocr_ready: "OCR is ready to process papers.",
      cc_consequence_memory_ready: "Your papers are indexed and searchable.",
      cc_consequence_agent_ready:
        "PaperForge Skills are deployed for the selected Agent platform.",
      cc_consequence_agent_not_enabled:
        "Choose an agent platform when you want to deploy PaperForge Skills.",
      cc_consequence_ocr_not_enabled:
        "OCR is optional and is currently not enabled.",
      cc_consequence_memory_not_enabled:
        "Smart Retrieval is optional and is currently not enabled.",
      md_foundation_overview: "Environment",
      md_foundation_ready:
        "PaperForge is installed, verified, and ready for normal use.",
      md_library_connection: "Zotero connection",
      md_library_ready: "Zotero is connected and literature is up to date.",
      md_library_corpus: "Literature corpus",
      md_library_last_sync: "Last successful sync",
      md_ocr_status: "OCR capability",
      md_status_refresh_hint:
        "Check status to load the current OCR details. This does not change any papers.",
      ocr_error_notice:
        "OCR stopped because of an error. Open Advanced Diagnostics for details.",
      ocr_run_complete: "OCR run complete.",
      ocr_rebuild_complete: "OCR rebuild complete.",
      ocr_redo_complete: "OCR redo complete.",
      ocr_stopped_notice: "OCR batch stopped.",
      ocr_failed_notice:
        "OCR did not complete. Open Advanced Diagnostics for details.",
      md_ocr_ready: "OCR is configured and ready.",
      md_ocr_workspace: "Open OCR Workspace",
      md_retrieval_coverage: "Retrieval coverage",
      md_retrieval_ready: "All available papers are indexed and searchable.",
      md_agent_integration: "Agent Integration",
      md_agent_placeholder:
        "Configure a target platform, deploy PaperForge files, and manage Skills. File deployment does not verify a live agent connection.",
      md_agent_platform: "Target platform",
      md_agent_deployment: "Deployment state",
      agent_deployed: "Files deployed",
      agent_not_deployed: "Files not deployed",
      agent_live_connection: "Live connection",
      agent_verify_found: "PaperForge Skills were found for this platform.",
      agent_verify_missing:
        "No PaperForge Skills were found for this platform. Run setup to deploy them.",
      skills_system: "System Skills",
      skills_user: "User Skills",
      skills_empty: "No Skills are deployed for the selected platform.",
      md_agent_connection_unknown: "Live connection is not verified",
      md_agent_skills: "PaperForge Skills",
      md_copy_diagnostic: "Copy Support Diagnostic",
      md_configuration: "Configuration",
      md_current_activity: "Current activity",
      config_change: "Change",
      config_save: "Save",
      config_cancel: "Cancel",
      config_verify: "Verify",
      config_configured: "Configured",
      config_not_configured: "Not configured",
      config_zotero_dir: "Zotero data directory",
      problem_what_happened: "What happened",
      problem_impact: "Impact:",
      problem_next: "Next:",
      problem_copy: "Copy Diagnostic Information",
      problem_use_action: "Use the action above to resolve this problem.",
      library_problem_impact:
        "New references and literature notes may not be available.",
      ocr_problem_impact: "Some papers may not have readable full text.",
      retrieval_problem_impact:
        "Search and retrieval may miss papers until coverage is restored.",
      metric_after_sync: "Available after the next successful sync",
      metric_not_available: "Not available",
      coverage_complete: "Complete",
      retrieval_freshness: "Last checked",
      md_module_switcher: "Module",
      advanced_diagnostics: "Advanced Diagnostics",
      foundation_version: "PaperForge version",
      foundation_last_verified: "Last verified",
      foundation_runtime_managed: "Managed environment",
      foundation_runtime_system: "System environment",
      foundation_runtime_unavailable: "Environment unavailable",
      foundation_skills_ready: "Available",
      foundation_skills: "Skills",
      md_foundation_legacy_migrate: "Migrate legacy configuration",
      foundation_setup_desc:
        "Run setup to create the Python-owned vault configuration and publish the runtime pointer.",
      foundation_setup_btn: "Open Setup",
      config_confirm: "Confirm",
      ocr_configure_credential: "Configure OCR credential",
      setup_welcome: "Set up PaperForge",
      setup_desc:
        "Complete the required stages, then choose any optional capabilities you want to enable.",
      setup_stage_1: "Foundation",
      setup_stage_2: "Connect Library",
      setup_stage_3: "Optional Capabilities",
      setup_stage_4: "Review & Begin",
      setup_progress: "Setup progress",
      setup_foundation_title: "Step 1: Foundation",
      setup_foundation_desc:
        "Choose the Python runtime, then install the PaperForge package. It does not create or configure your library.",
      setup_ready: "Foundation is ready.",
      setup_foundation_python: "Python executable",
      setup_foundation_python_hint:
        'Leave blank to use "python" from your system PATH.',
      setup_foundation_install_btn: "Install PaperForge",
      setup_library_title: "Step 2: Connect Library",
      setup_library_desc:
        "Connect Zotero so PaperForge can sync your literature.",
      setup_library_ready: "Library is connected.",
      setup_library_config_desc:
        "Verify the Zotero data directory, then confirm where PaperForge stores files in this vault.",
      setup_library_zotero_hint:
        "PaperForge reads this folder; it never modifies Zotero's database.",
      setup_library_folder_heading: "Vault folders",
      setup_library_verify: "Save and verify configuration",
      setup_library_configured:
        "Library configuration saved. Checking the connection.",
      setup_library_configuring:
        "Saving and checking library configuration\u2026",
      setup_library_config_failed:
        "Library configuration could not be verified. Check the paths, then try again.",
      setup_reinstall_notice:
        "Reinstall only the local PaperForge Python package. Your library configuration is unchanged.",
      setup_installing: "Installing and preparing PaperForge\u2026",
      setup_install_complete:
        "Installation complete. Checking the updated environment.",
      setup_install_failed:
        "PaperForge could not be installed. Check the Python path, then try again.",
      setup_optionals_title: "Step 3: Optional Capabilities",
      setup_optionals_desc:
        "Choose only what you need. Skipped capabilities can be enabled later.",
      setup_optional_saved: "Configuration saved securely.",
      setup_optional_save_failed:
        "Configuration could not be saved. Check Obsidian secure storage, then try again.",
      setup_opt_ocr_desc: "Extract text and figures from PDFs",
      setup_opt_memory_desc: "Search and navigate across your papers",
      setup_opt_agent_desc: "Deploy and manage PaperForge Skills",
      setup_review_title: "Step 4: Review & Begin",
      setup_review_selected: "Selected: ",
      setup_no_optionals: "No optional capabilities selected.",
      setup_incomplete_warn:
        "Foundation and Library must be ready before setup can finish.",
      setup_review_checking: "Checking your current configuration\u2026",
      setup_review_recheck: "Recheck configuration",
      setup_nav_continue: "Continue",
      setup_nav_skip: "Skip for now",
      setup_nav_back: "Back",
      setup_nav_cancel: "Cancel",
      setup_nav_later: "Later",
      setup_install_cancelled:
        "Setup cancelled. The runtime was not activated.",
      setup_nav_complete: "Complete Setup",
      help_title: "Help",
      help_eyebrow: "help",
      help_lede: "Open the relevant module, or copy a diagnostic for support.",
      help_intro:
        "Choose a task or copy a privacy-safe diagnostic for support.",
      help_getting_started: "Getting started",
      help_library_task: "Connect Zotero and sync your literature",
      help_ocr_task: "Configure OCR and open the OCR Workspace",
      help_retrieval_task: "Enable Smart Retrieval and build coverage",
      help_agent_task: "Choose an agent platform and deploy Skills",
      help_current_problem: "Current problem guidance",
      help_no_problem: "No current problem needs guidance.",
      help_support: "Support Diagnostic",
      help_support_desc:
        "Copies module states and version identifiers without secrets, content, identity, absolute paths, or raw logs.",
      help_copy: "Copy Support Diagnostic",
      help_documentation: "Documentation",
      help_documentation_desc:
        "Open the project guide for setup, workflows, and troubleshooting.",
      help_open_documentation: "Open PaperForge Documentation",
      help_release_notes: "Release notes",
      help_release_notes_desc:
        "Installed version: {version}. See GitHub for the complete change history.",
      help_open_release_notes: "Open Release Notes",
      help_load_error:
        "Failed to load help content. Check your internet connection.",
      maintenance_empty_title: "No maintenance needed",
      maintenance_empty_body:
        "There are no unresolved problems that require action.",
      maintenance_default_impact:
        "This capability may be unavailable or return incomplete results.",
      maintenance_open_module: "Open module",
      migration_banner_title: "Credential Migration Notice",
      foundation_git: "Git",
      foundation_git_missing:
        "Not installed \u2014 install Git for version control",
      foundation_python_packages: "Python Packages",
      foundation_paddle_key: "PaddleOCR API Key",
      foundation_paddle_missing:
        "Not configured \u2014 required for OCR extraction",
      foundation_openai_key: "OpenAI API Key",
      foundation_openai_missing:
        "Not configured \u2014 required for Smart Retrieval",
      foundation_python: "Python Path",
      foundation_python_status: "Python Status",
      foundation_python_ok: "Python is installed",
      foundation_python_missing: "Python not found \u2014 install Python 3.11+",
      foundation_vault_structure: "Vault folders",
      foundation_zotero: "Zotero data directory",
      foundation_zotero_missing:
        "Not configured \u2014 connect your Zotero data directory",
      foundation_reinstall: "Reinstall PaperForge",
      foundation_reinstall_desc:
        "Reinstall the Python package from the local source",
      foundation_reinstall_btn: "Reinstall",
      foundation_reinstalling: "Reinstalling PaperForge...",
      foundation_reinstall_ok: "PaperForge reinstalled successfully",
      foundation_reinstall_failed: "Reinstall failed",
      cc_summary_ok: "All systems ready",
      cc_summary_core_ok:
        "Core environment ready; {n} modules pending detection",
      cc_summary_attention: "Some modules need attention",
      cc_summary_ok_body:
        "PaperForge environment is fully operational. Installation and documentation are verified.",
      cc_summary_core_ok_body:
        "Installation and Help modules are active. Library, OCR, Memory, and Maintenance will show live status once their backends are connected.",
      cc_summary_attention_body:
        "One or more core modules require your attention to function properly.",
      cc_badge_ok: "Ready",
      cc_badge_pending: "Pending",
      cc_badge_setup: "Setup needed",
      cc_badge_attention: "Needs attention",
      cc_diagnostic_toggle: "Details",
      cc_n_ready: "{n} ready",
      migration_banner_body:
        "Credentials for {modules} could not be moved to secure storage automatically. Re-enter them in the owning module.",
      migration_banner_next:
        "Save the new value; PaperForge will retry secure migration on restart.",
      cc_n_pending: "{n} pending",
      cc_desc:
        "Real-time status of PaperForge core modules. Modules with a pending action need your attention.",
      cc_zone_attention: "Needs Attention",
      cc_zone_modules: "All Modules",
      cc_module_installation: "Foundation",
      cc_module_help: "Help & Docs",
      cc_module_library: "Library",
      cc_module_ocr: "OCR Engine",
      cc_module_memory: "Smart Retrieval",
      cc_module_maintenance: "Maintenance",
      cc_state_ready: "Ready",
      cc_state_limited: "Limited",
      cc_state_unavailable: "Unavailable",
      cc_state_unknown: "Unknown",
      cc_severity_ok: "OK",
      cc_severity_unknown: "Unknown",
      cc_severity_warning: "Warning",
      cc_severity_error: "Error",
      cc_state_missing_input: "Missing Input",
      cc_state_needs_action: "Needs Action",
      cc_action_setup: "Open Setup Wizard",
      setup_bbt_title: "Import BBT JSON",
      setup_bbt_desc:
        "Export your Zotero library as Better BibTeX JSON from Zotero (File \u2192 Export Library \u2192 Better BibTeX JSON), then drop or select the file(s) below.",
      setup_bbt_path: "Exports folder:",
      setup_bbt_drop: "Drop BBT JSON files here or click to select",
      setup_bbt_no_files: "No JSON files imported yet.",
      setup_bbt_invalid: "Invalid JSON file: ",
      setup_bbt_guide: "How to export from Zotero",
      setup_bbt_step1: "1. Install Better BibTeX",
      setup_bbt_step1_desc:
        "In Zotero, go to Tools \u2192 Add-ons, search for Better BibTeX and install it. If you cannot find it, download from: https://github.com/retorquere/zotero-better-bibtex/releases/tag/v9.0.50",
      setup_bbt_step2: "2. Export with auto-update",
      setup_bbt_step2_desc:
        "Right-click your library or collection \u2192 Export Library\u2026 \u2192 choose 'Better BibTeX JSON' format. Check 'Keep updated'.",
      setup_bbt_step3: "3. Save to exports folder",
      setup_bbt_step3_desc:
        "Point the export destination to the folder shown above. Once saved, click 'Detect'.",
      setup_bbt_copy: "Copy",
      setup_bbt_copied: "Path copied",
      setup_bbt_detect: "Detect",
      setup_bbt_found: "Found: ",
      cc_action_probe: "Check",
      cc_action_set_config: "Set Config",
      cc_action_update: "Update",
      action_ocr_run: "Run OCR",
      action_ocr_rebuild_derived: "Rebuild OCR output",
      action_memory_build: "Build memory index",
      action_embed_build: "Build vector index",
      action_embed_resume: "Resume vector build",
      action_foundation_update: "Update PaperForge",
      action_foundation_repair: "Repair runtime",
      cc_reason_installation_ready:
        "PaperForge environment is set up correctly.",
      cc_reason_config_missing:
        "Configuration file is missing. Run setup to create one.",
      cc_reason_config_corrupt:
        "Configuration file is corrupt. Run setup to repair.",
      cc_reason_python_version_unsupported:
        "Python version is not supported. Install Python 3.11+.",
      cc_reason_help_ready: "Help documentation is available.",
      cc_reason_docs_missing: "Help documentation is not yet installed.",
      cc_reason_placeholder:
        "Detection pending \u2014 will show live status once connected.",
      cc_reason_library_ready: "Library is synced and indexed.",
      cc_reason_library_config_missing:
        "Configuration not found \u2014 run setup to configure library.",
      cc_reason_library_config_corrupt:
        "Configuration file is corrupt \u2014 library cannot proceed.",
      cc_reason_library_zotero_missing:
        "Zotero data directory is not configured.",
      cc_reason_library_zotero_not_found:
        "Zotero data directory path does not exist.",
      cc_reason_library_index_missing:
        "Library index has not been built yet \u2014 run sync.",
      cc_reason_library_index_stale:
        "Library index is stale \u2014 sync to refresh.",
      cc_reason_library_sync_failed:
        "Last library sync failed. Retry when the source is available.",
      cc_reason_ocr_ready: "OCR pipeline is configured and functional.",
      cc_reason_ocr_config_missing:
        "Configuration not found \u2014 run setup to configure OCR.",
      cc_reason_ocr_config_corrupt:
        "Configuration file is corrupt \u2014 OCR cannot proceed.",
      cc_reason_ocr_api_key_missing:
        "No OCR API key configured \u2014 add one in setup.",
      cc_reason_ocr_artifacts_missing:
        "No OCR output found \u2014 run OCR on papers.",
      cc_reason_memory_ready: "Smart Retrieval is healthy and indexed.",
      cc_reason_memory_db_missing:
        "The retrieval index has not been built \u2014 build it to enable search.",
      cc_reason_memory_db_corrupt:
        "The retrieval index is damaged \u2014 restore it from backup.",
      cc_reason_memory_index_stale:
        "Smart Retrieval needs a rebuild to match the current library.",
      cc_diag_module: "Module",
      cc_diag_state: "State",
      cc_diag_severity: "Severity",
      cc_diag_activity: "Activity",
      cc_diag_reason: "Reason",
      cc_diag_ttl: "TTL",
      cc_diag_updated: "Updated",
      cc_reason_no_probe: "{module} has not been probed yet.",
      cc_reason_stale: "Cached probe data for {module} is stale.",
      cc_reason_invalid_response: "Probe response for {module} was invalid.",
      activity_syncing: "Syncing...",
      activity_ocr_running: "Processing OCR... {pct}%",
      activity_ocr_running_noprogress: "Processing OCR...",
      cc_action_unknown_verb: "Unknown backend action: {verb}",
      cc_action_investigate: "Running diagnostics...",
      cc_reason_probing: "Checking {module} status...",
      cc_notice_placeholder:
        "{module} module probing is not yet available; it will be added in a future update.",
      cc_notice_refreshed: "Module status refreshed.",
      cc_notice_refresh_failed: "Failed to refresh module status.",
      cc_activity_idle: "Idle",
      cc_activity_running: "Running",
      maintenance_inbox_title: "Maintenance Inbox",
      maintenance_checking: "Checking maintenance status\u2026",
      maintenance_all_clear:
        "All modules are ready \u2014 no maintenance needed.",
      maintenance_n_pending_inbox: "{n} module(s) need attention",
      maintenance_dismiss: "Dismiss",
      maintenance_undismiss: "Show",
      maintenance_ocr_section: "OCR Maintenance",
      maintenance_action_result_success:
        "Action complete \u2014 module is now ready.",
      maintenance_action_result_failure:
        "Action failed \u2014 module still needs attention.",
      maintenance_confirm_redo_title: "Confirm Rerun",
      maintenance_confirm_redo_body:
        "This will delete and re-run OCR for the selected papers. Existing derived artifacts will be replaced.",
      maintenance_confirm_restore_title: "Confirm Restore",
      maintenance_confirm_restore_body:
        "This will restore the memory database from backup. Current data will be replaced.",
      maintenance_confirm_ok: "Proceed",
      maintenance_confirm_cancel: "Cancel",
      confirmation_default_effect: "This action will change PaperForge data.",
      confirm_effect_label: "Effect",
      ocr_already_running: "OCR is already running.",
      ocr_activity_run: "Running OCR\u2026",
      ocr_activity_rebuild: "Rebuilding OCR derived artifacts\u2026",
      ocr_activity_redo: "Running OCR redo\u2026",
      ocr_run_confirm_title: "Run OCR",
      ocr_run_confirm_body:
        "Pending PDFs will be sent to the configured OCR service and may incur cost. Existing OCR output is preserved until each replacement succeeds. You can stop the run safely.",
      embed_already_running: "Vector build is already in progress.",
      embed_activity_stopping: "Stopping vector build\u2026",
      embed_activity_building: "Building vector index\u2026",
      embed_rebuild_title: "Rebuild vector index",
      embed_rebuild_body:
        "The embedding API may incur cost. Existing vectors stay available until the replacement is verified; PDFs, notes, and OCR are preserved. You can stop the build safely.",
      embed_build_complete: "Vector index build complete.",
      embed_build_warning: "Vector index published with warning: {detail}",
      embed_bookkeeping_incomplete: "bookkeeping incomplete",
      embed_build_stopped: "Build stopped. Run again to resume.",
      next_action_pending:
        "Vector embedding is ready. Open Smart Retrieval to review and run it.",
      next_action_runtime_unavailable:
        "PaperForge runtime unavailable; follow-up not started.",
      next_action_failed: "Follow-up failed: {detail}",
      maintenance_issue_draft_title: "OCR Issue Draft",
      maintenance_issue_draft_preview:
        "Review the issue draft below before opening GitHub.",
      maintenance_issue_draft_included: "Included",
      maintenance_issue_draft_redacted: "Redacted",
      maintenance_issue_draft_open_github: "Open GitHub Issue",
      maintenance_issue_draft_edit: "Edit Draft",
      ocr_state_ready: "{count} papers processed with OCR version {version}",
      ocr_state_ready_no_version: "{count} papers processed",
      ocr_state_update_available: "OCR v{version} is available",
      ocr_state_update_description:
        "The new pipeline improves structure detection, figure extraction accuracy, and fulltext formatting.",
      ocr_state_update_safety:
        "Your PDFs and existing OCR data are preserved. Backups are created before changes.",
      ocr_action_re_extract: "Re-extract All Papers",
      ocr_modal_title: "Re-extract All OCR",
      ocr_modal_description:
        "This will re-run OCR on all papers using the latest pipeline version.",
      ocr_state_running: "Re-extracting\u2026",
      sr_state_disabled: "Smart Retrieval is not enabled",
      sr_state_db_missing: "Memory database has not been built yet",
      sr_state_upgrade_available:
        "Your vector index uses the old ChromaDB backend",
      sr_state_build_failed: "The last vector build failed",
      sr_state_build_interrupted:
        "Vector index is partially built \u2014 resume to embed the remaining papers",
      sr_state_identity_changed:
        "Embedding configuration changed \u2014 existing vectors need a rebuild",
      sr_build_failed_notice: "Vector index build failed: {detail}",
      sr_action_build: "Build Index",
      sr_action_rebuild: "Rebuild Index",
      sr_action_upgrade: "Upgrade to vec0",
      sr_db_building: "Building",
      sr_db_partial: "Partially built",
      sr_db_failed: "Build failed",
      sr_db_corrupt: "Corrupted",
      sr_db_stale: "Index stale",
      sr_upgrade_modal_title: "Upgrade Vector Index",
      sr_upgrade_modal_description:
        "This will rebuild your entire vector index using the new vec0 backend.",
      sr_upgrade_modal_safety:
        "Your existing ChromaDB data is preserved. This process requires an active API key and may incur API charges.",
      sr_api_key_notice:
        "API key not configured \u2014 search and retrieval are unavailable",
      sr_config_label: "Configuration",
      ocr_ws_title: "OCR Workspace",
      ocr_ws_filter_all: "All",
      ocr_ws_filter_unprocessed: "Not processed",
      ocr_ws_filter_review: "Needs review",
      ocr_ws_filter_processed: "Processed",
      ocr_ws_col_title: "Title",
      ocr_ws_col_status: "Status",
      ocr_ws_col_version: "Version",
      ocr_ws_col_lastrun: "Last run",
      ocr_ws_btn_preview: "Preview",
      ocr_ws_btn_process_all: "Process All Unprocessed ({count})",
      ocr_ws_detail_view_fulltext: "View Fulltext",
      ocr_ws_detail_restore_backup: "Restore Backup",
      ocr_ws_detail_re_extract: "Re-extract This Paper",
      ocr_ws_detail_run: "Run OCR",
      ocr_ws_re_extract_disabled_title: "Re-extraction not available",
      ocr_ws_re_extract_disabled_body:
        "Single-paper re-extraction currently deletes all OCR data without creating a backup. Use Re-extract All Papers from OCR Settings \u2014 that path has built-in backup.",
      ocr_ws_what_happens: "What happens when I re-extract?",
      ocr_ws_disclosure_text:
        "Re-extraction re-runs OCR on the selected paper. The current version is backed up first. PDFs are never modified.",
      ocr_ws_no_papers: "No papers found with OCR data",
      ocr_ws_lede:
        "View and manage OCR extraction for your literature collection.",
      ocr_ws_processing: "Processing\u2026",
      ocr_ws_stop: "Stop",
      ocr_ws_stop_unavailable_rebuild: "Rebuild is not stoppable from here",
      ocr_ws_btn_refresh: "Refresh",
      ocr_ws_showing: "<strong>{count}</strong> of {total} papers",
      ocr_ws_filter_status: "Filter by status",
      ocr_ws_none_selected: "No papers selected",
      ocr_ws_select_hint:
        "Select papers that are not processed or have an update available.",
      ocr_ws_selected: "{count} paper(s) selected",
      ocr_ws_btn_process_selected: "Process selected",
      ocr_ws_btn_rebuild_selected: "Rebuild selected",
      ocr_ws_tooltip_process:
        "Run full OCR from scratch: extract text, then rebuild derived artifacts. Needed when the OCR model is updated, but generally not required.",
      ocr_ws_tooltip_rebuild:
        "Regenerate rendered results from existing OCR raw data without re-running OCR. Run this when the OCR render version has changed.",
      ocr_ws_tooltip_reextract:
        "Re-run OCR from scratch for this paper (deletes and regenerates all OCR data).",
      ocr_ws_detail_restore_done: "Restored backup {label}",
      next_action_memory_started: "Memory index rebuild started",
      next_action_done: "Follow-up completed",
      next_action_refused: "Follow-up refused by user",
      next_action_unknown: "Unknown follow-up action refused",
      next_action_cancel: "Later",
      ocr_ws_fulltext_not_found: "Fulltext not found",
      ocr_ws_restore_checking: "Checking versions\u2026",
      ocr_ws_restore_unavailable: "No backup versions available",
      ocr_ws_detail_rebuild: "Rebuild this paper",
      ocr_ws_memory_refresh: "Updating local text index\u2026",
      ocr_ws_memory_refresh_failed:
        "Text index refresh failed \u2014 retry later",
      ocr_ws_index_updated:
        "\u6B63\u6587\u7D22\u5F15\u5DF2\u66F4\u65B0\uFF0C\u8BED\u4E49\u7D22\u5F15\u9700\u8981\u5237\u65B0",
      ocr_ws_embed_confirm: "Confirm embedding",
      ocr_ws_embed_confirm_body:
        "Rebuilding vectors for changed papers may call a paid API. Continue?",
      ocr_ws_embed_done: "Vector embedding completed",
      ocr_rebuild_partial: "Rebuild finished with failures",
      ocr_ws_restore_confirm_title: "Restore displayed fulltext",
      ocr_ws_restore_confirm_body:
        "This overwrites render/fulltext.md with the selected version. OCR structure, indexes, memory units, and vectors are NOT affected. Continue?",
      ocr_ws_restore_confirm_btn: "Restore displayed fulltext",
      ocr_ws_restore_stale_notice:
        "This version predates the current structured state; rebuild the paper to re-sync structure",
      ocr_ws_restore_title: "Restore Backup Version",
      ocr_ws_restore_desc:
        "Select a version to restore for this paper. The current fulltext will be replaced.",
      ocr_ws_restore_current: "current",
      ocr_ws_restore_created: "Created:",
      ocr_ws_restore_source: "Source:",
      ocr_ws_restore_renderer: "Renderer:",
      ocr_ws_restore_btn: "Restore",
      ocr_ws_restore_versions: "Versions",
      ocr_ws_restore_compare: "Compare with current",
      ocr_ws_restore_diff_title: "Changes from current vs {v}",
      ocr_ws_restore_no_diff: "No differences found",
      ocr_ws_restore_back: "Back to preview",
      ocr_ws_restore_same: "This is already the current version",
      ocr_ws_close: "Close",
      ocr_ws_fact_version: "OCR Version",
      ocr_ws_fact_last_run: "Last Processed",
      ocr_ws_fact_authors: "Authors",
      ocr_ws_fact_year: "Year",
      ocr_ws_fact_pages: "Pages",
      ocr_ws_fact_backups: "Backups",
      ocr_ws_status_done: "Processed",
      ocr_ws_status_update: "Update available",
      ocr_ws_status_failed: "Failed",
      ocr_ws_status_processing: "Processing",
      ocr_ws_status_nopdf: "No PDF",
      ocr_ws_status_pending: "Pending",
      ocr_ws_status_unknown: "Unknown",
    },
    zh: {
      action_running: "\u6B63\u5728\u6267\u884C ",
      api_key_missing: "\u672A\u914D\u7F6E",
      api_key_set: "\u5DF2\u914D\u7F6E",
      btn_install: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      btn_install_desc:
        "\u81EA\u52A8\u68C0\u6D4B Python + \u524D\u7F6E\u73AF\u5883\uFF0C\u901A\u8FC7\u540E\u6253\u5F00\u5206\u6B65\u5B89\u88C5\u5411\u5BFC",
      btn_reconfig: "\u91CD\u65B0\u914D\u7F6E",
      btn_reconfig_desc:
        "\u91CD\u65B0\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\uFF0C\u4FEE\u6539\u76EE\u5F55\u6216\u5BC6\u94A5\u914D\u7F6E",
      btn_validate: "\u9A8C\u8BC1",
      check_bbt_fail: "\u672A\u68C0\u6D4B\u5230",
      check_bbt_ok: "\u5DF2\u5B89\u88C5",
      check_python_fail: "\u672A\u5B89\u88C5",
      check_python_ok: "\u5DF2\u5C31\u7EEA",
      check_zotero_fail: "\u672A\u68C0\u6D4B\u5230",
      check_zotero_ok: "\u5DF2\u5B89\u88C5",
      complete_export_path:
        "\u5C06 Better BibTeX JSON \u5BFC\u51FA\u4FDD\u5B58\u5230\uFF1A",
      complete_next: "\u4E0B\u4E00\u6B65\u64CD\u4F5C",
      complete_step1: "\u6253\u5F00 PaperForge Dashboard",
      complete_step1_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      complete_step2: "\u540C\u6B65\u6587\u732E",
      complete_step2_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      complete_step3: "\u8FD0\u884C OCR",
      complete_step3_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      complete_step4: "\u914D\u7F6E BBT \u81EA\u52A8\u5BFC\u51FA",
      complete_step4_desc:
        '\u5728 Zotero \u4E2D\uFF0C\u53F3\u952E\u8981\u540C\u6B65\u7684\u6587\u732E\u5E93/\u5206\u7C7B \u2192 \u5BFC\u51FA \u2192 Better BibTeX JSON \u2192 \u542F\u7528"\u4FDD\u6301\u66F4\u65B0"\u3002',
      complete_summary: "\u5F53\u524D\u5B8C\u6574\u914D\u7F6E",
      complete_title: "\u2713 PaperForge \u5B89\u88C5\u5B8C\u6210",
      copied: "\u5DF2\u590D\u5236\uFF01",
      copy_pf_deep_cmd: "\u590D\u5236 /pf-deep \u547D\u4EE4",
      dashboard_drift_warning:
        '\u63D2\u4EF6\u7248\u672C\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u4E0D\u5339\u914D\u3002\u8BF7\u5728\u8BBE\u7F6E\u4E2D\u70B9\u51FB"\u540C\u6B65\u8FD0\u884C\u65F6"\u3002',
      deep_reading_not_found: "\u7CBE\u8BFB\u6587\u4EF6\u672A\u627E\u5230",
      desc: "Obsidian + Zotero \u6587\u732E\u7BA1\u7406\u6D41\u6C34\u7EBF\u3002\u81EA\u52A8\u540C\u6B65\u6587\u732E\u3001\u751F\u6210\u7B14\u8BB0\u3001OCR \u63D0\u53D6\u5168\u6587\uFF0C\u4E00\u7AD9\u5F0F\u6587\u732E\u7CBE\u8BFB\u5DE5\u4F5C\u6D41\u3002",
      dir_base: "Base \u76EE\u5F55",
      dir_index: "\u7D22\u5F15\u76EE\u5F55",
      dir_notes: "\u6B63\u6587\u76EE\u5F55",
      dir_resources: "\u8D44\u6E90\u76EE\u5F55",
      dir_system: "\u7CFB\u7EDF\u76EE\u5F55",
      dir_vault: "Vault \u8DEF\u5F84",
      error_copied: "\u5DF2\u590D\u5236\uFF01",
      error_copy_diagnostic: "\u590D\u5236\u8BCA\u65AD\u4FE1\u606F",
      feat_agent_platform: "Agent \u5E73\u53F0",
      feat_agent_platform_desc:
        "\u9009\u62E9\u8981\u7BA1\u7406\u7684 Agent \u5E73\u53F0\u3002",
      feat_api_base_url: "API \u5730\u5740",
      feat_api_base_url_desc:
        "\u81EA\u5B9A\u4E49 OpenAI \u517C\u5BB9 API \u7AEF\u70B9\u3002\u7559\u7A7A\u4F7F\u7528\u9ED8\u8BA4\u5730\u5740\u3002",
      feat_api_model: "API \u6A21\u578B",
      feat_api_model_desc:
        "\u8BE5\u7AEF\u70B9\u4F7F\u7528\u7684\u5D4C\u5165\u6A21\u578B\u540D\u79F0\u3002",
      feat_build_btn: "\u6784\u5EFA",
      feat_build_complete: "\u5411\u91CF\u6784\u5EFA\u5B8C\u6210\u3002",
      feat_build_failed:
        "\u6784\u5EFA\u5931\u8D25\u3002\u8BF7\u67E5\u770B\u7EC8\u7AEF\u8F93\u51FA\u3002",
      feat_building: "\u6784\u5EFA\u4E2D\u2026",
      feat_cache_remove_failed: "\u5931\u8D25\uFF1A{0}",
      feat_cache_removed: "\u6A21\u578B\u7F13\u5B58\u5DF2\u6E05\u9664\u3002",
      feat_checking: "\u68C0\u6D4B\u4E2D\u2026",
      feat_checking_btn: "\u68C0\u6D4B\u4E2D\u2026",
      feat_deps_checking: "\u6B63\u5728\u68C0\u6D4B\u4F9D\u8D56\u2026",
      feat_enter_key:
        "\u8BF7\u8F93\u5165\u6709\u6548\u7684 OpenAI API Key\u3002",
      feat_install_btn: "\u5B89\u88C5",
      feat_install_deps: "\u5B89\u88C5\u4F9D\u8D56",
      feat_install_done:
        "\u4F9D\u8D56\u5DF2\u5B89\u88C5\u3002\u6B63\u5728\u6784\u5EFA\u5411\u91CF\u2026",
      feat_install_failed: "\u5B89\u88C5\u5931\u8D25\uFF1A",
      feat_installing: "\u5B89\u88C5\u4E2D\u2026",
      feat_installing_pkgs: "\u6B63\u5728\u5B89\u88C5 {pkgs}...",
      feat_key_rejected: "API Key \u88AB\u62D2\u7EDD\u3002",
      feat_memory_desc:
        "\u8BB0\u5FC6\u5C42\u662F PaperForge \u7684\u6838\u5FC3\u6570\u636E\u5F15\u64CE\uFF0C\u57FA\u4E8E SQLite \u6784\u5EFA\u3002\u5B83\u6574\u5408\u4E86\u6587\u732E\u5143\u6570\u636E\uFF08\u8BBA\u6587\u3001\u8D44\u6E90\u6587\u4EF6\u3001\u522B\u540D\u3001\u9605\u8BFB\u4E8B\u4EF6\uFF09\uFF0C\u652F\u6301 FTS5 \u5143\u6570\u636E\u68C0\u7D22\uFF08\u6807\u9898\u3001\u6458\u8981\u3001\u4F5C\u8005\u3001domain\u3001collection\uFF09\uFF0C\u5E76\u4E3A agent-context \u548C paper-status \u547D\u4EE4\u63D0\u4F9B\u6570\u636E\u652F\u6491\u3002\u59CB\u7EC8\u8FD0\u884C\uFF0C\u65E0\u9700\u624B\u52A8\u5F00\u542F\u3002",
      feat_memory_rebuild_btn: "\u91CD\u5EFA\u6570\u636E\u5E93",
      feat_memory_rebuild_done:
        "\u8BB0\u5FC6\u6570\u636E\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002",
      feat_memory_rebuild_failed: "\u91CD\u5EFA\u5931\u8D25\u3002",
      feat_memory_rebuilding: "\u91CD\u5EFA\u4E2D\u2026",
      feat_model: "\u6A21\u578B",
      feat_model_changed_warn:
        "\u6A21\u578B\u5DF2\u66F4\u6362\uFF08{0} -> {1}\uFF09\u3002\u5DF2\u6709\u5411\u91CF\u4E0D\u517C\u5BB9\u2014\u2014\u9700\u8981\u91CD\u5EFA\u3002",
      feat_network_error: "\u7F51\u7EDC\u9519\u8BEF\uFF1A",
      feat_no_python:
        "\u672A\u627E\u5230 Python\u3002\u8BF7\u67E5\u770B\u5B89\u88C5\u6807\u7B7E\u9875\u3002",
      feat_not_cached: "\u672A\u7F13\u5B58",
      feat_openai_key: "OpenAI API Key",
      feat_openai_key_desc:
        "\u7528\u4E8E API \u5D4C\u5165\u8C03\u7528\uFF0C\u6A21\u578B\u5728\u4E0B\u65B9\u5B9A\u4E49\u3002",
      feat_output_copied:
        "\u8F93\u51FA\u5DF2\u590D\u5236\u5230\u526A\u8D34\u677F\u3002",
      feat_rebuild_btn: "\u91CD\u5EFA",
      feat_rebuild_vectors: "\u91CD\u5EFA\u5411\u91CF",
      feat_rebuild_vectors_changed:
        "\u6A21\u578B\u5DF2\u66F4\u6362 \u2014 \u9700\u8981\u91CD\u5EFA\u5411\u91CF\u3002",
      feat_rebuild_vectors_desc:
        "\u91CD\u5EFA\u6240\u6709 OCR \u5168\u6587\u5411\u91CF\u3002\u66F4\u6362\u6A21\u578B\u6216\u6A21\u5F0F\u540E\u9700\u8981\u91CD\u5EFA\u3002",
      feat_removing: "\u5220\u9664\u4E2D\u2026",
      feat_retry_btn: "\u91CD\u8BD5",
      feat_skills_desc:
        "\u7BA1\u7406 Vault \u4E2D\u5DF2\u5B89\u88C5\u7684 Agent \u6280\u80FD\u3002\u6BCF\u884C\u5BF9\u5E94\u4E00\u4E2A SKILL.md \u6587\u4EF6\uFF0C\u5173\u95ED\u5F00\u5173\u53EF\u963B\u6B62 Agent \u81EA\u52A8\u8C03\u7528\u8BE5\u6280\u80FD\u3002",
      feat_skills_system:
        "\u7CFB\u7EDF\u6280\u80FD\u968F PaperForge \u4E00\u540C\u53D1\u5E03\uFF0C\u4F1A\u8DDF\u968F PaperForge \u7248\u672C\u66F4\u65B0\u3002",
      feat_skills_user:
        "\u7528\u6237\u6280\u80FD\u662F\u4F60\u81EA\u884C\u5B89\u88C5\u6216\u521B\u5EFA\u7684\u81EA\u5B9A\u4E49\u6280\u80FD\u3002",
      feat_uninstall_btn: "\u5378\u8F7D",
      feat_valid_key: "API Key \u6709\u6548\u3002",
      feat_vector_corrupted:
        "\u5411\u91CF\u7D22\u5F15\u5DF2\u635F\u574F \u2014 \u9700\u8981\u5F3A\u5236\u91CD\u5EFA\u3002",
      field_paddleocr: "PaddleOCR API \u5BC6\u94A5",
      field_python_custom: "\u81EA\u5B9A\u4E49 Python \u8DEF\u5F84",
      field_python_interp: "\u5F53\u524D Python \u89E3\u91CA\u5668",
      field_zotero_data: "Zotero \u6570\u636E\u76EE\u5F55",
      field_zotero_placeholder:
        "\u53EF\u9009\uFF0C\u7528\u4E8E\u81EA\u52A8\u68C0\u6D4B PDF",
      guide_ocr: "\u8FD0\u884C OCR",
      guide_ocr_desc:
        "Dashboard \u4E2D\u70B9 Run OCR\uFF0C\u63D0\u53D6 PDF \u5168\u6587\u4E0E\u56FE\u8868",
      guide_open: "\u6253\u5F00 Dashboard",
      guide_open_desc:
        "Ctrl+P \u2192 \u8F93\u5165 PaperForge: Open Dashboard\uFF0C\u6216\u70B9\u5DE6\u4FA7\u4E66\u672C\u56FE\u6807",
      guide_sync: "\u540C\u6B65\u6587\u732E",
      guide_sync_desc:
        "Dashboard \u4E2D\u70B9 Sync Library\uFF0C\u4ECE Zotero \u62C9\u53D6\u6587\u732E\u751F\u6210\u7B14\u8BB0",
      header_title: "PaperForge",
      install_bootstrapping:
        "\u672A\u68C0\u6D4B\u5230 PaperForge Python \u5305\uFF0C\u6B63\u5728\u81EA\u52A8\u5B89\u88C5\u2026",
      install_btn: "\u5F00\u59CB\u5B89\u88C5",
      install_btn_retry: "\u91CD\u8BD5",
      install_btn_running: "\u6B63\u5728\u5B89\u88C5...",
      install_complete: "\u2713 \u5B89\u88C5\u5B8C\u6210\uFF01",
      install_failed: "\u2717 \u5B89\u88C5\u5931\u8D25\uFF1A",
      install_validating:
        "\u6B63\u5728\u6821\u9A8C\u5B89\u88C5\u73AF\u5883\u2026",
      jump_to_deep_reading: "\u8DF3\u8F6C\u5230\u7CBE\u8BFB",
      label_agent: "Agent \u5E73\u53F0",
      nav_close: "\u5173\u95ED",
      nav_next: "\u4E0B\u4E00\u6B65 \u2192",
      nav_prev: "\u2190 \u4E0A\u4E00\u6B65",
      no_pending_ocr: "\u6240\u6709 OCR \u4EFB\u52A1\u5DF2\u5B8C\u6210",
      not_set: "\u672A\u8BBE\u7F6E",
      notice_check_fail: "\u7F3A\u5931\uFF1A",
      notice_python_missing:
        "Python \u672A\u68C0\u6D4B\u5230\uFF0C\u8BF7\u5148\u5B89\u88C5 Python 3.11+ \u5E76\u52A0\u5165 PATH",
      ocr_privacy_title: "OCR \u9690\u79C1\u63D0\u793A",
      ocr_privacy_warning:
        "OCR \u4F1A\u5C06 PDF \u4E0A\u4F20\u5230 PaddleOCR API \u8FDB\u884C\u5904\u7406\u3002\u8BF7\u4E0D\u8981\u4E0A\u4F20\u5305\u542B\u654F\u611F\u4FE1\u606F\u6216\u65E0\u6CD5\u5916\u4F20\u7684\u6587\u732E\u3002",
      ocr_queue_add: "\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_added: "\u5DF2\u52A0\u5165 OCR \u961F\u5217",
      ocr_queue_remove: "\u79FB\u51FA OCR \u961F\u5217",
      ocr_queue_removed: "\u5DF2\u79FB\u51FA OCR \u961F\u5217",
      ocr_understand: "\u6211\u4E86\u89E3\uFF0C\u7EE7\u7EED",
      optional_later:
        "\uFF08\u7A0D\u540E\u53EF\u5728\u8BBE\u7F6E\u4E2D\u8865\u5145\uFF09",
      orphan_delete_failed: "\u6E05\u7406\u5931\u8D25",
      orphan_delete_selected: "\u5220\u9664 {count} \u7BC7",
      orphan_deleted:
        "\u5DF2\u5220\u9664 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      orphan_desc:
        "\u8FD9\u4E9B\u6587\u732E\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002",
      orphan_deselect_all: "\u53D6\u6D88\u5168\u9009",
      orphan_explain:
        "\u5DF2\u4ECE Zotero \u4E2D\u79FB\u9664\u3002\u5DE5\u4F5C\u533A\u6587\u4EF6\u4ECD\u4FDD\u7559\u5728\u78C1\u76D8\u4E0A\u3002",
      orphan_keep_all: "\u4FDD\u7559\u5168\u90E8",
      orphan_none_selected: "\u672A\u9009\u62E9\u4EFB\u4F55\u6587\u732E",
      orphan_select_all: "\u5168\u9009",
      orphan_title: "\u53D1\u73B0 {count} \u7BC7\u6B8B\u7559\u6587\u732E",
      panel_actions: "\u5FEB\u6377\u64CD\u4F5C",
      prep_bbt: "Better BibTeX",
      prep_bbt_desc:
        "Zotero \u2192 \u5DE5\u5177 \u2192 \u63D2\u4EF6 \u2192 \u5B89\u88C5 Better BibTeX",
      prep_export: "BBT \u81EA\u52A8\u5BFC\u51FA",
      prep_export_desc:
        "\u53F3\u952E\u6587\u732E\u5B50\u5206\u7C7B \u2192 \u5BFC\u51FA\u5206\u7C7B \u2192 BetterBibTeX JSON \u2192 \u52FE\u9009\u4FDD\u6301\u66F4\u65B0 \u2192 \u5BFC\u51FA\u5230\uFF08JSON \u6587\u4EF6\u540D\u5373\u4E3A Base \u540D\uFF09\uFF1A",
      prep_export_path_label:
        "\u5C06\u5BFC\u51FA\u7684 JSON \u6587\u4EF6\u4FDD\u5B58\u5230\u6B64\u6587\u4EF6\u5939\uFF1A",
      prep_key: "PaddleOCR Key",
      prep_key_desc:
        "\u4ECE https://aistudio.baidu.com/paddleocr \u83B7\u53D6 API \u5BC6\u94A5",
      prep_python: "Python 3.11+",
      prep_python_desc:
        "\u786E\u4FDD Python \u53EF\u547D\u4EE4\u884C\u8C03\u7528\u3002\u70B9\u51FB\u4E0B\u65B9\u6309\u94AE\u81EA\u52A8\u68C0\u6D4B\u3002",
      prep_zotero: "Zotero \u684C\u9762\u7248",
      prep_zotero_desc: "\u5B89\u88C5 Zotero (https://www.zotero.org)",
      run_in_agent: "\u5728 {0} \u4E2D\u8FD0\u884C",
      runtime_health: "\u8FD0\u884C\u65F6\u72B6\u6001",
      runtime_health_checking: "\u6B63\u5728\u68C0\u6D4B\u2026",
      runtime_health_desc:
        "\u68C0\u67E5\u63D2\u4EF6\u4E0E Python \u8FD0\u884C\u65F6\u7248\u672C\u7684\u5339\u914D\u60C5\u51B5\uFF0C\u5E76\u786E\u8BA4\u5DF2\u90E8\u7F72\u7684 skill contract \u662F\u5426\u4E3A\u5F53\u524D\u7248\u672C\u3002",
      runtime_health_match: "\u5339\u914D",
      runtime_health_mismatch: "\u4E0D\u5339\u914D",
      runtime_health_package_ver: "Python \u5305 v{0}",
      runtime_health_plugin_ver: "\u63D2\u4EF6 v{0}",
      runtime_health_sync: "\u540C\u6B65\u8FD0\u884C\u65F6",
      runtime_health_sync_done:
        "\u8FD0\u884C\u65F6\u5DF2\u540C\u6B65\u81F3 v{0}",
      runtime_health_sync_fail:
        "\u8FD0\u884C\u65F6\u540C\u6B65\u5931\u8D25\uFF1A{0}",
      runtime_health_syncing: "\u6B63\u5728\u540C\u6B65\u2026",
      section_config: "\u5F53\u524D\u914D\u7F6E",
      section_guide: "\u64CD\u4F5C\u65B9\u5F0F",
      section_prep: "\u5B89\u88C5\u51C6\u5907",
      section_prep_desc:
        "\u9996\u6B21\u4F7F\u7528\u524D\uFF0C\u8BF7\u4F9D\u6B21\u5B8C\u6210\u4EE5\u4E0B\u51C6\u5907\uFF1A",
      setup_done:
        "\u2713 PaperForge \u73AF\u5883\u5DF2\u914D\u7F6E\u5B8C\u6210",
      setup_pending:
        "\u5C1A\u672A\u5B89\u88C5\uFF0C\u5B8C\u6210\u5B89\u88C5\u51C6\u5907\u540E\u70B9\u51FB\u5B89\u88C5\u5411\u5BFC",
      tab_overview: "\u6982\u89C8",
      tab_modules: "\u6A21\u5757\u8BE6\u60C5",
      tab_help: "\u5E2E\u52A9",
      tab_features: "\u529F\u80FD",
      tab_setup: "\u5B89\u88C5",
      tab_maintenance: "\u7EF4\u62A4",
      validate_base: "Base \u76EE\u5F55\u672A\u586B\u5199",
      validate_fail: "\u914D\u7F6E\u9A8C\u8BC1\u5931\u8D25",
      validate_index: "\u7D22\u5F15\u76EE\u5F55\u672A\u586B\u5199",
      validate_key: "PaddleOCR API \u5BC6\u94A5\u672A\u586B\u5199",
      validate_notes: "\u6B63\u6587\u76EE\u5F55\u672A\u586B\u5199",
      validate_resources: "\u8D44\u6E90\u76EE\u5F55\u672A\u586B\u5199",
      validate_system: "\u7CFB\u7EDF\u76EE\u5F55\u672A\u586B\u5199",
      validate_vault: "Vault \u8DEF\u5F84\u672A\u586B\u5199",
      validate_zotero:
        "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879",
      wizard_agent_hint:
        "\u9009\u62E9\u4F60\u4F7F\u7528\u7684 AI Agent \u5E73\u53F0\uFF0C\u5B89\u88C5\u65F6\u5C06\u6309\u5BF9\u5E94\u683C\u5F0F\u90E8\u7F72\u6280\u80FD\u6587\u4EF6\uFF1A",
      wizard_dir_hint:
        "\u8D44\u6E90\u76EE\u5F55\u662F\u6587\u732E\u6570\u636E\u7684\u7EDF\u4E00\u6839\u76EE\u5F55\uFF0C\u4EE5\u4E0B\u5B50\u76EE\u5F55\u5C06\u521B\u5EFA\u5728\u5176\u5185\u90E8\uFF1A",
      wizard_dir_sub_hint:
        "\u8D44\u6E90\u76EE\u5F55\u5185\u7684\u4E24\u4E2A\u5B50\u76EE\u5F55\uFF1A",
      wizard_intro:
        "\u672C\u5411\u5BFC\u5C06\u5F15\u5BFC\u60A8\u5B8C\u6210 PaperForge \u73AF\u5883\u7684\u5B8C\u6574\u914D\u7F6E\u3002\u5B89\u88C5\u8FC7\u7A0B\u4F1A\u81EA\u52A8\u521B\u5EFA\u6240\u6709\u76EE\u5F55\u7ED3\u6784\uFF0C\u65E0\u9700\u624B\u52A8\u64CD\u4F5C\u3002",
      wizard_keys_hint:
        "\u4EE5\u4E0B\u4E3A API \u5BC6\u94A5\u4E0E Zotero \u914D\u7F6E\uFF1A",
      wizard_preview:
        "\u7CFB\u7EDF\u6587\u4EF6\u548C Agent \u914D\u7F6E\u4F4D\u4E8E Vault \u6839\u76EE\u5F55\u4E0B\u3002\u6587\u732E\u6570\u636E\uFF08\u6B63\u6587\u3001\u7D22\u5F15\uFF09\u7EDF\u4E00\u5B58\u653E\u5728\u8D44\u6E90\u76EE\u5F55\u5185\u3002\u5B89\u88C5\u540E\u4ECD\u53EF\u5728\u8BBE\u7F6E\u4E2D\u4FEE\u6539\u3002",
      wizard_safety:
        "\u5B89\u5168\u8BF4\u660E\uFF1A\u5982\u679C\u4F60\u9009\u62E9\u7684\u76EE\u5F55\u91CC\u5DF2\u7ECF\u6709\u6587\u4EF6\uFF0C\u5B89\u88C5\u5411\u5BFC\u4F1A\u4FDD\u7559\u5DF2\u6709\u5185\u5BB9\uFF0C\u53EA\u8865\u5145\u7F3A\u5931\u7684 PaperForge \u6587\u4EF6\u548C\u76EE\u5F55\u3002",
      wizard_step1: "\u6982\u89C8",
      wizard_step2: "\u76EE\u5F55",
      wizard_step3: "Agent",
      wizard_step4: "\u5B89\u88C5",
      wizard_step5: "\u5B8C\u6210",
      wizard_skip_ocr_desc:
        "OCR \u529F\u80FD\u5728\u914D\u7F6E\u6709\u6548\u7684 PaddleOCR API \u5BC6\u94A5\u4E4B\u524D\u4E0D\u53EF\u7528\u3002\u60A8\u53EF\u4EE5\u7EE7\u7EED\u5B8C\u6210\u8BBE\u7F6E\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_skip_ocr_continue:
        "\u7EE7\u7EED\uFF0C\u7A0D\u540E\u914D\u7F6E\u5BC6\u94A5",
      wizard_skip_ocr_back: "\u8FD4\u56DE\u914D\u7F6E",
      wizard_api_hint_skip:
        "OCR \u5BC6\u94A5\u4E3A\u9009\u586B\u9879 \u2014 \u53EF\u8DF3\u8FC7\uFF0C\u7A0D\u540E\u5728\u8BBE\u7F6E\u4E2D\u914D\u7F6E\u3002",
      wizard_sys_hint:
        "\u72EC\u7ACB\u4E8E\u8D44\u6E90\u76EE\u5F55\u7684\u7CFB\u7EDF\u6587\u4EF6\uFF1A",
      wizard_title: "PaperForge \u5B89\u88C5\u5411\u5BFC",
      ocr_maint_no_action: "\u65E0\u9700\u5904\u7406",
      ocr_maint_rebuild: "\u5EFA\u8BAE\u91CD\u5EFA",
      ocr_maint_failed: "OCR \u5931\u8D25",
      ocr_maint_limited: "\u7ED3\u679C\u4E00\u822C",
      ocr_maint_needs_attention: "\u9700\u8981\u5904\u7406",
      ocr_maint_limitations: "\u7ED3\u679C\u8BF4\u660E",
      ocr_maint_hero_ok: "OCR \u6574\u4F53\u6B63\u5E38\u3002",
      ocr_maint_hero_warn:
        "OCR \u9700\u8981\u5173\u6CE8\uFF1A{rebuild} \u7BC7\u5EFA\u8BAE\u91CD\u5EFA\uFF0C{failed} \u7BC7\u5904\u7406\u5931\u8D25\u3002",
      ocr_maint_hero_note:
        "\u672C\u9875\u53EA\u63D0\u793A\u7EF4\u62A4\u540E\u5927\u6982\u7387\u4F1A\u6539\u5584\u7684\u95EE\u9898\u3002\u90E8\u5206\u8BBA\u6587\u6548\u679C\u4E00\u822C\uFF0C\u7EF4\u62A4\u672A\u5FC5\u80FD\u6539\u5584\u3002",
      ocr_maint_limitations_intro:
        "\u8FD9\u7C7B\u8BBA\u6587\u901A\u5E38\u8868\u793A\u7248\u5F0F\u590D\u6742\u6216\u4FE1\u53F7\u504F\u5F31\uFF0CPaperForge \u76EE\u524D\u6CA1\u6709\u9AD8\u7F6E\u4FE1\u5EA6\u7684\u7EF4\u62A4\u5EFA\u8BAE\u3002",
      ocr_maint_all_papers: "\u5168\u90E8\u8BBA\u6587",
      ocr_maint_rebuild_btn: "\u91CD\u5EFA\u7ED3\u679C",
      ocr_maint_redo_btn: "\u91CD\u65B0 OCR",
      ocr_maint_redo_confirm:
        "\u786E\u8BA4\u91CD\u65B0 OCR {n} \u7BC7\u8BBA\u6587\uFF1F\u73B0\u6709\u7684\u6D3E\u751F OCR \u7ED3\u679C\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_group_retry: "\u9700\u8981\u91CD\u8BD5",
      maintenance_group_rebuild: "\u53EF\u91CD\u5EFA\u7ED3\u679C",
      maintenance_group_legacy:
        "\u53EF\u5347\u7EA7\u65E7\u7ED3\u679C\uFF08\u53EF\u9009\uFF09",
      maintenance_btn_retry: "\u91CD\u8BD5",
      maintenance_btn_rebuild: "\u91CD\u5EFA",
      maintenance_btn_upgrade: "\u5347\u7EA7",
      maintenance_refresh_spinning: "\u6B63\u5728\u66F4\u65B0\u2026",
      maintenance_all_good: "\u2705 \u5168\u90E8\u6B63\u5E38",
      maintenance_n_pending: "{n} \u7BC7\u9700\u8981\u5904\u7406",
      maintenance_filter_all: "\u5168\u90E8",
      maintenance_filter_recommended: "\u5EFA\u8BAE\u5904\u7406",
      maintenance_batch_rebuild: "\u25B6 \u91CD\u5EFA\u5DF2\u9009",
      maintenance_batch_redo: "\u25B6 \u5168\u90E8\u91CD\u8DD1 OCR",
      maintenance_stop: "\u505C\u6B62",
      maintenance_batch_complete:
        "\u6279\u91CF\u64CD\u4F5C\u5B8C\u6210 \u2014 \u5904\u7406\u4E86 {n} \u7BC7\u8BBA\u6587\u3002",
      maintenance_progress_label: "{current}/{total} \u7BC7",
      version_panel_title: "\u7248\u672C\u5386\u53F2",
      version_panel_back: "\u8FD4\u56DE",
      version_filter_placeholder: "\u641C\u7D22\u8BBA\u6587...",
      version_papers_count: "{n} \u7BC7\u8BBA\u6587",
      version_current: "\u5F53\u524D",
      version_restore_btn: "\u6062\u590D",
      version_compare_btn: "\u5BF9\u6BD4",
      version_restore_selected: "\u6062\u590D\u9009\u4E2D\u7248\u672C",
      version_clear_old: "\u6E05\u9664\u65E7\u7248\u672C (\u91CA\u653E {size})",
      version_no_backups:
        "\u6CA1\u6709\u53EF\u6062\u590D\u7684\u5386\u53F2\u7248\u672C",
      md_select_installation: "\u57FA\u7840\u73AF\u5883",
      md_select_library: "\u6587\u732E\u5E93",
      md_select_ocr: "OCR",
      md_select_memory: "\u667A\u80FD\u68C0\u7D22",
      md_select_agent: "Agent \u96C6\u6210",
      installation_detail_heading: "\u57FA\u7840\u73AF\u5883",
      library_detail_heading: "\u6587\u732E\u5E93",
      ocr_detail_heading: "OCR",
      memory_detail_heading: "\u667A\u80FD\u68C0\u7D22",
      agent_detail_heading: "Agent \u96C6\u6210",
      btn_back_to_overview: "\u2190 \u8FD4\u56DE\u6982\u89C8",
      agent_integration_section: "Agent \u96C6\u6210",
      module_detail_open_installation: "\u6253\u5F00\u57FA\u7840\u73AF\u5883",
      module_detail_open_help: "\u5E2E\u52A9",
      module_detail_open_maintenance: "\u7EF4\u62A4",
      module_detail_open_library: "\u6253\u5F00\u6587\u732E\u5E93",
      module_detail_open_ocr: "\u6253\u5F00 OCR",
      module_detail_open_memory: "\u6253\u5F00\u667A\u80FD\u68C0\u7D22",
      action_unknown_pair: "\u672A\u77E5\u64CD\u4F5C: {verb}",
      update_python_manual:
        "Python 3.11+ \u5347\u7EA7\u9700\u8981\u624B\u52A8\u5B89\u88C5(python.org \u6216\u5305\u7BA1\u7406\u5668)\u3002",
      update_done: "PaperForge \u5DF2\u66F4\u65B0",
      update_failed: "\u66F4\u65B0\u5931\u8D25",
      migrate_done: "\u540E\u7AEF\u5DF2\u8FC1\u79FB\u5230 sqlite-vec",
      migrate_failed: "\u540E\u7AEF\u8FC1\u79FB\u5931\u8D25",
      ocr_stop_batch: "\u505C\u6B62 OCR \u6279\u5904\u7406",
      runtime_not_available: "\u73AF\u5883\u4E0D\u53EF\u7528",
      md_unavailable_module: "\u6682\u4E0D\u53EF\u7528",
      managed_runtime_status: "\u8FD0\u884C\u65F6\u72B6\u6001",
      managed_runtime_install: "\u5B89\u88C5\u8FD0\u884C\u65F6",
      managed_runtime_repair: "\u4FEE\u590D\u8FD0\u884C\u65F6",
      managed_runtime_update: "\u66F4\u65B0\u8FD0\u884C\u65F6",
      managed_runtime_check_status: "\u68C0\u67E5\u72B6\u6001",
      managed_runtime_refresh: "\u5237\u65B0\u72B6\u6001",
      managed_runtime_manual_setup: "\u624B\u52A8\u914D\u7F6E",
      managed_runtime_stop: "\u505C\u6B62",
      managed_runtime_unknown_state: "\u672A\u77E5",
      managed_runtime_ok_state: "\u5C31\u7EEA",
      managed_runtime_not_installed: "\u672A\u5B89\u88C5",
      managed_runtime_needs_repair: "\u9700\u8981\u4FEE\u590D",
      managed_runtime_unavailable: "\u4E0D\u53EF\u7528",
      managed_runtime_last_verified: "\u6700\u540E\u9A8C\u8BC1\uFF1A{time}",
      managed_runtime_running:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u8FDB\u884C\u4E2D...",
      managed_runtime_action_complete:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5DF2\u5B8C\u6210\u3002",
      managed_runtime_action_cancelled:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5DF2\u53D6\u6D88\u3002",
      managed_runtime_action_failed:
        "\u8FD0\u884C\u65F6\u64CD\u4F5C\u5931\u8D25\uFF1A{error}",
      version_restore_confirm:
        "\u786E\u8BA4\u5C06 {paper} \u6062\u590D\u5230 {label}\uFF1F",
      version_restore_done: "\u5DF2\u6062\u590D\u5230 {label}",
      version_compare_title: "{vA} vs {vB}",
      version_compare_paragraphs: "{n} \u6BB5\u6709\u53D8\u5316",
      version_error_read: "\u65E0\u6CD5\u8BFB\u53D6\u7248\u672C\u6570\u636E",
      retrieval_search_placeholder:
        "\u641C\u7D22\u8BBA\u6587...\uFF08@ \u542F\u52A8\u6DF1\u5EA6\u641C\u7D22\uFF09",
      retrieval_search_placeholder_deep:
        "\u641C\u7D22\u8BBA\u6587\u5185\u5BB9...",
      retrieval_search_idle_hint:
        "\u8F93\u5165\u5173\u952E\u8BCD\u641C\u7D22\u8BBA\u6587\uFF0C\u6216\u4EE5 @ \u5F00\u5934\u641C\u7D22\u8BBA\u6587\u5185\u5BB9",
      retrieval_searching_metadata: "\u641C\u7D22\u5143\u6570\u636E\u4E2D...",
      retrieval_searching_deep: "\u6DF1\u5EA6\u641C\u7D22\u4E2D...",
      retrieval_search_cancel: "\u53D6\u6D88",
      retrieval_results_count: "{n} \u4E2A\u7ED3\u679C",
      retrieval_empty: "\u672A\u627E\u5230\u5339\u914D\u7684\u8BBA\u6587\u3002",
      retrieval_empty_tips:
        "\u5C1D\u8BD5\u66F4\u5BBD\u6CDB\u7684\u5173\u952E\u8BCD\uFF0C\u6216\u4F7F\u7528 @ \u6DF1\u5EA6\u641C\u7D22\u8BBA\u6587\u5185\u5BB9\u3002",
      retrieval_vectors_not_built: "\u5411\u91CF\u7D22\u5F15\u672A\u6784\u5EFA",
      retrieval_vectors_not_built_desc:
        "\u6784\u5EFA\u5411\u91CF\u7D22\u5F15\u4EE5\u542F\u7528 @ \u6DF1\u5EA6\u8BED\u4E49\u641C\u7D22\u3002",
      retrieval_open_vector_settings: "\u6253\u5F00\u5411\u91CF\u8BBE\u7F6E",
      retrieval_backend_unavailable:
        "\u641C\u7D22\u540E\u7AEF\u4E0D\u53EF\u7528",
      retrieval_backend_unavailable_desc:
        "Python CLI \u641C\u7D22\u540E\u7AEF\u672A\u6B63\u5E38\u54CD\u5E94\u3002",
      retrieval_run_doctor: "\u8FD0\u884C\u8BCA\u65AD",
      retrieval_retry: "\u91CD\u8BD5",
      retrieval_timeout_title: "\u641C\u7D22\u8D85\u65F6",
      retrieval_timeout_desc:
        "\u641C\u7D22\u8017\u65F6\u8FC7\u957F\uFF0C\u8BF7\u5C1D\u8BD5\u66F4\u7CBE\u786E\u7684\u67E5\u8BE2\u3002",
      retrieval_model_changed: "\u6A21\u578B\u5DF2\u66F4\u6362",
      retrieval_model_changed_desc:
        "\u5D4C\u5165\u6A21\u578B\u5DF2\u66F4\u6362\uFF0C\u9700\u91CD\u5EFA\u5411\u91CF\u540E\u624D\u80FD\u4F7F\u7528\u6DF1\u5EA6\u641C\u7D22\u3002",
      retrieval_rebuild_vectors: "\u91CD\u5EFA\u5411\u91CF",
      retrieval_build_idle: "\u5411\u91CF\u6570\u636E\u5E93\u5C31\u7EEA",
      retrieval_build_ready: "\u5DF2\u6784\u5EFA {n} \u4E2A\u5411\u91CF",
      retrieval_build_stopping: "\u6B63\u5728\u505C\u6B62...",
      cc_module_foundation: "\u57FA\u7840\u73AF\u5883",
      cc_module_agent: "Agent \u96C6\u6210",
      cc_badge_checking: "\u6B63\u5728\u68C0\u67E5",
      cc_badge_ready: "\u5DF2\u5C31\u7EEA",
      cc_badge_not_enabled: "\u672A\u542F\u7528",
      cc_badge_setup_required: "\u9700\u8981\u8BBE\u7F6E",
      cc_badge_action_required: "\u9700\u8981\u64CD\u4F5C",
      cc_badge_detection_failed: "\u68C0\u6D4B\u5931\u8D25",
      cc_summary_ready: "PaperForge \u5DF2\u5C31\u7EEA",
      cc_summary_incomplete: "\u8BBE\u7F6E\u672A\u5B8C\u6210",
      cc_summary_ready_body:
        "\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u5747\u5DF2\u6B63\u5E38\u8FD0\u884C\u3002",
      cc_summary_incomplete_body:
        "\u8BF7\u5B8C\u6210\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u8BBE\u7F6E\u540E\u518D\u4F7F\u7528 PaperForge\u3002",
      cc_summary_checking: "\u6B63\u5728\u68C0\u67E5 PaperForge",
      cc_summary_checking_body:
        "\u6B63\u5728\u68C0\u67E5\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u72B6\u6001\u2026",
      cc_refresh_btn: "\u5237\u65B0\u72B6\u6001",
      cc_last_checked: "\u4E0A\u6B21\u68C0\u67E5\uFF1A",
      cc_needs_attention: "\u9879\u9700\u8981\u5173\u6CE8",
      cc_checked_pending: "\u5C1A\u672A\u68C0\u67E5",
      cc_eyebrow: "\u63A7\u5236\u4E2D\u5FC3",
      cc_title: "\u6587\u732E\u5DE5\u4F5C\u6D41",
      cc_lede:
        "\u67E5\u770B\u5404\u9879\u80FD\u529B\u7684\u8FD0\u884C\u72B6\u6001\u3001\u9700\u8981\u5904\u7406\u7684\u4E8B\u9879\uFF0C\u4EE5\u53CA\u4E0B\u4E00\u6B65\u8BE5\u505A\u4EC0\u4E48\u3002",
      cc_modules_header: "\u6A21\u5757",
      cc_five_capabilities: "\u4E94\u4E2A\u529F\u80FD",
      cc_optional_note:
        "\u53EF\u9009\u6A21\u5757\u4E0D\u5F71\u54CD\u6838\u5FC3\u8FD0\u884C\u72B6\u6001\u3002",
      cc_maintenance_count: "{n} \u9879\u9700\u8981\u5173\u6CE8",
      cc_card_retry: "\u91CD\u8BD5",
      cc_consequence_default:
        "\u5F53\u524D\u72B6\u6001\u6682\u4E0D\u53EF\u7528\u3002",
      cc_action_rebuild_derived: "\u91CD\u5EFA",
      ocr_progress: "{current}/{total} \u7BC7\u8BBA\u6587",
      cc_operational_modules: "\u8FD0\u884C\u6A21\u5757",
      cc_consequence_checking:
        "\u6B63\u5728\u68C0\u67E5\u6700\u65B0\u72B6\u6001\u2026",
      cc_consequence_detection_failed:
        "PaperForge \u65E0\u6CD5\u786E\u5B9A\u5F53\u524D\u72B6\u6001\u3002",
      cc_consequence_setup_required:
        "\u4F7F\u7528\u524D\u9700\u8981\u5B8C\u6210\u914D\u7F6E\u3002",
      cc_consequence_action_required:
        "\u6709\u4E00\u9879\u95EE\u9898\u9700\u8981\u5904\u7406\u3002",
      cc_consequence_installation_ready:
        "PaperForge \u5DF2\u5728\u6B64\u8BBE\u5907\u4E0A\u5C31\u7EEA\u3002",
      cc_consequence_library_ready:
        "Zotero \u6587\u732E\u5E93\u5DF2\u8FDE\u63A5\u5E76\u4FDD\u6301\u6700\u65B0\u3002",
      cc_consequence_ocr_ready:
        "OCR \u5DF2\u51C6\u5907\u597D\u5904\u7406\u8BBA\u6587\u3002",
      cc_consequence_memory_ready:
        "\u8BBA\u6587\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u5E76\u53EF\u641C\u7D22\u3002",
      cc_consequence_agent_ready:
        "PaperForge Skills \u5DF2\u90E8\u7F72\u5230\u6240\u9009 Agent \u5E73\u53F0\u3002",
      cc_consequence_agent_not_enabled:
        "\u9700\u8981\u90E8\u7F72 PaperForge Skills \u65F6\u518D\u9009\u62E9 Agent \u5E73\u53F0\u3002",
      cc_consequence_ocr_not_enabled:
        "OCR \u4E3A\u53EF\u9009\u529F\u80FD\uFF0C\u5F53\u524D\u672A\u542F\u7528\u3002",
      cc_consequence_memory_not_enabled:
        "\u667A\u80FD\u68C0\u7D22\u4E3A\u53EF\u9009\u529F\u80FD\uFF0C\u5F53\u524D\u672A\u542F\u7528\u3002",
      md_foundation_overview: "\u8FD0\u884C\u73AF\u5883",
      md_foundation_ready:
        "PaperForge \u5DF2\u5B89\u88C5\u5E76\u901A\u8FC7\u9A8C\u8BC1\uFF0C\u53EF\u4EE5\u6B63\u5E38\u4F7F\u7528\u3002",
      md_library_connection: "Zotero \u8FDE\u63A5",
      ocr_error_notice:
        "OCR \u56E0\u9519\u8BEF\u505C\u6B62\uFF0C\u8BF7\u6253\u5F00\u9AD8\u7EA7\u8BCA\u65AD\u67E5\u770B\u8BE6\u60C5\u3002",
      ocr_run_complete: "OCR \u5904\u7406\u5B8C\u6210\u3002",
      ocr_rebuild_complete: "OCR \u91CD\u5EFA\u5B8C\u6210\u3002",
      ocr_redo_complete: "OCR \u91CD\u505A\u5B8C\u6210\u3002",
      ocr_stopped_notice: "OCR \u6279\u5904\u7406\u5DF2\u505C\u6B62\u3002",
      ocr_failed_notice:
        "OCR \u672A\u5B8C\u6210\uFF0C\u8BF7\u6253\u5F00\u9AD8\u7EA7\u8BCA\u65AD\u67E5\u770B\u8BE6\u60C5\u3002",
      md_library_ready:
        "Zotero \u5DF2\u8FDE\u63A5\uFF0C\u6587\u732E\u5E93\u5DF2\u540C\u6B65\u3002",
      md_library_corpus: "\u6587\u732E\u8BED\u6599\u5E93",
      md_library_last_sync: "\u4E0A\u6B21\u6210\u529F\u540C\u6B65",
      md_ocr_status: "OCR \u529F\u80FD",
      md_status_refresh_hint:
        "\u8BF7\u5148\u68C0\u6D4B\u72B6\u6001\u4EE5\u52A0\u8F7D\u5F53\u524D OCR \u4FE1\u606F\uFF1B\u6B64\u64CD\u4F5C\u4E0D\u4F1A\u4FEE\u6539\u8BBA\u6587\u3002",
      md_ocr_ready: "OCR \u5DF2\u914D\u7F6E\u5E76\u53EF\u7528\u3002",
      md_ocr_workspace: "\u6253\u5F00 OCR \u5DE5\u4F5C\u533A",
      md_retrieval_coverage: "\u68C0\u7D22\u8986\u76D6\u8303\u56F4",
      md_retrieval_ready:
        "\u6240\u6709\u53EF\u7528\u8BBA\u6587\u5747\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u5E76\u53EF\u641C\u7D22\u3002",
      md_agent_integration: "Agent \u96C6\u6210",
      md_agent_placeholder:
        "\u914D\u7F6E\u76EE\u6807\u5E73\u53F0\u3001\u90E8\u7F72 PaperForge \u6587\u4EF6\u5E76\u7BA1\u7406 Skills\u3002\u6587\u4EF6\u5DF2\u90E8\u7F72\u4E0D\u4EE3\u8868\u5B9E\u65F6\u8FDE\u63A5\u5DF2\u7ECF\u9A8C\u8BC1\u3002",
      md_agent_platform: "\u76EE\u6807\u5E73\u53F0",
      md_agent_deployment: "\u90E8\u7F72\u72B6\u6001",
      agent_deployed: "\u6587\u4EF6\u5DF2\u90E8\u7F72",
      agent_not_deployed: "\u6587\u4EF6\u672A\u90E8\u7F72",
      agent_live_connection: "\u5B9E\u65F6\u8FDE\u63A5",
      agent_verify_found:
        "\u5DF2\u627E\u5230\u6B64\u5E73\u53F0\u7684 PaperForge Skills\u3002",
      agent_verify_missing:
        "\u672A\u627E\u5230\u6B64\u5E73\u53F0\u7684 PaperForge Skills\uFF0C\u8BF7\u8FD0\u884C\u8BBE\u7F6E\u8FDB\u884C\u90E8\u7F72\u3002",
      skills_system: "\u7CFB\u7EDF Skills",
      skills_user: "\u7528\u6237 Skills",
      skills_empty:
        "\u6240\u9009\u5E73\u53F0\u5C1A\u672A\u90E8\u7F72 Skills\u3002",
      md_agent_connection_unknown:
        "\u5B9E\u65F6\u8FDE\u63A5\u5C1A\u672A\u9A8C\u8BC1",
      md_agent_skills: "PaperForge Skills",
      md_copy_diagnostic: "\u590D\u5236\u652F\u6301\u8BCA\u65AD",
      md_configuration: "\u914D\u7F6E",
      md_current_activity: "\u5F53\u524D\u6D3B\u52A8",
      config_change: "\u66F4\u6539",
      config_save: "\u4FDD\u5B58",
      config_cancel: "\u53D6\u6D88",
      config_verify: "\u9A8C\u8BC1",
      config_configured: "\u5DF2\u914D\u7F6E",
      config_not_configured: "\u672A\u914D\u7F6E",
      config_zotero_dir: "Zotero \u6570\u636E\u76EE\u5F55",
      problem_what_happened: "\u53D1\u751F\u4E86\u4EC0\u4E48",
      problem_impact: "\u5F71\u54CD\uFF1A",
      problem_next: "\u4E0B\u4E00\u6B65\uFF1A",
      problem_copy: "\u590D\u5236\u8BCA\u65AD\u4FE1\u606F",
      problem_use_action:
        "\u4F7F\u7528\u4E0A\u65B9\u64CD\u4F5C\u5904\u7406\u6B64\u95EE\u9898\u3002",
      library_problem_impact:
        "\u65B0\u7684\u53C2\u8003\u6587\u732E\u548C\u6587\u732E\u7B14\u8BB0\u53EF\u80FD\u6682\u4E0D\u53EF\u7528\u3002",
      ocr_problem_impact:
        "\u90E8\u5206\u8BBA\u6587\u53EF\u80FD\u6CA1\u6709\u53EF\u9605\u8BFB\u7684\u5168\u6587\u3002",
      retrieval_problem_impact:
        "\u6062\u590D\u8986\u76D6\u524D\uFF0C\u641C\u7D22\u548C\u68C0\u7D22\u53EF\u80FD\u9057\u6F0F\u8BBA\u6587\u3002",
      metric_after_sync:
        "\u4E0B\u6B21\u6210\u529F\u540C\u6B65\u540E\u53EF\u7528",
      metric_not_available: "\u6682\u4E0D\u53EF\u7528",
      coverage_complete: "\u5B8C\u6574",
      retrieval_freshness: "\u4E0A\u6B21\u68C0\u67E5",
      md_module_switcher: "\u6A21\u5757",
      advanced_diagnostics: "\u9AD8\u7EA7\u8BCA\u65AD",
      foundation_version: "PaperForge \u7248\u672C",
      foundation_last_verified: "\u4E0A\u6B21\u9A8C\u8BC1",
      foundation_runtime_managed: "\u6258\u7BA1\u8FD0\u884C\u73AF\u5883",
      foundation_runtime_system: "\u7CFB\u7EDF\u8FD0\u884C\u73AF\u5883",
      foundation_runtime_unavailable:
        "\u8FD0\u884C\u73AF\u5883\u4E0D\u53EF\u7528",
      foundation_skills_ready: "\u53EF\u7528",
      foundation_skills: "Skills",
      md_foundation_legacy_migrate: "\u8FC1\u79FB\u65E7\u7248\u914D\u7F6E",
      foundation_setup_desc:
        "\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\uFF0C\u521B\u5EFA\u7531 Python \u7BA1\u7406\u7684\u5E93\u914D\u7F6E\u5E76\u53D1\u5E03\u8FD0\u884C\u73AF\u5883\u6307\u9488\u3002",
      foundation_setup_btn: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      config_confirm: "\u786E\u8BA4",
      ocr_configure_credential: "\u914D\u7F6E OCR \u51ED\u636E",
      feat_install_deps_desc:
        "\u5B89\u88C5\u667A\u80FD\u68C0\u7D22\u6240\u9700\u7684\u4F9D\u8D56\u9879\u3002",
      setup_welcome: "\u8BBE\u7F6E PaperForge",
      setup_desc:
        "\u5B8C\u6210\u5FC5\u9700\u9636\u6BB5\uFF0C\u7136\u540E\u9009\u62E9\u9700\u8981\u542F\u7528\u7684\u53EF\u9009\u529F\u80FD\u3002",
      setup_stage_1: "\u57FA\u7840\u73AF\u5883",
      setup_stage_2: "\u8FDE\u63A5\u6587\u732E\u5E93",
      setup_stage_3: "\u53EF\u9009\u529F\u80FD",
      setup_stage_4: "\u68C0\u67E5\u5E76\u5F00\u59CB",
      setup_progress: "\u8BBE\u7F6E\u8FDB\u5EA6",
      setup_foundation_title: "\u7B2C 1 \u6B65\uFF1A\u57FA\u7840\u73AF\u5883",
      setup_foundation_desc:
        "\u9009\u62E9 Python \u8FD0\u884C\u73AF\u5883\uFF0C\u7136\u540E\u5B89\u88C5 PaperForge \u5305\uFF1B\u6B64\u6B65\u9AA4\u4E0D\u4F1A\u521B\u5EFA\u6216\u914D\u7F6E\u6587\u732E\u5E93\u3002",
      setup_ready: "\u57FA\u7840\u73AF\u5883\u5DF2\u5C31\u7EEA\u3002",
      setup_foundation_python: "Python \u53EF\u6267\u884C\u6587\u4EF6",
      setup_foundation_python_hint:
        "\u7559\u7A7A\u65F6\u4F7F\u7528\u7CFB\u7EDF PATH \u4E2D\u7684 \u201Cpython\u201D\u3002",
      setup_foundation_install_btn: "\u5B89\u88C5 PaperForge",
      setup_library_title:
        "\u7B2C 2 \u6B65\uFF1A\u8FDE\u63A5\u6587\u732E\u5E93",
      setup_library_desc:
        "\u8FDE\u63A5 Zotero\uFF0C\u8BA9 PaperForge \u53EF\u4EE5\u540C\u6B65\u6587\u732E\u3002",
      setup_library_ready: "\u6587\u732E\u5E93\u5DF2\u8FDE\u63A5\u3002",
      setup_library_config_desc:
        "\u9A8C\u8BC1 Zotero \u6570\u636E\u76EE\u5F55\uFF0C\u7136\u540E\u786E\u8BA4 PaperForge \u5728\u6B64\u5E93\u4E2D\u4F7F\u7528\u7684\u6587\u4EF6\u5939\u3002",
      setup_library_zotero_hint:
        "PaperForge \u53EA\u8BFB\u53D6\u6B64\u6587\u4EF6\u5939\uFF0C\u4E0D\u4F1A\u4FEE\u6539 Zotero \u6570\u636E\u5E93\u3002",
      setup_library_folder_heading: "\u5E93\u5185\u6587\u4EF6\u5939",
      setup_library_verify: "\u4FDD\u5B58\u5E76\u9A8C\u8BC1\u914D\u7F6E",
      setup_library_configured:
        "\u6587\u732E\u5E93\u914D\u7F6E\u5DF2\u4FDD\u5B58\uFF0C\u6B63\u5728\u68C0\u67E5\u8FDE\u63A5\u3002",
      setup_library_configuring:
        "\u6B63\u5728\u4FDD\u5B58\u5E76\u68C0\u67E5\u6587\u732E\u5E93\u914D\u7F6E\u2026",
      setup_library_config_failed:
        "\u6587\u732E\u5E93\u914D\u7F6E\u65E0\u6CD5\u9A8C\u8BC1\u3002\u8BF7\u68C0\u67E5\u8DEF\u5F84\u540E\u91CD\u8BD5\u3002",
      setup_reinstall_notice:
        "\u53EA\u91CD\u65B0\u5B89\u88C5\u672C\u673A\u7684 PaperForge Python \u5305\uFF0C\u4E0D\u4F1A\u6539\u52A8\u6587\u732E\u5E93\u914D\u7F6E\u3002",
      setup_installing:
        "\u6B63\u5728\u5B89\u88C5\u5E76\u51C6\u5907 PaperForge\u2026",
      setup_install_complete:
        "\u5B89\u88C5\u5B8C\u6210\uFF0C\u6B63\u5728\u68C0\u67E5\u66F4\u65B0\u540E\u7684\u8FD0\u884C\u73AF\u5883\u3002",
      setup_install_failed:
        "PaperForge \u5B89\u88C5\u672A\u5B8C\u6210\u3002\u8BF7\u68C0\u67E5 Python \u8DEF\u5F84\u540E\u91CD\u8BD5\u3002",
      setup_optionals_title: "\u7B2C 3 \u6B65\uFF1A\u53EF\u9009\u529F\u80FD",
      setup_optionals_desc:
        "\u53EA\u9009\u62E9\u9700\u8981\u7684\u529F\u80FD\uFF1B\u8DF3\u8FC7\u540E\u4ECD\u53EF\u968F\u65F6\u542F\u7528\u3002",
      setup_optional_saved: "\u914D\u7F6E\u5DF2\u5B89\u5168\u4FDD\u5B58\u3002",
      setup_optional_save_failed:
        "\u914D\u7F6E\u65E0\u6CD5\u4FDD\u5B58\u3002\u8BF7\u68C0\u67E5 Obsidian \u5B89\u5168\u5B58\u50A8\u540E\u91CD\u8BD5\u3002",
      setup_opt_ocr_desc:
        "\u4ECE PDF \u63D0\u53D6\u6587\u672C\u548C\u56FE\u8868",
      setup_opt_memory_desc: "\u8DE8\u8BBA\u6587\u641C\u7D22\u548C\u6D4F\u89C8",
      setup_opt_agent_desc: "\u90E8\u7F72\u5E76\u7BA1\u7406 PaperForge Skills",
      setup_review_title: "\u7B2C 4 \u6B65\uFF1A\u68C0\u67E5\u5E76\u5F00\u59CB",
      setup_review_selected: "\u5DF2\u9009\u62E9\uFF1A",
      setup_no_optionals: "\u672A\u9009\u62E9\u53EF\u9009\u529F\u80FD\u3002",
      setup_incomplete_warn:
        "\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u5747\u5C31\u7EEA\u540E\u624D\u80FD\u5B8C\u6210\u8BBE\u7F6E\u3002",
      setup_review_checking:
        "\u6B63\u5728\u68C0\u67E5\u5F53\u524D\u914D\u7F6E\u2026",
      setup_review_recheck: "\u91CD\u65B0\u68C0\u67E5\u914D\u7F6E",
      setup_nav_continue: "\u7EE7\u7EED",
      setup_nav_skip: "\u6682\u65F6\u8DF3\u8FC7",
      setup_nav_back: "\u8FD4\u56DE",
      setup_nav_cancel: "\u53D6\u6D88",
      setup_nav_later: "\u7A0D\u540E",
      setup_install_cancelled:
        "\u8BBE\u7F6E\u5DF2\u53D6\u6D88\uFF0C\u8FD0\u884C\u65F6\u672A\u6FC0\u6D3B\u3002",
      setup_nav_complete: "\u5B8C\u6210\u8BBE\u7F6E",
      help_title: "\u5E2E\u52A9",
      help_lede:
        "\u6253\u5F00\u76F8\u5173\u6A21\u5757\uFF0C\u6216\u590D\u5236\u8BCA\u65AD\u4FE1\u606F\u5BFB\u6C42\u652F\u6301\u3002",
      help_intro:
        "\u9009\u62E9\u4E00\u4E2A\u4EFB\u52A1\uFF0C\u6216\u590D\u5236\u9690\u79C1\u5B89\u5168\u7684\u652F\u6301\u8BCA\u65AD\u3002",
      help_getting_started: "\u5F00\u59CB\u4F7F\u7528",
      help_library_task: "\u8FDE\u63A5 Zotero \u5E76\u540C\u6B65\u6587\u732E",
      help_ocr_task:
        "\u914D\u7F6E OCR \u5E76\u6253\u5F00 OCR \u5DE5\u4F5C\u533A",
      help_retrieval_task:
        "\u542F\u7528\u667A\u80FD\u68C0\u7D22\u5E76\u5EFA\u7ACB\u8986\u76D6",
      help_agent_task:
        "\u9009\u62E9 Agent \u5E73\u53F0\u5E76\u90E8\u7F72 Skills",
      help_current_problem: "\u5F53\u524D\u95EE\u9898\u6307\u5F15",
      help_no_problem:
        "\u5F53\u524D\u6CA1\u6709\u9700\u8981\u6307\u5F15\u7684\u95EE\u9898\u3002",
      help_support: "\u652F\u6301\u8BCA\u65AD",
      help_support_desc:
        "\u4EC5\u590D\u5236\u6A21\u5757\u72B6\u6001\u548C\u7248\u672C\u6807\u8BC6\uFF0C\u4E0D\u5305\u542B\u5BC6\u94A5\u3001\u5185\u5BB9\u3001\u8EAB\u4EFD\u3001\u7EDD\u5BF9\u8DEF\u5F84\u6216\u539F\u59CB\u65E5\u5FD7\u3002",
      help_copy: "\u590D\u5236\u652F\u6301\u8BCA\u65AD",
      help_documentation: "\u6587\u6863",
      help_documentation_desc:
        "\u6253\u5F00\u9879\u76EE\u6307\u5357\uFF0C\u67E5\u770B\u8BBE\u7F6E\u3001\u5DE5\u4F5C\u6D41\u7A0B\u548C\u6545\u969C\u6392\u9664\u8BF4\u660E\u3002",
      help_open_documentation: "\u6253\u5F00 PaperForge \u6587\u6863",
      help_release_notes: "\u7248\u672C\u8BF4\u660E",
      help_release_notes_desc:
        "\u5F53\u524D\u5B89\u88C5\u7248\u672C\uFF1A{version}\u3002\u5B8C\u6574\u53D8\u66F4\u8BB0\u5F55\u8BF7\u67E5\u770B GitHub\u3002",
      help_open_release_notes: "\u6253\u5F00\u7248\u672C\u8BF4\u660E",
      support_diagnostic_copied:
        "\u652F\u6301\u8BCA\u65AD\u5DF2\u590D\u5236\u3002",
      maintenance_empty_title: "\u65E0\u9700\u7EF4\u62A4",
      maintenance_empty_body:
        "\u5F53\u524D\u6CA1\u6709\u9700\u8981\u5904\u7406\u7684\u672A\u89E3\u51B3\u95EE\u9898\u3002",
      maintenance_default_impact:
        "\u6B64\u529F\u80FD\u53EF\u80FD\u4E0D\u53EF\u7528\uFF0C\u6216\u8FD4\u56DE\u4E0D\u5B8C\u6574\u7684\u7ED3\u679C\u3002",
      maintenance_open_module: "\u6253\u5F00\u6A21\u5757",
      migration_banner_title: "\u51ED\u636E\u8FC1\u79FB\u901A\u77E5",
      cc_summary_attention: "\u90E8\u5206\u6A21\u5757\u9700\u8981\u5173\u6CE8",
      help_load_error:
        "\u65E0\u6CD5\u52A0\u8F7D\u5E2E\u52A9\u5185\u5BB9\u3002\u8BF7\u68C0\u67E5\u7F51\u7EDC\u8FDE\u63A5\u3002",
      cc_summary_ok_body:
        "PaperForge \u73AF\u5883\u5DF2\u5B8C\u5168\u5C31\u7EEA\u3002\u5B89\u88C5\u548C\u5E2E\u52A9\u6587\u6863\u5747\u6B63\u5E38\u53EF\u7528\u3002",
      cc_summary_core_ok_body:
        "\u5B89\u88C5\u548C\u5E2E\u52A9\u6A21\u5757\u5DF2\u53EF\u7528\u3002\u6587\u732E\u7D22\u5F15\u3001OCR\u3001\u8BB0\u5FC6\u5C42\u548C\u7EF4\u62A4\u6A21\u5757\u5C06\u5728\u540E\u7AEF\u63A5\u5165\u540E\u663E\u793A\u5B9E\u65F6\u72B6\u6001\u3002",
      cc_summary_attention_body:
        "\u4E00\u4E2A\u6216\u591A\u4E2A\u6838\u5FC3\u6A21\u5757\u9700\u8981\u60A8\u7684\u5173\u6CE8\u624D\u80FD\u6B63\u5E38\u8FD0\u884C\u3002",
      retrieval_build_stopped:
        "\u6784\u5EFA\u5DF2\u505C\u6B62\uFF08{n}/{t} \u7BC7\uFF09",
      retrieval_build_failed: "\u6784\u5EFA\u5931\u8D25",
      retrieval_build_stale:
        "\u5411\u91CF\u5DF2\u8FC7\u671F \u2014 \u5EFA\u8BAE\u91CD\u5EFA",
      retrieval_build_runtime_mismatch:
        "Python \u8FD0\u884C\u65F6\u7248\u672C\u4E0D\u5339\u914D\u3002",
      retrieval_stop: "\u505C\u6B62",
      retrieval_no_python: "\u672A\u627E\u5230 Python",
      retrieval_internal_error: "\u53D1\u751F\u5185\u90E8\u9519\u8BEF",
      retrieval_force_rebuild: "\u5F3A\u5236\u91CD\u5EFA",
      retrieval_rebuild_warning:
        "\u91CD\u5EFA\u5C06\u66FF\u6362 {n} \u4E2A\u73B0\u6709\u6587\u672C\u5757\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F",
      foundation_git: "Git",
      foundation_git_missing:
        "\u672A\u5B89\u88C5 \u2014 \u8BF7\u5B89\u88C5 Git \u7528\u4E8E\u7248\u672C\u63A7\u5236",
      foundation_obsidian: "Obsidian \u7248\u672C",
      foundation_obsidian_old:
        "\u7248\u672C\u8FC7\u65E7 \u2014 \u8BF7\u66F4\u65B0 Obsidian",
      foundation_python_packages: "Python \u5305",
      foundation_python_packages_checking:
        "\u6B63\u5728\u68C0\u67E5\u5DF2\u5B89\u88C5\u7684\u5305...",
      foundation_paddle_key: "PaddleOCR API \u5BC6\u94A5",
      foundation_paddle_missing:
        "\u672A\u914D\u7F6E \u2014 OCR \u63D0\u53D6\u9700\u8981\u6B64\u5BC6\u94A5",
      foundation_openai_key: "OpenAI API \u5BC6\u94A5",
      foundation_openai_missing:
        "\u672A\u914D\u7F6E \u2014 \u667A\u80FD\u68C0\u7D22\u9700\u8981\u6B64\u5BC6\u94A5",
      foundation_python: "Python \u8DEF\u5F84",
      foundation_python_status: "Python \u72B6\u6001",
      foundation_python_ok: "Python \u5DF2\u5B89\u88C5",
      foundation_python_missing:
        "\u672A\u627E\u5230 Python \u2014 \u8BF7\u5B89\u88C5 Python 3.11+",
      foundation_vault_structure: "\u5E93\u5185\u6587\u4EF6\u5939",
      foundation_zotero: "Zotero \u6570\u636E\u76EE\u5F55",
      foundation_zotero_missing:
        "\u672A\u914D\u7F6E \u2014 \u8BF7\u8FDE\u63A5 Zotero \u6570\u636E\u76EE\u5F55",
      foundation_reinstall: "\u91CD\u65B0\u5B89\u88C5 PaperForge",
      foundation_reinstall_desc:
        "\u4ECE\u672C\u5730\u6E90\u7801\u91CD\u65B0\u5B89\u88C5 Python \u5305",
      foundation_reinstall_btn: "\u91CD\u65B0\u5B89\u88C5",
      foundation_reinstalling:
        "\u6B63\u5728\u91CD\u65B0\u5B89\u88C5 PaperForge...",
      foundation_reinstall_ok:
        "PaperForge \u91CD\u65B0\u5B89\u88C5\u6210\u529F",
      foundation_reinstall_failed: "\u91CD\u65B0\u5B89\u88C5\u5931\u8D25",
      cc_summary_ok: "\u5168\u90E8\u6B63\u5E38",
      cc_summary_core_ok:
        "\u6838\u5FC3\u73AF\u5883\u6B63\u5E38\uFF1B{n} \u4E2A\u6A21\u5757\u72B6\u6001\u68C0\u6D4B\u5F85\u63A5\u5165",
      cc_badge_ok: "\u5DF2\u5C31\u7EEA",
      cc_badge_pending: "\u5F85\u63A5\u5165",
      migration_banner_body:
        "{modules} \u7684\u51ED\u636E\u65E0\u6CD5\u81EA\u52A8\u8FC1\u79FB\u5230\u5B89\u5168\u5B58\u50A8\uFF0C\u8BF7\u5728\u6240\u5C5E\u6A21\u5757\u4E2D\u91CD\u65B0\u8F93\u5165\u3002",
      migration_banner_next:
        "\u4FDD\u5B58\u65B0\u503C\u540E\uFF0CPaperForge \u5C06\u5728\u91CD\u542F\u65F6\u518D\u6B21\u5C1D\u8BD5\u5B89\u5168\u8FC1\u79FB\u3002",
      cc_badge_setup: "\u9700\u8981\u5B89\u88C5",
      cc_badge_attention: "\u9700\u8981\u6CE8\u610F",
      cc_diagnostic_toggle: "\u8BE6\u60C5",
      cc_n_ready: "{n} \u5DF2\u5C31\u7EEA",
      cc_n_pending: "{n} \u5F85\u63A5\u5165",
      cc_desc:
        "PaperForge \u6838\u5FC3\u6A21\u5757\u7684\u5B9E\u65F6\u72B6\u6001\u3002\u6709\u5F85\u5904\u7406\u64CD\u4F5C\u7684\u6A21\u5757\u9700\u8981\u60A8\u7684\u5173\u6CE8\u3002",
      cc_zone_attention: "\u9700\u8981\u5173\u6CE8",
      cc_zone_modules: "\u6240\u6709\u6A21\u5757",
      cc_module_installation: "\u5B89\u88C5",
      cc_module_help: "\u5E2E\u52A9\u4E0E\u6587\u6863",
      cc_module_library: "\u6587\u732E\u5E93",
      cc_module_ocr: "OCR \u5F15\u64CE",
      cc_module_memory: "\u667A\u80FD\u68C0\u7D22",
      cc_module_maintenance: "\u7EF4\u62A4",
      cc_state_ready: "\u5C31\u7EEA",
      cc_state_limited: "\u53D7\u9650",
      cc_state_unavailable: "\u4E0D\u53EF\u7528",
      cc_state_unknown: "\u672A\u77E5",
      cc_severity_ok: "\u6B63\u5E38",
      cc_severity_unknown: "\u672A\u77E5",
      cc_severity_warning: "\u8B66\u544A",
      cc_severity_error: "\u9519\u8BEF",
      cc_state_missing_input: "\u7F3A\u5C11\u8F93\u5165",
      cc_state_needs_action: "\u9700\u8981\u64CD\u4F5C",
      cc_action_setup: "\u6253\u5F00\u5B89\u88C5\u5411\u5BFC",
      cc_action_probe: "\u68C0\u6D4B",
      cc_action_set_config: "\u914D\u7F6E\u8BBE\u7F6E",
      action_ocr_run: "\u8FD0\u884C OCR",
      action_ocr_rebuild_derived: "\u91CD\u5EFA OCR \u7ED3\u679C",
      action_memory_build: "\u6784\u5EFA\u6587\u672C\u7D22\u5F15",
      action_embed_build: "\u6784\u5EFA\u5411\u91CF\u7D22\u5F15",
      action_embed_resume: "\u7EE7\u7EED\u5411\u91CF\u6784\u5EFA",
      action_foundation_update: "\u66F4\u65B0 PaperForge",
      action_foundation_repair: "\u4FEE\u590D\u8FD0\u884C\u73AF\u5883",
      setup_bbt_title: "\u5BFC\u5165 BBT JSON",
      setup_bbt_desc:
        "\u4ECE Zotero \u4E2D\u5BFC\u51FA Better BibTeX JSON\uFF08\u6587\u4EF6 \u2192 \u5BFC\u51FA\u6587\u732E\u5E93 \u2192 Better BibTeX JSON\uFF09\uFF0C\u7136\u540E\u5C06\u6587\u4EF6\u62D6\u5165\u4E0B\u65B9\u6216\u70B9\u51FB\u9009\u62E9\u3002",
      setup_bbt_path: "\u5BFC\u51FA\u6587\u4EF6\u5939\uFF1A",
      setup_bbt_drop:
        "\u5C06 BBT JSON \u6587\u4EF6\u62D6\u5230\u6B64\u5904\uFF0C\u6216\u70B9\u51FB\u9009\u62E9",
      setup_bbt_no_files: "\u5C1A\u672A\u5BFC\u5165 JSON \u6587\u4EF6\u3002",
      setup_bbt_invalid: "\u65E0\u6548\u7684 JSON \u6587\u4EF6\uFF1A",
      setup_bbt_guide: "\u5982\u4F55\u4ECE Zotero \u5BFC\u51FA",
      setup_bbt_step1: "1. \u5B89\u88C5 Better BibTeX",
      setup_bbt_step2:
        "2. \u5BFC\u51FA\u5E76\u5F00\u542F\u81EA\u52A8\u66F4\u65B0",
      setup_bbt_step1_desc:
        "\u5728 Zotero \u4E2D\u6253\u5F00 \u5DE5\u5177 \u2192 \u63D2\u4EF6\uFF0C\u641C\u7D22 Better BibTeX \u5E76\u5B89\u88C5\u3002\u5982\u679C\u641C\u7D22\u4E0D\u5230\uFF0C\u8BF7\u4ECE\u4EE5\u4E0B\u5730\u5740\u4E0B\u8F7D\uFF1Ahttps://github.com/retorquere/zotero-better-bibtex/releases/tag/v9.0.50",
      setup_bbt_step2_desc:
        "\u53F3\u952E\u6587\u732E\u5E93\u6216\u5206\u7C7B \u2192 \u5BFC\u51FA\u6587\u732E\u5E93\u2026 \u2192 \u9009\u62E9\u300CBetter BibTeX JSON\u300D\u683C\u5F0F\u3002\u52FE\u9009\u300CKeep updated\u300D\uFF0C\u4EE5\u540E Zotero \u6709\u53D8\u5316\u65F6\u4F1A\u81EA\u52A8\u91CD\u65B0\u5BFC\u51FA\u3002",
      setup_bbt_step3: "3. \u4FDD\u5B58\u5230\u5BFC\u51FA\u6587\u4EF6\u5939",
      setup_bbt_step3_desc:
        "\u5C06\u5BFC\u51FA\u76EE\u6807\u6307\u5411\u4E0A\u65B9\u663E\u793A\u7684\u6587\u4EF6\u5939\u3002\u4FDD\u5B58\u540E\u70B9\u51FB\u300C\u68C0\u6D4B\u300D\u3002",
      setup_bbt_copy: "\u590D\u5236",
      setup_bbt_copied: "\u8DEF\u5F84\u5DF2\u590D\u5236",
      setup_bbt_detect: "\u68C0\u6D4B",
      setup_bbt_found: "\u5DF2\u627E\u5230\uFF1A",
      cc_reason_installation_ready:
        "PaperForge \u73AF\u5883\u5DF2\u6B63\u786E\u914D\u7F6E\u3002",
      cc_reason_config_missing:
        "\u914D\u7F6E\u6587\u4EF6\u7F3A\u5931\uFF0C\u8BF7\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\u3002",
      cc_reason_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0C\u8BF7\u8FD0\u884C\u5B89\u88C5\u5411\u5BFC\u4FEE\u590D\u3002",
      cc_reason_python_version_unsupported:
        "Python \u7248\u672C\u4E0D\u53D7\u652F\u6301\uFF0C\u8BF7\u5B89\u88C5 Python 3.11+\u3002",
      cc_reason_help_ready: "\u5E2E\u52A9\u6587\u6863\u5DF2\u53EF\u7528\u3002",
      cc_reason_docs_missing:
        "\u5E2E\u52A9\u6587\u6863\u5C1A\u672A\u5B89\u88C5\u3002",
      cc_reason_placeholder:
        "\u72B6\u6001\u68C0\u6D4B\u5F85\u63A5\u5165\uFF0C\u63A5\u5165\u540E\u5C06\u663E\u793A\u5B9E\u65F6\u72B6\u6001\u3002",
      cc_reason_library_ready:
        "\u6587\u732E\u5E93\u5DF2\u540C\u6B65\u5E76\u5EFA\u7ACB\u7D22\u5F15\u3002",
      cc_reason_library_config_missing:
        "\u672A\u627E\u5230\u914D\u7F6E\uFF0C\u8BF7\u5148\u8BBE\u7F6E\u6587\u732E\u5E93\u3002",
      cc_reason_library_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0C\u6587\u732E\u5E93\u65E0\u6CD5\u8FD0\u884C\u3002",
      cc_reason_library_zotero_missing:
        "\u5C1A\u672A\u914D\u7F6E Zotero \u6570\u636E\u76EE\u5F55\u3002",
      cc_reason_library_zotero_not_found:
        "Zotero \u6570\u636E\u76EE\u5F55\u4E0D\u5B58\u5728\u3002",
      cc_reason_library_index_missing:
        "\u5C1A\u672A\u5EFA\u7ACB\u6587\u732E\u7D22\u5F15\uFF0C\u8BF7\u5148\u540C\u6B65\u3002",
      cc_reason_library_index_stale:
        "\u6587\u732E\u7D22\u5F15\u5DF2\u8FC7\u671F\uFF0C\u8BF7\u540C\u6B65\u5237\u65B0\u3002",
      cc_reason_ocr_ready:
        "OCR \u5DF2\u914D\u7F6E\u5E76\u53EF\u6B63\u5E38\u8FD0\u884C\u3002",
      cc_reason_ocr_config_missing:
        "\u672A\u627E\u5230\u914D\u7F6E\uFF0C\u8BF7\u5148\u8BBE\u7F6E OCR\u3002",
      cc_reason_ocr_config_corrupt:
        "\u914D\u7F6E\u6587\u4EF6\u635F\u574F\uFF0COCR \u65E0\u6CD5\u8FD0\u884C\u3002",
      cc_reason_ocr_api_key_missing:
        "\u5C1A\u672A\u914D\u7F6E OCR API \u5BC6\u94A5\u3002",
      cc_reason_ocr_artifacts_missing:
        "\u5C1A\u65E0 OCR \u8F93\u51FA\uFF0C\u8BF7\u5148\u5904\u7406\u8BBA\u6587\u3002",
      cc_reason_memory_ready:
        "\u667A\u80FD\u68C0\u7D22\u72B6\u6001\u6B63\u5E38\u4E14\u5DF2\u5EFA\u7ACB\u7D22\u5F15\u3002",
      cc_reason_memory_db_missing:
        "\u5C1A\u672A\u5EFA\u7ACB\u68C0\u7D22\u7D22\u5F15\uFF0C\u8BF7\u5148\u6784\u5EFA\u4EE5\u542F\u7528\u641C\u7D22\u3002",
      cc_reason_memory_db_corrupt:
        "\u68C0\u7D22\u7D22\u5F15\u5DF2\u635F\u574F\uFF0C\u8BF7\u4ECE\u5907\u4EFD\u6062\u590D\u3002",
      cc_reason_memory_index_stale:
        "\u667A\u80FD\u68C0\u7D22\u9700\u8981\u91CD\u5EFA\u4EE5\u5339\u914D\u5F53\u524D\u6587\u732E\u5E93\u3002",
      cc_diag_module: "\u6A21\u5757",
      cc_diag_state: "\u72B6\u6001",
      cc_reason_library_sync_failed:
        "\u4E0A\u6B21\u6587\u732E\u5E93\u540C\u6B65\u5931\u8D25\uFF0C\u8BF7\u5728\u6570\u636E\u6E90\u53EF\u7528\u540E\u91CD\u8BD5\u3002",
      cc_diag_severity: "\u4E25\u91CD\u7A0B\u5EA6",
      cc_diag_activity: "\u6D3B\u52A8",
      cc_diag_reason: "\u539F\u56E0",
      cc_diag_ttl: "TTL",
      cc_diag_updated: "\u66F4\u65B0\u65F6\u95F4",
      cc_reason_no_probe: "{module} \u5C1A\u672A\u68C0\u6D4B\u3002",
      cc_reason_stale:
        "{module} \u7684\u68C0\u6D4B\u6570\u636E\u5DF2\u8FC7\u671F\u3002",
      cc_reason_invalid_response:
        "{module} \u7684\u68C0\u6D4B\u54CD\u5E94\u65E0\u6548\u3002",
      activity_syncing: "\u540C\u6B65\u4E2D...",
      activity_ocr_running: "\u6B63\u5728\u5904\u7406 OCR... {pct}%",
      activity_ocr_running_noprogress: "\u6B63\u5728\u5904\u7406 OCR...",
      cc_action_unknown_verb: "\u672A\u77E5\u540E\u7AEF\u64CD\u4F5C: {verb}",
      cc_action_investigate: "\u6B63\u5728\u8FD0\u884C\u8BCA\u65AD...",
      cc_reason_probing: "\u6B63\u5728\u68C0\u6D4B {module} \u72B6\u6001...",
      cc_notice_placeholder:
        "{module} \u6A21\u5757\u68C0\u6D4B\u529F\u80FD\u5C1A\u672A\u53EF\u7528\uFF0C\u5C06\u5728\u540E\u7EED\u7248\u672C\u4E2D\u6DFB\u52A0\u3002",
      cc_notice_refreshed: "\u6A21\u5757\u72B6\u6001\u5DF2\u5237\u65B0\u3002",
      cc_notice_refresh_failed:
        "\u6A21\u5757\u72B6\u6001\u5237\u65B0\u5931\u8D25\u3002",
      cc_activity_idle: "\u7A7A\u95F2",
      cc_activity_running: "\u8FD0\u884C\u4E2D",
      maintenance_inbox_title: "\u7EF4\u62A4\u6536\u4EF6\u7BB1",
      maintenance_checking:
        "\u6B63\u5728\u68C0\u6D4B\u7EF4\u62A4\u72B6\u6001\u2026",
      maintenance_all_clear:
        "\u6240\u6709\u6A21\u5757\u5DF2\u5C31\u7EEA \u2014 \u65E0\u9700\u7EF4\u62A4\u3002",
      maintenance_n_pending_inbox:
        "{n} \u4E2A\u6A21\u5757\u9700\u8981\u5173\u6CE8",
      maintenance_dismiss: "\u5FFD\u7565",
      maintenance_undismiss: "\u663E\u793A",
      maintenance_ocr_section: "OCR \u7EF4\u62A4",
      maintenance_action_result_success:
        "\u64CD\u4F5C\u5B8C\u6210 \u2014 \u6A21\u5757\u5DF2\u5C31\u7EEA\u3002",
      maintenance_action_result_failure:
        "\u64CD\u4F5C\u5931\u8D25 \u2014 \u6A21\u5757\u4ECD\u9700\u5173\u6CE8\u3002",
      maintenance_confirm_redo_title: "\u786E\u8BA4\u91CD\u65B0\u8FD0\u884C",
      maintenance_confirm_redo_body:
        "\u8FD9\u5C06\u5220\u9664\u5E76\u91CD\u65B0\u8FD0\u884C\u6240\u9009\u8BBA\u6587\u7684 OCR\u3002\u5DF2\u6709\u7684\u884D\u751F\u7ED3\u679C\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_confirm_restore_title: "\u786E\u8BA4\u6062\u590D",
      maintenance_confirm_restore_body:
        "\u8FD9\u5C06\u4ECE\u5907\u4EFD\u6062\u590D\u8BB0\u5FC6\u6570\u636E\u5E93\u3002\u5F53\u524D\u6570\u636E\u5C06\u88AB\u66FF\u6362\u3002",
      maintenance_confirm_ok: "\u7EE7\u7EED",
      maintenance_confirm_cancel: "\u53D6\u6D88",
      confirmation_default_effect:
        "\u6B64\u64CD\u4F5C\u5C06\u66F4\u6539 PaperForge \u6570\u636E\u3002",
      confirm_effect_label: "\u5F71\u54CD",
      ocr_already_running: "OCR \u6B63\u5728\u8FD0\u884C\u3002",
      ocr_activity_run: "\u6B63\u5728\u8FD0\u884C OCR\u2026",
      ocr_activity_rebuild:
        "\u6B63\u5728\u91CD\u5EFA OCR \u884D\u751F\u7ED3\u679C\u2026",
      ocr_activity_redo: "\u6B63\u5728\u91CD\u65B0\u6267\u884C OCR\u2026",
      ocr_run_confirm_title: "\u8FD0\u884C OCR",
      ocr_run_confirm_body:
        "\u5F85\u5904\u7406 PDF \u5C06\u53D1\u9001\u5230\u5DF2\u914D\u7F6E\u7684 OCR \u670D\u52A1\uFF0C\u53EF\u80FD\u4EA7\u751F\u8D39\u7528\u3002\u6BCF\u7BC7\u8BBA\u6587\u5904\u7406\u6210\u529F\u524D\uFF0C\u73B0\u6709 OCR \u7ED3\u679C\u4F1A\u4FDD\u7559\uFF1B\u8FD0\u884C\u53EF\u5B89\u5168\u505C\u6B62\u3002",
      embed_already_running:
        "\u5411\u91CF\u6784\u5EFA\u6B63\u5728\u8FDB\u884C\u3002",
      embed_activity_stopping:
        "\u6B63\u5728\u505C\u6B62\u5411\u91CF\u6784\u5EFA\u2026",
      embed_activity_building:
        "\u6B63\u5728\u6784\u5EFA\u5411\u91CF\u7D22\u5F15\u2026",
      embed_rebuild_title: "\u91CD\u5EFA\u5411\u91CF\u7D22\u5F15",
      embed_rebuild_body:
        "\u8C03\u7528\u5D4C\u5165 API \u53EF\u80FD\u4EA7\u751F\u8D39\u7528\u3002\u66FF\u6362\u7D22\u5F15\u9A8C\u8BC1\u5B8C\u6210\u524D\uFF0C\u73B0\u6709\u5411\u91CF\u4ECD\u53EF\u7528\uFF1BPDF\u3001\u7B14\u8BB0\u548C OCR \u5747\u4F1A\u4FDD\u7559\u3002\u6784\u5EFA\u53EF\u5B89\u5168\u505C\u6B62\u3002",
      embed_build_complete:
        "\u5411\u91CF\u7D22\u5F15\u6784\u5EFA\u5B8C\u6210\u3002",
      embed_build_warning:
        "\u5411\u91CF\u7D22\u5F15\u5DF2\u53D1\u5E03\uFF0C\u4F46\u5B58\u5728\u8B66\u544A\uFF1A{detail}",
      embed_bookkeeping_incomplete:
        "\u6536\u5C3E\u8BB0\u5F55\u672A\u5B8C\u6210",
      embed_build_stopped:
        "\u6784\u5EFA\u5DF2\u505C\u6B62\u3002\u518D\u6B21\u8FD0\u884C\u5373\u53EF\u7EE7\u7EED\u3002",
      next_action_pending:
        "\u5411\u91CF\u5D4C\u5165\u5DF2\u5C31\u7EEA\u3002\u8BF7\u6253\u5F00\u201C\u667A\u80FD\u68C0\u7D22\u201D\u67E5\u770B\u5E76\u8FD0\u884C\u3002",
      next_action_runtime_unavailable:
        "PaperForge \u8FD0\u884C\u73AF\u5883\u4E0D\u53EF\u7528\uFF1B\u540E\u7EED\u64CD\u4F5C\u672A\u542F\u52A8\u3002",
      next_action_failed: "\u540E\u7EED\u64CD\u4F5C\u5931\u8D25\uFF1A{detail}",
      maintenance_issue_draft_title: "OCR \u95EE\u9898\u8349\u7A3F",
      maintenance_issue_draft_preview:
        "\u5728\u6253\u5F00 GitHub \u4E4B\u524D\uFF0C\u8BF7\u5BA1\u9605\u4EE5\u4E0B\u95EE\u9898\u8349\u7A3F\u3002",
      maintenance_issue_draft_included: "\u5DF2\u5305\u542B",
      maintenance_issue_draft_redacted: "\u5DF2\u8131\u654F",
      maintenance_issue_draft_open_github: "\u6253\u5F00 GitHub Issue",
      maintenance_issue_draft_edit: "\u7F16\u8F91\u8349\u7A3F",
      ocr_state_ready:
        "\u5DF2\u5904\u7406 {count} \u7BC7\u8BBA\u6587\uFF0COCR \u7248\u672C {version}",
      ocr_state_ready_no_version:
        "\u5DF2\u5904\u7406 {count} \u7BC7\u8BBA\u6587",
      ocr_state_update_available: "OCR v{version} \u53EF\u7528",
      ocr_state_update_description:
        "\u65B0\u7248\u6D41\u6C34\u7EBF\u6539\u8FDB\u4E86\u7ED3\u6784\u68C0\u6D4B\u3001\u56FE\u8868\u63D0\u53D6\u7CBE\u5EA6\u548C\u5168\u6587\u683C\u5F0F\u3002",
      ocr_state_update_safety:
        "\u60A8\u7684 PDF \u548C\u73B0\u6709 OCR \u6570\u636E\u4F1A\u5F97\u5230\u4FDD\u7559\u3002\u64CD\u4F5C\u524D\u4F1A\u81EA\u52A8\u521B\u5EFA\u5907\u4EFD\u3002",
      ocr_action_re_extract: "\u5168\u90E8\u91CD\u65B0\u63D0\u53D6",
      ocr_modal_title: "\u5168\u90E8\u91CD\u65B0 OCR",
      ocr_modal_description:
        "\u8FD9\u5C06\u4F7F\u7528\u6700\u65B0\u6D41\u6C34\u7EBF\u7248\u672C\u5BF9\u6240\u6709\u8BBA\u6587\u91CD\u65B0\u8FD0\u884C OCR\u3002",
      ocr_state_running: "\u6B63\u5728\u91CD\u65B0\u63D0\u53D6\u2026",
      sr_state_disabled: "\u667A\u80FD\u68C0\u7D22\u672A\u542F\u7528",
      sr_state_db_missing:
        "\u8BB0\u5FC6\u6570\u636E\u5E93\u5C1A\u672A\u6784\u5EFA",
      sr_state_upgrade_available:
        "\u5411\u91CF\u7D22\u5F15\u4F7F\u7528\u65E7\u7248 ChromaDB \u540E\u7AEF",
      sr_state_build_failed: "\u4E0A\u6B21\u5411\u91CF\u6784\u5EFA\u5931\u8D25",
      sr_state_build_interrupted:
        "\u5411\u91CF\u7D22\u5F15\u90E8\u5206\u6784\u5EFA\u4E2D\u2014\u2014\u7EE7\u7EED\u5D4C\u5165\u5269\u4F59\u8BBA\u6587",
      sr_state_identity_changed:
        "\u5D4C\u5165\u914D\u7F6E\u5DF2\u53D8\u5316\u2014\u2014\u73B0\u6709\u5411\u91CF\u9700\u91CD\u5EFA",
      sr_build_failed_notice:
        "\u5411\u91CF\u7D22\u5F15\u6784\u5EFA\u5931\u8D25\uFF1A{detail}",
      sr_action_build: "\u6784\u5EFA\u7D22\u5F15",
      sr_action_rebuild: "\u91CD\u5EFA\u7D22\u5F15",
      sr_action_upgrade: "\u5347\u7EA7\u5230 vec0",
      sr_upgrade_modal_title: "\u5347\u7EA7\u5411\u91CF\u7D22\u5F15",
      sr_upgrade_modal_description:
        "\u8FD9\u5C06\u4F7F\u7528\u65B0\u7684 vec0 \u540E\u7AEF\u91CD\u5EFA\u6574\u4E2A\u5411\u91CF\u7D22\u5F15\u3002",
      sr_upgrade_modal_safety:
        "\u73B0\u6709 ChromaDB \u6570\u636E\u4F1A\u5F97\u5230\u4FDD\u7559\u3002\u6B64\u8FC7\u7A0B\u9700\u8981\u6709\u6548\u7684 API Key \u5E76\u53EF\u80FD\u4EA7\u751F API \u8D39\u7528\u3002",
      sr_api_key_notice:
        "API Key \u672A\u914D\u7F6E \u2014 \u641C\u7D22\u548C\u68C0\u7D22\u4E0D\u53EF\u7528",
      sr_db_status: "\u6570\u636E\u5E93",
      sr_backend: "\u540E\u7AEF",
      sr_api_key: "API Key",
      sr_db_exists: "\u5DF2\u6FC0\u6D3B",
      sr_db_missing: "\u672A\u6784\u5EFA",
      sr_db_building: "\u6784\u5EFA\u4E2D",
      sr_db_partial: "\u90E8\u5206\u6784\u5EFA",
      sr_db_failed: "\u6784\u5EFA\u5931\u8D25",
      sr_db_corrupt: "\u5DF2\u635F\u574F",
      sr_db_stale: "\u7D22\u5F15\u8FC7\u671F",
      sr_impact_db_missing:
        "\u667A\u80FD\u68C0\u7D22\u9700\u8981 OpenAI API Key \u548C\u5411\u91CF\u7D22\u5F15\u3002\u70B9\u51FB\u6784\u5EFA\u7D22\u5F15\u5F00\u59CB\u8BBE\u7F6E\u3002",
      sr_impact_upgrade:
        "\u65B0\u7684\u5411\u91CF\u540E\u7AEF\u53EF\u7528\u3002\u5347\u7EA7\u53EF\u63D0\u5347\u641C\u7D22\u8D28\u91CF\u3002",
      sr_impact_build_failed:
        "\u4E0A\u6B21\u6784\u5EFA\u5931\u8D25\u3002\u8BF7\u68C0\u67E5 API Key \u540E\u91CD\u8BD5\u3002",
      sr_impact_schema_stale:
        "\u5411\u91CF\u6A21\u5F0F\u5DF2\u8FC7\u671F\u3002\u8BF7\u91CD\u5EFA\u4EE5\u5339\u914D\u5F53\u524D\u6587\u732E\u5E93\u3002",
      sr_action_enable: "\u542F\u7528\u667A\u80FD\u68C0\u7D22",
      sr_configure_api_keys: "\u914D\u7F6E API Key...",
      sr_config_hint: "\u8BBE\u7F6E \u203A \u667A\u80FD\u68C0\u7D22",
      sr_configure_api_keys_hint:
        "\u8BF7\u5728 \u8BBE\u7F6E \u2192 PaperForge \u2192 Smart Retrieval \u4E2D\u914D\u7F6E API Key\u3002",
      sr_config_label: "\u914D\u7F6E",
      ocr_ws_title: "OCR \u5DE5\u4F5C\u533A",
      ocr_ws_filter_all: "\u5168\u90E8",
      ocr_ws_filter_unprocessed: "\u672A\u5904\u7406",
      ocr_ws_filter_review: "\u9700\u5BA1\u6838",
      ocr_ws_filter_processed: "\u5DF2\u5904\u7406",
      ocr_ws_col_title: "\u6807\u9898",
      ocr_ws_col_status: "\u72B6\u6001",
      ocr_ws_col_version: "\u7248\u672C",
      ocr_ws_col_lastrun: "\u6700\u540E\u8FD0\u884C",
      ocr_ws_btn_preview: "\u9884\u89C8",
      ocr_ws_btn_process_all:
        "\u5904\u7406\u6240\u6709\u672A\u5904\u7406 ({count})",
      ocr_ws_detail_view_fulltext: "\u67E5\u770B\u5168\u6587",
      ocr_ws_detail_restore_backup: "\u6062\u590D\u5907\u4EFD",
      ocr_ws_detail_re_extract: "\u91CD\u65B0\u63D0\u53D6\u6B64\u8BBA\u6587",
      ocr_ws_detail_run: "\u8FD0\u884C OCR",
      ocr_ws_re_extract_disabled_title:
        "\u91CD\u65B0\u63D0\u53D6\u4E0D\u53EF\u7528",
      ocr_ws_re_extract_disabled_body:
        "\u5355\u7BC7\u8BBA\u6587\u91CD\u65B0\u63D0\u53D6\u76EE\u524D\u4F1A\u5220\u9664\u6240\u6709OCR\u6570\u636E\u800C\u4E0D\u521B\u5EFA\u5907\u4EFD\u3002\u8BF7\u4F7F\u7528OCR\u8BBE\u7F6E\u4E2D\u7684\u2018\u91CD\u65B0\u63D0\u53D6\u6240\u6709\u8BBA\u6587\u2019\u2014\u2014\u8BE5\u8DEF\u5F84\u5177\u6709\u5185\u7F6E\u5907\u4EFD\u3002",
      ocr_ws_what_happens:
        "\u91CD\u65B0\u63D0\u53D6\u65F6\u4F1A\u53D1\u751F\u4EC0\u4E48\uFF1F",
      ocr_ws_disclosure_text:
        "\u91CD\u65B0\u63D0\u53D6\u4F1A\u5BF9\u6240\u9009\u8BBA\u6587\u91CD\u65B0\u8FD0\u884COCR\u3002\u5F53\u524D\u7248\u672C\u4F1A\u5148\u5907\u4EFD\u3002PDF\u6C38\u8FDC\u4E0D\u4F1A\u88AB\u4FEE\u6539\u3002",
      ocr_ws_no_papers:
        "\u672A\u627E\u5230\u5177\u6709OCR\u6570\u636E\u7684\u8BBA\u6587",
      ocr_ws_lede:
        "\u67E5\u770B\u548C\u7BA1\u7406\u6587\u732E\u96C6\u5408\u7684 OCR \u63D0\u53D6\u3002",
      ocr_ws_processing: "\u5904\u7406\u4E2D\u2026",
      ocr_ws_stop: "\u505C\u6B62",
      ocr_ws_stop_unavailable_rebuild:
        "\u91CD\u5EFA\u64CD\u4F5C\u65E0\u6CD5\u5728\u6B64\u505C\u6B62",
      ocr_ws_btn_refresh: "\u5237\u65B0",
      ocr_ws_search_placeholder:
        "\u6309\u6807\u9898\u3001\u4F5C\u8005\u3001\u5E74\u4EFD\u641C\u7D22\u8BBA\u6587...",
      ocr_ws_showing:
        "\u5171 {total} \u7BC7\uFF0C\u663E\u793A <strong>{count}</strong> \u7BC7",
      ocr_ws_filter_status: "\u6309\u72B6\u6001\u7B5B\u9009",
      ocr_ws_none_selected: "\u672A\u9009\u62E9\u8BBA\u6587",
      ocr_ws_select_hint:
        "\u9009\u62E9\u672A\u5904\u7406\u6216\u6709\u66F4\u65B0\u53EF\u7528\u7684\u8BBA\u6587\u3002",
      ocr_ws_selected: "\u5DF2\u9009\u62E9 {count} \u7BC7",
      ocr_ws_btn_process_selected: "\u5904\u7406\u6240\u9009",
      ocr_ws_btn_rebuild_selected: "\u91CD\u5EFA\u6240\u9009",
      ocr_ws_restore_title: "\u6062\u590D\u5907\u4EFD\u7248\u672C",
      ocr_ws_restore_versions: "\u7248\u672C",
      ocr_ws_restore_compare: "\u5BF9\u6BD4\u5F53\u524D\u7248\u672C",
      ocr_ws_restore_diff_title: "\u5F53\u524D vs {v} \u7684\u53D8\u5316",
      ocr_ws_restore_no_diff: "\u65E0\u5DEE\u5F02",
      ocr_ws_restore_back: "\u8FD4\u56DE\u9884\u89C8",
      ocr_ws_restore_same: "\u8FD9\u5DF2\u7ECF\u662F\u5F53\u524D\u7248\u672C",
      ocr_ws_restore_desc:
        "\u9009\u62E9\u8981\u6062\u590D\u7684\u7248\u672C\u3002\u5F53\u524D\u7684\u5168\u6587\u5C06\u88AB\u66FF\u6362\u3002",
      ocr_ws_restore_current: "\u5F53\u524D",
      ocr_ws_restore_created: "\u521B\u5EFA\u65F6\u95F4\uFF1A",
      ocr_ws_restore_source: "\u6765\u6E90\uFF1A",
      ocr_ws_restore_renderer: "\u6E32\u67D3\u5668\uFF1A",
      ocr_ws_restore_btn: "\u6062\u590D",
      ocr_ws_tooltip_process:
        "\u4ECE\u5934\u6267\u884C\u5B8C\u6574 OCR\uFF1A\u63D0\u53D6\u6587\u5B57\u5E76\u91CD\u5EFA\u884D\u751F\u7ED3\u679C\u3002OCR \u6A21\u578B\u66F4\u65B0\u540E\u9700\u8981\u6267\u884C\uFF0C\u4F46\u4E00\u822C\u4E0D\u9700\u8981\u3002",
      ocr_ws_tooltip_rebuild:
        "\u57FA\u4E8E\u5DF2\u6709 OCR \u539F\u59CB\u6570\u636E\u91CD\u65B0\u751F\u6210\u6E32\u67D3\u7ED3\u679C\uFF0C\u4E0D\u91CD\u65B0\u8FD0\u884C OCR\u3002OCR \u6E32\u67D3\u7248\u672C\u66F4\u65B0\u540E\u9700\u8981\u6267\u884C\u3002",
      ocr_ws_tooltip_reextract:
        "\u4ECE\u5934\u91CD\u65B0 OCR \u6B64\u8BBA\u6587\uFF08\u5220\u9664\u5E76\u91CD\u65B0\u751F\u6210\u5168\u90E8 OCR \u6570\u636E\uFF09\u3002",
      ocr_ws_detail_restore_done: "\u5DF2\u6062\u590D\u5907\u4EFD {label}",
      next_action_memory_started:
        "\u5185\u5B58\u7D22\u5F15\u91CD\u5EFA\u5DF2\u542F\u52A8",
      next_action_done: "\u540E\u7EED\u52A8\u4F5C\u5DF2\u5B8C\u6210",
      next_action_refused: "\u540E\u7EED\u52A8\u4F5C\u5DF2\u88AB\u62D2\u7EDD",
      next_action_unknown:
        "\u672A\u77E5\u540E\u7EED\u52A8\u4F5C\u5DF2\u62D2\u7EDD",
      next_action_cancel: "\u7A0D\u540E",
      ocr_ws_fulltext_not_found: "\u672A\u627E\u5230\u5168\u6587",
      ocr_ws_restore_checking: "\u6B63\u5728\u68C0\u67E5\u7248\u672C\u2026",
      ocr_ws_restore_unavailable:
        "\u6CA1\u6709\u53EF\u7528\u7684\u5907\u4EFD\u7248\u672C",
      ocr_ws_detail_rebuild: "\u91CD\u5EFA\u6B64\u8BBA\u6587",
      ocr_ws_memory_refresh:
        "\u6B63\u5728\u66F4\u65B0\u672C\u5730\u6587\u672C\u7D22\u5F15\u2026",
      ocr_ws_memory_refresh_failed:
        "\u6587\u672C\u7D22\u5F15\u5237\u65B0\u5931\u8D25\uFF0C\u53EF\u7A0D\u540E\u91CD\u8BD5",
      ocr_ws_index_updated:
        "\u6B63\u6587\u7D22\u5F15\u5DF2\u66F4\u65B0\uFF0C\u8BED\u4E49\u7D22\u5F15\u9700\u8981\u5237\u65B0",
      ocr_ws_embed_confirm: "\u786E\u8BA4\u5411\u91CF\u5D4C\u5165",
      ocr_ws_embed_confirm_body:
        "\u4E3A\u53D8\u66F4\u8BBA\u6587\u91CD\u5EFA\u5411\u91CF\u53EF\u80FD\u8C03\u7528\u4ED8\u8D39 API\uFF0C\u662F\u5426\u7EE7\u7EED\uFF1F",
      ocr_ws_embed_done: "\u5411\u91CF\u5D4C\u5165\u5B8C\u6210",
      ocr_rebuild_partial:
        "\u91CD\u5EFA\u5B8C\u6210\u4F46\u5B58\u5728\u5931\u8D25",
      ocr_ws_restore_confirm_title:
        "\u6062\u590D\u5C55\u793A\u5168\u6587\u6587\u672C",
      ocr_ws_restore_confirm_body:
        "\u5C06\u7528\u6240\u9009\u7248\u672C\u7684 fulltext.md \u8986\u76D6 render/fulltext.md\u3002OCR \u7ED3\u6784\u3001\u7D22\u5F15\u3001\u8BB0\u5FC6\u4E0E\u5411\u91CF\u5747\u4E0D\u53D7\u5F71\u54CD\u3002\u7EE7\u7EED\uFF1F",
      ocr_ws_restore_confirm_btn: "\u6062\u590D\u5C55\u793A\u5168\u6587",
      ocr_ws_restore_stale_notice:
        "\u8BE5\u7248\u672C\u65E9\u4E8E\u5F53\u524D\u7ED3\u6784\u72B6\u6001\uFF1B\u5982\u9700\u7ED3\u6784\u4E00\u81F4\u8BF7\u91CD\u5EFA\u6B64\u8BBA\u6587",
      ocr_ws_close: "\u5173\u95ED",
      ocr_ws_fact_version: "OCR \u7248\u672C",
      ocr_ws_fact_last_run: "\u6700\u540E\u5904\u7406",
      ocr_ws_fact_authors: "\u4F5C\u8005",
      ocr_ws_fact_year: "\u5E74\u4EFD",
      ocr_ws_fact_pages: "\u9875\u6570",
      ocr_ws_fact_backups: "\u5907\u4EFD",
      ocr_ws_status_done: "\u5DF2\u5904\u7406",
      ocr_ws_status_update: "\u6709\u66F4\u65B0",
      ocr_ws_status_failed: "\u5931\u8D25",
      ocr_ws_status_processing: "\u5904\u7406\u4E2D",
      ocr_ws_status_nopdf: "\u65E0PDF",
      ocr_ws_status_pending: "\u5F85\u5904\u7406",
      ocr_ws_status_unknown: "\u672A\u77E5",
    },
  },
  Pt = null;
function Rt(d) {
  try {
    let i = d.vault;
    if (typeof i.getConfig == "function") {
      let e = i.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (i) {}
  try {
    if (typeof localStorage != "undefined") {
      let i = localStorage.getItem("language");
      if (i && String(i).startsWith("zh")) return "zh";
    }
  } catch (i) {}
  try {
    let i = document.documentElement.lang || navigator.language;
    if (i && i.startsWith("zh")) return "zh";
  } catch (i) {}
  return "en";
}
function dr(d, i = "") {
  Pt = (i || Rt(d)).startsWith("zh") ? Ct.zh : Ct.en;
}
function s(d) {
  return (Pt && Pt[d]) || Ct.en[d] || d;
}
var T = require("obsidian"),
  J = V(require("fs")),
  Re = V(require("path")),
  de = require("child_process");
var Dt = require("child_process");
var pt = V(require("fs")),
  se = V(require("path")),
  gr = V(require("os")),
  he = require("child_process");
At();
var Tt = null,
  fr = !1;
function Ot(d, i, e, t) {
  let r = e || pt,
    n = t || he.execFileSync;
  if (i && i.python_path && i.python_path.trim()) {
    let l = i.python_path.trim();
    if (r.existsSync(l)) return { path: l, source: "manual", extraArgs: [] };
  }
  let a = [
    se.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
    se.join(d, ".venv", "Scripts", "python.exe"),
    se.join(d, "venv", "Scripts", "python.exe"),
  ];
  for (let l of a)
    try {
      if (r.existsSync(l))
        return { path: l, source: "auto-detected", extraArgs: [] };
    } catch (c) {}
  let o = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let l of o)
    try {
      let c = n(l.path, [...l.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (c && c.toLowerCase().includes("python"))
        return {
          path: l.path,
          source: "auto-detected",
          extraArgs: l.extraArgs,
        };
    } catch (c) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function hr(d) {
  let i = String(d),
    t = {
      ENOENT: {
        type: "python_missing",
        message: "Python executable not found",
        recoverable: !0,
      },
      "python-missing": {
        type: "python_missing",
        message: "Python executable not found",
        recoverable: !0,
      },
      MODULE_NOT_FOUND: {
        type: "import_failed",
        message: "PaperForge package not installed",
        recoverable: !0,
      },
      "import-failed": {
        type: "import_failed",
        message: "PaperForge package not installed",
        recoverable: !0,
      },
      "version-mismatch": {
        type: "version_mismatch",
        message: "Plugin and package versions differ",
        recoverable: !0,
        action: "sync-runtime",
      },
      "pip-failed": {
        type: "pip_install_failure",
        message: "pip install command failed",
        recoverable: !0,
      },
      ETIMEDOUT: {
        type: "timeout",
        message: "Subprocess timed out",
        recoverable: !0,
        action: "retry",
      },
      timeout: {
        type: "timeout",
        message: "Subprocess timed out",
        recoverable: !0,
        action: "retry",
      },
      NO_PYTHON: {
        type: "no_python",
        message: "Python executable not found",
        recoverable: !0,
        action: "open-setup",
      },
      VECTOR_NOT_BUILT: {
        type: "vectors_not_built",
        message: "Vector index has not been built yet",
        recoverable: !0,
        action: "open-vector-settings",
      },
      VECTOR_CORRUPTED: {
        type: "vectors_corrupted",
        message: "Vector index is corrupted",
        recoverable: !0,
        action: "force-rebuild",
      },
      MODEL_CHANGED: {
        type: "model_changed",
        message: "Embedding model has changed since vectors were built",
        recoverable: !0,
        action: "rebuild-vectors",
      },
      BACKEND_UNAVAILABLE: {
        type: "backend_unavailable",
        message: "Python CLI search backend is not responding",
        recoverable: !0,
        action: "run-doctor",
      },
      TIMEOUT: {
        type: "timeout",
        message: "Search timed out",
        recoverable: !0,
        action: "retry",
      },
      INTERNAL_ERROR: {
        type: "internal_error",
        message: "An internal error occurred",
        recoverable: !1,
      },
    }[i];
  return t
    ? { ...t }
    : { type: "unknown", message: String(d), recoverable: !1 };
}
function mr(d, i, e, t, r, n) {
  let a = r || he.spawn;
  return new Promise((o) => {
    let l = Date.now(),
      c = { cwd: e, timeout: t, windowsHide: !0 };
    n && (c.env = n);
    let p = a(d, i, c),
      u = [],
      f = [];
    (p.stdout.on("data", (_) => {
      u.push(_.toString("utf-8"));
    }),
      p.stderr.on("data", (_) => {
        f.push(_.toString("utf-8"));
      }),
      p.on("close", (_) => {
        o({
          stdout: u.join(""),
          stderr: f.join(""),
          exitCode: _,
          elapsed: Date.now() - l,
        });
      }),
      p.on("error", (_) => {
        o({
          stdout: u.join(""),
          stderr:
            f.join("") +
            `
` +
            _.message,
          exitCode: -1,
          elapsed: Date.now() - l,
        });
      }));
  });
}
function yr() {
  if (fr) return Tt;
  fr = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let i = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, he.execFileSync)(i, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      d = (0, he.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (d) {
      let i = d
        .split(
          `
`
        )[0]
        .trim();
      i && (Tt = se.dirname(i));
    }
  } catch (d) {}
  return Tt;
}
function G() {
  let d = { ...process.env },
    i = process.platform,
    e = gr.homedir(),
    t = [],
    r = yr();
  (r && t.push(r),
    i === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : i === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let n = d.PATH || "";
  return ((d.PATH = [...t, n].filter(Boolean).join(se.delimiter)), Ft(d));
}
async function me(d, i) {
  return G();
}
var ye = class extends Error {
  constructor(i, e, t) {
    (super(t != null ? t : i), (this.configCode = i), (this.details = e));
  }
};
function be(d, i, e) {
  return new Promise((t, r) => {
    let n = Ot(d, e, require("fs"), require("child_process").execFileSync);
    if (!n) {
      r(new ye("config.python_unresolved", {}));
      return;
    }
    let a = [...n.extraArgs, "-m", "paperforge", "--vault", d, ...i, "--json"];
    (0, Dt.execFile)(
      n.path,
      a,
      { encoding: "utf-8", timeout: 6e4, windowsHide: !0 },
      (o, l) => {
        var c, p, u, f, _, h, g, m, v;
        try {
          let b = JSON.parse(l);
          if (b.ok && b.data !== null) {
            t(b.data);
            return;
          }
          let x =
            ((c = b.error) == null ? void 0 : c.message) ||
            ((p = b.error) == null ? void 0 : p.code) ||
            "config.error";
          r(
            new ye(
              x,
              (f = (u = b.error) == null ? void 0 : u.details) != null ? f : {},
              (h = (_ = b.error) == null ? void 0 : _.message) != null ? h : x
            )
          );
          return;
        } catch (b) {
          let x = (g = o == null ? void 0 : o.message) != null ? g : "";
          r(
            new ye(
              "config.invalid_response",
              {
                stdout:
                  (m = l == null ? void 0 : l.slice(0, 200)) != null ? m : "",
                stderr:
                  (v = x == null ? void 0 : x.slice(0, 200)) != null ? v : "",
              },
              `Invalid config response: ${String(b)}`
            )
          );
        }
      }
    );
  });
}
function Lt(d, i) {
  return be(d, ["config", "list"], i);
}
function Be(d, i, e, t) {
  return be(d, ["config", "set", i, String(e)], t);
}
function br(d, i) {
  return be(d, ["config", "validate"], i);
}
function Bt(d, i, e) {
  return be(
    d,
    i ? ["config", "migrate", "--dry-run"] : ["config", "migrate"],
    e
  );
}
function vr(d, i) {
  return be(d, ["auth", "status", "embedding", "--json"], i).then((e) => {
    var t, r;
    return (r = ((t = e.credentials) != null ? t : []).some(
      (n) => n.state === "available"
    )) != null
      ? r
      : !1;
  });
}
function xr(d, i) {
  return be(d, ["auth", "status", "ocr", "--json"], i).then((e) => {
    var t, r;
    return (r = ((t = e.credentials) != null ? t : []).some(
      (n) => n.state === "available"
    )) != null
      ? r
      : !1;
  });
}
function wr(d, i) {
  return new Promise((e, t) => {
    let r = Ot(d, i, require("fs"), require("child_process").execFileSync);
    if (!r) {
      t(new ye("config.python_unresolved", {}));
      return;
    }
    let n = [
      ...r.extraArgs,
      "-m",
      "paperforge",
      "--vault",
      d,
      "probe",
      "all",
      "--json",
    ];
    (0, Dt.execFile)(
      r.path,
      n,
      { encoding: "utf-8", timeout: 6e4, windowsHide: !0 },
      (a, o) => {
        var l, c, p;
        try {
          let u = JSON.parse(o);
          if (u.module === "all" && u.modules) {
            e(u);
            return;
          }
          t(
            new ye(
              "probe.invalid_envelope",
              {
                stdout:
                  (l = o == null ? void 0 : o.slice(0, 200)) != null ? l : "",
              },
              "probe all returned an invalid envelope"
            )
          );
        } catch (u) {
          t(
            new ye(
              "config.invalid_response",
              {
                stdout:
                  (c = o == null ? void 0 : o.slice(0, 200)) != null ? c : "",
                stderr: (p = a == null ? void 0 : a.message) != null ? p : "",
              },
              `Invalid probe response: ${String(u)}`
            )
          );
        }
      }
    );
  });
}
function Er(d, i) {
  return be(d, ["memory", "status"], i);
}
function dt(d, i) {
  return be(d, ["embed", "status"], i);
}
var wn = null;
function kr() {
  wn = null;
}
var Wr = V(Mt());
var kn = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  Sn = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function ve(d, i, e) {
  return d.createEl("span", {
    cls: kn[i],
    text: e != null ? e : Sn[i],
    attr: { role: "status" },
  });
}
function Sr(d, i) {
  let e = d.createEl("div", { cls: "pf-activity-row" }),
    t = e.createEl("span", { cls: "pf-activity-label", text: i.label });
  if (i.progress && i.progress.total > 0) {
    let r = e.createEl("div", { cls: "pf-activity-bar" }),
      n = Math.round((i.progress.current / i.progress.total) * 100);
    (r.createEl("div", {
      cls: "pf-activity-bar-fill",
      attr: {
        style: `width: ${n}%`,
        role: "progressbar",
        "aria-valuenow": String(i.progress.current),
        "aria-valuemin": "1",
        "aria-valuemax": String(i.progress.total),
      },
    }),
      e.createEl("span", {
        cls: "pf-activity-count",
        text: `${i.progress.current}/${i.progress.total}`,
      }));
  } else
    e.createEl("span", { cls: "pf-activity-spinner" }).setAttr(
      "aria-label",
      "In progress"
    );
  if (
    (i.scope && e.createEl("span", { cls: "pf-activity-scope", text: i.scope }),
    i.stopLabel && i.onStop)
  ) {
    let r = e.createEl("button", {
      cls: "pf-activity-stop",
      text: i.stopLabel,
    });
    (r.addEventListener("click", i.onStop),
      r.addEventListener("keydown", (n) => {
        var a;
        (n.key === "Enter" || n.key === " ") &&
          (n.preventDefault(), (a = i.onStop) == null || a.call(i));
      }));
  }
  return e;
}
function j(d, i) {
  let e = d.createEl("button", {
    cls: "pf-action-btn",
    text: i.loading ? "\u2026" : i.label,
  });
  return (
    i.loading
      ? (e.setAttr("disabled", "true"),
        e.classList.add("pf-action-btn--loading"))
      : i.disabled &&
        (e.setAttr("disabled", "true"),
        e.classList.add("pf-action-btn--disabled")),
    e.addEventListener("click", i.onClick),
    e.addEventListener("keydown", (t) => {
      (t.key === "Enter" || t.key === " ") && (t.preventDefault(), i.onClick());
    }),
    e
  );
}
function Cr(d, i) {
  let e = d.createEl("div", { cls: "pf-error-anatomy" });
  e.createEl("div", { cls: "pf-error-title", text: i.whatHappened });
  let t = e.createEl("div", { cls: "pf-error-impact" });
  (t.createEl("span", {
    cls: "pf-error-impact-label",
    text: (i.impactLabel || "Impact:") + " ",
  }),
    t.createEl("span", { text: i.impact }),
    i.reasonCode &&
      e.createEl("div", { cls: "pf-error-code", text: i.reasonCode }));
  let r = e.createEl("div", { cls: "pf-error-next" });
  return (
    r.createEl("span", {
      cls: "pf-error-next-label",
      text: (i.nextLabel || "Next:") + " ",
    }),
    r.createEl("span", { text: i.nextStep }),
    i.onCopyDiagnostic &&
      e
        .createEl("button", {
          cls: "pf-error-copy-diagnostic",
          text: i.copyLabel || "Copy Diagnostic Information",
        })
        .addEventListener("click", i.onCopyDiagnostic),
    e
  );
}
function Pr(d, i) {
  let e = d.createEl("div", { cls: "pf-config-summary" });
  for (let r of i.items) {
    let n = e.createEl("div", { cls: "pf-config-row" });
    n.createEl("span", { cls: "pf-config-label", text: r.label });
    let a = r.isCredential
      ? r.value
        ? i.configuredLabel || "Configured"
        : i.notConfiguredLabel || "Not configured"
      : r.value;
    n.createEl("span", {
      cls: `pf-config-value${r.isCredential ? (r.value ? " pf-config-value--ok" : " pf-config-value--muted") : ""}`,
      text: a,
    });
  }
  return (
    e
      .createEl("button", {
        cls: "pf-config-change-btn",
        text: i.onChangeLabel,
      })
      .addEventListener("click", i.onChange),
    e
  );
}
function Rr(d) {
  let i = [];
  (i.push("=== PaperForge Support Diagnostic ==="),
    i.push(`Time: ${new Date().toISOString()}`),
    i.push(`Plugin: ${d.pluginVersion}`),
    d.backendVersion && i.push(`Backend: ${d.backendVersion}`),
    i.push(""),
    i.push("--- Module Status ---"));
  for (let e of d.modules)
    (i.push(`${e.module}: ${e.userState}`),
      e.reasonCode && i.push(`  reason: ${e.reasonCode}`),
      e.actionId && i.push(`  action: ${e.actionId}`),
      e.lastSuccessAt && i.push(`  last-success: ${e.lastSuccessAt}`),
      e.errorExcerpt && i.push(`  error: ${e.errorExcerpt}`));
  return (
    i.push(""),
    i.push("=== End ==="),
    i.join(`
`)
  );
}
function Fr(d, i) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      i == null || i();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Ar(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function Tr(d, i) {
  return !d || i.user_state === "ready"
    ? !0
    : !(i.user_state === "detection_failed" || d.user_state === "ready");
}
function Or(d, i) {
  var t, r, n, a, o, l, c;
  let e = [];
  for (let [p, u] of Object.entries(d)) {
    let f = i.get(p);
    e.push({
      module: p,
      userState: u.user_state,
      lastSuccessAt: (t = f == null ? void 0 : f.capturedAt) != null ? t : null,
      reasonCode: (r = u.reason) == null ? void 0 : r.code,
      actionId:
        (a = (n = u.action) == null ? void 0 : n.primary) == null
          ? void 0
          : a.action_id,
      errorExcerpt:
        (c =
          (l = (o = u.reason) == null ? void 0 : o.text) == null
            ? void 0
            : l.slice(0, 200)) != null
          ? c
          : void 0,
    });
  }
  return e;
}
var Me = require("obsidian");
function Dr(d) {
  try {
    let i = JSON.parse(d),
      e = i == null ? void 0 : i.next_actions;
    return Array.isArray(e) ? e : [];
  } catch (i) {
    return [];
  }
}
var It = new Set();
var Lr = {
  isInFlight: (d) => It.has(d),
  markInFlight: (d) => It.add(d),
  clearInFlight: (d) => It.delete(d),
};
var Cn = 1;
function Pn(d, i) {
  var e;
  return {
    action_id: d.action_id,
    scope: (e = d.scope) != null ? e : { kind: "all" },
    confirm: i ? d.action_id : void 0,
    follow: "auto",
  };
}
async function Br(d, i, e = 0) {
  var r, n;
  let t = 0;
  for (let a of d) {
    if (a.schema_version !== Cn) {
      i.notify(`Unknown next-action schema v${a.schema_version}; refused`);
      continue;
    }
    if (!a.action_id) {
      i.notify("Next action without action_id; refused");
      continue;
    }
    let o =
      a.dedupe_key ||
      `${a.action_id}:${(n = (r = a.scope) == null ? void 0 : r.kind) != null ? n : "all"}`;
    if (i.isInFlight(o)) continue;
    let l = !1;
    if (a.automatic !== !0) {
      if (e > 0) {
        i.notify(`Follow-up depth exceeded for '${a.action_id}'; skipped`);
        continue;
      }
      if (!(await i.confirm(a))) {
        i.notify(`Follow-up '${a.action_id}' refused by user`);
        continue;
      }
      l = !0;
    }
    i.markInFlight(o);
    let c = !1;
    try {
      c = i.runAction(Pn(a, l)) === !0;
    } finally {
      i.clearInFlight(o);
    }
    c && (t += 1);
  }
  return t;
}
function ut(d) {
  var e;
  let i = ["action", "run", d.action_id, "--scope", d.scope.kind];
  if (d.scope.kind === "papers")
    for (let t of (e = d.scope.keys) != null ? e : []) i.push("--key", t);
  return (
    d.confirm && i.push("--confirm", d.confirm),
    d.follow === "auto" && i.push("--follow", "auto"),
    i.push("--json"),
    i
  );
}
function Mr(d, i, e, t, r = 12e4) {
  let n = [...i, "-m", "paperforge", "--vault", e, ...ut(t)];
  return mr(d, n, e, r, void 0, G()).then((a) => {
    try {
      let o = JSON.parse(a.stdout);
      return { ok: o.ok === !0, payload: o, exitCode: a.exitCode };
    } catch (o) {
      return { ok: !1, payload: null, exitCode: a.exitCode };
    }
  });
}
async function Ie(d, i) {
  let e = Dr(d);
  if (e.length === 0) return 0;
  let t = e.filter((r) =>
    r.automatic ? !0 : (new Me.Notice(s("next_action_pending"), 8e3), !1)
  );
  return t.length === 0
    ? 0
    : Br(t, {
        runAction: (r) => {
          let n = i.resolveCommand(i.vaultPath);
          return n != null && n.path
            ? (Mr(n.path, n.args, i.vaultPath, r).then((a) => {
                var o, l;
                if (a.ok) new Me.Notice(s("next_action_done"));
                else {
                  let c =
                    (l = (o = a.payload) == null ? void 0 : o.error) == null
                      ? void 0
                      : l.message;
                  new Me.Notice(
                    s("next_action_failed").replace(
                      "{detail}",
                      String(c != null ? c : "unknown error")
                    )
                  );
                }
              }),
              !0)
            : (new Me.Notice(s("next_action_runtime_unavailable")), !1);
        },
        confirm: async () => !1,
        notify: (r) => new Me.Notice(r),
        ...Lr,
      });
}
var Ne = class {
  constructor() {
    this._queue = [];
    this._resolvers = [];
    this._done = !1;
    this._error = null;
  }
  push(i) {
    this._done ||
      (this._resolvers.length > 0
        ? this._resolvers.shift()({ value: i, done: !1 })
        : this._queue.push(i));
  }
  finish() {
    if (!this._done)
      for (this._done = !0; this._resolvers.length > 0; )
        this._resolvers.shift()({ value: void 0, done: !0 });
  }
  fail(i) {
    if (!this._done)
      for (this._error = i, this._done = !0; this._resolvers.length > 0; )
        this._resolvers.shift()({ value: void 0, done: !0 });
  }
  [Symbol.asyncIterator]() {
    return {
      next: () =>
        this._queue.length > 0
          ? Promise.resolve({ value: this._queue.shift(), done: !1 })
          : this._done
            ? this._error
              ? Promise.reject(this._error)
              : Promise.resolve({ value: void 0, done: !0 })
            : new Promise((i) => {
                this._resolvers.push(i);
              }),
    };
  }
};
var Rn = "available";
function Fn(d) {
  if (Array.isArray(d)) return d;
  if (!d || typeof d != "object") return [];
  let i = d,
    e = i.data;
  if (Array.isArray(e)) return e;
  if (e && typeof e == "object") {
    let t = e.rows;
    if (Array.isArray(t)) return t;
  }
  return Array.isArray(i.rows) ? i.rows : [];
}
function Ir(d) {
  let i = d;
  if (typeof d == "string")
    try {
      i = JSON.parse(d);
    } catch (t) {
      return [];
    }
  if (!i || typeof i != "object") return [];
  let e = i;
  if (e.data && typeof e.data == "object") {
    let t = e.data;
    if (Array.isArray(t.matches)) return t.matches;
    if (Array.isArray(t.results)) return t.results;
  }
  return Array.isArray(e.matches)
    ? e.matches
    : Array.isArray(e.results)
      ? e.results
      : Array.isArray(i)
        ? i
        : [];
}
var He = class {
  constructor(i) {
    this._epoch = 0;
    this._cache = new Map();
    this._inFlightReads = new Map();
    this._activeOperation = null;
    var e;
    ((this._transport = i.transport),
      (this._clock = (e = i.clock) != null ? e : Date.now));
  }
  getEpoch() {
    return this._epoch;
  }
  invalidateCache() {
    (this._epoch++, this._cache.clear(), this._inFlightReads.clear());
  }
  async _cachedRead(i, e, t) {
    let r = this._clock(),
      n = this._cache.get(i);
    if (n && n.epoch === this._epoch && n.expiresAt > r) return n.data;
    let a = this._inFlightReads.get(i);
    if (a && a.epoch === this._epoch) return a.promise;
    let o = this._epoch,
      l,
      c = (async () => {
        try {
          let p = await t();
          return (
            this._epoch === o &&
              this._cache.set(i, {
                data: p,
                expiresAt: this._clock() + e,
                epoch: o,
              }),
            p
          );
        } finally {
          l &&
            this._inFlightReads.get(i) === l &&
            this._inFlightReads.delete(i);
        }
      })();
    return ((l = { promise: c, epoch: o }), this._inFlightReads.set(i, l), c);
  }
  isOperationActive() {
    return this._activeOperation !== null;
  }
  get activeOperationId() {
    var i, e;
    return (e = (i = this._activeOperation) == null ? void 0 : i.operationId) !=
      null
      ? e
      : null;
  }
  cancelActiveOperation() {
    this._activeOperation && this._activeOperation.stop();
  }
  streamOperation(i, e, t) {
    if (this._activeOperation)
      throw new Error(
        `Another operation is already active: ${this._activeOperation.operationId}`
      );
    let r = this._transport.stream(e, t),
      n = new Ne();
    (async () => {
      try {
        for await (let o of r.events) n.push(o);
        n.finish();
      } catch (o) {
        n.fail(o);
      }
    })();
    let a = (async () => {
      try {
        return await r.outcome;
      } finally {
        ((this._activeOperation = null), this.invalidateCache());
      }
    })();
    return (
      (this._activeOperation = { operationId: i, stop: r.stop, outcome: a }),
      { events: n, stop: r.stop, outcome: a }
    );
  }
  async probe(i, e) {
    var n, a;
    let t = [];
    (e != null &&
      e.expectedVersion &&
      t.push("--expected-version", e.expectedVersion),
      (e == null ? void 0 : e.lastOperationExitCode) != null &&
        e.lastOperationExitCode !== 0 &&
        t.push("--last-operation-exit-code", String(e.lastOperationExitCode)));
    let r = `probe:${i}:${(n = e == null ? void 0 : e.expectedVersion) != null ? n : ""}:${(a = e == null ? void 0 : e.lastOperationExitCode) != null ? a : ""}`;
    return this._cachedRead(r, 6e4, async () => {
      let o = await this._transport.execute(["probe", i, "--json", ...t]);
      return JSON.parse(o);
    });
  }
  async probeAll() {
    return this._cachedRead("probe:all", 6e4, async () => {
      let i = await this._transport.execute(["probe", "all", "--json"]);
      return JSON.parse(i);
    });
  }
  async reconcile(i = "all", e) {
    let t = e ? [...e].sort().join(",") : "";
    return this._cachedRead(`reconcile:${i}:${t}`, 1e4, async () => {
      let r = ["reconcile", "--scope", i];
      for (let a of e != null ? e : []) r.push("--key", a);
      r.push("--json");
      let n = await this._transport.execute(r);
      return JSON.parse(n);
    });
  }
  async _executePfResult(i) {
    let e = await this._transport.execute(i),
      t;
    try {
      t = JSON.parse(e);
    } catch (r) {
      throw new Error(`Failed to parse PFResult JSON: ${e.slice(0, 100)}`);
    }
    return t && typeof t == "object" && "data" in t ? t.data : t;
  }
  async listActions() {
    return this._cachedRead("action:list", 3e5, async () => {
      var e;
      let i = await this._executePfResult(["action", "list", "--json"]);
      return (e = i == null ? void 0 : i.actions) != null
        ? e
        : Array.isArray(i)
          ? i
          : [];
    });
  }
  async describeAction(i) {
    return this._cachedRead(`action:describe:${i}`, 3e5, async () =>
      this._executePfResult(["action", "describe", i, "--json"])
    );
  }
  async preflightAction(i, e = { kind: "all" }) {
    var r;
    let t = ["action", "preflight", i, "--scope", e.kind];
    for (let n of (r = e.keys) != null ? r : []) t.push("--key", n);
    return (t.push("--json"), this._executePfResult(t));
  }
  async runAction(i, e) {
    var a, o, l, c;
    let t = await this.describeAction(i.action_id);
    if (t != null && t.availability && t.availability !== Rn)
      return {
        ok: !1,
        payload: {
          ok: !1,
          action_id: i.action_id,
          availability: t.availability,
          availability_reason: t.availability_reason,
        },
        exitCode: 1,
      };
    let r = { ...i, scope: (a = i.scope) != null ? a : { kind: "all" } },
      n = ut(r);
    if ((t == null ? void 0 : t.execution_mode) === "stream") {
      let u = await this.streamOperation(`action.${i.action_id}`, n, e).outcome,
        f = u.events.find(
          (h) =>
            h.event === "result" ||
            h.event === "error" ||
            h.event === "cancelled"
        ),
        _ = (o = f == null ? void 0 : f.result) != null ? o : null;
      return {
        ok: u.ok,
        payload: _,
        exitCode: (l = u.exitCode) != null ? l : u.ok ? 0 : 1,
        cancelled: u.cancelled,
      };
    }
    try {
      let p = await this._transport.execute(n),
        u = null;
      try {
        u = JSON.parse(p);
      } catch (f) {}
      return { ok: !0, payload: u, exitCode: 0 };
    } catch (p) {
      return {
        ok: !1,
        payload: null,
        exitCode: (c = p.exitCode) != null ? c : 1,
      };
    } finally {
      this.invalidateCache();
    }
  }
  streamAction(i, e = { kind: "all" }, t) {
    let r = typeof i == "string" ? { action_id: i, scope: e } : i,
      n = ut(r);
    return this.streamOperation(`action.${r.action_id}`, n, t);
  }
  setup(i, e) {
    let t = ["setup", "--json"];
    return (
      (i.modular || !i.headless) && t.push("--modular"),
      i.systemDir && t.push("--system-dir", i.systemDir),
      i.resourcesDir && t.push("--resources-dir", i.resourcesDir),
      i.literatureDir && t.push("--literature-dir", i.literatureDir),
      i.baseDir && t.push("--base-dir", i.baseDir),
      i.zoteroData && t.push("--zotero-data", i.zoteroData),
      i.agent && t.push("--agent", i.agent),
      i.skipChecks && t.push("--skip-checks"),
      this.streamOperation("foundation.setup", t, e)
    );
  }
  async sync(i = !1) {
    let e = ["sync", "--json"];
    i && e.push("--dry-run");
    let t = await this._transport.execute(e);
    return (this.invalidateCache(), JSON.parse(t));
  }
  async search(i, e) {
    var o;
    let r =
        (o = (typeof e == "number" ? { limit: e } : e != null ? e : {})
          .limit) != null
          ? o
          : 20,
      n = i.trim(),
      a = `search:${n}:${r}`;
    return this._cachedRead(a, 3e4, async () => {
      let l = await this._transport.execute([
        "search",
        n,
        "--limit",
        String(r),
        "--json",
      ]);
      return Ir(l);
    });
  }
  async retrieve(i, e) {
    var p, u;
    let t = typeof e == "number" ? { limit: e } : e != null ? e : {},
      r = (p = t.limit) != null ? p : 5,
      n = !!t.deep,
      a = ((u = t.paper) == null ? void 0 : u.trim()) || "",
      o = t.expand !== !1,
      l = i.trim(),
      c = `retrieve:${l}:${r}:${n}:${a}:${o}`;
    return this._cachedRead(c, 3e4, async () => {
      let f = ["retrieve", l, "--limit", String(r)];
      (n && f.push("--deep"),
        a && f.push("--paper", a),
        o || f.push("--no-expand"),
        f.push("--json"));
      let _ = await this._transport.execute(f);
      return Ir(_);
    });
  }
  async read(i, e, t = "auto") {
    return await this._transport.execute([
      "read",
      i,
      "--find",
      e,
      "--source",
      t,
    ]);
  }
  async paperStatus(i) {
    return this._cachedRead(`paper-status:${i}`, 3e4, async () => {
      let e = await this._transport.execute(["paper-status", i, "--json"]);
      return JSON.parse(e);
    });
  }
  async queryOcrPapers(i) {
    let e = i ? [...i].sort() : [],
      t = e.join(",");
    return this._cachedRead(`ocr-papers:${t}`, 1e4, async () => {
      let r = ["ocr", "list", "--json"];
      e.length > 0 && r.push("--keys", ...e);
      let n = await this._transport.execute(r);
      return Fn(JSON.parse(n));
    });
  }
  async _executeStructuredJson(i) {
    var e;
    try {
      let t = await this._transport.execute(i);
      return JSON.parse(t);
    } catch (t) {
      let r = t instanceof Error && (e = t.stdout) != null ? e : null;
      if (typeof r == "string" && r.trim())
        try {
          return JSON.parse(r);
        } catch (n) {}
      throw t;
    }
  }
  async renderAudit(i) {
    let e = ["render", "audit"];
    return (i && e.push(i), e.push("--json"), this._executeStructuredJson(e));
  }
  async renderReconcileStaging(i) {
    var r, n;
    return (n =
      (r = (
        await this._executeStructuredJson(["render", "reconcile", i, "--json"])
      ).papers) == null
        ? void 0
        : r.find((a) => a.paper_key === i)) != null
      ? n
      : {};
  }
  async promoteR(i, e = []) {
    let t = ["render", "promote-r", i, ...e, "--json"];
    try {
      return await this._executeStructuredJson(t);
    } finally {
      this.invalidateCache();
    }
  }
  async acceptProposal(i, e, t) {
    let r = ["render", "accept-proposal", i, e, "--plan-hash", t, "--json"];
    try {
      return await this._executeStructuredJson(r);
    } finally {
      this.invalidateCache();
    }
  }
};
var zr = require("child_process");
var Nt = require("child_process");
var An = new Set([
    "start",
    "preflight",
    "phase",
    "progress",
    "paper_settled",
    "heartbeat",
    "item_result",
    "result",
    "error",
    "cancelled",
  ]),
  Tn = new Set(["result", "error", "cancelled"]),
  $e = class {
    constructor() {
      this._buffer = "";
      this._terminalSeen = !1;
    }
    get protocolFailure() {
      return this._protocolFailure;
    }
    get terminalSeen() {
      return this._terminalSeen;
    }
    feed(i) {
      var n;
      if (this._protocolFailure) return [];
      let t = (this._buffer + i).split(`
`);
      this._buffer = (n = t.pop()) != null ? n : "";
      let r = [];
      for (let a of t) {
        if (!a.trim()) continue;
        let o;
        try {
          o = JSON.parse(a);
        } catch (l) {
          this._protocolFailure = `non-JSON stdout line: ${a.slice(0, 80)}`;
          break;
        }
        if (o.schema_version !== 1) {
          this._protocolFailure = `schema_version ${o.schema_version} != 1`;
          break;
        }
        if (typeof o.event != "string" || !An.has(o.event)) {
          this._protocolFailure = `unknown event: ${String(o.event)}`;
          break;
        }
        if (this._terminalSeen) {
          this._protocolFailure = "event after terminal";
          break;
        }
        (Tn.has(o.event) && (this._terminalSeen = !0), r.push(o));
      }
      return r;
    }
    finishEOF() {
      !this._protocolFailure &&
        !this._terminalSeen &&
        (this._protocolFailure = "EOF without terminal event");
    }
  };
function On(d) {
  if (d.pid)
    if (process.platform === "win32")
      try {
        (0, Nt.spawn)("taskkill", ["/T", "/F", "/PID", String(d.pid)], {
          stdio: "ignore",
        });
      } catch (i) {
        d.kill("SIGKILL");
      }
    else
      try {
        process.kill(-d.pid, "SIGKILL");
      } catch (i) {
        d.kill("SIGKILL");
      }
}
function Nr(d, i, e, t, r) {
  var f, _, h;
  let n = (f = r.env) != null ? f : G(),
    a = (0, Nt.spawn)(d, [...i, "-m", "paperforge", "--vault", e, ...t], {
      cwd: e,
      shell: !1,
      windowsHide: !0,
      env: n,
      stdio: ["pipe", "pipe", "pipe"],
    }),
    o = new $e(),
    l = [],
    c = !1,
    p = null;
  ((_ = a.stdout) == null || _.setEncoding("utf-8"),
    (h = a.stdout) == null ||
      h.on("data", (g) => {
        for (let m of o.feed(g)) (l.push(m), r.onEvent(m));
      }));
  let u = new Promise((g) => {
    (a.on("close", (m) => {
      (p && clearTimeout(p),
        o.finishEOF(),
        g({
          ok: !o.protocolFailure && m === 0,
          exitCode: m,
          cancelled: m === 130,
          events: l,
          protocolFailure: o.protocolFailure,
        }));
    }),
      a.on("error", (m) => {
        (p && clearTimeout(p),
          g({
            ok: !1,
            exitCode: -1,
            cancelled: !1,
            events: l,
            protocolFailure: `spawn error: ${m.message}`,
          }));
      }));
  });
  return {
    stop: () => {
      var m, v;
      try {
        (m = a.stdin) == null ||
          m.write(`PAPERFORGE_STOP
`);
      } catch (b) {}
      if (p) return;
      let g = (v = r.graceMs) != null ? v : 5e3;
      p = setTimeout(() => {
        a.exitCode === null && !c && ((c = !0), On(a));
      }, g);
    },
    promise: u,
  };
}
var $t = V(require("fs")),
  oe = V(require("path")),
  _t = require("child_process"),
  $r = V(require("os")),
  Hr = "3.11",
  Dn = 1,
  Ln = "pointer.json",
  Bn = "venv";
function Ht() {
  let d, i;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (i = r));
    }),
    resolve: d,
    reject: i,
  };
}
function Mn(d) {
  let i = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (i) return i[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function In(d, i) {
  var r, n;
  let e = d.split(".").map(Number),
    t = i.split(".").map(Number);
  for (let a = 0; a < Math.max(e.length, t.length); a++) {
    let o = (r = e[a]) != null ? r : 0,
      l = (n = t[a]) != null ? n : 0;
    if (o !== l) return o - l;
  }
  return 0;
}
function Nn(d, i) {
  return In(d, i) >= 0;
}
function Hn() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function $n() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function zn(d, i) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${i}`;
}
function ce(d) {
  return d ? { command: d.pythonPath, args: [] } : null;
}
var le = class {
    constructor(i) {
      var e, t, r, n, a, o;
      ((this.osPlatform =
        (e = i == null ? void 0 : i.osPlatform) != null ? e : process.platform),
        (this.osArch =
          (t = i == null ? void 0 : i.osArch) != null ? t : process.arch),
        (this.rootDir =
          (r = i == null ? void 0 : i.runtimeDir) != null
            ? r
            : oe.join($r.homedir(), ".paperforge", "runtime")),
        (this._fs = (n = i == null ? void 0 : i.fs) != null ? n : $t),
        (this._execFile =
          (a = i == null ? void 0 : i.execFile) != null ? a : _t.execFile),
        (this._execFileSync =
          (o = i == null ? void 0 : i.execFileSync) != null
            ? o
            : _t.execFileSync));
    }
    get venvDir() {
      return oe.join(this.rootDir, Bn);
    }
    pythonExeFor(i) {
      return this.osPlatform === "win32"
        ? oe.join(i, "Scripts", "python.exe")
        : oe.join(i, "bin", "python");
    }
    discoverInterpreter() {
      let i =
        this.osPlatform === "win32"
          ? [
              { path: "py", args: ["-3"] },
              { path: "py", args: ["-3.11"] },
              { path: "python", args: [] },
            ]
          : this.osPlatform === "darwin"
            ? [
                { path: "/usr/bin/python3", args: [] },
                { path: "python3", args: [] },
              ]
            : [
                { path: "/usr/bin/python3", args: [] },
                { path: "python3", args: [] },
              ];
      for (let e of i)
        try {
          let t = this._execFileSync(e.path, [...e.args, "--version"], {
              encoding: "utf-8",
              timeout: 5e3,
            }),
            r = Mn(t);
          if (r && Nn(r, Hr)) return { path: e.path, version: r };
        } catch (t) {}
      return null;
    }
    platformGate() {
      if (Hn() || $n())
        return {
          ok: !1,
          code: "FLATPAK_SNAP_UNSUPPORTED",
          message:
            "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
          platformAction:
            "Install Python 3.11+ from python.org or package manager",
        };
      let i = zn(this.osPlatform, this.osArch);
      return this.osPlatform === "darwin" &&
        ["macos-x64", "macos-arm64"].includes(i)
        ? {
            ok: !1,
            code: "NO_PYTHON",
            message:
              "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
            platformAction: "Install Python 3.11+ from python.org or Homebrew",
          }
        : ["windows-x64", "linux-x64"].includes(i)
          ? {
              ok: !1,
              code: "NO_PYTHON",
              message: "No Python 3.11+ found and automatic download failed.",
              platformAction: "Install Python 3.11+ manually",
            }
          : {
              ok: !1,
              code: "FALLBACK_UNAVAILABLE",
              message:
                "No Python found and this platform has no validated fallback.",
              platformAction: "Install Python 3.11+ manually from python.org",
            };
    }
    async installOnce(i, e) {
      if (e != null && e.aborted) throw new ze("Operation was cancelled");
      let t = this.discoverInterpreter();
      if (!t) {
        let n = this.platformGate();
        throw new Error(
          `No Python ${Hr}+ found (${n.ok ? "no interpreter" : n.message})`
        );
      }
      if (e != null && e.aborted) throw new ze("Operation was cancelled");
      let r = this.pythonExeFor(this.venvDir);
      try {
        if (
          (this._fs.mkdirSync(this.venvDir, { recursive: !0 }),
          await this._exec(
            t.path,
            ["-m", "venv", this.venvDir],
            { timeout: 6e4, signal: e },
            "venv creation"
          ),
          e != null && e.aborted)
        )
          throw new ze("Operation was cancelled");
        if (
          (await this._exec(
            r,
            ["-m", "pip", "install", `paperforge[vector]==${i}`],
            { timeout: 12e4, signal: e },
            "pip install"
          ),
          e != null && e.aborted)
        )
          throw new ze("Operation was cancelled");
        let n = await this._probeVersion(r, e);
        if (n !== i)
          throw new Error(
            `installed version mismatch: observed ${n} != requested ${i}`
          );
      } catch (n) {
        try {
          this._fs.rmSync(this.venvDir, { recursive: !0, force: !0 });
        } catch (a) {}
        throw n;
      }
      return { pythonPath: r, observedVersion: i };
    }
    async handshake(i, e) {
      var r;
      let t = (r = e.pythonPath) != null ? r : this.pythonExeFor(this.venvDir);
      if (!this._fs.existsSync(t))
        return { ok: !1, observedVersion: null, reason: "interpreter missing" };
      try {
        let n = await this._probeVersion(t, e.signal);
        if (n !== i)
          return {
            ok: !1,
            observedVersion: n,
            reason: `version mismatch: observed ${n} != expected ${i}`,
          };
        let a = await this._probeInstallation(t, e.vaultPath, i, e.signal);
        if (a === null)
          return {
            ok: !1,
            observedVersion: n,
            reason:
              "installation probe failed or returned an unparseable envelope",
          };
        if (a === "installation.version_mismatch")
          return {
            ok: !1,
            observedVersion: n,
            reason: "installation probe reports version mismatch",
          };
        if (
          a !== "installation.ready" &&
          a !== "installation.config_missing" &&
          a !== "installation.config_corrupt"
        )
          return {
            ok: !1,
            observedVersion: n,
            reason: `unexpected installation probe state: ${a}`,
          };
      } catch (n) {
        return {
          ok: !1,
          observedVersion: null,
          reason: n instanceof Error ? n.message : String(n),
        };
      }
      return { ok: !0, observedVersion: i };
    }
    readPointer() {
      let i = oe.join(this.rootDir, Ln),
        e;
      try {
        e = this._fs.readFileSync(i, "utf-8");
      } catch (o) {
        return null;
      }
      let t;
      try {
        t = JSON.parse(e);
      } catch (o) {
        return null;
      }
      if (t.schema_version !== Dn) return null;
      let { python_path: r, environment_root: n, paperforge_version: a } = t;
      return typeof r != "string" ||
        !r ||
        typeof n != "string" ||
        !n ||
        typeof a != "string" ||
        !a ||
        !oe.isAbsolute(r) ||
        !oe.isAbsolute(n)
        ? null
        : { pythonPath: r, environmentRoot: n, paperforgeVersion: a };
    }
    _exec(i, e, t, r) {
      let { promise: n, resolve: a, reject: o } = Ht();
      return (
        this._execFile(i, e, { ...t, encoding: "utf-8" }, (l) => {
          l ? o(new Error(`${r} failed: ${l.message}`)) : a();
        }),
        n
      );
    }
    _probeVersion(i, e) {
      let { promise: t, resolve: r, reject: n } = Ht();
      return (
        this._execFile(
          i,
          ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
          { timeout: 3e4, signal: e },
          (a, o) => {
            if (a) n(a);
            else {
              let l = (o != null ? o : "").trim() || null;
              r(l);
            }
          }
        ),
        t
      );
    }
    _probeInstallation(i, e, t, r) {
      let { promise: n, resolve: a, reject: o } = Ht();
      return (
        this._execFile(
          i,
          [
            "-m",
            "paperforge",
            "--vault",
            e,
            "probe",
            "installation",
            "--json",
            "--expected-version",
            t,
          ],
          { timeout: 3e4, signal: r },
          (l, c) => {
            var p, u;
            if (l) {
              a(null);
              return;
            }
            try {
              let f = JSON.parse(c);
              a(
                (u = (p = f.reason) == null ? void 0 : p.code) != null
                  ? u
                  : null
              );
            } catch (f) {
              a(null);
            }
          }
        ),
        n
      );
    }
  },
  ze = class extends Error {
    constructor(i) {
      (super(i), (this.name = "AbortError"));
    }
  };
var qe = class {
  constructor(i) {
    var e, t;
    ((this._vaultPath = i.vaultPath),
      (this._customPythonPath =
        (e = i.customPythonPath) == null ? void 0 : e.trim()),
      (this._resolveRuntime = i.resolveRuntime),
      (this._spawnFn = (t = i.spawnFn) != null ? t : zr.spawn));
  }
  async resolvePython() {
    if (this._resolveRuntime) {
      let r = await this._resolveRuntime();
      if (r != null && r.path) return r;
      throw new Error(
        "PaperForge Python runtime not ready. Please complete setup or configure python_path."
      );
    }
    if (this._customPythonPath)
      return { path: this._customPythonPath, args: [] };
    let e = new le().readPointer(),
      t = ce(e);
    if (t != null && t.command) return { path: t.command, args: [...t.args] };
    throw new Error(
      "PaperForge Python runtime not ready. Please complete setup or configure python_path."
    );
  }
  async execute(i, e) {
    var o, l;
    let t =
        e != null && e.pythonExe
          ? { path: e.pythonExe, args: [] }
          : await this.resolvePython(),
      r = (o = e == null ? void 0 : e.env) != null ? o : G(),
      n = (l = e == null ? void 0 : e.timeoutMs) != null ? l : 12e4,
      a = [...t.args, "-m", "paperforge", "--vault", this._vaultPath, ...i];
    return new Promise((c, p) => {
      var g, m, v, b, x, E, y;
      let u;
      try {
        u = this._spawnFn(t.path, a, {
          cwd: this._vaultPath,
          shell: !1,
          windowsHide: !0,
          env: r,
          stdio: ["pipe", "pipe", "pipe"],
        });
      } catch (w) {
        return p(new Error(`Failed to spawn Python process: ${w}`));
      }
      let f = [],
        _ = [];
      (typeof ((g = u.stdout) == null ? void 0 : g.setEncoding) == "function" &&
        u.stdout.setEncoding("utf-8"),
        (m = u.stdout) == null ||
          m.on("data", (w) => {
            f.push(w.toString());
          }),
        typeof ((v = u.stderr) == null ? void 0 : v.setEncoding) ==
          "function" && u.stderr.setEncoding("utf-8"),
        (b = u.stderr) == null ||
          b.on("data", (w) => {
            _.push(w.toString());
          }));
      let h = null;
      if (
        (n > 0 &&
          (h = setTimeout(() => {
            try {
              u.kill();
            } catch (w) {}
            p(
              new Error(
                `PaperForge command timed out after ${n}ms: ${i.join(" ")}`
              )
            );
          }, n)),
        e != null && e.stdin)
      )
        try {
          ((x = u.stdin) == null || x.write(e.stdin),
            (E = u.stdin) == null || E.end());
        } catch (w) {}
      else (y = u.stdin) == null || y.end();
      (u.on("close", (w) => {
        if ((clearTimeout(h), w === 0)) c(f.join(""));
        else {
          let k = _.join("").trim(),
            S = new Error(
              `PaperForge command failed (exit code ${w}): ${k || i.join(" ")}`
            );
          ((S.exitCode = w != null ? w : 1),
            (S.stderr = k),
            (S.stdout = f.join("")),
            p(S));
        }
      }),
        u.on("error", (w) => {
          (clearTimeout(h), p(w));
        }));
    });
  }
  stream(i, e) {
    let t = new Ne(),
      r = !1,
      n = null,
      a = (async () => {
        let o;
        try {
          o =
            e != null && e.pythonExe
              ? { path: e.pythonExe, args: [] }
              : await this.resolvePython();
        } catch (l) {
          let c = (l == null ? void 0 : l.message) || String(l);
          return (
            t.fail(l),
            {
              ok: !1,
              exitCode: -1,
              cancelled: !1,
              events: [],
              protocolFailure: c,
            }
          );
        }
        ((n = Nr(o.path, o.args, this._vaultPath, i, {
          graceMs: e == null ? void 0 : e.graceMs,
          env: e == null ? void 0 : e.env,
          onEvent: (l) => {
            var c;
            (t.push(l),
              (c = e == null ? void 0 : e.onEvent) == null || c.call(e, l));
          },
        })),
          r && n.stop());
        try {
          let l = await n.promise;
          return (t.finish(), l);
        } catch (l) {
          throw (t.fail(l), l);
        }
      })();
    return {
      events: t,
      stop: () => {
        ((r = !0), n && n.stop());
      },
      outcome: a,
    };
  }
};
var re = require("obsidian"),
  qr = V(require("fs")),
  qn = V(require("path")),
  Kn = V(require("https")),
  Kr = require("child_process");
var Xe = class extends re.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((a, o) => ({ ...a, _selected: !0, _idx: o }))),
      (this.vaultPath = r),
      (this.py = n));
  }
  _updateUI() {
    let e = this.orphans.filter((t) => t._selected);
    (this._countEl.setText(
      s("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? s("orphan_deselect_all")
          : s("orphan_select_all")
      ));
    for (let t of this.orphans) {
      let r = this._rowEls[t._idx];
      r && r.toggleClass("paperforge-orphan-dimmed", !t._selected);
    }
  }
  onOpen() {
    let { contentEl: e } = this;
    (e.addClass("paperforge-modal"),
      e.createEl("h2", {
        text: s("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: s("orphan_desc") }),
      (this._rowEls = []));
    let t = e.createEl("div", { cls: "paperforge-orphan-list" });
    for (let n of this.orphans) {
      let a = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(a);
      let o = a.createEl("div", { cls: "paperforge-orphan-info" }),
        l = o.createEl("div", { cls: "paperforge-orphan-header" });
      l.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let c = l.createEl("span", { cls: "paperforge-orphan-tags" });
      (c.createEl("span", {
        cls: "paperforge-tag " + (n.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: n.has_pdf ? "PDF" : "no PDF",
      }),
        n.collection_path &&
          c.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: n.collection_path,
          }),
        n.title &&
          o.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let p = [];
      (n.authors && p.push(n.authors),
        n.year && p.push(n.year),
        p.length > 0 &&
          o.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: p.join(" \xB7 "),
          }),
        o.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: s("orphan_explain"),
        }),
        a.addEventListener("click", () => {
          ((n._selected = !n._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let n = this.orphans.every((a) => a._selected);
        for (let a of this.orphans) a._selected = !n;
        this._updateUI();
      }),
      (this._countEl = r.createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: "Delete " + this.orphans.length + " selected",
      })),
      r
        .createEl("button", { cls: "paperforge-step-btn", text: "Keep all" })
        .addEventListener("click", () => this.close()),
      this._countEl.addEventListener("click", () => {
        var c, p, u;
        let n = this.orphans.filter((f) => f._selected);
        if (n.length === 0) {
          new re.Notice(s("orphan_none_selected"));
          return;
        }
        (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""));
        let a = n.map((f) => f.key),
          o =
            (p = (c = this.app.plugins) == null ? void 0 : c.plugins) == null
              ? void 0
              : p.paperforge,
          l =
            (u = o == null ? void 0 : o.getClient) == null ? void 0 : u.call(o);
        if (!l) {
          (new re.Notice("PaperForge: client unavailable"), this.close());
          return;
        }
        l.describeAction("library.prune")
          .then((f) => {
            var g;
            let _ =
                (g = f == null ? void 0 : f.action_id) != null
                  ? g
                  : "library.prune",
              h =
                (f == null ? void 0 : f.confirmation) === "required"
                  ? _
                  : void 0;
            return l.runAction({
              action_id: _,
              scope: { kind: "papers", keys: a },
              confirm: h,
            });
          })
          .then((f) => {
            var _, h, g;
            if (f.ok) {
              let m =
                (g =
                  (h = (_ = f.payload) == null ? void 0 : _.data) == null
                    ? void 0
                    : h.deleted) != null
                  ? g
                  : a;
              new re.Notice("Deleted " + m.length + " orphan workspace(s)");
            } else new re.Notice("PaperForge: prune failed");
            this.close();
          })
          .catch(() => {
            (new re.Notice("PaperForge: prune failed"), this.close());
          });
      }));
  }
  onClose() {
    this.contentEl.empty();
  }
};
function Ye(d, i, e) {
  var r;
  console.log("[PF] checkOrphanState called");
  let t = (r = i == null ? void 0 : i.getClient) == null ? void 0 : r.call(i);
  if (!t) {
    console.log("[PF] orphan file NOT FOUND");
    return;
  }
  t.reconcile("all")
    .then((n) => {
      var c;
      let o = (
          Array.isArray(n == null ? void 0 : n.deficits) ? n.deficits : []
        ).find(
          (p) =>
            p.kind === "orphan_residuals" || p.action_id === "library.prune"
        ),
        l = (c = o == null ? void 0 : o.paper_keys) != null ? c : [];
      if (l.length > 0) {
        console.log("[PF] orphan file FOUND");
        let p = l.map((u) => ({ key: u, title: u, folder: u }));
        new Xe(d, p, e, null).open();
      } else console.log("[PF] orphan file NOT FOUND");
    })
    .catch((n) => {
      console.log(
        "[PF] checkOrphanState exception:",
        (n == null ? void 0 : n.message) || n
      );
    });
}
function jr(d, i) {
  if (i.key !== "Tab") return;
  let e = d.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (e.length === 0) return;
  let t = e[0],
    r = e[e.length - 1];
  i.shiftKey
    ? document.activeElement === t && (i.preventDefault(), r.focus())
    : document.activeElement === r && (i.preventDefault(), t.focus());
}
var pe = class extends re.Modal {
    constructor(e, t, r) {
      super(e);
      this._returnFocusEl = null;
      this._inertedEls = [];
      ((this._config = t),
        (this._onConfirm = r),
        (this._returnFocusEl = document.activeElement));
    }
    onOpen() {
      let { contentEl: e } = this;
      (e.addClass("paperforge-modal"),
        e.addClass("paperforge-confirm-modal"),
        e.setAttr("role", "alertdialog"),
        e.setAttr("aria-modal", "true"));
      let t = e.closest(".modal-container");
      if (t) {
        let l = t.parentElement;
        if (l)
          for (let c of Array.from(l.children))
            c !== t &&
              !c.hasAttribute("inert") &&
              (c.setAttribute("inert", ""), this._inertedEls.push(c));
      }
      e.createEl("h2", { text: this._config.title });
      let r = e.createEl("div", { cls: "paperforge-confirm-effect" });
      (r.createEl("span", {
        cls: "paperforge-confirm-effect-label",
        text: s("confirm_effect_label") + ": ",
      }),
        r.createEl("span", { text: this._config.effectLabel }));
      let n = e.createEl("div", { cls: "paperforge-confirm-actions" }),
        a = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            s("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (a.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              s("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (l) => jr(e, l)),
        e.addEventListener("keydown", this._boundKeydown),
        a.focus());
    }
    onClose() {
      for (let e of this._inertedEls) e.removeAttribute("inert");
      if (
        ((this._inertedEls.length = 0),
        this._boundKeydown &&
          this.contentEl.removeEventListener("keydown", this._boundKeydown),
        this.contentEl.empty(),
        this._returnFocusEl && typeof this._returnFocusEl.focus == "function")
      )
        try {
          this._returnFocusEl.focus();
        } catch (e) {}
    }
  },
  jn = [
    { pattern: /sk-[A-Za-z0-9]{16,}/g, label: "API key", class_: "credential" },
    {
      pattern: /[A-Za-z0-9+/]{20,}={0,2}/g,
      label: "Credential token",
      class_: "credential",
    },
    {
      pattern: /api[_-]?key[=:]\s*['"]?\S+['"]?/gi,
      label: "API key",
      class_: "credential",
    },
    {
      pattern: /token[=:]\s*['"]?\S+['"]?/gi,
      label: "Token",
      class_: "credential",
    },
    {
      pattern: /[A-Za-z]:\\[^"'\n,;]+/gi,
      label: "Absolute path",
      class_: "vault-path",
    },
    {
      pattern: /(?<=^|\s)\/[^/\s][^"'\n,;]*/g,
      label: "Absolute path",
      class_: "vault-path",
    },
    {
      pattern: /Zotero[^"'\s,;]*/gi,
      label: "Zotero path",
      class_: "zotero-path",
    },
    {
      pattern: /Paper:\s*[^\n]+/gi,
      label: "Paper title",
      class_: "paper-title",
    },
    {
      pattern: /Title:\s*[^\n]+/gi,
      label: "Paper title",
      class_: "paper-title",
    },
  ];
function Qe(d) {
  let i = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of jn) {
    let a = 0;
    ((e = e.replace(t, () => (a++, "[REDACTED]"))),
      a > 0 &&
        (i[n] || (i[n] = { label: r, class_: n, count: 0 }),
        (i[n].count += a)));
  }
  return { clean: e, redactions: Object.values(i) };
}
function Vr(d, i, e, t) {
  let r = `OCR: ${d} (${e} papers)`,
    n = [
      "## Diagnostic Summary",
      `- Reason: ${d}`,
      `- Detail: ${i}`,
      `- Papers affected: ${e}`,
      "",
      "## Environment",
      "- Vault: [REDACTED]",
      "- Plugin version: PaperForge",
      "",
      "## Steps to reproduce",
      "1. Run OCR on affected papers",
      "2. Review output quality",
      "3. Review this draft, then open GitHub to submit",
    ].join(`
`);
  return { title: r, body: n, labels: ["ocr", "quality", "auto-generated"] };
}
var ft = class extends re.Modal {
  constructor(e, t, r) {
    super(e);
    this._returnFocusEl = null;
    this._inertedEls = [];
    ((this._draft = t),
      (this._githubUrl = r),
      (this._returnFocusEl = document.activeElement));
  }
  onOpen() {
    let { contentEl: e } = this;
    (e.addClass("paperforge-modal"),
      e.addClass("paperforge-issue-draft-modal"),
      e.setAttr("role", "dialog"),
      e.setAttr("aria-modal", "true"));
    let t = e.closest(".modal-container");
    if (t) {
      let g = t.parentElement;
      if (g)
        for (let m of Array.from(g.children))
          m !== t &&
            !m.hasAttribute("inert") &&
            (m.setAttribute("inert", ""), this._inertedEls.push(m));
    }
    (e.createEl("h2", {
      text: s("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          s("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = Qe(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let a = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    a.createEl("label", { text: "Body" });
    let o = Qe(this._draft.body).clean;
    this._bodyTextarea = a.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: o,
    });
    let { redactions: l } = Qe(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      c = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = c.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (s("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = c.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (u.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (s("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      u.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (l.length > 0
            ? " (" + l.map((g) => `${g.count} ${g.label}`).join(", ") + ")"
            : ""),
      }));
    let f = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (f
      .createEl("button", { text: s("maintenance_confirm_cancel") || "Cancel" })
      .addEventListener("click", () => this.close()),
      f
        .createEl("button", {
          cls: "mod-cta",
          text: s("maintenance_issue_draft_open_github") || "Open GitHub Issue",
        })
        .addEventListener("click", () => {
          let g = encodeURIComponent(Qe(this._titleInput.value).clean),
            m = encodeURIComponent(Qe(this._bodyTextarea.value).clean),
            v = encodeURIComponent(this._draft.labels.join(",")),
            b = `${this._githubUrl}?title=${g}&body=${m}&labels=${v}`;
          window.open(b, "_blank", "noopener,noreferrer");
        }),
      (this._boundKeydown = (g) => jr(e, g)),
      e.addEventListener("keydown", this._boundKeydown),
      this._titleInput.focus());
  }
  onClose() {
    for (let e of this._inertedEls) e.removeAttribute("inert");
    if (
      ((this._inertedEls.length = 0),
      this._boundKeydown &&
        this.contentEl.removeEventListener("keydown", this._boundKeydown),
      this.contentEl.empty(),
      this._returnFocusEl && typeof this._returnFocusEl.focus == "function")
    )
      try {
        this._returnFocusEl.focus();
      } catch (e) {}
  }
};
var je = class je extends T.PluginSettingTab {
  constructor(e, t) {
    super(e, t);
    this._saveTimeout = null;
    this._pfConfig = null;
    this._lastSyncTime = null;
    this._memoryStatusText = null;
    this._vectorDepsOk = null;
    this._embedStatusText = null;
    this._skillsCollapsed = { user: !0 };
    this._featurePanelsCollapsed = {};
    this._advCollapsed = !0;
    this._refreshPending = !1;
    this._pythonInterpDescEl = null;
    this._customPathDescEl = null;
    this._checkEl = null;
    this.activeTab = "overview";
    this._buildState = "idle";
    this._buildProgress = { current: 0, total: 0, key: "" };
    this._capabilityState = null;
    this._lastKnownState = new Map();
    this._navMemory = { destination: "overview" };
    this._initialDisplay = !0;
    this._probing = new Set();
    this._lastOrphanCount = 0;
    this._attemptedProbes = new Set();
    this._setupView = "overview";
    this._setupStage = 1;
    this._setupOptionals = { ocr: !1, memory: !1, agent: !1 };
    this._setupReinstallRequested = !1;
    this._setupOperation = "idle";
    this._setupFeedback = null;
    this._setupJourneyDismissedForSession = !1;
    this._selectedDetailModule = "";
    this._focusTargetId = null;
    this._runtimeAbortController = null;
    this._managedRuntime = null;
    this._runtimeBusy = !1;
    this._libraryRunning = !1;
    this._displayInProgress = !1;
    this._detailReturn = null;
    this._agentPlatformDraft = null;
    this._client = null;
    this.plugin = t;
  }
  _getOverviewModules() {
    return [
      { id: "installation", label: s("cc_module_foundation") || "Foundation" },
      { id: "library", label: s("cc_module_library") || "Library" },
      { id: "ocr", label: s("cc_module_ocr") || "OCR" },
      { id: "memory", label: s("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: s("cc_module_agent") || "Agent Integration" },
    ];
  }
  _getUserModuleName(e) {
    let t =
      "cc_module_" +
      (e === "installation" ? "foundation" : e === "memory" ? "memory" : e);
    return s(t) || e.charAt(0).toUpperCase() + e.slice(1);
  }
  _refreshPfConfig() {
    let e = this.plugin.settings;
    this._pfConfig = {
      system_dir: e.system_dir || "System",
      resources_dir: e.resources_dir || "Resources",
      literature_dir: e.literature_dir || "Literature",
      base_dir: e.base_dir || "Bases",
      zotero_data_dir: e.zotero_data_dir || "",
    };
  }
  display() {
    var u, f;
    this._displayInProgress = !0;
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      this._initialDisplay &&
        (this._restoreNavMemory(), (this._initialDisplay = !1)),
      this._initCapabilityState(),
      this.plugin.settings._setup_complete === !1 &&
        !this._setupJourneyDismissedForSession)
    ) {
      (this._renderSetupJourney(e), (this._displayInProgress = !1));
      return;
    }
    if (!document.getElementById("paperforge-tab-styles")) {
      let _ = document.createElement("style");
      ((_.id = "paperforge-tab-styles"),
        (_.textContent = `
                .paperforge-settings-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 1px solid var(--background-modifier-border); }
                .paperforge-settings-tab { padding: 6px 16px; border: none; background: none; cursor: pointer; border-bottom: 2px solid transparent; font-size: 14px; color: var(--text-muted); }
                .paperforge-settings-tab--active { color: var(--text-accent); border-bottom-color: var(--text-accent); }
                .paperforge-tab-content { display: none; }
                .paperforge-tab-content--active { display: block; }
                .paperforge-skills-collapse-header { display: flex !important; align-items: center; cursor: pointer; padding: 6px 0 !important; margin: 0 !important; }
                .paperforge-skills-collapse-header h4 { margin: 0 !important; }
                .paperforge-skills-collapse-content { margin: 0 !important; padding: 0 !important; }
                .paperforge-skills-group { margin-bottom: 10px; }
                .paperforge-skills-group:last-child { margin-bottom: 0; }
                .vertical-tab-content-container { overflow-y: scroll !important; }
                .paperforge-release-card { border: 1px solid var(--background-modifier-border); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
                .paperforge-release-header { margin-bottom: 8px; }
                .paperforge-release-date { color: var(--text-muted); font-size: 12px; }
                .paperforge-release-section { margin-bottom: 6px; }
                .paperforge-release-label { font-weight: 600; color: var(--text-accent); margin-bottom: 2px; font-size: 13px; }
                .paperforge-release-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-release-item-bold { font-size: 13px; margin-left: 8px; font-weight: 600; color: var(--text-normal); }
                .paperforge-release-recommended { background: rgba(var(--color-orange-rgb, 255,166,0), 0.08); border-radius: 4px; padding: 6px 8px; }
                .paperforge-manual-links { margin-top: 8px; }
                .paperforge-manual-links a { color: var(--text-accent); }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
                .paperforge-migration-warning { border: 1px solid var(--text-warning); border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; background: rgba(var(--color-yellow-rgb, 255, 208, 0), 0.08); color: var(--text-warning); font-size: 13px; }
                .paperforge-migration-warning strong { color: var(--text-warning); }
                .paperforge-migration-warning code { background: var(--background-modifier-border); padding: 1px 4px; border-radius: 3px; }
                .pf-maintenance-inbox { margin-bottom: 24px; container-type: inline-size; }
                .pf-maintenance-inbox-empty { color: var(--text-muted); font-style: italic; padding: 12px 0; }
                .pf-maintenance-inbox-summary { font-weight: 600; margin-bottom: 8px; }
                .pf-maintenance-inbox-list { display: flex; flex-direction: column; gap: 8px; }
                .pf-maintenance-inbox-item { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 8px 12px; border: 1px solid var(--background-modifier-border); border-radius: 6px; background: var(--background-primary); flex-wrap: wrap; }
                @container (max-width: 730px) { .pf-maintenance-inbox-item { flex-direction: column; } .pf-maintenance-inbox-item-actions { width: 100%; justify-content: flex-end; } }
                .pf-maintenance-inbox-item--dismissed { opacity: 0.45; }
                .pf-maintenance-inbox-item-info { flex: 1; min-width: 0; }
                .pf-maintenance-inbox-item-module { font-weight: 600; cursor: pointer; background: none; border: none; color: var(--text-accent); padding: 0; font-size: inherit; text-align: left; }
                .pf-maintenance-inbox-item-module:hover { text-decoration: underline; }
                .pf-maintenance-inbox-item-reason { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
                .pf-maintenance-inbox-item-activity { font-size: 11px; color: var(--text-accent); margin-top: 2px; }
                .pf-maintenance-inbox-item-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }
                .pf-maintenance-inbox-item-badge { font-size: 11px; padding: 2px 8px; border-radius: 10px; background: var(--background-modifier-border); white-space: nowrap; }
                .pf-maintenance-inbox-item-badge--warn { background: rgba(var(--color-yellow-rgb),0.15); color: var(--text-warning); }
                .pf-maintenance-inbox-item-badge--error { background: rgba(var(--color-red-rgb),0.12); color: var(--text-error); }
                .pf-maintenance-inbox-item-badge--unknown { background: var(--background-modifier-border); color: var(--text-muted); }
                .pf-maintenance-inbox-item-action { font-size: 12px; padding: 3px 10px; cursor: pointer; }
                .pf-maintenance-inbox-item-dismiss { font-size: 11px; padding: 2px 6px; background: none; border: 1px solid var(--background-modifier-border); border-radius: 4px; cursor: pointer; color: var(--text-muted); }
                .paperforge-confirm-effect { margin: 8px 0; font-size: 13px; }
                .paperforge-confirm-effect-label { font-weight: 600; }
                .paperforge-confirm-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
                .paperforge-issue-draft-desc { font-size: 13px; color: var(--text-muted); margin-bottom: 12px; }
                .paperforge-issue-draft-field { margin-bottom: 12px; }
                .paperforge-issue-draft-field label { display: block; font-weight: 600; margin-bottom: 4px; font-size: 13px; }
                .paperforge-issue-draft-input { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; }
                .paperforge-issue-draft-textarea { width: 100%; padding: 6px 8px; border: 1px solid var(--background-modifier-border); border-radius: 4px; font-size: 13px; resize: vertical; min-height: 120px; }
                .paperforge-issue-draft-preview { margin: 12px 0; padding: 8px 12px; background: var(--background-secondary); border-radius: 6px; font-size: 12px; }
                .paperforge-issue-draft-preview-label { font-weight: 600; }
                .paperforge-issue-draft-included { color: var(--text-success); margin-bottom: 2px; }
                .paperforge-issue-draft-redacted { color: var(--text-warning); }
                .paperforge-issue-draft-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; }
                .pf-diag-table { width: 100%; border-collapse: collapse; font-size: 12px; }
                .pf-diag-table tr + tr { border-top: 1px solid var(--background-modifier-border); }
                .pf-diag-label { padding: 4px 8px; color: var(--text-muted); white-space: nowrap; vertical-align: top; width: 140px; }
                .pf-diag-value { padding: 4px 8px; color: var(--text-normal); font-family: var(--font-monospace); }
                .pf-sr-diagnostics { margin-top: 16px; padding: 8px 12px; border: 1px solid var(--background-modifier-border); border-radius: 6px; }
                .pf-sr-diagnostics summary { cursor: pointer; font-weight: 600; font-size: 13px; color: var(--text-muted); }
                .pf-sr-diagnostics summary:hover { color: var(--text-normal); }
                .pf-sr-diagnostics-body { margin-top: 8px; }
            `),
        document.head.appendChild(_));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let _ = e.createDiv({ cls: "paperforge-migration-warning" }),
        h = t
          .map((g) => (g === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (_.createEl("strong", { text: s("migration_banner_title") }),
        _.createEl("p", {
          text: s("migration_banner_body").replace("{modules}", h),
        }),
        _.createEl("p", {
          text: s("migration_banner_next"),
          cls: "paperforge-manual-links",
        }));
    }
    let r = e.createDiv({ cls: "pf-cc-topbar" }),
      n = r.createDiv({ cls: "pf-cc-topbar-left" });
    (n.createEl("span", { cls: "pf-cc-topbar-brand", text: "PaperForge" }),
      n.createEl("span", {
        cls: "pf-cc-topbar-version",
        text:
          "v" +
          ((f = (u = this.plugin.manifest) == null ? void 0 : u.version) != null
            ? f
            : "?"),
      }));
    let a = r.createDiv({ cls: "pf-cc-topbar-center" }),
      o = [
        { id: "overview", label: s("tab_overview") || "Overview" },
        { id: "help", label: s("tab_help") || "Help" },
      ],
      l = {};
    if (
      (o.forEach((_) => {
        a.createEl("button", {
          cls:
            "pf-cc-topbar-tab" +
            (_.id === this.activeTab ? " pf-cc-topbar-tab--active" : ""),
          text: _.label,
        }).addEventListener("click", () => {
          ((this._detailReturn = null),
            (this.activeTab = _.id),
            (this._navMemory = { destination: _.id }),
            this._persistNavMemory(),
            this.display());
        });
      }),
      r
        .createDiv({ cls: "pf-cc-topbar-right" })
        .createEl("a", {
          cls: "pf-cc-topbar-ocr-link",
          text: (s("md_ocr_workspace") || "OCR Workspace") + " \u2197",
          attr: { href: "#", role: "button" },
        })
        .addEventListener("click", (_) => {
          (_.preventDefault(),
            this.app.setting.close(),
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }));
        }),
      o.forEach((_) => {
        l[_.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (_.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      (l["module-detail"] = e.createDiv({
        cls:
          "paperforge-tab-content" +
          (this.activeTab === "module-detail"
            ? " paperforge-tab-content--active"
            : ""),
      })),
      this.activeTab === "overview"
        ? this._renderOverviewTab(l.overview)
        : this.activeTab === "module-detail"
          ? this._renderModuleDetailTab(l["module-detail"])
          : this.activeTab === "help" && this._renderHelpTab(l.help),
      this._focusTargetId && this.activeTab !== "help")
    ) {
      let _ = e.querySelector(this._focusTargetId);
      if (
        (!_ &&
          this.activeTab === "overview" &&
          (_ = e.querySelector(".pf-cc-module-card")),
        _)
      ) {
        try {
          _.focus();
        } catch (h) {}
        this._focusTargetId = null;
      }
    }
    this._displayInProgress = !1;
  }
  getClient() {
    var r, n, a;
    if (this._client) return this._client;
    if (typeof ((r = this.plugin) == null ? void 0 : r.getClient) == "function")
      return ((this._client = this.plugin.getClient()), this._client);
    let e = this._getVaultBasePath(),
      t = new qe({
        vaultPath: e,
        customPythonPath:
          (a = (n = this.plugin) == null ? void 0 : n.settings) == null
            ? void 0
            : a.python_path,
        resolveRuntime: async () => this._resolveRuntimeCommand(e),
      });
    return ((this._client = new He({ transport: t })), this._client);
  }
  _startSetupJourney(e = 1, t = !1) {
    ((this._setupStage = e),
      (this._setupReinstallRequested = t),
      (this._setupOperation = "idle"),
      (this._setupFeedback = null),
      (this.plugin.settings._setup_complete = !1),
      this.plugin.saveSettings().then(() => this.display()));
  }
  _runSetupPython(e, t, r) {
    var o;
    let n = t == null ? void 0 : t.trim();
    if (!n) {
      let l = this._resolveRuntimeCommand(this._getVaultBasePath());
      n = (o = l == null ? void 0 : l.path) != null ? o : "";
    }
    if (!n) return Promise.reject(new Error("no managed runtime pointer"));
    let a = (0, de.spawn)(n, e, {
      cwd: this._getVaultBasePath(),
      env: G(),
      windowsHide: !0,
      signal: r,
    });
    return new Promise((l, c) => {
      var h;
      let p = "",
        u = !1,
        f = !1,
        _ = (g) => {
          u || ((u = !0), g ? c(g) : l());
        };
      ((h = a.stderr) == null ||
        h.on("data", (g) => {
          p += g.toString("utf-8");
        }),
        a.once("error", (g) => {
          (r != null && r.aborted) || g.name === "AbortError" ? (f = !0) : _(g);
        }),
        a.once("close", (g) => {
          f || (r != null && r.aborted) || g === null
            ? _(new DOMException("Operation was cancelled", "AbortError"))
            : _(g === 0 ? null : new Error(p || `exit code ${g}`));
        }));
    });
  }
  _installFoundation(e) {
    if (this._setupOperation === "running") return;
    ((this._setupOperation = "running"),
      (this._setupFeedback = null),
      this.display(),
      (this._runtimeAbortController = new AbortController()));
    let t = this._runtimeAbortController.signal;
    (async () => {
      var r, n, a, o, l, c;
      try {
        let p = this._getVaultBasePath(),
          u = this._ensureManagedRuntime(),
          f = await u.installOnce(this.plugin.manifest.version, t),
          _ = await u.handshake(this.plugin.manifest.version, {
            pythonPath: f.pythonPath,
            vaultPath: p,
            signal: t,
          });
        if (!_.ok)
          throw new Error((r = _.reason) != null ? r : "handshake failed");
        let h = this.plugin.settings;
        await this.plugin.saveSettings();
        let m = this.getClient().setup(
          {
            systemDir:
              ((n = h.system_dir) == null ? void 0 : n.trim()) || "System",
            resourcesDir:
              ((a = h.resources_dir) == null ? void 0 : a.trim()) ||
              "Resources",
            literatureDir:
              ((o = h.literature_dir) == null ? void 0 : o.trim()) ||
              "Literature",
            baseDir: ((l = h.base_dir) == null ? void 0 : l.trim()) || "Bases",
            zoteroData:
              ((c = h.zotero_data_dir) == null ? void 0 : c.trim()) || void 0,
            agent: h.agent_platform || "opencode",
            modular: !0,
          },
          {
            pythonExe: f.pythonPath,
            onEvent: (b) => {
              var x;
              b.event === "phase" &&
                ((this._setupFeedback = `${s("setup_installing") || "Installing"}: ${(x = b.phase) != null ? x : ""}`),
                this.display());
            },
          }
        );
        t == null || t.addEventListener("abort", () => m.stop());
        let v = await m.outcome;
        if (!v.ok) {
          if (v.cancelled) {
            ((this._setupOperation = "idle"),
              (this._setupFeedback = s("setup_install_cancelled")),
              this.display());
            return;
          }
          throw new Error(
            v.protocolFailure || `Setup failed with exit code ${v.exitCode}`
          );
        }
        ((this._setupOperation = "idle"),
          (this._setupReinstallRequested = !1),
          (this._setupFeedback = s("setup_install_complete")),
          this._probeModule("installation"),
          this._probeModule("help"),
          this.display());
      } catch (p) {
        if (
          t.aborted ||
          (typeof p == "object" && p !== null && p.name === "AbortError")
        ) {
          ((this._setupOperation = "idle"),
            (this._setupFeedback = s("setup_install_cancelled")),
            this.display());
          return;
        }
        (console.error("PaperForge runtime installation failed:", p),
          (this._setupOperation = "failed"),
          (this._setupFeedback = s("setup_install_failed")),
          this.display());
      } finally {
        this._runtimeAbortController = null;
      }
    })();
  }
  _applyLibraryConfiguration() {
    if (this._setupOperation === "running") return;
    ((this._setupOperation = "running"), (this._setupFeedback = null));
    let e = this.plugin.settings,
      t = this._getVaultBasePath(),
      r = {
        zotero_data_dir: e.zotero_data_dir,
        system_dir: e.system_dir,
        resources_dir: e.resources_dir,
        literature_dir: e.literature_dir,
        base_dir: e.base_dir,
      };
    (async () => {
      var a, o, l, c, p;
      let n = [];
      for (let [u, f] of Object.entries(r))
        f &&
          f.trim() &&
          n.push(
            Be(t, u, f.trim(), e).catch((_) => {
              console.error(`PaperForge: config set ${u} failed`, _);
            })
          );
      (await Promise.all(n).catch(() => {}), this.display());
      try {
        await this.plugin.saveSettings();
        let _ = await this.getClient().setup(
          {
            systemDir:
              ((a = e.system_dir) == null ? void 0 : a.trim()) || "System",
            resourcesDir:
              ((o = e.resources_dir) == null ? void 0 : o.trim()) ||
              "Resources",
            literatureDir:
              ((l = e.literature_dir) == null ? void 0 : l.trim()) ||
              "Literature",
            baseDir: ((c = e.base_dir) == null ? void 0 : c.trim()) || "Bases",
            zoteroData:
              ((p = e.zotero_data_dir) == null ? void 0 : p.trim()) || void 0,
            agent: e.agent_platform || "opencode",
            modular: !0,
          },
          {
            onEvent: (h) => {
              var g;
              h.event === "phase" &&
                ((this._setupFeedback = `${s("setup_library_configuring") || "Configuring"}: ${(g = h.phase) != null ? g : ""}`),
                this.display());
            },
          }
        ).outcome;
        if (!_.ok)
          throw new Error(
            _.protocolFailure || `Setup failed with exit code ${_.exitCode}`
          );
        ((this._setupOperation = "idle"),
          (this._setupFeedback = s("setup_library_configured")),
          this._attemptedProbes.add("library"),
          this._probeModule("library"),
          this.display());
      } catch (u) {
        (console.error("PaperForge library configuration failed:", u),
          (this._setupOperation = "failed"),
          (this._setupFeedback = s("setup_library_config_failed")),
          this.display());
      }
    })();
  }
  _renderOverviewTab(e) {
    var r;
    let t = this._getVaultBasePath();
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      e.createEl("h2", { text: s("header_title") || "PaperForge" }),
      e.createEl("p", { text: s("desc"), cls: "paperforge-settings-desc" }));
    for (let n of Le) {
      let a = (r = this._capabilityState) == null ? void 0 : r[n];
      if (!a) continue;
      let o =
          a.capability_state === "unknown" &&
          a.updated_at === new Date(0).toISOString(),
        l =
          a.user_state === "detection_failed" &&
          a.reason.code.endsWith(".stale");
      (o || l) &&
        !this._attemptedProbes.has(n) &&
        (this._attemptedProbes.add(n),
        n !== "maintenance" && this._probeModule(n));
    }
    this._renderControlCenter(e);
  }
  _getVaultBasePath() {
    let e = this.app.vault.adapter;
    if (e && typeof e == "object" && "basePath" in e) {
      let t = e.basePath;
      return typeof t == "string" ? t : "";
    }
    return "";
  }
  _ensureManagedRuntime() {
    var e, t, r;
    return this._managedRuntime
      ? this._managedRuntime
      : ((this._managedRuntime =
          (r =
            (t = (e = this.plugin).getManagedRuntime) == null
              ? void 0
              : t.call(e)) != null
            ? r
            : new le()),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    var n;
    let t = (n = this.plugin.settings.python_path) == null ? void 0 : n.trim();
    if (t && J.existsSync(t)) return { path: t, args: [] };
    let r = ce(this._ensureManagedRuntime().readPointer());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  _renderInstallationDetail(e) {
    var v, b, x, E, y, w, k;
    this._renderModuleDetailShell(e, "installation");
    let t =
        (b = (v = this._capabilityState) == null ? void 0 : v.installation) !=
        null
          ? b
          : Y("installation"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: s("md_foundation_overview") }),
      r.createEl("p", {
        text:
          t.user_state === "ready"
            ? s("md_foundation_ready")
            : this._getModuleConsequence("installation", t),
        cls:
          t.user_state === "ready"
            ? "pf-status-ok"
            : "setting-item-description",
      }));
    let n = r.createDiv({ cls: "pf-config" }),
      a = (S, C, A, D) => {
        let P = n.createDiv({ cls: "pf-config-row" });
        P.createEl("span", { cls: "pf-config-key", text: S });
        let L = P.createDiv({ cls: "pf-config-right" });
        (L.createEl("span", { cls: D, text: C }),
          L.createEl("span", { cls: "pf-config-value", text: A }));
      };
    a(
      s("foundation_version"),
      "\u2713",
      this.plugin.manifest.version,
      "pf-status-ok"
    );
    let o = this.app.vault.adapter.basePath,
      l =
        (E = (x = this._resolveRuntimeCommand(o)) == null ? void 0 : x.path) !=
        null
          ? E
          : this.plugin.settings.python_path || "python";
    a(
      s("foundation_python"),
      t.user_state === "ready" ? "\u2713" : "\u2014",
      l,
      t.user_state === "ready" ? "pf-status-ok" : "pf-status-checking"
    );
    let c = Re.join(o, this.plugin.settings.system_dir || "System"),
      p = J.existsSync(c);
    a(
      s("foundation_vault_structure"),
      p ? "\u2713" : "\u2717",
      p ? c : s("foundation_vault_missing"),
      p ? "pf-status-ok" : "pf-status-error"
    );
    let u =
      this.plugin.settings.zotero_data_dir &&
      J.existsSync(this.plugin.settings.zotero_data_dir);
    a(
      s("foundation_zotero"),
      u ? "\u2713" : "\u2717",
      u ? this.plugin.settings.zotero_data_dir : s("foundation_zotero_missing"),
      u ? "pf-status-ok" : "pf-status-error"
    );
    let f = !!this.plugin.settings._paddleocr_configured,
      _ = !!this.plugin.settings._vector_db_configured;
    (a(
      s("foundation_paddle_key"),
      f ? "\u2713" : "\u2717",
      f ? s("config_configured") : s("foundation_paddle_missing"),
      f ? "pf-status-ok" : "pf-status-error"
    ),
      a(
        s("foundation_openai_key"),
        _ ? "\u2713" : "\u2717",
        _ ? s("config_configured") : s("foundation_openai_missing"),
        _ ? "pf-status-ok" : "pf-status-error"
      ));
    let h = n.createDiv({ cls: "pf-config-row" });
    h.createEl("span", {
      cls: "pf-config-key",
      text:
        (y = s("md_foundation_legacy_migrate")) != null
          ? y
          : "Migrate legacy credentials",
    });
    let m = h
      .createDiv({ cls: "pf-config-right" })
      .createEl("button", { cls: "paperforge-refresh-btn", text: "Migrate" });
    ((m.title =
      "One-time migration of Obsidian SecretStorage values into the keyring (auth set)"),
      (m.onclick = () => this._migrateLegacyCredentials(m)),
      a(
        s("foundation_python_packages"),
        t.user_state === "ready" ? "\u2713" : "\u2014",
        t.user_state === "ready"
          ? s("check_bbt_ok") || "Ready"
          : (k = (w = t.reason) == null ? void 0 : w.text) != null
            ? k
            : "\u2014",
        t.user_state === "ready" ? "pf-status-ok" : "pf-status-checking"
      ),
      t.user_state !== "ready" &&
        new T.Setting(r)
          .setName(s("foundation_setup"))
          .setDesc(s("foundation_setup_desc"))
          .addButton((S) =>
            S.setButtonText(s("foundation_setup_btn"))
              .setCta()
              .onClick(() => this._startSetupJourney(1))
          ),
      new T.Setting(r)
        .setName(s("foundation_reinstall"))
        .setDesc(s("foundation_reinstall_desc"))
        .addButton((S) =>
          S.setButtonText(s("foundation_reinstall_btn"))
            .setWarning()
            .onClick(() => this._startSetupJourney(1, !0))
        ));
  }
  _renderSkillsList(e) {
    let t = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      r = this._getVaultBasePath(),
      n = this.plugin.settings.agent_platform || "opencode";
    e.createEl("h3", { text: s("md_agent_skills") });
    let a = e.createEl("div", { cls: "paperforge-desc-box" });
    (a.setText(s("feat_skills_desc")),
      a.createEl("br"),
      a.createEl("span", { text: s("feat_skills_system") }));
    let o = Re.join(r, t[n]),
      l = [],
      c = [];
    J.existsSync(o) &&
      J.readdirSync(o, { withFileTypes: !0 }).forEach((f) => {
        if (!f.isDirectory()) return;
        let _ = Re.join(o, f.name, "SKILL.md");
        if (!J.existsSync(_)) return;
        let h = J.readFileSync(_, "utf-8"),
          g = h.match(/^name:\s*(.+)$/m),
          m = h.split(`
`),
          v = m.findIndex((k) => /^description:/.test(k)),
          b = "";
        if (v >= 0) {
          let k = m[v].match(/^description:\s*(.+)$/);
          if (k && k[1] && k[1] !== ">" && k[1] !== "|-" && k[1] !== "|")
            b = k[1].trim();
          else {
            for (
              let S = v + 1;
              S < m.length && (/^\s{2,}/.test(m[S]) || m[S].trim() === "");
              S++
            )
              b += m[S].trim() + " ";
            b = b.trim();
          }
        }
        let x = h.match(/^source:\s*(.+)$/m),
          E = h.match(/^disable-model-invocation:\s*(.+)$/m),
          y = h.match(/^version:\s*(.+)$/m),
          w = {
            name: g ? g[1].trim() : f.name,
            desc: b,
            source: x ? x[1].trim() : "user",
            disabled: !!E && E[1].trim() === "true",
            version: y ? y[1].trim() : "",
            path: _,
            content: h,
            dirName: f.name,
          };
        w.source === "paperforge" ? l.push(w) : c.push(w);
      });
    let p = e.createEl("div", { cls: "paperforge-skills-box" }),
      u = (f, _, h) => {
        if (_.length === 0) return;
        let g = p.createEl("div", { cls: "paperforge-skills-group" }),
          m = g.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          v = g.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          b = m.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (m.createEl("h4", {
          text: `${f} (${_.length})`,
          cls: "paperforge-skills-subheader",
        }),
          _.forEach((y) => {
            let w = y.name + (y.version ? " v" + y.version : ""),
              k = h
                ? " [" + s("skills_system") + "]"
                : " [" + s("skills_user") + "]",
              S = y.desc || "",
              C = new T.Setting(v).setName(w + k).setDesc(S);
            ((C.settingEl.style.opacity = y.disabled ? "0.4" : "1"),
              C.addToggle((A) => {
                A.setValue(!y.disabled).onChange((D) => {
                  let P = !D,
                    K = y.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? y.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${P}`
                        )
                      : y.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${P}
`
                        );
                  (J.writeFileSync(y.path, K, "utf-8"),
                    (y.disabled = P),
                    (y.content = K),
                    (C.settingEl.style.opacity = y.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let x = h ? "system" : "user";
        ((this._skillsCollapsed[x] || !1) &&
          ((v.style.display = "none"), (b.style.transform = "rotate(-90deg)")),
          m.addEventListener("click", () => {
            (v.style.display !== "none"
              ? ((v.style.display = "none"),
                (b.style.transform = "rotate(-90deg)"))
              : ((v.style.display = ""), (b.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[x] = v.style.display === "none"));
          }));
      };
    (u(s("skills_system"), l, !0),
      u(s("skills_user"), c, !1),
      l.length === 0 &&
        c.length === 0 &&
        p.createEl("p", {
          text: s("skills_empty"),
          cls: "setting-item-description",
        }));
  }
  _renderModuleDetailTab(e) {
    (this._selectedDetailModule ||
      (this._selectedDetailModule = "installation"),
      this._selectedDetailModule === "installation"
        ? this._renderInstallationDetail(e)
        : this._selectedDetailModule === "library"
          ? this._renderLibraryDetail(e)
          : this._selectedDetailModule === "ocr"
            ? this._renderOcrDetail(e)
            : this._selectedDetailModule === "memory"
              ? this._renderMemoryDetail(e)
              : this._selectedDetailModule === "agent"
                ? this._renderAgentDetail(e)
                : ((this._selectedDetailModule = "installation"),
                  this._renderInstallationDetail(e)));
  }
  _renderLibraryDetail(e) {
    var u, f, _, h, g, m;
    this._renderModuleDetailShell(e, "library");
    let t =
        (f = (u = this._capabilityState) == null ? void 0 : u.library) != null
          ? f
          : Y("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: s("md_library_connection") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: s("md_library_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          Cr(r, {
            whatHappened:
              s("cc_module_library") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: s("library_problem_impact"),
            nextStep: s("problem_use_action"),
            impactLabel: s("problem_impact"),
            nextLabel: s("problem_next"),
            copyLabel: s("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      a = (_ = t.details) == null ? void 0 : _.paper_count,
      o = n.createDiv({ cls: "pf-module-fact" });
    (o.createEl("span", { text: s("md_library_corpus") }),
      o.createEl("span", {
        text: typeof a == "number" ? String(a) : s("metric_not_available"),
      }));
    let l =
        (m =
          (g = (h = this._capabilityState) == null ? void 0 : h.maintenance) ==
          null
            ? void 0
            : g.orphan) == null
          ? void 0
          : m.count,
      c = n.createDiv({ cls: "pf-module-fact" });
    (c.createEl("span", { text: "Orphans" }),
      c.createEl("span", {
        text: typeof l == "number" ? String(l) : s("metric_not_available"),
      }));
    let p = n.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: s("md_library_last_sync") }),
      p.createEl("span", {
        text: this.plugin._lastSyncTime || s("metric_not_available"),
      }),
      r.createEl("h3", { text: s("md_configuration") }),
      Pr(r, {
        items: [
          {
            label: s("config_zotero_dir"),
            value:
              this.plugin.settings.zotero_data_dir ||
              s("config_not_configured"),
          },
        ],
        configuredLabel: s("config_configured"),
        notConfiguredLabel: s("config_not_configured"),
        onChangeLabel: s("config_change"),
        onChange: () => this._startSetupJourney(2),
      }));
  }
  _renderOcrDetail(e) {
    var p, u, f, _, h, g, m, v, b, x, E, y, w, k;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (u = (p = this._capabilityState) == null ? void 0 : p.ocr) != null
          ? u
          : Y("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: s("md_ocr_status") }),
      t.user_state === "detection_failed" &&
        r.createEl("p", {
          cls: "pf-status-checking",
          text: s("md_status_refresh_hint"),
        }));
    let n = t.pipeline_version,
      a = t.last_pipeline_version,
      l =
        ((_ = (f = t.pipeline_version_summary) == null ? void 0 : f.stale) !=
        null
          ? _
          : 0) > 0,
      c = t.activity_state === "running";
    if (c) {
      ve(r, "checking", s("ocr_state_running"));
      let S = this.plugin._ocrProgress,
        C = r.createDiv({ cls: "pf-ocr-progress-card" });
      if (S != null && S.total) {
        let D = s("ocr_progress")
            .replace("{current}", String(S.current))
            .replace("{total}", String(S.total)),
          P = S.key ? " \u2014 " + S.key : "";
        C.createEl("span", {
          cls: "pf-detail-progress",
          text: s("ocr_state_running") + " " + D + P,
        });
        let L = C.createDiv({ cls: "pf-activity-bar" }),
          K = Math.round((S.current / S.total) * 100);
        L.createDiv({
          cls: "pf-activity-bar-fill",
          attr: {
            style: `width: ${K}%`,
            role: "progressbar",
            "aria-valuenow": String(S.current),
            "aria-valuemin": "1",
            "aria-valuemax": String(S.total),
          },
        });
      }
      let A = this.plugin.ocrProcessController;
      A.isRunning &&
        C.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: s("ocr_stop_batch"),
        }).addEventListener("click", () => void A.stop());
    } else if (l) {
      let S = n
        ? s("ocr_state_update_available").replace("{version}", n)
        : s("ocr_state_update_available").replace("{version}", "");
      (ve(r, "action_required", S),
        r.createEl("p", {
          text: s("ocr_state_update_description"),
          cls: "setting-item-description",
        }),
        r.createEl("p", {
          text: s("ocr_state_update_safety"),
          cls: "setting-item-description",
        }),
        r
          .createEl("button", {
            cls: "pf-action-btn mod-warning",
            text: s("ocr_action_re_extract"),
          })
          .addEventListener("click", () => {
            new pe(
              this.app,
              {
                title: s("ocr_modal_title"),
                effectLabel:
                  s("ocr_modal_description") +
                  " " +
                  s("ocr_state_update_safety"),
                confirmLabel: s("ocr_action_re_extract"),
                cancelLabel: s("maintenance_confirm_cancel"),
              },
              () => this._dispatchOcrAction("rebuild")
            ).open();
          }));
    } else if (t.user_state === "ready") {
      ve(r, "ready", s("cc_state_ready"));
      let S = n
        ? s("ocr_state_ready")
            .replace(
              "{count}",
              String(
                (b =
                  (v =
                    (g = (h = t.action) == null ? void 0 : h.primary) == null
                      ? void 0
                      : g.scope_count) != null
                    ? v
                    : (m = t.pipeline_version_summary) == null
                      ? void 0
                      : m.total) != null
                  ? b
                  : ""
              )
            )
            .replace("{version}", n)
        : s("ocr_state_ready_no_version").replace(
            "{count}",
            String(
              (k =
                (w =
                  (E = (x = t.action) == null ? void 0 : x.primary) == null
                    ? void 0
                    : E.scope_count) != null
                  ? w
                  : (y = t.pipeline_version_summary) == null
                    ? void 0
                    : y.total) != null
                ? k
                : ""
            )
          );
      (r.createEl("p", { text: S, cls: "pf-status-ok" }),
        j(r, {
          label: s("md_ocr_workspace"),
          onClick: () =>
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }),
        }),
        n &&
          a &&
          n !== a &&
          r
            .createDiv({ cls: "pf-ocr-update-banner" })
            .createEl("span", {
              text: s("ocr_state_update_available").replace("{version}", n),
            }));
    }
    c ||
      j(r, {
        label: s("ocr_configure_credential"),
        onClick: () => this._startSetupJourney(3),
      });
  }
  _renderAgentDetail(e) {
    var _, h;
    this._renderModuleDetailShell(e, "agent");
    let t = e.createDiv({ cls: "pf-module-body" }),
      r = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      n = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      a = this.plugin.settings.agent_platform || "opencode",
      o = Re.join(this._getVaultBasePath(), n[a]),
      l = J.existsSync(o),
      c = t.createDiv({ cls: "pf-module-facts" }),
      p = c.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: s("md_agent_platform") }),
      p.createEl("span", { text: (_ = r[a]) != null ? _ : a }));
    let u = c.createDiv({ cls: "pf-module-fact" });
    (u.createEl("span", { text: s("md_agent_deployment") }),
      u.createEl("span", {
        text: l ? s("agent_deployed") : s("agent_not_deployed"),
      }));
    let f = c.createDiv({ cls: "pf-module-fact" });
    if (
      (f.createEl("span", { text: s("agent_live_connection") }),
      f.createEl("span", { text: s("md_agent_connection_unknown") }),
      this._agentPlatformDraft === null)
    )
      j(t, {
        label: s("config_change"),
        onClick: () => {
          ((this._agentPlatformDraft = a), this.display());
        },
      });
    else {
      let g = t.createDiv({ cls: "pf-agent-config-editor" }),
        m = g.createEl("select", {
          attr: { "aria-label": s("md_agent_platform") },
        }),
        v = this.plugin.agentPlatformChoices.length
          ? this.plugin.agentPlatformChoices
          : Object.keys(r);
      for (let x of v) {
        let E = m.createEl("option", {
          text: (h = r[x]) != null ? h : x,
          attr: { value: x },
        });
        E.selected = x === this._agentPlatformDraft;
      }
      m.addEventListener("change", () => {
        this._agentPlatformDraft = m.value;
      });
      let b = g.createDiv({ cls: "pf-agent-config-actions" });
      (j(b, {
        label: s("config_save"),
        onClick: () => {
          var E;
          let x = (E = this._agentPlatformDraft) != null ? E : a;
          ((this.plugin.settings.agent_platform = x),
            Be(
              this._getVaultBasePath(),
              "agent_platform",
              x,
              this.plugin.settings
            ).catch(
              (y) =>
                new T.Notice(
                  `PaperForge: config set agent_platform failed: ${String(y)}`
                )
            ),
            this.plugin.saveSettings(),
            (this._agentPlatformDraft = null),
            this.display());
        },
      }),
        j(b, {
          label: s("config_cancel"),
          onClick: () => {
            ((this._agentPlatformDraft = null), this.display());
          },
        }),
        j(b, {
          label: s("config_verify"),
          onClick: () => {
            var y;
            let x = (y = this._agentPlatformDraft) != null ? y : a,
              E = J.existsSync(Re.join(this._getVaultBasePath(), n[x]));
            new T.Notice(
              E ? s("agent_verify_found") : s("agent_verify_missing")
            );
          },
        }));
    }
    this._renderSkillsList(t);
  }
  _memoryDbStatusText(e, t) {
    var n, a;
    let r = (a = (n = e.reason) == null ? void 0 : n.code) != null ? a : "";
    return e.user_state === "ready"
      ? s("sr_db_exists") || "Active"
      : t === "running"
        ? s("sr_db_building") || "Building"
        : t === "interrupted"
          ? s("sr_db_partial") || "Partially built"
          : t === "failed"
            ? s("sr_db_failed") || "Build failed"
            : r === "memory.db_missing"
              ? s("sr_db_missing") || "Not built"
              : r === "memory.db_corrupt"
                ? s("sr_db_corrupt") || "Corrupted"
                : r === "memory.index_stale"
                  ? s("sr_db_stale") || "Index stale"
                  : s("sr_db_missing") || "Not built";
  }
  _renderMemoryDetail(e) {
    var _e, fe, B, N, Z, I, W, F, ee, Te, at, Ut, Jt;
    this._renderModuleDetailShell(e, "memory", !1);
    let t =
        (fe = (_e = this._capabilityState) == null ? void 0 : _e.memory) != null
          ? fe
          : Y("memory"),
      r = e.createDiv({ cls: "pf-module-body" }),
      n = (N = (B = t.reason) == null ? void 0 : B.code) != null ? N : "",
      a = this.getClient(),
      o =
        typeof (a == null ? void 0 : a.isOperationActive) == "function" &&
        a.isOperationActive(),
      l = t.activity_state === "running" || o,
      c = null,
      p = "setting-item-description";
    if (
      (l
        ? ((c = (Z = t.activity_label) != null ? Z : s("cc_activity_running")),
          (p = "pf-status-ok"))
        : t.user_state === "ready"
          ? ((c = s("md_retrieval_ready")), (p = "pf-status-ok"))
          : ((c =
              (W = (I = t.reason) == null ? void 0 : I.text) != null
                ? W
                : null),
            (p = "pf-status-warn")),
      c && r.createEl("p", { text: c, cls: p }),
      l)
    )
      o &&
        j(r, {
          label: s("retrieval_stop"),
          onClick: () => {
            a.cancelActiveOperation();
          },
        });
    else if (
      (F = t.action) != null &&
      F.primary &&
      t.user_state !== "ready" &&
      t.user_state !== "not_enabled"
    ) {
      let R = t.action.primary,
        z =
          "action_" +
          ((ee = R.action_id) != null ? ee : R.verb).replace(/[.-]/g, "_"),
        ie =
          R.label ||
          (s(z) !== z
            ? s(z)
            : s("cc_action_" + R.verb) !== "cc_action_" + R.verb
              ? s("cc_action_" + R.verb)
              : s("cc_action_probe"));
      j(r, {
        label: ie,
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    }
    let u = (Te = t.details) != null ? Te : {},
      f =
        (Ut = (at = u.build_state) == null ? void 0 : at.status) != null
          ? Ut
          : "idle",
      _ = this._memoryDbStatusText(t, f),
      h = "vec0",
      g = !!u.api_key_configured,
      m = g
        ? s("api_key_set") || "Configured"
        : s("api_key_missing") || "Not configured",
      v = r.createDiv({ cls: "pf-sr-info-card" }),
      b = [
        [s("sr_db_status") || "Database", _],
        [s("sr_backend") || "Backend", h],
        [s("sr_api_key") || "API Key", m],
      ];
    for (let [R, z] of b) {
      let ie = v.createDiv({ cls: "pf-sr-info-row" });
      (ie.createEl("span", { cls: "pf-sr-info-label", text: R }),
        ie.createEl("span", { cls: "pf-sr-info-value", text: z }));
    }
    let x = !g,
      E = r.createDiv({ cls: "pf-sr-cfg" }),
      y = E.createDiv({ cls: "pf-sr-cfg-head" });
    y.createEl("span", {
      cls: "pf-sr-cfg-title",
      text: s("sr_config_label") || "\u914D\u7F6E",
    });
    let w = y.createEl("span", {
        cls: "pf-sr-cfg-icon",
        text: x ? "\u25BC" : "\u25B6",
      }),
      k = E.createDiv({ cls: "pf-sr-cfg-body" });
    ((k.style.display = x ? "" : "none"),
      y.addEventListener("click", () => {
        let R = k.style.display !== "none";
        ((k.style.display = R ? "none" : ""),
          (w.textContent = R ? "\u25B6" : "\u25BC"));
      }));
    let S = k.createDiv({ cls: "pf-sr-cfg-row" });
    S.createEl("label", {
      text: s("feat_openai_key") || "API Key",
      cls: "pf-sr-cfg-lbl",
    });
    let C = S.createEl("input", {
        cls: "pf-sr-cfg-input",
        attr: {
          type: "password",
          placeholder: g ? "\u2022\u2022\u2022\u2022" : "sk-...",
        },
      }),
      A = null;
    C.addEventListener("input", () => {
      let R = C.value;
      R &&
        (A && clearTimeout(A),
        (A = setTimeout(async () => {
          ((await this._storeVectorDbCredential(R)) &&
            ((C.value = ""),
            (C.placeholder = "\u2022\u2022\u2022\u2022"),
            (k.style.display = "none"),
            (w.textContent = "\u25B6")),
            (A = null));
        }, 600)));
    });
    let D = k.createDiv({ cls: "pf-sr-cfg-row" });
    D.createEl("label", {
      text: s("feat_api_base_url") || "API Base URL",
      cls: "pf-sr-cfg-lbl",
    });
    let P = D.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "https://api.openai.com/v1" },
    });
    ((P.value = this.plugin.settings.vector_db_api_base || ""),
      P.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_base = P.value),
          Be(
            this._getVaultBasePath(),
            "vector_db_api_base",
            P.value,
            this.plugin.settings
          ).catch(
            (R) =>
              new T.Notice(
                `PaperForge: config set vector_db_api_base failed: ${String(R)}`
              )
          ),
          this._refreshVectorDbCredentialStatus());
      }));
    let L = k.createDiv({ cls: "pf-sr-cfg-row" });
    L.createEl("label", {
      text: s("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    let K = L.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "text-embedding-3-small" },
    });
    if (
      ((K.value =
        this.plugin.settings.vector_db_api_model || "text-embedding-3-small"),
      K.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_model = K.value),
          Be(
            this._getVaultBasePath(),
            "vector_db_api_model",
            K.value,
            this.plugin.settings
          ).catch(
            (R) =>
              new T.Notice(
                `PaperForge: config set vector_db_api_model failed: ${String(R)}`
              )
          ),
          this._refreshVectorDbCredentialStatus());
      }),
      t.capability_state === "needs_action" && t.user_state !== "not_enabled")
    ) {
      let R = r.createDiv({ cls: "pf-sr-impact-box" });
      R.createEl("strong", {
        text: s("cc_badge_action_required") || "Action Required",
      });
      let z =
        ((Jt = t.reason) == null ? void 0 : Jt.text) ||
        s("sr_impact_db_missing") ||
        "Smart Retrieval needs an API key and vector index.";
      R.createEl("p", { text: z });
    }
    let X = r.createEl("details", { cls: "pf-sr-diagnostics" });
    X.createEl("summary", {
      text: s("cc_diagnostic_toggle") || "Advanced Status",
    });
    let ke = X.createDiv({ cls: "pf-sr-diagnostics-body" }),
      ne = this._getVaultBasePath(),
      Se = this.plugin.settings.vector_db_api_base || "-",
      Ce = ke.createEl("table", { cls: "pf-diag-table" }),
      ae = new Map(),
      M = (R, z) => {
        if (!ae.has(R)) {
          let Oe = Ce.createEl("tr");
          Oe.createEl("td", { cls: "pf-diag-label", text: R });
          let it = Oe.createEl("td", { cls: "pf-diag-value" });
          (ae.set(R, Oe), (it.textContent = z));
          return;
        }
        let ie = ae.get(R).children[1];
        ie.textContent = z;
      };
    (M("FTS5 Papers", "\u2026"),
      M("FTS5 Fresh", "\u2026"),
      M("Needs Rebuild", "\u2026"),
      M("", ""),
      M("Vector Backend", "vec0 (sqlite-vec)"),
      M("Vector Model", "\u2026"),
      M("Vector Mode", "\u2026"),
      M("Vector Dimension", "\u2026"),
      M("Base URL", Se),
      ne &&
        (Er(ne, this.plugin.settings)
          .then((R) => {
            var z;
            (M(
              "FTS5 Papers",
              String(
                (z = R == null ? void 0 : R.paper_count_db) != null ? z : "?"
              )
            ),
              M("FTS5 Fresh", R != null && R.fresh ? "Yes" : "Stale"),
              M("Needs Rebuild", R != null && R.needs_rebuild ? "Yes" : "No"));
          })
          .catch(() => {}),
        dt(ne, this.plugin.settings)
          .then((R) => {
            var ie, Oe, it, Wt, Zt, Gt, Qt, Xt, Yt;
            (M(
              "Vector Model",
              String((ie = R == null ? void 0 : R.model) != null ? ie : "-")
            ),
              M(
                "Vector Mode",
                String((Oe = R == null ? void 0 : R.mode) != null ? Oe : "-")
              ),
              M(
                "Body Chunks",
                String(
                  (it = R == null ? void 0 : R.body_chunk_count) != null
                    ? it
                    : 0
                )
              ),
              M(
                "Object Chunks",
                String(
                  (Wt = R == null ? void 0 : R.object_chunk_count) != null
                    ? Wt
                    : 0
                )
              ),
              M(
                "Total Chunks",
                String(
                  (Zt = R == null ? void 0 : R.total_chunks) != null ? Zt : 0
                )
              ));
            let z =
              (Gt = R == null ? void 0 : R.build_state) != null ? Gt : void 0;
            (M(
              "Build Status",
              String((Qt = z == null ? void 0 : z.status) != null ? Qt : "-")
            ),
              M(
                "Build Progress",
                `${(Xt = z == null ? void 0 : z.current) != null ? Xt : "?"}/${(Yt = z == null ? void 0 : z.total) != null ? Yt : "?"}`
              ));
          })
          .catch(() => {})),
      M("", ""),
      M("Capability State", t.capability_state),
      M("Severity", t.severity),
      M("Reason Code", n));
  }
  _dispatchModuleAction(e, t) {
    var n, a;
    let r = (n = t.action) == null ? void 0 : n.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    if (r.safety_class !== "safe" && r.confirmation_required) {
      let o =
          r.action_id === "ocr.run"
            ? s("ocr_run_confirm_title")
            : r.action_id === "embed.build"
              ? s("embed_rebuild_title")
              : r.label,
        l =
          r.action_id === "ocr.run"
            ? s("ocr_run_confirm_body")
            : r.action_id === "embed.build"
              ? s("embed_rebuild_body")
              : (a =
                    (r.replacement_facts || []).join("; ") ||
                    r.confirmation_prompt) != null
                ? a
                : s("confirmation_default_effect");
      new pe(this.app, { title: o, effectLabel: l }, () =>
        this._runAllowedDispatch(e, r, t)
      ).open();
      return;
    }
    this._runAllowedDispatch(e, r, t);
  }
  _runAllowedDispatch(e, t, r) {
    var o, l, c;
    let n = t.verb,
      a = t.action_id;
    if (n === "setup" || n === "set_config") {
      if (e === "library") this._startSetupJourney(2);
      else {
        let p =
          e === "installation" &&
          r.reason.code === "installation.version_mismatch";
        this._startSetupJourney(e === "ocr" || e === "memory" ? 3 : 1, p);
      }
      return;
    }
    if (n === "probe") {
      this._probeModule(e);
      return;
    }
    if (n === "update") {
      if (a === "foundation.update") {
        this._runUpdateAction();
        return;
      }
      (new T.Notice(
        s("update_python_manual") ||
          "Python 3.11+ upgrade requires a manual install (python.org or your package manager)."
      ),
        this._probeModule(e));
      return;
    }
    if (n === "install" && a === "memory.install_vector_deps") {
      this._startSetupJourney(3);
      return;
    }
    if (e === "library") {
      if (n === "sync" || a === "library.sync") {
        this._runManualSync();
        return;
      }
    } else if (e === "ocr") {
      if (n === "run" || a === "ocr.run") {
        this._dispatchOcrAction("run");
        return;
      }
      if (n === "rebuild_derived" || a === "ocr.rebuild_derived") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (n === "redo" || a === "ocr.redo") {
        this._dispatchOcrAction("redo");
        return;
      }
      if (n === "investigate") {
        let p = this._getVaultBasePath(),
          u = Vr(
            r.reason.code,
            r.reason.text,
            (c =
              (l = (o = r.action) == null ? void 0 : o.primary) == null
                ? void 0
                : l.scope_count) != null
              ? c
              : 0,
            p
          );
        new ft(
          this.app,
          u,
          "https://github.com/LLLin000/PaperForge/issues/new"
        ).open();
        return;
      }
    } else if (e === "memory") {
      if (n === "run" || n === "rebuild_index") {
        if (a === "embed.build")
          this._dispatchMemoryBuild("embed", "force", "embed.build");
        else if (a === "embed.resume")
          this._dispatchMemoryBuild("embed", "resume", "embed.resume");
        else if (a === "memory.build" || a === "memory.rebuild")
          this._dispatchMemoryBuild("build", void 0, a);
        else if (a === "memory.upgrade_backend") this._runBackendMigration();
        else {
          (new T.Notice(
            (s("action_unknown_pair") || "Unknown action: {verb}").replace(
              "{verb}",
              a || n
            ),
            5e3
          ),
            this._probeModule(e));
          return;
        }
        return;
      }
      if (n === "restore_backup" || a === "memory.restore_backup") {
        this._callPython(["memory", "restore-backup"], {
          timeout: 3e4,
          onClose: () => {
            this._refreshAllReadModels();
          },
        });
        return;
      }
    }
    (new T.Notice(
      (s("action_unknown_pair") || "Unknown action: {verb}").replace(
        "{verb}",
        n
      ),
      5e3
    ),
      this._probeModule(e));
  }
  _runUpdateAction() {
    let e = this._getVaultBasePath(),
      t = this._resolveRuntimeCommand(e);
    if (!t) {
      new T.Notice(s("retrieval_no_python") || "No Python runtime available");
      return;
    }
    (0, de.execFile)(
      t.path,
      [
        ...t.args,
        "-m",
        "paperforge",
        "--vault",
        e,
        "action",
        "run",
        "foundation.update",
        "--confirm",
        "foundation.update",
        "--json",
      ],
      { cwd: e, timeout: 6e5, env: G() },
      (r, n, a) => {
        (r
          ? new T.Notice(
              s("update_failed") ||
                `Update failed: ${(a == null ? void 0 : a.trim()) || r.message}`
            )
          : new T.Notice(s("update_done") || "PaperForge updated"),
          this._refreshAllReadModels());
      }
    );
  }
  _runBackendMigration() {
    this._callPython(["embed", "migrate", "--json"], {
      timeout: 6e5,
      onClose: (e, t, r) => {
        (e === 0
          ? new T.Notice(s("migrate_done") || "Backend migrated to sqlite-vec")
          : new T.Notice(
              s("migrate_failed") ||
                `Backend migration failed: ${(r == null ? void 0 : r.trim()) || "unknown error"}`
            ),
          this._refreshAllReadModels());
      },
    });
  }
  _dispatchOcrAction(e) {
    var o;
    let t = this.plugin.ocrProcessController;
    if (e === "run" && typeof this.plugin.requestOcrRun == "function") {
      this.plugin.requestOcrRun(!0);
      return;
    }
    if (t.isRunning) {
      new T.Notice(s("ocr_already_running"));
      return;
    }
    let r = {
        run: s("ocr_activity_run"),
        rebuild: s("ocr_activity_rebuild"),
        redo: s("ocr_activity_redo"),
      },
      n = (o = this._capabilityState) != null ? o : {};
    (n.ocr &&
      ((n.ocr.activity_state = "running"),
      (n.ocr.activity_label = r[e] || s("cc_activity_running")),
      (n.ocr.activity_progress = { current: 0, total: 1 })),
      (this.plugin._ocrBuffer = ""),
      (this.plugin._ocrProgress = { current: 0, total: 1, key: "" }),
      (this.plugin._ocrStderr = ""),
      (this.plugin._ocrWasStopped = !1),
      this.display());
    let a = {
      run: s("ocr_run_complete"),
      rebuild: s("ocr_rebuild_complete"),
      redo: s("ocr_redo_complete"),
    };
    t.start(e, {
      all: e === "rebuild",
      callbacks: {
        onProgress: (l, c, p) => {
          ((this.plugin._ocrProgress = { current: l, total: c, key: p }),
            n.ocr && (n.ocr.activity_progress = { current: l, total: c }),
            this.display());
        },
        onNotice: (l) => new T.Notice(l, 8e3),
      },
    })
      .then((l) => {
        if (
          (n.ocr &&
            ((n.ocr.activity_state = "idle"),
            (n.ocr.activity_label = null),
            (n.ocr.activity_progress = null)),
          l.ok)
        )
          new T.Notice(a[e] || "OCR completed");
        else if (l.stopped)
          ((this.plugin._ocrWasStopped = !1),
            new T.Notice(s("ocr_stopped_notice")));
        else {
          let c = l.failedKeys.join(", "),
            p =
              l.skippedKeys.length > 0
                ? `${c ? c + " " : ""}(${l.skippedKeys.length} skipped)`
                : c;
          new T.Notice(s("ocr_failed_notice") + (p ? ": " + p : ""), 8e3);
        }
        (this._refreshAllReadModels(), this.display());
      })
      .catch((l) => {
        (n.ocr &&
          ((n.ocr.activity_state = "idle"),
          (n.ocr.activity_label = null),
          (n.ocr.activity_progress = null)),
          new T.Notice(
            s("ocr_failed_notice") +
              ": " +
              ((l == null ? void 0 : l.message) || s("ocr_error_notice")),
            8e3
          ),
          this._refreshAllReadModels(),
          this.display());
      });
  }
  _dispatchMemoryBuild(e, t, r) {
    var f, _, h, g;
    e === "embed" && me(null, "embed");
    let n = this.getClient();
    if (!n) {
      new T.Notice(s("runtime_not_available") || "Environment unavailable");
      return;
    }
    if (
      typeof (n == null ? void 0 : n.isOperationActive) == "function" &&
      n.isOperationActive()
    ) {
      new T.Notice(s("embed_already_running") || "Operation already running");
      return;
    }
    let a = (f = this._capabilityState) != null ? f : {},
      o =
        (g =
          (h = (_ = a.memory) == null ? void 0 : _.action) == null
            ? void 0
            : h.primary) == null
          ? void 0
          : g.action_id,
      l;
    if (
      (r
        ? (l = r)
        : e === "embed"
          ? t === "resume"
            ? (l = "embed.resume")
            : t === "force"
              ? (l = "embed.build")
              : o === "embed.resume" || o === "embed.build"
                ? (l = o)
                : (l = "embed.build")
          : o === "memory.build" || o === "memory.rebuild"
            ? (l = o)
            : (l = "memory.rebuild"),
      !{
        embed: new Set(["embed.build", "embed.resume"]),
        build: new Set(["memory.build", "memory.rebuild"]),
      }[e].has(l))
    ) {
      new T.Notice(
        (s("action_unknown_pair") || "Unknown action: {verb}").replace(
          "{verb}",
          l
        )
      );
      return;
    }
    (a.memory &&
      ((a.memory.activity_state = "running"),
      (a.memory.activity_label =
        e === "embed"
          ? s("embed_activity_building") || "Building vector index\u2026"
          : "Building memory\u2026")),
      this.display());
    let p = !1,
      u = n.runAction(
        { action_id: l, scope: { kind: "all" }, confirm: l },
        {
          onEvent: (m) => {
            var v, b, x;
            if ((m.event === "cancelled" && (p = !0), m.event === "progress")) {
              let E = Number((v = m.current) != null ? v : 0),
                y = Number((b = m.total) != null ? b : 1);
              ((this.plugin._embedProgress = {
                current: E,
                total: y,
                key: String((x = m.item_id) != null ? x : ""),
              }),
                a.memory &&
                  (a.memory.activity_progress = { current: E, total: y }),
                this.display());
            }
          },
        }
      );
    (async () => {
      var m, v;
      try {
        let b = await u;
        if (
          (a.memory &&
            ((a.memory.activity_state = "idle"),
            (a.memory.activity_label = null),
            (a.memory.activity_progress = null)),
          b.ok)
        )
          new T.Notice(
            e === "embed"
              ? s("embed_build_complete")
              : s("feat_memory_rebuild_done")
          );
        else if (b.cancelled || p) new T.Notice(s("embed_build_stopped"), 8e3);
        else {
          let x =
            typeof ((m = b.payload) == null ? void 0 : m.availability_reason) ==
            "string"
              ? b.payload.availability_reason
              : `exit code ${b.exitCode}`;
          new T.Notice(
            (s("sr_build_failed_notice") || "Build failed: {detail}").replace(
              "{detail}",
              x
            ),
            8e3
          );
        }
      } catch (b) {
        (a.memory &&
          ((a.memory.activity_state = "idle"),
          (a.memory.activity_label = null),
          (a.memory.activity_progress = null)),
          new T.Notice(
            (s("sr_build_failed_notice") || "Build failed: {detail}").replace(
              "{detail}",
              (v = b == null ? void 0 : b.message) != null ? v : String(b)
            ),
            8e3
          ));
      } finally {
        (this._refreshAllReadModels(), this.display());
      }
    })();
  }
  _renderModuleDetailShell(e, t, r = !0) {
    var m, v, b, x, E, y;
    (e.classList.add("pf-module-detail"),
      e
        .createEl("button", {
          cls: "pf-back-btn",
          text: s("btn_back_to_overview"),
        })
        .addEventListener("click", () => {
          (this._detailReturn
            ? ((this.activeTab = this._detailReturn.tab),
              (this._focusTargetId = this._detailReturn.selector),
              (this._detailReturn = null))
            : ((this.activeTab = "overview"),
              (this._focusTargetId = `button.pf-cc-module-card[data-module="${t}"]`)),
            (this._selectedDetailModule = ""),
            this.display());
        }));
    let a = this._getOverviewModules(),
      o = e.createDiv({
        cls: "pf-module-detail-selector",
        attr: { role: "tablist", "aria-label": s("md_module_switcher") },
      });
    for (let w of a)
      o.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (w.id === t ? " pf-module-detail-btn--active" : ""),
        text: w.label,
        attr: { role: "tab", "aria-selected": String(w.id === t) },
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = w.id),
          (this._focusTargetId = "#pf-" + w.id + "-detail-heading"),
          this.display());
      });
    let l = e.createEl("select", {
      cls: "pf-module-switcher",
      attr: { "aria-label": s("md_module_switcher") },
    });
    for (let w of a) {
      let k = l.createEl("option", { text: w.label, attr: { value: w.id } });
      k.selected = w.id === t;
    }
    l.addEventListener("change", () => {
      ((this._selectedDetailModule = l.value),
        (this._focusTargetId = "#pf-" + l.value + "-detail-heading"),
        this.display());
    });
    let c =
        t === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (v = (m = this._capabilityState) == null ? void 0 : m[t]) != null
            ? v
            : Y(t),
      p =
        (b = c.user_state) != null
          ? b
          : c.capability_state === "ready"
            ? "ready"
            : "action_required",
      u = e.createDiv({
        cls: "pf-module-summary",
        attr: { "aria-live": "polite" },
      }),
      f = u.createDiv({ cls: "pf-module-summary-header" });
    (f.createEl("h2", {
      cls: "pf-module-summary-name pf-module-detail-heading",
      text: this._getUserModuleName(t),
      attr: { id: "pf-" + t + "-detail-heading", tabindex: "-1" },
    }),
      ve(f, p, this._getUserStateLabel(p)),
      u.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(t, c),
      }),
      c.activity_state === "running" &&
        Sr(u, {
          label: s("cc_activity_running"),
          progress: c.activity_progress,
        }));
    let _ = (x = c.action) == null ? void 0 : x.primary;
    if (r && _ && p !== "ready" && t !== "agent") {
      let w =
          "action_" +
          ((E = _.action_id) != null ? E : _.verb).replace(/[.-]/g, "_"),
        k = s(w),
        S =
          k !== w
            ? k
            : s("cc_action_" + _.verb) !== "cc_action_" + _.verb
              ? s("cc_action_" + _.verb)
              : s("cc_action_probe");
      j(u, {
        label: S,
        loading: c.activity_state === "running",
        onClick: () => this._dispatchModuleAction(t, c),
      });
    }
    let h = u.createEl("details", { cls: "pf-module-diagnostics" });
    h.createEl("summary", { text: s("advanced_diagnostics") });
    let g = h.createDiv({ cls: "pf-module-diagnostics-body" });
    (g.createEl("div", { text: s("cc_diag_module") + ": " + c.module }),
      g.createEl("div", {
        text: s("cc_diag_state") + ": " + this._getUserStateLabel(p),
      }),
      g.createEl("div", { text: s("cc_diag_severity") + ": " + c.severity }),
      g.createEl("div", {
        text: s("cc_diag_activity") + ": " + c.activity_state,
      }),
      g.createEl("div", { text: s("cc_diag_reason") + ": " + c.reason.code }),
      g.createEl("div", {
        text: s("cc_diag_ttl") + ": " + c.ttl_seconds + "s",
      }));
    for (let w of (y = c.notices) != null ? y : [])
      g.createEl("div", { text: w.message });
    g.createEl("div", {
      text:
        s("cc_diag_updated") + ": " + new Date(c.updated_at).toLocaleString(),
    });
  }
  _renderHelpTab(e) {
    (e.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: s("help_eyebrow") || "help",
    }),
      e.createEl("h1", { cls: "pf-cc-title", text: s("help_title") || "Help" }),
      e.createEl("p", {
        cls: "pf-cc-lede",
        text:
          s("help_lede") ||
          "Open the relevant module, or copy a diagnostic for support.",
      }));
    let t = e.createEl("p", {
        cls: "pf-help-loading",
        text: "Loading help content\u2026",
      }),
      r = Rt(this.app),
      n = "https://api.github.com/repos/LLLin000/PaperForge/contents/docs/help",
      a = ["guide", "faq", "support"],
      o = this;
    Promise.all(
      a.map((l) =>
        fetch(`${n}/${r}/${l}.md`)
          .then((c) => (c.ok ? c.json() : Promise.reject()))
          .then((c) => {
            let p = atob(c.content.replace(/\n/g, "")),
              u = new Uint8Array(p.length);
            for (let f = 0; f < p.length; f++) u[f] = p.charCodeAt(f);
            return new TextDecoder().decode(u);
          })
          .then((c) => ({ name: l, text: c }))
          .catch(() => ({ name: l, text: "" }))
      )
    )
      .then((l) => {
        t.remove();
        for (let { name: c, text: p } of l) {
          if (!p) continue;
          let u = p.match(/^#\s+(.+)/m),
            f = u ? u[1] : c,
            _ = p.replace(/^#\s+.+(\r?\n|$)/, "").trim(),
            h = e.createEl("details", {
              cls: "pf-help-section",
              attr: c === "support" ? { open: "true" } : {},
            });
          h.createEl("summary", { cls: "pf-help-section-title", text: f });
          let g = h.createDiv({ cls: "pf-help-section-body" });
          c === "support"
            ? (T.MarkdownRenderer.render(o.app, _, g, "", o.plugin),
              g
                .createEl("button", {
                  cls: "pf-help-diagnostic-btn",
                  text: s("help_copy") || "Copy Support Diagnostic",
                })
                .addEventListener("click", () => o._buildAndCopyDiagnostic()))
            : T.MarkdownRenderer.render(o.app, _, g, "", o.plugin);
        }
      })
      .catch(() => {
        t.setText(s("help_load_error") || "Failed to load help content.");
      });
  }
  _callPython(e, t) {
    let r = this.app.vault.adapter.basePath,
      n = this._resolveRuntimeCommand(r);
    if (!n)
      return (
        t && t.onClose && t.onClose(1, "", "No python runtime available"),
        null
      );
    let a = [...n.args, "-m", "paperforge", "--vault", r, ...e],
      o = (t == null ? void 0 : t.credentialType) && !(t != null && t.env),
      l = (u) => {
        let f = (0, de.spawn)(n.path, a, { cwd: r, env: u, windowsHide: !0 });
        return (
          t.onData && f.stdout.on("data", t.onData),
          t.onStderr && f.stderr.on("data", t.onStderr),
          t.onError && f.on("error", t.onError),
          f.on("close", t.onClose),
          f
        );
      },
      c = (u) => {
        (0, de.execFile)(
          n.path,
          a,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: u },
          (f, _, h) => {
            t && t.onClose && t.onClose(f ? 1 : 0, _, h);
          }
        );
      };
    if (o)
      return (
        me(null, t.credentialType).then((u) => {
          t && t.stream ? l(u) : c(u);
        }),
        null
      );
    let p = (t == null ? void 0 : t.env) || G();
    return t && t.stream ? l(p) : (c(p), null);
  }
  _runManualSync() {
    var n, a;
    let e = (n = this.app.vault.adapter.basePath) != null ? n : "",
      t = this.getClient();
    if (!t) {
      new T.Notice(s("runtime_not_available") || "Environment unavailable");
      return;
    }
    let r = (a = this._capabilityState) != null ? a : {};
    (r.library &&
      ((r.library.activity_state = "running"),
      (r.library.activity_label = "Syncing library\u2026")),
      (this.plugin._autoSyncRunning = !0),
      (this._libraryRunning = !0),
      this.display(),
      (async () => {
        let o = 1;
        try {
          let l = await t.sync();
          ((o = (l == null ? void 0 : l.ok) === !1 ? 1 : 0),
            o === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime),
              Ie(JSON.stringify(l), {
                vaultPath: e,
                resolveCommand: (c) => this._resolveRuntimeCommand(c),
              })));
        } catch (l) {
          new T.Notice(
            `Sync failed: ${l instanceof Error ? l.message : String(l)}`,
            8e3
          );
        } finally {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            this._refreshAllReadModels(o),
            this._refreshSnapshots(e),
            Ye(this.app, this.plugin, e));
        }
      })());
  }
  _refreshSnapshots(e) {
    let t = this._resolveRuntimeCommand(e);
    if (!t) return;
    let r = [
      ...t.args,
      "-m",
      "paperforge",
      "--vault",
      e,
      "runtime-health",
      "--json",
    ];
    ((this._refreshPending = !0),
      (0, de.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        () => {
          var o, l, c, p, u, f;
          this._refreshPending = !1;
          let n = (o = this._capabilityState) == null ? void 0 : o.memory,
            a = (l = this._capabilityState) == null ? void 0 : l.embed;
          ((this._memoryStatusText =
            n && (p = (c = n.reason) == null ? void 0 : c.text) != null
              ? p
              : null),
            (this._embedStatusText =
              a && (f = (u = a.reason) == null ? void 0 : u.text) != null
                ? f
                : null),
            this.display());
        }
      ));
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = Wr.default.versions || [];
    for (let a of t) {
      let o = e.createEl("div", { cls: "paperforge-release-card" }),
        l = o.createEl("div", { cls: "paperforge-release-header" });
      if (
        (l.createEl("strong", { text: `v${a.version} \u2014 ${a.title}` }),
        l.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${a.date})`,
        }),
        a.breaking_or_migration && a.breaking_or_migration.length > 0)
      ) {
        let c = o.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let p of a.breaking_or_migration)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (a.new_features && a.new_features.length > 0) {
        let c = o.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let p of a.new_features)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (a.fixes && a.fixes.length > 0) {
        let c = o.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let p of a.fixes)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (a.recommended_actions && a.recommended_actions.length > 0) {
        let c = o.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let p of a.recommended_actions)
          c.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${p}`,
          });
      }
    }
    (e.createEl("h3", { text: "\u4F7F\u7528\u624B\u518C" }),
      e
        .createEl("div", { cls: "paperforge-manual-links" })
        .createEl("a", {
          text: "\u2192 \u67E5\u770B\u5B8C\u6574\u4F7F\u7528\u624B\u518C\uFF08GitHub\uFF09",
          href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
        })
        .setAttr("target", "_blank"));
  }
  _initCapabilityState() {
    let e = this.plugin.settings.capabilityState;
    ((this._capabilityState = pr(e != null ? e : {}, Le)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var c, p, u, f, _;
    if (this._probing.has(e)) return;
    this._probing.add(e);
    let r = (c = this._capabilityState) == null ? void 0 : c[e],
      n = {
        schema_version: 2,
        module: e,
        capability_state:
          (p = r == null ? void 0 : r.capability_state) != null ? p : "unknown",
        activity_state: "running",
        activity_label: "Probing...",
        activity_progress: null,
        severity: "unknown",
        reason: { code: `${e}.probing`, text: `Checking ${e} status...` },
        action: { primary: Ze(e) },
        notices: (u = r == null ? void 0 : r.notices) != null ? u : [],
        user_state: "checking",
        capability_kind:
          e === "installation" || e === "library" ? "required" : "optional",
        maintenance_eligible: !1,
        user_visible_failure: !1,
        user_impact: null,
        updated_at: new Date().toISOString(),
        ttl_seconds: (f = r == null ? void 0 : r.ttl_seconds) != null ? f : 0,
      };
    this._updateCapabilityEnvelope(e, n);
    let a = this._getVaultBasePath();
    if (!this._resolveRuntimeCommand(a)) {
      if ((this._probing.delete(e), e === "installation")) {
        let h = {
          schema_version: 2,
          module: "installation",
          capability_state: "unknown",
          activity_state: "idle",
          activity_label: null,
          activity_progress: null,
          severity: "error",
          reason: {
            code: "installation.no_python",
            text: "No Python found. Run the Setup Wizard to install the managed runtime.",
          },
          action: { primary: Et() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !0,
          user_impact: "PaperForge cannot run without Python.",
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, h);
      } else this._updateCapabilityEnvelope(e, Ge(e));
      return;
    }
    this.getClient()
      .probe(e, {
        expectedVersion:
          e === "installation"
            ? (_ = this.plugin.manifest) == null
              ? void 0
              : _.version
            : void 0,
        lastOperationExitCode:
          e === "library" && t != null && t !== 0 ? t : void 0,
      })
      .then((h) => {
        (this._probing.delete(e),
          ct(h, e)
            ? this._updateCapabilityEnvelope(e, h)
            : (console.warn(
                `[PaperForge] Probe ${e}: invalid envelope schema`,
                h
              ),
              this._updateCapabilityEnvelope(e, Ge(e))));
      })
      .catch((h) => {
        var g, m, v;
        if (
          (this._probing.delete(e),
          e === "installation" &&
            (((g = h.message) != null && g.includes("runtime not ready")) ||
              ((m = h.message) != null &&
                m.includes("no managed runtime pointer")) ||
              ((v = h.message) != null && v.includes("not ready"))))
        ) {
          let b = {
            schema_version: 2,
            module: "installation",
            capability_state: "unknown",
            activity_state: "idle",
            activity_label: null,
            activity_progress: null,
            severity: "error",
            reason: {
              code: "installation.no_python",
              text: "No Python found. Run the Setup Wizard to install the managed runtime.",
            },
            action: { primary: Et() },
            notices: [],
            user_state: "setup_required",
            capability_kind: "required",
            maintenance_eligible: !1,
            user_visible_failure: !0,
            user_impact: "PaperForge cannot run without Python.",
            updated_at: new Date().toISOString(),
            ttl_seconds: 60,
          };
          this._updateCapabilityEnvelope(e, b);
        } else
          (console.warn(`[PaperForge] Probe ${e} failed:`, h.message),
            this._updateCapabilityEnvelope(e, Ge(e)));
      });
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    (Tr(r, t) && this._lastKnownState.set(e, Ar(t)),
      e === "installation" &&
        t.user_state === "ready" &&
        (this._setupReinstallRequested = !1),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        new T.Notice(s("cc_notice_refreshed"), 3e3),
      this._displayInProgress || this.display());
  }
  _ccBadgeKey(e, t) {
    return e.activity_state === "running"
      ? "cc_badge_checking"
      : e.severity === "ok"
        ? "cc_badge_ok"
        : e.severity === "error" && t === "installation"
          ? "cc_badge_setup"
          : e.severity === "warning" || e.severity === "error"
            ? "cc_badge_attention"
            : "cc_badge_pending";
  }
  _sevClass(e, t) {
    return t === "running"
      ? "checking"
      : e === "error"
        ? "error"
        : e === "warning"
          ? "warn"
          : e === "unknown"
            ? "unknown"
            : "ok";
  }
  _localizeReason(e, t) {
    let r = "cc_reason_" + e.replace(/\./g, "_"),
      n = s(r);
    if (n !== r) return n.replace("{module}", t);
    let o = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      l = s(o);
    return l === o ? null : l.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      a = this._sevClass(n.severity, n.activity_state),
      o = je._REAL_PROBE.has(t),
      l = je._NAVIGABLE.has(t),
      c = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${s("cc_module_" + t)} \u2014 ${s(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = c.createEl("div", { cls: "pf-cc-card-header" }),
      u = p.createEl("div", { cls: "pf-cc-card-name-area" });
    if (l) {
      let w =
          t === "installation"
            ? s("module_detail_open_installation")
            : t === "library"
              ? s("module_detail_open_library")
              : t === "ocr"
                ? s("module_detail_open_ocr")
                : t === "memory"
                  ? s("module_detail_open_memory")
                  : t === "help"
                    ? s("module_detail_open_help")
                    : s("md_select_installation"),
        k = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: s("cc_module_" + t),
          attr: { "data-module": t, "aria-label": w },
        });
      (k.addEventListener("click", () => this._handleCardNavigation(t)),
        k.addEventListener("keydown", (S) => {
          (S.key === "Enter" || S.key === " ") &&
            (S.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: s("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${a}`,
      text: s(this._ccBadgeKey(n, t)),
    });
    let f;
    if (!o)
      f = s("cc_reason_placeholder").replace("{module}", s("cc_module_" + t));
    else {
      let w = this._localizeReason(n.reason.code, t);
      f = w != null ? w : n.reason.text;
    }
    if (
      (c.createEl("div", { cls: "pf-cc-card-reason", text: f }),
      n.activity_state === "running" && n.activity_label)
    ) {
      let w = c.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (w.createEl("span", { text: n.activity_label }),
        n.activity_progress && n.activity_progress.total > 0)
      ) {
        let k = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          C = w
            .createEl("div", {
              cls: "pf-cc-card-progress",
              attr: {
                role: "progressbar",
                "aria-valuenow": String(n.activity_progress.current),
                "aria-valuemin": "0",
                "aria-valuemax": String(n.activity_progress.total),
              },
            })
            .createEl("div", { cls: "pf-cc-card-progress-fill" });
        C.style.width = k + "%";
      }
    }
    let _ = c.createEl("div", { cls: "pf-cc-card-footer" });
    if (o && n.action.primary && !lr(n)) {
      let w = cr(n),
        S =
          w.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      _.createEl("button", {
        cls: S,
        text: w.label,
        attr: { "aria-label": w.label },
      }).addEventListener("click", () => {
        w.kind === "setup"
          ? this._startSetupJourney(1)
          : this._dispatchModuleAction(t, n);
      });
    }
    let h = c.createEl("details", { cls: "pf-cc-card-diagnostic" });
    h.createEl("summary", { text: s("cc_diagnostic_toggle") });
    let g = h.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      m = s("cc_state_" + n.capability_state) || n.capability_state,
      v = s("cc_severity_" + n.severity) || n.severity,
      b = s("cc_activity_" + n.activity_state) || n.activity_state,
      x;
    try {
      x = new Date(n.updated_at).toLocaleString();
    } catch (w) {
      x = n.updated_at;
    }
    (g.createEl("div", { text: `${s("cc_diag_module")}: ${n.module}` }),
      g.createEl("div", { text: `${s("cc_diag_state")}: ${m}` }),
      g.createEl("div", { text: `${s("cc_diag_severity")}: ${v}` }),
      g.createEl("div", { text: `${s("cc_diag_activity")}: ${b}` }));
    let E = g.createEl("div");
    E.appendText(s("cc_diag_reason") + ": " + f + " ");
    let y = E.createEl("code", { text: n.reason.code });
    (g.createEl("div", {
      text: `${s("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      g.createEl("div", { text: `${s("cc_diag_updated")}: ${x}` }));
  }
  _handleCardNavigation(e) {
    (e === "help"
      ? ((this.activeTab = "help"),
        (this._selectedDetailModule = ""),
        (this._focusTargetId = "div.pf-open-module-btn[data-module=help]"))
      : ((this.activeTab = "module-detail"),
        (this._selectedDetailModule = e),
        (this._focusTargetId = "#pf-" + e + "-detail-heading")),
      this.display());
  }
  _renderControlCenter(e) {
    var S, C, A, D;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (S = this._capabilityState) != null ? S : {};
    (t.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: s("cc_eyebrow") || "control center",
    }),
      t.createEl("h1", {
        cls: "pf-cc-title",
        text: s("cc_title") || "Your literature pipeline",
      }),
      t.createEl("p", {
        cls: "pf-cc-lede",
        text:
          s("cc_lede") ||
          "See what is working and what needs attention across your pipeline.",
      }));
    let n = (C = r.installation) != null ? C : Y("installation"),
      a = (A = r.library) != null ? A : Y("library"),
      o = n.user_state === "ready",
      l = a.user_state === "ready",
      c = o && l,
      p = [n, a].some((P) => P.user_state === "checking"),
      u = Object.values(r).filter(
        (P) =>
          P.user_state &&
          P.user_state !== "ready" &&
          P.user_state !== "not_enabled"
      ).length,
      f = t.createEl("div", { cls: "pf-cc-summary" }),
      _ = c ? "ready" : p ? "checking" : "attention",
      h = c
        ? s("cc_badge_ready") || "Ready"
        : p
          ? s("cc_badge_checking") || "Checking"
          : s("cc_badge_attention") || "Needs attention";
    f.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${_}`,
      text: h,
    });
    let g = f.createDiv({ cls: "pf-cc-summary-copy" }),
      m = c
        ? s("cc_summary_ready")
        : p
          ? s("cc_summary_checking")
          : this.plugin.settings._setup_complete === !1
            ? s("cc_summary_incomplete")
            : s("cc_summary_attention"),
      v = c
        ? s("cc_summary_ready_body")
        : p
          ? s("cc_summary_checking_body")
          : this.plugin.settings._setup_complete === !1
            ? s("cc_summary_incomplete_body")
            : s("cc_summary_attention_body");
    (g.createEl("strong", { text: m }),
      g.createEl("span", { cls: "caption", text: v }));
    let b = f.createDiv({ cls: "pf-cc-summary-meta" }),
      x = b.createEl("span");
    (x.createEl("strong", { text: String(u) }),
      x.appendText(" " + (s("cc_needs_attention") || "item needs attention")));
    let E = Object.values(r)
      .map((P) => P.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    (b.createEl("span", {
      text: E
        ? (s("cc_last_checked") || "Checked just now: ") +
          new Date(E).toLocaleString()
        : s("cc_checked_pending") || "Not checked yet",
    }),
      b
        .createEl("button", {
          cls: "pf-cc-summary-refresh",
          text: s("cc_refresh_btn") || "Refresh status",
        })
        .addEventListener("click", () => this._refreshAllModules()));
    let w = t.createDiv({ cls: "pf-cc-section-head" });
    (w.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: s("cc_modules_header") || "modules",
    }),
      w.createEl("span", {
        cls: "caption",
        text:
          s("cc_optional_note") ||
          "Optional modules do not affect core readiness.",
      }));
    let k = t.createDiv({ cls: "pf-cc-module-list" });
    for (let [P, L] of this._getOverviewModules().entries()) {
      let K =
        L.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (D = r[L.id]) != null
            ? D
            : Y(L.id);
      this._renderOverviewCard(k, L.id, L.label, K, P + 1);
    }
  }
  _getAgentPlaceholderEnvelope() {
    var a;
    let e = this.plugin.settings.agent_platform || "opencode",
      t = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      r = Re.join(
        this._getVaultBasePath(),
        (a = t[e]) != null ? a : t.opencode,
        "paperforge",
        "SKILL.md"
      ),
      n = J.existsSync(r);
    return {
      schema_version: 2,
      module: "agent",
      capability_state: n ? "ready" : "needs_action",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: n ? "ok" : "warning",
      reason: {
        code: n ? "agent.skills_deployed" : "agent.skills_not_deployed",
        text: n
          ? "PaperForge Skills are deployed for the selected platform."
          : "PaperForge Skills have not been deployed for the selected platform.",
      },
      action: { primary: null },
      notices: [],
      user_state: n ? "ready" : "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: !1,
      user_visible_failure: !1,
      user_impact: null,
      updated_at: new Date().toISOString(),
      ttl_seconds: 300,
    };
  }
  _renderOverviewCard(e, t, r, n, a) {
    var c, p;
    let o = e.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn",
      attr: {
        "data-module": t,
        "aria-label": r + " \u2014 " + this._getUserStateLabel(n.user_state),
        role: "button",
        tabindex: "0",
      },
    });
    ((o.style.cursor = "pointer"),
      o.createEl("span", {
        cls: "pf-cc-num",
        text: String(a).padStart(2, "0"),
      }),
      o.createEl("span", { cls: "pf-cc-card-name", text: r }),
      ve(o, n.user_state, this._getUserStateLabel(n.user_state)),
      o.createEl("span", {
        cls: "pf-cc-card-sentence",
        text: this._getModuleConsequence(t, n),
      }));
    let l =
      n.user_state === "ready" &&
      (p = (c = n.action) == null ? void 0 : c.primary) != null &&
      p.scope_count &&
      n.action.primary.scope_count > 1
        ? (s("cc_metric_papers") || "Papers: ") + n.action.primary.scope_count
        : n.updated_at && n.updated_at !== new Date(0).toISOString()
          ? (s("cc_last_checked") || "") +
            new Date(n.updated_at).toLocaleString()
          : "";
    (o.createEl("span", { cls: "pf-cc-card-metric", text: l }),
      o.createEl("span", { cls: "pf-cc-card-arrow", text: "\u2192" }),
      o.addEventListener("click", () => this._handleCardNavigation(t)));
  }
  _getUserStateLabel(e) {
    return s("cc_badge_" + e);
  }
  _getModuleConsequence(e, t) {
    var p, u, f;
    let r =
        (p = t.user_state) != null
          ? p
          : t.capability_state === "ready"
            ? "ready"
            : "action_required",
      n = "cc_consequence_" + e + "_" + r,
      a = s(n);
    if (a && a !== n) return a;
    let o = this._localizeReason(
      (f = (u = t.reason) == null ? void 0 : u.code) != null ? f : "",
      this._getUserModuleName(e)
    );
    if (o) return o;
    let l = "cc_consequence_" + r,
      c = s(l);
    return c !== l ? c : s("cc_consequence_default");
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Le) {
      let r = this._capabilityState[t];
      r && St(r) && ((this._capabilityState[t] = kt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    this._refreshAllReadModels();
  }
  _refreshAllReadModels(e) {
    var r;
    kr();
    let t = (r = this.app.vault.adapter.basePath) != null ? r : "";
    if (!t) {
      this._probing.clear();
      return;
    }
    this._probing.clear();
    for (let n of Le) this._probing.add(n);
    wr(t, this.plugin.settings)
      .then((n) => {
        var c, p, u, f, _;
        this._probing.clear();
        for (let [h, g] of Object.entries((c = n.modules) != null ? c : {}))
          ct(g, h) && this._updateCapabilityEnvelope(h, g);
        e != null && e !== 0 && this._probeModule("library", e);
        let a = ((p = n.modules) != null ? p : {}).maintenance,
          o = (u = a == null ? void 0 : a.orphan) != null ? u : {},
          l = (f = o.count) != null ? f : 0;
        (l > 0 &&
          !this._lastOrphanCount &&
          this._openOrphanModal((_ = o.orphans) != null ? _ : []),
          (this._lastOrphanCount = l));
      })
      .catch(() => {
        (this._probing.clear(), this.display());
      });
  }
  _openOrphanModal(e) {
    var a;
    let t = (a = this.app.vault.adapter) == null ? void 0 : a.basePath;
    if (!t) return;
    let r = this._resolveRuntimeCommand(t);
    if (!r) {
      new T.Notice(s("next_action_runtime_unavailable"));
      return;
    }
    let n = { path: r.path, extraArgs: [...r.args], source: "auto-detected" };
    new Xe(this.app, e, t, n).open();
  }
  _buildAndCopyDiagnostic() {
    var a, o, l;
    let e =
        (o = (a = this.plugin.manifest) == null ? void 0 : a.version) != null
          ? o
          : "unknown",
      t = Or(
        (l = this._capabilityState) != null ? l : {},
        this._lastKnownState
      ),
      n = Rr({ pluginVersion: e, modules: t });
    Fr(n, () => {
      new T.Notice(s("support_diagnostic_copied"), 3e3);
    });
  }
  _persistNavMemory() {
    ((this.plugin.settings._navMemory = { ...this._navMemory }),
      this.plugin.saveSettings());
  }
  _renderSetupJourney(e) {
    this.plugin.settings._setup_journey_started !== !0 &&
      ((this.plugin.settings._setup_journey_started = !0),
      this.plugin.saveSettings());
    let t = e.createDiv({ cls: "pf-setup-journey" });
    (t.createEl("h2", { text: s("setup_welcome") }),
      t.createEl("p", { text: s("setup_desc"), cls: "pf-setup-desc" }));
    let r = [
        s("setup_stage_1"),
        s("setup_stage_2"),
        s("setup_stage_3"),
        s("setup_stage_4"),
      ],
      n = t.createDiv({
        cls: "pf-setup-progress",
        attr: { "aria-label": s("setup_progress") },
      });
    r.forEach((o, l) => {
      n.createEl("span", {
        cls:
          "pf-setup-step" +
          (l + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (l + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(l + 1) + ". " + o,
        attr: { "aria-current": l + 1 === this._setupStage ? "step" : "false" },
      });
    });
    let a = t.createDiv({ cls: "pf-setup-body" });
    this._setupStage === 1
      ? this._renderSetupStageFoundation(a)
      : this._setupStage === 2
        ? this._renderSetupStageLibrary(a)
        : this._setupStage === 3
          ? this._renderSetupStageOptionals(a)
          : this._renderSetupStageReview(a);
  }
  _renderSetupStageFoundation(e) {
    var l, c;
    let t =
      (c = (l = this._capabilityState) == null ? void 0 : l.installation) !=
      null
        ? c
        : Y("installation");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("installation") &&
      (this._attemptedProbes.add("installation"),
      this._probeModule("installation")),
      e.createEl("h3", { text: s("setup_foundation_title") }),
      e.createEl("p", { text: s("setup_foundation_desc") }));
    let n = e.createDiv({ cls: "pf-setup-field" });
    (n.createEl("label", { text: s("setup_foundation_python") }),
      n.createEl("span", {
        cls: "caption",
        text: s("setup_foundation_python_hint"),
      }));
    let a = n.createEl("input", {
      cls: "pf-setup-input",
      attr: { type: "text", placeholder: "python" },
    });
    ((a.value = this.plugin.settings.python_path || ""),
      a.addEventListener("input", () => {
        ((this.plugin.settings.python_path = a.value.trim()),
          this._debouncedSave());
      }),
      ve(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? s("setup_ready")
            : this._getModuleConsequence("installation", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: s("setup_installing"),
          })
        : (this._setupFeedback &&
            e.createEl("p", {
              cls:
                this._setupOperation === "failed"
                  ? "pf-setup-warn"
                  : "pf-setup-ok",
              text: this._setupFeedback,
            }),
          t.user_state !== "ready" &&
          (this._setupReinstallRequested ||
            t.reason.code === "installation.version_mismatch")
            ? (e.createEl("p", {
                cls: "pf-setup-warn",
                text: s("setup_reinstall_notice"),
              }),
              j(e, {
                label: s("foundation_reinstall_btn"),
                onClick: () => this._installFoundation(!0),
              }))
            : (t.user_state !== "ready" || this._setupOperation === "failed") &&
              j(e, {
                label: s("setup_foundation_install_btn"),
                onClick: () => this._installFoundation(!1),
              })));
    let o = e.createDiv({ cls: "pf-setup-nav" });
    (this._setupOperation === "running"
      ? j(o, {
          label: s("setup_nav_cancel"),
          onClick: () => {
            var p;
            (p = this._runtimeAbortController) == null || p.abort();
          },
        })
      : j(o, {
          label: s("setup_nav_later"),
          onClick: () => {
            ((this._setupOperation = "idle"),
              (this._setupFeedback = null),
              (this._setupStage = 1),
              (this.activeTab = "overview"),
              (this._setupJourneyDismissedForSession = !0),
              this.display());
          },
        }),
      j(o, {
        label: s("setup_nav_continue"),
        disabled: t.user_state !== "ready",
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 2),
            this.display());
        },
      }));
  }
  _renderSetupStageLibrary(e) {
    var w, k;
    let t =
      (k = (w = this._capabilityState) == null ? void 0 : w.library) != null
        ? k
        : Y("library");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("library") &&
      (this._attemptedProbes.add("library"), this._probeModule("library")),
      e.createEl("h3", { text: s("setup_library_title") }),
      e.createEl("p", { text: s("setup_library_desc") }),
      ve(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? s("setup_library_ready")
            : this._getModuleConsequence("library", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: s("setup_library_configuring"),
          })
        : this._setupFeedback &&
          e.createEl("p", {
            cls:
              this._setupOperation === "failed"
                ? "pf-setup-warn"
                : "pf-setup-ok",
            text: this._setupFeedback,
          }));
    let n = e.createDiv({ cls: "pf-setup-library-form" });
    n.createEl("p", {
      cls: "pf-setup-form-intro",
      text: s("setup_library_config_desc"),
    });
    let a = (S, C, A, D) => {
      let P = S.createDiv({ cls: "pf-setup-field" });
      (P.createEl("label", { text: C }),
        D && P.createEl("span", { cls: "caption", text: D }));
      let L = P.createEl("input", {
        cls: "pf-setup-input",
        attr: { type: "text" },
      });
      ((L.value = this.plugin.settings[A] || ""),
        L.addEventListener("input", () => {
          ((this.plugin.settings[A] = L.value.trim()), this._debouncedSave());
        }));
    };
    (a(
      n,
      s("field_zotero_data"),
      "zotero_data_dir",
      s("setup_library_zotero_hint")
    ),
      n.createEl("h4", { text: s("setup_library_folder_heading") }));
    let o = n.createDiv({ cls: "pf-setup-folder-grid" });
    (a(o, s("dir_system"), "system_dir"),
      a(o, s("dir_resources"), "resources_dir"),
      a(o, s("dir_notes"), "literature_dir"),
      a(o, s("dir_base"), "base_dir"));
    let l = n.createEl("button", {
      cls: "pf-setup-verify",
      text: s("setup_library_verify"),
      attr: { type: "button" },
    });
    ((l.disabled = this._setupOperation === "running"),
      l.addEventListener("click", () => this._applyLibraryConfiguration()));
    let c = e.createDiv({ cls: "pf-setup-import" });
    c.createEl("h4", { text: s("setup_bbt_title") || "BBT JSON Export" });
    let p = this.app.vault.adapter.basePath,
      u = (Ke(), rr(Jr)).resolveVaultPaths(p);
    c.createEl("p", {
      cls: "pf-setup-form-intro",
      text:
        s("setup_bbt_desc") ||
        "Export your Zotero library as Better BibTeX JSON into the folder below. Enable 'Keep updated' for automatic re-exports.",
    });
    let f = c.createDiv({ cls: "pf-setup-path-row" });
    (f.createEl("span", {
      cls: "pf-setup-path-label",
      text: s("setup_bbt_path") || "Exports folder:",
    }),
      f.createEl("code", { cls: "pf-setup-path-value", text: u.exportsDir }),
      f
        .createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: s("setup_bbt_copy") || "Copy",
        })
        .addEventListener("click", () => {
          (navigator.clipboard.writeText(u.exportsDir),
            new T.Notice(s("setup_bbt_copied") || "Path copied"));
        }));
    let h = c.createEl("details", { cls: "pf-setup-guide" });
    h.createEl("summary", {
      cls: "pf-setup-guide-summary",
      text: s("setup_bbt_guide") || "How to export from Zotero \u2192",
    });
    let g = h.createDiv({ cls: "pf-setup-guide-body" }),
      m =
        "https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/help/images",
      v = [
        {
          img: "bbt-plugin-installed.jpg",
          title: s("setup_bbt_step1") || "1. Install Better BibTeX",
          desc:
            s("setup_bbt_step1_desc") ||
            "In Zotero, go to Tools \u2192 Add-ons, search for Better BibTeX and install it. If you cannot find it, download from: https://github.com/retorquere/zotero-better-bibtex/releases/tag/v9.0.50",
        },
        {
          img: "bbt-export-dialog.jpg",
          title: s("setup_bbt_step2") || "2. Export with auto-update",
          desc:
            s("setup_bbt_step2_desc") ||
            "Right-click your library or collection \u2192 Export Library\u2026 \u2192 choose 'Better BibTeX JSON' format. Check 'Keep updated'.",
        },
        {
          img: "bbt-save-dialog.jpg",
          title: s("setup_bbt_step3") || "3. Save to exports folder",
          desc:
            s("setup_bbt_step3_desc") ||
            "Point the export destination to the folder above. Once saved, click 'Detect' below.",
        },
      ];
    for (let S of v) {
      let C = g.createDiv({ cls: "pf-setup-guide-step" });
      (C.createEl("strong", { text: S.title }),
        C.createEl("p", { text: S.desc }),
        C.createEl("img", {
          attr: {
            src: m + "/" + S.img,
            alt: S.title,
            loading: "lazy",
            onerror: "this.style.display='none'",
          },
        }).addClass("pf-setup-guide-img"));
    }
    let b = c.createDiv({ cls: "pf-setup-detect-row" }),
      x = b.createEl("span", { cls: "pf-setup-detect-status" }),
      E = e.createDiv({ cls: "pf-setup-nav" }),
      y = () => {
        try {
          J.existsSync(u.exportsDir) ||
            J.mkdirSync(u.exportsDir, { recursive: !0 });
          let S = J.readdirSync(u.exportsDir).filter((A) =>
            A.endsWith(".json")
          );
          S.length === 0
            ? x.setText(s("setup_bbt_no_files") || "No JSON files found.")
            : x.setText(
                "\u2713 " + (s("setup_bbt_found") || "Found: ") + S.join(", ")
              );
          let C = E.querySelector(".pf-action-btn:last-child");
          if (C) {
            let A =
              S.length === 0 ||
              t.user_state !== "ready" ||
              this._setupOperation === "running";
            ((C.disabled = A),
              C.classList.toggle("pf-action-btn--disabled", A));
          }
        } catch (S) {}
      };
    (b
      .createEl("button", {
        cls: "pf-btn pf-btn-primary",
        text: s("setup_bbt_detect") || "Detect",
      })
      .addEventListener("click", y),
      j(E, {
        label: s("setup_nav_back"),
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 1),
            this.display());
        },
      }),
      j(E, {
        label: s("setup_nav_continue"),
        disabled: !0,
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 3),
            this.display());
        },
      }),
      y());
  }
  async _migrateLegacyCredentials(e) {
    var c, p;
    let t = this._getVaultBasePath(),
      r = this._resolveRuntimeCommand(t);
    if (!r || !t) {
      new T.Notice("Runtime not ready \u2014 cannot migrate credentials");
      return;
    }
    let { migrateLegacySecret: n, isAllowlistedCommand: a } =
        await Promise.resolve().then(() => (At(), _r)),
      o = {
        spawn: (u, f, _) => (0, de.spawn)(u, f, _),
        pythonPath: r.path,
        pythonArgs: r.args,
        vaultPath: t,
        env: G(),
      };
    e.disabled = !0;
    let l = [];
    for (let u of ["ocr", "embedding"]) {
      let f = await n(u, this.app.secretStorage, o, {
        baseUrl: (c = this.plugin.settings.vector_db_api_base) != null ? c : "",
        model: (p = this.plugin.settings.vector_db_api_model) != null ? p : "",
      });
      f.migrated.length && l.push(`${u}: migrated`);
      for (let _ of f.warnings) l.push(_);
    }
    ((e.disabled = !1),
      l.length === 0
        ? new T.Notice("No legacy credentials found in SecretStorage")
        : l.forEach((u) => new T.Notice(u, 6e3)),
      this._refreshVectorDbCredentialStatus(),
      this._refreshAllReadModels());
  }
  _refreshVectorDbCredentialStatus() {
    let e = this._getVaultBasePath();
    e &&
      vr(e, this.plugin.settings)
        .then((t) => {
          t !== this.plugin.settings._vector_db_configured &&
            ((this.plugin.settings._vector_db_configured = t),
            this.plugin.saveSettings());
        })
        .catch(() => {});
  }
  async _storeVectorDbCredential(e) {
    return (await this._authSetSecret("embedding", e))
      ? ((this.plugin.settings._vector_db_configured = !0),
        (this.plugin.settings.vector_db_api_key = ""),
        (this.plugin.settings._migration_warnings = Array.isArray(
          this.plugin.settings._migration_warnings
        )
          ? this.plugin.settings._migration_warnings.filter(
              (r) => r !== "vector_db_api_key"
            )
          : []),
        await this.plugin.saveSettings(),
        this.display(),
        !0)
      : !1;
  }
  async _storeSetupSecret(e, t) {
    return e === "vector-db-api-key"
      ? this._storeVectorDbCredential(t)
      : !t || !(await this._authSetSecret("ocr", t))
        ? !1
        : ((this.plugin.settings._paddleocr_configured = !0),
          (this.plugin.settings.paddleocr_api_key = ""),
          await this.plugin.saveSettings(),
          !0);
  }
  _authSetSecret(e, t) {
    let r = this._getVaultBasePath(),
      n = this._resolveRuntimeCommand(r);
    return !n || !t
      ? Promise.resolve(!1)
      : new Promise((a) => {
          let o = (0, de.spawn)(
              n.path,
              [
                ...n.args,
                "-m",
                "paperforge",
                "--vault",
                r,
                "auth",
                "set",
                e,
                "--stdin",
                "--replace",
                "--json",
              ],
              {
                cwd: r,
                windowsHide: !0,
                stdio: ["pipe", "pipe", "pipe"],
                env: G(),
              }
            ),
            l = "";
          (o.stdout.on("data", (c) => (l += String(c))),
            o.on("error", () => a(!1)),
            o.on("close", (c) => {
              try {
                let p = JSON.parse(l);
                a(c === 0 && (p == null ? void 0 : p.ok) === !0);
              } catch (p) {
                a(!1);
              }
            }),
            o.stdin.write(t),
            o.stdin.end());
        });
  }
  _renderSetupStageOptionals(e) {
    var n;
    (e.createEl("h3", { text: s("setup_optionals_title") }),
      e.createEl("p", { text: s("setup_optionals_desc") }));
    let t = [
      { id: "ocr", label: s("cc_module_ocr"), desc: s("setup_opt_ocr_desc") },
      {
        id: "memory",
        label: s("cc_module_memory"),
        desc: s("setup_opt_memory_desc"),
      },
      {
        id: "agent",
        label: s("cc_module_agent"),
        desc: s("setup_opt_agent_desc"),
      },
    ];
    for (let a of t) {
      let o = e.createDiv({ cls: "pf-setup-optional" }),
        l = o.createEl("input", {
          attr: { type: "checkbox", id: "pf-setup-opt-" + a.id },
        });
      ((l.checked = this._setupOptionals[a.id]),
        l.addEventListener("change", () => {
          ((this._setupOptionals[a.id] = l.checked), this.display());
        }));
      let c =
          a.id === "ocr"
            ? !!this.plugin.settings._paddleocr_configured
            : a.id === "memory"
              ? !!this.plugin.settings._vector_db_configured
              : !0,
        p = o.createDiv({ cls: "pf-setup-optional-copy" });
      (p.createEl("label", {
        attr: { for: "pf-setup-opt-" + a.id },
        text: a.label,
        cls: "pf-setup-optional-label",
      }),
        p.createEl("div", { text: a.desc, cls: "pf-setup-optional-desc" }));
      let u = p.createEl("span", {
        cls: "pf-setup-optional-state",
        text: c ? s("config_configured") : s("config_not_configured"),
      });
      if (!l.checked) continue;
      let f = o.createDiv({ cls: "pf-setup-optional-config" });
      if (a.id === "ocr") {
        (f.createEl("label", { text: s("field_paddleocr") }),
          f.createEl("p", { cls: "caption", text: s("ocr_privacy_warning") }));
        let _ = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._paddleocr_configured
              ? "\u2022\u2022\u2022\u2022"
              : s("field_paddleocr"),
          },
        });
        f.createEl("button", {
          cls: "pf-setup-verify",
          text: s("config_save"),
          attr: { type: "button" },
        }).addEventListener("click", () => {
          this._storeSetupSecret("paddleocr-api-key", _.value).then((g) => {
            (u.setText(
              g ? s("setup_optional_saved") : s("setup_optional_save_failed")
            ),
              g && (_.value = ""));
          });
        });
      } else if (a.id === "memory") {
        (f.createEl("label", { text: s("feat_openai_key") }),
          f.createEl("p", { cls: "caption", text: s("feat_openai_key_desc") }));
        let _ = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._vector_db_configured
              ? "\u2022\u2022\u2022\u2022"
              : "sk-...",
          },
        });
        f.createEl("label", { text: s("feat_api_model") });
        let h = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_model ||
              "text-embedding-3-small",
          },
        });
        (h.addEventListener("change", () => {
          ((this.plugin.settings.vector_db_api_model = h.value.trim()),
            this.plugin.saveSettings(),
            this._refreshVectorDbCredentialStatus());
        }),
          f.createEl("label", { text: s("feat_api_base_url") }));
        let g = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_base ||
              "https://api.openai.com/v1",
          },
        });
        (g.addEventListener("change", () => {
          ((this.plugin.settings.vector_db_api_base = g.value.trim()),
            this.plugin.saveSettings(),
            this._refreshVectorDbCredentialStatus());
        }),
          f
            .createEl("button", {
              cls: "pf-setup-verify",
              text: s("config_save"),
              attr: { type: "button" },
            })
            .addEventListener("click", () => {
              this._storeSetupSecret("vector-db-api-key", _.value).then((v) => {
                (u.setText(
                  v
                    ? s("setup_optional_saved")
                    : s("setup_optional_save_failed")
                ),
                  v && (_.value = ""));
              });
            }));
      } else {
        (f.createEl("label", { text: s("feat_agent_platform") }),
          f.createEl("p", {
            cls: "caption",
            text: s("feat_agent_platform_desc"),
          }));
        let _ = f.createEl("select"),
          h = {
            opencode: "OpenCode",
            claude: "Claude Code",
            codex: "Codex",
            cursor: "Cursor",
            windsurf: "Windsurf",
            github_copilot: "GitHub Copilot",
            gemini: "Gemini CLI",
          },
          g = this.plugin.agentPlatformChoices.length
            ? this.plugin.agentPlatformChoices
            : Object.keys(h);
        for (let m of g) {
          let v = _.createEl("option", {
            text: (n = h[m]) != null ? n : m,
            attr: { value: m },
          });
          v.selected = m === this.plugin.settings.agent_platform;
        }
        _.addEventListener("change", () => {
          ((this.plugin.settings.agent_platform = _.value),
            Be(
              this._getVaultBasePath(),
              "agent_platform",
              _.value,
              this.plugin.settings
            ).catch(
              (m) =>
                new T.Notice(
                  `PaperForge: config set agent_platform failed: ${String(m)}`
                )
            ),
            this.plugin.saveSettings(),
            u.setText(s("setup_optional_saved")));
        });
      }
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (j(r, {
      label: s("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      j(r, {
        label: s("setup_nav_continue"),
        onClick: () => this._refreshSetupReadiness(),
      }));
  }
  _refreshSetupReadiness() {
    this._setupStage = 4;
    for (let e of ["installation", "library"])
      (this._attemptedProbes.add(e), this._probeModule(e));
    this.display();
  }
  _renderSetupStageReview(e) {
    var p, u;
    e.createEl("h3", { text: s("setup_review_title") });
    let t = (p = this._capabilityState) == null ? void 0 : p.installation,
      r = (u = this._capabilityState) == null ? void 0 : u.library,
      n = (t == null ? void 0 : t.user_state) === "ready",
      a = (r == null ? void 0 : r.user_state) === "ready",
      o =
        (t == null ? void 0 : t.user_state) === "checking" ||
        (r == null ? void 0 : r.user_state) === "checking";
    (e.createEl("p", {
      text: n
        ? s("setup_ready")
        : o
          ? s("setup_review_checking")
          : s("cc_consequence_setup_required"),
      cls: n ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: a
          ? s("setup_library_ready")
          : o
            ? s("setup_review_checking")
            : s("cc_consequence_setup_required"),
        cls: a ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let l = Object.entries(this._setupOptionals)
      .filter(([, f]) => f)
      .map(([f]) => this._getUserModuleName(f));
    e.createEl("p", {
      text:
        l.length > 0
          ? s("setup_review_selected") + l.join(", ")
          : s("setup_no_optionals"),
    });
    let c = e.createDiv({ cls: "pf-setup-nav" });
    (j(c, {
      label: s("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      (!n || !a) &&
        j(c, {
          label: s("setup_review_recheck"),
          disabled: o,
          onClick: () => this._refreshSetupReadiness(),
        }),
      j(c, {
        label: s("setup_nav_complete"),
        disabled: !n || !a,
        onClick: () => this._completeSetup(),
      }),
      (!n || !a) &&
        e.createEl("p", {
          text: o ? s("setup_review_checking") : s("setup_incomplete_warn"),
          cls: "pf-setup-warn",
        }));
  }
  _completeSetup() {
    ((this.plugin.settings._setup_complete = !0),
      this.plugin.saveSettings().then(() => this.display()));
  }
  _restoreNavMemory() {
    let e = this.plugin.settings._navMemory;
    e != null &&
      e.destination &&
      ["overview", "help"].includes(e.destination) &&
      ((this.activeTab = e.destination),
      (this._navMemory = { destination: e.destination }),
      this._focusTargetId ||
        ((this._focusTargetId = null),
        (this._detailReturn = null),
        (this._setupView = "overview")));
  }
  hide() {
    ((this._setupJourneyDismissedForSession = !1), super.hide());
  }
};
((je._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
])),
  (je._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "help",
  ])));
var ht = je;
var Gr = require("child_process");
var Vn = `PAPERFORGE_STOP
`,
  Zr = 500;
function Un(d, i) {
  var t, r, n;
  if (d === "run") return ["ocr", "run", ...((t = i.keys) != null ? t : [])];
  if (d === "redo") return ["ocr", "redo", ...((r = i.keys) != null ? r : [])];
  let e = (n = i.keys) != null ? n : [];
  return e.length > 0 ? ["ocr", "rebuild", ...e] : ["ocr", "rebuild", "--all"];
}
var mt = class {
  constructor(i) {
    this._opts = i;
    this._child = null;
    this._stopRequested = !1;
    this._parser = new $e();
    this._stderr = "";
  }
  get isRunning() {
    return this._child !== null;
  }
  stop() {
    var i;
    if (this._child) {
      this._stopRequested = !0;
      try {
        (i = this._child.stdin) == null || i.write(Vn);
      } catch (e) {}
    }
  }
  start(i, e = {}) {
    if (this.isRunning)
      return Promise.reject(new Error("OCR is already running"));
    let t = this._opts.resolveCommand();
    return t != null && t.path
      ? this._opts.needsCredential(i)
        ? this._opts
            .resolveEnv()
            .then((r) => this._spawn(i, e, t, r))
            .catch((r) =>
              Promise.reject(
                new Error(
                  `OCR credential unavailable: ${r instanceof Error ? r.message : String(r)}`
                )
              )
            )
        : this._spawn(i, e, t, {})
      : Promise.reject(new Error("No Python runtime available"));
  }
  _spawn(i, e, t, r) {
    var h, g, m, v, b, x;
    let n = (h = e.callbacks) != null ? h : {};
    ((this._stopRequested = !1),
      (this._parser = new $e()),
      (this._stderr = ""));
    let o = ((g = this._opts.spawnFn) != null ? g : Gr.spawn)(
      t.path,
      [...t.args, "-m", "paperforge", ...Un(i, e)],
      {
        cwd: this._opts.vaultPath,
        shell: !1,
        windowsHide: !0,
        env: { ...process.env, ...r },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
    this._child = o;
    let l = [],
      c = [],
      p = [],
      u = (() => {
        let E = !1;
        return (y, w, k, S) => {
          var C;
          E ||
            ((E = !0),
            (this._child = null),
            this._stderr.trim() &&
              ((C = n.onNotice) == null ||
                C.call(n, this._stderr.trim().slice(-Zr))),
            f({
              ok: k,
              exitCode: y,
              stopped: w,
              successKeys: l,
              failedKeys: c,
              skippedKeys: p,
              protocolFailure: S,
            }));
        };
      })(),
      f,
      _ = new Promise((E) => {
        f = E;
      });
    return (
      (m = o.stdout) == null || m.setEncoding("utf-8"),
      (v = o.stdout) == null ||
        v.on("data", (E) => {
          let y = this._parser.feed(E);
          for (let w of y) this._handleEvent(w, n, l, c, p);
        }),
      (b = o.stderr) == null || b.setEncoding("utf-8"),
      (x = o.stderr) == null ||
        x.on("data", (E) => {
          this._stderr = (this._stderr + E).slice(-Zr);
        }),
      o.on("error", (E) => {
        var y;
        ((y = n.onNotice) == null ||
          y.call(n, `OCR process error: ${E.message}`),
          u(null, this._stopRequested, !1));
      }),
      o.on("close", (E) => {
        var C;
        this._parser.finishEOF();
        let y = this._parser.protocolFailure;
        y &&
          ((C = n.onNotice) == null ||
            C.call(n, `OCR stream protocol failure: ${y}`));
        let w = this._stopRequested || E === 130,
          k = c.length > 0 || p.length > 0 || !!y;
        u(E, w, !w && !k && (E === 0 || E === null), y);
      }),
      _
    );
  }
  _handleEvent(i, e, t, r, n) {
    var a, o, l, c, p, u, f, _, h, g;
    switch (i.event) {
      case "progress":
        (c = e.onProgress) == null ||
          c.call(
            e,
            (a = i.current) != null ? a : 0,
            (o = i.total) != null ? o : 1,
            (l = i.item_id) != null ? l : ""
          );
        break;
      case "item_result":
        (i.status === "ok"
          ? t.push((p = i.item_id) != null ? p : "")
          : i.status === "failed"
            ? r.push((u = i.item_id) != null ? u : "")
            : i.status === "skipped" &&
              n.push({
                key: (f = i.item_id) != null ? f : "",
                reason: "backend_skip",
              }),
          (g = e.onResult) == null ||
            g.call(
              e,
              (_ = i.item_id) != null ? _ : "",
              (h = i.status) != null ? h : ""
            ));
        break;
      default:
        break;
    }
  }
};
var O = require("obsidian"),
  te = V(require("fs")),
  Ae = V(require("path")),
  Ee = require("child_process");
Ke();
var tt = V(require("path"));
function Qr(d) {
  if (!d) return null;
  let i = tt.dirname(d);
  for (;;) {
    let e = tt.basename(i);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = tt.dirname(i);
    if (r === i) break;
    i = r;
  }
  return null;
}
var $ = V(require("fs")),
  ue = V(require("path"));
Ke();
function rt(d) {
  return we(d).ocrDir;
}
function Yr(d, i) {
  let e = ue.join(rt(d), i, "versions", "manifest.json");
  try {
    if (!$.existsSync(e)) return null;
    let t = $.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let n = r,
        a = n.versions,
        o = n.current;
      if (Array.isArray(a) && o && typeof o == "object" && "label" in o)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function Jn(d) {
  let i = rt(d);
  try {
    return $.existsSync(i)
      ? $.readdirSync(i, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function nt(d, i) {
  let e = Yr(d, i);
  return e ? { versions: e.versions, currentLabel: e.current.label } : null;
}
function qt(d) {
  let i = Jn(d),
    e = [];
  for (let t of i) {
    let r = Yr(d, t);
    if (!r) continue;
    let n = r.versions.map((o) => o.label),
      a = 0;
    for (let o of n) {
      let l = ue.join(rt(d), t, "versions", o, "fulltext.md");
      try {
        $.existsSync(l) && (a += $.statSync(l).size);
      } catch (c) {}
    }
    e.push({
      key: t,
      title: t.replace(/_/g, " "),
      versions: r.versions,
      currentLabel: r.current.label,
      totalSize: a,
    });
  }
  return (e.sort((t, r) => t.title.localeCompare(r.title)), e);
}
function yt(d, i, e, t = "") {
  let r = rt(d),
    n = ue.join(r, i, "versions", e, "fulltext.md"),
    a = ue.join(r, i, "render"),
    o = ue.join(a, "fulltext.md");
  try {
    return $.existsSync(n)
      ? ($.existsSync(a) || $.mkdirSync(a, { recursive: !0 }),
        $.copyFileSync(n, o),
        Kt(r, i, {
          label: e,
          restored_at: new Date().toISOString(),
          version_created_at: t,
        }),
        !0)
      : !1;
  } catch (l) {
    return !1;
  }
}
function Kt(d, i, e) {
  try {
    let t = ue.join(d, i, "meta.json"),
      r = $.existsSync(t) ? JSON.parse($.readFileSync(t, "utf-8")) : {};
    ((r.restore_provenance = e),
      $.writeFileSync(t, JSON.stringify(r, null, 2), "utf-8"));
  } catch (t) {}
}
function en(d, i, e, t) {
  var _;
  let r = rt(d),
    n = ue.join(r, i, "versions", e, "fulltext.md"),
    a = ue.join(r, i, "versions", t, "fulltext.md"),
    o = "",
    l = "";
  try {
    $.existsSync(n) && (o = $.readFileSync(n, "utf-8"));
  } catch (h) {}
  try {
    $.existsSync(a) && (l = $.readFileSync(a, "utf-8"));
  } catch (h) {}
  let c = Xr(o),
    p = Xr(l),
    u = Math.max(c.length, p.length),
    f = [];
  for (let h = 0; h < u; h++) {
    let g = h < c.length ? c[h] : "",
      m = h < p.length ? p[h] : "",
      v =
        (_ = (g || m).split(`
`)[0]) != null
          ? _
          : "",
      b = v.startsWith("## ") ? v.replace(/^##\s+/, "") : "",
      x = "unchanged";
    (!g && m
      ? (x = "added")
      : g && !m
        ? (x = "removed")
        : g !== m && (x = "changed"),
      x !== "unchanged" &&
        f.push({
          paragraphIndex: h,
          heading: b,
          type: x,
          oldText: g || void 0,
          newText: m || void 0,
        }));
  }
  return f;
}
function Xr(d) {
  let i = d.split(`
`),
    e = [],
    t = [];
  for (let r of i)
    if (r.startsWith("## ") && t.length > 0)
      (e.push(
        t
          .join(
            `
`
          )
          .trim()
      ),
        (t = [r]));
    else if (r.trim() === "" && t.length > 0) {
      let n = t
        .join(
          `
`
        )
        .trim();
      n && (e.push(n), (t = []));
    } else t.push(r);
  if (t.length > 0) {
    let r = t
      .join(
        `
`
      )
      .trim();
    r && e.push(r);
  }
  return e;
}
var H = require("obsidian"),
  U = V(require("fs")),
  Q = V(require("path"));
Ke();
function Wn(d, i) {
  var e;
  return i
    ? ((e = i.flags) != null && e.version_old) || i.ocr === "stale"
      ? "update_available"
      : i.ocr === "missing" && d === "done"
        ? "pending"
        : i.ocr === "failed"
          ? "failed"
          : i.ocr === "incomplete"
            ? "done_incomplete"
            : i.ocr === "unknown" && d === "done"
              ? "unknown"
              : d
    : d;
}
var bt = 100;
var Ve = class extends H.ItemView {
  constructor(e, t) {
    super(e);
    this.plugin = t;
    this.papers = [];
    this.filter = "all";
    this.versionFilter = null;
    this.selectedKey = null;
    this.checkedKeys = new Set();
    this.running = !1;
    this.progress = {
      current: 0,
      total: 0,
      paperKey: "",
      phase: "",
      itemStatus: "",
    };
    this.globalActivity = { state: "idle", label: "", current: 0, total: 0 };
    this.actionDescriptors = new Map();
    this.pendingActionDescriptors = new Set();
    this._client = null;
    this._searchQuery = "";
    this._page = 1;
    this._runningMode = null;
  }
  static async open(e) {
    let t = e.app.workspace.getLeavesOfType(De);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getLeaf("tab");
    r &&
      (await r.setViewState({ type: De, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
  getViewType() {
    return De;
  }
  getDisplayText() {
    return s("ocr_ws_title");
  }
  getIcon() {
    return "scan-text";
  }
  async onOpen() {
    (await this._loadPapers(), this._render());
  }
  _getClient() {
    var e;
    if (this._client) return this._client;
    if (typeof ((e = this.plugin) == null ? void 0 : e.getClient) != "function")
      return null;
    try {
      let t = this.plugin.getClient();
      t && (this._client = t);
    } catch (t) {
      return null;
    }
    return this._client;
  }
  async _loadPapers() {
    var p,
      u,
      f,
      _,
      h,
      g,
      m,
      v,
      b,
      x,
      E,
      y,
      w,
      k,
      S,
      C,
      A,
      D,
      P,
      L,
      K,
      X,
      ke,
      ne,
      Se,
      Ce,
      ae,
      M,
      _e,
      fe,
      B,
      N,
      Z;
    this.actionDescriptors.clear();
    let e = this._getClient();
    if (!e) {
      ((this.globalActivity = {
        state: "unknown",
        label: s("runtime_not_available") || "Environment unavailable",
        current: 0,
        total: 0,
      }),
        (this.papers = []),
        (this.selectedKey = null),
        this.checkedKeys.clear(),
        (this._page = 1),
        (u = (p = this.containerEl) == null ? void 0 : p.children) != null &&
          u[1] &&
          this._refreshTable());
      return;
    }
    let [t, r, n] = await Promise.all([
        e.probe("lineage").catch(() => null),
        e.probe("ocr").catch(() => null),
        e.queryOcrPapers().catch(() => []),
      ]),
      a = t,
      o = r;
    this.globalActivity = {
      state:
        (o == null ? void 0 : o.activity_state) === "running"
          ? "running"
          : o
            ? "idle"
            : "unknown",
      label: (f = o == null ? void 0 : o.activity_label) != null ? f : "",
      current:
        (h =
          (_ = o == null ? void 0 : o.activity_progress) == null
            ? void 0
            : _.current) != null
          ? h
          : 0,
      total:
        (m =
          (g = o == null ? void 0 : o.activity_progress) == null
            ? void 0
            : g.total) != null
          ? m
          : 0,
    };
    let l = new Map(this.papers.map((I) => [I.key, I])),
      c = (v = a == null ? void 0 : a.papers) != null ? v : {};
    this.papers = [];
    for (let I of n) {
      let W = I.key;
      if (!W) continue;
      let F = l.get(W),
        ee = c[W],
        Te =
          (x =
            (b = ee == null ? void 0 : ee.details) == null
              ? void 0
              : b.ocr_execution) == null
            ? void 0
            : x.local_status,
        at =
          Te === "running" || Te === "processing"
            ? "processing"
            : Te === "queued"
              ? "queued"
              : Wn(
                  (y =
                    (E = I.status) != null
                      ? E
                      : F == null
                        ? void 0
                        : F.status) != null
                    ? y
                    : "pending",
                  ee
                );
      this.papers.push({
        key: W,
        title: (w = I.title) != null ? w : W,
        status: at,
        pipelineVersion:
          (S =
            (k = I.version) != null
              ? k
              : F == null
                ? void 0
                : F.pipelineVersion) != null
            ? S
            : "",
        lastRun:
          (A =
            (C = I.finished_at) != null ? C : F == null ? void 0 : F.lastRun) !=
          null
            ? A
            : "",
        hasBackup: (D = F == null ? void 0 : F.hasBackup) != null ? D : !1,
        authors:
          (L = (P = I.authors) != null ? P : F == null ? void 0 : F.authors) !=
          null
            ? L
            : "",
        year:
          I.year != null
            ? String(I.year)
            : (K = F == null ? void 0 : F.year) != null
              ? K
              : "",
        pages:
          I.pages != null
            ? String(I.pages)
            : (X = F == null ? void 0 : F.pages) != null
              ? X
              : "",
        backupCount: (ke = F == null ? void 0 : F.backupCount) != null ? ke : 0,
        canRedo:
          (Se =
            (ne = I.can_redo) != null ? ne : F == null ? void 0 : F.canRedo) !=
          null
            ? Se
            : !1,
        canRebuild:
          (ae =
            (Ce = I.can_rebuild) != null
              ? Ce
              : F == null
                ? void 0
                : F.canRebuild) != null
            ? ae
            : !1,
        recommendedAction:
          (_e =
            (M = I.recommended_action) != null
              ? M
              : F == null
                ? void 0
                : F.recommendedAction) != null
            ? _e
            : "",
        fulltextPath:
          (B =
            (fe = I.fulltext_path) != null
              ? fe
              : F == null
                ? void 0
                : F.fulltextPath) != null
            ? B
            : "",
        ocrFinishedAt:
          (Z =
            (N = I.finished_at) != null
              ? N
              : F == null
                ? void 0
                : F.ocrFinishedAt) != null
            ? Z
            : "",
      });
    }
    ((this._page = 1), this._refreshTable());
  }
  _render() {
    let e = this.containerEl.children[1];
    (e.empty(),
      e.addClass("pf-ocr-workspace"),
      this._renderHeader(e),
      this._renderActivity(e),
      this._renderToolbar(e),
      this._renderTable(e),
      this._renderBatchBar(e),
      this.selectedKey && this._renderDetail(e));
  }
  _refreshTable() {
    let e = this.containerEl.children[1],
      t = this._filteredPapers(),
      r = e.querySelector(".pf-ocr-ws-toolbar-count");
    r &&
      (r.innerHTML = s("ocr_ws_showing")
        .replace("{count}", String(t.length))
        .replace("{total}", String(this.papers.length)));
    let n = e.querySelector(".pf-ocr-ws-table");
    if (n) {
      let c = n.querySelector("tbody");
      (c && c.remove(), this._buildTableRows(n, this._currentPagePapers(t)));
    } else {
      let c = e.createDiv({ cls: "pf-ocr-ws-viewport" });
      this._buildTableBody(c, this._currentPagePapers(t));
    }
    let a = e.querySelector(".pf-ocr-ws-pagination");
    (a && a.remove(), this._renderPagination(e, t));
    let o = e.querySelector(".pf-ocr-ws-batchbar");
    (o && o.remove(), this._renderBatchBar(e));
    let l = e.querySelector(".pf-ocr-ws-detail");
    (l && l.remove(), this.selectedKey && this._renderDetail(e));
  }
  _renderHeader(e) {
    let t = e.createDiv({ cls: "pf-ocr-ws-header" });
    (t.createEl("h1", { text: s("ocr_ws_title") }),
      t.createEl("p", { cls: "pf-ocr-ws-lede", text: s("ocr_ws_lede") }));
  }
  _ensureActionDescriptor(e) {
    var r, n;
    if (this.actionDescriptors.has(e) || this.pendingActionDescriptors.has(e))
      return;
    let t = this._getClient();
    if (!t) {
      (this.actionDescriptors.set(e, {
        action_id: e,
        availability: "unavailable",
        availability_reason:
          s("runtime_not_available") || "Environment unavailable",
      }),
        (n = (r = this.containerEl) == null ? void 0 : r.children) != null &&
          n[1] &&
          this._render());
      return;
    }
    (this.pendingActionDescriptors.add(e),
      t
        .describeAction(e)
        .then((a) => {
          (a == null ? void 0 : a.action_id) === e &&
            this.actionDescriptors.set(e, a);
        })
        .catch(() => {
          this.actionDescriptors.set(e, {
            action_id: e,
            availability: "unavailable",
          });
        })
        .finally(() => {
          var a, o;
          (this.pendingActionDescriptors.delete(e),
            (o = (a = this.containerEl) == null ? void 0 : a.children) !=
              null &&
              o[1] &&
              this._render());
        }));
  }
  _isActionAvailable(e) {
    var t;
    return (
      ((t = this.actionDescriptors.get(e)) == null
        ? void 0
        : t.availability) === "available"
    );
  }
  _actionAvailabilityTitle(e, t) {
    let r = this.actionDescriptors.get(e);
    return (r && r.availability !== "available" && r.availability_reason) || t;
  }
  _renderActivity(e) {
    var m;
    let t = this.running,
      r = !t && this.globalActivity.state === "running";
    if (!t && !r) return;
    let n = t
        ? this.progress
        : {
            current: this.globalActivity.current,
            total: this.globalActivity.total,
            paperKey: "",
            phase: "",
            itemStatus: "",
          },
      a = e.createDiv({
        cls: "pf-ocr-ws-activity pf-active",
        attr: { "aria-live": "polite" },
      }),
      o = a.createDiv({ cls: "pf-ocr-ws-activity-head" }),
      l = o.createDiv({ cls: "pf-ocr-ws-activity-title" });
    l.setText(
      t
        ? s("ocr_ws_processing")
        : this.globalActivity.label || s("ocr_ws_processing")
    );
    let c = n.paperKey;
    if (c) {
      let v = this.papers.find((b) => b.key === c);
      v && l.createEl("span").setText((m = v.title) != null ? m : c);
    }
    t &&
      this.progress.phase &&
      l.createEl("span", { text: ` \xB7 ${this.progress.phase}` });
    let p = o.createEl("button", {
        cls: "pf-btn pf-btn-ghost",
        text: s("ocr_ws_stop") || "Stop",
      }),
      u = this._getClient();
    !u || !u.isOperationActive()
      ? ((p.disabled = !0),
        (p.title =
          s("ocr_ws_stop_unavailable") ||
          "Operation is not owned by this window"))
      : p.addEventListener("click", () => this._stopBuild());
    let _ = a
        .createDiv({ cls: "pf-ocr-ws-progress-track" })
        .createDiv({ cls: "pf-ocr-ws-progress-fill" }),
      h = n.total > 0 ? Math.round((n.current / n.total) * 100) : 0;
    _.style.transform = `scaleX(${h / 100})`;
    let g = a.createDiv({ cls: "pf-ocr-ws-progress-meta" });
    (g.createEl("span", { text: `${n.current} / ${n.total} papers` }),
      g.createEl("span", { text: `${h}%` }),
      t &&
        this.progress.itemStatus &&
        g.createEl("span", { text: this.progress.itemStatus }));
  }
  _renderToolbar(e) {
    let t = this._filteredPapers(),
      r = [
        ...new Set(this.papers.map((u) => u.pipelineVersion).filter(Boolean)),
      ]
        .sort()
        .reverse(),
      n = e.createDiv({ cls: "pf-ocr-ws-toolbar" }),
      a = n.createDiv({ cls: "pf-ocr-ws-toolbar-count" });
    a.innerHTML = s("ocr_ws_showing")
      .replace("{count}", String(t.length))
      .replace("{total}", String(this.papers.length));
    let l = n
      .createDiv({ cls: "pf-ocr-ws-search" })
      .createEl("input", {
        cls: "pf-ocr-ws-search-input",
        attr: {
          type: "text",
          placeholder:
            s("ocr_ws_search_placeholder") ||
            "Search papers by title, author, year...",
        },
      });
    ((l.value = this._searchQuery),
      l.addEventListener("input", () => {
        ((this._searchQuery = l.value),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          (this._page = 1),
          clearTimeout(this._searchTimer),
          (this._searchTimer = setTimeout(() => this._refreshTable(), 100)));
      }),
      l.addEventListener("keydown", (u) => {
        u.key === "Escape" &&
          ((l.value = ""),
          (this._searchQuery = ""),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          (this._page = 1),
          clearTimeout(this._searchTimer),
          this._refreshTable(),
          l.blur());
      }));
    let c = n.createDiv({ cls: "pf-ocr-ws-field" });
    c.createEl("label", { text: s("ocr_ws_filter_status") });
    let p = c.createEl("select");
    for (let [u, f] of [
      ["all", s("ocr_ws_filter_all")],
      ["unprocessed", s("ocr_ws_filter_unprocessed")],
      ["review", s("ocr_ws_filter_review")],
      ["processed", s("ocr_ws_filter_processed")],
    ]) {
      let _ = p.createEl("option", {
        text: String(f),
        attr: { value: String(u) },
      });
      u === this.filter && (_.selected = !0);
    }
    if (
      (p.addEventListener("change", () => {
        ((this.filter = p.value),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          (this._page = 1),
          this._refreshTable());
      }),
      r.length > 0)
    ) {
      let u = n.createDiv({ cls: "pf-ocr-ws-version-field" });
      for (let f of r)
        u.createEl("button", {
          cls: `pf-ocr-ws-chip${this.versionFilter === f ? " pf-active" : ""}`,
          text: `v${f}`,
        }).addEventListener("click", () => {
          ((this.versionFilter = this.versionFilter === f ? null : f),
            (this.selectedKey = null),
            this.checkedKeys.clear(),
            (this._page = 1),
            this._refreshTable());
        });
    }
  }
  _filteredPapers() {
    let e = this.papers;
    if (
      (this.filter === "unprocessed"
        ? (e = e.filter(
            (t) =>
              t.status === "pending" ||
              t.status === "nopdf" ||
              t.status === "update_available"
          ))
        : this.filter === "review"
          ? (e = e.filter(
              (t) => t.status === "failed" || t.status === "processing"
            ))
          : this.filter === "processed" &&
            (e = e.filter((t) => t.status === "done")),
      this.versionFilter &&
        (e = e.filter((t) => t.pipelineVersion === this.versionFilter)),
      this._searchQuery.trim())
    ) {
      let t = this._searchQuery.trim().toLowerCase();
      e = e.filter(
        (r) =>
          r.title.toLowerCase().includes(t) ||
          r.authors.toLowerCase().includes(t) ||
          r.year.toLowerCase().includes(t) ||
          r.key.toLowerCase().includes(t)
      );
    }
    return e;
  }
  _currentPagePapers(e) {
    let t = Math.max(1, Math.ceil(e.length / bt));
    (this._page > t && (this._page = t), this._page < 1 && (this._page = 1));
    let r = (this._page - 1) * bt;
    return e.slice(r, r + bt);
  }
  _renderPagination(e, t) {
    let r = Math.max(1, Math.ceil(t.length / bt));
    if (r <= 1) return;
    let n = e.createDiv({ cls: "pf-ocr-ws-pagination" }),
      a = n.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: "\u2039",
      });
    ((a.disabled = this._page <= 1),
      a.addEventListener("click", () => {
        ((this._page = Math.max(1, this._page - 1)), this._refreshTable());
      }));
    let o = n.createEl("span", { text: `${this._page} / ${r}` }),
      l = n.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: "\u203A",
      });
    ((l.disabled = this._page >= r),
      l.addEventListener("click", () => {
        ((this._page = Math.min(r, this._page + 1)), this._refreshTable());
      }));
  }
  _renderTable(e) {
    let t = this._filteredPapers(),
      r = e.createDiv({ cls: "pf-ocr-ws-viewport" });
    (this._buildTableBody(r, this._currentPagePapers(t)),
      this._renderPagination(e, t));
  }
  _buildTableBody(e, t) {
    if (t.length === 0) {
      e.createDiv({
        cls: "pf-ocr-ws-empty pf-visible",
        text: s("ocr_ws_no_papers"),
      });
      return;
    }
    let r = e.createEl("table", { cls: "pf-ocr-ws-table" });
    (this._buildTableHead(r), this._buildTableRows(r, t));
  }
  _buildTableHead(e) {
    let r = e.createEl("thead").createEl("tr");
    (r
      .createEl("th", { cls: "pf-ocr-ws-col-check" })
      .createEl("input", { attr: { type: "checkbox" } }, (n) => {
        n.addEventListener("change", () => {
          let a = this._currentPagePapers(this._filteredPapers());
          (n.checked
            ? a.forEach((o) => this.checkedKeys.add(o.key))
            : a.forEach((o) => this.checkedKeys.delete(o.key)),
            this._refreshTable());
        });
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-paper",
        text: s("ocr_ws_col_title"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-status",
        text: s("ocr_ws_col_status"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-version",
        text: s("ocr_ws_col_version"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-date",
        text: s("ocr_ws_col_lastrun"),
      }),
      r.createEl("th", { cls: "pf-ocr-ws-col-action" }));
  }
  _buildTableRows(e, t) {
    let r = e.createEl("tbody"),
      n = this.papers.reduce(
        (a, o) => (o.pipelineVersion > a ? o.pipelineVersion : a),
        ""
      );
    for (let a of t) {
      let o = !!(a.pipelineVersion && n > a.pipelineVersion),
        l = r.createEl("tr", { cls: o ? "pf-update" : "" });
      (l.addEventListener("click", (m) => {
        m.target.tagName !== "INPUT" &&
          ((this.selectedKey = a.key === this.selectedKey ? null : a.key),
          this._refreshTable());
      }),
        l
          .createEl("td", { cls: "pf-ocr-ws-col-check" })
          .createEl("input", { attr: { type: "checkbox" } }, (m) => {
            ((m.checked = this.checkedKeys.has(a.key)),
              m.addEventListener("change", () => {
                (m.checked
                  ? this.checkedKeys.add(a.key)
                  : this.checkedKeys.delete(a.key),
                  this._refreshTable());
              }));
          }));
      let p = l.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      if (
        (p.createDiv({ cls: "pf-ocr-ws-paper-title", text: a.title }),
        a.authors || a.year)
      ) {
        let m = p.createDiv({ cls: "pf-ocr-ws-paper-meta" });
        if (a.authors) {
          let v = a.authors.split(",")[0].trim(),
            b = a.authors.includes(",") ? " et al." : "";
          m.createEl("span", { cls: "pf-ocr-ws-meta-author", text: v + b });
        }
        a.year &&
          m.createEl("span", { cls: "pf-ocr-ws-meta-year", text: a.year });
      }
      (l
        .createEl("td", { cls: "pf-ocr-ws-col-status" })
        .createEl("span", {
          cls: `pf-ocr-ws-status pf-${tn(a.status)}`,
          text: rn(a.status),
        }),
        l
          .createEl("td", { cls: "pf-ocr-ws-col-version" })
          .createEl("span", {
            cls: "pf-ocr-ws-version",
            text: a.pipelineVersion || "\u2014",
          }),
        l
          .createEl("td", { cls: "pf-ocr-ws-col-date" })
          .setText(a.lastRun ? a.lastRun.slice(0, 10) : "\u2014"),
        l
          .createEl("td", { cls: "pf-ocr-ws-col-action" })
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: s("ocr_ws_btn_preview"),
          })
          .addEventListener("click", (m) => {
            (m.stopPropagation(), this._openFulltext(a.key));
          }));
    }
  }
  _requestOcrRun(e, t) {
    let r = this.actionDescriptors.get("ocr.run");
    if (!r) {
      this._ensureActionDescriptor("ocr.run");
      return;
    }
    if (r.availability !== "available") {
      new H.Notice(
        r.availability_reason ||
          s("ocr_ws_re_extract_disabled_body") ||
          "OCR is unavailable"
      );
      return;
    }
    if (r.confirmation === "required") {
      new pe(
        this.app,
        {
          title:
            t === "redo" ? s("ocr_modal_title") : s("ocr_run_confirm_title"),
          effectLabel:
            t === "redo"
              ? s("ocr_modal_description")
              : s("ocr_run_confirm_body"),
        },
        () => {
          this._runOcrAction("ocr.run", e, t);
        }
      ).open();
      return;
    }
    this._runOcrAction("ocr.run", e, t);
  }
  _renderBatchBar(e) {
    (this._ensureActionDescriptor("ocr.run"),
      this._ensureActionDescriptor("ocr.rebuild_derived"));
    let t = this.papers.filter((p) => this.checkedKeys.has(p.key)),
      r = t.filter((p) => p.canRedo || p.recommendedAction === "redo"),
      n = e.createDiv({ cls: "pf-ocr-ws-batchbar" }),
      a = n.createDiv({ cls: "pf-ocr-ws-selection" });
    t.length === 0
      ? (a.createEl("strong", { text: s("ocr_ws_none_selected") }),
        a.createEl("span", { text: s("ocr_ws_select_hint") }))
      : a.createEl("strong", {
          text: s("ocr_ws_selected").replace("{count}", String(t.length)),
        });
    let o = n.createDiv({ cls: "pf-ocr-ws-batch-actions" }),
      l = o.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: s("ocr_ws_btn_process_selected"),
      });
    if (
      ((l.title = this._actionAvailabilityTitle(
        "ocr.run",
        s("ocr_ws_tooltip_process")
      )),
      (l.disabled = t.length === 0 || !this._isActionAvailable("ocr.run")),
      l.addEventListener("click", () =>
        this._requestOcrRun(
          t.map((p) => p.key),
          "run"
        )
      ),
      r.length > 0)
    ) {
      let p = o.createEl("button", {
        cls: "pf-btn pf-btn-warning",
        text: `${s("ocr_ws_detail_re_extract")} (${r.length})`,
      });
      ((p.title = this._actionAvailabilityTitle(
        "ocr.run",
        s("ocr_ws_tooltip_reextract")
      )),
        (p.disabled = !this._isActionAvailable("ocr.run")),
        p.addEventListener("click", () =>
          this._requestOcrRun(
            r.map((u) => u.key),
            "redo"
          )
        ));
    }
    let c = o.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: s("ocr_ws_btn_rebuild_selected"),
    });
    ((c.title = this._actionAvailabilityTitle(
      "ocr.rebuild_derived",
      s("ocr_ws_tooltip_rebuild")
    )),
      (c.disabled =
        t.length === 0 || !this._isActionAvailable("ocr.rebuild_derived")),
      c.addEventListener("click", () => this._runRebuild(t.map((p) => p.key))));
  }
  _renderDetail(e) {
    let t = this.papers.find((w) => w.key === this.selectedKey);
    if (!t) return;
    let n = e
        .createDiv({ cls: "pf-ocr-ws-detail pf-open" })
        .createDiv({ cls: "pf-ocr-ws-detail-card" }),
      a = n.createDiv({ cls: "pf-ocr-ws-detail-head" }),
      o = a.createDiv({});
    (o.createEl("h2", { text: t.title }),
      o.createEl("span", {
        cls: `pf-ocr-ws-status pf-${tn(t.status)}`,
        text: rn(t.status),
      }),
      a
        .createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          text: s("ocr_ws_close"),
        })
        .addEventListener("click", () => {
          ((this.selectedKey = null), this._refreshTable());
        }));
    let c = n.createDiv({ cls: "pf-ocr-ws-detail-grid" });
    (this._addFact(c, s("ocr_ws_fact_version"), t.pipelineVersion || "\u2014"),
      this._addFact(
        c,
        s("ocr_ws_fact_last_run"),
        t.lastRun ? t.lastRun.slice(0, 10) : "\u2014"
      ),
      this._addFact(c, s("ocr_ws_fact_authors"), t.authors || "\u2014"),
      this._addFact(c, s("ocr_ws_fact_year"), t.year || "\u2014"),
      this._addFact(c, s("ocr_ws_fact_pages"), t.pages || "\u2014"),
      this._addFact(
        c,
        s("ocr_ws_fact_backups"),
        t.backupCount > 0 ? String(t.backupCount) : "\u2014"
      ));
    let p = n.createDiv({ cls: "pf-ocr-ws-detail-actions" });
    (p
      .createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: s("ocr_ws_detail_view_fulltext"),
      })
      .addEventListener("click", () => this._openFulltext(t.key)),
      this._ensureActionDescriptor("ocr.run"));
    let f = t.canRedo || t.recommendedAction === "redo",
      _ = p.createEl("button", {
        cls: `pf-btn ${f ? "pf-btn-warning" : "pf-btn-secondary"}`,
        text: f
          ? s("ocr_ws_detail_re_extract")
          : s("ocr_ws_detail_run") || s("ocr_ws_btn_process_selected"),
      });
    ((_.title = this._actionAvailabilityTitle(
      "ocr.run",
      f ? s("ocr_ws_tooltip_reextract") : s("ocr_ws_tooltip_process")
    )),
      (_.disabled = !this._isActionAvailable("ocr.run")),
      _.addEventListener("click", () =>
        this._requestOcrRun([t.key], f ? "redo" : "run")
      ));
    let h = p.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: s("ocr_ws_restore_checking") || "Checking versions\u2026",
    });
    h.disabled = !0;
    let g = this.app.vault.adapter.basePath,
      m = we(g),
      v = t.key,
      b = (() => {
        try {
          let w = nt(g, t.key);
          return w && w.versions.length > 0;
        } catch (w) {
          return !1;
        }
      })(),
      x = !1;
    if (!b) {
      let w = Q.join(m.ocrDir, t.key, "backups");
      try {
        x =
          U.readdirSync(w).filter((k) => k.startsWith("fulltext.pre-rebuild"))
            .length > 0;
      } catch (k) {}
    }
    let E = b || x;
    (this.selectedKey === v &&
      ((h.disabled = !E),
      h.setText(s("ocr_ws_detail_restore_backup") || "Restore Backup"),
      E ||
        (h.title =
          s("ocr_ws_restore_unavailable") || "No backup versions available")),
      h.addEventListener("click", () => {
        let w = nt(g, t.key);
        if (w && w.versions.length > 0) {
          new Fe(
            this.app,
            g,
            t.key,
            w.versions.map((P) => ({
              label: P.label,
              created_at: P.created_at,
              source: P.source,
              renderer_version: P.renderer_version,
              fulltext_size: P.fulltext_size,
            })),
            w.currentLabel,
            () => {
              this._loadPapers().then(() => this._render());
            },
            t.ocrFinishedAt
          ).open();
          return;
        }
        let k = Q.join(m.ocrDir, t.key, "backups");
        if (!U.existsSync(k)) {
          new H.Notice("No backup versions available");
          return;
        }
        let S = U.readdirSync(k)
          .filter((D) => D.startsWith("fulltext.pre-rebuild"))
          .sort();
        if (S.length === 0) {
          new H.Notice("No backup versions available");
          return;
        }
        let C = S.map((D) => {
          let P = D.replace("fulltext.pre-rebuild.", "").replace(/\.md$/, ""),
            L =
              P.length >= 16
                ? P.slice(0, 4) +
                  "-" +
                  P.slice(4, 6) +
                  "-" +
                  P.slice(6, 8) +
                  "T" +
                  P.slice(9, 11) +
                  ":" +
                  P.slice(11, 13) +
                  ":" +
                  P.slice(13, 15) +
                  "Z"
                : P,
            K = 0;
          try {
            K = U.statSync(Q.join(k, D)).size;
          } catch (X) {}
          return {
            label: "backup-" + P,
            created_at: L,
            source: "pre-rebuild",
            fulltext_size: K,
          };
        });
        new Fe(
          this.app,
          g,
          t.key,
          C,
          "",
          () => {
            this._loadPapers().then(() => this._render());
          },
          t.ocrFinishedAt
        ).open();
      }),
      this._ensureActionDescriptor("ocr.rebuild_derived"));
    let y = p.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: s("ocr_ws_detail_rebuild") || "Rebuild this paper",
    });
    ((y.title = s("ocr_ws_tooltip_rebuild")),
      (y.disabled = !this._isActionAvailable("ocr.rebuild_derived")),
      y.addEventListener("click", () => {
        this._runRebuild([t.key]);
      }));
  }
  _addFact(e, t, r) {
    let n = e.createDiv({ cls: "pf-ocr-ws-fact" });
    (n.createEl("dt", { text: t }), n.createEl("dd", { text: r }));
  }
  async _runOcrAction(
    e,
    t,
    r = e === "ocr.rebuild_derived" ? "rebuild" : "run"
  ) {
    var l, c, p;
    let n = this._getClient();
    if (!n) {
      new H.Notice(s("runtime_not_available") || "Environment unavailable");
      return;
    }
    if (this.running || n.isOperationActive()) {
      new H.Notice(s("ocr_already_running") || "OCR is already running");
      return;
    }
    ((this._runningMode = r),
      (this.running = !0),
      (this.progress = {
        current: 0,
        total: t.length,
        paperKey: "",
        phase: "",
        itemStatus: "",
      }),
      this._render());
    let a = {
        action_id: e,
        scope: t.length > 0 ? { kind: "papers", keys: t } : { kind: "all" },
        confirm: e === "ocr.run" ? e : void 0,
      },
      o = !1;
    try {
      let u = await n.runAction(a, {
        onEvent: (h) => {
          var g, m, v, b, x;
          (h.event === "cancelled" && (o = !0),
            (h.event === "start" ||
              h.event === "phase" ||
              h.event === "progress" ||
              h.event === "item_result") &&
              ((this.progress = {
                current: Number(
                  (g = h.current) != null ? g : this.progress.current
                ),
                total: Number((m = h.total) != null ? m : this.progress.total),
                paperKey: String(
                  (v = h.item_id) != null ? v : this.progress.paperKey
                ),
                phase:
                  h.event === "phase"
                    ? String((b = h.phase) != null ? b : h.operation)
                    : this.progress.phase,
                itemStatus:
                  h.event === "item_result"
                    ? String((x = h.status) != null ? x : "")
                    : this.progress.itemStatus,
              }),
              this._render()));
        },
      });
      (this.actionDescriptors.delete(e),
        (this._runningMode = null),
        (this.running = !1));
      let f =
        typeof ((l = u.payload) == null ? void 0 : l.status) == "string"
          ? u.payload.status
          : "";
      if (u.ok)
        new H.Notice(s("ocr_rebuild_complete") || "Operation completed");
      else if (u.cancelled || o || f === "cancelled")
        new H.Notice(s("ocr_stopped_notice") || "Operation cancelled");
      else {
        let h =
          typeof ((c = u.payload) == null ? void 0 : c.availability_reason) ==
          "string"
            ? u.payload.availability_reason
            : `exit code ${u.exitCode}`;
        new H.Notice((s("ocr_error_notice") || "OCR error") + ": " + h, 8e3);
      }
      let _ = (p = this.plugin) == null ? void 0 : p._settingTab;
      (_ &&
        typeof _._refreshAllReadModels == "function" &&
        _._refreshAllReadModels(),
        await this._loadPapers(),
        this._render());
    } catch (u) {
      (this.actionDescriptors.delete(e),
        (this.running = !1),
        (this._runningMode = null),
        new H.Notice(
          (s("ocr_error_notice") || "OCR error") +
            ": " +
            (u instanceof Error ? u.message : String(u)),
          8e3
        ),
        this._render());
    }
  }
  _runRebuild(e) {
    this._runOcrAction("ocr.rebuild_derived", e, "rebuild");
  }
  _stopBuild() {
    let e = this._getClient();
    if (!e || !e.isOperationActive()) {
      new H.Notice(
        s("ocr_stopped_notice") || "No local operation active to stop"
      );
      return;
    }
    (e.cancelActiveOperation(),
      (this.progress.itemStatus =
        s("ocr_stopping_notice") || "Stopping operation..."),
      new H.Notice(s("ocr_stopping_notice") || "Stopping operation..."),
      this._render());
  }
  _openFulltext(e) {
    var l;
    let t = this.app.vault.adapter.basePath,
      r = we(t),
      n = this.papers.find((c) => c.key === e),
      a = Zn(
        t,
        (l = n == null ? void 0 : n.fulltextPath) != null ? l : "",
        e,
        r.ocrDir,
        U.existsSync
      );
    if (!a) {
      new H.Notice(s("ocr_ws_fulltext_not_found") || "Fulltext not found");
      return;
    }
    let o = this.app.vault.getAbstractFileByPath(
      Q.relative(t, a).replace(/\\/g, "/").replace(/^\//, "")
    );
    o
      ? this.app.workspace.getLeaf().openFile(o)
      : new H.Notice(
          s("ocr_ws_fulltext_not_found") || "Fulltext not found in vault"
        );
  }
};
function Zn(d, i, e, t, r = U.existsSync) {
  if (i) {
    let a = Q.join(d, i);
    if (r(a)) return a;
  }
  let n = Q.join(t, e, "fulltext.md");
  return r(n) ? n : null;
}
function tn(d) {
  return d === "done"
    ? "done"
    : d === "update_available"
      ? "update"
      : d === "done_degraded"
        ? "done-degraded"
        : d === "done_incomplete"
          ? "done-incomplete"
          : d === "failed" || d === "error" || d === "fatal_error"
            ? "failed"
            : "pending";
}
function rn(d) {
  return d === "done"
    ? s("ocr_ws_status_done") || "Processed"
    : d === "update_available"
      ? s("ocr_ws_status_update") || "Update available"
      : d === "done_degraded"
        ? s("ocr_ws_status_degraded") || "Partial"
        : d === "done_incomplete"
          ? s("ocr_ws_status_incomplete") || "Incomplete"
          : d === "failed" || d === "error" || d === "fatal_error"
            ? s("ocr_ws_status_failed") || "Failed"
            : d === "retryable_error"
              ? s("ocr_ws_status_error") || "Error"
              : d === "processing" || d === "running"
                ? s("ocr_ws_status_processing") || "Processing"
                : d === "queued"
                  ? s("ocr_ws_status_queued") || "Queued"
                  : d === "blocked"
                    ? s("ocr_ws_status_blocked") || "Blocked"
                    : d === "nopdf"
                      ? s("ocr_ws_status_nopdf") || "No PDF"
                      : d === "unknown"
                        ? s("ocr_ws_status_unknown") || "Unknown"
                        : s("ocr_ws_status_pending") || "Pending";
}
function nn(d, i, e) {
  if (e.startsWith("backup-")) {
    let t = e.slice(7);
    return Q.join(d, i, "backups", "fulltext.pre-rebuild." + t + ".md");
  }
  return Q.join(d, i, "versions", e, "fulltext.md");
}
function Gn(d, i) {
  let e = (o) => o.split(/\n\n+/).filter(Boolean),
    t = e(d),
    r = e(i),
    n = Math.max(t.length, r.length),
    a = [];
  for (let o = 0; o < n; o++) {
    let l = o < t.length ? t[o] : "",
      c = o < r.length ? r[o] : "";
    !l && c
      ? a.push({ type: "added", text: c })
      : l && !c
        ? a.push({ type: "removed", text: l })
        : l !== c
          ? (a.push({ type: "removed", text: l }),
            a.push({ type: "added", text: c }))
          : a.push({ type: "unchanged", text: l });
  }
  return a;
}
var Fe = class extends H.Modal {
  constructor(e, t, r, n, a, o, l = "") {
    super(e);
    this.paperFinishedAt = l;
    this.selectedIdx = 0;
    this.contentCache = new Map();
    ((this.vaultPath = t),
      (this.paperKey = r),
      (this.ocrDir = Q.join(t, "System", "PaperForge", "ocr")),
      (this.versions = n),
      (this.currentLabel = a),
      (this.onRestored = o != null ? o : null),
      (this.mdComponent = new H.Component()),
      this.mdComponent.load());
  }
  getContent(e) {
    let t = this.contentCache.get(e);
    if (t !== void 0) return t;
    try {
      let r = nn(this.ocrDir, this.paperKey, e);
      if (U.existsSync(r)) {
        let n = U.readFileSync(r, "utf-8");
        return (this.contentCache.set(e, n), n);
      }
    } catch (r) {}
    return (this.contentCache.set(e, ""), "");
  }
  onOpen() {
    let { contentEl: e } = this;
    e.addClass("paperforge-modal");
    try {
      let r = e.closest(".modal");
      r && (r.style.width = "min(90vw, 1200px)");
    } catch (r) {}
    let t = Q.join(this.ocrDir, this.paperKey, "render", "fulltext.md");
    try {
      U.existsSync(t) &&
        this.contentCache.set("__current__", U.readFileSync(t, "utf-8"));
    } catch (r) {}
    this.renderAll();
  }
  renderAll() {
    let { contentEl: e } = this;
    e.empty();
    let t = e.createDiv({ cls: "pf-vr-layout" }),
      r = t.createDiv({ cls: "pf-vr-sidebar" }),
      n = t.createDiv({ cls: "pf-vr-preview" });
    r.createEl("div", {
      cls: "pf-vr-sidebar-title",
      text: s("ocr_ws_restore_versions") || "Versions",
    });
    let a = r.createDiv({ cls: "pf-vr-timeline" });
    this.versions.forEach((m, v) => {
      let b = new Date(m.created_at).toLocaleDateString(),
        x = a.createDiv({
          cls:
            "pf-vr-entry" +
            (v === this.selectedIdx ? " pf-vr-entry--active" : "") +
            (m.label === this.currentLabel ? " pf-vr-entry--current" : ""),
          attr: { "data-idx": String(v) },
        });
      (x.createEl("span", { cls: "pf-vr-entry-label", text: m.label }),
        x.createEl("span", { cls: "pf-vr-entry-date", text: b }),
        m.label === this.currentLabel &&
          x.createEl("span", {
            cls: "pf-vr-entry-badge",
            text: s("ocr_ws_restore_current") || "current",
          }),
        x.addEventListener("click", () => {
          ((this.selectedIdx = v), this.renderAll());
        }));
    });
    let o = this.versions[this.selectedIdx],
      l = o.label === this.currentLabel,
      c = n.createDiv({ cls: "pf-vr-toolbar" }),
      p = c.createDiv({ cls: "pf-vr-info" }),
      u = c.createDiv({ cls: "pf-vr-actions" }),
      f = new Date(o.created_at).toLocaleString(),
      _ =
        o.fulltext_size > 1024
          ? (o.fulltext_size / 1024).toFixed(0) + "KB"
          : o.fulltext_size + "B";
    p.innerHTML =
      "<strong>" +
      o.label +
      "</strong>" +
      (l
        ? ' <span class="pf-vr-current-tag">' +
          (s("ocr_ws_restore_current") || "current") +
          "</span>"
        : "") +
      '<br><span class="pf-vr-info-meta">' +
      f +
      " \xB7 " +
      o.source +
      " \xB7 " +
      _ +
      (o.renderer_version ? " \xB7 renderer v" + o.renderer_version : "") +
      "</span>";
    let h = n.createDiv({ cls: "pf-vr-content" }),
      g = n.createDiv({ cls: "pf-vr-diff" });
    (H.MarkdownRenderer.render(
      this.app,
      this.getContent(o.label),
      h,
      this.vaultPath,
      this.mdComponent
    ),
      (g.style.display = "none"),
      l ||
        (u
          .createEl("button", {
            cls: "btn-secondary pf-vr-btn",
            text: s("ocr_ws_restore_compare") || "Compare with current",
          })
          .addEventListener("click", () => {
            let b = this.getContent("__current__"),
              x = this.getContent(o.label);
            ((h.style.display = "none"),
              (g.style.display = "block"),
              g.empty(),
              g
                .createEl("div", { cls: "pf-vr-diff-header" })
                .setText(
                  (
                    s("ocr_ws_restore_diff_title") || "Changes from current"
                  ).replace("{v}", o.label)
                ));
            let y = g.createEl("div", { cls: "pf-vr-diff-body" }),
              w = Gn(b, x);
            for (let S of w) {
              let C = y.createEl("div", {
                cls: "pf-vr-diff-line pf-vr-diff-" + S.type,
              });
              (C.createEl("span", {
                cls: "pf-vr-diff-prefix",
                text:
                  S.type === "added"
                    ? "+ "
                    : S.type === "removed"
                      ? "\u2212 "
                      : "  ",
              }),
                C.createEl("span", {
                  cls: "pf-vr-diff-text",
                  text:
                    S.text.slice(0, 200) +
                    (S.text.length > 200 ? "\u2026" : ""),
                }));
            }
            (w.length === 0 &&
              y.createEl("div", {
                cls: "pf-vr-diff-empty",
                text: s("ocr_ws_restore_no_diff") || "No differences",
              }),
              g
                .createEl("button", {
                  cls: "btn-secondary pf-vr-btn",
                  text: s("ocr_ws_restore_back") || "Back",
                })
                .addEventListener("click", () => {
                  ((h.style.display = "block"),
                    (g.style.display = "none"),
                    g.empty());
                }));
          }),
        u
          .createEl("button", {
            cls: "btn-primary pf-vr-btn",
            text: s("ocr_ws_restore_btn") || "Restore this version",
          })
          .addEventListener("click", () => this.doRestore(o))));
  }
  doRestore(e) {
    if (e.label === this.currentLabel) return;
    let t = new H.Modal(this.app);
    (t.contentEl.addClass("paperforge-modal"),
      t.contentEl.createEl("h2", {
        text:
          s("ocr_ws_restore_confirm_title") ||
          "\u6062\u590D\u5C55\u793A\u5168\u6587\u6587\u672C",
      }),
      t.contentEl.createEl("div", {
        cls: "pf-vr-confirm-body",
        text:
          s("ocr_ws_restore_confirm_body") ||
          "\u5C06\u7528\u6240\u9009\u7248\u672C\u7684 fulltext.md \u8986\u76D6 render/fulltext.md\u3002OCR \u7ED3\u6784\u3001\u7D22\u5F15\u3001\u8BB0\u5FC6\u4E0E\u5411\u91CF\u5747\u4E0D\u53D7\u5F71\u54CD\u3002\u7EE7\u7EED\uFF1F",
      }));
    let r = t.contentEl.createDiv({ cls: "pf-vr-confirm-actions" });
    (r
      .createEl("button", {
        cls: "btn-secondary pf-vr-btn",
        text: s("next_action_cancel") || "Later",
      })
      .addEventListener("click", () => t.close()),
      r
        .createEl("button", {
          cls: "btn-primary pf-vr-btn mod-warning",
          text:
            s("ocr_ws_restore_confirm_btn") ||
            "\u6062\u590D\u5C55\u793A\u5168\u6587",
        })
        .addEventListener("click", () => {
          (t.close(), this._executeRestore(e));
        }),
      t.open());
  }
  _executeRestore(e) {
    var r;
    let t = !1;
    if (e.label.startsWith("backup-")) {
      let n = nn(this.ocrDir, this.paperKey, e.label),
        a = Q.join(this.ocrDir, this.paperKey, "render"),
        o = Q.join(a, "fulltext.md");
      try {
        U.existsSync(n) &&
          (U.existsSync(a) || U.mkdirSync(a, { recursive: !0 }),
          U.copyFileSync(n, o),
          (t = !0),
          Kt(this.ocrDir, this.paperKey, {
            label: e.label,
            restored_at: new Date().toISOString(),
            version_created_at: e.created_at,
          }));
      } catch (l) {
        console.warn("[PaperForge] Restore backup failed:", l);
      }
    } else t = yt(this.vaultPath, this.paperKey, e.label, e.created_at);
    if (t) {
      new H.Notice(s("ocr_ws_detail_restore_done").replace("{label}", e.label));
      let n = new Date(e.created_at).getTime(),
        a = new Date(this.paperFinishedAt).getTime();
      (Number.isFinite(n) &&
        Number.isFinite(a) &&
        n < a &&
        new H.Notice(
          s("ocr_ws_restore_stale_notice") ||
            "This version predates the current structured state; rebuild the paper to re-sync structure",
          8e3
        ),
        this.close(),
        (r = this.onRestored) == null || r.call(this));
    } else new H.Notice("Restore failed");
  }
  onClose() {
    try {
      this.contentEl.empty();
    } catch (e) {}
    (this.contentCache.clear(), this.mdComponent.unload());
  }
};
var Ue = class extends O.ItemView {
  constructor(e) {
    super(e);
    this._currentMode = null;
    this._currentDomain = null;
    this._currentPaperKey = null;
    this._currentPaperEntry = null;
    this._currentFilePath = null;
    this._cachedItems = null;
    this._modeSubscribers = [];
    this._leafChangeTimer = null;
    this._ocrPrivacyShown = !1;
    this._cachedStats = null;
    this._techDetailsExpanded = !1;
    this._paperforgeVersion = "";
    this._dashboardPermissions = {};
    this._headerTitle = null;
    this._versionBadge = null;
    this._messageEl = null;
    this._metricsEl = null;
    this._ocrSection = null;
    this._ocrEmpty = null;
    this._ocrBadge = null;
    this._ocrTrack = null;
    this._ocrCounts = null;
    this._versionPapers = null;
    this._versionFilter = "";
    this._searchContainer = null;
    this._searchInput = null;
    this._searchResultsEl = null;
    this._searchTimer = void 0;
    this._searchState = "idle";
    this._searchMode = "M";
    this._searchResults = null;
    this._searchActiveIndex = -1;
    this._onKeyDown = null;
    this._qualityStagingCache = null;
    this._librarySyncRunning = !1;
    ((this._currentMode = null),
      (this._currentDomain = null),
      (this._currentPaperKey = null),
      (this._currentPaperEntry = null),
      (this._currentFilePath = null),
      (this._cachedItems = null),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      (this._ocrPrivacyShown = !1));
  }
  _getClient() {
    var t, r;
    let e =
      (r = (t = this.app.plugins) == null ? void 0 : t.plugins) == null
        ? void 0
        : r.paperforge;
    return typeof (e == null ? void 0 : e.getClient) == "function"
      ? e.getClient()
      : null;
  }
  _resolvePython() {
    var a, o, l;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (o =
          (a = e == null ? void 0 : e.settings) == null
            ? void 0
            : a.python_path) == null
          ? void 0
          : o.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    let r =
      (l = e == null ? void 0 : e.getManagedRuntime) == null
        ? void 0
        : l.call(e);
    if (!r) return null;
    let n = ce(r.readPointer());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  getViewType() {
    return Pe;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Je;
  }
  async onOpen() {
    (this._buildPanel(),
      (this._modeSubscribers = []),
      (this._leafChangeTimer = null),
      this._setupEventSubscriptions(),
      this._fetchVersion(),
      this._detectAndSwitch(),
      (this._onKeyDown = (e) => {
        var t, r, n;
        if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey) {
          let a =
            (r = (t = e.target) == null ? void 0 : t.tagName) == null
              ? void 0
              : r.toLowerCase();
          a !== "input" &&
            a !== "textarea" &&
            (e.preventDefault(), (n = this._searchInput) == null || n.focus());
        }
      }),
      document.addEventListener("keydown", this._onKeyDown));
  }
  async onClose() {
    if (this._modeSubscribers && this._modeSubscribers.length > 0) {
      for (let e of this._modeSubscribers)
        e.event === "active-leaf-change"
          ? this.app.workspace.off("active-leaf-change", e.ref)
          : e.event === "modify" && this.app.vault.off("modify", e.ref);
      this._modeSubscribers = [];
    }
    (this._leafChangeTimer &&
      (clearTimeout(this._leafChangeTimer), (this._leafChangeTimer = null)),
      this._onKeyDown &&
        (document.removeEventListener("keydown", this._onKeyDown),
        (this._onKeyDown = null)),
      (this._searchState = "idle"),
      (this._searchResults = null),
      (this._searchActiveIndex = -1),
      (this._searchTimer = void 0),
      (this._cachedItems = null),
      (this._cachedStats = null));
  }
  _buildPanel() {
    let e = this.containerEl;
    (e.empty(), e.addClass("paperforge-status-panel"));
    let t = e.createEl("div", { cls: "paperforge-header" }),
      r = t.createEl("div", { cls: "paperforge-header-left" });
    (r.createEl("div", { cls: "paperforge-header-logo", text: "P" }),
      (this._modeContextEl = r.createEl("div", {
        cls: "paperforge-mode-context",
      })),
      (this._headerTitle = r.createEl("h3", {
        cls: "paperforge-header-title",
        text: "PaperForge",
      })),
      (this._versionBadge = r.createEl("span", {
        cls: "paperforge-header-badge",
        text: "v\u2014",
      })));
    let n = t.createEl("button", {
      cls: "paperforge-header-refresh",
      attr: { "aria-label": "Refresh" },
    });
    ((n.innerHTML = "\u21BB"),
      n.addEventListener("click", () => {
        (this._invalidateIndex(), this._detectAndSwitch());
      }),
      (this._messageEl = e.createEl("div", {
        cls: "paperforge-message",
        attr: { "aria-live": "polite" },
      })),
      (this._contentEl = e.createEl("div", {
        cls: "paperforge-content-area",
      })));
  }
  _fetchVersion() {
    let e = this.app.vault.adapter.basePath,
      t = this._resolvePython();
    if (!t) return;
    let { path: r, args: n = [] } = t;
    try {
      let a = (0, Ee.execFileSync)(
        r,
        [...n, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: e, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
      ).trim();
      if (!a) return;
      let o = a.startsWith("v") ? a : "v" + a;
      ((this._paperforgeVersion = o),
        this._versionBadge && this._versionBadge.setText(o));
    } catch (a) {}
  }
  _fetchStats(e) {
    if (!this._metricsEl) return;
    if (!e && !this._cachedStats)
      (this._metricsEl.empty(),
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "Loading...",
        }));
    else if (e && !this._cachedStats) return;
    let t = this.app.vault.adapter.basePath,
      r = this.app.plugins.plugins.paperforge,
      n = this._resolvePython();
    if (!n) {
      this._fallbackFetchStats(e, t, r);
      return;
    }
    let { path: a, args: o = [] } = n;
    (0, Ee.execFile)(
      a,
      [...o, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (l, c) => {
        if (!l)
          try {
            let p = JSON.parse(c);
            if (p.ok && p.data) {
              let u = this._normalizeDashboardData(p.data);
              ((this._cachedStats = u),
                this._metricsEl.empty(),
                this._renderStats(u),
                this._renderOcr(u),
                (this._dashboardPermissions = p.data.permissions || {}));
              return;
            }
          } catch (p) {}
        this._fallbackFetchStats(e, t, r);
      }
    );
  }
  _normalizeDashboardData(e) {
    let t = e.stats || {},
      r = t.ocr_health || {},
      n = t.pdf_health || {},
      a = e.ocr_version_state || {},
      o = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: o,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (n.broken || 0) + (n.missing || 0),
      ocr_version_state: {
        total_papers: a.total_papers || 0,
        derived_stale_count: a.derived_stale_count || 0,
        raw_upgradable_count: a.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var o, l;
    let n =
        ((o = r == null ? void 0 : r.settings) == null
          ? void 0
          : o.system_dir) || "System",
      a = Ae.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = te.readFileSync(a, "utf-8"),
        p = JSON.parse(c),
        u = p.items || [],
        f = {},
        _ = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        h = 0,
        g = 0,
        m = 0,
        v = 0,
        b = 0,
        x = 0;
      for (let E of u) {
        E.note_path && x++;
        let y = E.lifecycle || "pdf_ready";
        f[y] = (f[y] || 0) + 1;
        let w = E.health || {};
        for (let S of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (w[S] || "healthy") === "healthy" ? _[S].healthy++ : _[S].unhealthy++;
        let k = E.ocr_status || "";
        (h++,
          k === "done"
            ? g++
            : k === "pending"
              ? m++
              : k === "processing" || k === "queued" || k === "running"
                ? v++
                : b++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((l = this._cachedStats) == null ? void 0 : l.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: x,
        exports: 0,
        bases: 0,
        ocr: { total: h, pending: m, processing: v, done: g, failed: b },
        path_errors: 0,
        lifecycle_level_counts: f,
        health_aggregate: _,
      }),
        this._metricsEl.empty(),
        this._renderStats(this._cachedStats),
        this._renderOcr(this._cachedStats));
    } catch (c) {
      !e &&
        !this._cachedStats &&
        this._metricsEl.createEl("div", {
          cls: "paperforge-status-loading",
          text: "No index \u2014 trying CLI...",
        });
      let p = this._resolvePython();
      if (!p) {
        this._cachedStats ||
          this._metricsEl.createEl("div", {
            cls: "paperforge-status-error",
            text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
          });
        return;
      }
      let { path: u, args: f = [] } = p;
      (0, Ee.execFile)(
        u,
        [...f, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (_, h) => {
          if (_) {
            if (this._cachedStats) return;
            this._metricsEl.createEl("div", {
              cls: "paperforge-status-error",
              text: `Cannot reach PaperForge CLI.
Make sure paperforge is installed and in your PATH.`,
            });
            return;
          }
          try {
            let g = JSON.parse(h);
            ((this._cachedStats = g),
              this._metricsEl.empty(),
              this._renderStats(g),
              this._renderOcr(g));
          } catch (g) {
            this._cachedStats ||
              this._metricsEl.createEl("div", {
                cls: "paperforge-status-error",
                text: "Invalid response from paperforge status.",
              });
          }
        }
      );
    }
  }
  _renderSkeleton(e) {
    e.addClass("paperforge-loading");
  }
  _renderEmptyState(e, t) {
    e.createEl("div", { cls: "paperforge-empty-state", text: t || "No data" });
  }
  _buildMetricBar(e, t, r) {
    if (r <= 0) return;
    let n = Math.min(100, (t / r) * 100);
    e.createEl("div", { cls: "paperforge-metric-progress" }).createEl("div", {
      cls: "paperforge-metric-progress-fill",
      attr: { style: `width:${n.toFixed(1)}%` },
    });
  }
  _loadIndex() {
    var a;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((a = t == null ? void 0 : t.settings) == null
          ? void 0
          : a.system_dir) || "System",
      n = Ae.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let o = te.readFileSync(n, "utf-8");
      return JSON.parse(o);
    } catch (o) {
      return null;
    }
  }
  _getCachedIndex() {
    if (!this._cachedItems) {
      let e = this._loadIndex();
      this._cachedItems = e ? e.items || [] : [];
    }
    return this._cachedItems;
  }
  _findEntry(e) {
    if (!e) return null;
    let t = this._getCachedIndex().find((r) => r.zotero_key === e) || null;
    return or(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = wt(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var o;
    if (
      (this._versionBadge &&
        this._versionBadge.setText(
          this._paperforgeVersion || (e.version ? "v" + e.version : "v\u2014")
        ),
      !e || typeof e.total_papers == "undefined")
    ) {
      this._metricsEl && this._renderSkeleton(this._metricsEl);
      return;
    }
    if (!this._metricsEl) return;
    this._metricsEl.removeClass("paperforge-loading");
    let t = e.total_papers || 0,
      r = e.formal_notes || 0,
      n = [
        { value: t, label: "Papers", color: "var(--color-cyan)", barMax: 0 },
        {
          value: r,
          label: "Formal Notes",
          color: "var(--color-blue)",
          barMax: t,
        },
        {
          value: e.exports || 0,
          label: "Exports",
          color: "var(--color-purple)",
          barMax: 0,
        },
      ];
    for (let l of n) {
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", l.color),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((o = l.value) == null ? void 0 : o.toString()) || "\u2014",
        }),
        c.createEl("div", { cls: "paperforge-metric-label", text: l.label }),
        l.barMax > 0 && this._buildMetricBar(c, l.value, l.barMax));
    }
    let a = e.ocr_version_state || {};
    if (
      a.total_papers > 0 &&
      (a.derived_stale_count > 0 || a.raw_upgradable_count > 0)
    ) {
      let l = [];
      (a.derived_stale_count > 0 && l.push(`${a.derived_stale_count} stale`),
        a.raw_upgradable_count > 0 &&
          l.push(`${a.raw_upgradable_count} upgradable`));
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", "var(--color-yellow)"),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: l.join(", "),
        }),
        c.createEl("div", {
          cls: "paperforge-metric-label",
          text: "OCR Version",
        }));
    }
  }
  _renderOcr(e) {
    if (!this._ocrSection) return;
    let t = e.ocr || {},
      r = t.total || 0;
    if (r === 0) {
      this._ocrSection.style.display = "none";
      return;
    }
    ((this._ocrSection.style.display = "block"),
      this._ocrEmpty && (this._ocrEmpty.style.display = "none"));
    let n = t.done || 0,
      a = t.pending || 0,
      o = t.processing || 0,
      l = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        o > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : a > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        o > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let c = [
        { cls: "pending", count: a },
        { cls: "active", count: o },
        { cls: "done", count: n },
        { cls: "failed", count: l },
      ];
      for (let p of c)
        if (p.count > 0) {
          let u = ((p.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${p.cls}`,
            attr: { style: `width:${u}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let c = [
        { cls: "pending", value: a, label: "Pending" },
        { cls: "active", value: o, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: l, label: "Failed" },
      ];
      for (let p of c) {
        let u = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (u.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: p.value.toString(),
        }),
          u.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: p.label,
          }));
      }
    }
  }
  _renderLifecycleStepper(e, t, r) {
    if (!t || !r) {
      this._renderSkeleton(e);
      return;
    }
    let n = [
        { key: "indexed", label: "Indexed" },
        { key: "pdf_ready", label: "PDF Ready" },
        { key: "fulltext_ready", label: "Fulltext Ready" },
        { key: "deep_read_done", label: "Deep Read" },
      ],
      a = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      o = !1;
    for (let l of n) {
      let c = a.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: l.label }),
        l.key === r
          ? (c.addClass("current"), (o = !0))
          : o
            ? c.addClass("pending")
            : c.addClass("completed"));
    }
  }
  _renderHealthMatrix(e, t) {
    if (!t) {
      this._renderSkeleton(e);
      return;
    }
    let r = [
        {
          key: "pdf_health",
          label: "PDF Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "ocr_health",
          label: "OCR Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "note_health",
          label: "Note Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
        {
          key: "asset_health",
          label: "Asset Health",
          iconOk: "\u2713",
          iconWarn: "\u26A0",
          iconFail: "\u2717",
        },
      ],
      n = e.createEl("div", { cls: "paperforge-health-matrix" });
    for (let a of r) {
      let o = t[a.key] || "healthy",
        l = n.createEl("div", { cls: "paperforge-health-cell" }),
        c,
        p,
        u;
      (o === "healthy" || o === "ok"
        ? ((c = a.iconOk), (p = "ok"), (u = `${a.label}: OK`))
        : o === "warn" || o === "warning" || o === "degraded"
          ? ((c = a.iconWarn),
            (p = "warn"),
            (u = `${a.label}: Needs Attention`))
          : ((c = a.iconFail), (p = "fail"), (u = `${a.label}: Failed`)),
        l.addClass(p),
        l.setAttribute("title", u),
        l.createEl("div", { cls: "paperforge-health-cell-icon", text: c }),
        l.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: a.label,
        }));
    }
  }
  _renderMaturityGauge(e, t, r) {
    if (t == null || t === void 0) {
      this._renderSkeleton(e);
      return;
    }
    let n = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      a = n.createEl("div", { cls: "gauge-track" }),
      o = 4,
      l = Math.max(1, Math.min(o, Math.round(t)));
    for (let c = 1; c <= o; c++) {
      let p = a.createEl("div", { cls: "gauge-segment" });
      c <= l && (p.addClass("filled"), p.addClass(`level-${c}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${l} / ${o}` }),
      l < o && r)
    ) {
      let c = typeof r == "string" ? [r] : r;
      if (c.length > 0) {
        let p = n.createEl("ul", { cls: "gauge-blockers" });
        for (let u of c) p.createEl("li", { text: u });
      }
    }
  }
  _renderBarChart(e, t) {
    if (!t || Object.keys(t).length === 0) {
      this._renderEmptyState(e, "No lifecycle data");
      return;
    }
    let r = [
        { key: "indexed", label: "Indexed", cls: "stage-indexed" },
        { key: "pdf_ready", label: "PDF Ready", cls: "stage-pdf-ready" },
        {
          key: "fulltext_ready",
          label: "Fulltext Ready",
          cls: "stage-fulltext-ready",
        },
        { key: "deep_read_done", label: "Deep Read", cls: "stage-deep-read" },
      ],
      n = e.createEl("div", { cls: "paperforge-bar-chart" }),
      a = Math.max(1, ...r.map((o) => t[o.key] || 0));
    for (let o of r) {
      let l = t[o.key] || 0,
        c = (l / a) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: o.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${o.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: l.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return Qr(e);
  }
  _resolveModeForFile(e) {
    if (!e) return { mode: "global", filePath: null, key: null, domain: null };
    let t = e.extension,
      r = e.path;
    if (t === "base")
      return {
        mode: "collection",
        filePath: r,
        key: null,
        domain: e.basename.trim(),
      };
    if (t === "md") {
      let a = this.app.metadataCache.getFileCache(e),
        o = a && a.frontmatter && a.frontmatter.zotero_key;
      if (o) return { mode: "paper", filePath: r, key: o, domain: null };
    }
    if (t === "pdf") {
      let a = this._getCachedIndex();
      for (let o of a) {
        let l = (o.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((l ? l[1] : o.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: o.zotero_key,
            domain: null,
          };
      }
    }
    let n = this._extractZoteroKeyFromPath(r);
    return n
      ? { mode: "paper", filePath: r, key: n, domain: null }
      : { mode: "global", filePath: r, key: null, domain: null };
  }
  _detectAndSwitch() {
    let e = this._resolveModeForFile(this.app.workspace.getActiveFile());
    ((this._currentDomain = e.domain || null),
      (this._currentPaperKey = e.key || null),
      (this._currentPaperEntry = e.key ? this._findEntry(e.key) : null),
      this._switchMode(e.mode, e.filePath));
  }
  _switchMode(e, t) {
    if (this._currentMode === e && this._currentFilePath === t) {
      this._refreshCurrentMode();
      return;
    }
    if (
      ((this._currentMode = e),
      (this._currentFilePath = t),
      (this._techDetailsExpanded = !1),
      !!this._contentEl)
    )
      switch (
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader(e),
        e)
      ) {
        case "global":
          this._renderGlobalMode();
          break;
        case "paper":
          this._renderPaperMode();
          break;
        case "collection":
          this._renderCollectionMode();
          break;
        case "versions":
          this._renderVersionMode();
          break;
      }
  }
  _renderGlobalMode() {
    var ke, ne, Se, Ce, ae, M, _e, fe;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" }),
      t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      a = 0,
      o = 0;
    for (let B of t)
      (B.has_pdf && n++,
        B.ocr_status === "done" && a++,
        B.deep_reading_status === "done" && o++);
    let l = e.createEl("div", { cls: "paperforge-library-snapshot" });
    l.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let c = l.createEl("div", { cls: "paperforge-snapshot-pills" }),
      p = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: a, label: "OCR done" },
        { value: o, label: "deep-read done" },
      ];
    for (let B of p) {
      let N = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (N.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(B.value),
      }),
        N.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + B.label,
        }));
    }
    let u = e.createEl("div", { cls: "paperforge-system-status" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let f = u.createEl("div", { cls: "paperforge-status-grid" }),
      _ = this.app.plugins.plugins.paperforge,
      h = this._loadIndex(),
      g = h && h.items && h.items.length > 0;
    this._renderSystemStatusRow(
      f,
      "Index",
      g ? "healthy" : "missing",
      g ? h.items.length + " entries" : "formal-library.json not found"
    );
    let m =
        ((ke = _ == null ? void 0 : _.settings) == null
          ? void 0
          : ke.system_dir) || "System",
      v = this.app.vault.adapter.basePath,
      b = !1,
      x = "No exports found";
    try {
      let B = Ae.join(v, m, "PaperForge", "exports");
      if (te.existsSync(B)) {
        let N = te.readdirSync(B).filter((Z) => Z.endsWith(".json"));
        ((b = N.length > 0),
          (x = b ? N.length + " export(s)" : "No JSON exports"));
      }
    } catch (B) {}
    this._renderSystemStatusRow(
      f,
      "Zotero Export",
      b ? "healthy" : "missing",
      x
    );
    let E =
        (Se = (ne = this.app.plugins) == null ? void 0 : ne.plugins) == null
          ? void 0
          : Se.paperforge,
      y = this._renderSystemStatusRow(
        f,
        "OCR Token",
        "checking",
        "Checking\u2026"
      );
    xr(v, E == null ? void 0 : E.settings).then(
      (B) => {
        if (!y.isConnected) return;
        let N = y.querySelector(".paperforge-status-dot");
        (N == null || N.classList.toggle("ok", B),
          N == null || N.classList.toggle("fail", !B));
        let Z = y.querySelector(".paperforge-status-detail");
        Z && (Z.textContent = B ? "Configured" : "Not set");
      },
      () => {
        if (!y.isConnected) return;
        let B = y.querySelector(".paperforge-status-detail");
        B && (B.textContent = "Status unavailable");
      }
    );
    let w = (Ce = this.app.vault.adapter.basePath) != null ? Ce : "",
      k =
        (M =
          (ae = _ == null ? void 0 : _.settings) == null
            ? void 0
            : ae.capabilityState) == null
          ? void 0
          : M.memory,
      S = (k == null ? void 0 : k.capability_state) === "ready",
      C =
        (fe =
          (_e = k == null ? void 0 : k.reason) == null ? void 0 : _e.text) !=
        null
          ? fe
          : "Unknown";
    if (
      (this._renderSystemStatusRow(
        f,
        "Memory Layer",
        S ? "healthy" : "fail",
        C
      ),
      !g || !b)
    ) {
      let B = e.createEl("div", { cls: "paperforge-issue-summary" });
      B.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let N = B.createEl("div", { cls: "paperforge-issue-list" });
      (g ||
        N.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Index missing or corrupted",
        }),
        b ||
          N.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }));
      let Z = B.createEl("div", { cls: "paperforge-issue-actions" }),
        I = Z.createEl("button", { cls: "paperforge-contextual-btn" });
      (I.createEl("span", { text: "Run Doctor" }),
        I.addEventListener("click", () => {
          let F = ge.find((ee) => ee.id === "paperforge-doctor");
          F && this._runAction(F, I);
        }));
      let W = Z.createEl("button", { cls: "paperforge-contextual-btn" });
      (W.createEl("span", { text: "Repair Issues" }),
        W.addEventListener("click", () => {
          let F = ge.find((ee) => ee.id === "paperforge-repair");
          F && this._runAction(F, W);
        }));
    }
    let D = e.createEl("div", { cls: "paperforge-global-actions" });
    D.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let P = D.createEl("div", { cls: "paperforge-global-actions-row" }),
      L = P.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (L.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      L.createEl("span", { text: "Open Literature Hub" }),
      L.addEventListener("click", () => {
        var Z;
        let B =
            ((Z = _ == null ? void 0 : _.settings) == null
              ? void 0
              : Z.base_dir) || "Bases",
          N = this.app.vault.getAbstractFileByPath(B);
        if (N) {
          let I = null;
          if (
            (N.children && (I = N.children.find((W) => W.extension === "base")),
            I)
          ) {
            let W = this.app.workspace.getLeaf(!1);
            W && W.openFile(I);
          } else new O.Notice("[!!] No .base file found in " + B, 6e3);
        } else new O.Notice("[!!] Base directory not found: " + B, 6e3);
      }));
    let K = P.createEl("button", { cls: "paperforge-contextual-btn" });
    (K.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      K.createEl("span", { text: "Sync Library" }),
      K.addEventListener("click", () => {
        this._runLibrarySync();
      }));
    let X = P.createEl("button", { cls: "paperforge-contextual-btn" });
    (X.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      X.createEl("span", { text: "Run OCR" }),
      X.addEventListener("click", () => {
        let B = ge.find((N) => N.id === "paperforge-ocr");
        B && this._runAction(B, X);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let a = e.createEl("div", { cls: "paperforge-status-row" });
    return (
      a
        .createEl("span", { cls: "paperforge-status-dot" })
        .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      a.createEl("span", { cls: "paperforge-status-label", text: t }),
      a.createEl("span", { cls: "paperforge-status-detail", text: n || "" }),
      a
    );
  }
  _renderPaperMode() {
    let e = this._currentPaperEntry,
      t = this._currentPaperKey;
    if (!this._contentEl) return;
    if (!t) {
      this._renderEmptyState(this._contentEl, "No paper data available.");
      return;
    }
    if (!e) {
      this._contentEl.createEl("div", {
        cls: "paperforge-content-placeholder",
        text: 'Paper "' + t + '" not found in canonical index. Sync first.',
      });
      return;
    }
    let r = this._contentEl.createEl("div", { cls: "paperforge-paper-view" }),
      n = r.createEl("div", { cls: "paperforge-paper-header" });
    n.createEl("div", {
      cls: "paperforge-paper-title pf-copy",
      text: e.title || "Untitled",
    }).addEventListener("click", () => {
      (navigator.clipboard.writeText(e.title || ""),
        new O.Notice("Title copied"));
    });
    let o = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      o.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        o.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let l = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = l.createEl("div", { cls: "paperforge-status-strip-left" }),
      p = l.createEl("div", { cls: "paperforge-status-strip-right" }),
      u = [
        { key: "pdf", label: "PDF", ok: e.has_pdf === !0 },
        {
          key: "ocr",
          label: "OCR",
          ok: e.ocr_status === "done",
          pending: ["pending", "queued", "processing"].includes(
            e.ocr_status || ""
          ),
          fail: ["failed", "blocked", "done_incomplete", "nopdf"].includes(
            e.ocr_status || ""
          ),
        },
        {
          key: "deep",
          label: "\u7CBE\u8BFB",
          ok: e.deep_reading_status === "done",
        },
      ];
    for (let _ of u) {
      let h = c.createEl("span", { cls: "paperforge-status-pill" }),
        g = "pending";
      (_.ok ? (g = "ok") : _.fail ? (g = "fail") : _.pending && (g = "pending"),
        h.addClass(g));
      let m = _.ok ? "\u2713" : _.fail ? "\u2717" : "\u25CB";
      (h.createEl("span", { cls: "paperforge-status-pill-icon", text: m }),
        h.createEl("span", { text: " " + _.label }));
    }
    if (e.pdf_path) {
      let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (_.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        _.createEl("span", { text: "\u6253\u5F00 PDF" }),
        _.addEventListener("click", () => {
          var x, E, y;
          let h = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            g = h ? h[1] : e.pdf_path;
          if (this.app.vault.getAbstractFileByPath(g)) {
            this.app.workspace.openLinkText(g, "");
            return;
          }
          let v =
              (y =
                (E = (x = this.app.vault.adapter).getBasePath) == null
                  ? void 0
                  : E.call(x)) != null
                ? y
                : "",
            b = O.Platform.openPath;
          v && typeof b == "function"
            ? b.call(O.Platform, Ae.join(v, g))
            : new O.Notice("[!!] PDF not found: " + g, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (_.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        _.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        _.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (f.createEl("span", { text: s("version_panel_title") }),
      f.addEventListener("click", () => {
        let _ = t,
          h = this.app.vault.adapter.basePath,
          g = we(h),
          m = nt(h, _);
        if (m && m.versions.length > 0) {
          new Fe(
            this.app,
            h,
            _,
            m.versions.map((E) => ({
              label: E.label,
              created_at: E.created_at,
              source: E.source,
              renderer_version: E.renderer_version,
              fulltext_size: E.fulltext_size,
            })),
            m.currentLabel
          ).open();
          return;
        }
        let v = Ae.join(g.ocrDir, _, "backups");
        if (!te.existsSync(v)) return;
        let b = te
          .readdirSync(v)
          .filter((E) => E.startsWith("fulltext.pre-rebuild"))
          .sort();
        if (b.length === 0) return;
        let x = b.map((E) => {
          let y = E.replace("fulltext.pre-rebuild.", "").replace(/\.md$/, ""),
            w =
              y.length >= 16
                ? y.slice(0, 4) +
                  "-" +
                  y.slice(4, 6) +
                  "-" +
                  y.slice(6, 8) +
                  "T" +
                  y.slice(9, 11) +
                  ":" +
                  y.slice(11, 13) +
                  ":" +
                  y.slice(13, 15) +
                  "Z"
                : y,
            k = 0;
          try {
            k = te.statSync(Ae.join(v, E)).size;
          } catch (S) {}
          return {
            label: "backup-" + y,
            created_at: w,
            source: "pre-rebuild",
            fulltext_size: k,
          };
        });
        new Fe(this.app, h, _, x, "").open();
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let _ = r.createEl("div", { cls: "paperforge-complete-row" });
      (_.createEl("span", { text: "\u2713" }),
        _.createEl("span", {
          text: "\u5DF2\u5B8C\u6210\uFF0C\u53EF\u76F4\u63A5\u4F7F\u7528",
        }));
    } else this._renderNextStepCard(r, e, t);
    (this._renderRecentDiscussionCard(r, e),
      this._renderPaperTechnicalDetails(r, e));
  }
  _renderPaperOverviewCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-paper-overview" });
    r.createEl("div", { cls: "paperforge-paper-overview-header" }).createEl(
      "span",
      {
        cls: "paperforge-paper-overview-title",
        text: "\u6587\u7AE0\u6982\u89C8",
      }
    );
    let a = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      o = a.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let l = this.app.vault.getAbstractFileByPath(t.note_path);
      l
        ? this.app.vault
            .read(l)
            .then((c) => {
              let p = this._extractOverviewFromNote(c);
              if (p) {
                let u = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((o.setText(u), p.length > 200)) {
                  let f = a.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    _ = f.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  _.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let h = !1;
                  f.addEventListener("click", () => {
                    (o.setText(h ? u : p),
                      (_.innerHTML = h
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (h = !h));
                  });
                }
              } else
                o.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              o.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : o.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else o.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
  }
  _extractOverviewFromNote(e) {
    if (!e) return null;
    let t = e.indexOf("## \u{1F50D} \u7CBE\u8BFB");
    if (t === -1) return null;
    let r = e.slice(t),
      n = [
        "**\u4E00\u53E5\u8BDD\u603B\u89C8:**",
        "**\u4E00\u53E5\u8BDD\u603B\u89C8**",
        "**\u6587\u7AE0\u6458\u8981:**",
        "**\u6587\u7AE0\u6458\u8981**",
      ];
    for (let l of n) {
      let c = r.indexOf(l);
      if (c !== -1) {
        let p = r.slice(c + l.length),
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          f = p.length;
        for (let g of u) {
          let m = p.indexOf(g);
          m !== -1 && m < f && (f = m);
        }
        let _ = p.indexOf(`

`);
        _ !== -1 && _ < f && (f = _);
        let h = p.slice(0, f).trim();
        return (
          h.startsWith("**") && (h = h.slice(2)),
          h.endsWith("**") && (h = h.slice(0, -2)),
          h || null
        );
      }
    }
    let a = r.indexOf(`
`);
    if (a === -1) return null;
    let o = r
      .slice(a + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !o || o.startsWith("###") || o.startsWith("##")
      ? null
      : o.length > 300
        ? o.slice(0, 300) + "..."
        : o;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      o = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(o)
      .then((l) => {
        if (l) return this.app.vault.adapter.read(o);
      })
      .then(async (l) => {
        if (!l) return;
        let c = this._parseDiscussionMD(l);
        if (!c || c.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let f of c) {
          let _ = r.createEl("div", { cls: "paperforge-discussion-item" }),
            h = _.createEl("div", { cls: "paperforge-discussion-q" });
          (h.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            h.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: f.question,
            }));
          let g = _.createEl("div", { cls: "paperforge-discussion-a" }),
            m = !1;
          if (
            (f.answer &&
              f.answer.length > 500 &&
              ((m = !0), g.classList.add("paperforge-discussion-a-collapsed")),
            await O.MarkdownRenderer.render(
              this.app,
              f.answer || "",
              g,
              o,
              this
            ),
            m)
          ) {
            let v = !1;
            ((_.style.cursor = "pointer"),
              _.addEventListener("click", () => {
                ((v = !v),
                  g.classList.toggle("paperforge-discussion-a-collapsed", !v),
                  g.classList.toggle("paperforge-discussion-a-expanded", v));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (f) => {
          (f.preventDefault(),
            this.app.vault.getAbstractFileByPath(o)
              ? this.app.workspace.openLinkText(o, "")
              : new O.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((l) => {
        console.error("PaperForge: discussion.md read error", o, l.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      a = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let o of a) {
      let l = o.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!l) continue;
      let c = o.substring(0, l.index).trim(),
        p = o.substring(l.index + 3 + 4).trim();
      n.push({ question: c, answer: p });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      a = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      o = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((o.style.display = "none"),
      this._techDetailsExpanded
        ? ((o.style.display = "block"),
          a.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : a.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      a.addEventListener("click", () => {
        let _ = o.style.display !== "none";
        ((o.style.display = _ ? "none" : "block"),
          a.setText(
            _
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !_));
      }));
    let l = o.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let _ of c) {
      let h = l.createEl("label", { cls: "paperforge-workflow-toggle" }),
        g = h.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((g.checked = t[_.key] === !0),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: _.label,
        }),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: _.hint,
        }),
        g.addEventListener("change", async () => {
          let m = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!m) {
            new O.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let v = g.checked;
          (await this.app.fileManager.processFrontMatter(m, (b) => {
            b[_.key] = v;
          }),
            this._patchCachedEntry(r, { [_.key]: v }),
            (this._currentPaperEntry = wt(this._currentPaperEntry, {
              [_.key]: v,
            })));
        }));
    }
    let p = t.health || {},
      u = [
        ["PDF Health", p.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", p.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      f = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [_, h] of u) {
      let g = o.createEl("div", { cls: "paperforge-technical-row" });
      g.createEl("span", { cls: "paperforge-technical-label", text: _ });
      let m = g.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(h),
      });
      f.has(_) &&
        h &&
        h !== "\u2014" &&
        (m.addClass("pf-copy"),
        m.addEventListener("click", () => {
          (navigator.clipboard.writeText(h), new O.Notice(_ + " copied"));
        }));
    }
    r && this._renderQualitySection(o, r);
  }
  _renderQualitySection(e, t) {
    let r = e.createEl("div", { cls: "paperforge-quality-section" }),
      n = r.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      a = r.createEl("div", { cls: "paperforge-quality-body" });
    ((a.style.display = "none"),
      n.setText("Render Quality \u25B8"),
      n.addEventListener("click", () => {
        let o = a.style.display !== "none";
        ((a.style.display = o ? "none" : "block"),
          n.setText(o ? "Render Quality \u25B8" : "Render Quality \u25BE"),
          !o && !a.dataset.loaded && this._loadQualitySection(a, t));
      }));
  }
  async _loadQualitySection(e, t) {
    var a, o, l, c, p;
    let r = this._getClient();
    if (!r) {
      (e.empty(),
        (e.dataset.loaded = "1"),
        e.createEl("p", {
          cls: "pf-status-warn",
          text: "Backend unavailable",
        }));
      return;
    }
    ((e.dataset.loaded = "1"), e.empty());
    let n = e.createEl("p", {
      cls: "pf-status-checking",
      text: "Checking render consistency\u2026",
    });
    try {
      let u = await r.renderAudit(t),
        _ = ((a = u == null ? void 0 : u.papers) != null ? a : []).find(
          (v) => v.paper_key === t
        ),
        h = String((o = u == null ? void 0 : u.state) != null ? o : "UNKNOWN");
      (n.setText(`Render consistency: ${h}`),
        n.setAttr("class", h === "CLEAN" ? "pf-status-ok" : "pf-status-warn"));
      let g = (l = _ == null ? void 0 : _.issues) != null ? l : [];
      if (g.length > 0) {
        let v = e.createEl("ul", { cls: "paperforge-quality-issues" });
        for (let b of g.slice(0, 5))
          v.createEl("li", {
            text: String(
              (p = (c = b.message) != null ? c : b.code) != null
                ? p
                : JSON.stringify(b)
            ),
          });
        g.length > 5 &&
          v.createEl("li", { text: `\u2026and ${g.length - 5} more` });
      }
      let m = e.createDiv({ cls: "paperforge-quality-staging" });
      this._renderQualityStaging(m, t, e);
    } catch (u) {
      n.setText(
        `Render audit failed: ${u instanceof Error ? u.message : String(u)}`
      );
    }
  }
  _renderQualityStaging(e, t, r) {
    var a;
    e.empty();
    let n =
      ((a = this._qualityStagingCache) == null ? void 0 : a.key) === t
        ? this._qualityStagingCache.data
        : null;
    if (!n) {
      e.createEl("button", {
        cls: "pf-action-btn",
        text: "Stage R/P proposals",
      }).addEventListener("click", () => {
        this._loadQualityStaging(e, t, r);
      });
      return;
    }
    this._renderQualityStagingData(e, t, n, r);
  }
  async _loadQualityStaging(e, t, r) {
    let n = this._getClient();
    if (!n) {
      (e.empty(),
        e.createEl("p", {
          cls: "pf-status-warn",
          text: "Backend unavailable",
        }));
      return;
    }
    (e.empty(),
      e.createEl("p", {
        cls: "pf-status-checking",
        text: "Staging R/P proposals (isolated tmp root)\u2026",
      }));
    try {
      let a = await n.renderReconcileStaging(t);
      ((this._qualityStagingCache = { key: t, data: a }),
        this._renderQualityStagingData(e, t, a, r));
    } catch (a) {
      (e.empty(),
        e.createEl("p", {
          cls: "pf-status-warn",
          text: `Staging failed: ${a instanceof Error ? a.message : String(a)}`,
        }));
    }
  }
  _renderQualityStagingData(e, t, r, n) {
    var p, u, f, _, h, g, m, v, b;
    e.empty();
    let o = ((p = r.r_details) != null ? p : []).filter(
      (x) => typeof x.object_id == "string" && x.object_id
    );
    if (o.length > 0) {
      e.createEl("h4", { text: "R exact repairs" });
      for (let x of o) {
        let E = String(x.object_id),
          y = e.createDiv({ cls: "paperforge-quality-r-row" }),
          w = x.staged === !0;
        (y.createEl("span", { text: `${E} ${w ? "(staged)" : "(unstaged)"}` }),
          x.image && this._renderPreviewArtifact(y, String(x.image)));
        let k = y.createEl("button", { cls: "pf-action-btn", text: "Promote" });
        (w || (k.disabled = !0),
          k.addEventListener("click", () => {
            this._promoteRObject(n, t, E);
          }));
      }
    }
    let c = ((u = r.p_details) != null ? u : []).filter(
      (x) => typeof x.final_plan_hash == "string" && x.final_plan_hash
    );
    if (c.length > 0) {
      e.createEl("h4", {
        text: "P proposals \u2014 review the candidate before accepting",
      });
      for (let x of c) {
        let E = String((f = x.label) != null ? f : ""),
          y = String(x.final_plan_hash),
          w = e.createDiv({ cls: "paperforge-quality-p-card" });
        w.createEl("div", {
          text: `Figure ${E} \u2014 page ${String((_ = x.page) != null ? _ : "?")}, decision: ${String((h = x.decision) != null ? h : "?")}, staged: ${x.staged === !0}`,
        });
        let k = x.caption_text;
        typeof k == "string" &&
          k.trim() &&
          w.createEl("div", { cls: "paperforge-quality-caption", text: k });
        let S = (g = x.member_refs) != null ? g : [];
        if (S.length > 0) {
          let A = w.createEl("ul", { cls: "paperforge-quality-members" });
          for (let D of S)
            A.createEl("li", {
              text: `p${String((m = D.page) != null ? m : "?")} \xB7 block ${String((v = D.block_id) != null ? v : "?")} \xB7 bbox ${JSON.stringify((b = D.bbox) != null ? b : null)}`,
            });
        }
        (x.preview && this._renderPreviewArtifact(w, String(x.preview)),
          w.createEl("div", {
            cls: "paperforge-quality-plan-hash",
            text: `plan ${y.slice(0, 12)}\u2026`,
          }));
        let C = w.createEl("button", { cls: "pf-action-btn", text: "Accept" });
        (x.staged !== !0 && (C.disabled = !0),
          C.addEventListener("click", () => {
            this._acceptProposalCard(n, t, E, y);
          }));
      }
    }
    o.length === 0 &&
      c.length === 0 &&
      e.createEl("p", { text: "No staged R/P candidates for this paper." });
  }
  _renderPreviewArtifact(e, t) {
    let r = e.createDiv({ cls: "paperforge-quality-preview" }),
      n = r.createEl("img", {
        cls: "paperforge-quality-preview-img",
        attr: {
          src: "file:///" + t.replace(/\\/g, "/").replace(/^\//, ""),
          alt: "Staged preview",
        },
      });
    ((n.onerror = () => (n.style.display = "none")),
      r
        .createEl("button", {
          cls: "pf-action-btn paperforge-quality-preview-open",
          text: "Open preview",
        })
        .addEventListener("click", () => {
          this._openExternalPath(t);
        }));
  }
  _openExternalPath(e) {
    try {
      let { shell: t } = require("electron");
      t.openPath(e);
    } catch (t) {
      window.open(e, "_blank");
    }
  }
  _afterQualityMutation(e, t, r) {
    ((this._qualityStagingCache = null),
      this._loadQualitySection(e, t),
      r &&
        new O.Notice(
          "Authority rejected the action \u2014 re-stage and review the current proposals",
          8e3
        ));
  }
  async _promoteRObject(e, t, r) {
    var a, o, l;
    let n = this._getClient();
    if (n)
      try {
        let c = await n.promoteR(t, [r]),
          p = (c == null ? void 0 : c.ok) === !0;
        (new O.Notice(
          p
            ? `Promoted ${r}`
            : `Promotion rejected: ${String((l = (o = (a = c == null ? void 0 : c.error) == null ? void 0 : a.code) != null ? o : c == null ? void 0 : c.reason) != null ? l : "unknown")}`,
          8e3
        ),
          this._afterQualityMutation(e, t, !p));
      } catch (c) {
        new O.Notice(
          `Promotion failed: ${c instanceof Error ? c.message : String(c)}`,
          8e3
        );
      }
  }
  async _acceptProposalCard(e, t, r, n) {
    var o, l, c;
    let a = this._getClient();
    if (a)
      try {
        let p = await a.acceptProposal(t, r, n),
          u = (p == null ? void 0 : p.ok) === !0;
        (new O.Notice(
          u
            ? `Accepted proposal ${r}`
            : `Acceptance rejected: ${String((c = (l = (o = p == null ? void 0 : p.error) == null ? void 0 : o.code) != null ? l : p == null ? void 0 : p.reason) != null ? c : "unknown")}`,
          8e3
        ),
          this._afterQualityMutation(e, t, !u));
      } catch (p) {
        new O.Notice(
          `Acceptance failed: ${p instanceof Error ? p.message : String(p)}`,
          8e3
        );
      }
  }
  _renderNextStepCard(e, t, r) {
    var c, p;
    let n = t.next_step || "ready",
      a = {
        sync: {
          label: "Sync Needed",
          text: "This paper needs to be synced from Zotero. Click to run sync.",
          actionId: "paperforge-sync",
          icon: "\u21BB",
        },
        ocr: {
          label: "OCR Needed",
          text: "Fulltext is missing but PDF is present. Click to run OCR.",
          actionId: "paperforge-ocr",
          icon: "\u229E",
        },
        repair: {
          label: "Repair Needed",
          text: "State divergence or path errors detected. Click to repair.",
          actionId: "paperforge-repair",
          icon: "\u21BA",
        },
        "rebuild index": {
          label: "Rebuild Needed",
          text: "Index may be stale. Click to run sync to rebuild.",
          actionId: "paperforge-sync",
          icon: "\u21BB",
        },
        "/pf-deep": {
          label: "Ready for Deep Reading",
          text: "Fulltext is ready. Copy /pf-deep command and run in your agent.",
          actionId: null,
          icon: "\u{1F50D}",
        },
        ready: {
          label: "All Set",
          text: "This paper is fully processed and ready for use.",
          actionId: "ready",
          icon: "\u2713",
        },
      },
      o = a[n] || a.ready,
      l = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && l.addClass("ready"),
      l.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      l.createEl("div", { cls: "paperforge-next-step-text", text: o.text }),
      o.actionId && o.actionId !== "ready")
    ) {
      let u = l.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: o.icon + "  " + o.label }),
        u.addEventListener("click", () => {
          if (o.actionId === "paperforge-sync") {
            this._runLibrarySync();
            return;
          }
          let f = ge.find((_) => _.id === o.actionId);
          f && this._runAction(f, u);
        }));
    } else if (n === "/pf-deep") {
      let u = l.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: "\u{1F4CB}  " + s("copy_pf_deep_cmd") }),
        u.addEventListener("click", () => {
          let m = "/pf-deep " + r;
          navigator.clipboard
            .writeText(m)
            .then(() => {
              (u.setText("\u2713  " + s("copied")),
                new O.Notice(m + " copied"));
            })
            .catch(() => {
              new O.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let f =
          ((p =
            (c = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : c.settings) == null
            ? void 0
            : p.agent_platform) || "opencode",
        h =
          {
            opencode: "OpenCode",
            claude: "Claude Code",
            cursor: "Cursor",
            github_copilot: "GitHub Copilot",
            windsurf: "Windsurf",
            codex: "Codex",
            gemini: "Gemini CLI",
            cline: "Cline",
          }[f] || f;
      l.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        s("run_in_agent").replace("{0}", h)
      );
    } else
      n === "ready" &&
        l
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + o.label });
  }
  _openFulltext(e) {
    if (!e) {
      new O.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new O.Notice("[!!] Fulltext file not found: " + e, 6e3);
  }
  _renderCollectionMode() {
    let e = this._currentDomain || "Unknown",
      t = this._filterByDomain(e);
    if (t.length === 0) {
      this._renderGlobalMode();
      return;
    }
    if (!this._contentEl) return;
    let r = this._contentEl.createEl("div", {
        cls: "paperforge-collection-view",
      }),
      n = t.length,
      a = 0,
      o = 0,
      l = 0,
      c = 0,
      p = 0,
      u = 0,
      f = 0;
    for (let E of t) {
      (E.has_pdf && a++,
        E.ocr_status === "done" && o++,
        E.ocr_status === "done" && E.analyze === !0 && l++,
        E.deep_reading_status === "done" && c++);
      let y = E.ocr_status || "";
      y === "pending" || y === "queued"
        ? p++
        : y === "processing"
          ? u++
          : (y === "failed" ||
              y === "blocked" ||
              y === "done_incomplete" ||
              y === "nopdf") &&
            f++;
    }
    r.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: e,
    });
    let h = r.createEl("div", { cls: "paperforge-workflow-overview" });
    h.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let g = h.createEl("div", { cls: "paperforge-workflow-funnel" }),
      m = [
        { value: n, label: "Total" },
        { value: a, label: "PDF Ready" },
        { value: o, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let E = 0; E < m.length; E++) {
      let y = g.createEl("div", { cls: "paperforge-workflow-stage" });
      (y.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(m[E].value),
      }),
        y.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: m[E].label,
        }),
        E < m.length - 1 &&
          g.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (p + u + o + f > 0) {
      let E = r.createEl("div", { cls: "paperforge-ocr-section" }),
        y = E.createEl("div", { cls: "paperforge-collection-ocr-header" });
      y.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let w = y.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (w.addClass("active"), w.setText("Processing"))
        : p > 0
          ? w.setText("Pending")
          : (w.addClass("idle"), w.setText("Idle"));
      let k = E.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && k.addClass("paperforge-processing");
      let S = p + u + o + f,
        C = [
          { cls: "pending", count: p },
          { cls: "active", count: u },
          { cls: "done", count: o },
          { cls: "failed", count: f },
        ];
      for (let P of C)
        if (P.count > 0) {
          let L = ((P.count / S) * 100).toFixed(1);
          k.createEl("div", {
            cls: `paperforge-progress-seg ${P.cls}`,
            attr: { style: `width:${L}%` },
          });
        }
      let A = E.createEl("div", { cls: "paperforge-ocr-counts" }),
        D = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: o, label: "Done" },
          { cls: "failed", value: f, label: "Attention" },
        ];
      for (let P of D) {
        let L = A.createEl("div", { cls: "paperforge-ocr-count" });
        (L.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: P.value.toString(),
        }),
          L.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: P.label,
          }));
      }
    }
    let v = r.createEl("div", { cls: "paperforge-collection-actions" }),
      b = v.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (b.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      b.createEl("span", { text: "Run OCR" }),
      b.addEventListener("click", () => {
        let E = ge.find((y) => y.id === "paperforge-ocr");
        E && this._runAction(E, b);
      }));
    let x = v.createEl("button", { cls: "paperforge-contextual-btn" });
    (x.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      x.createEl("span", { text: "Sync Library" }),
      x.addEventListener("click", () => {
        this._runLibrarySync();
      }),
      this.renderSearchSection(r));
  }
  _refreshCurrentMode() {
    if (!(!this._currentMode || !this._contentEl)) {
      (this._contentEl.empty(),
        this._contentEl.addClass("switching"),
        this._invalidateIndex(),
        (this._currentPaperEntry = this._currentPaperKey
          ? this._findEntry(this._currentPaperKey)
          : null),
        this._renderModeHeader(this._currentMode));
      try {
        switch (this._currentMode) {
          case "global":
            this._renderGlobalMode();
            break;
          case "paper":
            this._renderPaperMode();
            break;
          case "collection":
            this._renderCollectionMode();
            break;
          case "versions":
            this._renderVersionMode();
            break;
        }
      } finally {
        setTimeout(() => {
          this._contentEl && this._contentEl.removeClass("switching");
        }, 50);
      }
    }
  }
  _switchToVersionMode(e) {
    let r = this.app.vault.adapter.basePath,
      n = typeof r == "string" ? r : "";
    if (!n) {
      new O.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = qt(n)),
      (this._versionFilter = ""),
      (this._currentMode = "versions"),
      (this._currentFilePath = null),
      (this._techDetailsExpanded = !1),
      this._contentEl &&
        (this._contentEl.empty(),
        this._contentEl.removeClass("switching"),
        this._renderModeHeader("versions"),
        this._renderVersionMode()));
  }
  _renderVersionMode() {
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", {
        cls: "paperforge-version-panel",
      }),
      r = this.app.vault.adapter.basePath,
      n = typeof r == "string" ? r : "";
    if (!n) {
      e.createEl("div", {
        cls: "paperforge-status-error",
        text: "Could not determine vault path",
      });
      return;
    }
    (!this._versionPapers || this._versionPapers.length === 0) &&
      (this._versionPapers = qt(n));
    let a = e.createEl("div", { cls: "paperforge-version-left" }),
      o = e.createEl("div", { cls: "paperforge-version-right" }),
      l = a.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: s("version_filter_placeholder") },
      });
    l.value = this._versionFilter;
    let c = a.createEl("div", { cls: "paperforge-version-paper-list" }),
      p = () => {
        c.empty();
        let b = this._versionFilter.toLowerCase(),
          x = this._versionPapers
            ? this._versionPapers.filter(
                (y) =>
                  !b ||
                  y.key.toLowerCase().includes(b) ||
                  y.title.toLowerCase().includes(b)
              )
            : [];
        if (x.length === 0) {
          c.createEl("div", {
            cls: "paperforge-meta",
            text: s("version_no_backups"),
          });
          return;
        }
        let E = c.createEl("div", {
          cls: "paperforge-meta",
          text: s("version_papers_count").replace("{n}", String(x.length)),
        });
        for (let y of x) {
          let w = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            k = w.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: y.title,
            }),
            S = w.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: y.versions.map((C) => C.label).join(" "),
            });
          w.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((C) => C.removeClass("selected")),
              w.addClass("selected"),
              f(y));
          });
        }
      };
    l.addEventListener("input", () => {
      ((this._versionFilter = l.value), p());
    });
    let u = o.createEl("div", { cls: "paperforge-version-timeline-area" }),
      f = (b) => {
        if (
          (u.empty(),
          u
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: b.title }),
          b.versions.length === 0)
        ) {
          u.createEl("div", {
            cls: "paperforge-meta",
            text: s("version_no_backups"),
          });
          return;
        }
        let E = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let y of b.versions) {
          let w = y.label === b.currentLabel,
            k = E.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (w ? " paperforge-version-current" : ""),
            }),
            S = k.createEl("div", { cls: "paperforge-version-dot" }),
            C = k.createEl("div", { cls: "paperforge-version-content" }),
            A = C.createEl("div", { cls: "paperforge-version-label-row" });
          (A.createEl("span", {
            cls: "paperforge-version-label",
            text: y.label,
          }),
            w &&
              A.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: s("version_current"),
              }));
          let D = y.created_at ? y.created_at.slice(0, 10) : "";
          C.createEl("div", {
            cls: "paperforge-meta",
            text: D + " \u2014 " + y.source,
          });
          let P = y.fulltext_size
            ? y.fulltext_size > 1024
              ? (y.fulltext_size / 1024).toFixed(0) + "KB"
              : y.fulltext_size + "B"
            : "";
          P && C.createEl("div", { cls: "paperforge-meta", text: P });
          let L = C.createEl("div", { cls: "paperforge-version-actions" });
          (L.createEl("button", {
            cls: "pf-btn-primary",
            text: s("version_restore_btn"),
          }).addEventListener("click", () => {
            yt(n, b.key, y.label)
              ? new O.Notice(
                  s("version_restore_done").replace("{label}", y.label)
                )
              : new O.Notice("Restore failed", 6e3);
          }),
            b.versions.length > 1 &&
              !w &&
              L.createEl("button", {
                cls: "pf-btn-secondary",
                text: s("version_compare_btn"),
              }).addEventListener("click", () => {
                h(b, y.label, b.currentLabel);
              }));
        }
      },
      _ = o.createEl("div", { cls: "paperforge-version-compare" });
    _.style.display = "none";
    let h = (b, x, E) => {
        let y = en(n, b.key, x, E);
        ((_.style.display = "block"), _.empty());
        let w = _.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (w.createEl("span", {
            cls: "pf-title",
            text: s("version_compare_title")
              .replace("{vA}", x)
              .replace("{vB}", E),
          }),
          w.createEl("span", {
            cls: "paperforge-meta",
            text: s("version_compare_paragraphs").replace(
              "{n}",
              String(y.length)
            ),
          }),
          y.length === 0)
        ) {
          _.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let k = _.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let S of y) {
          let C = k.createEl("div", { cls: "paperforge-version-diff-row" }),
            A =
              S.type === "added" ? "[+]" : S.type === "removed" ? "[-]" : "[~]",
            D = S.heading || "paragraph " + (S.paragraphIndex + 1);
          (C.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: A + " " + D,
          }),
            S.oldText &&
              C.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: S.oldText.slice(0, 200),
              }),
            S.newText &&
              C.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: S.newText.slice(0, 200),
              }));
        }
      },
      g = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      m = g.createEl("button", {
        cls: "pf-btn-primary",
        text: s("version_restore_selected"),
      }),
      v = g.createEl("button", {
        cls: "pf-btn-secondary",
        text: s("version_clear_old").replace("{size}", ""),
      });
    p();
  }
  renderSearchSection(e) {
    ((this._searchContainer = e.createEl("div", {
      cls: "paperforge-search-section",
    })),
      this._searchContainer
        .createEl("div", { cls: "paperforge-search-header" })
        .createEl("span", { cls: "pf-label", text: "Search" }));
    let r = this._searchContainer.createEl("div", {
        cls: "paperforge-search-input-row",
      }),
      n = r.createEl("span", { cls: "paperforge-search-mode", text: "M" });
    ((this._searchInput = r.createEl("input", {
      cls: "paperforge-search-input",
      attr: {
        type: "text",
        placeholder: "Search papers... (@ for deep search)",
      },
    })),
      (this._searchResultsEl = this._searchContainer.createEl("div", {
        cls: "paperforge-search-results",
      })),
      (this._searchInput.placeholder = s("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var o;
        let a = ((o = this._searchInput) == null ? void 0 : o.value) || "";
        if (
          (a.startsWith("@") && !a.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = s(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = s(
                  "retrieval_search_placeholder"
                ))),
          clearTimeout(this._searchTimer),
          !a.trim())
        ) {
          ((this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        a.startsWith("@") ||
          (this._searchTimer = setTimeout(() => {
            this.executeSearch();
          }, 200));
      }),
      this._searchInput.addEventListener("keydown", (a) => {
        var o, l;
        if (a.key === "Escape") {
          (a.preventDefault(),
            this._searchInput &&
              ((this._searchInput.value = ""), this._searchInput.blur()),
            (this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        if (a.key === "ArrowDown" || a.key === "ArrowUp") {
          if (
            this._searchState !== "results" ||
            !((o = this._searchResults) != null && o.length)
          )
            return;
          a.preventDefault();
          let c = this._searchResults.length;
          a.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                c - 1
              ))
            : (this._searchActiveIndex = Math.max(
                this._searchActiveIndex - 1,
                -1
              ));
          let p =
            (l = this._searchResultsEl) == null
              ? void 0
              : l.querySelectorAll(".paperforge-search-result-card");
          p &&
            p.forEach((u, f) => {
              f === this._searchActiveIndex
                ? (u.setAttribute("aria-selected", "true"),
                  u.classList.add("active"))
                : (u.setAttribute("aria-selected", "false"),
                  u.classList.remove("active"));
            });
          return;
        }
        if (a.key === "Enter" && a.ctrlKey) {
          (a.preventDefault(),
            this._searchTimer &&
              (clearTimeout(this._searchTimer), (this._searchTimer = void 0)));
          let c = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = c));
          return;
        }
        a.key === "Enter" &&
          (a.preventDefault(),
          this._searchTimer &&
            (clearTimeout(this._searchTimer), (this._searchTimer = void 0)),
          this.executeSearch());
      }));
  }
  _renderSearchState() {
    if (!this._searchResultsEl) return;
    switch (
      (this._searchResultsEl.empty(),
      this._searchResultsEl.removeAttribute("role"),
      this._searchResultsEl.removeAttribute("aria-live"),
      this._searchInput && (this._searchInput.disabled = !1),
      this._searchState)
    ) {
      case "idle":
        break;
      case "searching": {
        let t = this._searchMode === "@";
        (this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-loading",
          text: t
            ? s("retrieval_searching_deep")
            : s("retrieval_searching_metadata"),
        }),
          this._searchResultsEl.setAttr("aria-live", "polite"),
          t && this._searchInput && (this._searchInput.disabled = !0));
        break;
      }
      case "results": {
        (this._searchResultsEl.setAttr("role", "listbox"),
          this._searchResultsEl.setAttr("aria-live", "polite"),
          this._searchResults &&
            this._renderSearchResultsList(
              this._searchResults,
              this._searchMode === "@"
            ),
          setTimeout(() => {
            var r;
            let t =
              (r = this._searchResultsEl) == null
                ? void 0
                : r.querySelector(".paperforge-search-result-card");
            t && t instanceof HTMLElement && t.focus();
          }, 100));
        break;
      }
      case "empty": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-empty",
        });
        (t.setAttr("role", "alert"),
          t.createEl("div", { text: s("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: s("retrieval_empty_tips"),
          }));
        break;
      }
      case "vectors-not-built": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: s("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: s("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: s("retrieval_open_vector_settings"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let a = n.openTab;
            typeof a == "function" && a.call(n, "paperforge");
          }
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      case "backend-unavailable": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("error-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: s("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: s("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: s("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let o = this.app.vault.adapter.basePath;
          if (typeof o != "string") return;
          let l = this._resolvePython();
          if (!l) return;
          let { path: c, args: p = [] } = l;
          (0, Ee.spawn)(c, [...p, "-m", "paperforge", "doctor"], {
            cwd: o,
            stdio: "inherit",
          });
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: s("retrieval_retry"),
            })
            .addEventListener("click", () => {
              this.executeSearch();
            }),
          setTimeout(() => {
            n.focus();
          }, 100));
        break;
      }
      case "timeout": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: s("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: s("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: s("retrieval_retry"),
        });
        (r.addEventListener("click", () => {
          this.executeSearch();
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      case "model-changed": {
        let t = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-state-card",
          attr: { role: "alert" },
        });
        (t.addClass("warning-soft"),
          t.createEl("div", {
            cls: "paperforge-search-state-title",
            text: s("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: s("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: s("retrieval_rebuild_vectors"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let a = n.openTab;
            typeof a == "function" && a.call(n, "paperforge");
          }
        }),
          setTimeout(() => {
            r.focus();
          }, 100));
        break;
      }
      default: {
        (this._searchResultsEl
          .createEl("div", {
            cls: "paperforge-search-state-card",
            text: s("retrieval_internal_error"),
            attr: { role: "alert" },
          })
          .addClass("error-soft"),
          setTimeout(() => {
            this._searchInput && this._searchInput.focus();
          }, 100));
        break;
      }
    }
  }
  async executeSearch() {
    var o;
    if (!this._searchInput || !this._searchResultsEl) return;
    let e = this._searchInput.value.trim();
    if (!e) return;
    let t = this._searchMode === "@" || e.startsWith("@"),
      r = t ? e.replace(/^@\s*/, "").trim() : e;
    if (!r) return;
    let n = t ? "retrieve" : "search";
    ((this._searchState = "searching"),
      (this._searchResults = null),
      (this._searchActiveIndex = -1),
      this._renderSearchState());
    let a = this._getClient();
    if (!a) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    try {
      let l = t ? await a.retrieve(r, { deep: !0 }) : await a.search(r);
      ((this._searchResults = l),
        (this._searchState = l.length > 0 ? "results" : "empty"),
        this._renderSearchState());
    } catch (l) {
      let c = hr(String((o = l == null ? void 0 : l.message) != null ? o : l));
      ((this._searchState = this._mapErrorToSearchState(c.type)),
        this._renderSearchState());
    }
  }
  _mapErrorToSearchState(e) {
    switch (e) {
      case "vectors_not_built":
        return "vectors-not-built";
      case "vectors_corrupted":
        return "vectors-not-built";
      case "backend_unavailable":
        return "backend-unavailable";
      case "model_changed":
        return "model-changed";
      case "timeout":
        return "timeout";
      case "no_python":
      case "python_missing":
      case "import_failed":
      case "version_mismatch":
        return "backend-unavailable";
      default:
        return "backend-unavailable";
    }
  }
  _renderSearchResultsList(e, t) {
    if (!this._searchResultsEl) return;
    if (
      (this._searchResultsEl.setAttr("aria-live", "polite"), e.length === 0)
    ) {
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-empty",
        text: "No results found.",
      });
      return;
    }
    let r = this._searchResultsEl.createEl("div", {
      cls: "paperforge-search-results-header",
    });
    (r
      .createEl("span", {
        text: s("retrieval_results_count")
          .replace("{n}", String(e.length))
          .replace("{s}", e.length !== 1 ? "s" : ""),
      })
      .setAttr("aria-live", "polite"),
      r.createEl("span", {
        cls: "paperforge-search-mode",
        text: t ? "@" : "M",
      }));
    for (let a = 0; a < e.length; a++) {
      let o = e[a];
      if (!o || typeof o != "object") continue;
      let l = o,
        c = a === this._searchActiveIndex,
        p = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": c ? "true" : "false",
            "aria-posinset": String(a + 1),
            "aria-setsize": String(e.length),
          },
        });
      c && p.addClass("active");
      let u =
        typeof l.title == "string"
          ? l.title
          : typeof l.file_name == "string"
            ? l.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let f = typeof l.zotero_key == "string" ? l.zotero_key : "",
        _ =
          typeof l.main_note_path == "string" && l.main_note_path
            ? l.main_note_path
            : null,
        h = typeof l.note_path == "string" && l.note_path ? l.note_path : null,
        g = _ || h;
      if (!g && f) {
        let b = this._getCachedIndex().find(
          (x) =>
            x !== null &&
            typeof x == "object" &&
            "zotero_key" in x &&
            x.zotero_key === f
        );
        if (b && typeof b == "object") {
          let x = b;
          g =
            typeof x.main_note_path == "string" && x.main_note_path
              ? x.main_note_path
              : typeof x.note_path == "string" && x.note_path
                ? x.note_path
                : null;
        }
      }
      (g
        ? p.addEventListener("click", (v) => {
            let b = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", b);
          })
        : p.addEventListener("click", () => {
            new O.Notice("[!!] Note not found: " + (f || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (v) => {
          if (v.key === "Enter" && g) {
            v.preventDefault();
            let b = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", b);
          }
        }));
      let m = p.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof l.first_author == "string" &&
          l.first_author &&
          m.createEl("span", {
            cls: "paperforge-search-result-author",
            text: l.first_author,
          }),
        typeof l.journal == "string" &&
          l.journal &&
          m.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: l.journal,
          }),
        l.score !== void 0)
      ) {
        let v = l.score,
          b = typeof v == "number" ? v.toFixed(3) : String(v);
        m.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + b,
        });
      }
      if (
        (typeof l.domain == "string" &&
          l.domain &&
          p.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: l.domain,
          }),
        typeof l.abstract == "string" && l.abstract)
      ) {
        let v = l.abstract;
        p.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: v.length > 200 ? v.slice(0, 200) + "..." : v,
        });
      }
      if (t && typeof l.text == "string" && l.text) {
        let v = l.text;
        p.createEl("div", {
          cls: "paperforge-search-result-source",
          text: v.length > 300 ? v.slice(0, 300) + "..." : v,
        });
      }
    }
  }
  _renderSearchError(e) {
    this._searchResultsEl &&
      (this._searchResultsEl.empty(),
      this._searchResultsEl.createEl("div", {
        cls: "paperforge-search-error",
        text: e,
      }));
  }
  async _runLibrarySync() {
    if (this._librarySyncRunning) return;
    let e = this._getClient();
    if (!e) {
      new O.Notice("[!!] PaperForge backend unavailable", 6e3);
      return;
    }
    let t = this.app.vault.adapter.basePath;
    ((this._librarySyncRunning = !0),
      this._showMessage("Syncing library...", "running"));
    let r = !1;
    try {
      let n = await e.sync();
      ((r = (n == null ? void 0 : n.ok) !== !1),
        r
          ? (this._showMessage("[OK] Sync Library: complete", "ok"),
            new O.Notice("Sync complete"),
            Ie(JSON.stringify(n), {
              vaultPath: t != null ? t : "",
              resolveCommand: () => this._resolvePython(),
            }))
          : (this._showMessage("[!!] Sync failed", "error"),
            new O.Notice("[!!] Sync Library failed", 8e3)));
    } catch (n) {
      let a = n instanceof Error ? n.message : String(n);
      (this._showMessage("[!!] " + a, "error"),
        new O.Notice("[!!] Sync failed: " + a, 8e3));
    } finally {
      ((this._librarySyncRunning = !1), (this._cachedStats = null));
      try {
        this._fetchStats(!1);
      } catch (n) {
        console.log("[PF] fetchStats error:", n);
      }
      r &&
        Ye(
          this.app,
          this.app.plugins.plugins.paperforge,
          this.app.vault.adapter.basePath
        );
    }
  }
  async _runAction(e, t) {
    var m, v, b, x, E;
    if (e.disabled) {
      new O.Notice(
        `[i] ${e.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (e.id === "paperforge-ocr") {
      let y =
        (v = (m = this.app.plugins) == null ? void 0 : m.plugins) == null
          ? void 0
          : v.paperforge;
      if (typeof (y == null ? void 0 : y.requestOcrRun) == "function") {
        y.requestOcrRun();
        return;
      }
    }
    if (t.classList.contains("running")) return;
    t.addClass("running");
    let r = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let n = Array.isArray(e.args) ? [...e.args] : [];
    if (e.needsKey) {
      let y = this.app.workspace.getActiveFile(),
        w = null;
      if (y) {
        let k = this.app.metadataCache.getFileCache(y);
        if (
          (k && k.frontmatter && k.frontmatter.zotero_key
            ? (w = k.frontmatter.zotero_key)
            : (w = this._extractZoteroKeyFromPath(y.path)),
          w)
        )
          n = [...n, w];
        else if (k && k.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new O.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new O.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new O.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let a =
        (b = e.timeoutMs) != null
          ? b
          : e.needsFilter
            ? 6e4
            : e.needsKey
              ? 3e4
              : 6e5,
      o = this._resolvePython();
    if (!o) {
      (this._showMessage(
        "[!!] Runtime not available \u2014 open PaperForge Setup",
        "error"
      ),
        new O.Notice(
          "PaperForge runtime is not ready. Opening Setup\u2026",
          6e3
        ));
      let y = this.app.setting;
      (y == null || y.open(),
        (x = y == null ? void 0 : y.openTabById) == null ||
          x.call(y, "paperforge"),
        t.removeClass("running"));
      return;
    }
    let { path: l, args: c = [] } = o,
      p = await me(null, e.commandId),
      u = (E = ot(e.id)) != null ? E : [],
      f = (0, Ee.spawn)(l, [...c, "-m", "paperforge", ...u, ...n], {
        cwd: r,
        timeout: a,
        env: p,
      }),
      _ = [],
      h = Date.now(),
      g = setInterval(() => this._fetchStats(!0), 4e3);
    (f.stdout.on("data", (y) => {
      let w = y
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let k of w) {
        let S = k.trim();
        S &&
          (_.push(S),
          this._showMessage(
            _.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      f.stderr.on("data", (y) => {
        let w = y
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let k of w) {
          if (k.includes("\r") || k.includes("%") || k.includes("\u2588"))
            continue;
          let S = k.trim();
          S &&
            !S.match(/^\d+%|^\|/) &&
            (_.push(S),
            this._showMessage(
              _.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      f.on("close", (y) => {
        (clearInterval(g), t.removeClass("running"));
        let w = ((Date.now() - h) / 1e3).toFixed(1);
        if (y !== 0) {
          let k = _.slice(-3).join(" | ") || "exit code " + y;
          (e.commandId === "repair" || e.commandId === "ocr") && y === 1
            ? (this._showMessage("[WARN] " + k, "running"),
              new O.Notice("[WARN] " + e.commandId + " partial: " + k, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + k, "error"),
              new O.Notice("[!!] " + e.commandId + " failed: " + k, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let k = _.join(`
`);
          if (k.trim())
            try {
              (JSON.parse(k),
                navigator.clipboard
                  .writeText(k)
                  .then(() => {
                    let S = `${w}s \u2014 ${k.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + S, "ok"),
                      new O.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + k.length + " chars"
                      ));
                  })
                  .catch((S) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + S.message,
                      "error"
                    ),
                      new O.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (S) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new O.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    S.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new O.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let S =
              _.filter((A) => A.match(/updated \d+/)).pop() ||
              _[_.length - 1] ||
              "",
            C = `${w}s \u2014 ${S}`;
          (this._showMessage("[OK] " + e.title + ": " + C, "ok"),
            new O.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (A) {
            console.log("[PF] fetchStats error:", A);
          }
          (console.log("[PF] close cmd=" + e.commandId + " id=" + e.id),
            e.commandId === "sync" &&
              Ye(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      f.on("error", (y) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + y.message, "error"),
          new O.Notice("[!!] Cannot start: " + y.message, 8e3));
      }));
  }
  _showMessage(e, t) {
    this._messageEl &&
      (this._messageEl.setText(e),
      (this._messageEl.className = `paperforge-message msg-${t}`));
  }
  _renderModeHeader(e) {
    if (!this._modeContextEl) return;
    this._modeContextEl.empty();
    let t = this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-badge",
      }),
      r = "";
    switch (e) {
      case "global":
        (t.addClass("global"),
          t.setText("Global"),
          this._headerTitle && this._headerTitle.setText("PaperForge"));
        break;
      case "paper":
        (t.addClass("paper"),
          t.setText("Paper"),
          this._headerTitle && this._headerTitle.setText("Paper"),
          this._currentPaperEntry && this._currentPaperEntry.title
            ? (r = this._currentPaperEntry.title)
            : this._currentPaperKey
              ? ((r = this._currentPaperKey),
                this._modeContextEl.createEl("span", {
                  cls: "paperforge-mode-warning",
                  text: "Not found in index",
                }))
              : (r = "Unknown paper"));
        break;
      case "collection":
        (t.addClass("collection"),
          t.setText("Collection"),
          this._headerTitle && this._headerTitle.setText("Collection"),
          (r = this._currentDomain || "Unknown Domain"));
        break;
      case "versions":
        (t.addClass("versions"),
          t.setText(s("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(s("version_panel_title")));
        break;
    }
    r &&
      this._modeContextEl.createEl("span", {
        cls: "paperforge-mode-name",
        text: r,
      });
  }
  _setupEventSubscriptions() {
    let e = this.app.workspace.on("active-leaf-change", () => {
      (this._leafChangeTimer && clearTimeout(this._leafChangeTimer),
        (this._leafChangeTimer = setTimeout(() => {
          let r = this._resolveModeForFile(this.app.workspace.getActiveFile()),
            n = r.mode,
            a = r.filePath;
          (this._currentMode === n && this._currentFilePath === a) ||
            this._detectAndSwitch();
        }, 300)));
    });
    this._modeSubscribers.push({ event: "active-leaf-change", ref: e });
    let t = this.app.vault.on("modify", (r) => {
      r &&
        r.path &&
        r.path.endsWith("formal-library.json") &&
        (this._invalidateIndex(), this._refreshCurrentMode());
    });
    this._modeSubscribers.push({ event: "modify", ref: t });
  }
  static async open(e) {
    let t = e.app.workspace.getLeavesOfType(Pe);
    if (t.length > 0) {
      await e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: Pe, active: !0 }),
      await e.app.workspace.revealLeaf(r));
  }
};
Ke();
var jt = class extends q.Modal {
    constructor(e, t, r) {
      super(e);
      this.onConfirm = r;
      (this.setTitle("Migrate PaperForge configuration"),
        this.contentEl.createEl("p", {
          text: "Legacy configuration detected. Migration preview:",
        }),
        this.contentEl
          .createEl("pre", { cls: "pf-migration-summary" })
          .setText(t),
        this.contentEl.createEl("p", {
          text: "Canonical values win on conflict. Credentials are never migrated through config.",
          cls: "setting-item-description",
        }));
      let a = this.contentEl.createDiv({ cls: "pf-modal-actions" });
      (a
        .createEl("button", { text: "Cancel" })
        .addEventListener("click", () => this.close()),
        a
          .createEl("button", { text: "Migrate" })
          .addEventListener("click", () => {
            this.onConfirm().finally(() => this.close());
          }));
    }
  },
  vt = class extends q.Plugin {
    constructor() {
      super(...arguments);
      this.agentPlatformChoices = [];
      this._embedStatusCache = {};
      this._autoSyncRunning = !1;
      this._lastSyncTime = null;
      this._pollTimer = null;
      this._embedProcess = null;
      this._embedProgress = { current: 0, total: 0, key: "" };
      this._embedStderr = "";
      this._embedController = null;
      this._memoryStatusText = null;
      this._ocrProgress = { current: 0, total: 1, key: "" };
      this._settingTab = null;
      this._managedRuntime = null;
      this._client = null;
      this._needsConfigMigration = !1;
    }
    getClient() {
      var e, t, r;
      if (!this._client) {
        let n =
            (t = (e = this.app.vault.adapter) == null ? void 0 : e.basePath) !=
            null
              ? t
              : "",
          a = new qe({
            vaultPath: n,
            customPythonPath:
              (r = this.settings) == null ? void 0 : r.python_path,
            resolveRuntime: async () => this._getPythonCommand(),
          });
        this._client = new He({ transport: a });
      }
      return this._client;
    }
    getManagedRuntime() {
      return (
        this._managedRuntime || (this._managedRuntime = new le()),
        this._managedRuntime
      );
    }
    _getPythonCommand() {
      let e = ce(this.getManagedRuntime().readPointer());
      return e ? { path: e.command, args: [...e.args] } : null;
    }
    requestOcrRun(e = !1) {
      if (this.ocrProcessController.isRunning) {
        new q.Notice(s("ocr_already_running"));
        return;
      }
      let t = () => {
        var r;
        ((this._ocrProgress = { current: 0, total: 1, key: "" }),
          (r = this._settingTab) == null || r.display(),
          this.ocrProcessController
            .start("run", {
              callbacks: {
                onProgress: (n, a, o) => {
                  var l;
                  ((this._ocrProgress = { current: n, total: a, key: o }),
                    (l = this._settingTab) == null || l.display());
                },
                onNotice: (n) => new q.Notice(n, 8e3),
              },
            })
            .then((n) => {
              var o;
              if (n.ok) new q.Notice(s("ocr_run_complete"));
              else if (n.stopped) new q.Notice(s("ocr_stopped_notice"));
              else {
                let l = n.failedKeys.join(", ");
                new q.Notice(s("ocr_failed_notice") + (l ? ": " + l : ""), 8e3);
              }
              (o = this._settingTab) == null || o.display();
              let a = this.app.vault.adapter.basePath;
              this._autoSync(a);
            })
            .catch((n) => {
              var a;
              (new q.Notice(
                s("ocr_failed_notice") +
                  ": " +
                  (n.message || s("ocr_error_notice")),
                8e3
              ),
                (a = this._settingTab) == null || a.display());
            }));
      };
      if (e) {
        t();
        return;
      }
      new pe(
        this.app,
        {
          title: s("ocr_run_confirm_title"),
          effectLabel: s("ocr_run_confirm_body"),
          confirmLabel: s("maintenance_confirm_ok"),
          cancelLabel: s("maintenance_confirm_cancel"),
        },
        t
      ).open();
    }
    async onload() {
      (await this.loadSettings(),
        await this.saveSettings(),
        dr(this.app, this.settings.language),
        (this.ocrProcessController = new mt({
          vaultPath: this.app.vault.adapter.basePath,
          resolveCommand: () => this._getPythonCommand(),
          resolveEnv: async () => await me(null, "ocr"),
          needsCredential: (t) => t === "run" || t === "redo",
        })),
        this.registerView(Pe, (t) => new Ue(t)),
        this.registerView(De, (t) => new Ve(t, this)));
      try {
        (0, q.addIcon)(Je, sr);
      } catch (t) {}
      (this.addRibbonIcon(Je, "PaperForge Dashboard", () => Ue.open(this)),
        this.addRibbonIcon("scan-text", "PaperForge OCR Workspace", () =>
          Ve.open(this)
        ),
        (this._settingTab = new ht(this.app, this)),
        this.addSettingTab(this._settingTab),
        this.addCommand({
          id: "paperforge-status-panel",
          name: s("guide_open"),
          callback: () => Ue.open(this),
        }),
        this.addCommand({
          id: "paperforge-ocr-workspace",
          name: "Open OCR Workspace",
          callback: () => Ve.open(this),
        }));
      for (let t of ge)
        t.id !== "paperforge-ocr-redo" &&
          this.addCommand({
            id: t.id,
            name: t.title,
            callback: async () => {
              var u;
              if (t.id === "paperforge-ocr") {
                this.requestOcrRun();
                return;
              }
              if (t.disabled) {
                new q.Notice(
                  `[i] ${t.disabledMsg || "This action is not yet available."}`,
                  6e3
                );
                return;
              }
              let r = this.app.vault.adapter.basePath;
              new q.Notice(`PaperForge: running ${t.commandId}...`);
              let n = this._getPythonCommand();
              if (!n) {
                new q.Notice("Runtime not ready");
                return;
              }
              let { path: a, args: o = [] } = n,
                l = Array.isArray(t.args) ? [...t.args] : [],
                c = await me(null, t.commandId),
                p = (u = ot(t.id)) != null ? u : [];
              (0, Vt.execFile)(
                a,
                [...o, "-m", "paperforge", ...p, ...l],
                { cwd: r, timeout: 3e5, env: c },
                (f, _, h) => {
                  if (f) {
                    new q.Notice(
                      `[!!] ${t.commandId} failed: ${(h || f.message).slice(0, 120)}`,
                      8e3
                    );
                    return;
                  }
                  new q.Notice(
                    `[OK] ${
                      t.okMsg ||
                      _.trim()
                        .split(
                          `
`
                        )[0]
                        .slice(0, 80)
                    }`
                  );
                }
              );
            },
          });
      (this.addCommand({
        id: "paperforge-migrate-config",
        name: "Migrate PaperForge legacy configuration",
        callback: () => this._runLegacyConfigMigration(),
      }),
        this._startConvergenceTimer(),
        this._checkReleaseNotes());
      let e = this.app.vault.adapter.basePath;
      e &&
        (br(e, this.settings)
          .then((t) => {
            t.state === "migration_required" &&
              (this._needsConfigMigration = !0);
          })
          .catch(() => {}),
        dt(e, this.settings)
          .then((t) => {
            t && (this._embedStatusCache = t);
          })
          .catch(() => {}));
    }
    _runLegacyConfigMigration() {
      let e = this.app.vault.adapter.basePath;
      e &&
        (async () => {
          var n;
          let t = await Bt(e, !0, this.settings).catch((a) => null),
            r =
              t && (n = t.warnings) != null && n.length
                ? t.warnings.join(`
`)
                : "No conflicts; legacy path keys will move under vault_config.";
          new jt(this.app, r, async () => {
            var a, o, l, c, p, u, f, _;
            await Bt(e, !1, this.settings).catch((h) => {
              new q.Notice(`PaperForge: config migrate failed: ${String(h)}`);
            });
            try {
              let h = await Lt(e, this.settings),
                g = (S) => {
                  var C;
                  return (C = h.fields.find((A) => A.key === S)) == null
                    ? void 0
                    : C.value;
                },
                m = String((a = g("system_dir")) != null ? a : ""),
                v = String((o = g("resources_dir")) != null ? o : ""),
                b = String((l = g("literature_dir")) != null ? l : ""),
                x = String((c = g("base_dir")) != null ? c : ""),
                E = String((p = g("zotero_data_dir")) != null ? p : ""),
                y = String((u = g("vector_db_api_base")) != null ? u : ""),
                w = String((f = g("vector_db_api_model")) != null ? f : ""),
                k = String((_ = g("agent_platform")) != null ? _ : "");
              (m && (this.settings.system_dir = m),
                v && (this.settings.resources_dir = v),
                b && (this.settings.literature_dir = b),
                x && (this.settings.base_dir = x),
                E && (this.settings.zotero_data_dir = E),
                y && (this.settings.vector_db_api_base = y),
                w && (this.settings.vector_db_api_model = w),
                k && (this.settings.agent_platform = k),
                gt({
                  system_dir: m || "System",
                  resources_dir: v || "Resources",
                  literature_dir: b || "Literature",
                  base_dir: x || "Bases",
                  _warning: null,
                }));
            } catch (h) {}
            ((this._needsConfigMigration = !1),
              await this.saveSettings(),
              new q.Notice("PaperForge: configuration migrated"));
          }).open();
        })();
    }
    _startConvergenceTimer() {
      var r;
      let e = this.app.vault.adapter.basePath,
        t =
          Math.max(
            30,
            (r = this.settings.autoSyncIntervalSeconds) != null ? r : 120
          ) * 1e3;
      this.settings.autoSyncEnabled !== !1 &&
        (this._autoSync(e),
        (this._pollTimer = setInterval(() => {
          zt() && this._autoSync(e);
        }, t)));
    }
    _autoSync(e) {
      if (this._autoSyncRunning) return;
      this._autoSyncRunning = !0;
      let t = this._getPythonCommand();
      if (!t) {
        this._autoSyncRunning = !1;
        return;
      }
      let r = G();
      (0, Vt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "--vault", e, "sync", "--json"],
        { timeout: 12e4, encoding: "utf-8", cwd: e, windowsHide: !0, env: r },
        (n, a, o) => {
          var l;
          ((this._autoSyncRunning = !1),
            (this._memoryStatusText = null),
            n ||
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              Ie(a, {
                vaultPath: e,
                resolveCommand: (c) => this._getPythonCommand(),
              }),
              (l = this._settingTab) == null || l._refreshAllReadModels()));
        }
      );
    }
    readPaperforgeJson() {
      return {};
    }
    savePaperforgeJson(e) {
      console.warn(
        "PaperForge: savePaperforgeJson is retired; use paperforge config set"
      );
    }
    onunload() {
      var e, t;
      (this._pollTimer && clearInterval(this._pollTimer),
        (e = this._embedController) == null || e.dispose(),
        (this._embedController = null),
        this.app.workspace.detachLeavesOfType(Pe),
        (t = this._client) == null || t.cancelActiveOperation());
    }
    async loadSettings() {
      var n, a, o, l, c, p, u, f, _, h;
      let e = (n = await this.loadData()) != null ? n : {};
      ((this.settings = Object.assign({}, We, e)),
        this.settings.features &&
          We.features &&
          (this.settings.features = Object.assign(
            {},
            We.features,
            this.settings.features || {}
          )),
        this.settings.frozen_skills || (this.settings.frozen_skills = {}));
      let t = !!e.capabilityState || !!e.last_seen_version || !!e.vault_path;
      e._setup_complete === !1 &&
        t &&
        e._setup_journey_started !== !0 &&
        (this.settings._setup_complete = !0);
      let r = this.app.vault.adapter.basePath;
      if (r)
        try {
          let g = await Lt(r, this.settings),
            m = (A) => {
              var D;
              return (D = g.fields.find((P) => P.key === A)) == null
                ? void 0
                : D.value;
            },
            v = String((a = m("system_dir")) != null ? a : ""),
            b = String((o = m("resources_dir")) != null ? o : ""),
            x = String((l = m("literature_dir")) != null ? l : ""),
            E = String((c = m("base_dir")) != null ? c : ""),
            y = String((p = m("zotero_data_dir")) != null ? p : "");
          (v && (this.settings.system_dir = v),
            b && (this.settings.resources_dir = b),
            x && (this.settings.literature_dir = x),
            E && (this.settings.base_dir = E),
            y && (this.settings.zotero_data_dir = y));
          let w = String((u = m("vector_db_api_base")) != null ? u : ""),
            k = String((f = m("vector_db_api_model")) != null ? f : ""),
            S = String((_ = m("agent_platform")) != null ? _ : "");
          (w && (this.settings.vector_db_api_base = w),
            k && (this.settings.vector_db_api_model = k),
            S && (this.settings.agent_platform = S));
          let C = g.fields.find((A) => A.key === "agent_platform");
          ((this.agentPlatformChoices =
            (h = C == null ? void 0 : C.choices) != null ? h : []),
            gt({
              system_dir: v || "System",
              resources_dir: b || "Resources",
              literature_dir: x || "Literature",
              base_dir: E || "Bases",
              _warning: null,
            }));
        } catch (g) {}
      if (this.settings.python_path && this.settings.python_path.trim()) {
        let g = this.settings.python_path.trim();
        this.settings._python_path_stale = !an.existsSync(g);
      }
    }
    async saveSettings() {
      let e = {};
      for (let t of Object.keys(We))
        t in this.settings && (e[t] = this.settings[t]);
      await this.saveData(e);
    }
    _checkReleaseNotes() {
      let e = this.manifest.version;
      if (this.settings.last_seen_version === e) return;
      let a = (Mt().versions || []).find((l) => l.version === e);
      class o extends q.Modal {
        constructor(c, p) {
          (super(c), (this._entry = p));
        }
        onOpen() {
          let { contentEl: c } = this;
          if (
            (c.createEl("h2", {
              text: `PaperForge v${e} \u66F4\u65B0\u8BF4\u660E`,
            }),
            this._entry)
          ) {
            if (
              (c.createEl("p", {
                text: this._entry.title,
                cls: "paperforge-modal-subtitle",
              }),
              this._entry.breaking_or_migration &&
                this._entry.breaking_or_migration.length > 0)
            ) {
              c.createEl("h4", {
                text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
              });
              for (let p of this._entry.breaking_or_migration)
                c.createEl("p", {
                  text: `\u2022 ${p}`,
                  cls: "paperforge-modal-item",
                });
            }
            if (
              this._entry.new_features &&
              this._entry.new_features.length > 0
            ) {
              c.createEl("h4", { text: "\u65B0\u529F\u80FD" });
              for (let p of this._entry.new_features)
                c.createEl("p", {
                  text: `\u2022 ${p}`,
                  cls: "paperforge-modal-item",
                });
            }
            if (this._entry.fixes && this._entry.fixes.length > 0) {
              c.createEl("h4", { text: "\u4FEE\u590D" });
              for (let p of this._entry.fixes)
                c.createEl("p", {
                  text: `\u2022 ${p}`,
                  cls: "paperforge-modal-item",
                });
            }
            if (
              this._entry.recommended_actions &&
              this._entry.recommended_actions.length > 0
            ) {
              let p = c.createEl("div", {
                cls: "paperforge-release-recommended",
              });
              (p.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
                (p.style.marginBottom = "8px"));
              for (let u of this._entry.recommended_actions)
                p.createEl("p", {
                  text: `\u2022 ${u}`,
                  cls: "paperforge-release-item-bold",
                });
            }
          } else
            c.createEl("p", {
              text:
                "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
                e +
                "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
            });
          new q.Setting(c).addButton((p) =>
            p
              .setButtonText("\u77E5\u9053\u4E86")
              .setCta()
              .onClick(() => {
                this.close();
              })
          );
        }
        onClose() {
          let { contentEl: c } = this;
          c.empty();
        }
      }
      (new o(this.app, a).open(),
        (this.settings.last_seen_version = e),
        this.saveSettings());
    }
  };
