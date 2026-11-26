/**
 * Core UIKit primitives matching `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/`:
 * - renderListItem (Selected accent bar + IndentLevel + StartSlot + HoverEndSlot)
 * - renderKeycap (Keyboard chord keycap pills)
 * - renderSectionHeader (Uniform icon + title + tabular meta + trailing slot)
 * - renderInlineBanner / renderEmptyState / renderBadge / renderHoldToConfirm
 */

import { setPfIcon, type PfIconName } from "../views/icons";
import { applyElevation, applyFocusRing } from "./elevation";

export interface ListItemOptions {
  title: string;
  subtitle?: string;
  indentLevel?: number;
  selected?: boolean;
  disabled?: boolean;
  compact?: boolean;
  ariaLabel?: string;
  renderStart?: (slot: HTMLElement) => void;
  renderEnd?: (slot: HTMLElement) => void;
  renderHoverEnd?: (slot: HTMLElement) => void;
  onClick?: () => void;
}

export function renderListItem(
  parent: HTMLElement,
  opts: ListItemOptions
): HTMLButtonElement {
  const doc = parent.ownerDocument || document;
  const row = doc.createElement("button");
  row.type = "button";
  row.className = "pf-kit-list-item";
  if (opts.selected) row.classList.add("is-selected");
  if (opts.compact) row.classList.add("is-compact");
  if (opts.disabled) {
    row.disabled = true;
    row.classList.add("is-disabled");
  }
  row.setAttribute("aria-label", opts.ariaLabel || opts.title);
  if (opts.indentLevel && opts.indentLevel > 0) {
    row.style.paddingLeft = `${8 + opts.indentLevel * 12}px`;
  }
  applyFocusRing(row);

  if (opts.selected) {
    const bar = doc.createElement("span");
    bar.className = "pf-kit-list-item-bar";
    row.appendChild(bar);
  }

  if (opts.renderStart) {
    const start = doc.createElement("span");
    start.className = "pf-kit-list-item-start";
    opts.renderStart(start);
    row.appendChild(start);
  }

  const copy = doc.createElement("span");
  copy.className = "pf-kit-list-item-copy";
  const titleEl = doc.createElement("span");
  titleEl.className = "pf-kit-list-item-title";
  titleEl.textContent = opts.title;
  copy.appendChild(titleEl);
  if (opts.subtitle) {
    const subEl = doc.createElement("span");
    subEl.className = "pf-kit-list-item-sub";
    subEl.textContent = opts.subtitle;
    copy.appendChild(subEl);
  }
  row.appendChild(copy);

  if (opts.renderHoverEnd || opts.renderEnd) {
    const endWrap = doc.createElement("span");
    endWrap.className = "pf-kit-list-item-end";
    if (opts.renderEnd) {
      const restSlot = doc.createElement("span");
      restSlot.className = "pf-kit-list-item-end-rest";
      opts.renderEnd(restSlot);
      endWrap.appendChild(restSlot);
    }
    if (opts.renderHoverEnd) {
      const hoverSlot = doc.createElement("span");
      hoverSlot.className = "pf-kit-list-item-end-hover";
      opts.renderHoverEnd(hoverSlot);
      endWrap.appendChild(hoverSlot);
    }
    row.appendChild(endWrap);
  }

  if (!opts.disabled && opts.onClick) {
    row.addEventListener("click", opts.onClick);
  }
  parent.appendChild(row);
  return row;
}

/** Render one or more keycap chords like `"Ctrl+K / Ctrl+O"`. */
export function renderKeycap(parent: HTMLElement, chord: string): HTMLElement {
  const doc = parent.ownerDocument || document;
  const wrap = doc.createElement("span");
  wrap.className = "pf-kit-keycap-group pf-tnum";

  const alts = chord
    .split("/")
    .map((s) => s.trim())
    .filter(Boolean);
  alts.forEach((alt, altIdx) => {
    if (altIdx > 0) {
      const slash = doc.createElement("span");
      slash.className = "pf-kit-keycap-sep";
      slash.textContent = "/";
      wrap.appendChild(slash);
    }
    const keys = alt
      .split("+")
      .map((s) => s.trim())
      .filter(Boolean);
    const chordEl = doc.createElement("span");
    chordEl.className = "pf-kit-keycap-chord";
    for (const k of keys) {
      const kbd = doc.createElement("kbd");
      kbd.className = "pf-kit-keycap";
      kbd.textContent = k;
      chordEl.appendChild(kbd);
    }
    wrap.appendChild(chordEl);
  });

  parent.appendChild(wrap);
  return wrap;
}

export function renderSectionHeader(
  parent: HTMLElement,
  opts: {
    icon?: PfIconName;
    title: string;
    meta?: string;
    renderRight?: (slot: HTMLElement) => void;
  }
): HTMLElement {
  const doc = parent.ownerDocument || document;
  const header = doc.createElement("div");
  header.className = "pf-kit-section-header";

  const left = doc.createElement("div");
  left.className = "pf-kit-section-header-left";
  if (opts.icon) {
    const ico = doc.createElement("span");
    ico.className = "pf-kit-section-header-icon";
    setPfIcon(ico, opts.icon, 16);
    left.appendChild(ico);
  }
  const titleEl = doc.createElement("h3");
  titleEl.className = "pf-kit-section-header-title";
  titleEl.textContent = opts.title;
  left.appendChild(titleEl);

  if (opts.meta) {
    const metaEl = doc.createElement("span");
    metaEl.className = "pf-kit-section-header-meta pf-tnum";
    metaEl.textContent = opts.meta;
    left.appendChild(metaEl);
  }
  header.appendChild(left);

  if (opts.renderRight) {
    const right = doc.createElement("div");
    right.className = "pf-kit-section-header-right";
    opts.renderRight(right);
    header.appendChild(right);
  }

  parent.appendChild(header);
  return header;
}

export type BannerTone = "info" | "success" | "warning" | "danger";

export function renderInlineBanner(
  parent: HTMLElement,
  opts: {
    tone?: BannerTone;
    icon?: PfIconName;
    message: string;
    actionLabel?: string;
    onAction?: () => void;
  }
): HTMLElement {
  const doc = parent.ownerDocument || document;
  const tone = opts.tone ?? "info";
  const banner = doc.createElement("div");
  banner.className = `pf-kit-banner pf-kit-banner--${tone}`;
  banner.setAttribute("role", tone === "danger" ? "alert" : "status");

  const ico = doc.createElement("span");
  ico.className = "pf-kit-banner-icon";
  const defaultIcon: PfIconName =
    tone === "success"
      ? "check-circle"
      : tone === "warning"
        ? "alert-triangle"
        : tone === "danger"
          ? "alert-circle"
          : "info";
  setPfIcon(ico, opts.icon ?? defaultIcon, 15);
  banner.appendChild(ico);

  const msg = doc.createElement("span");
  msg.className = "pf-kit-banner-msg";
  msg.textContent = opts.message;
  banner.appendChild(msg);

  if (opts.actionLabel && opts.onAction) {
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "pf-kit-btn pf-kit-btn--ghost pf-kit-banner-action";
    btn.textContent = opts.actionLabel;
    btn.addEventListener("click", opts.onAction);
    banner.appendChild(btn);
  }

  parent.appendChild(banner);
  return banner;
}

export function renderEmptyState(
  parent: HTMLElement,
  opts: {
    icon?: PfIconName;
    title: string;
    subtitle?: string;
    actionLabel?: string;
    onAction?: () => void;
  }
): HTMLElement {
  const doc = parent.ownerDocument || document;
  const box = doc.createElement("div");
  box.className = "pf-kit-empty-state";
  applyElevation(box, "card");

  if (opts.icon) {
    const ico = doc.createElement("div");
    ico.className = "pf-kit-empty-icon";
    setPfIcon(ico, opts.icon, 20);
    box.appendChild(ico);
  }
  const titleEl = doc.createElement("div");
  titleEl.className = "pf-kit-empty-title";
  titleEl.textContent = opts.title;
  box.appendChild(titleEl);

  if (opts.subtitle) {
    const subEl = doc.createElement("div");
    subEl.className = "pf-kit-empty-sub";
    subEl.textContent = opts.subtitle;
    box.appendChild(subEl);
  }
  if (opts.actionLabel && opts.onAction) {
    const btn = doc.createElement("button");
    btn.type = "button";
    btn.className = "pf-kit-btn pf-kit-btn--primary";
    btn.textContent = opts.actionLabel;
    btn.addEventListener("click", opts.onAction);
    box.appendChild(btn);
  }

  parent.appendChild(box);
  return box;
}

export type KitBadgeTone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger";

export function renderBadge(
  parent: HTMLElement,
  text: string,
  tone: KitBadgeTone = "neutral"
): HTMLElement {
  const doc = parent.ownerDocument || document;
  const el = doc.createElement("span");
  el.className = `pf-kit-badge pf-kit-badge--${tone} pf-tnum`;
  el.textContent = text;
  parent.appendChild(el);
  return el;
}

/** Press-and-hold destructive confirmation button with smooth progress fill. */
export function renderHoldToConfirm(
  parent: HTMLElement,
  opts: {
    label: string;
    confirmedLabel?: string;
    durationMs?: number;
    tone?: "danger" | "accent";
    onConfirm: () => void;
  }
): HTMLButtonElement {
  const doc = parent.ownerDocument || document;
  const durationMs =
    opts.durationMs && opts.durationMs > 0 ? opts.durationMs : 900;
  const tone = opts.tone ?? "danger";

  const btn = doc.createElement("button");
  btn.type = "button";
  btn.className = `pf-kit-hold-btn pf-kit-hold-btn--${tone}`;

  const fill = doc.createElement("span");
  fill.className = "pf-kit-hold-fill";
  btn.appendChild(fill);

  const lbl = doc.createElement("span");
  lbl.className = "pf-kit-hold-label";
  lbl.textContent = opts.label;
  btn.appendChild(lbl);

  let rafId = 0;
  let resetTimer: ReturnType<typeof setTimeout> | undefined;
  let startAt = 0;
  let active = false;

  const cancelHold = () => {
    if (!active) return;
    active = false;
    if (rafId) cancelAnimationFrame(rafId);
    fill.style.width = "0%";
  };

  const step = () => {
    if (!active) return;
    const elapsed = Date.now() - startAt;
    const pct = Math.min(100, (elapsed / durationMs) * 100);
    fill.style.width = `${pct}%`;
    if (elapsed >= durationMs) {
      active = false;
      btn.classList.add("is-confirmed");
      lbl.textContent = opts.confirmedLabel || "已确认";
      opts.onConfirm();
      clearTimeout(resetTimer);
      resetTimer = setTimeout(() => {
        btn.classList.remove("is-confirmed");
        fill.style.width = "0%";
        lbl.textContent = opts.label;
      }, 1200);
      return;
    }
    rafId = requestAnimationFrame(step);
  };

  btn.addEventListener("mousedown", (ev) => {
    if (ev.button !== 0) return;
    active = true;
    startAt = Date.now();
    rafId = requestAnimationFrame(step);
  });
  btn.addEventListener("mouseup", cancelHold);
  btn.addEventListener("mouseleave", cancelHold);

  parent.appendChild(btn);
  return btn;
}
