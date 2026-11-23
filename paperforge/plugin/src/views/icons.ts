/**
 * Crisp 1.65px stroke vector line icons (Lucide geometry, zero UI emojis).
 * Constructed purely via standard SVG DOM APIs so views work identically in
 * Obsidian, Vitest/JSDOM, and headless Chromium without Obsidian runtime mocks.
 */

export type PfIconName =
  | "panel-left"
  | "panel-right"
  | "chevron-left"
  | "chevron-right"
  | "chevron-down"
  | "search"
  | "x"
  | "more-horizontal"
  | "columns-2"
  | "refresh-cw"
  | "check"
  | "alert-triangle"
  | "sliders"
  | "external-link"
  | "folder"
  | "book-open"
  | "file-text"
  | "sparkles"
  | "highlighter"
  | "pen-tool"
  | "text-cursor"
  | "box-select"
  | "pencil"
  | "shapes"
  | "square"
  | "circle"
  | "arrow-up-right"
  | "minus"
  | "plus"
  | "maximize-2"
  | "type"
  | "sticky-note"
  | "trash-2"
  | "quote"
  | "layers"
  | "play"
  | "wrench"
  | "stethoscope"
  | "underline"
  | "strikethrough"
  | "copy"
  | "list"
  | "filter"
  | "arrow-up-down"
  | "settings"
  | "layout-grid";

interface IconNodeSpec {
  tag: "path" | "rect" | "circle" | "line" | "polyline" | "polygon";
  attrs: Record<string, string>;
}

const SVG_NS = "http://www.w3.org/2000/svg";

const ICON_PATHS: Record<PfIconName, IconNodeSpec[]> = {
  "panel-left": [
    {
      tag: "rect",
      attrs: { x: "3", y: "3", width: "18", height: "18", rx: "2" },
    },
    { tag: "path", attrs: { d: "M9 3v18" } },
  ],
  "panel-right": [
    {
      tag: "rect",
      attrs: { x: "3", y: "3", width: "18", height: "18", rx: "2" },
    },
    { tag: "path", attrs: { d: "M15 3v18" } },
  ],
  "chevron-left": [{ tag: "path", attrs: { d: "m15 18-6-6 6-6" } }],
  "chevron-right": [{ tag: "path", attrs: { d: "m9 18 6-6-6-6" } }],
  "chevron-down": [{ tag: "path", attrs: { d: "m6 9 6 6 6-6" } }],
  search: [
    { tag: "circle", attrs: { cx: "11", cy: "11", r: "8" } },
    { tag: "path", attrs: { d: "m21 21-4.3-4.3" } },
  ],
  x: [
    { tag: "path", attrs: { d: "M18 6 6 18" } },
    { tag: "path", attrs: { d: "m6 6 12 12" } },
  ],
  "more-horizontal": [
    { tag: "circle", attrs: { cx: "12", cy: "12", r: "1" } },
    { tag: "circle", attrs: { cx: "19", cy: "12", r: "1" } },
    { tag: "circle", attrs: { cx: "5", cy: "12", r: "1" } },
  ],
  "columns-2": [
    {
      tag: "rect",
      attrs: { x: "3", y: "3", width: "18", height: "18", rx: "2" },
    },
    { tag: "path", attrs: { d: "M12 3v18" } },
  ],
  "refresh-cw": [
    {
      tag: "path",
      attrs: { d: "M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" },
    },
    { tag: "path", attrs: { d: "M21 3v5h-5" } },
    {
      tag: "path",
      attrs: { d: "M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" },
    },
    { tag: "path", attrs: { d: "M8 16H3v5" } },
  ],
  check: [{ tag: "path", attrs: { d: "M20 6 9 17l-5-5" } }],
  "alert-triangle": [
    {
      tag: "path",
      attrs: {
        d: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z",
      },
    },
    { tag: "path", attrs: { d: "M12 9v4" } },
    { tag: "path", attrs: { d: "M12 17h.01" } },
  ],
  sliders: [
    { tag: "line", attrs: { x1: "4", x2: "4", y1: "21", y2: "14" } },
    { tag: "line", attrs: { x1: "4", x2: "4", y1: "10", y2: "3" } },
    { tag: "line", attrs: { x1: "12", x2: "12", y1: "21", y2: "12" } },
    { tag: "line", attrs: { x1: "12", x2: "12", y1: "8", y2: "3" } },
    { tag: "line", attrs: { x1: "20", x2: "20", y1: "21", y2: "16" } },
    { tag: "line", attrs: { x1: "20", x2: "20", y1: "12", y2: "3" } },
    { tag: "line", attrs: { x1: "2", x2: "6", y1: "14", y2: "14" } },
    { tag: "line", attrs: { x1: "10", x2: "14", y1: "8", y2: "8" } },
    { tag: "line", attrs: { x1: "18", x2: "22", y1: "16", y2: "16" } },
  ],
  "external-link": [
    { tag: "path", attrs: { d: "M15 3h6v6" } },
    { tag: "path", attrs: { d: "M10 14 21 3" } },
    {
      tag: "path",
      attrs: { d: "M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" },
    },
  ],
  folder: [
    {
      tag: "path",
      attrs: {
        d: "M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z",
      },
    },
  ],
  "book-open": [
    { tag: "path", attrs: { d: "M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" } },
    { tag: "path", attrs: { d: "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" } },
  ],
  "file-text": [
    {
      tag: "path",
      attrs: {
        d: "M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z",
      },
    },
    { tag: "path", attrs: { d: "M14 2v4a2 2 0 0 0 2 2h4" } },
    { tag: "path", attrs: { d: "M10 9H8" } },
    { tag: "path", attrs: { d: "M16 13H8" } },
    { tag: "path", attrs: { d: "M16 17H8" } },
  ],
  sparkles: [
    {
      tag: "path",
      attrs: {
        d: "m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z",
      },
    },
    { tag: "path", attrs: { d: "M5 3v4" } },
    { tag: "path", attrs: { d: "M19 17v4" } },
    { tag: "path", attrs: { d: "M3 5h4" } },
    { tag: "path", attrs: { d: "M17 19h4" } },
  ],
  highlighter: [
    { tag: "path", attrs: { d: "m9 11-6 6v3h9l3-3" } },
    {
      tag: "path",
      attrs: {
        d: "m22 12-4.6 4.6a2 2 0 0 1-2.8 0l-5.2-5.2a2 2 0 0 1 0-2.8L14 4",
      },
    },
  ],
  "pen-tool": [
    // macOS Preview style: marker nib enclosed inside crisp circle
    { tag: "circle", attrs: { cx: "12", cy: "12", r: "9.5" } },
    { tag: "path", attrs: { d: "m9 15 1.5-5.5 3.5-2.5 2.5 2.5-2.5 3.5Z" } },
    { tag: "path", attrs: { d: "M8.5 17.5h7" } },
  ],
  "text-cursor": [
    { tag: "path", attrs: { d: "M17 22h-1a4 4 0 0 1-4-4V6a4 4 0 0 1 4-4h1" } },
    { tag: "path", attrs: { d: "M7 22h1a4 4 0 0 0 4-4v-1" } },
    { tag: "path", attrs: { d: "M7 2h1a4 4 0 0 1 4 4v1" } },
  ],
  "box-select": [
    { tag: "path", attrs: { d: "M5 3a2 2 0 0 0-2 2" } },
    { tag: "path", attrs: { d: "M19 3a2 2 0 0 1 2 2" } },
    { tag: "path", attrs: { d: "M21 19a2 2 0 0 1-2 2" } },
    { tag: "path", attrs: { d: "M5 21a2 2 0 0 1-2-2" } },
    { tag: "path", attrs: { d: "M9 3h1" } },
    { tag: "path", attrs: { d: "M9 21h1" } },
    { tag: "path", attrs: { d: "M14 3h1" } },
    { tag: "path", attrs: { d: "M14 21h1" } },
    { tag: "path", attrs: { d: "M3 9v1" } },
    { tag: "path", attrs: { d: "M21 9v1" } },
    { tag: "path", attrs: { d: "M3 14v1" } },
    { tag: "path", attrs: { d: "M21 14v1" } },
  ],
  pencil: [
    {
      tag: "path",
      attrs: {
        d: "M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z",
      },
    },
    { tag: "path", attrs: { d: "m15 5 4 4" } },
  ],
  shapes: [
    {
      tag: "path",
      attrs: {
        d: "M8.3 10a.7.7 0 0 1-.626-1.079L11.4 3a.7.7 0 0 1 1.198-.043L16.3 8.9a.7.7 0 0 1-.572 1.1Z",
      },
    },
    {
      tag: "rect",
      attrs: { x: "3", y: "14", width: "7", height: "7", rx: "1" },
    },
    { tag: "circle", attrs: { cx: "17.5", cy: "17.5", r: "3.5" } },
  ],
  square: [
    {
      tag: "rect",
      attrs: { x: "4", y: "4", width: "16", height: "16", rx: "1.5" },
    },
  ],
  circle: [{ tag: "circle", attrs: { cx: "12", cy: "12", r: "8.5" } }],
  "arrow-up-right": [
    { tag: "path", attrs: { d: "M5 19 19 5" } },
    { tag: "path", attrs: { d: "M9 5h10v10" } },
  ],
  minus: [{ tag: "path", attrs: { d: "M5 12h14" } }],
  plus: [
    { tag: "path", attrs: { d: "M5 12h14" } },
    { tag: "path", attrs: { d: "M12 5v14" } },
  ],
  "maximize-2": [
    { tag: "polyline", attrs: { points: "15 3 21 3 21 9" } },
    { tag: "polyline", attrs: { points: "9 21 3 21 3 15" } },
    { tag: "line", attrs: { x1: "21", x2: "14", y1: "3", y2: "10" } },
    { tag: "line", attrs: { x1: "3", x2: "10", y1: "21", y2: "14" } },
  ],
  type: [
    { tag: "polyline", attrs: { points: "4 7 4 4 20 4 20 7" } },
    { tag: "line", attrs: { x1: "9", x2: "15", y1: "20", y2: "20" } },
    { tag: "line", attrs: { x1: "12", x2: "12", y1: "4", y2: "20" } },
  ],
  "sticky-note": [
    {
      tag: "path",
      attrs: {
        d: "M16 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8Z",
      },
    },
    { tag: "path", attrs: { d: "M15 3v4a2 2 0 0 0 2 2h4" } },
  ],
  "trash-2": [
    { tag: "path", attrs: { d: "M3 6h18" } },
    { tag: "path", attrs: { d: "M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" } },
    { tag: "path", attrs: { d: "M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" } },
    { tag: "line", attrs: { x1: "10", x2: "10", y1: "11", y2: "17" } },
    { tag: "line", attrs: { x1: "14", x2: "14", y1: "11", y2: "17" } },
  ],
  quote: [
    {
      tag: "path",
      attrs: {
        d: "M16 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z",
      },
    },
    {
      tag: "path",
      attrs: {
        d: "M5 3a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2 1 1 0 0 1 1 1v1a2 2 0 0 1-2 2 1 1 0 0 0-1 1v2a1 1 0 0 0 1 1 6 6 0 0 0 6-6V5a2 2 0 0 0-2-2z",
      },
    },
  ],
  layers: [
    {
      tag: "path",
      attrs: {
        d: "m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z",
      },
    },
    {
      tag: "path",
      attrs: { d: "m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65" },
    },
    {
      tag: "path",
      attrs: { d: "m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65" },
    },
  ],
  play: [{ tag: "polygon", attrs: { points: "6 3 20 12 6 21 6 3" } }],
  wrench: [
    {
      tag: "path",
      attrs: {
        d: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z",
      },
    },
  ],
  stethoscope: [
    { tag: "path", attrs: { d: "M11 2v2" } },
    { tag: "path", attrs: { d: "M5 2v2" } },
    {
      tag: "path",
      attrs: { d: "M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1" },
    },
    { tag: "path", attrs: { d: "M8 15a6 6 0 0 0 12 0v-3" } },
    { tag: "circle", attrs: { cx: "20", cy: "10", r: "2" } },
  ],
  underline: [
    { tag: "path", attrs: { d: "M6 4v6a6 6 0 0 0 12 0V4" } },
    { tag: "line", attrs: { x1: "4", x2: "20", y1: "20", y2: "20" } },
  ],
  strikethrough: [
    { tag: "path", attrs: { d: "M16 4H9a3 3 0 0 0-2.83 4" } },
    { tag: "path", attrs: { d: "M14 12a4 4 0 0 1 0 8H6" } },
    { tag: "line", attrs: { x1: "4", x2: "20", y1: "12", y2: "12" } },
  ],
  copy: [
    {
      tag: "rect",
      attrs: { width: "14", height: "14", x: "8", y: "8", rx: "2", ry: "2" },
    },
    {
      tag: "path",
      attrs: { d: "M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" },
    },
  ],
  list: [
    { tag: "line", attrs: { x1: "8", x2: "21", y1: "6", y2: "6" } },
    { tag: "line", attrs: { x1: "8", x2: "21", y1: "12", y2: "12" } },
    { tag: "line", attrs: { x1: "8", x2: "21", y1: "18", y2: "18" } },
    { tag: "line", attrs: { x1: "3", x2: "3.01", y1: "6", y2: "6" } },
    { tag: "line", attrs: { x1: "3", x2: "3.01", y1: "12", y2: "12" } },
    { tag: "line", attrs: { x1: "3", x2: "3.01", y1: "18", y2: "18" } },
  ],
  filter: [
    {
      tag: "polygon",
      attrs: { points: "22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" },
    },
  ],
  "arrow-up-down": [
    { tag: "path", attrs: { d: "m21 16-4 4-4-4" } },
    { tag: "path", attrs: { d: "M17 20V4" } },
    { tag: "path", attrs: { d: "m3 8 4-4 4 4" } },
    { tag: "path", attrs: { d: "M7 4v16" } },
  ],
  settings: [
    {
      tag: "path",
      attrs: {
        d: "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z",
      },
    },
    { tag: "circle", attrs: { cx: "12", cy: "12", r: "3" } },
  ],
  "layout-grid": [
    {
      tag: "rect",
      attrs: { width: "7", height: "7", x: "3", y: "3", rx: "1" },
    },
    {
      tag: "rect",
      attrs: { width: "7", height: "7", x: "14", y: "3", rx: "1" },
    },
    {
      tag: "rect",
      attrs: { width: "7", height: "7", x: "14", y: "14", rx: "1" },
    },
    {
      tag: "rect",
      attrs: { width: "7", height: "7", x: "3", y: "14", rx: "1" },
    },
  ],
};

const SVG_TEMPLATE_CACHE = new WeakMap<Document, Map<string, SVGSVGElement>>();

function getIconTemplate(
  doc: Document,
  name: PfIconName,
  size: number
): SVGSVGElement {
  let docMap = SVG_TEMPLATE_CACHE.get(doc);
  if (!docMap) {
    docMap = new Map();
    SVG_TEMPLATE_CACHE.set(doc, docMap);
  }
  const cacheKey = `${name}:${size}`;
  let cached = docMap.get(cacheKey);
  if (cached) return cached;

  const svg = doc.createElementNS(SVG_NS, "svg") as SVGSVGElement;
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", String(size));
  svg.setAttribute("height", String(size));
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.65");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("pf-svg-icon", `pf-icon-${name}`);
  const specs = ICON_PATHS[name] ?? [];
  for (const spec of specs) {
    const node = doc.createElementNS(SVG_NS, spec.tag);
    for (const [k, v] of Object.entries(spec.attrs)) {
      node.setAttribute(k, v);
    }
    svg.appendChild(node);
  }
  docMap.set(cacheKey, svg);
  return svg;
}

/** Render a crisp single-color Lucide SVG icon inside `el` (cached cloneNode for high-FPS tables). */
export function setPfIcon(
  el: HTMLElement,
  name: PfIconName,
  size = 15
): SVGSVGElement {
  const doc = el.ownerDocument || document;
  el.textContent = "";
  const svg = getIconTemplate(doc, name, size).cloneNode(true) as SVGSVGElement;
  el.appendChild(svg);
  return svg;
}

/** Create an accessible 28px AsterLab/Preview line-icon button. */
export function createPfIconBtn(
  parent: HTMLElement,
  opts: {
    icon: PfIconName;
    label: string;
    size?: number;
    cls?: string;
    testid?: string;
    active?: boolean;
  }
): HTMLButtonElement {
  const doc = parent.ownerDocument || document;
  const btn = doc.createElement("button");
  btn.type = "button";
  btn.className = ["pf-icon-btn", opts.cls ?? ""].filter(Boolean).join(" ");
  if (opts.active) btn.classList.add("is-active");
  btn.setAttribute("aria-label", opts.label);
  btn.title = opts.label;
  if (opts.testid) btn.setAttribute("data-pf-testid", opts.testid);
  setPfIcon(btn, opts.icon, opts.size ?? 15);
  parent.appendChild(btn);
  return btn;
}
