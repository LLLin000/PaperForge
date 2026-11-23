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
