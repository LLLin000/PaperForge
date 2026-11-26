/**
 * Non-blocking Optimistic ToastQueue with Sonner-style stacked deck depth,
 * hover fan-out, swipe-to-dismiss gesture, and keyed DOM reconciliation.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/toast.go`.
 */

import { createPfIconBtn, setPfIcon, type PfIconName } from "../views/icons";
import { applyElevation } from "./elevation";

export type ToastTone = "info" | "success" | "warning" | "danger";

export interface ToastInput {
  id?: string;
  tone?: ToastTone;
  message: string;
  undoLabel?: string;
  onUndo?: () => void;
  durationMs?: number;
}

export interface ToastItem {
  id: string;
  tone: ToastTone;
  message: string;
  undoLabel: string;
  onUndo?: () => void;
  durationMs: number;
  createdAt: number;
}

export class ToastQueue {
  private _items: ToastItem[] = [];
  private _seq = 0;
  private _hostEl: HTMLElement | null = null;
  private _stackEl: HTMLElement | null = null;
  private _timers = new Map<string, ReturnType<typeof setTimeout>>();
  private _cardEls = new Map<string, HTMLElement>();

  mount(hostEl: HTMLElement): void {
    this._hostEl = hostEl;
    if (!this._stackEl) {
      const doc = hostEl.ownerDocument || document;
      this._stackEl = doc.createElement("div");
      this._stackEl.className = "pf-kit-toast-stack";
      this._stackEl.setAttribute("role", "status");
      this._stackEl.setAttribute("aria-live", "polite");
    }
    if (this._stackEl.parentElement !== hostEl) {
      hostEl.appendChild(this._stackEl);
    }
    this._render();
  }

  push(input: ToastInput): string {
    this._seq += 1;
    const id = input.id || `pf-toast-${this._seq}`;
    const durationMs =
      input.durationMs && input.durationMs > 0 ? input.durationMs : 5000;
    const item: ToastItem = {
      id,
      tone: input.tone ?? "info",
      message: input.message,
      undoLabel: input.undoLabel || "撤销",
      onUndo: input.onUndo,
      durationMs,
      createdAt: Date.now(),
    };
    const existingIdx = this._items.findIndex((it) => it.id === id);
    if (existingIdx >= 0) {
      this._items[existingIdx] = item;
      this._clearTimer(id);
      this._cardEls.get(id)?.remove();
      this._cardEls.delete(id);
    } else {
      this._items.push(item);
    }
    while (this._items.length > 6) {
      const evicted = this._items.shift();
      if (evicted) {
        this._clearTimer(evicted.id);
        this._removeCardNode(evicted.id, true);
      }
    }
    const timer = setTimeout(() => {
      this.dismiss(id);
    }, durationMs);
    this._timers.set(id, timer);
    this._render();
    return id;
  }

  dismiss(id: string): void {
    this._clearTimer(id);
    const before = this._items.length;
    this._items = this._items.filter((it) => it.id !== id);
    if (this._items.length !== before) {
      this._removeCardNode(id, false);
      this._render();
    }
  }

  items(): ToastItem[] {
    return this._items.map((it) => ({ ...it }));
  }

  clear(): void {
    for (const id of [...this._timers.keys()]) {
      this._clearTimer(id);
    }
    this._items = [];
    for (const card of this._cardEls.values()) {
      card.remove();
    }
    this._cardEls.clear();
    this._render();
  }

  destroy(): void {
    this.clear();
    this._stackEl?.remove();
    this._stackEl = null;
    this._hostEl = null;
  }

  private _clearTimer(id: string): void {
    const t = this._timers.get(id);
    if (t !== undefined) {
      clearTimeout(t);
      this._timers.delete(id);
    }
  }

  private _removeCardNode(id: string, immediate: boolean): void {
    const card = this._cardEls.get(id);
    this._cardEls.delete(id);
    if (!card) return;
    card.dataset.state = "closed";
    const hasAnims =
      !immediate &&
      typeof card.getAnimations === "function" &&
      card.getAnimations().length > 0;
    if (hasAnims) {
      setTimeout(() => card.remove(), 140);
    } else {
      card.remove();
    }
  }

  private _createCard(doc: Document, item: ToastItem): HTMLElement {
    const card = doc.createElement("div");
    card.className = `pf-kit-toast pf-kit-toast--${item.tone}`;
    card.dataset.toastId = item.id;
    card.dataset.state = "open";
    applyElevation(card, "floating");

    const mainWrap = doc.createElement("div");
    mainWrap.className = "pf-kit-toast-main";

    const iconWrap = doc.createElement("span");
    iconWrap.className = "pf-kit-toast-icon";
    const iconName: PfIconName =
      item.tone === "success"
        ? "check-circle"
        : item.tone === "warning"
          ? "alert-triangle"
          : item.tone === "danger"
            ? "alert-circle"
            : "info";
    setPfIcon(iconWrap, iconName, 15);
    mainWrap.appendChild(iconWrap);

    const msg = doc.createElement("span");
    msg.className = "pf-kit-toast-msg";
    msg.textContent = item.message;
    mainWrap.appendChild(msg);
    card.appendChild(mainWrap);

    const actions = doc.createElement("div");
    actions.className = "pf-kit-toast-actions";

    if (item.onUndo) {
      const undoBtn = doc.createElement("button");
      undoBtn.type = "button";
      undoBtn.className = "pf-kit-btn pf-kit-btn--secondary pf-kit-toast-undo";
      undoBtn.textContent = item.undoLabel;
      undoBtn.addEventListener("click", () => {
        const cb = item.onUndo;
        this.dismiss(item.id);
        cb?.();
      });
      actions.appendChild(undoBtn);
    }

    const closeBtn = createPfIconBtn(actions, {
      icon: "x",
      label: "关闭提示",
      size: 13,
      cls: "pf-kit-toast-close",
    });
    closeBtn.addEventListener("click", () => this.dismiss(item.id));
    card.appendChild(actions);

    // Tactile swipe-to-dismiss gesture (horizontal flick >= 72px)
    let startX = 0;
    let dragging = false;
    const onMove = (ev: PointerEvent) => {
      if (!dragging) return;
      const dx = ev.clientX - startX;
      card.style.setProperty("--pf-toast-swipe-x", `${dx}px`);
      card.style.opacity = String(Math.max(0.25, 1 - Math.abs(dx) / 140));
    };
    const onUp = (ev: PointerEvent) => {
      if (!dragging) return;
      dragging = false;
      card.classList.remove("is-swiping");
      doc.removeEventListener("pointermove", onMove);
      doc.removeEventListener("pointerup", onUp);
      doc.removeEventListener("pointercancel", onUp);
      const dx = ev.clientX - startX;
      if (Math.abs(dx) >= 72) {
        this.dismiss(item.id);
      } else {
        card.style.removeProperty("--pf-toast-swipe-x");
        card.style.removeProperty("opacity");
      }
    };
    card.addEventListener("pointerdown", (ev: PointerEvent) => {
      if ((ev.target as HTMLElement | null)?.closest("button")) return;
      if (ev.button !== 0) return;
      dragging = true;
      startX = ev.clientX;
      card.classList.add("is-swiping");
      doc.addEventListener("pointermove", onMove);
      doc.addEventListener("pointerup", onUp);
      doc.addEventListener("pointercancel", onUp);
    });

    return card;
  }

  private _render(): void {
    if (!this._stackEl) return;
    const doc = this._stackEl.ownerDocument || document;
    const visible = this._items.slice(-3);
    const visibleIds = new Set(visible.map((v) => v.id));
    this._stackEl.classList.toggle("is-empty", visible.length === 0);

    // Drop stale cards no longer in the visible top-3 window
    for (const [id, el] of [...this._cardEls.entries()]) {
      if (!visibleIds.has(id)) {
        el.remove();
        this._cardEls.delete(id);
      }
    }

    // Reconcile existing cards + create new ones without tearing down siblings
    const total = visible.length;
    visible.forEach((item, idx) => {
      const depth = total - 1 - idx; // 0 = frontmost newest, 1 = behind, 2 = back
      let card = this._cardEls.get(item.id);
      if (!card) {
        card = this._createCard(doc, item);
        this._cardEls.set(item.id, card);
        this._stackEl!.appendChild(card);
      } else if (card.parentElement === this._stackEl) {
        // Keep DOM order newest-last so depth 0 stacks above older cards
        this._stackEl!.appendChild(card);
      }
      card.dataset.depth = String(depth);
      card.style.setProperty("--pf-toast-depth", String(depth));
    });
  }
}
