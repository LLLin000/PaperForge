"use strict";
var xr = Object.create;
var We = Object.defineProperty;
var wr = Object.getOwnPropertyDescriptor;
var kr = Object.getOwnPropertyNames;
var Sr = Object.getPrototypeOf,
  Pr = Object.prototype.hasOwnProperty;
var Cr = (d, l) => () => (l || d((l = { exports: {} }).exports, l), l.exports),
  Rr = (d, l) => {
    for (var e in l) We(d, e, { get: l[e], enumerable: !0 });
  },
  Dt = (d, l, e, t) => {
    if ((l && typeof l == "object") || typeof l == "function")
      for (let r of kr(l))
        !Pr.call(d, r) &&
          r !== e &&
          We(d, r, {
            get: () => l[r],
            enumerable: !(t = wr(l, r)) || t.enumerable,
          });
    return d;
  };
var H = (d, l, e) => (
    (e = d != null ? xr(Sr(d)) : {}),
    Dt(
      l || !d || !d.__esModule
        ? We(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  Fr = (d) => Dt(We({}, "__esModule", { value: !0 }), d);
var ft = Cr((on, Or) => {
  Or.exports = {
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
var rn = {};
Rr(rn, { default: () => it });
module.exports = Fr(rn);
var U = require("obsidian"),
  q = H(require("fs")),
  Be = H(require("path")),
  Ie = require("child_process");
var ye = "paperforge-status",
  ke = "paperforge-ocr-workspace",
  Ne = "paperforge",
  Ot =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  re = [
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
  ],
  Ve = {
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
    _paddleocr_configured: !1,
    _vector_db_configured: !1,
    _setup_complete: !1,
  };
function Bt(d, l) {
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
function lt(d, l) {
  return d && { ...d, ...l };
}
var Ze = 2,
  Se = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  Dr = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  Tt = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  Tr = new Set(["unknown", "ok", "warning", "error"]),
  At = new Set(["idle", "running"]),
  Ar = new Set(["safe", "destructive", "irreversible"]);
function Lt(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let l = d;
  return !(
    typeof l.action_id != "string" ||
    !l.action_id ||
    typeof l.verb != "string" ||
    typeof l.label != "string" ||
    typeof l.availability != "string" ||
    typeof l.safety_class != "string" ||
    !Ar.has(l.safety_class) ||
    !Array.isArray(l.preservation_facts) ||
    !Array.isArray(l.replacement_facts) ||
    typeof l.interruptible != "boolean" ||
    typeof l.confirmation_required != "boolean" ||
    (l.confirmation_prompt !== null &&
      typeof l.confirmation_prompt != "string") ||
    typeof l.command != "string" ||
    typeof l.scope != "string" ||
    typeof l.scope_count != "number"
  );
}
function He(d) {
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
    command: "probe " + d,
    scope: d,
    scope_count: 1,
  };
}
function It() {
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
    command: "setup",
    scope: "installation",
    scope_count: 1,
  };
}
function ct(d, l) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== Ze ||
    typeof e.module != "string" ||
    !e.module ||
    !Se.includes(e.module) ||
    (l !== void 0 && e.module !== l) ||
    typeof e.capability_state != "string" ||
    !Tt.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !At.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !Dr.has(e.user_state) ||
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
    (r.primary !== null && !Lt(r.primary)) ||
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
        i = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof s.capability_state != "string" ||
        !Tt.has(s.capability_state) ||
        typeof s.severity != "string" ||
        !Tr.has(s.severity) ||
        typeof s.activity_state != "string" ||
        !At.has(s.activity_state) ||
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
        (s.action !== null && !Lt(s.action))
      )
        return !1;
    }
  }
  return !0;
}
function ne(d) {
  return {
    schema_version: Ze,
    module: d,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: d + ".no_probe", text: d + " has not been probed yet." },
    action: { primary: d === "maintenance" ? null : He(d) },
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
function pt(d) {
  return {
    schema_version: Ze,
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
    action: { primary: d === "maintenance" ? null : He(d) },
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
function Pe(d) {
  return {
    schema_version: Ze,
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
    action: { primary: d === "maintenance" ? null : He(d) },
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
function dt(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let l = new Date(d.updated_at).getTime();
  return isNaN(l) ? !0 : Date.now() - l > d.ttl_seconds * 1e3;
}
function Mt(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function Nt(d) {
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
function Vt(d, l) {
  let e = {};
  for (let t of l) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = ne(t);
      continue;
    }
    if (!ct(r, t)) {
      e[t] = Pe(t);
      continue;
    }
    if (dt(r)) {
      e[t] = pt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var ut = {
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
      ocr_stop_batch: "Stop OCR batch",
      runtime_not_available: "Environment unavailable",
      md_unavailable_module: "Not available yet",
      managed_runtime_status: "Runtime Status",
      managed_runtime_install: "Install Runtime",
      managed_runtime_repair: "Repair Runtime",
      managed_runtime_rollback: "Rollback",
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
      support_diagnostic_copied: "Support diagnostic copied.",
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
      cc_action_probe: "Check",
      cc_action_set_config: "Set Config",
      cc_action_update: "Update",
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
      ocr_ws_btn_update_selected: "Update selected",
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
      ocr_stop_batch: "\u505C\u6B62 OCR \u6279\u5904\u7406",
      runtime_not_available: "\u73AF\u5883\u4E0D\u53EF\u7528",
      md_unavailable_module: "\u6682\u4E0D\u53EF\u7528",
      managed_runtime_status: "\u8FD0\u884C\u65F6\u72B6\u6001",
      managed_runtime_install: "\u5B89\u88C5\u8FD0\u884C\u65F6",
      managed_runtime_repair: "\u4FEE\u590D\u8FD0\u884C\u65F6",
      managed_runtime_rollback: "\u56DE\u6EDA",
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
      cc_action_update: "\u66F4\u65B0",
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
      ocr_ws_btn_update_selected: "\u66F4\u65B0\u6240\u9009",
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
  _t = null;
function Lr(d) {
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
function Ht(d, l = "") {
  _t = (l || Lr(d)).startsWith("zh") ? ut.zh : ut.en;
}
function a(d) {
  return (_t && _t[d]) || ut.en[d] || d;
}
var F = require("obsidian"),
  z = H(require("fs")),
  J = H(require("path")),
  _r = H(require("os")),
  ee = require("child_process");
var fr = H(ft());
var Br = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  Ir = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function he(d, l, e) {
  return d.createEl("span", {
    cls: Br[l],
    text: e != null ? e : Ir[l],
    attr: { role: "status" },
  });
}
function zt(d, l) {
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
function $(d, l) {
  let e = d.createEl("button", {
    cls: "pf-action-btn",
    text: l.loading ? "\u2026" : l.label,
  });
  return (
    (l.disabled || l.loading) &&
      (e.setAttr("disabled", "true"),
      e.classList.add("pf-action-btn--disabled")),
    l.loading && e.classList.add("pf-action-btn--loading"),
    !l.disabled &&
      !l.loading &&
      (e.addEventListener("click", l.onClick),
      e.addEventListener("keydown", (t) => {
        (t.key === "Enter" || t.key === " ") &&
          (t.preventDefault(), l.onClick());
      })),
    e
  );
}
function jt(d, l) {
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
function $t(d, l) {
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
function Kt(d) {
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
function qt(d, l) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      l == null || l();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Ut(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function Wt(d, l) {
  return !d || l.user_state === "ready"
    ? !0
    : !(l.user_state === "detection_failed" || d.user_state === "ready");
}
function Zt(d, l) {
  var t, r, n, s, i, o, c;
  let e = [];
  for (let [p, u] of Object.entries(d)) {
    let f = l.get(p);
    e.push({
      module: p,
      userState: u.user_state,
      lastSuccessAt: (t = f == null ? void 0 : f.capturedAt) != null ? t : null,
      reasonCode: (r = u.reason) == null ? void 0 : r.code,
      actionId:
        (s = (n = u.action) == null ? void 0 : n.primary) == null
          ? void 0
          : s.action_id,
      errorExcerpt:
        (c =
          (o = (i = u.reason) == null ? void 0 : i.text) == null
            ? void 0
            : o.slice(0, 200)) != null
          ? c
          : void 0,
    });
  }
  return e;
}
var de = H(require("fs")),
  be = H(require("path")),
  tr = H(require("os")),
  Ce = require("child_process");
var Mr = ["paddleocr_api_key", "vector_db_api_key"],
  Nr = {
    paddleocr_api_key: "paddleocr-api-key",
    vector_db_api_key: "vector-db-api-key",
  },
  Jt = {
    paddleocr_api_key: "_paddleocr_configured",
    vector_db_api_key: "_vector_db_configured",
  },
  Vr = {
    ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
    memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
    embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  };
function Hr({ baseUrl: d, model: l }) {
  return `${d.trim()}\0${l.trim() || "text-embedding-3-small"}`;
}
async function Je(d) {
  let l = new TextEncoder().encode(Hr(d)),
    e = await crypto.subtle.digest("SHA-256", l);
  return `vector-db-api-key-v2-${[...new Uint8Array(e)]
    .map((r) => r.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 40)}`;
}
async function Gt(d, l, e) {
  if (!e) return !1;
  let t = await Je(l);
  try {
    return (
      await d.app.secretStorage.setSecret(t, e),
      (await d.app.secretStorage.getSecret(t)) === e
    );
  } catch (r) {
    return !1;
  }
}
async function ht(d, l) {
  return !!(await d.app.secretStorage.getSecret(await Je(l)));
}
async function Yt(d, l) {
  var f;
  let e = (f = d.app) == null ? void 0 : f.secretStorage;
  if (!e || typeof e.getSecret != "function")
    return { migrated: [], warnings: [] };
  let t = [],
    r = [],
    n = Array.isArray(l._migrated_keys) ? l._migrated_keys : [];
  for (let _ of Mr) {
    if (n.includes(_)) continue;
    let g = typeof l[_] == "string" ? l[_] : "";
    if (!g) continue;
    let h =
        _ === "vector_db_api_key"
          ? await Je({
              baseUrl:
                typeof l.vector_db_api_base == "string"
                  ? l.vector_db_api_base
                  : "",
              model:
                typeof l.vector_db_api_model == "string"
                  ? l.vector_db_api_model
                  : "",
            })
          : Nr[_] || _,
      b = await e.getSecret(h);
    if (b !== null) {
      if (b === g) {
        ((l[_] = ""), (l[Jt[_]] = !0), t.push(_));
        continue;
      }
      r.push(_);
      continue;
    }
    try {
      await e.setSecret(h, g);
    } catch (m) {
      r.push(_);
      continue;
    }
    if ((await e.getSecret(h)) !== g) {
      r.push(_);
      continue;
    }
    ((l[_] = ""), t.push(_), (l[Jt[_]] = !0));
  }
  let s = {
      baseUrl:
        typeof l.vector_db_api_base == "string" ? l.vector_db_api_base : "",
      model:
        typeof l.vector_db_api_model == "string" ? l.vector_db_api_model : "",
    },
    i = !1,
    o = await ht(d, s);
  l._vector_db_configured !== o && ((l._vector_db_configured = o), (i = !0));
  let c = Array.isArray(l._migration_warnings) ? l._migration_warnings : [],
    p = o
      ? [...c, ...r].filter((_) => _ !== "vector_db_api_key")
      : [...c, ...r],
    u = p.length !== c.length || p.some((_, g) => _ !== c[g]);
  if (t.length > 0 || r.length > 0 || i || u) {
    let _ = Array.isArray(l._migrated_keys) ? [...l._migrated_keys] : [];
    for (let g of t) _.includes(g) || _.push(g);
    ((l._migrated_keys = _), (l._migration_warnings = p), await d.saveData(l));
  }
  return { migrated: t, warnings: r };
}
function zr(d) {
  var e, t;
  let l = d.settings;
  if (l)
    return {
      baseUrl: (e = l.vector_db_api_base) != null ? e : "",
      model: (t = l.vector_db_api_model) != null ? t : "",
    };
}
async function Xt(d, l, e) {
  if (!Vr[l]) return {};
  let r = d.app.secretStorage,
    n = {};
  if (l === "ocr") {
    let s = await r.getSecret("paddleocr-api-key");
    s && ((n.PADDLEOCR_API_KEY = s), (n.PADDLEOCR_API_TOKEN = s));
  } else if (l === "memory" || l === "embed") {
    let s = e != null ? e : zr(d);
    if (!s) return n;
    let i = await r.getSecret(await Je(s));
    i && (n.VECTOR_DB_API_KEY = i);
  }
  return n;
}
var jr = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
function Qt(d) {
  let l = {};
  for (let [e, t] of Object.entries(d))
    jr.some((r) => e.startsWith(r)) || (l[e] = t);
  return l;
}
var gt = null,
  er = !1;
function mt(d) {
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
function rr() {
  if (er) return gt;
  er = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let l = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, Ce.execFileSync)(l, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      d = (0, Ce.execFileSync)("which", ["git"], {
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
      l && (gt = be.dirname(l));
    }
  } catch (d) {}
  return gt;
}
function ge() {
  let d = { ...process.env },
    l = process.platform,
    e = tr.homedir(),
    t = [],
    r = rr();
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
  return ((d.PATH = [...t, n].filter(Boolean).join(be.delimiter)), Qt(d));
}
async function ue(d, l, e) {
  let t = await Xt(d, l, e),
    r = ge();
  return Object.keys(t).length === 0 ? r : Object.assign({}, r, t);
}
function nr(d) {
  return String(d)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function yt(d) {
  if (!d) return !1;
  try {
    if (!de.existsSync(d)) return !1;
    for (let l of de.readdirSync(d)) if (nr(l)) return !0;
  } catch (l) {}
  return !1;
}
function Ge(d) {
  if (!d) return !1;
  try {
    if (!de.existsSync(d)) return !1;
    for (let l of de.readdirSync(d)) {
      let e = be.join(d, l, "extensions");
      try {
        if (!de.existsSync(e)) continue;
        for (let t of de.readdirSync(e)) if (nr(t)) return !0;
      } catch (t) {}
    }
  } catch (l) {}
  return !1;
}
var Fe = H(require("fs")),
  Z = H(require("path")),
  ar = require("child_process");
function $r(d, l) {
  let e = l || Fe,
    t = Z.join(d, "paperforge.json"),
    r = {
      system_dir: "System",
      resources_dir: "Resources",
      literature_dir: "Literature",
      base_dir: "Bases",
    };
  try {
    if (!e.existsSync(t))
      return { ...r, _warning: "paperforge.json not found; using defaults" };
    let n = e.readFileSync(t, "utf-8"),
      s = JSON.parse(n),
      i = s.vault_config || {};
    return {
      system_dir: i.system_dir || s.system_dir || r.system_dir,
      resources_dir: i.resources_dir || s.resources_dir || r.resources_dir,
      literature_dir: i.literature_dir || s.literature_dir || r.literature_dir,
      base_dir: i.base_dir || s.base_dir || r.base_dir,
      _warning: null,
    };
  } catch (n) {
    return (
      console.warn(
        "PaperForge: Failed to read paperforge.json, using defaults",
        n
      ),
      { ...r, _warning: "paperforge.json invalid; using defaults" }
    );
  }
}
function Q(d, l) {
  let e = $r(d, l),
    t = Z.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: Z.join(t, "indexes"),
    logsDir: Z.join(t, "logs"),
    dbPath: Z.join(t, "indexes", "paperforge.db"),
    memoryStatePath: Z.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: Z.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: Z.join(t, "indexes", "runtime-health.json"),
    buildStatePath: Z.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: Z.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: Z.join(t, "exports"),
    ocrDir: Z.join(t, "ocr"),
    pluginDataPath: Z.join(
      d,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: Z.join(d, "paperforge.json"),
    configWarning: e._warning,
  };
}
function bt(d) {
  try {
    return Fe.existsSync(d) ? JSON.parse(Fe.readFileSync(d, "utf-8")) : null;
  } catch (l) {
    return null;
  }
}
function Kr(d) {
  let l = Q(d);
  return bt(l.memoryStatePath);
}
var Re = null;
function Ye(d) {
  let l = Q(d),
    e = Date.now();
  if (Re && Re.vaultPath === d && e - Re.ts < 2e3) return Re.result;
  let t = "",
    r = [
      Z.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
      Z.join(d, ".venv", "Scripts", "python.exe"),
      Z.join(d, "venv", "Scripts", "python.exe"),
    ];
  for (let s = 0; s < r.length; s++)
    if (Fe.existsSync(r[s])) {
      t = r[s];
      break;
    }
  if (t)
    try {
      let s = (0, ar.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", d, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        i = JSON.parse(s);
      if (i.ok && i.data) {
        let o = i.data;
        return ((Re = { vaultPath: d, result: o, ts: e }), o);
      }
    } catch (s) {}
  let n = bt(l.vectorStatePath);
  return ((Re = { vaultPath: d, result: n, ts: e }), n);
}
function ze(d) {
  let l = Q(d);
  return bt(l.healthStatePath);
}
function sr(d) {
  var e;
  let l = ze(d);
  return !!(l && ((e = l.summary) == null ? void 0 : e.status) === "ok");
}
function vt(d) {
  let l = Kr(d);
  return !l || l.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + l.paper_count_db + " | " + (l.fresh ? "fresh" : "stale");
}
function De(d) {
  var t, r, n;
  let l = Ye(d);
  return l
    ? l.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = l.chunk_count) != null ? t : 0) +
          ((r = l.body_chunk_count) != null ? r : 0) +
          ((n = l.object_chunk_count) != null ? n : 0)) +
        " | " +
        l.model +
        " | " +
        l.mode
    : "Status unavailable";
}
var ie = require("obsidian"),
  Ee = H(require("fs")),
  Gr = H(require("path")),
  Yr = H(require("https")),
  wt = require("child_process");
var Et = H(require("fs")),
  N = H(require("path")),
  Qe = require("child_process"),
  lr = H(require("os")),
  ir = 300 * 1e3,
  qr = "3.11";
function Xe() {
  let d, l;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (l = r));
    }),
    resolve: d,
    reject: l,
  };
}
function Ur(d) {
  let l = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (l) return l[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function cr(d, l) {
  var r, n;
  let e = d.split(".").map(Number),
    t = l.split(".").map(Number);
  for (let s = 0; s < Math.max(e.length, t.length); s++) {
    let i = (r = e[s]) != null ? r : 0,
      o = (n = t[s]) != null ? n : 0;
    if (i !== o) return i - o;
  }
  return 0;
}
function Wr(d, l) {
  return cr(d, l) >= 0;
}
function Zr() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function Jr() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function or(d, l) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${l}`;
}
function _e(d) {
  return d.state !== "ready" || !d.pythonPath
    ? null
    : { command: d.pythonPath, args: [] };
}
var ve = class {
  constructor(l) {
    this._cache = null;
    this._cacheTime = 0;
    var r, n, s, i, o, c, p, u, f, _, g;
    let e =
        (n = (r = l.osPlatform) != null ? r : l.platform) != null
          ? n
          : process.platform,
      t = (i = (s = l.osArch) != null ? s : l.arch) != null ? i : process.arch;
    if (
      ((this.osPlatform = e),
      (this.osArch = t),
      (this.triplet = `${e}-${t}`),
      l.runtimeDir)
    )
      ((this.runtimeDir = l.runtimeDir),
        (this.rootDir = N.dirname(l.runtimeDir)),
        (this.pluginVersion =
          (c = (o = l.pluginVersion) != null ? o : l.version) != null
            ? c
            : "0.0.0"));
    else {
      let h = lr.homedir();
      ((this.rootDir = N.join(h, ".paperforge", "runtime")),
        (this.runtimeDir = N.join(this.rootDir, or(e, t))),
        (this.pluginVersion =
          (u = (p = l.version) != null ? p : l.pluginVersion) != null
            ? u
            : "0.0.0"));
    }
    ((this.pointerPath = N.join(this.rootDir, "active-runtime.json")),
      (this._fs = (f = l.fs) != null ? f : Et),
      (this._execFile = (_ = l.execFile) != null ? _ : Qe.execFile),
      (this._execFileSync =
        (g = l.execFileSync) != null ? g : Qe.execFileSync));
  }
  current() {
    return this._cache
      ? Date.now() - this._cacheTime > ir
        ? { ...this._cache, state: "unknown", stale: !0 }
        : { ...this._cache, stale: !1 }
      : {
          state: "unknown",
          pythonPath: null,
          version: null,
          source: "none",
          error: null,
          lastVerifiedAt: null,
          stale: !0,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
        };
  }
  async status(l) {
    var i;
    if (this._cache) {
      let o = Date.now() - this._cacheTime > ir;
      if (!o && this._cache.state === "ready")
        return { ...this._cache, stale: !1 };
      if (o && l != null && l.allowStale) return { ...this._cache, stale: !0 };
    }
    let e = null,
      t = null,
      r = null,
      n = null,
      s = [];
    try {
      let o = this._fs.readFileSync(this.pointerPath, "utf-8"),
        c = JSON.parse(o);
      e = typeof c.version == "string" ? c.version : null;
      let p = typeof c.pythonPath == "string" ? c.pythonPath : null;
      ((t = p ? N.resolve(N.dirname(this.pointerPath), p) : null),
        (r = typeof c.previousVersion == "string" ? c.previousVersion : null),
        (n =
          typeof c.previousPythonPath == "string"
            ? c.previousPythonPath
            : null),
        (s = Array.isArray(c.warnings) ? c.warnings : []));
    } catch (o) {
      return this._setCache({
        state: "not_installed",
        pythonPath: null,
        version: null,
        source: "none",
        error: null,
        lastVerifiedAt: null,
        stale: !1,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    }
    if (!t)
      return this._setCache({
        state: "needs_repair",
        pythonPath: null,
        version: e,
        source: "none",
        error: {
          code: "POINTER_MISSING_PATH",
          message: "Active runtime pointer has no pythonPath",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    if (!this._fs.existsSync(t))
      return this._setCache({
        state: "needs_repair",
        pythonPath: t,
        version: e,
        source: "none",
        error: {
          code: "PYTHON_NOT_FOUND",
          message: "Python executable not found at pointer path",
          platformAction: "Reinstall runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    try {
      let o = await this._probe(t),
        c = [...s];
      return this._setCache({
        state: "ready",
        pythonPath: t,
        version: (i = o.version) != null ? i : e,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: !1,
        warnings: c,
        previousVersion: r,
        previousPythonPath: n,
      });
    } catch (o) {
      let c = o instanceof Error ? o.message : String(o);
      return this._setCache({
        state: "needs_repair",
        pythonPath: t,
        version: e,
        source: "venv",
        error: {
          code: "PROBE_FAILED",
          message: c,
          platformAction: "Repair runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    }
  }
  async ensure(l) {
    var b, v;
    let e =
        (b = l == null ? void 0 : l.version) != null ? b : this.pluginVersion,
      t = (v = l == null ? void 0 : l.force) != null ? v : !1,
      r = l == null ? void 0 : l.signal;
    if (r != null && r.aborted) return this._abortedHealth();
    if (!t) {
      let m = this.current();
      if (m.state === "ready" && !m.stale) {
        let E = await this.status();
        if (E.state === "ready") return E;
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let n;
    try {
      n = this._resolveBootstrapPython();
    } catch (m) {
      if (Zr() || Jr())
        return this._setCache({
          state: "unavailable",
          pythonPath: null,
          version: null,
          source: "none",
          error: {
            code: "FLATPAK_SNAP_UNSUPPORTED",
            message:
              "Flatpak and Snap are not supported. Install Python 3.11+ natively.",
            platformAction:
              "Install Python 3.11+ from python.org or package manager",
          },
          lastVerifiedAt: null,
          stale: !1,
          warnings: [],
          previousVersion: null,
          previousPythonPath: null,
        });
      let E = or(this.osPlatform, this.osArch),
        w = this.osPlatform === "darwin",
        y = ["macos-x64", "macos-arm64"],
        x = ["windows-x64", "linux-x64"];
      return w && y.includes(E)
        ? this._setCache({
            state: "unavailable",
            pythonPath: null,
            version: null,
            source: "none",
            error: {
              code: "NO_PYTHON",
              message:
                "No Python 3.11+ found. macOS auto-download disabled until signed/notarized artifacts exist.",
              platformAction:
                "Install Python 3.11+ from python.org or Homebrew",
            },
            lastVerifiedAt: null,
            stale: !1,
            warnings: [],
            previousVersion: null,
            previousPythonPath: null,
          })
        : x.includes(E)
          ? this._setCache({
              state: "unavailable",
              pythonPath: null,
              version: null,
              source: "none",
              error: {
                code: "NO_PYTHON",
                message: "No Python 3.11+ found and automatic download failed.",
                platformAction: "Install Python 3.11+ manually",
              },
              lastVerifiedAt: null,
              stale: !1,
              warnings: [],
              previousVersion: null,
              previousPythonPath: null,
            })
          : this._setCache({
              state: "unavailable",
              pythonPath: null,
              version: null,
              source: "none",
              error: {
                code: "FALLBACK_UNAVAILABLE",
                message:
                  "No Python found and this platform has no validated fallback.",
                platformAction: "Install Python 3.11+ manually from python.org",
              },
              lastVerifiedAt: null,
              stale: !1,
              warnings: [],
              previousVersion: null,
              previousPythonPath: null,
            });
    }
    if (r != null && r.aborted) return this._abortedHealth();
    if (!Wr(n.version, qr))
      return this._setCache({
        state: "unavailable",
        pythonPath: null,
        version: n.version,
        source: "none",
        error: {
          code: "PYTHON_TOO_OLD",
          message: `Python ${n.version} is too old. Python 3.11+ required.`,
          platformAction: "Install Python 3.11+",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: [],
        previousVersion: null,
        previousPythonPath: null,
      });
    if (this._currentSlotExists(e) && !t) {
      let m = !1;
      try {
        let E = this._fs.readFileSync(this.pointerPath, "utf-8"),
          w = JSON.parse(E),
          y = typeof w.version == "string" ? w.version : null;
        m = y !== null && y !== e;
      } catch (E) {}
      if (m) {
        let E = N.join(this.runtimeDir, `v${e}`),
          w = N.join(E, "venv"),
          y =
            this.osPlatform === "win32"
              ? N.join(w, "Scripts", "python.exe")
              : N.join(w, "bin", "python");
        try {
          await this._probe(y, r);
        } catch (R) {
          if (R instanceof Error && R.name === "AbortError")
            return this._abortedHealth();
          let D = R instanceof Error ? R.message : String(R);
          return this._setCache({
            state: "needs_repair",
            pythonPath: y,
            version: e,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${e} failed verification: ${D}`,
              platformAction: "Repair runtime",
            },
            lastVerifiedAt: null,
            stale: !1,
            warnings: [],
            previousVersion: null,
            previousPythonPath: null,
          });
        }
        let x = null,
          k = null;
        try {
          let R = this._fs.readFileSync(this.pointerPath, "utf-8"),
            D = JSON.parse(R);
          ((x = typeof D.version == "string" ? D.version : null),
            (k = typeof D.pythonPath == "string" ? D.pythonPath : null));
        } catch (R) {}
        let S = N.dirname(this.pointerPath);
        this._fs.existsSync(S) || this._fs.mkdirSync(S, { recursive: !0 });
        let C = N.relative(N.dirname(this.pointerPath), y),
          O = JSON.stringify(
            {
              schema_version: 1,
              version: e,
              pythonPath: C,
              activatedAt: new Date().toISOString(),
              previousVersion: x,
              previousPythonPath: k,
            },
            null,
            2
          ),
          A = this.pointerPath + ".tmp";
        (this._fs.writeFileSync(A, O, "utf-8"),
          this._fs.renameSync(A, this.pointerPath));
        let L = {
          state: "ready",
          pythonPath: y,
          version: e,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: !1,
          warnings: [],
          previousVersion: x,
          previousPythonPath: k,
        };
        return (
          (this._cache = L),
          (this._cacheTime = Date.now()),
          this._cleanupOldSlots(e),
          L
        );
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let s = t
        ? N.join(this.runtimeDir, `v${e}_build2`)
        : N.join(this.runtimeDir, `v${e}`),
      i = N.join(s, "venv"),
      o =
        this.osPlatform === "win32"
          ? N.join(i, "Scripts", "python.exe")
          : N.join(i, "bin", "python");
    try {
      this._fs.mkdirSync(s, { recursive: !0 });
      let { promise: m, reject: E, resolve: w } = Xe();
      (this._execFile(
        n.path,
        ["-m", "venv", i],
        { timeout: 6e4, signal: r },
        (y) => {
          y ? E(y) : w();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VENV_CREATION_FAILED", m, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: E, resolve: w } = Xe();
      (this._execFile(
        o,
        ["-m", "pip", "install", `paperforge==${e}`],
        { timeout: 12e4, signal: r },
        (y) => {
          y ? E(y) : w();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "PIP_INSTALL_FAILED", m, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: E, resolve: w } = Xe();
      (this._execFile(
        o,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: r },
        (y) => {
          y ? E(y) : w();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (E) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VERIFY_FAILED", m, s);
    }
    let c = null,
      p = null;
    try {
      let m = this._fs.readFileSync(this.pointerPath, "utf-8"),
        E = JSON.parse(m);
      ((c = typeof E.version == "string" ? E.version : null),
        (p = typeof E.pythonPath == "string" ? E.pythonPath : null));
    } catch (m) {}
    let u = N.dirname(this.pointerPath);
    this._fs.existsSync(u) || this._fs.mkdirSync(u, { recursive: !0 });
    let f = N.relative(N.dirname(this.pointerPath), o),
      _ = JSON.stringify(
        {
          schema_version: 1,
          version: e,
          pythonPath: f,
          activatedAt: new Date().toISOString(),
          previousVersion: c,
          previousPythonPath: p,
        },
        null,
        2
      ),
      g = this.pointerPath + ".tmp";
    (this._fs.writeFileSync(g, _, "utf-8"),
      this._fs.renameSync(g, this.pointerPath));
    let h = {
      state: "ready",
      pythonPath: o,
      version: e,
      source: "venv",
      error: null,
      lastVerifiedAt: new Date().toISOString(),
      stale: !1,
      warnings: [],
      previousVersion: c,
      previousPythonPath: p,
    };
    return (
      (this._cache = h),
      (this._cacheTime = Date.now()),
      this._cleanupOldSlots(e),
      h
    );
  }
  _setCache(l) {
    return ((this._cache = l), (this._cacheTime = Date.now()), l);
  }
  _abortedHealth() {
    return {
      state: "needs_repair",
      pythonPath: null,
      version: null,
      source: "none",
      error: {
        code: "ABORTED",
        message: "Operation was cancelled",
        platformAction: "Retry operation",
      },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    };
  }
  _slotFailed(l, e, t, r) {
    try {
      this._fs.rmSync(r, { recursive: !0, force: !0 });
    } catch (s) {}
    let n = t instanceof Error ? t.message : String(t);
    return this._setCache({
      state: "needs_repair",
      pythonPath: null,
      version: l,
      source: "none",
      error: { code: e, message: n, platformAction: "Retry installation" },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    });
  }
  _currentSlotExists(l) {
    let e = N.join(this.runtimeDir, `v${l}`);
    return this._fs.existsSync(e);
  }
  _resolveBootstrapPython() {
    let l = [];
    this.osPlatform === "win32"
      ? l.push(
          { path: "py", args: ["-3.11"] },
          { path: "py", args: ["-3.10"] },
          { path: "py", args: ["-3"] },
          { path: "python", args: [] }
        )
      : this.osPlatform === "darwin"
        ? l.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          )
        : l.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          );
    for (let e of l)
      try {
        let t = this._execFileSync(e.path, [...e.args, "--version"], {
            encoding: "utf-8",
            timeout: 5e3,
          }),
          r = Ur(t);
        if (r) return { path: e.path, version: r };
      } catch (t) {}
    throw new Error("No Python 3.11+ found on system");
  }
  _probe(l, e) {
    let { promise: t, resolve: r, reject: n } = Xe();
    return (
      this._execFile(
        l,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: e },
        (s, i) => {
          if (s) n(s);
          else {
            let o = (i != null ? i : "").trim() || null;
            r({ version: o });
          }
        }
      ),
      t
    );
  }
  _cleanupOldSlots(l, e = 2) {
    try {
      let r = this._fs
        .readdirSync(this.runtimeDir, { withFileTypes: !0 })
        .filter((n) => n.isDirectory() && n.name.startsWith("v"))
        .map((n) => {
          let s = n.name.replace(/^v/, "").replace(/_build\d+$/, "");
          return { name: n.name, version: s };
        })
        .filter((n) => n.version !== l)
        .sort((n, s) => cr(s.version, n.version));
      for (let n = e; n < r.length; n++)
        this._fs.rmSync(N.join(this.runtimeDir, r[n].name), {
          recursive: !0,
          force: !0,
        });
    } catch (t) {}
  }
};
var xt = class extends ie.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((s, i) => ({ ...s, _selected: !0, _idx: i }))),
      (this.vaultPath = r),
      (this.py = n));
  }
  _updateUI() {
    let e = this.orphans.filter((t) => t._selected);
    (this._countEl.setText(
      a("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? a("orphan_deselect_all")
          : a("orphan_select_all")
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
        text: a("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: a("orphan_desc") }),
      (this._rowEls = []));
    let t = e.createEl("div", { cls: "paperforge-orphan-list" });
    for (let n of this.orphans) {
      let s = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(s);
      let i = s.createEl("div", { cls: "paperforge-orphan-info" }),
        o = i.createEl("div", { cls: "paperforge-orphan-header" });
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
          i.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let p = [];
      (n.authors && p.push(n.authors),
        n.year && p.push(n.year),
        p.length > 0 &&
          i.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: p.join(" \xB7 "),
          }),
        i.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: a("orphan_explain"),
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
        let n = this.orphans.filter((i) => i._selected);
        if (n.length === 0) {
          new ie.Notice(a("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new ie.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let s = n.map((i) => i.key);
        (0, wt.execFile)(
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
          (i, o) => {
            if (i) {
              (new ie.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let c = JSON.parse(o),
                p = (c.data && c.data.deleted) || [];
              new ie.Notice("Deleted " + p.length + " orphan workspace(s)");
            } catch (c) {
              new ie.Notice("PaperForge: prune done");
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
function tt(d, l, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = Q(e).orphanStatePath;
    if (!Ee.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = Ee.readFileSync(r, "utf-8"),
      i = JSON.parse(n),
      o = { path: "python", extraArgs: [], source: "auto-detected" };
    (console.log("[PF] py.path:", o ? o.path : "null"),
      new xt(d, i, e, o).open(),
      Ee.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
function pr(d, l) {
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
var $e = class extends ie.Modal {
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
        text: "Effect: ",
      }),
        r.createEl("span", { text: this._config.effectLabel }));
      let n = e.createEl("div", { cls: "paperforge-confirm-actions" }),
        s = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            a("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (s.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              a("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (o) => pr(e, o)),
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
  Xr = [
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
function je(d) {
  let l = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of Xr) {
    let s = 0;
    ((e = e.replace(t, () => (s++, "[REDACTED]"))),
      s > 0 &&
        (l[n] || (l[n] = { label: r, class_: n, count: 0 }),
        (l[n].count += s)));
  }
  return { clean: e, redactions: Object.values(l) };
}
function dr(d, l, e, t) {
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
var et = class extends ie.Modal {
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
      let h = t.parentElement;
      if (h)
        for (let b of Array.from(h.children))
          b !== t &&
            !b.hasAttribute("inert") &&
            (b.setAttribute("inert", ""), this._inertedEls.push(b));
    }
    (e.createEl("h2", {
      text: a("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          a("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = je(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let s = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    s.createEl("label", { text: "Body" });
    let i = je(this._draft.body).clean;
    this._bodyTextarea = s.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: i,
    });
    let { redactions: o } = je(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      c = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = c.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (a("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = c.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (u.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (a("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      u.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (o.length > 0
            ? " (" + o.map((h) => `${h.count} ${h.label}`).join(", ") + ")"
            : ""),
      }));
    let f = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (f
      .createEl("button", { text: a("maintenance_confirm_cancel") || "Cancel" })
      .addEventListener("click", () => this.close()),
      f
        .createEl("button", {
          cls: "mod-cta",
          text: a("maintenance_issue_draft_open_github") || "Open GitHub Issue",
        })
        .addEventListener("click", () => {
          let h = encodeURIComponent(je(this._titleInput.value).clean),
            b = encodeURIComponent(je(this._bodyTextarea.value).clean),
            v = encodeURIComponent(this._draft.labels.join(",")),
            m = `${this._githubUrl}?title=${h}&body=${b}&labels=${v}`;
          window.open(m, "_blank", "noopener,noreferrer");
        }),
      (this._boundKeydown = (h) => pr(e, h)),
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
function kt(d, l, e) {
  return !d ||
    typeof d != "object" ||
    !Object.prototype.hasOwnProperty.call(d, l)
    ? !!e
    : !!d[l];
}
function ur(d, l, e) {
  let t = !kt(d, l, e);
  return (d && typeof d == "object" && (d[l] = t), t);
}
var Qr = ["EMBED", "OCR_REBUILD", "OCR_REDO", "OCR_RUN"];
function rt(d, l) {
  var s, i;
  let t = (l + d).split(`
`),
    r = (s = t.pop()) != null ? s : "",
    n = [];
  for (let o of t)
    for (let c of Qr) {
      let p = c.length;
      if (o.startsWith(c + "_START:")) {
        let u = parseInt(o.slice(p + 7), 10) || 0;
        n.push({ prefix: c, event: "START", total: u });
        break;
      }
      if (o.startsWith(c + "_PROGRESS:")) {
        let f = o.slice(p + 10).split(":");
        n.push({
          prefix: c,
          event: "PROGRESS",
          current: parseInt(f[0], 10) || 0,
          total: parseInt(f[1], 10) || 0,
          key: (i = f[2]) != null ? i : "",
        });
        break;
      }
      if (o === c + "_DONE" || o.startsWith(c + "_DONE:")) {
        n.push({ prefix: c, event: "DONE" });
        break;
      }
    }
  return { events: n, buffer: r };
}
function Ke(d) {
  return { app: { secretStorage: d.secretStorage }, saveData: async () => {} };
}
function nt(d) {
  return { baseUrl: d.vector_db_api_base, model: d.vector_db_api_model };
}
var Te = class Te extends F.PluginSettingTab {
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
      { id: "installation", label: a("cc_module_foundation") || "Foundation" },
      { id: "library", label: a("cc_module_library") || "Library" },
      { id: "ocr", label: a("cc_module_ocr") || "OCR" },
      { id: "memory", label: a("cc_module_memory") || "Smart Retrieval" },
      { id: "agent", label: a("cc_module_agent") || "Agent Integration" },
    ];
  }
  _getUserModuleName(e) {
    let t =
      "cc_module_" +
      (e === "installation" ? "foundation" : e === "memory" ? "memory" : e);
    return a(t) || e.charAt(0).toUpperCase() + e.slice(1);
  }
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }
  display() {
    var u, f;
    this._displayInProgress = !0;
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      this._restoreNavMemory(),
      this._initCapabilityState(),
      this._applyStaleTolerance(),
      this.plugin.settings._setup_complete === !1)
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
            `),
        document.head.appendChild(_));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let _ = e.createDiv({ cls: "paperforge-migration-warning" }),
        g = t
          .map((h) => (h === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (_.createEl("strong", { text: a("migration_banner_title") }),
        _.createEl("p", {
          text: a("migration_banner_body").replace("{modules}", g),
        }),
        _.createEl("p", {
          text: a("migration_banner_next"),
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
    let s = r.createDiv({ cls: "pf-cc-topbar-center" }),
      i = [
        { id: "overview", label: a("tab_overview") || "Overview" },
        { id: "help", label: a("tab_help") || "Help" },
      ],
      o = {};
    if (
      (i.forEach((_) => {
        s.createEl("button", {
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
          text: (a("md_ocr_workspace") || "OCR Workspace") + " \u2197",
          attr: { href: "#", role: "button" },
        })
        .addEventListener("click", (_) => {
          (_.preventDefault(),
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }));
        }),
      i.forEach((_) => {
        o[_.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (_.id === this.activeTab ? " paperforge-tab-content--active" : ""),
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
      let _ = e.querySelector(this._focusTargetId);
      if (
        (!_ &&
          this.activeTab === "overview" &&
          (_ = e.querySelector(".pf-cc-module-card")),
        _)
      ) {
        try {
          _.focus();
        } catch (g) {}
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
  _runSetupPython(e) {
    var r;
    let t = (0, ee.spawn)(
      ((r = this.plugin.settings.python_path) == null ? void 0 : r.trim()) ||
        "python",
      e,
      { cwd: this._getVaultBasePath(), env: ge(), windowsHide: !0 }
    );
    return new Promise((n, s) => {
      var o;
      let i = "";
      ((o = t.stderr) == null ||
        o.on("data", (c) => {
          i += c.toString("utf-8");
        }),
        t.once("error", s),
        t.once("close", (c) => {
          c === 0 ? n() : s(new Error(i || `exit code ${c}`));
        }));
    });
  }
  _installFoundation(e) {
    if (this._setupOperation === "running") return;
    ((this._setupOperation = "running"),
      (this._setupFeedback = null),
      this.display());
    let t = async () => {
      let r = ["-m", "pip", "install", "--upgrade"];
      process.platform !== "win32" && r.push("--user");
      try {
        await this._runSetupPython([
          ...r,
          `paperforge==${this.plugin.manifest.version}`,
        ]);
      } catch (n) {
        await this._runSetupPython([
          ...r,
          `git+https://github.com/LLLin000/PaperForge.git@v${this.plugin.manifest.version}`,
        ]);
      }
    };
    (async () => {
      try {
        if (e) await t();
        else
          try {
            await this._runSetupPython(["-c", "import paperforge"]);
          } catch (r) {
            await t();
          }
        ((this._setupOperation = "idle"),
          (this._setupReinstallRequested = !1),
          (this._setupFeedback = a("setup_install_complete")),
          this._probeModule("installation"),
          this._probeModule("help"),
          this.display());
      } catch (r) {
        (console.error("PaperForge runtime installation failed:", r),
          (this._setupOperation = "failed"),
          (this._setupFeedback = a("setup_install_failed")),
          this.display());
      }
    })();
  }
  _applyLibraryConfiguration() {
    var n, s, i, o, c;
    if (this._setupOperation === "running") return;
    ((this._setupOperation = "running"), (this._setupFeedback = null));
    let e = this.plugin.settings,
      t = {
        zotero_data_dir: e.zotero_data_dir,
        system_dir: e.system_dir,
        resources_dir: e.resources_dir,
        literature_dir: e.literature_dir,
        base_dir: e.base_dir,
      };
    (this.plugin.savePaperforgeJson(t), this.display());
    let r = [
      "-m",
      "paperforge",
      "--vault",
      this._getVaultBasePath(),
      "setup",
      "--modular",
      "--system-dir",
      ((n = e.system_dir) == null ? void 0 : n.trim()) || "System",
      "--resources-dir",
      ((s = e.resources_dir) == null ? void 0 : s.trim()) || "Resources",
      "--literature-dir",
      ((i = e.literature_dir) == null ? void 0 : i.trim()) || "Literature",
      "--base-dir",
      ((o = e.base_dir) == null ? void 0 : o.trim()) || "Bases",
      "--agent",
      e.agent_platform || "opencode",
    ];
    ((c = e.zotero_data_dir) != null &&
      c.trim() &&
      r.push("--zotero-data", e.zotero_data_dir.trim()),
      (async () => {
        try {
          (await this.plugin.saveSettings(),
            await this._runSetupPython(r),
            (this._setupOperation = "idle"),
            (this._setupFeedback = a("setup_library_configured")),
            this._attemptedProbes.add("library"),
            this._probeModule("library"),
            this.display());
        } catch (p) {
          (console.error("PaperForge library configuration failed:", p),
            (this._setupOperation = "failed"),
            (this._setupFeedback = a("setup_library_config_failed")),
            this.display());
        }
      })());
  }
  _renderOverviewTab(e) {
    var r;
    let t = this._getVaultBasePath();
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      e.createEl("h2", { text: a("header_title") || "PaperForge" }),
      e.createEl("p", { text: a("desc"), cls: "paperforge-settings-desc" }),
      this._renderControlCenter(e));
    for (let n of Se) {
      let s = (r = this._capabilityState) == null ? void 0 : r[n];
      if (!s) continue;
      let i =
          s.capability_state === "unknown" &&
          s.updated_at === new Date(0).toISOString(),
        o =
          s.user_state === "detection_failed" &&
          s.reason.code.endsWith(".stale");
      (i || o) &&
        !this._attemptedProbes.has(n) &&
        (this._attemptedProbes.add(n),
        n !== "maintenance" && this._probeModule(n));
    }
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
            : new ve({ version: this.plugin.manifest.version })),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    var n;
    let t = (n = this.plugin.settings.python_path) == null ? void 0 : n.trim();
    if (t && z.existsSync(t)) return { path: t, args: [] };
    let r = _e(this._ensureManagedRuntime().current());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  _renderInstallationDetail(e) {
    var E, w;
    this._renderModuleDetailShell(e, "installation");
    let t =
        (w = (E = this._capabilityState) == null ? void 0 : E.installation) !=
        null
          ? w
          : ne("installation"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: a("md_foundation_overview") }),
      r.createEl("p", {
        text:
          t.user_state === "ready"
            ? a("md_foundation_ready")
            : this._getModuleConsequence("installation", t),
        cls:
          t.user_state === "ready"
            ? "pf-status-ok"
            : "setting-item-description",
      }));
    let n = r.createDiv({ cls: "pf-config" }),
      s = (y, x, k, S) => {
        let C = n.createDiv({ cls: "pf-config-row" });
        (C.createEl("span", { cls: "pf-config-key", text: y }),
          C.createEl("span", { cls: S, text: x }),
          C.createEl("span", { cls: "pf-config-value", text: k }));
      };
    s(
      a("foundation_version"),
      "\u2713",
      this.plugin.manifest.version,
      "pf-status-ok"
    );
    let i = this.plugin.settings.python_path || "python";
    s(a("foundation_python"), "\u2014", i, "pf-status-checking");
    let o = this.app.vault.adapter.basePath,
      c = J.join(o, this.plugin.settings.system_dir || "System"),
      p = z.existsSync(c);
    s(
      a("foundation_vault_structure"),
      p ? "\u2713" : "\u2717",
      p ? c : a("foundation_vault_missing"),
      p ? "pf-status-ok" : "pf-status-error"
    );
    let u =
      this.plugin.settings.zotero_data_dir &&
      z.existsSync(this.plugin.settings.zotero_data_dir);
    s(
      a("foundation_zotero"),
      u ? "\u2713" : "\u2717",
      u ? this.plugin.settings.zotero_data_dir : a("foundation_zotero_missing"),
      u ? "pf-status-ok" : "pf-status-error"
    );
    let f = !!this.plugin.settings.paddleocr_api_key,
      _ =
        !!this.plugin.settings.vector_db_api_key ||
        !!process.env.OPENAI_API_KEY;
    (s(
      a("foundation_paddle_key"),
      f ? "\u2713" : "\u2717",
      f ? a("config_configured") : a("foundation_paddle_missing"),
      f ? "pf-status-ok" : "pf-status-error"
    ),
      s(
        a("foundation_openai_key"),
        _ ? "\u2713" : "\u2717",
        _ ? a("config_configured") : a("foundation_openai_missing"),
        _ ? "pf-status-ok" : "pf-status-error"
      ));
    let { execSync: g } = require("child_process");
    try {
      (g("git --version", { timeout: 3e3 }),
        s(a("foundation_git"), "\u2713", a("check_bbt_ok"), "pf-status-ok"));
    } catch (y) {
      s(
        a("foundation_git"),
        "\u2717",
        a("foundation_git_missing"),
        "pf-status-error"
      );
    }
    let h = "1.11.4",
      b = "1.11.4",
      v = !0;
    (s(
      a("foundation_obsidian"),
      v ? "\u2713" : "\u2717",
      v ? `\u2265${h}` : a("foundation_obsidian_old"),
      v ? "pf-status-ok" : "pf-status-error"
    ),
      s(
        a("foundation_python_packages"),
        "\u2014",
        a("foundation_python_packages_checking"),
        "pf-status-checking"
      ));
    let { exec: m } = require("child_process");
    (m(`"${i}" --version`, { timeout: 5e3 }, (y) => {
      let x = n.children[1];
      if (x) {
        let k = x.querySelector(".pf-status-checking");
        k &&
          ((k.textContent = y ? "\u2717" : "\u2713"),
          (k.className = y ? "pf-status-error" : "pf-status-ok"));
      }
    }),
      m(
        `"${i}" -c "import paddleocr; import openai; import sqlite3; print('ok')"`,
        { timeout: 1e4 },
        (y) => {
          let x = n.children[n.children.length - 1];
          if (x) {
            let k = x.querySelector(".pf-status-checking");
            k &&
              ((k.textContent = y ? "\u2717" : "\u2713"),
              (k.className = y ? "pf-status-error" : "pf-status-ok"));
          }
        }
      ),
      t.user_state !== "ready" &&
        new F.Setting(r)
          .setName(a("foundation_setup"))
          .setDesc(a("foundation_setup_desc"))
          .addButton((y) =>
            y
              .setButtonText(a("foundation_setup_btn"))
              .setCta()
              .onClick(() => this._startSetupJourney(1))
          ),
      new F.Setting(r)
        .setName(a("foundation_reinstall"))
        .setDesc(a("foundation_reinstall_desc"))
        .addButton((y) =>
          y
            .setButtonText(a("foundation_reinstall_btn"))
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
    e.createEl("h3", { text: a("md_agent_skills") });
    let s = e.createEl("div", { cls: "paperforge-desc-box" });
    (s.setText(a("feat_skills_desc")),
      s.createEl("br"),
      s.createEl("span", { text: a("feat_skills_system") }));
    let i = J.join(r, t[n]),
      o = [],
      c = [];
    z.existsSync(i) &&
      z.readdirSync(i, { withFileTypes: !0 }).forEach((f) => {
        if (!f.isDirectory()) return;
        let _ = J.join(i, f.name, "SKILL.md");
        if (!z.existsSync(_)) return;
        let g = z.readFileSync(_, "utf-8"),
          h = g.match(/^name:\s*(.+)$/m),
          b = g.split(`
`),
          v = b.findIndex((k) => /^description:/.test(k)),
          m = "";
        if (v >= 0) {
          let k = b[v].match(/^description:\s*(.+)$/);
          if (k && k[1] && k[1] !== ">" && k[1] !== "|-" && k[1] !== "|")
            m = k[1].trim();
          else {
            for (
              let S = v + 1;
              S < b.length && (/^\s{2,}/.test(b[S]) || b[S].trim() === "");
              S++
            )
              m += b[S].trim() + " ";
            m = m.trim();
          }
        }
        let E = g.match(/^source:\s*(.+)$/m),
          w = g.match(/^disable-model-invocation:\s*(.+)$/m),
          y = g.match(/^version:\s*(.+)$/m),
          x = {
            name: h ? h[1].trim() : f.name,
            desc: m,
            source: E ? E[1].trim() : "user",
            disabled: !!w && w[1].trim() === "true",
            version: y ? y[1].trim() : "",
            path: _,
            content: g,
            dirName: f.name,
          };
        x.source === "paperforge" ? o.push(x) : c.push(x);
      });
    let p = e.createEl("div", { cls: "paperforge-skills-box" }),
      u = (f, _, g) => {
        if (_.length === 0) return;
        let h = p.createEl("div", { cls: "paperforge-skills-group" }),
          b = h.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          v = h.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          m = b.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (b.createEl("h4", {
          text: `${f} (${_.length})`,
          cls: "paperforge-skills-subheader",
        }),
          _.forEach((y) => {
            let x = y.name + (y.version ? " v" + y.version : ""),
              k = g
                ? " [" + a("skills_system") + "]"
                : " [" + a("skills_user") + "]",
              S = y.desc || "",
              C = new F.Setting(v).setName(x + k).setDesc(S);
            ((C.settingEl.style.opacity = y.disabled ? "0.4" : "1"),
              C.addToggle((O) => {
                O.setValue(!y.disabled).onChange((A) => {
                  let L = !A,
                    D = y.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? y.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${L}`
                        )
                      : y.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${L}
`
                        );
                  (z.writeFileSync(y.path, D, "utf-8"),
                    (y.disabled = L),
                    (y.content = D),
                    (C.settingEl.style.opacity = y.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let E = g ? "system" : "user";
        ((this._skillsCollapsed[E] || !1) &&
          ((v.style.display = "none"), (m.style.transform = "rotate(-90deg)")),
          b.addEventListener("click", () => {
            (v.style.display !== "none"
              ? ((v.style.display = "none"),
                (m.style.transform = "rotate(-90deg)"))
              : ((v.style.display = ""), (m.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[E] = v.style.display === "none"));
          }));
      };
    (u(a("skills_system"), o, !0),
      u(a("skills_user"), c, !1),
      o.length === 0 &&
        c.length === 0 &&
        p.createEl("p", {
          text: a("skills_empty"),
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
          : ne("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: a("md_library_connection") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: a("md_library_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          jt(r, {
            whatHappened:
              a("cc_module_library") +
              " \u2014 " +
              this._getUserStateLabel(t.user_state),
            impact: a("library_problem_impact"),
            nextStep: a("problem_use_action"),
            impactLabel: a("problem_impact"),
            nextLabel: a("problem_next"),
            copyLabel: a("problem_copy"),
            onCopyDiagnostic: () => this._buildAndCopyDiagnostic(),
          }));
    let n = r.createDiv({ cls: "pf-module-facts" }),
      s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: a("md_library_corpus") }),
      s.createEl("span", { text: a("metric_after_sync") }));
    let i = n.createDiv({ cls: "pf-module-fact" });
    (i.createEl("span", { text: a("md_library_last_sync") }),
      i.createEl("span", {
        text: this.plugin._lastSyncTime || a("metric_not_available"),
      }),
      r.createEl("h3", { text: a("md_configuration") }),
      $t(r, {
        items: [
          {
            label: a("config_zotero_dir"),
            value:
              this.plugin.settings.zotero_data_dir ||
              a("config_not_configured"),
          },
        ],
        configuredLabel: a("config_configured"),
        notConfiguredLabel: a("config_not_configured"),
        onChangeLabel: a("config_change"),
        onChange: () => this._startSetupJourney(2),
      }));
  }
  _renderOcrDetail(e) {
    var p, u, f, _, g, h, b, v, m, E, w, y, x, k;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (u = (p = this._capabilityState) == null ? void 0 : p.ocr) != null
          ? u
          : ne("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: a("md_ocr_status") }),
      t.user_state === "detection_failed" &&
        r.createEl("p", {
          cls: "pf-status-checking",
          text: a("md_status_refresh_hint"),
        }));
    let n = t.pipeline_version,
      s = t.last_pipeline_version,
      o =
        ((_ = (f = t.pipeline_version_summary) == null ? void 0 : f.stale) !=
        null
          ? _
          : 0) > 0;
    if (t.activity_state === "running") {
      he(r, "checking", a("ocr_state_running"));
      let S = this.plugin._ocrProgress,
        C = r.createDiv({ cls: "pf-ocr-progress-card" });
      if (S != null && S.total) {
        let A = a("ocr_progress")
            .replace("{current}", String(S.current))
            .replace("{total}", String(S.total)),
          L = S.key ? " \u2014 " + S.key : "";
        C.createEl("span", {
          cls: "pf-detail-progress",
          text: a("ocr_state_running") + " " + A + L,
        });
        let R = C.createDiv({ cls: "pf-activity-bar" }),
          D = Math.round((S.current / S.total) * 100);
        R.createDiv({
          cls: "pf-activity-bar-fill",
          attr: {
            style: `width: ${D}%`,
            role: "progressbar",
            "aria-valuenow": String(S.current),
            "aria-valuemin": "1",
            "aria-valuemax": String(S.total),
          },
        });
      }
      let O = this.plugin._ocrProcess;
      O &&
        C.createEl("button", {
          cls: "pf-action-btn mod-warning",
          text: a("ocr_stop_batch"),
        }).addEventListener("click", () => {
          var L, R;
          (L = O.stdin) != null && L.write
            ? (O.stdin.write(`PAPERFORGE_STOP
`),
              (this.plugin._ocrWasStopped = !0))
            : (R = O.kill) == null || R.call(O, "SIGINT");
        });
    } else if (o) {
      let S = n
        ? a("ocr_state_update_available").replace("{version}", n)
        : a("ocr_state_update_available").replace("{version}", "");
      (he(r, "action_required", S),
        r.createEl("p", {
          text: a("ocr_state_update_description"),
          cls: "setting-item-description",
        }),
        r.createEl("p", {
          text: a("ocr_state_update_safety"),
          cls: "setting-item-description",
        }),
        r
          .createEl("button", {
            cls: "pf-action-btn mod-warning",
            text: a("ocr_action_re_extract"),
          })
          .addEventListener("click", () => {
            new $e(
              this.app,
              {
                title: a("ocr_modal_title"),
                effectLabel:
                  a("ocr_modal_description") +
                  " " +
                  a("ocr_state_update_safety"),
                confirmLabel: a("ocr_action_re_extract"),
                cancelLabel: a("maintenance_confirm_cancel"),
              },
              () => this._dispatchOcrAction("rebuild")
            ).open();
          }));
    } else if (t.user_state === "ready") {
      he(r, "ready", a("cc_state_ready"));
      let S = n
        ? a("ocr_state_ready")
            .replace(
              "{count}",
              String(
                (m =
                  (v =
                    (h = (g = t.action) == null ? void 0 : g.primary) == null
                      ? void 0
                      : h.scope_count) != null
                    ? v
                    : (b = t.pipeline_version_summary) == null
                      ? void 0
                      : b.total) != null
                  ? m
                  : ""
              )
            )
            .replace("{version}", n)
        : a("ocr_state_ready_no_version").replace(
            "{count}",
            String(
              (k =
                (x =
                  (w = (E = t.action) == null ? void 0 : E.primary) == null
                    ? void 0
                    : w.scope_count) != null
                  ? x
                  : (y = t.pipeline_version_summary) == null
                    ? void 0
                    : y.total) != null
                ? k
                : ""
            )
          );
      (r.createEl("p", { text: S, cls: "pf-status-ok" }),
        $(r, {
          label: a("md_ocr_workspace"),
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
              text: a("ocr_state_update_available").replace("{version}", n),
            }));
    }
  }
  _renderAgentDetail(e) {
    var _;
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
      i = J.join(this._getVaultBasePath(), n[s]),
      o = z.existsSync(i),
      c = t.createDiv({ cls: "pf-module-facts" }),
      p = c.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: a("md_agent_platform") }),
      p.createEl("span", { text: (_ = r[s]) != null ? _ : s }));
    let u = c.createDiv({ cls: "pf-module-fact" });
    (u.createEl("span", { text: a("md_agent_deployment") }),
      u.createEl("span", {
        text: o ? a("agent_deployed") : a("agent_not_deployed"),
      }));
    let f = c.createDiv({ cls: "pf-module-fact" });
    if (
      (f.createEl("span", { text: a("agent_live_connection") }),
      f.createEl("span", { text: a("md_agent_connection_unknown") }),
      this._agentPlatformDraft === null)
    )
      $(t, {
        label: a("config_change"),
        onClick: () => {
          ((this._agentPlatformDraft = s), this.display());
        },
      });
    else {
      let g = t.createDiv({ cls: "pf-agent-config-editor" }),
        h = g.createEl("select", {
          attr: { "aria-label": a("md_agent_platform") },
        });
      for (let [v, m] of Object.entries(r)) {
        let E = h.createEl("option", { text: m, attr: { value: v } });
        E.selected = v === this._agentPlatformDraft;
      }
      h.addEventListener("change", () => {
        this._agentPlatformDraft = h.value;
      });
      let b = g.createDiv({ cls: "pf-agent-config-actions" });
      ($(b, {
        label: a("config_save"),
        onClick: () => {
          var m;
          let v = (m = this._agentPlatformDraft) != null ? m : s;
          ((this.plugin.settings.agent_platform = v),
            this.plugin.savePaperforgeJson({ agent_platform: v }),
            this.plugin.saveSettings(),
            (this._agentPlatformDraft = null),
            this.display());
        },
      }),
        $(b, {
          label: a("config_cancel"),
          onClick: () => {
            ((this._agentPlatformDraft = null), this.display());
          },
        }),
        $(b, {
          label: a("config_verify"),
          onClick: () => {
            var E;
            let v = (E = this._agentPlatformDraft) != null ? E : s,
              m = z.existsSync(J.join(this._getVaultBasePath(), n[v]));
            new F.Notice(
              m ? a("agent_verify_found") : a("agent_verify_missing")
            );
          },
        }));
    }
    this._renderSkillsList(t);
  }
  _renderMemoryDetail(e) {
    var R, D, P, V, Y, W, B;
    this._renderModuleDetailShell(e, "memory", !1);
    let t =
        (D = (R = this._capabilityState) == null ? void 0 : R.memory) != null
          ? D
          : ne("memory"),
      r = e.createDiv({ cls: "pf-module-body" }),
      n = (V = (P = t.reason) == null ? void 0 : P.code) != null ? V : "",
      s = t.activity_state === "running",
      i = null,
      o = "setting-item-description";
    if (
      (s && t.user_state === "ready"
        ? ((i = (Y = t.activity_label) != null ? Y : a("cc_activity_running")),
          (o = "pf-status-ok"))
        : n === "memory.disabled"
          ? (i = a("sr_state_disabled"))
          : n === "memory.db_missing"
            ? (i = a("sr_state_db_missing"))
            : n === "memory.backend_upgrade_available"
              ? (i = a("sr_state_upgrade_available"))
              : n === "memory.vector_build_failed"
                ? (i = a("sr_state_build_failed"))
                : n === "memory.schema_stale"
                  ? (i = t.reason.text)
                  : t.user_state === "ready" &&
                    ((i = a("md_retrieval_ready")), (o = "pf-status-ok")),
      i && r.createEl("p", { text: i, cls: o }),
      n === "memory.disabled")
    )
      $(r, {
        label: a("sr_action_enable") || "Enable Smart Retrieval",
        onClick: () => {
          (this.plugin.settings.features ||
            (this.plugin.settings.features = {
              memory_layer: !0,
              vector_db: !1,
            }),
            (this.plugin.settings.features.vector_db = !0),
            this.plugin.saveSettings().then(() => this._probeModule("memory")));
        },
      });
    else if (n === "memory.db_missing" || n === "memory.index_stale")
      $(r, {
        label: a("sr_action_build") || "Build Index",
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (n === "memory.backend_upgrade_available")
      $(r, {
        label: a("sr_action_upgrade") || "Upgrade",
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    else if (n === "memory.vector_build_failed" || n === "memory.schema_stale")
      $(r, {
        label: a("cc_action_rebuild_derived") || "Rebuild Index",
        onClick: () => this._dispatchMemoryBuild("embed"),
      });
    else if (
      (W = t.action) != null &&
      W.primary &&
      t.user_state !== "ready" &&
      t.user_state !== "not_enabled"
    ) {
      let M =
          "action_" +
          ((B = t.action.primary.action_id) != null
            ? B
            : t.action.primary.verb
          ).replace(/[.-]/g, "_"),
        X =
          a(M) !== M
            ? a(M)
            : a("cc_action_" + t.action.primary.verb) !==
                "cc_action_" + t.action.primary.verb
              ? a("cc_action_" + t.action.primary.verb)
              : a("cc_action_probe");
      $(r, {
        label: X,
        onClick: () => this._dispatchModuleAction("memory", t),
      });
    }
    let c =
        t.user_state === "ready"
          ? a("sr_db_exists") || "Active"
          : a("sr_db_missing") || "Not built",
      p = "vec0",
      u = this.plugin.settings._vector_db_configured || !1,
      f = u
        ? a("api_key_set") || "Configured"
        : a("api_key_missing") || "Not configured",
      _ = r.createDiv({ cls: "pf-sr-info-card" }),
      g = [
        [a("sr_db_status") || "Database", c],
        [a("sr_backend") || "Backend", p],
        [a("sr_api_key") || "API Key", f],
      ];
    for (let [M, X] of g) {
      let le = _.createDiv({ cls: "pf-sr-info-row" });
      (le.createEl("span", { cls: "pf-sr-info-label", text: M }),
        le.createEl("span", { cls: "pf-sr-info-value", text: X }));
    }
    let h = !u,
      b = r.createDiv({ cls: "pf-sr-cfg" }),
      v = b.createDiv({ cls: "pf-sr-cfg-head" });
    v.createEl("span", {
      cls: "pf-sr-cfg-title",
      text: a("sr_config_label") || "\u914D\u7F6E",
    });
    let m = v.createEl("span", {
        cls: "pf-sr-cfg-icon",
        text: h ? "\u25BC" : "\u25B6",
      }),
      E = b.createDiv({ cls: "pf-sr-cfg-body" });
    ((E.style.display = h ? "" : "none"),
      v.addEventListener("click", () => {
        let M = E.style.display !== "none";
        ((E.style.display = M ? "none" : ""),
          (m.textContent = M ? "\u25B6" : "\u25BC"));
      }));
    let w = E.createDiv({ cls: "pf-sr-cfg-row" });
    w.createEl("label", {
      text: a("feat_openai_key") || "API Key",
      cls: "pf-sr-cfg-lbl",
    });
    let y = w.createEl("input", {
        cls: "pf-sr-cfg-input",
        attr: {
          type: "password",
          placeholder: u ? "\u2022\u2022\u2022\u2022" : "sk-...",
        },
      }),
      x = null;
    y.addEventListener("input", () => {
      let M = y.value;
      M &&
        (x && clearTimeout(x),
        (x = setTimeout(async () => {
          ((await this._storeVectorDbCredential(M)) &&
            ((y.value = ""),
            (y.placeholder = "\u2022\u2022\u2022\u2022"),
            (E.style.display = "none"),
            (m.textContent = "\u25B6")),
            (x = null));
        }, 600)));
    });
    let k = E.createDiv({ cls: "pf-sr-cfg-row" });
    k.createEl("label", {
      text: a("feat_api_base_url") || "API Base URL",
      cls: "pf-sr-cfg-lbl",
    });
    let S = k.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "https://api.openai.com/v1" },
    });
    ((S.value = this.plugin.settings.vector_db_api_base || ""),
      S.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_base = S.value),
          this.plugin.saveSettings(),
          this._refreshVectorDbCredentialStatus());
      }));
    let C = E.createDiv({ cls: "pf-sr-cfg-row" });
    C.createEl("label", {
      text: a("feat_api_model") || "Model",
      cls: "pf-sr-cfg-lbl",
    });
    let O = C.createEl("input", {
      cls: "pf-sr-cfg-input",
      attr: { type: "text", placeholder: "text-embedding-3-small" },
    });
    if (
      ((O.value =
        this.plugin.settings.vector_db_api_model || "text-embedding-3-small"),
      O.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_model = O.value),
          this.plugin.saveSettings(),
          this._refreshVectorDbCredentialStatus());
      }),
      t.capability_state === "needs_action" && n !== "memory.disabled")
    ) {
      let M = r.createDiv({ cls: "pf-sr-impact-box" });
      (M.createEl("strong", {
        text: a("cc_badge_action_required") || "Action Required",
      }),
        M.createEl("p", {
          text:
            n === "memory.db_missing" || n === "memory.index_stale"
              ? a("sr_impact_db_missing") ||
                "Smart Retrieval needs an OpenAI API key and vector index. Click Build Index to get started."
              : n === "memory.backend_upgrade_available"
                ? a("sr_impact_upgrade") ||
                  "A new vector backend is available. Upgrade to improve search quality."
                : n === "memory.vector_build_failed"
                  ? a("sr_impact_build_failed") ||
                    "The last build failed. Check your API key and try again."
                  : a("sr_impact_schema_stale") ||
                    "The vector schema is outdated. Rebuild to match the current library.",
        }));
    }
    let A = r.createEl("details", { cls: "pf-sr-diagnostics" });
    (A.createEl("summary", {
      text: a("cc_diagnostic_toggle") || "Diagnostic Details",
    }),
      A.createDiv({ cls: "pf-sr-diagnostics-body" }).createEl("div", {
        text:
          "module: memory | state: " +
          t.capability_state +
          " | severity: " +
          t.severity +
          " | reason: " +
          n,
      }));
  }
  _dispatchModuleAction(e, t) {
    var i, o, c, p;
    let r = (i = t.action) == null ? void 0 : i.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    let n = r.verb,
      s = (o = r.command) != null ? o : "";
    if (r.safety_class !== "safe" && r.confirmation_required) {
      new $e(
        this.app,
        {
          title: r.label,
          effectLabel:
            (c =
              (r.replacement_facts || []).join("; ") ||
              r.confirmation_prompt) != null
              ? c
              : "Proceed?",
        },
        () => {
          var u;
          this._runAllowedDispatch(
            e,
            r.verb,
            (u = r.command) != null ? u : "",
            t
          );
        }
      ).open();
      return;
    }
    this._runAllowedDispatch(e, r.verb, (p = r.command) != null ? p : "", t);
  }
  _runAllowedDispatch(e, t, r, n) {
    var s, i, o;
    if ((t === "setup" || t === "set_config") && r === "paperforge setup") {
      if (e === "library") this._startSetupJourney(2);
      else {
        let c =
          e === "installation" &&
          n.reason.code === "installation.version_mismatch";
        this._startSetupJourney(e === "ocr" || e === "memory" ? 3 : 1, c);
      }
      return;
    }
    if (t === "probe" && r === "probe " + e) {
      this._probeModule(e);
      return;
    }
    if (e !== "installation") {
      if (e === "library") {
        if (t === "sync" && r === "paperforge sync") {
          this._runManualSync();
          return;
        }
      } else if (e === "ocr") {
        if (t === "run" && r === "paperforge ocr run") {
          this._dispatchOcrAction("run");
          return;
        }
        if (t === "rebuild_derived" && r === "paperforge ocr rebuild --all") {
          this._dispatchOcrAction("rebuild");
          return;
        }
        if (t === "redo" && r === "paperforge ocr redo") {
          this._dispatchOcrAction("redo");
          return;
        }
        if (t === "investigate") {
          if (r === "paperforge ocr issue-draft") {
            let c = this._getVaultBasePath(),
              p = dr(
                n.reason.code,
                n.reason.text,
                (o =
                  (i = (s = n.action) == null ? void 0 : s.primary) == null
                    ? void 0
                    : i.scope_count) != null
                  ? o
                  : 0,
                c
              );
            new et(
              this.app,
              p,
              "https://github.com/LLLin000/PaperForge/issues/new"
            ).open();
            return;
          }
          if (r === "paperforge ocr doctor") {
            this._callPython(["ocr", "doctor"], {
              timeout: 3e4,
              onClose: (c) => {
                (this._probeModule("ocr"), this.display());
              },
            });
            return;
          }
          if (r === "paperforge ocr list --json") {
            this._callPython(["ocr", "list", "--json"], {
              timeout: 3e4,
              onClose: (c) => {
                (this._probeModule("ocr"), this.display());
              },
            });
            return;
          }
        }
      } else if (e === "memory") {
        if (
          (t === "run" || t === "rebuild_index") &&
          r === "paperforge memory build"
        ) {
          this._dispatchMemoryBuild("build");
          return;
        }
        if (t === "rebuild_index" && r === "paperforge embed build --force") {
          this._dispatchMemoryBuild("embed");
          return;
        }
        if (
          t === "restore_backup" &&
          r === "paperforge memory restore-backup"
        ) {
          this._callPython(["memory", "restore-backup"], {
            timeout: 3e4,
            onClose: (c) => {
              (this._probeModule("memory"), this.display());
            },
          });
          return;
        }
      }
    }
    (new F.Notice(
      (a("action_unknown_pair") || "Unknown action: {verb}").replace(
        "{verb}",
        t
      ),
      5e3
    ),
      this._probeModule(e));
  }
  _dispatchOcrAction(e) {
    var c;
    let t = this.app.vault.adapter.basePath;
    if (!this._resolveRuntimeCommand(t)) {
      new F.Notice(a("runtime_not_available") || "No Python runtime available");
      return;
    }
    let n =
        e === "run"
          ? ["ocr", "run"]
          : e === "rebuild"
            ? ["ocr", "rebuild", "--all"]
            : ["ocr", "redo"],
      s = {
        run: "Running OCR\u2026",
        rebuild: "Rebuilding OCR derived artifacts\u2026",
        redo: "Running OCR redo\u2026",
      },
      i = (c = this._capabilityState) != null ? c : {};
    (i.ocr &&
      ((i.ocr.activity_state = "running"),
      (i.ocr.activity_label = s[e] || "Running\u2026"),
      (i.ocr.activity_progress = { current: 0, total: 1 })),
      (this.plugin._ocrBuffer = ""),
      (this.plugin._ocrProgress = { current: 0, total: 1, key: "" }),
      (this.plugin._ocrWasStopped = !1),
      this.display());
    let o = this._callPython(n, {
      stream: !0,
      onData: (p) => {
        var g;
        let u =
            typeof p == "string"
              ? p
              : Buffer.isBuffer(p)
                ? p.toString("utf-8")
                : String(p),
          { events: f, buffer: _ } = rt(
            u,
            (g = this.plugin._ocrBuffer) != null ? g : ""
          );
        this.plugin._ocrBuffer = _;
        for (let h of f)
          h.event === "START"
            ? (this.plugin._ocrProgress &&
                (this.plugin._ocrProgress.total = h.total || 1),
              i.ocr &&
                (i.ocr.activity_progress = { current: 0, total: h.total || 1 }))
            : h.event === "PROGRESS" &&
              ((this.plugin._ocrProgress = {
                current: h.current || 0,
                total: h.total || 1,
                key: h.key || "",
              }),
              i.ocr &&
                (i.ocr.activity_progress = {
                  current: h.current || 0,
                  total: h.total || 1,
                }));
        this.display();
      },
      onError: (p) => {
        ((this.plugin._ocrProcess = null),
          i.ocr &&
            ((i.ocr.activity_state = "idle"),
            (i.ocr.activity_label = null),
            (i.ocr.activity_progress = null)),
          new F.Notice(a("ocr_error_notice"), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
      onClose: (p) => {
        ((this.plugin._ocrProcess = null),
          i.ocr &&
            ((i.ocr.activity_state = "idle"),
            (i.ocr.activity_label = null),
            (i.ocr.activity_progress = null)),
          p === 0
            ? new F.Notice(
                e === "run"
                  ? a("ocr_run_complete")
                  : e === "rebuild"
                    ? a("ocr_rebuild_complete")
                    : a("ocr_redo_complete")
              )
            : p === 130 || this.plugin._ocrWasStopped
              ? ((this.plugin._ocrWasStopped = !1),
                new F.Notice(a("ocr_stopped_notice")))
              : new F.Notice(a("ocr_failed_notice"), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
    });
    this.plugin._ocrProcess = o;
  }
  _dispatchMemoryBuild(e) {
    var i;
    let t = this.app.vault.adapter.basePath,
      r = (i = this._capabilityState) != null ? i : {};
    (r.memory &&
      ((r.memory.activity_state = "running"),
      (r.memory.activity_label =
        e === "embed"
          ? "Building vector index\u2026"
          : "Building memory\u2026")),
      this.display());
    let n = e === "embed" ? ["embed", "build", "--force"] : ["memory", "build"],
      s = e === "embed" ? "Vector index" : "Memory";
    if (e === "embed") {
      ((this.plugin._embedBuffer = ""),
        (this.plugin._embedProgress = { current: 0, total: 0, key: "" }));
      let o = "",
        c = this._callPython(n, {
          credentialType: "embed",
          stream: !0,
          onData: (p) => {
            var g;
            let u =
                typeof p == "string"
                  ? p
                  : Buffer.isBuffer(p)
                    ? p.toString("utf-8")
                    : String(p),
              { events: f, buffer: _ } = rt(
                u,
                (g = this.plugin._embedBuffer) != null ? g : ""
              );
            this.plugin._embedBuffer = _;
            for (let h of f)
              h.event === "PROGRESS" &&
                ((this.plugin._embedProgress = {
                  current: h.current || 0,
                  total: h.total || 0,
                  key: h.key || "",
                }),
                r.memory &&
                  (r.memory.activity_progress = {
                    current: h.current || 0,
                    total: h.total || 1,
                  }));
            this.display();
          },
          onStderr: (p) => {
            o +=
              typeof p == "string"
                ? p
                : Buffer.isBuffer(p)
                  ? p.toString("utf-8")
                  : String(p);
          },
          onError: (p) => {
            ((this.plugin._embedProcess = null),
              r.memory &&
                ((r.memory.activity_state = "idle"),
                (r.memory.activity_label = null),
                (r.memory.activity_progress = null)),
              new F.Notice(s + " build error: " + (p.message || p), 8e3),
              this._probeModule("memory"),
              this.display());
          },
          onClose: (p) => {
            if (
              ((this.plugin._embedProcess = null),
              r.memory &&
                ((r.memory.activity_state = "idle"),
                (r.memory.activity_label = null),
                (r.memory.activity_progress = null)),
              p === 0)
            )
              new F.Notice(s + " build complete.");
            else {
              let u = o.trim().split(/\r?\n/).filter(Boolean),
                f = u[u.length - 1];
              new F.Notice(
                a("sr_build_failed_notice").replace(
                  "{detail}",
                  f || "exit code " + (p != null ? p : "?")
                ),
                8e3
              );
            }
            (this._probeModule("memory"), this.display());
          },
        });
      this.plugin._embedProcess = c;
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (o, c, p) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            o === 0
              ? new F.Notice(s + " rebuild complete")
              : new F.Notice(
                  s + " build failed" + (p ? ": " + p.slice(0, 120) : ""),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t, r = !0) {
    var b, v, m, E, w, y;
    (e.classList.add("pf-module-detail"),
      e
        .createEl("button", {
          cls: "pf-back-btn",
          text: a("btn_back_to_overview"),
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
      i = e.createDiv({
        cls: "pf-module-detail-selector",
        attr: { role: "tablist", "aria-label": a("md_module_switcher") },
      });
    for (let x of s)
      i.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (x.id === t ? " pf-module-detail-btn--active" : ""),
        text: x.label,
        attr: { role: "tab", "aria-selected": String(x.id === t) },
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = x.id),
          (this._focusTargetId = "#pf-" + x.id + "-detail-heading"),
          this.display());
      });
    let o = e.createEl("select", {
      cls: "pf-module-switcher",
      attr: { "aria-label": a("md_module_switcher") },
    });
    for (let x of s) {
      let k = o.createEl("option", { text: x.label, attr: { value: x.id } });
      k.selected = x.id === t;
    }
    o.addEventListener("change", () => {
      ((this._selectedDetailModule = o.value),
        (this._focusTargetId = "#pf-" + o.value + "-detail-heading"),
        this.display());
    });
    let c =
        t === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (v = (b = this._capabilityState) == null ? void 0 : b[t]) != null
            ? v
            : ne(t),
      p =
        (m = c.user_state) != null
          ? m
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
      he(f, p, this._getUserStateLabel(p)),
      u.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(t, c),
      }),
      c.activity_state === "running" &&
        zt(u, {
          label: a("cc_activity_running"),
          progress: c.activity_progress,
        }));
    let _ = (E = c.action) == null ? void 0 : E.primary;
    if (r && _ && p !== "ready" && t !== "agent") {
      let x =
          "action_" +
          ((w = _.action_id) != null ? w : _.verb).replace(/[.-]/g, "_"),
        k = a(x),
        S =
          k !== x
            ? k
            : a("cc_action_" + _.verb) !== "cc_action_" + _.verb
              ? a("cc_action_" + _.verb)
              : a("cc_action_probe");
      $(u, {
        label: S,
        loading: c.activity_state === "running",
        onClick: () => this._dispatchModuleAction(t, c),
      });
    }
    let g = u.createEl("details", { cls: "pf-module-diagnostics" });
    g.createEl("summary", { text: a("advanced_diagnostics") });
    let h = g.createDiv({ cls: "pf-module-diagnostics-body" });
    (h.createEl("div", { text: a("cc_diag_module") + ": " + c.module }),
      h.createEl("div", {
        text: a("cc_diag_state") + ": " + this._getUserStateLabel(p),
      }),
      h.createEl("div", { text: a("cc_diag_severity") + ": " + c.severity }),
      h.createEl("div", {
        text: a("cc_diag_activity") + ": " + c.activity_state,
      }),
      h.createEl("div", { text: a("cc_diag_reason") + ": " + c.reason.code }),
      h.createEl("div", {
        text: a("cc_diag_ttl") + ": " + c.ttl_seconds + "s",
      }));
    for (let x of (y = c.notices) != null ? y : [])
      h.createEl("div", { text: x.message });
    h.createEl("div", {
      text:
        a("cc_diag_updated") + ": " + new Date(c.updated_at).toLocaleString(),
    });
  }
  _renderHelpTab(e) {
    (e.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: a("help_eyebrow") || "help",
    }),
      e.createEl("h1", {
        cls: "pf-cc-title",
        text: a("help_title") || "Start with the task",
      }),
      e.createEl("p", {
        cls: "pf-cc-lede",
        text:
          a("help_lede") ||
          "Open the relevant module, or copy a diagnostic for support.",
      }));
    let t = e.createDiv({ cls: "pf-help-task-list" }),
      r = [
        ["library", a("help_library_task")],
        ["ocr", a("help_ocr_task")],
        ["memory", a("help_retrieval_task")],
        ["agent", a("help_agent_task")],
      ];
    for (let [n, s] of r)
      t.createEl("button", {
        cls: "pf-help-task-btn",
        text: s,
        attr: { "data-module": n },
      }).addEventListener("click", () => {
        ((this._detailReturn = {
          tab: "help",
          selector: `.pf-help-task-btn[data-module="${n}"]`,
        }),
          this._handleCardNavigation(n));
      });
    e.createEl("button", {
      cls: "pf-help-diagnostic-btn",
      text: a("help_copy") || "Copy diagnostic",
    }).addEventListener("click", () => this._buildAndCopyDiagnostic());
  }
  _execMemoryStatus(e, t, r) {
    let n = ge();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, i) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(i);
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
    let n = ge();
    (0, ee.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, i) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(i);
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
      i = (t == null ? void 0 : t.credentialType) && !(t != null && t.env),
      o = (u) => {
        let f = (0, ee.spawn)(n.path, s, { cwd: r, env: u, windowsHide: !0 });
        return (
          t.onData && f.stdout.on("data", t.onData),
          t.onStderr && f.stderr.on("data", t.onStderr),
          t.onError && f.on("error", t.onError),
          f.on("close", t.onClose),
          f
        );
      },
      c = (u) => {
        (0, ee.execFile)(
          n.path,
          s,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: u },
          (f, _, g) => {
            t && t.onClose && t.onClose(f ? 1 : 0, _, g);
          }
        );
      };
    if (i)
      return (
        ue(Ke(this.app), t.credentialType, nt(this.plugin.settings)).then(
          (u) => {
            t && t.stream ? o(u) : c(u);
          }
        ),
        null
      );
    let p = (t == null ? void 0 : t.env) || ge();
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
      text: a("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let i = this.app.vault.adapter.basePath,
          o = this._resolveRuntimeCommand(i);
        if (!(o != null && o.path)) {
          new F.Notice(a("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", o.path),
          n.setText(a("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (c, p, u) => {
              (console.log(
                "[PaperForge] memory build exit:",
                c ? "FAIL:" + c : "OK",
                (p || "").slice(0, 200),
                (u || "").slice(0, 200)
              ),
                n.setText(a("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                c === 0
                  ? new F.Notice(a("feat_memory_rebuild_done"))
                  : new F.Notice(
                      a("feat_memory_rebuild_failed") +
                        (u ? " " + u.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = vt(i)),
                this._refreshSnapshots(i));
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
      this._callPython(["sync"], {
        timeout: 12e4,
        onClose: (i) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            i === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this._probeModule("library", i != null ? i : 1),
            this.display(),
            this._refreshSnapshots(e),
            tt(this.app, this.plugin, e));
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
      (0, ee.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (n, s, i) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = vt(e)),
            (this._embedStatusText = De(e)),
            this.display());
        }
      ));
  }
  _renderVectorSection(e) {
    var c;
    if (
      (e.createEl("h4", { text: "Smart Retrieval" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(a("feat_vector_desc")),
      new F.Setting(e)
        .setName(a("feat_vector_enable"))
        .setDesc(a("feat_vector_enable_desc"))
        .addToggle((p) => {
          p.setValue(!!this.plugin.settings.features.vector_db).onChange(
            (u) => {
              ((this.plugin.settings.features.vector_db = u),
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
      text: a("feat_vector_config_label"),
    });
    let i = e.createEl("div", { cls: "paperforge-vector-config" }),
      o = (p) => {
        ((i.style.display = p ? "none" : ""),
          (s.style.transform = p ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (o(kt(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let p = ur(this._featurePanelsCollapsed, "vectorConfig", !1);
        o(p);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(i, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(i);
      return;
    }
    if (this._vectorDepsOk === null) {
      let p = Ye(r);
      ((this._vectorDepsOk = p && (c = p.deps_installed) != null ? c : !1),
        this._vectorDepsOk && (this._embedStatusText = De(r)),
        this.display());
    }
  }
  _renderApiConfig(e) {
    let r =
        this.plugin.settings._vector_db_configured || !1
          ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022"
          : "sk-...",
      n = null;
    (new F.Setting(e)
      .setName(a("feat_openai_key"))
      .setDesc(a("feat_openai_key_desc"))
      .addText((s) => {
        ((s.inputEl.type = "password"),
          s
            .setPlaceholder(r)
            .setValue("")
            .onChange((i) => {
              i &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  ((await this._storeVectorDbCredential(i)) && s.setValue(""),
                    (n = null));
                }, 600)));
            }));
      }),
      new F.Setting(e)
        .setName(a("feat_api_base_url"))
        .setDesc(a("feat_api_base_url_desc"))
        .addText((s) => {
          s.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((i) => {
              ((this.plugin.settings.vector_db_api_base = i),
                this.plugin.saveSettings(),
                this._refreshVectorDbCredentialStatus());
            });
        }),
      new F.Setting(e)
        .setName(a("feat_api_model"))
        .setDesc(a("feat_api_model_desc"))
        .addText((s) => {
          s.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((i) => {
              ((this.plugin.settings.vector_db_api_model = i),
                this.plugin.saveSettings(),
                this._refreshVectorDbCredentialStatus());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(a("feat_deps_missing")),
      new F.Setting(e)
        .setName(a("feat_install_deps"))
        .setDesc(a("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(a("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                s = this._resolveRuntimeCommand(n);
              if (!(s != null && s.path)) {
                new F.Notice(a("feat_no_python"));
                return;
              }
              (r.setButtonText(a("feat_installing")), r.setDisabled(!0));
              let i = "chromadb openai",
                o = new F.Notice(
                  a("feat_installing_pkgs").replace("{pkgs}", i),
                  0
                );
              try {
                let c = Object.assign(ge(), {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  p = i.split(" ");
                (await new Promise((u, f) => {
                  (0, ee.execFile)(
                    s.path,
                    [...s.args, "-m", "pip", "install", ...p],
                    { cwd: n, timeout: 3e5, env: c, windowsHide: !0 },
                    (_) => {
                      _ ? f(_) : u();
                    }
                  );
                }),
                  o.hide(),
                  new F.Notice(a("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = De(n)),
                  this.display());
              } catch (c) {
                (o.hide(),
                  new F.Notice(
                    a("feat_install_failed") + (c.stderr || c.message || c)
                  ),
                  r.setButtonText(a("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(De(t)),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: a("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let i = n.createEl("div", { cls: "paperforge-embed-controls" }),
      o = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (i.empty(), o.empty());
      let p = Ye(t),
        u = p == null ? void 0 : p.build_state,
        f = u && typeof u == "object" && !Array.isArray(u) ? u : {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          f.status === "running" &&
          (this.plugin._embedProgress = {
            current: typeof f.current == "number" ? f.current : 0,
            total: typeof f.total == "number" ? f.total : 1,
            key: typeof f.paper_id == "string" ? f.paper_id : "",
          }));
      let { current: _, total: g, key: h } = this.plugin._embedProgress,
        b =
          typeof (p == null ? void 0 : p.body_chunk_count) == "number"
            ? p.body_chunk_count
            : 0,
        v =
          typeof (p == null ? void 0 : p.object_chunk_count) == "number"
            ? p.object_chunk_count
            : 0,
        E =
          (typeof (p == null ? void 0 : p.chunk_count) == "number"
            ? p.chunk_count
            : 0) +
          b +
          v,
        w = E > 0,
        y = p !== null && typeof p.corrupted == "boolean" && p.corrupted,
        x = !!this.plugin._embedProcess,
        k = !this.plugin._embedProcess && f.status === "running",
        S =
          (p == null ? void 0 : p.deps_installed) !== void 0
            ? !!p.deps_installed
            : !0,
        C = typeof f.status == "string" ? f.status : "",
        O = typeof f.message == "string" ? f.message : "",
        A = async (P) => {
          var W;
          if (P === "--resume" && w && !y) {
            let B = a("retrieval_rebuild_warning").replace("{n}", String(E));
            if (!confirm(B)) return;
          }
          if (P === "--force" && w && !y) {
            let B =
              "Force rebuild will replace " +
              E +
              " existing chunk(s). Continue?";
            if (!confirm(B)) return;
          }
          let V = this._resolveRuntimeCommand(t);
          if (!(V != null && V.path)) {
            new F.Notice(a("retrieval_no_python"));
            return;
          }
          let Y = await ue(Ke(this.app), "embed", nt(this.plugin.settings));
          ((Y.PYTHONIOENCODING = "utf-8"),
            (Y.PYTHONUTF8 = "1"),
            (Y.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (Y.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", P],
              {
                stream: !0,
                env: Y,
                onData: (B) => {
                  var ce;
                  let M =
                      typeof B == "string"
                        ? B
                        : Buffer.isBuffer(B)
                          ? B.toString("utf-8")
                          : String(B),
                    { events: X, buffer: le } = rt(
                      M,
                      (ce = this.plugin._embedBuffer) != null ? ce : ""
                    );
                  this.plugin._embedBuffer = le;
                  for (let G of X)
                    G.event === "START"
                      ? (this.plugin._embedProgress.total = G.total || 0)
                      : G.event === "PROGRESS"
                        ? ((this.plugin._embedProgress.current =
                            G.current || 0),
                          (this.plugin._embedProgress.key = G.key || ""))
                        : G.event === "DONE" &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                  this.display();
                },
                onStderr: (B) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(B)));
                },
                onError: (B) => {
                  ((this.plugin._embedProcess = null),
                    new F.Notice(
                      a("feat_build_failed") + ": " + (B.message || B)
                    ),
                    this.display());
                },
                onClose: (B) => {
                  var M;
                  if (
                    (clearInterval(
                      (M = this.plugin._embedPollInterval) != null ? M : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    B === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = De(t)),
                      new F.Notice(a("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let X = (this.plugin._embedStderr || "").slice(0, 200);
                    new F.Notice(
                      a("feat_build_failed") + (X ? ": " + X : ""),
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
              (W = this.plugin._embedPollInterval) != null ? W : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (B, M) => {
                    var X;
                    if (((this.plugin._embedPolling = !1), B === 0 && M))
                      try {
                        let ce = JSON.parse(M).data;
                        if (ce && ce.build_state) {
                          let G = ce.build_state;
                          ((G.status === "stopping" || G.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (X = this.plugin._embedPollInterval) != null
                                ? X
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            G.current !== void 0 &&
                              G.total !== void 0 &&
                              ((this.plugin._embedProgress.current = G.current),
                              (this.plugin._embedProgress.total = G.total || 1),
                              (this.plugin._embedProgress.key =
                                G.paper_id || "")));
                        }
                      } catch (le) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        L = ze(t),
        R = !1;
      L &&
        typeof L.summary == "object" &&
        L.summary !== null &&
        "status" in L.summary &&
        (R = L.summary.status === "version_mismatch");
      let D;
      switch (
        (S
          ? R
            ? (D = "runtime-mismatch")
            : C === "stopping"
              ? (D = "stopping")
              : x && C === "running"
                ? (D = "building")
                : C === "failed"
                  ? (D = "failed")
                  : C === "stopped"
                    ? (D = "stopped")
                    : k
                      ? (D = "stale")
                      : y
                        ? (D = "corrupted")
                        : w
                          ? (D = "ready")
                          : (D = "idle")
          : (D = "deps-missing"),
        D)
      ) {
        case "building": {
          let P = i.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1;";
          let V = g > 0 ? ((_ / g) * 100).toFixed(1) : "0",
            Y = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Y.style.cssText = `width:${V}%; min-width:${_ > 0 ? "2px" : "0"};`),
            _ < g)
          ) {
            let B = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            B.style.cssText = `width:${(100 - parseFloat(V)).toFixed(1)}%;`;
          }
          (o.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${_}/${g} papers`,
          }),
            h &&
              o.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${h})`,
              }));
          let W = i.createEl("button");
          (W.setText(a("retrieval_stop")),
            (W.className = "mod-warning"),
            W.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let P = i.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1; opacity:0.5;";
          let V = g > 0 ? ((_ / g) * 100).toFixed(1) : "0",
            Y = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Y.style.cssText = `width:${V}%; min-width:${_ > 0 ? "2px" : "0"};`),
            _ < g)
          ) {
            let B = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            B.style.cssText = `width:${(100 - parseFloat(V)).toFixed(1)}%;`;
          }
          o.createEl("span", { text: a("retrieval_build_stopping") });
          let W = i.createEl("button");
          (W.setText(a("retrieval_stop")),
            (W.className = "mod-warning"),
            W.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("retrieval_build_failed") + (O ? ": " + O : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let P = i.createEl("button");
          (P.setText(a("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--resume")));
          let V = i.createEl("button");
          (V.setText(a("retrieval_force_rebuild")),
            (V.style.marginLeft = "6px"),
            V.addEventListener("click", () => A("--force")));
          break;
        }
        case "stopped": {
          o.setText(a("retrieval_build_stopped"));
          let P = i.createEl("button");
          (P.setText(a("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--resume")));
          break;
        }
        case "corrupted": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let P = i.createEl("button");
          (P.setText(a("retrieval_force_rebuild")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--force")));
          break;
        }
        case "stale": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = i.createEl("button");
          (P.setText(a("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--resume")));
          break;
        }
        case "ready": {
          i.createEl("span", {
            text: E + " chunks embedded",
            cls: "setting-item-description",
          });
          let P = i.createEl("button");
          (P.setText(a("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--resume")));
          let V = i.createEl("button");
          (V.setText(a("retrieval_force_rebuild")),
            (V.style.marginLeft = "6px"),
            V.addEventListener("click", () => A("--force")));
          break;
        }
        case "deps-missing": {
          o.setText(a("retrieval_build_deps_missing"));
          let P = i.createEl("a");
          (P.setText(a("feat_install_deps")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "runtime-mismatch": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = i.createEl("a");
          (P.setText(a("runtime_health_sync")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          o.setText(a("retrieval_build_idle"));
          let P = i.createEl("button");
          (P.setText(a("feat_build_btn")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => A("--resume")));
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
        new F.Notice(r));
      return;
    }
    if (!z.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new F.Notice(r, 4e3));
      return;
    }
    try {
      z.accessSync(e, z.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new F.Notice(n, 4e3));
      return;
    }
    (0, ee.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let c = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new F.Notice(c, 4e3));
        return;
      }
      let s = n.match(/Python (\d+)\.(\d+)/);
      if (!s) {
        let c = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new F.Notice(c, 4e3));
        return;
      }
      let i = parseInt(s[1], 10),
        o = parseInt(s[2], 10);
      if (i < 3 || (i === 3 && o < 11)) {
        let c =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${c}</span>`),
          new F.Notice(c, 4e3));
        return;
      }
      (0, ee.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (c) => {
        if (c) {
          let p = `\u2713 Python ${i}.${o} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${p}</span>`),
            new F.Notice(p, 4e3));
        } else {
          let p = `\u2713 Python ${i}.${o} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${p}</span>`),
            new F.Notice(p, 4e3));
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
    (0, ee.execFile)(
      r.path,
      [...r.args, "--version"],
      { timeout: 8e3 },
      (n, s) => {
        let i = [];
        i.push({
          label: "environment",
          ok: !n,
          detail: n ? a("check_python_fail") : s.trim(),
        });
        let o = !1,
          c = process.env.HOME || process.env.USERPROFILE || _r.homedir() || "";
        if (process.platform === "darwin")
          o = [
            "/Applications/Zotero.app",
            J.join(c, "Applications", "Zotero.app"),
          ].some((b) => {
            try {
              return z.existsSync(b);
            } catch (v) {
              return !1;
            }
          });
        else if (process.platform === "win32") {
          let h = process.env.ProgramFiles || "",
            b = process.env.LOCALAPPDATA || "";
          o = [
            J.join(h, "Zotero"),
            J.join(h, "(x86)", "Zotero"),
            J.join(b, "Programs", "Zotero"),
            J.join(b, "Zotero"),
            J.join(c, "AppData", "Local", "Programs", "Zotero"),
          ]
            .filter(Boolean)
            .some((m) => {
              try {
                return z.existsSync(m);
              } catch (E) {
                return !1;
              }
            });
        } else
          o = [
            J.join(c, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ].some((b) => {
            try {
              return z.existsSync(b);
            } catch (v) {
              return !1;
            }
          });
        let p = this.plugin.settings.zotero_data_dir;
        if (!o && p)
          try {
            o = z.existsSync(p);
          } catch (h) {}
        i.push({
          label: "Zotero",
          ok: o,
          detail: o ? a("check_zotero_ok") : a("check_zotero_fail"),
        });
        let u = !1,
          f = process.env.APPDATA || "";
        (process.platform === "win32" &&
          f &&
          (u = Ge(J.join(f, "Zotero", "Zotero", "Profiles"))),
          !u &&
            process.platform === "darwin" &&
            c &&
            (u = Ge(
              J.join(c, "Library", "Application Support", "Zotero", "Profiles")
            )),
          !u &&
            process.platform !== "win32" &&
            process.platform !== "darwin" &&
            c &&
            (u = Ge(J.join(c, ".zotero", "zotero", "Profiles"))),
          !u && p && String(p).trim() && (u = yt(p.trim())),
          !u && c && (u = yt(J.join(c, "Zotero"))),
          i.push({
            label: "Better BibTeX",
            ok: u,
            detail: u ? a("check_bbt_ok") : a("check_bbt_fail"),
          }));
        let _ = { true: "\u2713", false: "\u2717" };
        if (this._checkEl) {
          this._checkEl.setText(
            i.map((b) => `${_[String(b.ok)]} ${b.label}: ${b.detail}`).join(`
`)
          );
          let h = i.some((b) => !b.ok);
          this._checkEl.className = `paperforge-message msg-${h ? "error" : "ok"}`;
        }
        let g = i.filter((h) => !h.ok);
        (g.length > 0 &&
          new F.Notice(
            `[!!] \u672A\u901A\u8FC7: ${g.map((h) => h.label).join(", ")}`,
            6e3
          ),
          e());
      }
    );
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = fr.default.versions || [];
    for (let s of t) {
      let i = e.createEl("div", { cls: "paperforge-release-card" }),
        o = i.createEl("div", { cls: "paperforge-release-header" });
      if (
        (o.createEl("strong", { text: `v${s.version} \u2014 ${s.title}` }),
        o.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${s.date})`,
        }),
        s.breaking_or_migration && s.breaking_or_migration.length > 0)
      ) {
        let c = i.createEl("div", { cls: "paperforge-release-section" });
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
        let c = i.createEl("div", { cls: "paperforge-release-section" });
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
        let c = i.createEl("div", { cls: "paperforge-release-section" });
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
        let c = i.createEl("div", {
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
    ((this._capabilityState = Vt(e != null ? e : {}, Se)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var c, p, u, f;
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
        action: { primary: He(e) },
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
    let s = this.app.vault.adapter.basePath,
      i = this._resolveRuntimeCommand(s);
    if (!i) {
      if ((this._probing.delete(e), e === "installation")) {
        let _ = {
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
          action: { primary: It() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !1,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, _);
      } else this._updateCapabilityEnvelope(e, Pe(e));
      return;
    }
    let o = [...i.args, "-m", "paperforge", "--vault", s, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      o.push("--last-operation-exit-code", String(t)),
      e === "installation" &&
        o.push("--expected-version", this.plugin.manifest.version),
      (0, ee.execFile)(i.path, o, { cwd: s, timeout: 15e3 }, (_, g, h) => {
        if ((this._probing.delete(e), _)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, _.message),
            this._updateCapabilityEnvelope(e, Pe(e)));
          return;
        }
        try {
          let b = JSON.parse(g);
          ct(b, e)
            ? this._updateCapabilityEnvelope(e, b)
            : (console.warn(
                `[PaperForge] Probe ${e}: invalid envelope schema`,
                g == null ? void 0 : g.slice(0, 200)
              ),
              this._updateCapabilityEnvelope(e, Pe(e)));
        } catch (b) {
          (console.warn(
            `[PaperForge] Probe ${e}: unparseable JSON`,
            g == null ? void 0 : g.slice(0, 200)
          ),
            this._updateCapabilityEnvelope(e, Pe(e)));
        }
      }));
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    (Wt(r, t) && this._lastKnownState.set(e, Ut(t)),
      e === "installation" &&
        t.user_state === "ready" &&
        (this._setupReinstallRequested = !1),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        new F.Notice(a("cc_notice_refreshed"), 3e3),
      this._displayInProgress || this.display());
  }
  _ccBadgeKey(e, t) {
    return e.severity === "ok"
      ? "cc_badge_ok"
      : e.severity === "error" && t === "installation"
        ? "cc_badge_setup"
        : e.severity === "warning" || e.severity === "error"
          ? "cc_badge_attention"
          : "cc_badge_pending";
  }
  _sevClass(e) {
    return e === "error"
      ? "error"
      : e === "warning"
        ? "warn"
        : e === "unknown"
          ? "unknown"
          : "ok";
  }
  _localizeReason(e, t) {
    let r = "cc_reason_" + e.replace(/\./g, "_"),
      n = a(r);
    if (n !== r) return n.replace("{module}", t);
    let i = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      o = a(i);
    return o === i ? null : o.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      s = this._sevClass(n.severity),
      i = Te._REAL_PROBE.has(t),
      o = Te._NAVIGABLE.has(t),
      c = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${a("cc_module_" + t)} \u2014 ${a(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = c.createEl("div", { cls: "pf-cc-card-header" }),
      u = p.createEl("div", { cls: "pf-cc-card-name-area" });
    if (o) {
      let x =
          t === "installation"
            ? a("module_detail_open_installation")
            : t === "library"
              ? a("module_detail_open_library")
              : t === "ocr"
                ? a("module_detail_open_ocr")
                : t === "memory"
                  ? a("module_detail_open_memory")
                  : t === "help"
                    ? a("module_detail_open_help")
                    : a("md_select_installation"),
        k = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: a("cc_module_" + t),
          attr: { "data-module": t, "aria-label": x },
        });
      (k.addEventListener("click", () => this._handleCardNavigation(t)),
        k.addEventListener("keydown", (S) => {
          (S.key === "Enter" || S.key === " ") &&
            (S.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: a("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
      text: a(this._ccBadgeKey(n, t)),
    });
    let f;
    if (!i)
      f = a("cc_reason_placeholder").replace("{module}", a("cc_module_" + t));
    else {
      let x = this._localizeReason(n.reason.code, t);
      f = x != null ? x : n.reason.text;
    }
    if (
      (c.createEl("div", { cls: "pf-cc-card-reason", text: f }),
      n.activity_state === "running" && n.activity_label)
    ) {
      let x = c.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (x.createEl("span", { text: n.activity_label }),
        n.activity_progress && n.activity_progress.total > 0)
      ) {
        let k = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          C = x
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
    if (i && n.action.primary && !Mt(n)) {
      let x = Nt(n),
        S =
          x.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      _.createEl("button", {
        cls: S,
        text: x.label,
        attr: { "aria-label": x.label },
      }).addEventListener("click", () => {
        x.kind === "setup"
          ? this._startSetupJourney(1)
          : this._dispatchModuleAction(t, n);
      });
    }
    let g = c.createEl("details", { cls: "pf-cc-card-diagnostic" });
    g.createEl("summary", { text: a("cc_diagnostic_toggle") });
    let h = g.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      b = a("cc_state_" + n.capability_state) || n.capability_state,
      v = a("cc_severity_" + n.severity) || n.severity,
      m = a("cc_activity_" + n.activity_state) || n.activity_state,
      E;
    try {
      E = new Date(n.updated_at).toLocaleString();
    } catch (x) {
      E = n.updated_at;
    }
    (h.createEl("div", { text: `${a("cc_diag_module")}: ${n.module}` }),
      h.createEl("div", { text: `${a("cc_diag_state")}: ${b}` }),
      h.createEl("div", { text: `${a("cc_diag_severity")}: ${v}` }),
      h.createEl("div", { text: `${a("cc_diag_activity")}: ${m}` }));
    let w = h.createEl("div");
    w.appendText(a("cc_diag_reason") + ": " + f + " ");
    let y = w.createEl("code", { text: n.reason.code });
    (h.createEl("div", {
      text: `${a("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      h.createEl("div", { text: `${a("cc_diag_updated")}: ${E}` }));
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
    var C, O, A, L;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (C = this._capabilityState) != null ? C : {};
    (t.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: a("cc_eyebrow") || "control center",
    }),
      t.createEl("h1", {
        cls: "pf-cc-title",
        text: a("cc_title") || "Your literature pipeline",
      }),
      t.createEl("p", {
        cls: "pf-cc-lede",
        text:
          a("cc_lede") ||
          "See what is working and what needs attention across your pipeline.",
      }),
      t
        .createDiv({ cls: "pf-cc-refresh-row" })
        .createEl("button", {
          cls: "pf-action-btn pf-action-btn--ghost",
          text: "\u21BB " + (a("ocr_ws_btn_refresh") || "Refresh"),
        })
        .addEventListener("click", () => {
          for (let R of Se) R !== "maintenance" && this._probeModule(R);
        }));
    let s = (O = r.installation) != null ? O : ne("installation"),
      i = (A = r.library) != null ? A : ne("library"),
      o = s.user_state === "ready",
      c = i.user_state === "ready",
      p = o && c,
      u = [s, i].some((R) => R.user_state === "checking"),
      f = Object.values(r).filter(
        (R) =>
          R.user_state &&
          R.user_state !== "ready" &&
          R.user_state !== "not_enabled"
      ).length,
      _ = t.createEl("div", { cls: "pf-cc-summary" }),
      g = p ? "ready" : u ? "checking" : "attention",
      h = p
        ? a("cc_badge_ready") || "Ready"
        : u
          ? a("cc_badge_checking") || "Checking"
          : a("cc_badge_attention") || "Needs attention";
    _.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${g}`,
      text: h,
    });
    let b = _.createDiv({ cls: "pf-cc-summary-copy" }),
      v = p
        ? a("cc_summary_ready")
        : u
          ? a("cc_summary_checking")
          : this.plugin.settings._setup_complete === !1
            ? a("cc_summary_incomplete")
            : a("cc_summary_attention"),
      m = p
        ? a("cc_summary_ready_body")
        : u
          ? a("cc_summary_checking_body")
          : this.plugin.settings._setup_complete === !1
            ? a("cc_summary_incomplete_body")
            : a("cc_summary_attention_body");
    (b.createEl("strong", { text: v }),
      b.createEl("span", { cls: "caption", text: m }));
    let E = _.createDiv({ cls: "pf-cc-summary-meta" }),
      w = E.createEl("span");
    (w.createEl("strong", { text: String(f) }),
      w.appendText(" " + (a("cc_needs_attention") || "item needs attention")));
    let y = Object.values(r)
      .map((R) => R.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    (E.createEl("span", {
      text: y
        ? (a("cc_last_checked") || "Checked just now: ") +
          new Date(y).toLocaleString()
        : a("cc_checked_pending") || "Not checked yet",
    }),
      E.createEl("button", {
        cls: "pf-cc-summary-refresh",
        text: a("cc_refresh_btn") || "Refresh status",
      }).addEventListener("click", () => this._refreshAllModules()));
    let k = t.createDiv({ cls: "pf-cc-section-head" });
    (k.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: a("cc_modules_header") || "modules",
    }),
      k.createEl("h2", {
        text: a("cc_five_capabilities") || "Five capabilities",
      }),
      k.createEl("span", {
        cls: "caption",
        text:
          a("cc_optional_note") ||
          "Optional modules do not affect core readiness.",
      }));
    let S = t.createDiv({ cls: "pf-cc-module-list" });
    for (let [R, D] of this._getOverviewModules().entries()) {
      let P =
        D.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (L = r[D.id]) != null
            ? L
            : ne(D.id);
      this._renderOverviewCard(S, D.id, D.label, P, R + 1);
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
      n = z.existsSync(r);
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
    let i = e.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn",
      attr: {
        "data-module": t,
        "aria-label": r + " \u2014 " + this._getUserStateLabel(n.user_state),
        role: "button",
        tabindex: "0",
      },
    });
    ((i.style.cursor = "pointer"),
      i.createEl("span", {
        cls: "pf-cc-num",
        text: String(s).padStart(2, "0"),
      }),
      i.createEl("span", { cls: "pf-cc-card-name", text: r }),
      he(i, n.user_state, this._getUserStateLabel(n.user_state)),
      i.createEl("span", {
        cls: "pf-cc-card-sentence",
        text: this._getModuleConsequence(t, n),
      }));
    let o =
      n.user_state === "ready" &&
      (p = (c = n.action) == null ? void 0 : c.primary) != null &&
      p.scope_count
        ? (a("cc_metric_papers") || "Papers: ") + n.action.primary.scope_count
        : n.updated_at && n.updated_at !== new Date(0).toISOString()
          ? (a("cc_last_checked") || "") +
            new Date(n.updated_at).toLocaleString()
          : "";
    (i.createEl("span", { cls: "pf-cc-card-metric", text: o }),
      i.createEl("span", { cls: "pf-cc-card-arrow", text: "\u2192" }),
      i.addEventListener("click", () => this._handleCardNavigation(t)));
  }
  _getUserStateLabel(e) {
    return a("cc_badge_" + e);
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
      s = a(n);
    if (s && s !== n) return s;
    let i = this._localizeReason(
      (f = (u = t.reason) == null ? void 0 : u.code) != null ? f : "",
      this._getUserModuleName(e)
    );
    if (i) return i;
    let o = "cc_consequence_" + r,
      c = a(o);
    return c !== o ? c : a("cc_consequence_default");
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Se) {
      let r = this._capabilityState[t];
      r && dt(r) && ((this._capabilityState[t] = pt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    let e = ["installation", "library", "ocr", "memory"];
    for (let t of e) this._probeModule(t);
  }
  _buildAndCopyDiagnostic() {
    var s, i, o;
    let e =
        (i = (s = this.plugin.manifest) == null ? void 0 : s.version) != null
          ? i
          : "unknown",
      t = Zt(
        (o = this._capabilityState) != null ? o : {},
        this._lastKnownState
      ),
      n = Kt({ pluginVersion: e, modules: t });
    qt(n, () => {
      new F.Notice(a("support_diagnostic_copied"), 3e3);
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
    (t.createEl("h2", { text: a("setup_welcome") }),
      t.createEl("p", { text: a("setup_desc"), cls: "pf-setup-desc" }));
    let r = [
        a("setup_stage_1"),
        a("setup_stage_2"),
        a("setup_stage_3"),
        a("setup_stage_4"),
      ],
      n = t.createDiv({
        cls: "pf-setup-progress",
        attr: { "aria-label": a("setup_progress") },
      });
    r.forEach((i, o) => {
      n.createEl("span", {
        cls:
          "pf-setup-step" +
          (o + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (o + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(o + 1) + ". " + i,
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
        : ne("installation");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("installation") &&
      (this._attemptedProbes.add("installation"),
      this._probeModule("installation")),
      e.createEl("h3", { text: a("setup_foundation_title") }),
      e.createEl("p", { text: a("setup_foundation_desc") }));
    let n = e.createDiv({ cls: "pf-setup-field" });
    (n.createEl("label", { text: a("setup_foundation_python") }),
      n.createEl("span", {
        cls: "caption",
        text: a("setup_foundation_python_hint"),
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
      he(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? a("setup_ready")
            : this._getModuleConsequence("installation", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: a("setup_installing"),
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
                text: a("setup_reinstall_notice"),
              }),
              $(e, {
                label: a("foundation_reinstall_btn"),
                onClick: () => this._installFoundation(!0),
              }))
            : (t.user_state !== "ready" || this._setupOperation === "failed") &&
              $(e, {
                label: a("setup_foundation_install_btn"),
                onClick: () => this._installFoundation(!1),
              })));
    let i = e.createDiv({ cls: "pf-setup-nav" });
    $(i, {
      label: a("setup_nav_continue"),
      disabled: t.user_state !== "ready",
      onClick: () => {
        ((this._setupFeedback = null), (this._setupStage = 2), this.display());
      },
    });
  }
  _renderSetupStageLibrary(e) {
    var p, u;
    let t =
      (u = (p = this._capabilityState) == null ? void 0 : p.library) != null
        ? u
        : ne("library");
    (((t.capability_state === "unknown" &&
      t.updated_at === new Date(0).toISOString()) ||
      (t.user_state === "detection_failed" &&
        t.reason.code.endsWith(".stale"))) &&
      !this._attemptedProbes.has("library") &&
      (this._attemptedProbes.add("library"), this._probeModule("library")),
      e.createEl("h3", { text: a("setup_library_title") }),
      e.createEl("p", { text: a("setup_library_desc") }),
      he(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? a("setup_library_ready")
            : this._getModuleConsequence("library", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      this._setupOperation === "running"
        ? e.createEl("p", {
            cls: "pf-setup-status",
            text: a("setup_library_configuring"),
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
      text: a("setup_library_config_desc"),
    });
    let s = (f, _, g, h) => {
      let b = f.createDiv({ cls: "pf-setup-field" });
      (b.createEl("label", { text: _ }),
        h && b.createEl("span", { cls: "caption", text: h }));
      let v = b.createEl("input", {
        cls: "pf-setup-input",
        attr: { type: "text" },
      });
      ((v.value = this.plugin.settings[g] || ""),
        v.addEventListener("input", () => {
          ((this.plugin.settings[g] = v.value.trim()), this._debouncedSave());
        }));
    };
    (s(
      n,
      a("field_zotero_data"),
      "zotero_data_dir",
      a("setup_library_zotero_hint")
    ),
      n.createEl("h4", { text: a("setup_library_folder_heading") }));
    let i = n.createDiv({ cls: "pf-setup-folder-grid" });
    (s(i, a("dir_system"), "system_dir"),
      s(i, a("dir_resources"), "resources_dir"),
      s(i, a("dir_notes"), "literature_dir"),
      s(i, a("dir_base"), "base_dir"));
    let o = n.createEl("button", {
      cls: "pf-setup-verify",
      text: a("setup_library_verify"),
      attr: { type: "button" },
    });
    ((o.disabled = this._setupOperation === "running"),
      o.addEventListener("click", () => this._applyLibraryConfiguration()));
    let c = e.createDiv({ cls: "pf-setup-nav" });
    ($(c, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupFeedback = null), (this._setupStage = 1), this.display());
      },
    }),
      $(c, {
        label: a("setup_nav_continue"),
        disabled:
          t.user_state !== "ready" || this._setupOperation === "running",
        onClick: () => {
          ((this._setupFeedback = null),
            (this._setupStage = 3),
            this.display());
        },
      }));
  }
  _refreshVectorDbCredentialStatus() {
    ht(Ke(this.app), nt(this.plugin.settings)).then((e) => {
      e !== this.plugin.settings._vector_db_configured &&
        ((this.plugin.settings._vector_db_configured = e),
        this.plugin.saveSettings());
    });
  }
  async _storeVectorDbCredential(e) {
    return (await Gt(Ke(this.app), nt(this.plugin.settings), e))
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
    if (e === "vector-db-api-key") return this._storeVectorDbCredential(t);
    let r = Ke(this.app).app.secretStorage;
    if (!t || !(r != null && r.setSecret)) return !1;
    try {
      return (
        await r.setSecret(e, t),
        (await r.getSecret(e)) !== t
          ? !1
          : ((this.plugin.settings._paddleocr_configured = !0),
            (this.plugin.settings.paddleocr_api_key = ""),
            await this.plugin.saveSettings(),
            !0)
      );
    } catch (n) {
      return !1;
    }
  }
  _renderSetupStageOptionals(e) {
    (e.createEl("h3", { text: a("setup_optionals_title") }),
      e.createEl("p", { text: a("setup_optionals_desc") }));
    let t = [
      { id: "ocr", label: a("cc_module_ocr"), desc: a("setup_opt_ocr_desc") },
      {
        id: "memory",
        label: a("cc_module_memory"),
        desc: a("setup_opt_memory_desc"),
      },
      {
        id: "agent",
        label: a("cc_module_agent"),
        desc: a("setup_opt_agent_desc"),
      },
    ];
    for (let n of t) {
      let s = e.createDiv({ cls: "pf-setup-optional" }),
        i = s.createEl("input", {
          attr: { type: "checkbox", id: "pf-setup-opt-" + n.id },
        });
      ((i.checked = this._setupOptionals[n.id]),
        i.addEventListener("change", () => {
          ((this._setupOptionals[n.id] = i.checked), this.display());
        }));
      let o =
          n.id === "ocr"
            ? !!this.plugin.settings._paddleocr_configured
            : n.id === "memory"
              ? !!this.plugin.settings._vector_db_configured
              : !0,
        c = s.createDiv({ cls: "pf-setup-optional-copy" });
      (c.createEl("label", {
        attr: { for: "pf-setup-opt-" + n.id },
        text: n.label,
        cls: "pf-setup-optional-label",
      }),
        c.createEl("div", { text: n.desc, cls: "pf-setup-optional-desc" }));
      let p = c.createEl("span", {
        cls: "pf-setup-optional-state",
        text: o ? a("config_configured") : a("config_not_configured"),
      });
      if (!i.checked) continue;
      let u = s.createDiv({ cls: "pf-setup-optional-config" });
      if (n.id === "ocr") {
        (u.createEl("label", { text: a("field_paddleocr") }),
          u.createEl("p", { cls: "caption", text: a("ocr_privacy_warning") }));
        let f = u.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._paddleocr_configured
              ? "\u2022\u2022\u2022\u2022"
              : a("field_paddleocr"),
          },
        });
        u.createEl("button", {
          cls: "pf-setup-verify",
          text: a("config_save"),
          attr: { type: "button" },
        }).addEventListener("click", () => {
          this._storeSetupSecret("paddleocr-api-key", f.value).then((g) => {
            (p.setText(
              g ? a("setup_optional_saved") : a("setup_optional_save_failed")
            ),
              g && (f.value = ""));
          });
        });
      } else if (n.id === "memory") {
        (u.createEl("label", { text: a("feat_openai_key") }),
          u.createEl("p", { cls: "caption", text: a("feat_openai_key_desc") }));
        let f = u.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "password",
            autocomplete: "off",
            placeholder: this.plugin.settings._vector_db_configured
              ? "\u2022\u2022\u2022\u2022"
              : "sk-...",
          },
        });
        u.createEl("label", { text: a("feat_api_model") });
        let _ = u.createEl("input", {
          cls: "pf-setup-input",
          attr: {
            type: "text",
            placeholder:
              this.plugin.settings.vector_db_api_model ||
              "text-embedding-3-small",
          },
        });
        (_.addEventListener("change", () => {
          ((this.plugin.settings.vector_db_api_model = _.value.trim()),
            this.plugin.saveSettings(),
            this._refreshVectorDbCredentialStatus());
        }),
          u.createEl("label", { text: a("feat_api_base_url") }));
        let g = u.createEl("input", {
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
          u
            .createEl("button", {
              cls: "pf-setup-verify",
              text: a("config_save"),
              attr: { type: "button" },
            })
            .addEventListener("click", () => {
              this._storeSetupSecret("vector-db-api-key", f.value).then((b) => {
                (p.setText(
                  b
                    ? a("setup_optional_saved")
                    : a("setup_optional_save_failed")
                ),
                  b && (f.value = ""));
              });
            }));
      } else {
        (u.createEl("label", { text: a("feat_agent_platform") }),
          u.createEl("p", {
            cls: "caption",
            text: a("feat_agent_platform_desc"),
          }));
        let f = u.createEl("select");
        for (let [_, g] of Object.entries({
          opencode: "OpenCode",
          claude: "Claude Code",
          codex: "Codex",
          cursor: "Cursor",
          windsurf: "Windsurf",
          github_copilot: "GitHub Copilot",
          gemini: "Gemini CLI",
        })) {
          let h = f.createEl("option", { text: g, attr: { value: _ } });
          h.selected = _ === this.plugin.settings.agent_platform;
        }
        f.addEventListener("change", () => {
          ((this.plugin.settings.agent_platform = f.value),
            this.plugin.savePaperforgeJson({ agent_platform: f.value }),
            this.plugin.saveSettings(),
            p.setText(a("setup_optional_saved")));
        });
      }
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    ($(r, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      $(r, {
        label: a("setup_nav_continue"),
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
    e.createEl("h3", { text: a("setup_review_title") });
    let t = (p = this._capabilityState) == null ? void 0 : p.installation,
      r = (u = this._capabilityState) == null ? void 0 : u.library,
      n = (t == null ? void 0 : t.user_state) === "ready",
      s = (r == null ? void 0 : r.user_state) === "ready",
      i =
        (t == null ? void 0 : t.user_state) === "checking" ||
        (r == null ? void 0 : r.user_state) === "checking";
    (e.createEl("p", {
      text: n
        ? a("setup_ready")
        : i
          ? a("setup_review_checking")
          : a("cc_consequence_setup_required"),
      cls: n ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: s
          ? a("setup_library_ready")
          : i
            ? a("setup_review_checking")
            : a("cc_consequence_setup_required"),
        cls: s ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let o = Object.entries(this._setupOptionals)
      .filter(([, f]) => f)
      .map(([f]) => this._getUserModuleName(f));
    e.createEl("p", {
      text:
        o.length > 0
          ? a("setup_review_selected") + o.join(", ")
          : a("setup_no_optionals"),
    });
    let c = e.createDiv({ cls: "pf-setup-nav" });
    ($(c, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      (!n || !s) &&
        $(c, {
          label: a("setup_review_recheck"),
          disabled: i,
          onClick: () => this._refreshSetupReadiness(),
        }),
      $(c, {
        label: a("setup_nav_complete"),
        disabled: !n || !s,
        onClick: () => this._completeSetup(),
      }),
      (!n || !s) &&
        e.createEl("p", {
          text: i ? a("setup_review_checking") : a("setup_incomplete_warn"),
          cls: "pf-setup-warn",
        }));
  }
  _completeSetup() {
    ((this.plugin.settings._setup_complete = !0),
      this.plugin.saveSettings(),
      (this.activeTab = "overview"),
      this.display());
  }
  _restoreNavMemory() {
    let e = this.plugin.settings._navMemory;
    e != null &&
      e.destination &&
      ["overview", "help"].includes(e.destination) &&
      ((this.activeTab = e.destination),
      (this._navMemory = { destination: e.destination }),
      (this._focusTargetId = null),
      (this._detailReturn = null),
      (this._setupView = "overview"));
  }
};
((Te._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
])),
  (Te._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "help",
  ])));
var at = Te;
var T = require("obsidian"),
  xe = H(require("fs")),
  st = H(require("path")),
  fe = require("child_process");
var qe = H(require("path"));
function hr(d) {
  if (!d) return null;
  let l = qe.dirname(d);
  for (;;) {
    let e = qe.basename(l);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = qe.dirname(l);
    if (r === l) break;
    l = r;
  }
  return null;
}
var K = H(require("fs")),
  me = H(require("path"));
function Ue(d) {
  return Q(d).ocrDir;
}
function en(d, l) {
  let e = me.join(Ue(d), l, "versions", "manifest.json");
  try {
    if (!K.existsSync(e)) return null;
    let t = K.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let n = r,
        s = n.versions,
        i = n.current;
      if (Array.isArray(s) && i && typeof i == "object" && "label" in i)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function tn(d) {
  let l = Ue(d);
  try {
    return K.existsSync(l)
      ? K.readdirSync(l, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function St(d) {
  let l = tn(d),
    e = [];
  for (let t of l) {
    let r = en(d, t);
    if (!r) continue;
    let n = r.versions.map((i) => i.label),
      s = 0;
    for (let i of n) {
      let o = me.join(Ue(d), t, "versions", i, "fulltext.md");
      try {
        K.existsSync(o) && (s += K.statSync(o).size);
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
function mr(d, l, e) {
  let t = Ue(d),
    r = me.join(t, l, "versions", e, "fulltext.md"),
    n = me.join(t, l, "render"),
    s = me.join(n, "fulltext.md");
  try {
    return K.existsSync(r)
      ? (K.existsSync(n) || K.mkdirSync(n, { recursive: !0 }),
        K.copyFileSync(r, s),
        !0)
      : !1;
  } catch (i) {
    return !1;
  }
}
function yr(d, l, e, t) {
  var _;
  let r = Ue(d),
    n = me.join(r, l, "versions", e, "fulltext.md"),
    s = me.join(r, l, "versions", t, "fulltext.md"),
    i = "",
    o = "";
  try {
    K.existsSync(n) && (i = K.readFileSync(n, "utf-8"));
  } catch (g) {}
  try {
    K.existsSync(s) && (o = K.readFileSync(s, "utf-8"));
  } catch (g) {}
  let c = gr(i),
    p = gr(o),
    u = Math.max(c.length, p.length),
    f = [];
  for (let g = 0; g < u; g++) {
    let h = g < c.length ? c[g] : "",
      b = g < p.length ? p[g] : "",
      v =
        (_ = (h || b).split(`
`)[0]) != null
          ? _
          : "",
      m = v.startsWith("## ") ? v.replace(/^##\s+/, "") : "",
      E = "unchanged";
    (!h && b
      ? (E = "added")
      : h && !b
        ? (E = "removed")
        : h !== b && (E = "changed"),
      E !== "unchanged" &&
        f.push({
          paragraphIndex: g,
          heading: m,
          type: E,
          oldText: h || void 0,
          newText: b || void 0,
        }));
  }
  return f;
}
function gr(d) {
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
function Ae(d, l) {
  return d && typeof d == "object" && l in d ? Reflect.get(d, l) : void 0;
}
function br(d) {
  let l = Ae(d, "plugins"),
    e = Ae(l, "plugins"),
    t = Ae(e, "paperforge"),
    r = Ae(t, "settings");
  if (!r || typeof r != "object") return;
  let n = Ae(r, "vector_db_api_base"),
    s = Ae(r, "vector_db_api_model");
  return {
    baseUrl: typeof n == "string" ? n : "",
    model: typeof s == "string" ? s : "",
  };
}
var Le = class extends T.ItemView {
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
    this._driftBannerEl = null;
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
    var s, i, o;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (i =
          (s = e == null ? void 0 : e.settings) == null
            ? void 0
            : s.python_path) == null
          ? void 0
          : i.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    let r =
      (o = e == null ? void 0 : e.getManagedRuntime) == null
        ? void 0
        : o.call(e);
    if (!r) return null;
    let n = _e(r.current());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  getViewType() {
    return ye;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Ne;
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
    var o;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((o = t == null ? void 0 : t.manifest) == null ? void 0 : o.version) ||
        "?",
      n = this._resolvePython();
    if (!n) return;
    let { path: s, args: i = [] } = n;
    Promise.resolve({ status: "ok", pyVersion: "?" }).then((c) => {
      if (c.status === "not-installed") return;
      let p = c.pyVersion || "";
      ((this._paperforgeVersion = p.startsWith("v") ? p : "v" + p),
        this._versionBadge &&
          this._versionBadge.setText(this._paperforgeVersion),
        this._driftBannerEl &&
        r &&
        this._paperforgeVersion !== "v" + r.replace(/^v/, "")
          ? ((this._driftBannerEl.style.display = "block"),
            this._driftBannerEl.setText(
              a("dashboard_drift_warning")
                .replace("{0}", this._paperforgeVersion)
                .replace("{1}", "v" + r.replace(/^v/, ""))
            ))
          : this._driftBannerEl &&
            (this._driftBannerEl.style.display = "none"));
    });
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
    let { path: s, args: i = [] } = n;
    (0, fe.execFile)(
      s,
      [...i, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (o, c) => {
        if (!o)
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
      s = e.ocr_version_state || {},
      i = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: i,
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
    var i, o;
    let n =
        ((i = r == null ? void 0 : r.settings) == null
          ? void 0
          : i.system_dir) || "System",
      s = st.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = xe.readFileSync(s, "utf-8"),
        p = JSON.parse(c),
        u = p.items || [],
        f = {},
        _ = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        g = 0,
        h = 0,
        b = 0,
        v = 0,
        m = 0,
        E = 0;
      for (let w of u) {
        w.note_path && E++;
        let y = w.lifecycle || "pdf_ready";
        f[y] = (f[y] || 0) + 1;
        let x = w.health || {};
        for (let S of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (x[S] || "healthy") === "healthy" ? _[S].healthy++ : _[S].unhealthy++;
        let k = w.ocr_status || "";
        (g++,
          k === "done"
            ? h++
            : k === "pending"
              ? b++
              : k === "processing" || k === "queued" || k === "running"
                ? v++
                : m++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((o = this._cachedStats) == null ? void 0 : o.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: E,
        exports: 0,
        bases: 0,
        ocr: { total: g, pending: b, processing: v, done: h, failed: m },
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
      (0, fe.execFile)(
        u,
        [...f, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (_, g) => {
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
            let h = JSON.parse(g);
            ((this._cachedStats = h),
              this._metricsEl.empty(),
              this._renderStats(h),
              this._renderOcr(h));
          } catch (h) {
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
      n = st.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let i = xe.readFileSync(n, "utf-8");
      return JSON.parse(i);
    } catch (i) {
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
    return Bt(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = lt(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var i;
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
          text: ((i = o.value) == null ? void 0 : i.toString()) || "\u2014",
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
      i = t.processing || 0,
      o = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        i > 0
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
        i > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let c = [
        { cls: "pending", count: s },
        { cls: "active", count: i },
        { cls: "done", count: n },
        { cls: "failed", count: o },
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
        { cls: "pending", value: s, label: "Pending" },
        { cls: "active", value: i, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: o, label: "Failed" },
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
      s = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      i = !1;
    for (let o of n) {
      let c = s.createEl("div", { cls: "step" });
      (c.createEl("div", { cls: "step-indicator" }),
        c.createEl("div", { cls: "step-label", text: o.label }),
        o.key === r
          ? (c.addClass("current"), (i = !0))
          : i
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
      let i = t[s.key] || "healthy",
        o = n.createEl("div", { cls: "paperforge-health-cell" }),
        c,
        p,
        u;
      (i === "healthy" || i === "ok"
        ? ((c = s.iconOk), (p = "ok"), (u = `${s.label}: OK`))
        : i === "warn" || i === "warning" || i === "degraded"
          ? ((c = s.iconWarn),
            (p = "warn"),
            (u = `${s.label}: Needs Attention`))
          : ((c = s.iconFail), (p = "fail"), (u = `${s.label}: Failed`)),
        o.addClass(p),
        o.setAttribute("title", u),
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
      i = 4,
      o = Math.max(1, Math.min(i, Math.round(t)));
    for (let c = 1; c <= i; c++) {
      let p = s.createEl("div", { cls: "gauge-segment" });
      c <= o && (p.addClass("filled"), p.addClass(`level-${c}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${o} / ${i}` }),
      o < i && r)
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
      s = Math.max(1, ...r.map((i) => t[i.key] || 0));
    for (let i of r) {
      let o = t[i.key] || 0,
        c = (o / s) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: i.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${i.cls}`,
            attr: { style: `width:${c.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: o.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return hr(e);
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
        i = s && s.frontmatter && s.frontmatter.zotero_key;
      if (i) return { mode: "paper", filePath: r, key: i, domain: null };
    }
    if (t === "pdf") {
      let s = this._getCachedIndex();
      for (let i of s) {
        let o = (i.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((o ? o[1] : i.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: i.zotero_key,
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
    var X, le, ce, G, Ct, Rt, Ft;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = e.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      s = 0,
      i = 0;
    for (let I of t)
      (I.has_pdf && n++,
        I.ocr_status === "done" && s++,
        I.deep_reading_status === "done" && i++);
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
        { value: i, label: "deep-read done" },
      ];
    for (let I of p) {
      let j = c.createEl("div", { cls: "paperforge-snapshot-pill" });
      (j.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(I.value),
      }),
        j.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + I.label,
        }));
    }
    let u = e.createEl("div", { cls: "paperforge-system-status" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let f = u.createEl("div", { cls: "paperforge-status-grid" }),
      _ = this.app.plugins.plugins.paperforge,
      g =
        ((X = _ == null ? void 0 : _.manifest) == null ? void 0 : X.version) ||
        "?",
      h = this._paperforgeVersion;
    if (!h) {
      let I = this._resolvePython();
      if (I) {
        let { path: j, args: pe = [] } = I;
        try {
          let se = this.app.vault.adapter.basePath,
            te = (0, fe.execFileSync)(
              j,
              [...pe, "-c", "import paperforge; print(paperforge.__version__)"],
              { cwd: se, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
            ).trim();
          te &&
            ((h = te.startsWith("v") ? te : "v" + te),
            (this._paperforgeVersion = h));
        } catch (se) {}
      }
    }
    h = h || "\u2014";
    let b = h === "v" + g;
    this._renderSystemStatusRow(
      f,
      "Runtime",
      b ? "healthy" : "mismatch",
      b ? "v" + g : "plugin v" + g + " \u2260 CLI " + h
    );
    let v = this._loadIndex(),
      m = v && v.items && v.items.length > 0;
    this._renderSystemStatusRow(
      f,
      "Index",
      m ? "healthy" : "missing",
      m ? v.items.length + " entries" : "formal-library.json not found"
    );
    let E =
        ((le = _ == null ? void 0 : _.settings) == null
          ? void 0
          : le.system_dir) || "System",
      w = this.app.vault.adapter.basePath,
      y = !1,
      x = "No exports found";
    try {
      let I = st.join(w, E, "PaperForge", "exports");
      if (xe.existsSync(I)) {
        let j = xe.readdirSync(I).filter((pe) => pe.endsWith(".json"));
        ((y = j.length > 0),
          (x = y ? j.length + " export(s)" : "No JSON exports"));
      }
    } catch (I) {}
    this._renderSystemStatusRow(
      f,
      "Zotero Export",
      y ? "healthy" : "missing",
      x
    );
    let k =
        (G = (ce = this.app.plugins) == null ? void 0 : ce.plugins) == null
          ? void 0
          : G.paperforge,
      S = !!(
        (Ct = k == null ? void 0 : k.settings) != null &&
        Ct._paddleocr_configured
      );
    this._renderSystemStatusRow(
      f,
      "OCR Token",
      S ? "configured" : "missing",
      S ? "Configured" : "Not set"
    );
    let C = !1,
      O = "",
      A = this.app.vault.adapter.basePath,
      L = ze(A);
    ((C = sr(A)),
      (O =
        (L && ((Rt = L.summary) == null ? void 0 : Rt.reason)) ||
        (L && ((Ft = L.summary) == null ? void 0 : Ft.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        f,
        "Memory Layer",
        C ? "healthy" : "fail",
        O
      ));
    let R = !b && h !== "\u2014";
    if (R || !m || !y || !S) {
      let I = e.createEl("div", { cls: "paperforge-issue-summary" });
      I.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let j = I.createEl("div", { cls: "paperforge-issue-list" });
      (R &&
        j.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        m ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        y ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        S ||
          j.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let pe = I.createEl("div", { cls: "paperforge-issue-actions" }),
        se = pe.createEl("button", { cls: "paperforge-contextual-btn" });
      (se.createEl("span", { text: "Run Doctor" }),
        se.addEventListener("click", () => {
          let Me = re.find((ot) => ot.id === "paperforge-doctor");
          Me && this._runAction(Me, se);
        }));
      let te = pe.createEl("button", { cls: "paperforge-contextual-btn" });
      (te.createEl("span", { text: "Repair Issues" }),
        te.addEventListener("click", () => {
          let Me = re.find((ot) => ot.id === "paperforge-repair");
          Me && this._runAction(Me, te);
        }));
    }
    let P = e.createEl("div", { cls: "paperforge-global-actions" });
    P.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let V = P.createEl("div", { cls: "paperforge-global-actions-row" }),
      Y = V.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (Y.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      Y.createEl("span", { text: "Open Literature Hub" }),
      Y.addEventListener("click", () => {
        var pe;
        let I =
            ((pe = _ == null ? void 0 : _.settings) == null
              ? void 0
              : pe.base_dir) || "Bases",
          j = this.app.vault.getAbstractFileByPath(I);
        if (j) {
          let se = null;
          if (
            (j.children &&
              (se = j.children.find((te) => te.extension === "base")),
            se)
          ) {
            let te = this.app.workspace.getLeaf(!1);
            te && te.openFile(se);
          } else new T.Notice("[!!] No .base file found in " + I, 6e3);
        } else new T.Notice("[!!] Base directory not found: " + I, 6e3);
      }));
    let W = V.createEl("button", { cls: "paperforge-contextual-btn" });
    (W.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      W.createEl("span", { text: "Sync Library" }),
      W.addEventListener("click", () => {
        let I = re.find((j) => j.id === "paperforge-sync");
        I && this._runAction(I, W);
      }));
    let B = V.createEl("button", { cls: "paperforge-contextual-btn" });
    (B.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      B.createEl("span", { text: "Run OCR" }),
      B.addEventListener("click", () => {
        let I = re.find((j) => j.id === "paperforge-ocr");
        I && this._runAction(I, B);
      }));
    let M = V.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (M.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      M.createEl("span", { text: "Redo OCR" }),
      M.addEventListener("click", () => {
        let I = re.find((j) => j.id === "paperforge-ocr-redo");
        I && this._runAction(I, M);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let s = e.createEl("div", { cls: "paperforge-status-row" });
    (s
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      s.createEl("span", { cls: "paperforge-status-label", text: t }),
      s.createEl("span", { cls: "paperforge-status-detail", text: n || "" }));
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
        new T.Notice("Title copied"));
    });
    let i = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      i.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        i.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let o = r.createEl("div", { cls: "paperforge-status-strip" }),
      c = o.createEl("div", { cls: "paperforge-status-strip-left" }),
      p = o.createEl("div", { cls: "paperforge-status-strip-right" }),
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
      let g = c.createEl("span", { cls: "paperforge-status-pill" }),
        h = "pending";
      (_.ok ? (h = "ok") : _.fail ? (h = "fail") : _.pending && (h = "pending"),
        g.addClass(h));
      let b = _.ok ? "\u2713" : _.fail ? "\u2717" : "\u25CB";
      (g.createEl("span", { cls: "paperforge-status-pill-icon", text: b }),
        g.createEl("span", { text: " " + _.label }));
    }
    if (e.pdf_path) {
      let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (_.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        _.createEl("span", { text: "\u6253\u5F00 PDF" }),
        _.addEventListener("click", () => {
          let g = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            h = g ? g[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(h)
            ? this.app.workspace.openLinkText(h, "")
            : new T.Notice("[!!] PDF not found: " + h, 6e3);
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
      (f.createEl("span", { text: a("version_panel_title") }),
      f.addEventListener("click", () => {
        this._switchToVersionMode(t);
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
    let s = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      i = s.createEl("div", {
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
                let u = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((i.setText(u), p.length > 200)) {
                  let f = s.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    _ = f.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  _.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let g = !1;
                  f.addEventListener("click", () => {
                    (i.setText(g ? u : p),
                      (_.innerHTML = g
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (g = !g));
                  });
                }
              } else
                i.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              i.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : i.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else i.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
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
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          f = p.length;
        for (let h of u) {
          let b = p.indexOf(h);
          b !== -1 && b < f && (f = b);
        }
        let _ = p.indexOf(`

`);
        _ !== -1 && _ < f && (f = _);
        let g = p.slice(0, f).trim();
        return (
          g.startsWith("**") && (g = g.slice(2)),
          g.endsWith("**") && (g = g.slice(0, -2)),
          g || null
        );
      }
    }
    let s = r.indexOf(`
`);
    if (s === -1) return null;
    let i = r
      .slice(s + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !i || i.startsWith("###") || i.startsWith("##")
      ? null
      : i.length > 300
        ? i.slice(0, 300) + "..."
        : i;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      i = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(i)
      .then((o) => {
        if (o) return this.app.vault.adapter.read(i);
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
          let _ = r.createEl("div", { cls: "paperforge-discussion-item" }),
            g = _.createEl("div", { cls: "paperforge-discussion-q" });
          (g.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            g.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: f.question,
            }));
          let h = _.createEl("div", { cls: "paperforge-discussion-a" }),
            b = !1;
          if (
            (f.answer &&
              f.answer.length > 500 &&
              ((b = !0), h.classList.add("paperforge-discussion-a-collapsed")),
            await T.MarkdownRenderer.render(
              this.app,
              f.answer || "",
              h,
              i,
              this
            ),
            b)
          ) {
            let v = !1;
            ((_.style.cursor = "pointer"),
              _.addEventListener("click", () => {
                ((v = !v),
                  h.classList.toggle("paperforge-discussion-a-collapsed", !v),
                  h.classList.toggle("paperforge-discussion-a-expanded", v));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (f) => {
          (f.preventDefault(),
            this.app.vault.getAbstractFileByPath(i)
              ? this.app.workspace.openLinkText(i, "")
              : new T.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((o) => {
        console.error("PaperForge: discussion.md read error", i, o.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      s = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let i of s) {
      let o = i.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!o) continue;
      let c = i.substring(0, o.index).trim(),
        p = i.substring(o.index + 3 + 4).trim();
      n.push({ question: c, answer: p });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      s = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      i = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((i.style.display = "none"),
      this._techDetailsExpanded
        ? ((i.style.display = "block"),
          s.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : s.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      s.addEventListener("click", () => {
        let _ = i.style.display !== "none";
        ((i.style.display = _ ? "none" : "block"),
          s.setText(
            _
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !_));
      }));
    let o = i.createEl("div", { cls: "paperforge-workflow-toggles" }),
      c = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let _ of c) {
      let g = o.createEl("label", { cls: "paperforge-workflow-toggle" }),
        h = g.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((h.checked = t[_.key] === !0),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: _.label,
        }),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: _.hint,
        }),
        h.addEventListener("change", async () => {
          let b = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!b) {
            new T.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let v = h.checked;
          (await this.app.fileManager.processFrontMatter(b, (m) => {
            m[_.key] = v;
          }),
            this._patchCachedEntry(r, { [_.key]: v }),
            (this._currentPaperEntry = lt(this._currentPaperEntry, {
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
    for (let [_, g] of u) {
      let h = i.createEl("div", { cls: "paperforge-technical-row" });
      h.createEl("span", { cls: "paperforge-technical-label", text: _ });
      let b = h.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(g),
      });
      f.has(_) &&
        g &&
        g !== "\u2014" &&
        (b.addClass("pf-copy"),
        b.addEventListener("click", () => {
          (navigator.clipboard.writeText(g), new T.Notice(_ + " copied"));
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
          cmd: "sync",
          icon: "\u21BB",
        },
        ocr: {
          label: "OCR Needed",
          text: "Fulltext is missing but PDF is present. Click to run OCR.",
          cmd: "ocr",
          icon: "\u229E",
        },
        repair: {
          label: "Repair Needed",
          text: "State divergence or path errors detected. Click to repair.",
          cmd: "repair",
          icon: "\u21BA",
        },
        "rebuild index": {
          label: "Rebuild Needed",
          text: "Index may be stale. Click to run sync to rebuild.",
          cmd: "sync",
          icon: "\u21BB",
        },
        "/pf-deep": {
          label: "Ready for Deep Reading",
          text: "Fulltext is ready. Copy /pf-deep command and run in your agent.",
          cmd: null,
          icon: "\u{1F50D}",
        },
        ready: {
          label: "All Set",
          text: "This paper is fully processed and ready for use.",
          cmd: "ready",
          icon: "\u2713",
        },
      },
      i = s[n] || s.ready,
      o = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && o.addClass("ready"),
      o.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      o.createEl("div", { cls: "paperforge-next-step-text", text: i.text }),
      i.cmd && i.cmd !== "ready")
    ) {
      let u = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: i.icon + "  " + i.label }),
        u.addEventListener("click", () => {
          let f = re.find((_) => _.cmd === i.cmd);
          f && this._runAction(f, u);
        }));
    } else if (n === "/pf-deep") {
      let u = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: "\u{1F4CB}  " + a("copy_pf_deep_cmd") }),
        u.addEventListener("click", () => {
          let b = "/pf-deep " + r;
          navigator.clipboard
            .writeText(b)
            .then(() => {
              (u.setText("\u2713  " + a("copied")),
                new T.Notice(b + " copied"));
            })
            .catch(() => {
              new T.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let f =
          ((p =
            (c = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : c.settings) == null
            ? void 0
            : p.agent_platform) || "opencode",
        g =
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
        a("run_in_agent").replace("{0}", g)
      );
    } else
      n === "ready" &&
        o
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + i.label });
  }
  _openFulltext(e) {
    if (!e) {
      new T.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new T.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      i = 0,
      o = 0,
      c = 0,
      p = 0,
      u = 0,
      f = 0;
    for (let y of t) {
      (y.has_pdf && s++,
        y.ocr_status === "done" && i++,
        y.ocr_status === "done" && y.analyze === !0 && o++,
        y.deep_reading_status === "done" && c++);
      let x = y.ocr_status || "";
      x === "pending" || x === "queued"
        ? p++
        : x === "processing"
          ? u++
          : (x === "failed" ||
              x === "blocked" ||
              x === "done_incomplete" ||
              x === "nopdf") &&
            f++;
    }
    r.createEl("div", { cls: "paperforge-collection-header" }).createEl("div", {
      cls: "paperforge-collection-title",
      text: e,
    });
    let g = r.createEl("div", { cls: "paperforge-workflow-overview" });
    g.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let h = g.createEl("div", { cls: "paperforge-workflow-funnel" }),
      b = [
        { value: n, label: "Total" },
        { value: s, label: "PDF Ready" },
        { value: i, label: "OCR Done" },
        { value: c, label: "Deep Read" },
      ];
    for (let y = 0; y < b.length; y++) {
      let x = h.createEl("div", { cls: "paperforge-workflow-stage" });
      (x.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(b[y].value),
      }),
        x.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: b[y].label,
        }),
        y < b.length - 1 &&
          h.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (p + u + i + f > 0) {
      let y = r.createEl("div", { cls: "paperforge-ocr-section" }),
        x = y.createEl("div", { cls: "paperforge-collection-ocr-header" });
      x.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let k = x.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (k.addClass("active"), k.setText("Processing"))
        : p > 0
          ? k.setText("Pending")
          : (k.addClass("idle"), k.setText("Idle"));
      let S = y.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && S.addClass("paperforge-processing");
      let C = p + u + i + f,
        O = [
          { cls: "pending", count: p },
          { cls: "active", count: u },
          { cls: "done", count: i },
          { cls: "failed", count: f },
        ];
      for (let R of O)
        if (R.count > 0) {
          let D = ((R.count / C) * 100).toFixed(1);
          S.createEl("div", {
            cls: `paperforge-progress-seg ${R.cls}`,
            attr: { style: `width:${D}%` },
          });
        }
      let A = y.createEl("div", { cls: "paperforge-ocr-counts" }),
        L = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: i, label: "Done" },
          { cls: "failed", value: f, label: "Attention" },
        ];
      for (let R of L) {
        let D = A.createEl("div", { cls: "paperforge-ocr-count" });
        (D.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: R.value.toString(),
        }),
          D.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: R.label,
          }));
      }
    }
    let v = r.createEl("div", { cls: "paperforge-collection-actions" }),
      m = v.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (m.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      m.createEl("span", { text: "Run OCR" }),
      m.addEventListener("click", () => {
        let y = re.find((x) => x.id === "paperforge-ocr");
        y && this._runAction(y, m);
      }));
    let E = v.createEl("button", { cls: "paperforge-contextual-btn" });
    (E.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      E.createEl("span", { text: "Sync Library" }),
      E.addEventListener("click", () => {
        let y = re.find((x) => x.id === "paperforge-sync");
        y && this._runAction(y, E);
      }));
    let w = v.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (w.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      w.createEl("span", { text: "Redo OCR" }),
      w.addEventListener("click", () => {
        let y = re.find((x) => x.id === "paperforge-ocr-redo");
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
      new T.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = St(n)),
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
      (this._versionPapers = St(n));
    let s = e.createEl("div", { cls: "paperforge-version-left" }),
      i = e.createEl("div", { cls: "paperforge-version-right" }),
      o = s.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: a("version_filter_placeholder") },
      });
    o.value = this._versionFilter;
    let c = s.createEl("div", { cls: "paperforge-version-paper-list" }),
      p = () => {
        c.empty();
        let m = this._versionFilter.toLowerCase(),
          E = this._versionPapers
            ? this._versionPapers.filter(
                (y) =>
                  !m ||
                  y.key.toLowerCase().includes(m) ||
                  y.title.toLowerCase().includes(m)
              )
            : [];
        if (E.length === 0) {
          c.createEl("div", {
            cls: "paperforge-meta",
            text: a("version_no_backups"),
          });
          return;
        }
        let w = c.createEl("div", {
          cls: "paperforge-meta",
          text: a("version_papers_count").replace("{n}", String(E.length)),
        });
        for (let y of E) {
          let x = c.createEl("div", { cls: "paperforge-version-paper-item" }),
            k = x.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: y.title,
            }),
            S = x.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: y.versions.map((C) => C.label).join(" "),
            });
          x.addEventListener("click", () => {
            (c
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((C) => C.removeClass("selected")),
              x.addClass("selected"),
              f(y));
          });
        }
      };
    o.addEventListener("input", () => {
      ((this._versionFilter = o.value), p());
    });
    let u = i.createEl("div", { cls: "paperforge-version-timeline-area" }),
      f = (m) => {
        if (
          (u.empty(),
          u
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: m.title }),
          m.versions.length === 0)
        ) {
          u.createEl("div", {
            cls: "paperforge-meta",
            text: a("version_no_backups"),
          });
          return;
        }
        let w = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let y of m.versions) {
          let x = y.label === m.currentLabel,
            k = w.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (x ? " paperforge-version-current" : ""),
            }),
            S = k.createEl("div", { cls: "paperforge-version-dot" }),
            C = k.createEl("div", { cls: "paperforge-version-content" }),
            O = C.createEl("div", { cls: "paperforge-version-label-row" });
          (O.createEl("span", {
            cls: "paperforge-version-label",
            text: y.label,
          }),
            x &&
              O.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: a("version_current"),
              }));
          let A = y.created_at ? y.created_at.slice(0, 10) : "";
          C.createEl("div", {
            cls: "paperforge-meta",
            text: A + " \u2014 " + y.source,
          });
          let L = y.fulltext_size
            ? y.fulltext_size > 1024
              ? (y.fulltext_size / 1024).toFixed(0) + "KB"
              : y.fulltext_size + "B"
            : "";
          L && C.createEl("div", { cls: "paperforge-meta", text: L });
          let R = C.createEl("div", { cls: "paperforge-version-actions" });
          (R.createEl("button", {
            cls: "pf-btn-primary",
            text: a("version_restore_btn"),
          }).addEventListener("click", () => {
            mr(n, m.key, y.label)
              ? new T.Notice(
                  a("version_restore_done").replace("{label}", y.label)
                )
              : new T.Notice("Restore failed", 6e3);
          }),
            m.versions.length > 1 &&
              !x &&
              R.createEl("button", {
                cls: "pf-btn-secondary",
                text: a("version_compare_btn"),
              }).addEventListener("click", () => {
                g(m, y.label, m.currentLabel);
              }));
        }
      },
      _ = i.createEl("div", { cls: "paperforge-version-compare" });
    _.style.display = "none";
    let g = (m, E, w) => {
        let y = yr(n, m.key, E, w);
        ((_.style.display = "block"), _.empty());
        let x = _.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (x.createEl("span", {
            cls: "pf-title",
            text: a("version_compare_title")
              .replace("{vA}", E)
              .replace("{vB}", w),
          }),
          x.createEl("span", {
            cls: "paperforge-meta",
            text: a("version_compare_paragraphs").replace(
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
            O =
              S.type === "added" ? "[+]" : S.type === "removed" ? "[-]" : "[~]",
            A = S.heading || "paragraph " + (S.paragraphIndex + 1);
          (C.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: O + " " + A,
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
      h = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      b = h.createEl("button", {
        cls: "pf-btn-primary",
        text: a("version_restore_selected"),
      }),
      v = h.createEl("button", {
        cls: "pf-btn-secondary",
        text: a("version_clear_old").replace("{size}", ""),
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
      (this._searchInput.placeholder = a("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var i;
        let s = ((i = this._searchInput) == null ? void 0 : i.value) || "";
        if (
          (s.startsWith("@") && !s.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = a(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = a(
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
        var i, o;
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
            !((i = this._searchResults) != null && i.length)
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
            p.forEach((u, f) => {
              f === this._searchActiveIndex
                ? (u.setAttribute("aria-selected", "true"),
                  u.classList.add("active"))
                : (u.setAttribute("aria-selected", "false"),
                  u.classList.remove("active"));
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
            ? a("retrieval_searching_deep")
            : a("retrieval_searching_metadata"),
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
          t.createEl("div", { text: a("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: a("retrieval_empty_tips"),
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
            text: a("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: a("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: a("retrieval_open_vector_settings"),
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
            text: a("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: a("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: a("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let i = this.app.vault.adapter.basePath;
          if (typeof i != "string") return;
          let o = this._resolvePython();
          if (!o) return;
          let { path: c, args: p = [] } = o;
          (0, fe.spawn)(c, [...p, "-m", "paperforge", "doctor"], {
            cwd: i,
            stdio: "inherit",
          });
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: a("retrieval_retry"),
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
            text: a("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: a("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: a("retrieval_retry"),
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
            text: a("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: a("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: a("retrieval_rebuild_vectors"),
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
            text: a("retrieval_internal_error"),
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
      i = "";
    if (s && typeof s == "object" && "basePath" in s) {
      let h = s.basePath;
      i = typeof h == "string" ? h : "";
    }
    if (!i) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let o = this._resolvePython();
    if (!o) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let { path: c, args: p = [] } = o,
      u = n === "retrieve" ? ["--deep"] : [],
      f = await ue({ app: this.app }, "memory", br(this.app)),
      _ = (0, fe.spawn)(
        c,
        [...p, "-m", "paperforge", "--vault", i, n, r, ...u, "--json"],
        { cwd: i, timeout: 3e4, env: f }
      ),
      g = [];
    (_.stdout.on("data", (h) => {
      g.push(h.toString("utf-8"));
    }),
      _.stderr.on("data", () => {}),
      _.on("close", (h) => {
        if (h !== 0) {
          let w = mt(String(h));
          ((this._searchState = this._mapErrorToSearchState(w.type)),
            this._renderSearchState());
          return;
        }
        let b = g.join(""),
          v = b.indexOf("{"),
          m = b.lastIndexOf("}"),
          E = "";
        if (v !== -1 && m > v) E = b.slice(v, m + 1);
        else {
          let w = b.indexOf("["),
            y = b.lastIndexOf("]");
          w !== -1 && y > w && (E = b.slice(w, y + 1));
        }
        if (!E) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let w = JSON.parse(E),
            y = [];
          if (w && typeof w == "object" && "data" in w) {
            let x = w.data;
            if (x && typeof x == "object") {
              let k = x;
              "matches" in k && Array.isArray(k.matches) && (y = k.matches);
            }
          }
          ((this._searchResults = y),
            (this._searchState = y.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (w) {
          let y = w instanceof Error ? w.message : String(w);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      _.on("error", (h) => {
        let b = h.code;
        if (typeof b == "string") {
          let v = mt(b);
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
        text: a("retrieval_results_count")
          .replace("{n}", String(e.length))
          .replace("{s}", e.length !== 1 ? "s" : ""),
      })
      .setAttr("aria-live", "polite"),
      r.createEl("span", {
        cls: "paperforge-search-mode",
        text: t ? "@" : "M",
      }));
    for (let s = 0; s < e.length; s++) {
      let i = e[s];
      if (!i || typeof i != "object") continue;
      let o = i,
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
      let u =
        typeof o.title == "string"
          ? o.title
          : typeof o.file_name == "string"
            ? o.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let f = typeof o.zotero_key == "string" ? o.zotero_key : "",
        _ =
          typeof o.main_note_path == "string" && o.main_note_path
            ? o.main_note_path
            : null,
        g = typeof o.note_path == "string" && o.note_path ? o.note_path : null,
        h = _ || g;
      if (!h && f) {
        let m = this._getCachedIndex().find(
          (E) =>
            E !== null &&
            typeof E == "object" &&
            "zotero_key" in E &&
            E.zotero_key === f
        );
        if (m && typeof m == "object") {
          let E = m;
          h =
            typeof E.main_note_path == "string" && E.main_note_path
              ? E.main_note_path
              : typeof E.note_path == "string" && E.note_path
                ? E.note_path
                : null;
        }
      }
      (h
        ? p.addEventListener("click", (v) => {
            let m = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(h, "", m);
          })
        : p.addEventListener("click", () => {
            new T.Notice("[!!] Note not found: " + (f || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (v) => {
          if (v.key === "Enter" && h) {
            v.preventDefault();
            let m = v.ctrlKey || v.metaKey;
            this.app.workspace.openLinkText(h, "", m);
          }
        }));
      let b = p.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof o.first_author == "string" &&
          o.first_author &&
          b.createEl("span", {
            cls: "paperforge-search-result-author",
            text: o.first_author,
          }),
        typeof o.journal == "string" &&
          o.journal &&
          b.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: o.journal,
          }),
        o.score !== void 0)
      ) {
        let v = o.score,
          m = typeof v == "number" ? v.toFixed(3) : String(v);
        b.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + m,
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
    if (e.disabled) {
      new T.Notice(
        `[i] ${e.disabledMsg || "This action is not yet available."}`,
        6e3
      );
      return;
    }
    if (t.classList.contains("running")) return;
    t.addClass("running");
    let r = this.app.vault.adapter.basePath;
    this._showMessage("Processing...", "running");
    let n = Array.isArray(e.args) ? [...e.args] : [];
    if (e.needsKey) {
      let h = this.app.workspace.getActiveFile(),
        b = null;
      if (h) {
        let v = this.app.metadataCache.getFileCache(h);
        if (
          (v && v.frontmatter && v.frontmatter.zotero_key
            ? (b = v.frontmatter.zotero_key)
            : (b = this._extractZoteroKeyFromPath(h.path)),
          b)
        )
          n = [...n, b];
        else if (v && v.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new T.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new T.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new T.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let s = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      i = this._resolvePython();
    if (!i) {
      (this._showMessage("[!!] Runtime not available", "error"),
        new T.Notice(
          "[!!] PaperForge runtime is not ready. Check settings.",
          6e3
        ),
        t.removeClass("running"));
      return;
    }
    let { path: o, args: c = [] } = i,
      p = await ue({ app: this.app }, e.cmd, br(this.app)),
      u = (0, fe.spawn)(o, [...c, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: s,
        env: p,
      }),
      f = [],
      _ = Date.now(),
      g = setInterval(() => this._fetchStats(!0), 4e3);
    (u.stdout.on("data", (h) => {
      let b = h
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let v of b) {
        let m = v.trim();
        m &&
          (f.push(m),
          this._showMessage(
            f.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      u.stderr.on("data", (h) => {
        let b = h
          .toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let v of b) {
          if (v.includes("\r") || v.includes("%") || v.includes("\u2588"))
            continue;
          let m = v.trim();
          m &&
            !m.match(/^\d+%|^\|/) &&
            (f.push(m),
            this._showMessage(
              f.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      u.on("close", (h) => {
        (clearInterval(g), t.removeClass("running"));
        let b = ((Date.now() - _) / 1e3).toFixed(1);
        if (h !== 0) {
          let v = f.slice(-3).join(" | ") || "exit code " + h;
          (e.cmd === "repair" || e.cmd === "ocr") && h === 1
            ? (this._showMessage("[WARN] " + v, "running"),
              new T.Notice("[WARN] " + e.cmd + " partial: " + v, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + v, "error"),
              new T.Notice("[!!] " + e.cmd + " failed: " + v, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let v = f.join(`
`);
          if (v.trim())
            try {
              (JSON.parse(v),
                navigator.clipboard
                  .writeText(v)
                  .then(() => {
                    let m = `${b}s \u2014 ${v.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + m, "ok"),
                      new T.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + v.length + " chars"
                      ));
                  })
                  .catch((m) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + m.message,
                      "error"
                    ),
                      new T.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (m) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new T.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    m.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new T.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let m =
              f.filter((w) => w.match(/updated \d+/)).pop() ||
              f[f.length - 1] ||
              "",
            E = `${b}s \u2014 ${m}`;
          (this._showMessage("[OK] " + e.title + ": " + E, "ok"),
            new T.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (w) {
            console.log("[PF] fetchStats error:", w);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              tt(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      u.on("error", (h) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + h.message, "error"),
          new T.Notice("[!!] Cannot start: " + h.message, 8e3));
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
          t.setText(a("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(a("version_panel_title")));
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
    let t = e.app.workspace.getLeavesOfType(ye);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: ye, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var ae = require("obsidian"),
  oe = H(require("fs")),
  we = H(require("path")),
  Pt = require("child_process");
var Oe = class extends ae.ItemView {
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
  }
  static async open(e) {
    let t = e.app.workspace.getLeavesOfType(ke);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getLeaf("tab");
    r &&
      (await r.setViewState({ type: ke, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
  getViewType() {
    return ke;
  }
  getDisplayText() {
    return a("ocr_ws_title");
  }
  getIcon() {
    return "scan-text";
  }
  async onOpen() {
    (await this._loadPapers(), this._render());
  }
  async _loadPapers() {
    var n, s, i, o, c, p, u, f, _, g, h;
    let e = this.app.vault.adapter.basePath,
      t = Q(e),
      r = we.join(t.indexesDir, "formal-library.json");
    if (!oe.existsSync(r)) {
      this.papers = [];
      return;
    }
    try {
      let b = JSON.parse(oe.readFileSync(r, "utf-8")),
        v = (n = b == null ? void 0 : b.items) != null ? n : [];
      this.papers = [];
      for (let m of v) {
        let E = m.zotero_key;
        if (!E) continue;
        let w = we.join(t.ocrDir, E, "meta.json"),
          y = {};
        if (oe.existsSync(w))
          try {
            y = JSON.parse(oe.readFileSync(w, "utf-8"));
          } catch (S) {}
        let x = we.join(t.ocrDir, E, "backups"),
          k = 0;
        (oe.existsSync(x) &&
          (k = oe
            .readdirSync(x)
            .filter((S) => S.startsWith("fulltext.pre-rebuild")).length),
          this.papers.push({
            key: E,
            title: (s = m.title) != null ? s : E,
            status:
              (o = (i = y.ocr_status) != null ? i : y.ocrStatus) != null
                ? o
                : "pending",
            pipelineVersion: (c = y.ocr_pipeline_version) != null ? c : "",
            lastRun:
              (u = (p = y.ocr_finished_at) != null ? p : y.ocrFinishedAt) !=
              null
                ? u
                : "",
            hasBackup: k > 0,
            authors:
              (g =
                (_ = (f = m.authors) == null ? void 0 : f.join) == null
                  ? void 0
                  : _.call(f, ", ")) != null
                ? g
                : "",
            year: (h = m.year) != null ? h : "",
            pages: y.page_count ? String(y.page_count) : "",
            backupCount: k,
          }));
      }
    } catch (b) {
      this.papers = [];
    }
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
      t = e.querySelector(".pf-ocr-ws-viewport"),
      r = e.querySelector(".pf-ocr-ws-batchbar"),
      n = e.querySelector(".pf-ocr-ws-detail"),
      s = e.querySelector(".pf-ocr-ws-toolbar-count"),
      i = this._filteredPapers();
    (s &&
      (s.innerHTML = a("ocr_ws_showing")
        .replace("{count}", String(i.length))
        .replace("{total}", String(this.papers.length))),
      t && t.remove());
    let o = e.createDiv({ cls: "pf-ocr-ws-viewport" });
    (this._buildTableBody(o, i),
      r && r.remove(),
      this._renderBatchBar(e),
      n && n.remove(),
      this.selectedKey && this._renderDetail(e));
  }
  _renderHeader(e) {
    let t = e.createDiv({ cls: "pf-ocr-ws-header" });
    (t.createEl("h1", { text: a("ocr_ws_title") }),
      t.createEl("p", { cls: "pf-ocr-ws-lede", text: a("ocr_ws_lede") }));
  }
  _renderActivity(e) {
    var f;
    let t = e.createDiv({
        cls: `pf-ocr-ws-activity${this.running ? " pf-active" : ""}`,
        attr: { "aria-live": "polite" },
      }),
      r = t.createDiv({ cls: "pf-ocr-ws-activity-head" }),
      n = r.createDiv({ cls: "pf-ocr-ws-activity-title" });
    n.setText(a("ocr_ws_processing"));
    let s = this.progress.paperKey;
    if (s) {
      let _ = this.papers.find((g) => g.key === s);
      n.createEl("span", {
        text: (f = _ == null ? void 0 : _.title) != null ? f : s,
      });
    }
    r.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: a("ocr_ws_stop"),
    }).addEventListener("click", () => this._stopBuild());
    let c = t
        .createDiv({ cls: "pf-ocr-ws-progress-track" })
        .createDiv({ cls: "pf-ocr-ws-progress-fill" }),
      p =
        this.progress.total > 0
          ? Math.round((this.progress.current / this.progress.total) * 100)
          : 0;
    c.style.transform = `scaleX(${p / 100})`;
    let u = t.createDiv({ cls: "pf-ocr-ws-progress-meta" });
    (u.createEl("span", {
      text: `${this.progress.current} / ${this.progress.total} papers`,
    }),
      u.createEl("span", { text: `${p}%` }));
  }
  _renderToolbar(e) {
    let t = this._filteredPapers(),
      r = [
        ...new Set(this.papers.map((u) => u.pipelineVersion).filter(Boolean)),
      ]
        .sort()
        .reverse(),
      n = e.createDiv({ cls: "pf-ocr-ws-toolbar" }),
      s = n.createDiv({ cls: "pf-ocr-ws-toolbar-count" });
    s.innerHTML = a("ocr_ws_showing")
      .replace("{count}", String(t.length))
      .replace("{total}", String(this.papers.length));
    let o = n
      .createDiv({ cls: "pf-ocr-ws-search" })
      .createEl("input", {
        cls: "pf-ocr-ws-search-input",
        attr: {
          type: "text",
          placeholder:
            a("ocr_ws_search_placeholder") ||
            "Search papers by title, author, year...",
        },
      });
    ((o.value = this._searchQuery),
      o.addEventListener("input", () => {
        ((this._searchQuery = o.value),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          this._refreshTable());
      }),
      o.addEventListener("keydown", (u) => {
        u.key === "Escape" &&
          ((o.value = ""),
          (this._searchQuery = ""),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          this._refreshTable(),
          o.blur());
      }));
    let c = n.createDiv({ cls: "pf-ocr-ws-field" });
    c.createEl("label", { text: a("ocr_ws_filter_status") });
    let p = c.createEl("select");
    for (let [u, f] of [
      ["all", a("ocr_ws_filter_all")],
      ["unprocessed", a("ocr_ws_filter_unprocessed")],
      ["review", a("ocr_ws_filter_review")],
      ["processed", a("ocr_ws_filter_processed")],
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
  _renderTable(e) {
    let t = this._filteredPapers(),
      r = e.createDiv({ cls: "pf-ocr-ws-viewport" });
    this._buildTableBody(r, t);
  }
  _buildTableBody(e, t) {
    if (t.length === 0) {
      e.createDiv({
        cls: "pf-ocr-ws-empty pf-visible",
        text: a("ocr_ws_no_papers"),
      });
      return;
    }
    let r = e.createEl("table", { cls: "pf-ocr-ws-table" }),
      s = r.createEl("thead").createEl("tr");
    (s
      .createEl("th", { cls: "pf-ocr-ws-col-check" })
      .createEl("input", { attr: { type: "checkbox" } }, (o) => {
        o.addEventListener("change", () => {
          (o.checked
            ? t.forEach((c) => this.checkedKeys.add(c.key))
            : this.checkedKeys.clear(),
            this._refreshTable());
        });
      }),
      s.createEl("th", {
        cls: "pf-ocr-ws-col-paper",
        text: a("ocr_ws_col_title"),
      }),
      s.createEl("th", {
        cls: "pf-ocr-ws-col-status",
        text: a("ocr_ws_col_status"),
      }),
      s.createEl("th", {
        cls: "pf-ocr-ws-col-version",
        text: a("ocr_ws_col_version"),
      }),
      s.createEl("th", {
        cls: "pf-ocr-ws-col-date",
        text: a("ocr_ws_col_lastrun"),
      }),
      s.createEl("th", { cls: "pf-ocr-ws-col-action" }));
    let i = r.createEl("tbody");
    for (let o of t) {
      let c = !!this.papers.find(
          (m) =>
            m.pipelineVersion &&
            o.pipelineVersion &&
            m.pipelineVersion > o.pipelineVersion
        ),
        p = i.createEl("tr", { cls: c ? "pf-update" : "" });
      (p.addEventListener("click", (m) => {
        m.target.tagName !== "INPUT" &&
          ((this.selectedKey = o.key === this.selectedKey ? null : o.key),
          this._refreshTable());
      }),
        p
          .createEl("td", { cls: "pf-ocr-ws-col-check" })
          .createEl("input", { attr: { type: "checkbox" } }, (m) => {
            ((m.checked = this.checkedKeys.has(o.key)),
              m.addEventListener("change", () => {
                (m.checked
                  ? this.checkedKeys.add(o.key)
                  : this.checkedKeys.delete(o.key),
                  this._refreshTable());
              }));
          }));
      let f = p.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      if (
        (f.createDiv({ cls: "pf-ocr-ws-paper-title", text: o.title }),
        o.authors || o.year)
      ) {
        let m = f.createDiv({ cls: "pf-ocr-ws-paper-meta" });
        if (o.authors) {
          let E = o.authors.split(",")[0].trim(),
            w = o.authors.includes(",") ? " et al." : "";
          m.createEl("span", { cls: "pf-ocr-ws-meta-author", text: E + w });
        }
        o.year &&
          m.createEl("span", { cls: "pf-ocr-ws-meta-year", text: o.year });
      }
      (p
        .createEl("td", { cls: "pf-ocr-ws-col-status" })
        .createEl("span", {
          cls: `pf-ocr-ws-status pf-${vr(o.status)}`,
          text: Er(o.status),
        }),
        p
          .createEl("td", { cls: "pf-ocr-ws-col-version" })
          .createEl("span", {
            cls: "pf-ocr-ws-version",
            text: o.pipelineVersion || "\u2014",
          }),
        p
          .createEl("td", { cls: "pf-ocr-ws-col-date" })
          .setText(o.lastRun ? o.lastRun.slice(0, 10) : "\u2014"),
        p
          .createEl("td", { cls: "pf-ocr-ws-col-action" })
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: a("ocr_ws_btn_preview"),
          })
          .addEventListener("click", (m) => {
            (m.stopPropagation(), this._openFulltext(o.key));
          }));
    }
  }
  _renderBatchBar(e) {
    let t = this.papers.filter((c) => this.checkedKeys.has(c.key)),
      r = e.createDiv({ cls: "pf-ocr-ws-batchbar" }),
      n = r.createDiv({ cls: "pf-ocr-ws-selection" });
    t.length === 0
      ? (n.createEl("strong", { text: a("ocr_ws_none_selected") }),
        n.createEl("span", { text: a("ocr_ws_select_hint") }))
      : n.createEl("strong", {
          text: a("ocr_ws_selected").replace("{count}", String(t.length)),
        });
    let s = r.createDiv({ cls: "pf-ocr-ws-batch-actions" }),
      i = s.createEl("button", {
        cls: "pf-btn pf-btn-primary",
        text: a("ocr_ws_btn_process_selected"),
      });
    ((i.disabled = t.length === 0),
      i.addEventListener("click", () => this._runOcr(t.map((c) => c.key))));
    let o = s.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: a("ocr_ws_btn_update_selected"),
    });
    ((o.disabled = t.length === 0),
      o.addEventListener("click", () => this._runRebuild(t.map((c) => c.key))));
  }
  _renderDetail(e) {
    let t = this.papers.find((b) => b.key === this.selectedKey);
    if (!t) return;
    let n = e
        .createDiv({ cls: "pf-ocr-ws-detail pf-open" })
        .createDiv({ cls: "pf-ocr-ws-detail-card" }),
      s = n.createDiv({ cls: "pf-ocr-ws-detail-head" }),
      i = s.createDiv({});
    (i.createEl("h2", { text: t.title }),
      i.createEl("span", {
        cls: `pf-ocr-ws-status pf-${vr(t.status)}`,
        text: Er(t.status),
      }),
      s
        .createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          text: a("ocr_ws_close"),
        })
        .addEventListener("click", () => {
          ((this.selectedKey = null), this._refreshTable());
        }));
    let c = n.createDiv({ cls: "pf-ocr-ws-detail-grid" });
    (this._addFact(c, a("ocr_ws_fact_version"), t.pipelineVersion || "\u2014"),
      this._addFact(
        c,
        a("ocr_ws_fact_last_run"),
        t.lastRun ? t.lastRun.slice(0, 10) : "\u2014"
      ),
      this._addFact(c, a("ocr_ws_fact_authors"), t.authors || "\u2014"),
      this._addFact(c, a("ocr_ws_fact_year"), t.year || "\u2014"),
      this._addFact(c, a("ocr_ws_fact_pages"), t.pages || "\u2014"),
      this._addFact(
        c,
        a("ocr_ws_fact_backups"),
        t.backupCount > 0 ? String(t.backupCount) : "\u2014"
      ));
    let p = n.createDiv({ cls: "pf-impact-box" });
    (p.createEl("strong", { text: a("ocr_ws_re_extract_disabled_title") }),
      p.createEl("p", { text: a("ocr_ws_re_extract_disabled_body") }));
    let u = n.createDiv({ cls: "pf-ocr-ws-detail-actions" });
    u.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: a("ocr_ws_detail_view_fulltext"),
    }).addEventListener("click", () => this._openFulltext(t.key));
    let _ = u.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: a("ocr_ws_detail_restore_backup"),
    });
    ((_.disabled = !t.hasBackup),
      _.addEventListener("click", () => {
        new ae.Notice("Version history panel not yet integrated");
      }));
    let g = u.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: a("ocr_ws_detail_re_extract"),
    });
    g.disabled = !0;
    let h = n.createEl("details");
    (h.createEl("summary", { text: a("ocr_ws_what_happens") }),
      h.createEl("p", { text: a("ocr_ws_disclosure_text") }));
  }
  _addFact(e, t, r) {
    let n = e.createDiv({ cls: "pf-ocr-ws-fact" });
    (n.createEl("dt", { text: t }), n.createEl("dd", { text: r }));
  }
  _resolvePython() {
    var s, i;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (i =
          (s = e == null ? void 0 : e.settings) == null
            ? void 0
            : s.python_path) == null
          ? void 0
          : i.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    if (!e || typeof e.getManagedRuntime != "function") return null;
    let r = e.getManagedRuntime();
    if (!r) return null;
    let n = _e(r.current());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  _runOcr(e) {
    let t = this._resolvePython();
    if (!t) {
      new ae.Notice("Runtime not ready");
      return;
    }
    let r = this.app.vault.adapter.basePath;
    ((this.running = !0),
      (this.progress = { current: 0, total: e.length, paperKey: "" }),
      this._render(),
      (0, Pt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "ocr", "run", ...e],
        { cwd: r, timeout: 6e5 },
        (n) => {
          ((this.running = !1),
            n
              ? new ae.Notice("OCR failed: " + (n.message || n))
              : new ae.Notice("OCR completed"),
            this._loadPapers().then(() => this._render()));
        }
      ));
  }
  _runRebuild(e) {
    let t = this._resolvePython();
    if (!t) {
      new ae.Notice("Runtime not ready");
      return;
    }
    let r = this.app.vault.adapter.basePath;
    ((this.running = !0),
      (this.progress = { current: 0, total: e.length, paperKey: "" }),
      this._render(),
      (0, Pt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "ocr", "rebuild", ...e],
        { cwd: r, timeout: 6e5 },
        (n) => {
          ((this.running = !1),
            n
              ? new ae.Notice("Rebuild failed: " + (n.message || n))
              : new ae.Notice("Rebuild completed"),
            this._loadPapers().then(() => this._render()));
        }
      ));
  }
  _stopBuild() {
    ((this.running = !1), this._render());
  }
  _openFulltext(e) {
    let t = this.app.vault.adapter.basePath,
      r = Q(t),
      n = we.join(t, r.systemDir, "PaperForge", "ocr", e, "fulltext.md");
    if (!oe.existsSync(n)) {
      new ae.Notice("Fulltext not found");
      return;
    }
    let s = this.app.vault.getAbstractFileByPath(
      we.relative(t, n).replace(/\\/g, "/")
    );
    s
      ? this.app.workspace.getLeaf().openFile(s)
      : new ae.Notice("Fulltext not found in vault");
  }
};
function vr(d) {
  return d === "done"
    ? "pf-done"
    : d === "done_degraded"
      ? "pf-done-degraded"
      : d === "done_incomplete"
        ? "pf-done-incomplete"
        : d === "failed" || d === "error" || d === "fatal_error"
          ? "pf-failed"
          : d === "retryable_error"
            ? "pf-error"
            : d === "processing" || d === "running"
              ? "pf-running"
              : d === "queued"
                ? "pf-queued"
                : d === "blocked"
                  ? "pf-blocked"
                  : "pf-pending";
}
function Er(d) {
  return d === "done"
    ? a("ocr_ws_status_done") || "Processed"
    : d === "done_degraded"
      ? a("ocr_ws_status_degraded") || "Partial"
      : d === "done_incomplete"
        ? a("ocr_ws_status_incomplete") || "Incomplete"
        : d === "failed" || d === "error" || d === "fatal_error"
          ? a("ocr_ws_status_failed") || "Failed"
          : d === "retryable_error"
            ? a("ocr_ws_status_error") || "Error"
            : d === "processing" || d === "running"
              ? a("ocr_ws_status_processing") || "Processing"
              : d === "queued"
                ? a("ocr_ws_status_queued") || "Queued"
                : d === "blocked"
                  ? a("ocr_ws_status_blocked") || "Blocked"
                  : d === "nopdf"
                    ? a("ocr_ws_status_nopdf") || "No PDF"
                    : a("ocr_ws_status_pending") || "Pending";
}
var it = class extends U.Plugin {
  constructor() {
    super(...arguments);
    this._lastExportMtime = 0;
    this._lastOcrMtimes = {};
    this._autoSyncRunning = !1;
    this._lastSyncTime = null;
    this._pollTimer = null;
    this._embedProcess = null;
    this._embedProgress = { current: 0, total: 0, key: "" };
    this._embedStderr = "";
    this._memoryStatusText = null;
    this._managedRuntime = null;
  }
  getManagedRuntime() {
    return (
      this._managedRuntime ||
        (this._managedRuntime = new ve({ version: this.manifest.version })),
      this._managedRuntime
    );
  }
  _getPythonCommand() {
    let e = _e(this.getManagedRuntime().current());
    return e ? { path: e.command, args: [...e.args] } : null;
  }
  async onload() {
    (await this.loadSettings(),
      await Yt(
        {
          app: { secretStorage: this.app.secretStorage },
          saveData: async () => this.saveSettings(),
        },
        this.settings
      ),
      await this.saveSettings());
    try {
      await this.getManagedRuntime().status();
    } catch (t) {}
    (Ht(this.app, this.settings.language),
      this.registerView(ye, (t) => new Le(t)),
      this.registerView(ke, (t) => new Oe(t, this)));
    try {
      (0, U.addIcon)(Ne, Ot);
    } catch (t) {}
    (this.addRibbonIcon(Ne, "PaperForge Dashboard", () => Le.open(this)),
      this.addRibbonIcon("scan-text", "PaperForge OCR Workspace", () =>
        Oe.open(this)
      ),
      re.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", async () => {
          let t = this.app.vault.adapter.basePath;
          new U.Notice("PaperForge: Redo OCR starting...");
          let r = this._getPythonCommand();
          if (!r) {
            new U.Notice("Runtime not ready");
            return;
          }
          let { path: n, args: s } = r,
            i = await ue(this, "ocr");
          (0, Ie.execFile)(
            n,
            [...s, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5, env: i },
            (o, c, p) => {
              if (o) {
                new U.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new U.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new at(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: a("guide_open"),
        callback: () => Le.open(this),
      }),
      this.addCommand({
        id: "paperforge-ocr-workspace",
        name: "Open OCR Workspace",
        callback: () => Oe.open(this),
      }));
    for (let t of re)
      this.addCommand({
        id: t.id,
        name: t.title,
        callback: async () => {
          if (t.disabled) {
            new U.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new U.Notice(`PaperForge: running ${t.cmd}...`);
          let n = this._getPythonCommand();
          if (!n) {
            new U.Notice("Runtime not ready");
            return;
          }
          let { path: s, args: i = [] } = n,
            o = Array.isArray(t.args) ? [...t.args] : [],
            c = await ue(this, t.cmd);
          (0, Ie.execFile)(
            s,
            [...i, "-m", "paperforge", t.cmd, ...o],
            { cwd: r, timeout: 3e5, env: c },
            (p, u, f) => {
              if (p) {
                new U.Notice(
                  `[!!] ${t.cmd} failed: ${(f || p.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new U.Notice(
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
    (this._startFilePolling(), this._checkReleaseNotes());
  }
  _startFilePolling() {
    let e = this.app.vault.adapter.basePath;
    this._pollTimer = setInterval(() => {
      (this._checkExports(e), this._checkOcr(e));
    }, 12e4);
  }
  _checkExports(e) {
    if (this._autoSyncRunning) return;
    let t = Q(e).exportsDir;
    if (!q.existsSync(t)) return;
    let r = 0;
    try {
      q.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let s = q.statSync(Be.join(t, n));
        s.mtimeMs > r && (r = s.mtimeMs);
      });
    } catch (n) {
      return;
    }
    r > this._lastExportMtime &&
      ((this._lastExportMtime = r), this._autoSync(e));
  }
  _autoSync(e) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = !0;
    let t = this._getPythonCommand();
    if (!t) {
      this._autoSyncRunning = !1;
      return;
    }
    let r = `"${t.path}" ${t.args.join(" ")} -m paperforge --vault "${e}" sync`;
    (0, Ie.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, s, i) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let o = Q(e).exportsDir,
          c = 0;
        (q.readdirSync(o).forEach((p) => {
          p.endsWith(".json") &&
            (c = Math.max(c, q.statSync(Be.join(o, p)).mtimeMs));
        }),
          (this._lastExportMtime = c));
      } catch (o) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = Q(e).ocrDir;
    if (q.existsSync(t))
      try {
        q.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = Be.join(t, r.name, "meta.json");
          if (!q.existsSync(n)) return;
          let s = q.statSync(n),
            i = this._lastOcrMtimes[r.name] || 0;
          if (
            s.mtimeMs <= i ||
            ((this._lastOcrMtimes[r.name] = s.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let o = this._getPythonCommand();
          if (!o) {
            this._autoSyncRunning = !1;
            return;
          }
          let c = `"${o.path}" ${o.args.join(" ")} -m paperforge --vault "${e}" sync`;
          (0, Ie.exec)(c, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = Be.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
        zotero_data_dir: "",
      };
    try {
      if (!q.existsSync(t)) return r;
      let n = q.readFileSync(t, "utf-8"),
        s = JSON.parse(n),
        i = s.vault_config || {};
      return {
        system_dir: i.system_dir || s.system_dir || r.system_dir,
        resources_dir: i.resources_dir || s.resources_dir || r.resources_dir,
        literature_dir:
          i.literature_dir || s.literature_dir || r.literature_dir,
        base_dir: i.base_dir || s.base_dir || r.base_dir,
        zotero_data_dir: s.zotero_data_dir || r.zotero_data_dir,
      };
    } catch (n) {
      return (
        console.warn(
          "PaperForge: Failed to read paperforge.json, using defaults",
          n
        ),
        r
      );
    }
  }
  savePaperforgeJson(e) {
    let t = this.app.vault.adapter.basePath,
      r = Be.join(t, "paperforge.json"),
      n = {};
    try {
      q.existsSync(r) && (n = JSON.parse(q.readFileSync(r, "utf-8")));
    } catch (i) {
      console.warn("PaperForge: Failed to read paperforge.json for update", i);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let s = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let i of s) e[i] !== void 0 && (n.vault_config[i] = e[i]);
    (e.zotero_data_dir !== void 0 && (n.zotero_data_dir = e.zotero_data_dir),
      n.schema_version || (n.schema_version = "2"));
    for (let i of s) delete n[i];
    try {
      if (
        (q.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let i = this.readPaperforgeJson();
        ((this.settings.system_dir = i.system_dir),
          (this.settings.resources_dir = i.resources_dir),
          (this.settings.literature_dir = i.literature_dir),
          (this.settings.base_dir = i.base_dir));
      }
    } catch (i) {
      (console.error("PaperForge: Failed to write paperforge.json", i),
        new U.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(ye));
  }
  async loadSettings() {
    var n, s;
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
    let r = this.readPaperforgeJson();
    if (
      ((this.settings.system_dir = r.system_dir),
      (this.settings.resources_dir = r.resources_dir),
      (this.settings.literature_dir = r.literature_dir),
      (this.settings.base_dir = r.base_dir),
      r.zotero_data_dir
        ? (this.settings.zotero_data_dir = r.zotero_data_dir)
        : (s = this.settings.zotero_data_dir) != null &&
          s.trim() &&
          this.savePaperforgeJson({
            zotero_data_dir: this.settings.zotero_data_dir.trim(),
          }),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let i = this.settings.python_path.trim();
      this.settings._python_path_stale = !q.existsSync(i);
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
    let s = (ft().versions || []).find((o) => o.version === e);
    class i extends U.Modal {
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
          if (this._entry.new_features && this._entry.new_features.length > 0) {
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
        new U.Setting(c).addButton((p) =>
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
    (new i(this.app, s).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
