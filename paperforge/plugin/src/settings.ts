import { PluginSettingTab, App, Setting, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettings } from "./constants";
import releaseNotesData from "./release-notes.json";
import {
  resolvePythonExecutable, buildRuntimeInstallCommand,
  paperforgeEnrichedEnv, scanBbtUnderProfiles, scanBbtDirectChildren,
  runSubprocess,
} from "./services/python-bridge";
import {
  resolveVaultPaths, getMemoryRuntime, getVectorRuntime, getRuntimeHealth,
  isMemoryReady, isVectorReady, getMemoryStatusText, getVectorStatusText,
  getCachedPython,
} from "./services/memory-state";
import { getDisclosureState, toggleDisclosureState } from "./utils/disclosure";
import { PaperForgeOcrPrivacyModal, PaperForgeSetupModal, checkOrphanState } from "./views/modals";
import { categorizeMaintenanceRow, buildMaintenanceSummary } from "./services/ocr-maintenance-ui";

// ── Interface ──

interface ISettingPlugin {
  settings: PaperForgeSettings;
  saveSettings(): Promise<void>;
  loadSettings(): Promise<void>;
  manifest: { version: string };
  readPaperforgeJson(): Record<string, string>;
  savePaperforgeJson(pc: Record<string, string>): void;
  _autoSyncRunning?: boolean;
  _lastSyncTime?: string | null;
  _memoryStatusText?: string | null;
  _embedProcess?: unknown;
  _embedProgress?: { current: number; total: number; key: string };
  _embedStderr?: string;
}

export class PaperForgeSettingTab extends PluginSettingTab {
  plugin: ISettingPlugin;
  private _saveTimeout: ReturnType<typeof setTimeout> | null = null;
  private _pfConfig: Record<string, string> | null = null;
  private _lastSyncTime: string | null = null;
  private _memoryStatusText: string | null = null;
  private _vectorDepsOk: boolean | null = null;
  private _embedStatusText: string | null = null;
  private _skillsCollapsed: Record<string, boolean> = { user: true };
  private _featurePanelsCollapsed: Record<string, unknown> = {};
  private _advCollapsed = true;
  private _refreshPending = false;
  private _pythonInterpDescEl: HTMLElement | null = null;
  private _customPathDescEl: HTMLElement | null = null;
  private _checkEl: HTMLDivElement | null = null;
  activeTab = "setup";

  constructor(app: App, plugin: ISettingPlugin) {
    super(app, plugin as any);
    this.plugin = plugin;
  }

  /** Reload path config from paperforge.json */
  _refreshPfConfig() {
    this._pfConfig = this.plugin.readPaperforgeJson();
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    this._refreshPfConfig();

    // Inject tab CSS once
    if (!document.getElementById("paperforge-tab-styles")) {
      const style = document.createElement("style");
      style.id = "paperforge-tab-styles";
      style.textContent = `
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
                .paperforge-modal-subtitle { color: var(--text-muted); font-size: 13px; margin-bottom: 12px; }
                .paperforge-modal-item { font-size: 13px; margin-left: 8px; color: var(--text-muted); }
            `;
      document.head.appendChild(style);
    }

    // --- Tab bar ---
    const tabBar = containerEl.createDiv({ cls: "paperforge-settings-tabs" });
    const tabs = [
      { id: "setup", label: t("tab_setup") || "\u5B89\u88C5" },
      { id: "features", label: t("tab_features") || "\u529F\u80FD" },
      { id: "maintenance", label: t("tab_maintenance") || "\u7EF4\u62A4" },
      { id: "release-notes", label: "\u66F4\u65B0\u4E0E\u624B\u518C" },
    ];
    const tabContents: Record<string, HTMLDivElement> = {};

    tabs.forEach(tab => {
      const btn = tabBar.createEl("button", {
        cls: "paperforge-settings-tab" + (tab.id === this.activeTab ? " paperforge-settings-tab--active" : ""),
        text: tab.label,
      });
      btn.addEventListener("click", () => {
        this.activeTab = tab.id;
        this.display();
      });
    });

    // --- Tab content containers ---
    tabs.forEach(tab => {
      tabContents[tab.id] = containerEl.createDiv({
        cls: "paperforge-tab-content" + (tab.id === this.activeTab ? " paperforge-tab-content--active" : ""),
      });
    });

    // --- Render active tab ---
    if (this.activeTab === "setup") {
      this._renderSetupTab(tabContents.setup);
    } else if (this.activeTab === "features") {
      this._renderFeaturesTab(tabContents.features);
    } else if (this.activeTab === "maintenance") {
      this._renderMaintenanceTab(tabContents.maintenance);
    } else {
      this._renderReleaseNotesTab(tabContents["release-notes"]);
    }
  }

  _renderSetupTab(containerEl: HTMLElement) {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    if (!this.plugin.settings.vault_path) {
      this.plugin.settings.vault_path = vaultPath;
      this._debouncedSave();
    }

    /* Validate setup_complete against paperforge.json */
    if (this.plugin.settings.setup_complete) {
      if (!fs.existsSync(path.join(vaultPath, "paperforge.json"))) {
        this.plugin.settings.setup_complete = false;
        this._debouncedSave();
      }
    }

    /* Header */
    containerEl.createEl("h2", { text: t("header_title") || "PaperForge" });
    containerEl.createEl("p", {
      text: t("desc"),
      cls: "paperforge-settings-desc",
    });

    /* Setup Status */
    const statusRow = containerEl.createEl("div", { cls: "paperforge-setup-bar" });
    const statusLabel = statusRow.createEl("span", { cls: "paperforge-setup-label" });
    if (this.plugin.settings.setup_complete) {
      statusLabel.setText(t("setup_done"));
      statusLabel.addClass("paperforge-setup-done");
    } else {
      statusLabel.setText(t("setup_pending"));
      statusLabel.addClass("paperforge-setup-pending");
    }

    /* Python Interpreter Section */
    const vaultPathForPython = (this.app.vault.adapter as any).basePath as string;
    const pyResult = resolvePythonExecutable(vaultPathForPython, this.plugin.settings, undefined, undefined);
    const pyPath = pyResult.path;
    const pySource = this.plugin.settings._python_path_stale ? "stale" : pyResult.source;

    const pyInterpSetting = new Setting(containerEl)
      .setName(t("field_python_interp"))
      .setDesc(this._getPythonDesc(pyPath, pySource));
    this._pythonInterpDescEl = pyInterpSetting.descEl;

    const customSetting = new Setting(containerEl)
      .setName(t("field_python_custom"))
      .setDesc("");
    this._customPathDescEl = customSetting.descEl;

    customSetting.addText(text => {
      text.setPlaceholder("e.g. C:\\Python310\\python.exe")
        .setValue(this.plugin.settings.python_path || "")
        .onChange(value => {
          this.plugin.settings.python_path = value;
          this.plugin.saveSettings();

          if (value && value.trim()) {
            const exists = fs.existsSync(value.trim());
            this.plugin.settings._python_path_stale = !exists;
          } else {
            this.plugin.settings._python_path_stale = false;
          }

          const pyResult2 = resolvePythonExecutable((this.app.vault.adapter as any).basePath as string, this.plugin.settings, undefined, undefined);
          const pySource2 = this.plugin.settings._python_path_stale ? "stale" : pyResult2.source;
          if (this._pythonInterpDescEl) {
            this._pythonInterpDescEl.textContent = this._getPythonDesc(pyResult2.path, pySource2);
          }
        });
    });

    customSetting.addButton(btn => {
      btn.setButtonText(t("btn_validate"))
        .onClick(() => this._validatePythonOverride());
    });

    /* Runtime Health Section */
    containerEl.createEl("h3", { text: t("runtime_health") });
    containerEl.createEl("p", { text: t("runtime_health_desc"), cls: "paperforge-settings-desc" });

    const versionRow = new Setting(containerEl)
      .setName("PaperForge")
      .setDesc(t("runtime_health_checking"));

    const badgeEl = versionRow.descEl.createEl("span", { cls: "paperforge-runtime-badge" });
    let syncBtn: any = null;

    versionRow.addButton(btn => {
      syncBtn = btn;
      btn.setButtonText(t("runtime_health_sync"))
        .setDisabled(true)
        .onClick(() => this._syncRuntime(btn));
    });

    {
      const vp = (this.app.vault.adapter as any).basePath as string;
      const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings, undefined, undefined);
      const pluginVer = this.plugin.manifest.version || "?";

      execFile(pythonExe, [...extraArgs, "-c", "import paperforge; print(paperforge.__version__)"], { cwd: vp, timeout: 10000 }, (err, stdout) => {
        const setupDone = this.plugin.settings.setup_complete;
        const pyVer = (!err && stdout) ? stdout.trim() : null;
        const descText = pyVer
          ? `${t("runtime_health_plugin_ver").replace("{0}", pluginVer)} \u2192 ${t("runtime_health_package_ver").replace("{0}", pyVer)}`
          : (setupDone ? `Plugin v${pluginVer} \u2192 Python package not installed. Click "Sync Runtime" to install.`
            : `Plugin v${pluginVer} \u2192 Not configured. Please open the setup wizard first.`);
        versionRow.setDesc(descText);
        if (pyVer === pluginVer) {
          badgeEl.setText(t("runtime_health_match"));
          badgeEl.className = "paperforge-runtime-badge match";
          if (syncBtn) syncBtn.setDisabled(true);
        } else if (pyVer) {
          badgeEl.setText(t("runtime_health_mismatch"));
          badgeEl.className = "paperforge-runtime-badge mismatch";
          if (syncBtn) syncBtn.setDisabled(false);
        } else {
          badgeEl.setText(setupDone ? "Not installed" : "Setup needed");
          badgeEl.className = "paperforge-runtime-badge missing";
          if (syncBtn) syncBtn.setDisabled(false);
        }
      });
    }

    /* Preparation Guide */
    containerEl.createEl("h3", { text: t("section_prep") });
    containerEl.createEl("p", { text: t("section_prep_desc"), cls: "paperforge-settings-desc" });
    const prep = containerEl.createEl("div", { cls: "paperforge-guide" });
    const prepData = [
      ["prep_python", "prep_python_desc"],
      ["prep_zotero", "prep_zotero_desc"],
      ["prep_bbt", "prep_bbt_desc"],
      ["prep_key", "prep_key_desc"],
    ];
    for (const [kTitle, kDesc] of prepData) {
      const row = prep.createEl("div", { cls: "paperforge-guide-item" });
      row.createEl("strong", { text: t(kTitle) });
      row.createEl("span", { text: " \u2014 " + t(kDesc) });
    }

    /* Pre-check status area */
    this._checkEl = containerEl.createEl("div", { cls: "paperforge-message" });

    /* Install / Reconfigure Button */
    const needSetup = !this.plugin.settings.setup_complete;
    new Setting(containerEl)
      .setName(t(needSetup ? "btn_install" : "btn_reconfig"))
      .setDesc(t(needSetup ? "btn_install_desc" : "btn_reconfig_desc"))
      .addButton((btn) => {
        btn.setButtonText(t(needSetup ? "btn_install" : "btn_reconfig"))
          .setCta()
          .onClick(() => {
            if (!needSetup) {
              new PaperForgeSetupModal(this.app, this.plugin).open();
            } else {
              this._preCheck(() => {
                new PaperForgeSetupModal(this.app, this.plugin).open();
              });
            }
          });
      });

    /* Operation Guide */
    containerEl.createEl("h3", { text: t("section_guide") });
    const guide = containerEl.createEl("div", { cls: "paperforge-guide" });
    const guideData = [
      ["guide_open", "guide_open_desc"],
      ["guide_sync", "guide_sync_desc"],
      ["guide_ocr", "guide_ocr_desc"],
    ];
    for (const [kTitle, kDesc] of guideData) {
      const row = guide.createEl("div", { cls: "paperforge-guide-item" });
      row.createEl("strong", { text: t(kTitle) });
      row.createEl("span", { text: " \u2014 " + t(kDesc) });
    }

    /* Config Summary */
    if (this.plugin.settings.setup_complete) {
      containerEl.createEl("h3", { text: t("section_config") });
      const summary = containerEl.createEl("div", { cls: "paperforge-summary" });
      const s = this.plugin.settings;
      const pf = this._pfConfig;
      const items = [
        { label: t("dir_vault"), val: vaultPath },
        { label: t("dir_resources"), val: `${vaultPath}/${pf?.resources_dir}` },
        { label: "  " + t("dir_notes"), val: `${vaultPath}/${pf?.resources_dir}/${pf?.literature_dir}` },
        { label: t("dir_base"), val: `${vaultPath}/${pf?.base_dir}` },
        { label: t("dir_system"), val: `${vaultPath}/${pf?.system_dir}` },
        { label: "API Key", val: s.paddleocr_api_key ? t("api_key_set") : t("api_key_missing") },
        { label: t("field_zotero_data"), val: s.zotero_data_dir || t("not_set") },
      ];
      for (const item of items) {
        const row = summary.createEl("div", { cls: "paperforge-summary-row" });
        row.createEl("span", { cls: "paperforge-summary-label", text: item.label });
        row.createEl("span", { cls: "paperforge-summary-value", text: item.val });
      }
    }
  }

  _execMemoryStatus(pythonPath: string, vp: string, callback: (text: string) => void) {
    exec(`"${pythonPath}" -m paperforge --vault "${vp}" memory status --json`, { encoding: "utf-8", timeout: 15000 }, (err, stdout) => {
      if (err) { callback("Status unavailable"); return; }
      try {
        const data = JSON.parse(stdout);
        if (data.ok) {
          const s = data.data;
          const freshness = s.fresh ? "fresh" : "stale";
          callback(`Papers: ${s.paper_count_db} | ${freshness}${s.needs_rebuild ? " - needs rebuild" : ""}`);
        } else {
          callback("DB not found. Run paperforge memory build.");
        }
      } catch (e) { callback("Could not parse status."); }
    });
  }

  _execEmbedStatus(pythonPath: string, vp: string, callback: (text: string) => void) {
    exec(`"${pythonPath}" -m paperforge --vault "${vp}" embed status --json`, { encoding: "utf-8", timeout: 15000 }, (err, stdout) => {
      if (err) { callback("Status unavailable"); return; }
      try {
        const data = JSON.parse(stdout);
        if (data.ok) {
          callback(`Chunks: ${data.data.chunk_count} | ${data.data.model} | ${data.data.mode}`);
        } else {
          callback("Could not parse status.");
        }
      } catch (e) { callback("Could not parse status."); }
    });
  }

  _callPython(command: string[], opts?: any) {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const py = getCachedPython(vp, this.plugin.settings);
    const args = [...py.extraArgs, "-m", "paperforge", "--vault", vp, ...command];
    if (opts && opts.stream) {
      const child = spawn(py.path, args, { cwd: vp, env: opts.env || process.env, windowsHide: true });
      if (opts.onData) child.stdout.on("data", opts.onData);
      if (opts.onStderr) child.stderr.on("data", opts.onStderr);
      if (opts.onError) child.on("error", opts.onError);
      child.on("close", opts.onClose);
      return child;
    }
    execFile(py.path, args, { cwd: vp, timeout: opts && opts.timeout || 60000 },
      (err, stdout, stderr) => { if (opts && opts.onClose) opts.onClose(err ? 1 : 0, stdout, stderr); });
    return null;
  }

  _renderMemoryStatusText(el: HTMLElement, text: string, extraInfo: string | null | undefined) {
    el.innerHTML = "";
    el.createEl("span", { text: text, cls: "paperforge-memory-text" }).style.cssText = "flex:1;";

    if (extraInfo === "syncing") {
      const syncEl = el.createEl("span", { text: "Syncing...", cls: "paperforge-sync-status" });
      syncEl.style.cssText = "opacity:0.7; margin-right:8px;";
    } else if (extraInfo) {
      const timeEl = el.createEl("span", { text: extraInfo, cls: "paperforge-sync-status" });
      timeEl.style.cssText = "opacity:0.7; margin-right:8px;";
    }

    const rebuildBtn = el.createEl("button", { cls: "paperforge-rebuild-btn", text: t("feat_memory_rebuild_btn") });
    rebuildBtn.style.cssText = "margin-left:auto; border:1px solid var(--background-modifier-border); background:var(--background-secondary); cursor:pointer; font-size:11px; padding:2px 6px; border-radius:3px; margin-right:4px;";
    rebuildBtn.title = "Rebuild memory database";
    rebuildBtn.onclick = () => {
      const vp = (this.app.vault.adapter as any).basePath as string;
      const py = getCachedPython(vp, this.plugin.settings);
      if (!py.path) { new Notice(t("feat_no_python")); return; }
      console.log("[PaperForge] Rebuilding memory:", py.path);
      rebuildBtn.setText(t("feat_memory_rebuilding"));
      rebuildBtn.setAttr("disabled", "");
      this._callPython(["memory", "build"], {
        timeout: 60000,
        onClose: (code: number | null, stdout: string, stderr: string) => {
          console.log("[PaperForge] memory build exit:", code ? "FAIL:" + code : "OK", (stdout || "").slice(0, 200), (stderr || "").slice(0, 200));
          rebuildBtn.setText(t("feat_memory_rebuild_btn"));
          rebuildBtn.removeAttribute("disabled");
          if (code === 0) {
            new Notice(t("feat_memory_rebuild_done"));
          } else {
            new Notice(t("feat_memory_rebuild_failed") + (stderr ? " " + stderr.slice(0, 80) : ""));
          }
          this._memoryStatusText = getMemoryStatusText(vp);
          this._refreshSnapshots(vp);
        },
      });
    };

    const refreshBtn = el.createEl("button", { cls: "paperforge-refresh-btn", text: "\u21BB" });
    refreshBtn.style.cssText = "border:none; background:none; cursor:pointer; font-size:16px; padding:0 4px;";
    refreshBtn.title = "Sync now";
    refreshBtn.onclick = () => {
      this._memoryStatusText = null;
      this._runManualSync();
    };
  }

  _getBuildCommand(settings: PaperForgeSettings): string | null {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const pyResult = resolvePythonExecutable(vp, settings, undefined, undefined);
    if (!pyResult.path) return null;
    return `"${pyResult.path}" -m paperforge --vault "${vp}" sync`;
  }

  _runManualSync() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const py = getCachedPython(vp, this.plugin.settings);
    if (!py.path) return;

    const statusRow = document.querySelector(".paperforge-memory-status");
    if (statusRow) {
      this._renderMemoryStatusText(statusRow as HTMLElement, "Checking...", "syncing");
    }

    this.plugin._autoSyncRunning = true;
    this._callPython(["sync"], {
      timeout: 120000,
      onClose: (code: number | null) => {
        this.plugin._autoSyncRunning = false;
        this._memoryStatusText = null;
        if (code === 0) {
          this._lastSyncTime = new Date().toLocaleTimeString();
          this.plugin._lastSyncTime = this._lastSyncTime;
        }
        this.display();
        this._refreshSnapshots(vp);
        checkOrphanState(this.app, this.plugin, vp);
      },
    });
  }

  _refreshSnapshots(vp: string) {
    const py = getCachedPython(vp, this.plugin.settings);
    const args = [...py.extraArgs, "-m", "paperforge", "--vault", vp, "runtime-health", "--json"];

    this._refreshPending = true;

    execFile(py.path, args, { cwd: vp, timeout: 30000, windowsHide: true },
      (err, stdout, stderr) => {
        this._refreshPending = false;
        this._memoryStatusText = getMemoryStatusText(vp);
        this._embedStatusText = getVectorStatusText(vp);
        this.display();
      },
    );
  }

  _renderFeaturesTab(containerEl: HTMLElement) {
    // --- Section: Skills ---
    containerEl.createEl("h3", { text: "Skills" });
    const skillsDescEl = containerEl.createEl("div", { cls: "paperforge-desc-box" });
    skillsDescEl.style.cssText = "padding:8px 12px; margin:0 0 12px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;";
    skillsDescEl.setText(t("feat_skills_desc"));
    skillsDescEl.createEl("br");
    skillsDescEl.createEl("span", { text: t("feat_skills_system"), cls: "" }).style.opacity = "0.7";

    // Agent platform selector
    const agentPlatforms: Record<string, string> = {
      opencode: "OpenCode",
      claude: "Claude Code",
      codex: "Codex",
      cursor: "Cursor",
      windsurf: "Windsurf",
      github_copilot: "GitHub Copilot",
      gemini: "Gemini CLI",
    };
    const agentDirs: Record<string, string> = {
      opencode: ".opencode/skills",
      claude: ".claude/skills",
      codex: ".codex/skills",
      cursor: ".cursor/skills",
      windsurf: ".windsurf/skills",
      github_copilot: ".github/skills",
      gemini: ".gemini/skills",
    };

    const vaultPath = (this.app.vault.adapter as any).basePath as string;

    let selectedPlatform = this.plugin.settings.selected_skill_platform || "opencode";

    new Setting(containerEl)
      .setName(t("feat_agent_platform"))
      .setDesc(t("feat_agent_platform_desc"))
      .addDropdown(dropdown => {
        Object.entries(agentPlatforms).forEach(([key, label]) => dropdown.addOption(key, label));
        dropdown.setValue(selectedPlatform)
          .onChange(value => {
            this.plugin.settings.selected_skill_platform = value;
            this.plugin.saveSettings();
            this.display();
          });
      })
      .addExtraButton(btn => {
        btn.setIcon("folder")
          .setTooltip("Open skills folder")
          .onClick(() => {
            const dir = agentDirs[selectedPlatform] || ".opencode/skills";
            const fullPath = path.join(vaultPath, dir);
            if (fs.existsSync(fullPath)) {
              exec(`start "" "${fullPath}"`);
            } else {
              new Notice(`Skills folder not found: ${dir}`);
            }
          });
      });

    // Show skills for selected platform
    const skillDir = path.join(vaultPath, agentDirs[selectedPlatform]);
    const systemSkills: any[] = [];
    const userSkills: any[] = [];

    if (fs.existsSync(skillDir)) {
      fs.readdirSync(skillDir, { withFileTypes: true }).forEach(entry => {
        if (!entry.isDirectory()) return;
        const skillFile = path.join(skillDir, entry.name, "SKILL.md");
        if (!fs.existsSync(skillFile)) return;
        const content = fs.readFileSync(skillFile, "utf-8");
        const nameMatch = content.match(/^name:\s*(.+)$/m);
        const lines = content.split("\n");
        const descIdx = lines.findIndex(l => /^description:/.test(l));
        let desc = "";
        if (descIdx >= 0) {
          const first = lines[descIdx].match(/^description:\s*(.+)$/);
          if (first && first[1] && first[1] !== ">" && first[1] !== "|-" && first[1] !== "|") {
            desc = first[1].trim();
          } else {
            for (let i = descIdx + 1; i < lines.length; i++) {
              if (/^\s{2,}/.test(lines[i]) || lines[i].trim() === "") {
                desc += lines[i].trim() + " ";
              } else break;
            }
            desc = desc.trim();
          }
        }
        const sourceMatch = content.match(/^source:\s*(.+)$/m);
        const disableMatch = content.match(/^disable-model-invocation:\s*(.+)$/m);
        const versionMatch = content.match(/^version:\s*(.+)$/m);

        const skill = {
          name: nameMatch ? nameMatch[1].trim() : entry.name,
          desc: desc,
          source: sourceMatch ? sourceMatch[1].trim() : "user",
          disabled: disableMatch && disableMatch[1].trim() === "true",
          version: versionMatch ? versionMatch[1].trim() : "",
          path: skillFile,
          content: content,
          dirName: entry.name,
        };

        if (skill.source === "paperforge") {
          systemSkills.push(skill);
        } else {
          userSkills.push(skill);
        }
      });
    }

    const skillsBox = containerEl.createEl("div");
    skillsBox.style.cssText = "background:var(--background-secondary); border-radius:8px; padding:12px 12px 10px; margin:8px 0 16px;";

    const renderCollapsibleSkills = (label: string, skills: any[], isSystem: boolean) => {
      if (skills.length === 0) return;

      const group = skillsBox.createEl("div", { cls: "paperforge-skills-group" });
      const header = group.createEl("div", { cls: "paperforge-skills-collapse-header" });
      const content = group.createEl("div", { cls: "paperforge-skills-collapse-content" });
      const arrow = header.createEl("span", { text: "\u25BC", cls: "paperforge-skills-arrow" });
      arrow.style.cssText = "display:inline-block; font-size:10px; margin-right:6px; transition:transform 0.2s; transform:rotate(0deg);";
      header.createEl("h4", { text: `${label} (${skills.length})`, cls: "paperforge-skills-subheader" });

      skills.forEach(s => {
        const nameText = s.name + (s.version ? " v" + s.version : "");
        const sourceLabel = isSystem ? " [system]" : " [user]";
        const descText = s.desc || "";

        const setting = new Setting(content)
          .setName(nameText + sourceLabel)
          .setDesc(descText);
        setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";

        setting.addToggle(toggle => {
          toggle.setValue(!s.disabled)
            .onChange(value => {
              const newDisabled = !value;
              const disableMatch = s.content.match(/^disable-model-invocation:\s*(.+)$/m);
              const newContent = disableMatch
                ? s.content.replace(/^disable-model-invocation:\s*.+$/m, `disable-model-invocation: ${newDisabled}`)
                : s.content.replace(/^(---\r?\n)/, `$1disable-model-invocation: ${newDisabled}\n`);
              fs.writeFileSync(s.path, newContent, "utf-8");
              s.disabled = newDisabled;
              s.content = newContent;
              setting.settingEl.style.opacity = s.disabled ? "0.4" : "1";
            });
        });
      });

      const stateKey = isSystem ? "system" : "user";
      const collapsed = this._skillsCollapsed[stateKey] || false;
      if (collapsed) {
        content.style.display = "none";
        arrow.style.transform = "rotate(-90deg)";
      }

      header.addEventListener("click", () => {
        const nowCollapsed = content.style.display !== "none";
        if (nowCollapsed) {
          content.style.display = "none";
          arrow.style.transform = "rotate(-90deg)";
        } else {
          content.style.display = "";
          arrow.style.transform = "rotate(0deg)";
        }
        this._skillsCollapsed[stateKey] = content.style.display === "none";
      });
    };

    // System skills
    renderCollapsibleSkills("System Skills", systemSkills, true);

    // User skills
    renderCollapsibleSkills("User Skills", userSkills, false);

    if (systemSkills.length === 0 && userSkills.length === 0) {
      skillsBox.createEl("p", {
        text: `No skills found in ${agentDirs[selectedPlatform]}. Run setup to deploy skills.`,
        cls: "setting-item-description",
      });
    }

    // --- Section: Advanced ---
    if (this._advCollapsed === undefined) this._advCollapsed = true;
    const advHeader = containerEl.createEl("div", { cls: "paperforge-collapsible-header" });
    advHeader.style.cssText = "cursor:pointer; display:flex; align-items:center; gap:8px; padding:8px 0; user-select:none;";
    const advArrow = advHeader.createEl("span", { text: "\u25B6", cls: "paperforge-collapsible-arrow" });
    advArrow.style.cssText = "display:inline-block; transition:transform 0.2s; font-size:10px; transform:" + (this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)") + ";";
    const advTitle = advHeader.createEl("span", { text: "Advanced" });
    advTitle.style.cssText = "font-size:16px; font-weight:700; line-height:1.4;";
    const advSub = advHeader.createEl("span", { text: "Memory + Vector DB + Embedding" });
    advSub.style.cssText = "font-size:12px; color:var(--text-muted); margin-left:10px;";

    const advContent = containerEl.createEl("div", { cls: "paperforge-collapsible-content" });
    advContent.style.display = this._advCollapsed ? "none" : "";

    advHeader.addEventListener("click", () => {
      this._advCollapsed = !this._advCollapsed;
      advContent.style.display = this._advCollapsed ? "none" : "";
      advArrow.style.transform = this._advCollapsed ? "rotate(0deg)" : "rotate(90deg)";
    });

    // Memory Layer section
    advContent.createEl("h4", { text: "Memory Layer" });

    const memoryDescEl = advContent.createEl("div", { cls: "paperforge-desc-box" });
    memoryDescEl.style.cssText = "padding:8px 12px; margin:0 0 12px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;";
    memoryDescEl.setText(t("feat_memory_desc"));

    const statusRow = advContent.createEl("div", { cls: "paperforge-memory-status" });
    statusRow.style.cssText = "display:flex; align-items:center; padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;";

    const vp = (this.app.vault.adapter as any).basePath as string;

    if (this.plugin._lastSyncTime && !this._lastSyncTime) {
      this._lastSyncTime = this.plugin._lastSyncTime;
    }

    if (this._memoryStatusText === null) {
      this._memoryStatusText = getMemoryStatusText(vp);
    }
    this._renderMemoryStatusText(statusRow, this._memoryStatusText, this._lastSyncTime);

    this._renderVectorSection(advContent);
  }

  _renderVectorSection(containerEl: HTMLElement) {
    // --- Vector Database ---
    containerEl.createEl("h4", { text: "Vector Database" });

    if (!this.plugin.settings.features) {
      this.plugin.settings.features = { memory_layer: true, vector_db: false };
    }

    const vecDescEl = containerEl.createEl("div", { cls: "paperforge-desc-box" });
    vecDescEl.style.cssText = "padding:8px 12px; margin:0 0 8px; background:var(--background-secondary); border-radius:4px; font-size:12px; color:var(--text-muted); line-height:1.5;";
    vecDescEl.setText(t("feat_vector_desc"));

    new Setting(containerEl)
      .setName(t("feat_vector_enable"))
      .setDesc(t("feat_vector_enable_desc"))
      .addToggle(toggle => {
        toggle.setValue(!!this.plugin.settings.features.vector_db)
          .onChange(value => {
            this.plugin.settings.features.vector_db = value;
            this.plugin.saveSettings();
            this._vectorDepsOk = null;
            this._embedStatusText = null;
            this.display();
          });
      });

    if (!this.plugin.settings.features.vector_db) return;

    const vp = (this.app.vault.adapter as any).basePath as string;

    const vecConfigHeader = containerEl.createEl("div", { cls: "paperforge-skills-collapse-header" });
    vecConfigHeader.style.cssText = "display:flex; align-items:center; cursor:pointer; padding:6px 0 2px; margin:0;";
    const vecArrow = vecConfigHeader.createEl("span", { text: "\u25BC" });
    vecArrow.style.cssText = "display:inline-block; font-size:10px; margin-right:6px; transition:transform 0.2s;";
    vecConfigHeader.createEl("span", { text: t("feat_vector_config_label"), cls: "" }).style.cssText = "font-size:12px; color:var(--text-muted);";
    const vecConfigContent = containerEl.createEl("div", { cls: "paperforge-vector-config" });

    const applyVectorConfigDisclosure = (collapsed: boolean) => {
      vecConfigContent.style.display = collapsed ? "none" : "";
      vecArrow.style.transform = collapsed ? "rotate(-90deg)" : "rotate(0deg)";
    };

    applyVectorConfigDisclosure(getDisclosureState(this._featurePanelsCollapsed, "vectorConfig", false));

    vecConfigHeader.addEventListener("click", () => {
      const collapsed = toggleDisclosureState(this._featurePanelsCollapsed, "vectorConfig", false);
      applyVectorConfigDisclosure(collapsed);
    });

    if (this._vectorDepsOk === true) {
      this._renderVectorReady(vecConfigContent, vp);
      return;
    }
    if (this._vectorDepsOk === false) {
      this._renderVectorNoDeps(vecConfigContent);
      return;
    }
    if (this._vectorDepsOk === null) {
      const vr = getVectorRuntime(vp);
      this._vectorDepsOk = vr ? (vr.deps_installed ?? false) : false;
      if (this._vectorDepsOk) {
        this._embedStatusText = getVectorStatusText(vp);
      }
      this.display();
    }
  }

  _renderApiConfig(containerEl: HTMLElement) {
    new Setting(containerEl)
      .setName(t("feat_openai_key"))
      .setDesc(t("feat_openai_key_desc"))
      .addText(text => {
        text.setPlaceholder("sk-...")
          .setValue(this.plugin.settings.vector_db_api_key || "")
          .onChange(value => {
            this.plugin.settings.vector_db_api_key = value;
            this.plugin.saveSettings();
          });
      });
    new Setting(containerEl)
      .setName(t("feat_api_base_url"))
      .setDesc(t("feat_api_base_url_desc"))
      .addText(text => {
        text.setPlaceholder("https://api.openai.com/v1")
          .setValue(this.plugin.settings.vector_db_api_base || "")
          .onChange(value => {
            this.plugin.settings.vector_db_api_base = value;
            this.plugin.saveSettings();
          });
      });
    new Setting(containerEl)
      .setName(t("feat_api_model"))
      .setDesc(t("feat_api_model_desc"))
      .addText(text => {
        text.setPlaceholder("text-embedding-3-small")
          .setValue(this.plugin.settings.vector_db_api_model || "text-embedding-3-small")
          .onChange(value => {
            this.plugin.settings.vector_db_api_model = value;
            this.plugin.saveSettings();
          });
      });
  }

  _renderVectorNoDeps(containerEl: HTMLElement) {
    const box = containerEl.createEl("div");
    box.style.cssText = "padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;";
    box.setText(t("feat_deps_missing"));

    new Setting(containerEl)
      .setName(t("feat_install_deps"))
      .setDesc(t("feat_install_deps_desc"))
      .addButton(button => {
        button.setButtonText(t("feat_install_btn"))
          .setCta()
          .onClick(async () => {
            const vp = (this.app.vault.adapter as any).basePath as string;
            const pyResult = getCachedPython(vp, this.plugin.settings);
            if (!pyResult.path) { new Notice(t("feat_no_python")); return; }
            button.setButtonText(t("feat_installing"));
            button.setDisabled(true);
            const pkgs = "chromadb openai";
            const notice = new Notice(t("feat_installing_pkgs").replace("{pkgs}", pkgs), 0);
            try {
              const env = Object.assign({}, process.env, { PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1" });
              const pkgsArg = pkgs.split(" ");
              await new Promise<void>((resolve, reject) => {
                execFile(pyResult.path, [...pyResult.extraArgs, "-m", "pip", "install", ...pkgsArg], {
                  cwd: vp, timeout: 300000, env: env, windowsHide: true,
                }, (error) => { error ? reject(error) : resolve(); });
              });
              notice.hide();
              new Notice(t("feat_install_done"));
              this._vectorDepsOk = true;
              this._embedStatusText = getVectorStatusText(vp);
              this.display();
            } catch (e: any) {
              notice.hide();
              new Notice(t("feat_install_failed") + (e.stderr || e.message || e));
              button.setButtonText(t("feat_retry_btn"));
              button.setDisabled(false);
            }
          });
      });
  }

  _renderVectorReady(containerEl: HTMLElement, vp: string) {
    const statusEl = containerEl.createEl("div");
    statusEl.style.cssText = "padding:8px 12px; margin:8px 0; background:var(--background-secondary); border-radius:4px;";
    statusEl.setText(getVectorStatusText(vp));

    this._renderApiConfig(containerEl);

    const embedSection = containerEl.createEl("div");
    embedSection.style.cssText = "padding:4px 0;";

    const embedHeader = embedSection.createEl("div");
    embedHeader.style.cssText = "display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;";
    embedHeader.createEl("span", { text: t("feat_rebuild_vectors"), cls: "setting-item-name" });

    const embedControls = embedSection.createEl("div");
    embedControls.style.cssText = "display:flex; align-items:center; gap:8px;";

    const embedStatusText = embedSection.createEl("div", { cls: "paperforge-embed-status-text" });

    const renderEmbedUI = () => {
      embedControls.empty();
      embedStatusText.empty();
      const buildState: any = (getVectorRuntime(vp) || {}).build_state || {};
      this.plugin._embedProgress = this.plugin._embedProgress || { current: 0, total: 0, key: "" };

      if (!this.plugin._embedProcess && buildState.status === "running") {
        this.plugin._embedProgress = {
          current: buildState.current || 0,
          total: buildState.total || 1,
          key: buildState.paper_id || "",
        };
      }

      const { current, total, key } = this.plugin._embedProgress;
      const isRunning = !!(this.plugin._embedProcess) || buildState.status === "running";

      if (isRunning) {
        const track = embedControls.createEl("div", { cls: "paperforge-progress-track" });
        track.style.cssText = "flex:1;";
        const pct = total > 0 ? (current / total * 100).toFixed(1) : "0";
        const doneSeg = track.createEl("div", { cls: "paperforge-progress-seg done" });
        doneSeg.style.cssText = `width:${pct}%; min-width:${current > 0 ? "2px" : "0"};`;
        if (current < total) {
          const pendingSeg = track.createEl("div", { cls: "paperforge-progress-seg pending" });
          pendingSeg.style.cssText = `width:${(100 - parseFloat(pct)).toFixed(1)}%;`;
        }
        embedStatusText.createEl("span", { cls: "paperforge-embed-progress-text",
          text: `${current}/${total} papers` });
        if (key) {
          embedStatusText.createEl("span", { cls: "paperforge-embed-progress-key",
            text: ` (${key})` });
        }

        const stopBtn = embedControls.createEl("button");
        stopBtn.setText("Stop");
        stopBtn.className = "mod-warning";
        stopBtn.addEventListener("click", () => {
          this._callPython(["embed", "stop", "--json"], { timeout: 8000 });
          if (this.plugin._embedProcess) {
            (this.plugin._embedProcess as any).kill();
            this.plugin._embedProcess = null;
          }
          this.display();
        });
      } else {
        const embedInfo = getVectorRuntime(vp);
        const hasChunks = !!(embedInfo && (embedInfo.chunk_count ?? 0) > 0);
        const isCorrupted = embedInfo && (embedInfo as any).corrupted;

        const startBuild = (flag: string) => {
          const py = getCachedPython(vp, this.plugin.settings);
          if (!py.path) { new Notice(t("feat_no_python")); return; }
          const env = Object.assign({}, process.env, {
            PYTHONIOENCODING: "utf-8", PYTHONUTF8: "1",
            VECTOR_DB_API_KEY: this.plugin.settings.vector_db_api_key || "",
            VECTOR_DB_API_BASE: this.plugin.settings.vector_db_api_base || "",
            VECTOR_DB_API_MODEL: this.plugin.settings.vector_db_api_model || "",
          });
          this.plugin._embedStderr = "";
          this.plugin._embedProgress = { current: 0, total: 0, key: "" };
          this.plugin._embedProcess = this._callPython(["embed", "build", flag], {
            stream: true,
            env: env,
            onData: (data: any) => {
              const lines = data.toString("utf-8").split("\n");
              for (const line of lines) {
                if (line.startsWith("EMBED_START:")) {
                  this.plugin._embedProgress!.total = parseInt(line.split(":")[1]) || 0;
                } else if (line.startsWith("EMBED_PROGRESS:")) {
                  const parts = line.split(":");
                  this.plugin._embedProgress!.current = parseInt(parts[1]) || 0;
                  this.plugin._embedProgress!.key = parts[3] || "";
                } else if (line.startsWith("EMBED_DONE")) {
                  this.plugin._embedProcess = null;
                  this.plugin._embedProgress!.current = this.plugin._embedProgress!.total;
                }
              }
              this.display();
            },
            onStderr: (data: any) => {
              if (!this.plugin._embedStderr) this.plugin._embedStderr = "";
              this.plugin._embedStderr += data.toString("utf-8");
            },
            onError: (err: any) => {
              this.plugin._embedProcess = null;
              new Notice(t("feat_build_failed") + ": " + (err.message || err));
              this.display();
            },
            onClose: (code: number | null) => {
              this.plugin._embedProcess = null;
              if (code === 0) {
                this.plugin._embedProgress!.current = this.plugin._embedProgress!.total;
                this.plugin.saveSettings();
                this._embedStatusText = getVectorStatusText(vp);
                new Notice(t("feat_build_complete"));
              } else {
                this._embedStatusText = null;
                const errMsg = (this.plugin._embedStderr || "").slice(0, 200);
                new Notice(t("feat_build_failed") + (errMsg ? ": " + errMsg : ""), 8000);
              }
              this.plugin._embedStderr = "";
              this.display();
              this._refreshSnapshots(vp);
            },
          });

          this.display();
        };

        if (isCorrupted) {
          const warnEl = embedSection.createEl("div");
          warnEl.style.cssText = "padding:8px 12px; margin:8px 0; background:var(--background-modifier-warning); border-radius:4px; font-size:12px; display:flex; align-items:center; justify-content:space-between;";
          warnEl.createEl("span", { text: t("feat_vector_corrupted") });
          const forceBtn = warnEl.createEl("button", { text: t("feat_vector_rebuild_force_btn") });
          forceBtn.className = "mod-cta";
          forceBtn.addEventListener("click", () => startBuild("--force"));
        }

        if (hasChunks && !isCorrupted) {
          embedControls.createEl("span", {
            text: embedInfo.chunk_count + " chunks embedded",
            cls: "setting-item-description",
          });
        }
        const buildBtn = embedControls.createEl("button");
        buildBtn.setText(hasChunks ? t("feat_rebuild_btn") : t("feat_build_btn"));
        buildBtn.addClass("mod-cta");
        buildBtn.addEventListener("click", () => startBuild("--resume"));
        if (!isCorrupted && hasChunks) {
          const forceBtn2 = embedControls.createEl("button");
          forceBtn2.setText(t("feat_vector_rebuild_force_btn"));
          forceBtn2.style.marginLeft = "6px";
          forceBtn2.addEventListener("click", () => startBuild("--force"));
        }
      }
    };

    renderEmbedUI();
  }

  _getCurrentModelKey(): string {
    return this.plugin.settings.vector_db_api_model || "text-embedding-3-small";
  }

  _parseEmbedStatus(text: string): Record<string, any> {
    const info: Record<string, any> = {};
    if (!text) return info;
    text.split("\n").forEach(line => {
      const m = line.match(/^\s*([^:]+):\s*(.*)/);
      if (m) info[m[1].trim()] = m[2].trim();
    });
    if (info.db_exists !== undefined) info.db_exists = info.db_exists === "True";
    if (info.chunk_count !== undefined) info.chunk_count = parseInt(info.chunk_count, 10) || 0;
    return info;
  }

  _getPythonDesc(pyPath: string, source: string): string {
    if (source === "stale") {
      return `[!!] ${pyPath} (stale \u2014 path no longer exists, update or clear the override below)`;
    }
    if (source === "manual") {
      return `${pyPath} (manual)`;
    }
    return `${pyPath} (auto-detected)`;
  }

  _refreshPythonInterpDesc(pyPath: string, source: string) {
    const desc = this._pythonInterpDescEl;
    if (desc) {
      if (source === "stale") {
        desc.textContent = `[!!] ${pyPath} (stale \u2014 path no longer exists, update or clear the override below)`;
      } else if (source === "manual") {
        desc.textContent = `${pyPath} (manual)`;
      } else {
        desc.textContent = `${pyPath} (auto-detected)`;
      }
    }
  }

  _validatePythonOverride() {
    const customPath = this.plugin.settings.python_path ? this.plugin.settings.python_path.trim() : "";
    const desc = this._customPathDescEl;

    if (!customPath) {
      const msg = "\u8BF7\u8F93\u5165\u8DEF\u5F84 / Enter a path first";
      if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg);
      return;
    }

    if (!fs.existsSync(customPath)) {
      const msg = "\u8DEF\u5F84\u4E0D\u5B58\u5728 / Path does not exist";
      if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg, 4000);
      return;
    }

    try {
      fs.accessSync(customPath, fs.constants.X_OK);
    } catch {
      const msg = "\u4E0D\u53EF\u6267\u884C / Not executable";
      if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
      new Notice(msg, 4000);
      return;
    }

    execFile(customPath, ["--version"], { timeout: 8000 }, (verErr, verOut) => {
      if (verErr || !verOut) {
        const msg = "\u65E0\u6CD5\u8FD0\u884C / Cannot run";
        if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      const match = verOut.match(/Python (\d+)\.(\d+)/);
      if (!match) {
        const msg = "\u65E0\u6CD5\u89E3\u6790\u7248\u672C / Cannot parse version";
        if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      const major = parseInt(match[1], 10);
      const minor = parseInt(match[2], 10);

      if (major < 3 || (major === 3 && minor < 10)) {
        const msg = "Python \u7248\u672C\u8FC7\u4F4E\uFF0C\u9700\u8981 3.10+ / Python version too low, need 3.10+";
        if (desc) desc.innerHTML = `<span style="color:var(--text-error)">\u2717 ${msg}</span>`;
        new Notice(msg, 4000);
        return;
      }

      execFile(customPath, ["-m", "pip", "--version"], { timeout: 8000 }, (pipErr) => {
        if (pipErr) {
          const warnMsg = `\u2713 Python ${major}.${minor} \u6709\u6548\uFF0C\u4F46\u672A\u68C0\u6D4B\u5230 pip / Valid, but pip not found`;
          if (desc) desc.innerHTML = `<span style="color:var(--text-warning)">\u26A0 ${warnMsg}</span>`;
          new Notice(warnMsg, 4000);
        } else {
          const okMsg = `\u2713 Python ${major}.${minor} \u6709\u6548 / Valid`;
          if (desc) desc.innerHTML = `<span style="color:var(--text-accent)">${okMsg}</span>`;
          new Notice(okMsg, 4000);
        }
      });
    });
  }

  _syncRuntime(btn: any) {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.plugin.settings, undefined, undefined);
    const ver = this.plugin.manifest.version;
    const installCmd = buildRuntimeInstallCommand(pythonExe, ver, extraArgs);

    btn.setDisabled(true);
    btn.setButtonText(t("runtime_health_syncing"));

    const tryInstall = (args: string[], label: string) => {
      console.log(`[PaperForge] Sync Runtime: trying ${label}`);
      return runSubprocess(installCmd.cmd, args, vp, installCmd.timeout, undefined, paperforgeEnrichedEnv());
    };

    const deploySkills = () => {
      let agentKey = "opencode";
      try {
        const cfgRaw = fs.readFileSync(path.join(vp, "paperforge.json"), "utf-8");
        const cfg = JSON.parse(cfgRaw);
        if (cfg.agent_key) agentKey = cfg.agent_key;
      } catch {}
      const deployArgs = [...extraArgs, "-c",
        "from paperforge.services.skill_deploy import deploy_skills; " +
        "from pathlib import Path; " +
        'r=deploy_skills(vault=Path(r"' + vp.replace(/\\/g, "\\\\") + '"), agent_key="' + agentKey + '", overwrite=True); ' +
        'print("skills deployed" if r["skill_deployed"] else "skills skipped", flush=True)',
      ];
      const child = spawn(pythonExe, deployArgs, { cwd: vp, timeout: 30000, windowsHide: true });
      let out = "";
      child.stdout.on("data", (d) => { out += d.toString("utf-8"); });
      child.on("close", (code) => {
        console.log(`[PaperForge] Skill deploy: ${out.trim()} (exit ${code})`);
      });
    };

    tryInstall(installCmd.pypiArgs, "PyPI").then((result) => {
      if (result.exitCode === 0) {
        console.log("[PaperForge] Sync Runtime: installed via PyPI");
        deploySkills();
        new Notice(t("runtime_health_sync_done").replace("{0}", ver), 5000);
        this.display();
        return;
      }
      console.warn("[PaperForge] Sync Runtime: PyPI failed, falling back to git...");
      tryInstall(installCmd.gitArgs, "git").then((r2) => {
        if (r2.exitCode === 0) {
          console.log("[PaperForge] Sync Runtime: installed via git");
          deploySkills();
          new Notice(t("runtime_health_sync_done").replace("{0}", ver), 5000);
          this.display();
        } else {
          btn.setDisabled(false);
          btn.setButtonText(t("runtime_health_sync"));
          console.error("[PaperForge] git fallback stderr:", r2.stderr);
          new Notice(t("runtime_health_sync_fail").replace("{0}", "pip exit code " + r2.exitCode), 8000);
        }
      });
    });
  }

  _debouncedSave() {
    clearTimeout(this._saveTimeout!);
    this._saveTimeout = setTimeout(() => this.plugin.saveSettings(), 500);
  }

  _preCheck(onPass: () => void) {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vaultPath, this.plugin?.settings, undefined, undefined);
    execFile(pythonExe, [...extraArgs, "--version"], { timeout: 8000 }, (pyErr, pyOut) => {
      const results: { label: string; ok: boolean; detail: string }[] = [];

      /* Python */
      results.push({ label: "Python", ok: !pyErr, detail: pyErr ? t("check_python_fail") : pyOut.trim() });

      /* Zotero */
      let zotOk = false;
      const home = process.env.HOME || process.env.USERPROFILE || os.homedir() || "";
      if (process.platform === "darwin") {
        const macZot = [
          "/Applications/Zotero.app",
          path.join(home, "Applications", "Zotero.app"),
        ];
        zotOk = macZot.some(d => { try { return fs.existsSync(d); } catch { return false; } });
      } else if (process.platform === "win32") {
        const progFiles = process.env.ProgramFiles || "";
        const localAppData = process.env.LOCALAPPDATA || "";
        const zotInstallDirs = [
          path.join(progFiles, "Zotero"),
          path.join(progFiles, "(x86)", "Zotero"),
          path.join(localAppData, "Programs", "Zotero"),
          path.join(localAppData, "Zotero"),
          path.join(home, "AppData", "Local", "Programs", "Zotero"),
        ].filter(Boolean);
        zotOk = zotInstallDirs.some(d => { try { return fs.existsSync(d); } catch { return false; } });
      } else {
        const linuxPaths = [
          path.join(home, ".local", "share", "zotero", "zotero"),
          "/usr/bin/zotero",
          "/usr/local/bin/zotero",
        ];
        zotOk = linuxPaths.some(d => { try { return fs.existsSync(d); } catch { return false; } });
      }
      const zotDataDir = this.plugin.settings.zotero_data_dir;
      if (!zotOk && zotDataDir) {
        try { zotOk = fs.existsSync(zotDataDir); } catch {}
      }
      results.push({ label: "Zotero", ok: zotOk, detail: zotOk ? t("check_zotero_ok") : t("check_zotero_fail") });

      /* Better BibTeX */
      let bbtOk = false;
      const appData = process.env.APPDATA || "";
      if (process.platform === "win32" && appData) {
        bbtOk = scanBbtUnderProfiles(path.join(appData, "Zotero", "Zotero", "Profiles"));
      }
      if (!bbtOk && process.platform === "darwin" && home) {
        bbtOk = scanBbtUnderProfiles(path.join(home, "Library", "Application Support", "Zotero", "Profiles"));
      }
      if (!bbtOk && process.platform !== "win32" && process.platform !== "darwin" && home) {
        bbtOk = scanBbtUnderProfiles(path.join(home, ".zotero", "zotero", "Profiles"));
      }
      if (!bbtOk && zotDataDir && String(zotDataDir).trim()) {
        bbtOk = scanBbtDirectChildren(zotDataDir.trim());
      }
      if (!bbtOk && home) {
        bbtOk = scanBbtDirectChildren(path.join(home, "Zotero"));
      }
      results.push({ label: "Better BibTeX", ok: bbtOk, detail: bbtOk ? t("check_bbt_ok") : t("check_bbt_fail") });

      /* Render */
      const marks: Record<string, string> = { true: "\u2713", false: "\u2717" };
      if (this._checkEl) {
        this._checkEl.setText(results.map(r => `${marks[String(r.ok)]} ${r.label}: ${r.detail}`).join("\n"));
        const anyFail = results.some(r => !r.ok);
        this._checkEl.className = `paperforge-message msg-${anyFail ? "error" : "ok"}`;
      }
      const bad = results.filter(r => !r.ok);
      if (bad.length > 0) {
        new Notice(`[!!] \u672A\u901A\u8FC7: ${bad.map(r => r.label).join(", ")}`, 6000);
      }

      onPass();
    });
  }

  _renderMaintenanceTab(containerEl: HTMLElement) {
    containerEl.createEl("h2", { text: t("tab_maintenance") || "\u7EF4\u62A4" });

    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const py = resolvePythonExecutable(vaultPath, this.plugin.settings as any, fs, execFileSync);
    if (!py.path) {
      containerEl.createEl("p", { text: "\u26A0 Python \u672A\u914D\u7F6E\uFF0C\u8BF7\u5148\u5728\u201C\u5B89\u88C5\u201D\u6807\u7B7E\u9875\u914D\u7F6E\u3002", cls: "setting-item-description" });
      return;
    }

    // ── State ──
    const state = containerEl.createEl("div");
    state.createEl("p", { text: "\u6B63\u5728\u52A0\u8F7D OCR \u7EF4\u62A4\u6570\u636E\u2026" });

    // ── Run paperforge ocr list --json --output ──
    const tmpFile = path.join(os.tmpdir(), `pf_ocr_maintenance_${Date.now()}.json`);
    const args = ["-m", "paperforge", "ocr", "list", "--json", "--output", tmpFile];

    execFile(py.path, args, { cwd: vaultPath, timeout: 30000, windowsHide: true },
      (_err, _stdout, _stderr) => {
        state.empty();
        if (!fs.existsSync(tmpFile)) {
          state.createEl("p", { text: "\u274C \u65E0\u6CD5\u52A0\u8F7D OCR \u6570\u636E\u3002\u8BF7\u786E\u4FDD\u5DF2\u5B89\u88C5 paperforge \u5E76\u8FD0\u884C\u8FC7 OCR\u3002", cls: "setting-item-description" });
          return;
        }

        let rows: any[] = [];
        try { rows = JSON.parse(fs.readFileSync(tmpFile, "utf-8")); } catch { rows = []; }
        try { fs.unlinkSync(tmpFile); } catch {}
        if (!rows.length) {
          state.createEl("p", { text: "\u6CA1\u6709 OCR \u8BBA\u6587\u3002\u8BF7\u5148\u8FD0\u884C OCR\u3002" });
          return;
        }

        // ── Categorize each row ──
        const items = rows.map((row: any) => ({ row, ui: categorizeMaintenanceRow(row) }));
        const summary = buildMaintenanceSummary(items.map(item => item.ui));

        state.empty();

        // ── Hero: overall conclusion card ──
        const hero = state.createEl("div", { cls: "pf-maint-hero pf-card" });
        hero.createEl("h3", {
          text: summary.tone === "warn"
            ? t("ocr_maint_hero_warn").replace("{rebuild}", String(summary.counts.rebuild)).replace("{failed}", String(summary.counts.failed))
            : t("ocr_maint_hero_ok"),
        });
        hero.createEl("p", {
          text: t("ocr_maint_hero_note"),
          cls: "setting-item-description",
        });

        // Count chips
        const counts = hero.createEl("div", { cls: "pf-maint-counts" });
        for (const [label, value] of [
          [t("ocr_maint_no_action"), summary.counts.ok] as const,
          [t("ocr_maint_rebuild"), summary.counts.rebuild] as const,
          [t("ocr_maint_failed"), summary.counts.failed] as const,
        ]) {
          const stat = counts.createEl("div", { cls: "pf-maint-stat" });
          stat.createEl("strong", { text: String(value) });
          stat.createEl("span", { text: label });
        }

        // ── Section: Needs Attention ──
        const actionable = items.filter(item => item.ui.category === "rebuild" || item.ui.category === "failed");
        if (actionable.length > 0) {
          state.createEl("h3", { text: t("ocr_maint_needs_attention") });
          const actSection = state.createEl("div", { cls: "pf-maint-section" });
          for (const item of actionable) {
            const card = actSection.createEl("div", { cls: "pf-maint-card" });
            card.createEl("strong", { text: item.row.title_short || item.row.title || item.row.key });
            const chip = card.createEl("span", { cls: "pf-maint-chip pf-maint-chip--" + item.ui.category, text: item.ui.label });
            chip.style.marginLeft = "8px";
            card.createEl("p", { text: item.ui.reason, cls: "setting-item-description" });
            const btn = card.createEl("button", { text: item.ui.primaryAction === "rebuild" ? t("ocr_maint_rebuild_btn") : t("ocr_maint_redo_btn") });
            btn.style.cssText = "padding:4px 10px; border-radius:4px; cursor:pointer; font-size:12px;";
            btn.dataset.action = item.ui.primaryAction || "";
            btn.dataset.key = item.row.key;
          }
        }

        // ── Section: Result Limitations ──
        const limited = items.filter(item => item.ui.category === "limited");
        if (limited.length > 0) {
          state.createEl("h3", { text: t("ocr_maint_limitations") });
          state.createEl("p", {
            text: t("ocr_maint_limitations_intro"),
            cls: "setting-item-description",
          });
          for (const item of limited) {
            const card = state.createEl("div", { cls: "pf-maint-card" });
            card.createEl("strong", { text: item.row.title_short || item.row.title || item.row.key });
            const chip = card.createEl("span", { cls: "pf-maint-chip pf-maint-chip--limited", text: item.ui.label });
            chip.style.marginLeft = "8px";
            card.createEl("p", { text: item.ui.reason, cls: "setting-item-description" });
          }
        }

        // ── Section: All Papers (advanced, collapsed) ──
        const advanced = state.createEl("details", { cls: "pf-maint-advanced" });
        advanced.createEl("summary", { text: t("ocr_maint_all_papers") + " (" + rows.length + ")" });

        // Helper functions for the table
        const classifyPaper = (r: any) => {
          const s = r.status, h = r.health;
          if (s === "done" && r.version === "v1") return { badge: "? \u672A\u8BC4\u4F30", color: "#9e9e9e" };
          if (s === "done" && h === "green") return { badge: "\u2713 \u5B8C\u6210", color: "#4caf50" };
          if (s === "done" && h === "yellow") return { badge: "\u26A0 \u8D28\u91CF\u95EE\u9898", color: "#ff9800" };
          if (s === "done" && h === "red") return { badge: "\u26A0 \u4E25\u91CD\u5F02\u5E38", color: "#f44336" };
          if (s === "done_degraded") return { badge: "\u26A0 \u8D28\u91CF\u95EE\u9898", color: "#ff9800" };
          if (s === "failed" || s === "fatal_error") return { badge: "\u2717 \u5931\u8D25", color: "#f44336" };
          if (s === "pending" || s === "nopdf" || s === "blocked") return { badge: "\u25CB \u5F85\u5904\u7406", color: "#9e9e9e" };
          if (s === "running" || s === "queued") return { badge: "\u25CF \u5904\u7406\u4E2D", color: "#2196f3" };
          if (s === "retryable_error") return { badge: "\u2717 \u53EF\u91CD\u8BD5", color: "#ff9800" };
          return { badge: s, color: "#9e9e9e" };
        };
        const actionHint = (r: any) => {
          if (r.recommended_action === "redo") return "\u91CD\u65B0OCR";
          if (r.recommended_action === "rebuild") return "\u91CD\u5EFA\u7D22\u5F15";
          return "";
        };

        // Count categories for filter dropdown
        const catCounts: Record<string, number> = {};
        for (const r of rows) { const b = classifyPaper(r).badge; catCounts[b] = (catCounts[b] || 0) + 1; }
        const badgeOrder = ["\u2713 \u5B8C\u6210", "? \u672A\u8BC4\u4F30", "\u26A0 \u8D28\u91CF\u95EE\u9898", "\u26A0 \u4E25\u91CD\u5F02\u5E38", "\u2717 \u5931\u8D25", "\u25CB \u5F85\u5904\u7406", "\u25CF \u5904\u7406\u4E2D"];

        // Toolbar (inside details)
        const toolbar = advanced.createEl("div");
        toolbar.style.cssText = "display:flex; align-items:center; gap:8px; margin-bottom:8px; flex-wrap:wrap;";

        // Row state
        const selState: Record<string, { sel: boolean; action: string }> = {};
        for (const r of rows) { selState[r.key] = { sel: false, action: r.recommended_action || "" }; }

        // ── Active filter ──
        let activeFilter = "all";
        let filtered = rows;
        const redrawTable = () => {
          filtered = activeFilter === "all" ? rows : rows.filter((r: any) => classifyPaper(r).badge === activeFilter);
          tbody.empty();
          renderRows(filtered);
          updateSummary();
        };

        // Filter dropdown
        const filterSel = toolbar.createEl("select");
        filterSel.style.cssText = "padding:4px 8px; border-radius:4px;";
        filterSel.createEl("option", { text: "\u5168\u90E8", value: "all" });
        for (const k of badgeOrder) { if (catCounts[k]) filterSel.createEl("option", { text: k + " " + catCounts[k], value: k }); }
        filterSel.addEventListener("change", () => { activeFilter = filterSel.value; redrawTable(); });

        // Select / deselect / execute buttons
        const selAllBtn = toolbar.createEl("button", { text: "\u5168\u9009" });
        const deselAllBtn = toolbar.createEl("button", { text: "\u53D6\u6D88\u5168\u9009" });
        Object.assign(selAllBtn.style, { padding: "4px 10px", borderRadius: "4px", cursor: "pointer" });
        Object.assign(deselAllBtn.style, { padding: "4px 10px", borderRadius: "4px", cursor: "pointer" });
        const execBtn = toolbar.createEl("button", { text: "\u25B8 \u6267\u884C\u5DF2\u9009" });
        execBtn.style.cssText = "padding:4px 12px; border-radius:4px; cursor:pointer; font-weight:600; margin-left:auto;";
        const execLabel = toolbar.createEl("span", { cls: "setting-item-description" });
        execLabel.style.cssText = "font-size:11px;";

        const updateSummary = () => {
          let n = 0;
          for (const r of filtered) { if (selState[r.key].action) n++; }
          execLabel.setText("\u5F85\u4FEE\u590D " + n + " \u7BC7");
        };

        selAllBtn.addEventListener("click", () => {
          for (const r of filtered) {
            selState[r.key].sel = true;
            if (!selState[r.key].action) selState[r.key].action = r.recommended_action || "";
          }
          redrawTable();
        });
        deselAllBtn.addEventListener("click", () => {
          for (const r of rows) { selState[r.key].sel = false; selState[r.key].action = ""; }
          redrawTable();
        });
        execBtn.addEventListener("click", () => {
          const redoKeys: string[] = [], rebuildKeys: string[] = [];
          for (const r of rows) {
            const a = selState[r.key].action;
            if (a === "redo") redoKeys.push(r.key);
            else if (a === "rebuild") rebuildKeys.push(r.key);
          }
          if (!redoKeys.length && !rebuildKeys.length) { new Notice("\u8BF7\u5148\u9009\u62E9\u8981\u4FEE\u590D\u7684\u8BBA\u6587\u3002"); return; }
          state.empty();
          state.createEl("p", { text: "\u6267\u884C\u4E2D\u2026" });
          if (redoKeys.length) execFile(py.path, ["-m", "paperforge", "ocr", "redo", ...redoKeys],
            { cwd: vaultPath, timeout: 300000, windowsHide: true },
            () => { new Notice("\u91CD\u65B0OCR\u5DF2\u89E6\u53D1\uFF0C\u5171 " + redoKeys.length + " \u7BC7\u3002"); });
          if (rebuildKeys.length) execFile(py.path, ["-m", "paperforge", "ocr", "rebuild", ...rebuildKeys],
            { cwd: vaultPath, timeout: 120000, windowsHide: true },
            () => { new Notice("\u91CD\u5EFA\u5B8C\u6210\uFF0C\u5171 " + rebuildKeys.length + " \u7BC7\u3002"); });
        });

        // ── Table ──
        const tableWrapper = advanced.createEl("div");
        tableWrapper.style.cssText = "max-height:60vh; overflow-y:auto; border:1px solid var(--background-modifier-border); border-radius:6px; margin-bottom:16px;";
        const table = tableWrapper.createEl("table");
        table.style.cssText = "width:100%; border-collapse:collapse; font-size:12px;";
        const thead = table.createEl("thead");
        const tbody = table.createEl("tbody");
        const headerRow = thead.insertRow();
        ["", "Key", "Title", "\u72B6\u6001", "\u5EFA\u8BAE", "Model", "Time", "\u4FEE\u590D"].forEach(h => {
          const th = document.createElement("th");
          th.textContent = h;
          th.style.cssText = "padding:4px 6px; text-align:left; border-bottom:1px solid var(--background-modifier-border); position:sticky; top:0; background:var(--background-primary); z-index:1; white-space:nowrap;";
          headerRow.appendChild(th);
        });

        const badgeHtml = (label: string, color: string) =>
          `<span style="display:inline-block;padding:1px 6px;border-radius:3px;font-size:11px;background:${color}22;color:${color};border:1px solid ${color}44;white-space:nowrap;">${label}</span>`;

        const renderRows = (rowList: any[]) => {
          for (const r of rowList) {
            const st = selState[r.key];
            const cp = classifyPaper(r);
            const hint = actionHint(r);
            const tr = tbody.insertRow();
            tr.style.cssText = "border-bottom:1px solid var(--background-modifier-border);";

            // Sel checkbox
            const selTd = tr.insertCell(); selTd.style.cssText = "padding:3px 4px;";
            const selCb = document.createElement("input"); selCb.type = "checkbox"; selCb.checked = st.sel;
            selCb.addEventListener("change", () => {
              st.sel = selCb.checked;
              if (!st.sel && st.action) st.action = "";
              if (st.sel && !st.action) st.action = r.recommended_action || "";
            });
            selTd.appendChild(selCb);

            // Key
            const keyTd = tr.insertCell();
            keyTd.style.cssText = "padding:3px 4px; white-space:nowrap; font-size:11px; max-width:90px; overflow:hidden; text-overflow:ellipsis;";
            keyTd.textContent = r.key;

            // Title
            const titleTd = tr.insertCell();
            titleTd.style.cssText = "padding:3px 4px; white-space:nowrap; max-width:220px; overflow:hidden; text-overflow:ellipsis;";
            titleTd.textContent = r.title_short || r.title || r.key;
            titleTd.title = r.title || r.key;

            // Status badge
            const badgeTd = tr.insertCell();
            badgeTd.style.cssText = "padding:3px 4px; white-space:nowrap;";
            badgeTd.innerHTML = badgeHtml(cp.badge, cp.color);

            // Suggestion column
            const sugTd = tr.insertCell();
            sugTd.style.cssText = "padding:3px 4px; white-space:nowrap; max-width:160px; overflow:hidden; text-overflow:ellipsis; font-size:11px; color:var(--text-muted);";
            let sug = "";
            if (hint) sug = hint;
            else if (cp.badge === "\u2713 \u5B8C\u6210") sug = "\u5DF2\u5B8C\u6210";
            else if (cp.badge.includes("\u5F85\u5904\u7406")) sug = "\u7B49\u5F85OCR";
            else if (cp.badge.includes("\u5931\u8D25")) sug = r.error_summary?.substring(0, 50) || "";
            else if (cp.badge.includes("\u672A\u8BC4\u4F30")) sug = "\u5EFA\u8BAE\u91CD\u65B0\u5904\u7406";
            else if (r.degraded_reasons?.length) sug = r.degraded_reasons[0].substring(0, 50);
            sugTd.textContent = sug;

            // Model
            const modelTd = tr.insertCell();
            modelTd.style.cssText = "padding:3px 4px; white-space:nowrap; max-width:140px; overflow:hidden; text-overflow:ellipsis; font-size:11px;";
            modelTd.textContent = r.model || "-";

            // Time
            const timeTd = tr.insertCell();
            timeTd.style.cssText = "padding:3px 4px; white-space:nowrap; font-size:11px; color:var(--text-muted);";
            timeTd.textContent = r.finished_at || "-";

            // Fix checkbox
            const fixTd = tr.insertCell(); fixTd.style.cssText = "padding:3px 4px; text-align:center; white-space:nowrap;";
            if (hint) {
              const fixCb = document.createElement("input"); fixCb.type = "checkbox"; fixCb.checked = !!st.action;
              fixCb.title = hint;
              fixCb.addEventListener("change", () => {
                st.action = fixCb.checked ? r.recommended_action : "";
                st.sel = fixCb.checked;
                redrawTable();
              });
              fixTd.appendChild(fixCb);
              const lbl = document.createElement("span");
              lbl.style.cssText = "font-size:10px; color:var(--text-faint); margin-left:2px;";
              lbl.textContent = hint;
              fixTd.appendChild(lbl);
            } else {
              fixTd.textContent = "-";
              fixTd.style.cssText = "padding:3px 4px; text-align:center; font-size:11px; color:var(--text-faint);";
            }
          }
        };

        renderRows(rows);
        updateSummary();

        // ── Separator + Global actions (inside callback, after details) ──
        containerEl.createEl("hr");
        containerEl.createEl("h3", { text: "\u5168\u5C40\u64CD\u4F5C" });

        const globalActions = containerEl.createEl("div");
        globalActions.style.cssText = "display:flex; gap:8px; flex-wrap:wrap;";

        const rebuildIndexBtn = globalActions.createEl("button", { text: "\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15" });
        rebuildIndexBtn.style.cssText = "padding:6px 14px; border-radius:4px; cursor:pointer;";
        rebuildIndexBtn.addEventListener("click", () => {
          new Notice("\u6B63\u5728\u91CD\u5EFA\u641C\u7D22\u7D22\u5F15\u2026");
          execFile(py.path, ["-m", "paperforge", "embed", "build", "--force"], { cwd: vaultPath, timeout: 300000, windowsHide: true },
            (_e: any, _o: string, _s: any) => { new Notice("\u641C\u7D22\u7D22\u5F15\u91CD\u5EFA\u5B8C\u6210\u3002"); });
        });

        const rebuildMemBtn = globalActions.createEl("button", { text: "\u91CD\u5EFA\u8BB0\u5FC6\u5E93" });
        rebuildMemBtn.style.cssText = "padding:6px 14px; border-radius:4px; cursor:pointer;";
        rebuildMemBtn.addEventListener("click", () => {
          new Notice("\u6B63\u5728\u91CD\u5EFA\u8BB0\u5FC6\u5E93\u2026");
          execFile(py.path, ["-m", "paperforge", "repair", "--fix"], { cwd: vaultPath, timeout: 120000, windowsHide: true },
            (_e: any, _o: string, _s: any) => { new Notice("\u8BB0\u5FC6\u5E93\u91CD\u5EFA\u5B8C\u6210\u3002"); });
        });
      });

  }

  _renderReleaseNotesTab(containerEl: HTMLElement) {
    containerEl.createEl("h2", { text: "\u66F4\u65B0\u4E0E\u624B\u518C" });

    containerEl.createEl("h3", { text: "\u7248\u672C\u66F4\u65B0\u8BB0\u5F55" });

    const versions = (releaseNotesData as any).versions || [];
    for (const ver of versions) {
      const card = containerEl.createEl("div", { cls: "paperforge-release-card" });

      const header = card.createEl("div", { cls: "paperforge-release-header" });
      header.createEl("strong", { text: `v${ver.version} \u2014 ${ver.title}` });
      header.createEl("span", { cls: "paperforge-release-date", text: `  (${ver.date})` });

      if (ver.breaking_or_migration && ver.breaking_or_migration.length > 0) {
        const section = card.createEl("div", { cls: "paperforge-release-section" });
        section.createEl("div", { cls: "paperforge-release-label", text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F" });
        for (const item of ver.breaking_or_migration) {
          section.createEl("div", { cls: "paperforge-release-item", text: `\u2022 ${item}` });
        }
      }

      if (ver.new_features && ver.new_features.length > 0) {
        const section = card.createEl("div", { cls: "paperforge-release-section" });
        section.createEl("div", { cls: "paperforge-release-label", text: "\u65B0\u529F\u80FD" });
        for (const item of ver.new_features) {
          section.createEl("div", { cls: "paperforge-release-item", text: `\u2022 ${item}` });
        }
      }

      if (ver.fixes && ver.fixes.length > 0) {
        const section = card.createEl("div", { cls: "paperforge-release-section" });
        section.createEl("div", { cls: "paperforge-release-label", text: "\u4FEE\u590D" });
        for (const item of ver.fixes) {
          section.createEl("div", { cls: "paperforge-release-item", text: `\u2022 ${item}` });
        }
      }

      if (ver.recommended_actions && ver.recommended_actions.length > 0) {
        const section = card.createEl("div", { cls: "paperforge-release-section paperforge-release-recommended" });
        section.createEl("div", { cls: "paperforge-release-label", text: "\u5EFA\u8BAE\u64CD\u4F5C" });
        for (const item of ver.recommended_actions) {
          section.createEl("div", { cls: "paperforge-release-item paperforge-release-item-bold", text: `\u2022 ${item}` });
        }
      }
    }

    containerEl.createEl("h3", { text: "\u4F7F\u7528\u624B\u518C" });
    const manualSection = containerEl.createEl("div", { cls: "paperforge-manual-links" });
    const manualLink = manualSection.createEl("a", {
      text: "\u2192 \u67E5\u770B\u5B8C\u6574\u4F7F\u7528\u624B\u518C\uFF08GitHub\uFF09",
      href: "https://github.com/LLLin000/PaperForge/blob/master/docs/user-manual.md",
    });
    manualLink.setAttr("target", "_blank");
  }
}
