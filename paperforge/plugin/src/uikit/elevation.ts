/**
 * 5-tier Elevation surface hierarchy (Canvas -> Surface -> Card -> Floating -> Modal).
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/elevation.go`.
 */

export type ElevationTier =
  | "canvas"
  | "surface"
  | "card"
  | "floating"
  | "modal";

const ELEVATION_CLASSES: readonly string[] = [
  "pf-elev-canvas",
  "pf-elev-surface",
  "pf-elev-card",
  "pf-elev-floating",
  "pf-elev-modal",
];

/** Apply one semantic elevation tier (surface fill, hairline, shadow, dark specular top highlight). */
export function applyElevation<T extends HTMLElement>(
  el: T,
  tier: ElevationTier
): T {
  for (const cls of ELEVATION_CLASSES) {
    el.classList.remove(cls);
  }
  el.classList.add(`pf-elev-${tier}`);
  return el;
}

/** Attach keyboard `:focus-visible` accent ring styling to an element. */
export function applyFocusRing<T extends HTMLElement>(el: T): T {
  el.classList.add("pf-focus-ring");
  return el;
}
