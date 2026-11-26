/**
 * Single-source CommandRegistry with `when`-clause gating and user shortcut overrides.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/commands.go`.
 */

import type { PfIconName } from "../views/icons";

export interface CommandContext {
  modalOpen?: boolean;
  textInputFocused?: boolean;
  activeView?:
    | "base"
    | "pdf"
    | "companion"
    | "ocr"
    | "settings"
    | "gallery"
    | "";
  hasSelection?: boolean;
  hasActivePaper?: boolean;
}

export interface CommandSpec {
  id: string;
  title: string;
  subtitle?: string;
  category: string;
  defaultShortcut?: string;
  icon?: PfIconName;
  when?: (ctx: CommandContext) => boolean;
  run: () => void;
}

export class CommandRegistry {
  private _specs: CommandSpec[] = [];
  private _byId = new Map<string, number>();
  private _overrides = new Map<string, string>();

  register(spec: CommandSpec): void {
    if (!spec.id) return;
    const existing = this._byId.get(spec.id);
    if (existing !== undefined) {
      this._specs[existing] = spec;
      return;
    }
    this._byId.set(spec.id, this._specs.length);
    this._specs.push(spec);
  }

  setOverrides(overrides: Record<string, string>): void {
    this._overrides.clear();
    for (const [k, v] of Object.entries(overrides)) {
      const clean = v.trim();
      if (clean) this._overrides.set(k, clean);
    }
  }

  shortcutFor(id: string): string {
    const ov = this._overrides.get(id);
    if (ov) return ov;
    const idx = this._byId.get(id);
    return idx !== undefined ? (this._specs[idx].defaultShortcut ?? "") : "";
  }

  canRun(spec: CommandSpec, ctx: CommandContext): boolean {
    return spec.when ? spec.when(ctx) : true;
  }

  search(query: string, ctx: CommandContext = {}): CommandSpec[] {
    const q = query.trim().toLowerCase();
    return this._specs.filter((spec) => {
      if (!this.canRun(spec, ctx)) return false;
      if (!q) return true;
      const haystack = [
        spec.id,
        spec.title,
        spec.subtitle ?? "",
        spec.category,
        this.shortcutFor(spec.id),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }

  all(): CommandSpec[] {
    return [...this._specs];
  }

  find(id: string): CommandSpec | undefined {
    const idx = this._byId.get(id);
    return idx !== undefined ? this._specs[idx] : undefined;
  }
}
