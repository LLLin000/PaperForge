/**
 * Browser-safe Obsidian API shim for the standalone interactive UI Gallery
 * HTML (`prototypes/ui-gallery.html`). Never imported by `main.js`.
 */

const SVG_ICONS: Record<string, string> = {
  "file-text":
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>',
  table:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>',
  "arrow-up-down":
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>',
  filter:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>',
  sliders:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/><line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/></svg>',
  search:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
  plus: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
  layers:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
  "chevron-down":
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
  check:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>',
  settings:
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
};

export function installDomPolyfills(): void {
  if (typeof HTMLElement === "undefined") return;
  const proto = HTMLElement.prototype as unknown as Record<string, unknown>;
  if (typeof proto.empty !== "function") {
    proto.empty = function (this: HTMLElement) {
      this.textContent = "";
    };
  }
  if (typeof proto.addClass !== "function") {
    proto.addClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c || "")
          .split(/\s+/)
          .filter(Boolean)) {
          this.classList.add(p);
        }
      }
    };
  }
  if (typeof proto.removeClass !== "function") {
    proto.removeClass = function (this: HTMLElement, ...cls: string[]) {
      for (const c of cls) {
        for (const p of String(c || "")
          .split(/\s+/)
          .filter(Boolean)) {
          this.classList.remove(p);
        }
      }
    };
  }
  if (typeof proto.toggleClass !== "function") {
    proto.toggleClass = function (
      this: HTMLElement,
      cls: string,
      force?: boolean
    ) {
      this.classList.toggle(cls, force);
    };
  }
  if (typeof proto.setText !== "function") {
    proto.setText = function (this: HTMLElement, text: string) {
      this.textContent = text;
    };
  }
  if (typeof proto.setAttr !== "function") {
    proto.setAttr = function (this: HTMLElement, k: string, v: string) {
      this.setAttribute(k, v);
    };
  }
  if (typeof proto.createEl !== "function") {
    proto.createEl = function (
      this: HTMLElement,
      tag: string,
      opts?:
        | string
        | {
            cls?: string;
            text?: string;
            type?: string;
            value?: string;
            placeholder?: string;
            title?: string;
            href?: string;
            attr?: Record<string, string>;
          },
      cb?: (el: HTMLElement) => void
    ) {
      const doc = this.ownerDocument || document;
      const el = doc.createElement(tag);
      const o = typeof opts === "string" ? { cls: opts } : opts;
      if (o?.cls) {
        for (const c of String(o.cls).split(/\s+/).filter(Boolean)) {
          el.classList.add(c);
        }
      }
      if (o?.text !== undefined) el.textContent = String(o.text);
      if (o?.type && "type" in el) (el as HTMLInputElement).type = o.type;
      if (o?.value !== undefined && "value" in el) {
        (el as HTMLInputElement).value = o.value;
      }
      if (o?.placeholder !== undefined && "placeholder" in el) {
        (el as HTMLInputElement).placeholder = o.placeholder;
      }
      if (o?.title) el.title = o.title;
      if (o?.href && "href" in el) (el as HTMLAnchorElement).href = o.href;
      if (o?.attr) {
        for (const [k, v] of Object.entries(o.attr)) {
          el.setAttribute(k, String(v));
        }
      }
      this.appendChild(el);
      cb?.(el);
      return el;
    };
  }
  if (typeof proto.createDiv !== "function") {
    proto.createDiv = function (
      this: HTMLElement,
      opts?: unknown,
      cb?: (el: HTMLElement) => void
    ) {
      return (
        this as unknown as {
          createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
        }
      ).createEl("div", opts, cb);
    };
  }
  if (typeof proto.createSpan !== "function") {
    proto.createSpan = function (
      this: HTMLElement,
      opts?: unknown,
      cb?: (el: HTMLElement) => void
    ) {
      return (
        this as unknown as {
          createEl: (t: string, o?: unknown, c?: unknown) => HTMLElement;
        }
      ).createEl("span", opts, cb);
    };
  }
}

installDomPolyfills();

export type EventRef = Record<string, unknown>;

export class TFile {
  path: string;
  basename: string;
  extension: string;
  name: string;
  constructor(path = "mock.md") {
    this.path = path;
    const parts = path.split("/");
    this.name = parts[parts.length - 1] || "mock.md";
    const dot = this.name.lastIndexOf(".");
    this.basename = dot > 0 ? this.name.slice(0, dot) : this.name;
    this.extension = dot > 0 ? this.name.slice(dot + 1) : "";
  }
}

export class WorkspaceLeaf {
  app?: App;
  view?: unknown;
  updateHeader(): void {}
  async setViewState(): Promise<void> {}
}

export class App {
  __modalHost?: HTMLElement;
  vault = {
    adapter: {
      basePath: "/mock-vault",
      getResourcePath: (p: string) => p,
    },
    getConfig: (key?: string) => (key === "theme" ? "obsidian" : "zh"),
    getAbstractFileByPath: (p: string) => new TFile(p),
    getMarkdownFiles: () => [] as TFile[],
    cachedRead: async () => "# Mock Note\n\nContent preview.",
    read: async () => "# Mock Note\n\nContent preview.",
    on: () => ({}),
    offref: () => {},
  };
  workspace = {
    on: () => ({}),
    offref: () => {},
    getLeavesOfType: () => [] as WorkspaceLeaf[],
    getActiveViewOfType: () => null,
    getActiveFile: () => null,
    getRightLeaf: () => new WorkspaceLeaf(),
    getLeaf: () => new WorkspaceLeaf(),
    revealLeaf: async () => {},
    openLinkText: async () => {},
    trigger: () => {},
  };
  metadataCache = {
    getFileCache: () => ({ frontmatter: {} }),
    on: () => ({}),
    offref: () => {},
  };
  plugins = { plugins: {} as Record<string, unknown> };
  keymap = { pushScope: () => {}, popScope: () => {} };
  commands = {
    commands: {} as Record<string, { name: string }>,
    executeCommandById: () => false,
  };
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
  type = "paperforge-table";
  app: App = new App();
  config: Record<string, unknown> = {};
  data: { data: unknown[]; groupedData?: unknown[] } = { data: [] };
  onDataUpdated(): void {}
}

export class ItemView extends Component {
  leaf: WorkspaceLeaf;
  app: App;
  containerEl: HTMLElement;
  contentEl: HTMLElement;
  constructor(leaf: WorkspaceLeaf) {
    super();
    this.leaf = leaf;
    this.app = leaf.app ?? new App();
    this.containerEl = document.createElement("div");
    const header = document.createElement("div");
    header.className = "view-header";
    this.containerEl.appendChild(header);
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
  async setState(): Promise<void> {}
}

export class Modal {
  app: App;
  containerEl: HTMLElement;
  modalEl: HTMLElement;
  contentEl: HTMLElement;
  titleEl: HTMLElement;
  constructor(app: App) {
    this.app = app;
    this.containerEl = document.createElement("div");
    this.containerEl.className = "modal-container";
    this.modalEl = document.createElement("div");
    this.modalEl.className = "modal";
    this.titleEl = document.createElement("div");
    this.titleEl.className = "modal-title";
    this.contentEl = document.createElement("div");
    this.contentEl.className = "modal-content";
    this.modalEl.appendChild(this.titleEl);
    this.modalEl.appendChild(this.contentEl);
    this.containerEl.appendChild(this.modalEl);
  }
  open(): void {
    const host = this.app.__modalHost;
    if (host && !this.containerEl.parentElement) {
      host.appendChild(this.containerEl);
    }
    this.onOpen();
  }
  close(): void {
    this.onClose();
    this.containerEl.remove();
  }
  onOpen(): void {}
  onClose(): void {}
  setTitle(t: string): void {
    this.titleEl.textContent = t;
  }
}

export class SuggestModal<T> extends Modal {
  inputEl: HTMLInputElement = document.createElement("input");
  resultContainerEl: HTMLElement = document.createElement("div");
  limit = 40;
  setPlaceholder(p: string): void {
    this.inputEl.placeholder = p;
  }
  setInstructions(): void {}
  getSuggestions(_query: string): T[] {
    return [];
  }
  renderSuggestion(_item: T, _el: HTMLElement): void {}
  onChooseSuggestion(_item: T, _evt: MouseEvent | KeyboardEvent): void {}
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
}

export class MarkdownView {}

export class Scope {
  register(): void {}
}

export class Notice {
  constructor(_message: string, _duration?: number) {}
  setMessage(): void {}
  hide(): void {}
}

export class Menu {
  private _items: Array<{ title: string; cb?: () => void }> = [];
  addItem(
    fn: (item: {
      setTitle: (t: string) => unknown;
      setIcon: (i: string) => unknown;
      onClick: (cb: () => void) => unknown;
    }) => void
  ): this {
    const rec = { title: "", cb: undefined as (() => void) | undefined };
    const api = {
      setTitle: (t: string) => {
        rec.title = t;
        return api;
      },
      setIcon: () => api,
      onClick: (cb: () => void) => {
        rec.cb = cb;
        return api;
      },
    };
    fn(api);
    this._items.push(rec);
    return this;
  }
  addSeparator(): this {
    return this;
  }
  showAtMouseEvent(): void {}
}

export class Setting {
  settingEl: HTMLElement;
  constructor(containerEl: HTMLElement) {
    this.settingEl = document.createElement("div");
    this.settingEl.className = "setting-item";
    containerEl.appendChild(this.settingEl);
  }
  setName(name: string): this {
    const n = document.createElement("div");
    n.className = "setting-item-name";
    n.textContent = name;
    this.settingEl.appendChild(n);
    return this;
  }
  setDesc(desc: string): this {
    const d = document.createElement("div");
    d.className = "setting-item-description";
    d.textContent = desc;
    this.settingEl.appendChild(d);
    return this;
  }
  addToggle(
    cb: (comp: {
      setValue: (v: boolean) => unknown;
      onChange: (fn: (v: boolean) => void) => unknown;
    }) => void
  ): this {
    const input = document.createElement("input");
    input.type = "checkbox";
    this.settingEl.appendChild(input);
    const comp = {
      setValue: (v: boolean) => {
        input.checked = v;
        return comp;
      },
      onChange: () => comp,
    };
    cb(comp);
    return this;
  }
  addText(
    cb: (comp: {
      setValue: (v: string) => unknown;
      setPlaceholder: (p: string) => unknown;
      onChange: (fn: (v: string) => void) => unknown;
    }) => void
  ): this {
    const input = document.createElement("input");
    input.type = "text";
    this.settingEl.appendChild(input);
    const comp = {
      setValue: (v: string) => {
        input.value = v;
        return comp;
      },
      setPlaceholder: (p: string) => {
        input.placeholder = p;
        return comp;
      },
      onChange: () => comp,
    };
    cb(comp);
    return this;
  }
  addDropdown(
    cb: (comp: {
      addOption: (k: string, l: string) => unknown;
      setValue: (v: string) => unknown;
      onChange: (fn: (v: string) => void) => unknown;
    }) => void
  ): this {
    const sel = document.createElement("select");
    this.settingEl.appendChild(sel);
    const comp = {
      addOption: (k: string, l: string) => {
        const opt = document.createElement("option");
        opt.value = k;
        opt.textContent = l;
        sel.appendChild(opt);
        return comp;
      },
      setValue: (v: string) => {
        sel.value = v;
        return comp;
      },
      onChange: () => comp,
    };
    cb(comp);
    return this;
  }
  addButton(
    cb: (comp: {
      buttonEl: HTMLButtonElement;
      setButtonText: (t: string) => unknown;
      setIcon: (icon: string) => unknown;
      setTooltip: (t: string) => unknown;
      setCta: () => unknown;
      setWarning: () => unknown;
      setDisabled: (d: boolean) => unknown;
      onClick: (fn: () => void) => unknown;
    }) => void
  ): this {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pf-btn";
    this.settingEl.appendChild(btn);
    const comp = {
      buttonEl: btn,
      setButtonText: (t: string) => {
        btn.textContent = t;
        return comp;
      },
      setIcon: (icon: string) => {
        setIcon(btn, icon);
        return comp;
      },
      setTooltip: (t: string) => {
        btn.title = t;
        btn.setAttribute("aria-label", t);
        return comp;
      },
      setCta: () => {
        btn.classList.add("mod-cta", "pf-btn-primary");
        return comp;
      },
      setWarning: () => {
        btn.classList.add("mod-warning", "pf-btn-warning");
        return comp;
      },
      setDisabled: (d: boolean) => {
        btn.disabled = d;
        return comp;
      },
      onClick: (fn: () => void) => {
        btn.addEventListener("click", fn);
        return comp;
      },
    };
    cb(comp);
    return this;
  }
  addExtraButton(
    cb: (comp: {
      extraSettingsEl: HTMLButtonElement;
      setIcon: (icon: string) => unknown;
      setTooltip: (t: string) => unknown;
      setDisabled: (d: boolean) => unknown;
      onClick: (fn: () => void) => unknown;
    }) => void
  ): this {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "clickable-icon extra-setting-button";
    this.settingEl.appendChild(btn);
    const comp = {
      extraSettingsEl: btn,
      setIcon: (icon: string) => {
        setIcon(btn, icon);
        return comp;
      },
      setTooltip: (t: string) => {
        btn.title = t;
        btn.setAttribute("aria-label", t);
        return comp;
      },
      setDisabled: (d: boolean) => {
        btn.disabled = d;
        return comp;
      },
      onClick: (fn: () => void) => {
        btn.addEventListener("click", fn);
        return comp;
      },
    };
    cb(comp);
    return this;
  }
}

export class MarkdownRenderer {
  static async render(_app: App, md: string, el: HTMLElement): Promise<void> {
    el.textContent = md;
  }
}

export const Platform = {
  isWin: true,
  isMacOS: false,
  isLinux: false,
  resourcePathPrefix: "app://local/",
};

export const Keymap = {
  isModEvent: (e: MouseEvent | KeyboardEvent) =>
    Boolean(e?.ctrlKey || e?.metaKey),
};

export function setIcon(parent: HTMLElement, iconId: string): void {
  parent.innerHTML = SVG_ICONS[iconId] || SVG_ICONS["file-text"];
}

export function setTooltip(el: HTMLElement, tooltip: string): void {
  el.setAttribute("aria-label", tooltip);
  el.title = tooltip;
}

export function drawMockAcademicPage(
  ctx: CanvasRenderingContext2D,
  pageNumber: number
): void {
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, 560, 490);
  ctx.fillStyle = "#64748b";
  ctx.font = "10px Inter, system-ui, sans-serif";
  ctx.fillText(`Biomaterials (2025) · p.${pageNumber}`, 36, 28);
  ctx.fillStyle = "#0f172a";
  ctx.font = "bold 14px Inter, system-ui, sans-serif";
  ctx.fillText(
    "75 Hz PEMF Enhances Osteogenic Differentiation via L-Type Ca2+",
    36,
    56
  );

  // Two-column simulated text lines
  ctx.fillStyle = "#1e293b";
  ctx.font = "10.5px Georgia, serif";
  const linesL = [
    "3.1 Stimulation Parameters",
    "PEMF stimulation at 75 Hz (1.2 mT) enhanced",
    "early osteogenic differentiation and Ca2+ influx.",
    "Nifedipine (10 µM) abolished downstream ERK",
    "phosphorylation at 22 min across n = 6 donors.",
    "ALP activity peaked at day 7 compared to sham",
    "and 15 Hz controls (p < 0.01, ANOVA + Tukey).",
  ];
  let y = 92;
  for (const line of linesL) {
    ctx.fillText(line, 36, y);
    y += 22;
  }

  // Right column simulated bar plot (Fig 1)
  ctx.strokeStyle = "#cbd5e1";
  ctx.lineWidth = 1;
  ctx.strokeRect(290, 92, 232, 168);
  ctx.fillStyle = "#0f172a";
  ctx.font = "bold 11px Inter, system-ui, sans-serif";
  ctx.fillText("Fig 1. Osteogenic ALP Peak", 304, 114);
  const bars = [
    { x: 318, h: 42, c: "#94a3b8", l: "Sham" },
    { x: 364, h: 68, c: "#60a5fa", l: "15Hz" },
    { x: 410, h: 102, c: "#5b45c9", l: "75Hz*" },
    { x: 456, h: 48, c: "#a5b4fc", l: "75+Nif" },
  ];
  for (const b of bars) {
    ctx.fillStyle = b.c;
    ctx.fillRect(b.x, 230 - b.h, 28, b.h);
    ctx.fillStyle = "#475569";
    ctx.font = "9px Inter, system-ui, sans-serif";
    ctx.fillText(b.l, b.x - 1, 246);
  }
}

export function createMockPdfDoc() {
  return {
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
            if (
              !canvasContext ||
              typeof canvasContext.fillRect !== "function"
            ) {
              return;
            }
            const s = Math.max(0.25, viewport.width / 560);
            canvasContext.save();
            canvasContext.scale(s, s);
            drawMockAcademicPage(canvasContext, pageNumber);
            canvasContext.restore();
          })(),
        }),
        getTextContent: async () => ({
          items: [
            {
              str: "PEMF stimulation at 75 Hz ± 5 µM markedly enhanced galvanotaxis",
              transform: [1, 0, 0, 11, 36, 360],
            },
          ],
        }),
      };
    },
    async getOutline() {
      return [
        { title: "1. Introduction", dest: null, items: [] },
        { title: "2. Materials & Methods", dest: null, items: [] },
        {
          title: "3. Results",
          dest: null,
          items: [{ title: "3.1 Stimulation Parameters", dest: null }],
        },
        { title: "4. Discussion", dest: null, items: [] },
      ];
    },
    async destroy() {},
  };
}

export async function loadPdfJs(): Promise<unknown> {
  return {
    getDocument: () => ({
      promise: Promise.resolve(createMockPdfDoc()),
    }),
  };
}
