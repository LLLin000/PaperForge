import { Plugin, addIcon, Notice, Modal, Setting, App } from "obsidian";

/** Thin confirm modal for the one-time plugin-assisted config migration. */
class ConfirmMigrationModal extends Modal {
  constructor(
    app: App,
    summary: string,
    private readonly onConfirm: () => Promise<void>
  ) {
    super(app);
    this.setTitle("Migrate PaperForge configuration");
    this.contentEl.createEl("p", {
      text: "Legacy configuration detected. Migration preview:",
    });
    const pre = this.contentEl.createEl("pre", { cls: "pf-migration-summary" });
    pre.setText(summary);
    this.contentEl.createEl("p", {
      text: "Canonical values win on conflict. Credentials are never migrated through config.",
      cls: "setting-item-description",
    });
    const actions = this.contentEl.createDiv({ cls: "pf-modal-actions" });
    const cancel = actions.createEl("button", { text: "Cancel" });
    cancel.addEventListener("click", () => this.close());
    const go = actions.createEl("button", { text: "Migrate" });
    go.addEventListener("click", () => {
      void this.onConfirm().finally(() => this.close());
    });
  }
}
import * as fs from "fs";
import * as path from "path";
import { execFile, exec, spawn } from "child_process";
import {
  VIEW_TYPE_PAPERFORGE,
  VIEW_TYPE_OCR_WORKSPACE,
  PF_ICON_ID,
  PF_RIBBON_SVG,
  ACTIONS,
  DEFAULT_SETTINGS,
  PaperForgeSettings,
  toolArgvFor,
} from "./constants";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettingTab } from "./settings";
import { orchestrateFromSync } from "./services/next-actions-bridge";
import { OcrProcessController } from "./services/ocr-process-controller";
import { PaperForgeStatusView } from "./views/dashboard";
import { OcrWorkspaceView } from "./views/ocr-workspace";
import {
  paperforgeEnrichedEnv,
  buildTargetedEnv,
} from "./services/python-bridge";
import { resolveVaultPaths } from "./services/runtime-paths";
import {
  setPathConfigSource,
  isConfigHydrated,
} from "./services/runtime-paths";
import {
  configList,
  configMigrate,
  configValidate,
  queryEmbedStatus,
} from "./services/config-client";
import {
  ManagedRuntime,
  resolveRuntimeCommand,
} from "./services/managed-runtime";

export default class PaperForgePlugin extends Plugin {
  /** agent_platform choices from Python's config list (#142) — empty until hydrated. */
  agentPlatformChoices: string[] = [];

  /** #161/R: embed status read model cache (embed status --json). */
  _embedStatusCache: Record<string, unknown> = {};

  settings!: PaperForgeSettings;
  private _autoSyncRunning = false;
  private _lastSyncTime: string | null = null;
  private _pollTimer: ReturnType<typeof setInterval> | null = null;
  private _embedProcess: unknown = null;
  private _embedProgress = { current: 0, total: 0, key: "" };
  private _embedStderr = "";
  _embedController:
    | import("./services/embed-build-controller").EmbedBuildController
    | null = null;
  /** #126 PR B: the single OCR process controller shared by Settings and Workspace. */
  ocrProcessController!: OcrProcessController;
  _memoryStatusText: string | null = null;
  private _managedRuntime: ManagedRuntime | null = null;

  getManagedRuntime(): ManagedRuntime {
    if (!this._managedRuntime) {
      this._managedRuntime = new ManagedRuntime({
        version: this.manifest.version,
      });
    }
    return this._managedRuntime;
  }

  _getPythonCommand(): { path: string; args: string[] } | null {
    const run = resolveRuntimeCommand(this.getManagedRuntime().current());
    return run ? { path: run.command, args: [...run.args] } : null;
  }
  async onload() {
    await this.loadSettings();
    await this.saveSettings();
    try {
      await this.getManagedRuntime().status();
    } catch {
      // Runtime UI exposes repair/install actions; plugin loading must continue.
    }
    setLanguage(this.app, this.settings.language);

    // #126 PR B: one OCR process controller for Settings and Workspace —
    // run/redo resolve the Paddle credential (fail closed when missing),
    // rebuild never requires it.
    this.ocrProcessController = new OcrProcessController({
      vaultPath: (this.app.vault.adapter as any).basePath as string,
      resolveCommand: () => this._getPythonCommand(),
      // #173/C1: the plugin never injects credentials — Python resolves them
      // from the credential authority; missing credentials fail closed there.
      resolveEnv: async () => {
        const env = await buildTargetedEnv(null, "ocr");
        return env;
      },
      needsCredential: (mode) => mode === "run" || mode === "redo",
    });

    this.registerView(
      VIEW_TYPE_PAPERFORGE,
      (leaf) => new PaperForgeStatusView(leaf)
    );

    this.registerView(
      VIEW_TYPE_OCR_WORKSPACE,
      (leaf) => new OcrWorkspaceView(leaf, this)
    );

    try {
      addIcon(PF_ICON_ID, PF_RIBBON_SVG);
    } catch (_) {}
    this.addRibbonIcon(PF_ICON_ID, "PaperForge Dashboard", () =>
      PaperForgeStatusView.open(this as any)
    );
    this.addRibbonIcon("scan-text", "PaperForge OCR Workspace", () =>
      OcrWorkspaceView.open(this as any)
    );

    // #99 (owner decision): redo is an internal maintenance command, NOT
    // exposed to users. No ribbon, no command — the CLI keeps it.
    this.addSettingTab(new PaperForgeSettingTab(this.app, this as any));

    this.addCommand({
      id: "paperforge-status-panel",
      name: t("guide_open"),
      callback: () => PaperForgeStatusView.open(this as any),
    });
    this.addCommand({
      id: "paperforge-ocr-workspace",
      name: "Open OCR Workspace",
      callback: () => OcrWorkspaceView.open(this as any),
    });

    for (const a of ACTIONS) {
      // #99 (owner decision): redo is internal-only — never a user command.
      if (a.id === "paperforge-ocr-redo") continue;
      this.addCommand({
        id: a.id,
        name: a.title,
        callback: async () => {
          if (a.disabled) {
            new Notice(
              `[i] ${a.disabledMsg || "This action is not yet available."}`,
              6000
            );
            return;
          }
          const vp = (this.app.vault.adapter as any).basePath as string;
          new Notice(`PaperForge: running ${a.commandId}...`);
          const pyCmd = this._getPythonCommand();
          if (!pyCmd) {
            new Notice("Runtime not ready");
            return;
          }
          const { path: cmdPythonExe, args: cmdExtra = [] } = pyCmd;
          const cmdArgs = Array.isArray(a.args) ? [...a.args] : [];
          // #173/C1: credentials are resolved by Python; the env is redacted.
          const env = await buildTargetedEnv(null, a.commandId);
          // T8 (#169): typed tool argv — never a generic dispatch table.
          const toolArgv = toolArgvFor(a.id) ?? [];
          execFile(
            cmdPythonExe,
            [...cmdExtra, "-m", "paperforge", ...toolArgv, ...cmdArgs],
            { cwd: vp, timeout: 300000, env },
            (err, stdout, stderr) => {
              if (err) {
                new Notice(
                  `[!!] ${a.commandId} failed: ${(stderr || err.message).slice(0, 120)}`,
                  8000
                );
                return;
              }
              new Notice(
                `[OK] ${a.okMsg || stdout.trim().split("\n")[0].slice(0, 80)}`
              );
            }
          );
        },
      });
    }

    this.addCommand({
      id: "paperforge-migrate-config",
      name: "Migrate PaperForge legacy configuration",
      callback: () => this._runLegacyConfigMigration(),
    });

    this._startConvergenceTimer();
    this._checkReleaseNotes();

    // #142/C0: one-time plugin-assisted config migration — detect legacy
    // vaults and surface an explicit migrate command.
    const vaultBase = (
      this.app.vault.adapter as unknown as { basePath?: string }
    ).basePath;
    if (vaultBase) {
      void configValidate(vaultBase, this.settings)
        .then((validation) => {
          if (validation.state === "migration_required") {
            this._needsConfigMigration = true;
          }
        })
        .catch(() => undefined);
      // #161/R: embed status read model for the vector UI.
      void queryEmbedStatus(vaultBase, this.settings)
        .then((d) => {
          if (d) {
            this._embedStatusCache = d as unknown as Record<string, unknown>;
          }
        })
        .catch(() => undefined);
    }
  }

  private _needsConfigMigration = false;

  /** Thin plugin-assisted migration (#142 §12): dry-run -> confirm -> migrate
   * -> re-hydrate -> purge legacy domain values from data.json. */
  private _runLegacyConfigMigration(): void {
    const vaultPath = (
      this.app.vault.adapter as unknown as { basePath?: string }
    ).basePath;
    if (!vaultPath) return;
    void (async () => {
      const dry = await configMigrate(vaultPath, true, this.settings).catch(
        (e) => null
      );
      const summary =
        dry && dry.warnings?.length
          ? dry.warnings.join("\n")
          : "No conflicts; legacy path keys will move under vault_config.";
      new ConfirmMigrationModal(this.app, summary, async () => {
        await configMigrate(vaultPath, false, this.settings).catch((e) => {
          new Notice(`PaperForge: config migrate failed: ${String(e)}`);
          return;
        });
        // Re-hydrate mirrors from the canonical config, then purge the
        // legacy domain values from data.json (#142 §12 step 4/5).
        try {
          const list = await configList(vaultPath, this.settings);
          const pick = (key: string) =>
            list.fields.find((f) => f.key === key)?.value;
          const systemDir = String(pick("system_dir") ?? "");
          const resourcesDir = String(pick("resources_dir") ?? "");
          const literatureDir = String(pick("literature_dir") ?? "");
          const baseDir = String(pick("base_dir") ?? "");
          const zoteroDir = String(pick("zotero_data_dir") ?? "");
          const apiBase = String(pick("vector_db_api_base") ?? "");
          const apiModel = String(pick("vector_db_api_model") ?? "");
          const agentPlatform = String(pick("agent_platform") ?? "");
          if (systemDir) this.settings.system_dir = systemDir;
          if (resourcesDir) this.settings.resources_dir = resourcesDir;
          if (literatureDir) this.settings.literature_dir = literatureDir;
          if (baseDir) this.settings.base_dir = baseDir;
          if (zoteroDir) this.settings.zotero_data_dir = zoteroDir;
          if (apiBase) this.settings.vector_db_api_base = apiBase;
          if (apiModel) this.settings.vector_db_api_model = apiModel;
          if (agentPlatform) this.settings.agent_platform = agentPlatform;
          setPathConfigSource({
            system_dir: systemDir || "System",
            resources_dir: resourcesDir || "Resources",
            literature_dir: literatureDir || "Literature",
            base_dir: baseDir || "Bases",
            _warning: null,
          });
        } catch {
          /* mirrors keep prior values; canonical file is authoritative */
        }
        this._needsConfigMigration = false;
        await this.saveSettings();
        new Notice("PaperForge: configuration migrated");
      }).open();
    })();
  }

  private _startConvergenceTimer() {
    // T8 (#169) convergence tick (#158): fires `paperforge sync` only, on a
    // cadence from data.json (autoSyncIntervalSeconds, default 120).  The
    // mtime scanner and canonical path/state scanning are DELETED — the
    // Python side derives state from reconcile(all).
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const cadenceMs =
      Math.max(30, this.settings.autoSyncIntervalSeconds ?? 120) * 1000;

    if (this.settings.autoSyncEnabled === false) {
      return;
    }
    // Vault-open tick + cadence interval.
    this._autoSync(vaultPath);
    this._pollTimer = setInterval(() => {
      if (!isConfigHydrated()) return;
      this._autoSync(vaultPath);
    }, cadenceMs);
  }

  // T8: mtime scanner deleted — the convergence tick fires sync directly.

  private _autoSync(vaultPath: string) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = true;

    const pyCmd = this._getPythonCommand();
    if (!pyCmd) {
      this._autoSyncRunning = false;
      return;
    }

    // #173/C1: the desktop child env is the redacted
    // paperforgeEnrichedEnv() — never the bare process env.
    const env = paperforgeEnrichedEnv();
    execFile(
      pyCmd.path,
      [
        ...pyCmd.args,
        "-m",
        "paperforge",
        "--vault",
        vaultPath,
        "sync",
        "--json",
      ],
      {
        timeout: 120000,
        encoding: "utf-8",
        cwd: vaultPath,
        windowsHide: true,
        env,
      },
      (err, stdout, _stderr) => {
        this._autoSyncRunning = false;
        this._memoryStatusText = null;
        if (!err) {
          this._lastSyncTime = new Date().toLocaleTimeString();
          // #127/#169: consume next_actions — the Python registry is the
          // policy authority; the plugin executes via the action client.
          void orchestrateFromSync(stdout, {
            app: this.app,
            vaultPath,
            resolveCommand: (v) => this._getPythonCommand(),
          });
        }
      }
    );
  }

  // T8: OCR mtime scanning deleted — the convergence tick fires sync only.

  readPaperforgeJson(): Record<string, string> {
    // #142 / C0: removed — the plugin never parses paperforge.json. Values
    // come from `paperforge config list` (hydrated into settings mirrors).
    return {};
  }

  savePaperforgeJson(_pathConfig: Record<string, string | undefined>): void {
    // #142 / C0: removed — the plugin never writes paperforge.json. Mutations
    // route through `paperforge config set/unset` (config-client).
    console.warn(
      "PaperForge: savePaperforgeJson is retired; use paperforge config set"
    );
  }

  onunload() {
    if (this._pollTimer) clearInterval(this._pollTimer);
    // #120: kill any in-flight embed build and stop its status poll — a
    // reload/unload must not orphan the child (UI would lose control).
    this._embedController?.dispose();
    this._embedController = null;
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
  }

  async loadSettings() {
    const saved = ((await this.loadData()) ?? {}) as Record<string, unknown>;
    this.settings = Object.assign({}, DEFAULT_SETTINGS, saved);
    if (this.settings.features && DEFAULT_SETTINGS.features) {
      this.settings.features = Object.assign(
        {},
        DEFAULT_SETTINGS.features,
        this.settings.features || {}
      );
    }
    if (!this.settings.frozen_skills) {
      this.settings.frozen_skills = {};
    }

    // Existing installations predate the Setup Journey. The previous rollout
    // wrote the new default false into their data, so migrate only profiles
    // that already carried durable pre-redesign state and never started the journey.
    const establishedInstall =
      !!saved.capabilityState ||
      !!saved.last_seen_version ||
      !!saved.vault_path;
    if (
      saved._setup_complete === false &&
      establishedInstall &&
      saved._setup_journey_started !== true
    ) {
      this.settings._setup_complete = true;
    }

    // #142 / C0: display mirrors are hydrated from the Python config
    // authority; the plugin never parses paperforge.json.
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    if (vaultPath) {
      try {
        const list = await configList(vaultPath, this.settings);
        const pick = (key: string) =>
          list.fields.find((f) => f.key === key)?.value;
        const systemDir = String(pick("system_dir") ?? "");
        const resourcesDir = String(pick("resources_dir") ?? "");
        const literatureDir = String(pick("literature_dir") ?? "");
        const baseDir = String(pick("base_dir") ?? "");
        const zoteroDir = String(pick("zotero_data_dir") ?? "");
        if (systemDir) this.settings.system_dir = systemDir;
        if (resourcesDir) this.settings.resources_dir = resourcesDir;
        if (literatureDir) this.settings.literature_dir = literatureDir;
        if (baseDir) this.settings.base_dir = baseDir;
        if (zoteroDir) this.settings.zotero_data_dir = zoteroDir;
        // Provider fields are canonical config: mirrors hydrated for display,
        // mutations route through config set (#142).
        const apiBase = String(pick("vector_db_api_base") ?? "");
        const apiModel = String(pick("vector_db_api_model") ?? "");
        const agentPlatform = String(pick("agent_platform") ?? "");
        if (apiBase) this.settings.vector_db_api_base = apiBase;
        if (apiModel) this.settings.vector_db_api_model = apiModel;
        if (agentPlatform) this.settings.agent_platform = agentPlatform;
        // agent_platform choices come from Python's config list (#142).
        const platformField = list.fields.find(
          (f) => f.key === "agent_platform"
        );
        this.agentPlatformChoices = platformField?.choices ?? [];
        setPathConfigSource({
          system_dir: systemDir || "System",
          resources_dir: resourcesDir || "Resources",
          literature_dir: literatureDir || "Literature",
          base_dir: baseDir || "Bases",
          _warning: null,
        });
      } catch {
        // Display mirrors keep defaults until Python is reachable; actions
        // stay disabled until a fresh probe/config response (#144).
      }
    }

    if (this.settings.python_path && this.settings.python_path.trim()) {
      const pp = this.settings.python_path.trim();
      this.settings._python_path_stale = !fs.existsSync(pp);
    }
  }

  async saveSettings() {
    const dataToSave: Record<string, unknown> = {};
    for (const key of Object.keys(DEFAULT_SETTINGS)) {
      if (key in this.settings) {
        dataToSave[key] = this.settings[key];
      }
    }
    await this.saveData(dataToSave);
  }

  private _checkReleaseNotes() {
    const currentVersion = this.manifest.version;
    const seen = this.settings.last_seen_version;
    if (seen === currentVersion) return;

    const releaseNotesData = require("./release-notes.json");
    const versions = releaseNotesData.versions || [];
    const currentEntry = versions.find(
      (v: any) => v.version === currentVersion
    );

    class ReleaseNotesModal extends Modal {
      private _entry: any;
      constructor(app: any, entry: any) {
        super(app);
        this._entry = entry;
      }
      onOpen() {
        const { contentEl } = this;
        contentEl.createEl("h2", {
          text: `PaperForge v${currentVersion} \u66F4\u65B0\u8BF4\u660E`,
        });
        if (this._entry) {
          contentEl.createEl("p", {
            text: this._entry.title,
            cls: "paperforge-modal-subtitle",
          });
          if (
            this._entry.breaking_or_migration &&
            this._entry.breaking_or_migration.length > 0
          ) {
            contentEl.createEl("h4", {
              text: "\u884C\u4E3A\u53D8\u66F4 / \u8FC1\u79FB\u6CE8\u610F",
            });
            for (const item of this._entry.breaking_or_migration) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (this._entry.new_features && this._entry.new_features.length > 0) {
            contentEl.createEl("h4", { text: "\u65B0\u529F\u80FD" });
            for (const item of this._entry.new_features) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (this._entry.fixes && this._entry.fixes.length > 0) {
            contentEl.createEl("h4", { text: "\u4FEE\u590D" });
            for (const item of this._entry.fixes) {
              contentEl.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-modal-item",
              });
            }
          }
          if (
            this._entry.recommended_actions &&
            this._entry.recommended_actions.length > 0
          ) {
            const section = contentEl.createEl("div", {
              cls: "paperforge-release-recommended",
            });
            section.createEl("h4", {
              text: "\u5EFA\u8BAE\u64CD\u4F5C",
              cls: "",
            });
            section.style.marginBottom = "8px";
            for (const item of this._entry.recommended_actions) {
              section.createEl("p", {
                text: `\u2022 ${item}`,
                cls: "paperforge-release-item-bold",
              });
            }
          }
        } else {
          contentEl.createEl("p", {
            text:
              "\u7248\u672C\u5DF2\u66F4\u65B0\u81F3 v" +
              currentVersion +
              "\uFF0C\u8BF7\u524D\u5F80\u8BBE\u7F6E \u2192 \u66F4\u65B0\u4E0E\u624B\u518C \u67E5\u770B\u5B8C\u6574\u66F4\u65B0\u8BB0\u5F55\u3002",
          });
        }
        new Setting(contentEl).addButton((btn) =>
          btn
            .setButtonText("\u77E5\u9053\u4E86")
            .setCta()
            .onClick(() => {
              this.close();
            })
        );
      }
      onClose() {
        const { contentEl } = this;
        contentEl.empty();
      }
    }

    new ReleaseNotesModal(this.app, currentEntry).open();
    this.settings.last_seen_version = currentVersion;
    this.saveSettings();
  }
}
