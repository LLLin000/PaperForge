/**
 * AsterLab / PaperForge Design System Tokens & Scoped Theme Engine.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/theme/`.
 */

export type UiThemePreset = "obsidian" | "asterlab" | "zinc" | "warm";
export type UiColorMode = "follow" | "light" | "dark";
export type UiDensity = "compact" | "default" | "comfortable";

export interface UiThemeTokens {
  preset: UiThemePreset;
  dark: boolean;
  density: UiDensity;
  liquidGlass: boolean;
  canvas: string;
  surface: string;
  elevated: string;
  rail: string;
  hover: string;
  selectedRow: string;
  border: string;
  borderStrong: string;
  borderSubtle: string;
  text: string;
  textMuted: string;
  textSubtle: string;
  accent: string;
  accentHover: string;
  accentText: string;
  accentSoft: string;
  success: string;
  warning: string;
  danger: string;
  spacing: {
    s4: number;
    s8: number;
    s12: number;
    s16: number;
    s24: number;
    s32: number;
    s48: number;
  };
  typography: {
    page: number;
    section: number;
    body: number;
    data: number;
    meta: number;
  };
  controlHeight: number;
  rowHeight: number;
  radii: {
    control: number;
    panel: number;
    dialog: number;
  };
}

export const MOTION_TOKENS = {
  instant: {
    durationMs: 60,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    label: "MotionInstant · 60ms",
  },
  micro: {
    durationMs: 100,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    label: "MotionMicro · 100ms (:active 0.97)",
  },
  snappy: {
    durationMs: 160,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    label: "MotionSnappy · 160ms exponential",
  },
  fluid: {
    durationMs: 220,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    label: "MotionFluid · 220ms exponential",
  },
  hero: {
    durationMs: 260,
    easing: "cubic-bezier(0.22, 1, 0.36, 1)",
    label: "MotionHero · 260ms spatial",
  },
} as const;

const CATEGORICAL_LIGHT = [
  "#3b6fd8",
  "#2f7a4f",
  "#c47f17",
  "#7a49c4",
  "#c94a5a",
  "#1b8a88",
  "#5d6bb8",
  "#9e6235",
] as const;

const CATEGORICAL_DARK = [
  "#78a5ff",
  "#74cfa3",
  "#e2b96f",
  "#b8a5ff",
  "#f08e96",
  "#5bd0cb",
  "#9aa7f0",
  "#d99b6a",
] as const;

/** Return the 8-color accessible categorical group ladder for Light or Dark mode. */
export function categoricalPalette(dark: boolean): readonly string[] {
  return dark ? CATEGORICAL_DARK : CATEGORICAL_LIGHT;
}

export function normalizePreset(raw?: string): UiThemePreset {
  if (raw === "asterlab" || raw === "zinc" || raw === "warm") return raw;
  return "obsidian";
}

export function normalizeDensity(raw?: string): UiDensity {
  if (raw === "compact" || raw === "comfortable") return raw;
  return "default";
}

/** Resolve explicit semantic token values matching `internal/theme/theme.go`. */
export function tokensFor(
  preset: UiThemePreset,
  dark: boolean,
  density: UiDensity = "default",
  liquidGlass = false
): UiThemeTokens {
  const normPreset = normalizePreset(preset);
  const normDensity = normalizeDensity(density);

  const spacing =
    normDensity === "compact"
      ? { s4: 4, s8: 6, s12: 9, s16: 12, s24: 18, s32: 26, s48: 40 }
      : normDensity === "comfortable"
        ? { s4: 4, s8: 8, s12: 14, s16: 18, s24: 28, s32: 36, s48: 52 }
        : { s4: 4, s8: 8, s12: 12, s16: 16, s24: 24, s32: 32, s48: 48 };

  const controlHeight =
    normDensity === "compact" ? 28 : normDensity === "comfortable" ? 34 : 30;
  const rowHeight =
    normDensity === "compact" ? 30 : normDensity === "comfortable" ? 38 : 32;

  let palette: Omit<
    UiThemeTokens,
    | "preset"
    | "dark"
    | "density"
    | "liquidGlass"
    | "spacing"
    | "typography"
    | "controlHeight"
    | "rowHeight"
    | "radii"
  >;

  if (normPreset === "warm") {
    palette = dark
      ? {
          canvas: "#171614",
          surface: "#1e1d1a",
          elevated: "#242320",
          rail: "#171614",
          hover: "#2b2925",
          selectedRow: "#2c2a25",
          border: "#37352f",
          borderStrong: "#4a473f",
          borderSubtle: "rgba(255, 255, 255, 0.08)",
          text: "#f2efe9",
          textMuted: "#a9a49a",
          textSubtle: "#78736a",
          accent: "#a996ff",
          accentHover: "#bcabff",
          accentText: "#1b1533",
          accentSoft: "rgba(169, 150, 255, 0.14)",
          success: "#84c9a4",
          warning: "#d9b878",
          danger: "#e79a9c",
        }
      : {
          canvas: "#f7f6f3",
          surface: "#ffffff",
          elevated: "#faf9f7",
          rail: "#f1efea",
          hover: "#efece6",
          selectedRow: "#edeae3",
          border: "#e7e3db",
          borderStrong: "#d6d0c5",
          borderSubtle: "rgba(28, 27, 24, 0.08)",
          text: "#1c1b18",
          textMuted: "#5f5a52",
          textSubtle: "#8f897f",
          accent: "#5b45c9",
          accentHover: "#4b37ae",
          accentText: "#ffffff",
          accentSoft: "rgba(91, 69, 201, 0.10)",
          success: "#2f7a4f",
          warning: "#7a6233",
          danger: "#a3373a",
        };
  } else if (normPreset === "zinc") {
    palette = dark
      ? {
          canvas: "#0f1115",
          surface: "#16181e",
          elevated: "#1e2129",
          rail: "#0c0d10",
          hover: "#262a34",
          selectedRow: "#262a34",
          border: "#262a35",
          borderStrong: "#383e4d",
          borderSubtle: "rgba(255, 255, 255, 0.08)",
          text: "#f3f4f6",
          textMuted: "#9ca3af",
          textSubtle: "#6b7280",
          accent: "#a397ff",
          accentHover: "#b8aeff",
          accentText: "#131026",
          accentSoft: "rgba(163, 151, 255, 0.16)",
          success: "#74cfa3",
          warning: "#e2b96f",
          danger: "#ed939b",
        }
      : {
          canvas: "#f4f5f7",
          surface: "#ffffff",
          elevated: "#eceef2",
          rail: "#eff1f4",
          hover: "#e5e7ec",
          selectedRow: "#e5e7ec",
          border: "#e2e5ec",
          borderStrong: "#cbd0da",
          borderSubtle: "rgba(17, 24, 39, 0.07)",
          text: "#111827",
          textMuted: "#5c6370",
          textSubtle: "#8b93a1",
          accent: "#635bff",
          accentHover: "#5046e5",
          accentText: "#ffffff",
          accentSoft: "#eeecff",
          success: "#18794e",
          warning: "#8c6115",
          danger: "#c03641",
        };
  } else {
    // obsidian & asterlab share the pure editorial palette when evaluated explicitly
    palette = dark
      ? {
          canvas: "#111215",
          surface: "#16181d",
          elevated: "#1e2027",
          rail: "#111215",
          hover: "#252831",
          selectedRow: "#272a33",
          border: "#2b2e38",
          borderStrong: "#3d4250",
          borderSubtle: "rgba(255, 255, 255, 0.08)",
          text: "#f3f4f8",
          textMuted: "#a6adbd",
          textSubtle: "#737a8c",
          accent: "#a596ff",
          accentHover: "#b8acff",
          accentText: "#161229",
          accentSoft: "#2a2645",
          success: "#84c9a4",
          warning: "#d9b878",
          danger: "#e79a9c",
        }
      : {
          canvas: "#ffffff",
          surface: "#ffffff",
          elevated: "#f5f6f8",
          rail: "#f5f6f8",
          hover: "#ededf0",
          selectedRow: "#ededf0",
          border: "#e5e7ec",
          borderStrong: "#cfd4de",
          borderSubtle: "rgba(20, 21, 26, 0.07)",
          text: "#14151a",
          textMuted: "#525766",
          textSubtle: "#848b9c",
          accent: "#6c5ce7",
          accentHover: "#5848d6",
          accentText: "#ffffff",
          accentSoft: "#eeebff",
          success: "#2f7a4f",
          warning: "#7a6233",
          danger: "#c4383b",
        };
  }

  return {
    preset: normPreset,
    dark,
    density: normDensity,
    liquidGlass,
    ...palette,
    spacing,
    typography: {
      page: 22,
      section: 15,
      body: 13.5,
      data: 13,
      meta: 12,
    },
    controlHeight,
    rowHeight,
    radii: {
      control: 6,
      panel: 10,
      dialog: 12,
    },
  };
}

/** Trigger one crisp +/-5px attention shake (ApplyNudge). */
export function applyNudge(el: HTMLElement): void {
  el.classList.remove("pf-nudge");
  // Force style flush so repeated clicks replay cleanly.
  void el.offsetWidth;
  el.classList.add("pf-nudge");
}

export interface ThemeScopeOptions {
  preset: UiThemePreset;
  mode: UiColorMode;
  density: UiDensity;
  liquidGlass: boolean;
  reduceMotion: boolean;
  hostDark?: boolean;
}

/**
 * Scope theme, color scheme, density, material, and reduced-motion classes onto
 * a container element (used by UI Gallery previews without mutating `document.body`).
 */
export function applyThemeScope(
  el: HTMLElement,
  opts: ThemeScopeOptions
): boolean {
  const hostDark =
    opts.hostDark ??
    (typeof document !== "undefined" &&
      document.documentElement.classList.contains("theme-dark"));
  const resolvedDark =
    opts.mode === "dark" ? true : opts.mode === "light" ? false : hostDark;

  el.classList.toggle("pf-scope-dark", resolvedDark);
  el.classList.toggle("pf-scope-light", !resolvedDark);
  el.classList.toggle("theme-dark", resolvedDark);
  el.classList.toggle("theme-light", !resolvedDark);

  el.classList.toggle("pf-scope-obsidian", opts.preset === "obsidian");
  el.classList.toggle("pf-scope-asterlab", opts.preset === "asterlab");
  el.classList.toggle("pf-scope-zinc", opts.preset === "zinc");
  el.classList.toggle("pf-scope-warm", opts.preset === "warm");

  el.classList.toggle("pf-density-compact", opts.density === "compact");
  el.classList.toggle("pf-density-default", opts.density === "default");
  el.classList.toggle("pf-density-comfortable", opts.density === "comfortable");

  el.classList.toggle("pf-no-glass", !opts.liquidGlass);
  el.classList.toggle("pf-reduce-motion", opts.reduceMotion);

  return resolvedDark;
}
