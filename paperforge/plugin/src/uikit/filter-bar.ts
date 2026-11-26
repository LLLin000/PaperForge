/**
 * Composable Twenty/Plane-style FilterBar engine: search + saved views +
 * multi-condition popover + removable active condition pills.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/filter_bar.go`.
 */

import { setPfIcon } from "../views/icons";
import { applyElevation } from "./elevation";
import type { LayerStack } from "./layer-stack";
import { renderListItem } from "./primitives";

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterField {
  key: string;
  label: string;
  options: FilterOption[];
}

export interface ActiveFilter {
  fieldKey: string;
  value: string;
}

export interface SavedFilterView {
  id: string;
  label: string;
  filters: ActiveFilter[];
}

export class FilterBarState {
  query = "";
  active: ActiveFilter[] = [];
  savedViewId = "";
  pickerOpen = false;
  pickerField = "";

  hasFilter(fieldKey: string, value: string): boolean {
    return this.active.some(
      (f) => f.fieldKey === fieldKey && f.value === value
    );
  }

  toggleFilter(fieldKey: string, value: string): void {
    this.savedViewId = "";
    const idx = this.active.findIndex(
      (f) => f.fieldKey === fieldKey && f.value === value
    );
    if (idx >= 0) {
      this.active.splice(idx, 1);
      return;
    }
    this.active.push({ fieldKey, value });
  }

  clearFilters(): void {
    this.active = [];
    this.savedViewId = "";
  }

  applySavedView(view: SavedFilterView): void {
    this.savedViewId = view.id;
    this.active = view.filters.map((f) => ({ ...f }));
  }
}

export interface RenderFilterBarOptions {
  state: FilterBarState;
  fields: FilterField[];
  savedViews?: SavedFilterView[];
  searchPlaceholder?: string;
  layerStack?: LayerStack;
  onChange?: () => void;
}

function resolveLabels(
  fields: FilterField[],
  filter: ActiveFilter
): { fieldLabel: string; optLabel: string } {
  const fd = fields.find((f) => f.key === filter.fieldKey);
  if (!fd) return { fieldLabel: filter.fieldKey, optLabel: filter.value };
  const opt = fd.options.find((o) => o.value === filter.value);
  return {
    fieldLabel: fd.label,
    optLabel: opt ? opt.label : filter.value,
  };
}

export function renderFilterBar(
  parent: HTMLElement,
  opts: RenderFilterBarOptions
): HTMLElement {
  const doc = parent.ownerDocument || document;
  const st = opts.state;
  const savedViews = opts.savedViews ?? [];

  const root = doc.createElement("div");
  root.className = "pf-kit-filterbar";

  const mainRow = doc.createElement("div");
  mainRow.className = "pf-kit-filterbar-main";
  applyElevation(mainRow, "surface");

  const searchWrap = doc.createElement("div");
  searchWrap.className = "pf-kit-filterbar-search";
  const searchIco = doc.createElement("span");
  searchIco.className = "pf-kit-filterbar-search-icon";
  setPfIcon(searchIco, "search", 14);
  searchWrap.appendChild(searchIco);

  const searchInput = doc.createElement("input");
  searchInput.type = "search";
  searchInput.className = "pf-kit-filterbar-input";
  searchInput.value = st.query;
  searchInput.placeholder = opts.searchPlaceholder ?? "搜索或筛选条件…";
  searchInput.addEventListener("input", () => {
    st.query = searchInput.value;
    opts.onChange?.();
  });
  searchInput.addEventListener("keydown", (ev) => {
    if (
      ev.key === "Backspace" &&
      searchInput.value === "" &&
      st.active.length > 0
    ) {
      st.active.pop();
      st.savedViewId = "";
      opts.onChange?.();
    }
  });
  searchWrap.appendChild(searchInput);
  mainRow.appendChild(searchWrap);

  if (savedViews.length > 0) {
    const sep = doc.createElement("span");
    sep.className = "pf-kit-filterbar-sep";
    mainRow.appendChild(sep);

    const viewsRow = doc.createElement("div");
    viewsRow.className = "pf-kit-filterbar-views";
    for (const sv of savedViews) {
      const isDefaultEmpty =
        !st.savedViewId && sv.filters.length === 0 && st.active.length === 0;
      const active = st.savedViewId === sv.id || isDefaultEmpty;
      const btn = doc.createElement("button");
      btn.type = "button";
      btn.className = `pf-kit-btn ${active ? "pf-kit-btn--toolbar is-active" : "pf-kit-btn--ghost"} pf-tnum`;
      btn.textContent = sv.label;
      btn.addEventListener("click", () => {
        st.applySavedView(sv);
        st.pickerOpen = false;
        opts.onChange?.();
      });
      viewsRow.appendChild(btn);
    }
    mainRow.appendChild(viewsRow);
  }

  if (opts.fields.length > 0) {
    const pickerWrap = doc.createElement("div");
    pickerWrap.className = "pf-kit-filterbar-picker-wrap";

    const addBtn = doc.createElement("button");
    addBtn.type = "button";
    addBtn.className = "pf-kit-btn pf-kit-btn--secondary";
    addBtn.textContent = "+ 筛选";
    addBtn.setAttribute("aria-expanded", String(st.pickerOpen));
    addBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      st.pickerOpen = !st.pickerOpen;
      if (st.pickerOpen && !st.pickerField) {
        st.pickerField = opts.fields[0].key;
      }
      if (st.pickerOpen) {
        opts.layerStack?.register("pf-kit-filterbar-picker", () => {
          st.pickerOpen = false;
          opts.onChange?.();
        });
      } else {
        opts.layerStack?.unregister("pf-kit-filterbar-picker");
      }
      opts.onChange?.();
    });
    pickerWrap.appendChild(addBtn);

    if (st.pickerOpen) {
      const popover = doc.createElement("div");
      popover.className = "pf-kit-filterbar-popover";
      applyElevation(popover, "floating");

      const popTitle = doc.createElement("div");
      popTitle.className = "pf-kit-filterbar-pop-title";
      popTitle.textContent = "组合条件筛选";
      popover.appendChild(popTitle);

      const fieldTabs = doc.createElement("div");
      fieldTabs.className = "pf-kit-filterbar-field-tabs";
      for (const fd of opts.fields) {
        const ftBtn = doc.createElement("button");
        ftBtn.type = "button";
        const on = st.pickerField === fd.key;
        ftBtn.className = `pf-kit-btn ${on ? "pf-kit-btn--toolbar is-active" : "pf-kit-btn--ghost"}`;
        ftBtn.textContent = fd.label;
        ftBtn.addEventListener("click", (ev) => {
          ev.stopPropagation();
          st.pickerField = fd.key;
          opts.onChange?.();
        });
        fieldTabs.appendChild(ftBtn);
      }
      popover.appendChild(fieldTabs);

      const optList = doc.createElement("div");
      optList.className = "pf-kit-filterbar-opt-list";
      const curField =
        opts.fields.find((f) => f.key === st.pickerField) ?? opts.fields[0];
      for (const opt of curField.options) {
        const selected = st.hasFilter(curField.key, opt.value);
        renderListItem(optList, {
          title: opt.label,
          selected,
          compact: true,
          renderStart: (slot) => {
            setPfIcon(slot, selected ? "check-circle" : "circle", 14);
          },
          onClick: () => {
            st.toggleFilter(curField.key, opt.value);
            opts.onChange?.();
          },
        });
      }
      popover.appendChild(optList);
      pickerWrap.appendChild(popover);
      const win = doc.defaultView || window;
      const checkFlip = () => {
        if (typeof popover.getBoundingClientRect !== "function") return;
        const rect = popover.getBoundingClientRect();
        const vh = win.innerHeight || 900;
        if (
          rect.height > 0 &&
          rect.bottom > vh - 8 &&
          rect.top > rect.height + 16
        ) {
          popover.classList.add("is-flipped-up");
        }
      };
      if (typeof win.requestAnimationFrame === "function") {
        win.requestAnimationFrame(checkFlip);
      } else {
        checkFlip();
      }
    }

    mainRow.appendChild(pickerWrap);
  }

  root.appendChild(mainRow);

  if (st.active.length > 0 || st.query.trim()) {
    const pillsRow = doc.createElement("div");
    pillsRow.className = "pf-kit-filterbar-pills";
    for (const f of st.active) {
      const { fieldLabel, optLabel } = resolveLabels(opts.fields, f);
      const pill = doc.createElement("button");
      pill.type = "button";
      pill.className = "pf-kit-filterbar-pill";
      pill.title = "点击移除筛选条件";

      const txt = doc.createElement("span");
      txt.textContent = `${fieldLabel}: ${optLabel}`;
      pill.appendChild(txt);

      const x = doc.createElement("span");
      x.className = "pf-kit-filterbar-pill-x";
      setPfIcon(x, "x", 12);
      pill.appendChild(x);

      pill.addEventListener("click", () => {
        st.toggleFilter(f.fieldKey, f.value);
        opts.onChange?.();
      });
      pillsRow.appendChild(pill);
    }

    const clearBtn = doc.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "pf-kit-btn pf-kit-btn--ghost pf-kit-filterbar-clear";
    clearBtn.textContent = "清空筛选";
    clearBtn.addEventListener("click", () => {
      st.query = "";
      st.clearFilters();
      opts.onChange?.();
    });
    pillsRow.appendChild(clearBtn);
    root.appendChild(pillsRow);
  }

  parent.appendChild(root);
  return root;
}
