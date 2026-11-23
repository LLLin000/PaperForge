/**
 * Unified UX Feedback Hierarchy, Daemon Notice Deduplication & i18n Parity Tests.
 */
import * as fs from "fs";
import * as path from "path";
import { describe, expect, it } from "vitest";
import { I18N_DICTIONARIES, setLanguage, t } from "../src/i18n";
import {
  extractConciseErrorLine,
  formatDaemonNotice,
  formatHumanError,
} from "../src/services/feedback";

describe("i18n dictionary parity & zero-leak guards", () => {
  it("keeps EN and ZH dictionaries at 100% key parity", () => {
    const enKeys = Object.keys(I18N_DICTIONARIES.en).sort();
    const zhKeys = Object.keys(I18N_DICTIONARIES.zh).sort();
    const onlyEn = enKeys.filter((k) => !(k in I18N_DICTIONARIES.zh));
    const onlyZh = zhKeys.filter((k) => !(k in I18N_DICTIONARIES.en));
    expect(onlyEn).toEqual([]);
    expect(onlyZh).toEqual([]);
    expect(enKeys.length).toBeGreaterThan(1300);
  });

  it("ensures Rust daemon production code emits zero hardcoded Chinese strings", () => {
    const rustDir = path.resolve(
      __dirname,
      "../../../crates/paperforge-daemon/src"
    );
    const zhRe = /[\u4e00-\u9fff]/;
    const violations: string[] = [];
    for (const file of ["supervisor.rs", "query_ops.rs", "runtime.rs"]) {
      const full = path.join(rustDir, file);
      if (!fs.existsSync(full)) continue;
      const lines = fs.readFileSync(full, "utf-8").split(/\r?\n/);
      lines.forEach((line, idx) => {
        const s = line.trim();
        if (s.startsWith("//")) return;
        if (zhRe.test(s)) {
          violations.push(`${file}:L${idx + 1}: ${s}`);
        }
      });
    }
    expect(violations).toEqual([]);
  });
});

describe("Unified human error translator & daemon notice deduplication", () => {
  it("extracts root error line from multi-line Python tracebacks", () => {
    const tb = [
      "Traceback (most recent call last):",
      '  File "paperforge/cli.py", line 42, in main',
      "    run_sync()",
      "sqlite3.OperationalError: database is locked",
    ].join("\n");
    expect(extractConciseErrorLine(tb)).toBe(
      "sqlite3.OperationalError: database is locked"
    );
    setLanguage({} as never, "en");
    expect(formatHumanError(tb)).toContain("Zotero database is busy");
    setLanguage({} as never, "zh");
    expect(formatHumanError(tb)).toContain("Zotero 数据库正被占用");
  });

  it("translates common network, auth, quota, and missing-runtime failures cleanly in EN & ZH", () => {
    setLanguage({} as never, "en");
    expect(formatHumanError("NO_PYTHON worker missing")).toContain(
      "Compute engine is not installed"
    );
    expect(formatHumanError("HTTP 401 Unauthorized")).toContain("API Key");
    expect(formatHumanError("429 quota exceeded")).toContain("Quota exceeded");
    expect(formatHumanError("ECONNREFUSED 127.0.0.1")).toContain("network");
    expect(formatHumanError("PermissionError: file locked")).toContain(
      "locked"
    );

    setLanguage({} as never, "zh");
    expect(formatHumanError("NO_PYTHON worker missing")).toContain(
      "计算引擎尚未安装"
    );
    expect(formatHumanError("HTTP 401 Unauthorized")).toContain("API Key 无效");
    expect(formatHumanError("429 quota exceeded")).toContain("免费额度已用完");
    expect(formatHumanError("ECONNREFUSED 127.0.0.1")).toContain("网络或代理");
    expect(formatHumanError("PermissionError: file locked")).toContain("占用");
  });

  it("localizes daemon notice.push by semantic code and suppresses duplicate runtime.install notices", () => {
    setLanguage({} as never, "en");
    const doneEn = formatDaemonNotice({
      code: "runtime.install.done",
      level: "success",
      title: "Python compute engine is ready",
    });
    expect(doneEn?.message).toBe(t("daemon_notice_runtime_install_done"));
    expect(doneEn?.durationMs).toBe(5000);

    // Suppress duplicate toast when Settings onboarding already polls inline
    expect(
      formatDaemonNotice(
        { code: "runtime.install.done", level: "success", title: "Ready" },
        { suppressRuntimeInstall: true }
      )
    ).toBeNull();
    expect(
      formatDaemonNotice(
        {
          code: "runtime.install.failed",
          level: "warning",
          title: "Failed",
          detail: "ECONNREFUSED",
        },
        { suppressRuntimeInstall: true }
      )
    ).toBeNull();

    setLanguage({} as never, "zh");
    const healZh = formatDaemonNotice({
      code: "job.upgrade.heal.done",
      level: "success",
      title: "Background library organization completed",
    });
    expect(healZh?.message).toContain("后台渐进整理已完成");

    const failZh = formatDaemonNotice({
      code: "job.ocr.failed",
      level: "warning",
      title: "Background task did not complete (ocr)",
      detail: "Traceback (most recent call last):\nHTTP 401 Unauthorized",
    });
    expect(failZh?.message).toContain("OCR 全文解析");
    expect(failZh?.message).toContain("API Key 无效");
    expect(failZh?.message).not.toContain("Traceback");
    expect(failZh?.durationMs).toBe(8000);
  });
});

describe("Deterministic Setup & Readiness Decision Tree", () => {
  it("routes every real-world user state to one unambiguous card and next action", async () => {
    const { resolveSetupDecision } =
      await import("../src/services/setup-decision-tree");
    const { createUnknownEnvelope } = await import("../src/constants");

    const readyInst = {
      ...createUnknownEnvelope("installation"),
      user_state: "ready" as const,
      capability_state: "ready" as const,
    };
    const failedInst = {
      ...createUnknownEnvelope("installation"),
      user_state: "detection_failed" as const,
      capability_state: "invalid" as const,
    };
    const readyLib = {
      ...createUnknownEnvelope("library"),
      user_state: "ready" as const,
      capability_state: "ready" as const,
      details: { paper_count: 42 },
    };
    const actionLib = {
      ...createUnknownEnvelope("library"),
      user_state: "action_required" as const,
      capability_state: "needs_action" as const,
    };

    const base = {
      daemonUpdating: false,
      runtimeUpdating: false,
      canCancelInstall: false,
      quarantinedBinDir: null,
      upgradePlan: null,
      upgradeBannerDismissed: false,
      runtimePointer: {
        schemaVersion: 1,
        pythonPath: "/opt/pf/python",
        paperforgeVersion: "2.0.4",
      },
      expectedVersion: "2.0.4",
      installationEnv: readyInst,
      libraryEnv: readyLib,
      isProbing: false,
      zoteroDataDir: "/home/u/Zotero",
      zoteroDetectedPapers: 42,
      lastAutoSyncError: null,
      paperCount: 42,
    };

    setLanguage({} as never, "zh");

    // 0. Hot-swap/updating suppresses transient probe failure & sync error
    const updating = resolveSetupDecision({
      ...base,
      daemonUpdating: true,
      installationEnv: failedInst,
      lastAutoSyncError: "PaperForge daemon shut down",
    });
    expect(updating.id).toBe("engine_updating");
    expect(updating.badgeCls).toBe("checking");

    // 1. Antivirus quarantine takes priority over setup
    const quar = resolveSetupDecision({
      ...base,
      quarantinedBinDir: "C:\\Users\\u\\.paperforge\\bin",
    });
    expect(quar.id).toBe("engine_quarantined");
    expect(quar.codeBlock).toBe("C:\\Users\\u\\.paperforge\\bin");
    expect(quar.primaryAction?.kind).toBe("copy_quarantine_path");

    // 2. Veteran legacy vault upgrade surfaces immediately
    const legacy = resolveSetupDecision({
      ...base,
      upgradePlan: {
        vault: "/v",
        provenance: {
          state: "veteran_legacy",
          needs_upgrade: true,
          confidence: "high",
          signals: ["legacy_engine_dir:System/PaperForge"],
        },
        census: {},
        manifest: null,
        rollback_available: false,
        category_a_auto: [],
        category_b_reconfig: [],
        category_c_tamper: [],
        cleanup_candidates: [],
        summary: {
          auto_count: 1,
          fast_cutover_count: 1,
          progressive_heal_count: 0,
          reconfig_critical_count: 0,
          reconfig_minor_count: 0,
          tamper_count: 0,
          cleanup_candidate_count: 0,
          ocr_atoms: {
            total: 0,
            current: 0,
            rebuild_derived_local: 0,
            backfill_from_result_json: 0,
            re_ocr_needed: 0,
          },
        },
      },
    });
    expect(legacy.id).toBe("legacy_vault_upgrade");
    expect(legacy.primaryAction?.kind).toBe("open_vault_upgrade");

    // 4. Version mismatch offers 1-click engine update (not Step 1 install!)
    const mismatch = resolveSetupDecision({
      ...base,
      runtimePointer: {
        schemaVersion: 1,
        pythonPath: "/opt/pf/python",
        paperforgeVersion: "2.0.2",
      },
      expectedVersion: "2.0.4",
      installationEnv: failedInst,
    });
    expect(mismatch.id).toBe("engine_version_mismatch");
    expect(mismatch.primaryAction?.kind).toBe("update_engine");

    // 5. Brand-new user with no runtime pointer sees Step 1
    const fresh = resolveSetupDecision({
      ...base,
      runtimePointer: null,
      installationEnv: failedInst,
    });
    expect(fresh.id).toBe("engine_not_installed");
    expect(fresh.primaryAction?.kind).toBe("start_setup_step1");

    // 6. Existing installed runtime whose probe failed sees Refresh + Repair (NEVER Step 1!)
    const probeFailed = resolveSetupDecision({
      ...base,
      installationEnv: failedInst,
    });
    expect(probeFailed.id).toBe("engine_probe_failed");
    expect(probeFailed.primaryAction?.kind).toBe("refresh_status");
    expect(probeFailed.secondaryAction?.kind).toBe("repair_engine");

    // 7. Engine ready, Zotero not configured -> Step 2
    const step2 = resolveSetupDecision({
      ...base,
      libraryEnv: actionLib,
      zoteroDataDir: "",
    });
    expect(step2.id).toBe("zotero_not_configured");
    expect(step2.primaryAction?.kind).toBe("connect_zotero");
    expect(step2.body).toContain("42");

    // 8. Sync error -> Retry Sync
    const syncErr = resolveSetupDecision({
      ...base,
      lastAutoSyncError: "Zotero 数据库正被占用",
    });
    expect(syncErr.id).toBe("library_sync_error");
    expect(syncErr.primaryAction?.kind).toBe("retry_sync");

    // 9. Ready!
    const ok = resolveSetupDecision(base);
    expect(ok.id).toBe("ready");
    expect(ok.badgeCls).toBe("ready");
    expect(ok.title).toContain("42");
  });
});
