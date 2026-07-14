# Obsidian Native Control Patterns — PaperForge Fit Analysis

- **Date:** 2026-07-14
- **Wayfinder ticket:** [Issue #67](https://github.com/LLLin000/PaperForge/issues/67)

---

## Research Method

Six plugins plus official API docs were studied from source code and official documentation:

| # | Plugin | Version Studied | Repository | Key Areas |
|---|--------|----------------|------------|-----------|
| 1 | **Dataview** | 0.5.70 | [blacksmithgu/obsidian-dataview](https://github.com/blacksmithgu/obsidian-dataview) | Settings tab, imperative `display()`, feature toggles, refresh debouncing |
| 2 | **Templater** | 2.18.1 | [SilentVoid13/Templater](https://github.com/SilentVoid13/Templater) | Per-vault dangerous settings, `ConfirmDangerousSettingModal`, modal-based config, decl settings adoption |
| 3 | **Obsidian Git** | 2.38.6 | [Vinzent03/obsidian-git](https://github.com/Vinzent03/obsidian-git) | External runtime detection (`git` binary), `checkRequirements()` pattern, status bar, `displayError()` |
| 4 | **Tasks** | 8.0.0 | [obsidian-tasks-group/obsidian-tasks](https://github.com/obsidian-tasks-group/obsidian-tasks) | Dynamic settings from `generalSettings`, debug/log options, heading state tracking, i18n |
| 5 | **Obsidian Sample Plugin** | — | [obsidianmd/obsidian-sample-plugin](https://github.com/obsidianmd/obsidian-sample-plugin) | Canonical `PluginSettingTab` implementation |
| 6 | **Obsidian Core API** | 1.13.0+ | [docs.obsidian.md](https://docs.obsidian.md/) | Declarative Settings API, SecretStorage, Platform, Notices, Modals, Commands |

**PaperForge manifest context:** `isDesktopOnly: true`, `minAppVersion: 1.9.0` — confirmed from `manifest.json` in the repo.

---

## Pattern Catalogue

### 1. Settings Tab Architecture

#### Obsidian Convention

**Imperative (v0.9.7+):** Extend `PluginSettingTab`, implement `display()`, build DOM with `new Setting(containerEl)`.

```ts
import { PluginSettingTab, Setting } from 'obsidian';

class MySettingTab extends PluginSettingTab {
  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl)
      .setName('Toggle')
      .addToggle(t => t.setValue(val).onChange(async v => { /* save */ }));
  }
}
```

Source: [Settings.md — obsidian-developer-docs](https://github.com/obsidianmd/obsidian-developer-docs/blob/31946e5a/en/Plugins/User%20interface/Settings.md)

**Declarative (1.13.0+):** Override `getSettingDefinitions()`, return typed definition objects. Obsidian handles rendering, search indexing, persistence, and validation.

```ts
class MySettingTab extends PluginSettingTab {
  getSettingDefinitions() {
    return [{
      name: 'Enable feature',
      control: { type: 'toggle', key: 'enabled' },
    }];
  }
}
```

Source: [Migrate to declarative settings — obsidian-developer-docs](https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/Guides/Migrate%20to%20declarative%20settings.md)

#### Evidence from Plugins

| Plugin | Approach | minAppVersion | Notes |
|--------|----------|--------------|-------|
| Dataview | Imperative `display()` | 0.12+ | Manual tab state, `Setting` per row |
| Obsidian Git | Imperative `display()` | 0.12+ | Manual tab, `icon` on settings tab |
| Templater | Declarative (recent) + imperative fallback | 1.13.0 (recent) | Dual support via Path B in older versions |
| Tasks | Imperative `display()` | 0.12+ | Uses `customFunctions` map for extensibility |

**Strength of imperative:** Full control over layout, conditional rendering, async loading, custom component composition.
**Limitation of imperative:** No built-in search indexing, manual persistence wiring, no keyboard nav.

**Strength of declarative:** Free search, auto-save, validation, sub-pages, groups with visibility predicates, lists, buttons.
**Limitation of declarative:** Requires 1.13.0+, limited to supported control types, `render` callbacks lose auto-save.

#### PaperForge Fit

PaperForge's current `display()` is 2394 lines of imperative code with custom tab bar. This is **unsustainable** — it duplicates the tab infrastructure Obsidian provides natively. Recommend **Path B (dual support)**: adopt declarative `getSettingDefinitions()` for simple controls (toggles, dropdowns, text inputs, secret components) while keeping imperative `render` callbacks for the custom sections (skills list, status health, embed build controls).

---

### 2. Tab and Section Navigation

#### Obsidian Convention

Use `.setHeading()` on `Setting` objects to demarcate sections. Official guidance: "General settings should be at the top… should not have a heading."

```ts
new Setting(containerEl).setName("Appearance").setHeading();
```

Source: [Settings.md](https://github.com/obsidianmd/obsidian-developer-docs/blob/31946e5a/en/Plugins/User%20interface/Settings.md)

For multi-tab layouts, plugins implement **custom CSS-tab toggling** (like PaperForge already does). The declarative API supports **sub-pages** natively via the `page` property in definitions.

**Obsidian Git** uses a single tab with icons in the settings sidebar (`icon: "git-pull-request"` on the tab class).

**Tasks** uses heading tracking (`headingOpened: HeadingState`) to remember which sections the user has collapsed, persisted in `data.json`.

#### PaperForge Fit

PaperForge's custom tab bar (`.paperforge-settings-tabs`) is well-implemented. Replace the inline `<style>` injection with entries in `styles.css`. The tab labels should map to PaperForge's six target modules: 安装 / 文献库 / OCR / 记忆 / 维护 / 帮助. There is no canonical six-tab layout among studied plugins, but PaperForge's current 4-tab separation (setup / features / maintenance / release-notes) can be expanded to six by splitting the current 功能 tab into per-module tabs.

---

### 3. Onboarding / First-Launch Setup

#### Obsidian Convention

Most plugins **do not have a setup wizard**. They present all settings in the tab and let users configure at will. Exceptions exist for plugins requiring external dependencies:

**Obsidian Git** uses `init()` → `checkRequirements()` which returns `"missing-git" | "missing-repo" | "valid"`. On `"missing-git"`, it calls `displayError()` with a descriptive Notice. On `"missing-repo"`, it shows a Notice with instructions and offers **commands** (`Create new repo`, `Clone existing repo`) that users can run from the command palette.

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) lines 600-650

```ts
const result = await this.gitManager.checkRequirements();
switch (result) {
    case "missing-git":
        this.displayError(`Cannot run git command. Trying to run: '${gitPath}' .`);
        break;
    case "missing-repo":
        new Notice("Can't find a valid git repository. Please create one via the given command or clone an existing repo.", 10000);
        break;
    case "valid":
        this.gitReady = true;
        // ...
}
```

**Templater** uses per-vault dangerous settings with a **confirmation modal** (`ConfirmDangerousSettingModal`) before enabling risky operations like system command execution. On mobile (where `Platform.isDesktop` is false), the checkbox is replaced with updated button text.

Source: [Templater commit 70a24ce](https://github.com/SilentVoid13/Templater/commit/70a24cefece47be55018b989b255b224a9b3b718)

#### PaperForge Fit

PaperForge's dedicated 安装 tab and `PaperForgeSetupModal` fit Obsidian's modal pattern, but initialization is overly coupled to settings rendering. **Adapt the Obsidian Git pattern**: separate startup capability checks from the wizard UI. The control center should expose setup as the primary action for modules that need input; an onboarding-dismissed marker may control first-run presentation, but `setup_complete` must not represent runtime readiness.

---

### 4. Dependency Detection & External Runtime Boundaries

#### Obsidian Convention

**Obsidian Git** is the canonical reference. It:

1. Defines `checkRequirements(): Promise<'missing-git' | 'missing-repo' | 'valid'>`
2. In `init()`, creates the appropriate `GitManager` implementation (`SimpleGit` on desktop, `IsomorphicGit` on mobile)
3. Uses `Platform.isDesktopApp` to select implementation:
   ```ts
   get useSimpleGit(): boolean { return Platform.isDesktopApp; }
   ```
4. Stores the Git binary path in `localStorage` (via `LocalStorageSettings`), not `data.json`, so it persists across plugin updates
5. Reports clear errors via `displayError()` — which calls `new Notice()` with the error message

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) lines 600-650, `init()` method

**Templater** on mobile uses a reduced UI (`ConfirmDangerousSettingModal` without checkbox), acknowledging that mobile has different interaction constraints.

#### PaperForge Fit

PaperForge's `resolvePythonExecutable()` already implements a similar strategy — searching for Python in standard locations, checking custom paths, marking stale paths. However, the **error reporting** is mixed: some errors go to `Notice`, others to `console.log`, and the settings tab redraws on every failure. **Adopt the Git pattern exactly**: a dedicated `checkRequirements()` Promise that returns a typed result union, called from `onload()` and re-checkable via command. All external runtime errors should route through a single `displayError()` method that shows a Notice with duration === 8000ms for errors.

PaperForge's `manifest.json` already has `isDesktopOnly: true`, which means Obsidian blocks loading the plugin on mobile entirely. No Platform guards are needed for the current deployment surface. The `Platform` patterns documented here are a prerequisite reference **if mobile support is ever added**.

---

### 5. Error Display Patterns (Notices, Modals, Status Bar)

#### Obsidian Convention

**Notice:** Transient message at bottom of viewport. Duration in ms (default 4000). Use for:
- Operation completion (`sync done`, `OCR started`)
- Transient errors (`command failed: ...`)
- Informational messages (`No results found`)

```ts
new Notice("Message", 5000);  // 5 second duration
```

Source: [Notices — docs.obsidian.md](https://docs.obsidian.md/Plugins/User+interface/Notices)

**Modal:** Persistent dialog for decisions or multi-step flows. Extend `Modal`, implement `onOpen()` / `onClose()`. Use for:
- Privacy/consent dialogs
- Multi-field setup steps
- Confirmation before destructive operations

Source: [Modals — docs.obsidian.md](https://docs.obsidian.md/Plugins/User+interface/Modals)

**Status Bar:** `addStatusBarItem()` returns an `HTMLElement`. Use for persistent status (e.g., git branch, sync time).

**Obsidian Git** demonstrates all three:
- `displayError()` → `new Notice()` with error text
- `GeneralModal` for user input (clone URL, directory selection)
- `BranchModal` for branch switching
- `StatusBar` and `BranchStatusBar` for persistent git state
- `setPluginState()` drives status bar content

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts)

**Tasks** uses `createFragmentWithHTML` for rich descriptions in settings, and `loggingOptions` with per-module log levels for diagnostics.

Source: [Tasks Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts)

#### PaperForge Fit

PaperForge already uses all three patterns but inconsistently:
- Notice duration varies (0, 4000, 5000, 6000, 8000 ms) — **standardize**: 4000 for success, 6000 for warnings, 8000 for errors
- `console.log` for debug info — **migrate** to `loggingOptions` with per-module levels (adopt Tasks pattern)
- Status bar unused — **reserve** it for active operations or one actionable failure; normal readiness remains in the control center
- Error messages mix Chinese and English — **keep** i18n through the existing `t()` function

---

### 6. Command Availability & Conditional Commands

#### Obsidian Convention

```ts
this.addCommand({
  id: 'command-id',
  name: 'Command name',
  callback: () => { /* ... */ }
});
```

For conditional availability, use `checkCallback`:

```ts
this.addCommand({
  id: 'conditional-command',
  name: 'Do something only when ready',
  checkCallback: (checking: boolean) => {
    if (!this.gitReady) return false;
    if (checking) return true;
    // perform action
  }
});
```

Source: [Commands — docs.obsidian.md](https://docs.obsidian.md/Plugins/User+interface/Commands)

**Obsidian Git** uses `isAllInitialized()` as its capability probe — it checks the actual `gitManager` state:

```ts
async isAllInitialized(): Promise<boolean> {
    if (!this.gitReady) {
        await this.init({ fromReload: true });
    }
    return this.gitReady;
}
```

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) lines 770-775

**Dataview** registers commands with simple callbacks (force refresh, drop cache, rebuild view) — no guards because the commands work regardless of external state.

#### PaperForge Fit

PaperForge registers commands from `ACTIONS` definition array but uses **no `checkCallback` guards** — every command unconditionally runs `resolvePythonExecutable()`. This means commands appear enabled even when Python is missing.

**Adopt `checkCallback` with principle-only guidance** — each command's availability must be gated by an independent capability probe, not by `setup_complete`. Probes must be:
- **Lightweight**: cached results, not full `execFile` calls on every palette open
- **Specific**: each command probes the exact runtime capability it needs
- **Re-evaluated**: on settings change or explicit refresh

**Important:** Path resolution (`resolvePythonExecutable`) is not capability readiness — a file existing at a path does not guarantee the binary works or has the required packages installed. Separate these concerns in the capability model.

The `setup_complete` flag is for **onboarding flow gating** (whether to show the wizard), not for runtime capability checks. Exact probe design is deferred to Issue #69 (Settings Redesign).

---

### 7. Secret/Credential Handling

#### Obsidian Convention

**Current PaperForge pattern:** Stores API keys directly in `data.json` as plaintext:
```ts
paddleocr_api_key: string;
vector_db_api_key: string;
```

Source: [PaperForge constants.ts](https://github.com/LLLin000/PaperForge/blob/master/paperforge/plugin/src/constants.ts)

**Obsidian 1.11.4+ native pattern:** Use `SecretStorage` + `SecretComponent`:

```ts
import { SecretComponent } from 'obsidian';

new Setting(containerEl)
  .setName('API key')
  .addComponent(el => new SecretComponent(this.app, el)
    .setValue(this.plugin.settings.mySetting)
    .onChange(value => {
      this.plugin.settings.mySetting = value; // stores NAME, not value
      this.plugin.saveSettings();
    }));

// At runtime:
const secret = app.secretStorage.getSecret(this.settings.mySetting);
```

Source: [Store secrets — obsidian-developer-docs](https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/Guides/Store%20secrets.md)

**Obsidian Git** stores Git credentials through `LocalStorageSettings` (Obsidian's `app.saveLocalStorage()` API), not in `data.json`. Obsidian Git settings that formerly held credentials are migrated to localStorage.

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) `migrateSettings()` method at lines 480-500

#### PaperForge Fit

**Adopt SecretStorage** for `paddleocr_api_key` and `vector_db_api_key`. This requires bumping `minAppVersion` from `1.9.0` to at least `1.11.4`.

**Min-version tradeoff:** PaperForge's current `minAppVersion: 1.9.0` supports Obsidian releases from mid-2024. SecretStorage (1.11.4) was released approximately late 2025. By mid-2026, a 1.11.4 floor is likely sustainable — but the project must explicitly decide:
- **Option A:** Bump to 1.11.4, adopt SecretStorage, remove plaintext keys from settings
- **Option B:** Stay at 1.9.0, keep plaintext keys, migrate later

This decision should be informed by PaperForge's actual user version distribution (not available during this research).

The migration function must: (1) detect existing keys in `data.json`, (2) import them into SecretStorage, (3) remove them from settings on next load. A migration crash must not lose credentials — keep originals in `data.json` until SecretStorage confirms the write.

---

### 8. Progressive Disclosure & Collapsible Sections

#### Obsidian Convention

Plugins implement collapsible sections with CSS + click handlers:

**Tasks:** Uses `headingOpened` in settings to persist which sections are expanded:
```ts
headingOpened: HeadingState = { 'section-id': true };
```

Source: [Tasks Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts)

**PaperForge:** Already implements this pattern with `_advCollapsed` + CSS toggle. The `getDisclosureState`/`toggleDisclosureState` utility at `src/utils/disclosure.ts` wraps the pattern cleanly.

**Templater:** Uses modals for complex settings (folder templates, regex templates) instead of inline collapsible sections, keeping the main settings tab clean.

Source: [Templater commit 8d41bf9](https://github.com/SilentVoid13/Templater/commit/8d41bf9a35187d221e26fba284ba3a94ba27af8e)

**Declarative API equivalent:** Groups with `visible` predicates:
```ts
{
  type: 'group',
  name: 'Advanced Settings',
  visible: () => settings.showAdvanced,
  children: [ /* ... */ ],
}
```

#### PaperForge Fit

PaperForge's collapsible "Advanced" section and skills collapsible groups are well-implemented. Suggested improvements:
- Persist collapse state in `data.json` (currently `_advCollapsed` lives in the tab instance, so it resets on re-render)
- **Consider Templater's pattern**: move complex multi-field configuration (embed build controls, vector DB deps install) into dedicated modals, keeping the settings tab focused

---

### 9. Platform Constraints

#### Obsidian Convention

```ts
import { Platform } from 'obsidian';
// Platform.isDesktop, Platform.isMobile
// Platform.isIosApp, Platform.isAndroidApp
// Platform.isPhone, Platform.isTablet
```

Source: [Platform API — docs.obsidian.md](https://docs.obsidian.md/Reference/TypeScript+API/Platform)

**Obsidian Git** uses `Platform.isDesktopApp` to choose between `SimpleGit` (desktop, native binary) and `IsomorphicGit` (mobile, JS implementation).

**Templater** removes the checkbox in `ConfirmDangerousSettingModal` on mobile and uses updated button text instead.

Source: [Templater commit 70a24ce](https://github.com/SilentVoid13/Templater/commit/70a24cefece47be55018b989b255b224a9b3b718)

#### PaperForge Fit

PaperForge's `manifest.json` declares `isDesktopOnly: true`, which means Obsidian blocks the plugin from loading on mobile entirely. No runtime Platform guards are needed for the current deployment surface.

**If mobile support is ever added**, the following patterns become prerequisites:
1. All `execFile`/`spawn`/`exec` calls must be guarded by `Platform.isDesktopApp` checks
2. Mobile-relevant operations must fall back to a Node.js/WASM implementation (analogous to Obsidian Git's `IsomorphicGit`)
3. Python runtime detection must return `"not-available"` on mobile
4. The settings tab must handle the absence of Python gracefully

This report documents the Platform patterns from mature plugins as a **reference for that future decision**, not as a current gap.

---

### 10. Diagnostics, Support & Logging

#### Obsidian Convention

**Tasks** provides a structured logging pattern:

```ts
interface LogOptions {
  minLevels: {
    '': string;           // root logger
    'tasks': string;      // module-level
    'tasks.Cache': string;
    'tasks.Events': string;
    'tasks.File': string;
    'tasks.Query': string;
    'tasks.Task': string;
  };
}
```

Source: [Tasks Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts) lines 90-107

Each module logs at its configured minimum level (`debug` | `info` | `warn` | `error`). The settings UI exposes an About section with a "Show debug log" button.

**Dataview** logs version info on load:
```ts
console.log(`Dataview: version ${this.manifest.version} (requires obsidian ${this.manifest.minAppVersion})`);
```

Source: [Dataview main.ts](https://github.com/blacksmithgu/obsidian-dataview/blob/master/src/main.ts) line 120

#### PaperForge Fit

PaperForge logs only via `console.log`/`console.warn` with no structured logging. **Adopt the Tasks pattern**: define `LogOptions` with per-module levels (`sync`, `ocr`, `embed`, `memory`, `doctor`) and create a debug section in the 维护 tab that shows recent log entries and provides a "Copy diagnostics" button for support.

---

### 11. Settings Persistence & Migration

#### Obsidian Convention

**Tasks** has a mature migration pattern:

```ts
function migrateSettings(loadedSettings: any): Partial<Settings> {
  const migratedSettings = { ...loadedSettings };
  if ('includes' in migratedSettings && !('presets' in migratedSettings)) {
    migratedSettings.presets = migratedSettings.includes;
    delete migratedSettings.includes;
  }
  // Add future migrations here as needed
  return migratedSettings;
}
```

Source: [Tasks Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts)

**Obsidian Git** also migrates settings in `migrateSettings()`:
```ts
async migrateSettings(): Promise<void> {
  if (this.settings.mergeOnPull != undefined) {
    this.settings.syncMethod = this.settings.mergeOnPull ? "merge" : "rebase";
    this.settings.mergeOnPull = undefined;
    await this.saveSettings();
  }
  // ...
}
```

Source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts)

#### PaperForge Fit

PaperForge has no centralized schema-versioned settings migration — defaults are applied with `Object.assign()` which only works for new installations. **Adopt the Tasks migration pattern**: add a `migrateSettings()` function called from `loadSettings()` that handles:
- SecretStorage key import (if minAppVersion is bumped)
- Adding new default fields to existing configs
- Handling `_python_path_stale` cleanup

---

### 12. Internationalization (i18n)

#### Obsidian Convention

**Tasks** uses a custom `i18n` module with JSON locale files:
```ts
import { i18n } from '../i18n/i18n';
new Setting(containerEl)
  .setName(i18n.t('settings.format.displayName.tasksEmojiFormat'))
```

Source: [Tasks SettingsTab.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/SettingsTab.ts)

**PaperForge** already has an i18n system (`i18n.ts` + `t()` function) covering Chinese and English.

#### PaperForge Fit

PaperForge's i18n is ahead of the majority of Obsidian plugins. Keep it. Minor suggestion: call `setLanguage(this.app)` earlier in `onload()` (before any UI registration) to prevent initial language flash.

---

### 13. Release Notes & Update Notification

#### Obsidian Convention

Most plugins use `CHANGELOG.md` only. **Obsidian Git** references its `CHANGELOG.md` for release notes.

**PaperForge** implements a dedicated release-notes tab rendered from a structured `release-notes.json` file, with version comparison against `last_seen_version`. This goes beyond what the studied plugins do.

#### PaperForge Fit

PaperForge's release-notes tab is a well-designed feature that should be kept. Minor improvement: visually indicate when a new version has been released since last open (like VS Code's changelog badge), using `last_seen_version` comparison in `_checkReleaseNotes()`.

---

## Evidence Matrix

| Pattern | Source Plugin | Source URL | Observable Code Seam | Strength | Limitation | PaperForge Fit |
|---------|--------------|-----------|---------------------|----------|------------|---------------|
| Settings Tab (imperative) | Dataview | [src/main.ts](https://github.com/blacksmithgu/obsidian-dataview/blob/master/src/main.ts) | `addSettingTab(new GeneralSettingsTab(...))` | Full DOM control | No search indexing | Keep for complex tabs; adopt declarative for simple controls |
| Declarative Settings | Templater | [commit 957a175](https://github.com/SilentVoid13/Templater/commit/957a17541a3bc87eac0fe6e4729ccbeaef42f199) | `getSettingDefinitions()` override | Free search, auto-save, validation | Requires 1.13.0+ | Path B (dual support) |
| Dependency Detection | Obsidian Git | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) L600-660 | `checkRequirements()` → union result | Clear error states, retry flow | N/A | Adopt directly |
| External Runtime Selection | Obsidian Git | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) | `Platform.isDesktopApp` for git impl | Platform-adaptive | N/A | Reference for future mobile support |
| Secret/Key Storage | Obsidian Core | [Store secrets guide](https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/Guides/Store%20secrets.md) | `SecretComponent` + `app.secretStorage.getSecret()` | Vault-keyed, cross-plugin, no plaintext | Requires 1.11.4+ | Adopt for API keys; requires minAppVersion decision |
| Per-Vault Dangerous Settings | Templater | [commit 957a175](https://github.com/SilentVoid13/Templater/commit/957a175) | `ConfirmDangerousSettingModal`, vault-scoped flags | Social engineering mitigation | More UI clicks | Consider for auto-update/exec features |
| Settings Migration | Tasks | [src/Config/Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts) | `migrateSettings()` function | Backward compat, explicit | Must be maintained | Adopt directly |
| Structured Logging | Tasks | [src/Config/Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts) L90-107 | `LogOptions.minLevels` per module | Debuggable, user-controllable | Configuration overhead | Adopt for sync/ocr/embed |
| Conditional Commands | Obsidian Git | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) | `isAllInitialized()` guard via `checkCallback` | Prevents no-op execution | N/A | Adopt with independent capability probes |
| Status Bar | Obsidian Git | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) | `addStatusBarItem()` + `StatusBar` class | Persistent, glanceable | Limited real estate | Adopt for sync status |
| Error Display | Obsidian Git | [src/main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) | `displayError()` → `new Notice()` | Consistent routing | Duration not standardized | Standardize durations |
| Privacy/Consent Modal | PaperForge (self) | [src/views/modals.ts](https://github.com/LLLin000/PaperForge) | `PaperForgeOcrPrivacyModal` | Clear consent flow | N/A | Keep |
| Collapsible Sections (persisted) | Tasks | [src/Config/Settings.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/Settings.ts) | `headingOpened: HeadingState` | Persisted state | Minor complexity | Adopt persistence |
| Setup Wizard Modal | PaperForge (self) | [src/views/modals.ts](https://github.com/LLLin000/PaperForge) | `PaperForgeSetupModal` | Step-by-step | Coupled to settings tab | Decouple from settings |
| Plugin Version Logging | Dataview | [src/main.ts](https://github.com/blacksmithgu/obsidian-dataview/blob/master/src/main.ts) L120 | `console.log` on load | Simple, informative | Not user-visible | Adopt with logging module |
| i18n | Tasks | [src/Config/SettingsTab.ts](https://github.com/obsidian-tasks-group/obsidian-tasks/blob/b157cadb/src/Config/SettingsTab.ts) | `i18n.t('key')` throughout | Full localization | Maintenance cost | Keep existing |
| Release Notes Tab | PaperForge (self) | [src/settings.ts](https://github.com/LLLin000/PaperForge) | `release-notes.json` + render tab | Structured, version-tracked | N/A | Keep |
| Modal-Based Complex Config | Templater | [commit 8d41bf9](https://github.com/SilentVoid13/Templater/commit/8d41bf9) | `FileRegexTemplateModal`, `FolderTemplateModal` | Clean settings tab | Extra modal navigation | Consider for embed build controls |

---

## Adopt / Adapt / Reject Decisions

### Adopt (directly integrate without significant change)

| Pattern | Rationale |
|---------|-----------|
| `checkRequirements()` result union | Replaces ad-hoc `resolvePythonExecutable` + status string checks; enables typed error states |
| `migrateSettings()` function | PaperForge has no centralized schema-versioned settings migration; needed for schema evolution |
| `LogOptions` with per-module levels | Structured debugging essential for external runtime issues |
| `checkCallback` with principle guidance | Prevents users from clicking commands that cannot work; probes must be independent capability checks, not setup_complete. Path resolution ≠ capability readiness |
| Minimal status bar for active work or one actionable failure | Keeps transient operation state glanceable without duplicating the normal control-center dashboard |
| `displayError()` / `displayMessage()` | Consolidates scattered Notice creation patterns |
| Persist collapse state in `data.json` | Currently resets on every re-render |

### Adapt (modify for PaperForge context)

| Pattern | Adaptation |
|---------|------------|
| Declarative Settings (Path B) | Adopt simple controls (toggles, dropdowns, text) while keeping imperative `render` for skills list, embed build, health display |
| SecretStorage | API keys → SecretStorage; config URL/model stays in settings. Migration function required. Requires minAppVersion decision (1.9.0 → ≥1.11.4) |
| Per-vault dangerous settings | Not applicable to `auto_update_on_startup` — plugin `data.json` is already vault-local per Obsidian's plugin isolation model |
| Templater's modal-based complex config | Move embed build controls + vector DB dependency install into dedicated modals instead of inline collapse |
| Notice duration standardization | 4000ms success, 6000ms warnings, 8000ms errors — currently inconsistent |

### Reject (not suitable for PaperForge)

| Pattern | Rationale |
|---------|-----------|
| Pure declarative settings (Path A) | PaperForge has too many custom UI components (skills list, live status, embed progress) that can't be expressed declaratively |
| Heading tracking for all sections | Overkill for PaperForge's multi-tab layout; current tab-based navigation is sufficient |
| Full Svelte/React settings (some plugins use frameworks) | Would require build system changes; PaperForge's vanilla TS approach matches the current `esbuild` setup |

---

## Pattern Guidance for the Six PaperForge Modules

The approved information architecture remains **安装 / 文献库 / OCR / 记忆 / 维护 / 帮助**. This research does not define the final controls; Issues #69 and #71 own that design.

| Module | Verified current seams | Pattern guidance |
|---|---|---|
| 安装 | `paperforge/plugin/src/settings.ts`, `views/modals.ts`, `services/python-bridge.ts` | Keep progressive setup and validation in a focused modal. Separate capability checks from settings rendering and from onboarding history. |
| 文献库 | Path settings and sync actions in `settings.ts` and `main.ts` | Simple stored values may use declarative settings after a minimum-version decision; live validation and sync actions remain imperative. |
| OCR | Privacy modal in `views/modals.ts`; maintenance rendering in `settings.ts` and `services/ocr-maintenance-ui.ts` | Preserve explicit consent. Gate actions on OCR capability facts, not on a global setup flag. |
| 记忆 | Runtime snapshots in `services/memory-state.ts`; controls in `settings.ts` | Render backend-owned memory and vector states independently. Keep progress and rebuild actions imperative. |
| 维护 | OCR maintenance service, doctor/repair command paths, and maintenance tab rendering | Show only actionable or currently running work. Put advanced diagnostics behind disclosure and keep destructive actions explicit. |
| 帮助 | `release-notes.json`, release-notes rendering, and `last_seen_version` | Keep dynamic release notes and support guidance together. Issue reporting must open a user-reviewed draft rather than submit automatically. |

Across all six modules, reuse one capability vocabulary and one action vocabulary once #69 defines them. Avoid duplicating backend classification rules in the plugin.

### Implementation Notes (cross-module)

- **Tab architecture:** Keep the current custom CSS-tab pattern through the redesign; consider declarative sub-pages only if `minAppVersion` is deliberately raised to 1.13.0+.
- **Declarative mix:** Simple settings can use declarative definitions; complex live sections remain imperative. Dual support avoids forcing a version decision in this research ticket.
- **Settings persistence:** Add a centralized schema-versioned migration path before changing stored settings, especially before any SecretStorage adoption.
- **i18n:** Route all new user-facing settings text through the existing `t()` function.


### Cross-Module: Status Bar

Use the status bar exclusively for active background operations or a single failure needing user attention. Normal readiness state belongs in the control center (dashboard view), not in the status bar.

Pattern source: [Obsidian Git main.ts](https://github.com/Vinzent03/obsidian-git/blob/master/src/main.ts) uses status bar only for git action state and branch display, driven by `setPluginState()` — it shows the current operation (pulling, committing) when active, and is minimal otherwise.

### Cross-Module: Conditional Command Availability

Commands that depend on external runtime availability **must** use `checkCallback` for conditional enablement. Probes must be independent capability checks, not `setup_complete`:

```ts
this.addCommand({
  id: 'paperforge-sync',
  name: 'PaperForge: Sync Library',
  checkCallback: (checking: boolean) => {
    if (!capabilityProbe.pythonAvailable()) return false;
    if (checking) return true;
    // perform sync
  }
});
```

Capability probes must be lightweight (cached results, not subprocess calls) and re-evaluated on settings change or explicit refresh.

**Important:** Path resolution (`resolvePythonExecutable`) checks that a file exists at the configured path — that is **path resolution, not capability readiness**. A file existing at a path does not guarantee the binary works or has the required packages installed. Separate these concerns:
- **Path resolution** → lights-on check (during `checkRequirements()`)
- **Capability readiness** → per-command probe (Python can actually run the target module)

Exact probe design is deferred to Issue #69 (Settings Redesign).

## Unresolved Questions

1. **Minimum Obsidian version target:** PaperForge's current `minAppVersion: 1.9.0` predates SecretStorage (1.11.4+) and declarative settings (1.13.0+). Adopting either pattern requires a version bump. This research cannot determine the user version distribution — that data lives in the plugin's Obsidian dashboard stats. The team should check dashboard analytics and decide whether the 1.9.0 floor is still necessary.

2. **Settings tab DOM weight on lower-end desktops:** The 2394-line `display()` method constructs the full DOM for all tabs on every call. Lazy rendering (build tab DOM only when selected) would improve initial render time.

3. **SecretStorage migration safety:** Existing users have API keys in `data.json`. The migration must import existing keys into SecretStorage on first launch after upgrade, then remove them from `data.json`. If the migration crashes, users lose credentials. Strategy: keep originals in `data.json` until SecretStorage confirms the write.

4. **Status bar on mobile (if ever supported):** Obsidian's status bar exists on mobile but has limited space. Follow the same principle: only active operations or a single failure; normal readiness in the control center.

5. **i18n maintenance burden:** PaperForge's i18n is comprehensive, but adding a new locale requires translating ~200+ strings. Consider whether community contributions for additional locales are expected.

---

## Appendix: Source URLs

| Resource | URL |
|----------|-----|
| Obsidian Settings (imperative) | https://github.com/obsidianmd/obsidian-developer-docs/blob/31946e5a/en/Plugins/User%20interface/Settings.md |
| Declarative Settings Migration | https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/Guides/Migrate%20to%20declarative%20settings.md |
| Secret Storage Guide | https://github.com/obsidianmd/obsidian-developer-docs/blob/main/en/Plugins/Guides/Store%20secrets.md |
| Platform API | https://docs.obsidian.md/Reference/TypeScript+API/Platform |
| Notices API | https://docs.obsidian.md/Reference/TypeScript+API/Notice |
| Modals API | https://docs.obsidian.md/Reference/TypeScript+API/Modal |
| Commands API | https://docs.obsidian.md/Plugins/User+interface/Commands |
| Dataview | https://github.com/blacksmithgu/obsidian-dataview |
| Templater | https://github.com/SilentVoid13/Templater |
| Obsidian Git | https://github.com/Vinzent03/obsidian-git |
| Tasks | https://github.com/obsidian-tasks-group/obsidian-tasks |
| Sample Plugin | https://github.com/obsidianmd/obsidian-sample-plugin |
| PaperForge Manifest | manifest.json in repo (isDesktopOnly: true, minAppVersion: 1.9.0) |
