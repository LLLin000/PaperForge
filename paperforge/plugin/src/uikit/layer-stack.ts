/**
 * Ordered overlay LayerStack so Escape strictly dismisses ONLY the topmost active overlay.
 * Mirrors `cellplanner-replica/prototypes/mygo-run/internal/uikit/kit/layer_stack.go`.
 */

export interface LayerEntry {
  id: string;
  onDismiss: () => void;
}

export class LayerStack {
  private _entries: LayerEntry[] = [];

  register(id: string, onDismiss: () => void): void {
    if (!id) return;
    const idx = this._entries.findIndex((e) => e.id === id);
    if (idx >= 0) {
      this._entries.splice(idx, 1);
    }
    this._entries.push({ id, onDismiss });
  }

  unregister(id: string): void {
    const idx = this._entries.findIndex((e) => e.id === id);
    if (idx >= 0) {
      this._entries.splice(idx, 1);
    }
  }

  hasOpen(): boolean {
    return this._entries.length > 0;
  }

  topId(): string | null {
    return this._entries.length > 0
      ? this._entries[this._entries.length - 1].id
      : null;
  }

  dismissTop(): boolean {
    if (this._entries.length === 0) return false;
    const top = this._entries.pop()!;
    top.onDismiss();
    return true;
  }

  handleKeyDown(ev: KeyboardEvent): boolean {
    if (ev.key !== "Escape" || this._entries.length === 0) return false;
    ev.preventDefault();
    ev.stopPropagation();
    return this.dismissTop();
  }

  clear(): void {
    this._entries = [];
  }
}
