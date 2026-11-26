/**
 * Linear/Twenty-style right slide-over detail drawer (SidePeek).
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/side_peek.go`.
 */

import { createPfIconBtn, setPfIcon, type PfIconName } from "../views/icons";
import { applyElevation } from "./elevation";
import type { LayerStack } from "./layer-stack";

export interface SidePeekOptions {
  id?: string;
  title: string;
  subtitle?: string;
  icon?: PfIconName;
  width?: number;
  layerStack?: LayerStack;
  renderHeaderActions?: (parent: HTMLElement) => void;
  renderBody: (bodyEl: HTMLElement) => void;
  renderFooter?: (footerEl: HTMLElement) => void;
  onClose?: () => void;
}

export class SidePeekController {
  private _hostEl: HTMLElement;
  private _opts: SidePeekOptions;
  private _rootEl: HTMLElement | null = null;
  private _open = false;
  private _previousFocus: HTMLElement | null = null;
  private _exitTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly _layerId: string;

  constructor(hostEl: HTMLElement, opts: SidePeekOptions) {
    this._hostEl = hostEl;
    this._opts = opts;
    this._layerId = opts.id || "pf-kit-sidepeek";
  }

  isOpen(): boolean {
    return this._open;
  }

  open(nextOpts?: Partial<SidePeekOptions>): void {
    if (nextOpts) {
      this._opts = { ...this._opts, ...nextOpts };
    }
    const doc = this._hostEl.ownerDocument || document;
    if (!this._open) {
      this._previousFocus = (doc.activeElement as HTMLElement | null) ?? null;
    }
    if (this._exitTimer) {
      clearTimeout(this._exitTimer);
      this._exitTimer = null;
    }
    this._open = true;
    this._mount();
    this._opts.layerStack?.register(this._layerId, () => this.close());
  }

  close(): void {
    if (!this._open) return;
    this._open = false;
    this._opts.layerStack?.unregister(this._layerId);

    const root = this._rootEl;
    const prevFocus = this._previousFocus;
    this._previousFocus = null;

    if (root) {
      root.dataset.state = "closed";
      const hasActiveAnimations =
        typeof root.getAnimations === "function" &&
        root.getAnimations({ subtree: true }).length > 0;
      if (hasActiveAnimations) {
        this._exitTimer = setTimeout(() => {
          this._exitTimer = null;
          if (!this._open && this._rootEl === root) {
            root.remove();
            this._rootEl = null;
          }
        }, 150);
      } else {
        root.remove();
        this._rootEl = null;
      }
    }

    if (
      prevFocus &&
      prevFocus.isConnected &&
      typeof prevFocus.focus === "function"
    ) {
      try {
        prevFocus.focus();
      } catch {
        // Ignore unfocusable previous targets
      }
    }
    this._opts.onClose?.();
  }

  destroy(): void {
    if (this._exitTimer) {
      clearTimeout(this._exitTimer);
      this._exitTimer = null;
    }
    this._opts.layerStack?.unregister(this._layerId);
    this._rootEl?.remove();
    this._rootEl = null;
    this._previousFocus = null;
    this._open = false;
  }

  private _mount(): void {
    const doc = this._hostEl.ownerDocument || document;
    this._rootEl?.remove();

    const root = doc.createElement("div");
    root.className = "pf-kit-sidepeek-overlay";
    root.dataset.state = "open";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", this._opts.title);

    const scrim = doc.createElement("button");
    scrim.type = "button";
    scrim.className = "pf-kit-sidepeek-scrim";
    scrim.setAttribute("aria-label", "关闭侧滑详情");
    scrim.addEventListener("click", () => this.close());
    root.appendChild(scrim);

    const panel = doc.createElement("div");
    panel.className = "pf-kit-sidepeek-panel";
    if (this._opts.width && this._opts.width > 0) {
      panel.style.width = `${this._opts.width}px`;
    }
    applyElevation(panel, "modal");

    const header = doc.createElement("div");
    header.className = "pf-kit-sidepeek-header";
    if (this._opts.icon) {
      const ico = doc.createElement("span");
      ico.className = "pf-kit-sidepeek-icon";
      setPfIcon(ico, this._opts.icon, 16);
      header.appendChild(ico);
    }

    const titles = doc.createElement("div");
    titles.className = "pf-kit-sidepeek-titles";
    const titleEl = doc.createElement("div");
    titleEl.className = "pf-kit-sidepeek-title";
    titleEl.textContent = this._opts.title;
    titles.appendChild(titleEl);
    if (this._opts.subtitle) {
      const subEl = doc.createElement("div");
      subEl.className = "pf-kit-sidepeek-subtitle";
      subEl.textContent = this._opts.subtitle;
      titles.appendChild(subEl);
    }
    header.appendChild(titles);

    if (this._opts.renderHeaderActions) {
      const actionsEl = doc.createElement("div");
      actionsEl.className = "pf-kit-sidepeek-header-actions";
      this._opts.renderHeaderActions(actionsEl);
      header.appendChild(actionsEl);
    }

    const closeBtn = createPfIconBtn(header, {
      icon: "x",
      label: "关闭侧滑面板",
      size: 15,
      cls: "pf-kit-sidepeek-close",
    });
    closeBtn.addEventListener("click", () => this.close());
    panel.appendChild(header);

    const body = doc.createElement("div");
    body.className = "pf-kit-sidepeek-body";
    this._opts.renderBody(body);
    panel.appendChild(body);

    if (this._opts.renderFooter) {
      const footer = doc.createElement("div");
      footer.className = "pf-kit-sidepeek-footer";
      this._opts.renderFooter(footer);
      panel.appendChild(footer);
    }

    root.appendChild(panel);
    this._hostEl.appendChild(root);
    this._rootEl = root;

    const firstFocusable = panel.querySelector<HTMLElement>(
      'button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
    );
    if (firstFocusable && typeof firstFocusable.focus === "function") {
      try {
        firstFocusable.focus();
      } catch {
        // Ignore in headless/detached nodes
      }
    } else {
      panel.tabIndex = -1;
      try {
        panel.focus();
      } catch {
        // Ignore in headless/detached nodes
      }
    }
  }
}
