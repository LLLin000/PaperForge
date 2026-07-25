"use strict";
var vr = Object.create;
var We = Object.defineProperty;
var Er = Object.getOwnPropertyDescriptor;
var xr = Object.getOwnPropertyNames;
var wr = Object.getPrototypeOf,
  kr = Object.prototype.hasOwnProperty;
var Sr = (d, c) => () => (c || d((c = { exports: {} }).exports, c), c.exports),
  Pr = (d, c) => {
    for (var e in c) We(d, e, { get: c[e], enumerable: !0 });
  },
  Rt = (d, c, e, t) => {
    if ((c && typeof c == "object") || typeof c == "function")
      for (let r of xr(c))
        !kr.call(d, r) &&
          r !== e &&
          We(d, r, {
            get: () => c[r],
            enumerable: !(t = Er(c, r)) || t.enumerable,
          });
    return d;
  };
var N = (d, c, e) => (
    (e = d != null ? vr(wr(d)) : {}),
    Rt(
      c || !d || !d.__esModule
        ? We(e, "default", { value: d, enumerable: !0 })
        : e,
      d
    )
  ),
  Cr = (d) => Rt(We({}, "__esModule", { value: !0 }), d);
var ut = Sr((en, Tr) => {
  Tr.exports = {
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
Pr(Jr, { default: () => at });
module.exports = Cr(Jr);
var q = require("obsidian"),
  K = N(require("fs")),
  Be = N(require("path")),
  Me = require("child_process");
var be = "paperforge-status",
  Se = "paperforge-ocr-workspace",
  Ne = "paperforge",
  Tt =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  te = [
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
  He = {
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
function Ot(d, c) {
  if (!c || !c.note_path) return c;
  let e = d.vault.getAbstractFileByPath(c.note_path);
  if (!e) return c;
  let t = d.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return c;
  let n = { ...c };
  for (let i of [
    "do_ocr",
    "analyze",
    "ocr_status",
    "ocr_redo",
    "deep_reading_status",
  ])
    Object.prototype.hasOwnProperty.call(r, i) && (n[i] = r[i]);
  return n;
}
function it(d, c) {
  return d && { ...d, ...c };
}
var Ze = 2,
  Ve = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  Rr = new Set([
    "checking",
    "ready",
    "not_enabled",
    "setup_required",
    "action_required",
    "detection_failed",
  ]),
  Ft = new Set([
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ]),
  Fr = new Set(["unknown", "ok", "warning", "error"]),
  Dt = new Set(["idle", "running"]),
  Dr = new Set(["safe", "destructive", "irreversible"]);
function At(d) {
  if (!d || typeof d != "object" || Array.isArray(d)) return !1;
  let c = d;
  return !(
    typeof c.action_id != "string" ||
    !c.action_id ||
    typeof c.verb != "string" ||
    typeof c.label != "string" ||
    typeof c.availability != "string" ||
    typeof c.safety_class != "string" ||
    !Dr.has(c.safety_class) ||
    !Array.isArray(c.preservation_facts) ||
    !Array.isArray(c.replacement_facts) ||
    typeof c.interruptible != "boolean" ||
    typeof c.confirmation_required != "boolean" ||
    (c.confirmation_prompt !== null &&
      typeof c.confirmation_prompt != "string") ||
    typeof c.command != "string" ||
    typeof c.scope != "string" ||
    typeof c.scope_count != "number"
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
    command: "probe " + d,
    scope: d,
    scope_count: 1,
  };
}
function Lt() {
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
function ot(d, c) {
  if (!d || typeof d != "object") return !1;
  let e = d;
  if (
    e.schema_version !== Ze ||
    typeof e.module != "string" ||
    !e.module ||
    !Ve.includes(e.module) ||
    (c !== void 0 && e.module !== c) ||
    typeof e.capability_state != "string" ||
    !Ft.has(e.capability_state) ||
    typeof e.activity_state != "string" ||
    !Dt.has(e.activity_state) ||
    typeof e.user_state != "string" ||
    !Rr.has(e.user_state) ||
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
    (r.primary !== null && !At(r.primary)) ||
    typeof e.updated_at != "string" ||
    !e.updated_at ||
    typeof e.ttl_seconds != "number"
  )
    return !1;
  if (e.module === "maintenance") {
    if (r.primary !== null || !Array.isArray(e.items)) return !1;
    for (let n of e.items) {
      if (!n || typeof n != "object") return !1;
      let i = n,
        s = ["installation", "library", "ocr", "memory", "help"];
      if (
        typeof i.capability_state != "string" ||
        !Ft.has(i.capability_state) ||
        typeof i.severity != "string" ||
        !Fr.has(i.severity) ||
        typeof i.activity_state != "string" ||
        !Dt.has(i.activity_state) ||
        (i.activity_label !== null && typeof i.activity_label != "string")
      )
        return !1;
      if (i.activity_progress !== null) {
        if (typeof i.activity_progress != "object") return !1;
        let o = i.activity_progress;
        if (typeof o.current != "number" || typeof o.total != "number")
          return !1;
      }
      if (
        typeof i.reason_code != "string" ||
        !i.reason_code ||
        typeof i.reason_text != "string" ||
        (i.action !== null && !At(i.action))
      )
        return !1;
    }
  }
  return !0;
}
function se(d) {
  return {
    schema_version: Ze,
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
function lt(d) {
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
function ct(d) {
  if (d.activity_state === "running") return !1;
  if (d.ttl_seconds <= 0) return !0;
  let c = new Date(d.updated_at).getTime();
  return isNaN(c) ? !0 : Date.now() - c > d.ttl_seconds * 1e3;
}
function Bt(d) {
  return d.capability_state === "ready" && d.action.primary === null;
}
function Mt(d) {
  var r, n, i;
  let c = (r = d.action) == null ? void 0 : r.primary,
    e = (n = c == null ? void 0 : c.verb) != null ? n : "probe",
    t = (i = c == null ? void 0 : c.label) != null ? i : e;
  return e === "setup" || e === "set_config" || e === "update"
    ? { kind: "setup", verb: e, label: t }
    : e === "probe"
      ? { kind: "probe", verb: e, label: t }
      : { kind: "action", verb: e, label: t };
}
function It(d, c) {
  let e = {};
  for (let t of c) {
    let r = d[t];
    if (!r || typeof r != "object") {
      e[t] = se(t);
      continue;
    }
    if (!ot(r, t)) {
      e[t] = Pe(t);
      continue;
    }
    if (ct(r)) {
      e[t] = lt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var pt = {
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
        "PaperForge needs a verified environment on this device.",
      setup_ready: "Foundation is ready.",
      setup_library_title: "Step 2: Connect Library",
      setup_library_desc:
        "Connect Zotero so PaperForge can sync your literature.",
      setup_library_ready: "Library is connected.",
      setup_optionals_title: "Step 3: Optional Capabilities",
      setup_optionals_desc:
        "Choose only what you need. Skipped capabilities can be enabled later.",
      setup_opt_ocr_desc: "Extract text and figures from PDFs",
      setup_opt_memory_desc: "Search and navigate across your papers",
      setup_opt_agent_desc: "Deploy and manage PaperForge Skills",
      setup_review_title: "Step 4: Review & Begin",
      setup_review_selected: "Selected: ",
      setup_no_optionals: "No optional capabilities selected.",
      setup_incomplete_warn:
        "Foundation and Library must be ready before setup can finish.",
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
      sr_action_build: "Build Memory",
      sr_action_rebuild: "Rebuild Index",
      sr_action_upgrade: "Upgrade to vec0",
      sr_upgrade_modal_title: "Upgrade Vector Index",
      sr_upgrade_modal_description:
        "This will rebuild your entire vector index using the new vec0 backend.",
      sr_upgrade_modal_safety:
        "Your existing ChromaDB data is preserved. This process requires an active API key and may incur API charges.",
      sr_api_key_notice:
        "API key not configured \u2014 search and retrieval are unavailable",
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
      api_key_missing: "\u672A\u914D\u7F6E \u2717",
      api_key_set: "\u5DF2\u914D\u7F6E \u2713",
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
        "PaperForge \u9700\u8981\u5728\u6B64\u8BBE\u5907\u4E0A\u51C6\u5907\u597D\u7ECF\u8FC7\u9A8C\u8BC1\u7684\u8FD0\u884C\u73AF\u5883\u3002",
      setup_ready: "\u57FA\u7840\u73AF\u5883\u5DF2\u5C31\u7EEA\u3002",
      setup_library_title:
        "\u7B2C 2 \u6B65\uFF1A\u8FDE\u63A5\u6587\u732E\u5E93",
      setup_library_desc:
        "\u8FDE\u63A5 Zotero\uFF0C\u8BA9 PaperForge \u53EF\u4EE5\u540C\u6B65\u6587\u732E\u3002",
      setup_library_ready: "\u6587\u732E\u5E93\u5DF2\u8FDE\u63A5\u3002",
      setup_optionals_title: "\u7B2C 3 \u6B65\uFF1A\u53EF\u9009\u529F\u80FD",
      setup_optionals_desc:
        "\u53EA\u9009\u62E9\u9700\u8981\u7684\u529F\u80FD\uFF1B\u8DF3\u8FC7\u540E\u4ECD\u53EF\u968F\u65F6\u542F\u7528\u3002",
      setup_opt_ocr_desc:
        "\u4ECE PDF \u63D0\u53D6\u6587\u672C\u548C\u56FE\u8868",
      setup_opt_memory_desc: "\u8DE8\u8BBA\u6587\u641C\u7D22\u548C\u6D4F\u89C8",
      setup_opt_agent_desc: "\u90E8\u7F72\u5E76\u7BA1\u7406 PaperForge Skills",
      setup_review_title: "\u7B2C 4 \u6B65\uFF1A\u68C0\u67E5\u5E76\u5F00\u59CB",
      setup_review_selected: "\u5DF2\u9009\u62E9\uFF1A",
      setup_no_optionals: "\u672A\u9009\u62E9\u53EF\u9009\u529F\u80FD\u3002",
      setup_incomplete_warn:
        "\u57FA\u7840\u73AF\u5883\u548C\u6587\u732E\u5E93\u5747\u5C31\u7EEA\u540E\u624D\u80FD\u5B8C\u6210\u8BBE\u7F6E\u3002",
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
      sr_action_build: "\u6784\u5EFA\u8BB0\u5FC6\u5E93",
      sr_action_rebuild: "\u91CD\u5EFA\u7D22\u5F15",
      sr_action_upgrade: "\u5347\u7EA7\u5230 vec0",
      sr_upgrade_modal_title: "\u5347\u7EA7\u5411\u91CF\u7D22\u5F15",
      sr_upgrade_modal_description:
        "\u8FD9\u5C06\u4F7F\u7528\u65B0\u7684 vec0 \u540E\u7AEF\u91CD\u5EFA\u6574\u4E2A\u5411\u91CF\u7D22\u5F15\u3002",
      sr_upgrade_modal_safety:
        "\u73B0\u6709 ChromaDB \u6570\u636E\u4F1A\u5F97\u5230\u4FDD\u7559\u3002\u6B64\u8FC7\u7A0B\u9700\u8981\u6709\u6548\u7684 API Key \u5E76\u53EF\u80FD\u4EA7\u751F API \u8D39\u7528\u3002",
      sr_api_key_notice:
        "API Key \u672A\u914D\u7F6E \u2014 \u641C\u7D22\u548C\u68C0\u7D22\u4E0D\u53EF\u7528",
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
  dt = null;
function Ar(d) {
  try {
    let c = d.vault;
    if (typeof c.getConfig == "function") {
      let e = c.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (c) {}
  try {
    if (typeof localStorage != "undefined") {
      let c = localStorage.getItem("language");
      if (c && String(c).startsWith("zh")) return "zh";
    }
  } catch (c) {}
  try {
    let c = document.documentElement.lang || navigator.language;
    if (c && c.startsWith("zh")) return "zh";
  } catch (c) {}
  return "en";
}
function Nt(d, c = "") {
  dt = (c || Ar(d)).startsWith("zh") ? pt.zh : pt.en;
}
function a(d) {
  return (dt && dt[d]) || pt.en[d] || d;
}
var R = require("obsidian"),
  H = N(require("fs")),
  Z = N(require("path")),
  ur = N(require("os")),
  ne = require("child_process");
var _r = N(ut());
var Or = {
    checking: "pf-badge pf-badge--checking",
    ready: "pf-badge pf-badge--ready",
    not_enabled: "pf-badge pf-badge--not-enabled",
    setup_required: "pf-badge pf-badge--setup-required",
    action_required: "pf-badge pf-badge--action-required",
    detection_failed: "pf-badge pf-badge--detection-failed",
  },
  Lr = {
    checking: "Checking",
    ready: "Ready",
    not_enabled: "Not Enabled",
    setup_required: "Setup Required",
    action_required: "Action Required",
    detection_failed: "Detection Failed",
  };
function Y(d, c, e) {
  return d.createEl("span", {
    cls: Or[c],
    text: e != null ? e : Lr[c],
    attr: { role: "status" },
  });
}
function Ht(d, c) {
  let e = d.createEl("div", { cls: "pf-activity-row" }),
    t = e.createEl("span", { cls: "pf-activity-label", text: c.label });
  if (c.progress && c.progress.total > 0) {
    let r = e.createEl("div", { cls: "pf-activity-bar" }),
      n = Math.round((c.progress.current / c.progress.total) * 100);
    (r.createEl("div", {
      cls: "pf-activity-bar-fill",
      attr: {
        style: `width: ${n}%`,
        role: "progressbar",
        "aria-valuenow": String(c.progress.current),
        "aria-valuemin": "1",
        "aria-valuemax": String(c.progress.total),
      },
    }),
      e.createEl("span", {
        cls: "pf-activity-count",
        text: `${c.progress.current}/${c.progress.total}`,
      }));
  } else
    e.createEl("span", { cls: "pf-activity-spinner" }).setAttr(
      "aria-label",
      "In progress"
    );
  if (
    (c.scope && e.createEl("span", { cls: "pf-activity-scope", text: c.scope }),
    c.stopLabel && c.onStop)
  ) {
    let r = e.createEl("button", {
      cls: "pf-activity-stop",
      text: c.stopLabel,
    });
    (r.addEventListener("click", c.onStop),
      r.addEventListener("keydown", (n) => {
        var i;
        (n.key === "Enter" || n.key === " ") &&
          (n.preventDefault(), (i = c.onStop) == null || i.call(c));
      }));
  }
  return e;
}
function z(d, c) {
  let e = d.createEl("button", {
    cls: "pf-action-btn",
    text: c.loading ? "\u2026" : c.label,
  });
  return (
    (c.disabled || c.loading) &&
      (e.setAttr("disabled", "true"),
      e.classList.add("pf-action-btn--disabled")),
    c.loading && e.classList.add("pf-action-btn--loading"),
    !c.disabled &&
      !c.loading &&
      (e.addEventListener("click", c.onClick),
      e.addEventListener("keydown", (t) => {
        (t.key === "Enter" || t.key === " ") &&
          (t.preventDefault(), c.onClick());
      })),
    e
  );
}
function Vt(d, c) {
  let e = d.createEl("div", { cls: "pf-error-anatomy" });
  e.createEl("div", { cls: "pf-error-title", text: c.whatHappened });
  let t = e.createEl("div", { cls: "pf-error-impact" });
  (t.createEl("span", {
    cls: "pf-error-impact-label",
    text: (c.impactLabel || "Impact:") + " ",
  }),
    t.createEl("span", { text: c.impact }),
    c.reasonCode &&
      e.createEl("div", { cls: "pf-error-code", text: c.reasonCode }));
  let r = e.createEl("div", { cls: "pf-error-next" });
  return (
    r.createEl("span", {
      cls: "pf-error-next-label",
      text: (c.nextLabel || "Next:") + " ",
    }),
    r.createEl("span", { text: c.nextStep }),
    c.onCopyDiagnostic &&
      e
        .createEl("button", {
          cls: "pf-error-copy-diagnostic",
          text: c.copyLabel || "Copy Diagnostic Information",
        })
        .addEventListener("click", c.onCopyDiagnostic),
    e
  );
}
function jt(d, c) {
  let e = d.createEl("div", { cls: "pf-config-summary" });
  for (let r of c.items) {
    let n = e.createEl("div", { cls: "pf-config-row" });
    n.createEl("span", { cls: "pf-config-label", text: r.label });
    let i = r.isCredential
      ? r.value
        ? c.configuredLabel || "Configured"
        : c.notConfiguredLabel || "Not configured"
      : r.value;
    n.createEl("span", {
      cls: `pf-config-value${r.isCredential ? (r.value ? " pf-config-value--ok" : " pf-config-value--muted") : ""}`,
      text: i,
    });
  }
  return (
    e
      .createEl("button", {
        cls: "pf-config-change-btn",
        text: c.onChangeLabel,
      })
      .addEventListener("click", c.onChange),
    e
  );
}
function zt(d) {
  let c = [];
  (c.push("=== PaperForge Support Diagnostic ==="),
    c.push(`Time: ${new Date().toISOString()}`),
    c.push(`Plugin: ${d.pluginVersion}`),
    d.backendVersion && c.push(`Backend: ${d.backendVersion}`),
    c.push(""),
    c.push("--- Module Status ---"));
  for (let e of d.modules)
    (c.push(`${e.module}: ${e.userState}`),
      e.reasonCode && c.push(`  reason: ${e.reasonCode}`),
      e.actionId && c.push(`  action: ${e.actionId}`),
      e.lastSuccessAt && c.push(`  last-success: ${e.lastSuccessAt}`),
      e.errorExcerpt && c.push(`  error: ${e.errorExcerpt}`));
  return (
    c.push(""),
    c.push("=== End ==="),
    c.join(`
`)
  );
}
function $t(d, c) {
  navigator.clipboard
    .writeText(d)
    .then(() => {
      c == null || c();
    })
    .catch((e) => {
      console.warn("[PaperForge] Failed to copy diagnostic:", e);
    });
}
function Kt(d) {
  return { envelope: d, capturedAt: new Date().toISOString() };
}
function qt(d, c) {
  return !d || c.user_state === "ready"
    ? !0
    : !(c.user_state === "detection_failed" || d.user_state === "ready");
}
function Ut(d, c) {
  var t, r, n, i, s, o, l;
  let e = [];
  for (let [p, u] of Object.entries(d)) {
    let _ = c.get(p);
    e.push({
      module: p,
      userState: u.user_state,
      lastSuccessAt: (t = _ == null ? void 0 : _.capturedAt) != null ? t : null,
      reasonCode: (r = u.reason) == null ? void 0 : r.code,
      actionId:
        (i = (n = u.action) == null ? void 0 : n.primary) == null
          ? void 0
          : i.action_id,
      errorExcerpt:
        (l =
          (o = (s = u.reason) == null ? void 0 : s.text) == null
            ? void 0
            : o.slice(0, 200)) != null
          ? l
          : void 0,
    });
  }
  return e;
}
var _e = N(require("fs")),
  ve = N(require("path")),
  Xt = N(require("os")),
  Ce = require("child_process");
var Br = ["paddleocr_api_key", "vector_db_api_key"],
  Mr = {
    paddleocr_api_key: "paddleocr-api-key",
    vector_db_api_key: "vector-db-api-key",
  },
  Wt = {
    paddleocr_api_key: "_paddleocr_configured",
    vector_db_api_key: "_vector_db_configured",
  },
  Ir = {
    ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
    memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
    embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  };
async function Zt(d, c) {
  var i;
  let e = (i = d.app) == null ? void 0 : i.secretStorage;
  if (!e || typeof e.getSecret != "function")
    return { migrated: [], warnings: [] };
  let t = [],
    r = [],
    n = Array.isArray(c._migrated_keys) ? c._migrated_keys : [];
  for (let s of Br) {
    if (n.includes(s)) continue;
    let o = typeof c[s] == "string" ? c[s] : "";
    if (!o) continue;
    let l = Mr[s] || s,
      p = await e.getSecret(l);
    if (p !== null) {
      if (p === o) {
        ((c[s] = ""), (c[Wt[s]] = !0), t.push(s));
        continue;
      }
      r.push(s);
      continue;
    }
    try {
      await e.setSecret(l, o);
    } catch (_) {
      r.push(s);
      continue;
    }
    if ((await e.getSecret(l)) !== o) {
      r.push(s);
      continue;
    }
    ((c[s] = ""), t.push(s), (c[Wt[s]] = !0));
  }
  if (t.length > 0 || r.length > 0) {
    let s = Array.isArray(c._migrated_keys) ? [...c._migrated_keys] : [];
    for (let o of t) s.includes(o) || s.push(o);
    if (((c._migrated_keys = s), r.length > 0)) {
      let o = Array.isArray(c._migration_warnings) ? c._migration_warnings : [];
      c._migration_warnings = [...o, ...r];
    }
    await d.saveData(c);
  }
  return { migrated: t, warnings: r };
}
async function Gt(d, c) {
  if (!Ir[c]) return {};
  let t = d.app.secretStorage,
    r = {};
  if (c === "ocr") {
    let n = await t.getSecret("paddleocr-api-key");
    n && ((r.PADDLEOCR_API_KEY = n), (r.PADDLEOCR_API_TOKEN = n));
  } else if (c === "memory" || c === "embed") {
    let n = await t.getSecret("vector-db-api-key");
    n && (r.VECTOR_DB_API_KEY = n);
  }
  return r;
}
var Nr = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
function Jt(d) {
  let c = {};
  for (let [e, t] of Object.entries(d))
    Nr.some((r) => e.startsWith(r)) || (c[e] = t);
  return c;
}
var _t = null,
  Yt = !1;
function ft(d) {
  let c = String(d),
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
    }[c];
  return t
    ? { ...t }
    : { type: "unknown", message: String(d), recoverable: !1 };
}
function ht() {
  if (Yt) return _t;
  Yt = !0;
  try {
    let d;
    if (process.platform === "win32") {
      let c = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      d = (0, Ce.execFileSync)(c, ["/c", "where", "git"], {
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
      let c = d
        .split(
          `
`
        )[0]
        .trim();
      c && (_t = ve.dirname(c));
    }
  } catch (d) {}
  return _t;
}
function fe() {
  let d = { ...process.env },
    c = process.platform,
    e = Xt.homedir(),
    t = [],
    r = ht();
  (r && t.push(r),
    c === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : c === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let n = d.PATH || "";
  return ((d.PATH = [...t, n].filter(Boolean).join(ve.delimiter)), Jt(d));
}
async function he(d, c) {
  let e = await Gt(d, c),
    t = fe();
  return Object.keys(e).length === 0 ? t : Object.assign({}, t, e);
}
function Qt(d) {
  return String(d)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function gt(d) {
  if (!d) return !1;
  try {
    if (!_e.existsSync(d)) return !1;
    for (let c of _e.readdirSync(d)) if (Qt(c)) return !0;
  } catch (c) {}
  return !1;
}
function Ge(d) {
  if (!d) return !1;
  try {
    if (!_e.existsSync(d)) return !1;
    for (let c of _e.readdirSync(d)) {
      let e = ve.join(d, c, "extensions");
      try {
        if (!_e.existsSync(e)) continue;
        for (let t of _e.readdirSync(e)) if (Qt(t)) return !0;
      } catch (t) {}
    }
  } catch (c) {}
  return !1;
}
var Fe = N(require("fs")),
  U = N(require("path")),
  er = require("child_process");
function Hr(d, c) {
  let e = c || Fe,
    t = U.join(d, "paperforge.json"),
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
      i = JSON.parse(n),
      s = i.vault_config || {};
    return {
      system_dir: s.system_dir || i.system_dir || r.system_dir,
      resources_dir: s.resources_dir || i.resources_dir || r.resources_dir,
      literature_dir: s.literature_dir || i.literature_dir || r.literature_dir,
      base_dir: s.base_dir || i.base_dir || r.base_dir,
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
function X(d, c) {
  let e = Hr(d, c),
    t = U.join(d, e.system_dir, "PaperForge");
  return {
    vault: d,
    systemDir: t,
    indexesDir: U.join(t, "indexes"),
    logsDir: U.join(t, "logs"),
    dbPath: U.join(t, "indexes", "paperforge.db"),
    memoryStatePath: U.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: U.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: U.join(t, "indexes", "runtime-health.json"),
    buildStatePath: U.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: U.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: U.join(t, "exports"),
    ocrDir: U.join(t, "ocr"),
    pluginDataPath: U.join(
      d,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: U.join(d, "paperforge.json"),
    configWarning: e._warning,
  };
}
function mt(d) {
  try {
    return Fe.existsSync(d) ? JSON.parse(Fe.readFileSync(d, "utf-8")) : null;
  } catch (c) {
    return null;
  }
}
function Vr(d) {
  let c = X(d);
  return mt(c.memoryStatePath);
}
var Re = null;
function Je(d) {
  let c = X(d),
    e = Date.now();
  if (Re && Re.vaultPath === d && e - Re.ts < 2e3) return Re.result;
  let t = "",
    r = [
      U.join(d, ".paperforge-test-venv", "Scripts", "python.exe"),
      U.join(d, ".venv", "Scripts", "python.exe"),
      U.join(d, "venv", "Scripts", "python.exe"),
    ];
  for (let i = 0; i < r.length; i++)
    if (Fe.existsSync(r[i])) {
      t = r[i];
      break;
    }
  if (t)
    try {
      let i = (0, er.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", d, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        s = JSON.parse(i);
      if (s.ok && s.data) {
        let o = s.data;
        return ((Re = { vaultPath: d, result: o, ts: e }), o);
      }
    } catch (i) {}
  let n = mt(c.vectorStatePath);
  return ((Re = { vaultPath: d, result: n, ts: e }), n);
}
function ze(d) {
  let c = X(d);
  return mt(c.healthStatePath);
}
function tr(d) {
  var e;
  let c = ze(d);
  return !!(c && ((e = c.summary) == null ? void 0 : e.status) === "ok");
}
function yt(d) {
  let c = Vr(d);
  return !c || c.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + c.paper_count_db + " | " + (c.fresh ? "fresh" : "stale");
}
function De(d) {
  var t, r, n;
  let c = Je(d);
  return c
    ? c.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = c.chunk_count) != null ? t : 0) +
          ((r = c.body_chunk_count) != null ? r : 0) +
          ((n = c.object_chunk_count) != null ? n : 0)) +
        " | " +
        c.model +
        " | " +
        c.mode
    : "Status unavailable";
}
var G = require("obsidian"),
  re = N(require("fs")),
  vt = N(require("path")),
  or = N(require("https")),
  Ae = require("child_process");
var bt = N(require("fs")),
  I = N(require("path")),
  Xe = require("child_process"),
  ar = N(require("os")),
  rr = 300 * 1e3,
  jr = "3.11";
function Ye() {
  let d, c;
  return {
    promise: new Promise((t, r) => {
      ((d = t), (c = r));
    }),
    resolve: d,
    reject: c,
  };
}
function zr(d) {
  let c = d.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (c) return c[1];
  let e = d.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function sr(d, c) {
  var r, n;
  let e = d.split(".").map(Number),
    t = c.split(".").map(Number);
  for (let i = 0; i < Math.max(e.length, t.length); i++) {
    let s = (r = e[i]) != null ? r : 0,
      o = (n = t[i]) != null ? n : 0;
    if (s !== o) return s - o;
  }
  return 0;
}
function $r(d, c) {
  return sr(d, c) >= 0;
}
function Kr() {
  var d;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((d = process.env.XDG_DATA_DIRS) != null ? d : "").includes("flatpak") ||
    !1
  );
}
function qr() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function nr(d, c) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[d]) != null ? t : d}-${c}`;
}
function ce(d) {
  return d.state !== "ready" || !d.pythonPath
    ? null
    : { command: d.pythonPath, args: [] };
}
var me = class {
  constructor(c) {
    this._cache = null;
    this._cacheTime = 0;
    var r, n, i, s, o, l, p, u, _, f, g;
    let e =
        (n = (r = c.osPlatform) != null ? r : c.platform) != null
          ? n
          : process.platform,
      t = (s = (i = c.osArch) != null ? i : c.arch) != null ? s : process.arch;
    if (
      ((this.osPlatform = e),
      (this.osArch = t),
      (this.triplet = `${e}-${t}`),
      c.runtimeDir)
    )
      ((this.runtimeDir = c.runtimeDir),
        (this.rootDir = I.dirname(c.runtimeDir)),
        (this.pluginVersion =
          (l = (o = c.pluginVersion) != null ? o : c.version) != null
            ? l
            : "0.0.0"));
    else {
      let h = ar.homedir();
      ((this.rootDir = I.join(h, ".paperforge", "runtime")),
        (this.runtimeDir = I.join(this.rootDir, nr(e, t))),
        (this.pluginVersion =
          (u = (p = c.version) != null ? p : c.pluginVersion) != null
            ? u
            : "0.0.0"));
    }
    ((this.pointerPath = I.join(this.rootDir, "active-runtime.json")),
      (this._fs = (_ = c.fs) != null ? _ : bt),
      (this._execFile = (f = c.execFile) != null ? f : Xe.execFile),
      (this._execFileSync =
        (g = c.execFileSync) != null ? g : Xe.execFileSync));
  }
  current() {
    return this._cache
      ? Date.now() - this._cacheTime > rr
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
  async status(c) {
    var s;
    if (this._cache) {
      let o = Date.now() - this._cacheTime > rr;
      if (!o && this._cache.state === "ready")
        return { ...this._cache, stale: !1 };
      if (o && c != null && c.allowStale) return { ...this._cache, stale: !0 };
    }
    let e = null,
      t = null,
      r = null,
      n = null,
      i = [];
    try {
      let o = this._fs.readFileSync(this.pointerPath, "utf-8"),
        l = JSON.parse(o);
      e = typeof l.version == "string" ? l.version : null;
      let p = typeof l.pythonPath == "string" ? l.pythonPath : null;
      ((t = p ? I.resolve(I.dirname(this.pointerPath), p) : null),
        (r = typeof l.previousVersion == "string" ? l.previousVersion : null),
        (n =
          typeof l.previousPythonPath == "string"
            ? l.previousPythonPath
            : null),
        (i = Array.isArray(l.warnings) ? l.warnings : []));
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
        warnings: i,
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
        warnings: i,
        previousVersion: r,
        previousPythonPath: n,
      });
    try {
      let o = await this._probe(t),
        l = [...i];
      return this._setCache({
        state: "ready",
        pythonPath: t,
        version: (s = o.version) != null ? s : e,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: !1,
        warnings: l,
        previousVersion: r,
        previousPythonPath: n,
      });
    } catch (o) {
      let l = o instanceof Error ? o.message : String(o);
      return this._setCache({
        state: "needs_repair",
        pythonPath: t,
        version: e,
        source: "venv",
        error: {
          code: "PROBE_FAILED",
          message: l,
          platformAction: "Repair runtime",
        },
        lastVerifiedAt: null,
        stale: !1,
        warnings: i,
        previousVersion: r,
        previousPythonPath: n,
      });
    }
  }
  async ensure(c) {
    var b, E;
    let e =
        (b = c == null ? void 0 : c.version) != null ? b : this.pluginVersion,
      t = (E = c == null ? void 0 : c.force) != null ? E : !1,
      r = c == null ? void 0 : c.signal;
    if (r != null && r.aborted) return this._abortedHealth();
    if (!t) {
      let m = this.current();
      if (m.state === "ready" && !m.stale) {
        let v = await this.status();
        if (v.state === "ready") return v;
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let n;
    try {
      n = this._resolveBootstrapPython();
    } catch (m) {
      if (Kr() || qr())
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
      let v = nr(this.osPlatform, this.osArch),
        k = this.osPlatform === "darwin",
        y = ["macos-x64", "macos-arm64"],
        x = ["windows-x64", "linux-x64"];
      return k && y.includes(v)
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
        : x.includes(v)
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
    if (!$r(n.version, jr))
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
        let v = this._fs.readFileSync(this.pointerPath, "utf-8"),
          k = JSON.parse(v),
          y = typeof k.version == "string" ? k.version : null;
        m = y !== null && y !== e;
      } catch (v) {}
      if (m) {
        let v = I.join(this.runtimeDir, `v${e}`),
          k = I.join(v, "venv"),
          y =
            this.osPlatform === "win32"
              ? I.join(k, "Scripts", "python.exe")
              : I.join(k, "bin", "python");
        try {
          await this._probe(y, r);
        } catch (O) {
          if (O instanceof Error && O.name === "AbortError")
            return this._abortedHealth();
          let L = O instanceof Error ? O.message : String(O);
          return this._setCache({
            state: "needs_repair",
            pythonPath: y,
            version: e,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${e} failed verification: ${L}`,
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
          w = null;
        try {
          let O = this._fs.readFileSync(this.pointerPath, "utf-8"),
            L = JSON.parse(O);
          ((x = typeof L.version == "string" ? L.version : null),
            (w = typeof L.pythonPath == "string" ? L.pythonPath : null));
        } catch (O) {}
        let S = I.dirname(this.pointerPath);
        this._fs.existsSync(S) || this._fs.mkdirSync(S, { recursive: !0 });
        let P = I.relative(I.dirname(this.pointerPath), y),
          F = JSON.stringify(
            {
              schema_version: 1,
              version: e,
              pythonPath: P,
              activatedAt: new Date().toISOString(),
              previousVersion: x,
              previousPythonPath: w,
            },
            null,
            2
          ),
          T = this.pointerPath + ".tmp";
        (this._fs.writeFileSync(T, F, "utf-8"),
          this._fs.renameSync(T, this.pointerPath));
        let A = {
          state: "ready",
          pythonPath: y,
          version: e,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: !1,
          warnings: [],
          previousVersion: x,
          previousPythonPath: w,
        };
        return (
          (this._cache = A),
          (this._cacheTime = Date.now()),
          this._cleanupOldSlots(e),
          A
        );
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let i = t
        ? I.join(this.runtimeDir, `v${e}_build2`)
        : I.join(this.runtimeDir, `v${e}`),
      s = I.join(i, "venv"),
      o =
        this.osPlatform === "win32"
          ? I.join(s, "Scripts", "python.exe")
          : I.join(s, "bin", "python");
    try {
      this._fs.mkdirSync(i, { recursive: !0 });
      let { promise: m, reject: v, resolve: k } = Ye();
      (this._execFile(
        n.path,
        ["-m", "venv", s],
        { timeout: 6e4, signal: r },
        (y) => {
          y ? v(y) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(i, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VENV_CREATION_FAILED", m, i);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: v, resolve: k } = Ye();
      (this._execFile(
        o,
        ["-m", "pip", "install", `paperforge==${e}`],
        { timeout: 12e4, signal: r },
        (y) => {
          y ? v(y) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(i, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "PIP_INSTALL_FAILED", m, i);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: m, reject: v, resolve: k } = Ye();
      (this._execFile(
        o,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: r },
        (y) => {
          y ? v(y) : k();
        }
      ),
        await m);
    } catch (m) {
      if (m instanceof Error && m.name === "AbortError") {
        try {
          this._fs.rmSync(i, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VERIFY_FAILED", m, i);
    }
    let l = null,
      p = null;
    try {
      let m = this._fs.readFileSync(this.pointerPath, "utf-8"),
        v = JSON.parse(m);
      ((l = typeof v.version == "string" ? v.version : null),
        (p = typeof v.pythonPath == "string" ? v.pythonPath : null));
    } catch (m) {}
    let u = I.dirname(this.pointerPath);
    this._fs.existsSync(u) || this._fs.mkdirSync(u, { recursive: !0 });
    let _ = I.relative(I.dirname(this.pointerPath), o),
      f = JSON.stringify(
        {
          schema_version: 1,
          version: e,
          pythonPath: _,
          activatedAt: new Date().toISOString(),
          previousVersion: l,
          previousPythonPath: p,
        },
        null,
        2
      ),
      g = this.pointerPath + ".tmp";
    (this._fs.writeFileSync(g, f, "utf-8"),
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
      previousVersion: l,
      previousPythonPath: p,
    };
    return (
      (this._cache = h),
      (this._cacheTime = Date.now()),
      this._cleanupOldSlots(e),
      h
    );
  }
  _setCache(c) {
    return ((this._cache = c), (this._cacheTime = Date.now()), c);
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
  _slotFailed(c, e, t, r) {
    try {
      this._fs.rmSync(r, { recursive: !0, force: !0 });
    } catch (i) {}
    let n = t instanceof Error ? t.message : String(t);
    return this._setCache({
      state: "needs_repair",
      pythonPath: null,
      version: c,
      source: "none",
      error: { code: e, message: n, platformAction: "Retry installation" },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    });
  }
  _currentSlotExists(c) {
    let e = I.join(this.runtimeDir, `v${c}`);
    return this._fs.existsSync(e);
  }
  _resolveBootstrapPython() {
    let c = [];
    this.osPlatform === "win32"
      ? c.push(
          { path: "py", args: ["-3.11"] },
          { path: "py", args: ["-3.10"] },
          { path: "py", args: ["-3"] },
          { path: "python", args: [] }
        )
      : this.osPlatform === "darwin"
        ? c.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          )
        : c.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          );
    for (let e of c)
      try {
        let t = this._execFileSync(e.path, [...e.args, "--version"], {
            encoding: "utf-8",
            timeout: 5e3,
          }),
          r = zr(t);
        if (r) return { path: e.path, version: r };
      } catch (t) {}
    throw new Error("No Python 3.11+ found on system");
  }
  _probe(c, e) {
    let { promise: t, resolve: r, reject: n } = Ye();
    return (
      this._execFile(
        c,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: e },
        (i, s) => {
          if (i) n(i);
          else {
            let o = (s != null ? s : "").trim() || null;
            r({ version: o });
          }
        }
      ),
      t
    );
  }
  _cleanupOldSlots(c, e = 2) {
    try {
      let r = this._fs
        .readdirSync(this.runtimeDir, { withFileTypes: !0 })
        .filter((n) => n.isDirectory() && n.name.startsWith("v"))
        .map((n) => {
          let i = n.name.replace(/^v/, "").replace(/_build\d+$/, "");
          return { name: n.name, version: i };
        })
        .filter((n) => n.version !== c)
        .sort((n, i) => sr(i.version, n.version));
      for (let n = e; n < r.length; n++)
        this._fs.rmSync(I.join(this.runtimeDir, r[n].name), {
          recursive: !0,
          force: !0,
        });
    } catch (t) {}
  }
};
function ir(d, c) {
  return !c || !c.trim()
    ? { blocked: !0, reason: "zotero" }
    : d
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var Et = class extends G.Modal {
  constructor(e, t, r, n) {
    super(e);
    this._rowEls = [];
    ((this.orphans = t.map((i, s) => ({ ...i, _selected: !0, _idx: s }))),
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
      let i = t.createEl("div", {
        cls:
          "paperforge-orphan-row" +
          (n._selected ? "" : " paperforge-orphan-dimmed"),
      });
      this._rowEls.push(i);
      let s = i.createEl("div", { cls: "paperforge-orphan-info" }),
        o = s.createEl("div", { cls: "paperforge-orphan-header" });
      o.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let l = o.createEl("span", { cls: "paperforge-orphan-tags" });
      (l.createEl("span", {
        cls: "paperforge-tag " + (n.has_pdf ? "tag-pdf" : "tag-nopdf"),
        text: n.has_pdf ? "PDF" : "no PDF",
      }),
        n.collection_path &&
          l.createEl("span", {
            cls: "paperforge-tag tag-collection",
            text: n.collection_path,
          }),
        n.title &&
          s.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let p = [];
      (n.authors && p.push(n.authors),
        n.year && p.push(n.year),
        p.length > 0 &&
          s.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: p.join(" \xB7 "),
          }),
        s.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: a("orphan_explain"),
        }),
        i.addEventListener("click", () => {
          ((n._selected = !n._selected), this._updateUI());
        }));
    }
    let r = e.createEl("div", { cls: "paperforge-modal-actions" });
    ((this._selectAllBtn = r.createEl("button", {
      cls: "paperforge-step-btn",
      text: "Deselect all",
    })),
      this._selectAllBtn.addEventListener("click", () => {
        let n = this.orphans.every((i) => i._selected);
        for (let i of this.orphans) i._selected = !n;
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
        let n = this.orphans.filter((s) => s._selected);
        if (n.length === 0) {
          new G.Notice(a("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new G.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let i = n.map((s) => s.key);
        (0, Ae.execFile)(
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
            ...i,
          ],
          { cwd: this.vaultPath, timeout: 6e4 },
          (s, o) => {
            if (s) {
              (new G.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let l = JSON.parse(o),
                p = (l.data && l.data.deleted) || [];
              new G.Notice("Deleted " + p.length + " orphan workspace(s)");
            } catch (l) {
              new G.Notice("PaperForge: prune done");
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
function et(d, c, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = X(e).orphanStatePath;
    if (!re.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = re.readFileSync(r, "utf-8"),
      s = JSON.parse(n),
      o = { path: "python", extraArgs: [], source: "auto-detected" };
    (console.log("[PF] py.path:", o ? o.path : "null"),
      new Et(d, s, e, o).open(),
      re.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var Ee = class extends G.Modal {
  constructor(e, t, r) {
    super(e);
    this._pendingSave = null;
    this._showSkipConfirm = !1;
    ((this.plugin = t), (this._step = 1), (this._onComplete = r));
  }
  _resolvePython() {
    var i, s;
    let e = (i = this.plugin.settings.python_path) == null ? void 0 : i.trim();
    if (e && re.existsSync(e)) return { path: e, args: [] };
    let t =
        ((s = this.plugin.settings.vault_path) == null ? void 0 : s.trim()) ||
        ".",
      r = new me({
        runtimeDir: vt.join(t, ".paperforge-test-venv"),
        pluginVersion: this.plugin.manifest.version,
        osPlatform: process.platform,
        osArch: process.arch,
        fs: re,
        execFile: Ae.execFile,
        execFileSync: require("child_process").execFileSync,
      }),
      n = ce(r.current());
    return n
      ? { path: n.command, args: [...n.args] }
      : { path: "python", args: [] };
  }
  onOpen() {
    this._render();
  }
  onClose() {
    this.contentEl.empty();
  }
  _render() {
    let { contentEl: e } = this;
    (e.empty(),
      e.addClass("paperforge-modal"),
      this._renderStepIndicator(),
      this._renderStepContent(),
      this._renderNavigation());
  }
  _renderStepIndicator() {
    let e = [
        a("wizard_step1"),
        a("wizard_step2"),
        a("wizard_step3"),
        a("wizard_step4"),
        a("wizard_step5"),
      ],
      t = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    e.forEach((r, n) => {
      let i = n + 1,
        s = t.createEl("div", {
          cls: `paperforge-step-dot ${i === this._step ? "active" : ""} ${i < this._step ? "done" : ""}`,
        });
      (s.createEl("span", { cls: "paperforge-step-num", text: `${i}` }),
        s.createEl("span", { cls: "paperforge-step-label", text: r }));
    });
  }
  _renderStepContent() {
    let e = this.contentEl.createEl("div", { cls: "paperforge-step-content" });
    switch (this._step) {
      case 1:
        this._stepOverview(e);
        break;
      case 2:
        this._stepDirectories(e);
        break;
      case 3:
        this._stepKeys(e);
        break;
      case 4:
        this._stepInstall(e);
        break;
      case 5:
        this._stepComplete(e);
        break;
    }
  }
  _renderNavigation() {
    let e = this.contentEl.createEl("div", { cls: "paperforge-step-nav" });
    (this._step > 1 &&
      e
        .createEl("button", { cls: "paperforge-step-btn", text: a("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? e
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: a("nav_next"),
            })
            .addEventListener("click", () => {
              if (this._step === 3) {
                let r = this._validateStep3();
                if (r.blocked) {
                  if (r.reason === "zotero") return;
                  if (r.reason === "ocr") {
                    ((this._showSkipConfirm = !0), this._render());
                    return;
                  }
                }
              }
              (this._step++, (this._showSkipConfirm = !1), this._render());
            })
        : e
            .createEl("button", {
              cls: "paperforge-step-btn",
              text: a("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let e = this.plugin.settings,
      t = ir(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new G.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!re.existsSync(r))
      return (
        new G.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!re.statSync(r).isDirectory())
      return (
        new G.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let n = vt.join(r, "storage");
    return !re.existsSync(n) || !re.statSync(n).isDirectory()
      ? (new G.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(e) {
    (e.createEl("h2", { text: a("wizard_title") }),
      e.createEl("p", { text: a("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-dir-tree" }),
      i = n.createEl("div", { cls: "paperforge-dir-node root" });
    i.textContent = `\u{1F4C1} Vault (${r})`;
    let s = n.createEl("div", { cls: "paperforge-dir-children" }),
      o = s.createEl("div", { cls: "paperforge-dir-node folder" });
    ((o.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      o
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${t.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      s.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      s.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
      }),
      e.createEl("p", {
        text: a("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      e.createEl("p", {
        text: a("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let p = e.createEl("div", { cls: "paperforge-summary" }),
      u = [
        {
          label: a("dir_resources"),
          val: `${r}/${t.resources_dir || "Resources"}`,
        },
        {
          label: a("dir_notes"),
          val: `${r}/${t.resources_dir || "Resources"}/${t.literature_dir || "Literature"}`,
        },
        { label: a("dir_base"), val: `${r}/${t.base_dir || "Bases"}` },
        { label: a("dir_system"), val: `${r}/${t.system_dir || "System"}` },
      ];
    for (let _ of u) {
      let f = p.createEl("div", { cls: "paperforge-summary-row" });
      (f.createEl("span", { cls: "paperforge-summary-label", text: _.label }),
        f.createEl("span", { cls: "paperforge-summary-value", text: _.val }));
    }
  }
  _stepDirectories(e) {
    (e.createEl("h2", { text: a("wizard_step2") }),
      e.createEl("p", { text: a("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath;
    (this._modalField(e, a("dir_vault"), r, !0),
      e.createEl("p", {
        text: a("wizard_dir_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u8D44\u6E90\u76EE\u5F55\uFF08\u521B\u5EFA\u6587\u732E\u5361\u7247\u76EE\u5F55\u7684\u5730\u65B9\uFF09",
        "resources_dir",
        t.resources_dir,
        "Resources"
      ),
      e.createEl("p", {
        text: a("wizard_dir_sub_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08\u5B58\u653E\u6587\u732E\u5361\u7247\u7684\u5730\u65B9\uFF0CBase \u6570\u636E\u6765\u6E90\uFF09",
        "literature_dir",
        t.literature_dir,
        "Literature"
      ),
      e.createEl("p", {
        text: a("wizard_sys_hint"),
        cls: "paperforge-modal-hint",
      }),
      this._modalInput(
        e,
        "\u7CFB\u7EDF\u76EE\u5F55\uFF08\u5B58\u653E Zotero \u8F6F\u94FE\u63A5\u548C PaperForge \u7CFB\u7EDF\u6587\u4EF6\uFF09",
        "system_dir",
        t.system_dir,
        "System"
      ),
      this._modalInput(
        e,
        "Base \u76EE\u5F55\uFF08\u5B58\u653E\u6570\u636E\u7BA1\u7406\u9762\u677F\u7684\u5730\u65B9\uFF09",
        "base_dir",
        t.base_dir,
        "Bases"
      ),
      e.createEl("p", {
        text: a("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-summary" }),
      i = [
        { label: a("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: a("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: a("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: a("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let s of i) {
      let o = n.createEl("div", { cls: "paperforge-summary-row" });
      (o.createEl("span", { cls: "paperforge-summary-label", text: s.label }),
        o.createEl("span", { cls: "paperforge-summary-value", text: s.val }));
    }
  }
  _stepKeys(e) {
    if (
      (e.createEl("h2", { text: a("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(e);
      return;
    }
    let t = this.plugin.settings;
    e.createEl("p", {
      text: a("wizard_agent_hint"),
      cls: "paperforge-modal-hint",
    });
    let r = [
        { key: "opencode", name: "OpenCode" },
        { key: "claude", name: "Claude Code" },
        { key: "cursor", name: "Cursor" },
        { key: "github_copilot", name: "GitHub Copilot" },
        { key: "windsurf", name: "Windsurf" },
        { key: "codex", name: "Codex" },
        { key: "gemini", name: "Gemini CLI" },
        { key: "cline", name: "Cline" },
      ],
      n = e.createEl("div", { cls: "paperforge-modal-field" });
    n.createEl("label", {
      cls: "paperforge-modal-label",
      text: a("label_agent"),
    });
    let i = n.createEl("select", { cls: "paperforge-modal-select" });
    for (let f of r) {
      let g = i.createEl("option", { text: f.name, attr: { value: f.key } });
      f.key === (t.agent_platform || "opencode") && (g.selected = !0);
    }
    (i.addEventListener("change", () => {
      ((t.agent_platform = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: a("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", {
      cls: "paperforge-modal-label",
      text: a("field_paddleocr"),
    });
    let o = s.createEl("input", {
        cls: "paperforge-modal-input",
        attr: { type: "password", placeholder: "API Key" },
      }),
      l = this.plugin.settings._paddleocr_configured || !1;
    ((o.placeholder = l
      ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored securely)"
      : "API Key"),
      (o.value = ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = s.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let p = s.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (p.addEventListener("click", () => this._validateApiKey(o.value, p)),
      o.addEventListener("input", () => {
        ((this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      e.createEl("p", {
        text: a("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let u = e.createEl("div", { cls: "paperforge-modal-field" });
    u.createEl("label", {
      cls: "paperforge-modal-label",
      text: a("field_zotero_data"),
    });
    let _ = u.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: a("field_zotero_placeholder") },
    });
    ((_.value = t.zotero_data_dir || ""),
      _.addEventListener("input", () => {
        ((t.zotero_data_dir = _.value),
          this._pendingSave && clearTimeout(this._pendingSave),
          (this._pendingSave = setTimeout(() => {
            (this.plugin.saveSettings(), (this._pendingSave = null));
          }, 500)));
      }));
  }
  _validateApiKey(e, t) {
    if (!e || e.length < 10) {
      ((this._apiKeyStatus.textContent =
        "\u5BC6\u94A5\u683C\u5F0F\u4E0D\u6B63\u786E\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"));
      return;
    }
    ((t.disabled = !0),
      (t.textContent = "\u9A8C\u8BC1\u4E2D\u2026"),
      (this._apiKeyStatus.textContent = "\u6B63\u5728\u9A8C\u8BC1\u2026"),
      (this._apiKeyStatus.className = "paperforge-apikey-status"));
    let r = JSON.stringify({ model: "PaddleOCR-VL-1.5" }),
      n = {
        hostname: "paddleocr.aistudio-app.com",
        path: "/api/v2/ocr/jobs",
        method: "POST",
        headers: {
          Authorization: "bearer " + e,
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(r),
        },
        timeout: 1e4,
      },
      i = or.request(n, async (s) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let o = "";
        (s.on("data", (l) => (o += l)),
          s.on("end", async () => {
            var l, p;
            try {
              let u = JSON.parse(o);
              if (s.statusCode === 400 && u.code === 10001) {
                let _ = this.app.secretStorage;
                try {
                  if (
                    (await ((l = _ == null ? void 0 : _.setSecret) == null
                      ? void 0
                      : l.call(_, "paddleocr-api-key", e)),
                    (await ((p = _ == null ? void 0 : _.getSecret) == null
                      ? void 0
                      : p.call(_, "paddleocr-api-key"))) === e)
                  ) {
                    let g = this.plugin.settings;
                    ((g._paddleocr_configured = !0),
                      (g.paddleocr_api_key = ""),
                      this.plugin.saveSettings());
                  }
                } catch (f) {}
                ((this._apiKeyStatus.textContent =
                  "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0));
              } else
                s.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      s.statusCode +
                      "\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1));
            } catch (u) {
              ((this._apiKeyStatus.textContent =
                "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u89E3\u6790\u54CD\u5E94\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                (this._apiKeyStatus.className =
                  "paperforge-apikey-status error"),
                (this._apiKeyValidated = !1));
            }
          }));
      });
    (i.on("error", (s) => {
      ((t.disabled = !1),
        (t.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          s.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      i.write(r),
      i.end());
  }
  _renderSkipConfirm(e) {
    e.createEl("p", {
      text: a("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let t = e.createEl("div", { cls: "paperforge-modal-actions" });
    (t
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: a("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      t
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: a("wizard_skip_ocr_back"),
        })
        .addEventListener("click", () => {
          ((this._showSkipConfirm = !1), this._render());
        }));
  }
  _modalField(e, t, r, n) {
    let i = e.createEl("div", { cls: "paperforge-modal-field" });
    i.createEl("label", { cls: "paperforge-modal-label", text: t });
    let s = i.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((s.value = r), (s.disabled = !!n));
  }
  _modalInput(e, t, r, n, i) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let o = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: i || "" },
    });
    o.value = n;
    let l = this.plugin.settings;
    o.addEventListener("input", () => {
      ((l[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, n, i) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let o = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: i || "" },
    });
    o.value = n;
    let l = this.plugin.settings;
    o.addEventListener("input", () => {
      ((l[r] = o.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(e) {
    (e.createEl("h2", { text: a("wizard_step4") }),
      (this._installLog = e.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let t = e.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: a("install_btn"),
    });
    t.addEventListener("click", () => this._runInstall(t));
  }
  async _runInstall(e) {
    var s, o, l, p, u, _;
    ((e.disabled = !0),
      (e.textContent = a("install_btn_running")),
      this._installLog.setText(
        a("install_validating") +
          `
`
      ),
      this._log(a("install_validating")));
    let t = this.plugin.settings,
      r = this._validate();
    if (r.length > 0) {
      (this._log(a("validate_fail") + ":"),
        r.forEach((f) => this._log("  \u2717 " + f)),
        (e.disabled = !1),
        (e.textContent = a("install_btn_retry")));
      return;
    }
    let n = (f, g = {}) =>
        new Promise((h, b) => {
          let { path: E, args: m = [] } = this._resolvePython(),
            v = (0, Ae.spawn)(E, [...m, ...f], {
              cwd: t.vault_path.trim(),
              env: fe(),
              timeout: 12e4,
              ...g,
            }),
            k = "",
            y = "";
          (v.stdout.on("data", (x) => {
            let w = x.toString("utf-8");
            ((k += w), g.logStdout && this._processSetupOutput(w));
          }),
            v.stderr.on("data", (x) => {
              let w = x.toString("utf-8");
              ((y += w), this._log("[stderr] " + w.trim()));
            }),
            v.on("close", (x) => {
              x === 0
                ? h({ stdout: k, stderr: y })
                : b(new Error(y.trim() || k.trim() || `exit code ${x}`));
            }),
            v.on("error", (x) => b(x)));
        }),
      i = [
        "-m",
        "paperforge",
        "--vault",
        t.vault_path.trim(),
        "setup",
        "--modular",
        "--system-dir",
        t.system_dir.trim(),
        "--resources-dir",
        t.resources_dir.trim(),
        "--literature-dir",
        t.literature_dir.trim(),
        "--base-dir",
        t.base_dir.trim(),
        "--agent",
        t.agent_platform || "opencode",
      ];
    t.zotero_data_dir &&
      t.zotero_data_dir.trim() &&
      i.push("--zotero-data", t.zotero_data_dir.trim());
    try {
      let f = !0;
      try {
        await n(["-c", "import paperforge"]);
      } catch (g) {
        f = !1;
      }
      if (!f) {
        this._log(a("install_bootstrapping"));
        let g = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${g}`);
        let h = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && h.push("--user"),
          h.push(`paperforge==${g}`));
        try {
          await n(h, { logStdout: !0 });
        } catch (b) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${g}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (s = b.message) == null ? void 0 : s.slice(0, 200)
            ));
          let E = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && E.push("--user"),
            E.push(`git+https://github.com/LLLin000/PaperForge.git@v${g}`),
            await n(E, { logStdout: !0 }));
        }
      }
      (await n(i, { logStdout: !0, env: fe() }),
        this._log(a("install_complete")),
        await this.plugin.saveSettings(),
        this._onComplete && this._onComplete(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (f) {
      console.error("PaperForge setup failed:", f.message);
      let g = this._formatSetupError(f.message);
      this._log(a("install_failed") + g);
      let h =
        (o = this._installLog.parentElement) == null
          ? void 0
          : o.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: a("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (h) {
        let b = f.message,
          E =
            ((p = (l = this.plugin) == null ? void 0 : l.settings) == null
              ? void 0
              : p.python_path) || "auto",
          m =
            ((_ = (u = this.plugin) == null ? void 0 : u.manifest) == null
              ? void 0
              : _.version) || "?",
          v = process.platform + " " + process.arch,
          k,
          y;
        try {
          k = ht() || "(not found)";
        } catch (P) {
          k = "(error)";
        }
        try {
          y = this._resolvePython();
        } catch (P) {
          y = null;
        }
        let x = (process.env.PATH || "").length,
          w = (process.env.PATH || "").toLowerCase().includes("git"),
          S = [
            "[PaperForge Diagnostic]",
            "Category: " + g,
            "Plugin version: " + m,
            "Python: " + E,
            "Resolved Python: " + ((y == null ? void 0 : y.path) || "?"),
            "OS: " + v,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + k,
            "PATH length: " + x + " chars",
            "PATH contains git: " + w,
            "--- Raw error ---",
            b.slice(0, 2e3),
          ].join(`
`);
        h.addEventListener("click", () => {
          navigator.clipboard
            .writeText(S)
            .then(() => {
              (h.setText(a("error_copied") || "Copied!"),
                setTimeout(() => {
                  h.setText(a("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new G.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((e.disabled = !1), (e.textContent = a("install_btn_retry")));
    }
  }
  _log(e) {
    this._installLog &&
      this._installLog.setText(
        this._installLog.textContent +
          e +
          `
`
      );
  }
  _validate() {
    let e = [],
      t = this.plugin.settings;
    return (
      (!t.vault_path || !t.vault_path.trim()) && e.push(a("validate_vault")),
      (!t.resources_dir || !t.resources_dir.trim()) &&
        e.push(a("validate_resources")),
      (!t.literature_dir || !t.literature_dir.trim()) &&
        e.push(a("validate_notes")),
      (!t.base_dir || !t.base_dir.trim()) && e.push(a("validate_base")),
      this.plugin.settings._paddleocr_configured ||
        !1 ||
        this._log("  ! " + a("validate_key") + " " + a("optional_later")),
      (!t.zotero_data_dir || !t.zotero_data_dir.trim()) &&
        this._log("  ! " + a("validate_zotero") + " " + a("optional_later")),
      e
    );
  }
  _processSetupOutput(e) {
    let t = e
      .split(
        `
`
      )
      .filter(Boolean);
    for (let r of t)
      if (r.includes("[*]") || r.includes("[OK]") || r.includes("[FAIL]")) {
        let n = r
          .replace(/^\[\*\].*\d+:?\s*/, "")
          .replace(/^\[OK\]\s*/, "")
          .replace(/^\[FAIL\]\s*/, "");
        this._log("  " + n);
      }
  }
  _formatSetupError(e) {
    if (
      process.platform === "darwin" &&
      /No module named ['"]?paperforge/i.test(e)
    )
      return "PaperForge not installed \u2014 install Python from Homebrew or python.org (Apple CLT /Library/Developer/CommandLineTools python often fails); then: python3 -m pip install --user git+https://github.com/LLLin000/PaperForge.git";
    let t = [
      {
        match: /pip.*not found|No module named.*pip|command not found.*pip/i,
        msg: "pip not found",
      },
      {
        match: /command not found|No such file|not recognized/i,
        msg: "Python not found",
      },
      {
        match:
          /resolve host|getaddrinfo.*nodename|connect ETIMEDOUT|connect ECONNREFUSED|fetch failed|Network error|ENOTFOUND|ECONNREFUSED|ECONNRESET/i,
        msg: "Network error",
      },
      {
        match:
          /certificate verify failed|SSL.*certificate|self.signed.cert|CERTIFICATE_VERIFY_FAILED/i,
        msg: "SSL certificate error",
      },
      { match: /No space left on device|disk full|ENOSPC/i, msg: "Disk full" },
      {
        match:
          /paperforge.*not found|cannot import|ModuleNotFoundError|No module named/i,
        msg: "PaperForge not installed",
      },
      { match: /permission denied|EACCES|EPERM/i, msg: "Permission denied" },
      { match: /ENOENT/i, msg: "Path not found" },
      { match: /timeout|timed out/i, msg: "Timeout" },
    ];
    for (let n of t) if (n.match.test(e)) return n.msg;
    return (
      e
        .split(
          `
`
        )
        .filter(Boolean)
        .slice(0, 3)
        .join(" | ")
        .slice(0, 200) || "Unknown error"
    );
  }
  _stepComplete(e) {
    e.createEl("h2", { text: a("complete_title") });
    let t = e.createEl("div", { cls: "paperforge-summary" });
    t.createEl("div", {
      cls: "paperforge-summary-title",
      text: a("complete_summary"),
    });
    let r = this.plugin.settings,
      n = this.app.vault.adapter.basePath,
      i = [
        { label: a("dir_vault"), val: n },
        { label: a("dir_resources"), val: `${n}/${r.resources_dir}` },
        {
          label: a("dir_notes"),
          val: `${n}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: a("dir_base"), val: `${n}/${r.base_dir}` },
        { label: a("dir_system"), val: `${n}/${r.system_dir}` },
        {
          label: "API Key",
          val: this.plugin.settings._paddleocr_configured
            ? a("api_key_set")
            : a("api_key_missing"),
        },
        {
          label: a("field_zotero_data"),
          val: r.zotero_data_dir || a("not_set"),
        },
      ];
    for (let u of i) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    let s = t.createEl("div", { cls: "paperforge-summary-row" });
    s.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let o = s.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let u = n,
        { path: _, args: f = [] } = this._resolvePython();
      (0, Ae.execFile)(
        _,
        [...f, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: u, timeout: 1e4 },
        (g, h) => {
          !g && h && (o.textContent = "v" + h.trim());
        }
      );
    }
    for (let u of i) {
      let _ = t.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    e.createEl("h3", { text: a("complete_next") });
    let l = e.createEl("div", { cls: "paperforge-nextsteps" }),
      p = [
        [a("complete_step4"), a("complete_step4_desc")],
        [
          "",
          `${a("complete_export_path")} ${n}/${r.system_dir}/PaperForge/exports/`,
        ],
        [a("complete_step1"), a("complete_step1_desc")],
        [a("complete_step2"), a("complete_step2_desc")],
        [a("complete_step3"), a("complete_step3_desc")],
      ];
    for (let [u, _] of p) {
      let f = l.createEl("div", { cls: "paperforge-nextstep-item" });
      (u && f.createEl("strong", { text: u }), f.createEl("span", { text: _ }));
    }
  }
};
function lr(d, c) {
  if (c.key !== "Tab") return;
  let e = d.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (e.length === 0) return;
  let t = e[0],
    r = e[e.length - 1];
  c.shiftKey
    ? document.activeElement === t && (c.preventDefault(), r.focus())
    : document.activeElement === r && (c.preventDefault(), t.focus());
}
var Ke = class extends G.Modal {
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
          for (let l of Array.from(o.children))
            l !== t &&
              !l.hasAttribute("inert") &&
              (l.setAttribute("inert", ""), this._inertedEls.push(l));
      }
      e.createEl("h2", { text: this._config.title });
      let r = e.createEl("div", { cls: "paperforge-confirm-effect" });
      (r.createEl("span", {
        cls: "paperforge-confirm-effect-label",
        text: "Effect: ",
      }),
        r.createEl("span", { text: this._config.effectLabel }));
      let n = e.createEl("div", { cls: "paperforge-confirm-actions" }),
        i = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            a("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (i.addEventListener("click", () => this.close()),
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
        (this._boundKeydown = (o) => lr(e, o)),
        e.addEventListener("keydown", this._boundKeydown),
        i.focus());
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
  Ur = [
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
function $e(d) {
  let c = {},
    e = d;
  for (let { pattern: t, label: r, class_: n } of Ur) {
    let i = 0;
    ((e = e.replace(t, () => (i++, "[REDACTED]"))),
      i > 0 &&
        (c[n] || (c[n] = { label: r, class_: n, count: 0 }),
        (c[n].count += i)));
  }
  return { clean: e, redactions: Object.values(c) };
}
function cr(d, c, e, t) {
  let r = `OCR: ${d} (${e} papers)`,
    n = [
      "## Diagnostic Summary",
      `- Reason: ${d}`,
      `- Detail: ${c}`,
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
var Qe = class extends G.Modal {
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
    let n = $e(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let i = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    i.createEl("label", { text: "Body" });
    let s = $e(this._draft.body).clean;
    this._bodyTextarea = i.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: s,
    });
    let { redactions: o } = $e(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      l = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      p = l.createEl("div", { cls: "paperforge-issue-draft-included" });
    (p.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (a("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      p.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = l.createEl("div", { cls: "paperforge-issue-draft-redacted" });
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
    let _ = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (_.createEl("button", {
      text: a("maintenance_confirm_cancel") || "Cancel",
    }).addEventListener("click", () => this.close()),
      _.createEl("button", {
        cls: "mod-cta",
        text: a("maintenance_issue_draft_open_github") || "Open GitHub Issue",
      }).addEventListener("click", () => {
        let h = encodeURIComponent($e(this._titleInput.value).clean),
          b = encodeURIComponent($e(this._bodyTextarea.value).clean),
          E = encodeURIComponent(this._draft.labels.join(",")),
          m = `${this._githubUrl}?title=${h}&body=${b}&labels=${E}`;
        window.open(m, "_blank", "noopener,noreferrer");
      }),
      (this._boundKeydown = (h) => lr(e, h)),
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
function xt(d, c, e) {
  return !d ||
    typeof d != "object" ||
    !Object.prototype.hasOwnProperty.call(d, c)
    ? !!e
    : !!d[c];
}
function pr(d, c, e) {
  let t = !xt(d, c, e);
  return (d && typeof d == "object" && (d[c] = t), t);
}
var Wr = ["EMBED", "OCR_REBUILD", "OCR_REDO", "OCR_RUN"];
function tt(d, c) {
  var i, s;
  let t = (c + d).split(`
`),
    r = (i = t.pop()) != null ? i : "",
    n = [];
  for (let o of t)
    for (let l of Wr) {
      let p = l.length;
      if (o.startsWith(l + "_START:")) {
        let u = parseInt(o.slice(p + 7), 10) || 0;
        n.push({ prefix: l, event: "START", total: u });
        break;
      }
      if (o.startsWith(l + "_PROGRESS:")) {
        let _ = o.slice(p + 10).split(":");
        n.push({
          prefix: l,
          event: "PROGRESS",
          current: parseInt(_[0], 10) || 0,
          total: parseInt(_[1], 10) || 0,
          key: (s = _[2]) != null ? s : "",
        });
        break;
      }
      if (o === l + "_DONE" || o.startsWith(l + "_DONE:")) {
        n.push({ prefix: l, event: "DONE" });
        break;
      }
    }
  return { events: n, buffer: r };
}
function dr(d) {
  return { app: { secretStorage: d.secretStorage }, saveData: async () => {} };
}
var Te = class Te extends R.PluginSettingTab {
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
    var u, _;
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
      let f = document.createElement("style");
      ((f.id = "paperforge-tab-styles"),
        (f.textContent = `
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
        document.head.appendChild(f));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let f = e.createDiv({ cls: "paperforge-migration-warning" }),
        g = t
          .map((h) => (h === "paddleocr_api_key" ? "OCR" : "Smart Retrieval"))
          .join(", ");
      (f.createEl("strong", { text: a("migration_banner_title") }),
        f.createEl("p", {
          text: a("migration_banner_body").replace("{modules}", g),
        }),
        f.createEl("p", {
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
          ((_ = (u = this.plugin.manifest) == null ? void 0 : u.version) != null
            ? _
            : "?"),
      }));
    let i = r.createDiv({ cls: "pf-cc-topbar-center" }),
      s = [
        { id: "overview", label: a("tab_overview") || "Overview" },
        { id: "help", label: a("tab_help") || "Help" },
      ],
      o = {};
    if (
      (s.forEach((f) => {
        i.createEl("button", {
          cls:
            "pf-cc-topbar-tab" +
            (f.id === this.activeTab ? " pf-cc-topbar-tab--active" : ""),
          text: f.label,
        }).addEventListener("click", () => {
          ((this._detailReturn = null),
            (this.activeTab = f.id),
            (this._navMemory = { destination: f.id }),
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
        .addEventListener("click", (f) => {
          (f.preventDefault(),
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }));
        }),
      s.forEach((f) => {
        o[f.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (f.id === this.activeTab ? " paperforge-tab-content--active" : ""),
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
      let f = e.querySelector(this._focusTargetId);
      if (
        (!f &&
          this.activeTab === "overview" &&
          (f = e.querySelector(".pf-cc-module-card")),
        f)
      ) {
        try {
          f.focus();
        } catch (g) {}
        this._focusTargetId = null;
      }
    }
    this._displayInProgress = !1;
  }
  _renderOverviewTab(e) {
    var r;
    let t = this._getVaultBasePath();
    (this.plugin.settings.vault_path ||
      ((this.plugin.settings.vault_path = t), this._debouncedSave()),
      e.createEl("h2", { text: a("header_title") || "PaperForge" }),
      e.createEl("p", { text: a("desc"), cls: "paperforge-settings-desc" }),
      this._renderControlCenter(e));
    for (let n of Ve) {
      let i = (r = this._capabilityState) == null ? void 0 : r[n];
      if (!i) continue;
      let s =
          i.capability_state === "unknown" &&
          i.updated_at === new Date(0).toISOString(),
        o =
          i.user_state === "detection_failed" &&
          i.reason.code.endsWith(".stale");
      (s || o) &&
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
            : new me({ version: this.plugin.manifest.version })),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    var n;
    let t = (n = this.plugin.settings.python_path) == null ? void 0 : n.trim();
    if (t && H.existsSync(t)) return { path: t, args: [] };
    let r = ce(this._ensureManagedRuntime().current());
    return r ? { path: r.command, args: [...r.args] } : null;
  }
  _renderInstallationDetail(e) {
    var v, k;
    this._renderModuleDetailShell(e, "installation");
    let t =
        (k = (v = this._capabilityState) == null ? void 0 : v.installation) !=
        null
          ? k
          : se("installation"),
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
      i = (y, x, w, S) => {
        let P = n.createDiv({ cls: "pf-config-row" });
        (P.createEl("span", { cls: "pf-config-key", text: y }),
          P.createEl("span", { cls: S, text: x }),
          P.createEl("span", { cls: "pf-config-value", text: w }));
      };
    i(
      a("foundation_version"),
      "\u2713",
      this.plugin.manifest.version,
      "pf-status-ok"
    );
    let s = this.plugin.settings.python_path || "python";
    i(a("foundation_python"), "\u2014", s, "pf-status-checking");
    let o = this.app.vault.adapter.basePath,
      l = Z.join(o, this.plugin.settings.system_dir || "System"),
      p = H.existsSync(l);
    i(
      a("foundation_vault_structure"),
      p ? "\u2713" : "\u2717",
      p ? l : a("foundation_vault_missing"),
      p ? "pf-status-ok" : "pf-status-error"
    );
    let u =
      this.plugin.settings.zotero_data_dir &&
      H.existsSync(this.plugin.settings.zotero_data_dir);
    i(
      a("foundation_zotero"),
      u ? "\u2713" : "\u2717",
      u ? this.plugin.settings.zotero_data_dir : a("foundation_zotero_missing"),
      u ? "pf-status-ok" : "pf-status-error"
    );
    let _ = !!this.plugin.settings.paddleocr_api_key,
      f =
        !!this.plugin.settings.vector_db_api_key ||
        !!process.env.OPENAI_API_KEY;
    (i(
      a("foundation_paddle_key"),
      _ ? "\u2713" : "\u2717",
      _ ? "Configured" : a("foundation_paddle_missing"),
      _ ? "pf-status-ok" : "pf-status-error"
    ),
      i(
        a("foundation_openai_key"),
        f ? "\u2713" : "\u2717",
        f ? "Configured" : a("foundation_openai_missing"),
        f ? "pf-status-ok" : "pf-status-error"
      ));
    let { execSync: g } = require("child_process");
    try {
      (g("git --version", { timeout: 3e3 }),
        i(a("foundation_git"), "\u2713", "Installed", "pf-status-ok"));
    } catch (y) {
      i(
        a("foundation_git"),
        "\u2717",
        a("foundation_git_missing"),
        "pf-status-error"
      );
    }
    let h = "1.11.4",
      b = "1.11.4",
      E = !0;
    (i(
      a("foundation_obsidian"),
      E ? "\u2713" : "\u2717",
      E ? `\u2265${h}` : a("foundation_obsidian_old"),
      E ? "pf-status-ok" : "pf-status-error"
    ),
      i(
        a("foundation_python_packages"),
        "\u2014",
        a("foundation_python_packages_checking"),
        "pf-status-checking"
      ));
    let { exec: m } = require("child_process");
    (m(`"${s}" --version`, { timeout: 5e3 }, (y) => {
      let x = n.children[1];
      if (x) {
        let w = x.querySelector(".pf-status-checking");
        w &&
          ((w.textContent = y ? "\u2717" : "\u2713"),
          (w.className = y ? "pf-status-error" : "pf-status-ok"));
      }
    }),
      m(
        `"${s}" -c "import paddleocr; import openai; import sqlite3; print('ok')"`,
        { timeout: 1e4 },
        (y) => {
          let x = n.children[n.children.length - 1];
          if (x) {
            let w = x.querySelector(".pf-status-checking");
            w &&
              ((w.textContent = y ? "\u2717" : "\u2713"),
              (w.className = y ? "pf-status-error" : "pf-status-ok"));
          }
        }
      ),
      t.user_state !== "ready" &&
        new R.Setting(r)
          .setName(a("foundation_setup"))
          .setDesc(a("foundation_setup_desc"))
          .addButton((y) =>
            y
              .setButtonText(a("foundation_setup_btn"))
              .setCta()
              .onClick(() => {
                (new R.Notice(a("foundation_running_setup")),
                  (this.plugin.settings._setup_complete = !1),
                  this.plugin.saveSettings(),
                  this.display());
              })
          ),
      new R.Setting(r)
        .setName(a("foundation_reinstall"))
        .setDesc(a("foundation_reinstall_desc"))
        .addButton((y) =>
          y
            .setButtonText(a("foundation_reinstall_btn"))
            .setWarning()
            .onClick(() => {
              new Ee(this.app, this.plugin, () => {
                (this._probeModule("installation"), this._probeModule("help"));
              }).open();
            })
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
    let i = e.createEl("div", { cls: "paperforge-desc-box" });
    (i.setText(a("feat_skills_desc")),
      i.createEl("br"),
      i.createEl("span", { text: a("feat_skills_system") }));
    let s = Z.join(r, t[n]),
      o = [],
      l = [];
    H.existsSync(s) &&
      H.readdirSync(s, { withFileTypes: !0 }).forEach((_) => {
        if (!_.isDirectory()) return;
        let f = Z.join(s, _.name, "SKILL.md");
        if (!H.existsSync(f)) return;
        let g = H.readFileSync(f, "utf-8"),
          h = g.match(/^name:\s*(.+)$/m),
          b = g.split(`
`),
          E = b.findIndex((w) => /^description:/.test(w)),
          m = "";
        if (E >= 0) {
          let w = b[E].match(/^description:\s*(.+)$/);
          if (w && w[1] && w[1] !== ">" && w[1] !== "|-" && w[1] !== "|")
            m = w[1].trim();
          else {
            for (
              let S = E + 1;
              S < b.length && (/^\s{2,}/.test(b[S]) || b[S].trim() === "");
              S++
            )
              m += b[S].trim() + " ";
            m = m.trim();
          }
        }
        let v = g.match(/^source:\s*(.+)$/m),
          k = g.match(/^disable-model-invocation:\s*(.+)$/m),
          y = g.match(/^version:\s*(.+)$/m),
          x = {
            name: h ? h[1].trim() : _.name,
            desc: m,
            source: v ? v[1].trim() : "user",
            disabled: !!k && k[1].trim() === "true",
            version: y ? y[1].trim() : "",
            path: f,
            content: g,
            dirName: _.name,
          };
        x.source === "paperforge" ? o.push(x) : l.push(x);
      });
    let p = e.createEl("div", { cls: "paperforge-skills-box" }),
      u = (_, f, g) => {
        if (f.length === 0) return;
        let h = p.createEl("div", { cls: "paperforge-skills-group" }),
          b = h.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          E = h.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          m = b.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (b.createEl("h4", {
          text: `${_} (${f.length})`,
          cls: "paperforge-skills-subheader",
        }),
          f.forEach((y) => {
            let x = y.name + (y.version ? " v" + y.version : ""),
              w = g
                ? " [" + a("skills_system") + "]"
                : " [" + a("skills_user") + "]",
              S = y.desc || "",
              P = new R.Setting(E).setName(x + w).setDesc(S);
            ((P.settingEl.style.opacity = y.disabled ? "0.4" : "1"),
              P.addToggle((F) => {
                F.setValue(!y.disabled).onChange((T) => {
                  let A = !T,
                    L = y.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? y.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${A}`
                        )
                      : y.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${A}
`
                        );
                  (H.writeFileSync(y.path, L, "utf-8"),
                    (y.disabled = A),
                    (y.content = L),
                    (P.settingEl.style.opacity = y.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let v = g ? "system" : "user";
        ((this._skillsCollapsed[v] || !1) &&
          ((E.style.display = "none"), (m.style.transform = "rotate(-90deg)")),
          b.addEventListener("click", () => {
            (E.style.display !== "none"
              ? ((E.style.display = "none"),
                (m.style.transform = "rotate(-90deg)"))
              : ((E.style.display = ""), (m.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[v] = E.style.display === "none"));
          }));
      };
    (u(a("skills_system"), o, !0),
      u(a("skills_user"), l, !1),
      o.length === 0 &&
        l.length === 0 &&
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
    var o, l;
    this._renderModuleDetailShell(e, "library");
    let t =
        (l = (o = this._capabilityState) == null ? void 0 : o.library) != null
          ? l
          : se("library"),
      r = e.createDiv({ cls: "pf-module-body" });
    (r.createEl("h3", { text: a("md_library_connection") }),
      t.user_state === "ready"
        ? r.createEl("p", { text: a("md_library_ready"), cls: "pf-status-ok" })
        : t.user_state !== "checking" &&
          t.user_state !== "not_enabled" &&
          Vt(r, {
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
      i = n.createDiv({ cls: "pf-module-fact" });
    (i.createEl("span", { text: a("md_library_corpus") }),
      i.createEl("span", { text: a("metric_after_sync") }));
    let s = n.createDiv({ cls: "pf-module-fact" });
    (s.createEl("span", { text: a("md_library_last_sync") }),
      s.createEl("span", {
        text: this.plugin._lastSyncTime || a("metric_not_available"),
      }),
      r.createEl("h3", { text: a("md_configuration") }),
      jt(r, {
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
        onChange: () => {
          new Ee(this.app, this.plugin, () => {
            (this.plugin.savePaperforgeJson({
              zotero_data_dir: this.plugin.settings.zotero_data_dir,
            }),
              this._probeModule("library"));
          }).open();
        },
      }));
  }
  _renderOcrDetail(e) {
    var p, u, _, f, g, h, b, E, m, v;
    this._renderModuleDetailShell(e, "ocr");
    let t =
        (u = (p = this._capabilityState) == null ? void 0 : p.ocr) != null
          ? u
          : se("ocr"),
      r = e.createDiv({ cls: "pf-module-body" });
    r.createEl("h3", { text: a("md_ocr_status") });
    let n = t.pipeline_version,
      i = t.last_pipeline_version,
      o =
        ((f = (_ = t.pipeline_version_summary) == null ? void 0 : _.stale) !=
        null
          ? f
          : 0) > 0;
    if (t.activity_state === "running") {
      Y(r, "checking", a("ocr_state_running"));
      let k = this.plugin._ocrProgress,
        y = r.createDiv({ cls: "pf-ocr-progress-card" });
      if (k != null && k.total) {
        let w = a("ocr_progress")
            .replace("{current}", String(k.current))
            .replace("{total}", String(k.total)),
          S = k.key ? " \u2014 " + k.key : "";
        y.createEl("span", {
          cls: "pf-detail-progress",
          text: a("ocr_state_running") + " " + w + S,
        });
        let P = y.createDiv({ cls: "pf-activity-bar" }),
          F = Math.round((k.current / k.total) * 100);
        P.createDiv({
          cls: "pf-activity-bar-fill",
          attr: {
            style: `width: ${F}%`,
            role: "progressbar",
            "aria-valuenow": String(k.current),
            "aria-valuemin": "1",
            "aria-valuemax": String(k.total),
          },
        });
      }
      let x = this.plugin._ocrProcess;
      x &&
        y
          .createEl("button", {
            cls: "pf-action-btn mod-warning",
            text: a("ocr_stop_batch"),
          })
          .addEventListener("click", () => {
            var S, P;
            (S = x.stdin) != null && S.write
              ? (x.stdin.write(`PAPERFORGE_STOP
`),
                (this.plugin._ocrWasStopped = !0))
              : (P = x.kill) == null || P.call(x, "SIGINT");
          });
    } else if (o) {
      let k = n
        ? a("ocr_state_update_available").replace("{version}", n)
        : a("ocr_state_update_available").replace("{version}", "");
      (Y(r, "action_required", k),
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
            new Ke(
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
      Y(r, "ready");
      let k = n
        ? a("ocr_state_ready")
            .replace(
              "{count}",
              String(
                (b =
                  (h = (g = t.action) == null ? void 0 : g.primary) == null
                    ? void 0
                    : h.scope_count) != null
                  ? b
                  : ""
              )
            )
            .replace("{version}", n)
        : a("ocr_state_ready_no_version").replace(
            "{count}",
            String(
              (v =
                (m = (E = t.action) == null ? void 0 : E.primary) == null
                  ? void 0
                  : m.scope_count) != null
                ? v
                : ""
            )
          );
      (r.createEl("p", { text: k, cls: "pf-status-ok" }),
        z(r, {
          label: a("md_ocr_workspace"),
          onClick: () =>
            this.app.workspace
              .getLeaf()
              .setViewState({ type: "paperforge-ocr-workspace" }),
        }),
        n &&
          i &&
          n !== i &&
          r
            .createDiv({ cls: "pf-ocr-update-banner" })
            .createEl("span", {
              text: a("ocr_state_update_available").replace("{version}", n),
            }));
    }
  }
  _renderAgentDetail(e) {
    var f;
    this._renderModuleDetailShell(e, "agent");
    let t = e.createDiv({ cls: "pf-module-body" });
    (t.createEl("h3", { text: a("md_agent_integration") }),
      t.createEl("p", {
        text: a("md_agent_placeholder"),
        cls: "setting-item-description",
      }));
    let r = {
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
      i = this.plugin.settings.agent_platform || "opencode",
      s = Z.join(this._getVaultBasePath(), n[i]),
      o = H.existsSync(s),
      l = t.createDiv({ cls: "pf-module-facts" }),
      p = l.createDiv({ cls: "pf-module-fact" });
    (p.createEl("span", { text: a("md_agent_platform") }),
      p.createEl("span", { text: (f = r[i]) != null ? f : i }));
    let u = l.createDiv({ cls: "pf-module-fact" });
    (u.createEl("span", { text: a("md_agent_deployment") }),
      u.createEl("span", {
        text: o ? a("agent_deployed") : a("agent_not_deployed"),
      }));
    let _ = l.createDiv({ cls: "pf-module-fact" });
    if (
      (_.createEl("span", { text: a("agent_live_connection") }),
      _.createEl("span", { text: a("md_agent_connection_unknown") }),
      this._agentPlatformDraft === null)
    )
      z(t, {
        label: a("config_change"),
        onClick: () => {
          ((this._agentPlatformDraft = i), this.display());
        },
      });
    else {
      let g = t.createDiv({ cls: "pf-agent-config-editor" }),
        h = g.createEl("select", {
          attr: { "aria-label": a("md_agent_platform") },
        });
      for (let [E, m] of Object.entries(r)) {
        let v = h.createEl("option", { text: m, attr: { value: E } });
        v.selected = E === this._agentPlatformDraft;
      }
      h.addEventListener("change", () => {
        this._agentPlatformDraft = h.value;
      });
      let b = g.createDiv({ cls: "pf-agent-config-actions" });
      (z(b, {
        label: a("config_save"),
        onClick: () => {
          var m;
          let E = (m = this._agentPlatformDraft) != null ? m : i;
          ((this.plugin.settings.agent_platform = E),
            this.plugin.savePaperforgeJson({ agent_platform: E }),
            this.plugin.saveSettings(),
            (this._agentPlatformDraft = null),
            this.display());
        },
      }),
        z(b, {
          label: a("config_cancel"),
          onClick: () => {
            ((this._agentPlatformDraft = null), this.display());
          },
        }),
        z(b, {
          label: a("config_verify"),
          onClick: () => {
            var v;
            let E = (v = this._agentPlatformDraft) != null ? v : i,
              m = H.existsSync(Z.join(this._getVaultBasePath(), n[E]));
            new R.Notice(
              m ? a("agent_verify_found") : a("agent_verify_missing")
            );
          },
        }));
    }
    this._renderSkillsList(t);
  }
  _renderMemoryDetail(e) {
    var m, v, k, y, x, w, S;
    this._renderModuleDetailShell(e, "memory");
    let t =
        (v = (m = this._capabilityState) == null ? void 0 : m.memory) != null
          ? v
          : se("memory"),
      r = e.createDiv({ cls: "pf-module-body" });
    r.createEl("h3", { text: a("md_retrieval_coverage") });
    let n = (y = (k = t.reason) == null ? void 0 : k.code) != null ? y : "",
      i = t.activity_state === "running",
      s =
        (x = t.notices) == null
          ? void 0
          : x.some(
              (P) =>
                P.level === "warning" &&
                (P.message.toLowerCase().includes("api key") ||
                  P.message.toLowerCase().includes("api_key"))
            );
    if (i && t.user_state === "ready") {
      Y(r, "ready");
      let P = (w = t.activity_label) != null ? w : a("cc_activity_running");
      r.createEl("p", { text: P, cls: "pf-status-ok" });
    } else
      n === "memory.disabled"
        ? (Y(r, "not_enabled"),
          r.createEl("p", {
            text: a("sr_state_disabled"),
            cls: "setting-item-description",
          }),
          z(r, {
            label: a("sr_action_enable") || "Enable Smart Retrieval",
            onClick: () => {
              (this.plugin.settings.features ||
                (this.plugin.settings.features = {
                  memory_layer: !0,
                  vector_db: !1,
                }),
                (this.plugin.settings.features.vector_db = !0),
                this.plugin
                  .saveSettings()
                  .then(() => this._probeModule("memory")));
            },
          }))
        : n === "memory.db_missing"
          ? (Y(r, "action_required"),
            r.createEl("p", {
              text: a("sr_state_db_missing"),
              cls: "setting-item-description",
            }),
            z(r, {
              label: a("sr_action_build"),
              onClick: () => this._dispatchMemoryBuild("build"),
            }))
          : n === "memory.backend_upgrade_available"
            ? (Y(r, "action_required"),
              r.createEl("p", {
                text: a("sr_state_upgrade_available"),
                cls: "setting-item-description",
              }),
              (S = t.action) != null &&
                S.primary &&
                z(r, {
                  label: a("sr_action_upgrade"),
                  onClick: () => this._dispatchModuleAction("memory", t),
                }))
            : n === "memory.vector_build_failed"
              ? (Y(r, "action_required"),
                r.createEl("p", {
                  text: a("sr_state_build_failed"),
                  cls: "setting-item-description",
                }),
                z(r, {
                  label: a("cc_action_rebuild_derived"),
                  onClick: () => this._dispatchMemoryBuild("embed"),
                }))
              : n === "memory.schema_stale"
                ? (Y(r, "action_required"),
                  r.createEl("p", {
                    text: t.reason.text,
                    cls: "setting-item-description",
                  }),
                  z(r, {
                    label: a("sr_action_rebuild"),
                    onClick: () => this._dispatchMemoryBuild("build"),
                  }))
                : t.user_state === "ready" &&
                  (Y(r, "ready"),
                  r.createEl("p", {
                    text: a("md_retrieval_ready"),
                    cls: "pf-status-ok",
                  }));
    s &&
      r
        .createDiv({ cls: "pf-notice-warning" })
        .createEl("span", { text: a("sr_api_key_notice") });
    let o = r.createDiv({ cls: "pf-module-facts" }),
      l = o.createDiv({ cls: "pf-module-fact" });
    (l.createEl("span", { text: a("md_retrieval_coverage") }),
      l.createEl("span", {
        text:
          t.user_state === "ready"
            ? a("coverage_complete")
            : a("metric_not_available"),
      }));
    let p = o.createDiv({ cls: "pf-module-fact" });
    if (
      (p.createEl("span", { text: a("retrieval_freshness") }),
      p.createEl("span", {
        text:
          t.updated_at && t.updated_at !== new Date(0).toISOString()
            ? new Date(t.updated_at).toLocaleString()
            : a("metric_not_available"),
      }),
      r.createEl("h4", {
        text: a("feat_vector_config_label") || "Configuration",
      }),
      n === "memory.disabled")
    ) {
      let P = r.createDiv({ cls: "pf-module-field" }),
        F = P.createEl("label", {
          text: a("feat_vector_enable") || "Enable",
          cls: "setting-item-name",
        });
      F.style.cursor = "pointer";
      let T = P.createEl("input", { attr: { type: "checkbox" } });
      ((T.checked = !1),
        T.addEventListener("change", () => {
          (this.plugin.settings.features ||
            (this.plugin.settings.features = {
              memory_layer: !0,
              vector_db: !1,
            }),
            (this.plugin.settings.features.vector_db = T.checked),
            this.plugin.saveSettings().then(() => {
              T.checked && this._probeModule("memory");
            }));
        }));
    }
    let u = r.createDiv({ cls: "pf-module-field" });
    u.createEl("label", {
      text: a("feat_openai_key") || "API Key",
      cls: "setting-item-name",
    });
    let _ = u.createEl("input", {
        cls: "pf-module-input",
        attr: {
          type: "password",
          placeholder: this.plugin.settings._vector_db_configured
            ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored)"
            : "sk-...",
        },
      }),
      f = null;
    _.addEventListener("input", () => {
      let P = _.value;
      P &&
        (f && clearTimeout(f),
        (f = setTimeout(async () => {
          let F = this.app.secretStorage;
          if (F != null && F.setSecret) {
            try {
              (await F.setSecret("vector-db-api-key", P),
                (await F.getSecret("vector-db-api-key")) === P &&
                  ((this.plugin.settings._vector_db_configured = !0),
                  (this.plugin.settings.vector_db_api_key = ""),
                  await this.plugin.saveSettings(),
                  (_.value = ""),
                  (_.placeholder =
                    "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored)")));
            } catch (T) {}
            f = null;
          }
        }, 600)));
    });
    let g = r.createDiv({ cls: "pf-module-field" });
    g.createEl("label", {
      text: a("feat_api_base_url") || "API Base URL",
      cls: "setting-item-name",
    });
    let h = g.createEl("input", {
      cls: "pf-module-input",
      attr: { type: "text", placeholder: "https://api.openai.com/v1" },
    });
    ((h.value = this.plugin.settings.vector_db_api_base || ""),
      h.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_base = h.value),
          this.plugin.saveSettings());
      }));
    let b = r.createDiv({ cls: "pf-module-field" });
    b.createEl("label", {
      text: a("feat_api_model") || "Model",
      cls: "setting-item-name",
    });
    let E = b.createEl("input", {
      cls: "pf-module-input",
      attr: { type: "text", placeholder: "text-embedding-3-small" },
    });
    ((E.value =
      this.plugin.settings.vector_db_api_model || "text-embedding-3-small"),
      E.addEventListener("change", () => {
        ((this.plugin.settings.vector_db_api_model = E.value),
          this.plugin.saveSettings());
      }),
      (n === "memory.db_missing" ||
        n === "memory.vector_build_failed" ||
        n === "memory.schema_stale" ||
        t.user_state === "ready") &&
        (r.createEl("p", { cls: "setting-item-description", text: " " }),
        z(r, {
          label:
            n === "memory.db_missing"
              ? a("sr_action_build") || "Build Index"
              : a("cc_action_rebuild_derived") || "Rebuild Index",
          onClick: () =>
            this._dispatchMemoryBuild(
              n === "memory.db_missing" ? "build" : "embed"
            ),
        })));
  }
  _dispatchModuleAction(e, t) {
    var s, o, l, p;
    let r = (s = t.action) == null ? void 0 : s.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    let n = r.verb,
      i = (o = r.command) != null ? o : "";
    if (r.safety_class !== "safe" && r.confirmation_required) {
      new Ke(
        this.app,
        {
          title: r.label,
          effectLabel:
            (l =
              (r.replacement_facts || []).join("; ") ||
              r.confirmation_prompt) != null
              ? l
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
    var i, s, o;
    if (
      (t === "setup" || t === "set_config") &&
      r === "paperforge setup" &&
      (e === "installation" || e === "library" || e === "ocr" || e === "memory")
    ) {
      let l = [e];
      (e === "installation" && l.push("help"),
        new Ee(this.app, this.plugin, () => {
          for (let p of l) this._probeModule(p);
        }).open());
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
            let l = this._getVaultBasePath(),
              p = cr(
                n.reason.code,
                n.reason.text,
                (o =
                  (s = (i = n.action) == null ? void 0 : i.primary) == null
                    ? void 0
                    : s.scope_count) != null
                  ? o
                  : 0,
                l
              );
            new Qe(
              this.app,
              p,
              "https://github.com/LLLin000/PaperForge/issues/new"
            ).open();
            return;
          }
          if (r === "paperforge ocr doctor") {
            this._callPython(["ocr", "doctor"], {
              timeout: 3e4,
              onClose: (l) => {
                (this._probeModule("ocr"), this.display());
              },
            });
            return;
          }
          if (r === "paperforge ocr list --json") {
            this._callPython(["ocr", "list", "--json"], {
              timeout: 3e4,
              onClose: (l) => {
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
            onClose: (l) => {
              (this._probeModule("memory"), this.display());
            },
          });
          return;
        }
      }
    }
    (new R.Notice(
      (a("action_unknown_pair") || "Unknown action: {verb}").replace(
        "{verb}",
        t
      ),
      5e3
    ),
      this._probeModule(e));
  }
  _dispatchOcrAction(e) {
    var l;
    let t = this.app.vault.adapter.basePath;
    if (!this._resolveRuntimeCommand(t)) {
      new R.Notice(a("runtime_not_available") || "No Python runtime available");
      return;
    }
    let n =
        e === "run"
          ? ["ocr", "run"]
          : e === "rebuild"
            ? ["ocr", "rebuild", "--all"]
            : ["ocr", "redo"],
      i = {
        run: "Running OCR\u2026",
        rebuild: "Rebuilding OCR derived artifacts\u2026",
        redo: "Running OCR redo\u2026",
      },
      s = (l = this._capabilityState) != null ? l : {};
    (s.ocr &&
      ((s.ocr.activity_state = "running"),
      (s.ocr.activity_label = i[e] || "Running\u2026"),
      (s.ocr.activity_progress = { current: 0, total: 1 })),
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
          { events: _, buffer: f } = tt(
            u,
            (g = this.plugin._ocrBuffer) != null ? g : ""
          );
        this.plugin._ocrBuffer = f;
        for (let h of _)
          h.event === "START"
            ? (this.plugin._ocrProgress &&
                (this.plugin._ocrProgress.total = h.total || 1),
              s.ocr &&
                (s.ocr.activity_progress = { current: 0, total: h.total || 1 }))
            : h.event === "PROGRESS" &&
              ((this.plugin._ocrProgress = {
                current: h.current || 0,
                total: h.total || 1,
                key: h.key || "",
              }),
              s.ocr &&
                (s.ocr.activity_progress = {
                  current: h.current || 0,
                  total: h.total || 1,
                }));
        this.display();
      },
      onError: (p) => {
        ((this.plugin._ocrProcess = null),
          s.ocr &&
            ((s.ocr.activity_state = "idle"),
            (s.ocr.activity_label = null),
            (s.ocr.activity_progress = null)),
          new R.Notice(a("ocr_error_notice"), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
      onClose: (p) => {
        ((this.plugin._ocrProcess = null),
          s.ocr &&
            ((s.ocr.activity_state = "idle"),
            (s.ocr.activity_label = null),
            (s.ocr.activity_progress = null)),
          p === 0
            ? new R.Notice(
                e === "run"
                  ? a("ocr_run_complete")
                  : e === "rebuild"
                    ? a("ocr_rebuild_complete")
                    : a("ocr_redo_complete")
              )
            : p === 130 || this.plugin._ocrWasStopped
              ? ((this.plugin._ocrWasStopped = !1),
                new R.Notice(a("ocr_stopped_notice")))
              : new R.Notice(a("ocr_failed_notice"), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
    });
    this.plugin._ocrProcess = o;
  }
  _dispatchMemoryBuild(e) {
    var s;
    let t = this.app.vault.adapter.basePath,
      r = (s = this._capabilityState) != null ? s : {};
    (r.memory &&
      ((r.memory.activity_state = "running"),
      (r.memory.activity_label =
        e === "embed"
          ? "Building vector index\u2026"
          : "Building memory\u2026")),
      this.display());
    let n = e === "embed" ? ["embed", "build", "--force"] : ["memory", "build"],
      i = e === "embed" ? "Vector index" : "Memory";
    if (e === "embed") {
      ((this.plugin._embedBuffer = ""),
        (this.plugin._embedProgress = { current: 0, total: 0, key: "" }));
      let o = this._callPython(n, {
        stream: !0,
        onData: (l) => {
          var f;
          let p =
              typeof l == "string"
                ? l
                : Buffer.isBuffer(l)
                  ? l.toString("utf-8")
                  : String(l),
            { events: u, buffer: _ } = tt(
              p,
              (f = this.plugin._embedBuffer) != null ? f : ""
            );
          this.plugin._embedBuffer = _;
          for (let g of u)
            g.event === "PROGRESS" &&
              ((this.plugin._embedProgress = {
                current: g.current || 0,
                total: g.total || 0,
                key: g.key || "",
              }),
              r.memory &&
                (r.memory.activity_progress = {
                  current: g.current || 0,
                  total: g.total || 1,
                }));
          this.display();
        },
        onError: (l) => {
          ((this.plugin._embedProcess = null),
            r.memory &&
              ((r.memory.activity_state = "idle"),
              (r.memory.activity_label = null),
              (r.memory.activity_progress = null)),
            new R.Notice(i + " build error: " + (l.message || l), 8e3),
            this._probeModule("memory"),
            this.display());
        },
        onClose: (l) => {
          ((this.plugin._embedProcess = null),
            r.memory &&
              ((r.memory.activity_state = "idle"),
              (r.memory.activity_label = null),
              (r.memory.activity_progress = null)),
            l === 0
              ? new R.Notice(i + " build complete.")
              : new R.Notice(
                  i + " build failed with exit code " + (l != null ? l : "?"),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
      this.plugin._embedProcess = o;
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (o, l, p) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            o === 0
              ? new R.Notice(i + " rebuild complete")
              : new R.Notice(
                  i + " build failed" + (p ? ": " + p.slice(0, 120) : ""),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t) {
    var E, m, v, k, y, x;
    e.classList.add("pf-module-detail");
    let r = t === "agent" ? "agent_detail_heading" : t + "_detail_heading",
      n = "pf-" + t + "-detail-heading";
    e.createEl("button", {
      cls: "pf-back-btn",
      text: a("btn_back_to_overview"),
    }).addEventListener("click", () => {
      (this._detailReturn
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId = `button.pf-cc-module-card[data-module="${t}"]`)),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let s = this._getOverviewModules(),
      o = e.createDiv({
        cls: "pf-module-detail-selector",
        attr: { role: "tablist", "aria-label": a("md_module_switcher") },
      });
    for (let w of s)
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
      attr: { "aria-label": a("md_module_switcher") },
    });
    for (let w of s) {
      let S = l.createEl("option", { text: w.label, attr: { value: w.id } });
      S.selected = w.id === t;
    }
    (l.addEventListener("change", () => {
      ((this._selectedDetailModule = l.value),
        (this._focusTargetId = "#pf-" + l.value + "-detail-heading"),
        this.display());
    }),
      e.createEl("h2", {
        cls: "pf-module-detail-heading",
        text: a(r),
        attr: { id: n, tabindex: "-1" },
      }));
    let p =
        t === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (m = (E = this._capabilityState) == null ? void 0 : E[t]) != null
            ? m
            : se(t),
      u =
        (v = p.user_state) != null
          ? v
          : p.capability_state === "ready"
            ? "ready"
            : "action_required",
      _ = e.createDiv({
        cls: "pf-module-summary",
        attr: { "aria-live": "polite" },
      }),
      f = _.createDiv({ cls: "pf-module-summary-header" });
    (f.createEl("span", {
      cls: "pf-module-summary-name",
      text: this._getUserModuleName(t),
    }),
      Y(f, u, this._getUserStateLabel(u)),
      _.createEl("p", {
        cls: "pf-module-summary-consequence",
        text: this._getModuleConsequence(t, p),
      }),
      p.activity_state === "running" &&
        Ht(_, {
          label: a("cc_activity_running"),
          progress: p.activity_progress,
        }));
    let g = (k = p.action) == null ? void 0 : k.primary;
    if (g && u !== "ready" && t !== "agent") {
      let w =
          "action_" +
          ((y = g.action_id) != null ? y : g.verb).replace(/[.-]/g, "_"),
        S = a(w),
        P =
          S !== w
            ? S
            : a("cc_action_" + g.verb) !== "cc_action_" + g.verb
              ? a("cc_action_" + g.verb)
              : a("cc_action_probe");
      z(_, {
        label: P,
        loading: p.activity_state === "running",
        onClick: () => this._dispatchModuleAction(t, p),
      });
    }
    let h = _.createEl("details", { cls: "pf-module-diagnostics" });
    h.createEl("summary", { text: a("advanced_diagnostics") });
    let b = h.createDiv({ cls: "pf-module-diagnostics-body" });
    (b.createEl("div", { text: a("cc_diag_module") + ": " + p.module }),
      b.createEl("div", {
        text: a("cc_diag_state") + ": " + this._getUserStateLabel(u),
      }),
      b.createEl("div", { text: a("cc_diag_severity") + ": " + p.severity }),
      b.createEl("div", {
        text: a("cc_diag_activity") + ": " + p.activity_state,
      }),
      b.createEl("div", { text: a("cc_diag_reason") + ": " + p.reason.code }),
      b.createEl("div", {
        text: a("cc_diag_ttl") + ": " + p.ttl_seconds + "s",
      }));
    for (let w of (x = p.notices) != null ? x : [])
      b.createEl("div", { text: w.message });
    b.createEl("div", {
      text:
        a("cc_diag_updated") + ": " + new Date(p.updated_at).toLocaleString(),
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
    for (let [n, i] of r)
      t.createEl("button", {
        cls: "pf-help-task-btn",
        text: i,
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
    let n = fe();
    (0, ne.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (i, s) => {
        if (i) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(s);
          if (o.ok) {
            let l = o.data,
              p = l.fresh ? "fresh" : "stale";
            r(
              `Papers: ${l.paper_count_db} | ${p}${l.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (o) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    let n = fe();
    (0, ne.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (i, s) => {
        if (i) {
          r("Status unavailable");
          return;
        }
        try {
          let o = JSON.parse(s);
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
    let i = [...n.args, "-m", "paperforge", "--vault", r, ...e],
      s = (t == null ? void 0 : t.credentialType) && !(t != null && t.env),
      o = (u) => {
        let _ = (0, ne.spawn)(n.path, i, { cwd: r, env: u, windowsHide: !0 });
        return (
          t.onData && _.stdout.on("data", t.onData),
          t.onStderr && _.stderr.on("data", t.onStderr),
          t.onError && _.on("error", t.onError),
          _.on("close", t.onClose),
          _
        );
      },
      l = (u) => {
        (0, ne.execFile)(
          n.path,
          i,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: u },
          (_, f, g) => {
            t && t.onClose && t.onClose(_ ? 1 : 0, f, g);
          }
        );
      };
    if (s)
      return (
        he(dr(this.app), t.credentialType).then((u) => {
          t && t.stream ? o(u) : l(u);
        }),
        null
      );
    let p = (t == null ? void 0 : t.env) || fe();
    return t && t.stream ? o(p) : (l(p), null);
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
        let s = this.app.vault.adapter.basePath,
          o = this._resolveRuntimeCommand(s);
        if (!(o != null && o.path)) {
          new R.Notice(a("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", o.path),
          n.setText(a("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (l, p, u) => {
              (console.log(
                "[PaperForge] memory build exit:",
                l ? "FAIL:" + l : "OK",
                (p || "").slice(0, 200),
                (u || "").slice(0, 200)
              ),
                n.setText(a("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                l === 0
                  ? new R.Notice(a("feat_memory_rebuild_done"))
                  : new R.Notice(
                      a("feat_memory_rebuild_failed") +
                        (u ? " " + u.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = yt(s)),
                this._refreshSnapshots(s));
            },
          }));
      }));
    let i = e.createEl("button", {
      cls: "paperforge-refresh-btn",
      text: "\u21BB",
    });
    ((i.title = "Sync now"),
      (i.onclick = () => {
        ((this._memoryStatusText = null), this._runManualSync());
      }));
  }
  _getBuildCommand(e) {
    let t = this.app.vault.adapter.basePath,
      r = this._resolveRuntimeCommand(t);
    return r ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    var i;
    let e = this.app.vault.adapter.basePath,
      t = this._resolveRuntimeCommand(e);
    if (!(t != null && t.path)) return;
    let r = (i = this._capabilityState) != null ? i : {};
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
        onClose: (s) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            s === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this._probeModule("library", s != null ? s : 1),
            this.display(),
            this._refreshSnapshots(e),
            et(this.app, this.plugin, e));
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
      (0, ne.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (n, i, s) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = yt(e)),
            (this._embedStatusText = De(e)),
            this.display());
        }
      ));
  }
  _renderVectorSection(e) {
    var l;
    if (
      (e.createEl("h4", { text: "Smart Retrieval" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(a("feat_vector_desc")),
      new R.Setting(e)
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
      i = n.createEl("span", {
        text: "\u25BC",
        cls: "paperforge-skills-arrow",
      });
    n.createEl("span", {
      cls: "paperforge-vec-header-label",
      text: a("feat_vector_config_label"),
    });
    let s = e.createEl("div", { cls: "paperforge-vector-config" }),
      o = (p) => {
        ((s.style.display = p ? "none" : ""),
          (i.style.transform = p ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (o(xt(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let p = pr(this._featurePanelsCollapsed, "vectorConfig", !1);
        o(p);
      }),
      this._vectorDepsOk === !0)
    ) {
      this._renderVectorReady(s, r);
      return;
    }
    if (this._vectorDepsOk === !1) {
      this._renderVectorNoDeps(s);
      return;
    }
    if (this._vectorDepsOk === null) {
      let p = Je(r);
      ((this._vectorDepsOk = p && (l = p.deps_installed) != null ? l : !1),
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
    (new R.Setting(e)
      .setName(a("feat_openai_key"))
      .setDesc(a("feat_openai_key_desc"))
      .addText((i) => {
        ((i.inputEl.type = "password"),
          i
            .setPlaceholder(r)
            .setValue("")
            .onChange((s) => {
              s &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  let o = this.app.secretStorage;
                  if (o != null && o.setSecret) {
                    try {
                      (await o.setSecret("vector-db-api-key", s),
                        (await o.getSecret("vector-db-api-key")) === s &&
                          ((this.plugin.settings._vector_db_configured = !0),
                          (this.plugin.settings.vector_db_api_key = ""),
                          await this.plugin.saveSettings(),
                          i.setValue("")));
                    } catch (l) {}
                    n = null;
                  }
                }, 600)));
            }));
      }),
      new R.Setting(e)
        .setName(a("feat_api_base_url"))
        .setDesc(a("feat_api_base_url_desc"))
        .addText((i) => {
          i.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((s) => {
              ((this.plugin.settings.vector_db_api_base = s),
                this.plugin.saveSettings());
            });
        }),
      new R.Setting(e)
        .setName(a("feat_api_model"))
        .setDesc(a("feat_api_model_desc"))
        .addText((i) => {
          i.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((s) => {
              ((this.plugin.settings.vector_db_api_model = s),
                this.plugin.saveSettings());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(a("feat_deps_missing")),
      new R.Setting(e)
        .setName(a("feat_install_deps"))
        .setDesc(a("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(a("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                i = this._resolveRuntimeCommand(n);
              if (!(i != null && i.path)) {
                new R.Notice(a("feat_no_python"));
                return;
              }
              (r.setButtonText(a("feat_installing")), r.setDisabled(!0));
              let s = "chromadb openai",
                o = new R.Notice(
                  a("feat_installing_pkgs").replace("{pkgs}", s),
                  0
                );
              try {
                let l = Object.assign(fe(), {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  p = s.split(" ");
                (await new Promise((u, _) => {
                  (0, ne.execFile)(
                    i.path,
                    [...i.args, "-m", "pip", "install", ...p],
                    { cwd: n, timeout: 3e5, env: l, windowsHide: !0 },
                    (f) => {
                      f ? _(f) : u();
                    }
                  );
                }),
                  o.hide(),
                  new R.Notice(a("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = De(n)),
                  this.display());
              } catch (l) {
                (o.hide(),
                  new R.Notice(
                    a("feat_install_failed") + (l.stderr || l.message || l)
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
    let s = n.createEl("div", { cls: "paperforge-embed-controls" }),
      o = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (s.empty(), o.empty());
      let p = Je(t),
        u = p == null ? void 0 : p.build_state,
        _ = u && typeof u == "object" && !Array.isArray(u) ? u : {};
      ((this.plugin._embedProgress = this.plugin._embedProgress || {
        current: 0,
        total: 0,
        key: "",
      }),
        !this.plugin._embedProcess &&
          _.status === "running" &&
          (this.plugin._embedProgress = {
            current: typeof _.current == "number" ? _.current : 0,
            total: typeof _.total == "number" ? _.total : 1,
            key: typeof _.paper_id == "string" ? _.paper_id : "",
          }));
      let { current: f, total: g, key: h } = this.plugin._embedProgress,
        b =
          typeof (p == null ? void 0 : p.body_chunk_count) == "number"
            ? p.body_chunk_count
            : 0,
        E =
          typeof (p == null ? void 0 : p.object_chunk_count) == "number"
            ? p.object_chunk_count
            : 0,
        v =
          (typeof (p == null ? void 0 : p.chunk_count) == "number"
            ? p.chunk_count
            : 0) +
          b +
          E,
        k = v > 0,
        y = p !== null && typeof p.corrupted == "boolean" && p.corrupted,
        x = !!this.plugin._embedProcess,
        w = !this.plugin._embedProcess && _.status === "running",
        S =
          (p == null ? void 0 : p.deps_installed) !== void 0
            ? !!p.deps_installed
            : !0,
        P = typeof _.status == "string" ? _.status : "",
        F = typeof _.message == "string" ? _.message : "",
        T = async (C) => {
          var J;
          if (C === "--resume" && k && !y) {
            let M = a("retrieval_rebuild_warning").replace("{n}", String(v));
            if (!confirm(M)) return;
          }
          if (C === "--force" && k && !y) {
            let M =
              "Force rebuild will replace " +
              v +
              " existing chunk(s). Continue?";
            if (!confirm(M)) return;
          }
          let V = this._resolveRuntimeCommand(t);
          if (!(V != null && V.path)) {
            new R.Notice(a("retrieval_no_python"));
            return;
          }
          let Q = await he(dr(this.app), "embed");
          ((Q.PYTHONIOENCODING = "utf-8"),
            (Q.PYTHONUTF8 = "1"),
            (Q.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (Q.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", C],
              {
                stream: !0,
                env: Q,
                onData: (M) => {
                  var de;
                  let ae =
                      typeof M == "string"
                        ? M
                        : Buffer.isBuffer(M)
                          ? M.toString("utf-8")
                          : String(M),
                    { events: oe, buffer: ke } = tt(
                      ae,
                      (de = this.plugin._embedBuffer) != null ? de : ""
                    );
                  this.plugin._embedBuffer = ke;
                  for (let W of oe)
                    W.event === "START"
                      ? (this.plugin._embedProgress.total = W.total || 0)
                      : W.event === "PROGRESS"
                        ? ((this.plugin._embedProgress.current =
                            W.current || 0),
                          (this.plugin._embedProgress.key = W.key || ""))
                        : W.event === "DONE" &&
                          ((this.plugin._embedProcess = null),
                          (this.plugin._embedProgress.current =
                            this.plugin._embedProgress.total));
                  this.display();
                },
                onStderr: (M) => {
                  (this.plugin._embedStderr || (this.plugin._embedStderr = ""),
                    (this.plugin._embedStderr += String(M)));
                },
                onError: (M) => {
                  ((this.plugin._embedProcess = null),
                    new R.Notice(
                      a("feat_build_failed") + ": " + (M.message || M)
                    ),
                    this.display());
                },
                onClose: (M) => {
                  var ae;
                  if (
                    (clearInterval(
                      (ae = this.plugin._embedPollInterval) != null
                        ? ae
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    M === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = De(t)),
                      new R.Notice(a("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let oe = (this.plugin._embedStderr || "").slice(0, 200);
                    new R.Notice(
                      a("feat_build_failed") + (oe ? ": " + oe : ""),
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
              (J = this.plugin._embedPollInterval) != null ? J : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (M, ae) => {
                    var oe;
                    if (((this.plugin._embedPolling = !1), M === 0 && ae))
                      try {
                        let de = JSON.parse(ae).data;
                        if (de && de.build_state) {
                          let W = de.build_state;
                          ((W.status === "stopping" || W.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (oe = this.plugin._embedPollInterval) != null
                                ? oe
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            W.current !== void 0 &&
                              W.total !== void 0 &&
                              ((this.plugin._embedProgress.current = W.current),
                              (this.plugin._embedProgress.total = W.total || 1),
                              (this.plugin._embedProgress.key =
                                W.paper_id || "")));
                        }
                      } catch (ke) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        A = ze(t),
        O = !1;
      A &&
        typeof A.summary == "object" &&
        A.summary !== null &&
        "status" in A.summary &&
        (O = A.summary.status === "version_mismatch");
      let L;
      switch (
        (S
          ? O
            ? (L = "runtime-mismatch")
            : P === "stopping"
              ? (L = "stopping")
              : x && P === "running"
                ? (L = "building")
                : P === "failed"
                  ? (L = "failed")
                  : P === "stopped"
                    ? (L = "stopped")
                    : w
                      ? (L = "stale")
                      : y
                        ? (L = "corrupted")
                        : k
                          ? (L = "ready")
                          : (L = "idle")
          : (L = "deps-missing"),
        L)
      ) {
        case "building": {
          let C = s.createEl("div", { cls: "paperforge-progress-track" });
          C.style.cssText = "flex:1;";
          let V = g > 0 ? ((f / g) * 100).toFixed(1) : "0",
            Q = C.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Q.style.cssText = `width:${V}%; min-width:${f > 0 ? "2px" : "0"};`),
            f < g)
          ) {
            let M = C.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            M.style.cssText = `width:${(100 - parseFloat(V)).toFixed(1)}%;`;
          }
          (o.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${f}/${g} papers`,
          }),
            h &&
              o.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${h})`,
              }));
          let J = s.createEl("button");
          (J.setText(a("retrieval_stop")),
            (J.className = "mod-warning"),
            J.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let C = s.createEl("div", { cls: "paperforge-progress-track" });
          C.style.cssText = "flex:1; opacity:0.5;";
          let V = g > 0 ? ((f / g) * 100).toFixed(1) : "0",
            Q = C.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((Q.style.cssText = `width:${V}%; min-width:${f > 0 ? "2px" : "0"};`),
            f < g)
          ) {
            let M = C.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            M.style.cssText = `width:${(100 - parseFloat(V)).toFixed(1)}%;`;
          }
          o.createEl("span", { text: a("retrieval_build_stopping") });
          let J = s.createEl("button");
          (J.setText(a("retrieval_stop")),
            (J.className = "mod-warning"),
            J.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("retrieval_build_failed") + (F ? ": " + F : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let C = s.createEl("button");
          (C.setText(a("retrieval_retry")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--resume")));
          let V = s.createEl("button");
          (V.setText(a("retrieval_force_rebuild")),
            (V.style.marginLeft = "6px"),
            V.addEventListener("click", () => T("--force")));
          break;
        }
        case "stopped": {
          o.setText(a("retrieval_build_stopped"));
          let C = s.createEl("button");
          (C.setText(a("retrieval_retry")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--resume")));
          break;
        }
        case "corrupted": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let C = s.createEl("button");
          (C.setText(a("retrieval_force_rebuild")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--force")));
          break;
        }
        case "stale": {
          o.createEl("div", {
            cls: "paperforge-desc-box",
            text: a("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let C = s.createEl("button");
          (C.setText(a("retrieval_rebuild_vectors")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--resume")));
          break;
        }
        case "ready": {
          s.createEl("span", {
            text: v + " chunks embedded",
            cls: "setting-item-description",
          });
          let C = s.createEl("button");
          (C.setText(a("retrieval_rebuild_vectors")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--resume")));
          let V = s.createEl("button");
          (V.setText(a("retrieval_force_rebuild")),
            (V.style.marginLeft = "6px"),
            V.addEventListener("click", () => T("--force")));
          break;
        }
        case "deps-missing": {
          o.setText(a("retrieval_build_deps_missing"));
          let C = s.createEl("a");
          (C.setText(a("feat_install_deps")),
            (C.style.cssText = "cursor:pointer; text-decoration:underline;"),
            C.addEventListener("click", () => {
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
          let C = s.createEl("a");
          (C.setText(a("runtime_health_sync")),
            (C.style.cssText = "cursor:pointer; text-decoration:underline;"),
            C.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          o.setText(a("retrieval_build_idle"));
          let C = s.createEl("button");
          (C.setText(a("feat_build_btn")),
            (C.className = "mod-cta"),
            C.addEventListener("click", () => T("--resume")));
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
    if (!H.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new R.Notice(r, 4e3));
      return;
    }
    try {
      H.accessSync(e, H.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new R.Notice(n, 4e3));
      return;
    }
    (0, ne.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let l = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      let i = n.match(/Python (\d+)\.(\d+)/);
      if (!i) {
        let l = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      let s = parseInt(i[1], 10),
        o = parseInt(i[2], 10);
      if (s < 3 || (s === 3 && o < 11)) {
        let l =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      (0, ne.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (l) => {
        if (l) {
          let p = `\u2713 Python ${s}.${o} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${p}</span>`),
            new R.Notice(p, 4e3));
        } else {
          let p = `\u2713 Python ${s}.${o} \u6709\u6548 / Valid`;
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
    (0, ne.execFile)(
      r.path,
      [...r.args, "--version"],
      { timeout: 8e3 },
      (n, i) => {
        let s = [];
        s.push({
          label: "environment",
          ok: !n,
          detail: n ? a("check_python_fail") : i.trim(),
        });
        let o = !1,
          l = process.env.HOME || process.env.USERPROFILE || ur.homedir() || "";
        if (process.platform === "darwin")
          o = [
            "/Applications/Zotero.app",
            Z.join(l, "Applications", "Zotero.app"),
          ].some((b) => {
            try {
              return H.existsSync(b);
            } catch (E) {
              return !1;
            }
          });
        else if (process.platform === "win32") {
          let h = process.env.ProgramFiles || "",
            b = process.env.LOCALAPPDATA || "";
          o = [
            Z.join(h, "Zotero"),
            Z.join(h, "(x86)", "Zotero"),
            Z.join(b, "Programs", "Zotero"),
            Z.join(b, "Zotero"),
            Z.join(l, "AppData", "Local", "Programs", "Zotero"),
          ]
            .filter(Boolean)
            .some((m) => {
              try {
                return H.existsSync(m);
              } catch (v) {
                return !1;
              }
            });
        } else
          o = [
            Z.join(l, ".local", "share", "zotero", "zotero"),
            "/usr/bin/zotero",
            "/usr/local/bin/zotero",
          ].some((b) => {
            try {
              return H.existsSync(b);
            } catch (E) {
              return !1;
            }
          });
        let p = this.plugin.settings.zotero_data_dir;
        if (!o && p)
          try {
            o = H.existsSync(p);
          } catch (h) {}
        s.push({
          label: "Zotero",
          ok: o,
          detail: o ? a("check_zotero_ok") : a("check_zotero_fail"),
        });
        let u = !1,
          _ = process.env.APPDATA || "";
        (process.platform === "win32" &&
          _ &&
          (u = Ge(Z.join(_, "Zotero", "Zotero", "Profiles"))),
          !u &&
            process.platform === "darwin" &&
            l &&
            (u = Ge(
              Z.join(l, "Library", "Application Support", "Zotero", "Profiles")
            )),
          !u &&
            process.platform !== "win32" &&
            process.platform !== "darwin" &&
            l &&
            (u = Ge(Z.join(l, ".zotero", "zotero", "Profiles"))),
          !u && p && String(p).trim() && (u = gt(p.trim())),
          !u && l && (u = gt(Z.join(l, "Zotero"))),
          s.push({
            label: "Better BibTeX",
            ok: u,
            detail: u ? a("check_bbt_ok") : a("check_bbt_fail"),
          }));
        let f = { true: "\u2713", false: "\u2717" };
        if (this._checkEl) {
          this._checkEl.setText(
            s.map((b) => `${f[String(b.ok)]} ${b.label}: ${b.detail}`).join(`
`)
          );
          let h = s.some((b) => !b.ok);
          this._checkEl.className = `paperforge-message msg-${h ? "error" : "ok"}`;
        }
        let g = s.filter((h) => !h.ok);
        (g.length > 0 &&
          new R.Notice(
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
    let t = _r.default.versions || [];
    for (let i of t) {
      let s = e.createEl("div", { cls: "paperforge-release-card" }),
        o = s.createEl("div", { cls: "paperforge-release-header" });
      if (
        (o.createEl("strong", { text: `v${i.version} \u2014 ${i.title}` }),
        o.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${i.date})`,
        }),
        i.breaking_or_migration && i.breaking_or_migration.length > 0)
      ) {
        let l = s.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let p of i.breaking_or_migration)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (i.new_features && i.new_features.length > 0) {
        let l = s.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let p of i.new_features)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (i.fixes && i.fixes.length > 0) {
        let l = s.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let p of i.fixes)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${p}`,
          });
      }
      if (i.recommended_actions && i.recommended_actions.length > 0) {
        let l = s.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let p of i.recommended_actions)
          l.createEl("div", {
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
    ((this._capabilityState = It(e != null ? e : {}, Ve)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var l, p, u, _;
    if (this._probing.has(e)) return;
    this._probing.add(e);
    let r = (l = this._capabilityState) == null ? void 0 : l[e],
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
        notices: (u = r == null ? void 0 : r.notices) != null ? u : [],
        user_state: "checking",
        capability_kind:
          e === "installation" || e === "library" ? "required" : "optional",
        maintenance_eligible: !1,
        user_visible_failure: !1,
        user_impact: null,
        updated_at: new Date().toISOString(),
        ttl_seconds: (_ = r == null ? void 0 : r.ttl_seconds) != null ? _ : 0,
      };
    this._updateCapabilityEnvelope(e, n);
    let i = this.app.vault.adapter.basePath,
      s = this._resolveRuntimeCommand(i);
    if (!s) {
      if ((this._probing.delete(e), e === "installation")) {
        let f = {
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
          action: { primary: Lt() },
          notices: [],
          user_state: "setup_required",
          capability_kind: "required",
          maintenance_eligible: !1,
          user_visible_failure: !1,
          user_impact: null,
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, f);
      } else this._updateCapabilityEnvelope(e, Pe(e));
      return;
    }
    let o = [...s.args, "-m", "paperforge", "--vault", i, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      o.push("--last-operation-exit-code", String(t)),
      (0, ne.execFile)(s.path, o, { cwd: i, timeout: 15e3 }, (f, g, h) => {
        if ((this._probing.delete(e), f)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, f.message),
            this._updateCapabilityEnvelope(e, Pe(e)));
          return;
        }
        try {
          let b = JSON.parse(g);
          ot(b, e)
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
    (qt(r, t) && this._lastKnownState.set(e, Kt(t)),
      (this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        new R.Notice(a("cc_notice_refreshed"), 3e3),
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
    let s = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      o = a(s);
    return o === s ? null : o.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      i = this._sevClass(n.severity),
      s = Te._REAL_PROBE.has(t),
      o = Te._NAVIGABLE.has(t),
      l = e.createEl("div", {
        cls: "pf-cc-card pf-open-module-btn",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${a("cc_module_" + t)} \u2014 ${a(this._ccBadgeKey(n, t))}`,
        },
      }),
      p = l.createEl("div", { cls: "pf-cc-card-header" }),
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
        w = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: a("cc_module_" + t),
          attr: { "data-module": t, "aria-label": x },
        });
      (w.addEventListener("click", () => this._handleCardNavigation(t)),
        w.addEventListener("keydown", (S) => {
          (S.key === "Enter" || S.key === " ") &&
            (S.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: a("cc_module_" + t) });
    p.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${i}`,
      text: a(this._ccBadgeKey(n, t)),
    });
    let _;
    if (!s)
      _ = a("cc_reason_placeholder").replace("{module}", a("cc_module_" + t));
    else {
      let x = this._localizeReason(n.reason.code, t);
      _ = x != null ? x : n.reason.text;
    }
    if (
      (l.createEl("div", { cls: "pf-cc-card-reason", text: _ }),
      n.activity_state === "running" && n.activity_label)
    ) {
      let x = l.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (x.createEl("span", { text: n.activity_label }),
        n.activity_progress && n.activity_progress.total > 0)
      ) {
        let w = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          P = x
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
        P.style.width = w + "%";
      }
    }
    let f = l.createEl("div", { cls: "pf-cc-card-footer" });
    if (s && n.action.primary && !Bt(n)) {
      let x = Mt(n),
        S =
          x.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      f.createEl("button", {
        cls: S,
        text: x.label,
        attr: { "aria-label": x.label },
      }).addEventListener("click", () => {
        x.kind === "setup"
          ? new Ee(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._dispatchModuleAction(t, n);
      });
    }
    let g = l.createEl("details", { cls: "pf-cc-card-diagnostic" });
    g.createEl("summary", { text: a("cc_diagnostic_toggle") });
    let h = g.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      b = a("cc_state_" + n.capability_state) || n.capability_state,
      E = a("cc_severity_" + n.severity) || n.severity,
      m = a("cc_activity_" + n.activity_state) || n.activity_state,
      v;
    try {
      v = new Date(n.updated_at).toLocaleString();
    } catch (x) {
      v = n.updated_at;
    }
    (h.createEl("div", { text: `${a("cc_diag_module")}: ${n.module}` }),
      h.createEl("div", { text: `${a("cc_diag_state")}: ${b}` }),
      h.createEl("div", { text: `${a("cc_diag_severity")}: ${E}` }),
      h.createEl("div", { text: `${a("cc_diag_activity")}: ${m}` }));
    let k = h.createEl("div");
    k.appendText(a("cc_diag_reason") + ": " + _ + " ");
    let y = k.createEl("code", { text: n.reason.code });
    (h.createEl("div", {
      text: `${a("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      h.createEl("div", { text: `${a("cc_diag_updated")}: ${v}` }));
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
    var S, P, F, T;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = (S = this._capabilityState) != null ? S : {};
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
      }));
    let n = (P = r.installation) != null ? P : se("installation"),
      i = (F = r.library) != null ? F : se("library"),
      s = n.user_state === "ready",
      o = i.user_state === "ready",
      l = s && o,
      p = [n, i].some((A) => A.user_state === "checking"),
      u = Object.values(r).filter(
        (A) =>
          A.user_state &&
          A.user_state !== "ready" &&
          A.user_state !== "not_enabled"
      ).length,
      _ = t.createEl("div", { cls: "pf-cc-summary" }),
      f = l ? "ready" : p ? "checking" : "attention",
      g = l
        ? a("cc_badge_ready") || "Ready"
        : p
          ? a("cc_badge_checking") || "Checking"
          : a("cc_badge_attention") || "Needs attention";
    _.createEl("span", {
      cls: `pf-cc-summary-badge pf-cc-summary-badge--${f}`,
      text: g,
    });
    let h = _.createDiv({ cls: "pf-cc-summary-copy" }),
      b = l
        ? a("cc_summary_ready")
        : p
          ? a("cc_summary_checking")
          : this.plugin.settings._setup_complete === !1
            ? a("cc_summary_incomplete")
            : a("cc_summary_attention"),
      E = l
        ? a("cc_summary_ready_body")
        : p
          ? a("cc_summary_checking_body")
          : this.plugin.settings._setup_complete === !1
            ? a("cc_summary_incomplete_body")
            : a("cc_summary_attention_body");
    (h.createEl("strong", { text: b }),
      h.createEl("span", { cls: "caption", text: E }));
    let m = _.createDiv({ cls: "pf-cc-summary-meta" }),
      v = m.createEl("span");
    (v.createEl("strong", { text: String(u) }),
      v.appendText(" " + (a("cc_needs_attention") || "item needs attention")));
    let k = Object.values(r)
      .map((A) => A.updated_at)
      .filter(Boolean)
      .sort()
      .pop();
    (m.createEl("span", {
      text: k
        ? (a("cc_last_checked") || "Checked just now: ") +
          new Date(k).toLocaleString()
        : a("cc_checked_pending") || "Not checked yet",
    }),
      m
        .createEl("button", {
          cls: "pf-cc-summary-refresh",
          text: a("cc_refresh_btn") || "Refresh status",
        })
        .addEventListener("click", () => this._refreshAllModules()));
    let x = t.createDiv({ cls: "pf-cc-section-head" });
    (x.createEl("div", {
      cls: "pf-cc-eyebrow",
      text: a("cc_modules_label") || "modules",
    }),
      x.createEl("h2", { text: a("cc_modules_title") || "Five capabilities" }),
      x.createEl("span", {
        cls: "caption",
        text:
          a("cc_modules_caption") ||
          "Optional modules do not affect core readiness.",
      }));
    let w = t.createDiv({ cls: "pf-cc-module-list" });
    for (let [A, O] of this._getOverviewModules().entries()) {
      let L =
        O.id === "agent"
          ? this._getAgentPlaceholderEnvelope()
          : (T = r[O.id]) != null
            ? T
            : se(O.id);
      this._renderOverviewCard(w, O.id, O.label, L, A + 1);
    }
  }
  _getAgentPlaceholderEnvelope() {
    return {
      schema_version: 2,
      module: "agent",
      capability_state: "unknown",
      activity_state: "idle",
      activity_label: null,
      activity_progress: null,
      severity: "unknown",
      reason: {
        code: "agent.not_implemented",
        text: "Agent Integration will be available in a future update.",
      },
      action: { primary: null },
      notices: [],
      user_state: "not_enabled",
      capability_kind: "optional",
      maintenance_eligible: !1,
      user_visible_failure: !1,
      user_impact: null,
      updated_at: new Date(0).toISOString(),
      ttl_seconds: 0,
    };
  }
  _renderOverviewCard(e, t, r, n, i) {
    var l, p;
    let s = e.createEl("div", {
      cls: "pf-cc-module-card pf-open-module-btn",
      attr: {
        "data-module": t,
        "aria-label": r + " \u2014 " + this._getUserStateLabel(n.user_state),
        role: "button",
        tabindex: "0",
      },
    });
    ((s.style.cursor = "pointer"),
      s.createEl("span", {
        cls: "pf-cc-num",
        text: String(i).padStart(2, "0"),
      }),
      s.createEl("span", { cls: "pf-cc-card-name", text: r }),
      Y(s, n.user_state, this._getUserStateLabel(n.user_state)),
      s.createEl("span", {
        cls: "pf-cc-card-sentence",
        text: this._getModuleConsequence(t, n),
      }));
    let o =
      n.user_state === "ready" &&
      (p = (l = n.action) == null ? void 0 : l.primary) != null &&
      p.scope_count
        ? (a("cc_metric_papers") || "Papers: ") + n.action.primary.scope_count
        : n.updated_at && n.updated_at !== new Date(0).toISOString()
          ? (a("cc_last_checked") || "") +
            new Date(n.updated_at).toLocaleString()
          : "";
    (s.createEl("span", { cls: "pf-cc-card-metric", text: o }),
      s.createEl("span", { cls: "pf-cc-card-arrow", text: "\u2192" }),
      s.addEventListener("click", () => this._handleCardNavigation(t)));
  }
  _getUserStateLabel(e) {
    return a("cc_badge_" + e);
  }
  _getModuleConsequence(e, t) {
    var p, u, _;
    let r =
        (p = t.user_state) != null
          ? p
          : t.capability_state === "ready"
            ? "ready"
            : "action_required",
      n = "cc_consequence_" + e + "_" + r,
      i = a(n);
    if (i && i !== n) return i;
    let s = this._localizeReason(
      (_ = (u = t.reason) == null ? void 0 : u.code) != null ? _ : "",
      this._getUserModuleName(e)
    );
    if (s) return s;
    let o = "cc_consequence_" + r,
      l = a(o);
    return l !== o ? l : a("cc_consequence_default");
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Ve) {
      let r = this._capabilityState[t];
      r && ct(r) && ((this._capabilityState[t] = lt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
  _refreshAllModules() {
    let e = ["installation", "library", "ocr", "memory"];
    for (let t of e) this._probeModule(t);
  }
  _buildAndCopyDiagnostic() {
    var i, s, o;
    let e =
        (s = (i = this.plugin.manifest) == null ? void 0 : i.version) != null
          ? s
          : "unknown",
      t = Ut(
        (o = this._capabilityState) != null ? o : {},
        this._lastKnownState
      ),
      n = zt({ pluginVersion: e, modules: t });
    $t(n, () => {
      new R.Notice(a("support_diagnostic_copied"), 3e3);
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
    r.forEach((s, o) => {
      n.createEl("span", {
        cls:
          "pf-setup-step" +
          (o + 1 === this._setupStage ? " pf-setup-step--active" : "") +
          (o + 1 < this._setupStage ? " pf-setup-step--done" : ""),
        text: String(o + 1) + ". " + s,
        attr: { "aria-current": o + 1 === this._setupStage ? "step" : "false" },
      });
    });
    let i = t.createDiv({ cls: "pf-setup-body" });
    this._setupStage === 1
      ? this._renderSetupStageFoundation(i)
      : this._setupStage === 2
        ? this._renderSetupStageLibrary(i)
        : this._setupStage === 3
          ? this._renderSetupStageOptionals(i)
          : this._renderSetupStageReview(i);
  }
  _renderSetupStageFoundation(e) {
    var n, i, s;
    let t =
      (i = (n = this._capabilityState) == null ? void 0 : n.installation) !=
      null
        ? i
        : se("installation");
    if (
      (e.createEl("h3", { text: a("setup_foundation_title") }),
      e.createEl("p", { text: a("setup_foundation_desc") }),
      Y(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? a("setup_ready")
            : this._getModuleConsequence("installation", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      (s = t.action) != null && s.primary && t.user_state !== "ready")
    ) {
      let o = "cc_action_" + t.action.primary.verb;
      z(e, {
        label: a(o) === o ? a("cc_action_setup") : a(o),
        onClick: () =>
          this._runAllowedDispatch(
            "installation",
            t.action.primary.verb,
            t.action.primary.command,
            t
          ),
      });
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    z(r, {
      label: a("setup_nav_continue"),
      disabled: t.user_state !== "ready",
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    });
  }
  _renderSetupStageLibrary(e) {
    var n, i, s;
    let t =
      (i = (n = this._capabilityState) == null ? void 0 : n.library) != null
        ? i
        : se("library");
    if (
      (e.createEl("h3", { text: a("setup_library_title") }),
      e.createEl("p", { text: a("setup_library_desc") }),
      Y(e, t.user_state, this._getUserStateLabel(t.user_state)),
      e.createEl("p", {
        text:
          t.user_state === "ready"
            ? a("setup_library_ready")
            : this._getModuleConsequence("library", t),
        cls: t.user_state === "ready" ? "pf-setup-ok" : "pf-setup-status",
      }),
      (s = t.action) != null && s.primary && t.user_state !== "ready")
    ) {
      let o = "cc_action_" + t.action.primary.verb;
      z(e, {
        label: a(o) === o ? a("cc_action_set_config") : a(o),
        onClick: () =>
          this._runAllowedDispatch(
            "library",
            t.action.primary.verb,
            t.action.primary.command,
            t
          ),
      });
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (z(r, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 1), this.display());
      },
    }),
      z(r, {
        label: a("setup_nav_continue"),
        disabled: t.user_state !== "ready",
        onClick: () => {
          ((this._setupStage = 3), this.display());
        },
      }));
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
      let i = e.createDiv({ cls: "pf-setup-optional" }),
        s = i.createEl("input", {
          attr: { type: "checkbox", id: "pf-setup-opt-" + n.id },
        });
      ((s.checked = this._setupOptionals[n.id]),
        s.addEventListener("change", () => {
          this._setupOptionals[n.id] = s.checked;
        }));
      let o = i.createDiv({ cls: "pf-setup-optional-copy" });
      (o.createEl("label", {
        attr: { for: "pf-setup-opt-" + n.id },
        text: n.label,
        cls: "pf-setup-optional-label",
      }),
        o.createEl("div", { text: n.desc, cls: "pf-setup-optional-desc" }));
    }
    let r = e.createDiv({ cls: "pf-setup-nav" });
    (z(r, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 2), this.display());
      },
    }),
      z(r, {
        label: a("setup_nav_continue"),
        onClick: () => {
          ((this._setupStage = 4), this.display());
        },
      }));
  }
  _renderSetupStageReview(e) {
    var s, o, l, p;
    e.createEl("h3", { text: a("setup_review_title") });
    let t =
        ((o = (s = this._capabilityState) == null ? void 0 : s.installation) ==
        null
          ? void 0
          : o.user_state) === "ready",
      r =
        ((p = (l = this._capabilityState) == null ? void 0 : l.library) == null
          ? void 0
          : p.user_state) === "ready";
    (e.createEl("p", {
      text: t ? a("setup_ready") : a("cc_consequence_setup_required"),
      cls: t ? "pf-setup-ok" : "pf-setup-warn",
    }),
      e.createEl("p", {
        text: r ? a("setup_library_ready") : a("cc_consequence_setup_required"),
        cls: r ? "pf-setup-ok" : "pf-setup-warn",
      }));
    let n = Object.entries(this._setupOptionals)
      .filter(([, u]) => u)
      .map(([u]) => this._getUserModuleName(u));
    e.createEl("p", {
      text:
        n.length > 0
          ? a("setup_review_selected") + n.join(", ")
          : a("setup_no_optionals"),
    });
    let i = e.createDiv({ cls: "pf-setup-nav" });
    (z(i, {
      label: a("setup_nav_back"),
      onClick: () => {
        ((this._setupStage = 3), this.display());
      },
    }),
      z(i, {
        label: a("setup_nav_complete"),
        disabled: !t || !r,
        onClick: () => this._completeSetup(),
      }),
      (!t || !r) &&
        e.createEl("p", {
          text: a("setup_incomplete_warn"),
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
var rt = Te;
var D = require("obsidian"),
  xe = N(require("fs")),
  nt = N(require("path")),
  ge = require("child_process");
var qe = N(require("path"));
function fr(d) {
  if (!d) return null;
  let c = qe.dirname(d);
  for (;;) {
    let e = qe.basename(c);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = qe.dirname(c);
    if (r === c) break;
    c = r;
  }
  return null;
}
var $ = N(require("fs")),
  ye = N(require("path"));
function Ue(d) {
  return X(d).ocrDir;
}
function Zr(d, c) {
  let e = ye.join(Ue(d), c, "versions", "manifest.json");
  try {
    if (!$.existsSync(e)) return null;
    let t = $.readFileSync(e, "utf-8"),
      r = JSON.parse(t);
    if (r && typeof r == "object" && "versions" in r && "current" in r) {
      let n = r,
        i = n.versions,
        s = n.current;
      if (Array.isArray(i) && s && typeof s == "object" && "label" in s)
        return r;
    }
    return null;
  } catch (t) {
    return null;
  }
}
function Gr(d) {
  let c = Ue(d);
  try {
    return $.existsSync(c)
      ? $.readdirSync(c, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function wt(d) {
  let c = Gr(d),
    e = [];
  for (let t of c) {
    let r = Zr(d, t);
    if (!r) continue;
    let n = r.versions.map((s) => s.label),
      i = 0;
    for (let s of n) {
      let o = ye.join(Ue(d), t, "versions", s, "fulltext.md");
      try {
        $.existsSync(o) && (i += $.statSync(o).size);
      } catch (l) {}
    }
    e.push({
      key: t,
      title: t.replace(/_/g, " "),
      versions: r.versions,
      currentLabel: r.current.label,
      totalSize: i,
    });
  }
  return (e.sort((t, r) => t.title.localeCompare(r.title)), e);
}
function gr(d, c, e) {
  let t = Ue(d),
    r = ye.join(t, c, "versions", e, "fulltext.md"),
    n = ye.join(t, c, "render"),
    i = ye.join(n, "fulltext.md");
  try {
    return $.existsSync(r)
      ? ($.existsSync(n) || $.mkdirSync(n, { recursive: !0 }),
        $.copyFileSync(r, i),
        !0)
      : !1;
  } catch (s) {
    return !1;
  }
}
function mr(d, c, e, t) {
  var f;
  let r = Ue(d),
    n = ye.join(r, c, "versions", e, "fulltext.md"),
    i = ye.join(r, c, "versions", t, "fulltext.md"),
    s = "",
    o = "";
  try {
    $.existsSync(n) && (s = $.readFileSync(n, "utf-8"));
  } catch (g) {}
  try {
    $.existsSync(i) && (o = $.readFileSync(i, "utf-8"));
  } catch (g) {}
  let l = hr(s),
    p = hr(o),
    u = Math.max(l.length, p.length),
    _ = [];
  for (let g = 0; g < u; g++) {
    let h = g < l.length ? l[g] : "",
      b = g < p.length ? p[g] : "",
      E =
        (f = (h || b).split(`
`)[0]) != null
          ? f
          : "",
      m = E.startsWith("## ") ? E.replace(/^##\s+/, "") : "",
      v = "unchanged";
    (!h && b
      ? (v = "added")
      : h && !b
        ? (v = "removed")
        : h !== b && (v = "changed"),
      v !== "unchanged" &&
        _.push({
          paragraphIndex: g,
          heading: m,
          type: v,
          oldText: h || void 0,
          newText: b || void 0,
        }));
  }
  return _;
}
function hr(d) {
  let c = d.split(`
`),
    e = [],
    t = [];
  for (let r of c)
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
var Oe = class extends D.ItemView {
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
    var i, s, o;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (s =
          (i = e == null ? void 0 : e.settings) == null
            ? void 0
            : i.python_path) == null
          ? void 0
          : s.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    let r =
      (o = e == null ? void 0 : e.getManagedRuntime) == null
        ? void 0
        : o.call(e);
    if (!r) return null;
    let n = ce(r.current());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  getViewType() {
    return be;
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
          let i =
            (r = (t = e.target) == null ? void 0 : t.tagName) == null
              ? void 0
              : r.toLowerCase();
          i !== "input" &&
            i !== "textarea" &&
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
    let { path: i, args: s = [] } = n;
    Promise.resolve({ status: "ok", pyVersion: "?" }).then((l) => {
      if (l.status === "not-installed") return;
      let p = l.pyVersion || "";
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
    let { path: i, args: s = [] } = n;
    (0, ge.execFile)(
      i,
      [...s, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (o, l) => {
        if (!o)
          try {
            let p = JSON.parse(l);
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
      i = e.ocr_version_state || {},
      s = (r.done || 0) + (r.pending || 0) + (r.failed || 0);
    return {
      total_papers: t.papers || 0,
      formal_notes: t.papers || 0,
      exports: 0,
      bases: 0,
      ocr: {
        total: s,
        pending: r.pending || 0,
        processing: 0,
        done: r.done || 0,
        failed: r.failed || 0,
      },
      path_errors: (n.broken || 0) + (n.missing || 0),
      ocr_version_state: {
        total_papers: i.total_papers || 0,
        derived_stale_count: i.derived_stale_count || 0,
        raw_upgradable_count: i.raw_upgradable_count || 0,
      },
    };
  }
  _fallbackFetchStats(e, t, r) {
    var s, o;
    let n =
        ((s = r == null ? void 0 : r.settings) == null
          ? void 0
          : s.system_dir) || "System",
      i = nt.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let l = xe.readFileSync(i, "utf-8"),
        p = JSON.parse(l),
        u = p.items || [],
        _ = {},
        f = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        g = 0,
        h = 0,
        b = 0,
        E = 0,
        m = 0,
        v = 0;
      for (let k of u) {
        k.note_path && v++;
        let y = k.lifecycle || "pdf_ready";
        _[y] = (_[y] || 0) + 1;
        let x = k.health || {};
        for (let S of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (x[S] || "healthy") === "healthy" ? f[S].healthy++ : f[S].unhealthy++;
        let w = k.ocr_status || "";
        (g++,
          w === "done"
            ? h++
            : w === "pending"
              ? b++
              : w === "processing" || w === "queued" || w === "running"
                ? E++
                : m++);
      }
      ((this._cachedStats = {
        version:
          p.paperforge_version ||
          ((o = this._cachedStats) == null ? void 0 : o.version) ||
          "\u2014",
        total_papers: u.length,
        formal_notes: v,
        exports: 0,
        bases: 0,
        ocr: { total: g, pending: b, processing: E, done: h, failed: m },
        path_errors: 0,
        lifecycle_level_counts: _,
        health_aggregate: f,
      }),
        this._metricsEl.empty(),
        this._renderStats(this._cachedStats),
        this._renderOcr(this._cachedStats));
    } catch (l) {
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
      let { path: u, args: _ = [] } = p;
      (0, ge.execFile)(
        u,
        [..._, "-m", "paperforge", "status", "--json"],
        { cwd: t, timeout: 3e4 },
        (f, g) => {
          if (f) {
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
    var i;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((i = t == null ? void 0 : t.settings) == null
          ? void 0
          : i.system_dir) || "System",
      n = nt.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let s = xe.readFileSync(n, "utf-8");
      return JSON.parse(s);
    } catch (s) {
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
    return Ot(this.app, t);
  }
  _patchCachedEntry(e, t) {
    if (!e || !this._cachedItems) return;
    let r = this._cachedItems.findIndex((n) => n.zotero_key === e);
    r !== -1 && (this._cachedItems[r] = it(this._cachedItems[r], t));
  }
  _filterByDomain(e) {
    return e ? this._getCachedIndex().filter((t) => t.domain === e) : [];
  }
  _renderStats(e) {
    var s;
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
      let l = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (l.style.setProperty("--metric-color", o.color),
        l.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((s = o.value) == null ? void 0 : s.toString()) || "\u2014",
        }),
        l.createEl("div", { cls: "paperforge-metric-label", text: o.label }),
        o.barMax > 0 && this._buildMetricBar(l, o.value, o.barMax));
    }
    let i = e.ocr_version_state || {};
    if (
      i.total_papers > 0 &&
      (i.derived_stale_count > 0 || i.raw_upgradable_count > 0)
    ) {
      let o = [];
      (i.derived_stale_count > 0 && o.push(`${i.derived_stale_count} stale`),
        i.raw_upgradable_count > 0 &&
          o.push(`${i.raw_upgradable_count} upgradable`));
      let l = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (l.style.setProperty("--metric-color", "var(--color-yellow)"),
        l.createEl("div", {
          cls: "paperforge-metric-value",
          text: o.join(", "),
        }),
        l.createEl("div", {
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
      i = t.pending || 0,
      s = t.processing || 0,
      o = t.failed || 0;
    if (
      (this._ocrBadge &&
        (this._ocrBadge.removeClass("active", "idle"),
        s > 0
          ? (this._ocrBadge.addClass("active"),
            this._ocrBadge.setText("Processing"))
          : i > 0
            ? (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Pending"))
            : (this._ocrBadge.addClass("idle"),
              this._ocrBadge.setText("Idle"))),
      this._ocrTrack)
    ) {
      (this._ocrTrack.empty(),
        s > 0
          ? this._ocrTrack.addClass("paperforge-processing")
          : this._ocrTrack.removeClass("paperforge-processing"));
      let l = [
        { cls: "pending", count: i },
        { cls: "active", count: s },
        { cls: "done", count: n },
        { cls: "failed", count: o },
      ];
      for (let p of l)
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
      let l = [
        { cls: "pending", value: i, label: "Pending" },
        { cls: "active", value: s, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: o, label: "Failed" },
      ];
      for (let p of l) {
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
      i = e.createEl("div", { cls: "paperforge-lifecycle-stepper" }),
      s = !1;
    for (let o of n) {
      let l = i.createEl("div", { cls: "step" });
      (l.createEl("div", { cls: "step-indicator" }),
        l.createEl("div", { cls: "step-label", text: o.label }),
        o.key === r
          ? (l.addClass("current"), (s = !0))
          : s
            ? l.addClass("pending")
            : l.addClass("completed"));
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
    for (let i of r) {
      let s = t[i.key] || "healthy",
        o = n.createEl("div", { cls: "paperforge-health-cell" }),
        l,
        p,
        u;
      (s === "healthy" || s === "ok"
        ? ((l = i.iconOk), (p = "ok"), (u = `${i.label}: OK`))
        : s === "warn" || s === "warning" || s === "degraded"
          ? ((l = i.iconWarn),
            (p = "warn"),
            (u = `${i.label}: Needs Attention`))
          : ((l = i.iconFail), (p = "fail"), (u = `${i.label}: Failed`)),
        o.addClass(p),
        o.setAttribute("title", u),
        o.createEl("div", { cls: "paperforge-health-cell-icon", text: l }),
        o.createEl("div", {
          cls: "paperforge-health-cell-label",
          text: i.label,
        }));
    }
  }
  _renderMaturityGauge(e, t, r) {
    if (t == null || t === void 0) {
      this._renderSkeleton(e);
      return;
    }
    let n = e.createEl("div", { cls: "paperforge-maturity-gauge" }),
      i = n.createEl("div", { cls: "gauge-track" }),
      s = 4,
      o = Math.max(1, Math.min(s, Math.round(t)));
    for (let l = 1; l <= s; l++) {
      let p = i.createEl("div", { cls: "gauge-segment" });
      l <= o && (p.addClass("filled"), p.addClass(`level-${l}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${o} / ${s}` }),
      o < s && r)
    ) {
      let l = typeof r == "string" ? [r] : r;
      if (l.length > 0) {
        let p = n.createEl("ul", { cls: "gauge-blockers" });
        for (let u of l) p.createEl("li", { text: u });
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
      i = Math.max(1, ...r.map((s) => t[s.key] || 0));
    for (let s of r) {
      let o = t[s.key] || 0,
        l = (o / i) * 100,
        p = n.createEl("div", { cls: "bar-row" });
      (p.createEl("div", { cls: "bar-label", text: s.label }),
        p
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${s.cls}`,
            attr: { style: `width:${l.toFixed(1)}%` },
          }),
        p.createEl("div", { cls: "bar-count", text: o.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return fr(e);
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
      let i = this.app.metadataCache.getFileCache(e),
        s = i && i.frontmatter && i.frontmatter.zotero_key;
      if (s) return { mode: "paper", filePath: r, key: s, domain: null };
    }
    if (t === "pdf") {
      let i = this._getCachedIndex();
      for (let s of i) {
        let o = (s.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((o ? o[1] : s.pdf_path) === r)
          return {
            mode: "paper",
            filePath: r,
            key: s.zotero_key,
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
    var oe, ke, de, W, St, Pt, Ct;
    if (!this._contentEl) return;
    let e = this._contentEl.createEl("div", { cls: "paperforge-global-view" });
    ((this._driftBannerEl = e.createEl("div", {
      cls: "paperforge-drift-banner",
    })),
      (this._driftBannerEl.style.display = "none"));
    let t = this._getCachedIndex(),
      r = t.length,
      n = 0,
      i = 0,
      s = 0;
    for (let B of t)
      (B.has_pdf && n++,
        B.ocr_status === "done" && i++,
        B.deep_reading_status === "done" && s++);
    let o = e.createEl("div", { cls: "paperforge-library-snapshot" });
    o.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let l = o.createEl("div", { cls: "paperforge-snapshot-pills" }),
      p = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: i, label: "OCR done" },
        { value: s, label: "deep-read done" },
      ];
    for (let B of p) {
      let j = l.createEl("div", { cls: "paperforge-snapshot-pill" });
      (j.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(B.value),
      }),
        j.createEl("span", {
          cls: "paperforge-snapshot-label",
          text: " " + B.label,
        }));
    }
    let u = e.createEl("div", { cls: "paperforge-system-status" });
    u.createEl("div", {
      cls: "paperforge-section-label",
      text: "System Status",
    });
    let _ = u.createEl("div", { cls: "paperforge-status-grid" }),
      f = this.app.plugins.plugins.paperforge,
      g =
        ((oe = f == null ? void 0 : f.manifest) == null
          ? void 0
          : oe.version) || "?",
      h = this._paperforgeVersion;
    if (!h) {
      let B = this._resolvePython();
      if (B) {
        let { path: j, args: ue = [] } = B;
        try {
          let le = this.app.vault.adapter.basePath,
            ee = (0, ge.execFileSync)(
              j,
              [...ue, "-c", "import paperforge; print(paperforge.__version__)"],
              { cwd: le, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
            ).trim();
          ee &&
            ((h = ee.startsWith("v") ? ee : "v" + ee),
            (this._paperforgeVersion = h));
        } catch (le) {}
      }
    }
    h = h || "\u2014";
    let b = h === "v" + g;
    this._renderSystemStatusRow(
      _,
      "Runtime",
      b ? "healthy" : "mismatch",
      b ? "v" + g : "plugin v" + g + " \u2260 CLI " + h
    );
    let E = this._loadIndex(),
      m = E && E.items && E.items.length > 0;
    this._renderSystemStatusRow(
      _,
      "Index",
      m ? "healthy" : "missing",
      m ? E.items.length + " entries" : "formal-library.json not found"
    );
    let v =
        ((ke = f == null ? void 0 : f.settings) == null
          ? void 0
          : ke.system_dir) || "System",
      k = this.app.vault.adapter.basePath,
      y = !1,
      x = "No exports found";
    try {
      let B = nt.join(k, v, "PaperForge", "exports");
      if (xe.existsSync(B)) {
        let j = xe.readdirSync(B).filter((ue) => ue.endsWith(".json"));
        ((y = j.length > 0),
          (x = y ? j.length + " export(s)" : "No JSON exports"));
      }
    } catch (B) {}
    this._renderSystemStatusRow(
      _,
      "Zotero Export",
      y ? "healthy" : "missing",
      x
    );
    let w =
        (W = (de = this.app.plugins) == null ? void 0 : de.plugins) == null
          ? void 0
          : W.paperforge,
      S = !!(
        (St = w == null ? void 0 : w.settings) != null &&
        St._paddleocr_configured
      );
    this._renderSystemStatusRow(
      _,
      "OCR Token",
      S ? "configured" : "missing",
      S ? "Configured" : "Not set"
    );
    let P = !1,
      F = "",
      T = this.app.vault.adapter.basePath,
      A = ze(T);
    ((P = tr(T)),
      (F =
        (A && ((Pt = A.summary) == null ? void 0 : Pt.reason)) ||
        (A && ((Ct = A.summary) == null ? void 0 : Ct.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        _,
        "Memory Layer",
        P ? "healthy" : "fail",
        F
      ));
    let O = !b && h !== "\u2014";
    if (O || !m || !y || !S) {
      let B = e.createEl("div", { cls: "paperforge-issue-summary" });
      B.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let j = B.createEl("div", { cls: "paperforge-issue-list" });
      (O &&
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
      let ue = B.createEl("div", { cls: "paperforge-issue-actions" }),
        le = ue.createEl("button", { cls: "paperforge-contextual-btn" });
      (le.createEl("span", { text: "Run Doctor" }),
        le.addEventListener("click", () => {
          let Ie = te.find((st) => st.id === "paperforge-doctor");
          Ie && this._runAction(Ie, le);
        }));
      let ee = ue.createEl("button", { cls: "paperforge-contextual-btn" });
      (ee.createEl("span", { text: "Repair Issues" }),
        ee.addEventListener("click", () => {
          let Ie = te.find((st) => st.id === "paperforge-repair");
          Ie && this._runAction(Ie, ee);
        }));
    }
    let C = e.createEl("div", { cls: "paperforge-global-actions" });
    C.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let V = C.createEl("div", { cls: "paperforge-global-actions-row" }),
      Q = V.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (Q.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      Q.createEl("span", { text: "Open Literature Hub" }),
      Q.addEventListener("click", () => {
        var ue;
        let B =
            ((ue = f == null ? void 0 : f.settings) == null
              ? void 0
              : ue.base_dir) || "Bases",
          j = this.app.vault.getAbstractFileByPath(B);
        if (j) {
          let le = null;
          if (
            (j.children &&
              (le = j.children.find((ee) => ee.extension === "base")),
            le)
          ) {
            let ee = this.app.workspace.getLeaf(!1);
            ee && ee.openFile(le);
          } else new D.Notice("[!!] No .base file found in " + B, 6e3);
        } else new D.Notice("[!!] Base directory not found: " + B, 6e3);
      }));
    let J = V.createEl("button", { cls: "paperforge-contextual-btn" });
    (J.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      J.createEl("span", { text: "Sync Library" }),
      J.addEventListener("click", () => {
        let B = te.find((j) => j.id === "paperforge-sync");
        B && this._runAction(B, J);
      }));
    let M = V.createEl("button", { cls: "paperforge-contextual-btn" });
    (M.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      M.createEl("span", { text: "Run OCR" }),
      M.addEventListener("click", () => {
        let B = te.find((j) => j.id === "paperforge-ocr");
        B && this._runAction(B, M);
      }));
    let ae = V.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (ae.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      ae.createEl("span", { text: "Redo OCR" }),
      ae.addEventListener("click", () => {
        let B = te.find((j) => j.id === "paperforge-ocr-redo");
        B && this._runAction(B, ae);
      }));
  }
  _renderSystemStatusRow(e, t, r, n) {
    let i = e.createEl("div", { cls: "paperforge-status-row" });
    (i
      .createEl("span", { cls: "paperforge-status-dot" })
      .addClass(r === "healthy" || r === "configured" ? "ok" : "fail"),
      i.createEl("span", { cls: "paperforge-status-label", text: t }),
      i.createEl("span", { cls: "paperforge-status-detail", text: n || "" }));
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
        new D.Notice("Title copied"));
    });
    let s = n.createEl("div", { cls: "paperforge-paper-meta" });
    (e.authors &&
      e.authors.length > 0 &&
      s.createEl("span", {
        cls: "paperforge-paper-authors",
        text: e.authors.join(", "),
      }),
      e.year &&
        s.createEl("span", {
          cls: "paperforge-paper-year",
          text: String(e.year),
        }));
    let o = r.createEl("div", { cls: "paperforge-status-strip" }),
      l = o.createEl("div", { cls: "paperforge-status-strip-left" }),
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
    for (let f of u) {
      let g = l.createEl("span", { cls: "paperforge-status-pill" }),
        h = "pending";
      (f.ok ? (h = "ok") : f.fail ? (h = "fail") : f.pending && (h = "pending"),
        g.addClass(h));
      let b = f.ok ? "\u2713" : f.fail ? "\u2717" : "\u25CB";
      (g.createEl("span", { cls: "paperforge-status-pill-icon", text: b }),
        g.createEl("span", { text: " " + f.label }));
    }
    if (e.pdf_path) {
      let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (f.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        f.createEl("span", { text: "\u6253\u5F00 PDF" }),
        f.addEventListener("click", () => {
          let g = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            h = g ? g[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(h)
            ? this.app.workspace.openLinkText(h, "")
            : new D.Notice("[!!] PDF not found: " + h, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let f = p.createEl("button", { cls: "paperforge-contextual-btn" });
      (f.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        f.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        f.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let _ = p.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (_.createEl("span", { text: a("version_panel_title") }),
      _.addEventListener("click", () => {
        this._switchToVersionMode(t);
      }),
      this._renderPaperOverviewCard(r, e),
      e.next_step === "ready" && e.deep_reading_status === "done")
    ) {
      let f = r.createEl("div", { cls: "paperforge-complete-row" });
      (f.createEl("span", { text: "\u2713" }),
        f.createEl("span", {
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
    let i = r.createEl("div", { cls: "paperforge-paper-overview-body" }),
      s = i.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let o = this.app.vault.getAbstractFileByPath(t.note_path);
      o
        ? this.app.vault
            .read(o)
            .then((l) => {
              let p = this._extractOverviewFromNote(l);
              if (p) {
                let u = p.length > 200 ? p.slice(0, 200) + "..." : p;
                if ((s.setText(u), p.length > 200)) {
                  let _ = i.createEl("div", {
                      cls: "paperforge-expand-container",
                    }),
                    f = _.createEl("button", {
                      cls: "paperforge-expand-icon",
                      title: "\u5C55\u5F00/\u6536\u8D77",
                    });
                  f.innerHTML =
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
                  let g = !1;
                  _.addEventListener("click", () => {
                    (s.setText(g ? u : p),
                      (f.innerHTML = g
                        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>'
                        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>'),
                      (g = !g));
                  });
                }
              } else
                s.setText(
                  "\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8\u3002\u8FD0\u884C /pf-deep \u5F00\u59CB\u7CBE\u8BFB\u3002"
                );
            })
            .catch(() => {
              s.setText("\u65E0\u6CD5\u8BFB\u53D6\u7B14\u8BB0\u5185\u5BB9");
            })
        : s.setText("\u7B14\u8BB0\u6587\u4EF6\u4E0D\u5B58\u5728");
    } else s.setText("\u5C1A\u672A\u751F\u6210\u6587\u7AE0\u6982\u89C8");
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
      let l = r.indexOf(o);
      if (l !== -1) {
        let p = r.slice(l + o.length),
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          _ = p.length;
        for (let h of u) {
          let b = p.indexOf(h);
          b !== -1 && b < _ && (_ = b);
        }
        let f = p.indexOf(`

`);
        f !== -1 && f < _ && (_ = f);
        let g = p.slice(0, _).trim();
        return (
          g.startsWith("**") && (g = g.slice(2)),
          g.endsWith("**") && (g = g.slice(0, -2)),
          g || null
        );
      }
    }
    let i = r.indexOf(`
`);
    if (i === -1) return null;
    let s = r
      .slice(i + 1)
      .split(
        `

`
      )[0]
      .trim();
    return !s || s.startsWith("###") || s.startsWith("##")
      ? null
      : s.length > 300
        ? s.slice(0, 300) + "..."
        : s;
  }
  _renderRecentDiscussionCard(e, t) {
    let r = e.createEl("div", { cls: "paperforge-discussion-card" });
    if (((r.style.display = "none"), !t.note_path)) return;
    let n = t.note_path.lastIndexOf("/"),
      s = (n !== -1 ? t.note_path.substring(0, n) : ".") + "/ai/discussion.md";
    this.app.vault.adapter
      .exists(s)
      .then((o) => {
        if (o) return this.app.vault.adapter.read(s);
      })
      .then(async (o) => {
        if (!o) return;
        let l = this._parseDiscussionMD(o);
        if (!l || l.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let _ of l) {
          let f = r.createEl("div", { cls: "paperforge-discussion-item" }),
            g = f.createEl("div", { cls: "paperforge-discussion-q" });
          (g.createEl("span", {
            cls: "paperforge-discussion-q-label",
            text: "\u63D0\u95EE\uFF1A",
          }),
            g.createEl("span", {
              cls: "paperforge-discussion-q-text",
              text: _.question,
            }));
          let h = f.createEl("div", { cls: "paperforge-discussion-a" }),
            b = !1;
          if (
            (_.answer &&
              _.answer.length > 500 &&
              ((b = !0), h.classList.add("paperforge-discussion-a-collapsed")),
            await D.MarkdownRenderer.render(
              this.app,
              _.answer || "",
              h,
              s,
              this
            ),
            b)
          ) {
            let E = !1;
            ((f.style.cursor = "pointer"),
              f.addEventListener("click", () => {
                ((E = !E),
                  h.classList.toggle("paperforge-discussion-a-collapsed", !E),
                  h.classList.toggle("paperforge-discussion-a-expanded", E));
              }));
          }
        }
        r.createEl("a", {
          cls: "paperforge-discussion-viewall",
          text: "\u67E5\u770B\u5168\u90E8\u8BA8\u8BBA \u2192",
        }).addEventListener("click", (_) => {
          (_.preventDefault(),
            this.app.vault.getAbstractFileByPath(s)
              ? this.app.workspace.openLinkText(s, "")
              : new D.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((o) => {
        console.error("PaperForge: discussion.md read error", s, o.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      i = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let s of i) {
      let o = s.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!o) continue;
      let l = s.substring(0, o.index).trim(),
        p = s.substring(o.index + 3 + 4).trim();
      n.push({ question: l, answer: p });
    }
    return n.slice(-3);
  }
  _renderPaperTechnicalDetails(e, t) {
    let r = this._currentPaperKey,
      n = e.createEl("div", { cls: "paperforge-technical-details" }),
      i = n.createEl("button", { cls: "paperforge-technical-details-toggle" }),
      s = n.createEl("div", { cls: "paperforge-technical-details-body" });
    ((s.style.display = "none"),
      this._techDetailsExpanded
        ? ((s.style.display = "block"),
          i.setText("\u6280\u672F\u8BE6\u60C5 \u25BE"))
        : i.setText("\u6280\u672F\u8BE6\u60C5 \u25B8"),
      i.addEventListener("click", () => {
        let f = s.style.display !== "none";
        ((s.style.display = f ? "none" : "block"),
          i.setText(
            f
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !f));
      }));
    let o = s.createEl("div", { cls: "paperforge-workflow-toggles" }),
      l = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let f of l) {
      let g = o.createEl("label", { cls: "paperforge-workflow-toggle" }),
        h = g.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((h.checked = t[f.key] === !0),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: f.label,
        }),
        g.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: f.hint,
        }),
        h.addEventListener("change", async () => {
          let b = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!b) {
            new D.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let E = h.checked;
          (await this.app.fileManager.processFrontMatter(b, (m) => {
            m[f.key] = E;
          }),
            this._patchCachedEntry(r, { [f.key]: E }),
            (this._currentPaperEntry = it(this._currentPaperEntry, {
              [f.key]: E,
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
      _ = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [f, g] of u) {
      let h = s.createEl("div", { cls: "paperforge-technical-row" });
      h.createEl("span", { cls: "paperforge-technical-label", text: f });
      let b = h.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(g),
      });
      _.has(f) &&
        g &&
        g !== "\u2014" &&
        (b.addClass("pf-copy"),
        b.addEventListener("click", () => {
          (navigator.clipboard.writeText(g), new D.Notice(f + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var l, p;
    let n = t.next_step || "ready",
      i = {
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
      s = i[n] || i.ready,
      o = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && o.addClass("ready"),
      o.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      o.createEl("div", { cls: "paperforge-next-step-text", text: s.text }),
      s.cmd && s.cmd !== "ready")
    ) {
      let u = o.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: s.icon + "  " + s.label }),
        u.addEventListener("click", () => {
          let _ = te.find((f) => f.cmd === s.cmd);
          _ && this._runAction(_, u);
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
                new D.Notice(b + " copied"));
            })
            .catch(() => {
              new D.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let _ =
          ((p =
            (l = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : l.settings) == null
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
          }[_] || _;
      o.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        a("run_in_agent").replace("{0}", g)
      );
    } else
      n === "ready" &&
        o
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + s.label });
  }
  _openFulltext(e) {
    if (!e) {
      new D.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new D.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      i = 0,
      s = 0,
      o = 0,
      l = 0,
      p = 0,
      u = 0,
      _ = 0;
    for (let y of t) {
      (y.has_pdf && i++,
        y.ocr_status === "done" && s++,
        y.ocr_status === "done" && y.analyze === !0 && o++,
        y.deep_reading_status === "done" && l++);
      let x = y.ocr_status || "";
      x === "pending" || x === "queued"
        ? p++
        : x === "processing"
          ? u++
          : (x === "failed" ||
              x === "blocked" ||
              x === "done_incomplete" ||
              x === "nopdf") &&
            _++;
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
        { value: i, label: "PDF Ready" },
        { value: s, label: "OCR Done" },
        { value: l, label: "Deep Read" },
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
    if (p + u + s + _ > 0) {
      let y = r.createEl("div", { cls: "paperforge-ocr-section" }),
        x = y.createEl("div", { cls: "paperforge-collection-ocr-header" });
      x.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let w = x.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (w.addClass("active"), w.setText("Processing"))
        : p > 0
          ? w.setText("Pending")
          : (w.addClass("idle"), w.setText("Idle"));
      let S = y.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && S.addClass("paperforge-processing");
      let P = p + u + s + _,
        F = [
          { cls: "pending", count: p },
          { cls: "active", count: u },
          { cls: "done", count: s },
          { cls: "failed", count: _ },
        ];
      for (let O of F)
        if (O.count > 0) {
          let L = ((O.count / P) * 100).toFixed(1);
          S.createEl("div", {
            cls: `paperforge-progress-seg ${O.cls}`,
            attr: { style: `width:${L}%` },
          });
        }
      let T = y.createEl("div", { cls: "paperforge-ocr-counts" }),
        A = [
          { cls: "pending", value: p, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: s, label: "Done" },
          { cls: "failed", value: _, label: "Attention" },
        ];
      for (let O of A) {
        let L = T.createEl("div", { cls: "paperforge-ocr-count" });
        (L.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: O.value.toString(),
        }),
          L.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: O.label,
          }));
      }
    }
    let E = r.createEl("div", { cls: "paperforge-collection-actions" }),
      m = E.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (m.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      m.createEl("span", { text: "Run OCR" }),
      m.addEventListener("click", () => {
        let y = te.find((x) => x.id === "paperforge-ocr");
        y && this._runAction(y, m);
      }));
    let v = E.createEl("button", { cls: "paperforge-contextual-btn" });
    (v.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      v.createEl("span", { text: "Sync Library" }),
      v.addEventListener("click", () => {
        let y = te.find((x) => x.id === "paperforge-sync");
        y && this._runAction(y, v);
      }));
    let k = E.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (k.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      k.createEl("span", { text: "Redo OCR" }),
      k.addEventListener("click", () => {
        let y = te.find((x) => x.id === "paperforge-ocr-redo");
        y && this._runAction(y, k);
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
      new D.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = wt(n)),
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
      (this._versionPapers = wt(n));
    let i = e.createEl("div", { cls: "paperforge-version-left" }),
      s = e.createEl("div", { cls: "paperforge-version-right" }),
      o = i.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: a("version_filter_placeholder") },
      });
    o.value = this._versionFilter;
    let l = i.createEl("div", { cls: "paperforge-version-paper-list" }),
      p = () => {
        l.empty();
        let m = this._versionFilter.toLowerCase(),
          v = this._versionPapers
            ? this._versionPapers.filter(
                (y) =>
                  !m ||
                  y.key.toLowerCase().includes(m) ||
                  y.title.toLowerCase().includes(m)
              )
            : [];
        if (v.length === 0) {
          l.createEl("div", {
            cls: "paperforge-meta",
            text: a("version_no_backups"),
          });
          return;
        }
        let k = l.createEl("div", {
          cls: "paperforge-meta",
          text: a("version_papers_count").replace("{n}", String(v.length)),
        });
        for (let y of v) {
          let x = l.createEl("div", { cls: "paperforge-version-paper-item" }),
            w = x.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: y.title,
            }),
            S = x.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: y.versions.map((P) => P.label).join(" "),
            });
          x.addEventListener("click", () => {
            (l
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((P) => P.removeClass("selected")),
              x.addClass("selected"),
              _(y));
          });
        }
      };
    o.addEventListener("input", () => {
      ((this._versionFilter = o.value), p());
    });
    let u = s.createEl("div", { cls: "paperforge-version-timeline-area" }),
      _ = (m) => {
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
        let k = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let y of m.versions) {
          let x = y.label === m.currentLabel,
            w = k.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (x ? " paperforge-version-current" : ""),
            }),
            S = w.createEl("div", { cls: "paperforge-version-dot" }),
            P = w.createEl("div", { cls: "paperforge-version-content" }),
            F = P.createEl("div", { cls: "paperforge-version-label-row" });
          (F.createEl("span", {
            cls: "paperforge-version-label",
            text: y.label,
          }),
            x &&
              F.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: a("version_current"),
              }));
          let T = y.created_at ? y.created_at.slice(0, 10) : "";
          P.createEl("div", {
            cls: "paperforge-meta",
            text: T + " \u2014 " + y.source,
          });
          let A = y.fulltext_size
            ? y.fulltext_size > 1024
              ? (y.fulltext_size / 1024).toFixed(0) + "KB"
              : y.fulltext_size + "B"
            : "";
          A && P.createEl("div", { cls: "paperforge-meta", text: A });
          let O = P.createEl("div", { cls: "paperforge-version-actions" });
          (O.createEl("button", {
            cls: "pf-btn-primary",
            text: a("version_restore_btn"),
          }).addEventListener("click", () => {
            gr(n, m.key, y.label)
              ? new D.Notice(
                  a("version_restore_done").replace("{label}", y.label)
                )
              : new D.Notice("Restore failed", 6e3);
          }),
            m.versions.length > 1 &&
              !x &&
              O.createEl("button", {
                cls: "pf-btn-secondary",
                text: a("version_compare_btn"),
              }).addEventListener("click", () => {
                g(m, y.label, m.currentLabel);
              }));
        }
      },
      f = s.createEl("div", { cls: "paperforge-version-compare" });
    f.style.display = "none";
    let g = (m, v, k) => {
        let y = mr(n, m.key, v, k);
        ((f.style.display = "block"), f.empty());
        let x = f.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (x.createEl("span", {
            cls: "pf-title",
            text: a("version_compare_title")
              .replace("{vA}", v)
              .replace("{vB}", k),
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
          f.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let w = f.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let S of y) {
          let P = w.createEl("div", { cls: "paperforge-version-diff-row" }),
            F =
              S.type === "added" ? "[+]" : S.type === "removed" ? "[-]" : "[~]",
            T = S.heading || "paragraph " + (S.paragraphIndex + 1);
          (P.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: F + " " + T,
          }),
            S.oldText &&
              P.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: S.oldText.slice(0, 200),
              }),
            S.newText &&
              P.createEl("pre", {
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
      E = h.createEl("button", {
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
        var s;
        let i = ((s = this._searchInput) == null ? void 0 : s.value) || "";
        if (
          (i.startsWith("@") && !i.startsWith("@ ")
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
          !i.trim())
        ) {
          ((this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        i.startsWith("@") ||
          (this._searchTimer = setTimeout(() => {
            this.executeSearch();
          }, 200));
      }),
      this._searchInput.addEventListener("keydown", (i) => {
        var s, o;
        if (i.key === "Escape") {
          (i.preventDefault(),
            this._searchInput &&
              ((this._searchInput.value = ""), this._searchInput.blur()),
            (this._searchState = "idle"),
            (this._searchResults = null),
            (this._searchActiveIndex = -1),
            this._renderSearchState());
          return;
        }
        if (i.key === "ArrowDown" || i.key === "ArrowUp") {
          if (
            this._searchState !== "results" ||
            !((s = this._searchResults) != null && s.length)
          )
            return;
          i.preventDefault();
          let l = this._searchResults.length;
          i.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                l - 1
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
            p.forEach((u, _) => {
              _ === this._searchActiveIndex
                ? (u.setAttribute("aria-selected", "true"),
                  u.classList.add("active"))
                : (u.setAttribute("aria-selected", "false"),
                  u.classList.remove("active"));
            });
          return;
        }
        if (i.key === "Enter" && i.ctrlKey) {
          (i.preventDefault(),
            this._searchTimer &&
              (clearTimeout(this._searchTimer), (this._searchTimer = void 0)));
          let l = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = l));
          return;
        }
        i.key === "Enter" &&
          (i.preventDefault(),
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
            let i = n.openTab;
            typeof i == "function" && i.call(n, "paperforge");
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
          let s = this.app.vault.adapter.basePath;
          if (typeof s != "string") return;
          let o = this._resolvePython();
          if (!o) return;
          let { path: l, args: p = [] } = o;
          (0, ge.spawn)(l, [...p, "-m", "paperforge", "doctor"], {
            cwd: s,
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
            let i = n.openTab;
            typeof i == "function" && i.call(n, "paperforge");
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
    let i = this.app.vault.adapter,
      s = "";
    if (i && typeof i == "object" && "basePath" in i) {
      let m = i.basePath;
      s = typeof m == "string" ? m : "";
    }
    if (!s) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let o = null,
      p = this.app.plugins;
    if (p && typeof p == "object" && "plugins" in p) {
      let m = p.plugins;
      if (m && typeof m == "object" && "paperforge" in m) {
        let v = m.paperforge;
        v && typeof v == "object" && "settings" in v && (o = v.settings);
      }
    }
    let u = this._resolvePython();
    if (!u) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let { path: _, args: f = [] } = u,
      g = n === "retrieve" ? ["--deep"] : [],
      h = await he({ app: this.app }, "memory"),
      b = (0, ge.spawn)(
        _,
        [...f, "-m", "paperforge", "--vault", s, n, r, ...g, "--json"],
        { cwd: s, timeout: 3e4, env: h }
      ),
      E = [];
    (b.stdout.on("data", (m) => {
      E.push(m.toString("utf-8"));
    }),
      b.stderr.on("data", () => {}),
      b.on("close", (m) => {
        if (m !== 0) {
          let w = ft(String(m));
          ((this._searchState = this._mapErrorToSearchState(w.type)),
            this._renderSearchState());
          return;
        }
        let v = E.join(""),
          k = v.indexOf("{"),
          y = v.lastIndexOf("}"),
          x = "";
        if (k !== -1 && y > k) x = v.slice(k, y + 1);
        else {
          let w = v.indexOf("["),
            S = v.lastIndexOf("]");
          w !== -1 && S > w && (x = v.slice(w, S + 1));
        }
        if (!x) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let w = JSON.parse(x),
            S = [];
          if (w && typeof w == "object" && "data" in w) {
            let P = w.data;
            if (P && typeof P == "object") {
              let F = P;
              "matches" in F && Array.isArray(F.matches) && (S = F.matches);
            }
          }
          ((this._searchResults = S),
            (this._searchState = S.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (w) {
          let S = w instanceof Error ? w.message : String(w);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      b.on("error", (m) => {
        let v = m.code;
        if (typeof v == "string") {
          let k = ft(v);
          this._searchState = this._mapErrorToSearchState(k.type);
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
    for (let i = 0; i < e.length; i++) {
      let s = e[i];
      if (!s || typeof s != "object") continue;
      let o = s,
        l = i === this._searchActiveIndex,
        p = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": l ? "true" : "false",
            "aria-posinset": String(i + 1),
            "aria-setsize": String(e.length),
          },
        });
      l && p.addClass("active");
      let u =
        typeof o.title == "string"
          ? o.title
          : typeof o.file_name == "string"
            ? o.file_name
            : "(untitled)";
      p.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let _ = typeof o.zotero_key == "string" ? o.zotero_key : "",
        f =
          typeof o.main_note_path == "string" && o.main_note_path
            ? o.main_note_path
            : null,
        g = typeof o.note_path == "string" && o.note_path ? o.note_path : null,
        h = f || g;
      if (!h && _) {
        let m = this._getCachedIndex().find(
          (v) =>
            v !== null &&
            typeof v == "object" &&
            "zotero_key" in v &&
            v.zotero_key === _
        );
        if (m && typeof m == "object") {
          let v = m;
          h =
            typeof v.main_note_path == "string" && v.main_note_path
              ? v.main_note_path
              : typeof v.note_path == "string" && v.note_path
                ? v.note_path
                : null;
        }
      }
      (h
        ? p.addEventListener("click", (E) => {
            let m = E.ctrlKey || E.metaKey;
            this.app.workspace.openLinkText(h, "", m);
          })
        : p.addEventListener("click", () => {
            new D.Notice("[!!] Note not found: " + (_ || "unknown"), 6e3);
          }),
        p.addEventListener("keydown", (E) => {
          if (E.key === "Enter" && h) {
            E.preventDefault();
            let m = E.ctrlKey || E.metaKey;
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
        let E = o.score,
          m = typeof E == "number" ? E.toFixed(3) : String(E);
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
        let E = o.abstract;
        p.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: E.length > 200 ? E.slice(0, 200) + "..." : E,
        });
      }
      if (t && typeof o.text == "string" && o.text) {
        let E = o.text;
        p.createEl("div", {
          cls: "paperforge-search-result-source",
          text: E.length > 300 ? E.slice(0, 300) + "..." : E,
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
      new D.Notice(
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
        let E = this.app.metadataCache.getFileCache(h);
        if (
          (E && E.frontmatter && E.frontmatter.zotero_key
            ? (b = E.frontmatter.zotero_key)
            : (b = this._extractZoteroKeyFromPath(h.path)),
          b)
        )
          n = [...n, b];
        else if (E && E.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new D.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new D.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new D.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let i = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      s = this._resolvePython();
    if (!s) {
      (this._showMessage("[!!] Runtime not available", "error"),
        new D.Notice(
          "[!!] PaperForge runtime is not ready. Check settings.",
          6e3
        ),
        t.removeClass("running"));
      return;
    }
    let { path: o, args: l = [] } = s,
      p = await he({ app: this.app }, e.cmd),
      u = (0, ge.spawn)(o, [...l, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: i,
        env: p,
      }),
      _ = [],
      f = Date.now(),
      g = setInterval(() => this._fetchStats(!0), 4e3);
    (u.stdout.on("data", (h) => {
      let b = h
        .toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let E of b) {
        let m = E.trim();
        m &&
          (_.push(m),
          this._showMessage(
            _.slice(-8).join(`
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
        for (let E of b) {
          if (E.includes("\r") || E.includes("%") || E.includes("\u2588"))
            continue;
          let m = E.trim();
          m &&
            !m.match(/^\d+%|^\|/) &&
            (_.push(m),
            this._showMessage(
              _.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      u.on("close", (h) => {
        (clearInterval(g), t.removeClass("running"));
        let b = ((Date.now() - f) / 1e3).toFixed(1);
        if (h !== 0) {
          let E = _.slice(-3).join(" | ") || "exit code " + h;
          (e.cmd === "repair" || e.cmd === "ocr") && h === 1
            ? (this._showMessage("[WARN] " + E, "running"),
              new D.Notice("[WARN] " + e.cmd + " partial: " + E, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + E, "error"),
              new D.Notice("[!!] " + e.cmd + " failed: " + E, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let E = _.join(`
`);
          if (E.trim())
            try {
              (JSON.parse(E),
                navigator.clipboard
                  .writeText(E)
                  .then(() => {
                    let m = `${b}s \u2014 ${E.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + m, "ok"),
                      new D.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + E.length + " chars"
                      ));
                  })
                  .catch((m) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + m.message,
                      "error"
                    ),
                      new D.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (m) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new D.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    m.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new D.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let m =
              _.filter((k) => k.match(/updated \d+/)).pop() ||
              _[_.length - 1] ||
              "",
            v = `${b}s \u2014 ${m}`;
          (this._showMessage("[OK] " + e.title + ": " + v, "ok"),
            new D.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (k) {
            console.log("[PF] fetchStats error:", k);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              et(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      u.on("error", (h) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + h.message, "error"),
          new D.Notice("[!!] Cannot start: " + h.message, 8e3));
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
            i = r.filePath;
          (this._currentMode === n && this._currentFilePath === i) ||
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
    let t = e.app.workspace.getLeavesOfType(be);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: be, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var ie = require("obsidian"),
  pe = N(require("fs")),
  we = N(require("path")),
  kt = require("child_process");
var Le = class extends ie.ItemView {
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
  }
  static async open(e) {
    let { WorkspaceLeaf: t } = require("obsidian"),
      r = e.app.workspace.getLeavesOfType(Se);
    if (r.length > 0) {
      e.app.workspace.revealLeaf(r[0]);
      return;
    }
    let n = e.app.workspace.getRightLeaf(!1);
    n &&
      (await n.setViewState({ type: Se, active: !0 }),
      e.app.workspace.revealLeaf(n));
  }
  getViewType() {
    return Se;
  }
  getDisplayText() {
    return "OCR Workspace";
  }
  getIcon() {
    return "scan-text";
  }
  async onOpen() {
    (await this._loadPapers(), this._render());
  }
  async _loadPapers() {
    var n, i, s, o, l, p, u, _, f, g, h;
    let e = this.app.vault.adapter.basePath,
      t = X(e),
      r = we.join(
        e,
        t.systemDir,
        "PaperForge",
        "indexes",
        "formal-library.json"
      );
    if (!pe.existsSync(r)) {
      this.papers = [];
      return;
    }
    try {
      let b = JSON.parse(pe.readFileSync(r, "utf-8")),
        E = (n = b == null ? void 0 : b.items) != null ? n : [];
      this.papers = [];
      for (let m of E) {
        let v = m.zotero_key;
        if (!v) continue;
        let k = we.join(e, t.systemDir, "PaperForge", "ocr", v, "meta.json"),
          y = {};
        if (pe.existsSync(k))
          try {
            y = JSON.parse(pe.readFileSync(k, "utf-8"));
          } catch (S) {}
        let x = we.join(e, t.systemDir, "PaperForge", "ocr", v, "backups"),
          w = 0;
        (pe.existsSync(x) &&
          (w = pe
            .readdirSync(x)
            .filter((S) => S.startsWith("fulltext.pre-rebuild")).length),
          this.papers.push({
            key: v,
            title: (i = m.title) != null ? i : v,
            status:
              (o = (s = y.ocr_status) != null ? s : y.ocrStatus) != null
                ? o
                : "pending",
            pipelineVersion: (l = y.ocr_pipeline_version) != null ? l : "",
            lastRun:
              (u = (p = y.ocr_finished_at) != null ? p : y.ocrFinishedAt) !=
              null
                ? u
                : "",
            hasBackup: w > 0,
            authors:
              (g =
                (f = (_ = m.authors) == null ? void 0 : _.join) == null
                  ? void 0
                  : f.call(_, ", ")) != null
                ? g
                : "",
            year: (h = m.year) != null ? h : "",
            pages: y.page_count ? String(y.page_count) : "",
            backupCount: w,
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
  _renderHeader(e) {
    let t = e.createDiv({ cls: "pf-ocr-ws-header" });
    (t.createEl("h1", { text: a("ocr_ws_title") }),
      t.createEl("p", { cls: "pf-ocr-ws-lede", text: a("ocr_ws_lede") }));
  }
  _renderActivity(e) {
    var _;
    let t = e.createDiv({
        cls: `pf-ocr-ws-activity${this.running ? " pf-active" : ""}`,
        attr: { "aria-live": "polite" },
      }),
      r = t.createDiv({ cls: "pf-ocr-ws-activity-head" }),
      n = r.createDiv({ cls: "pf-ocr-ws-activity-title" });
    n.setText(a("ocr_ws_processing"));
    let i = this.progress.paperKey;
    if (i) {
      let f = this.papers.find((g) => g.key === i);
      n.createEl("span", {
        text: (_ = f == null ? void 0 : f.title) != null ? _ : i,
      });
    }
    r.createEl("button", {
      cls: "pf-btn pf-btn-ghost",
      text: a("ocr_ws_stop"),
    }).addEventListener("click", () => this._stopBuild());
    let l = t
        .createDiv({ cls: "pf-ocr-ws-progress-track" })
        .createDiv({ cls: "pf-ocr-ws-progress-fill" }),
      p =
        this.progress.total > 0
          ? Math.round((this.progress.current / this.progress.total) * 100)
          : 0;
    l.style.transform = `scaleX(${p / 100})`;
    let u = t.createDiv({ cls: "pf-ocr-ws-progress-meta" });
    (u.createEl("span", {
      text: `${this.progress.current} / ${this.progress.total} papers`,
    }),
      u.createEl("span", { text: `${p}%` }));
  }
  _renderToolbar(e) {
    let t = this._filteredPapers(),
      r = [
        ...new Set(this.papers.map((l) => l.pipelineVersion).filter(Boolean)),
      ]
        .sort()
        .reverse(),
      n = e.createDiv({ cls: "pf-ocr-ws-toolbar" }),
      i = n.createDiv({ cls: "pf-ocr-ws-toolbar-count" });
    i.innerHTML = a("ocr_ws_showing")
      .replace("{count}", String(t.length))
      .replace("{total}", String(this.papers.length));
    let s = n.createDiv({ cls: "pf-ocr-ws-field" });
    s.createEl("label", { text: a("ocr_ws_filter_status") });
    let o = s.createEl("select");
    for (let [l, p] of [
      ["all", a("ocr_ws_filter_all")],
      ["unprocessed", a("ocr_ws_filter_unprocessed")],
      ["review", a("ocr_ws_filter_review")],
      ["processed", a("ocr_ws_filter_processed")],
    ]) {
      let u = o.createEl("option", {
        text: String(p),
        attr: { value: String(l) },
      });
      l === this.filter && (u.selected = !0);
    }
    if (
      (o.addEventListener("change", () => {
        ((this.filter = o.value),
          (this.selectedKey = null),
          this.checkedKeys.clear(),
          this._render());
      }),
      r.length > 0)
    ) {
      let l = n.createDiv({ cls: "pf-ocr-ws-version-field" });
      for (let p of r)
        l.createEl("button", {
          cls: `pf-ocr-ws-chip${this.versionFilter === p ? " pf-active" : ""}`,
          text: `v${p}`,
        }).addEventListener("click", () => {
          ((this.versionFilter = this.versionFilter === p ? null : p),
            this._render());
        });
    }
  }
  _filteredPapers() {
    let e = this.papers;
    return (
      this.filter === "unprocessed"
        ? (e = e.filter((t) => t.status === "pending" || t.status === "nopdf"))
        : this.filter === "review"
          ? (e = e.filter(
              (t) => t.status === "failed" || t.status === "processing"
            ))
          : this.filter === "processed" &&
            (e = e.filter((t) => t.status === "done")),
      this.versionFilter &&
        (e = e.filter((t) => t.pipelineVersion === this.versionFilter)),
      e
    );
  }
  _renderTable(e) {
    let t = this._filteredPapers(),
      r = e.createDiv({ cls: "pf-ocr-ws-viewport" });
    if (t.length === 0) {
      r.createDiv({
        cls: "pf-ocr-ws-empty pf-visible",
        text: a("ocr_ws_no_papers"),
      });
      return;
    }
    let n = r.createEl("table", { cls: "pf-ocr-ws-table" }),
      s = n.createEl("thead").createEl("tr");
    (s
      .createEl("th", { cls: "pf-ocr-ws-col-check" })
      .createEl("input", { attr: { type: "checkbox" } }, (l) => {
        l.addEventListener("change", () => {
          (l.checked
            ? t.forEach((p) => this.checkedKeys.add(p.key))
            : this.checkedKeys.clear(),
            this._render());
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
    let o = n.createEl("tbody");
    for (let l of t) {
      let p = !!this.papers.find(
          (v) =>
            v.pipelineVersion &&
            l.pipelineVersion &&
            v.pipelineVersion > l.pipelineVersion
        ),
        u = o.createEl("tr", { cls: p ? "pf-update" : "" });
      (u.addEventListener("click", (v) => {
        v.target.tagName !== "INPUT" &&
          ((this.selectedKey = l.key === this.selectedKey ? null : l.key),
          this._render());
      }),
        u
          .createEl("td", { cls: "pf-ocr-ws-col-check" })
          .createEl("input", { attr: { type: "checkbox" } }, (v) => {
            ((v.checked = this.checkedKeys.has(l.key)),
              v.addEventListener("change", () => {
                (v.checked
                  ? this.checkedKeys.add(l.key)
                  : this.checkedKeys.delete(l.key),
                  this._render());
              }));
          }));
      let f = u.createEl("td", { cls: "pf-ocr-ws-col-paper" });
      (f.createDiv({ cls: "pf-ocr-ws-paper-title", text: l.title }),
        (l.authors || l.year) &&
          f.createDiv({
            cls: "pf-ocr-ws-paper-meta",
            text: [l.authors, l.year].filter(Boolean).join(", "),
          }),
        u
          .createEl("td", { cls: "pf-ocr-ws-col-status" })
          .createEl("span", {
            cls: `pf-ocr-ws-status pf-${yr(l.status)}`,
            text: br(l.status),
          }),
        u
          .createEl("td", { cls: "pf-ocr-ws-col-version" })
          .createEl("span", {
            cls: "pf-ocr-ws-version",
            text: l.pipelineVersion || "\u2014",
          }),
        u
          .createEl("td", { cls: "pf-ocr-ws-col-date" })
          .setText(l.lastRun ? l.lastRun.slice(0, 10) : "\u2014"),
        u
          .createEl("td", { cls: "pf-ocr-ws-col-action" })
          .createEl("button", {
            cls: "pf-btn pf-btn-secondary",
            text: a("ocr_ws_btn_preview"),
          })
          .addEventListener("click", (v) => {
            (v.stopPropagation(), this._openFulltext(l.key));
          }));
    }
  }
  _renderBatchBar(e) {
    let t = this.papers.filter((l) => this.checkedKeys.has(l.key)),
      r = e.createDiv({ cls: "pf-ocr-ws-batchbar" }),
      n = r.createDiv({ cls: "pf-ocr-ws-selection" });
    t.length === 0
      ? (n.createEl("strong", { text: a("ocr_ws_none_selected") }),
        n.createEl("span", { text: a("ocr_ws_select_hint") }))
      : n.createEl("strong", {
          text: a("ocr_ws_selected").replace("{count}", String(t.length)),
        });
    let i = r.createDiv({ cls: "pf-ocr-ws-batch-actions" }),
      s = i.createEl("button", {
        cls: "pf-btn pf-btn-primary",
        text: a("ocr_ws_btn_process_selected"),
      });
    ((s.disabled = t.length === 0),
      s.addEventListener("click", () => this._runOcr(t.map((l) => l.key))));
    let o = i.createEl("button", {
      cls: "pf-btn pf-btn-warning",
      text: a("ocr_ws_btn_update_selected"),
    });
    ((o.disabled = t.length === 0),
      o.addEventListener("click", () => this._runRebuild(t.map((l) => l.key))));
  }
  _renderDetail(e) {
    let t = this.papers.find((b) => b.key === this.selectedKey);
    if (!t) return;
    let n = e
        .createDiv({ cls: "pf-ocr-ws-detail pf-open" })
        .createDiv({ cls: "pf-ocr-ws-detail-card" }),
      i = n.createDiv({ cls: "pf-ocr-ws-detail-head" }),
      s = i.createDiv({});
    (s.createEl("h2", { text: t.title }),
      s.createEl("span", {
        cls: `pf-ocr-ws-status pf-${yr(t.status)}`,
        text: br(t.status),
      }),
      i
        .createEl("button", {
          cls: "pf-btn pf-btn-ghost",
          text: a("ocr_ws_close"),
        })
        .addEventListener("click", () => {
          ((this.selectedKey = null), this._render());
        }));
    let l = n.createDiv({ cls: "pf-ocr-ws-detail-grid" });
    (this._addFact(l, a("ocr_ws_fact_version"), t.pipelineVersion || "\u2014"),
      this._addFact(
        l,
        a("ocr_ws_fact_last_run"),
        t.lastRun ? t.lastRun.slice(0, 10) : "\u2014"
      ),
      this._addFact(l, a("ocr_ws_fact_authors"), t.authors || "\u2014"),
      this._addFact(l, a("ocr_ws_fact_year"), t.year || "\u2014"),
      this._addFact(l, a("ocr_ws_fact_pages"), t.pages || "\u2014"),
      this._addFact(
        l,
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
    let f = u.createEl("button", {
      cls: "pf-btn pf-btn-secondary",
      text: a("ocr_ws_detail_restore_backup"),
    });
    ((f.disabled = !t.hasBackup),
      f.addEventListener("click", () => {
        new ie.Notice("Version history panel not yet integrated");
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
    var i, s;
    let e = this.app.plugins.plugins.paperforge,
      t =
        (s =
          (i = e == null ? void 0 : e.settings) == null
            ? void 0
            : i.python_path) == null
          ? void 0
          : s.trim();
    if (t && require("fs").existsSync(t)) return { path: t, args: [] };
    if (!e || typeof e.getManagedRuntime != "function") return null;
    let r = e.getManagedRuntime();
    if (!r) return null;
    let n = ce(r.current());
    return n ? { path: n.command, args: [...n.args] } : null;
  }
  _runOcr(e) {
    let t = this._resolvePython();
    if (!t) {
      new ie.Notice("Runtime not ready");
      return;
    }
    let r = this.app.vault.adapter.basePath;
    ((this.running = !0),
      (this.progress = { current: 0, total: e.length, paperKey: "" }),
      this._render(),
      (0, kt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "ocr", "run", ...e],
        { cwd: r, timeout: 6e5 },
        (n) => {
          ((this.running = !1),
            n
              ? new ie.Notice("OCR failed: " + (n.message || n))
              : new ie.Notice("OCR completed"),
            this._loadPapers().then(() => this._render()));
        }
      ));
  }
  _runRebuild(e) {
    let t = this._resolvePython();
    if (!t) {
      new ie.Notice("Runtime not ready");
      return;
    }
    let r = this.app.vault.adapter.basePath;
    ((this.running = !0),
      (this.progress = { current: 0, total: e.length, paperKey: "" }),
      this._render(),
      (0, kt.execFile)(
        t.path,
        [...t.args, "-m", "paperforge", "ocr", "rebuild", ...e],
        { cwd: r, timeout: 6e5 },
        (n) => {
          ((this.running = !1),
            n
              ? new ie.Notice("Rebuild failed: " + (n.message || n))
              : new ie.Notice("Rebuild completed"),
            this._loadPapers().then(() => this._render()));
        }
      ));
  }
  _stopBuild() {
    ((this.running = !1), this._render());
  }
  _openFulltext(e) {
    let t = this.app.vault.adapter.basePath,
      r = X(t),
      n = we.join(t, r.systemDir, "PaperForge", "ocr", e, "fulltext.md");
    if (!pe.existsSync(n)) {
      new ie.Notice("Fulltext not found");
      return;
    }
    let i = this.app.vault.getAbstractFileByPath(
      we.relative(t, n).replace(/\\/g, "/")
    );
    i
      ? this.app.workspace.getLeaf().openFile(i)
      : new ie.Notice("Fulltext not found in vault");
  }
};
function yr(d) {
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
function br(d) {
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
var at = class extends q.Plugin {
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
        (this._managedRuntime = new me({ version: this.manifest.version })),
      this._managedRuntime
    );
  }
  _getPythonCommand() {
    let e = ce(this.getManagedRuntime().current());
    return e ? { path: e.command, args: [...e.args] } : null;
  }
  async onload() {
    (await this.loadSettings(),
      await Zt(
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
    (Nt(this.app, this.settings.language),
      this.registerView(be, (t) => new Oe(t)),
      this.registerView(Se, (t) => new Le(t, this)));
    try {
      (0, q.addIcon)(Ne, Tt);
    } catch (t) {}
    (this.addRibbonIcon(Ne, "PaperForge Dashboard", () => Oe.open(this)),
      this.addRibbonIcon("scan-text", "PaperForge OCR Workspace", () =>
        Le.open(this)
      ),
      te.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", async () => {
          let t = this.app.vault.adapter.basePath;
          new q.Notice("PaperForge: Redo OCR starting...");
          let r = this._getPythonCommand();
          if (!r) {
            new q.Notice("Runtime not ready");
            return;
          }
          let { path: n, args: i } = r,
            s = await he(this, "ocr");
          (0, Me.execFile)(
            n,
            [...i, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5, env: s },
            (o, l, p) => {
              if (o) {
                new q.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new q.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new rt(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${a("guide_open")}`,
        callback: () => Oe.open(this),
      }),
      this.addCommand({
        id: "paperforge-ocr-workspace",
        name: "PaperForge: Open OCR Workspace",
        callback: () => Le.open(this),
      }));
    for (let t of te)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: async () => {
          if (t.disabled) {
            new q.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new q.Notice(`PaperForge: running ${t.cmd}...`);
          let n = this._getPythonCommand();
          if (!n) {
            new q.Notice("Runtime not ready");
            return;
          }
          let { path: i, args: s = [] } = n,
            o = Array.isArray(t.args) ? [...t.args] : [],
            l = await he(this, t.cmd);
          (0, Me.execFile)(
            i,
            [...s, "-m", "paperforge", t.cmd, ...o],
            { cwd: r, timeout: 3e5, env: l },
            (p, u, _) => {
              if (p) {
                new q.Notice(
                  `[!!] ${t.cmd} failed: ${(_ || p.message).slice(0, 120)}`,
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
    let t = X(e).exportsDir;
    if (!K.existsSync(t)) return;
    let r = 0;
    try {
      K.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let i = K.statSync(Be.join(t, n));
        i.mtimeMs > r && (r = i.mtimeMs);
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
    (0, Me.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, i, s) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let o = X(e).exportsDir,
          l = 0;
        (K.readdirSync(o).forEach((p) => {
          p.endsWith(".json") &&
            (l = Math.max(l, K.statSync(Be.join(o, p)).mtimeMs));
        }),
          (this._lastExportMtime = l));
      } catch (o) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = X(e).ocrDir;
    if (K.existsSync(t))
      try {
        K.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = Be.join(t, r.name, "meta.json");
          if (!K.existsSync(n)) return;
          let i = K.statSync(n),
            s = this._lastOcrMtimes[r.name] || 0;
          if (
            i.mtimeMs <= s ||
            ((this._lastOcrMtimes[r.name] = i.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let o = this._getPythonCommand();
          if (!o) {
            this._autoSyncRunning = !1;
            return;
          }
          let l = `"${o.path}" ${o.args.join(" ")} -m paperforge --vault "${e}" sync`;
          (0, Me.exec)(l, { timeout: 3e4, encoding: "utf-8" }, () => {
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
      if (!K.existsSync(t)) return r;
      let n = K.readFileSync(t, "utf-8"),
        i = JSON.parse(n),
        s = i.vault_config || {};
      return {
        system_dir: s.system_dir || i.system_dir || r.system_dir,
        resources_dir: s.resources_dir || i.resources_dir || r.resources_dir,
        literature_dir:
          s.literature_dir || i.literature_dir || r.literature_dir,
        base_dir: s.base_dir || i.base_dir || r.base_dir,
        zotero_data_dir: i.zotero_data_dir || r.zotero_data_dir,
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
      K.existsSync(r) && (n = JSON.parse(K.readFileSync(r, "utf-8")));
    } catch (s) {
      console.warn("PaperForge: Failed to read paperforge.json for update", s);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let i = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let s of i) e[s] !== void 0 && (n.vault_config[s] = e[s]);
    (e.zotero_data_dir !== void 0 && (n.zotero_data_dir = e.zotero_data_dir),
      n.schema_version || (n.schema_version = "2"));
    for (let s of i) delete n[s];
    try {
      if (
        (K.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let s = this.readPaperforgeJson();
        ((this.settings.system_dir = s.system_dir),
          (this.settings.resources_dir = s.resources_dir),
          (this.settings.literature_dir = s.literature_dir),
          (this.settings.base_dir = s.base_dir));
      }
    } catch (s) {
      (console.error("PaperForge: Failed to write paperforge.json", s),
        new q.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(be));
  }
  async loadSettings() {
    var n, i;
    let e = (n = await this.loadData()) != null ? n : {};
    ((this.settings = Object.assign({}, He, e)),
      this.settings.features &&
        He.features &&
        (this.settings.features = Object.assign(
          {},
          He.features,
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
        : (i = this.settings.zotero_data_dir) != null &&
          i.trim() &&
          this.savePaperforgeJson({
            zotero_data_dir: this.settings.zotero_data_dir.trim(),
          }),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let s = this.settings.python_path.trim();
      this.settings._python_path_stale = !K.existsSync(s);
    }
  }
  async saveSettings() {
    let e = {};
    for (let t of Object.keys(He))
      t in this.settings && (e[t] = this.settings[t]);
    await this.saveData(e);
  }
  _checkReleaseNotes() {
    let e = this.manifest.version;
    if (this.settings.last_seen_version === e) return;
    let i = (ut().versions || []).find((o) => o.version === e);
    class s extends q.Modal {
      constructor(l, p) {
        (super(l), (this._entry = p));
      }
      onOpen() {
        let { contentEl: l } = this;
        if (
          (l.createEl("h2", {
            text: `PaperForge v${e} \u66F4\u65B0\u8BF4\u660E`,
          }),
          this._entry)
        ) {
          if (
            (l.createEl("p", {
              text: this._entry.title,
              cls: "paperforge-modal-subtitle",
            }),
            this._entry.breaking_or_migration &&
              this._entry.breaking_or_migration.length > 0)
          ) {
            l.createEl("h4", {
              text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
            });
            for (let p of this._entry.breaking_or_migration)
              l.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            l.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let p of this._entry.new_features)
              l.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            l.createEl("h4", { text: "\u4FEE\u590D" });
            for (let p of this._entry.fixes)
              l.createEl("p", {
                text: `\u2022 ${p}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let p = l.createEl("div", {
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
          l.createEl("p", {
            text:
              "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
              e +
              "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
          });
        new q.Setting(l).addButton((p) =>
          p
            .setButtonText("\u77E5\u9053\u4E86")
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        let { contentEl: l } = this;
        l.empty();
      }
    }
    (new s(this.app, i).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
