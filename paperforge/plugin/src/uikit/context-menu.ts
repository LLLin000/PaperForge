/**
 * Accessible floating ContextMenu with groups, shortcuts, checkmarks, and keyboard nav.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/context_menu.go`.
 */

import { setPfIcon, type PfIconName } from "../views/icons";
import { applyElevation } from "./elevation";
import type { LayerStack } from "./layer-stack";
import { renderKeycap } from "./primitives";

export type ContextMenuEntry =
  | {
      kind?: "item";
      label: string;
      icon?: PfIconName;
      shortcut?: string;
      checked?: boolean;
      disabled?: boolean;
      danger?: boolean;
      onSelect: () => void;
    }
  | { kind: "separator" }
  | { kind: "group"; label: string };

export interface ContextMenuOptions {
  layerStack?: LayerStack;
  hostEl?: HTMLElement;
}

let activeMenuCleanup: (() => void) | null = null;

export function closeActiveContextMenu(): void {
  activeMenuCleanup?.();
  activeMenuCleanup = null;
}

export function openContextMenuAt(
  x: number,
  y: number,
  entries: ContextMenuEntry[],
  opts: ContextMenuOptions = {}
): () => void {
  closeActiveContextMenu();

  const host = opts.hostEl ?? document.body;
  const doc = host.ownerDocument || document;
  const win = doc.defaultView || window;
  const previousFocus = (doc.activeElement as HTMLElement | null) ?? null;
  const menu = doc.createElement("div");
  menu.className = "pf-kit-context-menu";
  menu.dataset.state = "open";
  menu.setAttribute("role", "menu");
  menu.tabIndex = -1;
  applyElevation(menu, "floating");

  const buttons: HTMLButtonElement[] = [];

  for (const entry of entries) {
    if (entry.kind === "separator") {
      const sep = doc.createElement("div");
      sep.className = "pf-kit-menu-sep";
      menu.appendChild(sep);
      continue;
    }
    if (entry.kind === "group") {
      const grp = doc.createElement("div");
      grp.className = "pf-kit-menu-group";
      grp.textContent = entry.label;
      menu.appendChild(grp);
      continue;
    }
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "pf-kit-menu-item";
    btn.setAttribute("role", "menuitem");
    if (entry.danger) btn.classList.add("is-danger");
    if (entry.disabled) {
      btn.disabled = true;
      btn.classList.add("is-disabled");
    }

    const startSlot = doc.createElement("span");
    startSlot.className = "pf-kit-menu-start";
    if (entry.checked) {
      setPfIcon(startSlot, "check", 13);
    } else if (entry.icon) {
      setPfIcon(startSlot, entry.icon, 13);
    }
    btn.appendChild(startSlot);

    const lbl = doc.createElement("span");
    lbl.className = "pf-kit-menu-label";
    lbl.textContent = entry.label;
    btn.appendChild(lbl);

    if (entry.shortcut) {
      const scWrap = doc.createElement("span");
      scWrap.className = "pf-kit-menu-shortcut";
      renderKeycap(scWrap, entry.shortcut);
      btn.appendChild(scWrap);
    }

    btn.addEventListener("click", () => {
      if (entry.disabled) return;
      cleanup();
      entry.onSelect();
    });
    if (!entry.disabled) {
      buttons.push(btn);
    }
    menu.appendChild(btn);
  }

  menu.style.left = `${x}px`;
  menu.style.top = `${y}px`;
  host.appendChild(menu);

  // Viewport collision flip & clamping so menus near bottom/right edges stay inside viewport
  if (typeof menu.getBoundingClientRect === "function") {
    const rect = menu.getBoundingClientRect();
    const mw = Math.max(rect.width, 190);
    const mh = Math.max(rect.height, 120);
    const vw = win.innerWidth || 1024;
    const vh = win.innerHeight || 768;

    let clampedX = x;
    if (x + mw + 8 > vw && x - mw >= 8) {
      clampedX = x - mw;
    } else {
      clampedX = Math.max(8, Math.min(x, vw - mw - 8));
    }

    let clampedY = y;
    if (y + mh + 8 > vh && y - mh >= 8) {
      clampedY = y - mh;
      menu.classList.add("is-flipped-up");
    } else {
      clampedY = Math.max(8, Math.min(y, vh - mh - 8));
    }

    menu.style.left = `${clampedX}px`;
    menu.style.top = `${clampedY}px`;
  }

  let focusIdx = -1;
  const moveFocus = (delta: number) => {
    if (buttons.length === 0) return;
    focusIdx = (focusIdx + delta + buttons.length) % buttons.length;
    buttons[focusIdx].focus();
  };

  const onKeyDown = (ev: KeyboardEvent) => {
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      moveFocus(1);
    } else if (ev.key === "ArrowUp") {
      ev.preventDefault();
      moveFocus(-1);
    } else if (ev.key === "Home" && buttons.length > 0) {
      ev.preventDefault();
      focusIdx = 0;
      buttons[0].focus();
    } else if (ev.key === "End" && buttons.length > 0) {
      ev.preventDefault();
      focusIdx = buttons.length - 1;
      buttons[focusIdx].focus();
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      cleanup();
    }
  };

  const onPointerDownOutside = (ev: MouseEvent) => {
    if (!menu.contains(ev.target as Node)) {
      cleanup();
    }
  };

  menu.addEventListener("keydown", onKeyDown);
  const timer = setTimeout(() => {
    doc.addEventListener("mousedown", onPointerDownOutside);
  }, 0);

  let exitTimer: ReturnType<typeof setTimeout> | null = null;
  const cleanup = () => {
    clearTimeout(timer);
    if (exitTimer) {
      clearTimeout(exitTimer);
      exitTimer = null;
    }
    doc.removeEventListener("mousedown", onPointerDownOutside);
    menu.removeEventListener("keydown", onKeyDown);
    opts.layerStack?.unregister("pf-kit-context-menu");
    if (activeMenuCleanup === cleanup) {
      activeMenuCleanup = null;
    }
    if (
      previousFocus &&
      previousFocus.isConnected &&
      menu.contains(doc.activeElement) &&
      typeof previousFocus.focus === "function"
    ) {
      try {
        previousFocus.focus();
      } catch {
        // Ignore unfocusable triggers
      }
    }
    menu.dataset.state = "closed";
    const hasAnims =
      typeof menu.getAnimations === "function" &&
      menu.getAnimations().length > 0;
    if (hasAnims) {
      exitTimer = setTimeout(() => {
        exitTimer = null;
        menu.remove();
      }, 120);
    } else {
      menu.remove();
    }
  };

  opts.layerStack?.register("pf-kit-context-menu", cleanup);
  activeMenuCleanup = cleanup;
  menu.focus();
  return cleanup;
}

export function attachContextMenu(
  target: HTMLElement,
  buildEntries: () => ContextMenuEntry[],
  opts: ContextMenuOptions = {}
): () => void {
  const handler = (ev: MouseEvent) => {
    ev.preventDefault();
    ev.stopPropagation();
    openContextMenuAt(ev.clientX, ev.clientY, buildEntries(), opts);
  };
  target.addEventListener("contextmenu", handler);
  return () => target.removeEventListener("contextmenu", handler);
}
