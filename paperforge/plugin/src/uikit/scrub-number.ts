/**
 * Blender/Figma-style horizontal scrubbable numeric field with Shift 0.1x precision,
 * Ctrl/Cmd 5x boost, and click-to-edit exact numeric mode.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/scrub_number.go`.
 */

export interface ScrubNumberOptions {
  label: string;
  unit?: string;
  min?: number;
  max?: number;
  step?: number;
  decimals?: number;
  sensitivity?: number; // px per step (default 6)
  onChange?: (val: number) => void;
  onCommit?: (val: number) => void;
}

function clampScrub(v: number, minV?: number, maxV?: number): number {
  let out = v;
  if (minV !== undefined && out < minV) out = minV;
  if (maxV !== undefined && maxV > (minV ?? -Infinity) && out > maxV) {
    out = maxV;
  }
  return out;
}

function roundDecimals(v: number, decimals: number): number {
  if (decimals <= 0) return Math.round(v);
  const pow = 10 ** decimals;
  return Math.round(v * pow) / pow;
}

function formatScrub(v: number, decimals: number): string {
  return decimals <= 0 ? String(Math.round(v)) : v.toFixed(decimals);
}

export function renderScrubNumber(
  parent: HTMLElement,
  initialValue: number,
  opts: ScrubNumberOptions
): { el: HTMLElement; getValue: () => number; setValue: (v: number) => void } {
  const doc = parent.ownerDocument || document;
  const step = opts.step && opts.step > 0 ? opts.step : 1;
  const decimals = Math.max(0, opts.decimals ?? 1);
  const sensitivity =
    opts.sensitivity && opts.sensitivity > 0 ? opts.sensitivity : 6;

  let value = clampScrub(
    roundDecimals(initialValue, decimals),
    opts.min,
    opts.max
  );
  let mode: "idle" | "pointing" | "dragging" | "editing" = "idle";
  let downX = 0;
  let startVal = value;

  const host = doc.createElement("div");
  host.className = "pf-kit-scrub";

  const pill = doc.createElement("button");
  pill.type = "button";
  pill.className = "pf-kit-scrub-pill";
  pill.setAttribute(
    "aria-label",
    `${opts.label}: 拖拽横向微调数值（Shift 精细 / Ctrl 快速），点击精确输入`
  );

  const labelSpan = doc.createElement("span");
  labelSpan.className = "pf-kit-scrub-label";
  labelSpan.textContent = opts.label;
  pill.appendChild(labelSpan);

  const valWrap = doc.createElement("span");
  valWrap.className = "pf-kit-scrub-value-wrap pf-tnum";
  const valSpan = doc.createElement("span");
  valSpan.className = "pf-kit-scrub-value";
  valWrap.appendChild(valSpan);
  if (opts.unit) {
    const unitSpan = doc.createElement("span");
    unitSpan.className = "pf-kit-scrub-unit";
    unitSpan.textContent = ` ${opts.unit}`;
    valWrap.appendChild(unitSpan);
  }
  pill.appendChild(valWrap);
  host.appendChild(pill);

  const editInput = doc.createElement("input");
  editInput.type = "text";
  editInput.className = "pf-kit-scrub-input pf-tnum";
  editInput.style.display = "none";
  host.appendChild(editInput);

  const syncDisplay = () => {
    valSpan.textContent = formatScrub(value, decimals);
  };
  syncDisplay();

  const enterEdit = () => {
    mode = "editing";
    pill.style.display = "none";
    editInput.style.display = "";
    editInput.value = formatScrub(value, decimals);
    editInput.focus();
    editInput.select();
  };

  const exitEdit = (commit: boolean) => {
    if (mode !== "editing") return;
    if (commit) {
      const parsed = Number.parseFloat(editInput.value.trim());
      if (Number.isFinite(parsed)) {
        const next = clampScrub(
          roundDecimals(parsed, decimals),
          opts.min,
          opts.max
        );
        if (next !== value) {
          value = next;
          opts.onChange?.(value);
        }
        opts.onCommit?.(value);
      }
    }
    mode = "idle";
    editInput.style.display = "none";
    pill.style.display = "";
    syncDisplay();
  };

  const onWindowMove = (ev: MouseEvent) => {
    if (mode !== "pointing" && mode !== "dragging") return;
    const dx = ev.clientX - downX;
    if (mode === "pointing") {
      if (Math.abs(dx) < 3) return;
      mode = "dragging";
      host.classList.add("is-dragging");
    }
    const mult = ev.shiftKey ? 0.1 : ev.ctrlKey || ev.metaKey ? 5 : 1;
    const steps = (dx / sensitivity) * mult;
    const next = clampScrub(
      roundDecimals(startVal + steps * step, decimals),
      opts.min,
      opts.max
    );
    if (next !== value) {
      value = next;
      syncDisplay();
      opts.onChange?.(value);
    }
  };

  const onWindowUp = () => {
    doc.removeEventListener("mousemove", onWindowMove);
    doc.removeEventListener("mouseup", onWindowUp);
    host.classList.remove("is-dragging");
    if (mode === "dragging") {
      mode = "idle";
      opts.onCommit?.(value);
    } else if (mode === "pointing") {
      enterEdit();
    }
  };

  pill.addEventListener("mousedown", (ev) => {
    if (ev.button !== 0 || mode === "editing") return;
    mode = "pointing";
    downX = ev.clientX;
    startVal = value;
    doc.addEventListener("mousemove", onWindowMove);
    doc.addEventListener("mouseup", onWindowUp);
  });

  pill.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      enterEdit();
    } else if (ev.key === "ArrowRight" || ev.key === "ArrowUp") {
      ev.preventDefault();
      const mult = ev.shiftKey ? 0.1 : ev.ctrlKey || ev.metaKey ? 5 : 1;
      value = clampScrub(
        roundDecimals(value + step * mult, decimals),
        opts.min,
        opts.max
      );
      syncDisplay();
      opts.onChange?.(value);
      opts.onCommit?.(value);
    } else if (ev.key === "ArrowLeft" || ev.key === "ArrowDown") {
      ev.preventDefault();
      const mult = ev.shiftKey ? 0.1 : ev.ctrlKey || ev.metaKey ? 5 : 1;
      value = clampScrub(
        roundDecimals(value - step * mult, decimals),
        opts.min,
        opts.max
      );
      syncDisplay();
      opts.onChange?.(value);
      opts.onCommit?.(value);
    }
  });

  editInput.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      exitEdit(true);
    } else if (ev.key === "Escape") {
      ev.preventDefault();
      exitEdit(false);
    }
  });
  editInput.addEventListener("blur", () => exitEdit(true));

  parent.appendChild(host);
  return {
    el: host,
    getValue: () => value,
    setValue: (v: number) => {
      value = clampScrub(roundDecimals(v, decimals), opts.min, opts.max);
      syncDisplay();
    },
  };
}
