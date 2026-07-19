"use strict";
var vr = Object.create;
var Qe = Object.defineProperty;
var Er = Object.getOwnPropertyDescriptor;
var xr = Object.getOwnPropertyNames;
var kr = Object.getPrototypeOf,
  wr = Object.prototype.hasOwnProperty;
var Sr = (p, d) => () => (d || p((d = { exports: {} }).exports, d), d.exports),
  Pr = (p, d) => {
    for (var e in d) Qe(p, e, { get: d[e], enumerable: !0 });
  },
  Bt = (p, d, e, t) => {
    if ((d && typeof d == "object") || typeof d == "function")
      for (let r of xr(d))
        !wr.call(p, r) &&
          r !== e &&
          Qe(p, r, {
            get: () => d[r],
            enumerable: !(t = Er(d, r)) || t.enumerable,
          });
    return p;
  };
var $ = (p, d, e) => (
    (e = p != null ? vr(kr(p)) : {}),
    Bt(
      d || !p || !p.__esModule
        ? Qe(e, "default", { value: p, enumerable: !0 })
        : e,
      p
    )
  ),
  Cr = (p) => Bt(Qe({}, "__esModule", { value: !0 }), p);
var Et = Sr((Gr, Tr) => {
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
var Ur = {};
Pr(Ur, { default: () => ut });
module.exports = Cr(Ur);
var ee = require("obsidian"),
  J = $(require("fs")),
  Le = $(require("path")),
  Ne = require("child_process");
var Re = "paperforge-status",
  Ve = "paperforge",
  Ht =
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path><line x1="8" y1="7" x2="16" y2="7"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>',
  ce = [
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
  };
function jt(p, d) {
  if (!d || !d.note_path) return d;
  let e = p.vault.getAbstractFileByPath(d.note_path);
  if (!e) return d;
  let t = p.metadataCache.getFileCache(e),
    r = t && t.frontmatter;
  if (!r) return d;
  let n = { ...d };
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
function ft(p, d) {
  return p && { ...p, ...d };
}
var ht = 1,
  Fe = ["installation", "library", "ocr", "memory", "maintenance", "help"],
  It = [
    "unknown",
    "unavailable",
    "missing_input",
    "needs_action",
    "limited",
    "ready",
  ],
  Lt = ["unknown", "ok", "warning", "error"],
  Nt = ["idle", "running"];
function Vt(p) {
  if (!p || typeof p != "object" || Array.isArray(p)) return !1;
  let d = p;
  return !(
    typeof d.verb != "string" ||
    typeof d.label != "string" ||
    typeof d.destructive != "boolean" ||
    (d.destructive_scope !== null && typeof d.destructive_scope != "string") ||
    (d.destructive_effect !== null &&
      typeof d.destructive_effect != "string") ||
    typeof d.confirmation_required != "boolean" ||
    (d.confirmation_prompt !== null &&
      typeof d.confirmation_prompt != "string") ||
    typeof d.command != "string" ||
    typeof d.scope != "string" ||
    typeof d.scope_count != "number"
  );
}
function je(p) {
  return {
    verb: "probe",
    label: "Check",
    destructive: !1,
    destructive_scope: null,
    destructive_effect: null,
    confirmation_required: !1,
    confirmation_prompt: null,
    command: `probe ${p}`,
    scope: p,
    scope_count: 1,
  };
}
function $t() {
  return {
    verb: "setup",
    label: "Open Setup Wizard",
    destructive: !1,
    destructive_scope: null,
    destructive_effect: null,
    confirmation_required: !1,
    confirmation_prompt: null,
    command: "setup",
    scope: "installation",
    scope_count: 1,
  };
}
function gt(p, d) {
  if (!p || typeof p != "object") return !1;
  let e = p;
  if (
    e.schema_version !== 1 ||
    typeof e.module != "string" ||
    !e.module ||
    !Fe.includes(e.module) ||
    (d !== void 0 && e.module !== d) ||
    typeof e.capability_state != "string" ||
    !It.includes(e.capability_state) ||
    typeof e.severity != "string" ||
    !Lt.includes(e.severity) ||
    typeof e.activity_state != "string" ||
    !Nt.includes(e.activity_state) ||
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
    (r.primary !== null && !Vt(r.primary)) ||
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
        typeof s.module != "string" ||
        !a.includes(s.module) ||
        typeof s.capability_state != "string" ||
        !It.includes(s.capability_state) ||
        typeof s.severity != "string" ||
        !Lt.includes(s.severity) ||
        typeof s.activity_state != "string" ||
        !Nt.includes(s.activity_state) ||
        (s.activity_label !== null && typeof s.activity_label != "string")
      )
        return !1;
      if (s.activity_progress !== null) {
        if (typeof s.activity_progress != "object") return !1;
        let i = s.activity_progress;
        if (typeof i.current != "number" || typeof i.total != "number")
          return !1;
      }
      if (
        typeof s.reason_code != "string" ||
        !s.reason_code ||
        typeof s.reason_text != "string" ||
        (s.action !== null && !Vt(s.action))
      )
        return !1;
    }
  }
  return !0;
}
function Te(p) {
  return {
    schema_version: ht,
    module: p,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: { code: `${p}.no_probe`, text: `${p} has not been probed yet.` },
    action: { primary: p === "maintenance" ? null : je(p) },
    notices: [],
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function mt(p) {
  return {
    schema_version: ht,
    module: p,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: `${p}.stale`,
      text: `Cached probe data for ${p} is stale.`,
    },
    action: { primary: p === "maintenance" ? null : je(p) },
    notices: [],
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function De(p) {
  return {
    schema_version: ht,
    module: p,
    capability_state: "unknown",
    activity_state: "idle",
    activity_label: null,
    activity_progress: null,
    severity: "unknown",
    reason: {
      code: `${p}.invalid_response`,
      text: `Probe response for ${p} was invalid.`,
    },
    action: { primary: p === "maintenance" ? null : je(p) },
    notices: [],
    updated_at: new Date(0).toISOString(),
    ttl_seconds: 0,
  };
}
function yt(p) {
  if (p.activity_state === "running") return !1;
  if (p.ttl_seconds <= 0) return !0;
  let d = new Date(p.updated_at).getTime();
  return isNaN(d) ? !0 : Date.now() - d > p.ttl_seconds * 1e3;
}
function $e(p) {
  return p.capability_state === "ready" && p.action.primary === null;
}
function ze(p) {
  var r, n, s;
  let d = (r = p.action) == null ? void 0 : r.primary,
    e = (n = d == null ? void 0 : d.verb) != null ? n : "probe",
    t = (s = d == null ? void 0 : d.label) != null ? s : e;
  return e === "setup" || e === "set_config" || e === "update"
    ? { kind: "setup", verb: e, label: t }
    : e === "probe"
      ? { kind: "probe", verb: e, label: t }
      : { kind: "action", verb: e, label: t };
}
function zt(p, d) {
  let e = {};
  for (let t of d) {
    let r = p[t];
    if (!r || typeof r != "object") {
      e[t] = Te(t);
      continue;
    }
    if (!gt(r, t)) {
      e[t] = De(t);
      continue;
    }
    if (yt(r)) {
      e[t] = mt(t);
      continue;
    }
    e[t] = r;
  }
  return e;
}
var bt = {
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
        'Press Ctrl+P and run "PaperForge: Open Main Panel", or click the PaperForge icon in the left sidebar.',
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
      md_select_installation: "Installation",
      md_select_library: "Library",
      md_select_ocr: "OCR",
      md_select_memory: "Memory",
      installation_detail_heading: "Installation Details",
      btn_back_to_overview: "\u2190 Back to Overview",
      agent_integration_section: "Agent Integration",
      module_detail_open_installation: "Open Installation",
      module_detail_open_help: "Help & Docs",
      module_detail_open_maintenance: "Maintenance",
      module_detail_open_library: "Open Library",
      module_detail_open_ocr: "Open OCR",
      module_detail_open_memory: "Open Memory",
      action_unknown_pair: "Unknown action: {verb}",
      ocr_stop_batch: "Stop OCR batch",
      runtime_not_available: "No Python runtime available",
      md_unavailable_module: "Not available yet",
      library_detail_heading: "Library Details",
      ocr_detail_heading: "OCR Details",
      memory_detail_heading: "Memory Details",
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
      cc_n_pending: "{n} pending",
      cc_title: "System Status",
      cc_desc:
        "Real-time status of PaperForge core modules. Modules with a pending action need your attention.",
      cc_zone_attention: "Needs Attention",
      cc_zone_modules: "All Modules",
      cc_module_installation: "Installation",
      cc_module_help: "Help & Docs",
      cc_module_library: "Library Index",
      cc_module_ocr: "OCR Engine",
      cc_module_memory: "Memory Layer",
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
      cc_reason_ocr_ready: "OCR pipeline is configured and functional.",
      cc_reason_ocr_config_missing:
        "Configuration not found \u2014 run setup to configure OCR.",
      cc_reason_ocr_config_corrupt:
        "Configuration file is corrupt \u2014 OCR cannot proceed.",
      cc_reason_ocr_api_key_missing:
        "No OCR API key configured \u2014 add one in setup.",
      cc_reason_ocr_artifacts_missing:
        "No OCR output found \u2014 run OCR on papers.",
      cc_reason_memory_ready: "Memory database is healthy and indexed.",
      cc_reason_memory_db_missing:
        "Memory database not built \u2014 run memory build.",
      cc_reason_memory_db_corrupt:
        "Memory database is corrupted \u2014 restore from backup.",
      cc_reason_memory_index_stale:
        "Memory index needs rebuild to match current library.",
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
      prep_key: "PaddleOCR Key",
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
      md_select_installation: "\u5B89\u88C5",
      md_select_library: "\u6587\u732E\u5E93",
      md_select_ocr: "OCR",
      md_select_memory: "\u8BB0\u5FC6\u5C42",
      installation_detail_heading: "\u5B89\u88C5\u8BE6\u60C5",
      btn_back_to_overview: "\u2190 \u8FD4\u56DE\u6982\u89C8",
      agent_integration_section: "Agent \u96C6\u6210",
      module_detail_open_installation: "\u6253\u5F00\u5B89\u88C5",
      module_detail_open_help: "\u5E2E\u52A9\u4E0E\u6587\u6863",
      module_detail_open_maintenance: "\u7EF4\u62A4",
      module_detail_open_library: "\u6253\u5F00\u6587\u732E\u5E93",
      module_detail_open_ocr: "\u6253\u5F00 OCR",
      module_detail_open_memory: "\u6253\u5F00\u8BB0\u5FC6",
      action_unknown_pair: "\u672A\u77E5\u64CD\u4F5C: {verb}",
      ocr_stop_batch: "\u505C\u6B62 OCR \u6279\u5904\u7406",
      runtime_not_available: "Python \u8FD0\u884C\u65F6\u4E0D\u53EF\u7528",
      md_unavailable_module: "\u6682\u4E0D\u53EF\u7528",
      library_detail_heading: "\u6587\u732E\u5E93\u8BE6\u60C5",
      ocr_detail_heading: "OCR \u8BE6\u60C5",
      memory_detail_heading: "\u8BB0\u5FC6\u5C42\u8BE6\u60C5",
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
      cc_summary_ok: "\u5168\u90E8\u6B63\u5E38",
      cc_summary_core_ok:
        "\u6838\u5FC3\u73AF\u5883\u6B63\u5E38\uFF1B{n} \u4E2A\u6A21\u5757\u72B6\u6001\u68C0\u6D4B\u5F85\u63A5\u5165",
      cc_badge_ok: "\u5DF2\u5C31\u7EEA",
      cc_badge_pending: "\u5F85\u63A5\u5165",
      cc_badge_setup: "\u9700\u8981\u5B89\u88C5",
      cc_badge_attention: "\u9700\u8981\u6CE8\u610F",
      cc_diagnostic_toggle: "\u8BE6\u60C5",
      cc_n_ready: "{n} \u5DF2\u5C31\u7EEA",
      cc_n_pending: "{n} \u5F85\u63A5\u5165",
      cc_title: "\u7CFB\u7EDF\u72B6\u6001",
      cc_desc:
        "PaperForge \u6838\u5FC3\u6A21\u5757\u7684\u5B9E\u65F6\u72B6\u6001\u3002\u6709\u5F85\u5904\u7406\u64CD\u4F5C\u7684\u6A21\u5757\u9700\u8981\u60A8\u7684\u5173\u6CE8\u3002",
      cc_zone_attention: "\u9700\u8981\u5173\u6CE8",
      cc_zone_modules: "\u6240\u6709\u6A21\u5757",
      cc_module_installation: "\u5B89\u88C5",
      cc_module_help: "\u5E2E\u52A9\u4E0E\u6587\u6863",
      cc_module_library: "\u6587\u732E\u7D22\u5F15",
      cc_module_ocr: "OCR \u5F15\u64CE",
      cc_module_memory: "\u8BB0\u5FC6\u5C42",
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
      cc_diag_module: "\u6A21\u5757",
      cc_diag_state: "\u72B6\u6001",
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
    },
  },
  vt = null;
function Rr(p) {
  try {
    let d = p.vault;
    if (typeof d.getConfig == "function") {
      let e = d.getConfig("language");
      if (e && String(e).startsWith("zh")) return "zh";
    }
  } catch (d) {}
  try {
    if (typeof localStorage != "undefined") {
      let d = localStorage.getItem("language");
      if (d && String(d).startsWith("zh")) return "zh";
    }
  } catch (d) {}
  return "en";
}
function Kt(p) {
  vt = Rr(p) === "zh" ? bt.zh : bt.en;
}
function o(p) {
  return (vt && vt[p]) || bt.en[p] || p;
}
var R = require("obsidian"),
  q = $(require("fs")),
  re = $(require("path")),
  fr = $(require("os")),
  Y = require("child_process");
var hr = $(Et());
var me = $(require("fs")),
  ge = $(require("path")),
  qt = $(require("os")),
  ve = require("child_process");
var Ar = {
  ocr: ["PADDLEOCR_API_KEY", "PADDLEOCR_API_TOKEN"],
  memory: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
  embed: ["VECTOR_DB_API_KEY", "VECTOR_DB_API_BASE", "VECTOR_DB_API_MODEL"],
};
async function Ke(p, d) {
  if (!Ar[d]) return {};
  let t = p.app.secretStorage,
    r = {};
  if (d === "ocr") {
    let n = await t.getSecret("paddleocr-api-key");
    n && ((r.PADDLEOCR_API_KEY = n), (r.PADDLEOCR_API_TOKEN = n));
  } else if (d === "memory" || d === "embed") {
    let n = await t.getSecret("vector-db-api-key");
    n && (r.VECTOR_DB_API_KEY = n);
  }
  return r;
}
var Fr = ["PADDLEOCR_", "VECTOR_DB_", "OPENAI_"];
function Ut(p) {
  let d = {};
  for (let [e, t] of Object.entries(p))
    Fr.some((r) => e.startsWith(r)) || (d[e] = t);
  return d;
}
var xt = null,
  Wt = !1;
function K(p, d, e, t) {
  let r = e || me,
    n = t || ve.execFileSync;
  if (d && d.python_path && d.python_path.trim()) {
    let i = d.python_path.trim();
    if (r.existsSync(i)) return { path: i, source: "manual", extraArgs: [] };
  }
  let s = [
    ge.join(p, ".paperforge-test-venv", "Scripts", "python.exe"),
    ge.join(p, ".venv", "Scripts", "python.exe"),
    ge.join(p, "venv", "Scripts", "python.exe"),
  ];
  for (let i of s)
    try {
      if (r.existsSync(i))
        return { path: i, source: "auto-detected", extraArgs: [] };
    } catch (l) {}
  let a = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let i of a)
    try {
      let l = n(i.path, [...i.extraArgs, "--version"], {
        encoding: "utf-8",
        timeout: 5e3,
        windowsHide: !0,
      });
      if (l && l.toLowerCase().includes("python"))
        return {
          path: i.path,
          source: "auto-detected",
          extraArgs: i.extraArgs,
        };
    } catch (l) {}
  return { path: "python", source: "auto-detected", extraArgs: [] };
}
function Zt(p, d, e, t, r) {
  t === void 0 && (t = 1e4);
  let n = r || ve.execFile;
  return new Promise((s) => {
    n(
      p,
      ["-c", "import paperforge; print(paperforge.__version__)"],
      { cwd: e, timeout: t },
      (a, i) => {
        if (a) {
          s({
            status: "not-installed",
            pyVersion: null,
            pluginVersion: d,
            error: a.message,
          });
          return;
        }
        let l = (i && i.trim()) || null;
        s(
          l === d
            ? { status: "match", pyVersion: l, pluginVersion: d, error: null }
            : {
                status: "mismatch",
                pyVersion: l,
                pluginVersion: d,
                error: null,
              }
        );
      }
    );
  });
}
function kt(p) {
  let d = String(p),
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
    }[d];
  return t
    ? { ...t }
    : { type: "unknown", message: String(p), recoverable: !1 };
}
function Gt(p, d, e) {
  e === void 0 && (e = []);
  let t = `paperforge==${d}`,
    r = `git+https://github.com/LLLin000/PaperForge.git@${d}`,
    n = [...e, "-m", "pip", "install", "--upgrade", t],
    s = [...e, "-m", "pip", "install", "--upgrade", r];
  return { cmd: p, url: r, args: s, pypiArgs: n, gitArgs: s, timeout: 12e4 };
}
function Jt(p, d, e, t, r, n) {
  let s = r || ve.spawn;
  return new Promise((a) => {
    let i = Date.now(),
      l = { cwd: e, timeout: t, windowsHide: !0 };
    n && (l.env = n);
    let c = s(p, d, l),
      u = [],
      f = [];
    (c.stdout.on("data", (_) => {
      u.push(_.toString("utf-8"));
    }),
      c.stderr.on("data", (_) => {
        f.push(_.toString("utf-8"));
      }),
      c.on("close", (_) => {
        a({
          stdout: u.join(""),
          stderr: f.join(""),
          exitCode: _,
          elapsed: Date.now() - i,
        });
      }),
      c.on("error", (_) => {
        a({
          stdout: u.join(""),
          stderr:
            f.join("") +
            `
` +
            _.message,
          exitCode: -1,
          elapsed: Date.now() - i,
        });
      }));
  });
}
function wt() {
  if (Wt) return xt;
  Wt = !0;
  try {
    let p;
    if (process.platform === "win32") {
      let d = process.env.ComSpec || "C:\\Windows\\System32\\cmd.exe";
      p = (0, ve.execFileSync)(d, ["/c", "where", "git"], {
        timeout: 5e3,
        windowsHide: !0,
        encoding: "utf-8",
      });
    } else
      p = (0, ve.execFileSync)("which", ["git"], {
        timeout: 5e3,
        encoding: "utf-8",
      });
    if (p) {
      let d = p
        .split(
          `
`
        )[0]
        .trim();
      d && (xt = ge.dirname(d));
    }
  } catch (p) {}
  return xt;
}
function pe() {
  let p = { ...process.env },
    d = process.platform,
    e = qt.homedir(),
    t = [],
    r = wt();
  (r && t.push(r),
    d === "darwin"
      ? t.push(
          "/opt/homebrew/bin",
          "/usr/local/bin",
          "/usr/bin",
          `${e}/.local/bin`
        )
      : d === "linux" &&
        t.push("/usr/local/bin", "/usr/bin", `${e}/.local/bin`));
  let n = p.PATH || "";
  return ((p.PATH = [...t, n].filter(Boolean).join(ge.delimiter)), Ut(p));
}
async function ye(p, d) {
  let e = await Ke(p, d),
    t = pe();
  return Object.keys(e).length === 0 ? t : Object.assign({}, t, e);
}
function Yt(p) {
  return String(p)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "")
    .includes("betterbibtex");
}
function St(p) {
  if (!p) return !1;
  try {
    if (!me.existsSync(p)) return !1;
    for (let d of me.readdirSync(p)) if (Yt(d)) return !0;
  } catch (d) {}
  return !1;
}
function et(p) {
  if (!p) return !1;
  try {
    if (!me.existsSync(p)) return !1;
    for (let d of me.readdirSync(p)) {
      let e = ge.join(p, d, "extensions");
      try {
        if (!me.existsSync(e)) continue;
        for (let t of me.readdirSync(e)) if (Yt(t)) return !0;
      } catch (t) {}
    }
  } catch (d) {}
  return !1;
}
var ke = $(require("fs")),
  W = $(require("path")),
  Pt = require("child_process"),
  be = null;
function Dr(p, d) {
  let e = d || ke,
    t = W.join(p, "paperforge.json"),
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
      a = s.vault_config || {};
    return {
      system_dir: a.system_dir || s.system_dir || r.system_dir,
      resources_dir: a.resources_dir || s.resources_dir || r.resources_dir,
      literature_dir: a.literature_dir || s.literature_dir || r.literature_dir,
      base_dir: a.base_dir || s.base_dir || r.base_dir,
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
function ue(p, d) {
  let e = Dr(p, d),
    t = W.join(p, e.system_dir, "PaperForge");
  return {
    vault: p,
    systemDir: t,
    indexesDir: W.join(t, "indexes"),
    logsDir: W.join(t, "logs"),
    dbPath: W.join(t, "indexes", "paperforge.db"),
    memoryStatePath: W.join(t, "indexes", "memory-runtime-state.json"),
    vectorStatePath: W.join(t, "indexes", "vector-runtime-state.json"),
    healthStatePath: W.join(t, "indexes", "runtime-health.json"),
    buildStatePath: W.join(t, "indexes", "vector-build-state.json"),
    orphanStatePath: W.join(t, "indexes", "sync-orphan-state.json"),
    exportsDir: W.join(t, "exports"),
    ocrDir: W.join(t, "ocr"),
    pluginDataPath: W.join(
      p,
      ".obsidian",
      "plugins",
      "paperforge",
      "data.json"
    ),
    pfJsonPath: W.join(p, "paperforge.json"),
    configWarning: e._warning,
  };
}
function Ct(p) {
  try {
    return ke.existsSync(p) ? JSON.parse(ke.readFileSync(p, "utf-8")) : null;
  } catch (d) {
    return null;
  }
}
function Or(p) {
  let d = ue(p);
  return Ct(d.memoryStatePath);
}
var Oe = null;
function tt(p) {
  let d = ue(p),
    e = Date.now();
  if (Oe && Oe.vaultPath === p && e - Oe.ts < 2e3) return Oe.result;
  let t = "",
    r = [
      W.join(p, ".paperforge-test-venv", "Scripts", "python.exe"),
      W.join(p, ".venv", "Scripts", "python.exe"),
      W.join(p, "venv", "Scripts", "python.exe"),
    ];
  for (let s = 0; s < r.length; s++)
    if (ke.existsSync(r[s])) {
      t = r[s];
      break;
    }
  if (t)
    try {
      let s = (0, Pt.execFileSync)(
          t,
          ["-m", "paperforge", "--vault", p, "embed", "status", "--json"],
          { encoding: "utf-8", timeout: 1e4, windowsHide: !0 }
        ),
        a = JSON.parse(s);
      if (a.ok && a.data) {
        let i = a.data;
        return ((Oe = { vaultPath: p, result: i, ts: e }), i);
      }
    } catch (s) {}
  let n = Ct(d.vectorStatePath);
  return ((Oe = { vaultPath: p, result: n, ts: e }), n);
}
function Ue(p) {
  let d = ue(p);
  return Ct(d.healthStatePath);
}
function Xt(p) {
  var e;
  let d = Ue(p);
  return !!(d && ((e = d.summary) == null ? void 0 : e.status) === "ok");
}
function rt(p) {
  let d = Or(p);
  return !d || d.paper_count_db === 0
    ? "DB not found. Run paperforge memory build."
    : "Papers: " + d.paper_count_db + " | " + (d.fresh ? "fresh" : "stale");
}
function Me(p) {
  var t, r, n;
  let d = tt(p);
  return d
    ? d.healthy === !1
      ? "Vector index unreadable - rebuild required"
      : "Chunks: " +
        (((t = d.chunk_count) != null ? t : 0) +
          ((r = d.body_chunk_count) != null ? r : 0) +
          ((n = d.object_chunk_count) != null ? n : 0)) +
        " | " +
        d.model +
        " | " +
        d.mode
    : "Status unavailable";
}
function we(p, d) {
  if (be) return be;
  if (d && d.python_path && d.python_path.trim()) {
    let r = d.python_path.trim();
    if (ke.existsSync(r))
      return ((be = { path: r, source: "manual", extraArgs: [] }), be);
  }
  let e = [
    W.join(p, ".paperforge-test-venv", "Scripts", "python.exe"),
    W.join(p, ".venv", "Scripts", "python.exe"),
    W.join(p, "venv", "Scripts", "python.exe"),
  ];
  for (let r = 0; r < e.length; r++)
    if (ke.existsSync(e[r]))
      return (
        (be = { path: e[r], source: "auto-detected", extraArgs: [] }),
        be
      );
  let t = [
    { path: "py", extraArgs: ["-3"] },
    { path: "python", extraArgs: [] },
    { path: "python3", extraArgs: [] },
  ];
  for (let r = 0; r < t.length; r++)
    try {
      let n = t[r],
        s = (0, Pt.execFileSync)(n.path, n.extraArgs.concat(["--version"]), {
          encoding: "utf-8",
          timeout: 5e3,
          windowsHide: !0,
        });
      if (s && s.toLowerCase().indexOf("python") !== -1)
        return (
          (be = {
            path: n.path,
            source: "auto-detected",
            extraArgs: n.extraArgs,
          }),
          be
        );
    } catch (n) {}
  return (
    (be = { path: "python", source: "auto-detected", extraArgs: [] }),
    be
  );
}
var te = require("obsidian"),
  _e = $(require("fs")),
  er = $(require("path")),
  tr = $(require("https")),
  qe = require("child_process");
function Qt(p, d) {
  return !d || !d.trim()
    ? { blocked: !0, reason: "zotero" }
    : p
      ? { blocked: !1 }
      : { blocked: !0, reason: "ocr" };
}
var Rt = class extends te.Modal {
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
      o("orphan_delete_selected").replace("{count}", String(e.length))
    ),
      this._selectAllBtn.setText(
        e.length === this.orphans.length
          ? o("orphan_deselect_all")
          : o("orphan_select_all")
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
        text: o("orphan_title").replace("{count}", String(this.orphans.length)),
      }),
      e.createEl("p", { cls: "paperforge-modal-desc", text: o("orphan_desc") }),
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
        i = a.createEl("div", { cls: "paperforge-orphan-header" });
      i.createEl("span", {
        cls: "paperforge-orphan-key",
        text: n.citation_key || n.key,
      });
      let l = i.createEl("span", { cls: "paperforge-orphan-tags" });
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
          a.createEl("div", { cls: "paperforge-orphan-title", text: n.title }));
      let c = [];
      (n.authors && c.push(n.authors),
        n.year && c.push(n.year),
        c.length > 0 &&
          a.createEl("div", {
            cls: "paperforge-orphan-meta",
            text: c.join(" \xB7 "),
          }),
        a.createEl("div", {
          cls: "paperforge-orphan-explain",
          text: o("orphan_explain"),
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
          new te.Notice(o("orphan_none_selected"));
          return;
        }
        if (
          (this._countEl.setText("Deleting..."),
          this._countEl.setAttr("disabled", ""),
          this._selectAllBtn.setAttr("disabled", ""),
          !this.py || !this.py.path)
        ) {
          (new te.Notice("PaperForge: Python not found"), this.close());
          return;
        }
        let s = n.map((a) => a.key);
        (0, qe.execFile)(
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
          (a, i) => {
            if (a) {
              (new te.Notice("PaperForge: prune failed"), this.close());
              return;
            }
            try {
              let l = JSON.parse(i),
                c = (l.data && l.data.deleted) || [];
              new te.Notice("Deleted " + c.length + " orphan workspace(s)");
            } catch (l) {
              new te.Notice("PaperForge: prune done");
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
function st(p, d, e) {
  console.log("[PF] checkOrphanState called");
  try {
    let r = ue(e).orphanStatePath;
    if (!_e.existsSync(r)) {
      console.log("[PF] orphan file NOT FOUND");
      return;
    }
    console.log("[PF] orphan file FOUND");
    let n = _e.readFileSync(r, "utf-8"),
      a = JSON.parse(n).orphans || [];
    if ((console.log("[PF] orphans count:", a.length), a.length === 0)) return;
    let i = we(e, d.settings);
    (console.log("[PF] py.path:", i ? i.path : "null"),
      new Rt(p, a, e, i).open(),
      _e.unlinkSync(r),
      console.log("[PF] orphan file cleaned"));
  } catch (t) {
    console.log("[PF] checkOrphanState exception:", t.message || t);
  }
}
var Ae = class extends te.Modal {
  constructor(e, t, r) {
    super(e);
    this._pendingSave = null;
    this._showSkipConfirm = !1;
    ((this.plugin = t), (this._step = 1), (this._onComplete = r));
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
        o("wizard_step1"),
        o("wizard_step2"),
        o("wizard_step3"),
        o("wizard_step4"),
        o("wizard_step5"),
      ],
      t = this.contentEl.createEl("div", { cls: "paperforge-step-bar" });
    e.forEach((r, n) => {
      let s = n + 1,
        a = t.createEl("div", {
          cls: `paperforge-step-dot ${s === this._step ? "active" : ""} ${s < this._step ? "done" : ""}`,
        });
      (a.createEl("span", { cls: "paperforge-step-num", text: `${s}` }),
        a.createEl("span", { cls: "paperforge-step-label", text: r }));
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
        .createEl("button", { cls: "paperforge-step-btn", text: o("nav_prev") })
        .addEventListener("click", () => {
          (this._step--, (this._showSkipConfirm = !1), this._render());
        }),
      this._step < 5
        ? e
            .createEl("button", {
              cls: "paperforge-step-btn mod-cta",
              text: o("nav_next"),
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
              text: o("nav_close"),
            })
            .addEventListener("click", () => this.close()));
  }
  _validateStep3() {
    let e = this.plugin.settings,
      t = Qt(this._apiKeyValidated, e.zotero_data_dir);
    if (t.reason === "ocr") return t;
    let r = (e.zotero_data_dir || "").trim();
    if (!r)
      return (
        new te.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E3A\u5FC5\u586B\u9879\uFF0C\u8BF7\u586B\u5199\u8DEF\u5F84"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!_e.existsSync(r))
      return (
        new te.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u5B58\u5728"
        ),
        { blocked: !0, reason: "zotero" }
      );
    if (!_e.statSync(r).isDirectory())
      return (
        new te.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u8DEF\u5F84\u4E0D\u662F\u4E00\u4E2A\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" }
      );
    let n = er.join(r, "storage");
    return !_e.existsSync(n) || !_e.statSync(n).isDirectory()
      ? (new te.Notice(
          "Zotero \u6570\u636E\u76EE\u5F55\u4E2D\u672A\u627E\u5230 storage/ \u5B50\u76EE\u5F55"
        ),
        { blocked: !0, reason: "zotero" })
      : { blocked: !1 };
  }
  _stepOverview(e) {
    (e.createEl("h2", { text: o("wizard_title") }),
      e.createEl("p", { text: o("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath,
      n = e.createEl("div", { cls: "paperforge-dir-tree" }),
      s = n.createEl("div", { cls: "paperforge-dir-node root" });
    s.textContent = `\u{1F4C1} Vault (${r})`;
    let a = n.createEl("div", { cls: "paperforge-dir-children" }),
      i = a.createEl("div", { cls: "paperforge-dir-node folder" });
    ((i.textContent = `\u{1F4C1} ${t.resources_dir || "Resources"}/ \u2014 \u6587\u732E\u5361\u7247\u76EE\u5F55\uFF08Base \u6570\u636E\u6765\u6E90\uFF09`),
      i
        .createEl("div", { cls: "paperforge-dir-children" })
        .createEl("div", {
          cls: "paperforge-dir-node file",
          text: `\u{1F4C1} ${t.literature_dir || "Literature"}/ \u2014 \u6587\u732E\u5361\u7247`,
        }),
      a.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.base_dir || "Bases"}/ \u2014 \u6570\u636E\u7BA1\u7406\u9762\u677F`,
      }),
      a.createEl("div", {
        cls: "paperforge-dir-node folder",
        text: `\u{1F4C1} ${t.system_dir || "System"}/ \u2014 Zotero \u8F6F\u94FE\u63A5 + PaperForge \u7CFB\u7EDF\u6587\u4EF6\u5939`,
      }),
      e.createEl("p", {
        text: o("wizard_preview"),
        cls: "paperforge-modal-hint",
      }),
      e.createEl("p", {
        text: o("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let c = e.createEl("div", { cls: "paperforge-summary" }),
      u = [
        {
          label: o("dir_resources"),
          val: `${r}/${t.resources_dir || "Resources"}`,
        },
        {
          label: o("dir_notes"),
          val: `${r}/${t.resources_dir || "Resources"}/${t.literature_dir || "Literature"}`,
        },
        { label: o("dir_base"), val: `${r}/${t.base_dir || "Bases"}` },
        { label: o("dir_system"), val: `${r}/${t.system_dir || "System"}` },
      ];
    for (let f of u) {
      let _ = c.createEl("div", { cls: "paperforge-summary-row" });
      (_.createEl("span", { cls: "paperforge-summary-label", text: f.label }),
        _.createEl("span", { cls: "paperforge-summary-value", text: f.val }));
    }
  }
  _stepDirectories(e) {
    (e.createEl("h2", { text: o("wizard_step2") }),
      e.createEl("p", { text: o("wizard_intro") }));
    let t = this.plugin.settings,
      r = this.app.vault.adapter.basePath;
    (this._modalField(e, o("dir_vault"), r, !0),
      e.createEl("p", {
        text: o("wizard_dir_hint"),
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
        text: o("wizard_dir_sub_hint"),
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
        text: o("wizard_sys_hint"),
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
        text: o("wizard_safety"),
        cls: "paperforge-modal-hint",
      }));
    let n = e.createEl("div", { cls: "paperforge-summary" }),
      s = [
        { label: o("dir_resources"), val: `${r}/${t.resources_dir || ""}` },
        {
          label: o("dir_notes"),
          val: `${r}/${t.resources_dir || ""}/${t.literature_dir || ""}`,
        },
        { label: o("dir_system"), val: `${r}/${t.system_dir || ""}` },
        { label: o("dir_base"), val: `${r}/${t.base_dir || ""}` },
      ];
    for (let a of s) {
      let i = n.createEl("div", { cls: "paperforge-summary-row" });
      (i.createEl("span", { cls: "paperforge-summary-label", text: a.label }),
        i.createEl("span", { cls: "paperforge-summary-value", text: a.val }));
    }
  }
  _stepKeys(e) {
    if (
      (e.createEl("h2", { text: o("wizard_step3") }), this._showSkipConfirm)
    ) {
      this._renderSkipConfirm(e);
      return;
    }
    let t = this.plugin.settings;
    e.createEl("p", {
      text: o("wizard_agent_hint"),
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
      text: o("label_agent"),
    });
    let s = n.createEl("select", { cls: "paperforge-modal-select" });
    for (let _ of r) {
      let h = s.createEl("option", { text: _.name, attr: { value: _.key } });
      _.key === (t.agent_platform || "opencode") && (h.selected = !0);
    }
    (s.addEventListener("change", () => {
      ((t.agent_platform = s.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    }),
      e.createEl("p", {
        text: o("wizard_keys_hint"),
        cls: "paperforge-modal-hint",
      }));
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_paddleocr"),
    });
    let i = a.createEl("input", {
        cls: "paperforge-modal-input",
        attr: { type: "password", placeholder: "API Key" },
      }),
      l = this.plugin.settings._paddleocr_configured || !1;
    ((i.placeholder = l
      ? "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (stored securely)"
      : "API Key"),
      (i.value = ""),
      (this._apiKeyValidated = !1),
      (this._apiKeyStatus = a.createEl("span", {
        cls: "paperforge-apikey-status",
        text: "",
      })));
    let c = a.createEl("button", {
      cls: "paperforge-step-btn",
      text: "\u9A8C\u8BC1",
    });
    (c.addEventListener("click", () => this._validateApiKey(i.value, c)),
      i.addEventListener("input", () => {
        ((this._apiKeyValidated = !1),
          (this._apiKeyStatus.textContent = ""),
          (this._apiKeyStatus.className = "paperforge-apikey-status"));
      }),
      this._pendingSave && clearTimeout(this._pendingSave),
      (this._pendingSave = setTimeout(() => {
        (this.plugin.saveSettings(), (this._pendingSave = null));
      }, 500)),
      e.createEl("p", {
        text: o("wizard_api_hint_skip"),
        cls: "paperforge-modal-hint",
      }));
    let u = e.createEl("div", { cls: "paperforge-modal-field" });
    u.createEl("label", {
      cls: "paperforge-modal-label",
      text: o("field_zotero_data"),
    });
    let f = u.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: o("field_zotero_placeholder") },
    });
    ((f.value = t.zotero_data_dir || ""),
      f.addEventListener("input", () => {
        ((t.zotero_data_dir = f.value),
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
      s = tr.request(n, async (a) => {
        ((t.disabled = !1), (t.textContent = "\u9A8C\u8BC1"));
        let i = "";
        (a.on("data", (l) => (i += l)),
          a.on("end", async () => {
            var l, c;
            try {
              let u = JSON.parse(i);
              if (a.statusCode === 400 && u.code === 10001) {
                let f = this.app.secretStorage;
                try {
                  if (
                    (await ((l = f == null ? void 0 : f.setSecret) == null
                      ? void 0
                      : l.call(f, "paddleocr-api-key", e)),
                    (await ((c = f == null ? void 0 : f.getSecret) == null
                      ? void 0
                      : c.call(f, "paddleocr-api-key"))) === e)
                  ) {
                    let h = this.plugin.settings;
                    ((h._paddleocr_configured = !0),
                      (h.paddleocr_api_key = ""),
                      this.plugin.saveSettings());
                  }
                } catch (_) {}
                ((this._apiKeyStatus.textContent =
                  "\u2713 \u5BC6\u94A5\u6709\u6548"),
                  (this._apiKeyStatus.className =
                    "paperforge-apikey-status ok"),
                  (this._apiKeyValidated = !0));
              } else
                a.statusCode === 401
                  ? ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u5BC6\u94A5\u65E0\u6548\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
                    (this._apiKeyStatus.className =
                      "paperforge-apikey-status error"),
                    (this._apiKeyValidated = !1))
                  : ((this._apiKeyStatus.textContent =
                      "\u9A8C\u8BC1\u5931\u8D25\uFF1AAPI \u8FD4\u56DE " +
                      a.statusCode +
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
    (s.on("error", (a) => {
      ((t.disabled = !1),
        (t.textContent = "\u9A8C\u8BC1"),
        (this._apiKeyStatus.textContent =
          "\u9A8C\u8BC1\u5931\u8D25\uFF1A\u65E0\u6CD5\u8FDE\u63A5 (" +
          a.message +
          ")\u3002\u53EF\u70B9\u4E0B\u4E00\u6B65\u8DF3\u8FC7\uFF0C\u7B49\u4F1A\u513F\u518D\u914D\u7F6E\u3002"),
        (this._apiKeyStatus.className = "paperforge-apikey-status error"),
        (this._apiKeyValidated = !1));
    }),
      s.write(r),
      s.end());
  }
  _renderSkipConfirm(e) {
    e.createEl("p", {
      text: o("wizard_skip_ocr_desc"),
      cls: "paperforge-modal-desc",
    });
    let t = e.createEl("div", { cls: "paperforge-modal-actions" });
    (t
      .createEl("button", {
        cls: "paperforge-step-btn mod-cta",
        text: o("wizard_skip_ocr_continue"),
      })
      .addEventListener("click", () => {
        ((this._showSkipConfirm = !1), this._step++, this._render());
      }),
      t
        .createEl("button", {
          cls: "paperforge-step-btn",
          text: o("wizard_skip_ocr_back"),
        })
        .addEventListener("click", () => {
          ((this._showSkipConfirm = !1), this._render());
        }));
  }
  _modalField(e, t, r, n) {
    let s = e.createEl("div", { cls: "paperforge-modal-field" });
    s.createEl("label", { cls: "paperforge-modal-label", text: t });
    let a = s.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text" },
    });
    ((a.value = r), (a.disabled = !!n));
  }
  _modalInput(e, t, r, n, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "text", placeholder: s || "" },
    });
    i.value = n;
    let l = this.plugin.settings;
    i.addEventListener("input", () => {
      ((l[r] = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _modalSecret(e, t, r, n, s) {
    let a = e.createEl("div", { cls: "paperforge-modal-field" });
    a.createEl("label", { cls: "paperforge-modal-label", text: t });
    let i = a.createEl("input", {
      cls: "paperforge-modal-input",
      attr: { type: "password", placeholder: s || "" },
    });
    i.value = n;
    let l = this.plugin.settings;
    i.addEventListener("input", () => {
      ((l[r] = i.value),
        this._pendingSave && clearTimeout(this._pendingSave),
        (this._pendingSave = setTimeout(() => {
          (this.plugin.saveSettings(), (this._pendingSave = null));
        }, 500)));
    });
  }
  _stepInstall(e) {
    (e.createEl("h2", { text: o("wizard_step4") }),
      (this._installLog = e.createEl("div", {
        cls: "paperforge-install-log",
      })));
    let t = e.createEl("button", {
      cls: "paperforge-step-btn mod-cta",
      text: o("install_btn"),
    });
    t.addEventListener("click", () => this._runInstall(t));
  }
  async _runInstall(e) {
    var a, i, l, c, u, f;
    ((e.disabled = !0),
      (e.textContent = o("install_btn_running")),
      this._installLog.setText(
        o("install_validating") +
          `
`
      ),
      this._log(o("install_validating")));
    let t = this.plugin.settings,
      r = this._validate();
    if (r.length > 0) {
      (this._log(o("validate_fail") + ":"),
        r.forEach((_) => this._log("  \u2717 " + _)),
        (e.disabled = !1),
        (e.textContent = o("install_btn_retry")));
      return;
    }
    let n = (_, h = {}) =>
        new Promise((m, E) => {
          let { path: y, extraArgs: g = [] } = K(
              t.vault_path.trim(),
              this.plugin.settings,
              void 0,
              void 0
            ),
            v = (0, qe.spawn)(y, [...g, ..._], {
              cwd: t.vault_path.trim(),
              env: pe(),
              timeout: 12e4,
              ...h,
            }),
            w = "",
            b = "";
          (v.stdout.on("data", (x) => {
            let C = x.toString("utf-8");
            ((w += C), h.logStdout && this._processSetupOutput(C));
          }),
            v.stderr.on("data", (x) => {
              let C = x.toString("utf-8");
              ((b += C), this._log("[stderr] " + C.trim()));
            }),
            v.on("close", (x) => {
              x === 0
                ? m({ stdout: w, stderr: b })
                : E(new Error(b.trim() || w.trim() || `exit code ${x}`));
            }),
            v.on("error", (x) => E(x)));
        }),
      s = [
        "-m",
        "paperforge",
        "--vault",
        t.vault_path.trim(),
        "setup",
        "--headless",
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
      s.push("--zotero-data", t.zotero_data_dir.trim());
    try {
      let _ = !0;
      try {
        await n(["-c", "import paperforge"]);
      } catch (h) {
        _ = !1;
      }
      if (!_) {
        this._log(o("install_bootstrapping"));
        let h = this.plugin.manifest.version;
        this._log(`[install] Trying PyPI: pip install paperforge==${h}`);
        let m = ["-m", "pip", "install", "--upgrade"];
        (process.platform !== "win32" && m.push("--user"),
          m.push(`paperforge==${h}`));
        try {
          await n(m, { logStdout: !0 });
        } catch (E) {
          (this._log(
            `[install] PyPI failed, falling back to git: git+https://...@v${h}`
          ),
            console.warn(
              "[PaperForge] PyPI install failed, falling back to git:",
              (a = E.message) == null ? void 0 : a.slice(0, 200)
            ));
          let y = ["-m", "pip", "install", "--upgrade"];
          (process.platform !== "win32" && y.push("--user"),
            y.push(`git+https://github.com/LLLin000/PaperForge.git@v${h}`),
            await n(y, { logStdout: !0 }));
        }
      }
      (await n(s, { logStdout: !0, env: pe() }),
        this._log(o("install_complete")),
        await this.plugin.saveSettings(),
        this._onComplete && this._onComplete(),
        setTimeout(() => {
          ((this._step = 5), this._render());
        }, 800));
    } catch (_) {
      console.error("PaperForge setup failed:", _.message);
      let h = this._formatSetupError(_.message);
      this._log(o("install_failed") + h);
      let m =
        (i = this._installLog.parentElement) == null
          ? void 0
          : i.createEl("button", {
              cls: "paperforge-copy-diag-btn",
              text: o("error_copy_diagnostic") || "Copy diagnostic",
            });
      if (m) {
        let E = _.message,
          y =
            ((c = (l = this.plugin) == null ? void 0 : l.settings) == null
              ? void 0
              : c.python_path) || "auto",
          g =
            ((f = (u = this.plugin) == null ? void 0 : u.manifest) == null
              ? void 0
              : f.version) || "?",
          v = process.platform + " " + process.arch,
          w,
          b;
        try {
          w = wt() || "(not found)";
        } catch (k) {
          w = "(error)";
        }
        try {
          b = K(t.vault_path.trim(), this.plugin.settings, void 0, void 0);
        } catch (k) {
          b = null;
        }
        let x = (process.env.PATH || "").length,
          C = (process.env.PATH || "").toLowerCase().includes("git"),
          S = [
            "[PaperForge Diagnostic]",
            "Category: " + h,
            "Plugin version: " + g,
            "Python: " + y,
            "Resolved Python: " + ((b == null ? void 0 : b.path) || "?"),
            "OS: " + v,
            "Vault path: " + (t.vault_path || "?"),
            "--- Git ---",
            "Git dir (resolved): " + w,
            "PATH length: " + x + " chars",
            "PATH contains git: " + C,
            "--- Raw error ---",
            E.slice(0, 2e3),
          ].join(`
`);
        m.addEventListener("click", () => {
          navigator.clipboard
            .writeText(S)
            .then(() => {
              (m.setText(o("error_copied") || "Copied!"),
                setTimeout(() => {
                  m.setText(o("error_copy_diagnostic") || "Copy diagnostic");
                }, 3e3));
            })
            .catch(() => {
              new te.Notice("[!!] Clipboard write failed", 6e3);
            });
        });
      }
      ((e.disabled = !1), (e.textContent = o("install_btn_retry")));
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
      (!t.vault_path || !t.vault_path.trim()) && e.push(o("validate_vault")),
      (!t.resources_dir || !t.resources_dir.trim()) &&
        e.push(o("validate_resources")),
      (!t.literature_dir || !t.literature_dir.trim()) &&
        e.push(o("validate_notes")),
      (!t.base_dir || !t.base_dir.trim()) && e.push(o("validate_base")),
      this.plugin.settings._paddleocr_configured ||
        !1 ||
        this._log("  ! " + o("validate_key") + " " + o("optional_later")),
      (!t.zotero_data_dir || !t.zotero_data_dir.trim()) &&
        this._log("  ! " + o("validate_zotero") + " " + o("optional_later")),
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
    e.createEl("h2", { text: o("complete_title") });
    let t = e.createEl("div", { cls: "paperforge-summary" });
    t.createEl("div", {
      cls: "paperforge-summary-title",
      text: o("complete_summary"),
    });
    let r = this.plugin.settings,
      n = this.app.vault.adapter.basePath,
      s = [
        { label: o("dir_vault"), val: n },
        { label: o("dir_resources"), val: `${n}/${r.resources_dir}` },
        {
          label: o("dir_notes"),
          val: `${n}/${r.resources_dir}/${r.literature_dir}`,
        },
        { label: o("dir_base"), val: `${n}/${r.base_dir}` },
        { label: o("dir_system"), val: `${n}/${r.system_dir}` },
        {
          label: "API Key",
          val: this.plugin.settings._paddleocr_configured
            ? o("api_key_set")
            : o("api_key_missing"),
        },
        {
          label: o("field_zotero_data"),
          val: r.zotero_data_dir || o("not_set"),
        },
      ];
    for (let u of s) {
      let f = t.createEl("div", { cls: "paperforge-summary-row" });
      (f.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        f.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    let a = t.createEl("div", { cls: "paperforge-summary-row" });
    a.createEl("span", { cls: "paperforge-summary-label", text: "PaperForge" });
    let i = a.createEl("span", {
      cls: "paperforge-summary-value",
      text: "\u2014",
    });
    {
      let u = n,
        { path: f, extraArgs: _ = [] } = K(
          u,
          this.plugin.settings,
          void 0,
          void 0
        );
      (0, qe.execFile)(
        f,
        [..._, "-c", "import paperforge; print(paperforge.__version__)"],
        { cwd: u, timeout: 1e4 },
        (h, m) => {
          !h && m && (i.textContent = "v" + m.trim());
        }
      );
    }
    for (let u of s) {
      let f = t.createEl("div", { cls: "paperforge-summary-row" });
      (f.createEl("span", { cls: "paperforge-summary-label", text: u.label }),
        f.createEl("span", { cls: "paperforge-summary-value", text: u.val }));
    }
    e.createEl("h3", { text: o("complete_next") });
    let l = e.createEl("div", { cls: "paperforge-nextsteps" }),
      c = [
        [o("complete_step4"), o("complete_step4_desc")],
        [
          "",
          `${o("complete_export_path")} ${n}/${r.system_dir}/PaperForge/exports/`,
        ],
        [o("complete_step1"), o("complete_step1_desc")],
        [o("complete_step2"), o("complete_step2_desc")],
        [o("complete_step3"), o("complete_step3_desc")],
      ];
    for (let [u, f] of c) {
      let _ = l.createEl("div", { cls: "paperforge-nextstep-item" });
      (u && _.createEl("strong", { text: u }), _.createEl("span", { text: f }));
    }
  }
};
function rr(p, d) {
  if (d.key !== "Tab") return;
  let e = p.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (e.length === 0) return;
  let t = e[0],
    r = e[e.length - 1];
  d.shiftKey
    ? document.activeElement === t && (d.preventDefault(), r.focus())
    : document.activeElement === r && (d.preventDefault(), t.focus());
}
var nt = class extends te.Modal {
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
        let i = t.parentElement;
        if (i)
          for (let l of Array.from(i.children))
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
        s = n.createEl("button", {
          text:
            this._config.cancelLabel ||
            o("maintenance_confirm_cancel") ||
            "Cancel",
        });
      (s.addEventListener("click", () => this.close()),
        n
          .createEl("button", {
            cls: "mod-warning",
            text:
              this._config.confirmLabel ||
              o("maintenance_confirm_ok") ||
              "Proceed",
          })
          .addEventListener("click", () => {
            (this._onConfirm && this._onConfirm(), this.close());
          }),
        (this._boundKeydown = (i) => rr(e, i)),
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
  Mr = [
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
function We(p) {
  let d = {},
    e = p;
  for (let { pattern: t, label: r, class_: n } of Mr) {
    let s = 0;
    ((e = e.replace(t, () => (s++, "[REDACTED]"))),
      s > 0 &&
        (d[n] || (d[n] = { label: r, class_: n, count: 0 }),
        (d[n].count += s)));
  }
  return { clean: e, redactions: Object.values(d) };
}
function nr(p, d, e, t) {
  let r = `OCR: ${p} (${e} papers)`,
    n = [
      "## Diagnostic Summary",
      `- Reason: ${p}`,
      `- Detail: ${d}`,
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
var at = class extends te.Modal {
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
      let m = t.parentElement;
      if (m)
        for (let E of Array.from(m.children))
          E !== t &&
            !E.hasAttribute("inert") &&
            (E.setAttribute("inert", ""), this._inertedEls.push(E));
    }
    (e.createEl("h2", {
      text: o("maintenance_issue_draft_title") || "OCR Issue Draft",
    }),
      e.createEl("p", {
        cls: "paperforge-issue-draft-desc",
        text:
          o("maintenance_issue_draft_preview") ||
          "Review the issue draft below before opening GitHub.",
      }));
    let r = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    r.createEl("label", { text: "Title" });
    let n = We(this._draft.title).clean;
    this._titleInput = r.createEl("input", {
      cls: "paperforge-issue-draft-input",
      attr: { type: "text", value: n },
    });
    let s = e.createEl("div", { cls: "paperforge-issue-draft-field" });
    s.createEl("label", { text: "Body" });
    let a = We(this._draft.body).clean;
    this._bodyTextarea = s.createEl("textarea", {
      cls: "paperforge-issue-draft-textarea",
      attr: { rows: "12" },
      text: a,
    });
    let { redactions: i } = We(
        this._draft.title +
          `
` +
          this._draft.body
      ),
      l = e.createEl("div", { cls: "paperforge-issue-draft-preview" }),
      c = l.createEl("div", { cls: "paperforge-issue-draft-included" });
    (c.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (o("maintenance_issue_draft_included") || "Included") + ": ",
    }),
      c.createEl("span", {
        text: `Title, Body, Labels (${this._draft.labels.join(", ")})`,
      }));
    let u = l.createEl("div", { cls: "paperforge-issue-draft-redacted" });
    (u.createEl("span", {
      cls: "paperforge-issue-draft-preview-label",
      text: (o("maintenance_issue_draft_redacted") || "Redacted") + ": ",
    }),
      u.createEl("span", {
        text:
          "Credentials, vault/Zotero paths, paper titles, paper content are excluded" +
          (i.length > 0
            ? " (" + i.map((m) => `${m.count} ${m.label}`).join(", ") + ")"
            : ""),
      }));
    let f = e.createEl("div", { cls: "paperforge-issue-draft-actions" });
    (f
      .createEl("button", { text: o("maintenance_confirm_cancel") || "Cancel" })
      .addEventListener("click", () => this.close()),
      f
        .createEl("button", {
          cls: "mod-cta",
          text: o("maintenance_issue_draft_open_github") || "Open GitHub Issue",
        })
        .addEventListener("click", () => {
          let m = encodeURIComponent(We(this._titleInput.value).clean),
            E = encodeURIComponent(We(this._bodyTextarea.value).clean),
            y = encodeURIComponent(this._draft.labels.join(",")),
            g = `${this._githubUrl}?title=${m}&body=${E}&labels=${y}`;
          window.open(g, "_blank", "noopener,noreferrer");
        }),
      (this._boundKeydown = (m) => rr(e, m)),
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
var Be = $(require("fs")),
  it = $(require("path")),
  sr = require("child_process");
function Tt(p) {
  return p.display_action === "rebuild_result"
    ? "rebuild"
    : p.display_action === "retry_ocr" || p.display_action === "upgrade_legacy"
      ? "redo"
      : null;
}
function At(p) {
  return p === "redo";
}
function Br(p, d, e) {
  let t = { manifest: p, papers: {}, cached_at: new Date().toISOString() };
  if (e != null && e.papers)
    for (let r of Object.keys(p)) e.papers[r] && (t.papers[r] = e.papers[r]);
  for (let r of d) t.papers[r.key] = r;
  return t;
}
function ir(p) {
  return it.join(p, "System", "PaperForge", "cache", "ocr_maintenance.json");
}
function ot(p) {
  try {
    let d = ir(p),
      e = Be.readFileSync(d, "utf-8");
    return JSON.parse(e);
  } catch (d) {
    return null;
  }
}
function Ir(p, d) {
  let e = ir(p),
    t = it.dirname(e);
  (Be.mkdirSync(t, { recursive: !0 }),
    Be.writeFileSync(e, JSON.stringify(d, null, 2), "utf-8"));
}
function ar(p, d, e) {
  return new Promise((t, r) => {
    (0, sr.execFile)(p, d, e, (n, s) => {
      n ? r(n) : t(s);
    });
  });
}
async function Ft(p, d, e, t) {
  let r = await ar(d, [...e, "-m", "paperforge", "ocr", "list", "--manifest"], {
      cwd: p,
      timeout: 3e4,
    }),
    n = JSON.parse(r);
  if (t) {
    let u = Object.keys(t.manifest),
      f = Object.keys(n);
    if (
      u.length === f.length &&
      u.every((h) => t.manifest[h] === n[h]) &&
      Object.values(t.papers).every(
        (m) => typeof m.needs_derived_rebuild == "boolean"
      )
    )
      return { data: Object.values(t.papers), changed: !1 };
  }
  let s = Object.keys(n),
    a = await ar(
      d,
      [...e, "-m", "paperforge", "ocr", "list", "--json", "--keys", ...s],
      { cwd: p, timeout: 3e4 }
    ),
    i = JSON.parse(a),
    l = Br(n, i, t);
  return (Ir(p, l), { data: Object.values(l.papers), changed: !0 });
}
var Dt = $(require("fs")),
  j = $(require("path")),
  dt = require("child_process"),
  cr = $(require("os")),
  or = 300 * 1e3,
  Lr = "3.11";
function lt() {
  let p, d;
  return {
    promise: new Promise((t, r) => {
      ((p = t), (d = r));
    }),
    resolve: p,
    reject: d,
  };
}
function Nr(p) {
  let d = p.match(/Python\s+(\d+\.\d+(?:\.\d+)?)/);
  if (d) return d[1];
  let e = p.match(/Python\s+(\d+\.\d+)/);
  return e ? e[1] + ".0" : null;
}
function dr(p, d) {
  var r, n;
  let e = p.split(".").map(Number),
    t = d.split(".").map(Number);
  for (let s = 0; s < Math.max(e.length, t.length); s++) {
    let a = (r = e[s]) != null ? r : 0,
      i = (n = t[s]) != null ? n : 0;
    if (a !== i) return a - i;
  }
  return 0;
}
function Vr(p, d) {
  return dr(p, d) >= 0;
}
function Hr() {
  var p;
  return (
    process.env.FLATPAK_ID !== void 0 ||
    ((p = process.env.XDG_DATA_DIRS) != null ? p : "").includes("flatpak") ||
    !1
  );
}
function jr() {
  return process.env.SNAP !== void 0 || process.env.SNAP_NAME !== void 0 || !1;
}
function lr(p, d) {
  var t;
  return `${(t = { win32: "windows", darwin: "macos", linux: "linux" }[p]) != null ? t : p}-${d}`;
}
function pr(p, d, e) {
  if (d !== void 0 || e !== void 0) {
    if (e) return [{ verb: "stop", label: "Stop" }];
    switch (p.state) {
      case "not_installed":
        return [{ verb: "install", label: "Install Runtime" }];
      case "needs_repair": {
        let t = [{ verb: "repair", label: "Repair Runtime" }];
        return (
          p.pythonPath && t.push({ verb: "rollback", label: "Rollback" }),
          t
        );
      }
      case "ready": {
        let t = [
          { verb: "status", label: "Check Status" },
          { verb: "update", label: "Update Runtime" },
        ];
        return (
          p.previousVersion && t.push({ verb: "rollback", label: "Rollback" }),
          t
        );
      }
      case "unknown":
        return [{ verb: "retry", label: "Retry" }];
      case "unavailable":
        return [{ verb: "setup", label: "Manual Setup" }];
      default:
        return [{ verb: "retry", label: "Retry" }];
    }
  }
  switch (p.state) {
    case "not_installed":
      return [
        {
          id: "install",
          label: "Install Runtime",
          primary: !0,
          destructive: !1,
        },
      ];
    case "needs_repair": {
      let t = [
        { id: "repair", label: "Repair Runtime", primary: !0, destructive: !1 },
      ];
      return (
        p.pythonPath &&
          t.push({
            id: "rollback",
            label: "Rollback",
            primary: !1,
            destructive: !1,
          }),
        t
      );
    }
    case "ready":
      return [
        { id: "status", label: "Check Status", primary: !1, destructive: !1 },
        { id: "update", label: "Update Runtime", primary: !1, destructive: !1 },
      ];
    case "unknown":
      return [
        { id: "probe", label: "Refresh Status", primary: !0, destructive: !1 },
      ];
    case "unavailable":
      return [
        { id: "setup", label: "Manual Setup", primary: !0, destructive: !1 },
      ];
    default:
      return [
        { id: "probe", label: "Refresh Status", primary: !0, destructive: !1 },
      ];
  }
}
function ur(p) {
  return p.state !== "ready" || !p.pythonPath
    ? null
    : { command: p.pythonPath, args: [] };
}
var ct = class {
  constructor(d) {
    this._cache = null;
    this._cacheTime = 0;
    var r, n, s, a, i, l, c, u, f, _, h;
    let e =
        (n = (r = d.osPlatform) != null ? r : d.platform) != null
          ? n
          : process.platform,
      t = (a = (s = d.osArch) != null ? s : d.arch) != null ? a : process.arch;
    if (
      ((this.osPlatform = e),
      (this.osArch = t),
      (this.triplet = `${e}-${t}`),
      d.runtimeDir)
    )
      ((this.runtimeDir = d.runtimeDir),
        (this.rootDir = j.dirname(d.runtimeDir)),
        (this.pluginVersion =
          (l = (i = d.pluginVersion) != null ? i : d.version) != null
            ? l
            : "0.0.0"));
    else {
      let m = cr.homedir();
      ((this.rootDir = j.join(m, ".paperforge", "runtime")),
        (this.runtimeDir = j.join(this.rootDir, lr(e, t))),
        (this.pluginVersion =
          (u = (c = d.version) != null ? c : d.pluginVersion) != null
            ? u
            : "0.0.0"));
    }
    ((this.pointerPath = j.join(this.rootDir, "active-runtime.json")),
      (this._fs = (f = d.fs) != null ? f : Dt),
      (this._execFile = (_ = d.execFile) != null ? _ : dt.execFile),
      (this._execFileSync =
        (h = d.execFileSync) != null ? h : dt.execFileSync));
  }
  current() {
    return this._cache
      ? Date.now() - this._cacheTime > or
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
  async status(d) {
    var a;
    if (this._cache) {
      let i = Date.now() - this._cacheTime > or;
      if (!i && this._cache.state === "ready")
        return { ...this._cache, stale: !1 };
      if (i && d != null && d.allowStale) return { ...this._cache, stale: !0 };
    }
    let e = null,
      t = null,
      r = null,
      n = null,
      s = [];
    try {
      let i = this._fs.readFileSync(this.pointerPath, "utf-8"),
        l = JSON.parse(i);
      e = typeof l.version == "string" ? l.version : null;
      let c = typeof l.pythonPath == "string" ? l.pythonPath : null;
      ((t = c ? j.resolve(j.dirname(this.pointerPath), c) : null),
        (r = typeof l.previousVersion == "string" ? l.previousVersion : null),
        (n =
          typeof l.previousPythonPath == "string"
            ? l.previousPythonPath
            : null),
        (s = Array.isArray(l.warnings) ? l.warnings : []));
    } catch (i) {
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
      let i = await this._probe(t),
        l = [...s];
      return this._setCache({
        state: "ready",
        pythonPath: t,
        version: (a = i.version) != null ? a : e,
        source: "venv",
        error: null,
        lastVerifiedAt: new Date().toISOString(),
        stale: !1,
        warnings: l,
        previousVersion: r,
        previousPythonPath: n,
      });
    } catch (i) {
      let l = i instanceof Error ? i.message : String(i);
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
        warnings: s,
        previousVersion: r,
        previousPythonPath: n,
      });
    }
  }
  async ensure(d) {
    var E, y;
    let e =
        (E = d == null ? void 0 : d.version) != null ? E : this.pluginVersion,
      t = (y = d == null ? void 0 : d.force) != null ? y : !1,
      r = d == null ? void 0 : d.signal;
    if (r != null && r.aborted) return this._abortedHealth();
    if (!t) {
      let g = this.current();
      if (g.state === "ready" && !g.stale) {
        let v = await this.status();
        if (v.state === "ready") return v;
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let n;
    try {
      n = this._resolveBootstrapPython();
    } catch (g) {
      if (Hr() || jr())
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
      let v = lr(this.osPlatform, this.osArch),
        w = this.osPlatform === "darwin",
        b = ["macos-x64", "macos-arm64"],
        x = ["windows-x64", "linux-x64"];
      return w && b.includes(v)
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
    if (!Vr(n.version, Lr))
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
      let g = !1;
      try {
        let v = this._fs.readFileSync(this.pointerPath, "utf-8"),
          w = JSON.parse(v),
          b = typeof w.version == "string" ? w.version : null;
        g = b !== null && b !== e;
      } catch (v) {}
      if (g) {
        let v = j.join(this.runtimeDir, `v${e}`),
          w = j.join(v, "venv"),
          b =
            this.osPlatform === "win32"
              ? j.join(w, "Scripts", "python.exe")
              : j.join(w, "bin", "python");
        try {
          await this._probe(b, r);
        } catch (F) {
          if (F instanceof Error && F.name === "AbortError")
            return this._abortedHealth();
          let A = F instanceof Error ? F.message : String(F);
          return this._setCache({
            state: "needs_repair",
            pythonPath: b,
            version: e,
            source: "venv",
            error: {
              code: "RETAINED_SLOT_PROBE_FAILED",
              message: `Retained slot v${e} failed verification: ${A}`,
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
          C = null;
        try {
          let F = this._fs.readFileSync(this.pointerPath, "utf-8"),
            A = JSON.parse(F);
          ((x = typeof A.version == "string" ? A.version : null),
            (C = typeof A.pythonPath == "string" ? A.pythonPath : null));
        } catch (F) {}
        let S = j.dirname(this.pointerPath);
        this._fs.existsSync(S) || this._fs.mkdirSync(S, { recursive: !0 });
        let k = j.relative(j.dirname(this.pointerPath), b),
          T = JSON.stringify(
            {
              schema_version: 1,
              version: e,
              pythonPath: k,
              activatedAt: new Date().toISOString(),
              previousVersion: x,
              previousPythonPath: C,
            },
            null,
            2
          ),
          M = this.pointerPath + ".tmp";
        (this._fs.writeFileSync(M, T, "utf-8"),
          this._fs.renameSync(M, this.pointerPath));
        let B = {
          state: "ready",
          pythonPath: b,
          version: e,
          source: "venv",
          error: null,
          lastVerifiedAt: new Date().toISOString(),
          stale: !1,
          warnings: [],
          previousVersion: x,
          previousPythonPath: C,
        };
        return (
          (this._cache = B),
          (this._cacheTime = Date.now()),
          this._cleanupOldSlots(e),
          B
        );
      }
    }
    if (r != null && r.aborted) return this._abortedHealth();
    let s = t
        ? j.join(this.runtimeDir, `v${e}_build2`)
        : j.join(this.runtimeDir, `v${e}`),
      a = j.join(s, "venv"),
      i =
        this.osPlatform === "win32"
          ? j.join(a, "Scripts", "python.exe")
          : j.join(a, "bin", "python");
    try {
      this._fs.mkdirSync(s, { recursive: !0 });
      let { promise: g, reject: v, resolve: w } = lt();
      (this._execFile(
        n.path,
        ["-m", "venv", a],
        { timeout: 6e4, signal: r },
        (b) => {
          b ? v(b) : w();
        }
      ),
        await g);
    } catch (g) {
      if (g instanceof Error && g.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VENV_CREATION_FAILED", g, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: g, reject: v, resolve: w } = lt();
      (this._execFile(
        i,
        ["-m", "pip", "install", `paperforge==${e}`],
        { timeout: 12e4, signal: r },
        (b) => {
          b ? v(b) : w();
        }
      ),
        await g);
    } catch (g) {
      if (g instanceof Error && g.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "PIP_INSTALL_FAILED", g, s);
    }
    if (r != null && r.aborted) return this._abortedHealth();
    try {
      let { promise: g, reject: v, resolve: w } = lt();
      (this._execFile(
        i,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: r },
        (b) => {
          b ? v(b) : w();
        }
      ),
        await g);
    } catch (g) {
      if (g instanceof Error && g.name === "AbortError") {
        try {
          this._fs.rmSync(s, { recursive: !0, force: !0 });
        } catch (v) {}
        return this._abortedHealth();
      }
      return this._slotFailed(e, "VERIFY_FAILED", g, s);
    }
    let l = null,
      c = null;
    try {
      let g = this._fs.readFileSync(this.pointerPath, "utf-8"),
        v = JSON.parse(g);
      ((l = typeof v.version == "string" ? v.version : null),
        (c = typeof v.pythonPath == "string" ? v.pythonPath : null));
    } catch (g) {}
    let u = j.dirname(this.pointerPath);
    this._fs.existsSync(u) || this._fs.mkdirSync(u, { recursive: !0 });
    let f = j.relative(j.dirname(this.pointerPath), i),
      _ = JSON.stringify(
        {
          schema_version: 1,
          version: e,
          pythonPath: f,
          activatedAt: new Date().toISOString(),
          previousVersion: l,
          previousPythonPath: c,
        },
        null,
        2
      ),
      h = this.pointerPath + ".tmp";
    (this._fs.writeFileSync(h, _, "utf-8"),
      this._fs.renameSync(h, this.pointerPath));
    let m = {
      state: "ready",
      pythonPath: i,
      version: e,
      source: "venv",
      error: null,
      lastVerifiedAt: new Date().toISOString(),
      stale: !1,
      warnings: [],
      previousVersion: l,
      previousPythonPath: c,
    };
    return (
      (this._cache = m),
      (this._cacheTime = Date.now()),
      this._cleanupOldSlots(e),
      m
    );
  }
  _setCache(d) {
    return ((this._cache = d), (this._cacheTime = Date.now()), d);
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
  _slotFailed(d, e, t, r) {
    try {
      this._fs.rmSync(r, { recursive: !0, force: !0 });
    } catch (s) {}
    let n = t instanceof Error ? t.message : String(t);
    return this._setCache({
      state: "needs_repair",
      pythonPath: null,
      version: d,
      source: "none",
      error: { code: e, message: n, platformAction: "Retry installation" },
      lastVerifiedAt: null,
      stale: !1,
      warnings: [],
      previousVersion: null,
      previousPythonPath: null,
    });
  }
  _currentSlotExists(d) {
    let e = j.join(this.runtimeDir, `v${d}`);
    return this._fs.existsSync(e);
  }
  _resolveBootstrapPython() {
    let d = [];
    this.osPlatform === "win32"
      ? d.push(
          { path: "py", args: ["-3.11"] },
          { path: "py", args: ["-3.10"] },
          { path: "py", args: ["-3"] },
          { path: "python", args: [] }
        )
      : this.osPlatform === "darwin"
        ? d.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          )
        : d.push(
            { path: "/usr/bin/python3", args: [] },
            { path: "python3", args: [] },
            { path: "python", args: [] }
          );
    for (let e of d)
      try {
        let t = this._execFileSync(e.path, [...e.args, "--version"], {
            encoding: "utf-8",
            timeout: 5e3,
          }),
          r = Nr(t);
        if (r) return { path: e.path, version: r };
      } catch (t) {}
    throw new Error("No Python 3.11+ found on system");
  }
  _probe(d, e) {
    let { promise: t, resolve: r, reject: n } = lt();
    return (
      this._execFile(
        d,
        ["-I", "-c", "import paperforge; print(paperforge.__version__)"],
        { timeout: 3e4, signal: e },
        (s, a) => {
          if (s) n(s);
          else {
            let i = (a != null ? a : "").trim() || null;
            r({ version: i });
          }
        }
      ),
      t
    );
  }
  _cleanupOldSlots(d, e = 2) {
    try {
      let r = this._fs
        .readdirSync(this.runtimeDir, { withFileTypes: !0 })
        .filter((n) => n.isDirectory() && n.name.startsWith("v"))
        .map((n) => {
          let s = n.name.replace(/^v/, "").replace(/_build\d+$/, "");
          return { name: n.name, version: s };
        })
        .filter((n) => n.version !== d)
        .sort((n, s) => dr(s.version, n.version));
      for (let n = e; n < r.length; n++)
        this._fs.rmSync(j.join(this.runtimeDir, r[n].name), {
          recursive: !0,
          force: !0,
        });
    } catch (t) {}
  }
};
function Ot(p, d, e) {
  return !p ||
    typeof p != "object" ||
    !Object.prototype.hasOwnProperty.call(p, d)
    ? !!e
    : !!p[d];
}
function _r(p, d, e) {
  let t = !Ot(p, d, e);
  return (p && typeof p == "object" && (p[d] = t), t);
}
var $r = ["EMBED", "OCR_REBUILD", "OCR_REDO"];
function Ze(p, d) {
  var s, a;
  let t = (d + p).split(`
`),
    r = (s = t.pop()) != null ? s : "",
    n = [];
  for (let i of t)
    for (let l of $r) {
      let c = l.length;
      if (i.startsWith(l + "_START:")) {
        let u = parseInt(i.slice(c + 7), 10) || 0;
        n.push({ prefix: l, event: "START", total: u });
        break;
      }
      if (i.startsWith(l + "_PROGRESS:")) {
        let f = i.slice(c + 10).split(":");
        n.push({
          prefix: l,
          event: "PROGRESS",
          current: parseInt(f[0], 10) || 0,
          total: parseInt(f[1], 10) || 0,
          key: (a = f[2]) != null ? a : "",
        });
        break;
      }
      if (i === l + "_DONE" || i.startsWith(l + "_DONE:")) {
        n.push({ prefix: l, event: "DONE" });
        break;
      }
    }
  return { events: n, buffer: r };
}
function Ge(p) {
  return { app: { secretStorage: p.secretStorage }, saveData: async () => {} };
}
var Se = class Se extends R.PluginSettingTab {
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
    this._probing = new Set();
    this._attemptedProbes = new Set();
    this._setupView = "overview";
    this._selectedDetailModule = "";
    this._focusTargetId = null;
    this._runtimeAbortController = null;
    this._managedRuntime = null;
    this._runtimeBusy = !1;
    this._libraryRunning = !1;
    this._dismissedMaintenanceItems = new Set();
    this._displayInProgress = !1;
    this._pendingMaintenanceRefresh = !1;
    this._maintenanceNoticeShown = !1;
    this._detailReturn = null;
    this.plugin = t;
  }
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }
  display() {
    this._displayInProgress = !0;
    let { containerEl: e } = this;
    if (
      (e.empty(),
      this._refreshPfConfig(),
      this._initCapabilityState(),
      this._applyStaleTolerance(),
      !document.getElementById("paperforge-tab-styles"))
    ) {
      let a = document.createElement("style");
      ((a.id = "paperforge-tab-styles"),
        (a.textContent = `
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
        document.head.appendChild(a));
    }
    let t = this.plugin.settings._migration_warnings;
    if (Array.isArray(t) && t.length > 0) {
      let a = e.createDiv({ cls: "paperforge-migration-warning" }),
        i = t
          .map((l) =>
            l === "paddleocr_api_key" ? "OCR (PaddleOCR)" : "Memory (Vector DB)"
          )
          .join(", ");
      (a.createEl("strong", { text: "Credential Migration Notice" }),
        a.createEl("p", {
          text: `One or more credentials could not be automatically migrated (${i}). Your existing keys are preserved in plaintext and remain functional. To complete the migration, re-enter the affected keys in the Settings fields below.`,
        }),
        a.createEl("p", {
          text: "After re-entering, save settings. The plugin will retry migration on next restart.",
          cls: "paperforge-manual-links",
        }));
    }
    let r = e.createDiv({ cls: "paperforge-settings-tabs" }),
      n = [
        { id: "overview", label: o("tab_overview") || "Overview" },
        { id: "module-detail", label: o("tab_modules") || "Module Detail" },
        { id: "maintenance", label: o("tab_maintenance") || "Maintenance" },
        { id: "help", label: o("tab_help") || "Help" },
      ],
      s = {};
    if (
      (n.forEach((a) => {
        r.createEl("button", {
          cls:
            "paperforge-settings-tab" +
            (a.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
          text: a.label,
        }).addEventListener("click", () => {
          (a.id === "maintenance"
            ? ((this._maintenanceNoticeShown = !1),
              (this._focusTargetId = "#pf-maintenance-heading"))
            : (this._detailReturn = null),
            (this.activeTab = a.id),
            this.display());
        });
      }),
      n.forEach((a) => {
        s[a.id] = e.createDiv({
          cls:
            "paperforge-tab-content" +
            (a.id === this.activeTab ? " paperforge-tab-content--active" : ""),
        });
      }),
      this.activeTab === "overview"
        ? this._renderOverviewTab(s.overview)
        : this.activeTab === "module-detail"
          ? this._renderModuleDetailTab(s["module-detail"])
          : this.activeTab === "maintenance"
            ? this._renderMaintenanceTab(s.maintenance)
            : this.activeTab === "help" && this._renderHelpTab(s.help),
      this._focusTargetId && this.activeTab !== "help")
    ) {
      let a = e.querySelector(this._focusTargetId);
      if (a) {
        try {
          a.focus();
        } catch (i) {}
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
      e.createEl("h2", { text: o("header_title") || "PaperForge" }),
      e.createEl("p", { text: o("desc"), cls: "paperforge-settings-desc" }),
      this._renderControlCenter(e),
      this._renderAdvancedSection(e));
    for (let n of Fe) {
      let s = (r = this._capabilityState) == null ? void 0 : r[n];
      s &&
        s.capability_state === "unknown" &&
        s.updated_at === new Date(0).toISOString() &&
        !this._attemptedProbes.has(n) &&
        (this._attemptedProbes.add(n),
        n !== "maintenance" && this._probeModule(n));
    }
  }
  _renderAdvancedSection(e) {
    this._advCollapsed === void 0 && (this._advCollapsed = !0);
    let t = e.createEl("div", { cls: "paperforge-collapsible-header" }),
      r = t.createEl("span", {
        text: "\u25B6",
        cls: "paperforge-collapsible-arrow",
      });
    r.style.transform = this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)";
    let n = t.createEl("span", {
        cls: "paperforge-collapsible-title",
        text: "Advanced",
      }),
      s = t.createEl("span", {
        cls: "paperforge-collapsible-sub",
        text: "Memory + Vector DB + Embedding",
      }),
      a = e.createEl("div", { cls: "paperforge-collapsible-content" });
    ((a.style.display = this._advCollapsed ? "none" : ""),
      t.addEventListener("click", () => {
        ((this._advCollapsed = !this._advCollapsed),
          (a.style.display = this._advCollapsed ? "none" : ""),
          (r.style.transform = this._advCollapsed
            ? "rotate(0deg)"
            : "rotate(90deg)"));
      }),
      a.createEl("h4", { text: "Memory Layer" }),
      a
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(o("feat_memory_desc")));
    let l = a.createEl("div", { cls: "paperforge-memory-status" }),
      c = this.app.vault.adapter.basePath;
    (this.plugin._lastSyncTime &&
      !this._lastSyncTime &&
      (this._lastSyncTime = this.plugin._lastSyncTime),
      this._memoryStatusText === null && (this._memoryStatusText = rt(c)),
      this._renderMemoryStatusText(
        l,
        this._memoryStatusText,
        this._lastSyncTime
      ),
      this._renderVectorSection(a));
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
    return this._managedRuntime
      ? this._managedRuntime
      : ((this._managedRuntime = new ct({
          version: this.plugin.manifest.version,
        })),
        this._managedRuntime);
  }
  _resolveRuntimeCommand(e) {
    let t = ur(this._ensureManagedRuntime().current());
    return t ? { path: t.command, args: [...t.args] } : null;
  }
  _renderInstallationDetail(e) {
    var C, S;
    e.createEl("button", {
      cls: "pf-back-btn",
      text: o("btn_back_to_overview"),
    }).addEventListener("click", () => {
      var k;
      (((k = this._detailReturn) == null ? void 0 : k.tab) === "maintenance"
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId =
            "button.pf-open-module-btn[data-module=installation]")),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let r = e.createEl("h2", {
        cls: "pf-installation-detail-heading",
        text: o("installation_detail_heading") || "Installation Details",
        attr: { id: "pf-installation-detail-heading", tabindex: "-1" },
      }),
      n = [
        {
          id: "installation",
          labelKey: "md_select_installation",
          disabled: !1,
        },
      ],
      s = e.createEl("div", { cls: "pf-module-detail-selector" });
    for (let k of n) {
      let T = s.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (k.id === "installation" ? " pf-module-detail-btn--active" : "") +
          (k.disabled ? " pf-module-detail-btn--disabled" : ""),
        text: o(k.labelKey),
      });
      k.disabled && (T.disabled = !0);
    }
    let a = (C = this._capabilityState) != null ? C : {},
      i = "installation",
      l = (S = a[i]) != null ? S : Te(i),
      c = this._sevClass(l.severity),
      u = $e(l),
      f = e.createEl("div", {
        cls: "pf-cc-card",
        attr: { style: "margin-bottom: 12px;" },
      }),
      _ = f.createEl("div", { cls: "pf-cc-card-header" });
    (_.createEl("span", {
      cls: "pf-cc-card-name",
      text: o("cc_module_installation"),
    }),
      _.createEl("span", {
        cls: `pf-cc-card-badge pf-cc-card-badge--${c}`,
        text: o(this._ccBadgeKey(l, i)),
      }));
    let h = this._localizeReason(l.reason.code, "installation");
    if (
      (f.createEl("div", {
        cls: "pf-cc-card-reason",
        text: h != null ? h : l.reason.text,
      }),
      l.action.primary && !u)
    ) {
      let k = ze(l),
        M =
          k.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      f.createEl("button", { cls: M, text: k.label }).addEventListener(
        "click",
        () => {
          k.kind === "setup"
            ? new Ae(this.app, this.plugin, () => {
                (this._probeModule("installation"), this._probeModule("help"));
              }).open()
            : this._probeModule(i);
        }
      );
    }
    e.createEl("h3", { text: o("managed_runtime_status") });
    let m = e.createEl("div", { cls: "pf-runtime-status-card" }),
      E = (k, T, M) => {
        let B = m.createEl("div", { cls: "pf-runtime-actions" });
        for (let F of k) {
          let A = B.createEl("button", {
            cls: "pf-runtime-action-btn",
            text: F.label,
          });
          (M && F.verb !== "stop" && (A.disabled = !0),
            A.addEventListener("click", async () => {
              var z;
              if (F.verb === "stop") {
                let H = this._runtimeAbortController;
                if (!H || H.signal.aborted) return;
                (H.abort(),
                  new R.Notice(o("managed_runtime_action_cancelled")),
                  this.display(),
                  this._probeModule("installation"),
                  this._probeModule("help"));
                return;
              }
              let P = this._ensureManagedRuntime(),
                L = new AbortController();
              ((this._runtimeAbortController = L),
                (this._runtimeBusy = !0),
                new R.Notice(o("managed_runtime_running")));
              try {
                (F.verb === "install" ||
                F.verb === "repair" ||
                F.verb === "update"
                  ? await P.ensure({
                      signal: L.signal,
                      force: F.verb === "update" || F.verb === "repair",
                    })
                  : F.verb === "rollback"
                    ? await P.ensure({
                        signal: L.signal,
                        version: (z = T.previousVersion) != null ? z : void 0,
                      })
                    : await P.status(),
                  L.signal.aborted ||
                    new R.Notice(o("managed_runtime_action_complete")));
              } catch (H) {
                if ((H == null ? void 0 : H.name) !== "AbortError") {
                  let N = H instanceof Error ? H.message : String(H);
                  new R.Notice(
                    o("managed_runtime_action_failed").replace("{error}", N),
                    8e3
                  );
                }
              } finally {
                ((this._runtimeAbortController = null),
                  (this._runtimeBusy = !1),
                  this._probeModule("installation"),
                  this._probeModule("help"),
                  this.display());
              }
            }));
        }
      },
      y = () => {
        var P;
        m.empty();
        let T = this._ensureManagedRuntime().current(),
          M = m.createEl("div", { cls: "pf-runtime-status-header" });
        M.createEl("div", {
          cls: "pf-runtime-status-label",
          text: o("managed_runtime_status"),
        });
        let B, F;
        switch (T.state) {
          case "ready":
            ((B = "ok"), (F = o("managed_runtime_ok_state")));
            break;
          case "not_installed":
            ((B = "warn"), (F = o("managed_runtime_not_installed")));
            break;
          case "needs_repair":
            ((B = "warn"), (F = o("managed_runtime_needs_repair")));
            break;
          case "unavailable":
            ((B = "error"), (F = o("managed_runtime_unavailable")));
            break;
          default:
            ((B = "unknown"), (F = o("managed_runtime_unknown_state")));
        }
        if (
          (M.createEl("span", {
            cls: `pf-runtime-status-state pf-runtime-status-state--${B}`,
            text: F,
          }),
          T.version &&
            m.createEl("div", { cls: "pf-meta", text: `Python ${T.version}` }),
          T.pythonPath &&
            m.createEl("div", {
              cls: "pf-meta",
              text: T.pythonPath,
              attr: { style: "word-break: break-all;" },
            }),
          T.lastVerifiedAt &&
            m.createEl("div", {
              cls: "pf-meta",
              text: o("managed_runtime_last_verified").replace(
                "{time}",
                new Date(T.lastVerifiedAt).toLocaleString()
              ),
            }),
          T.error &&
            m.createEl("div", {
              cls: "pf-runtime-error",
              text: `${T.error.code}: ${T.error.message}`,
            }),
          T.warnings && T.warnings.length > 0)
        )
          for (let L of T.warnings) {
            let z = m.createEl("div", {
              cls: "pf-runtime-warning",
              text: `\u26A0 ${L.message}`,
            });
            L.platformAction &&
              z.createEl("div", {
                cls: "pf-runtime-warning-action",
                text: L.platformAction,
              });
          }
        (P = T.error) != null &&
          P.platformAction &&
          m.createEl("div", {
            cls: "pf-runtime-error-action",
            text: T.error.platformAction,
          });
        let A = pr(T, this.plugin.manifest.version, this._runtimeBusy);
        E(A, T, this._runtimeBusy);
      };
    y();
    let g = this._ensureManagedRuntime().status();
    (g &&
      g
        .then(() => {
          e.isConnected && y();
        })
        .catch(() => {}),
      e.createEl("h3", {
        text: o("section_config") || "Current Configuration",
      }));
    let v = this._getVaultBasePath(),
      w = K(v, this.plugin.settings, void 0, void 0),
      b = this._getPythonDesc(w.path, w.source);
    new R.Setting(e)
      .setName(o("field_python_interp") || "Python Interpreter")
      .setDesc(b)
      .addExtraButton((k) => {
        k.setIcon("reset")
          .setTooltip("Re-detect")
          .onClick(() => {
            ((this._pythonInterpDescEl = null),
              (this._managedRuntime = null),
              this.display());
          });
      })
      .addButton((k) => {
        k.setButtonText(o("runtime_health_sync") || "Sync Runtime").onClick(
          () => {
            this._syncRuntime(k);
          }
        );
      });
    let x = e.createEl("div", { cls: "setting-item-description" });
    ((this._customPathDescEl = x),
      new R.Setting(e)
        .setName(o("field_python_custom") || "Custom Python Path")
        .setDesc(o("optional_later"))
        .addText((k) => {
          k.setPlaceholder("e.g. C:\\Python311\\python.exe")
            .setValue(this.plugin.settings.python_path || "")
            .onChange((T) => {
              ((this.plugin.settings.python_path = T.trim()),
                this._debouncedSave(),
                (this._managedRuntime = null));
            });
        })
        .addButton((k) => {
          k.setButtonText(o("feat_verify") || "Validate").onClick(() => {
            this._validatePythonOverride();
          });
        }),
      new R.Setting(e)
        .setName(o("field_zotero_data") || "Zotero Data Dir")
        .setDesc(o("field_zotero_placeholder"))
        .addText((k) => {
          k.setPlaceholder("C:\\Users\\...\\Zotero")
            .setValue(this.plugin.settings.zotero_data_dir || "")
            .onChange((T) => {
              ((this.plugin.settings.zotero_data_dir = T.trim()),
                this._debouncedSave());
            });
        }),
      e.createEl("h3", {
        text: o("agent_integration_section") || "Agent Integration",
      }),
      this._renderSkillsList(e));
    try {
      r.focus();
    } catch (k) {}
  }
  _renderSkillsList(e) {
    let t = {
        opencode: "OpenCode",
        claude: "Claude Code",
        codex: "Codex",
        cursor: "Cursor",
        windsurf: "Windsurf",
        github_copilot: "GitHub Copilot",
        gemini: "Gemini CLI",
      },
      r = {
        opencode: ".opencode/skills",
        claude: ".claude/skills",
        codex: ".codex/skills",
        cursor: ".cursor/skills",
        windsurf: ".windsurf/skills",
        github_copilot: ".github/skills",
        gemini: ".gemini/skills",
      },
      n = this._getVaultBasePath(),
      s = this.plugin.settings.agent_platform || "opencode";
    (new R.Setting(e)
      .setName(o("label_agent") || "Agent Platform")
      .setDesc(o("feat_agent_platform_desc"))
      .addDropdown((_) => {
        (Object.entries(t).forEach(([h, m]) => _.addOption(h, m)),
          _.setValue(s).onChange((h) => {
            ((this.plugin.settings.agent_platform = h),
              this.plugin.saveSettings(),
              this.display());
          }));
      })
      .addExtraButton((_) => {
        _.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            let h = r[s] || ".opencode/skills",
              m = re.join(n, h);
            q.existsSync(m)
              ? (0, Y.exec)(`start "" "${m}"`)
              : new R.Notice(`Skills folder not found: ${h}`);
          });
      }),
      e.createEl("h3", { text: "Skills" }));
    let a = e.createEl("div", { cls: "paperforge-desc-box" });
    (a.setText(o("feat_skills_desc")),
      a.createEl("br"),
      a.createEl("span", { text: o("feat_skills_system") }));
    let i = re.join(n, r[s]),
      l = [],
      c = [];
    q.existsSync(i) &&
      q.readdirSync(i, { withFileTypes: !0 }).forEach((_) => {
        if (!_.isDirectory()) return;
        let h = re.join(i, _.name, "SKILL.md");
        if (!q.existsSync(h)) return;
        let m = q.readFileSync(h, "utf-8"),
          E = m.match(/^name:\s*(.+)$/m),
          y = m.split(`
`),
          g = y.findIndex((S) => /^description:/.test(S)),
          v = "";
        if (g >= 0) {
          let S = y[g].match(/^description:\s*(.+)$/);
          if (S && S[1] && S[1] !== ">" && S[1] !== "|-" && S[1] !== "|")
            v = S[1].trim();
          else {
            for (
              let k = g + 1;
              k < y.length && (/^\s{2,}/.test(y[k]) || y[k].trim() === "");
              k++
            )
              v += y[k].trim() + " ";
            v = v.trim();
          }
        }
        let w = m.match(/^source:\s*(.+)$/m),
          b = m.match(/^disable-model-invocation:\s*(.+)$/m),
          x = m.match(/^version:\s*(.+)$/m),
          C = {
            name: E ? E[1].trim() : _.name,
            desc: v,
            source: w ? w[1].trim() : "user",
            disabled: !!b && b[1].trim() === "true",
            version: x ? x[1].trim() : "",
            path: h,
            content: m,
            dirName: _.name,
          };
        C.source === "paperforge" ? l.push(C) : c.push(C);
      });
    let u = e.createEl("div", { cls: "paperforge-skills-box" }),
      f = (_, h, m) => {
        if (h.length === 0) return;
        let E = u.createEl("div", { cls: "paperforge-skills-group" }),
          y = E.createEl("div", { cls: "paperforge-skills-collapse-header" }),
          g = E.createEl("div", { cls: "paperforge-skills-collapse-content" }),
          v = y.createEl("span", {
            text: "\u25BC",
            cls: "paperforge-skills-arrow",
          });
        (y.createEl("h4", {
          text: `${_} (${h.length})`,
          cls: "paperforge-skills-subheader",
        }),
          h.forEach((x) => {
            let C = x.name + (x.version ? " v" + x.version : ""),
              S = m ? " [system]" : " [user]",
              k = x.desc || "",
              T = new R.Setting(g).setName(C + S).setDesc(k);
            ((T.settingEl.style.opacity = x.disabled ? "0.4" : "1"),
              T.addToggle((M) => {
                M.setValue(!x.disabled).onChange((B) => {
                  let F = !B,
                    P = x.content.match(/^disable-model-invocation:\s*(.+)$/m)
                      ? x.content.replace(
                          /^disable-model-invocation:\s*.+$/m,
                          `disable-model-invocation: ${F}`
                        )
                      : x.content.replace(
                          /^(---\r?\n)/,
                          `$1disable-model-invocation: ${F}
`
                        );
                  (q.writeFileSync(x.path, P, "utf-8"),
                    (x.disabled = F),
                    (x.content = P),
                    (T.settingEl.style.opacity = x.disabled ? "0.4" : "1"));
                });
              }));
          }));
        let w = m ? "system" : "user";
        ((this._skillsCollapsed[w] || !1) &&
          ((g.style.display = "none"), (v.style.transform = "rotate(-90deg)")),
          y.addEventListener("click", () => {
            (g.style.display !== "none"
              ? ((g.style.display = "none"),
                (v.style.transform = "rotate(-90deg)"))
              : ((g.style.display = ""), (v.style.transform = "rotate(0deg)")),
              (this._skillsCollapsed[w] = g.style.display === "none"));
          }));
      };
    (f("System Skills", l, !0),
      f("User Skills", c, !1),
      l.length === 0 &&
        c.length === 0 &&
        u.createEl("p", {
          text: `No skills found in ${r[s]}. Run setup to deploy skills.`,
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
              : ((this._selectedDetailModule = "installation"),
                this._renderInstallationDetail(e)));
  }
  _renderLibraryDetail(e) {
    this._renderModuleDetailShell(e, "library");
  }
  _renderOcrDetail(e) {
    if (
      (this._renderModuleDetailShell(e, "ocr"), this.plugin._ocrProcess != null)
    ) {
      let r = e.createEl("div", { cls: "pf-detail-controls" });
      r.createEl("button", {
        cls: "mod-warning",
        text: o("ocr_stop_batch") || "Stop OCR batch",
      }).addEventListener("click", () => {
        var i;
        let a = this.plugin._ocrProcess;
        (i = a == null ? void 0 : a.stdin) != null && i.write
          ? (a.stdin.write(`PAPERFORGE_STOP
`),
            (this.plugin._ocrWasStopped = !0))
          : a != null && a.kill && a.kill("SIGINT");
      });
      let s = this.plugin._ocrProgress;
      s &&
        s.total > 0 &&
        r.createEl("span", {
          cls: "pf-detail-progress",
          text: `${s.current}/${s.total} papers`,
        });
    }
  }
  _renderMemoryDetail(e) {
    this._renderModuleDetailShell(e, "memory");
  }
  _dispatchModuleAction(e, t) {
    var a, i, l, c, u;
    let r = (a = t.action) == null ? void 0 : a.primary;
    if (!r) {
      this._probeModule(e);
      return;
    }
    let n = r.verb,
      s = (i = r.command) != null ? i : "";
    if (r.destructive && r.confirmation_required) {
      new nt(
        this.app,
        {
          title: r.label,
          effectLabel:
            (c =
              (l = r.destructive_effect) != null ? l : r.confirmation_prompt) !=
            null
              ? c
              : "Proceed?",
        },
        () => {
          var f;
          this._runAllowedDispatch(
            e,
            r.verb,
            (f = r.command) != null ? f : "",
            t
          );
        }
      ).open();
      return;
    }
    this._runAllowedDispatch(e, r.verb, (u = r.command) != null ? u : "", t);
  }
  _runAllowedDispatch(e, t, r, n) {
    var s, a, i;
    if (
      (t === "setup" || t === "set_config") &&
      r === "paperforge setup" &&
      (e === "installation" || e === "library" || e === "ocr")
    ) {
      let l = [e];
      (e === "installation" && l.push("help"),
        new Ae(this.app, this.plugin, () => {
          for (let c of l) this._probeModule(c);
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
              c = nr(
                n.reason.code,
                n.reason.text,
                (i =
                  (a = (s = n.action) == null ? void 0 : s.primary) == null
                    ? void 0
                    : a.scope_count) != null
                  ? i
                  : 0,
                l
              );
            new at(
              this.app,
              c,
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
      (o("action_unknown_pair") || "Unknown action: {verb}").replace(
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
      new R.Notice(o("runtime_not_available") || "No Python runtime available");
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
      a = (l = this._capabilityState) != null ? l : {};
    (a.ocr &&
      ((a.ocr.activity_state = "running"),
      (a.ocr.activity_label = s[e] || "Running\u2026"),
      (a.ocr.activity_progress = { current: 0, total: 1 })),
      (this.plugin._ocrBuffer = ""),
      (this.plugin._ocrProgress = { current: 0, total: 1, key: "" }),
      (this.plugin._ocrWasStopped = !1),
      this.display());
    let i = this._callPython(n, {
      stream: !0,
      onData: (c) => {
        var h;
        let u =
            typeof c == "string"
              ? c
              : Buffer.isBuffer(c)
                ? c.toString("utf-8")
                : String(c),
          { events: f, buffer: _ } = Ze(
            u,
            (h = this.plugin._ocrBuffer) != null ? h : ""
          );
        this.plugin._ocrBuffer = _;
        for (let m of f)
          m.event === "START"
            ? (this.plugin._ocrProgress &&
                (this.plugin._ocrProgress.total = m.total || 1),
              a.ocr &&
                (a.ocr.activity_progress = { current: 0, total: m.total || 1 }))
            : m.event === "PROGRESS" &&
              ((this.plugin._ocrProgress = {
                current: m.current || 0,
                total: m.total || 1,
                key: m.key || "",
              }),
              a.ocr &&
                (a.ocr.activity_progress = {
                  current: m.current || 0,
                  total: m.total || 1,
                }));
        this.display();
      },
      onError: (c) => {
        ((this.plugin._ocrProcess = null),
          a.ocr &&
            ((a.ocr.activity_state = "idle"),
            (a.ocr.activity_label = null),
            (a.ocr.activity_progress = null)),
          new R.Notice("OCR error: " + (c.message || c), 8e3),
          this._probeModule("ocr"),
          this.display());
      },
      onClose: (c) => {
        ((this.plugin._ocrProcess = null),
          a.ocr &&
            ((a.ocr.activity_state = "idle"),
            (a.ocr.activity_label = null),
            (a.ocr.activity_progress = null)),
          c === 0
            ? new R.Notice(
                e === "run"
                  ? "OCR run complete."
                  : e === "rebuild"
                    ? "OCR rebuild complete."
                    : "OCR redo complete."
              )
            : c === 130 || this.plugin._ocrWasStopped
              ? ((this.plugin._ocrWasStopped = !1),
                new R.Notice("OCR batch stopped by user."))
              : new R.Notice(
                  "OCR operation failed with exit code " +
                    (c != null ? c : "?"),
                  8e3
                ),
          this._probeModule("ocr"),
          this.display());
      },
    });
    this.plugin._ocrProcess = i;
  }
  _dispatchMemoryBuild(e) {
    var a;
    let t = this.app.vault.adapter.basePath,
      r = (a = this._capabilityState) != null ? a : {};
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
      let i = this._callPython(n, {
        stream: !0,
        onData: (l) => {
          var _;
          let c =
              typeof l == "string"
                ? l
                : Buffer.isBuffer(l)
                  ? l.toString("utf-8")
                  : String(l),
            { events: u, buffer: f } = Ze(
              c,
              (_ = this.plugin._embedBuffer) != null ? _ : ""
            );
          this.plugin._embedBuffer = f;
          for (let h of u)
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
        onError: (l) => {
          ((this.plugin._embedProcess = null),
            r.memory &&
              ((r.memory.activity_state = "idle"),
              (r.memory.activity_label = null),
              (r.memory.activity_progress = null)),
            new R.Notice(s + " build error: " + (l.message || l), 8e3),
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
              ? new R.Notice(s + " build complete.")
              : new R.Notice(
                  s + " build failed with exit code " + (l != null ? l : "?"),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
      this.plugin._embedProcess = i;
    } else
      this._callPython(n, {
        timeout: 12e4,
        onClose: (i, l, c) => {
          (r.memory &&
            ((r.memory.activity_state = "idle"),
            (r.memory.activity_label = null)),
            i === 0
              ? new R.Notice(s + " rebuild complete")
              : new R.Notice(
                  s + " build failed" + (c ? ": " + c.slice(0, 120) : ""),
                  8e3
                ),
            this._probeModule("memory"),
            this.display());
        },
      });
  }
  _renderModuleDetailShell(e, t) {
    var T, M, B, F;
    let r = t + "_detail_heading",
      n = "pf-" + t + "-detail-heading";
    e.createEl("button", {
      cls: "pf-back-btn",
      text: o("btn_back_to_overview"),
    }).addEventListener("click", () => {
      var A;
      (((A = this._detailReturn) == null ? void 0 : A.tab) === "maintenance"
        ? ((this.activeTab = this._detailReturn.tab),
          (this._focusTargetId = this._detailReturn.selector),
          (this._detailReturn = null))
        : ((this.activeTab = "overview"),
          (this._focusTargetId =
            "button.pf-open-module-btn[data-module=" + t + "]")),
        (this._selectedDetailModule = ""),
        this.display());
    });
    let a = e.createEl("h2", {
        cls: "pf-module-detail-heading",
        text: o(r) || o("cc_module_" + t),
        attr: { id: n, tabindex: "-1" },
      }),
      i = [
        { id: "installation", labelKey: "md_select_installation" },
        { id: "library", labelKey: "md_select_library" },
        { id: "ocr", labelKey: "md_select_ocr" },
        { id: "memory", labelKey: "md_select_memory" },
      ],
      l = e.createEl("div", { cls: "pf-module-detail-selector" });
    for (let A of i)
      l.createEl("button", {
        cls:
          "pf-module-detail-btn" +
          (A.id === t ? " pf-module-detail-btn--active" : ""),
        text: o(A.labelKey),
      }).addEventListener("click", () => {
        ((this._selectedDetailModule = A.id),
          (this._focusTargetId =
            A.id === "installation"
              ? "#pf-installation-detail-heading"
              : "#pf-" + A.id + "-detail-heading"),
          this.display());
      });
    let u =
        (M = ((T = this._capabilityState) != null ? T : {})[t]) != null
          ? M
          : Te(t),
      f = this._sevClass(u.severity),
      _ = $e(u),
      h = e.createEl("div", { cls: "pf-cc-card pf-module-detail-card" }),
      m = h.createEl("div", { cls: "pf-cc-card-header" });
    if (
      (m.createEl("span", {
        cls: "pf-cc-card-name",
        text: o("cc_module_" + t),
      }),
      m.createEl("span", {
        cls: "pf-cc-card-badge pf-cc-card-badge--" + f,
        text: o(this._ccBadgeKey(u, t)),
      }),
      u.activity_state === "running" && u.activity_label)
    ) {
      let A = h.createEl("div", {
        cls: "pf-cc-card-activity",
        attr: { "aria-live": "polite" },
      });
      if (
        (A.createEl("span", { text: u.activity_label }),
        u.activity_progress && u.activity_progress.total > 0)
      ) {
        let P = Math.round(
            (u.activity_progress.current / u.activity_progress.total) * 100
          ),
          z = A.createEl("div", {
            cls: "pf-cc-card-progress",
            attr: {
              role: "progressbar",
              "aria-valuenow": String(u.activity_progress.current),
              "aria-valuemin": "0",
              "aria-valuemax": String(u.activity_progress.total),
            },
          }).createEl("div", { cls: "pf-cc-card-progress-fill" });
        z.style.width = P + "%";
      }
    }
    let E = this._localizeReason(u.reason.code, t);
    h.createEl("div", {
      cls: "pf-cc-card-reason",
      text: E != null ? E : u.reason.text,
    });
    let y = (B = u.action) == null ? void 0 : B.primary;
    if (y && !_) {
      y.destructive &&
        y.confirmation_required &&
        h
          .createEl("div", { cls: "pf-destructive-notice" })
          .createEl("span", {
            text: (F = y.destructive_effect) != null ? F : "",
          });
      let A = u.activity_state === "running",
        P = ze(u),
        L = h.createEl("button", {
          cls: "pf-cc-card-action pf-cc-card-action--primary",
          text: P.label,
        });
      (A && L.setAttr("disabled", "disabled"),
        L.addEventListener("click", () => {
          A || this._dispatchModuleAction(t, u);
        }));
    }
    let g = h.createEl("div", { cls: "pf-meta" }),
      v;
    try {
      v = new Date(u.updated_at).toLocaleString();
    } catch (A) {
      v = u.updated_at;
    }
    if (
      (g.createEl("span", {
        text:
          o("cc_diag_updated") +
          ": " +
          v +
          " | TTL: " +
          String(u.ttl_seconds) +
          "s",
      }),
      u.notices && u.notices.length > 0)
    )
      for (let A of u.notices)
        e.createEl("div", {
          cls: "pf-notice pf-notice--" + (A.level || "info"),
          text: A.message,
        });
    let w = h.createEl("details", { cls: "pf-cc-card-diagnostic" });
    w.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let b = w.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      x = o("cc_state_" + u.capability_state) || u.capability_state,
      C = o("cc_severity_" + u.severity) || u.severity,
      S = o("cc_activity_" + u.activity_state) || u.activity_state;
    (b.createEl("div", { text: o("cc_diag_module") + ": " + u.module }),
      b.createEl("div", { text: o("cc_diag_state") + ": " + x }),
      b.createEl("div", { text: o("cc_diag_severity") + ": " + C }),
      b.createEl("div", { text: o("cc_diag_activity") + ": " + S }));
    let k = b.createEl("div");
    (k.appendText(
      o("cc_diag_reason") + ": " + (E != null ? E : u.reason.text) + " "
    ),
      k.createEl("code", { text: u.reason.code }));
    try {
      a.focus();
    } catch (A) {}
  }
  _renderHelpTab(e) {
    var v, w;
    let t = (v = this._capabilityState) != null ? v : {},
      r = "help",
      n = (w = t[r]) != null ? w : Te(r),
      s = this._sevClass(n.severity),
      a = Se._REAL_PROBE.has(r);
    e.createEl("h2", { text: o("cc_module_help") || "Help & Docs" });
    let i = e.createEl("div", {
        cls: "pf-cc-card",
        attr: { style: "margin-bottom: 12px;" },
      }),
      l = i.createEl("div", { cls: "pf-cc-card-header" });
    (l.createEl("span", { cls: "pf-cc-card-name", text: o("cc_module_help") }),
      l.createEl("span", {
        cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
        text: o(this._ccBadgeKey(n, r)),
      }));
    let c;
    if (!a)
      c = o("cc_reason_placeholder").replace("{module}", o("cc_module_" + r));
    else {
      let b = this._localizeReason(n.reason.code, r);
      c = b != null ? b : n.reason.text;
    }
    if (
      (i.createEl("div", { cls: "pf-cc-card-reason", text: c }),
      n.action.primary && !$e(n))
    ) {
      let b = ze(n),
        C =
          b.kind === "setup"
            ? "pf-cc-card-action pf-cc-card-action--primary"
            : "pf-cc-card-action";
      i.createEl("button", {
        cls: C,
        text: b.label,
        attr: { "aria-label": b.label },
      }).addEventListener("click", () => {
        b.kind === "setup"
          ? new Ae(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._probeModule(r);
      });
    }
    let u = i.createEl("details", { cls: "pf-cc-card-diagnostic" });
    u.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let f = u.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      _ = o("cc_state_" + n.capability_state) || n.capability_state,
      h = o("cc_severity_" + n.severity) || n.severity,
      m = o("cc_activity_" + n.activity_state) || n.activity_state,
      E;
    try {
      E = new Date(n.updated_at).toLocaleString();
    } catch (b) {
      E = n.updated_at;
    }
    (f.createEl("div", { text: `${o("cc_diag_module")}: ${n.module}` }),
      f.createEl("div", { text: `${o("cc_diag_state")}: ${_}` }),
      f.createEl("div", { text: `${o("cc_diag_severity")}: ${h}` }),
      f.createEl("div", { text: `${o("cc_diag_activity")}: ${m}` }));
    let y = f.createEl("div");
    y.appendText(o("cc_diag_reason") + ": " + c + " ");
    let g = y.createEl("code", { text: n.reason.code });
    (f.createEl("div", {
      text: `${o("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      f.createEl("div", { text: `${o("cc_diag_updated")}: ${E}` }),
      this._renderReleaseNotesTab(e));
  }
  _execMemoryStatus(e, t, r) {
    let n = pe();
    (0, Y.exec)(
      `"${e}" -m paperforge --vault "${t}" memory status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let i = JSON.parse(a);
          if (i.ok) {
            let l = i.data,
              c = l.fresh ? "fresh" : "stale";
            r(
              `Papers: ${l.paper_count_db} | ${c}${l.needs_rebuild ? " - needs rebuild" : ""}`
            );
          } else r("DB not found. Run paperforge memory build.");
        } catch (i) {
          r("Could not parse status.");
        }
      }
    );
  }
  _execEmbedStatus(e, t, r) {
    let n = pe();
    (0, Y.exec)(
      `"${e}" -m paperforge --vault "${t}" embed status --json`,
      { encoding: "utf-8", timeout: 15e3, env: n },
      (s, a) => {
        if (s) {
          r("Status unavailable");
          return;
        }
        try {
          let i = JSON.parse(a);
          i.ok
            ? r(
                `Chunks: ${i.data.chunk_count} | ${i.data.model} | ${i.data.mode}`
              )
            : r("Could not parse status.");
        } catch (i) {
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
      i = (u) => {
        let f = (0, Y.spawn)(n.path, s, { cwd: r, env: u, windowsHide: !0 });
        return (
          t.onData && f.stdout.on("data", t.onData),
          t.onStderr && f.stderr.on("data", t.onStderr),
          t.onError && f.on("error", t.onError),
          f.on("close", t.onClose),
          f
        );
      },
      l = (u) => {
        (0, Y.execFile)(
          n.path,
          s,
          { cwd: r, timeout: (t && t.timeout) || 6e4, env: u },
          (f, _, h) => {
            t && t.onClose && t.onClose(f ? 1 : 0, _, h);
          }
        );
      };
    if (a)
      return (
        ye(Ge(this.app), t.credentialType).then((u) => {
          t && t.stream ? i(u) : l(u);
        }),
        null
      );
    let c = (t == null ? void 0 : t.env) || pe();
    return t && t.stream ? i(c) : (l(c), null);
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
      text: o("feat_memory_rebuild_btn"),
    });
    ((n.title = "Rebuild memory database"),
      (n.onclick = () => {
        let a = this.app.vault.adapter.basePath,
          i = we(a, this.plugin.settings);
        if (!i.path) {
          new R.Notice(o("feat_no_python"));
          return;
        }
        (console.log("[PaperForge] Rebuilding memory:", i.path),
          n.setText(o("feat_memory_rebuilding")),
          n.setAttr("disabled", ""),
          this._callPython(["memory", "build"], {
            timeout: 6e4,
            onClose: (l, c, u) => {
              (console.log(
                "[PaperForge] memory build exit:",
                l ? "FAIL:" + l : "OK",
                (c || "").slice(0, 200),
                (u || "").slice(0, 200)
              ),
                n.setText(o("feat_memory_rebuild_btn")),
                n.removeAttribute("disabled"),
                l === 0
                  ? new R.Notice(o("feat_memory_rebuild_done"))
                  : new R.Notice(
                      o("feat_memory_rebuild_failed") +
                        (u ? " " + u.slice(0, 80) : "")
                    ),
                (this._memoryStatusText = rt(a)),
                this._refreshSnapshots(a));
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
      r = K(t, e, void 0, void 0);
    return r.path ? `"${r.path}" -m paperforge --vault "${t}" sync` : null;
  }
  _runManualSync() {
    var s;
    let e = this.app.vault.adapter.basePath;
    if (!we(e, this.plugin.settings).path) return;
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
        onClose: (a) => {
          ((this.plugin._autoSyncRunning = !1),
            (this._libraryRunning = !1),
            (this._memoryStatusText = null),
            r.library &&
              ((r.library.activity_state = "idle"),
              (r.library.activity_label = null)),
            a === 0 &&
              ((this._lastSyncTime = new Date().toLocaleTimeString()),
              (this.plugin._lastSyncTime = this._lastSyncTime)),
            this._probeModule("library", a != null ? a : 1),
            this.display(),
            this._refreshSnapshots(e),
            st(this.app, this.plugin, e));
        },
      }));
  }
  _refreshSnapshots(e) {
    let t = we(e, this.plugin.settings),
      r = [
        ...t.extraArgs,
        "-m",
        "paperforge",
        "--vault",
        e,
        "runtime-health",
        "--json",
      ];
    ((this._refreshPending = !0),
      (0, Y.execFile)(
        t.path,
        r,
        { cwd: e, timeout: 3e4, windowsHide: !0 },
        (n, s, a) => {
          ((this._refreshPending = !1),
            (this._memoryStatusText = rt(e)),
            (this._embedStatusText = Me(e)),
            this.display());
        }
      ));
  }
  _renderVectorSection(e) {
    var l;
    if (
      (e.createEl("h4", { text: "Vector Database" }),
      this.plugin.settings.features ||
        (this.plugin.settings.features = { memory_layer: !0, vector_db: !1 }),
      e
        .createEl("div", { cls: "paperforge-desc-box" })
        .setText(o("feat_vector_desc")),
      new R.Setting(e)
        .setName(o("feat_vector_enable"))
        .setDesc(o("feat_vector_enable_desc"))
        .addToggle((c) => {
          c.setValue(!!this.plugin.settings.features.vector_db).onChange(
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
      text: o("feat_vector_config_label"),
    });
    let a = e.createEl("div", { cls: "paperforge-vector-config" }),
      i = (c) => {
        ((a.style.display = c ? "none" : ""),
          (s.style.transform = c ? "rotate(-90deg)" : "rotate(0deg)"));
      };
    if (
      (i(Ot(this._featurePanelsCollapsed, "vectorConfig", !1)),
      n.addEventListener("click", () => {
        let c = _r(this._featurePanelsCollapsed, "vectorConfig", !1);
        i(c);
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
    if (this._vectorDepsOk === null) {
      let c = tt(r);
      ((this._vectorDepsOk = c && (l = c.deps_installed) != null ? l : !1),
        this._vectorDepsOk && (this._embedStatusText = Me(r)),
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
      .setName(o("feat_openai_key"))
      .setDesc(o("feat_openai_key_desc"))
      .addText((s) => {
        ((s.inputEl.type = "password"),
          s
            .setPlaceholder(r)
            .setValue("")
            .onChange((a) => {
              a &&
                (n && clearTimeout(n),
                (n = setTimeout(async () => {
                  let i = this.app.secretStorage;
                  if (i != null && i.setSecret) {
                    try {
                      (await i.setSecret("vector-db-api-key", a),
                        (await i.getSecret("vector-db-api-key")) === a &&
                          ((this.plugin.settings._vector_db_configured = !0),
                          (this.plugin.settings.vector_db_api_key = ""),
                          await this.plugin.saveSettings(),
                          s.setValue("")));
                    } catch (l) {}
                    n = null;
                  }
                }, 600)));
            }));
      }),
      new R.Setting(e)
        .setName(o("feat_api_base_url"))
        .setDesc(o("feat_api_base_url_desc"))
        .addText((s) => {
          s.setPlaceholder("https://api.openai.com/v1")
            .setValue(this.plugin.settings.vector_db_api_base || "")
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_base = a),
                this.plugin.saveSettings());
            });
        }),
      new R.Setting(e)
        .setName(o("feat_api_model"))
        .setDesc(o("feat_api_model_desc"))
        .addText((s) => {
          s.setPlaceholder("text-embedding-3-small")
            .setValue(
              this.plugin.settings.vector_db_api_model ||
                "text-embedding-3-small"
            )
            .onChange((a) => {
              ((this.plugin.settings.vector_db_api_model = a),
                this.plugin.saveSettings());
            });
        }));
  }
  _renderVectorNoDeps(e) {
    (e
      .createEl("div", { cls: "paperforge-desc-box" })
      .setText(o("feat_deps_missing")),
      new R.Setting(e)
        .setName(o("feat_install_deps"))
        .setDesc(o("feat_install_deps_desc"))
        .addButton((r) => {
          r.setButtonText(o("feat_install_btn"))
            .setCta()
            .onClick(async () => {
              let n = this.app.vault.adapter.basePath,
                s = we(n, this.plugin.settings);
              if (!s.path) {
                new R.Notice(o("feat_no_python"));
                return;
              }
              (r.setButtonText(o("feat_installing")), r.setDisabled(!0));
              let a = "chromadb openai",
                i = new R.Notice(
                  o("feat_installing_pkgs").replace("{pkgs}", a),
                  0
                );
              try {
                let l = Object.assign({}, process.env, {
                    PYTHONIOENCODING: "utf-8",
                    PYTHONUTF8: "1",
                  }),
                  c = a.split(" ");
                (await new Promise((u, f) => {
                  (0, Y.execFile)(
                    s.path,
                    [...s.extraArgs, "-m", "pip", "install", ...c],
                    { cwd: n, timeout: 3e5, env: l, windowsHide: !0 },
                    (_) => {
                      _ ? f(_) : u();
                    }
                  );
                }),
                  i.hide(),
                  new R.Notice(o("feat_install_done")),
                  (this._vectorDepsOk = !0),
                  (this._embedStatusText = Me(n)),
                  this.display());
              } catch (l) {
                (i.hide(),
                  new R.Notice(
                    o("feat_install_failed") + (l.stderr || l.message || l)
                  ),
                  r.setButtonText(o("feat_retry_btn")),
                  r.setDisabled(!1));
              }
            });
        }));
  }
  _renderVectorReady(e, t) {
    (e.createEl("div", { cls: "paperforge-desc-box" }).setText(Me(t)),
      this._renderApiConfig(e));
    let n = e.createEl("div", { cls: "paperforge-embed-section" });
    n.createEl("div", { cls: "paperforge-embed-header" }).createEl("span", {
      text: o("retrieval_rebuild_vectors"),
      cls: "setting-item-name",
    });
    let a = n.createEl("div", { cls: "paperforge-embed-controls" }),
      i = n.createEl("div", {
        cls: "paperforge-embed-status-text",
        attr: { "aria-live": "polite" },
      });
    (() => {
      (a.empty(), i.empty());
      let c = tt(t),
        u = c == null ? void 0 : c.build_state,
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
      let { current: _, total: h, key: m } = this.plugin._embedProgress,
        E =
          typeof (c == null ? void 0 : c.body_chunk_count) == "number"
            ? c.body_chunk_count
            : 0,
        y =
          typeof (c == null ? void 0 : c.object_chunk_count) == "number"
            ? c.object_chunk_count
            : 0,
        v =
          (typeof (c == null ? void 0 : c.chunk_count) == "number"
            ? c.chunk_count
            : 0) +
          E +
          y,
        w = v > 0,
        b = c !== null && typeof c.corrupted == "boolean" && c.corrupted,
        x = !!this.plugin._embedProcess,
        C = !this.plugin._embedProcess && f.status === "running",
        S =
          (c == null ? void 0 : c.deps_installed) !== void 0
            ? !!c.deps_installed
            : !0,
        k = typeof f.status == "string" ? f.status : "",
        T = typeof f.message == "string" ? f.message : "",
        M = async (P) => {
          var H;
          if (P === "--resume" && w && !b) {
            let N = o("retrieval_rebuild_warning").replace("{n}", String(v));
            if (!confirm(N)) return;
          }
          if (P === "--force" && w && !b) {
            let N =
              "Force rebuild will replace " +
              v +
              " existing chunk(s). Continue?";
            if (!confirm(N)) return;
          }
          if (!we(t, this.plugin.settings).path) {
            new R.Notice(o("retrieval_no_python"));
            return;
          }
          let z = await ye(Ge(this.app), "embed");
          ((z.PYTHONIOENCODING = "utf-8"),
            (z.PYTHONUTF8 = "1"),
            (z.VECTOR_DB_API_BASE =
              this.plugin.settings.vector_db_api_base || ""),
            (z.VECTOR_DB_API_MODEL =
              this.plugin.settings.vector_db_api_model || ""),
            (this.plugin._embedStderr = ""),
            (this.plugin._embedProgress = { current: 0, total: 0, key: "" }),
            (this.plugin._embedProcess = this._callPython(
              ["embed", "build", P],
              {
                stream: !0,
                env: z,
                onData: (N) => {
                  var oe;
                  let ne =
                      typeof N == "string"
                        ? N
                        : Buffer.isBuffer(N)
                          ? N.toString("utf-8")
                          : String(N),
                    { events: ie, buffer: fe } = Ze(
                      ne,
                      (oe = this.plugin._embedBuffer) != null ? oe : ""
                    );
                  this.plugin._embedBuffer = fe;
                  for (let Z of ie)
                    Z.event === "START"
                      ? (this.plugin._embedProgress.total = Z.total || 0)
                      : Z.event === "PROGRESS"
                        ? ((this.plugin._embedProgress.current =
                            Z.current || 0),
                          (this.plugin._embedProgress.key = Z.key || ""))
                        : Z.event === "DONE" &&
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
                      o("feat_build_failed") + ": " + (N.message || N)
                    ),
                    this.display());
                },
                onClose: (N) => {
                  var ne;
                  if (
                    (clearInterval(
                      (ne = this.plugin._embedPollInterval) != null
                        ? ne
                        : void 0
                    ),
                    (this.plugin._embedPollInterval = null),
                    (this.plugin._embedProcess = null),
                    N === 0)
                  )
                    ((this.plugin._embedProgress.current =
                      this.plugin._embedProgress.total),
                      this.plugin.saveSettings(),
                      (this._embedStatusText = Me(t)),
                      new R.Notice(o("feat_build_complete")));
                  else {
                    this._embedStatusText = null;
                    let ie = (this.plugin._embedStderr || "").slice(0, 200);
                    new R.Notice(
                      o("feat_build_failed") + (ie ? ": " + ie : ""),
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
              (H = this.plugin._embedPollInterval) != null ? H : void 0
            ),
            (this.plugin._embedPollInterval = setInterval(() => {
              this.plugin._embedPolling ||
                ((this.plugin._embedPolling = !0),
                this._callPython(["embed", "status", "--json"], {
                  timeout: 5e3,
                  onClose: (N, ne) => {
                    var ie;
                    if (((this.plugin._embedPolling = !1), N === 0 && ne))
                      try {
                        let oe = JSON.parse(ne).data;
                        if (oe && oe.build_state) {
                          let Z = oe.build_state;
                          ((Z.status === "stopping" || Z.status === "idle") &&
                            this.plugin._embedProcess &&
                            ((this.plugin._embedProcess = null),
                            clearInterval(
                              (ie = this.plugin._embedPollInterval) != null
                                ? ie
                                : void 0
                            ),
                            (this.plugin._embedPollInterval = null),
                            this.display()),
                            Z.current !== void 0 &&
                              Z.total !== void 0 &&
                              ((this.plugin._embedProgress.current = Z.current),
                              (this.plugin._embedProgress.total = Z.total || 1),
                              (this.plugin._embedProgress.key =
                                Z.paper_id || "")));
                        }
                      } catch (fe) {}
                  },
                }));
            }, 2e3)),
            this.display());
        },
        B = Ue(t),
        F = !1;
      B &&
        typeof B.summary == "object" &&
        B.summary !== null &&
        "status" in B.summary &&
        (F = B.summary.status === "version_mismatch");
      let A;
      switch (
        (S
          ? F
            ? (A = "runtime-mismatch")
            : k === "stopping"
              ? (A = "stopping")
              : x && k === "running"
                ? (A = "building")
                : k === "failed"
                  ? (A = "failed")
                  : k === "stopped"
                    ? (A = "stopped")
                    : C
                      ? (A = "stale")
                      : b
                        ? (A = "corrupted")
                        : w
                          ? (A = "ready")
                          : (A = "idle")
          : (A = "deps-missing"),
        A)
      ) {
        case "building": {
          let P = a.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1;";
          let L = h > 0 ? ((_ / h) * 100).toFixed(1) : "0",
            z = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((z.style.cssText = `width:${L}%; min-width:${_ > 0 ? "2px" : "0"};`),
            _ < h)
          ) {
            let N = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(L)).toFixed(1)}%;`;
          }
          (i.createEl("span", {
            cls: "paperforge-embed-progress-text",
            text: `${_}/${h} papers`,
          }),
            m &&
              i.createEl("span", {
                cls: "paperforge-embed-progress-key",
                text: ` (${m})`,
              }));
          let H = a.createEl("button");
          (H.setText(o("retrieval_stop")),
            (H.className = "mod-warning"),
            H.addEventListener("click", () => {
              (this._callPython(["embed", "stop", "--json"], { timeout: 8e3 }),
                this.display());
            }));
          break;
        }
        case "stopping": {
          let P = a.createEl("div", { cls: "paperforge-progress-track" });
          P.style.cssText = "flex:1; opacity:0.5;";
          let L = h > 0 ? ((_ / h) * 100).toFixed(1) : "0",
            z = P.createEl("div", { cls: "paperforge-progress-seg done" });
          if (
            ((z.style.cssText = `width:${L}%; min-width:${_ > 0 ? "2px" : "0"};`),
            _ < h)
          ) {
            let N = P.createEl("div", {
              cls: "paperforge-progress-seg pending",
            });
            N.style.cssText = `width:${(100 - parseFloat(L)).toFixed(1)}%;`;
          }
          i.createEl("span", { text: o("retrieval_build_stopping") });
          let H = a.createEl("button");
          (H.setText(o("retrieval_stop")),
            (H.className = "mod-warning"),
            H.setAttr("disabled", ""));
          break;
        }
        case "failed": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_failed") + (T ? ": " + T : ""),
            attr: { style: "color:var(--text-error);" },
          });
          let P = a.createEl("button");
          (P.setText(o("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          let L = a.createEl("button");
          (L.setText(o("retrieval_force_rebuild")),
            (L.style.marginLeft = "6px"),
            L.addEventListener("click", () => M("--force")));
          break;
        }
        case "stopped": {
          i.setText(o("retrieval_build_stopped"));
          let P = a.createEl("button");
          (P.setText(o("retrieval_retry")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          break;
        }
        case "corrupted": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("feat_vector_corrupted"),
            attr: { style: "background:var(--background-modifier-warning);" },
          });
          let P = a.createEl("button");
          (P.setText(o("retrieval_force_rebuild")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--force")));
          break;
        }
        case "stale": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_stale"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = a.createEl("button");
          (P.setText(o("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          break;
        }
        case "ready": {
          a.createEl("span", {
            text: v + " chunks embedded",
            cls: "setting-item-description",
          });
          let P = a.createEl("button");
          (P.setText(o("retrieval_rebuild_vectors")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
          let L = a.createEl("button");
          (L.setText(o("retrieval_force_rebuild")),
            (L.style.marginLeft = "6px"),
            L.addEventListener("click", () => M("--force")));
          break;
        }
        case "deps-missing": {
          i.setText(o("retrieval_build_deps_missing"));
          let P = a.createEl("a");
          (P.setText(o("feat_install_deps")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "runtime-mismatch": {
          i.createEl("div", {
            cls: "paperforge-desc-box",
            text: o("retrieval_build_runtime_mismatch"),
            attr: { style: "color:var(--text-warning);" },
          });
          let P = a.createEl("a");
          (P.setText(o("runtime_health_sync")),
            (P.style.cssText = "cursor:pointer; text-decoration:underline;"),
            P.addEventListener("click", () => {
              this.display();
            }));
          break;
        }
        case "idle":
        default: {
          i.setText(o("retrieval_build_idle"));
          let P = a.createEl("button");
          (P.setText(o("feat_build_btn")),
            (P.className = "mod-cta"),
            P.addEventListener("click", () => M("--resume")));
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
    if (!q.existsSync(e)) {
      let r = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${r}</span>`),
        new R.Notice(r, 4e3));
      return;
    }
    try {
      q.accessSync(e, q.constants.X_OK);
    } catch (r) {
      let n = "\u4E0D\u53EF\u6267\u884C / Not executable";
      (t &&
        (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${n}</span>`),
        new R.Notice(n, 4e3));
      return;
    }
    (0, Y.execFile)(e, ["--version"], { timeout: 8e3 }, (r, n) => {
      if (r || !n) {
        let l = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      let s = n.match(/Python (\d+)\.(\d+)/);
      if (!s) {
        let l = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      let a = parseInt(s[1], 10),
        i = parseInt(s[2], 10);
      if (a < 3 || (a === 3 && i < 11)) {
        let l =
          "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.11+ / Python version too low, need 3.11+";
        (t &&
          (t.innerHTML = `<span style="color:var(--text-error)">\u2717 ${l}</span>`),
          new R.Notice(l, 4e3));
        return;
      }
      (0, Y.execFile)(e, ["-m", "pip", "--version"], { timeout: 8e3 }, (l) => {
        if (l) {
          let c = `\u2713 Python ${a}.${i} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${c}</span>`),
            new R.Notice(c, 4e3));
        } else {
          let c = `\u2713 Python ${a}.${i} \u6709\u6548 / Valid`;
          (t &&
            (t.innerHTML = `<span style="color:var(--text-accent)">${c}</span>`),
            new R.Notice(c, 4e3));
        }
      });
    });
  }
  _syncRuntime(e) {
    let t = this.app.vault.adapter.basePath,
      { path: r, extraArgs: n = [] } = K(
        t,
        this.plugin.settings,
        void 0,
        void 0
      ),
      s = this.plugin.manifest.version,
      a = Gt(r, s, n);
    (e.setDisabled(!0), e.setButtonText(o("runtime_health_syncing")));
    let i = (c, u) => (
        console.log(`[PaperForge] Sync Runtime: trying ${u}`),
        Jt(a.cmd, c, t, a.timeout, void 0, pe())
      ),
      l = () => {
        let c = "opencode";
        try {
          let h = q.readFileSync(re.join(t, "paperforge.json"), "utf-8"),
            m = JSON.parse(h);
          m.agent_key && (c = m.agent_key);
        } catch (h) {}
        let u = [
            ...n,
            "-c",
            'from paperforge.services.skill_deploy import deploy_skills; from pathlib import Path; r=deploy_skills(vault=Path(r"' +
              t.replace(/\\/g, "\\\\") +
              '"), agent_key="' +
              c +
              '", overwrite=True); print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
          ],
          f = (0, Y.spawn)(r, u, { cwd: t, timeout: 3e4, windowsHide: !0 }),
          _ = "";
        (f.stdout.on("data", (h) => {
          _ += h.toString("utf-8");
        }),
          f.on("close", (h) => {
            console.log(`[PaperForge] Skill deploy: ${_.trim()} (exit ${h})`);
          }));
      };
    i(a.pypiArgs, "PyPI").then((c) => {
      if (c.exitCode === 0) {
        (console.log("[PaperForge] Sync Runtime: installed via PyPI"),
          l(),
          new R.Notice(o("runtime_health_sync_done").replace("{0}", s), 5e3),
          this.display());
        return;
      }
      (console.warn(
        "[PaperForge] Sync Runtime: PyPI failed, falling back to git..."
      ),
        i(a.gitArgs, "git").then((u) => {
          u.exitCode === 0
            ? (console.log("[PaperForge] Sync Runtime: installed via git"),
              l(),
              new R.Notice(
                o("runtime_health_sync_done").replace("{0}", s),
                5e3
              ),
              this.display())
            : (e.setDisabled(!1),
              e.setButtonText(o("runtime_health_sync")),
              console.error("[PaperForge] git fallback stderr:", u.stderr),
              new R.Notice(
                o("runtime_health_sync_fail").replace(
                  "{0}",
                  "pip exit code " + u.exitCode
                ),
                8e3
              ));
        }));
    });
  }
  _debouncedSave() {
    (clearTimeout(this._saveTimeout),
      (this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500)));
  }
  _preCheck(e) {
    var s;
    let t = this.app.vault.adapter.basePath,
      { path: r, extraArgs: n = [] } = K(
        t,
        (s = this.plugin) == null ? void 0 : s.settings,
        void 0,
        void 0
      );
    (0, Y.execFile)(r, [...n, "--version"], { timeout: 8e3 }, (a, i) => {
      let l = [];
      l.push({
        label: "Python",
        ok: !a,
        detail: a ? o("check_python_fail") : i.trim(),
      });
      let c = !1,
        u = process.env.HOME || process.env.USERPROFILE || fr.homedir() || "";
      if (process.platform === "darwin")
        c = [
          "/Applications/Zotero.app",
          re.join(u, "Applications", "Zotero.app"),
        ].some((g) => {
          try {
            return q.existsSync(g);
          } catch (v) {
            return !1;
          }
        });
      else if (process.platform === "win32") {
        let y = process.env.ProgramFiles || "",
          g = process.env.LOCALAPPDATA || "";
        c = [
          re.join(y, "Zotero"),
          re.join(y, "(x86)", "Zotero"),
          re.join(g, "Programs", "Zotero"),
          re.join(g, "Zotero"),
          re.join(u, "AppData", "Local", "Programs", "Zotero"),
        ]
          .filter(Boolean)
          .some((w) => {
            try {
              return q.existsSync(w);
            } catch (b) {
              return !1;
            }
          });
      } else
        c = [
          re.join(u, ".local", "share", "zotero", "zotero"),
          "/usr/bin/zotero",
          "/usr/local/bin/zotero",
        ].some((g) => {
          try {
            return q.existsSync(g);
          } catch (v) {
            return !1;
          }
        });
      let f = this.plugin.settings.zotero_data_dir;
      if (!c && f)
        try {
          c = q.existsSync(f);
        } catch (y) {}
      l.push({
        label: "Zotero",
        ok: c,
        detail: c ? o("check_zotero_ok") : o("check_zotero_fail"),
      });
      let _ = !1,
        h = process.env.APPDATA || "";
      (process.platform === "win32" &&
        h &&
        (_ = et(re.join(h, "Zotero", "Zotero", "Profiles"))),
        !_ &&
          process.platform === "darwin" &&
          u &&
          (_ = et(
            re.join(u, "Library", "Application Support", "Zotero", "Profiles")
          )),
        !_ &&
          process.platform !== "win32" &&
          process.platform !== "darwin" &&
          u &&
          (_ = et(re.join(u, ".zotero", "zotero", "Profiles"))),
        !_ && f && String(f).trim() && (_ = St(f.trim())),
        !_ && u && (_ = St(re.join(u, "Zotero"))),
        l.push({
          label: "Better BibTeX",
          ok: _,
          detail: _ ? o("check_bbt_ok") : o("check_bbt_fail"),
        }));
      let m = { true: "\u2713", false: "\u2717" };
      if (this._checkEl) {
        this._checkEl.setText(
          l.map((g) => `${m[String(g.ok)]} ${g.label}: ${g.detail}`).join(`
`)
        );
        let y = l.some((g) => !g.ok);
        this._checkEl.className = `paperforge-message msg-${y ? "error" : "ok"}`;
      }
      let E = l.filter((y) => !y.ok);
      (E.length > 0 &&
        new R.Notice(
          `[!!] \u672A\u901A\u8FC7: ${E.map((y) => y.label).join(", ")}`,
          6e3
        ),
        e());
    });
  }
  _dispatchItemAction(e) {
    if (!e.action) return;
    this._pendingMaintenanceRefresh = !0;
    let t = {
      schema_version: 1,
      module: e.module,
      capability_state: e.capability_state,
      activity_state: e.activity_state,
      activity_label: e.activity_label,
      activity_progress: e.activity_progress,
      severity: e.severity,
      reason: { code: e.reason_code, text: e.reason_text },
      action: { primary: e.action },
      notices: [],
      updated_at: e.module + "-item",
      ttl_seconds: 60,
    };
    this._dispatchModuleAction(e.module, t);
  }
  _requestMaintenanceProjection() {
    if (this._probing.has("maintenance")) {
      this._pendingMaintenanceRefresh = !0;
      return;
    }
    ((this._pendingMaintenanceRefresh = !1), this._probeModule("maintenance"));
  }
  _renderMaintenanceInbox(e) {
    var i, l, c;
    let t = e.createEl("div", { cls: "pf-maintenance-inbox" }),
      r = (i = this._capabilityState) == null ? void 0 : i.maintenance;
    if (!r) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._probeModule("maintenance"));
      return;
    }
    if (
      r.activity_state === "running" &&
      ((l = r.reason) == null ? void 0 : l.code) === "maintenance.probing"
    ) {
      t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      });
      return;
    }
    if (
      r.capability_state === "ready" &&
      ((c = r.reason) == null ? void 0 : c.code) === "maintenance.no_items" &&
      Array.isArray(r.items) &&
      r.items.length === 0
    ) {
      t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text:
          o("maintenance_all_clear") ||
          "All modules are ready \u2014 no maintenance needed.",
      });
      return;
    }
    if (r.capability_state === "unknown") {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._probing.has("maintenance") || this._probeModule("maintenance"));
      return;
    }
    if (
      r.capability_state !== "ready" &&
      r.capability_state !== "needs_action"
    ) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._requestMaintenanceProjection());
      return;
    }
    let n = r.items;
    if (!n || !Array.isArray(n) || n.length === 0) {
      (t.createEl("div", {
        cls: "pf-maintenance-inbox-empty",
        text: o("maintenance_checking") || "Checking maintenance status\u2026",
      }),
        this._requestMaintenanceProjection());
      return;
    }
    (this._maintenanceNoticeShown ||
      ((this._maintenanceNoticeShown = !0),
      new R.Notice(
        o("maintenance_n_pending").replace("{n}", String(n.length)),
        5e3
      )),
      t
        .createEl("div", { cls: "pf-maintenance-inbox-summary" })
        .createEl("span", {
          text: o("maintenance_n_pending").replace("{n}", String(n.length)),
        }));
    let a = t.createEl("div", {
      cls: "pf-maintenance-inbox-list",
      attr: { role: "list" },
    });
    for (let u of n) this._renderMaintenanceInboxItem(a, u);
  }
  _renderMaintenanceInboxItem(e, t) {
    let r = this._dismissedMaintenanceItems.has(t.module),
      n = this._sevClass(t.severity),
      s = e.createEl("div", {
        cls:
          "pf-maintenance-inbox-item" +
          (r ? " pf-maintenance-inbox-item--dismissed" : ""),
        attr: { role: "listitem", "data-module": t.module },
      }),
      a = s.createEl("div", { cls: "pf-maintenance-inbox-item-info" }),
      i = o("cc_module_" + t.module) || t.module;
    a.createEl("button", {
      cls: "pf-maintenance-inbox-item-module",
      text: i,
      attr: { "data-module": t.module },
    }).addEventListener("click", () => {
      ((this._detailReturn = {
        tab: "maintenance",
        selector:
          'button.pf-maintenance-inbox-item-module[data-module="' +
          t.module +
          '"]',
      }),
        this._handleCardNavigation(t.module));
    });
    let c = this._localizeReason(t.reason_code, t.module);
    (a.createEl("div", {
      cls: "pf-maintenance-inbox-item-reason",
      text: c != null ? c : t.reason_text,
    }),
      t.activity_state === "running" &&
        t.activity_label &&
        a.createEl("div", {
          cls: "pf-maintenance-inbox-item-activity",
          text: t.activity_label,
        }));
    let u = s.createEl("div", { cls: "pf-maintenance-inbox-item-actions" });
    (u.createEl("span", {
      cls:
        "pf-maintenance-inbox-item-badge pf-maintenance-inbox-item-badge--" + n,
      text: o("cc_badge_" + (n === "ok" ? "ok" : "attention")),
    }),
      t.action &&
        u
          .createEl("button", {
            cls: "pf-maintenance-inbox-item-action",
            text: t.action.label,
          })
          .addEventListener("click", () => {
            this._dispatchItemAction(t);
          }),
      u
        .createEl("button", {
          cls: "pf-maintenance-inbox-item-dismiss",
          text: r
            ? o("maintenance_undismiss") || "Show"
            : o("maintenance_dismiss") || "Dismiss",
        })
        .addEventListener("click", () => {
          (r
            ? this._dismissedMaintenanceItems.delete(t.module)
            : this._dismissedMaintenanceItems.add(t.module),
            this.display());
        }));
  }
  _renderMaintenanceTab(e) {
    var u;
    (e.createEl("h2", {
      text: o("tab_maintenance") || "\u7EF4\u62A4",
      attr: { id: "pf-maintenance-heading", tabindex: "-1" },
    }),
      this._renderMaintenanceInbox(e),
      e.createEl("h3", {
        text: o("maintenance_ocr_section") || "OCR Maintenance",
      }));
    let r = (u = this.app.vault.adapter.basePath) != null ? u : "",
      n = e.createEl("div"),
      s = { active: "all" },
      a = null;
    try {
      a = ot(r);
    } catch (f) {}
    let i = K(r, this.plugin.settings, q, Y.execFileSync);
    if (!i.path) {
      n.createEl("p", {
        text: "\u26A0 Python \u672A\u914D\u7F6E\uFF0C\u8BF7\u5148\u5728\u300C\u5B89\u88C5\u300D\u6807\u7B7E\u9875\u914D\u7F6E\u3002",
        cls: "setting-item-description",
      });
      return;
    }
    let l = () => !!this.plugin._ocrProcess,
      c = (f) => {
        n.empty();
        let _ = f,
          h = n.createEl("div", { cls: "pf-maint-filters" }),
          m = h.createEl("button", {
            cls: "pf-maint-filter" + (s.active === "all" ? " active" : ""),
            text: o("maintenance_filter_all") || "All",
          });
        m.addEventListener("click", () => {
          ((s.active = "all"), c(f));
        });
        let E = h.createEl("button", {
          cls:
            "pf-maint-filter" + (s.active === "recommended" ? " active" : ""),
          text: o("maintenance_filter_recommended") || "Recommended",
        });
        E.addEventListener("click", () => {
          ((s.active = "recommended"), c(f));
        });
        let y =
          s.active === "recommended"
            ? _.filter((g) => g.needs_derived_rebuild === !0)
            : _;
        if (y.length === 0)
          n.createEl("p", {
            text: "\u5F53\u524D\u7B5B\u9009\u6761\u4EF6\u4E0B\u65E0\u6570\u636E",
            cls: "setting-item-description",
          });
        else {
          let g = i.path,
            v = i.extraArgs || [],
            w = n.createEl("div", { cls: "pf-maint-progress" });
          w.style.display = "none";
          let b = w.createEl("div", { cls: "paperforge-progress-track" });
          b.style.cssText = "flex:1;";
          let x = b.createEl("div", { cls: "paperforge-progress-seg done" }),
            C = b.createEl("div", { cls: "paperforge-progress-seg pending" }),
            S = w.createEl("span", { cls: "pf-maint-progress-text" }),
            k = w.createEl("span", { cls: "pf-maint-progress-key" }),
            T = w.createEl("button", { text: o("maintenance_stop") || "Stop" });
          ((T.className = "mod-warning"),
            T.addEventListener("click", () => {
              let O = this.plugin._ocrProcess;
              (O &&
                (O.stdin && typeof O.stdin.write == "function"
                  ? O.stdin.write(`PAPERFORGE_STOP
`)
                  : typeof O.kill == "function" && O.kill("SIGINT")),
                (this.plugin._ocrWasStopped = !0),
                (T.disabled = !0),
                (T.textContent = (o("maintenance_stop") || "Stop") + "\u2026"));
            }));
          let M = () => {
            let O = this.plugin._ocrProgress;
            if (!O || O.total === 0 || !this.plugin._ocrProcess) {
              w.style.display = "none";
              return;
            }
            w.style.display = "flex";
            let X =
              O.total > 0 ? ((O.current / O.total) * 100).toFixed(1) : "0";
            ((x.style.width = `${X}%`),
              (x.style.minWidth = O.current > 0 ? "2px" : "0"),
              O.current < O.total
                ? ((C.style.display = ""), (C.style.flex = "1"))
                : (C.style.display = "none"),
              (S.textContent = (
                o("maintenance_progress_label") || "{current}/{total} papers"
              )
                .replace("{current}", String(O.current))
                .replace("{total}", String(O.total))),
              (k.textContent = O.key ? ` (${O.key})` : ""));
          };
          M();
          let B = new Map();
          for (let O of y) B.set(O.key, !1);
          let F = n.createEl("div", { cls: "pf-maint-table-wrap" }),
            A = F.createEl("table", { cls: "pf-maint-table" }),
            P = A.createEl("thead"),
            L = A.createEl("tbody"),
            z = P.insertRow();
          ["", "Paper", "Status Reason", "Actions"].forEach((O) => {
            let X = document.createElement("th");
            ((X.textContent = O), z.appendChild(X));
          });
          let H = l();
          for (let O of y) {
            let X = L.insertRow(),
              de = X.insertCell();
            de.style.cssText = "padding:3px 4px;text-align:center;width:24px;";
            let he = document.createElement("input");
            ((he.type = "checkbox"),
              (he.className = "pf-maint-sel"),
              (he.checked = B.get(O.key) || !1),
              he.addEventListener("change", () => {
                (B.set(O.key, he.checked), ie());
              }),
              de.appendChild(he));
            let Ce = X.insertCell();
            Ce.style.cssText = "padding:3px 4px;";
            let I = Ce.createEl("div", { cls: "pf-maint-paper-info" });
            (I.createEl("div", {
              cls: "pf-maint-paper-title",
              text: O.title || O.key,
            }),
              I.createEl("div", { cls: "pf-maint-paper-key", text: O.key }));
            let D = X.insertCell();
            ((D.style.cssText = "padding:3px 4px;"),
              D.createEl("div", {
                cls: "pf-maint-reason",
                text: O.display_reason || "",
              }));
            let Q = X.insertCell();
            Q.style.cssText = "padding:3px 4px;white-space:nowrap;";
            let U = Q.createEl("div", { cls: "pf-maint-actions" }),
              le = Tt(O);
            if (le === "rebuild") {
              let ae = U.createEl("button", {
                cls: "pf-maint-action-btn rebuild",
                text: o("maintenance_btn_rebuild") || "Rebuild",
              });
              (H && (ae.disabled = !0),
                ae.addEventListener("click", async () => {
                  let se = await Ke(Ge(this.app), "ocr"),
                    _t = pe();
                  (0, Y.execFile)(
                    g,
                    [...v, "-m", "paperforge", "ocr", "rebuild", O.key],
                    {
                      cwd: r,
                      timeout: 12e4,
                      windowsHide: !0,
                      env: Object.assign({}, _t, se),
                    },
                    () => {
                      new R.Notice(
                        (o("maintenance_btn_rebuild") || "Rebuild") +
                          " \u2014 " +
                          O.key
                      );
                    }
                  );
                }));
            } else if (le === "redo") {
              let ae = U.createEl("button", {
                cls: "pf-maint-action-btn redo",
                text: o("ocr_maint_redo_btn") || "Redo",
              });
              (H && (ae.disabled = !0),
                ae.addEventListener("click", async () => {
                  if (
                    At("redo") &&
                    !confirm(
                      (
                        o("ocr_maint_redo_confirm") ||
                        "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced."
                      ).replace("{n}", "1")
                    )
                  )
                    return;
                  let se = await Ke(Ge(this.app), "ocr"),
                    _t = pe();
                  (0, Y.execFile)(
                    g,
                    [...v, "-m", "paperforge", "ocr", "redo", O.key],
                    {
                      cwd: r,
                      timeout: 3e5,
                      windowsHide: !0,
                      env: Object.assign({}, _t, se),
                    },
                    () => {
                      new R.Notice(
                        (o("ocr_maint_redo_btn") || "Redo OCR") +
                          " \u2014 " +
                          O.key
                      );
                    }
                  );
                }));
            }
          }
          let N = n.createEl("div", { cls: "pf-maint-batch-bar" }),
            ne = N.createEl("span", {
              cls: "pf-maint-batch-label",
              text: "0 selected",
            }),
            ie = () => {
              let O = y.filter((X) => B.get(X.key)).length;
              ne.textContent = O + " selected";
            },
            fe = N.createEl("button", {
              cls: "mod-cta",
              text: o("maintenance_batch_rebuild") || "\u25B6 Rebuild selected",
            });
          fe.disabled = H;
          let oe = N.createEl("button", {
            cls: "mod-cta",
            text:
              o("maintenance_batch_redo") || "\u25B6 Full OCR redo selected",
          });
          oe.disabled = H;
          let Z = async (O) => {
            let X = y.filter((D) => B.get(D.key) && Tt(D) === O);
            if (X.length === 0) {
              let D =
                O === "rebuild"
                  ? o("maintenance_btn_rebuild") || "Rebuild"
                  : o("ocr_maint_redo_btn") || "Redo";
              new R.Notice(
                "Selected papers are not eligible for " +
                  D +
                  ". Uncheck ineligible rows and try again.",
                6e3
              );
              return;
            }
            if (
              At(O) &&
              !confirm(
                (
                  o("ocr_maint_redo_confirm") ||
                  "Rerun OCR for {n} paper(s)? Existing derived OCR artifacts will be replaced."
                ).replace("{n}", String(X.length))
              )
            )
              return;
            let de = X.map((D) => D.key);
            ((this.plugin._ocrProgress = {
              current: 0,
              total: de.length,
              key: "",
            }),
              (this.plugin._ocrBuffer = ""),
              (this.plugin._ocrWasStopped = !1));
            let he = O === "rebuild" ? "OCR_REBUILD" : "OCR_REDO";
            ((fe.disabled = !0),
              (oe.disabled = !0),
              Array.from(F.querySelectorAll(".pf-maint-action-btn")).forEach(
                (D) => {
                  D.disabled = !0;
                }
              ),
              Array.from(F.querySelectorAll(".pf-maint-sel")).forEach((D) => {
                D.disabled = !0;
              }),
              (m.disabled = !0),
              (E.disabled = !0),
              (T.disabled = !1),
              (T.textContent = o("maintenance_stop") || "Stop"));
            let Ce = await ye(Ge(this.app), "ocr"),
              I = this._callPython(["ocr", O, ...de], {
                env: Ce,
                onData: (D) => {
                  var ae;
                  let Q =
                      typeof D == "string"
                        ? D
                        : Buffer.isBuffer(D)
                          ? D.toString("utf-8")
                          : String(D),
                    { events: U, buffer: le } = Ze(
                      Q,
                      (ae = this.plugin._ocrBuffer) != null ? ae : ""
                    );
                  this.plugin._ocrBuffer = le;
                  for (let se of U)
                    se.event === "START"
                      ? this.plugin._ocrProgress &&
                        (this.plugin._ocrProgress.total = se.total || de.length)
                      : se.event === "PROGRESS" &&
                        (this.plugin._ocrProgress = {
                          current: se.current || 0,
                          total: se.total || de.length,
                          key: se.key || "",
                        });
                  M();
                },
                onError: (D) => {
                  ((this.plugin._ocrProcess = null),
                    new R.Notice("Batch error: " + (D.message || D)),
                    c(f));
                },
                onClose: (D) => {
                  (this.plugin._ocrWasStopped || D === 130
                    ? ((this.plugin._ocrWasStopped = !1),
                      (this.plugin._ocrProcess = null),
                      M(),
                      new R.Notice("OCR batch stopped by user."))
                    : D === 0
                      ? (this.plugin._ocrProgress &&
                          (this.plugin._ocrProgress.current =
                            this.plugin._ocrProgress.total),
                        (this.plugin._ocrProcess = null),
                        M(),
                        new R.Notice(
                          (
                            o("maintenance_batch_complete") ||
                            "Batch operation complete \u2014 {n} papers processed."
                          ).replace("{n}", String(de.length))
                        ))
                      : ((this.plugin._ocrProcess = null),
                        M(),
                        new R.Notice(
                          "Batch operation finished with exit code " + D + ".",
                          8e3
                        )),
                    Ft(r, g, v, a)
                      .then((Q) => {
                        ((a = ot(r)), c(Q.data));
                      })
                      .catch(() => {
                        c(_);
                      }));
                },
              });
            ((this.plugin._ocrProcess = I), M());
          };
          (fe.addEventListener("click", () => Z("rebuild")),
            oe.addEventListener("click", () => Z("redo")),
            ie());
        }
      };
    if (a) {
      let f = Object.values(a.papers);
      c(f);
    } else
      n.createEl("p", {
        text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026",
      });
    Ft(r, i.path, i.extraArgs || [], a || null)
      .then((f) => {
        ((a = ot(r)), (f.changed || !a) && c(f.data));
      })
      .catch(() => {
        a ||
          (n.empty(),
          n.createEl("p", {
            text: "\u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002",
            cls: "setting-item-description",
          }));
      });
  }
  _renderReleaseNotesTab(e) {
    (e.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" }),
      e.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" }));
    let t = hr.default.versions || [];
    for (let s of t) {
      let a = e.createEl("div", { cls: "paperforge-release-card" }),
        i = a.createEl("div", { cls: "paperforge-release-header" });
      if (
        (i.createEl("strong", { text: `v${s.version} \u2014 ${s.title}` }),
        i.createEl("span", {
          cls: "paperforge-release-date",
          text: `  (${s.date})`,
        }),
        s.breaking_or_migration && s.breaking_or_migration.length > 0)
      ) {
        let l = a.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
        });
        for (let c of s.breaking_or_migration)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (s.new_features && s.new_features.length > 0) {
        let l = a.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u65B0\u529F\u80FD",
        });
        for (let c of s.new_features)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (s.fixes && s.fixes.length > 0) {
        let l = a.createEl("div", { cls: "paperforge-release-section" });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u4FEE\u590D",
        });
        for (let c of s.fixes)
          l.createEl("div", {
            cls: "paperforge-release-item",
            text: `\u2022 ${c}`,
          });
      }
      if (s.recommended_actions && s.recommended_actions.length > 0) {
        let l = a.createEl("div", {
          cls: "paperforge-release-section paperforge-release-recommended",
        });
        l.createEl("div", {
          cls: "paperforge-release-label",
          text: "\u5EFA\u8BAE\u64CD\u4F5C",
        });
        for (let c of s.recommended_actions)
          l.createEl("div", {
            cls: "paperforge-release-item paperforge-release-item-bold",
            text: `\u2022 ${c}`,
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
    ((this._capabilityState = zt(e != null ? e : {}, Fe)),
      this._persistCapabilityState());
  }
  _persistCapabilityState() {
    this._capabilityState &&
      ((this.plugin.settings.capabilityState = this._capabilityState),
      this.plugin.saveSettings());
  }
  _probeModule(e, t) {
    var l, c, u, f;
    if (this._probing.has(e)) return;
    this._probing.add(e);
    let r = (l = this._capabilityState) == null ? void 0 : l[e],
      n = {
        schema_version: 1,
        module: e,
        capability_state:
          (c = r == null ? void 0 : r.capability_state) != null ? c : "unknown",
        activity_state: "running",
        activity_label: "Probing...",
        activity_progress: null,
        severity: "unknown",
        reason: { code: `${e}.probing`, text: `Checking ${e} status...` },
        action: { primary: e === "maintenance" ? null : je(e) },
        notices: (u = r == null ? void 0 : r.notices) != null ? u : [],
        updated_at: new Date().toISOString(),
        ttl_seconds: (f = r == null ? void 0 : r.ttl_seconds) != null ? f : 0,
      };
    this._updateCapabilityEnvelope(e, n);
    let s = this.app.vault.adapter.basePath,
      a = this._resolveRuntimeCommand(s);
    if (!a) {
      if ((this._probing.delete(e), e === "installation")) {
        let _ = {
          schema_version: 1,
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
          action: { primary: $t() },
          notices: [],
          updated_at: new Date().toISOString(),
          ttl_seconds: 60,
        };
        this._updateCapabilityEnvelope(e, _);
      } else this._updateCapabilityEnvelope(e, De(e));
      return;
    }
    let i = [...a.args, "-m", "paperforge", "--vault", s, "probe", e, "--json"];
    (e === "library" &&
      t != null &&
      t !== 0 &&
      i.push("--last-operation-exit-code", String(t)),
      (0, Y.execFile)(a.path, i, { cwd: s, timeout: 15e3 }, (_, h, m) => {
        if ((this._probing.delete(e), _)) {
          (console.warn(`[PaperForge] Probe ${e} failed:`, _.message),
            this._updateCapabilityEnvelope(e, De(e)));
          return;
        }
        try {
          let E = JSON.parse(h);
          gt(E, e)
            ? this._updateCapabilityEnvelope(e, E)
            : (console.warn(
                `[PaperForge] Probe ${e}: invalid envelope schema`,
                h == null ? void 0 : h.slice(0, 200)
              ),
              this._updateCapabilityEnvelope(e, De(e)));
        } catch (E) {
          (console.warn(
            `[PaperForge] Probe ${e}: unparseable JSON`,
            h == null ? void 0 : h.slice(0, 200)
          ),
            this._updateCapabilityEnvelope(e, De(e)));
        }
      }));
  }
  _updateCapabilityEnvelope(e, t) {
    this._capabilityState || (this._capabilityState = {});
    let r = this._capabilityState[t.module];
    ((this._capabilityState[t.module] = t),
      this._persistCapabilityState(),
      (r == null ? void 0 : r.activity_state) === "running" &&
        t.activity_state !== "running" &&
        (new R.Notice(o("cc_notice_refreshed"), 3e3),
        t.module !== "maintenance"
          ? (this._pendingMaintenanceRefresh ||
              this.activeTab === "maintenance") &&
            this._requestMaintenanceProjection()
          : this._pendingMaintenanceRefresh &&
            ((this._pendingMaintenanceRefresh = !1),
            this._probeModule("maintenance"))),
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
      n = o(r);
    if (n !== r) return n.replace("{module}", t);
    let a = "cc_reason_" + e.replace(/^[a-z]+\./, ""),
      i = o(a);
    return i === a ? null : i.replace("{module}", t);
  }
  _renderCard(e, t, r) {
    let n = r,
      s = this._sevClass(n.severity),
      a = Se._REAL_PROBE.has(t),
      i = Se._NAVIGABLE.has(t),
      l = e.createEl("div", {
        cls: "pf-cc-card",
        attr: {
          role: "listitem",
          tabindex: "0",
          "data-module": t,
          "aria-label": `${o("cc_module_" + t)} \u2014 ${o(this._ccBadgeKey(n, t))}`,
        },
      }),
      c = l.createEl("div", { cls: "pf-cc-card-header" }),
      u = c.createEl("div", { cls: "pf-cc-card-name-area" });
    if (i) {
      let x =
          t === "installation"
            ? o("module_detail_open_installation")
            : t === "library"
              ? o("module_detail_open_library")
              : t === "ocr"
                ? o("module_detail_open_ocr")
                : t === "memory"
                  ? o("module_detail_open_memory")
                  : t === "help"
                    ? o("module_detail_open_help")
                    : t === "maintenance"
                      ? o("module_detail_open_maintenance")
                      : o("md_select_installation"),
        C = u.createEl("button", {
          cls: "pf-open-module-btn",
          text: o("cc_module_" + t),
          attr: { "data-module": t, "aria-label": x },
        });
      (C.addEventListener("click", () => this._handleCardNavigation(t)),
        C.addEventListener("keydown", (S) => {
          (S.key === "Enter" || S.key === " ") &&
            (S.preventDefault(), this._handleCardNavigation(t));
        }));
    } else
      u.createEl("div", { cls: "pf-cc-card-name", text: o("cc_module_" + t) });
    c.createEl("div", {
      cls: `pf-cc-card-badge pf-cc-card-badge--${s}`,
      text: o(this._ccBadgeKey(n, t)),
    });
    let f;
    if (!a)
      f = o("cc_reason_placeholder").replace("{module}", o("cc_module_" + t));
    else {
      let x = this._localizeReason(n.reason.code, t);
      f = x != null ? x : n.reason.text;
    }
    if (
      (l.createEl("div", { cls: "pf-cc-card-reason", text: f }),
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
        let C = Math.round(
            (n.activity_progress.current / n.activity_progress.total) * 100
          ),
          k = x
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
        k.style.width = C + "%";
      }
    }
    let _ = l.createEl("div", { cls: "pf-cc-card-footer" });
    if (a && n.action.primary && !$e(n)) {
      let x = ze(n),
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
          ? new Ae(this.app, this.plugin, () => {
              (this._probeModule("installation"), this._probeModule("help"));
            }).open()
          : this._dispatchModuleAction(t, n);
      });
    }
    let h = l.createEl("details", { cls: "pf-cc-card-diagnostic" });
    h.createEl("summary", { text: o("cc_diagnostic_toggle") });
    let m = h.createEl("div", { cls: "pf-cc-card-diagnostic-body" }),
      E = o("cc_state_" + n.capability_state) || n.capability_state,
      y = o("cc_severity_" + n.severity) || n.severity,
      g = o("cc_activity_" + n.activity_state) || n.activity_state,
      v;
    try {
      v = new Date(n.updated_at).toLocaleString();
    } catch (x) {
      v = n.updated_at;
    }
    (m.createEl("div", { text: `${o("cc_diag_module")}: ${n.module}` }),
      m.createEl("div", { text: `${o("cc_diag_state")}: ${E}` }),
      m.createEl("div", { text: `${o("cc_diag_severity")}: ${y}` }),
      m.createEl("div", { text: `${o("cc_diag_activity")}: ${g}` }));
    let w = m.createEl("div");
    w.appendText(o("cc_diag_reason") + ": " + f + " ");
    let b = w.createEl("code", { text: n.reason.code });
    (m.createEl("div", {
      text: `${o("cc_diag_ttl")}: ${String(n.ttl_seconds)}s`,
    }),
      m.createEl("div", { text: `${o("cc_diag_updated")}: ${v}` }));
  }
  _handleCardNavigation(e) {
    (e === "installation"
      ? ((this.activeTab = "module-detail"),
        (this._selectedDetailModule = "installation"),
        (this._focusTargetId = "#pf-installation-detail-heading"))
      : e === "library"
        ? ((this.activeTab = "module-detail"),
          (this._selectedDetailModule = "library"),
          (this._focusTargetId = "#pf-library-detail-heading"))
        : e === "ocr"
          ? ((this.activeTab = "module-detail"),
            (this._selectedDetailModule = "ocr"),
            (this._focusTargetId = "#pf-ocr-detail-heading"))
          : e === "memory"
            ? ((this.activeTab = "module-detail"),
              (this._selectedDetailModule = "memory"),
              (this._focusTargetId = "#pf-memory-detail-heading"))
            : e === "help"
              ? ((this.activeTab = "help"),
                (this._selectedDetailModule = ""),
                (this._focusTargetId =
                  "button.pf-open-module-btn[data-module=help]"))
              : e === "maintenance" &&
                ((this.activeTab = "maintenance"),
                (this._selectedDetailModule = ""),
                (this._focusTargetId = "#pf-maintenance-heading"),
                (this._maintenanceNoticeShown = !1)),
      this.display());
  }
  _renderControlCenter(e) {
    var h, m, E;
    let t = e.createEl("div", { cls: "pf-control-center" }),
      r = Fe,
      n = (h = this._capabilityState) != null ? h : {},
      s = 0,
      a = 0,
      i = 0;
    for (let y of r) {
      let g = (m = n[y]) != null ? m : Te(y);
      g.severity === "ok" &&
      g.capability_state === "ready" &&
      g.action.primary === null
        ? s++
        : Se._REAL_PROBE.has(y)
          ? (g.severity === "error" ||
              g.severity === "warning" ||
              g.severity === "unknown") &&
            a++
          : i++;
    }
    let l = t.createEl("div", { cls: "pf-cc-summary" });
    l.createEl("div", { cls: "pf-cc-summary-eyebrow", text: o("cc_title") });
    let c, u;
    (a > 0
      ? ((c = o("cc_summary_attention")), (u = o("cc_summary_attention_body")))
      : s === r.length
        ? ((c = o("cc_summary_ok")), (u = o("cc_summary_ok_body")))
        : s > 0 && i > 0 && a === 0
          ? ((c = o("cc_summary_core_ok").replace("{n}", String(i))),
            (u = o("cc_summary_core_ok_body")))
          : ((c = o("cc_summary_core_ok").replace("{n}", String(r.length - s))),
            (u = o("cc_desc"))),
      l.createEl("div", { cls: "pf-cc-summary-title", text: c }),
      l.createEl("div", { cls: "pf-cc-summary-body", text: u }));
    let f = l.createEl("div", { cls: "pf-cc-summary-counts" });
    (f.createEl("div", {
      cls: "pf-cc-summary-count",
      text: o("cc_n_ready").replace("{n}", String(s)),
    }),
      i > 0 &&
        f.createEl("div", {
          cls: "pf-cc-summary-count",
          text: o("cc_n_pending").replace("{n}", String(i)),
        }));
    let _ = t.createEl("div", {
      cls: "pf-cc-grid",
      attr: { role: "list", "aria-label": o("cc_zone_modules") },
    });
    for (let y of r) {
      let g = (E = n[y]) != null ? E : Te(y);
      this._renderCard(_, y, g);
    }
  }
  _applyStaleTolerance() {
    if (!this._capabilityState) return;
    let e = !1;
    for (let t of Fe) {
      let r = this._capabilityState[t];
      r && yt(r) && ((this._capabilityState[t] = mt(t)), (e = !0));
    }
    e && this._persistCapabilityState();
  }
};
((Se._REAL_PROBE = new Set([
  "installation",
  "library",
  "ocr",
  "memory",
  "help",
  "maintenance",
])),
  (Se._NAVIGABLE = new Set([
    "installation",
    "library",
    "ocr",
    "memory",
    "maintenance",
    "help",
  ])));
var pt = Se;
var V = require("obsidian"),
  Ee = $(require("fs")),
  Xe = $(require("path")),
  xe = require("child_process");
var Je = $(require("path"));
function gr(p) {
  if (!p) return null;
  let d = Je.dirname(p);
  for (;;) {
    let e = Je.basename(d);
    if (!e || e === ".") break;
    let t = e.match(/^([A-Z0-9]{8})(?:\s*-\s*.*)?$/i);
    if (t) return t[1];
    let r = Je.dirname(d);
    if (r === d) break;
    d = r;
  }
  return null;
}
var G = $(require("fs")),
  Pe = $(require("path"));
function Ye(p) {
  return ue(p).ocrDir;
}
function zr(p, d) {
  let e = Pe.join(Ye(p), d, "versions", "manifest.json");
  try {
    if (!G.existsSync(e)) return null;
    let t = G.readFileSync(e, "utf-8"),
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
function Kr(p) {
  let d = Ye(p);
  try {
    return G.existsSync(d)
      ? G.readdirSync(d, { withFileTypes: !0 })
          .filter((e) => e.isDirectory())
          .map((e) => e.name)
      : [];
  } catch (e) {
    return [];
  }
}
function Mt(p) {
  let d = Kr(p),
    e = [];
  for (let t of d) {
    let r = zr(p, t);
    if (!r) continue;
    let n = r.versions.map((a) => a.label),
      s = 0;
    for (let a of n) {
      let i = Pe.join(Ye(p), t, "versions", a, "fulltext.md");
      try {
        G.existsSync(i) && (s += G.statSync(i).size);
      } catch (l) {}
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
function yr(p, d, e) {
  let t = Ye(p),
    r = Pe.join(t, d, "versions", e, "fulltext.md"),
    n = Pe.join(t, d, "render"),
    s = Pe.join(n, "fulltext.md");
  try {
    return G.existsSync(r)
      ? (G.existsSync(n) || G.mkdirSync(n, { recursive: !0 }),
        G.copyFileSync(r, s),
        !0)
      : !1;
  } catch (a) {
    return !1;
  }
}
function br(p, d, e, t) {
  var _;
  let r = Ye(p),
    n = Pe.join(r, d, "versions", e, "fulltext.md"),
    s = Pe.join(r, d, "versions", t, "fulltext.md"),
    a = "",
    i = "";
  try {
    G.existsSync(n) && (a = G.readFileSync(n, "utf-8"));
  } catch (h) {}
  try {
    G.existsSync(s) && (i = G.readFileSync(s, "utf-8"));
  } catch (h) {}
  let l = mr(a),
    c = mr(i),
    u = Math.max(l.length, c.length),
    f = [];
  for (let h = 0; h < u; h++) {
    let m = h < l.length ? l[h] : "",
      E = h < c.length ? c[h] : "",
      y =
        (_ = (m || E).split(`
`)[0]) != null
          ? _
          : "",
      g = y.startsWith("## ") ? y.replace(/^##\s+/, "") : "",
      v = "unchanged";
    (!m && E
      ? (v = "added")
      : m && !E
        ? (v = "removed")
        : m !== E && (v = "changed"),
      v !== "unchanged" &&
        f.push({
          paragraphIndex: h,
          heading: g,
          type: v,
          oldText: m || void 0,
          newText: E || void 0,
        }));
  }
  return f;
}
function mr(p) {
  let d = p.split(`
`),
    e = [],
    t = [];
  for (let r of d)
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
var Ie = class extends V.ItemView {
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
  getViewType() {
    return Re;
  }
  getDisplayText() {
    return "PaperForge";
  }
  getIcon() {
    return Ve;
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
    var a, i;
    let e = this.app.vault.adapter.basePath,
      t = this.app.plugins.plugins.paperforge,
      r =
        ((a = t == null ? void 0 : t.manifest) == null ? void 0 : a.version) ||
        "?",
      { path: n, extraArgs: s = [] } = K(
        e,
        (i = t == null ? void 0 : t.settings) != null ? i : null,
        void 0,
        void 0
      );
    Zt(n, r, e, 1e4, void 0).then((l) => {
      if (l.status === "not-installed") return;
      let c = l.pyVersion || "";
      ((this._paperforgeVersion = c.startsWith("v") ? c : "v" + c),
        this._versionBadge &&
          this._versionBadge.setText(this._paperforgeVersion),
        this._driftBannerEl &&
        r &&
        this._paperforgeVersion !== "v" + r.replace(/^v/, "")
          ? ((this._driftBannerEl.style.display = "block"),
            this._driftBannerEl.setText(
              o("dashboard_drift_warning")
                .replace("{0}", this._paperforgeVersion)
                .replace("{1}", "v" + r.replace(/^v/, ""))
            ))
          : this._driftBannerEl &&
            (this._driftBannerEl.style.display = "none"));
    });
  }
  _fetchStats(e) {
    var a;
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
      { path: n, extraArgs: s = [] } = K(
        t,
        (a = r == null ? void 0 : r.settings) != null ? a : null,
        void 0,
        void 0
      );
    (0, xe.execFile)(
      n,
      [...s, "-m", "paperforge", "dashboard", "--json"],
      { cwd: t, timeout: 3e4 },
      (i, l) => {
        if (!i)
          try {
            let c = JSON.parse(l);
            if (c.ok && c.data) {
              let u = this._normalizeDashboardData(c.data);
              ((this._cachedStats = u),
                this._metricsEl.empty(),
                this._renderStats(u),
                this._renderOcr(u),
                (this._dashboardPermissions = c.data.permissions || {}));
              return;
            }
          } catch (c) {}
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
    var a, i, l;
    let n =
        ((a = r == null ? void 0 : r.settings) == null
          ? void 0
          : a.system_dir) || "System",
      s = Xe.join(t, n, "PaperForge", "indexes", "formal-library.json");
    try {
      let c = Ee.readFileSync(s, "utf-8"),
        u = JSON.parse(c),
        f = u.items || [],
        _ = {},
        h = {
          pdf_health: { healthy: 0, unhealthy: 0 },
          ocr_health: { healthy: 0, unhealthy: 0 },
          note_health: { healthy: 0, unhealthy: 0 },
          asset_health: { healthy: 0, unhealthy: 0 },
        },
        m = 0,
        E = 0,
        y = 0,
        g = 0,
        v = 0,
        w = 0;
      for (let b of f) {
        b.note_path && w++;
        let x = b.lifecycle || "pdf_ready";
        _[x] = (_[x] || 0) + 1;
        let C = b.health || {};
        for (let k of [
          "pdf_health",
          "ocr_health",
          "note_health",
          "asset_health",
        ])
          (C[k] || "healthy") === "healthy" ? h[k].healthy++ : h[k].unhealthy++;
        let S = b.ocr_status || "";
        (m++,
          S === "done"
            ? E++
            : S === "pending"
              ? y++
              : S === "processing" || S === "queued" || S === "running"
                ? g++
                : v++);
      }
      ((this._cachedStats = {
        version:
          u.paperforge_version ||
          ((i = this._cachedStats) == null ? void 0 : i.version) ||
          "\u2014",
        total_papers: f.length,
        formal_notes: w,
        exports: 0,
        bases: 0,
        ocr: { total: m, pending: y, processing: g, done: E, failed: v },
        path_errors: 0,
        lifecycle_level_counts: _,
        health_aggregate: h,
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
      let { path: u, extraArgs: f = [] } = K(
        t,
        (l = r == null ? void 0 : r.settings) != null ? l : null,
        void 0,
        void 0
      );
      (0, xe.execFile)(
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
            let m = JSON.parse(h);
            ((this._cachedStats = m),
              this._metricsEl.empty(),
              this._renderStats(m),
              this._renderOcr(m));
          } catch (m) {
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
      n = Xe.join(e, r, "PaperForge", "indexes", "formal-library.json");
    try {
      let a = Ee.readFileSync(n, "utf-8");
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
    return jt(this.app, t);
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
    for (let i of n) {
      let l = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (l.style.setProperty("--metric-color", i.color),
        l.createEl("div", {
          cls: "paperforge-metric-value",
          text: ((a = i.value) == null ? void 0 : a.toString()) || "\u2014",
        }),
        l.createEl("div", { cls: "paperforge-metric-label", text: i.label }),
        i.barMax > 0 && this._buildMetricBar(l, i.value, i.barMax));
    }
    let s = e.ocr_version_state || {};
    if (
      s.total_papers > 0 &&
      (s.derived_stale_count > 0 || s.raw_upgradable_count > 0)
    ) {
      let i = [];
      (s.derived_stale_count > 0 && i.push(`${s.derived_stale_count} stale`),
        s.raw_upgradable_count > 0 &&
          i.push(`${s.raw_upgradable_count} upgradable`));
      let l = this._metricsEl.createEl("div", {
        cls: "paperforge-metric-card",
      });
      (l.style.setProperty("--metric-color", "var(--color-yellow)"),
        l.createEl("div", {
          cls: "paperforge-metric-value",
          text: i.join(", "),
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
      s = t.pending || 0,
      a = t.processing || 0,
      i = t.failed || 0;
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
      let l = [
        { cls: "pending", count: s },
        { cls: "active", count: a },
        { cls: "done", count: n },
        { cls: "failed", count: i },
      ];
      for (let c of l)
        if (c.count > 0) {
          let u = ((c.count / r) * 100).toFixed(1);
          this._ocrTrack.createEl("div", {
            cls: `paperforge-progress-seg ${c.cls}`,
            attr: { style: `width:${u}%` },
          });
        }
    }
    if (this._ocrCounts) {
      this._ocrCounts.empty();
      let l = [
        { cls: "pending", value: s, label: "Pending" },
        { cls: "active", value: a, label: "Processing" },
        { cls: "done", value: n, label: "Done" },
        { cls: "failed", value: i, label: "Failed" },
      ];
      for (let c of l) {
        let u = this._ocrCounts.createEl("div", {
          cls: "paperforge-ocr-count",
        });
        (u.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: c.value.toString(),
        }),
          u.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: c.label,
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
    for (let i of n) {
      let l = s.createEl("div", { cls: "step" });
      (l.createEl("div", { cls: "step-indicator" }),
        l.createEl("div", { cls: "step-label", text: i.label }),
        i.key === r
          ? (l.addClass("current"), (a = !0))
          : a
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
    for (let s of r) {
      let a = t[s.key] || "healthy",
        i = n.createEl("div", { cls: "paperforge-health-cell" }),
        l,
        c,
        u;
      (a === "healthy" || a === "ok"
        ? ((l = s.iconOk), (c = "ok"), (u = `${s.label}: OK`))
        : a === "warn" || a === "warning" || a === "degraded"
          ? ((l = s.iconWarn),
            (c = "warn"),
            (u = `${s.label}: Needs Attention`))
          : ((l = s.iconFail), (c = "fail"), (u = `${s.label}: Failed`)),
        i.addClass(c),
        i.setAttribute("title", u),
        i.createEl("div", { cls: "paperforge-health-cell-icon", text: l }),
        i.createEl("div", {
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
      i = Math.max(1, Math.min(a, Math.round(t)));
    for (let l = 1; l <= a; l++) {
      let c = s.createEl("div", { cls: "gauge-segment" });
      l <= i && (c.addClass("filled"), c.addClass(`level-${l}`));
    }
    if (
      (n.createEl("div", { cls: "gauge-level", text: `Level ${i} / ${a}` }),
      i < a && r)
    ) {
      let l = typeof r == "string" ? [r] : r;
      if (l.length > 0) {
        let c = n.createEl("ul", { cls: "gauge-blockers" });
        for (let u of l) c.createEl("li", { text: u });
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
      let i = t[a.key] || 0,
        l = (i / s) * 100,
        c = n.createEl("div", { cls: "bar-row" });
      (c.createEl("div", { cls: "bar-label", text: a.label }),
        c
          .createEl("div", { cls: "bar-track" })
          .createEl("div", {
            cls: `bar-fill ${a.cls}`,
            attr: { style: `width:${l.toFixed(1)}%` },
          }),
        c.createEl("div", { cls: "bar-count", text: i.toString() }));
    }
  }
  _invalidateIndex() {
    this._cachedItems = null;
  }
  _extractZoteroKeyFromPath(e) {
    return gr(e);
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
        let i = (a.pdf_path || "").match(/\[\[([^\]]+)\]\]/);
        if ((i ? i[1] : a.pdf_path) === r)
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
    var ie, fe, oe, Z, O, X, de, he, Ce;
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
      a = 0;
    for (let I of t)
      (I.has_pdf && n++,
        I.ocr_status === "done" && s++,
        I.deep_reading_status === "done" && a++);
    let i = e.createEl("div", { cls: "paperforge-library-snapshot" });
    i.createEl("div", {
      cls: "paperforge-section-label",
      text: "Library Snapshot",
    });
    let l = i.createEl("div", { cls: "paperforge-snapshot-pills" }),
      c = [
        { value: r, label: "papers" },
        { value: n, label: "PDFs ready" },
        { value: s, label: "OCR done" },
        { value: a, label: "deep-read done" },
      ];
    for (let I of c) {
      let D = l.createEl("div", { cls: "paperforge-snapshot-pill" });
      (D.createEl("span", {
        cls: "paperforge-snapshot-value",
        text: String(I.value),
      }),
        D.createEl("span", {
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
      h =
        ((ie = _ == null ? void 0 : _.manifest) == null
          ? void 0
          : ie.version) || "?",
      m = this._paperforgeVersion;
    if (!m)
      try {
        let I = this.app.vault.adapter.basePath,
          { path: D, extraArgs: Q = [] } = K(
            I,
            (fe = _ == null ? void 0 : _.settings) != null ? fe : null,
            void 0,
            void 0
          ),
          U = (0, xe.execFileSync)(
            D,
            [...Q, "-c", "import paperforge; print(paperforge.__version__)"],
            { cwd: I, timeout: 5e3, encoding: "utf-8", windowsHide: !0 }
          ).trim();
        U &&
          ((m = U.startsWith("v") ? U : "v" + U),
          (this._paperforgeVersion = m));
      } catch (I) {}
    m = m || "\u2014";
    let E = m === "v" + h;
    this._renderSystemStatusRow(
      f,
      "Runtime",
      E ? "healthy" : "mismatch",
      E ? "v" + h : "plugin v" + h + " \u2260 CLI " + m
    );
    let y = this._loadIndex(),
      g = y && y.items && y.items.length > 0;
    this._renderSystemStatusRow(
      f,
      "Index",
      g ? "healthy" : "missing",
      g ? y.items.length + " entries" : "formal-library.json not found"
    );
    let v =
        ((oe = _ == null ? void 0 : _.settings) == null
          ? void 0
          : oe.system_dir) || "System",
      w = this.app.vault.adapter.basePath,
      b = !1,
      x = "No exports found";
    try {
      let I = Xe.join(w, v, "PaperForge", "exports");
      if (Ee.existsSync(I)) {
        let D = Ee.readdirSync(I).filter((Q) => Q.endsWith(".json"));
        ((b = D.length > 0),
          (x = b ? D.length + " export(s)" : "No JSON exports"));
      }
    } catch (I) {}
    this._renderSystemStatusRow(
      f,
      "Zotero Export",
      b ? "healthy" : "missing",
      x
    );
    let C =
        (O = (Z = this.app.plugins) == null ? void 0 : Z.plugins) == null
          ? void 0
          : O.paperforge,
      S = !!(
        (X = C == null ? void 0 : C.settings) != null && X._paddleocr_configured
      );
    if (!S)
      try {
        let I =
            ((de = _ == null ? void 0 : _.settings) == null
              ? void 0
              : de.system_dir) || "System",
          D = Xe.join(w, I, "PaperForge", ".env");
        if (Ee.existsSync(D)) {
          let U = Ee.readFileSync(D, "utf-8").match(
            /^PADDLEOCR_API_TOKEN\s*=\s*(.+)$/m
          );
          S = !!(U && U[1] && U[1].trim());
        }
      } catch (I) {}
    (S ||
      (S = !!(
        process.env.PADDLEOCR_API_TOKEN ||
        process.env.PADDLEOCR_API_KEY ||
        process.env.OCR_TOKEN
      )),
      this._renderSystemStatusRow(
        f,
        "OCR Token",
        S ? "configured" : "missing",
        S ? "Configured" : "Not set"
      ));
    let k = !1,
      T = "",
      M = this.app.vault.adapter.basePath,
      B = Ue(M);
    ((k = Xt(M)),
      (T =
        (B && ((he = B.summary) == null ? void 0 : he.reason)) ||
        (B && ((Ce = B.summary) == null ? void 0 : Ce.status)) ||
        "Unknown"),
      this._renderSystemStatusRow(
        f,
        "Memory Layer",
        k ? "healthy" : "fail",
        T
      ));
    let F = !E && m !== "\u2014";
    if (F || !g || !b || !S) {
      let I = e.createEl("div", { cls: "paperforge-issue-summary" });
      I.createEl("div", {
        cls: "paperforge-section-label",
        text: "\u9700\u8981\u5904\u7406",
      });
      let D = I.createEl("div", { cls: "paperforge-issue-list" });
      (F &&
        D.createEl("div", {
          cls: "paperforge-issue-item",
          text: "Runtime version mismatch",
        }),
        g ||
          D.createEl("div", {
            cls: "paperforge-issue-item",
            text: "Index missing or corrupted",
          }),
        b ||
          D.createEl("div", {
            cls: "paperforge-issue-item",
            text: "No Zotero export found",
          }),
        S ||
          D.createEl("div", {
            cls: "paperforge-issue-item",
            text: "PaddleOCR API key not configured",
          }));
      let Q = I.createEl("div", { cls: "paperforge-issue-actions" }),
        U = Q.createEl("button", { cls: "paperforge-contextual-btn" });
      (U.createEl("span", { text: "Run Doctor" }),
        U.addEventListener("click", () => {
          let ae = ce.find((se) => se.id === "paperforge-doctor");
          ae && this._runAction(ae, U);
        }));
      let le = Q.createEl("button", { cls: "paperforge-contextual-btn" });
      (le.createEl("span", { text: "Repair Issues" }),
        le.addEventListener("click", () => {
          let ae = ce.find((se) => se.id === "paperforge-repair");
          ae && this._runAction(ae, le);
        }));
    }
    let P = e.createEl("div", { cls: "paperforge-global-actions" });
    P.createEl("div", {
      cls: "paperforge-section-label",
      text: "Start Working",
    });
    let L = P.createEl("div", { cls: "paperforge-global-actions-row" }),
      z = L.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (z.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u{1F4C1}",
    }),
      z.createEl("span", { text: "Open Literature Hub" }),
      z.addEventListener("click", () => {
        var Q;
        let I =
            ((Q = _ == null ? void 0 : _.settings) == null
              ? void 0
              : Q.base_dir) || "Bases",
          D = this.app.vault.getAbstractFileByPath(I);
        if (D) {
          let U = null;
          if (
            (D.children &&
              (U = D.children.find((le) => le.extension === "base")),
            U)
          ) {
            let le = this.app.workspace.getLeaf(!1);
            le && le.openFile(U);
          } else new V.Notice("[!!] No .base file found in " + I, 6e3);
        } else new V.Notice("[!!] Base directory not found: " + I, 6e3);
      }));
    let H = L.createEl("button", { cls: "paperforge-contextual-btn" });
    (H.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      H.createEl("span", { text: "Sync Library" }),
      H.addEventListener("click", () => {
        let I = ce.find((D) => D.id === "paperforge-sync");
        I && this._runAction(I, H);
      }));
    let N = L.createEl("button", { cls: "paperforge-contextual-btn" });
    (N.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      N.createEl("span", { text: "Run OCR" }),
      N.addEventListener("click", () => {
        let I = ce.find((D) => D.id === "paperforge-ocr");
        I && this._runAction(I, N);
      }));
    let ne = L.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (ne.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      ne.createEl("span", { text: "Redo OCR" }),
      ne.addEventListener("click", () => {
        let I = ce.find((D) => D.id === "paperforge-ocr-redo");
        I && this._runAction(I, ne);
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
        new V.Notice("Title copied"));
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
    let i = r.createEl("div", { cls: "paperforge-status-strip" }),
      l = i.createEl("div", { cls: "paperforge-status-strip-left" }),
      c = i.createEl("div", { cls: "paperforge-status-strip-right" }),
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
      let h = l.createEl("span", { cls: "paperforge-status-pill" }),
        m = "pending";
      (_.ok ? (m = "ok") : _.fail ? (m = "fail") : _.pending && (m = "pending"),
        h.addClass(m));
      let E = _.ok ? "\u2713" : _.fail ? "\u2717" : "\u25CB";
      (h.createEl("span", { cls: "paperforge-status-pill-icon", text: E }),
        h.createEl("span", { text: " " + _.label }));
    }
    if (e.pdf_path) {
      let _ = c.createEl("button", { cls: "paperforge-contextual-btn" });
      (_.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4C4}",
      }),
        _.createEl("span", { text: "\u6253\u5F00 PDF" }),
        _.addEventListener("click", () => {
          let h = e.pdf_path.match(/\[\[([^\]]+)\]\]/),
            m = h ? h[1] : e.pdf_path;
          this.app.vault.getAbstractFileByPath(m)
            ? this.app.workspace.openLinkText(m, "")
            : new V.Notice("[!!] PDF not found: " + m, 6e3);
        }));
    }
    if (e.fulltext_path) {
      let _ = c.createEl("button", { cls: "paperforge-contextual-btn" });
      (_.createEl("span", {
        cls: "paperforge-contextual-btn-icon",
        text: "\u{1F4DD}",
      }),
        _.createEl("span", { text: "\u6253\u5F00\u5168\u6587" }),
        _.addEventListener("click", () => this._openFulltext(e.fulltext_path)));
    }
    let f = c.createEl("button", { cls: "paperforge-contextual-btn" });
    if (
      (f.createEl("span", { text: o("version_panel_title") }),
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
      a = s.createEl("div", {
        cls: "paperforge-paper-overview-excerpt",
        text: "\u52A0\u8F7D\u4E2D...",
      });
    if (t.note_path) {
      let i = this.app.vault.getAbstractFileByPath(t.note_path);
      i
        ? this.app.vault
            .read(i)
            .then((l) => {
              let c = this._extractOverviewFromNote(l);
              if (c) {
                let u = c.length > 200 ? c.slice(0, 200) + "..." : c;
                if ((a.setText(u), c.length > 200)) {
                  let f = s.createEl("div", {
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
                    (a.setText(h ? u : c),
                      (_.innerHTML = h
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
    for (let i of n) {
      let l = r.indexOf(i);
      if (l !== -1) {
        let c = r.slice(l + i.length),
          u = ["**5 Cs", "**Figure", "**\u8BC1\u636E", "### Pass 2", "## "],
          f = c.length;
        for (let m of u) {
          let E = c.indexOf(m);
          E !== -1 && E < f && (f = E);
        }
        let _ = c.indexOf(`

`);
        _ !== -1 && _ < f && (f = _);
        let h = c.slice(0, f).trim();
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
      .then((i) => {
        if (i) return this.app.vault.adapter.read(a);
      })
      .then(async (i) => {
        if (!i) return;
        let l = this._parseDiscussionMD(i);
        if (!l || l.length === 0) return;
        ((r.style.display = "block"),
          r
            .createEl("div", { cls: "paperforge-discussion-header" })
            .createEl("span", {
              cls: "paperforge-discussion-title",
              text: "\u6700\u8FD1\u8BA8\u8BBA",
            }));
        for (let f of l) {
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
          let m = _.createEl("div", { cls: "paperforge-discussion-a" }),
            E = !1;
          if (
            (f.answer &&
              f.answer.length > 500 &&
              ((E = !0), m.classList.add("paperforge-discussion-a-collapsed")),
            await V.MarkdownRenderer.render(
              this.app,
              f.answer || "",
              m,
              a,
              this
            ),
            E)
          ) {
            let y = !1;
            ((_.style.cursor = "pointer"),
              _.addEventListener("click", () => {
                ((y = !y),
                  m.classList.toggle("paperforge-discussion-a-collapsed", !y),
                  m.classList.toggle("paperforge-discussion-a-expanded", y));
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
              : new V.Notice(
                  "\u8BA8\u8BBA\u6587\u4EF6\u5C1A\u672A\u751F\u6210"
                ));
        });
      })
      .catch((i) => {
        console.error("PaperForge: discussion.md read error", a, i.message);
      });
  }
  _parseDiscussionMD(e) {
    let t = e.split(/\n## /).slice(1);
    if (t.length === 0) return null;
    let r = t[t.length - 1],
      n = [],
      s = r.split(/\*\*\u95EE\u9898:\*\*/).slice(1);
    for (let a of s) {
      let i = a.match(/\*\*\u89E3\u7B54:\*\*/);
      if (!i) continue;
      let l = a.substring(0, i.index).trim(),
        c = a.substring(i.index + 3 + 4).trim();
      n.push({ question: l, answer: c });
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
        let _ = a.style.display !== "none";
        ((a.style.display = _ ? "none" : "block"),
          s.setText(
            _
              ? "\u6280\u672F\u8BE6\u60C5 \u25B8"
              : "\u6280\u672F\u8BE6\u60C5 \u25BE"
          ),
          (this._techDetailsExpanded = !_));
      }));
    let i = a.createEl("div", { cls: "paperforge-workflow-toggles" }),
      l = [
        { key: "do_ocr", label: "OCR", hint: "\u52A0\u5165 OCR" },
        {
          key: "analyze",
          label: "\u7CBE\u8BFB",
          hint: "\u6807\u8BB0\u7CBE\u8BFB",
        },
      ];
    for (let _ of l) {
      let h = i.createEl("label", { cls: "paperforge-workflow-toggle" }),
        m = h.createEl("input", {
          type: "checkbox",
          cls: "paperforge-workflow-checkbox",
        });
      ((m.checked = t[_.key] === !0),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-label",
          text: _.label,
        }),
        h.createEl("span", {
          cls: "paperforge-workflow-toggle-hint",
          text: _.hint,
        }),
        m.addEventListener("change", async () => {
          let E = t.note_path
            ? this.app.vault.getAbstractFileByPath(t.note_path)
            : null;
          if (!E) {
            new V.Notice("[!!] Note file not found", 6e3);
            return;
          }
          let y = m.checked;
          (await this.app.fileManager.processFrontMatter(E, (g) => {
            g[_.key] = y;
          }),
            this._patchCachedEntry(r, { [_.key]: y }),
            (this._currentPaperEntry = ft(this._currentPaperEntry, {
              [_.key]: y,
            })));
        }));
    }
    let c = t.health || {},
      u = [
        ["PDF Health", c.pdf_health || "\u2014"],
        ["OCR Status", t.ocr_status || "\u2014"],
        ["Asset Health", c.asset_health || "\u2014"],
        ["Note Path", t.note_path || "\u2014"],
        ["Fulltext Path", t.fulltext_path || "\u2014"],
      ],
      f = new Set(["Note Path", "Fulltext Path", "Key"]);
    for (let [_, h] of u) {
      let m = a.createEl("div", { cls: "paperforge-technical-row" });
      m.createEl("span", { cls: "paperforge-technical-label", text: _ });
      let E = m.createEl("span", {
        cls: "paperforge-technical-value",
        text: String(h),
      });
      f.has(_) &&
        h &&
        h !== "\u2014" &&
        (E.addClass("pf-copy"),
        E.addEventListener("click", () => {
          (navigator.clipboard.writeText(h), new V.Notice(_ + " copied"));
        }));
    }
  }
  _renderNextStepCard(e, t, r) {
    var l, c;
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
      a = s[n] || s.ready,
      i = e.createEl("div", { cls: "paperforge-next-step-card" });
    if (
      (n === "ready" && i.addClass("ready"),
      i.createEl("div", {
        cls: "paperforge-next-step-label",
        text: "Recommended Next Step",
      }),
      i.createEl("div", { cls: "paperforge-next-step-text", text: a.text }),
      a.cmd && a.cmd !== "ready")
    ) {
      let u = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: a.icon + "  " + a.label }),
        u.addEventListener("click", () => {
          let f = ce.find((_) => _.cmd === a.cmd);
          f && this._runAction(f, u);
        }));
    } else if (n === "/pf-deep") {
      let u = i.createEl("button", { cls: "paperforge-next-step-trigger" });
      (u.createEl("span", { text: "\u{1F4CB}  " + o("copy_pf_deep_cmd") }),
        u.addEventListener("click", () => {
          let E = "/pf-deep " + r;
          navigator.clipboard
            .writeText(E)
            .then(() => {
              (u.setText("\u2713  " + o("copied")),
                new V.Notice(E + " copied"));
            })
            .catch(() => {
              new V.Notice("[!!] Clipboard write failed", 6e3);
            });
        }));
      let f =
          ((c =
            (l = this.app.plugins.plugins.paperforge) == null
              ? void 0
              : l.settings) == null
            ? void 0
            : c.agent_platform) || "opencode",
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
      i.createEl("div", { cls: "paperforge-agent-platform-label" }).setText(
        o("run_in_agent").replace("{0}", h)
      );
    } else
      n === "ready" &&
        i
          .createEl("button", { cls: "paperforge-next-step-trigger" })
          .createEl("span", { text: "\u2713  " + a.label });
  }
  _openFulltext(e) {
    if (!e) {
      new V.Notice("[!!] No fulltext path available for this paper", 6e3);
      return;
    }
    let t = this.app.vault.getAbstractFileByPath(e);
    t
      ? this.app.workspace.openLinkText(t.path, "")
      : new V.Notice("[!!] Fulltext file not found: " + e, 6e3);
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
      i = 0,
      l = 0,
      c = 0,
      u = 0,
      f = 0;
    for (let b of t) {
      (b.has_pdf && s++,
        b.ocr_status === "done" && a++,
        b.ocr_status === "done" && b.analyze === !0 && i++,
        b.deep_reading_status === "done" && l++);
      let x = b.ocr_status || "";
      x === "pending" || x === "queued"
        ? c++
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
    let h = r.createEl("div", { cls: "paperforge-workflow-overview" });
    h.createEl("div", {
      cls: "paperforge-section-label",
      text: "Workflow Overview",
    });
    let m = h.createEl("div", { cls: "paperforge-workflow-funnel" }),
      E = [
        { value: n, label: "Total" },
        { value: s, label: "PDF Ready" },
        { value: a, label: "OCR Done" },
        { value: l, label: "Deep Read" },
      ];
    for (let b = 0; b < E.length; b++) {
      let x = m.createEl("div", { cls: "paperforge-workflow-stage" });
      (x.createEl("div", {
        cls: "paperforge-workflow-stage-value",
        text: String(E[b].value),
      }),
        x.createEl("div", {
          cls: "paperforge-workflow-stage-label",
          text: E[b].label,
        }),
        b < E.length - 1 &&
          m.createEl("div", {
            cls: "paperforge-workflow-arrow",
            text: "\u2192",
          }));
    }
    if (c + u + a + f > 0) {
      let b = r.createEl("div", { cls: "paperforge-ocr-section" }),
        x = b.createEl("div", { cls: "paperforge-collection-ocr-header" });
      x.createEl("h4", { cls: "paperforge-ocr-title", text: "OCR Pipeline" });
      let C = x.createEl("span", { cls: "paperforge-ocr-badge idle" });
      u > 0
        ? (C.addClass("active"), C.setText("Processing"))
        : c > 0
          ? C.setText("Pending")
          : (C.addClass("idle"), C.setText("Idle"));
      let S = b.createEl("div", { cls: "paperforge-progress-track" });
      u > 0 && S.addClass("paperforge-processing");
      let k = c + u + a + f,
        T = [
          { cls: "pending", count: c },
          { cls: "active", count: u },
          { cls: "done", count: a },
          { cls: "failed", count: f },
        ];
      for (let F of T)
        if (F.count > 0) {
          let A = ((F.count / k) * 100).toFixed(1);
          S.createEl("div", {
            cls: `paperforge-progress-seg ${F.cls}`,
            attr: { style: `width:${A}%` },
          });
        }
      let M = b.createEl("div", { cls: "paperforge-ocr-counts" }),
        B = [
          { cls: "pending", value: c, label: "Pending" },
          { cls: "active", value: u, label: "Processing" },
          { cls: "done", value: a, label: "Done" },
          { cls: "failed", value: f, label: "Attention" },
        ];
      for (let F of B) {
        let A = M.createEl("div", { cls: "paperforge-ocr-count" });
        (A.createEl("div", {
          cls: "paperforge-ocr-count-value",
          text: F.value.toString(),
        }),
          A.createEl("div", {
            cls: "paperforge-ocr-count-label",
            text: F.label,
          }));
      }
    }
    let y = r.createEl("div", { cls: "paperforge-collection-actions" }),
      g = y.createEl("button", { cls: "paperforge-contextual-btn primary" });
    (g.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u229E",
    }),
      g.createEl("span", { text: "Run OCR" }),
      g.addEventListener("click", () => {
        let b = ce.find((x) => x.id === "paperforge-ocr");
        b && this._runAction(b, g);
      }));
    let v = y.createEl("button", { cls: "paperforge-contextual-btn" });
    (v.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BB",
    }),
      v.createEl("span", { text: "Sync Library" }),
      v.addEventListener("click", () => {
        let b = ce.find((x) => x.id === "paperforge-sync");
        b && this._runAction(b, v);
      }));
    let w = y.createEl("button", { cls: "paperforge-contextual-btn warn" });
    (w.createEl("span", {
      cls: "paperforge-contextual-btn-icon",
      text: "\u21BA",
    }),
      w.createEl("span", { text: "Redo OCR" }),
      w.addEventListener("click", () => {
        let b = ce.find((x) => x.id === "paperforge-ocr-redo");
        b && this._runAction(b, w);
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
      new V.Notice("Cannot determine vault path");
      return;
    }
    ((this._versionPapers = Mt(n)),
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
      (this._versionPapers = Mt(n));
    let s = e.createEl("div", { cls: "paperforge-version-left" }),
      a = e.createEl("div", { cls: "paperforge-version-right" }),
      i = s.createEl("input", {
        cls: "paperforge-version-filter",
        attr: { type: "text", placeholder: o("version_filter_placeholder") },
      });
    i.value = this._versionFilter;
    let l = s.createEl("div", { cls: "paperforge-version-paper-list" }),
      c = () => {
        l.empty();
        let g = this._versionFilter.toLowerCase(),
          v = this._versionPapers
            ? this._versionPapers.filter(
                (b) =>
                  !g ||
                  b.key.toLowerCase().includes(g) ||
                  b.title.toLowerCase().includes(g)
              )
            : [];
        if (v.length === 0) {
          l.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let w = l.createEl("div", {
          cls: "paperforge-meta",
          text: o("version_papers_count").replace("{n}", String(v.length)),
        });
        for (let b of v) {
          let x = l.createEl("div", { cls: "paperforge-version-paper-item" }),
            C = x.createEl("span", {
              cls: "paperforge-version-paper-title",
              text: b.title,
            }),
            S = x.createEl("span", {
              cls: "paperforge-version-paper-versions",
              text: b.versions.map((k) => k.label).join(" "),
            });
          x.addEventListener("click", () => {
            (l
              .querySelectorAll(".paperforge-version-paper-item.selected")
              .forEach((k) => k.removeClass("selected")),
              x.addClass("selected"),
              f(b));
          });
        }
      };
    i.addEventListener("input", () => {
      ((this._versionFilter = i.value), c());
    });
    let u = a.createEl("div", { cls: "paperforge-version-timeline-area" }),
      f = (g) => {
        if (
          (u.empty(),
          u
            .createEl("div", { cls: "paperforge-version-timeline-header" })
            .createEl("span", { cls: "pf-title", text: g.title }),
          g.versions.length === 0)
        ) {
          u.createEl("div", {
            cls: "paperforge-meta",
            text: o("version_no_backups"),
          });
          return;
        }
        let w = u.createEl("div", { cls: "paperforge-version-timeline" });
        for (let b of g.versions) {
          let x = b.label === g.currentLabel,
            C = w.createEl("div", {
              cls:
                "paperforge-version-entry" +
                (x ? " paperforge-version-current" : ""),
            }),
            S = C.createEl("div", { cls: "paperforge-version-dot" }),
            k = C.createEl("div", { cls: "paperforge-version-content" }),
            T = k.createEl("div", { cls: "paperforge-version-label-row" });
          (T.createEl("span", {
            cls: "paperforge-version-label",
            text: b.label,
          }),
            x &&
              T.createEl("span", {
                cls: "paperforge-version-current-tag",
                text: o("version_current"),
              }));
          let M = b.created_at ? b.created_at.slice(0, 10) : "";
          k.createEl("div", {
            cls: "paperforge-meta",
            text: M + " \u2014 " + b.source,
          });
          let B = b.fulltext_size
            ? b.fulltext_size > 1024
              ? (b.fulltext_size / 1024).toFixed(0) + "KB"
              : b.fulltext_size + "B"
            : "";
          B && k.createEl("div", { cls: "paperforge-meta", text: B });
          let F = k.createEl("div", { cls: "paperforge-version-actions" });
          (F.createEl("button", {
            cls: "pf-btn-primary",
            text: o("version_restore_btn"),
          }).addEventListener("click", () => {
            yr(n, g.key, b.label)
              ? new V.Notice(
                  o("version_restore_done").replace("{label}", b.label)
                )
              : new V.Notice("Restore failed", 6e3);
          }),
            g.versions.length > 1 &&
              !x &&
              F.createEl("button", {
                cls: "pf-btn-secondary",
                text: o("version_compare_btn"),
              }).addEventListener("click", () => {
                h(g, b.label, g.currentLabel);
              }));
        }
      },
      _ = a.createEl("div", { cls: "paperforge-version-compare" });
    _.style.display = "none";
    let h = (g, v, w) => {
        let b = br(n, g.key, v, w);
        ((_.style.display = "block"), _.empty());
        let x = _.createEl("div", { cls: "paperforge-version-compare-header" });
        if (
          (x.createEl("span", {
            cls: "pf-title",
            text: o("version_compare_title")
              .replace("{vA}", v)
              .replace("{vB}", w),
          }),
          x.createEl("span", {
            cls: "paperforge-meta",
            text: o("version_compare_paragraphs").replace(
              "{n}",
              String(b.length)
            ),
          }),
          b.length === 0)
        ) {
          _.createEl("div", { cls: "paperforge-meta", text: "No changes" });
          return;
        }
        let C = _.createEl("div", { cls: "paperforge-version-diff-list" });
        for (let S of b) {
          let k = C.createEl("div", { cls: "paperforge-version-diff-row" }),
            T =
              S.type === "added" ? "[+]" : S.type === "removed" ? "[-]" : "[~]",
            M = S.heading || "paragraph " + (S.paragraphIndex + 1);
          (k.createEl("span", {
            cls: "paperforge-version-diff-label",
            text: T + " " + M,
          }),
            S.oldText &&
              k.createEl("pre", {
                cls: "paperforge-version-diff-old",
                text: S.oldText.slice(0, 200),
              }),
            S.newText &&
              k.createEl("pre", {
                cls: "paperforge-version-diff-new",
                text: S.newText.slice(0, 200),
              }));
        }
      },
      m = e.createEl("div", { cls: "paperforge-version-actions-bar" }),
      E = m.createEl("button", {
        cls: "pf-btn-primary",
        text: o("version_restore_selected"),
      }),
      y = m.createEl("button", {
        cls: "pf-btn-secondary",
        text: o("version_clear_old").replace("{size}", ""),
      });
    c();
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
      (this._searchInput.placeholder = o("retrieval_search_placeholder")),
      this._searchInput.addEventListener("input", () => {
        var a;
        let s = ((a = this._searchInput) == null ? void 0 : a.value) || "";
        if (
          (s.startsWith("@") && !s.startsWith("@ ")
            ? ((this._searchMode = "@"),
              n.setText("@"),
              n.addClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
                  "retrieval_search_placeholder_deep"
                )))
            : ((this._searchMode = "M"),
              n.setText("M"),
              n.removeClass("deep"),
              this._searchInput &&
                (this._searchInput.placeholder = o(
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
        var a, i;
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
          let l = this._searchResults.length;
          s.key === "ArrowDown"
            ? (this._searchActiveIndex = Math.min(
                this._searchActiveIndex + 1,
                l - 1
              ))
            : (this._searchActiveIndex = Math.max(
                this._searchActiveIndex - 1,
                -1
              ));
          let c =
            (i = this._searchResultsEl) == null
              ? void 0
              : i.querySelectorAll(".paperforge-search-result-card");
          c &&
            c.forEach((u, f) => {
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
          let l = this._searchMode;
          ((this._searchMode = "@"),
            this.executeSearch(),
            (this._searchMode = l));
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
            ? o("retrieval_searching_deep")
            : o("retrieval_searching_metadata"),
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
          t.createEl("div", { text: o("retrieval_empty") }),
          t.createEl("div", {
            cls: "paperforge-search-empty-tips",
            text: o("retrieval_empty_tips"),
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
            text: o("retrieval_vectors_not_built"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_vectors_not_built_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-link",
          text: o("retrieval_open_vector_settings"),
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
            text: o("retrieval_backend_unavailable"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_backend_unavailable_desc"),
          }));
        let r = t.createEl("div", { cls: "paperforge-search-state-actions" }),
          n = r.createEl("button", {
            cls: "pf-btn-primary",
            text: o("retrieval_run_doctor"),
          });
        (n.addEventListener("click", () => {
          let a = this.app.vault.adapter.basePath;
          if (typeof a == "string") {
            let { path: i, extraArgs: l = [] } = K(a, null, void 0, void 0);
            (0, xe.spawn)(i, [...l, "-m", "paperforge", "doctor"], {
              cwd: a,
              stdio: "inherit",
            });
          }
        }),
          r
            .createEl("button", {
              cls: "pf-btn-secondary",
              text: o("retrieval_retry"),
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
            text: o("retrieval_timeout_title"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_timeout_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: o("retrieval_retry"),
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
            text: o("retrieval_model_changed"),
          }),
          t.createEl("div", {
            cls: "paperforge-search-state-desc",
            text: o("retrieval_model_changed_desc"),
          }));
        let r = t.createEl("button", {
          cls: "pf-btn-primary",
          text: o("retrieval_rebuild_vectors"),
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
            text: o("retrieval_internal_error"),
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
      let y = s.basePath;
      a = typeof y == "string" ? y : "";
    }
    if (!a) {
      ((this._searchState = "backend-unavailable"), this._renderSearchState());
      return;
    }
    let i = null,
      c = this.app.plugins;
    if (c && typeof c == "object" && "plugins" in c) {
      let y = c.plugins;
      if (y && typeof y == "object" && "paperforge" in y) {
        let g = y.paperforge;
        g && typeof g == "object" && "settings" in g && (i = g.settings);
      }
    }
    let { path: u, extraArgs: f = [] } = K(a, i, void 0, void 0),
      _ = n === "retrieve" ? ["--deep"] : [],
      h = await ye({ app: this.app }, "memory"),
      m = (0, xe.spawn)(
        u,
        [...f, "-m", "paperforge", "--vault", a, n, r, ..._, "--json"],
        { cwd: a, timeout: 3e4, env: h }
      ),
      E = [];
    (m.stdout.on("data", (y) => {
      E.push(y.toString("utf-8"));
    }),
      m.stderr.on("data", () => {}),
      m.on("close", (y) => {
        if (y !== 0) {
          let x = kt(String(y));
          ((this._searchState = this._mapErrorToSearchState(x.type)),
            this._renderSearchState());
          return;
        }
        let g = E.join(""),
          v = g.indexOf("{"),
          w = g.lastIndexOf("}"),
          b = "";
        if (v !== -1 && w > v) b = g.slice(v, w + 1);
        else {
          let x = g.indexOf("["),
            C = g.lastIndexOf("]");
          x !== -1 && C > x && (b = g.slice(x, C + 1));
        }
        if (!b) {
          ((this._searchState = "internal-error"), this._renderSearchState());
          return;
        }
        try {
          let x = JSON.parse(b),
            C = [];
          if (x && typeof x == "object" && "data" in x) {
            let S = x.data;
            if (S && typeof S == "object") {
              let k = S;
              "matches" in k && Array.isArray(k.matches) && (C = k.matches);
            }
          }
          ((this._searchResults = C),
            (this._searchState = C.length > 0 ? "results" : "empty"),
            this._renderSearchState());
        } catch (x) {
          let C = x instanceof Error ? x.message : String(x);
          ((this._searchState = "internal-error"), this._renderSearchState());
        }
      }),
      m.on("error", (y) => {
        let g = y.code;
        if (typeof g == "string") {
          let v = kt(g);
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
        text: o("retrieval_results_count")
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
      let i = a,
        l = s === this._searchActiveIndex,
        c = this._searchResultsEl.createEl("div", {
          cls: "paperforge-search-result-card",
          attr: {
            role: "option",
            tabindex: "0",
            "aria-selected": l ? "true" : "false",
            "aria-posinset": String(s + 1),
            "aria-setsize": String(e.length),
          },
        });
      l && c.addClass("active");
      let u =
        typeof i.title == "string"
          ? i.title
          : typeof i.file_name == "string"
            ? i.file_name
            : "(untitled)";
      c.createEl("div", { cls: "paperforge-search-result-title", text: u });
      let f = typeof i.zotero_key == "string" ? i.zotero_key : "",
        _ =
          typeof i.main_note_path == "string" && i.main_note_path
            ? i.main_note_path
            : null,
        h = typeof i.note_path == "string" && i.note_path ? i.note_path : null,
        m = _ || h;
      if (!m && f) {
        let g = this._getCachedIndex().find(
          (v) =>
            v !== null &&
            typeof v == "object" &&
            "zotero_key" in v &&
            v.zotero_key === f
        );
        if (g && typeof g == "object") {
          let v = g;
          m =
            typeof v.main_note_path == "string" && v.main_note_path
              ? v.main_note_path
              : typeof v.note_path == "string" && v.note_path
                ? v.note_path
                : null;
        }
      }
      (m
        ? c.addEventListener("click", (y) => {
            let g = y.ctrlKey || y.metaKey;
            this.app.workspace.openLinkText(m, "", g);
          })
        : c.addEventListener("click", () => {
            new V.Notice("[!!] Note not found: " + (f || "unknown"), 6e3);
          }),
        c.addEventListener("keydown", (y) => {
          if (y.key === "Enter" && m) {
            y.preventDefault();
            let g = y.ctrlKey || y.metaKey;
            this.app.workspace.openLinkText(m, "", g);
          }
        }));
      let E = c.createEl("div", { cls: "paperforge-search-result-meta" });
      if (
        (typeof i.first_author == "string" &&
          i.first_author &&
          E.createEl("span", {
            cls: "paperforge-search-result-author",
            text: i.first_author,
          }),
        typeof i.journal == "string" &&
          i.journal &&
          E.createEl("span", {
            cls: "paperforge-search-result-journal",
            text: i.journal,
          }),
        i.score !== void 0)
      ) {
        let y = i.score,
          g = typeof y == "number" ? y.toFixed(3) : String(y);
        E.createEl("span", {
          cls: "paperforge-search-result-score",
          text: "Score: " + g,
        });
      }
      if (
        (typeof i.domain == "string" &&
          i.domain &&
          c.createEl("span", {
            cls: "paperforge-search-result-tag",
            text: i.domain,
          }),
        typeof i.abstract == "string" && i.abstract)
      ) {
        let y = i.abstract;
        c.createEl("div", {
          cls: "paperforge-search-result-abstract",
          text: y.length > 200 ? y.slice(0, 200) + "..." : y,
        });
      }
      if (t && typeof i.text == "string" && i.text) {
        let y = i.text;
        c.createEl("div", {
          cls: "paperforge-search-result-source",
          text: y.length > 300 ? y.slice(0, 300) + "..." : y,
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
    var h, m;
    if (e.disabled) {
      new V.Notice(
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
      let E = this.app.workspace.getActiveFile(),
        y = null;
      if (E) {
        let g = this.app.metadataCache.getFileCache(E);
        if (
          (g && g.frontmatter && g.frontmatter.zotero_key
            ? (y = g.frontmatter.zotero_key)
            : (y = this._extractZoteroKeyFromPath(E.path)),
          y)
        )
          n = [...n, y];
        else if (g && g.frontmatter) {
          (this._showMessage(
            "[!!] No zotero_key in active note frontmatter",
            "error"
          ),
            new V.Notice(
              "[!!] Open a paper note with a zotero_key in its frontmatter first",
              6e3
            ),
            t.removeClass("running"));
          return;
        } else {
          (this._showMessage("[!!] No frontmatter in active note", "error"),
            new V.Notice(
              "[!!] The active note has no frontmatter with a zotero_key",
              6e3
            ),
            t.removeClass("running"));
          return;
        }
      } else {
        (this._showMessage("[!!] No active note open", "error"),
          new V.Notice(
            "[!!] Open a paper note with a zotero_key in its frontmatter first",
            6e3
          ),
          t.removeClass("running"));
        return;
      }
    }
    e.needsFilter && (n = [...n, "--all"]);
    let s = e.needsFilter ? 6e4 : e.needsKey ? 3e4 : 6e5,
      { path: a, extraArgs: i = [] } = K(
        r,
        (m =
          (h = this.app.plugins.plugins.paperforge) == null
            ? void 0
            : h.settings) != null
          ? m
          : null,
        void 0,
        void 0
      ),
      l = await ye({ app: this.app }, e.cmd),
      c = (0, xe.spawn)(a, [...i, "-m", "paperforge", e.cmd, ...n], {
        cwd: r,
        timeout: s,
        env: l,
      }),
      u = [],
      f = Date.now(),
      _ = setInterval(() => this._fetchStats(!0), 4e3);
    (c.stdout.on("data", (E) => {
      let y = E.toString("utf-8")
        .split(
          `
`
        )
        .filter(Boolean);
      for (let g of y) {
        let v = g.trim();
        v &&
          (u.push(v),
          this._showMessage(
            u.slice(-8).join(`
`),
            "running"
          ));
      }
    }),
      c.stderr.on("data", (E) => {
        let y = E.toString("utf-8")
          .split(
            `
`
          )
          .filter(Boolean);
        for (let g of y) {
          if (g.includes("\r") || g.includes("%") || g.includes("\u2588"))
            continue;
          let v = g.trim();
          v &&
            !v.match(/^\d+%|^\|/) &&
            (u.push(v),
            this._showMessage(
              u.slice(-8).join(`
`),
              "running"
            ));
        }
      }),
      c.on("close", (E) => {
        (clearInterval(_), t.removeClass("running"));
        let y = ((Date.now() - f) / 1e3).toFixed(1);
        if (E !== 0) {
          let g = u.slice(-3).join(" | ") || "exit code " + E;
          (e.cmd === "repair" || e.cmd === "ocr") && E === 1
            ? (this._showMessage("[WARN] " + g, "running"),
              new V.Notice("[WARN] " + e.cmd + " partial: " + g, 8e3),
              this._fetchStats(!0))
            : (this._showMessage("[!!] " + g, "error"),
              new V.Notice("[!!] " + e.cmd + " failed: " + g, 8e3));
        } else if (e.needsKey || e.needsFilter) {
          let g = u.join(`
`);
          if (g.trim())
            try {
              (JSON.parse(g),
                navigator.clipboard
                  .writeText(g)
                  .then(() => {
                    let v = `${y}s \u2014 ${g.length} chars copied`;
                    (this._showMessage("[OK] " + e.title + ": " + v, "ok"),
                      new V.Notice(
                        "[OK] " + e.okMsg + " \u2014 " + g.length + " chars"
                      ));
                  })
                  .catch((v) => {
                    (this._showMessage(
                      "[!!] Clipboard write failed: " + v.message,
                      "error"
                    ),
                      new V.Notice("[!!] Clipboard error", 6e3));
                  }));
            } catch (v) {
              (this._showMessage("[!!] Invalid JSON from " + e.title, "error"),
                new V.Notice(
                  "[!!] " +
                    e.title +
                    " returned invalid JSON: " +
                    v.message.slice(0, 100),
                  8e3
                ));
            }
          else
            (this._showMessage("[!!] No output from context command", "error"),
              new V.Notice("[!!] Context command returned empty output", 8e3));
          this._fetchStats(!0);
        } else {
          let v =
              u.filter((b) => b.match(/updated \d+/)).pop() ||
              u[u.length - 1] ||
              "",
            w = `${y}s \u2014 ${v}`;
          (this._showMessage("[OK] " + e.title + ": " + w, "ok"),
            new V.Notice("[OK] " + e.okMsg),
            this._contentEl && this._contentEl.removeClass("switching"),
            (this._cachedStats = null));
          try {
            this._fetchStats(!1);
          } catch (b) {
            console.log("[PF] fetchStats error:", b);
          }
          (console.log("[PF] close cmd=" + e.cmd + " id=" + e.id),
            e.cmd === "sync" &&
              st(this.app, this.app.plugins.plugins.paperforge, r));
        }
      }),
      c.on("error", (E) => {
        (t.removeClass("running"),
          this._contentEl && this._contentEl.removeClass("switching"),
          this._showMessage("[!!] " + E.message, "error"),
          new V.Notice("[!!] Cannot start: " + E.message, 8e3));
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
          t.setText(o("version_panel_title")),
          this._headerTitle &&
            this._headerTitle.setText(o("version_panel_title")));
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
    let t = e.app.workspace.getLeavesOfType(Re);
    if (t.length > 0) {
      e.app.workspace.revealLeaf(t[0]);
      return;
    }
    let r = e.app.workspace.getRightLeaf(!1);
    r &&
      (await r.setViewState({ type: Re, active: !0 }),
      e.app.workspace.revealLeaf(r));
  }
};
var ut = class extends ee.Plugin {
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
  }
  async onload() {
    (await this.loadSettings(),
      Kt(this.app),
      this.registerView(Re, (t) => new Ie(t)));
    try {
      (0, ee.addIcon)(Ve, Ht);
    } catch (t) {}
    (this.addRibbonIcon(Ve, "PaperForge Dashboard", () => Ie.open(this)),
      ce.find((t) => t.id === "paperforge-ocr-redo") &&
        this.addRibbonIcon("reset", "PaperForge: Redo OCR", async () => {
          let t = this.app.vault.adapter.basePath;
          new ee.Notice("PaperForge: Redo OCR starting...");
          let { path: r, extraArgs: n } = K(t, this.settings, void 0, void 0),
            s = await ye(this, "ocr");
          (0, Ne.execFile)(
            r,
            [...n, "-m", "paperforge", "ocr", "redo"],
            { cwd: t, timeout: 6e5, env: s },
            (a, i, l) => {
              if (a) {
                new ee.Notice("PaperForge: Redo OCR failed");
                return;
              }
              new ee.Notice("PaperForge: Redo OCR done");
            }
          );
        }),
      this.addSettingTab(new pt(this.app, this)),
      this.addCommand({
        id: "paperforge-status-panel",
        name: `PaperForge: ${o("guide_open")}`,
        callback: () => Ie.open(this),
      }));
    for (let t of ce)
      this.addCommand({
        id: t.id,
        name: `PaperForge: ${t.title}`,
        callback: async () => {
          if (t.disabled) {
            new ee.Notice(
              `[i] ${t.disabledMsg || "This action is not yet available."}`,
              6e3
            );
            return;
          }
          let r = this.app.vault.adapter.basePath;
          new ee.Notice(`PaperForge: running ${t.cmd}...`);
          let { path: n, extraArgs: s = [] } = K(
              r,
              this.settings,
              void 0,
              void 0
            ),
            a = Array.isArray(t.args) ? [...t.args] : [],
            i = await ye(this, t.cmd);
          (0, Ne.execFile)(
            n,
            [...s, "-m", "paperforge", t.cmd, ...a],
            { cwd: r, timeout: 3e5, env: i },
            (l, c, u) => {
              if (l) {
                new ee.Notice(
                  `[!!] ${t.cmd} failed: ${(u || l.message).slice(0, 120)}`,
                  8e3
                );
                return;
              }
              new ee.Notice(
                `[OK] ${
                  t.okMsg ||
                  c
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
    let t = ue(e).exportsDir;
    if (!J.existsSync(t)) return;
    let r = 0;
    try {
      J.readdirSync(t).forEach((n) => {
        if (!n.endsWith(".json")) return;
        let s = J.statSync(Le.join(t, n));
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
    let t = K(e, this.settings, void 0, void 0);
    if (!t.path) {
      this._autoSyncRunning = !1;
      return;
    }
    let r = `"${t.path}" -m paperforge --vault "${e}" sync`;
    (0, Ne.exec)(r, { timeout: 12e4, encoding: "utf-8" }, (n, s, a) => {
      ((this._autoSyncRunning = !1),
        (this._memoryStatusText = null),
        n || (this._lastSyncTime = new Date().toLocaleTimeString()));
      try {
        let i = ue(e).exportsDir,
          l = 0;
        (J.readdirSync(i).forEach((c) => {
          c.endsWith(".json") &&
            (l = Math.max(l, J.statSync(Le.join(i, c)).mtimeMs));
        }),
          (this._lastExportMtime = l));
      } catch (i) {}
    });
  }
  _checkOcr(e) {
    if (this._autoSyncRunning) return;
    let t = ue(e).ocrDir;
    if (J.existsSync(t))
      try {
        J.readdirSync(t, { withFileTypes: !0 }).forEach((r) => {
          if (!r.isDirectory()) return;
          let n = Le.join(t, r.name, "meta.json");
          if (!J.existsSync(n)) return;
          let s = J.statSync(n),
            a = this._lastOcrMtimes[r.name] || 0;
          if (
            s.mtimeMs <= a ||
            ((this._lastOcrMtimes[r.name] = s.mtimeMs), this._autoSyncRunning)
          )
            return;
          this._autoSyncRunning = !0;
          let i = K(e, this.settings, void 0, void 0);
          if (!i.path) {
            this._autoSyncRunning = !1;
            return;
          }
          let l = `"${i.path}" -m paperforge --vault "${e}" sync`;
          (0, Ne.exec)(l, { timeout: 3e4, encoding: "utf-8" }, () => {
            ((this._autoSyncRunning = !1), (this._memoryStatusText = null));
          });
        });
      } catch (r) {}
  }
  readPaperforgeJson() {
    let e = this.app.vault.adapter.basePath,
      t = Le.join(e, "paperforge.json"),
      r = {
        system_dir: "System",
        resources_dir: "Resources",
        literature_dir: "Literature",
        base_dir: "Bases",
      };
    try {
      if (!J.existsSync(t)) return r;
      let n = J.readFileSync(t, "utf-8"),
        s = JSON.parse(n),
        a = s.vault_config || {};
      return {
        system_dir: a.system_dir || s.system_dir || r.system_dir,
        resources_dir: a.resources_dir || s.resources_dir || r.resources_dir,
        literature_dir:
          a.literature_dir || s.literature_dir || r.literature_dir,
        base_dir: a.base_dir || s.base_dir || r.base_dir,
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
      r = Le.join(t, "paperforge.json"),
      n = {};
    try {
      J.existsSync(r) && (n = JSON.parse(J.readFileSync(r, "utf-8")));
    } catch (a) {
      console.warn("PaperForge: Failed to read paperforge.json for update", a);
    }
    (!n.vault_config || typeof n.vault_config != "object") &&
      (n.vault_config = {});
    let s = ["system_dir", "resources_dir", "literature_dir", "base_dir"];
    for (let a of s) e[a] !== void 0 && (n.vault_config[a] = e[a]);
    n.schema_version || (n.schema_version = "2");
    for (let a of s) delete n[a];
    try {
      if (
        (J.writeFileSync(r, JSON.stringify(n, null, 2), "utf-8"), this.settings)
      ) {
        let a = this.readPaperforgeJson();
        ((this.settings.system_dir = a.system_dir),
          (this.settings.resources_dir = a.resources_dir),
          (this.settings.literature_dir = a.literature_dir),
          (this.settings.base_dir = a.base_dir));
      }
    } catch (a) {
      (console.error("PaperForge: Failed to write paperforge.json", a),
        new ee.Notice(
          "PaperForge: Failed to save configuration to paperforge.json"
        ));
    }
  }
  onunload() {
    (this._pollTimer && clearInterval(this._pollTimer),
      this.app.workspace.detachLeavesOfType(Re));
  }
  async loadSettings() {
    ((this.settings = Object.assign({}, He, await this.loadData())),
      this.settings.features &&
        He.features &&
        (this.settings.features = Object.assign(
          {},
          He.features,
          this.settings.features || {}
        )),
      this.settings.frozen_skills || (this.settings.frozen_skills = {}));
    let e = this.readPaperforgeJson();
    if (
      ((this.settings.system_dir = e.system_dir),
      (this.settings.resources_dir = e.resources_dir),
      (this.settings.literature_dir = e.literature_dir),
      (this.settings.base_dir = e.base_dir),
      this.settings.python_path && this.settings.python_path.trim())
    ) {
      let t = this.settings.python_path.trim();
      J.existsSync(t)
        ? (this.settings._python_path_stale = !1)
        : (console.warn(
            `PaperForge: Saved python_path "${t}" no longer exists - showing stale warning`
          ),
          (this.settings._python_path_stale = !0));
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
    let s = (Et().versions || []).find((i) => i.version === e);
    class a extends ee.Modal {
      constructor(l, c) {
        (super(l), (this._entry = c));
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
            for (let c of this._entry.breaking_or_migration)
              l.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            l.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (let c of this._entry.new_features)
              l.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            l.createEl("h4", { text: "\u4FEE\u590D" });
            for (let c of this._entry.fixes)
              l.createEl("p", {
                text: `\u2022 ${c}`,
                cls: "paperforge-modal-item",
              });
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            let c = l.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            (c.createEl("h4", { text: "\u5EFA\u8BAE\u64CD\u4F5C", cls: "" }),
              (c.style.marginBottom = "8px"));
            for (let u of this._entry.recommended_actions)
              c.createEl("p", {
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
        new ee.Setting(l).addButton((c) =>
          c
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
    (new a(this.app, s).open(),
      (this.settings.last_seen_version = e),
      this.saveSettings());
  }
};
