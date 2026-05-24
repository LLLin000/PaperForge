import { PluginSettingTab, App, Setting, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFile, execFileSync, spawn, exec } from "child_process";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettings } from "./constants";
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
            `;
      document.head.appendChild(style);
    }

    // --- Tab bar ---
    const tabBar = containerEl.createDiv({ cls: "paperforge-settings-tabs" });
    const tabs = [
      { id: "setup", label: t("tab_setup") || "Installation" },
      { id: "features", label: t("tab_features") || "Features" },
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
    } else {
      this._renderFeaturesTab(tabContents.features);
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
    };
    const agentDirs: Record<string, string> = {
      opencode: ".opencode/skills",
      claude: ".claude/skills",
      codex: ".codex/skills",
      cursor: ".cursor/skills",
      windsurf: ".windsurf/skills",
      github_copilot: ".github/skills",
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
}
