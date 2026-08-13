"use strict";
var tn = Object.create;
var Ye = Object.defineProperty;
var rn = Object.getOwnPropertyDescriptor;
var nn = Object.getOwnPropertyNames;
var sn = Object.getPrototypeOf,
  an = Object.prototype.hasOwnProperty;
var Jt = (d, l) => () => (d && (l = d((d = 0))), l);
var on = (d, l) => () => (l || d((l = { exports: {} }).exports, l), l.exports),
  _t = (d, l) => {
    for (var e in l) Ye(d, e, { get: l[e], enumerable: !0 });
  },
  Gt = (d, l, e, t) => {
    if ((l && typeof l == "object") || typeof l == "function")
      for (let r of nn(l))
        !an.call(d, r) &&
          r !== e &&
          Ye(d, r, {
            get: () => l[r],
            enumerable: !(t = rn(l, r)) || t.enumerable,
          });
    return d;
  };
var Z = (d, l, e) => (
    (e = d != null ? tn(sn(d)) : {}),
    Gt(
      l || !d || !d.__esModule
        ? Ye(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  Yt = (d) => Gt(Ye({}, "__esModule", { value: !0 }), d);
var cr = {};
_t(cr, {
  isAllowlistedCommand: () => _n,
  legacyEmbeddingSecretIds: () => lr,
  migrateLegacySecret: () => hn,
  stripCredentialEnv: () => vt,
});
function vt(d) {
  let l = {};
  for (let [e, t] of Object.entries(d))
    dn.some((r) => e.startsWith(r)) || (l[e] = t);
  return l;
}
function _n(d) {
  return un.has(d);
}
async function lr(d, l) {
  let e = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(
      `${d.trim()}\0${l.trim() || "text-embedding-3-small"}`
    )
  );
  return [
    `vector-db-api-key-v2-${[...new Uint8Array(e)]
      .map((r) => r.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 40)}`,
    gn,
  ];
}
async function hn(d, l, e, t) {
  var n, s;
  if (!l || typeof l.getSecret != "function")
    return { migrated: [], warnings: ["SecretStorage unavailable"] };
  let r =
    d === "embedding"
      ? await lr(
          (n = t == null ? void 0 : t.baseUrl) != null ? n : "",
          (s = t == null ? void 0 : t.model) != null ? s : ""
        )
      : [fn];
  for (let a of r) {
    let o = await l.getSecret(a);
    if (!o) continue;
    if (!(await mn(d, o, e)))
      return {
        migrated: [],
        warnings: [
          "Keyring write failed \u2014 the legacy SecretStorage value was kept. Run `paperforge auth set " +
            d +
            " --stdin` manually.",
        ],
      };
    try {
      await l.setSecret(a, "");
    } catch (p) {
      return {
        migrated: [a],
        warnings: [
          "Credential migrated and verified, but the old SecretStorage value could not be cleared \u2014 delete it manually in Obsidian.",
        ],
      };
    }
    return { migrated: [a], warnings: [] };
  }
  return { migrated: [], warnings: [] };
}
function mn(d, l, e) {
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
    (r.stdout.on("data", (s) => (n += String(s))),
      r.on("error", () => t(!1)),
      r.on("close", (s) => {
        try {
          let a = JSON.parse(n);
          t(s === 0 && (a == null ? void 0 : a.ok) === !0);
        } catch (a) {
          t(!1);
        }
      }),
      r.stdin.write(l),
      r.stdin.end());
  });
}
var dn,
  un,
  fn,
  gn,
  xt = Jt(() => {
    "use strict";
    dn = ["PAPERFORGE_CREDENTIAL_", "PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
    un = new Set(["ocr", "memory", "embed"]);
    ((fn = "paddleocr-api-key"), (gn = "vector-db-api-key"));
  });
var Tt = on((es, yn) => {
  yn.exports = {
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
var Br = {};
_t(Br, {
  isConfigHydrated: () => Ot,
  readPathConfig: () => Lr,
  resolveVaultPaths: () => ae,
  setPathConfigSource: () => st,
});
function st(d) {
  qe = d;
}
function Ot() {
  return qe !== null;
}
function Lr(d, l) {
  var e;
  return qe
    ? { ...qe, _warning: (e = qe._warning) != null ? e : null }
    : {
        system_dir: "",
        resources_dir: "",
        literature_dir: "",
        base_dir: "",
        _warning:
          "config authority not hydrated; paths unavailable \u2014 no semantic work may run",
      };
}
function ae(d, l) {
  let e = Lr(d, l),
    t = Se.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: Se.join(t, "indexes"),
    logsDir: Se.join(t, "logs"),
    dbPath: Se.join(t, "indexes", "paperforge.db"),
    orphanStatePath: Se.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: Se.join(t, "exports"),
    ocrDir: Se.join(t, "ocr"),
    configWarning: e._warning,
  };
}
var Se,
  qe,
  Pe = Jt(() => {
    "use strict";
    ((Se = Z(require("path"))), (qe = null));
  });
var Un = {};
_t(Un, { default: () => ut });
module.exports = Yt(Un);
var q = require("obsidian"),
  en = Z(require("fs")),
  Vt = require("child_process");
var Ce = "paperforge-status",
  Ae = "paperforge-ocr-workspace",
  ze = "paperforge",
  tr =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  ce = [
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
function Xe(d) {
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
var Ve = {
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
function rr(d, l) {
  if (!l || !l.note_path) return l;
  let e = d.vault.getAbstractFileByPath(l.note_path);
  if (!e) return l;
  let t = d.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return l;
  let n = { ...l };
  for (let s of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, s) && (n[s] = r[s]);
  return n;
}
function ft(d, l) {
  return d && { ...d, ...l };
}
var Qe = 2,
  Oe = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  ln = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  Xt = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  cn = new Set(["unknown", "ok", "warning", "error"]),
  Qt = new Set(["idle", "running"]),
  pn = new Set(["safe", "destructive", "irreversible"]);
function er(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let l = d;
  return !(
    typeof l.action_id != "string" ||
    !l.action_id ||
    typeof l.verb != "string" ||
    typeof l.label != "string" ||
    typeof l.availability != "string" ||
    typeof l.safety_class != "string" ||
    !pn.has(l.safety_class) ||
    !Array.isArray(l.preservation_facts) ||
    !Array.isArray(l.replacement_facts) ||
    typeof l.interruptible != "boolean" ||
    typeof l.confirmation_required != "boolean" ||
    (l.confirmation_prompt !== null &&
      typeof l.confirmation_prompt != "string") ||
    typeof l.scope != "string" ||
    typeof l.scope_count != "number"
  );
}
function je(d) {
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
function nr() {
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
function et(d, l) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== Qe ||
    typeof e.module != "string" ||
    !e.module ||
    !Oe.includes(e.module) ||
    (l !== void 0 && e.module !== l) ||
    typeof e.capability_state != "string" ||
    !Xt.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !Qt.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !ln.has(e.user_state) ||
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
    (r.primary !== null && !er(r.primary)) ||
    typeof e.updated_at != "string" ||
    !e.updated_at ||
    typeof e.ttl_seconds != "number"
  )
    return !1;
  if (e.module === "maintenance") {
    if (r.primary !== null || !Array.isArray(e.items)) return !1;
    for (let n of e.items) {
      if (!n || typeof n != "object") return !1;
      let s = n,
        a = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof s.capability_state != "string" ||
        !Xt.has(s.capability_state) ||
        typeof s.severity != "string" ||
        !cn.has(s.severity) ||
        typeof s.activity_state != "string" ||
        !Qt.has(s.activity_state) ||
        (s.activity_label !== null && typeof s.activity_label != "string")
      )
        return !1;
      if (s.activity_progress !== null) {
        if (typeof s.activity_progress != "object") return !1;
        let o = s.activity_progress;
        if (typeof o.current != "number" || typeof o.total != "number")
          return !1;
      }
      if (
        typeof s.reason_code != "string" ||
        !s.reason_code ||
        typeof s.reason_text != "string" ||
        (s.action !== null && !er(s.action))
      )
        return !1;
    }
  }
  return !0;
}
function ie(d) {
  return {
    schema_version: Qe,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: d + ".no_probe", text: d + " has not been probed yet." },
    action: { primary: d === "maintenance" ? null : je(d) },
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
function gt(d) {
  return {
    schema_version: Qe,
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
    action: { primary: d === "maintenance" ? null : je(d) },
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
function Le(d) {
  return {
    schema_version: Qe,
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
    action: { primary: d === "maintenance" ? null : je(d) },
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
function ht(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let l = new Date(d.updated_at).getTime();
  return isNaN(l) ? !0 : Date.now() - l > d.ttl_seconds * 1e3;
}
function sr(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function ir(d) {
  var r, n, s;
  let l = (r = d.action) == null ? void 0 : r.primary,
    e = (n = l == null ? void 0 : l.verb) != null ? n : "probe",
    t = (s = l == null ? void 0 : l.label) != null ? s : e;
  return e === "setup" || e === "set_config" || e === "update"
    ? { kind: "setup", verb: e, label: t }
    : e === "probe"
      ? { kind: "probe", verb: e, label: t }
      : { kind: "action", verb: e, label: t };
}
function ar(d, l) {
  let e = {};
  for (let t of l) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = ie(t);
      continue;
    }
    if (!et(r, t)) {
      e[t] = Le(t);
      continue;
    }
    if (ht(r)) {
      e[t] = gt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var mt = {
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
      feat_build_complete: "Vector build complete.",
      feat_build_failed: "Build failed. See terminal output.",
      feat_building: "Building...",
      feat_cache_remove_failed: "Failed: {0}",
      feat_cache_removed: "Model cache removed.",
      feat_checking: "Checking...",
      feat_checking_btn: "Checking...",
      feat_deps_checking: "Checking dependencies...",
      feat_deps_missing:
        "Dependencies not installed. Required: chromadb, openai.",
      feat_enter_key: "Enter a valid OpenAI API key.",
      feat_install_btn: "Install",
      feat_install_deps: "Install Dependencies",
      feat_install_deps_desc: "pip install chromadb openai (~35MB).",
      feat_install_done: "Dependencies installed. Building vectors...",
      feat_install_failed: "Install failed: ",
      feat_installing: "Installing...",
      feat_installing_pkgs: "Installing {pkgs}...",
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
      feat_no_python: "No Python found. Check Installation tab.",
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
      feat_retry_btn: "Retry",
      feat_skills_desc:
        "Manage and enable/disable agent skills installed in your vault. Each row corresponds to a SKILL.md file \u2014 toggle off to prevent the agent from auto-invoking that skill.",
      feat_skills_system:
        "System Skills ship with PaperForge and are updated alongside PaperForge.",
      feat_skills_user:
        "User Skills are custom skills you install from community or create yourself.",
      feat_uninstall_btn: "Uninstall",
      feat_valid_key: "API key valid.",
      feat_vector_config_label: "Vector Settings",
      feat_vector_corrupted:
        "Vector index corrupted \u2014 needs force rebuild.",
      feat_vector_desc:
        "Vector Database enables semantic search across OCR-extracted fulltext via API embedding. Documents are split into chunks, embedded via OpenAI-compatible API, and stored in ChromaDB.",
      feat_vector_enable: "Enable Vector Retrieval",
      feat_vector_enable_desc:
        "Semantic search across OCR fulltext. Requires: pip install openai chromadb (~35MB).",
      feat_vector_rebuild_force_btn: "Force Rebuild",
      feat_verify: "Verify",
      feat_verify_btn: "Verify",
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
      retrieval_build_stale: "Vectors are stale \u2014 rebuild recommended",
      retrieval_build_deps_missing:
        "Dependencies missing. Install chromadb and openai.",
      retrieval_build_runtime_mismatch: "Python runtime version mismatch.",
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
      foundation_obsidian: "Obsidian Version",
      foundation_obsidian_old: "Version too old \u2014 update Obsidian",
      foundation_python_packages: "Python Packages",
      foundation_python_packages_checking: "Checking installed packages...",
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
      sr_build_failed_notice: "Vector index build failed: {detail}",
      sr_action_build: "Build Index",
      sr_action_rebuild: "Rebuild Index",
      sr_action_upgrade: "Upgrade to vec0",
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
      ocr_ws_status_failed: "Failed",
      ocr_ws_status_processing: "Processing",
      ocr_ws_status_nopdf: "No PDF",
      ocr_ws_status_pending: "Pending",
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
      feat_deps_missing:
        "\u4F9D\u8D56\u672A\u5B89\u88C5\u3002\u9700\u8981\uFF1Achromadb, openai\u3002",
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
      feat_vector_config_label: "\u5411\u91CF\u5E93\u914D\u7F6E",
      feat_vector_corrupted:
        "\u5411\u91CF\u7D22\u5F15\u5DF2\u635F\u574F \u2014 \u9700\u8981\u5F3A\u5236\u91CD\u5EFA\u3002",
      feat_vector_desc:
        "\u5411\u91CF\u6570\u636E\u5E93\u901A\u8FC7\u5D4C\u5165\u6A21\u578B\u5B9E\u73B0 OCR \u5168\u6587\u7684\u8BED\u4E49\u641C\u7D22\u3002\u6587\u6863\u88AB\u5207\u5206\u4E3A\u6587\u672C\u5757\uFF08chunk\uFF09\uFF0C\u7F16\u7801\u4E3A\u5411\u91CF\u5B58\u5165 ChromaDB\u3002\u652F\u6301\u672C\u5730\u6A21\u578B\uFF08\u514D\u8D39\uFF0CCPU \u8FD0\u884C\uFF09\u6216 OpenAI API\uFF08\u4ED8\u8D39\uFF0C\u66F4\u5FEB\u901F\uFF09\u3002",
      feat_vector_enable: "\u542F\u7528\u5411\u91CF\u68C0\u7D22",
      feat_vector_enable_desc:
        "\u5BF9 OCR \u5168\u6587\u8FDB\u884C\u8BED\u4E49\u641C\u7D22\u3002\u9700\u5B89\u88C5: pip install chromadb sentence-transformers openai (~500MB)\u3002",
      feat_vector_rebuild_force_btn: "\u5F3A\u5236\u91CD\u5EFA",
      feat_verify: "\u9A8C\u8BC1",
      feat_verify_btn: "\u9A8C\u8BC1",
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
      retrieval_build_deps_missing:
        "\u4F9D\u8D56\u7F3A\u5931\u3002\u8BF7\u5B89\u88C5 chromadb \u548C openai\u3002",
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
      ocr_ws_status_failed: "\u5931\u8D25",
      ocr_ws_status_processing: "\u5904\u7406\u4E2D",
      ocr_ws_status_nopdf: "\u65E0PDF",
      ocr_ws_status_pending: "\u5F85\u5904\u7406",
    },
  },
  bt = null;
function yt(d) {
  try {
    let l = d.vault;
    if (typeof l.getConfig == "function") {
      let e = l.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (l) {}
  try {
    if (typeof localStorage != "undefined") {
      let l = localStorage.getItem("language");
      if (l && String(l).startsWith("zh")) return "zh";
    }
  } catch (l) {}
  try {
    let l = document.documentElement.lang || navigator.language;
    if (l && l.startsWith("zh")) return "zh";
  } catch (l) {}
  return "en";
}
function or(d, l = "") {
  bt = (l || yt(d)).startsWith("zh") ? mt.zh : mt.en;
}
function i(d) {
  return (bt && bt[d]) || mt.en[d] || d;
}
var R = require("obsidian"),
  $ = Z(require("fs")),
  J = Z(require("path")),
  Vr = Z(require("os")),
  G = require("child_process");
var Pt = require("child_process");
var de = Z(require("fs")),
  pe = Z(require("path")),
  dr = Z(require("os")),
  ye = require("child_process");
xt();
var Et = null,
  pr = !1;
function wt(d, l, e, t) {
  let r = e || de,
    n = t || ye.execFileSync;
  if (l && l.python_path && l.python_path.trim()) {
    let o = l.python_path.trim();
    if (r.existsSync(o)) return { path: o, source: "manual", extraArgs: [] };
  }
  let s = [
    pe.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
    pe.join(d, ".venv", "Scripts", "python.exe"),
    pe.join(d, "venv", "Scripts", "python.exe"),
  ];
  for (let o of s)
    try {
      if (r.existsSync(o))
        return { path: o, source: "auto-detected", extraArgs: [] };
    } catch (c) {}
  let a = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let o of a)
    try {
      let c = n(o.path, [...o.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (c && c.toLowerCase().includes("python"))
        return {
          path: o.path,
          source: "auto-detected",
          extraArgs: o.extraArgs,
        };
    } catch (c) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function kt(d) {
  let l = String(d),
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
    }[l];
  return t
    ? { ...t }
    : { type: "unknown", message: String(d), recoverable: !1 };
}
function St(d, l, e, t, r, n) {
  let s = r || ye.spawn;
  return new Promise((a) => {
    let o = Date.now(),
      c = { cwd: e, timeout: t, windowsHide: !0 };
    n && (c.env = n);
    let p = s(d, l, c),
      _ = [],
      f = [];
    (p.stdout.on("data", (u) => {
      _.push(u.toString("utf-8"));
    }),
      p.stderr.on("data", (u) => {
        f.push(u.toString("utf-8"));
      }),
      p.on("close", (u) => {
        a({
          stdout: _.join(""),
          stderr: f.join(""),
          exitCode: u,
          elapsed: Date.now() - o,
        });
      }),
      p.on("error", (u) => {
        a({
          stdout: _.join(""),
          stderr:
            f.join("") +
            `
` +
            u.message,
          exitCode: -1,
          elapsed: Date.now() - o,
        });
      }));
  });
}
function ur() {
  if (pr) return Et;
  pr = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let l = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, ye.execFileSync)(l, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      d = (0, ye.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (d) {
      let l = d
        .split(
          `
`
        )[0]
        .trim();
      l && (Et = pe.dirname(l));
    }
  } catch (d) {}
  return Et;
}
function Y() {
  let d = { ...process.env },
    l = process.platform,
    e = dr.homedir(),
    t = [],
    r = ur();
  (r && t.push(r),
    l === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : l === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let n = d.PATH || "";
  return ((d.PATH = [...t, n].filter(Boolean).join(pe.delimiter)), vt(d));
}
async function ue(d, l) {
  return Y();
}
function _r(d) {
  return String(d)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function Ct(d) {
  if (!d) return !1;
  try {
    if (!de.existsSync(d)) return !1;
    for (let l of de.readdirSync(d)) if (_r(l)) return !0;
  } catch (l) {}
  return !1;
}
function tt(d) {
  if (!d) return !1;
  try {
    if (!de.existsSync(d)) return !1;
    for (let l of de.readdirSync(d)) {
      let e = pe.join(d, l, "extensions");
      try {
        if (!de.existsSync(e)) continue;
        for (let t of de.readdirSync(e)) if (_r(t)) return !0;
      } catch (t) {}
    }
  } catch (l) {}
  return !1;
}
function fr(d, l, e, t, r, n, s = 12e4) {
  var o;
  let a = [
    ...l,
    "-m",
    "paperforge",
    "--vault",
    e,
    "action",
    "run",
    t,
    "--scope",
    r.kind,
    ...(r.kind === "papers" ? ((o = r.keys) != null ? o : []) : []),
    "--json",
  ];
  return St(d, a, e, s, void 0, n).then((c) => {
    try {
      let p = JSON.parse(c.stdout);
      return { ok: p.ok === !0, payload: p, exitCode: c.exitCode };
    } catch (p) {
      return { ok: !1, payload: null, exitCode: c.exitCode };
    }
  });
}
var ve = class extends Error {
  constructor(l, e, t) {
    (super(t != null ? t : l), (this.configCode = l), (this.details = e));
  }
};
function xe(d, l, e) {
  return new Promise((t, r) => {
    let n = wt(d, e, require("fs"), require("child_process").execFileSync);
    if (!n) {
      r(new ve("config.python_unresolved", {}));
      return;
    }
    let s = [...n.extraArgs, "-m", "paperforge", "--vault", d, ...l, "--json"];
    (0, Pt.execFile)(
      n.path,
      s,
      { encoding: "utf-8", timeout: 6e4, windowsHide: !0 },
      (a, o) => {
        var c, p, _, f, u, h, g, m, v;
        try {
          let x = JSON.parse(o);
          if (x.ok && x.data !== null) {
            t(x.data);
            return;
          }
          let w =
            ((c = x.error) == null ? void 0 : c.message) ||
            ((p = x.error) == null ? void 0 : p.code) ||
            "config.error";
          r(
            new ve(
              w,
              (f = (_ = x.error) == null ? void 0 : _.details) != null ? f : {},
              (h = (u = x.error) == null ? void 0 : u.message) != null ? h : w
            )
          );
          return;
        } catch (x) {
          let w = (g = a == null ? void 0 : a.message) != null ? g : "";
          r(
            new ve(
              "config.invalid_response",
              {
                stdout:
                  (m = o == null ? void 0 : o.slice(0, 200)) != null ? m : "",
                stderr:
                  (v = w == null ? void 0 : w.slice(0, 200)) != null ? v : "",
              },
              `Invalid config response: ${String(x)}`
            )
          );
        }
      }
    );
  });
}
function Rt(d, l) {
  return xe(d, ["config", "list"], l);
}
function Ee(d, l, e, t) {
  return xe(d, ["config", "set", l, String(e)], t);
}
function gr(d, l) {
  return xe(d, ["config", "validate"], l);
}
function Ft(d, l, e) {
  return xe(
    d,
    l ? ["config", "migrate", "--dry-run"] : ["config", "migrate"],
    e
  );
}
function hr(d, l) {
  return xe(d, ["auth", "status", "embedding", "--json"], l).then((e) => {
    var t, r;
    return (r = ((t = e.credentials) != null ? t : []).some(
      (n) => n.state === "available"
    )) != null
      ? r
      : !1;
  });
}
function mr(d, l) {
  return xe(d, ["auth", "status", "ocr", "--json"], l).then((e) => {
    var t, r;
    return (r = ((t = e.credentials) != null ? t : []).some(
      (n) => n.state === "available"
    )) != null
      ? r
      : !1;
  });
}
function br(d, l) {
  return new Promise((e, t) => {
    let r = wt(d, l, require("fs"), require("child_process").execFileSync);
    if (!r) {
      t(new ve("config.python_unresolved", {}));
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
    (0, Pt.execFile)(
      r.path,
      n,
      { encoding: "utf-8", timeout: 6e4, windowsHide: !0 },
      (s, a) => {
        var o, c, p;
        try {
          let _ = JSON.parse(a);
          if (_.module === "all" && _.modules) {
            e(_);
            return;
          }
          t(
            new ve(
              "probe.invalid_envelope",
              {
                stdout:
                  (o = a == null ? void 0 : a.slice(0, 200)) != null ? o : "",
              },
              "probe all returned an invalid envelope"
            )
          );
        } catch (_) {
          t(
            new ve(
              "config.invalid_response",
              {
                stdout:
                  (c = a == null ? void 0 : a.slice(0, 200)) != null ? c : "",
                stderr: (p = s == null ? void 0 : s.message) != null ? p : "",
              },
              `Invalid probe response: ${String(_)}`
            )
          );
        }
      }
    );
  });
}
function yr(d, l) {
  return xe(d, ["memory", "status"], l);
}
function Ke(d, l) {
  return xe(d, ["embed", "status"], l);
}
var bn = null;
function vr() {
  bn = null;
}
var jr = Z(Tt());
var vn = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  xn = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function we(d, l, e) {
  return d.createEl("span", {
    cls: vn[l],
    text: e != null ? e : xn[l],
    attr: { role: "status" },
  });
}
function xr(d, l) {
  let e = d.createEl("div", { cls: "pf-activity-row" }),
    t = e.createEl("span", { cls: "pf-activity-label", text: l.label });
  if (l.progress && l.progress.total > 0) {
    let r = e.createEl("div", { cls: "pf-activity-bar" }),
      n = Math.round((l.progress.current / l.progress.total) * 100);
    (r.createEl("div", {
      cls: "pf-activity-bar-fill",
      attr: {
        style: `width: ${n}%`,
        role: "progressbar",
        "aria-valuenow": String(l.progress.current),
        "aria-valuemin": "1",
        "aria-valuemax": String(l.progress.total),
      },
    }),
      e.createEl("span", {
        cls: "pf-activity-count",
        text: `${l.progress.current}/${l.progress.total}`,
      }));
  } else
    e.createEl("span", { cls: "pf-activity-spinner" }).setAttr(
      "aria-label",
      "In progress"
    );
  if (
    (l.scope && e.createEl("span", { cls: "pf-activity-scope", text: l.scope }),
    l.stopLabel && l.onStop)
  ) {
    let r = e.createEl("button", {
      cls: "pf-activity-stop",
      text: l.stopLabel,
    });
    (r.addEventListener("click", l.onStop),
      r.addEventListener("keydown", (n) => {
        var s;
        (n.key === "Enter" || n.key === " ") &&
          (n.preventDefault(), (s = l.onStop) == null || s.call(l));
      }));
  }
  return e;
}
function V(d, l) {
  let e = d.createEl("button", {
    cls: "pf-action-btn",
    text: l.loading ? "\u2026" : l.label,
  });
  return (
    l.loading
      ? (e.setAttr("disabled", "true"),
        e.classList.add("pf-action-btn--loading"))
      : l.disabled &&
        (e.setAttr("disabled", "true"),
        e.classList.add("pf-action-btn--disabled")),
    e.addEventListener("click", l.onClick),
    e.addEventListener("keydown", (t) => {
      (t.key === "Enter" || t.key === " ") && (t.preventDefault(), l.onClick());
    }),
    e
  );
}
function Er(d, l) {
  let e = d.createEl("div", { cls: "pf-error-anatomy" });
  e.createEl("div", { cls: "pf-error-title", text: l.whatHappened });
  let t = e.createEl("div", { cls: "pf-error-impact" });
  (t.createEl("span", {
    cls: "pf-error-impact-label",
    text: (l.impactLabel || "Impact:") + " ",
  }),
    t.createEl("span", { text: l.impact }),
    l.reasonCode &&
      e.createEl("div", { cls: "pf-error-code", text: l.reasonCode }));
  let r = e.createEl("div", { cls: "pf-error-next" });
  return (
    r.createEl("span", {
      cls: "pf-error-next-label",
      text: (l.nextLabel || "Next:") + " ",
    }),
    r.createEl("span", { text: l.nextStep }),
    l.onCopyDiagnostic &&
      e
        .createEl("button", {
          cls: "pf-error-copy-diagnostic",
          text: l.copyLabel || "Copy Diagnostic Information",
        })
        .addEventListener("click", l.onCopyDiagnostic),
    e
  );
}
function wr(d, l) {
  let e = d.createEl("div", { cls: "pf-config-summary" });
  for (let r of l.items) {
    let n = e.createEl("div", { cls: "pf-config-row" });
    n.createEl("span", { cls: "pf-config-label", text: r.label });
    let s = r.isCredential
      ? r.value
        ? l.configuredLabel || "Configured"
        : l.notConfiguredLabel || "Not configured"
      : r.value;
    n.createEl("span", {
      cls: `pf-config-value${r.isCredential ? (r.value ? " pf-config-value--ok" : " pf-config-value--muted") : ""}`,
      text: s,
    });
  }
  return (
    e
      .createEl("button", {
        cls: "pf-config-change-btn",
        text: l.onChangeLabel,
      })
      .addEventListener("click", l.onChange),
    e
  );
}
function kr(d) {
  let l = [];
  (l.push("=== PaperForge Support Diagnostic ==="),
    l.push(`Time: ${new Date().toISOString()}`),
    l.push(`Plugin: ${d.pluginVersion}`),
    d.backendVersion && l.push(`Backend: ${d.backendVersion}`),
    l.push(""),
    l.push("--- Module Status ---"));
  for (let e of d.modules)
    (l.push(`${e.module}: ${e.userState}`),
      e.reasonCode && l.push(`  reason: ${e.reasonCode}`),
      e.actionId && l.push(`  action: ${e.actionId}`),
      e.lastSuccessAt && l.push(`  last-success: ${e.lastSuccessAt}`),
      e.errorExcerpt && l.push(`  error: ${e.errorExcerpt}`));
  return (
    l.push(""),
    l.push("=== End ==="),
    l.join(`
`)
  );
}
function Sr(d, l) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      l == null || l();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Cr(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function Pr(d, l) {
  return !d || l.user_state === "ready"
    ? !0
    : !(l.user_state === "detection_failed" || d.user_state === "ready");
}
function Rr(d, l) {
  var t, r, n, s, a, o, c;
  let e = [];
  for (let [p, _] of Object.entries(d)) {
    let f = l.get(p);
    e.push({
      module: p,
      userState: _.user_state,
      lastSuccessAt: (t = f == null ? void 0 : f.capturedAt) != null ? t : null,
      reasonCode: (r = _.reason) == null ? void 0 : r.code,
      actionId:
        (s = (n = _.action) == null ? void 0 : n.primary) == null
          ? void 0
          : s.action_id,
      errorExcerpt:
        (c =
          (o = (a = _.reason) == null ? void 0 : a.text) == null
            ? void 0
            : o.slice(0, 200)) != null
          ? c
          : void 0,
    });
  }
  return e;
}
var Dt = require("child_process");
var En = require("child_process");
var wn = new Set([
    "start",
    "phase",
    "progress",
    "item_result",
    "result",
    "error",
    "cancelled",
  ]),
  kn = new Set(["result", "error", "cancelled"]),
  ke = class {
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
    feed(l) {
      var n;
      if (this._protocolFailure) return [];
      let t = (this._buffer + l).split(`
`);
      this._buffer = (n = t.pop()) != null ? n : "";
      let r = [];
      for (let s of t) {
        if (!s.trim()) continue;
        let a;
        try {
          a = JSON.parse(s);
        } catch (o) {
          this._protocolFailure = `non-JSON stdout line: ${s.slice(0, 80)}`;
          break;
        }
        if (a.schema_version !== 1) {
          this._protocolFailure = `schema_version ${a.schema_version} != 1`;
          break;
        }
        if (typeof a.event != "string" || !wn.has(a.event)) {
          this._protocolFailure = `unknown event: ${String(a.event)}`;
          break;
        }
        if (this._terminalSeen) {
          this._protocolFailure = "event after terminal";
          break;
        }
        (kn.has(a.event) && (this._terminalSeen = !0), r.push(a));
      }
      return r;
    }
    finishEOF() {
      !this._protocolFailure &&
        !this._terminalSeen &&
        (this._protocolFailure = "EOF without terminal event");
    }
  };
var rt = class {
  constructor(l) {
    this._opts = l;
    this._state = "idle";
    this._child = null;
    this._poll = null;
    this._progress = { current: 0, total: 0, key: "" };
    this._warning = null;
    this._stopResult = null;
    this._stderr = "";
    this._parser = new ke();
    this._graceTimer = null;
    this._disposed = !1;
  }
  get state() {
    return this._state;
  }
  get progress() {
    return this._progress;
  }
  get warning() {
    return this._warning;
  }
  get busy() {
    return (
      this._state === "resolving_credentials" ||
      this._state === "running" ||
      this._state === "stopping"
    );
  }
  async start(l) {
    if (this.busy || this._disposed) return;
    (this._setState("resolving_credentials"),
      (this._warning = null),
      (this._stopResult = null),
      (this._stderr = ""),
      (this._parser = new ke()),
      (this._progress = { current: 0, total: 0, key: "" }));
    let e;
    try {
      e = await this._opts.resolveEnv();
    } catch (r) {
      ((this._warning = `Failed to resolve credentials: ${String(r)}`),
        this._setState("failed"));
      return;
    }
    ((e.PYTHONIOENCODING = "utf-8"), (e.PYTHONUTF8 = "1"));
    let t = (0, Dt.spawn)(
      this._opts.pythonPath,
      [...this._opts.pythonArgs, "embed", "build", l],
      { cwd: this._opts.vaultPath, env: e, windowsHide: !0 }
    );
    ((this._child = t),
      t.stdout.on("data", (r) => {
        var a;
        let n =
            typeof r == "string"
              ? r
              : Buffer.isBuffer(r)
                ? r.toString("utf-8")
                : String(r),
          s = this._parser.feed(n);
        for (let o of s)
          if (o.event === "start") this._progress.total = o.total || 0;
          else if (o.event === "progress")
            ((this._progress.current = o.current || 0),
              (this._progress.key = o.item_id || ""));
          else if (o.event === "result") {
            this._progress.current = this._progress.total;
            let c = o.result,
              p = c == null ? void 0 : c.warnings;
            p && p.length > 0 && (this._warning = String(p[0]));
          } else if (o.event === "error") {
            let c = (a = o.result) == null ? void 0 : a.error;
            c && typeof c.message == "string" && (this._warning = c.message);
          }
        this._emit();
      }),
      t.stderr.on("data", (r) => {
        this._stderr += String(r);
      }),
      t.on("error", (r) => {
        ((this._child = null),
          this._stopPoll(),
          (this._warning = r.message || String(r)),
          this._setState("failed"));
      }),
      t.on("close", (r) => {
        if (
          (this._parser.finishEOF(),
          this._graceTimer && clearTimeout(this._graceTimer),
          (this._child = null),
          this._stopPoll(),
          (this._progress.current = this._progress.total),
          this._stopResult === "stopped" || r === 130)
        )
          ((this._warning = null), this._setState("cancelled"));
        else if (r === 0) {
          let n = (this._stderr || "").trim().slice(0, 300);
          (!this._warning && n && (this._warning = n),
            this._setState(this._warning ? "success_with_warning" : "success"));
        } else
          ((this._warning =
            (this._stderr || "").slice(0, 300) || `exit code ${r}`),
            this._setState("failed"));
        this._stderr = "";
      }),
      this._startPoll(),
      this._setState("running"));
  }
  async stop() {
    var t;
    if (this._state !== "running" || this._disposed) return;
    (this._setState("stopping"), (this._stopResult = "stopped"));
    let l = this._child;
    try {
      (t = l == null ? void 0 : l.stdin) == null ||
        t.write(`PAPERFORGE_STOP
`);
    } catch (r) {}
    if (this._graceTimer) return;
    let e = 5e3;
    this._graceTimer = setTimeout(() => {
      if (l && l.exitCode === null && !l.killed) {
        if (process.platform === "win32")
          try {
            let r = l.pid;
            if (!r) return;
            (0, Dt.spawn)("taskkill", ["/T", "/F", "/PID", String(r)], {
              stdio: "ignore",
            });
          } catch (r) {
            l.kill("SIGKILL");
          }
        else
          try {
            let r = l.pid;
            r && process.kill(-r, "SIGKILL");
          } catch (r) {
            l.kill("SIGKILL");
          }
        this._warning = "Build stopped after grace window (hard kill).";
      }
    }, e);
  }
  dispose() {
    ((this._disposed = !0), this._stopPoll());
    let l = this._child;
    ((this._child = null), l && !l.killed && l.kill());
  }
  _startPoll() {
    (this._stopPoll(),
      (this._poll = setInterval(() => {
        this._state === "running" &&
          this._opts
            .runShort(["embed", "status", "--json"], 5e3)
            .then(({ code: l, stdout: e }) => {
              var t;
              if (!(l !== 0 || !e || this._state !== "running"))
                try {
                  let r = JSON.parse(e).data,
                    n = r == null ? void 0 : r.build_state;
                  n &&
                    typeof n.current == "number" &&
                    ((this._progress.current = n.current),
                    (this._progress.total =
                      typeof n.total == "number" && n.total > 0 ? n.total : 1),
                    (this._progress.key = String(
                      (t = n.paper_id) != null ? t : ""
                    )),
                    this._emit());
                } catch (r) {}
            })
            .catch(() => {});
      }, 2e3)));
  }
  _stopPoll() {
    var l;
    (clearInterval((l = this._poll) != null ? l : void 0), (this._poll = null));
  }
  _setState(l) {
    ((this._state = l), this._emit());
  }
  _emit() {
    this._disposed ||
      this._opts.callbacks.onStateChange(
        this._state,
        this._progress,
        this._warning,
        this._stopResult
      );
  }
};
function Fr() {
  let d, l;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (l = r));
    }),
    resolve: d,
    reject: l,
  };
}
var Be = require("obsidian");
function Tr(d) {
  try {
    let l = JSON.parse(d),
      e = l == null ? void 0 : l.next_actions;
    return Array.isArray(e) ? e : [];
  } catch (l) {
    return [];
  }
}
var At = new Set();
var Dr = {
  isInFlight: (d) => At.has(d),
  markInFlight: (d) => At.add(d),
  clearInFlight: (d) => At.delete(d),
};
var Sn = 1;
function Cn(d, l) {
  var e;
  return {
    action_id: d.action_id,
    scope: (e = d.scope) != null ? e : { kind: "all" },
    confirm: l ? d.action_id : void 0,
    follow: "auto",
  };
}
async function Ar(d, l, e = 0) {
  var r, n;
  let t = 0;
  for (let s of d) {
    if (s.schema_version !== Sn) {
      l.notify(`Unknown next-action schema v${s.schema_version}; refused`);
      continue;
    }
    if (!s.action_id) {
      l.notify("Next action without action_id; refused");
      continue;
    }
    let a =
      s.dedupe_key ||
      `${s.action_id}:${(n = (r = s.scope) == null ? void 0 : r.kind) != null ? n : "all"}`;
    if (l.isInFlight(a)) continue;
    let o = !1;
    if (s.automatic !== !0) {
      if (e > 0) {
        l.notify(`Follow-up depth exceeded for '${s.action_id}'; skipped`);
        continue;
      }
      if (!(await l.confirm(s))) {
        l.notify(`Follow-up '${s.action_id}' refused by user`);
        continue;
      }
      o = !0;
    }
    l.markInFlight(a);
    let c = !1;
    try {
      c = l.runAction(Cn(s, o)) === !0;
    } finally {
      l.clearInFlight(a);
    }
    c && (t += 1);
  }
  return t;
}
function Pn(d) {
  var e;
  let l = ["action", "run", d.action_id, "--scope", d.scope.kind];
  if (d.scope.kind === "papers")
    for (let t of (e = d.scope.keys) != null ? e : []) l.push("--key", t);
  return (
    d.confirm && l.push("--confirm", d.confirm),
    d.follow === "auto" && l.push("--follow", "auto"),
    l.push("--json"),
    l
  );
}
function Or(d, l, e, t, r = 12e4) {
  let n = [...l, "-m", "paperforge", "--vault", e, ...Pn(t)];
  return St(d, n, e, r, void 0, Y()).then((s) => {
    try {
      let a = JSON.parse(s.stdout);
      return { ok: a.ok === !0, payload: a, exitCode: s.exitCode };
    } catch (a) {
      return { ok: !1, payload: null, exitCode: s.exitCode };
    }
  });
}
async function nt(d, l) {
  let e = Tr(d);
  if (e.length === 0) return 0;
  let t = e.filter((r) =>
    r.automatic ? !0 : (new Be.Notice(i("next_action_pending"), 8e3), !1)
  );
  return t.length === 0
    ? 0
    : Ar(t, {
        runAction: (r) => {
          let n = l.resolveCommand(l.vaultPath);
          return n != null && n.path
            ? (Or(n.path, n.args, l.vaultPath, r).then((s) => {
                var a, o;
                if (s.ok) new Be.Notice(i("next_action_done"));
                else {
                  let c =
                    (o = (a = s.payload) == null ? void 0 : a.error) == null
                      ? void 0
                      : o.message;
                  new Be.Notice(
                    i("next_action_failed").replace(
                      "{detail}",
                      String(c != null ? c : "unknown error")
                    )
                  );
                }
              }),
              !0)
            : (new Be.Notice(i("next_action_runtime_unavailable")), !1);
        },
        confirm: async () => !1,
        notify: (r) => new Be.Notice(r),
        ...Dr,
      });
}
var _e = require("obsidian"),
  Te = Z(require("fs")),
  Mn = Z(require("path")),
  Nn = Z(require("https")),
  Mt = require("child_process");
Pe();
var Bt = Z(require("fs")),
  ge = Z(require("path")),
  it = require("child_process"),
  Mr = Z(require("os")),
  Ir = "3.11",
  Rn = 1,
  Fn = "pointer.json",
  Tn = "venv";
function Lt() {
  let d, l;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (l = r));
    }),
    resolve: d,
    reject: l,
  };
}
function Dn(d) {
  let l = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (l) return l[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function An(d, l) {
  var r, n;
  let e = d.split(".").map(Number),
    t = l.split(".").map(Number);
  for (let s = 0; s < Math.max(e.length, t.length); s++) {
    let a = (r = e[s]) != null ? r : 0,
      o = (n = t[s]) != null ? n : 0;
    if (a !== o) return a - o;
  }
  return 0;
}
function On(d, l) {
  return An(d, l) >= 0;
}
function Ln() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function Bn() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function In(d, l) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${l}`;
}
function he(d) {
  return d ? { command: d.pythonPath, args: [] } : null;
}
var Re = class {
    constructor(l) {
      var e, t, r, n, s, a;
      ((this.osPlatform =
        (e = l == null ? void 0 : l.osPlatform) != null ? e : process.platform),
        (this.osArch =
          (t = l == null ? void 0 : l.osArch) != null ? t : process.arch),
        (this.rootDir =
          (r = l == null ? void 0 : l.runtimeDir) != null
            ? r
            : ge.join(Mr.homedir(), ".paperforge", "runtime")),
        (this._fs = (n = l == null ? void 0 : l.fs) != null ? n : Bt),
        (this._execFile =
          (s = l == null ? void 0 : l.execFile) != null ? s : it.execFile),
        (this._execFileSync =
          (a = l == null ? void 0 : l.execFileSync) != null
            ? a
            : it.execFileSync));
    }
    get venvDir() {
      return ge.join(this.rootDir, Tn);
    }
    pythonExeFor(l) {
      return this.osPlatform === "win32"
        ? ge.join(l, "Scripts", "python.exe")
        : ge.join(l, "bin", "python");
    }
    discoverInterpreter() {
      let l =
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
      for (let e of l)
        try {
          let t = this._execFileSync(e.path, [...e.args, "--version"], {
              encoding: "utf-8",
              timeout: 5e3,
            }),
            r = Dn(t);
          if (r && On(r, Ir)) return { path: e.path, version: r };
        } catch (t) {}
      return null;
    }
    platformGate() {
      if (Ln() || Bn())
        return {
          ok: !1,
          code: "FLATPAK_SNAP_UNSUPPORTED",
          message:
            "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
          platformAction:
            "Install Python 3.11+ from python.org or package manager",
        };
      let l = In(this.osPlatform, this.osArch);
      return this.osPlatform === "darwin" &&
        ["macos-x64", "macos-arm64"].includes(l)
        ? {
            ok: !1,
            code: "NO_PYTHON",
            message:
              "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
            platformAction: "Install Python 3.11+ from python.org or Homebrew",
          }
        : ["windows-x64", "linux-x64"].includes(l)
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
    async installOnce(l, e) {
      if (e != null && e.aborted) throw new Ie("Operation was cancelled");
      let t = this.discoverInterpreter();
      if (!t) {
        let n = this.platformGate();
        throw new Error(
          `No Python ${Ir}+ found (${n.ok ? "no interpreter" : n.message})`
        );
      }
      if (e != null && e.aborted) throw new Ie("Operation was cancelled");
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
          throw new Ie("Operation was cancelled");
        if (
          (await this._exec(
            r,
            ["-m", "pip", "install", `paperforge[vector]==${l}`],
            { timeout: 12e4, signal: e },
            "pip install"
          ),
          e != null && e.aborted)
        )
          throw new Ie("Operation was cancelled");
        let n = await this._probeVersion(r, e);
        if (n !== l)
          throw new Error(
            `installed version mismatch: observed ${n} != requested ${l}`
          );
      } catch (n) {
        try {
          this._fs.rmSync(this.venvDir, { recursive: !0, force: !0 });
        } catch (s) {}
        throw n;
      }
      return { pythonPath: r, observedVersion: l };
    }
    async handshake(l, e) {
      var r;
      let t = (r = e.pythonPath) != null ? r : this.pythonExeFor(this.venvDir);
      if (!this._fs.existsSync(t))
        return { ok: !1, observedVersion: null, reason: "interpreter missing" };
      try {
        let n = await this._probeVersion(t, e.signal);
        if (n !== l)
          return {
            ok: !1,
            observedVersion: n,
            reason: `version mismatch: observed ${n} != expected ${l}`,
          };
        let s = await this._probeInstallation(t, e.vaultPath, l, e.signal);
        if (s === null)
          return {
            ok: !1,
            observedVersion: n,
            reason:
              "installation probe failed or returned an unparseable envelope",
          };
        if (s === "installation.version_mismatch")
          return {
            ok: !1,
            observedVersion: n,
            reason: "installation probe reports version mismatch",
          };
        if (
          s !== "installation.ready" &&
          s !== "installation.config_missing" &&
          s !== "installation.config_corrupt"
        )
          return {
            ok: !1,
            observedVersion: n,
            reason: `unexpected installation probe state: ${s}`,
          };
      } catch (n) {
        return {
          ok: !1,
          observedVersion: null,
          reason: n instanceof Error ? n.message : String(n),
        };
      }
      return { ok: !0, observedVersion: l };
    }
    readPointer() {
      let l = ge.join(this.rootDir, Fn),
        e;
      try {
        e = this._fs.readFileSync(l, "utf-8");
      } catch (a) {
        return null;
      }
      let t;
      try {
        t = JSON.parse(e);
      } catch (a) {
        return null;
      }
      if (t.schema_version !== Rn) return null;
      let { python_path: r, environment_root: n, paperforge_version: s } = t;
      return typeof r != "string" ||
        !r ||
        typeof n != "string" ||
        !n ||
        typeof s != "string" ||
        !s ||
        !ge.isAbsolute(r) ||
        !ge.isAbsolute(n)
        ? null
        : { pythonPath: r, environmentRoot: n, paperforgeVersion: s };
    }
    _exec(l, e, t, r) {
      let { promise: n, resolve: s, reject: a } = Lt();
      return (
        this._execFile(l, e, { ...t, encoding: "utf-8" }, (o) => {
          o ? a(new Error(`${r} failed: ${o.message}`)) : s();
        }),
        n
      );
    }
    _probeVersion(l, e) {
      let { promise: t, resolve: r, reject: n } = Lt();
      return (
        this._execFile(
          l,
          ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
          { timeout: 3e4, signal: e },
          (s, a) => {
            if (s) n(s);
            else {
              let o = (a != null ? a : "").trim() || null;
              r(o);
            }
          }
        ),
        t
      );
    }
    _probeInstallation(l, e, t, r) {
      let { promise: n, resolve: s, reject: a } = Lt();
      return (
        this._execFile(
          l,
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
          (o, c) => {
            var p, _;
            if (o) {
              s(null);
              return;
            }
            try {
              let f = JSON.parse(c);
              s(
                (_ = (p = f.reason) == null ? void 0 : p.code) != null
                  ? _
                  : null
              );
            } catch (f) {
              s(null);
            }
          }
        ),
        n
      );
    }
  },
  Ie = class extends Error {
    constructor(l) {
      (super(l), (this.name = "AbortError"));
    }
  };
var It = class extends _e.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((s, a) => ({ ...s, _selected: !0, _idx: a }))),
      (this.vaultPath = r),
      (this.py = n));
  }
  _updateUI() {
    let e = this.orphans.filter((t) => t._selected);
    (this._countEl.setText(
      i("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? i("orphan_deselect_all")
          : i("orphan_select_all")
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
        text: i("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: i("orphan_desc") }),
      (this._rowEls = []));
    let t = e.createEl("div", { cls: "paperforge-orphan-list" });
    for (let n of this.orphans) {
      let s = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(s);
      let a = s.createEl("div", { cls: "paperforge-orphan-info" }),
        o = a.createEl("div", { cls: "paperforge-orphan-header" });
      o.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let c = o.createEl("span", { cls: "paperforge-orphan-tags" });
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
          a.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let p = [];
      (n.authors && p.push(n.authors),
        n.year && p.push(n.year),
        p.length > 0 &&
          a.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: p.join(" \xB7 "),
          }),
        a.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: i("orphan_explain"),
        }),
        s.addEventListener("click", () => {
          ((n._selected = !n._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let n = this.orphans.every((s) => s._selected);
        for (let s of this.orphans) s._selected = !n;
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
        let n = this.orphans.filter((a) => a._selected);
        if (n.length === 0) {
          new _e.Notice(i("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new _e.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let s = n.map((a) => a.key);
        (0, Mt.execFile)(
          this.py.path,
          [
            ...this.py.extraArgs,
            "-m",
            "paperforge",
            "--vault",
            this.vaultPath,
            "prune",
            "--force",
            "--json",
            ...s,
          ],
          { cwd: this.vaultPath, timeout: 6e4 },
          (a, o) => {
            if (a) {
              (new _e.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let c = JSON.parse(o),
                p = (c.data && c.data.deleted) || [];
              new _e.Notice("Deleted " + p.length + " orphan workspace(s)");
            } catch (c) {
              new _e.Notice("PaperForge: prune done");
            }
            this.close();
          }
        );
      }));
  }
  onClose() {
    this.contentEl.empty();
  }
};
function ot(d, l, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = ae(e).orphanStatePath;
    if (!Te.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = Te.readFileSync(r, "utf-8"),
      a = JSON.parse(n),
      o = { path: "python", extraArgs: [], source: "auto-detected" };
    (console.log("[PF] py.path:", o ? o.path : "null"),
      new It(d, a, e, o).open(),
      Te.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
function Nr(d, l) {
  if (l.key !== "Tab") return;
  let e = d.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (e.length === 0) return;
  let t = e[0],
    r = e[e.length - 1];
  l.shiftKey
    ? document.activeElement === t && (l.preventDefault(), r.focus())
    : document.activeElement === r && (l.preventDefault(), t.focus());
}
var Fe = class extends _e.Modal {
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
        let o = t.parentElement;
        if (o)
          for (let c of Array.from(o.children))
            c !== t &&
              !c.hasAttribute("inert") &&
              (c.setAttribute("inert", ""), this._inertedEls.push(c));
      }
      e.createEl("h2", { text: this._config.title });
      let r = e.createEl("div", { cls: "paperforge-confirm-effect" });
      (r.createEl("span", {
        cls: "paperforge-confirm-effect-label",
        text: i("confirm_effect_label") + ": ",
      }),
        r.createEl("span", { text: this._config.effectLabel }));
      let n = e.createEl("div", { cls: "paperforge-confirm-actions" }),
        s = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            i("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (s.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              i("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (o) => Nr(e, o)),
        e.addEventListener("keydown", this._boundKeydown),
        s.focus());
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
  Hn = [
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
function Ue(d) {
  let l = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of Hn) {
    let s = 0;
    ((e = e.replace(t, () => (s++, "[REDACTED]"))),
      s > 0 &&
        (l[n] || (l[n] = { label: r, class_: n, count: 0 }),
        (l[n].count += s)));
  }
  return { clean: e, redactions: Object.values(l) };
}
function Hr(d, l, e, t) {
  let r = `OCR: ${d} (${e} papers)`,
    n = [
      "## Diagnostic Summary",
      `- Reason: ${d}`,
      `- Detail: ${l}`,
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
var at = class extends _e.Modal {
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
      text: i("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          i("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = Ue(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let s = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    s.createEl("label", { text: "Body" });
    let a = Ue(this._draft.body).clean;
    this._bodyTextarea = s.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: a,
    });
    let { redactions: o } = Ue(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      c = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = c.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (i("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let _ = c.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (_.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (i("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      _.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (o.length > 0
            ? " (" + o.map((g) => `${g.count} ${g.label}`).join(", ") + ")"
            : ""),
      }));
    let f = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (f
      .createEl("button", { text: i("maintenance_confirm_cancel") || "Cancel" })
      .addEventListener("click", () => this.close()),
      f
        .createEl("button", {
          cls: "mod-cta",
          text: i("maintenance_issue_draft_open_github") || "Open GitHub Issue",
        })
        .addEventListener("click", () => {
          let g = encodeURIComponent(Ue(this._titleInput.value).clean),
            m = encodeURIComponent(Ue(this._bodyTextarea.value).clean),
            v = encodeURIComponent(this._draft.labels.join(",")),
            x = `${this._githubUrl}?title=${g}&body=${m}&labels=${v}`;
          window.open(x, "_blank", "noopener,noreferrer");
        }),
      (this._boundKeydown = (g) => Nr(e, g)),
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
function Nt(d, l, e) {
  return !d ||
    typeof d != "object" ||
    !Object.prototype.hasOwnProperty.call(d, l)
    ? !!e
    : !!d[l];
}
function $r(d, l, e) {
  let t = !Nt(d, l, e);
  return (d && typeof d == "object" && (d[l] = t), t);
}
var $n = new Set(["result", "error", "cancelled"]);
function zr(d, l) {
  var a;
  let t = (l + d).split(`
`),
    r = (a = t.pop()) != null ? a : "",
    n = [],
    s;
  for (let o of t)
    if (o.trim()) {
      if (s) break;
      try {
        let c = JSON.parse(o);
        if (c.schema_version !== 1) {
          s = `schema_version ${c.schema_version} != 1`;
          break;
        }
        if (typeof c.event != "string" || !c.event) {
          s = "event discriminator required";
          break;
        }
        if ($n.has(c.event) && !("result" in c)) {
          s = `terminal ${c.event} missing result payload`;
          break;
        }
        n.push(c);
      } catch (c) {
        s = `non-JSON stdout line: ${o.slice(0, 80)}`;
        break;
      }
    }
  return { events: n, buffer: r, protocolFailure: s };
}
var Me = class Me extends R.PluginSettingTab {
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
    this._attemptedProbes = new Set();
    this._setupView = "overview";
    this._setupStage = 1;
    this._setupOptionals = { ocr: !1, memory: !1, agent: !1 };
    this._setupReinstallRequested = !1;
    this._setupOperation = "idle";
    this._setupFeedback = null;
    this._selectedDetailModule = "";
    this._focusTargetId = null;
    this._runtimeAbortController = null;
    this._managedRuntime = null;
    this._runtimeBusy = !1;
    this._libraryRunning = !1;
    this._displayInProgress = !1;
    this._detailReturn = null;
    this._agentPlatformDraft = null;
    this.plugin = t;
  }
  _getOverviewModules() {
    return [
      { id: "installation", label: i("cc_module_foundation") || "Foundation" },
      { id: "library", label: i("cc_module_library") || "Library" },
      { id: "ocr", label: i("cc_module_ocr") || "OCR" },
      { id: "memory", label: i("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: i("cc_module_agent") || "Agent Integration" },
    ];
  }
  _getUserModuleName(e) {
    let t =
      "cc_module_" +
      (e === "installation" ? "foundation" : e === "memory" ? "memory" : e);
    return i(t) || e.charAt(0).toUpperCase() + e.slice(1);
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
    var _, f;
    this._displayInProgress = !0;
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      this._initialDisplay &&
        (this._restoreNavMemory(), (this._initialDisplay = !1)),
      this._initCapabilityState(),
      this.plugin.settings._setup_complete === !1)
    ) {
      (this._renderSetupJourney(e), (this._displayInProgress = !1));
      return;
    }
    if (!document.getElementById("paperforge-tab-styles")) {
      let u = document.createElement("style");
      ((u.id = "paperforge-tab-styles"),
        (u.textContent = `
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
        document.head.appendChild(u));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let u = e.createDiv({ cls: "paperforge-migration-warning" }),
        h = t
          .map((g) => (g === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (u.createEl("strong", { text: i("migration_banner_title") }),
        u.createEl("p", {
          text: i("migration_banner_body").replace("{modules}", h),
        }),
        u.createEl("p", {
          text: i("migration_banner_next"),
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
          ((f = (_ = this.plugin.manifest) == null ? void 0 : _.version) != null
            ? f
            : "?"),
      }));
    let s = r.createDiv({ cls: "pf-cc-topbar-center" }),
      a = [
        { id: "overview", label: i("tab_overview") || "Overview" },
        { id: "help", label: i("tab_help") || "Help" },
      ],
      o = {};
    if (
      (a.forEach((u) => {
        s.createEl("button", {
          cls:
            "pf-cc-topbar-tab" +
            (u.id === this.activeTab ? " pf-cc-topbar-tab--active" : ""),
          text: u.label,
        }).addEventListener("click", () => {
          ((this._detailReturn = null),
            (this.activeTab = u.id),
            (this._navMemory = { destination: u.id }),
            this._persistNavMemory(),
            this.display());
        });
      }),
      r
        .createDiv({ cls: "pf-cc-topbar-right" })
        .createEl("a", {
          cls: "pf-cc-topbar-ocr-link",
          text: (i("md_ocr_workspace") || "OCR Workspace") + " \u2197",
          attr: { href: "#", role: "button" },
        })
        .addEventListener("click", (u) => {
          (u.preventDefault(),
            this.app.setting.close(),
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }));
        }),
      a.forEach((u) => {
        o[u.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (u.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      (o["module-detail"] = e.createDiv({
        cls:
          "paperforge-tab-content" +
          (this.activeTab === "module-detail"
            ? " paperforge-tab-content--active"
            : ""),
      })),
      this.activeTab === "overview"
        ? this._renderOverviewTab(o.overview)
        : this.activeTab === "module-detail"
          ? this._renderModuleDetailTab(o["module-detail"])
          : this.activeTab === "help" && this._renderHelpTab(o.help),
      this._focusTargetId && this.activeTab !== "help")
    ) {
      let u = e.querySelector(this._focusTargetId);
      if (
        (!u &&
          this.activeTab === "overview" &&
          (u = e.querySelector(".pf-cc-module-card")),
        u)
      ) {
        try {
          u.focus();
        } catch (h) {}
        this._focusTargetId = null;
      }
    }
    this._displayInProgress = !1;
  }
  _startSetupJourney(e = 1, t = !1) {
    ((this._setupStage = e),
      (this._setupReinstallRequested = t),
      (this._setupOperation = "idle"),
      (this._setupFeedback = null),
      (this.plugin.settings._setup_complete = !1),
      this.plugin.saveSettings().then(() => this.display()));
  }
  _runSetupPython(e, t) {
    var n;
    let r = (0, G.spawn)(
      (t == null ? void 0 : t.trim()) ||
        ((n = this.plugin.settings.python_path) == null ? void 0 : n.trim()) ||
        "python",
      e,
      { cwd: this._getVaultBasePath(), env: Y(), windowsHide: !0 }
    );
    return new Promise((s, a) => {
      var c;
      let o = "";
      ((c = r.stderr) == null ||
        c.on("data", (p) => {
          o += p.toString("utf-8");
        }),
        r.once("error", a),
        r.once("close", (p) => {
          p === 0 ? s() : a(new Error(o || `exit code ${p}`));
        }));
    });
  }
  _installFoundation(e) {
    this._setupOperation !== "running" &&
      ((this._setupOperation = "running"),
      (this._setupFeedback = null),
      this.display(),
      (async () => {
        var t, r, n, s, a, o;
        try {
          let c = this._getVaultBasePath(),
            p = this._ensureManagedRuntime(),
            _ = await p.installOnce(this.plugin.manifest.version),
            f = await p.handshake(this.plugin.manifest.version, {
              pythonPath: _.pythonPath,
              vaultPath: c,
            });
          if (!f.ok)
            throw new Error((t = f.reason) != null ? t : "handshake failed");
          let u = this.plugin.settings,
            h = [
              "-m",
              "paperforge",
              "--vault",
              c,
              "setup",
              "--modular",
              "--json",
              "--system-dir",
              ((r = u.system_dir) == null ? void 0 : r.trim()) || "System",
              "--resources-dir",
              ((n = u.resources_dir) == null ? void 0 : n.trim()) ||
                "Resources",
              "--literature-dir",
              ((s = u.literature_dir) == null ? void 0 : s.trim()) ||
                "Literature",
              "--base-dir",
              ((a = u.base_dir) == null ? void 0 : a.trim()) || "Bases",
              "--agent",
              u.agent_platform || "opencode",
            ];
          ((o = u.zotero_data_dir) != null &&
            o.trim() &&
            h.push("--zotero-data", u.zotero_data_dir.trim()),
            await this.plugin.saveSettings(),
            await this._runSetupPython(h, _.pythonPath),
            (this._setupOperation = "idle"),
            (this._setupReinstallRequested = !1),
            (this._setupFeedback = i("setup_install_complete")),
            this._probeModule("installation"),
            this._probeModule("help"),
            this.display());
        } catch (c) {
          (console.error("PaperForge runtime installation failed:", c),
            (this._setupOperation = "failed"),
            (this._setupFeedback = i("setup_install_failed")),
            this.display());
        }
      })());
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
      var a, o, c, p, _;
      let n = [];
      for (let [f, u] of Object.entries(r))
        u &&
          u.trim() &&
          n.push(
            Ee(t, f, u.trim(), e).catch((h) => {
              console.error(`PaperForge: config set ${f} failed`, h);
            })
          );
      (await Promise.all(n).catch(() => {}), this.display());
      let s = [
        "-m",
        "paperforge",
        "--vault",
        t,
        "setup",
        "--modular",
        "--system-dir",
        ((a = e.system_dir) == null ? void 0 : a.trim()) || "System",
        "--resources-dir",
        ((o = e.resources_dir) == null ? void 0 : o.trim()) || "Resources",
        "--literature-dir",
        ((c = e.literature_dir) == null ? void 0 : c.trim()) || "Literature",
        "--base-dir",
        ((p = e.base_dir) == null ? void 0 : p.trim()) || "Bases",
        "--agent",
        e.agent_platform || "opencode",
      ];
      (_ = e.zotero_data_dir) != null &&
        _.trim() &&
        s.push("--zotero-data", e.zotero_data_dir.trim());
      try {
        (await this.plugin.saveSettings(),
          await this._runSetupPython(s),
          (this._setupOperation = "idle"),
          (this._setupFeedback = i("setup_library_configured")),
          this._attemptedProbes.add("library"),
          this._probeModule("library"),
          this.display());
      } catch (f) {
        (console.error("PaperForge library configuration failed:", f),
          (this._setupOperation = "failed"),
          (this._setupFeedback = i("setup_library_config_failed")),
          this.display());
      }
    })();
  }
  _renderOverviewTab(e) {
    var r;
    let t = this._getVaultBasePath();
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      e.createEl("h2", { text: i("header_title") || "PaperForge" }),
      e.createEl("p", { text: i("desc"), cls: "paperforge-settings-desc" }));
    for (let n of Oe) {
      let s = (r = this._capabilityState) == null ? void 0 : r[n];
      if (!s) continue;
      let a =
          s.capability_state === "unknown" &&
          s.updated_at === new Date(0).toISOString(),
        o =
          s.user_state === "detection_failed" &&
          s.reason.code.endsWith(".stale");
      (a || o) &&
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
            : new Re()),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    var n;
    let t = (n = this.plugin.settings.python_path) == null ? void 0 : n.trim();
    if (t && $.existsSync(t)) return { path: t, args: [] };
    let r = he(this._ensureManagedRuntime().readPointer());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  _renderInstallationDetail(e) {
    var b, k, S;
    this._renderModuleDetailShell(e, "installation");
    let t =
        (k = (b = this._capabilityState) == null ? void 0 : b.installation) !=
        null
          ? k
          : ie("installation"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_foundation_overview") }),
      r.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("md_foundation_ready")
            : this._getModuleConsequence("installation", t),
        cls:
          t.user_state === "ready"
            ? "pf-status-ok"
            : "setting-item-description",
      }));
    let n = r.createDiv({ cls: "pf-config" }),
      s = (E, C, P, T) => {
        let D = n.createDiv({ cls: "pf-config-row" });
        D.createEl("span", { cls: "pf-config-key", text: E });
        let I = D.createDiv({ cls: "pf-config-right" });
        (I.createEl("span", { cls: T, text: C }),
          I.createEl("span", { cls: "pf-config-value", text: P }));
      };
    s(
      i("foundation_version"),
      "\u2713",
      this.plugin.manifest.version,
      "pf-status-ok"
    );
    let a = this.plugin.settings.python_path || "python";
    s(i("foundation_python"), "\u2014", a, "pf-status-checking");
    let o = this.app.vault.adapter.basePath,
      c = J.join(o, this.plugin.settings.system_dir || "System"),
      p = $.existsSync(c);
    s(
      i("foundation_vault_structure"),
      p ? "\u2713" : "\u2717",
      p ? c : i("foundation_vault_missing"),
      p ? "pf-status-ok" : "pf-status-error"
    );
    let _ =
      this.plugin.settings.zotero_data_dir &&
      $.existsSync(this.plugin.settings.zotero_data_dir);
    s(
      i("foundation_zotero"),
      _ ? "\u2713" : "\u2717",
      _ ? this.plugin.settings.zotero_data_dir : i("foundation_zotero_missing"),
      _ ? "pf-status-ok" : "pf-status-error"
    );
    let f = !!this.plugin.settings._paddleocr_configured,
      u = !!this.plugin.settings._vector_db_configured;
    (s(
      i("foundation_paddle_key"),
      f ? "\u2713" : "\u2717",
      f ? i("config_configured") : i("foundation_paddle_missing"),
      f ? "pf-status-ok" : "pf-status-error"
    ),
      s(
        i("foundation_openai_key"),
        u ? "\u2713" : "\u2717",
        u ? i("config_configured") : i("foundation_openai_missing"),
        u ? "pf-status-ok" : "pf-status-error"
      ));
    let h = n.createDiv({ cls: "pf-config-row" });
    h.createEl("span", {
      cls: "pf-config-key",
      text:
        (S = i("md_foundation_legacy_migrate")) != null
          ? S
          : "Migrate legacy credentials",
    });
    let m = h
      .createDiv({ cls: "pf-config-right" })
      .createEl("button", { cls: "paperforge-refresh-btn", text: "Migrate" });
    ((m.title =
      "One-time migration of Obsidian SecretStorage values into the keyring (auth set)"),
      (m.onclick = () => this._migrateLegacyCredentials(m)));
    let v = "1.11.4",
      x = "1.11.4",
      w = !0;
    (s(
      i("foundation_obsidian"),
      w ? "\u2713" : "\u2717",
      w ? `\u2265${v}` : i("foundation_obsidian_old"),
      w ? "pf-status-ok" : "pf-status-error"
    ),
      s(
        i("foundation_python_packages"),
        "\u2014",
        i("foundation_python_packages_checking"),
        "pf-status-checking"
      ));
    let { exec: y } = require("child_process");
    (y(`"${a}" --version`, { timeout: 5e3 }, (E) => {
      let C = n.children[1];
      if (C) {
        let P = C.querySelector(".pf-status-checking");
        P &&
          ((P.textContent = E ? "\u2717" : "\u2713"),
          (P.className = E ? "pf-status-error" : "pf-status-ok"));
      }
    }),
      y(
        `"${a}" -c "import openai; import sqlite3; print('ok')"`,
        { timeout: 1e4 },
        (E) => {
          let C = n.children[n.children.length - 1];
          if (C) {
            let P = C.querySelector(".pf-status-checking");
            if (P) {
              ((P.textContent = E ? "\u2717" : "\u2713"),
                (P.className = E ? "pf-status-error" : "pf-status-ok"));
              let T = C.querySelector(".pf-config-value");
              T &&
                (T.textContent = E
                  ? i("foundation_packages_missing") || "Missing packages"
                  : i("check_bbt_ok") || "Ready");
            }
          }
        }
      ),
      t.user_state !== "ready" &&
        new R.Setting(r)
          .setName(i("foundation_setup"))
          .setDesc(i("foundation_setup_desc"))
          .addButton((E) =>
            E.setButtonText(i("foundation_setup_btn"))
              .setCta()
              .onClick(() => this._startSetupJourney(1))
          ),
      new R.Setting(r)
        .setName(i("foundation_reinstall"))
        .setDesc(i("foundation_reinstall_desc"))
        .addButton((E) =>
          E.setButtonText(i("foundation_reinstall_btn"))
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
    e.createEl("h3", { text: i("md_agent_skills") });
    let s = e.createEl("div", { cls: "paperforge-desc-box" });
    (s.setText(i("feat_skills_desc")),
      s.createEl("br"),
      s.createEl("span", { text: i("feat_skills_system") }));
    let a = J.join(r, t[n]),
      o = [],
      c = [];
    $.existsSync(a) &&
      $.readdirSync(a, { withFileTypes: !0 }).forEach((f) => {
        if (!f.isDirectory()) return;
        let u = J.join(a, f.name, "SKILL.md");
        if (!$.existsSync(u)) return;
        let h = $.readFileSync(u, "utf-8"),
          g = h.match(/^name:\s*(.+)$/m),
          m = h.split(`
`),
          v = m.findIndex((S) => /^description:/.test(S)),
          x = "";
        if (v >= 0) {
          let S = m[v].match(/^description:\s*(.+)$/);
          if (S && S[1] && S[1] !== ">" && S[1] !== "|-" && S[1] !== "|")
            x = S[1].trim();
          else {
            for (
              let E = v + 1;
              E < m.length && (/^\s{2,}/.test(m[E]) || m[E].trim() === "");
              E++
            )
              x += m[E].trim() + " ";
            x = x.trim();
          }
        }
        let w = h.match(/^source:\s*(.+)$/m),
          y = h.match(/^disable-model-invocation:\s*(.+)$/m),
          b = h.match(/^version:\s*(.+)$/m),
          k = {
            name: g ? g[1].trim() : f.name,
            desc: x,
            source: w ? w[1].trim() : "user",
            disabled: !!y && y[1].trim() === "true",
            version: b ? b[1].trim() : "",
            path: u,
            content: h,
            dirName: f.name,
          };
        k.source === "paperforge" ? o.push(k) : c.push(k);
      });
    let p = e.createEl("div", { cls: "paperforge-skills-box" }),
      _ = (f, u, h) => {
        if (u.length === 0) return;
        let g = p.createEl("div", { cls: "paperforge-skills-group" }),
          m = g.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          v = g.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          x = m.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (m.createEl("h4", {
          text: `${f} (${u.length})`,
          cls: "paperforge-skills-subheader",
        }),
          u.forEach((b) => {
            let k = b.name + (b.version ? " v" + b.version : ""),
              S = h
                ? " [" + i("skills_system") + "]"
                : " [" + i("skills_user") + "]",
              E = b.desc || "",
              C = new R.Setting(v).setName(k + S).setDesc(E);
            ((C.settingEl.style.opacity = b.disabled ? "0.4" : "1"),
              C.addToggle((P) => {
                P.setValue(!b.disabled).onChange((T) => {
                  let D = !T,
                    z = b.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? b.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${D}`
                        )
                      : b.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${D}
`
                        );
                  ($.writeFileSync(b.path, z, "utf-8"),
                    (b.disabled = D),
                    (b.content = z),
                    (C.settingEl.style.opacity = b.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let w = h ? "system" : "user";
        ((this._skillsCollapsed[w] || !1) &&
          ((v.style.display = "none"), (x.style.transform = "rotate(-90deg)")),
          m.addEventListener("click", () => {
            (v.style.display !== "none"
              ? ((v.style.display = "none"),
                (x.style.transform = "rotate(-90deg)"))
              : ((v.style.display = ""), (x.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[w] = v.style.display === "none"));
          }));
      };
    (_(i("skills_system"), o, !0),
      _(i("skills_user"), c, !1),
      o.length === 0 &&
        c.length === 0 &&
        p.createEl("p", {
          text: i("skills_empty"),
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
    var o, c;
    this._renderModuleDetailShell(e, "library");
    let t =
        (c = (o = this._capabilityState) == null ? void 0 : o.library) != null
          ? c
          : ie("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_library_connection") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: i("md_library_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          Er(r, {
            whatHappened:
              i("cc_module_library") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: i("library_problem_impact"),
            nextStep: i("problem_use_action"),
            impactLabel: i("problem_impact"),
            nextLabel: i("problem_next"),
            copyLabel: i("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: i("md_library_corpus") }),
      s.createEl("span", { text: i("metric_after_sync") }));
    let a = n.createDiv({ cls: "pf-module-fact" });
    (a.createEl("span", { text: i("md_library_last_sync") }),
      a.createEl("span", {
        text: this.plugin._lastSyncTime || i("metric_not_available"),
      }),
      r.createEl("h3", { text: i("md_configuration") }),
      wr(r, {
        items: [
          {
            label: i("config_zotero_dir"),
            value:
              this.plugin.settings.zotero_data_dir ||
              i("config_not_configured"),
          },
        ],
        configuredLabel: i("config_configured"),
        notConfiguredLabel: i("config_not_configured"),
        onChangeLabel: i("config_change"),
        onChange: () => this._startSetupJourney(2),
      }));
  }
  _renderOcrDetail(e) {
    var p, _, f, u, h, g, m, v, x, w, y, b, k, S;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (_ = (p = this._capabilityState) == null ? void 0 : p.ocr) != null
          ? _
          : ie("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: i("md_ocr_status") }),
      t.user_state === "detection_failed" &&
        r.createEl("p", {
          cls: "pf-status-checking",
          text: i("md_status_refresh_hint"),
        }));
    let n = t.pipeline_version,
      s = t.last_pipeline_version,
      o =
        ((u = (f = t.pipeline_version_summary) == null ? void 0 : f.stale) !=
        null
          ? u
          : 0) > 0,
      c = t.activity_state === "running";
    if (c) {
      we(r, "checking", i("ocr_state_running"));
      let E = this.plugin._ocrProgress,
        C = r.createDiv({ cls: "pf-ocr-progress-card" });
      if (E != null && E.total) {
        let T = i("ocr_progress")
            .replace("{current}", String(E.current))
            .replace("{total}", String(E.total)),
          D = E.key ? " \u2014 " + E.key : "";
        C.createEl("span", {
          cls: "pf-detail-progress",
          text: i("ocr_state_running") + " " + T + D,
        });
        let I = C.createDiv({ cls: "pf-activity-bar" }),
          z = Math.round((E.current / E.total) * 100);
        I.createDiv({
          cls: "pf-activity-bar-fill",
          attr: {
            style: `width: ${z}%`,
            role: "progressbar",
            "aria-valuenow": String(E.current),
            "aria-valuemin": "1",
            "aria-valuemax": String(E.total),
          },
        });
      }
      let P = this.plugin.ocrProcessController;
      P.isRunning &&
        C.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: i("ocr_stop_batch"),
        }).addEventListener("click", () => void P.stop());
    } else if (o) {
      let E = n
        ? i("ocr_state_update_available").replace("{version}", n)
        : i("ocr_state_update_available").replace("{version}", "");
      (we(r, "action_required", E),
        r.createEl("p", {
          text: i("ocr_state_update_description"),
          cls: "setting-item-description",
        }),
        r.createEl("p", {
          text: i("ocr_state_update_safety"),
          cls: "setting-item-description",
        }),
        r
          .createEl("button", {
            cls: "pf-action-btn mod-warning",
            text: i("ocr_action_re_extract"),
          })
          .addEventListener("click", () => {
            new Fe(
              this.app,
              {
                title: i("ocr_modal_title"),
                effectLabel:
                  i("ocr_modal_description") +
                  " " +
                  i("ocr_state_update_safety"),
                confirmLabel: i("ocr_action_re_extract"),
                cancelLabel: i("maintenance_confirm_cancel"),
              },
              () => this._dispatchOcrAction("rebuild")
            ).open();
          }));
    } else if (t.user_state === "ready") {
      we(r, "ready", i("cc_state_ready"));
      let E = n
        ? i("ocr_state_ready")
            .replace(
              "{count}",
              String(
                (x =
                  (v =
                    (g = (h = t.action) == null ? void 0 : h.primary) == null
                      ? void 0
                      : g.scope_count) != null
                    ? v
                    : (m = t.pipeline_version_summary) == null
                      ? void 0
                      : m.total) != null
                  ? x
                  : ""
              )
            )
            .replace("{version}", n)
        : i("ocr_state_ready_no_version").replace(
            "{count}",
            String(
              (S =
                (k =
                  (y = (w = t.action) == null ? void 0 : w.primary) == null
                    ? void 0
                    : y.scope_count) != null
                  ? k
                  : (b = t.pipeline_version_summary) == null
                    ? void 0
                    : b.total) != null
                ? S
                : ""
            )
          );
      (r.createEl("p", { text: E, cls: "pf-status-ok" }),
        V(r, {
          label: i("md_ocr_workspace"),
          onClick: () =>
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }),
        }),
        n &&
          s &&
          n !== s &&
          r
            .createDiv({ cls: "pf-ocr-update-banner" })
            .createEl("span", {
              text: i("ocr_state_update_available").replace("{version}", n),
            }));
    }
    c ||
      V(r, {
        label: i("ocr_configure_credential"),
        onClick: () => this._startSetupJourney(3),
      });
  }
  _renderAgentDetail(e) {
    var u, h;
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
      s = this.plugin.settings.agent_platform || "opencode",
      a = J.join(this._getVaultBasePath(), n[s]),
      o = $.existsSync(a),
      c = t.createDiv({ cls: "pf-module-facts" }),
      p = c.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: i("md_agent_platform") }),
      p.createEl("span", { text: (u = r[s]) != null ? u : s }));
    let _ = c.createDiv({ cls: "pf-module-fact" });
    (_.createEl("span", { text: i("md_agent_deployment") }),
      _.createEl("span", {
        text: o ? i("agent_deployed") : i("agent_not_deployed"),
      }));
    let f = c.createDiv({ cls: "pf-module-fact" });
    if (
      (f.createEl("span", { text: i("agent_live_connection") }),
      f.createEl("span", { text: i("md_agent_connection_unknown") }),
      this._agentPlatformDraft === null)
    )
      V(t, {
        label: i("config_change"),
        onClick: () => {
          ((this._agentPlatformDraft = s), this.display());
        },
      });
    else {
      let g = t.createDiv({ cls: "pf-agent-config-editor" }),
        m = g.createEl("select", {
          attr: { "aria-label": i("md_agent_platform") },
        }),
        v = this.plugin.agentPlatformChoices.length
          ? this.plugin.agentPlatformChoices
          : Object.keys(r);
      for (let w of v) {
        let y = m.createEl("option", {
          text: (h = r[w]) != null ? h : w,
          attr: { value: w },
        });
        y.selected = w === this._agentPlatformDraft;
      }
      m.addEventListener("change", () => {
        this._agentPlatformDraft = m.value;
      });
      let x = g.createDiv({ cls: "pf-agent-config-actions" });
      (V(x, {
        label: i("config_save"),
        onClick: () => {
          var y;
          let w = (y = this._agentPlatformDraft) != null ? y : s;
          ((this.plugin.settings.agent_platform = w),
            Ee(
              this._getVaultBasePath(),
              "agent_platform",
              w,
              this.plugin.settings
            ).catch(
              (b) =>
                new R.Notice(
                  `PaperForge: config set agent_platform failed: ${String(b)}`
                )
            ),
            this.plugin.saveSettings(),
            (this._agentPlatformDraft = null),
            this.display());
        },
      }),
        V(x, {
          label: i("config_cancel"),
          onClick: () => {
            ((this._agentPlatformDraft = null), this.display());
          },
        }),
        V(x, {
          label: i("config_verify"),
          onClick: () => {
            var b;
            let w = (b = this._agentPlatformDraft) != null ? b : s,
              y = $.existsSync(J.join(this._getVaultBasePath(), n[w]));
            new R.Notice(
              y ? i("agent_verify_found") : i("agent_verify_missing")
            );
          },
        }));
    }
    this._renderSkillsList(t);
  }
  _renderMemoryDetail(e) {
    var N, te, re, fe, L, O, ne;
    this._renderModuleDetailShell(e, "memory", !1);
    let t =
        (te = (N = this._capabilityState) == null ? void 0 : N.memory) != null
          ? te
          : ie("memory"),
      r = e.createDiv({ cls: "pf-module-body" }),
      n = (fe = (re = t.reason) == null ? void 0 : re.code) != null ? fe : "",
      s = this.plugin._embedController,
      a = t.activity_state === "running" || !!(s != null && s.busy),
      o = (s == null ? void 0 : s.state) === "failed" ? s.warning : null,
      c = null,
      p = "setting-item-description";
    if (
      (a
        ? ((c = (L = t.activity_label) != null ? L : i("cc_activity_running")),
          (p = "pf-status-ok"))
        : o
          ? ((c = `${i("retrieval_build_failed")}: ${o}`),
            (p = "pf-status-error"))
          : n === "memory.disabled"
            ? (c = i("sr_state_disabled"))
            : n === "memory.db_missing"
              ? (c = i("sr_state_db_missing"))
              : n === "memory.backend_upgrade_available"
                ? (c = i("sr_state_upgrade_available"))
                : n === "memory.vector_build_failed"
                  ? (c = i("sr_state_build_failed"))
                  : n === "memory.schema_stale"
                    ? (c = t.reason.text)
                    : t.user_state === "ready" &&
                      ((c = i("md_retrieval_ready")), (p = "pf-status-ok")),
      c && r.createEl("p", { text: c, cls: p }),
      a && s)
    )
      V(r, { label: i("retrieval_stop"), onClick: () => void s.stop() });
    else if (o)
      V(r, {
        label: i("retrieval_retry"),
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (n === "memory.disabled")
      V(r, {
        label: i("sr_action_enable") || "Enable Smart Retrieval",
        onClick: () => {
          (this.plugin.settings.features ||
            (this.plugin.settings.features = {
              memory_layer: !0,
              vector_db: !1,
            }),
            (this.plugin.settings.features.vector_db = !0),
            this.plugin
              .saveSettings()
              .then(() => this._refreshAllReadModels()));
        },
      });
    else if (n === "memory.db_missing" || n === "memory.index_stale")
      V(r, {
        label: i("sr_action_build") || "Build Index",
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (n === "memory.backend_upgrade_available")
      V(r, {
        label: i("sr_action_upgrade") || "Upgrade",
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (
      n === "memory.vector_build_failed" ||
      n === "memory.vector_build_interrupted"
    )
      V(r, {
        label: i("cc_action_rebuild_derived") || "Rebuild Index",
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (
      (O = t.action) != null &&
      O.primary &&
      t.user_state !== "ready" &&
      t.user_state !== "not_enabled"
    ) {
      let F =
          "action_" +
          ((ne = t.action.primary.action_id) != null
            ? ne
            : t.action.primary.verb
          ).replace(/[.-]/g, "_"),
        H =
          i(F) !== F
            ? i(F)
            : i("cc_action_" + t.action.primary.verb) !==
                "cc_action_" + t.action.primary.verb
              ? i("cc_action_" + t.action.primary.verb)
              : i("cc_action_probe");
      V(r, {
        label: H,
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    }
    let _ =
        t.user_state === "ready"
          ? i("sr_db_exists") || "Active"
          : i("sr_db_missing") || "Not built",
      f = "vec0",
      u = this.plugin.settings._vector_db_configured || !1,
      h = u
        ? i("api_key_set") || "Configured"
        : i("api_key_missing") || "Not configured",
      g = r.createDiv({ cls: "pf-sr-info-card" }),
      m = [
        [i("sr_db_status") || "Database", _],
        [i("sr_backend") || "Backend", f],
        [i("sr_api_key") || "API Key", h],
      ];
    for (let [F, H] of m) {
      let se = g.createDiv({ cls: "pf-sr-info-row" });
      (se.createEl("span", { cls: "pf-sr-info-label", text: F }),
        se.createEl("span", { cls: "pf-sr-info-value", text: H }));
    }
    let v = !u,
      x = r.createDiv({ cls: "pf-sr-cfg" }),
      w = x.createDiv({ cls: "pf-sr-cfg-head" });
    w.createEl("span", {
      cls: "pf-sr-cfg-title",
      text: i("sr_config_label") || "\u914D\u7F6E",
    });
    let y = w.createEl("span", {
        cls: "pf-sr-cfg-icon",
        text: v ? "\u25BC" : "\u25B6",
      }),
      b = x.createDiv({ cls: "pf-sr-cfg-body" });
    ((b.style.display = v ? "" : "none"),
      w.addEventListener("click", () => {
        let F = b.style.display !== "none";
        ((b.style.display = F ? "none" : ""),
          (y.textContent = F ? "\u25B6" : "\u25BC"));
      }));
    let k = b.createDiv({ cls: "pf-sr-cfg-row" });
    k.createEl("label", {
      text: i("feat_openai_key") || "API Key",
      cls: "pf-sr-cfg-lbl",
    });
    let S = k.createEl("input", {
        cls: "pf-sr-cfg-input",
        attr: {
          type: "password",
          placeholder: u ? "\u2022\u2022\u2022\u2022" : "sk-...",
        },
      }),
      E = null;
    S.addEventListener("input", () => {
      let F = S.value;
      F &&
        (E && clearTimeout(E),
        (E = setTimeout(async () => {
          ((await this._storeVectorDbCredential(F)) &&
            ((S.value = ""),
            (S.placeholder = "\u2022\u2022\u2022\u2022"),
            (b.style.display = "none"),
            (y.textContent = "\u25B6")),
            (E = null));
        }, 600)));
    });
    let C = b.createDiv({ cls: "pf-sr-cfg-row" });
    C.createEl("label", {
      text: i("feat_api_base_url") || "API Base URL",
      cls: "pf-sr-cfg-lbl",
    });
    let P = C.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "https://api.openai.com/v1" },
    });
    ((P.value = this.plugin.settings.vector_db_api_base || ""),
      P.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_base = P.value),
          Ee(
            this._getVaultBasePath(),
            "vector_db_api_base",
            P.value,
            this.plugin.settings
          ).catch(
            (F) =>
              new R.Notice(
                `PaperForge: config set vector_db_api_base failed: ${String(F)}`
              )
          ),
          this._refreshVectorDbCredentialStatus());
      }));
    let T = b.createDiv({ cls: "pf-sr-cfg-row" });
    T.createEl("label", {
      text: i("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    let D = T.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "text-embedding-3-small" },
    });
    if (
      ((D.value =
        this.plugin.settings.vector_db_api_model || "text-embedding-3-small"),
      D.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_model = D.value),
          Ee(
            this._getVaultBasePath(),
            "vector_db_api_model",
            D.value,
            this.plugin.settings
          ).catch(
            (F) =>
              new R.Notice(
                `PaperForge: config set vector_db_api_model failed: ${String(F)}`
              )
          ),
          this._refreshVectorDbCredentialStatus());
      }),
      t.capability_state === "needs_action" && n !== "memory.disabled")
    ) {
      let F = r.createDiv({ cls: "pf-sr-impact-box" });
      (F.createEl("strong", {
        text: i("cc_badge_action_required") || "Action Required",
      }),
        F.createEl("p", {
          text:
            n === "memory.db_missing" || n === "memory.index_stale"
              ? i("sr_impact_db_missing") ||
                "Smart Retrieval needs an OpenAI API key and vector index. Click Build Index to get started."
              : n === "memory.backend_upgrade_available"
                ? i("sr_impact_upgrade") ||
                  "A new vector backend is available. Upgrade to improve search quality."
                : n === "memory.vector_build_failed"
                  ? i("sr_impact_build_failed") ||
                    "The last build failed. Check your API key and try again."
                  : i("sr_impact_schema_stale") ||
                    "The vector schema is outdated. Rebuild to match the current library.",
        }));
    }
    let I = r.createEl("details", { cls: "pf-sr-diagnostics" });
    I.createEl("summary", {
      text: i("cc_diagnostic_toggle") || "Advanced Status",
    });
    let z = I.createDiv({ cls: "pf-sr-diagnostics-body" }),
      ee = this._getVaultBasePath(),
      A = this.plugin.settings.vector_db_api_base || "-",
      U = z.createEl("table", { cls: "pf-diag-table" }),
      X = new Map(),
      B = (F, H) => {
        if (!X.has(F)) {
          let le = U.createEl("tr");
          le.createEl("td", { cls: "pf-diag-label", text: F });
          let Ge = le.createEl("td", { cls: "pf-diag-value" });
          (X.set(F, le), (Ge.textContent = H));
          return;
        }
        let se = X.get(F).children[1];
        se.textContent = H;
      };
    (B("FTS5 Papers", "\u2026"),
      B("FTS5 Fresh", "\u2026"),
      B("Needs Rebuild", "\u2026"),
      B("", ""),
      B("Vector Backend", "vec0 (sqlite-vec)"),
      B("Vector Model", "\u2026"),
      B("Vector Mode", "\u2026"),
      B("Vector Dimension", "\u2026"),
      B("Base URL", A),
      ee &&
        (yr(ee, this.plugin.settings)
          .then((F) => {
            var H;
            (B(
              "FTS5 Papers",
              String(
                (H = F == null ? void 0 : F.paper_count_db) != null ? H : "?"
              )
            ),
              B("FTS5 Fresh", F != null && F.fresh ? "Yes" : "Stale"),
              B("Needs Rebuild", F != null && F.needs_rebuild ? "Yes" : "No"));
          })
          .catch(() => {}),
        Ke(ee, this.plugin.settings)
          .then((F) => {
            var se, le, Ge, jt, Kt, qt, Ut, Zt, Wt;
            (B(
              "Vector Model",
              String((se = F == null ? void 0 : F.model) != null ? se : "-")
            ),
              B(
                "Vector Mode",
                String((le = F == null ? void 0 : F.mode) != null ? le : "-")
              ),
              B(
                "Body Chunks",
                String(
                  (Ge = F == null ? void 0 : F.body_chunk_count) != null
                    ? Ge
                    : 0
                )
              ),
              B(
                "Object Chunks",
                String(
                  (jt = F == null ? void 0 : F.object_chunk_count) != null
                    ? jt
                    : 0
                )
              ),
              B(
                "Total Chunks",
                String(
                  (Kt = F == null ? void 0 : F.total_chunks) != null ? Kt : 0
                )
              ));
            let H =
              (qt = F == null ? void 0 : F.build_state) != null ? qt : void 0;
            (B(
              "Build Status",
              String((Ut = H == null ? void 0 : H.status) != null ? Ut : "-")
            ),
              B(
                "Build Progress",
                `${(Zt = H == null ? void 0 : H.current) != null ? Zt : "?"}/${(Wt = H == null ? void 0 : H.total) != null ? Wt : "?"}`
              ));
          })
          .catch(() => {})),
      B("", ""),
      B("Capability State", t.capability_state),
      B("Severity", t.severity),
      B("Reason Code", n));
  }
  _dispatchModuleAction(e, t) {
    var n, s;
    let r = (n = t.action) == null ? void 0 : n.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    if (r.safety_class !== "safe" && r.confirmation_required) {
      let a =
          r.action_id === "ocr.run"
            ? i("ocr_run_confirm_title")
            : r.action_id === "embed.build"
              ? i("embed_rebuild_title")
              : r.label,
        o =
          r.action_id === "ocr.run"
            ? i("ocr_run_confirm_body")
            : r.action_id === "embed.build"
              ? i("embed_rebuild_body")
              : (s =
                    (r.replacement_facts || []).join("; ") ||
                    r.confirmation_prompt) != null
                ? s
                : i("confirmation_default_effect");
      new Fe(this.app, { title: a, effectLabel: o }, () =>
        this._runAllowedDispatch(e, r, t)
      ).open();
      return;
    }
    this._runAllowedDispatch(e, r, t);
  }
  _runAllowedDispatch(e, t, r) {
    var a, o, c;
    let n = t.verb,
      s = t.action_id;
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
      if (s === "foundation.update") {
        this._runUpdateAction();
        return;
      }
      (new R.Notice(
        i("update_python_manual") ||
          "Python 3.11+ upgrade requires a manual install (python.org or your package manager)."
      ),
        this._probeModule(e));
      return;
    }
    if (n === "install" && s === "memory.install_vector_deps") {
      this._startSetupJourney(3);
      return;
    }
    if (e === "library") {
      if (n === "sync" || s === "library.sync") {
        this._runManualSync();
        return;
      }
    } else if (e === "ocr") {
      if (n === "run" || s === "ocr.run") {
        this._dispatchOcrAction("run");
        return;
      }
      if (n === "rebuild_derived" || s === "ocr.rebuild_derived") {
        this._dispatchOcrAction("rebuild");
        return;
      }
      if (n === "redo" || s === "ocr.redo") {
        this._dispatchOcrAction("redo");
        return;
      }
      if (n === "investigate") {
        let p = this._getVaultBasePath(),
          _ = Hr(
            r.reason.code,
            r.reason.text,
            (c =
              (o = (a = r.action) == null ? void 0 : a.primary) == null
                ? void 0
                : o.scope_count) != null
              ? c
              : 0,
            p
          );
        new at(
          this.app,
          _,
          "https://github.com/LLLin000/PaperForge/issues/new"
        ).open();
        return;
      }
    } else if (e === "memory") {
      if (n === "run" || n === "rebuild_index") {
        s === "embed.build"
          ? this._dispatchMemoryBuild("embed")
          : s === "memory.upgrade_backend"
            ? this._runBackendMigration()
            : this._dispatchMemoryBuild("build");
        return;
      }
      if (n === "restore_backup" || s === "memory.restore_backup") {
        this._callPython(["memory", "restore-backup"], {
          timeout: 3e4,
          onClose: () => {
            this._refreshAllReadModels();
          },
        });
        return;
      }
    }
    (new R.Notice(
      (i("action_unknown_pair") || "Unknown action: {verb}").replace(
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
      new R.Notice(i("retrieval_no_python") || "No Python runtime available");
      return;
    }
    (0, G.execFile)(
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
      { cwd: e, timeout: 6e5, env: Y() },
      (r, n, s) => {
        (r
          ? new R.Notice(
              i("update_failed") ||
                `Update failed: ${(s == null ? void 0 : s.trim()) || r.message}`
            )
          : new R.Notice(i("update_done") || "PaperForge updated"),
          this._refreshAllReadModels());
      }
    );
  }
  _runBackendMigration() {
    this._callPython(["embed", "migrate", "--json"], {
      timeout: 6e5,
      onClose: (e, t, r) => {
        (e === 0
          ? new R.Notice(i("migrate_done") || "Backend migrated to sqlite-vec")
          : new R.Notice(
              i("migrate_failed") ||
                `Backend migration failed: ${(r == null ? void 0 : r.trim()) || "unknown error"}`
            ),
          this._refreshAllReadModels());
      },
    });
  }
  _dispatchOcrAction(e) {
    var a;
    let t = this.plugin.ocrProcessController;
    if (e === "run" && typeof this.plugin.requestOcrRun == "function") {
      this.plugin.requestOcrRun(!0);
      return;
    }
    if (t.isRunning) {
      new R.Notice(i("ocr_already_running"));
      return;
    }
    let r = {
        run: i("ocr_activity_run"),
        rebuild: i("ocr_activity_rebuild"),
        redo: i("ocr_activity_redo"),
      },
      n = (a = this._capabilityState) != null ? a : {};
    (n.ocr &&
      ((n.ocr.activity_state = "running"),
      (n.ocr.activity_label = r[e] || i("cc_activity_running")),
      (n.ocr.activity_progress = { current: 0, total: 1 })),
      (this.plugin._ocrBuffer = ""),
      (this.plugin._ocrProgress = { current: 0, total: 1, key: "" }),
      (this.plugin._ocrStderr = ""),
      (this.plugin._ocrWasStopped = !1),
      this.display());
    let s = {
      run: i("ocr_run_complete"),
      rebuild: i("ocr_rebuild_complete"),
      redo: i("ocr_redo_complete"),
    };
    t.start(e, {
      all: e === "rebuild",
      callbacks: {
        onProgress: (o, c, p) => {
          ((this.plugin._ocrProgress = { current: o, total: c, key: p }),
            n.ocr && (n.ocr.activity_progress = { current: o, total: c }),
            this.display());
        },
        onNotice: (o) => new R.Notice(o, 8e3),
      },
    })
      .then((o) => {
        if (
          (n.ocr &&
            ((n.ocr.activity_state = "idle"),
            (n.ocr.activity_label = null),
            (n.ocr.activity_progress = null)),
          o.ok)
        )
          new R.Notice(s[e] || "OCR completed");
        else if (o.stopped)
          ((this.plugin._ocrWasStopped = !1),
            new R.Notice(i("ocr_stopped_notice")));
        else {
          let c = o.failedKeys.join(", "),
            p =
              o.skippedKeys.length > 0
                ? `${c ? c + " " : ""}(${o.skippedKeys.length} skipped)`
                : c;
          new R.Notice(i("ocr_failed_notice") + (p ? ": " + p : ""), 8e3);
        }
        (this._refreshAllReadModels(), this.display());
      })
      .catch((o) => {
        (n.ocr &&
          ((n.ocr.activity_state = "idle"),
          (n.ocr.activity_label = null),
          (n.ocr.activity_progress = null)),
          new R.Notice(
            i("ocr_failed_notice") +
              ": " +
              ((o == null ? void 0 : o.message) || i("ocr_error_notice")),
            8e3
          ),
          this._refreshAllReadModels(),
          this.display());
      });
  }
  _dispatchMemoryBuild(e) {
    var s, a;
    let t = this.app.vault.adapter.basePath,
      r = (s = this._capabilityState) != null ? s : {};
    (e !== "embed" &&
      r.memory &&
      ((r.memory.activity_state = "running"),
      (r.memory.activity_label = "Building memory\u2026")),
      this.display());
    let n = e === "embed" ? ["embed", "build", "--force"] : ["memory", "build"];
    if (e === "embed") {
      if ((a = this.plugin._embedController) != null && a.busy) {
        new R.Notice(i("embed_already_running"));
        return;
      }
      let o = this._resolveRuntimeCommand(t);
      if (!o) {
        (new R.Notice(i("retrieval_no_python")), this._refreshAllReadModels());
        return;
      }
      (() => {
        let p = [...o.args, "-m", "paperforge", "--vault", t],
          _ = new rt({
            vaultPath: t,
            pythonPath: o.path,
            pythonArgs: p,
            resolveEnv: () => ue(null, "embed"),
            runShort: (f, u) => {
              let { promise: h, resolve: g } = Fr();
              return (
                (0, G.execFile)(
                  o.path,
                  [...o.args, "-m", "paperforge", "--vault", t, ...f],
                  { cwd: t, timeout: u, env: Y() },
                  (m, v, x) => {
                    g({
                      code: m ? 1 : 0,
                      stdout: v != null ? v : "",
                      stderr: x != null ? x : "",
                    });
                  }
                ),
                h
              );
            },
            callbacks: {
              onStateChange: (f, u, h, g) => {
                ((this.plugin._embedProgress = {
                  current: u.current,
                  total: u.total,
                  key: u.key,
                }),
                  r.memory &&
                    (f === "running" ||
                    f === "resolving_credentials" ||
                    f === "stopping"
                      ? ((r.memory.activity_state = "running"),
                        (r.memory.activity_label =
                          f === "stopping"
                            ? i("embed_activity_stopping")
                            : i("embed_activity_building")),
                        (r.memory.activity_progress = {
                          current: u.current,
                          total: u.total || 1,
                        }))
                      : ((r.memory.activity_state = "idle"),
                        (r.memory.activity_label = null),
                        (r.memory.activity_progress = null))),
                  f === "success"
                    ? new R.Notice(i("embed_build_complete"))
                    : f === "success_with_warning"
                      ? new R.Notice(
                          i("embed_build_warning").replace(
                            "{detail}",
                            h || i("embed_bookkeeping_incomplete")
                          ),
                          8e3
                        )
                      : f === "failed"
                        ? new R.Notice(
                            i("sr_build_failed_notice").replace(
                              "{detail}",
                              h || "exit code ?"
                            ),
                            8e3
                          )
                        : f === "cancelled" &&
                          new R.Notice(i("embed_build_stopped"), 8e3),
                  this.display());
              },
            },
          });
        ((this.plugin._embedController = _), _.start("--force"));
      })();
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (o, c, p) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            o === 0
              ? new R.Notice(i("feat_memory_rebuild_done"))
              : new R.Notice(
                  i("feat_memory_rebuild_failed") +
                    (p ? " " + p.slice(0, 120) : ""),
                  8e3
                ),
            this._refreshAllReadModels(),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t, r = !0) {
    var m, v, x, w, y, b;
    (e.classList.add("pf-module-detail"),
      e
        .createEl("button", {
          cls: "pf-back-btn",
          text: i("btn_back_to_overview"),
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
    let s = this._getOverviewModules(),
      a = e.createDiv({
        cls: "pf-module-detail-selector",
        attr: { role: "tablist", "aria-label": i("md_module_switcher") },
      });
    for (let k of s)
      a.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (k.id === t ? " pf-module-detail-btn--active" : ""),
        text: k.label,
        attr: { role: "tab", "aria-selected": String(k.id === t) },
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = k.id),
          (this._focusTargetId = "#pf-" + k.id + "-detail-heading"),
          this.display());
      });
    let o = e.createEl("select", {
      cls: "pf-module-switcher",
      attr: { "aria-label": i("md_module_switcher") },
    });
    for (let k of s) {
      let S = o.createEl("option", { text: k.label, attr: { value: k.id } });
      S.selected = k.id === t;
    }
    o.addEventListener("change", () => {
      ((this._selectedDetailModule = o.value),
        (this._focusTargetId = "#pf-" + o.value + "-detail-heading"),
        this.display());
    });
    let c =
        t === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (v = (m = this._capabilityState) == null ? void 0 : m[t]) != null
            ? v
            : ie(t),
      p =
        (x = c.user_state) != null
          ? x
          : c.capability_state === "ready"
            ? "ready"
            : "action_required",
      _ = e.createDiv({
        cls: "pf-module-summary",
        attr: { "aria-live": "polite" },
      }),
      f = _.createDiv({ cls: "pf-module-summary-header" });
    (f.createEl("h2", {
      cls: "pf-module-summary-name pf-module-detail-heading",
      text: this._getUserModuleName(t),
      attr: { id: "pf-" + t + "-detail-heading", tabindex: "-1" },
    }),
      we(f, p, this._getUserStateLabel(p)),
      _.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(t, c),
      }),
      c.activity_state === "running" &&
        xr(_, {
          label: i("cc_activity_running"),
          progress: c.activity_progress,
        }));
    let u = (w = c.action) == null ? void 0 : w.primary;
    if (r && u && p !== "ready" && t !== "agent") {
      let k =
          "action_" +
          ((y = u.action_id) != null ? y : u.verb).replace(/[.-]/g, "_"),
        S = i(k),
        E =
          S !== k
            ? S
            : i("cc_action_" + u.verb) !== "cc_action_" + u.verb
              ? i("cc_action_" + u.verb)
              : i("cc_action_probe");
      V(_, {
        label: E,
        loading: c.activity_state === "running",
        onClick: () => this._dispatchModuleAction(t, c),
      });
    }
    let h = _.createEl("details", { cls: "pf-module-diagnostics" });
    h.createEl("summary", { text: i("advanced_diagnostics") });
    let g = h.createDiv({ cls: "pf-module-diagnostics-body" });
    (g.createEl("div", { text: i("cc_diag_module") + ": " + c.module }),
      g.createEl("div", {
        text: i("cc_diag_state") + ": " + this._getUserStateLabel(p),
      }),
      g.createEl("div", { text: i("cc_diag_severity") + ": " + c.severity }),
      g.createEl("div", {
        text: i("cc_diag_activity") + ": " + c.activity_state,
      }),
      g.createEl("div", { text: i("cc_diag_reason") + ": " + c.reason.code }),
      g.createEl("div", {
        text: i("cc_diag_ttl") + ": " + c.ttl_seconds + "s",
      }));
    for (let k of (b = c.notices) != null ? b : [])
      g.createEl("div", { text: k.message });
    g.createEl("div", {
      text:
        i("cc_diag_updated") + ": " + new Date(c.updated_at).toLocaleString(),
    });
  }
  _renderHelpTab(e) {
    (e.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: i("help_eyebrow") || "help",
    }),
      e.createEl("h1", { cls: "pf-cc-title", text: i("help_title") || "Help" }),
      e.createEl("p", {
        cls: "pf-cc-lede",
        text:
          i("help_lede") ||
          "Open the relevant module, or copy a diagnostic for support.",
      }));
    let t = e.createEl("p", {
        cls: "pf-help-loading",
        text: "Loading help content\u2026",
      }),
      r = yt(this.app),
      n = "https://api.github.com/repos/LLLin000/PaperForge/contents/docs/help",
      s = ["guide", "faq", "support"],
      a = this;
    Promise.all(
      s.map((o) =>
        fetch(`${n}/${r}/${o}.md`)
          .then((c) => (c.ok ? c.json() : Promise.reject()))
          .then((c) => {
            let p = atob(c.content.replace(/\n/g, "")),
              _ = new Uint8Array(p.length);
            for (let f = 0; f < p.length; f++) _[f] = p.charCodeAt(f);
            return new TextDecoder().decode(_);
          })
          .then((c) => ({ name: o, text: c }))
          .catch(() => ({ name: o, text: "" }))
      )
    )
      .then((o) => {
        t.remove();
        for (let { name: c, text: p } of o) {
          if (!p) continue;
          let _ = p.match(/^#\s+(.+)/m),
            f = _ ? _[1] : c,
            u = p.replace(/^#\s+.+(\r?\n|$)/, "").trim(),
            h = e.createEl("details", {
              cls: "pf-help-section",
              attr: c === "support" ? { open: "true" } : {},
            });
          h.createEl("summary", { cls: "pf-help-section-title", text: f });
          let g = h.createDiv({ cls: "pf-help-section-body" });
          c === "support"
            ? (R.MarkdownRenderer.render(a.app, u, g, "", a.plugin),
              g
                .createEl("button", {
                  cls: "pf-help-diagnostic-btn",
                  text: i("help_copy") || "Copy Support Diagnostic",
                })
                .addEventListener("click", () => a._buildAndCopyDiagnostic()))
            : R.MarkdownRenderer.render(a.app, u, g, "", a.plugin);
        }
      })
      .catch(() => {
        t.setText(i("help_load_error") || "Failed to load help content.");
      });
  }
  _execMemoryStatus(e, t, r) {
    let n = Y();
    (0, G.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(a);
          if (o.ok) {
            let c = o.data,
              p = c.fresh ? "fresh" : "stale";
            r(
              `Papers: ${c.paper_count_db} | ${p}${c.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (o) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    let n = Y();
    (0, G.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(a);
          o.ok
            ? r(
                `Chunks: ${o.data.chunk_count} | ${o.data.model} | ${o.data.mode}`
              )
            : r("Could not parse status.");
        } catch (o) {
          r("Could not parse status.");
        }
      }
    );
  }
  _callPython(e, t) {
    let r = this.app.vault.adapter.basePath,
      n = this._resolveRuntimeCommand(r);
    if (!n)
      return (
        t && t.onClose && t.onClose(1, "", "No python runtime available"),
        null
      );
    let s = [...n.args, "-m", "paperforge", "--vault", r, ...e],
      a = (t == null ? void 0 : t.credentialType) && !(t != null && t.env),
      o = (_) => {
        let f = (0, G.spawn)(n.path, s, { cwd: r, env: _, windowsHide: !0 });
        return (
          t.onData && f.stdout.on("data", t.onData),
          t.onStderr && f.stderr.on("data", t.onStderr),
          t.onError && f.on("error", t.onError),
          f.on("close", t.onClose),
          f
        );
      },
      c = (_) => {
        (0, G.execFile)(
          n.path,
          s,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: _ },
          (f, u, h) => {
            t && t.onClose && t.onClose(f ? 1 : 0, u, h);
          }
        );
      };
    if (a)
      return (
        ue(null, t.credentialType).then((_) => {
          t && t.stream ? o(_) : c(_);
        }),
        null
      );
    let p = (t == null ? void 0 : t.env) || Y();
    return t && t.stream ? o(p) : (c(p), null);
  }
  _renderMemoryStatusText(e, t, r) {
    ((e.innerHTML = ""),
      e.createEl("span", { text: t, cls: "paperforge-memory-text" }),
      r === "syncing"
        ? e.createEl("span", {
            text: "Syncing...",
            cls: "paperforge-sync-status",
          })
        : r && e.createEl("span", { text: r, cls: "paperforge-sync-status" }));
    let n = e.createEl("button", {
      cls: "paperforge-rebuild-btn",
      text: i("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let a = this.app.vault.adapter.basePath,
          o = this._resolveRuntimeCommand(a);
        if (!(o != null && o.path)) {
          new R.Notice(i("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", o.path),
          n.setText(i("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (c, p, _) => {
              (console.log(
                "[PaperForge] memory build exit:",
                c ? "FAIL:" + c : "OK",
                (p || "").slice(0, 200),
                (_ || "").slice(0, 200)
              ),
                n.setText(i("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                c === 0
                  ? new R.Notice(i("feat_memory_rebuild_done"))
                  : new R.Notice(
                      i("feat_memory_rebuild_failed") +
                        (_ ? " " + _.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = i("feat_memory_rebuild_done")),
                this._refreshAllReadModels());
            },
          }));
      }));
    let s = e.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    ((s.title = "Sync now"),
      (s.onclick = () => {
        ((this._memoryStatusText = null), this._runManualSync());
      }));
  }
  _getBuildCommand(e) {
    let t = this.app.vault.adapter.basePath,
      r = this._resolveRuntimeCommand(t);
    return r ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    var s;
    let e = this.app.vault.adapter.basePath,
      t = this._resolveRuntimeCommand(e);
    if (!(t != null && t.path)) return;
    let r = (s = this._capabilityState) != null ? s : {};
    r.library &&
      ((r.library.activity_state = "running"),
      (r.library.activity_label = "Syncing library\u2026"));
    let n = document.querySelector(".paperforge-memory-status");
    (n && this._renderMemoryStatusText(n, "Checking...", "syncing"),
      (this.plugin._autoSyncRunning = !0),
      (this._libraryRunning = !0),
      this.display(),
      this._callPython(["sync", "--json"], {
        timeout: 12e4,
        onClose: (a, o) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            a === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime),
              nt(o, {
                vaultPath: e,
                resolveCommand: (c) => this._resolveRuntimeCommand(c),
              })),
            this._refreshAllReadModels(a != null ? a : 1),
            this._refreshSnapshots(e),
            ot(this.app, this.plugin, e));
        },
      }));
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
      (0, G.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        () => {
          var a, o, c, p, _, f;
          this._refreshPending = !1;
          let n = (a = this._capabilityState) == null ? void 0 : a.memory,
            s = (o = this._capabilityState) == null ? void 0 : o.embed;
          ((this._memoryStatusText =
            n && (p = (c = n.reason) == null ? void 0 : c.text) != null
              ? p
              : null),
            (this._embedStatusText =
              s && (f = (_ = s.reason) == null ? void 0 : _.text) != null
                ? f
                : null),
            this.display());
        }
      ));
  }
  _renderVectorSection(e) {
    if (
      (e.createEl("h4", { text: "Smart Retrieval" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(i("feat_vector_desc")),
      new R.Setting(e)
        .setName(i("feat_vector_enable"))
        .setDesc(i("feat_vector_enable_desc"))
        .addToggle((c) => {
          c.setValue(!!this.plugin.settings.features.vector_db).onChange(
            (p) => {
              ((this.plugin.settings.features.vector_db = p),
                this.plugin.saveSettings(),
                (this._vectorDepsOk = null),
                (this._embedStatusText = null),
                this.display());
            }
          );
        }),
      !this.plugin.settings.features.vector_db)
    )
      return;
    let r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-vec-header" }),
      s = n.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    n.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: i("feat_vector_config_label"),
    });
    let a = e.createEl("div", { cls: "paperforge-vector-config" }),
      o = (c) => {
        ((a.style.display = c ? "none" : ""),
          (s.style.transform = c ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (o(Nt(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let c = $r(this._featurePanelsCollapsed, "vectorConfig", !1);
        o(c);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(a, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(a);
      return;
    }
    if (this._vectorDepsOk === null && r) {
      Ke(r, this.plugin.settings)
        .then((c) => {
          var p;
          ((this._vectorDepsOk = c ? !!c.deps_installed : !1),
            this._vectorDepsOk &&
              (this._embedStatusText = String(
                (p = c == null ? void 0 : c.mode) != null ? p : ""
              )),
            this.display());
        })
        .catch(() => {
          ((this._vectorDepsOk = !1), this.display());
        });
      return;
    }
  }
  _renderApiConfig(e) {
    let r =
        this.plugin.settings._vector_db_configured || !1
          ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
          : "sk-...",
      n = null;
    (new R.Setting(e)
      .setName(i("feat_openai_key"))
      .setDesc(i("feat_openai_key_desc"))
      .addText((s) => {
        ((s.inputEl.type = "password"),
          s
            .setPlaceholder(r)
            .setValue("")
            .onChange((a) => {
              a &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  ((await this._storeVectorDbCredential(a)) && s.setValue(""),
                    (n = null));
                }, 600)));
            }));
      }),
      new R.Setting(e)
        .setName(i("feat_api_base_url"))
        .setDesc(i("feat_api_base_url_desc"))
        .addText((s) => {
          s.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_base = a),
                Ee(
                  this._getVaultBasePath(),
                  "vector_db_api_base",
                  a,
                  this.plugin.settings
                ).catch(
                  (o) =>
                    new R.Notice(
                      `PaperForge: config set vector_db_api_base failed: ${String(o)}`
                    )
                ),
                this._refreshVectorDbCredentialStatus());
            });
        }),
      new R.Setting(e)
        .setName(i("feat_api_model"))
        .setDesc(i("feat_api_model_desc"))
        .addText((s) => {
          s.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_model = a),
                Ee(
                  this._getVaultBasePath(),
                  "vector_db_api_model",
                  a,
                  this.plugin.settings
                ).catch(
                  (o) =>
                    new R.Notice(
                      `PaperForge: config set vector_db_api_model failed: ${String(o)}`
                    )
                ),
                this._refreshVectorDbCredentialStatus());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(i("feat_deps_missing")),
      new R.Setting(e)
        .setName(i("feat_install_deps"))
        .setDesc(i("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(i("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                s = this._resolveRuntimeCommand(n);
              if (!(s != null && s.path)) {
                new R.Notice(i("feat_no_python"));
                return;
              }
              (r.setButtonText(i("feat_installing")), r.setDisabled(!0));
              let a = "chromadb openai",
                o = new R.Notice(
                  i("feat_installing_pkgs").replace("{pkgs}", a),
                  0
                );
              try {
                let c = Object.assign(Y(), {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  p = a.split(" ");
                (await new Promise((_, f) => {
                  (0, G.execFile)(
                    s.path,
                    [...s.args, "-m", "pip", "install", ...p],
                    { cwd: n, timeout: 3e5, env: c, windowsHide: !0 },
                    (u) => {
                      u ? f(u) : _();
                    }
                  );
                }),
                  o.hide(),
                  new R.Notice(i("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText =
                    i("feat_deps_installed") || "Dependencies installed"),
                  this.display());
              } catch (c) {
                (o.hide(),
                  new R.Notice(
                    i("feat_install_failed") + (c.stderr || c.message || c)
                  ),
                  r.setButtonText(i("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    var p;
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(
        (p = this._embedStatusText) != null
          ? p
          : i("feat_vector_ready") || "Vector index ready"
      ),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: i("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let a = n.createEl("div", { cls: "paperforge-embed-controls" }),
      o = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      var ee;
      (a.empty(), o.empty());
      let _ = (ee = this.plugin._embedStatusCache) != null ? ee : {},
        f = _.build_state,
        u = f && typeof f == "object" && !Array.isArray(f) ? f : {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          u.status === "running" &&
          (this.plugin._embedProgress = {
            current: typeof u.current == "number" ? u.current : 0,
            total: typeof u.total == "number" ? u.total : 1,
            key: typeof u.paper_id == "string" ? u.paper_id : "",
          }));
      let { current: h, total: g, key: m } = this.plugin._embedProgress,
        v = typeof _.body_chunk_count == "number" ? _.body_chunk_count : 0,
        x = typeof _.object_chunk_count == "number" ? _.object_chunk_count : 0,
        y = (typeof _.chunk_count == "number" ? _.chunk_count : 0) + v + x,
        b = y > 0,
        k = typeof _.corrupted == "boolean" && _.corrupted,
        S = !!this.plugin._embedProcess,
        E = !this.plugin._embedProcess && u.status === "running",
        C = _.deps_installed !== void 0 ? !!_.deps_installed : !0,
        P = typeof u.status == "string" ? u.status : "",
        T = typeof u.message == "string" ? u.message : "",
        D = async (A) => {
          var B;
          if (A === "--resume" && b && !k) {
            let N = i("retrieval_rebuild_warning").replace("{n}", String(y));
            if (!confirm(N)) return;
          }
          if (A === "--force" && b && !k) {
            let N =
              "Force rebuild will replace " +
              y +
              " existing chunk(s). Continue?";
            if (!confirm(N)) return;
          }
          let U = this._resolveRuntimeCommand(t);
          if (!(U != null && U.path)) {
            new R.Notice(i("retrieval_no_python"));
            return;
          }
          let X = await ue(null, "embed");
          ((X.PYTHONIOENCODING = "utf-8"),
            (X.PYTHONUTF8 = "1"),
            (X.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (X.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", A],
              {
                stream: !0,
                env: X,
                onData: (N) => {
                  var L;
                  let te =
                      typeof N == "string"
                        ? N
                        : Buffer.isBuffer(N)
                          ? N.toString("utf-8")
                          : String(N),
                    { events: re, buffer: fe } = zr(
                      te,
                      (L = this.plugin._embedBuffer) != null ? L : ""
                    );
                  this.plugin._embedBuffer = fe;
                  for (let O of re)
                    O.event === "start"
                      ? (this.plugin._embedProgress.total = O.total || 0)
                      : O.event === "progress"
                        ? ((this.plugin._embedProgress.current =
                            O.current || 0),
                          (this.plugin._embedProgress.key = O.item_id || ""))
                        : (O.event === "result" ||
                            O.event === "error" ||
                            O.event === "cancelled") &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                  this.display();
                },
                onStderr: (N) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(N)));
                },
                onError: (N) => {
                  ((this.plugin._embedProcess = null),
                    new R.Notice(
                      i("feat_build_failed") + ": " + (N.message || N)
                    ),
                    this.display());
                },
                onClose: (N) => {
                  var te;
                  if (
                    (clearInterval(
                      (te = this.plugin._embedPollInterval) != null
                        ? te
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    N === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText =
                        i("feat_build_complete") || "Embedding build complete"),
                      new R.Notice(i("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let re = (this.plugin._embedStderr || "").slice(0, 200);
                    new R.Notice(
                      i("feat_build_failed") + (re ? ": " + re : ""),
                      8e3
                    );
                  }
                  ((this.plugin._embedStderr = ""),
                    this.display(),
                    this._refreshSnapshots(t));
                },
              }
            )),
            clearInterval(
              (B = this.plugin._embedPollInterval) != null ? B : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (N, te) => {
                    var re;
                    if (((this.plugin._embedPolling = !1), N === 0 && te))
                      try {
                        let L = JSON.parse(te).data;
                        if (L && L.build_state) {
                          let O = L.build_state;
                          ((O.status === "stopping" || O.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (re = this.plugin._embedPollInterval) != null
                                ? re
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            O.current !== void 0 &&
                              O.total !== void 0 &&
                              ((this.plugin._embedProgress.current = O.current),
                              (this.plugin._embedProgress.total = O.total || 1),
                              (this.plugin._embedProgress.key =
                                O.paper_id || "")));
                        }
                      } catch (fe) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        I = !1,
        z;
      switch (
        (C
          ? I
            ? (z = "runtime-mismatch")
            : P === "stopping"
              ? (z = "stopping")
              : S && P === "running"
                ? (z = "building")
                : P === "failed"
                  ? (z = "failed")
                  : P === "stopped"
                    ? (z = "stopped")
                    : E
                      ? (z = "stale")
                      : k
                        ? (z = "corrupted")
                        : b
                          ? (z = "ready")
                          : (z = "idle")
          : (z = "deps-missing"),
        z)
      ) {
        case "building": {
          let A = a.createEl("div", { cls: "paperforge-progress-track" });
          A.style.cssText = "flex:1;";
          let U = g > 0 ? ((h / g) * 100).toFixed(1) : "0",
            X = A.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((X.style.cssText = `width:${U}%; min-width:${h > 0 ? "2px" : "0"};`),
            h < g)
          ) {
            let N = A.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(U)).toFixed(1)}%;`;
          }
          (o.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${h}/${g} papers`,
          }),
            m &&
              o.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${m})`,
              }));
          let B = a.createEl("button");
          (B.setText(i("retrieval_stop")),
            (B.className = "mod-warning"),
            B.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let A = a.createEl("div", { cls: "paperforge-progress-track" });
          A.style.cssText = "flex:1; opacity:0.5;";
          let U = g > 0 ? ((h / g) * 100).toFixed(1) : "0",
            X = A.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((X.style.cssText = `width:${U}%; min-width:${h > 0 ? "2px" : "0"};`),
            h < g)
          ) {
            let N = A.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(U)).toFixed(1)}%;`;
          }
          o.createEl("span", { text: i("retrieval_build_stopping") });
          let B = a.createEl("button");
          (B.setText(i("retrieval_stop")),
            (B.className = "mod-warning"),
            B.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_failed") + (T ? ": " + T : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let A = a.createEl("button");
          (A.setText(i("retrieval_retry")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--resume")));
          let U = a.createEl("button");
          (U.setText(i("retrieval_force_rebuild")),
            (U.style.marginLeft = "6px"),
            U.addEventListener("click", () => D("--force")));
          break;
        }
        case "stopped": {
          o.setText(i("retrieval_build_stopped"));
          let A = a.createEl("button");
          (A.setText(i("retrieval_retry")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--resume")));
          break;
        }
        case "corrupted": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let A = a.createEl("button");
          (A.setText(i("retrieval_force_rebuild")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--force")));
          break;
        }
        case "stale": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let A = a.createEl("button");
          (A.setText(i("retrieval_rebuild_vectors")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--resume")));
          break;
        }
        case "ready": {
          a.createEl("span", {
            text: y + " chunks embedded",
            cls: "setting-item-description",
          });
          let A = a.createEl("button");
          (A.setText(i("retrieval_rebuild_vectors")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--resume")));
          let U = a.createEl("button");
          (U.setText(i("retrieval_force_rebuild")),
            (U.style.marginLeft = "6px"),
            U.addEventListener("click", () => D("--force")));
          break;
        }
        case "deps-missing": {
          o.setText(i("retrieval_build_deps_missing"));
          let A = a.createEl("a");
          (A.setText(i("feat_install_deps")),
            (A.style.cssText = "cursor:pointer; text-decoration:underline;"),
            A.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "runtime-mismatch": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: i("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          let A = a.createEl("a");
          (A.setText(i("runtime_health_sync")),
            (A.style.cssText = "cursor:pointer; text-decoration:underline;"),
            A.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          o.setText(i("retrieval_build_idle"));
          let A = a.createEl("button");
          (A.setText(i("feat_build_btn")),
            (A.className = "mod-cta"),
            A.addEventListener("click", () => D("--resume")));
          break;
        }
      }
    })();
  }
  _getCurrentModelKey() {
    return this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
  }
  _parseEmbedStatus(e) {
    let t = {};
    return (
      e &&
        (e
          .split(
            `
`
          )
          .forEach((r) => {
            let n = r.match(/^\s*([^:]+):\s*(.*)/);
            n && (t[n[1].trim()] = n[2].trim());
          }),
        t.db_exists !== void 0 && (t.db_exists = t.db_exists === "True"),
        t.chunk_count !== void 0 &&
          (t.chunk_count = parseInt(t.chunk_count, 10) || 0)),
      t
    );
  }
  _getPythonDesc(e, t) {
    return t === "stale"
      ? `[!!] ${e} (stale \u2014 path no longer exists, update or clear the override below)`
      : t === "manual"
        ? `${e} (manual)`
        : `${e} (auto-detected)`;
  }
  _refreshPythonInterpDesc(e, t) {
    let r = this._pythonInterpDescEl;
    r &&
      (t === "stale"
        ? (r.textContent = `[!!] ${e} (stale \u2014 path no longer exists, update or clear the override below)`)
        : t === "manual"
          ? (r.textContent = `${e} (manual)`)
          : (r.textContent = `${e} (auto-detected)`));
  }
  _validatePythonOverride() {
    let e = this.plugin.settings.python_path
        ? this.plugin.settings.python_path.trim()
        : "",
      t = this._customPathDescEl;
    if (!e) {
      let r = "\u8BF7\u8F93\u5165\u8DEF\u5F84 / Enter a path first";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new R.Notice(r));
      return;
    }
    if (!$.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new R.Notice(r, 4e3));
      return;
    }
    try {
      $.accessSync(e, $.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new R.Notice(n, 4e3));
      return;
    }
    (0, G.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let c = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new R.Notice(c, 4e3));
        return;
      }
      let s = n.match(/Python (\d+)\.(\d+)/);
      if (!s) {
        let c = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new R.Notice(c, 4e3));
        return;
      }
      let a = parseInt(s[1], 10),
        o = parseInt(s[2], 10);
      if (a < 3 || (a === 3 && o < 11)) {
        let c =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new R.Notice(c, 4e3));
        return;
      }
      (0, G.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (c) => {
        if (c) {
          let p = `\u2713 Python ${a}.${o} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${p}</span>`),
            new R.Notice(p, 4e3));
        } else {
          let p = `\u2713 Python ${a}.${o} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${p}</span>`),
            new R.Notice(p, 4e3));
        }
      });
    });
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _preCheck(e) {
    let t = this.app.vault.adapter.basePath,
      r = this._resolveRuntimeCommand(t);
    if (!r) {
      e();
      return;
    }
    (0, G.execFile)(
      r.path,
      [...r.args, "--version"],
      { timeout: 8e3 },
      (n, s) => {
        let a = [];
        a.push({
          label: "environment",
          ok: !n,
          detail: n ? i("check_python_fail") : s.trim(),
        });
        let o = !1,
          c = process.env.HOME || process.env.USERPROFILE || Vr.homedir() || "";
        if (process.platform === "darwin")
          o = [
            "/Applications/Zotero.app",
            J.join(c, "Applications", "Zotero.app"),
          ].some((m) => {
            try {
              return $.existsSync(m);
            } catch (v) {
              return !1;
            }
          });
        else if (process.platform === "win32") {
          let g = process.env.ProgramFiles || "",
            m = process.env.LOCALAPPDATA || "";
          o = [
            J.join(g, "Zotero"),
            J.join(g, "(x86)", "Zotero"),
            J.join(m, "Programs", "Zotero"),
            J.join(m, "Zotero"),
            J.join(c, "AppData", "Local", "Programs", "Zotero"),
          ]
            .filter(Boolean)
            .some((x) => {
              try {
                return $.existsSync(x);
              } catch (w) {
                return !1;
              }
            });
        } else
          o = [
            J.join(c, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ].some((m) => {
            try {
              return $.existsSync(m);
            } catch (v) {
              return !1;
            }
          });
        let p = this.plugin.settings.zotero_data_dir;
        if (!o && p)
          try {
            o = $.existsSync(p);
          } catch (g) {}
        a.push({
          label: "Zotero",
          ok: o,
          detail: o ? i("check_zotero_ok") : i("check_zotero_fail"),
        });
        let _ = !1,
          f = process.env.APPDATA || "";
        (process.platform === "win32" &&
          f &&
          (_ = tt(J.join(f, "Zotero", "Zotero", "Profiles"))),
          !_ &&
            process.platform === "darwin" &&
            c &&
            (_ = tt(
              J.join(c, "Library", "Application Support", "Zotero", "Profiles")
            )),
          !_ &&
            process.platform !== "win32" &&
            process.platform !== "darwin" &&
            c &&
            (_ = tt(J.join(c, ".zotero", "zotero", "Profiles"))),
          !_ && p && String(p).trim() && (_ = Ct(p.trim())),
          !_ && c && (_ = Ct(J.join(c, "Zotero"))),
          a.push({
            label: "Better BibTeX",
            ok: _,
            detail: _ ? i("check_bbt_ok") : i("check_bbt_fail"),
          }));
        let u = { true: "\u2713", false: "\u2717" };
        if (this._checkEl) {
          this._checkEl.setText(
            a.map((m) => `${u[String(m.ok)]} ${m.label}: ${m.detail}`).join(`
`)
          );
          let g = a.some((m) => !m.ok);
          this._checkEl.className = `paperforge-message msg-${g ? "error" : "ok"}`;
        }
        let h = a.filter((g) => !g.ok);
        (h.length > 0 &&
          new R.Notice(
            `[!!] \u672A\u901A\u8FC7: ${h.map((g) => g.label).join(", ")}`,
            6e3
          ),
          e());
      }
    );
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = jr.default.versions || [];
    for (let s of t) {
      let a = e.createEl("div", { cls: "paperforge-release-card" }),
        o = a.createEl("div", { cls: "paperforge-release-header" });
      if (
        (o.createEl("strong", { text: `v${s.version} \u2014 ${s.title}` }),
        o.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${s.date})`,
        }),
        s.breaking_or_migration && s.breaking_or_migration.length > 0)
      ) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let p of s.breaking_or_migration)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.new_features && s.new_features.length > 0) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let p of s.new_features)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.fixes && s.fixes.length > 0) {
        let c = a.createEl("div", { cls: "paperforge-release-section" });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let p of s.fixes)
          c.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (s.recommended_actions && s.recommended_actions.length > 0) {
        let c = a.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        c.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let p of s.recommended_actions)
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
    ((this._capabilityState = ar(e != null ? e : {}, Oe)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var c, p, _, f;
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
        action: { primary: je(e) },
        notices: (_ = r == null ? void 0 : r.notices) != null ? _ : [],
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
    let s = this.app.vault.adapter.basePath,
      a = this._resolveRuntimeCommand(s);
    if (!a) {
      if ((this._probing.delete(e), e === "installation")) {
        let u = {
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
          action: { primary: nr() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !1,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, u);
      } else this._updateCapabilityEnvelope(e, Le(e));
      return;
    }
    let o = [...a.args, "-m", "paperforge", "--vault", s, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      o.push("--last-operation-exit-code", String(t)),
      e === "installation" &&
        o.push("--expected-version", this.plugin.manifest.version),
      (0, G.execFile)(a.path, o, { cwd: s, timeout: 15e3 }, (u, h, g) => {
        if ((this._probing.delete(e), u)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, u.message),
            this._updateCapabilityEnvelope(e, Le(e)));
          return;
        }
        try {
          let m = JSON.parse(h);
          if (et(m, e)) {
            let v = m;
            this._updateCapabilityEnvelope(e, v);
          } else
            (console.warn(
              `[PaperForge] Probe ${e}: invalid envelope schema`,
              h == null ? void 0 : h.slice(0, 200)
            ),
              this._updateCapabilityEnvelope(e, Le(e)));
        } catch (m) {
          (console.warn(
            `[PaperForge] Probe ${e}: unparseable JSON`,
            h == null ? void 0 : h.slice(0, 200)
          ),
            this._updateCapabilityEnvelope(e, Le(e)));
        }
      }));
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    (Pr(r, t) && this._lastKnownState.set(e, Cr(t)),
      e === "installation" &&
        t.user_state === "ready" &&
        (this._setupReinstallRequested = !1),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        new R.Notice(i("cc_notice_refreshed"), 3e3),
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
      n = i(r);
    if (n !== r) return n.replace("{module}", t);
    let a = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      o = i(a);
    return o === a ? null : o.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      s = this._sevClass(n.severity, n.activity_state),
      a = Me._REAL_PROBE.has(t),
      o = Me._NAVIGABLE.has(t),
      c = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${i("cc_module_" + t)} \u2014 ${i(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = c.createEl("div", { cls: "pf-cc-card-header" }),
      _ = p.createEl("div", { cls: "pf-cc-card-name-area" });
    if (o) {
      let k =
          t === "installation"
            ? i("module_detail_open_installation")
            : t === "library"
              ? i("module_detail_open_library")
              : t === "ocr"
                ? i("module_detail_open_ocr")
                : t === "memory"
                  ? i("module_detail_open_memory")
                  : t === "help"
                    ? i("module_detail_open_help")
                    : i("md_select_installation"),
        S = _.createEl("button", {
          cls: "pf-open-module-btn",
          text: i("cc_module_" + t),
          attr: { "data-module": t, "aria-label": k },
        });
      (S.addEventListener("click", () => this._handleCardNavigation(t)),
        S.addEventListener("keydown", (E) => {
          (E.key === "Enter" || E.key === " ") &&
            (E.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      _.createEl("div", { cls: "pf-cc-card-name", text: i("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
      text: i(this._ccBadgeKey(n, t)),
    });
    let f;
    if (!a)
      f = i("cc_reason_placeholder").replace("{module}", i("cc_module_" + t));
    else {
      let k = this._localizeReason(n.reason.code, t);
      f = k != null ? k : n.reason.text;
    }
    if (
      (c.createEl("div", { cls: "pf-cc-card-reason", text: f }),
      n.activity_state === "running" && n.activity_label)
    ) {
      let k = c.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (k.createEl("span", { text: n.activity_label }),
        n.activity_progress && n.activity_progress.total > 0)
      ) {
        let S = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          C = k
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
        C.style.width = S + "%";
      }
    }
    let u = c.createEl("div", { cls: "pf-cc-card-footer" });
    if (a && n.action.primary && !sr(n)) {
      let k = ir(n),
        E =
          k.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      u.createEl("button", {
        cls: E,
        text: k.label,
        attr: { "aria-label": k.label },
      }).addEventListener("click", () => {
        k.kind === "setup"
          ? this._startSetupJourney(1)
          : this._dispatchModuleAction(t, n);
      });
    }
    let h = c.createEl("details", { cls: "pf-cc-card-diagnostic" });
    h.createEl("summary", { text: i("cc_diagnostic_toggle") });
    let g = h.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      m = i("cc_state_" + n.capability_state) || n.capability_state,
      v = i("cc_severity_" + n.severity) || n.severity,
      x = i("cc_activity_" + n.activity_state) || n.activity_state,
      w;
    try {
      w = new Date(n.updated_at).toLocaleString();
    } catch (k) {
      w = n.updated_at;
    }
    (g.createEl("div", { text: `${i("cc_diag_module")}: ${n.module}` }),
      g.createEl("div", { text: `${i("cc_diag_state")}: ${m}` }),
      g.createEl("div", { text: `${i("cc_diag_severity")}: ${v}` }),
      g.createEl("div", { text: `${i("cc_diag_activity")}: ${x}` }));
    let y = g.createEl("div");
    y.appendText(i("cc_diag_reason") + ": " + f + " ");
    let b = y.createEl("code", { text: n.reason.code });
    (g.createEl("div", {
      text: `${i("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      g.createEl("div", { text: `${i("cc_diag_updated")}: ${w}` }));
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
    var E, C, P, T;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (E = this._capabilityState) != null ? E : {};
    (t.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: i("cc_eyebrow") || "control center",
    }),
      t.createEl("h1", {
        cls: "pf-cc-title",
        text: i("cc_title") || "Your literature pipeline",
      }),
      t.createEl("p", {
        cls: "pf-cc-lede",
        text:
          i("cc_lede") ||
          "See what is working and what needs attention across your pipeline.",
      }));
    let n = (C = r.installation) != null ? C : ie("installation"),
      s = (P = r.library) != null ? P : ie("library"),
      a = n.user_state === "ready",
      o = s.user_state === "ready",
      c = a && o,
      p = [n, s].some((D) => D.user_state === "checking"),
      _ = Object.values(r).filter(
        (D) =>
          D.user_state &&
          D.user_state !== "ready" &&
          D.user_state !== "not_enabled"
      ).length,
      f = t.createEl("div", { cls: "pf-cc-summary" }),
      u = c ? "ready" : p ? "checking" : "attention",
      h = c
        ? i("cc_badge_ready") || "Ready"
        : p
          ? i("cc_badge_checking") || "Checking"
          : i("cc_badge_attention") || "Needs attention";
    f.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${u}`,
      text: h,
    });
    let g = f.createDiv({ cls: "pf-cc-summary-copy" }),
      m = c
        ? i("cc_summary_ready")
        : p
          ? i("cc_summary_checking")
          : this.plugin.settings._setup_complete === !1
            ? i("cc_summary_incomplete")
            : i("cc_summary_attention"),
      v = c
        ? i("cc_summary_ready_body")
        : p
          ? i("cc_summary_checking_body")
          : this.plugin.settings._setup_complete === !1
            ? i("cc_summary_incomplete_body")
            : i("cc_summary_attention_body");
    (g.createEl("strong", { text: m }),
      g.createEl("span", { cls: "caption", text: v }));
    let x = f.createDiv({ cls: "pf-cc-summary-meta" }),
      w = x.createEl("span");
    (w.createEl("strong", { text: String(_) }),
      w.appendText(" " + (i("cc_needs_attention") || "item needs attention")));
    let y = Object.values(r)
      .map((D) => D.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    (x.createEl("span", {
      text: y
        ? (i("cc_last_checked") || "Checked just now: ") +
          new Date(y).toLocaleString()
        : i("cc_checked_pending") || "Not checked yet",
    }),
      x
        .createEl("button", {
          cls: "pf-cc-summary-refresh",
          text: i("cc_refresh_btn") || "Refresh status",
        })
        .addEventListener("click", () => this._refreshAllModules()));
    let k = t.createDiv({ cls: "pf-cc-section-head" });
    (k.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: i("cc_modules_header") || "modules",
    }),
      k.createEl("span", {
        cls: "caption",
        text:
          i("cc_optional_note") ||
          "Optional modules do not affect core readiness.",
      }));
    let S = t.createDiv({ cls: "pf-cc-module-list" });
    for (let [D, I] of this._getOverviewModules().entries()) {
      let z =
        I.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (T = r[I.id]) != null
            ? T
            : ie(I.id);
      this._renderOverviewCard(S, I.id, I.label, z, D + 1);
    }
  }
  _getAgentPlaceholderEnvelope() {
    var s;
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
      r = J.join(
        this._getVaultBasePath(),
        (s = t[e]) != null ? s : t.opencode,
        "paperforge",
        "SKILL.md"
      ),
      n = $.existsSync(r);
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
  _renderOverviewCard(e, t, r, n, s) {
    var c, p;
    let a = e.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn",
      attr: {
        "data-module": t,
        "aria-label": r + " \u2014 " + this._getUserStateLabel(n.user_state),
        role: "button",
        tabindex: "0",
      },
    });
    ((a.style.cursor = "pointer"),
      a.createEl("span", {
        cls: "pf-cc-num",
        text: String(s).padStart(2, "0"),
      }),
      a.createEl("span", { cls: "pf-cc-card-name", text: r }),
      we(a, n.user_state, this._getUserStateLabel(n.user_state)),
      a.createEl("span", {
        cls: "pf-cc-card-sentence",
        text: this._getModuleConsequence(t, n),
      }));
    let o =
      n.user_state === "ready" &&
      (p = (c = n.action) == null ? void 0 : c.primary) != null &&
      p.scope_count &&
      n.action.primary.scope_count > 1
        ? (i("cc_metric_papers") || "Papers: ") + n.action.primary.scope_count
        : n.updated_at && n.updated_at !== new Date(0).toISOString()
          ? (i("cc_last_checked") || "") +
            new Date(n.updated_at).toLocaleString()
          : "";
    (a.createEl("span", { cls: "pf-cc-card-metric", text: o }),
      a.createEl("span", { cls: "pf-cc-card-arrow", text: "\u2192" }),
      a.addEventListener("click", () => this._handleCardNavigation(t)));
  }
  _getUserStateLabel(e) {
    return i("cc_badge_" + e);
  }
  _getModuleConsequence(e, t) {
    var p, _, f;
    let r =
        (p = t.user_state) != null
          ? p
          : t.capability_state === "ready"
            ? "ready"
            : "action_required",
      n = "cc_consequence_" + e + "_" + r,
      s = i(n);
    if (s && s !== n) return s;
    let a = this._localizeReason(
      (f = (_ = t.reason) == null ? void 0 : _.code) != null ? f : "",
      this._getUserModuleName(e)
    );
    if (a) return a;
    let o = "cc_consequence_" + r,
      c = i(o);
    return c !== o ? c : i("cc_consequence_default");
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Oe) {
      let r = this._capabilityState[t];
      r && ht(r) && ((this._capabilityState[t] = gt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    this._refreshAllReadModels();
  }
  _refreshAllReadModels(e) {
    var r;
    vr();
    let t = (r = this.app.vault.adapter.basePath) != null ? r : "";
    if (!t) {
      this._probing.clear();
      return;
    }
    this._probing.clear();
    for (let n of Oe) this._probing.add(n);
    br(t, this.plugin.settings)
      .then((n) => {
        var s;
        this._probing.clear();
        for (let [a, o] of Object.entries((s = n.modules) != null ? s : {}))
          et(o, a) && this._updateCapabilityEnvelope(a, o);
        e != null && e !== 0 && this._probeModule("library", e);
      })
      .catch(() => {
        (this._probing.clear(), this.display());
      });
  }
  _buildAndCopyDiagnostic() {
    var s, a, o;
    let e =
        (a = (s = this.plugin.manifest) == null ? void 0 : s.version) != null
          ? a
          : "unknown",
      t = Rr(
        (o = this._capabilityState) != null ? o : {},
        this._lastKnownState
      ),
      n = kr({ pluginVersion: e, modules: t });
    Sr(n, () => {
      new R.Notice(i("support_diagnostic_copied"), 3e3);
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
    (t.createEl("h2", { text: i("setup_welcome") }),
      t.createEl("p", { text: i("setup_desc"), cls: "pf-setup-desc" }));
    let r = [
        i("setup_stage_1"),
        i("setup_stage_2"),
        i("setup_stage_3"),
        i("setup_stage_4"),
      ],
      n = t.createDiv({
        cls: "pf-setup-progress",
        attr: { "aria-label": i("setup_progress") },
      });
    r.forEach((a, o) => {
      n.createEl("span", {
        cls:
          "pf-setup-step" +
          (o + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (o + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(o + 1) + ". " + a,
        attr: { "aria-current": o + 1 === this._setupStage ? "step" : "false" },
      });
    });
    let s = t.createDiv({ cls: "pf-setup-body" });
    this._setupStage === 1
      ? this._renderSetupStageFoundation(s)
      : this._setupStage === 2
        ? this._renderSetupStageLibrary(s)
        : this._setupStage === 3
          ? this._renderSetupStageOptionals(s)
          : this._renderSetupStageReview(s);
  }
  _renderSetupStageFoundation(e) {
    var o, c;
    let t =
      (c = (o = this._capabilityState) == null ? void 0 : o.installation) !=
      null
        ? c
        : ie("installation");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("installation") &&
      (this._attemptedProbes.add("installation"),
      this._probeModule("installation")),
      e.createEl("h3", { text: i("setup_foundation_title") }),
      e.createEl("p", { text: i("setup_foundation_desc") }));
    let n = e.createDiv({ cls: "pf-setup-field" });
    (n.createEl("label", { text: i("setup_foundation_python") }),
      n.createEl("span", {
        cls: "caption",
        text: i("setup_foundation_python_hint"),
      }));
    let s = n.createEl("input", {
      cls: "pf-setup-input",
      attr: { type: "text", placeholder: "python" },
    });
    ((s.value = this.plugin.settings.python_path || ""),
      s.addEventListener("input", () => {
        ((this.plugin.settings.python_path = s.value.trim()),
          this._debouncedSave());
      }),
      we(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("setup_ready")
            : this._getModuleConsequence("installation", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: i("setup_installing"),
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
                text: i("setup_reinstall_notice"),
              }),
              V(e, {
                label: i("foundation_reinstall_btn"),
                onClick: () => this._installFoundation(!0),
              }))
            : (t.user_state !== "ready" || this._setupOperation === "failed") &&
              V(e, {
                label: i("setup_foundation_install_btn"),
                onClick: () => this._installFoundation(!1),
              })));
    let a = e.createDiv({ cls: "pf-setup-nav" });
    V(a, {
      label: i("setup_nav_continue"),
      disabled: t.user_state !== "ready",
      onClick: () => {
        ((this._setupFeedback = null), (this._setupStage = 2), this.display());
      },
    });
  }
  _renderSetupStageLibrary(e) {
    var k, S;
    let t =
      (S = (k = this._capabilityState) == null ? void 0 : k.library) != null
        ? S
        : ie("library");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("library") &&
      (this._attemptedProbes.add("library"), this._probeModule("library")),
      e.createEl("h3", { text: i("setup_library_title") }),
      e.createEl("p", { text: i("setup_library_desc") }),
      we(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? i("setup_library_ready")
            : this._getModuleConsequence("library", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: i("setup_library_configuring"),
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
      text: i("setup_library_config_desc"),
    });
    let s = (E, C, P, T) => {
      let D = E.createDiv({ cls: "pf-setup-field" });
      (D.createEl("label", { text: C }),
        T && D.createEl("span", { cls: "caption", text: T }));
      let I = D.createEl("input", {
        cls: "pf-setup-input",
        attr: { type: "text" },
      });
      ((I.value = this.plugin.settings[P] || ""),
        I.addEventListener("input", () => {
          ((this.plugin.settings[P] = I.value.trim()), this._debouncedSave());
        }));
    };
    (s(
      n,
      i("field_zotero_data"),
      "zotero_data_dir",
      i("setup_library_zotero_hint")
    ),
      n.createEl("h4", { text: i("setup_library_folder_heading") }));
    let a = n.createDiv({ cls: "pf-setup-folder-grid" });
    (s(a, i("dir_system"), "system_dir"),
      s(a, i("dir_resources"), "resources_dir"),
      s(a, i("dir_notes"), "literature_dir"),
      s(a, i("dir_base"), "base_dir"));
    let o = n.createEl("button", {
      cls: "pf-setup-verify",
      text: i("setup_library_verify"),
      attr: { type: "button" },
    });
    ((o.disabled = this._setupOperation === "running"),
      o.addEventListener("click", () => this._applyLibraryConfiguration()));
    let c = e.createDiv({ cls: "pf-setup-import" });
    c.createEl("h4", { text: i("setup_bbt_title") || "BBT JSON Export" });
    let p = this.app.vault.adapter.basePath,
      _ = (Pe(), Yt(Br)).resolveVaultPaths(p);
    c.createEl("p", {
      cls: "pf-setup-form-intro",
      text:
        i("setup_bbt_desc") ||
        "Export your Zotero library as Better BibTeX JSON into the folder below. Enable 'Keep updated' for automatic re-exports.",
    });
    let f = c.createDiv({ cls: "pf-setup-path-row" });
    (f.createEl("span", {
      cls: "pf-setup-path-label",
      text: i("setup_bbt_path") || "Exports folder:",
    }),
      f.createEl("code", { cls: "pf-setup-path-value", text: _.exportsDir }),
      f
        .createEl("button", {
          cls: "pf-btn pf-btn-secondary",
          text: i("setup_bbt_copy") || "Copy",
        })
        .addEventListener("click", () => {
          (navigator.clipboard.writeText(_.exportsDir),
            new R.Notice(i("setup_bbt_copied") || "Path copied"));
        }));
    let h = c.createEl("details", { cls: "pf-setup-guide" });
    h.createEl("summary", {
      cls: "pf-setup-guide-summary",
      text: i("setup_bbt_guide") || "How to export from Zotero \u2192",
    });
    let g = h.createDiv({ cls: "pf-setup-guide-body" }),
      m =
        "https://raw.githubusercontent.com/LLLin000/PaperForge/master/docs/help/images",
      v = [
        {
          img: "bbt-plugin-installed.jpg",
          title: i("setup_bbt_step1") || "1. Install Better BibTeX",
          desc:
            i("setup_bbt_step1_desc") ||
            "In Zotero, go to Tools \u2192 Add-ons, search for Better BibTeX and install it. If you cannot find it, download from: https://github.com/retorquere/zotero-better-bibtex/releases/tag/v9.0.50",
        },
        {
          img: "bbt-export-dialog.jpg",
          title: i("setup_bbt_step2") || "2. Export with auto-update",
          desc:
            i("setup_bbt_step2_desc") ||
            "Right-click your library or collection \u2192 Export Library\u2026 \u2192 choose 'Better BibTeX JSON' format. Check 'Keep updated'.",
        },
        {
          img: "bbt-save-dialog.jpg",
          title: i("setup_bbt_step3") || "3. Save to exports folder",
          desc:
            i("setup_bbt_step3_desc") ||
            "Point the export destination to the folder above. Once saved, click 'Detect' below.",
        },
      ];
    for (let E of v) {
      let C = g.createDiv({ cls: "pf-setup-guide-step" });
      (C.createEl("strong", { text: E.title }),
        C.createEl("p", { text: E.desc }),
        C.createEl("img", {
          attr: {
            src: m + "/" + E.img,
            alt: E.title,
            loading: "lazy",
            onerror: "this.style.display='none'",
          },
        }).addClass("pf-setup-guide-img"));
    }
    let x = c.createDiv({ cls: "pf-setup-detect-row" }),
      w = x.createEl("span", { cls: "pf-setup-detect-status" }),
      y = e.createDiv({ cls: "pf-setup-nav" }),
      b = () => {
        try {
          $.existsSync(_.exportsDir) ||
            $.mkdirSync(_.exportsDir, { recursive: !0 });
          let E = $.readdirSync(_.exportsDir).filter((P) =>
            P.endsWith(".json")
          );
          E.length === 0
            ? w.setText(i("setup_bbt_no_files") || "No JSON files found.")
            : w.setText(
                "\u2713 " + (i("setup_bbt_found") || "Found: ") + E.join(", ")
              );
          let C = y.querySelector(".pf-action-btn:last-child");
          if (C) {
            let P =
              E.length === 0 ||
              t.user_state !== "ready" ||
              this._setupOperation === "running";
            ((C.disabled = P),
              C.classList.toggle("pf-action-btn--disabled", P));
          }
        } catch (E) {}
      };
    (x
      .createEl("button", {
        cls: "pf-btn pf-btn-primary",
        text: i("setup_bbt_detect") || "Detect",
      })
      .addEventListener("click", b),
      V(y, {
        label: i("setup_nav_back"),
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 1),
            this.display());
        },
      }),
      V(y, {
        label: i("setup_nav_continue"),
        disabled: !0,
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 3),
            this.display());
        },
      }),
      b());
  }
  async _migrateLegacyCredentials(e) {
    var c, p;
    let t = this._getVaultBasePath(),
      r = this._resolveRuntimeCommand(t);
    if (!r || !t) {
      new R.Notice("Runtime not ready \u2014 cannot migrate credentials");
      return;
    }
    let { migrateLegacySecret: n, isAllowlistedCommand: s } =
        await Promise.resolve().then(() => (xt(), cr)),
      a = {
        spawn: (_, f, u) => (0, G.spawn)(_, f, u),
        pythonPath: r.path,
        pythonArgs: r.args,
        vaultPath: t,
        env: Y(),
      };
    e.disabled = !0;
    let o = [];
    for (let _ of ["ocr", "embedding"]) {
      let f = await n(_, this.app.secretStorage, a, {
        baseUrl: (c = this.plugin.settings.vector_db_api_base) != null ? c : "",
        model: (p = this.plugin.settings.vector_db_api_model) != null ? p : "",
      });
      f.migrated.length && o.push(`${_}: migrated`);
      for (let u of f.warnings) o.push(u);
    }
    ((e.disabled = !1),
      o.length === 0
        ? new R.Notice("No legacy credentials found in SecretStorage")
        : o.forEach((_) => new R.Notice(_, 6e3)),
      this._refreshVectorDbCredentialStatus(),
      this._refreshAllReadModels());
  }
  _refreshVectorDbCredentialStatus() {
    let e = this._getVaultBasePath();
    e &&
      hr(e, this.plugin.settings)
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
      : new Promise((s) => {
          let a = (0, G.spawn)(
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
                "--json",
              ],
              {
                cwd: r,
                windowsHide: !0,
                stdio: ["pipe", "pipe", "pipe"],
                env: Y(),
              }
            ),
            o = "";
          (a.stdout.on("data", (c) => (o += String(c))),
            a.on("error", () => s(!1)),
            a.on("close", (c) => {
              try {
                let p = JSON.parse(o);
                s(c === 0 && (p == null ? void 0 : p.ok) === !0);
              } catch (p) {
                s(!1);
              }
            }),
            a.stdin.write(t),
            a.stdin.end());
        });
  }
  _renderSetupStageOptionals(e) {
    var n;
    (e.createEl("h3", { text: i("setup_optionals_title") }),
      e.createEl("p", { text: i("setup_optionals_desc") }));
    let t = [
      { id: "ocr", label: i("cc_module_ocr"), desc: i("setup_opt_ocr_desc") },
      {
        id: "memory",
        label: i("cc_module_memory"),
        desc: i("setup_opt_memory_desc"),
      },
      {
        id: "agent",
        label: i("cc_module_agent"),
        desc: i("setup_opt_agent_desc"),
      },
    ];
    for (let s of t) {
      let a = e.createDiv({ cls: "pf-setup-optional" }),
        o = a.createEl("input", {
          attr: { type: "checkbox", id: "pf-setup-opt-" + s.id },
        });
      ((o.checked = this._setupOptionals[s.id]),
        o.addEventListener("change", () => {
          ((this._setupOptionals[s.id] = o.checked), this.display());
        }));
      let c =
          s.id === "ocr"
            ? !!this.plugin.settings._paddleocr_configured
            : s.id === "memory"
              ? !!this.plugin.settings._vector_db_configured
              : !0,
        p = a.createDiv({ cls: "pf-setup-optional-copy" });
      (p.createEl("label", {
        attr: { for: "pf-setup-opt-" + s.id },
        text: s.label,
        cls: "pf-setup-optional-label",
      }),
        p.createEl("div", { text: s.desc, cls: "pf-setup-optional-desc" }));
      let _ = p.createEl("span", {
        cls: "pf-setup-optional-state",
        text: c ? i("config_configured") : i("config_not_configured"),
      });
      if (!o.checked) continue;
      let f = a.createDiv({ cls: "pf-setup-optional-config" });
      if (s.id === "ocr") {
        (f.createEl("label", { text: i("field_paddleocr") }),
          f.createEl("p", { cls: "caption", text: i("ocr_privacy_warning") }));
        let u = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._paddleocr_configured
              ? "\u2022\u2022\u2022\u2022"
              : i("field_paddleocr"),
          },
        });
        f.createEl("button", {
          cls: "pf-setup-verify",
          text: i("config_save"),
          attr: { type: "button" },
        }).addEventListener("click", () => {
          this._storeSetupSecret("paddleocr-api-key", u.value).then((g) => {
            (_.setText(
              g ? i("setup_optional_saved") : i("setup_optional_save_failed")
            ),
              g && (u.value = ""));
          });
        });
      } else if (s.id === "memory") {
        (f.createEl("label", { text: i("feat_openai_key") }),
          f.createEl("p", { cls: "caption", text: i("feat_openai_key_desc") }));
        let u = f.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._vector_db_configured
              ? "\u2022\u2022\u2022\u2022"
              : "sk-...",
          },
        });
        f.createEl("label", { text: i("feat_api_model") });
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
          f.createEl("label", { text: i("feat_api_base_url") }));
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
              text: i("config_save"),
              attr: { type: "button" },
            })
            .addEventListener("click", () => {
              this._storeSetupSecret("vector-db-api-key", u.value).then((v) => {
                (_.setText(
                  v
                    ? i("setup_optional_saved")
                    : i("setup_optional_save_failed")
                ),
                  v && (u.value = ""));
              });
            }));
      } else {
        (f.createEl("label", { text: i("feat_agent_platform") }),
          f.createEl("p", {
            cls: "caption",
            text: i("feat_agent_platform_desc"),
          }));
        let u = f.createEl("select"),
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
          let v = u.createEl("option", {
            text: (n = h[m]) != null ? n : m,
            attr: { value: m },
          });
          v.selected = m === this.plugin.settings.agent_platform;
        }
        u.addEventListener("change", () => {
          ((this.plugin.settings.agent_platform = u.value),
            Ee(
              this._getVaultBasePath(),
              "agent_platform",
              u.value,
              this.plugin.settings
            ).catch(
              (m) =>
                new R.Notice(
                  `PaperForge: config set agent_platform failed: ${String(m)}`
                )
            ),
            this.plugin.saveSettings(),
            _.setText(i("setup_optional_saved")));
        });
      }
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (V(r, {
      label: i("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      V(r, {
        label: i("setup_nav_continue"),
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
    var p, _;
    e.createEl("h3", { text: i("setup_review_title") });
    let t = (p = this._capabilityState) == null ? void 0 : p.installation,
      r = (_ = this._capabilityState) == null ? void 0 : _.library,
      n = (t == null ? void 0 : t.user_state) === "ready",
      s = (r == null ? void 0 : r.user_state) === "ready",
      a =
        (t == null ? void 0 : t.user_state) === "checking" ||
        (r == null ? void 0 : r.user_state) === "checking";
    (e.createEl("p", {
      text: n
        ? i("setup_ready")
        : a
          ? i("setup_review_checking")
          : i("cc_consequence_setup_required"),
      cls: n ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: s
          ? i("setup_library_ready")
          : a
            ? i("setup_review_checking")
            : i("cc_consequence_setup_required"),
        cls: s ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let o = Object.entries(this._setupOptionals)
      .filter(([, f]) => f)
      .map(([f]) => this._getUserModuleName(f));
    e.createEl("p", {
      text:
        o.length > 0
          ? i("setup_review_selected") + o.join(", ")
          : i("setup_no_optionals"),
    });
    let c = e.createDiv({ cls: "pf-setup-nav" });
    (V(c, {
      label: i("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      (!n || !s) &&
        V(c, {
          label: i("setup_review_recheck"),
          disabled: a,
          onClick: () => this._refreshSetupReadiness(),
        }),
      V(c, {
        label: i("setup_nav_complete"),
        disabled: !n || !s,
        onClick: () => this._completeSetup(),
      }),
      (!n || !s) &&
        e.createEl("p", {
          text: a ? i("setup_review_checking") : i("setup_incomplete_warn"),
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
};
((Me._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
])),
  (Me._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "help",
  ])));
var lt = Me;
var qr = require("child_process");
var zn = `PAPERFORGE_STOP
`,
  Kr = 500;
function Vn(d, l) {
  var t, r, n;
  if (d === "run") return ["ocr", "run", ...((t = l.keys) != null ? t : [])];
  if (d === "redo") return ["ocr", "redo", ...((r = l.keys) != null ? r : [])];
  let e = (n = l.keys) != null ? n : [];
  return e.length > 0 ? ["ocr", "rebuild", ...e] : ["ocr", "rebuild", "--all"];
}
var ct = class {
  constructor(l) {
    this._opts = l;
    this._child = null;
    this._stopRequested = !1;
    this._parser = new ke();
    this._stderr = "";
  }
  get isRunning() {
    return this._child !== null;
  }
  stop() {
    var l;
    if (this._child) {
      this._stopRequested = !0;
      try {
        (l = this._child.stdin) == null || l.write(zn);
      } catch (e) {}
    }
  }
  start(l, e = {}) {
    if (this.isRunning)
      return Promise.reject(new Error("OCR is already running"));
    let t = this._opts.resolveCommand();
    return t != null && t.path
      ? this._opts.needsCredential(l)
        ? this._opts
            .resolveEnv()
            .then((r) => this._spawn(l, e, t, r))
            .catch((r) =>
              Promise.reject(
                new Error(
                  `OCR credential unavailable: ${r instanceof Error ? r.message : String(r)}`
                )
              )
            )
        : this._spawn(l, e, t, {})
      : Promise.reject(new Error("No Python runtime available"));
  }
  _spawn(l, e, t, r) {
    var h, g, m, v, x, w;
    let n = (h = e.callbacks) != null ? h : {};
    ((this._stopRequested = !1),
      (this._parser = new ke()),
      (this._stderr = ""));
    let a = ((g = this._opts.spawnFn) != null ? g : qr.spawn)(
      t.path,
      [...t.args, "-m", "paperforge", ...Vn(l, e)],
      {
        cwd: this._opts.vaultPath,
        shell: !1,
        windowsHide: !0,
        env: { ...process.env, ...r },
        stdio: ["pipe", "pipe", "pipe"],
      }
    );
    this._child = a;
    let o = [],
      c = [],
      p = [],
      _ = (() => {
        let y = !1;
        return (b, k, S, E) => {
          var C;
          y ||
            ((y = !0),
            (this._child = null),
            this._stderr.trim() &&
              ((C = n.onNotice) == null ||
                C.call(n, this._stderr.trim().slice(-Kr))),
            f({
              ok: S,
              exitCode: b,
              stopped: k,
              successKeys: o,
              failedKeys: c,
              skippedKeys: p,
              protocolFailure: E,
            }));
        };
      })(),
      f,
      u = new Promise((y) => {
        f = y;
      });
    return (
      (m = a.stdout) == null || m.setEncoding("utf-8"),
      (v = a.stdout) == null ||
        v.on("data", (y) => {
          let b = this._parser.feed(y);
          for (let k of b) this._handleEvent(k, n, o, c, p);
        }),
      (x = a.stderr) == null || x.setEncoding("utf-8"),
      (w = a.stderr) == null ||
        w.on("data", (y) => {
          this._stderr = (this._stderr + y).slice(-Kr);
        }),
      a.on("error", (y) => {
        var b;
        ((b = n.onNotice) == null ||
          b.call(n, `OCR process error: ${y.message}`),
          _(null, this._stopRequested, !1));
      }),
      a.on("close", (y) => {
        var C;
        this._parser.finishEOF();
        let b = this._parser.protocolFailure;
        b &&
          ((C = n.onNotice) == null ||
            C.call(n, `OCR stream protocol failure: ${b}`));
        let k = this._stopRequested || y === 130,
          S = c.length > 0 || p.length > 0 || !!b;
        _(y, k, !k && !S && (y === 0 || y === null), b);
      }),
      u
    );
  }
  _handleEvent(l, e, t, r, n) {
    var s, a, o, c, p, _, f, u, h, g;
    switch (l.event) {
      case "progress":
        (c = e.onProgress) == null ||
          c.call(
            e,
            (s = l.current) != null ? s : 0,
            (a = l.total) != null ? a : 1,
            (o = l.item_id) != null ? o : ""
          );
        break;
      case "item_result":
        (l.status === "ok"
          ? t.push((p = l.item_id) != null ? p : "")
          : l.status === "failed"
            ? r.push((_ = l.item_id) != null ? _ : "")
            : l.status === "skipped" &&
              n.push({
                key: (f = l.item_id) != null ? f : "",
                reason: "backend_skip",
              }),
          (g = e.onResult) == null ||
            g.call(
              e,
              (u = l.item_id) != null ? u : "",
              (h = l.status) != null ? h : ""
            ));
        break;
      default:
        break;
    }
  }
};
var M = require("obsidian"),
  oe = Z(require("fs")),
  He = Z(require("path")),
  be = require("child_process");
Pe();
var Ze = Z(require("path"));
function Ur(d) {
  if (!d) return null;
  let l = Ze.dirname(d);
  for (;;) {
    let e = Ze.basename(l);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = Ze.dirname(l);
    if (r === l) break;
    l = r;
  }
  return null;
}
var j = Z(require("fs")),
  me = Z(require("path"));
Pe();
function We(d) {
  return ae(d).ocrDir;
}
function Wr(d, l) {
  let e = me.join(We(d), l, "versions", "manifest.json");
  try {
    if (!j.existsSync(e)) return null;
    let t = j.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let n = r,
        s = n.versions,
        a = n.current;
      if (Array.isArray(s) && a && typeof a == "object" && "label" in a)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function jn(d) {
  let l = We(d);
  try {
    return j.existsSync(l)
      ? j
          .readdirSync(l, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function Je(d, l) {
  let e = Wr(d, l);
  return e ? { versions: e.versions, currentLabel: e.current.label } : null;
}
function Ht(d) {
  let l = jn(d),
    e = [];
  for (let t of l) {
    let r = Wr(d, t);
    if (!r) continue;
    let n = r.versions.map((a) => a.label),
      s = 0;
    for (let a of n) {
      let o = me.join(We(d), t, "versions", a, "fulltext.md");
      try {
        j.existsSync(o) && (s += j.statSync(o).size);
      } catch (c) {}
    }
    e.push({
      key: t,
      title: t.replace(/_/g, " "),
      versions: r.versions,
      currentLabel: r.current.label,
      totalSize: s,
    });
  }
  return (e.sort((t, r) => t.title.localeCompare(r.title)), e);
}
function pt(d, l, e, t = "") {
  let r = We(d),
    n = me.join(r, l, "versions", e, "fulltext.md"),
    s = me.join(r, l, "render"),
    a = me.join(s, "fulltext.md");
  try {
    return j.existsSync(n)
      ? (j.existsSync(s) || j.mkdirSync(s, { recursive: !0 }),
        j.copyFileSync(n, a),
        $t(r, l, {
          label: e,
          restored_at: new Date().toISOString(),
          version_created_at: t,
        }),
        !0)
      : !1;
  } catch (o) {
    return !1;
  }
}
function $t(d, l, e) {
  try {
    let t = me.join(d, l, "meta.json"),
      r = j.existsSync(t) ? JSON.parse(j.readFileSync(t, "utf-8")) : {};
    ((r.restore_provenance = e),
      j.writeFileSync(t, JSON.stringify(r, null, 2), "utf-8"));
  } catch (t) {}
}
function Jr(d, l, e, t) {
  var u;
  let r = We(d),
    n = me.join(r, l, "versions", e, "fulltext.md"),
    s = me.join(r, l, "versions", t, "fulltext.md"),
    a = "",
    o = "";
  try {
    j.existsSync(n) && (a = j.readFileSync(n, "utf-8"));
  } catch (h) {}
  try {
    j.existsSync(s) && (o = j.readFileSync(s, "utf-8"));
  } catch (h) {}
  let c = Zr(a),
    p = Zr(o),
    _ = Math.max(c.length, p.length),
    f = [];
  for (let h = 0; h < _; h++) {
    let g = h < c.length ? c[h] : "",
      m = h < p.length ? p[h] : "",
      v =
        (u = (g || m).split(`
`)[0]) != null
          ? u
          : "",
      x = v.startsWith("## ") ? v.replace(/^##\s+/, "") : "",
      w = "unchanged";
    (!g && m
      ? (w = "added")
      : g && !m
        ? (w = "removed")
        : g !== m && (w = "changed"),
      w !== "unchanged" &&
        f.push({
          paragraphIndex: h,
          heading: x,
          type: w,
          oldText: g || void 0,
          newText: m || void 0,
        }));
  }
  return f;
}
function Zr(d) {
  let l = d.split(`
`),
    e = [],
    t = [];
  for (let r of l)
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
var K = require("obsidian"),
  W = Z(require("fs")),
  Q = Z(require("path")),
  Qr = require("child_process");
Pe();
var dt = 100;
var Ne = class extends K.ItemView {
  constructor(e, t) {
    super(e);
    this.plugin = t;
    this.papers = [];
    this.filter = "all";
    this.versionFilter = null;
    this.selectedKey = null;
    this.checkedKeys = new Set();
    this.running = !1;
    this.progress = { current: 0, total: 0, paperKey: "" };
    this._searchQuery = "";
    this._page = 1;
    this._enriched = !1;
    this._runningMode = null;
  }
  static async open(e) {
    let t = e.app.workspace.getLeavesOfType(Ae);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getLeaf("tab");
    r &&
      (await r.setViewState({ type: Ae, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
  getViewType() {
    return Ae;
  }
  getDisplayText() {
    return i("ocr_ws_title");
  }
  getIcon() {
    return "scan-text";
  }
  async onOpen() {
    (await this._loadPapers(), this._render());
  }
  async _loadPapers() {
    var n, s, a, o, c, p, _, f, u, h, g, m, v, x, w, y, b;
    let e = this.app.vault.adapter.basePath,
      t = ae(e),
      r = Q.join(t.indexesDir, "formal-library.json");
    if (!W.existsSync(r)) {
      this.papers = [];
      return;
    }
    try {
      let k = JSON.parse(W.readFileSync(r, "utf-8")),
        S = (n = k == null ? void 0 : k.items) != null ? n : [],
        E = new Map(this.papers.map((C) => [C.key, C]));
      this.papers = [];
      for (let C of S) {
        let P = C.zotero_key;
        if (!P) continue;
        let T = E.get(P);
        this.papers.push({
          key: P,
          title: (s = C.title) != null ? s : P,
          status:
            (o =
              (a = T == null ? void 0 : T.status) != null ? a : C.ocr_status) !=
            null
              ? o
              : "pending",
          pipelineVersion:
            (c = T == null ? void 0 : T.pipelineVersion) != null ? c : "",
          lastRun:
            (_ =
              (p = T == null ? void 0 : T.lastRun) != null ? p : C.ocr_time) !=
            null
              ? _
              : "",
          hasBackup: (f = T == null ? void 0 : T.hasBackup) != null ? f : !1,
          authors:
            (g =
              (h = (u = C.authors) == null ? void 0 : u.join) == null
                ? void 0
                : h.call(u, ", ")) != null
              ? g
              : "",
          year: (m = C.year) != null ? m : "",
          pages: (v = T == null ? void 0 : T.pages) != null ? v : "",
          backupCount: (x = T == null ? void 0 : T.backupCount) != null ? x : 0,
          fulltextPath: (w = C.fulltext_path) != null ? w : "",
          ocrFinishedAt:
            (b =
              (y = T == null ? void 0 : T.ocrFinishedAt) != null
                ? y
                : C.ocr_time) != null
              ? b
              : "",
        });
      }
    } catch (k) {
      this.papers = [];
    }
    ((this._page = 1),
      this._enriched || ((this._enriched = !0), this._enrichFromOcrList(e)));
  }
  _enrichFromOcrList(e) {
    let t = this._resolvePython();
    return t
      ? new Promise((r) => {
          (0, Qr.execFile)(
            t.path,
            [...t.args, "-m", "paperforge", "ocr", "list", "--json"],
            { cwd: e, timeout: 6e4, windowsHide: !0 },
            (n, s) => {
              var a, o, c, p, _, f;
              if (!n)
                try {
                  let u = JSON.parse(s),
                    h =
                      (c =
                        (o =
                          (a = u == null ? void 0 : u.data) == null
                            ? void 0
                            : a.rows) != null
                          ? o
                          : u == null
                            ? void 0
                            : u.rows) != null
                        ? c
                        : [],
                    g = new Map(h.map((m) => [m.key, m]));
                  for (let m of this.papers) {
                    let v = g.get(m.key);
                    v &&
                      ((m.status = (p = v.status) != null ? p : m.status),
                      (m.pipelineVersion = (_ = v.version) != null ? _ : ""),
                      (m.lastRun = (f = v.finished_at) != null ? f : m.lastRun),
                      (m.pages = v.pages ? String(v.pages) : ""));
                  }
                } catch (u) {}
              (this._refreshTable(), r());
            }
          );
        })
      : Promise.resolve();
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
      (r.innerHTML = i("ocr_ws_showing")
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
    let s = e.querySelector(".pf-ocr-ws-pagination");
    (s && s.remove(), this._renderPagination(e, t));
    let a = e.querySelector(".pf-ocr-ws-batchbar");
    (a && a.remove(), this._renderBatchBar(e));
    let o = e.querySelector(".pf-ocr-ws-detail");
    (o && o.remove(), this.selectedKey && this._renderDetail(e));
  }
  _renderHeader(e) {
    let t = e.createDiv({ cls: "pf-ocr-ws-header" });
    (t.createEl("h1", { text: i("ocr_ws_title") }),
      t.createEl("p", { cls: "pf-ocr-ws-lede", text: i("ocr_ws_lede") }));
  }
  _renderActivity(e) {
    var f;
    if (!this.running) return;
    let t = e.createDiv({
        cls: "pf-ocr-ws-activity pf-active",
        attr: { "aria-live": "polite" },
      }),
      r = t.createDiv({ cls: "pf-ocr-ws-activity-head" }),
      n = r.createDiv({ cls: "pf-ocr-ws-activity-title" });
    n.setText(i("ocr_ws_processing"));
    let s = this.progress.paperKey;
    if (s) {
      let u = this.papers.find((h) => h.key === s);
      u && n.createEl("span").setText((f = u.title) != null ? f : s);
    }
    r.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: i("ocr_ws_stop"),
    }).addEventListener("click", () => this._stopBuild());
    let c = t
        .createDiv({ cls: "pf-ocr-ws-progress-track" })
        .createDiv({ cls: "pf-ocr-ws-progress-fill" }),
      p =
        this.progress.total > 0
          ? Math.round((this.progress.current / this.progress.total) * 100)
          : 0;
    c.style.transform = `scaleX(${p / 100})`;
    let _ = t.createDiv({ cls: "pf-ocr-ws-progress-meta" });
    (_.createEl("span", {
      text: `${this.progress.current} / ${this.progress.total} papers`,
    }),
      _.createEl("span", { text: `${p}%` }));
  }
  _renderToolbar(e) {
    let t = this._filteredPapers(),
      r = [
        ...new Set(this.papers.map((_) => _.pipelineVersion).filter(Boolean)),
      ]
        .sort()
        .reverse(),
      n = e.createDiv({ cls: "pf-ocr-ws-toolbar" }),
      s = n.createDiv({ cls: "pf-ocr-ws-toolbar-count" });
    s.innerHTML = i("ocr_ws_showing")
      .replace("{count}", String(t.length))
      .replace("{total}", String(this.papers.length));
    let o = n
      .createDiv({ cls: "pf-ocr-ws-search" })
      .createEl("input", {
        cls: "pf-ocr-ws-search-input",
        attr: {
          type: "text",
          placeholder:
            i("ocr_ws_search_placeholder") ||
            "Search papers by title, author, year...",
        },
      });
    ((o.value = this._searchQuery),
      o.addEventListener("input", () => {
        ((this._searchQuery = o.value),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          (this._page = 1),
          clearTimeout(this._searchTimer),
          (this._searchTimer = setTimeout(() => this._refreshTable(), 100)));
      }),
      o.addEventListener("keydown", (_) => {
        _.key === "Escape" &&
          ((o.value = ""),
          (this._searchQuery = ""),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          (this._page = 1),
          clearTimeout(this._searchTimer),
          this._refreshTable(),
          o.blur());
      }));
    let c = n.createDiv({ cls: "pf-ocr-ws-field" });
    c.createEl("label", { text: i("ocr_ws_filter_status") });
    let p = c.createEl("select");
    for (let [_, f] of [
      ["all", i("ocr_ws_filter_all")],
      ["unprocessed", i("ocr_ws_filter_unprocessed")],
      ["review", i("ocr_ws_filter_review")],
      ["processed", i("ocr_ws_filter_processed")],
    ]) {
      let u = p.createEl("option", {
        text: String(f),
        attr: { value: String(_) },
      });
      _ === this.filter && (u.selected = !0);
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
      let _ = n.createDiv({ cls: "pf-ocr-ws-version-field" });
      for (let f of r)
        _.createEl("button", {
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
        ? (e = e.filter((t) => t.status === "pending" || t.status === "nopdf"))
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
    let t = Math.max(1, Math.ceil(e.length / dt));
    (this._page > t && (this._page = t), this._page < 1 && (this._page = 1));
    let r = (this._page - 1) * dt;
    return e.slice(r, r + dt);
  }
  _renderPagination(e, t) {
    let r = Math.max(1, Math.ceil(t.length / dt));
    if (r <= 1) return;
    let n = e.createDiv({ cls: "pf-ocr-ws-pagination" }),
      s = n.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: "\u2039",
      });
    ((s.disabled = this._page <= 1),
      s.addEventListener("click", () => {
        ((this._page = Math.max(1, this._page - 1)), this._refreshTable());
      }));
    let a = n.createEl("span", { text: `${this._page} / ${r}` }),
      o = n.createEl("button", {
        cls: "pf-btn pf-btn-secondary",
        text: "\u203A",
      });
    ((o.disabled = this._page >= r),
      o.addEventListener("click", () => {
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
        text: i("ocr_ws_no_papers"),
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
          let s = this._currentPagePapers(this._filteredPapers());
          (n.checked
            ? s.forEach((a) => this.checkedKeys.add(a.key))
            : s.forEach((a) => this.checkedKeys.delete(a.key)),
            this._refreshTable());
        });
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-paper",
        text: i("ocr_ws_col_title"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-status",
        text: i("ocr_ws_col_status"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-version",
        text: i("ocr_ws_col_version"),
      }),
      r.createEl("th", {
        cls: "pf-ocr-ws-col-date",
        text: i("ocr_ws_col_lastrun"),
      }),
      r.createEl("th", { cls: "pf-ocr-ws-col-action" }));
  }
  _buildTableRows(e, t) {
    let r = e.createEl("tbody"),
      n = this.papers.reduce(
        (s, a) => (a.pipelineVersion > s ? a.pipelineVersion : s),
        ""
      );
    for (let s of t) {
      let a = !!(s.pipelineVersion && n > s.pipelineVersion),
        o = r.createEl("tr", { cls: a ? "pf-update" : "" });
      (o.addEventListener("click", (m) => {
        m.target.tagName !== "INPUT" &&
          ((this.selectedKey = s.key === this.selectedKey ? null : s.key),
          this._refreshTable());
      }),
        o
          .createEl("td", { cls: "pf-ocr-ws-col-check" })
          .createEl("input", { attr: { type: "checkbox" } }, (m) => {
            ((m.checked = this.checkedKeys.has(s.key)),
              m.addEventListener("change", () => {
                (m.checked
                  ? this.checkedKeys.add(s.key)
                  : this.checkedKeys.delete(s.key),
                  this._refreshTable());
              }));
          }));
      let p = o.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      if (
        (p.createDiv({ cls: "pf-ocr-ws-paper-title", text: s.title }),
        s.authors || s.year)
      ) {
        let m = p.createDiv({ cls: "pf-ocr-ws-paper-meta" });
        if (s.authors) {
          let v = s.authors.split(",")[0].trim(),
            x = s.authors.includes(",") ? " et al." : "";
          m.createEl("span", { cls: "pf-ocr-ws-meta-author", text: v + x });
        }
        s.year &&
          m.createEl("span", { cls: "pf-ocr-ws-meta-year", text: s.year });
      }
      (o
        .createEl("td", { cls: "pf-ocr-ws-col-status" })
        .createEl("span", {
          cls: `pf-ocr-ws-status pf-${Gr(s.status)}`,
          text: Yr(s.status),
        }),
        o
          .createEl("td", { cls: "pf-ocr-ws-col-version" })
          .createEl("span", {
            cls: "pf-ocr-ws-version",
            text: s.pipelineVersion || "\u2014",
          }),
        o
          .createEl("td", { cls: "pf-ocr-ws-col-date" })
          .setText(s.lastRun ? s.lastRun.slice(0, 10) : "\u2014"),
        o
          .createEl("td", { cls: "pf-ocr-ws-col-action" })
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: i("ocr_ws_btn_preview"),
          })
          .addEventListener("click", (m) => {
            (m.stopPropagation(), this._openFulltext(s.key));
          }));
    }
  }
  _renderBatchBar(e) {
    let t = this.papers.filter((o) => this.checkedKeys.has(o.key)),
      r = e.createDiv({ cls: "pf-ocr-ws-batchbar" }),
      n = r.createDiv({ cls: "pf-ocr-ws-selection" });
    t.length === 0
      ? (n.createEl("strong", { text: i("ocr_ws_none_selected") }),
        n.createEl("span", { text: i("ocr_ws_select_hint") }))
      : n.createEl("strong", {
          text: i("ocr_ws_selected").replace("{count}", String(t.length)),
        });
    let a = r
      .createDiv({ cls: "pf-ocr-ws-batch-actions" })
      .createEl("button", {
        cls: "pf-btn pf-btn-warning",
        text: i("ocr_ws_btn_rebuild_selected"),
      });
    ((a.title = i("ocr_ws_tooltip_rebuild")),
      (a.disabled = t.length === 0),
      a.addEventListener("click", () => this._runRebuild(t.map((o) => o.key))));
  }
  _renderDetail(e) {
    let t = this.papers.find((y) => y.key === this.selectedKey);
    if (!t) return;
    let n = e
        .createDiv({ cls: "pf-ocr-ws-detail pf-open" })
        .createDiv({ cls: "pf-ocr-ws-detail-card" }),
      s = n.createDiv({ cls: "pf-ocr-ws-detail-head" }),
      a = s.createDiv({});
    (a.createEl("h2", { text: t.title }),
      a.createEl("span", {
        cls: `pf-ocr-ws-status pf-${Gr(t.status)}`,
        text: Yr(t.status),
      }),
      s
        .createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          text: i("ocr_ws_close"),
        })
        .addEventListener("click", () => {
          ((this.selectedKey = null), this._refreshTable());
        }));
    let c = n.createDiv({ cls: "pf-ocr-ws-detail-grid" });
    (this._addFact(c, i("ocr_ws_fact_version"), t.pipelineVersion || "\u2014"),
      this._addFact(
        c,
        i("ocr_ws_fact_last_run"),
        t.lastRun ? t.lastRun.slice(0, 10) : "\u2014"
      ),
      this._addFact(c, i("ocr_ws_fact_authors"), t.authors || "\u2014"),
      this._addFact(c, i("ocr_ws_fact_year"), t.year || "\u2014"),
      this._addFact(c, i("ocr_ws_fact_pages"), t.pages || "\u2014"),
      this._addFact(
        c,
        i("ocr_ws_fact_backups"),
        t.backupCount > 0 ? String(t.backupCount) : "\u2014"
      ));
    let p = n.createDiv({ cls: "pf-ocr-ws-detail-actions" });
    p.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: i("ocr_ws_detail_view_fulltext"),
    }).addEventListener("click", () => this._openFulltext(t.key));
    let f = p.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: i("ocr_ws_restore_checking") || "Checking versions\u2026",
    });
    f.disabled = !0;
    let u = this.app.vault.adapter.basePath,
      h = ae(u),
      g = t.key,
      m = (() => {
        try {
          let y = Je(u, t.key);
          return y && y.versions.length > 0;
        } catch (y) {
          return !1;
        }
      })(),
      v = !1;
    if (!m) {
      let y = Q.join(h.ocrDir, t.key, "backups");
      try {
        v =
          W.readdirSync(y).filter((b) => b.startsWith("fulltext.pre-rebuild"))
            .length > 0;
      } catch (b) {}
    }
    let x = m || v;
    (this.selectedKey === g &&
      ((f.disabled = !x),
      f.setText(i("ocr_ws_detail_restore_backup") || "Restore Backup"),
      x ||
        (f.title =
          i("ocr_ws_restore_unavailable") || "No backup versions available")),
      f.addEventListener("click", () => {
        let y = Je(u, t.key);
        if (y && y.versions.length > 0) {
          new De(
            this.app,
            u,
            t.key,
            y.versions.map((P) => ({
              label: P.label,
              created_at: P.created_at,
              source: P.source,
              renderer_version: P.renderer_version,
              fulltext_size: P.fulltext_size,
            })),
            y.currentLabel,
            () => {
              this._loadPapers().then(() => this._render());
            },
            t.ocrFinishedAt
          ).open();
          return;
        }
        let b = Q.join(h.ocrDir, t.key, "backups");
        if (!W.existsSync(b)) {
          new K.Notice("No backup versions available");
          return;
        }
        let k = W.readdirSync(b)
          .filter((C) => C.startsWith("fulltext.pre-rebuild"))
          .sort();
        if (k.length === 0) {
          new K.Notice("No backup versions available");
          return;
        }
        let S = k.map((C) => {
          let P = C.replace("fulltext.pre-rebuild.", "").replace(/\.md$/, ""),
            T =
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
            D = 0;
          try {
            D = W.statSync(Q.join(b, C)).size;
          } catch (I) {}
          return {
            label: "backup-" + P,
            created_at: T,
            source: "pre-rebuild",
            fulltext_size: D,
          };
        });
        new De(
          this.app,
          u,
          t.key,
          S,
          "",
          () => {
            this._loadPapers().then(() => this._render());
          },
          t.ocrFinishedAt
        ).open();
      }),
      p
        .createEl("button", {
          cls: "pf-btn pf-btn-warning",
          text: i("ocr_ws_detail_rebuild") || "Rebuild this paper",
        })
        .addEventListener("click", () => {
          this._runRebuild([t.key]);
        }));
  }
  _addFact(e, t, r) {
    let n = e.createDiv({ cls: "pf-ocr-ws-fact" });
    (n.createEl("dt", { text: t }), n.createEl("dd", { text: r }));
  }
  _resolvePython() {
    var s, a;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (a =
          (s = e == null ? void 0 : e.settings) == null
            ? void 0
            : s.python_path) == null
          ? void 0
          : a.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    if (!e || typeof e.getManagedRuntime != "function") return null;
    let r = e.getManagedRuntime();
    if (!r) return null;
    let n = he(r.current());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  _runRebuild(e) {
    let t = this._resolvePython(),
      r = this.app.vault.adapter.basePath;
    if (!(t != null && t.path)) {
      new K.Notice("Runtime not ready for rebuild");
      return;
    }
    ((this._runningMode = "rebuild"),
      (this.running = !0),
      (this.progress = { current: 0, total: e.length, paperKey: "" }),
      this._render());
    let n = e.length > 0 ? { kind: "papers", keys: e } : { kind: "all" };
    fr(t.path, t.args, r, "ocr.rebuild_derived", n, void 0, 3e5)
      .then((s) => {
        var _, f, u, h, g, m;
        ((this._runningMode = null), (this.running = !1));
        let a =
            (f = (_ = s.payload) == null ? void 0 : _.data) != null ? f : {},
          o = Array.isArray(a.rebuilt) ? a.rebuilt : [],
          c = Array.isArray(a.failed) ? a.failed : [];
        s.ok
          ? new K.Notice(
              (i("ocr_rebuild_complete") || "Rebuild completed") +
                (o.length ? ` (${o.length})` : "")
            )
          : c.length > 0
            ? new K.Notice(
                (i("ocr_rebuild_partial") || "Rebuild finished with failures") +
                  ": " +
                  c.join(", "),
                8e3
              )
            : new K.Notice(
                (i("ocr_error_notice") || "OCR error") +
                  ": " +
                  String(
                    (g =
                      (h = (u = s.payload) == null ? void 0 : u.error) == null
                        ? void 0
                        : h.message) != null
                      ? g
                      : "rebuild failed"
                  ),
                8e3
              );
        let p = (m = s.payload) == null ? void 0 : m.next_actions;
        (p &&
          p.some((v) => v.action_id === "embed.resume") &&
          new K.Notice(i("next_action_pending"), 8e3),
          this._loadPapers().then(() => this._render()));
      })
      .catch((s) => {
        ((this.running = !1),
          new K.Notice(
            (i("ocr_error_notice") || "OCR error") +
              ": " +
              ((s == null ? void 0 : s.message) || String(s))
          ),
          this._render());
      });
  }
  _stopBuild() {
    var e, t;
    if (this._runningMode === "rebuild") {
      new K.Notice(
        i("ocr_stopped_notice") || "Rebuild is not stoppable from here",
        4e3
      );
      return;
    }
    ((t = (e = this.plugin) == null ? void 0 : e.ocrProcessController) ==
      null || t.stop(),
      (this.running = !1),
      this._render());
  }
  _openFulltext(e) {
    var o;
    let t = this.app.vault.adapter.basePath,
      r = ae(t),
      n = this.papers.find((c) => c.key === e),
      s = Kn(
        t,
        (o = n == null ? void 0 : n.fulltextPath) != null ? o : "",
        e,
        r.ocrDir,
        W.existsSync
      );
    if (!s) {
      new K.Notice(i("ocr_ws_fulltext_not_found") || "Fulltext not found");
      return;
    }
    let a = this.app.vault.getAbstractFileByPath(
      Q.relative(t, s).replace(/\\/g, "/").replace(/^\//, "")
    );
    a
      ? this.app.workspace.getLeaf().openFile(a)
      : new K.Notice(
          i("ocr_ws_fulltext_not_found") || "Fulltext not found in vault"
        );
  }
};
function Kn(d, l, e, t, r = W.existsSync) {
  if (l) {
    let s = Q.join(d, l);
    if (r(s)) return s;
  }
  let n = Q.join(t, e, "fulltext.md");
  return r(n) ? n : null;
}
function Gr(d) {
  return d === "done"
    ? "pf-done"
    : d === "done_degraded"
      ? "pf-done-degraded"
      : d === "done_incomplete"
        ? "pf-done-incomplete"
        : d === "failed" || d === "error" || d === "fatal_error"
          ? "pf-failed"
          : "";
}
function Yr(d) {
  return d === "done"
    ? i("ocr_ws_status_done") || "Processed"
    : d === "done_degraded"
      ? i("ocr_ws_status_degraded") || "Partial"
      : d === "done_incomplete"
        ? i("ocr_ws_status_incomplete") || "Incomplete"
        : d === "failed" || d === "error" || d === "fatal_error"
          ? i("ocr_ws_status_failed") || "Failed"
          : d === "retryable_error"
            ? i("ocr_ws_status_error") || "Error"
            : d === "processing" || d === "running"
              ? i("ocr_ws_status_processing") || "Processing"
              : d === "queued"
                ? i("ocr_ws_status_queued") || "Queued"
                : d === "blocked"
                  ? i("ocr_ws_status_blocked") || "Blocked"
                  : d === "nopdf"
                    ? i("ocr_ws_status_nopdf") || "No PDF"
                    : i("ocr_ws_status_pending") || "Pending";
}
function Xr(d, l, e) {
  if (e.startsWith("backup-")) {
    let t = e.slice(7);
    return Q.join(d, l, "backups", "fulltext.pre-rebuild." + t + ".md");
  }
  return Q.join(d, l, "versions", e, "fulltext.md");
}
function qn(d, l) {
  let e = (a) => a.split(/\n\n+/).filter(Boolean),
    t = e(d),
    r = e(l),
    n = Math.max(t.length, r.length),
    s = [];
  for (let a = 0; a < n; a++) {
    let o = a < t.length ? t[a] : "",
      c = a < r.length ? r[a] : "";
    !o && c
      ? s.push({ type: "added", text: c })
      : o && !c
        ? s.push({ type: "removed", text: o })
        : o !== c
          ? (s.push({ type: "removed", text: o }),
            s.push({ type: "added", text: c }))
          : s.push({ type: "unchanged", text: o });
  }
  return s;
}
var De = class extends K.Modal {
  constructor(e, t, r, n, s, a, o = "") {
    super(e);
    this.paperFinishedAt = o;
    this.selectedIdx = 0;
    this.contentCache = new Map();
    ((this.vaultPath = t),
      (this.paperKey = r),
      (this.ocrDir = Q.join(t, "System", "PaperForge", "ocr")),
      (this.versions = n),
      (this.currentLabel = s),
      (this.onRestored = a != null ? a : null),
      (this.mdComponent = new K.Component()),
      this.mdComponent.load());
  }
  getContent(e) {
    let t = this.contentCache.get(e);
    if (t !== void 0) return t;
    try {
      let r = Xr(this.ocrDir, this.paperKey, e);
      if (W.existsSync(r)) {
        let n = W.readFileSync(r, "utf-8");
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
      W.existsSync(t) &&
        this.contentCache.set("__current__", W.readFileSync(t, "utf-8"));
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
      text: i("ocr_ws_restore_versions") || "Versions",
    });
    let s = r.createDiv({ cls: "pf-vr-timeline" });
    this.versions.forEach((m, v) => {
      let x = new Date(m.created_at).toLocaleDateString(),
        w = s.createDiv({
          cls:
            "pf-vr-entry" +
            (v === this.selectedIdx ? " pf-vr-entry--active" : "") +
            (m.label === this.currentLabel ? " pf-vr-entry--current" : ""),
          attr: { "data-idx": String(v) },
        });
      (w.createEl("span", { cls: "pf-vr-entry-label", text: m.label }),
        w.createEl("span", { cls: "pf-vr-entry-date", text: x }),
        m.label === this.currentLabel &&
          w.createEl("span", {
            cls: "pf-vr-entry-badge",
            text: i("ocr_ws_restore_current") || "current",
          }),
        w.addEventListener("click", () => {
          ((this.selectedIdx = v), this.renderAll());
        }));
    });
    let a = this.versions[this.selectedIdx],
      o = a.label === this.currentLabel,
      c = n.createDiv({ cls: "pf-vr-toolbar" }),
      p = c.createDiv({ cls: "pf-vr-info" }),
      _ = c.createDiv({ cls: "pf-vr-actions" }),
      f = new Date(a.created_at).toLocaleString(),
      u =
        a.fulltext_size > 1024
          ? (a.fulltext_size / 1024).toFixed(0) + "KB"
          : a.fulltext_size + "B";
    p.innerHTML =
      "<strong>" +
      a.label +
      "</strong>" +
      (o
        ? ' <span class="pf-vr-current-tag">' +
          (i("ocr_ws_restore_current") || "current") +
          "</span>"
        : "") +
      '<br><span class="pf-vr-info-meta">' +
      f +
      " \xB7 " +
      a.source +
      " \xB7 " +
      u +
      (a.renderer_version ? " \xB7 renderer v" + a.renderer_version : "") +
      "</span>";
    let h = n.createDiv({ cls: "pf-vr-content" }),
      g = n.createDiv({ cls: "pf-vr-diff" });
    (K.MarkdownRenderer.render(
      this.app,
      this.getContent(a.label),
      h,
      this.vaultPath,
      this.mdComponent
    ),
      (g.style.display = "none"),
      o ||
        (_.createEl("button", {
          cls: "btn-secondary pf-vr-btn",
          text: i("ocr_ws_restore_compare") || "Compare with current",
        }).addEventListener("click", () => {
          let x = this.getContent("__current__"),
            w = this.getContent(a.label);
          ((h.style.display = "none"),
            (g.style.display = "block"),
            g.empty(),
            g
              .createEl("div", { cls: "pf-vr-diff-header" })
              .setText(
                (
                  i("ocr_ws_restore_diff_title") || "Changes from current"
                ).replace("{v}", a.label)
              ));
          let b = g.createEl("div", { cls: "pf-vr-diff-body" }),
            k = qn(x, w);
          for (let E of k) {
            let C = b.createEl("div", {
              cls: "pf-vr-diff-line pf-vr-diff-" + E.type,
            });
            (C.createEl("span", {
              cls: "pf-vr-diff-prefix",
              text:
                E.type === "added"
                  ? "+ "
                  : E.type === "removed"
                    ? "\u2212 "
                    : "  ",
            }),
              C.createEl("span", {
                cls: "pf-vr-diff-text",
                text:
                  E.text.slice(0, 200) + (E.text.length > 200 ? "\u2026" : ""),
              }));
          }
          (k.length === 0 &&
            b.createEl("div", {
              cls: "pf-vr-diff-empty",
              text: i("ocr_ws_restore_no_diff") || "No differences",
            }),
            g
              .createEl("button", {
                cls: "btn-secondary pf-vr-btn",
                text: i("ocr_ws_restore_back") || "Back",
              })
              .addEventListener("click", () => {
                ((h.style.display = "block"),
                  (g.style.display = "none"),
                  g.empty());
              }));
        }),
        _.createEl("button", {
          cls: "btn-primary pf-vr-btn",
          text: i("ocr_ws_restore_btn") || "Restore this version",
        }).addEventListener("click", () => this.doRestore(a))));
  }
  doRestore(e) {
    if (e.label === this.currentLabel) return;
    let t = new K.Modal(this.app);
    (t.contentEl.addClass("paperforge-modal"),
      t.contentEl.createEl("h2", {
        text:
          i("ocr_ws_restore_confirm_title") ||
          "\u6062\u590D\u5C55\u793A\u5168\u6587\u6587\u672C",
      }),
      t.contentEl.createEl("div", {
        cls: "pf-vr-confirm-body",
        text:
          i("ocr_ws_restore_confirm_body") ||
          "\u5C06\u7528\u6240\u9009\u7248\u672C\u7684 fulltext.md \u8986\u76D6 render/fulltext.md\u3002OCR \u7ED3\u6784\u3001\u7D22\u5F15\u3001\u8BB0\u5FC6\u4E0E\u5411\u91CF\u5747\u4E0D\u53D7\u5F71\u54CD\u3002\u7EE7\u7EED\uFF1F",
      }));
    let r = t.contentEl.createDiv({ cls: "pf-vr-confirm-actions" });
    (r
      .createEl("button", {
        cls: "btn-secondary pf-vr-btn",
        text: i("next_action_cancel") || "Later",
      })
      .addEventListener("click", () => t.close()),
      r
        .createEl("button", {
          cls: "btn-primary pf-vr-btn mod-warning",
          text:
            i("ocr_ws_restore_confirm_btn") ||
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
      let n = Xr(this.ocrDir, this.paperKey, e.label),
        s = Q.join(this.ocrDir, this.paperKey, "render"),
        a = Q.join(s, "fulltext.md");
      try {
        W.existsSync(n) &&
          (W.existsSync(s) || W.mkdirSync(s, { recursive: !0 }),
          W.copyFileSync(n, a),
          (t = !0),
          $t(this.ocrDir, this.paperKey, {
            label: e.label,
            restored_at: new Date().toISOString(),
            version_created_at: e.created_at,
          }));
      } catch (o) {
        console.warn("[PaperForge] Restore backup failed:", o);
      }
    } else t = pt(this.vaultPath, this.paperKey, e.label, e.created_at);
    if (t) {
      new K.Notice(i("ocr_ws_detail_restore_done").replace("{label}", e.label));
      let n = new Date(e.created_at).getTime(),
        s = new Date(this.paperFinishedAt).getTime();
      (Number.isFinite(n) &&
        Number.isFinite(s) &&
        n < s &&
        new K.Notice(
          i("ocr_ws_restore_stale_notice") ||
            "This version predates the current structured state; rebuild the paper to re-sync structure",
          8e3
        ),
        this.close(),
        (r = this.onRestored) == null || r.call(this));
    } else new K.Notice("Restore failed");
  }
  onClose() {
    try {
      this.contentEl.empty();
    } catch (e) {}
    (this.contentCache.clear(), this.mdComponent.unload());
  }
};
var $e = class extends M.ItemView {
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
  _resolvePython() {
    var s, a, o;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (a =
          (s = e == null ? void 0 : e.settings) == null
            ? void 0
            : s.python_path) == null
          ? void 0
          : a.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    let r =
      (o = e == null ? void 0 : e.getManagedRuntime) == null
        ? void 0
        : o.call(e);
    if (!r) return null;
    let n = he(r.readPointer());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  getViewType() {
    return Ce;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return ze;
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
          let s =
            (r = (t = e.target) == null ? void 0 : t.tagName) == null
              ? void 0
              : r.toLowerCase();
          s !== "input" &&
            s !== "textarea" &&
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
      let s = (0, be.execFileSync)(
        r,
        [...n, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: e, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
      ).trim();
      if (!s) return;
      let a = s.startsWith("v") ? s : "v" + s;
      ((this._paperforgeVersion = a),
        this._versionBadge && this._versionBadge.setText(a));
    } catch (s) {}
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
    let { path: s, args: a = [] } = n;
    (0, be.execFile)(
      s,
      [...a, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (o, c) => {
        if (!o)
          try {
            let p = JSON.parse(c);
            if (p.ok && p.data) {
              let _ = this._normalizeDashboardData(p.data);
              ((this._cachedStats = _),
                this._metricsEl.empty(),
                this._renderStats(_),
                this._renderOcr(_),
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
      s = e.ocr_version_state || {},
      a = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: a,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (n.broken || 0) + (n.missing || 0),
      ocr_version_state: {
        total_papers: s.total_papers || 0,
        derived_stale_count: s.derived_stale_count || 0,
        raw_upgradable_count: s.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var a, o;
    let n =
        ((a = r == null ? void 0 : r.settings) == null
          ? void 0
          : a.system_dir) || "System",
      s = He.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = oe.readFileSync(s, "utf-8"),
        p = JSON.parse(c),
        _ = p.items || [],
        f = {},
        u = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        h = 0,
        g = 0,
        m = 0,
        v = 0,
        x = 0,
        w = 0;
      for (let y of _) {
        y.note_path && w++;
        let b = y.lifecycle || "pdf_ready";
        f[b] = (f[b] || 0) + 1;
        let k = y.health || {};
        for (let E of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (k[E] || "healthy") === "healthy" ? u[E].healthy++ : u[E].unhealthy++;
        let S = y.ocr_status || "";
        (h++,
          S === "done"
            ? g++
            : S === "pending"
              ? m++
              : S === "processing" || S === "queued" || S === "running"
                ? v++
                : x++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((o = this._cachedStats) == null ? void 0 : o.version) ||
          "\u2014",
        total_papers: _.length,
        formal_notes: w,
        exports: 0,
        bases: 0,
        ocr: { total: h, pending: m, processing: v, done: g, failed: x },
        path_errors: 0,
        lifecycle_level_counts: f,
        health_aggregate: u,
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
      let { path: _, args: f = [] } = p;
      (0, be.execFile)(
        _,
        [...f, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (u, h) => {
          if (u) {
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
    var s;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((s = t == null ? void 0 : t.settings) == null
          ? void 0
          : s.system_dir) || "System",
      n = He.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let a = oe.readFileSync(n, "utf-8");
      return JSON.parse(a);
    } catch (a) {
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
    return rr(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = ft(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var a;
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
    for (let o of n) {
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", o.color),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((a = o.value) == null ? void 0 : a.toString()) || "\u2014",
        }),
        c.createEl("div", { cls: "paperforge-metric-label", text: o.label }),
        o.barMax > 0 && this._buildMetricBar(c, o.value, o.barMax));
    }
    let s = e.ocr_version_state || {};
    if (
      s.total_papers > 0 &&
      (s.derived_stale_count > 0 || s.raw_upgradable_count > 0)
    ) {
      let o = [];
      (s.derived_stale_count > 0 && o.push(`${s.derived_stale_count} stale`),
        s.raw_upgradable_count > 0 &&
          o.push(`${s.raw_upgradable_count} upgradable`));
      let c = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (c.style.setProperty("--metric-color", "var(--color-yellow)"),
        c.createEl("div", {
          cls: "paperforge-metric-value",
          text: o.join(", "),
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
      s = t.pending || 0,
      a = t.processing || 0,
      o = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        a > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : s > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        a > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let c = [
        { cls: "pending", count: s },
        { cls: "active", count: a },
        { cls: "done", count: n },
        { cls: "failed", count: o },
      ];
      for (let p of c)
        if (p.count > 0) {
          let _ = ((p.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${p.cls}`,
            attr: { style: `width:${_}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let c = [
        { cls: "pending", value: s, label: "Pending" },
        { cls: "active", value: a, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: o, label: "Failed" },
      ];
      for (let p of c) {
        let _ = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (_.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: p.value.toString(),
        }),
          _.createEl("div", {
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
      s = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      a = !1;
    for (let o of n) {
      let c = s.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: o.label }),
        o.key === r
          ? (c.addClass("current"), (a = !0))
          : a
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
    for (let s of r) {
      let a = t[s.key] || "healthy",
        o = n.createEl("div", { cls: "paperforge-health-cell" }),
        c,
        p,
        _;
      (a === "healthy" || a === "ok"
        ? ((c = s.iconOk), (p = "ok"), (_ = `${s.label}: OK`))
        : a === "warn" || a === "warning" || a === "degraded"
          ? ((c = s.iconWarn),
            (p = "warn"),
            (_ = `${s.label}: Needs Attention`))
          : ((c = s.iconFail), (p = "fail"), (_ = `${s.label}: Failed`)),
        o.addClass(p),
        o.setAttribute("title", _),
        o.createEl("div", { cls: "paperforge-health-cell-icon", text: c }),
        o.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: s.label,
        }));
    }
  }
  _renderMaturityGauge(e, t, r) {
    if (t == null || t === void 0) {
      this._renderSkeleton(e);
      return;
    }
    let n = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      s = n.createEl("div", { cls: "gauge-track" }),
      a = 4,
      o = Math.max(1, Math.min(a, Math.round(t)));
    for (let c = 1; c <= a; c++) {
      let p = s.createEl("div", { cls: "gauge-segment" });
      c <= o && (p.addClass("filled"), p.addClass(`level-${c}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${o} / ${a}` }),
      o < a && r)
    ) {
      let c = typeof r == "string" ? [r] : r;
      if (c.length > 0) {
        let p = n.createEl("ul", { cls: "gauge-blockers" });
        for (let _ of c) p.createEl("li", { text: _ });
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
      s = Math.max(1, ...r.map((a) => t[a.key] || 0));
    for (let a of r) {
      let o = t[a.key] || 0,
        c = (o / s) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: a.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${a.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: o.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return Ur(e);
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
      let s = this.app.metadataCache.getFileCache(e),
        a = s && s.frontmatter && s.frontmatter.zotero_key;
      if (a) return { mode: "paper", filePath: r, key: a, domain: null };
    }
    if (t === "pdf") {
      let s = this._getCachedIndex();
      for (let a of s) {
        let o = (a.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((o ? o[1] : a.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: a.zotero_key,
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
    var A, U, X, B, N, te, re, fe;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" }),
      t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      s = 0,
      a = 0;
    for (let L of t)
      (L.has_pdf && n++,
        L.ocr_status === "done" && s++,
        L.deep_reading_status === "done" && a++);
    let o = e.createEl("div", { cls: "paperforge-library-snapshot" });
    o.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let c = o.createEl("div", { cls: "paperforge-snapshot-pills" }),
      p = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: s, label: "OCR done" },
        { value: a, label: "deep-read done" },
      ];
    for (let L of p) {
      let O = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (O.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(L.value),
      }),
        O.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + L.label,
        }));
    }
    let _ = e.createEl("div", { cls: "paperforge-system-status" });
    _.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let f = _.createEl("div", { cls: "paperforge-status-grid" }),
      u = this.app.plugins.plugins.paperforge,
      h = this._loadIndex(),
      g = h && h.items && h.items.length > 0;
    this._renderSystemStatusRow(
      f,
      "Index",
      g ? "healthy" : "missing",
      g ? h.items.length + " entries" : "formal-library.json not found"
    );
    let m =
        ((A = u == null ? void 0 : u.settings) == null
          ? void 0
          : A.system_dir) || "System",
      v = this.app.vault.adapter.basePath,
      x = !1,
      w = "No exports found";
    try {
      let L = He.join(v, m, "PaperForge", "exports");
      if (oe.existsSync(L)) {
        let O = oe.readdirSync(L).filter((ne) => ne.endsWith(".json"));
        ((x = O.length > 0),
          (w = x ? O.length + " export(s)" : "No JSON exports"));
      }
    } catch (L) {}
    this._renderSystemStatusRow(
      f,
      "Zotero Export",
      x ? "healthy" : "missing",
      w
    );
    let y =
        (X = (U = this.app.plugins) == null ? void 0 : U.plugins) == null
          ? void 0
          : X.paperforge,
      b = this._renderSystemStatusRow(
        f,
        "OCR Token",
        "checking",
        "Checking\u2026"
      );
    mr(v, y == null ? void 0 : y.settings).then(
      (L) => {
        if (!b.isConnected) return;
        let O = b.querySelector(".paperforge-status-dot");
        (O == null || O.classList.toggle("ok", L),
          O == null || O.classList.toggle("fail", !L));
        let ne = b.querySelector(".paperforge-status-detail");
        ne && (ne.textContent = L ? "Configured" : "Not set");
      },
      () => {
        if (!b.isConnected) return;
        let L = b.querySelector(".paperforge-status-detail");
        L && (L.textContent = "Status unavailable");
      }
    );
    let k = (B = this.app.vault.adapter.basePath) != null ? B : "",
      S =
        (te =
          (N = u == null ? void 0 : u.settings) == null
            ? void 0
            : N.capabilityState) == null
          ? void 0
          : te.memory,
      E = (S == null ? void 0 : S.capability_state) === "ready",
      C =
        (fe =
          (re = S == null ? void 0 : S.reason) == null ? void 0 : re.text) !=
        null
          ? fe
          : "Unknown";
    if (
      (this._renderSystemStatusRow(
        f,
        "Memory Layer",
        E ? "healthy" : "fail",
        C
      ),
      !g || !x)
    ) {
      let L = e.createEl("div", { cls: "paperforge-issue-summary" });
      L.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let O = L.createEl("div", { cls: "paperforge-issue-list" });
      (g ||
        O.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Index missing or corrupted",
        }),
        x ||
          O.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }));
      let ne = L.createEl("div", { cls: "paperforge-issue-actions" }),
        F = ne.createEl("button", { cls: "paperforge-contextual-btn" });
      (F.createEl("span", { text: "Run Doctor" }),
        F.addEventListener("click", () => {
          let se = ce.find((le) => le.id === "paperforge-doctor");
          se && this._runAction(se, F);
        }));
      let H = ne.createEl("button", { cls: "paperforge-contextual-btn" });
      (H.createEl("span", { text: "Repair Issues" }),
        H.addEventListener("click", () => {
          let se = ce.find((le) => le.id === "paperforge-repair");
          se && this._runAction(se, H);
        }));
    }
    let T = e.createEl("div", { cls: "paperforge-global-actions" });
    T.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let D = T.createEl("div", { cls: "paperforge-global-actions-row" }),
      I = D.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (I.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      I.createEl("span", { text: "Open Literature Hub" }),
      I.addEventListener("click", () => {
        var ne;
        let L =
            ((ne = u == null ? void 0 : u.settings) == null
              ? void 0
              : ne.base_dir) || "Bases",
          O = this.app.vault.getAbstractFileByPath(L);
        if (O) {
          let F = null;
          if (
            (O.children && (F = O.children.find((H) => H.extension === "base")),
            F)
          ) {
            let H = this.app.workspace.getLeaf(!1);
            H && H.openFile(F);
          } else new M.Notice("[!!] No .base file found in " + L, 6e3);
        } else new M.Notice("[!!] Base directory not found: " + L, 6e3);
      }));
    let z = D.createEl("button", { cls: "paperforge-contextual-btn" });
    (z.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      z.createEl("span", { text: "Sync Library" }),
      z.addEventListener("click", () => {
        let L = ce.find((O) => O.id === "paperforge-sync");
        L && this._runAction(L, z);
      }));
    let ee = D.createEl("button", { cls: "paperforge-contextual-btn" });
    (ee.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      ee.createEl("span", { text: "Run OCR" }),
      ee.addEventListener("click", () => {
        let L = ce.find((O) => O.id === "paperforge-ocr");
        L && this._runAction(L, ee);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let s = e.createEl("div", { cls: "paperforge-status-row" });
    return (
      s
        .createEl("span", { cls: "paperforge-status-dot" })
        .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      s.createEl("span", { cls: "paperforge-status-label", text: t }),
      s.createEl("span", { cls: "paperforge-status-detail", text: n || "" }),
      s
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
        new M.Notice("Title copied"));
    });
    let a = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      a.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        a.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let o = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = o.createEl("div", { cls: "paperforge-status-strip-left" }),
      p = o.createEl("div", { cls: "paperforge-status-strip-right" }),
      _ = [
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
    for (let u of _) {
      let h = c.createEl("span", { cls: "paperforge-status-pill" }),
        g = "pending";
      (u.ok ? (g = "ok") : u.fail ? (g = "fail") : u.pending && (g = "pending"),
        h.addClass(g));
      let m = u.ok ? "\u2713" : u.fail ? "\u2717" : "\u25CB";
      (h.createEl("span", { cls: "paperforge-status-pill-icon", text: m }),
        h.createEl("span", { text: " " + u.label }));
    }
    if (e.pdf_path) {
      let u = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (u.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        u.createEl("span", { text: "\u6253\u5F00 PDF" }),
        u.addEventListener("click", () => {
          let h = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            g = h ? h[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(g)
            ? this.app.workspace.openLinkText(g, "")
            : new M.Notice("[!!] PDF not found: " + g, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let u = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (u.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        u.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        u.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (f.createEl("span", { text: i("version_panel_title") }),
      f.addEventListener("click", () => {
        let u = t,
          h = this.app.vault.adapter.basePath,
          g = ae(h),
          m = Je(h, u);
        if (m && m.versions.length > 0) {
          new De(
            this.app,
            h,
            u,
            m.versions.map((y) => ({
              label: y.label,
              created_at: y.created_at,
              source: y.source,
              renderer_version: y.renderer_version,
              fulltext_size: y.fulltext_size,
            })),
            m.currentLabel
          ).open();
          return;
        }
        let v = He.join(g.ocrDir, u, "backups");
        if (!oe.existsSync(v)) return;
        let x = oe
          .readdirSync(v)
          .filter((y) => y.startsWith("fulltext.pre-rebuild"))
          .sort();
        if (x.length === 0) return;
        let w = x.map((y) => {
          let b = y.replace("fulltext.pre-rebuild.", "").replace(/\.md$/, ""),
            k =
              b.length >= 16
                ? b.slice(0, 4) +
                  "-" +
                  b.slice(4, 6) +
                  "-" +
                  b.slice(6, 8) +
                  "T" +
                  b.slice(9, 11) +
                  ":" +
                  b.slice(11, 13) +
                  ":" +
                  b.slice(13, 15) +
                  "Z"
                : b,
            S = 0;
          try {
            S = oe.statSync(He.join(v, y)).size;
          } catch (E) {}
          return {
            label: "backup-" + b,
            created_at: k,
            source: "pre-rebuild",
            fulltext_size: S,
          };
        });
        new De(this.app, h, u, w, "").open();
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let u = r.createEl("div", { cls: "paperforge-complete-row" });
      (u.createEl("span", { text: "\u2713" }),
        u.createEl("span", {
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
    let s = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      a = s.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let o = this.app.vault.getAbstractFileByPath(t.note_path);
      o
        ? this.app.vault
            .read(o)
            .then((c) => {
              let p = this._extractOverviewFromNote(c);
              if (p) {
                let _ = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((a.setText(_), p.length > 200)) {
                  let f = s.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    u = f.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  u.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let h = !1;
                  f.addEventListener("click", () => {
                    (a.setText(h ? _ : p),
                      (u.innerHTML = h
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (h = !h));
                  });
                }
              } else
                a.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              a.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : a.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else a.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
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
    for (let o of n) {
      let c = r.indexOf(o);
      if (c !== -1) {
        let p = r.slice(c + o.length),
          _ = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          f = p.length;
        for (let g of _) {
          let m = p.indexOf(g);
          m !== -1 && m < f && (f = m);
        }
        let u = p.indexOf(`

`);
        u !== -1 && u < f && (f = u);
        let h = p.slice(0, f).trim();
        return (
          h.startsWith("**") && (h = h.slice(2)),
          h.endsWith("**") && (h = h.slice(0, -2)),
          h || null
        );
      }
    }
    let s = r.indexOf(`
`);
    if (s === -1) return null;
    let a = r
      .slice(s + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !a || a.startsWith("###") || a.startsWith("##")
      ? null
      : a.length > 300
        ? a.slice(0, 300) + "..."
        : a;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      a = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(a)
      .then((o) => {
        if (o) return this.app.vault.adapter.read(a);
      })
      .then(async (o) => {
        if (!o) return;
        let c = this._parseDiscussionMD(o);
        if (!c || c.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let f of c) {
          let u = r.createEl("div", { cls: "paperforge-discussion-item" }),
            h = u.createEl("div", { cls: "paperforge-discussion-q" });
          (h.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            h.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: f.question,
            }));
          let g = u.createEl("div", { cls: "paperforge-discussion-a" }),
            m = !1;
          if (
            (f.answer &&
              f.answer.length > 500 &&
              ((m = !0), g.classList.add("paperforge-discussion-a-collapsed")),
            await M.MarkdownRenderer.render(
              this.app,
              f.answer || "",
              g,
              a,
              this
            ),
            m)
          ) {
            let v = !1;
            ((u.style.cursor = "pointer"),
              u.addEventListener("click", () => {
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
            this.app.vault.getAbstractFileByPath(a)
              ? this.app.workspace.openLinkText(a, "")
              : new M.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((o) => {
        console.error("PaperForge: discussion.md read error", a, o.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      s = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let a of s) {
      let o = a.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!o) continue;
      let c = a.substring(0, o.index).trim(),
        p = a.substring(o.index + 3 + 4).trim();
      n.push({ question: c, answer: p });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      s = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      a = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((a.style.display = "none"),
      this._techDetailsExpanded
        ? ((a.style.display = "block"),
          s.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : s.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      s.addEventListener("click", () => {
        let u = a.style.display !== "none";
        ((a.style.display = u ? "none" : "block"),
          s.setText(
            u
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !u));
      }));
    let o = a.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let u of c) {
      let h = o.createEl("label", { cls: "paperforge-workflow-toggle" }),
        g = h.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((g.checked = t[u.key] === !0),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: u.label,
        }),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: u.hint,
        }),
        g.addEventListener("change", async () => {
          let m = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!m) {
            new M.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let v = g.checked;
          (await this.app.fileManager.processFrontMatter(m, (x) => {
            x[u.key] = v;
          }),
            this._patchCachedEntry(r, { [u.key]: v }),
            (this._currentPaperEntry = ft(this._currentPaperEntry, {
              [u.key]: v,
            })));
        }));
    }
    let p = t.health || {},
      _ = [
        ["PDF Health", p.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", p.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      f = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [u, h] of _) {
      let g = a.createEl("div", { cls: "paperforge-technical-row" });
      g.createEl("span", { cls: "paperforge-technical-label", text: u });
      let m = g.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(h),
      });
      f.has(u) &&
        h &&
        h !== "\u2014" &&
        (m.addClass("pf-copy"),
        m.addEventListener("click", () => {
          (navigator.clipboard.writeText(h), new M.Notice(u + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var c, p;
    let n = t.next_step || "ready",
      s = {
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
      a = s[n] || s.ready,
      o = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && o.addClass("ready"),
      o.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      o.createEl("div", { cls: "paperforge-next-step-text", text: a.text }),
      a.actionId && a.actionId !== "ready")
    ) {
      let _ = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (_.createEl("span", { text: a.icon + "  " + a.label }),
        _.addEventListener("click", () => {
          let f = ce.find((u) => u.id === a.actionId);
          f && this._runAction(f, _);
        }));
    } else if (n === "/pf-deep") {
      let _ = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (_.createEl("span", { text: "\u{1F4CB}  " + i("copy_pf_deep_cmd") }),
        _.addEventListener("click", () => {
          let m = "/pf-deep " + r;
          navigator.clipboard
            .writeText(m)
            .then(() => {
              (_.setText("\u2713  " + i("copied")),
                new M.Notice(m + " copied"));
            })
            .catch(() => {
              new M.Notice("[!!] Clipboard write failed", 6e3);
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
      o.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        i("run_in_agent").replace("{0}", h)
      );
    } else
      n === "ready" &&
        o
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + a.label });
  }
  _openFulltext(e) {
    if (!e) {
      new M.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new M.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      s = 0,
      a = 0,
      o = 0,
      c = 0,
      p = 0,
      _ = 0,
      f = 0;
    for (let y of t) {
      (y.has_pdf && s++,
        y.ocr_status === "done" && a++,
        y.ocr_status === "done" && y.analyze === !0 && o++,
        y.deep_reading_status === "done" && c++);
      let b = y.ocr_status || "";
      b === "pending" || b === "queued"
        ? p++
        : b === "processing"
          ? _++
          : (b === "failed" ||
              b === "blocked" ||
              b === "done_incomplete" ||
              b === "nopdf") &&
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
        { value: s, label: "PDF Ready" },
        { value: a, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let y = 0; y < m.length; y++) {
      let b = g.createEl("div", { cls: "paperforge-workflow-stage" });
      (b.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(m[y].value),
      }),
        b.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: m[y].label,
        }),
        y < m.length - 1 &&
          g.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (p + _ + a + f > 0) {
      let y = r.createEl("div", { cls: "paperforge-ocr-section" }),
        b = y.createEl("div", { cls: "paperforge-collection-ocr-header" });
      b.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let k = b.createEl("span", { cls: "paperforge-ocr-badge idle" });
      _ > 0
        ? (k.addClass("active"), k.setText("Processing"))
        : p > 0
          ? k.setText("Pending")
          : (k.addClass("idle"), k.setText("Idle"));
      let S = y.createEl("div", { cls: "paperforge-progress-track" });
      _ > 0 && S.addClass("paperforge-processing");
      let E = p + _ + a + f,
        C = [
          { cls: "pending", count: p },
          { cls: "active", count: _ },
          { cls: "done", count: a },
          { cls: "failed", count: f },
        ];
      for (let D of C)
        if (D.count > 0) {
          let I = ((D.count / E) * 100).toFixed(1);
          S.createEl("div", {
            cls: `paperforge-progress-seg ${D.cls}`,
            attr: { style: `width:${I}%` },
          });
        }
      let P = y.createEl("div", { cls: "paperforge-ocr-counts" }),
        T = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: _, label: "Processing" },
          { cls: "done", value: a, label: "Done" },
          { cls: "failed", value: f, label: "Attention" },
        ];
      for (let D of T) {
        let I = P.createEl("div", { cls: "paperforge-ocr-count" });
        (I.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: D.value.toString(),
        }),
          I.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: D.label,
          }));
      }
    }
    let v = r.createEl("div", { cls: "paperforge-collection-actions" }),
      x = v.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (x.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      x.createEl("span", { text: "Run OCR" }),
      x.addEventListener("click", () => {
        let y = ce.find((b) => b.id === "paperforge-ocr");
        y && this._runAction(y, x);
      }));
    let w = v.createEl("button", { cls: "paperforge-contextual-btn" });
    (w.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      w.createEl("span", { text: "Sync Library" }),
      w.addEventListener("click", () => {
        let y = ce.find((b) => b.id === "paperforge-sync");
        y && this._runAction(y, w);
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
      new M.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = Ht(n)),
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
      (this._versionPapers = Ht(n));
    let s = e.createEl("div", { cls: "paperforge-version-left" }),
      a = e.createEl("div", { cls: "paperforge-version-right" }),
      o = s.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: i("version_filter_placeholder") },
      });
    o.value = this._versionFilter;
    let c = s.createEl("div", { cls: "paperforge-version-paper-list" }),
      p = () => {
        c.empty();
        let x = this._versionFilter.toLowerCase(),
          w = this._versionPapers
            ? this._versionPapers.filter(
                (b) =>
                  !x ||
                  b.key.toLowerCase().includes(x) ||
                  b.title.toLowerCase().includes(x)
              )
            : [];
        if (w.length === 0) {
          c.createEl("div", {
            cls: "paperforge-meta",
            text: i("version_no_backups"),
          });
          return;
        }
        let y = c.createEl("div", {
          cls: "paperforge-meta",
          text: i("version_papers_count").replace("{n}", String(w.length)),
        });
        for (let b of w) {
          let k = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            S = k.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: b.title,
            }),
            E = k.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: b.versions.map((C) => C.label).join(" "),
            });
          k.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((C) => C.removeClass("selected")),
              k.addClass("selected"),
              f(b));
          });
        }
      };
    o.addEventListener("input", () => {
      ((this._versionFilter = o.value), p());
    });
    let _ = a.createEl("div", { cls: "paperforge-version-timeline-area" }),
      f = (x) => {
        if (
          (_.empty(),
          _.createEl("div", {
            cls: "paperforge-version-timeline-header",
          }).createEl("span", { cls: "pf-title", text: x.title }),
          x.versions.length === 0)
        ) {
          _.createEl("div", {
            cls: "paperforge-meta",
            text: i("version_no_backups"),
          });
          return;
        }
        let y = _.createEl("div", { cls: "paperforge-version-timeline" });
        for (let b of x.versions) {
          let k = b.label === x.currentLabel,
            S = y.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (k ? " paperforge-version-current" : ""),
            }),
            E = S.createEl("div", { cls: "paperforge-version-dot" }),
            C = S.createEl("div", { cls: "paperforge-version-content" }),
            P = C.createEl("div", { cls: "paperforge-version-label-row" });
          (P.createEl("span", {
            cls: "paperforge-version-label",
            text: b.label,
          }),
            k &&
              P.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: i("version_current"),
              }));
          let T = b.created_at ? b.created_at.slice(0, 10) : "";
          C.createEl("div", {
            cls: "paperforge-meta",
            text: T + " \u2014 " + b.source,
          });
          let D = b.fulltext_size
            ? b.fulltext_size > 1024
              ? (b.fulltext_size / 1024).toFixed(0) + "KB"
              : b.fulltext_size + "B"
            : "";
          D && C.createEl("div", { cls: "paperforge-meta", text: D });
          let I = C.createEl("div", { cls: "paperforge-version-actions" });
          (I.createEl("button", {
            cls: "pf-btn-primary",
            text: i("version_restore_btn"),
          }).addEventListener("click", () => {
            pt(n, x.key, b.label)
              ? new M.Notice(
                  i("version_restore_done").replace("{label}", b.label)
                )
              : new M.Notice("Restore failed", 6e3);
          }),
            x.versions.length > 1 &&
              !k &&
              I.createEl("button", {
                cls: "pf-btn-secondary",
                text: i("version_compare_btn"),
              }).addEventListener("click", () => {
                h(x, b.label, x.currentLabel);
              }));
        }
      },
      u = a.createEl("div", { cls: "paperforge-version-compare" });
    u.style.display = "none";
    let h = (x, w, y) => {
        let b = Jr(n, x.key, w, y);
        ((u.style.display = "block"), u.empty());
        let k = u.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (k.createEl("span", {
            cls: "pf-title",
            text: i("version_compare_title")
              .replace("{vA}", w)
              .replace("{vB}", y),
          }),
          k.createEl("span", {
            cls: "paperforge-meta",
            text: i("version_compare_paragraphs").replace(
              "{n}",
              String(b.length)
            ),
          }),
          b.length === 0)
        ) {
          u.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let S = u.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let E of b) {
          let C = S.createEl("div", { cls: "paperforge-version-diff-row" }),
            P =
              E.type === "added" ? "[+]" : E.type === "removed" ? "[-]" : "[~]",
            T = E.heading || "paragraph " + (E.paragraphIndex + 1);
          (C.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: P + " " + T,
          }),
            E.oldText &&
              C.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: E.oldText.slice(0, 200),
              }),
            E.newText &&
              C.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: E.newText.slice(0, 200),
              }));
        }
      },
      g = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      m = g.createEl("button", {
        cls: "pf-btn-primary",
        text: i("version_restore_selected"),
      }),
      v = g.createEl("button", {
        cls: "pf-btn-secondary",
        text: i("version_clear_old").replace("{size}", ""),
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
      (this._searchInput.placeholder = i("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var a;
        let s = ((a = this._searchInput) == null ? void 0 : a.value) || "";
        if (
          (s.startsWith("@") && !s.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = i(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = i(
                  "retrieval_search_placeholder"
                ))),
          clearTimeout(this._searchTimer),
          !s.trim())
        ) {
          ((this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        s.startsWith("@") ||
          (this._searchTimer = setTimeout(() => {
            this.executeSearch();
          }, 200));
      }),
      this._searchInput.addEventListener("keydown", (s) => {
        var a, o;
        if (s.key === "Escape") {
          (s.preventDefault(),
            this._searchInput &&
              ((this._searchInput.value = ""), this._searchInput.blur()),
            (this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        if (s.key === "ArrowDown" || s.key === "ArrowUp") {
          if (
            this._searchState !== "results" ||
            !((a = this._searchResults) != null && a.length)
          )
            return;
          s.preventDefault();
          let c = this._searchResults.length;
          s.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                c - 1
              ))
            : (this._searchActiveIndex = Math.max(
                this._searchActiveIndex - 1,
                -1
              ));
          let p =
            (o = this._searchResultsEl) == null
              ? void 0
              : o.querySelectorAll(".paperforge-search-result-card");
          p &&
            p.forEach((_, f) => {
              f === this._searchActiveIndex
                ? (_.setAttribute("aria-selected", "true"),
                  _.classList.add("active"))
                : (_.setAttribute("aria-selected", "false"),
                  _.classList.remove("active"));
            });
          return;
        }
        if (s.key === "Enter" && s.ctrlKey) {
          (s.preventDefault(),
            this._searchTimer &&
              (clearTimeout(this._searchTimer), (this._searchTimer = void 0)));
          let c = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = c));
          return;
        }
        s.key === "Enter" &&
          (s.preventDefault(),
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
            ? i("retrieval_searching_deep")
            : i("retrieval_searching_metadata"),
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
          t.createEl("div", { text: i("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: i("retrieval_empty_tips"),
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
            text: i("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: i("retrieval_open_vector_settings"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let s = n.openTab;
            typeof s == "function" && s.call(n, "paperforge");
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
            text: i("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: i("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let a = this.app.vault.adapter.basePath;
          if (typeof a != "string") return;
          let o = this._resolvePython();
          if (!o) return;
          let { path: c, args: p = [] } = o;
          (0, be.spawn)(c, [...p, "-m", "paperforge", "doctor"], {
            cwd: a,
            stdio: "inherit",
          });
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: i("retrieval_retry"),
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
            text: i("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: i("retrieval_retry"),
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
            text: i("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: i("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: i("retrieval_rebuild_vectors"),
        });
        (r.addEventListener("click", () => {
          let n = this.app.setting;
          if (n && typeof n == "object") {
            let s = n.openTab;
            typeof s == "function" && s.call(n, "paperforge");
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
            text: i("retrieval_internal_error"),
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
    let s = this.app.vault.adapter,
      a = "";
    if (s && typeof s == "object" && "basePath" in s) {
      let g = s.basePath;
      a = typeof g == "string" ? g : "";
    }
    if (!a) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let o = this._resolvePython();
    if (!o) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let { path: c, args: p = [] } = o,
      _ = n === "retrieve" ? ["--deep"] : [],
      f = await ue(null, "memory"),
      u = (0, be.spawn)(
        c,
        [...p, "-m", "paperforge", "--vault", a, n, r, ..._, "--json"],
        { cwd: a, timeout: 3e4, env: f }
      ),
      h = [];
    (u.stdout.on("data", (g) => {
      h.push(g.toString("utf-8"));
    }),
      u.stderr.on("data", () => {}),
      u.on("close", (g) => {
        if (g !== 0) {
          let y = kt(String(g));
          ((this._searchState = this._mapErrorToSearchState(y.type)),
            this._renderSearchState());
          return;
        }
        let m = h.join(""),
          v = m.indexOf("{"),
          x = m.lastIndexOf("}"),
          w = "";
        if (v !== -1 && x > v) w = m.slice(v, x + 1);
        else {
          let y = m.indexOf("["),
            b = m.lastIndexOf("]");
          y !== -1 && b > y && (w = m.slice(y, b + 1));
        }
        if (!w) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let y = JSON.parse(w),
            b = [];
          if (y && typeof y == "object" && "data" in y) {
            let k = y.data;
            if (k && typeof k == "object") {
              let S = k;
              "matches" in S && Array.isArray(S.matches) && (b = S.matches);
            }
          }
          ((this._searchResults = b),
            (this._searchState = b.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (y) {
          let b = y instanceof Error ? y.message : String(y);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      u.on("error", (g) => {
        let m = g.code;
        if (typeof m == "string") {
          let v = kt(m);
          this._searchState = this._mapErrorToSearchState(v.type);
        } else this._searchState = "backend-unavailable";
        this._renderSearchState();
      }));
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
        text: i("retrieval_results_count")
          .replace("{n}", String(e.length))
          .replace("{s}", e.length !== 1 ? "s" : ""),
      })
      .setAttr("aria-live", "polite"),
      r.createEl("span", {
        cls: "paperforge-search-mode",
        text: t ? "@" : "M",
      }));
    for (let s = 0; s < e.length; s++) {
      let a = e[s];
      if (!a || typeof a != "object") continue;
      let o = a,
        c = s === this._searchActiveIndex,
        p = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": c ? "true" : "false",
            "aria-posinset": String(s + 1),
            "aria-setsize": String(e.length),
          },
        });
      c && p.addClass("active");
      let _ =
        typeof o.title == "string"
          ? o.title
          : typeof o.file_name == "string"
            ? o.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: _ });
      let f = typeof o.zotero_key == "string" ? o.zotero_key : "",
        u =
          typeof o.main_note_path == "string" && o.main_note_path
            ? o.main_note_path
            : null,
        h = typeof o.note_path == "string" && o.note_path ? o.note_path : null,
        g = u || h;
      if (!g && f) {
        let x = this._getCachedIndex().find(
          (w) =>
            w !== null &&
            typeof w == "object" &&
            "zotero_key" in w &&
            w.zotero_key === f
        );
        if (x && typeof x == "object") {
          let w = x;
          g =
            typeof w.main_note_path == "string" && w.main_note_path
              ? w.main_note_path
              : typeof w.note_path == "string" && w.note_path
                ? w.note_path
                : null;
        }
      }
      (g
        ? p.addEventListener("click", (v) => {
            let x = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", x);
          })
        : p.addEventListener("click", () => {
            new M.Notice("[!!] Note not found: " + (f || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (v) => {
          if (v.key === "Enter" && g) {
            v.preventDefault();
            let x = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(g, "", x);
          }
        }));
      let m = p.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof o.first_author == "string" &&
          o.first_author &&
          m.createEl("span", {
            cls: "paperforge-search-result-author",
            text: o.first_author,
          }),
        typeof o.journal == "string" &&
          o.journal &&
          m.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: o.journal,
          }),
        o.score !== void 0)
      ) {
        let v = o.score,
          x = typeof v == "number" ? v.toFixed(3) : String(v);
        m.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + x,
        });
      }
      if (
        (typeof o.domain == "string" &&
          o.domain &&
          p.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: o.domain,
          }),
        typeof o.abstract == "string" && o.abstract)
      ) {
        let v = o.abstract;
        p.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: v.length > 200 ? v.slice(0, 200) + "..." : v,
        });
      }
      if (t && typeof o.text == "string" && o.text) {
        let v = o.text;
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
  async _runAction(e, t) {
    var m, v, x, w, y;
    if (e.disabled) {
      new M.Notice(
        `[i] ${e.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (e.id === "paperforge-ocr") {
      let b =
        (v = (m = this.app.plugins) == null ? void 0 : m.plugins) == null
          ? void 0
          : v.paperforge;
      if (typeof (b == null ? void 0 : b.requestOcrRun) == "function") {
        b.requestOcrRun();
        return;
      }
    }
    if (t.classList.contains("running")) return;
    t.addClass("running");
    let r = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let n = Array.isArray(e.args) ? [...e.args] : [];
    if (e.needsKey) {
      let b = this.app.workspace.getActiveFile(),
        k = null;
      if (b) {
        let S = this.app.metadataCache.getFileCache(b);
        if (
          (S && S.frontmatter && S.frontmatter.zotero_key
            ? (k = S.frontmatter.zotero_key)
            : (k = this._extractZoteroKeyFromPath(b.path)),
          k)
        )
          n = [...n, k];
        else if (S && S.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new M.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new M.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new M.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let s =
        (x = e.timeoutMs) != null
          ? x
          : e.needsFilter
            ? 6e4
            : e.needsKey
              ? 3e4
              : 6e5,
      a = this._resolvePython();
    if (!a) {
      (this._showMessage(
        "[!!] Runtime not available \u2014 open PaperForge Setup",
        "error"
      ),
        new M.Notice(
          "PaperForge runtime is not ready. Opening Setup\u2026",
          6e3
        ));
      let b = this.app.setting;
      (b == null || b.open(),
        (w = b == null ? void 0 : b.openTabById) == null ||
          w.call(b, "paperforge"),
        t.removeClass("running"));
      return;
    }
    let { path: o, args: c = [] } = a,
      p = await ue(null, e.commandId),
      _ = (y = Xe(e.id)) != null ? y : [],
      f = (0, be.spawn)(o, [...c, "-m", "paperforge", ..._, ...n], {
        cwd: r,
        timeout: s,
        env: p,
      }),
      u = [],
      h = Date.now(),
      g = setInterval(() => this._fetchStats(!0), 4e3);
    (f.stdout.on("data", (b) => {
      let k = b
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let S of k) {
        let E = S.trim();
        E &&
          (u.push(E),
          this._showMessage(
            u.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      f.stderr.on("data", (b) => {
        let k = b
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let S of k) {
          if (S.includes("\r") || S.includes("%") || S.includes("\u2588"))
            continue;
          let E = S.trim();
          E &&
            !E.match(/^\d+%|^\|/) &&
            (u.push(E),
            this._showMessage(
              u.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      f.on("close", (b) => {
        (clearInterval(g), t.removeClass("running"));
        let k = ((Date.now() - h) / 1e3).toFixed(1);
        if (b !== 0) {
          let S = u.slice(-3).join(" | ") || "exit code " + b;
          (e.commandId === "repair" || e.commandId === "ocr") && b === 1
            ? (this._showMessage("[WARN] " + S, "running"),
              new M.Notice("[WARN] " + e.commandId + " partial: " + S, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + S, "error"),
              new M.Notice("[!!] " + e.commandId + " failed: " + S, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let S = u.join(`
`);
          if (S.trim())
            try {
              (JSON.parse(S),
                navigator.clipboard
                  .writeText(S)
                  .then(() => {
                    let E = `${k}s \u2014 ${S.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + E, "ok"),
                      new M.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + S.length + " chars"
                      ));
                  })
                  .catch((E) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + E.message,
                      "error"
                    ),
                      new M.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (E) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new M.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    E.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new M.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let E =
              u.filter((P) => P.match(/updated \d+/)).pop() ||
              u[u.length - 1] ||
              "",
            C = `${k}s \u2014 ${E}`;
          (this._showMessage("[OK] " + e.title + ": " + C, "ok"),
            new M.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (P) {
            console.log("[PF] fetchStats error:", P);
          }
          (console.log("[PF] close cmd=" + e.commandId + " id=" + e.id),
            e.commandId === "sync" &&
              ot(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      f.on("error", (b) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + b.message, "error"),
          new M.Notice("[!!] Cannot start: " + b.message, 8e3));
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
          t.setText(i("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(i("version_panel_title")));
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
            s = r.filePath;
          (this._currentMode === n && this._currentFilePath === s) ||
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
    let t = e.app.workspace.getLeavesOfType(Ce);
    if (t.length > 0) {
      await e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: Ce, active: !0 }),
      await e.app.workspace.revealLeaf(r));
  }
};
Pe();
var zt = class extends q.Modal {
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
      let s = this.contentEl.createDiv({ cls: "pf-modal-actions" });
      (s
        .createEl("button", { text: "Cancel" })
        .addEventListener("click", () => this.close()),
        s
          .createEl("button", { text: "Migrate" })
          .addEventListener("click", () => {
            this.onConfirm().finally(() => this.close());
          }));
    }
  },
  ut = class extends q.Plugin {
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
      this._needsConfigMigration = !1;
    }
    getManagedRuntime() {
      return (
        this._managedRuntime || (this._managedRuntime = new Re()),
        this._managedRuntime
      );
    }
    _getPythonCommand() {
      let e = he(this.getManagedRuntime().readPointer());
      return e ? { path: e.command, args: [...e.args] } : null;
    }
    requestOcrRun(e = !1) {
      if (this.ocrProcessController.isRunning) {
        new q.Notice(i("ocr_already_running"));
        return;
      }
      let t = () => {
        var r;
        ((this._ocrProgress = { current: 0, total: 1, key: "" }),
          (r = this._settingTab) == null || r.display(),
          this.ocrProcessController
            .start("run", {
              callbacks: {
                onProgress: (n, s, a) => {
                  var o;
                  ((this._ocrProgress = { current: n, total: s, key: a }),
                    (o = this._settingTab) == null || o.display());
                },
                onNotice: (n) => new q.Notice(n, 8e3),
              },
            })
            .then((n) => {
              var a;
              if (n.ok) new q.Notice(i("ocr_run_complete"));
              else if (n.stopped) new q.Notice(i("ocr_stopped_notice"));
              else {
                let o = n.failedKeys.join(", ");
                new q.Notice(i("ocr_failed_notice") + (o ? ": " + o : ""), 8e3);
              }
              (a = this._settingTab) == null || a.display();
              let s = this.app.vault.adapter.basePath;
              this._autoSync(s);
            })
            .catch((n) => {
              var s;
              (new q.Notice(
                i("ocr_failed_notice") +
                  ": " +
                  (n.message || i("ocr_error_notice")),
                8e3
              ),
                (s = this._settingTab) == null || s.display());
            }));
      };
      if (e) {
        t();
        return;
      }
      new Fe(
        this.app,
        {
          title: i("ocr_run_confirm_title"),
          effectLabel: i("ocr_run_confirm_body"),
          confirmLabel: i("maintenance_confirm_ok"),
          cancelLabel: i("maintenance_confirm_cancel"),
        },
        t
      ).open();
    }
    async onload() {
      (await this.loadSettings(),
        await this.saveSettings(),
        or(this.app, this.settings.language),
        (this.ocrProcessController = new ct({
          vaultPath: this.app.vault.adapter.basePath,
          resolveCommand: () => this._getPythonCommand(),
          resolveEnv: async () => await ue(null, "ocr"),
          needsCredential: (t) => t === "run" || t === "redo",
        })),
        this.registerView(Ce, (t) => new $e(t)),
        this.registerView(Ae, (t) => new Ne(t, this)));
      try {
        (0, q.addIcon)(ze, tr);
      } catch (t) {}
      (this.addRibbonIcon(ze, "PaperForge Dashboard", () => $e.open(this)),
        this.addRibbonIcon("scan-text", "PaperForge OCR Workspace", () =>
          Ne.open(this)
        ),
        (this._settingTab = new lt(this.app, this)),
        this.addSettingTab(this._settingTab),
        this.addCommand({
          id: "paperforge-status-panel",
          name: i("guide_open"),
          callback: () => $e.open(this),
        }),
        this.addCommand({
          id: "paperforge-ocr-workspace",
          name: "Open OCR Workspace",
          callback: () => Ne.open(this),
        }));
      for (let t of ce)
        t.id !== "paperforge-ocr-redo" &&
          this.addCommand({
            id: t.id,
            name: t.title,
            callback: async () => {
              var _;
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
              let { path: s, args: a = [] } = n,
                o = Array.isArray(t.args) ? [...t.args] : [],
                c = await ue(null, t.commandId),
                p = (_ = Xe(t.id)) != null ? _ : [];
              (0, Vt.execFile)(
                s,
                [...a, "-m", "paperforge", ...p, ...o],
                { cwd: r, timeout: 3e5, env: c },
                (f, u, h) => {
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
                      u
                        .trim()
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
        (gr(e, this.settings)
          .then((t) => {
            t.state === "migration_required" &&
              (this._needsConfigMigration = !0);
          })
          .catch(() => {}),
        Ke(e, this.settings)
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
          let t = await Ft(e, !0, this.settings).catch((s) => null),
            r =
              t && (n = t.warnings) != null && n.length
                ? t.warnings.join(`
`)
                : "No conflicts; legacy path keys will move under vault_config.";
          new zt(this.app, r, async () => {
            var s, a, o, c, p, _, f, u;
            await Ft(e, !1, this.settings).catch((h) => {
              new q.Notice(`PaperForge: config migrate failed: ${String(h)}`);
            });
            try {
              let h = await Rt(e, this.settings),
                g = (E) => {
                  var C;
                  return (C = h.fields.find((P) => P.key === E)) == null
                    ? void 0
                    : C.value;
                },
                m = String((s = g("system_dir")) != null ? s : ""),
                v = String((a = g("resources_dir")) != null ? a : ""),
                x = String((o = g("literature_dir")) != null ? o : ""),
                w = String((c = g("base_dir")) != null ? c : ""),
                y = String((p = g("zotero_data_dir")) != null ? p : ""),
                b = String((_ = g("vector_db_api_base")) != null ? _ : ""),
                k = String((f = g("vector_db_api_model")) != null ? f : ""),
                S = String((u = g("agent_platform")) != null ? u : "");
              (m && (this.settings.system_dir = m),
                v && (this.settings.resources_dir = v),
                x && (this.settings.literature_dir = x),
                w && (this.settings.base_dir = w),
                y && (this.settings.zotero_data_dir = y),
                b && (this.settings.vector_db_api_base = b),
                k && (this.settings.vector_db_api_model = k),
                S && (this.settings.agent_platform = S),
                st({
                  system_dir: m || "System",
                  resources_dir: v || "Resources",
                  literature_dir: x || "Literature",
                  base_dir: w || "Bases",
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
          Ot() && this._autoSync(e);
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
      let r = Y();
      (0, Vt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "--vault", e, "sync", "--json"],
        { timeout: 12e4, encoding: "utf-8", cwd: e, windowsHide: !0, env: r },
        (n, s, a) => {
          ((this._autoSyncRunning = !1),
            (this._memoryStatusText = null),
            n ||
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              nt(s, {
                vaultPath: e,
                resolveCommand: (o) => this._getPythonCommand(),
              })));
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
      var e;
      (this._pollTimer && clearInterval(this._pollTimer),
        (e = this._embedController) == null || e.dispose(),
        (this._embedController = null),
        this.app.workspace.detachLeavesOfType(Ce));
    }
    async loadSettings() {
      var n, s, a, o, c, p, _, f, u, h;
      let e = (n = await this.loadData()) != null ? n : {};
      ((this.settings = Object.assign({}, Ve, e)),
        this.settings.features &&
          Ve.features &&
          (this.settings.features = Object.assign(
            {},
            Ve.features,
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
          let g = await Rt(r, this.settings),
            m = (P) => {
              var T;
              return (T = g.fields.find((D) => D.key === P)) == null
                ? void 0
                : T.value;
            },
            v = String((s = m("system_dir")) != null ? s : ""),
            x = String((a = m("resources_dir")) != null ? a : ""),
            w = String((o = m("literature_dir")) != null ? o : ""),
            y = String((c = m("base_dir")) != null ? c : ""),
            b = String((p = m("zotero_data_dir")) != null ? p : "");
          (v && (this.settings.system_dir = v),
            x && (this.settings.resources_dir = x),
            w && (this.settings.literature_dir = w),
            y && (this.settings.base_dir = y),
            b && (this.settings.zotero_data_dir = b));
          let k = String((_ = m("vector_db_api_base")) != null ? _ : ""),
            S = String((f = m("vector_db_api_model")) != null ? f : ""),
            E = String((u = m("agent_platform")) != null ? u : "");
          (k && (this.settings.vector_db_api_base = k),
            S && (this.settings.vector_db_api_model = S),
            E && (this.settings.agent_platform = E));
          let C = g.fields.find((P) => P.key === "agent_platform");
          ((this.agentPlatformChoices =
            (h = C == null ? void 0 : C.choices) != null ? h : []),
            st({
              system_dir: v || "System",
              resources_dir: x || "Resources",
              literature_dir: w || "Literature",
              base_dir: y || "Bases",
              _warning: null,
            }));
        } catch (g) {}
      if (this.settings.python_path && this.settings.python_path.trim()) {
        let g = this.settings.python_path.trim();
        this.settings._python_path_stale = !en.existsSync(g);
      }
    }
    async saveSettings() {
      let e = {};
      for (let t of Object.keys(Ve))
        t in this.settings && (e[t] = this.settings[t]);
      await this.saveData(e);
    }
    _checkReleaseNotes() {
      let e = this.manifest.version;
      if (this.settings.last_seen_version === e) return;
      let s = (Tt().versions || []).find((o) => o.version === e);
      class a extends q.Modal {
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
              for (let _ of this._entry.recommended_actions)
                p.createEl("p", {
                  text: `\u2022 ${_}`,
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
      (new a(this.app, s).open(),
        (this.settings.last_seen_version = e),
        this.saveSettings());
    }
  };
