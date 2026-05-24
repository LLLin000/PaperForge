import { Plugin, addIcon, Notice } from "obsidian";
import * as fs from "fs";
import * as path from "path";
import { execFile, exec, spawn } from "child_process";
import { VIEW_TYPE_PAPERFORGE, PF_ICON_ID, PF_RIBBON_SVG, ACTIONS, DEFAULT_SETTINGS, PaperForgeSettings } from "./constants";
import { t, setLanguage } from "./i18n";
import { PaperForgeSettingTab } from "./settings";
import { PaperForgeStatusView } from "./views/dashboard";
import { resolvePythonExecutable, paperforgeEnrichedEnv } from "./services/python-bridge";
import { resolveVaultPaths } from "./services/memory-state";

export default class PaperForgePlugin extends Plugin {
  settings!: PaperForgeSettings;
  private _lastExportMtime = 0;
  private _lastOcrMtimes: Record<string, number> = {};
  private _autoSyncRunning = false;
  private _lastSyncTime: string | null = null;
  private _pollTimer: ReturnType<typeof setInterval> | null = null;
  private _embedProcess: unknown = null;
  private _embedProgress = { current: 0, total: 0, key: "" };
  private _embedStderr = "";
  _memoryStatusText: string | null = null;

  async onload() {
    await this.loadSettings();
    this.saveSettings();
    setLanguage(this.app);
    this.registerView(VIEW_TYPE_PAPERFORGE, (leaf) => new PaperForgeStatusView(leaf));

    try { addIcon(PF_ICON_ID, PF_RIBBON_SVG); } catch (_) {}
    this.addRibbonIcon(PF_ICON_ID, "PaperForge Dashboard", () => PaperForgeStatusView.open(this as any));

    this.addSettingTab(new PaperForgeSettingTab(this.app, this as any));

    this.addCommand({
      id: "paperforge-status-panel",
      name: `PaperForge: ${t("guide_open")}`,
      callback: () => PaperForgeStatusView.open(this as any),
    });

    for (const a of ACTIONS) {
      this.addCommand({
        id: a.id,
        name: `PaperForge: ${a.title}`,
        callback: () => {
          if (a.disabled) {
            new Notice(`[i] ${a.disabledMsg || 'This action is not yet available.'}`, 6000);
            return;
          }
          const vp = (this.app.vault.adapter as any).basePath as string;
          new Notice(`PaperForge: running ${a.cmd}...`);
          const { path: cmdPythonExe, extraArgs: cmdExtra = [] } = resolvePythonExecutable(vp, this.settings, undefined, undefined);
          execFile(cmdPythonExe, [...cmdExtra, "-m", "paperforge", a.cmd], { cwd: vp, timeout: 300000 }, (err, stdout, stderr) => {
            if (err) {
              new Notice(`[!!] ${a.cmd} failed: ${(stderr || err.message).slice(0, 120)}`, 8000);
              return;
            }
            new Notice(`[OK] ${a.okMsg || stdout.trim().split("\n")[0].slice(0, 80)}`);
          });
        },
      });
    }

    if (this.settings.auto_update_on_startup === true && this.settings.setup_complete) {
      setTimeout(() => this._autoUpdate(), 3000);
    }
    this._startFilePolling();
    this._firstLaunchSnapshotMigration();
  }

  private _firstLaunchSnapshotMigration() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    if (!vp) return;
    const runtimePaths = resolveVaultPaths(vp);
    const memSnap = runtimePaths.memoryStatePath;
    if (!fs.existsSync(memSnap)) {
      const py = resolvePythonExecutable(vp, this.settings, undefined, undefined);
      const commands: string[][] = [
        ['runtime-health', '--json'],
        ['memory', 'status', '--json'],
        ['embed', 'status', '--json'],
      ];
      commands.forEach((cmdArgs) => {
        const args = [...py.extraArgs, '-m', 'paperforge', '--vault', vp, ...cmdArgs];
        execFile(py.path, args, { cwd: vp, timeout: 60000, windowsHide: true }, () => {});
      });
    }
  }

  private _autoUpdate() {
    const vp = (this.app.vault.adapter as any).basePath as string;
    const { path: pythonExe, extraArgs = [] } = resolvePythonExecutable(vp, this.settings, undefined, undefined);
    const ver = this.manifest.version;
    const pypiPkg = `paperforge==${ver}`;
    const gitUrl = `git+https://github.com/LLLin000/PaperForge.git@v${ver}`;

    const doInstall = (pkg: string, onDone: (ok: boolean) => void) => {
      const child = spawn(pythonExe, [...extraArgs, '-m', 'pip', 'install', '--upgrade', pkg], { cwd: vp, timeout: 120000, env: paperforgeEnrichedEnv() });
      child.on('close', (code) => onDone(code === 0));
    };

    execFile(pythonExe, [...extraArgs, '-c', 'import paperforge; print(paperforge.__version__)'], { cwd: vp, timeout: 10000 }, (err, stdout) => {
      const install = (label: string) => {
        console.log(`[PaperForge] Auto-update: trying PyPI (paperforge==${ver})`);
        doInstall(pypiPkg, (ok) => {
          if (ok) { console.log('[PaperForge] Auto-update: installed via PyPI'); new Notice(`[OK] PaperForge CLI ${label}`, 5000); return; }
          console.warn('[PaperForge] Auto-update: PyPI failed, falling back to git...');
          doInstall(gitUrl, (ok2) => {
            if (ok2) { console.log('[PaperForge] Auto-update: installed via git'); new Notice(`[OK] PaperForge CLI ${label} (via git)`, 5000); }
          });
        });
      };
      if (err) {
        install('installed');
        return;
      }
      const pyVer = stdout.trim();
      if (pyVer !== ver) {
        install(`${pyVer} -> ${ver}`);
      }
    });
  }

  private _startFilePolling() {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;

    this._pollTimer = setInterval(() => {
      this._checkExports(vaultPath);
      this._checkOcr(vaultPath);
    }, 120000);
  }

  private _checkExports(vaultPath: string) {
    if (this._autoSyncRunning) return;
    const exportsDir = resolveVaultPaths(vaultPath).exportsDir;
    if (!fs.existsSync(exportsDir)) return;

    let newestMtime = 0;
    try {
      fs.readdirSync(exportsDir).forEach(f => {
        if (!f.endsWith('.json')) return;
        const stat = fs.statSync(path.join(exportsDir, f));
        if (stat.mtimeMs > newestMtime) newestMtime = stat.mtimeMs;
      });
    } catch(e) { return; }

    if (newestMtime > this._lastExportMtime) {
      this._lastExportMtime = newestMtime;
      this._autoSync(vaultPath);
    }
  }

  private _autoSync(vaultPath: string) {
    if (this._autoSyncRunning) return;
    this._autoSyncRunning = true;

    const pyResult = resolvePythonExecutable(vaultPath, this.settings, undefined, undefined);
    if (!pyResult.path) { this._autoSyncRunning = false; return; }

    const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync`;
    exec(cmd, { timeout: 120000, encoding: 'utf-8' }, (err, _stdout, _stderr) => {
      this._autoSyncRunning = false;
      this._memoryStatusText = null;
      if (!err) {
        this._lastSyncTime = new Date().toLocaleTimeString();
      }
      try {
        const exportsDir = resolveVaultPaths(vaultPath).exportsDir;
        let newest = 0;
        fs.readdirSync(exportsDir).forEach(f => {
          if (!f.endsWith('.json')) return;
          newest = Math.max(newest, fs.statSync(path.join(exportsDir, f)).mtimeMs);
        });
        this._lastExportMtime = newest;
      } catch(_e) {}
    });
  }

  private _checkOcr(vaultPath: string) {
    if (this._autoSyncRunning) return;
    const ocrDir = resolveVaultPaths(vaultPath).ocrDir;
    if (!fs.existsSync(ocrDir)) return;

    try {
      fs.readdirSync(ocrDir, { withFileTypes: true }).forEach(entry => {
        if (!entry.isDirectory()) return;
        const metaPath = path.join(ocrDir, entry.name, 'meta.json');
        if (!fs.existsSync(metaPath)) return;
        const stat = fs.statSync(metaPath);
        const prevMtime = this._lastOcrMtimes[entry.name] || 0;
        if (stat.mtimeMs <= prevMtime) return;

        this._lastOcrMtimes[entry.name] = stat.mtimeMs;
        if (this._autoSyncRunning) return;
        this._autoSyncRunning = true;

        const pyResult = resolvePythonExecutable(vaultPath, this.settings, undefined, undefined);
        if (!pyResult.path) { this._autoSyncRunning = false; return; }

        const cmd = `"${pyResult.path}" -m paperforge --vault "${vaultPath}" sync`;
        exec(cmd, { timeout: 30000, encoding: 'utf-8' }, () => {
          this._autoSyncRunning = false;
          this._memoryStatusText = null;
        });
      });
    } catch(_e) {}
  }

  readPaperforgeJson(): Record<string, string> {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const pfPath = path.join(vaultPath, 'paperforge.json');

    const DEFAULTS: Record<string, string> = {
      system_dir: 'System',
      resources_dir: 'Resources',
      literature_dir: 'Literature',
      base_dir: 'Bases',
    };

    try {
      if (!fs.existsSync(pfPath)) {
        return DEFAULTS;
      }
      const raw = fs.readFileSync(pfPath, 'utf-8');
      const data = JSON.parse(raw);

      const vc = data.vault_config || {};
      return {
        system_dir: vc.system_dir || data.system_dir || DEFAULTS.system_dir,
        resources_dir: vc.resources_dir || data.resources_dir || DEFAULTS.resources_dir,
        literature_dir: vc.literature_dir || data.literature_dir || DEFAULTS.literature_dir,
        base_dir: vc.base_dir || data.base_dir || DEFAULTS.base_dir,
      };
    } catch (e) {
      console.warn('PaperForge: Failed to read paperforge.json, using defaults', e);
      return DEFAULTS;
    }
  }

  savePaperforgeJson(pathConfig: Record<string, string | undefined>): void {
    const vaultPath = (this.app.vault.adapter as any).basePath as string;
    const pfPath = path.join(vaultPath, 'paperforge.json');

    let data: Record<string, any> = {};
    try {
      if (fs.existsSync(pfPath)) {
        data = JSON.parse(fs.readFileSync(pfPath, 'utf-8'));
      }
    } catch (e) {
      console.warn('PaperForge: Failed to read paperforge.json for update', e);
    }

    if (!data.vault_config || typeof data.vault_config !== 'object') {
      data.vault_config = {};
    }

    const validPathKeys = ['system_dir', 'resources_dir', 'literature_dir', 'base_dir'];
    for (const key of validPathKeys) {
      if (pathConfig[key] !== undefined) {
        data.vault_config[key] = pathConfig[key];
      }
    }

    if (!data.schema_version) {
      data.schema_version = '2';
    }

    for (const key of validPathKeys) {
      delete data[key];
    }

    try {
      fs.writeFileSync(pfPath, JSON.stringify(data, null, 2), 'utf-8');
      if (this.settings) {
        const pfConfig = this.readPaperforgeJson();
        this.settings.system_dir = pfConfig.system_dir;
        this.settings.resources_dir = pfConfig.resources_dir;
        this.settings.literature_dir = pfConfig.literature_dir;
        this.settings.base_dir = pfConfig.base_dir;
      }
    } catch (e) {
      console.error('PaperForge: Failed to write paperforge.json', e);
      new Notice('PaperForge: Failed to save configuration to paperforge.json');
    }
  }

  onunload() {
    if (this._pollTimer) clearInterval(this._pollTimer);
    this.app.workspace.detachLeavesOfType(VIEW_TYPE_PAPERFORGE);
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    if (this.settings.features && DEFAULT_SETTINGS.features) {
      this.settings.features = Object.assign({}, DEFAULT_SETTINGS.features, this.settings.features || {});
    }
    if (!this.settings.frozen_skills) { this.settings.frozen_skills = {}; }
    const pfConfig = this.readPaperforgeJson();
    this.settings.system_dir = pfConfig.system_dir;
    this.settings.resources_dir = pfConfig.resources_dir;
    this.settings.literature_dir = pfConfig.literature_dir;
    this.settings.base_dir = pfConfig.base_dir;

    if (this.settings.python_path && this.settings.python_path.trim()) {
      const pp = this.settings.python_path.trim();
      if (!fs.existsSync(pp)) {
        console.warn(`PaperForge: Saved python_path "${pp}" no longer exists - showing stale warning`);
        this.settings._python_path_stale = true;
      } else {
        this.settings._python_path_stale = false;
      }
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
}
