// Browser-hosted Obsidian 1.12 shim for deterministic UI state & Base documentation rendering.
// Note: used ONLY by scripts/dev/render_obsidian_ui_docs.py; never bundled into paperforge/plugin/main.js.

type CreateElOptions = {
  cls?: string | string[];
  text?: string;
  attr?: Record<string, string | number | boolean | null | undefined>;
  title?: string;
  type?: string;
  value?: string;
  href?: string;
  placeholder?: string;
  prepend?: boolean;
};

function installDomPolyfills(): void {
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (typeof proto.__pfShimInstalled === "boolean") return;
  proto.__pfShimInstalled = true;

  proto.empty = function (this: HTMLElement): void {
    this.innerHTML = "";
  };
  proto.addClass = function (this: HTMLElement, ...classes: string[]): void {
    for (const c of classes) {
      for (const token of String(c || "").split(/\s+/).filter(Boolean)) {
        this.classList.add(token);
      }
    }
  };
  proto.removeClass = function (this: HTMLElement, ...classes: string[]): void {
    for (const c of classes) {
      for (const token of String(c || "").split(/\s+/).filter(Boolean)) {
        this.classList.remove(token);
      }
    }
  };
  proto.toggleClass = function (
    this: HTMLElement,
    cls: string,
    force?: boolean
  ): void {
    for (const token of String(cls || "").split(/\s+/).filter(Boolean)) {
      this.classList.toggle(token, force);
    }
  };
  proto.hasClass = function (this: HTMLElement, cls: string): boolean {
    return this.classList.contains(cls);
  };
  proto.setText = function (this: HTMLElement, text: string): void {
    this.textContent = text ?? "";
  };
  proto.setAttr = function (
    this: HTMLElement,
    name: string,
    value: string | number | boolean | null
  ): void {
    if (value === null) {
      this.removeAttribute(name);
    } else {
      this.setAttribute(name, String(value));
    }
  };
  proto.createEl = function (
    this: HTMLElement,
    tag: string,
    opts?: CreateElOptions,
    cb?: (el: HTMLElement) => void
  ): HTMLElement {
    const el = this.ownerDocument.createElement(tag);
    if (opts?.cls) {
      const list = Array.isArray(opts.cls) ? opts.cls : [opts.cls];
      for (const c of list) {
        for (const token of String(c || "").split(/\s+/).filter(Boolean)) {
          el.classList.add(token);
        }
      }
    }
    if (opts?.text !== undefined) {
      el.textContent = String(opts.text);
    }
    if (opts?.title) el.title = opts.title;
    if (opts?.type && "type" in el) (el as HTMLInputElement).type = opts.type;
    if (opts?.value !== undefined && "value" in el)
      (el as HTMLInputElement).value = opts.value;
    if (opts?.href && el instanceof HTMLAnchorElement) el.href = opts.href;
    if (opts?.placeholder && "placeholder" in el)
      (el as HTMLInputElement).placeholder = opts.placeholder;
    if (opts?.attr) {
      for (const [k, v] of Object.entries(opts.attr)) {
        if (v !== null && v !== undefined) el.setAttribute(k, String(v));
      }
    }
    if (opts?.prepend && this.firstChild) {
      this.insertBefore(el, this.firstChild);
    } else {
      this.appendChild(el);
    }
    if (typeof cb === "function") {
      cb(el);
    }
    return el;
  };
  proto.createDiv = function (
    this: HTMLElement,
    opts?: CreateElOptions,
    cb?: (el: HTMLElement) => void
  ): HTMLDivElement {
    return (this as unknown as {
      createEl: (
        t: string,
        o?: CreateElOptions,
        fn?: (el: HTMLElement) => void
      ) => HTMLElement;
    }).createEl("div", opts, cb) as HTMLDivElement;
  };
  proto.createSpan = function (
    this: HTMLElement,
    opts?: CreateElOptions,
    cb?: (el: HTMLElement) => void
  ): HTMLSpanElement {
    return (this as unknown as {
      createEl: (
        t: string,
        o?: CreateElOptions,
        fn?: (el: HTMLElement) => void
      ) => HTMLElement;
    }).createEl("span", opts, cb) as HTMLSpanElement;
  };
}

installDomPolyfills();

const LUCIDE_SVG: Record<string, string> = {
  "book-open":
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>',
  library:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m16 6 4 14"/><path d="M12 6v14"/><path d="M8 8v12"/><path d="M4 4v16"/></svg>',
  "scan-text":
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 8h8"/><path d="M7 12h10"/><path d="M7 16h6"/></svg>',
  "file-text":
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
  settings:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/></svg>',
  "folder-open":
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/></svg>',
  "refresh-cw":
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/></svg>',
  table:
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>',
  filter:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
  "arrow-up-down":
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>',
  sliders:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/><line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/></svg>',
  search:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
};

export function setIcon(parent: HTMLElement, iconId: string): void {
  parent.innerHTML = LUCIDE_SVG[iconId] || LUCIDE_SVG["file-text"];
}

export function setTooltip(el: HTMLElement, tooltip: string): void {
  el.setAttribute("aria-label", tooltip);
  el.title = tooltip;
}

export class Component {
  load(): void {}
  unload(): void {}
  addChild<T extends Component>(c: T): T {
    return c;
  }
  register(_cb: () => void): void {}
  registerEvent(_ref: unknown): void {}
  registerDomEvent(_el: unknown, _ev: string, _cb: unknown): void {}
  registerInterval(id: number): number {
    return id;
  }
}

export class BasesView extends Component {
  type = "base";
  app: App = new App();
  config: Record<string, unknown> = {};
  data: { data: unknown[]; groupedData?: unknown[]; properties?: string[] } = {
    data: [],
  };
  allProperties: string[] = [];
  constructor(_controller?: unknown) {
    super();
  }
  onDataUpdated(): void {}
}

export class ItemView extends Component {
  leaf: WorkspaceLeaf;
  app: App;
  containerEl: HTMLElement;
  contentEl: HTMLElement;
  navigation = true;
  constructor(leaf: WorkspaceLeaf) {
    super();
    this.leaf = leaf;
    this.app = (leaf as unknown as { app?: App }).app ?? new App();
    this.containerEl = document.createElement("div");
    const viewHeader = document.createElement("div");
    viewHeader.className = "view-header";
    this.containerEl.appendChild(viewHeader);
    this.contentEl = document.createElement("div");
    this.contentEl.className = "view-content";
    this.containerEl.appendChild(this.contentEl);
  }
  getViewType(): string {
    return "";
  }
  getDisplayText(): string {
    return "";
  }
  getIcon(): string {
    return "file-text";
  }
  getState(): Record<string, unknown> {
    return {};
  }
  async setState(_state: unknown, _result: unknown): Promise<void> {}
}

export class PluginSettingTab extends Component {
  app: App;
  plugin: unknown;
  containerEl: HTMLElement;
  constructor(app: App, plugin: unknown) {
    super();
    this.app = app;
    this.plugin = plugin;
    this.containerEl = document.createElement("div");
  }
  display(): void {}
  hide(): void {}
}

export class Plugin extends Component {
  app: App = new App();
  manifest = { id: "paperforge", version: "2.2.0", name: "PaperForge" };
  addRibbonIcon(_icon: string, _title: string, _cb: () => void): HTMLElement {
    return document.createElement("div");
  }
  registerView(_type: string, _factory: unknown): void {}
  registerBasesView(_type: string, _reg: unknown): boolean {
    return true;
  }
  addSettingTab(_tab: unknown): void {}
  addCommand(_cmd: unknown): void {}
  async loadData(): Promise<Record<string, unknown>> {
    return {};
  }
  async saveData(_data: unknown): Promise<void> {}
}

export class Modal {
  app: App;
  modalEl: HTMLElement;
  titleEl: HTMLElement;
  contentEl: HTMLElement;
  private _rootEl: HTMLElement | null = null;
  constructor(app: App) {
    this.app = app;
    this.modalEl = document.createElement("div");
    this.modalEl.className = "modal pf-shim-modal";
    const header = document.createElement("div");
    header.className = "modal-header";
    this.titleEl = document.createElement("div");
    this.titleEl.className = "modal-title";
    header.appendChild(this.titleEl);
    this.contentEl = document.createElement("div");
    this.contentEl.className = "modal-content";
    this.modalEl.appendChild(header);
    this.modalEl.appendChild(this.contentEl);
  }
  setTitle(title: string): void {
    this.titleEl.textContent = title;
  }
  open(): void {
    const host = (this.app as unknown as { __modalHost?: HTMLElement })
      ?.__modalHost;
    const container = document.createElement("div");
    container.className = "modal-container pf-shim-modal-container";
    container.appendChild(this.modalEl);
    this._rootEl = container;
    if (host) {
      host.appendChild(container);
    }
    const self = this as unknown as { onOpen?: () => void };
    if (typeof self.onOpen === "function") {
      self.onOpen();
    }
  }
  close(): void {
    const self = this as unknown as { onClose?: () => void };
    if (typeof self.onClose === "function") self.onClose();
    this._rootEl?.remove();
    this._rootEl = null;
  }
}

export class Setting {
  settingEl: HTMLElement;
  infoEl: HTMLElement;
  nameEl: HTMLElement;
  descEl: HTMLElement;
  controlEl: HTMLElement;
  constructor(containerEl: HTMLElement) {
    this.settingEl = containerEl.createDiv({ cls: "setting-item" });
    this.infoEl = this.settingEl.createDiv({ cls: "setting-item-info" });
    this.nameEl = this.infoEl.createDiv({ cls: "setting-item-name" });
    this.descEl = this.infoEl.createDiv({ cls: "setting-item-description" });
    this.controlEl = this.settingEl.createDiv({ cls: "setting-item-control" });
  }
  setName(name: string | DocumentFragment): this {
    this.nameEl.textContent = typeof name === "string" ? name : name.textContent || "";
    return this;
  }
  setDesc(desc: string | DocumentFragment): this {
    this.descEl.textContent = typeof desc === "string" ? desc : desc.textContent || "";
    return this;
  }
  setClass(cls: string): this {
    this.settingEl.addClass(cls);
    return this;
  }
  setHeading(): this {
    this.settingEl.addClass("setting-item-heading");
    return this;
  }
  setDisabled(disabled: boolean): this {
    this.settingEl.toggleClass("is-disabled", disabled);
    return this;
  }
  addText(cb: (c: unknown) => unknown): this {
    const input = this.controlEl.createEl("input", { type: "text" }) as HTMLInputElement;
    let onChangeCb: ((val: string) => void) | null = null;
    input.addEventListener("change", () => onChangeCb?.(input.value));
    const api = {
      inputEl: input,
      setValue(v: string) {
        input.value = v ?? "";
        return api;
      },
      setPlaceholder(p: string) {
        input.placeholder = p ?? "";
        return api;
      },
      setDisabled(d: boolean) {
        input.disabled = d;
        return api;
      },
      onChange(fn: (v: string) => void) {
        onChangeCb = fn;
        return api;
      },
    };
    cb(api);
    return this;
  }
  addTextArea(cb: (c: unknown) => unknown): this {
    const ta = this.controlEl.createEl("textarea") as HTMLTextAreaElement;
    let onChangeCb: ((val: string) => void) | null = null;
    ta.addEventListener("change", () => onChangeCb?.(ta.value));
    const api = {
      inputEl: ta,
      setValue(v: string) {
        ta.value = v ?? "";
        return api;
      },
      setPlaceholder(p: string) {
        ta.placeholder = p ?? "";
        return api;
      },
      onChange(fn: (v: string) => void) {
        onChangeCb = fn;
        return api;
      },
    };
    cb(api);
    return this;
  }
  addDropdown(cb: (c: unknown) => unknown): this {
    const sel = this.controlEl.createEl("select", { cls: "dropdown" }) as HTMLSelectElement;
    let onChangeCb: ((val: string) => void) | null = null;
    sel.addEventListener("change", () => onChangeCb?.(sel.value));
    const api = {
      selectEl: sel,
      addOption(val: string, label: string) {
        sel.createEl("option", { value: val, text: label });
        return api;
      },
      addOptions(opts: Record<string, string>) {
        for (const [k, v] of Object.entries(opts || {})) {
          sel.createEl("option", { value: k, text: v });
        }
        return api;
      },
      setValue(v: string) {
        sel.value = v ?? "";
        return api;
      },
      onChange(fn: (v: string) => void) {
        onChangeCb = fn;
        return api;
      },
    };
    cb(api);
    return this;
  }
  addToggle(cb: (c: unknown) => unknown): this {
    let checked = false;
    let onChangeCb: ((v: boolean) => void) | null = null;
    const toggle = this.controlEl.createDiv({ cls: "checkbox-container" });
    const render = () => toggle.toggleClass("is-enabled", checked);
    toggle.addEventListener("click", () => {
      checked = !checked;
      render();
      onChangeCb?.(checked);
    });
    const api = {
      toggleEl: toggle,
      setValue(v: boolean) {
        checked = Boolean(v);
        render();
        return api;
      },
      setDisabled(d: boolean) {
        toggle.toggleClass("is-disabled", d);
        return api;
      },
      onChange(fn: (v: boolean) => void) {
        onChangeCb = fn;
        return api;
      },
    };
    cb(api);
    return this;
  }
  addButton(cb: (c: unknown) => unknown): this {
    const btn = this.controlEl.createEl("button", { type: "button" }) as HTMLButtonElement;
    const api = {
      buttonEl: btn,
      setButtonText(t: string) {
        btn.textContent = t;
        return api;
      },
      setCta() {
        btn.addClass("mod-cta");
        return api;
      },
      setWarning() {
        btn.addClass("mod-warning");
        return api;
      },
      setDisabled(d: boolean) {
        btn.disabled = d;
        return api;
      },
      setIcon(icon: string) {
        setIcon(btn, icon);
        return api;
      },
      onClick(fn: () => void) {
        btn.addEventListener("click", fn);
        return api;
      },
    };
    cb(api);
    return this;
  }
  addExtraButton(cb: (c: unknown) => unknown): this {
    const btn = this.controlEl.createEl("button", {
      type: "button",
      cls: "clickable-icon extra-setting-button",
    }) as HTMLButtonElement;
    const api = {
      extraSettingsEl: btn,
      setIcon(icon: string) {
        setIcon(btn, icon);
        return api;
      },
      setTooltip(t: string) {
        btn.title = t;
        return api;
      },
      onClick(fn: () => void) {
        btn.addEventListener("click", fn);
        return api;
      },
    };
    cb(api);
    return this;
  }
}

export class Notice {
  constructor(_msg: string, _timeout?: number) {}
}

export class TFile {
  path: string;
  basename: string;
  name: string;
  extension: string;
  constructor(p = "") {
    this.path = p;
    this.name = p.split("/").pop() || "";
    this.extension = this.name.includes(".") ? this.name.split(".").pop() || "" : "";
    this.basename = this.extension ? this.name.slice(0, -(this.extension.length + 1)) : this.name;
  }
}

export class TFolder {
  path = "";
  name = "";
}

export class WorkspaceLeaf {
  view: unknown = null;
  async setViewState(_state: unknown): Promise<void> {}
  getViewState(): Record<string, unknown> {
    return { state: {} };
  }
}

export class Scope {
  register(_mods: string[], _key: string, _cb: () => boolean): void {}
}

export class FileSystemAdapter {}

export class App {
  vault: Record<string, unknown>;
  workspace: Record<string, unknown>;
  plugins: { plugins: Record<string, unknown> };
  setting: Record<string, unknown>;
  private _files: Record<string, string> = {};
  private _events = new Map<string, Set<(...args: unknown[]) => void>>();

  constructor(files: Record<string, string> = {}, vaultPath = "D:/ResearchVault") {
    this._files = files;
    this.vault = {
      adapter: {
        basePath: vaultPath,
        getBasePath: () => vaultPath,
        exists: async (p: string) => p in this._files,
        read: async (p: string) => this._files[p] ?? "",
        getResourcePath: (p: string) => createFigurePreviewSvgDataUri(p),
      },
      read: async (f: TFile) => this._files[f.path] ?? "",
      getAbstractFileByPath: (p: string) => (p in this._files ? new TFile(p) : null),
      getFiles: () => Object.keys(this._files).map((p) => new TFile(p)),
      on: () => () => {},
      off: () => {},
      getConfig: (k: string) => (k === "language" ? "zh" : null),
    };
    this.workspace = {
      on: (ev: string, cb: (...args: unknown[]) => void) => {
        if (!this._events.has(ev)) this._events.set(ev, new Set());
        this._events.get(ev)!.add(cb);
        return { ev, cb };
      },
      off: (ev: string, ref: unknown) => {
        const cb = (ref as { cb?: (...a: unknown[]) => void })?.cb ?? ref;
        this._events.get(ev)?.delete(cb as (...a: unknown[]) => void);
      },
      offref: (ref: unknown) => {
        const r = ref as { ev?: string; cb?: (...a: unknown[]) => void };
        if (r?.ev && r?.cb) this._events.get(r.ev)?.delete(r.cb);
      },
      trigger: (ev: string, ...args: unknown[]) => {
        this._events.get(ev)?.forEach((cb) => cb(...args));
      },
      getActiveFile: () => null,
      openLinkText: async () => {},
      getLeavesOfType: () => [],
      getLeaf: () => new WorkspaceLeaf(),
      revealLeaf: async () => {},
    };
    this.plugins = { plugins: {} };
    this.setting = { open: () => {}, openTabById: () => ({}) };
  }
}

export const Platform = {
  isMobile: false,
  isDesktopApp: true,
  resourcePathPrefix: "app://local/",
};

export const MarkdownRenderer = {
  async render(
    _app: App,
    markdown: string,
    el: HTMLElement,
    _sourcePath: string,
    _component: Component
  ): Promise<void> {
    const html = String(markdown || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n\n/g, "</p><p>")
      .replace(/\n/g, "<br>");
    el.innerHTML = `<p>${html}</p>`;
  },
};

export const MarkdownView = class {};
export function addIcon(): void {}
export function normalizePath(p: string): string {
  return String(p || "").replace(/\\/g, "/");
}
export function debounce<T extends (...args: unknown[]) => void>(fn: T): T {
  return fn;
}
export function requestUrl(): Promise<unknown> {
  return Promise.resolve({});
}

function createFigurePreviewSvgDataUri(pathOrLabel: string): string {
  const label = pathOrLabel.split("/").pop() || "crop.jpg";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="320" height="150" viewBox="0 0 320 150">
    <rect width="320" height="150" fill="#fafafe" stroke="#d9dcef"/>
    <text x="14" y="20" font-family="sans-serif" font-size="11" font-weight="600" fill="#334155">Fig. 1B · ALP Activity (U/mg protein)</text>
    <line x1="42" y1="32" x2="42" y2="122" stroke="#64748b" stroke-width="1.2"/>
    <line x1="42" y1="122" x2="295" y2="122" stroke="#64748b" stroke-width="1.2"/>
    <rect x="64" y="88" width="34" height="34" fill="#cbd5e1" rx="2"/>
    <rect x="116" y="64" width="34" height="58" fill="#93c5fd" rx="2"/>
    <rect x="168" y="42" width="34" height="80" fill="#6366f1" rx="2"/>
    <rect x="220" y="54" width="34" height="68" fill="#a5b4fc" rx="2"/>
    <text x="64" y="136" font-family="sans-serif" font-size="9" fill="#475569">Ctrl</text>
    <text x="113" y="136" font-family="sans-serif" font-size="9" fill="#475569">15Hz</text>
    <text x="166" y="136" font-family="sans-serif" font-size="9" font-weight="600" fill="#4338ca">75Hz*</text>
    <text x="216" y="136" font-family="sans-serif" font-size="9" fill="#475569">150Hz</text>
    <text x="242" y="20" font-family="monospace" font-size="9" fill="#64748b">${label.slice(0, 18)}</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function drawSimulatedAcademicPage(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  pageNumber: number
): void {
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  // Header & divider
  ctx.fillStyle = "#64748b";
  ctx.font = "11px Inter, system-ui, sans-serif";
  ctx.fillText("Biomaterials Research · Original Article (2025)", 42, 28);
  ctx.fillText(`Page ${pageNumber}`, w - 76, 28);
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(42, 36);
  ctx.lineTo(w - 42, 36);
  ctx.stroke();

  // Title block
  ctx.fillStyle = "#0f172a";
  ctx.font = "bold 17px Georgia, serif";
  ctx.fillText("Pulsed Electromagnetic Field (75 Hz) Enhances Osteogenic", 42, 62);
  ctx.fillText("Differentiation via L-Type Calcium Channel Activation", 42, 84);
  ctx.fillStyle = "#475569";
  ctx.font = "italic 11px Georgia, serif";
  ctx.fillText("Zhang W., Li M., Chen H. · Department of Orthopaedics", 42, 104);

  const col1X = 42;
  const col2X = w * 0.52;
  const colW = w * 0.43;

  // Left column text (aligns visually with left-col highlight & margin bracket)
  const leftLines = [
    "3. Results & Mechanistic Validation",
    "PEMF stimulation at 75 Hz ± 5 µM markedly",
    "enhanced galvanotaxis and early osteogenic",
    "differentiation in 3D agarose scaffolds (p=0.003).",
    "Intracellular Ca2+ transients peaked at 22 min",
    "and were abolished by nifedipine (10 µM),",
    "confirming L-type channel dependency prior to",
    "nuclear RUNX2 translocation.",
    "",
    "4. Statistical Modeling (Scanned Appendix Block)",
    "Cross-cohort linear mixed model evaluated age,",
    "sex, and scaffold stiffness covariates across",
    "48 New Zealand white rabbits over 12 weeks.",
    "Random intercepts remained non-significant",
    "(ICC = 0.04), supporting treatment generalizability.",
  ];
  let y = 138;
  for (const line of leftLines) {
    if (line.startsWith("3.") || line.startsWith("4.")) {
      ctx.fillStyle = "#0f172a";
      ctx.font = "bold 12px Inter, system-ui, sans-serif";
      y += 6;
    } else {
      ctx.fillStyle = "#1e293b";
      ctx.font = "11px Georgia, serif";
    }
    ctx.fillText(line, col1X, y, colW);
    y += 18;
  }

  // Right column figure box + text
  const figX = col2X;
  const figY = 140;
  const figW = colW - 6;
  const figH = 190;
  ctx.fillStyle = "#f8fafc";
  ctx.strokeStyle = "#cbd5e1";
  ctx.fillRect(figX, figY, figW, figH);
  ctx.strokeRect(figX, figY, figW, figH);

  ctx.fillStyle = "#0f172a";
  ctx.font = "bold 11px Inter, sans-serif";
  ctx.fillText("Fig 1. Osteogenic markers under 75 Hz PEMF", figX + 12, figY + 22);

  // Mini plotted bars inside Fig 1
  ctx.strokeStyle = "#475569";
  ctx.beginPath();
  ctx.moveTo(figX + 34, figY + 42);
  ctx.lineTo(figX + 34, figY + 148);
  ctx.lineTo(figX + figW - 22, figY + 148);
  ctx.stroke();

  const bars = [
    { x: 52, h: 40, color: "#94a3b8", label: "Sham" },
    { x: 96, h: 68, color: "#60a5fa", label: "15Hz" },
    { x: 140, h: 98, color: "#6366f1", label: "75Hz*" },
    { x: 184, h: 52, color: "#a5b4fc", label: "75+Nif" },
  ];
  for (const b of bars) {
    ctx.fillStyle = b.color;
    ctx.fillRect(figX + b.x, figY + 148 - b.h, 28, b.h);
    ctx.fillStyle = "#334155";
    ctx.font = "10px Inter, sans-serif";
    ctx.fillText(b.label, figX + b.x - 2, figY + 164);
  }

  // Right column paragraphs below Figure 1
  const rightLines = [
    "3.2 Pathway Specificity",
    "Notably, co-administration of BAPTA-AM",
    "completely blocked ERK1/2 phosphorylation,",
    "whereas static sham fields showed no drift",
    "in baseline mineralization across replicates.",
  ];
  y = figY + figH + 28;
  for (const line of rightLines) {
    if (line.startsWith("3.2")) {
      ctx.fillStyle = "#0f172a";
      ctx.font = "bold 12px Inter, system-ui, sans-serif";
    } else {
      ctx.fillStyle = "#1e293b";
      ctx.font = "11px Georgia, serif";
    }
    ctx.fillText(line, col2X, y, colW);
    y += 18;
  }
}

export async function loadPdfJs(): Promise<unknown> {
  return {
    getDocument: () => ({
      promise: Promise.resolve({
        numPages: 12,
        async getPage(pageNumber: number) {
          return {
            getViewport: ({ scale }: { scale: number }) => ({
              width: 560 * scale,
              height: 490 * scale,
              transform: [scale, 0, 0, scale, 0, 0],
            }),
            render: ({
              canvasContext,
              viewport,
            }: {
              canvasContext: CanvasRenderingContext2D;
              viewport: { width: number; height: number };
            }) => ({
              promise: (async () => {
                drawSimulatedAcademicPage(
                  canvasContext,
                  viewport.width,
                  viewport.height,
                  pageNumber
                );
              })(),
            }),
            getTextContent: async () => ({
              items: [
                {
                  str: "PEMF stimulation at 75 Hz ± 5 µM markedly",
                  transform: [1, 0, 0, 11, 42, 330],
                },
              ],
            }),
          };
        },
        async destroy() {},
      }),
    }),
  };
}
