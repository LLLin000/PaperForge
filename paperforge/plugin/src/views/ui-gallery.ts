/**
 * PaperForgeGalleryView — In-Obsidian full interactive Design System &
 * UI Component Gallery leaf (`Ctrl/Cmd+P` -> "Open UI Gallery & Design System").
 */

import { ItemView, WorkspaceLeaf } from "obsidian";
import { VIEW_TYPE_UI_GALLERY } from "../constants";
import { t } from "../i18n";
import { PaperForgeGalleryController } from "../uikit/gallery";
import { setPfIcon } from "./icons";

export interface GalleryPluginHost {
  settings?: {
    ui_theme_mode?: string;
    ui_density?: string;
    ui_liquid_glass?: boolean;
    reduce_motion?: boolean;
  };
}

export class PaperForgeGalleryView extends ItemView {
  private readonly _plugin: GalleryPluginHost;
  private _controller: PaperForgeGalleryController | null = null;

  constructor(leaf: WorkspaceLeaf, plugin: GalleryPluginHost) {
    super(leaf);
    this._plugin = plugin;
  }

  static async open(plugin: {
    app: {
      workspace: {
        getLeavesOfType: (t: string) => WorkspaceLeaf[];
        getLeaf: (
          newLeaf?: boolean | "tab" | "split" | "window"
        ) => WorkspaceLeaf;
        revealLeaf: (leaf: WorkspaceLeaf) => Promise<void> | void;
      };
    };
  }): Promise<PaperForgeGalleryView | null> {
    const existing = plugin.app.workspace.getLeavesOfType(VIEW_TYPE_UI_GALLERY);
    if (existing.length > 0) {
      await plugin.app.workspace.revealLeaf(existing[0]);
      const view = existing[0].view;
      return view instanceof PaperForgeGalleryView ? view : null;
    }
    const leaf = plugin.app.workspace.getLeaf("tab");
    await leaf.setViewState({ type: VIEW_TYPE_UI_GALLERY, active: true });
    await plugin.app.workspace.revealLeaf(leaf);
    return leaf.view instanceof PaperForgeGalleryView ? leaf.view : null;
  }

  getViewType(): string {
    return VIEW_TYPE_UI_GALLERY;
  }

  getDisplayText(): string {
    return t("gallery_tab_title") || "UI Design Gallery";
  }

  getIcon(): string {
    return "palette";
  }

  async onOpen(): Promise<void> {
    const { contentEl } = this;
    contentEl.empty();
    contentEl.addClass("pf-gallery-view-host");

    const rawPreset = this._plugin?.settings?.ui_theme_mode;
    const preset =
      rawPreset === "asterlab"
        ? "asterlab"
        : rawPreset === "zinc"
          ? "zinc"
          : rawPreset === "warm"
            ? "warm"
            : "obsidian";
    const rawDensity = this._plugin?.settings?.ui_density;
    const density =
      rawDensity === "compact"
        ? "compact"
        : rawDensity === "comfortable"
          ? "comfortable"
          : "default";

    const isDarkDoc =
      typeof document !== "undefined" &&
      document.body?.classList?.contains("theme-dark");

    this._controller = new PaperForgeGalleryController(contentEl, {
      preset,
      mode: isDarkDoc ? "dark" : "light",
      density,
      liquidGlass: this._plugin?.settings?.ui_liquid_glass !== false,
      reduceMotion: this._plugin?.settings?.reduce_motion === true,
    });
    await this._controller.mount();

    const headerIcon = this.containerEl?.querySelector?.(
      ".view-header-icon"
    ) as HTMLElement | null;
    if (headerIcon) {
      setPfIcon(headerIcon, "palette");
    }
  }

  async onClose(): Promise<void> {
    this._controller?.destroy();
    this._controller = null;
    this.contentEl.empty();
  }
}
