import { Notice } from "obsidian";
import * as obsidian from "obsidian";
import { t } from "../i18n";

export interface SafeOpenVaultFileOptions {
  filePath?: string | null;
  zoteroKey?: string | null;
  mod?: boolean | "tab" | "split" | "window";
  preferRootLeaf?: boolean;
  missingNotice?: string;
}

/**
 * Safely open an existing vault note or asset without calling `openLinkText` on
 * non-existent paths (which creates 0-byte phantom files or fails on OS paths).
 * When a path is stale or points to a 0-byte stub and `zoteroKey` is provided,
 * recovers by scanning `getMarkdownFiles()` for a non-empty matching note.
 */
export async function openVaultFileSafely(
  app: unknown,
  opts: SafeOpenVaultFileOptions
): Promise<boolean> {
  const appObj = app as {
    vault?: {
      getAbstractFileByPath?: (p: string) => {
        path?: string;
        basename?: string;
        extension?: string;
        stat?: { size?: number };
      } | null;
      getMarkdownFiles?: () => Array<{
        path: string;
        basename?: string;
        extension?: string;
        stat?: { size?: number };
      }>;
    };
    workspace?: {
      getLeaf?: (newLeaf?: boolean | "tab" | "split" | "window") => {
        openFile?: (f: unknown) => Promise<void>;
      } | null;
      getMostRecentLeaf?: () => {
        openFile?: (f: unknown) => Promise<void>;
      } | null;
      revealLeaf?: (leaf: unknown) => Promise<void> | void;
      setActiveLeaf?: (leaf: unknown, opts?: { focus?: boolean }) => void;
      openLinkText?: (
        linktext: string,
        sourcePath: string,
        newLeaf?: boolean | "tab" | "split" | "window"
      ) => Promise<void> | void;
    };
  } | null;

  const rawPath = String(opts.filePath ?? "");
  const normPath = rawPath.replace(/\\/g, "/").trim();
  const zoteroKey = String(opts.zoteroKey ?? "").trim();

  const callOpenLink = async (pathToOpen: string): Promise<void> => {
    const ws = appObj?.workspace;
    if (typeof ws?.openLinkText !== "function") return;
    if (opts.mod !== undefined) {
      await ws.openLinkText(pathToOpen, "", opts.mod);
    } else {
      await ws.openLinkText(pathToOpen, "");
    }
  };

  const vaultApi = appObj?.vault;
  if (typeof vaultApi?.getAbstractFileByPath === "function") {
    const direct = normPath ? vaultApi.getAbstractFileByPath(normPath) : null;
    const isFileNode = (node: unknown): boolean =>
      Boolean(node) &&
      typeof node === "object" &&
      "extension" in (node as Record<string, unknown>);
    const directHealthy =
      isFileNode(direct) &&
      ((direct as { stat?: { size?: number } })?.stat?.size ?? 1) > 0;

    let targetFile = directHealthy ? direct : null;
    if (
      !targetFile &&
      zoteroKey &&
      typeof vaultApi.getMarkdownFiles === "function"
    ) {
      const matches = vaultApi
        .getMarkdownFiles()
        .filter(
          (f) =>
            f.basename === zoteroKey ||
            (typeof f.basename === "string" &&
              f.basename.startsWith(`${zoteroKey} - `))
        );
      targetFile =
        matches.find((f) => (f.stat?.size ?? 1) > 0) ??
        (isFileNode(direct) ? direct : (matches[0] ?? null));
    } else if (!targetFile && isFileNode(direct)) {
      targetFile = direct;
    }

    if (targetFile) {
      const ws = appObj?.workspace;
      if (typeof ws?.getLeaf === "function") {
        const leaf = opts.mod
          ? ws.getLeaf(opts.mod)
          : opts.preferRootLeaf
            ? (ws.getMostRecentLeaf?.() ?? ws.getLeaf("tab"))
            : ws.getLeaf(false);
        if (typeof leaf?.openFile === "function") {
          await leaf.openFile(targetFile);
          await ws.revealLeaf?.(leaf);
          ws.setActiveLeaf?.(leaf, { focus: true });
          return true;
        }
      }
      await callOpenLink(targetFile.path || normPath);
      return true;
    }

    new Notice(
      opts.missingNotice ||
        t("paper_note_missing") ||
        "Note not found in vault."
    );
    return false;
  }

  if (!normPath) {
    new Notice(
      opts.missingNotice || t("paper_note_missing") || "Note path unavailable."
    );
    return false;
  }
  await callOpenLink(rawPath);
  return true;
}

export interface UnifiedPaperMenuOptions {
  key: string;
  title?: string;
  notePath?: string | null;
  hasPdf?: boolean;
  needsDiagnostic?: boolean;
  onOpenNote?: () => void;
  onOpenPdf?: () => void;
  onOpenSplit?: () => void;
  onRunOcr?: () => void;
  onOpenDiagnostic?: () => void;
}

/**
 * Bind Obsidian's native Ctrl/Cmd+Hover Page Preview trigger to any paper element.
 * Safely degrades to a no-op under minimal test harnesses where workspace.trigger is absent.
 */
export function bindObsidianHoverPreview(
  app: unknown,
  targetEl: HTMLElement | null | undefined,
  sourceId: string,
  linkPath?: string | null
): void {
  if (!targetEl || !linkPath) return;
  targetEl.addEventListener("mouseover", (event: MouseEvent) => {
    const ws = (
      app as {
        workspace?: { trigger?: (ev: string, data: unknown) => void };
      } | null
    )?.workspace;
    if (typeof ws?.trigger !== "function") return;
    ws.trigger("hover-link", {
      event,
      source: sourceId,
      hoverParent: ws,
      targetEl,
      linktext: linkPath,
    });
  });
}

/**
 * Open a consistent Obsidian-native context menu for any paper entry across
 * Base rows, Companion reading header, and Search results.
 */
export function openUnifiedPaperContextMenu(
  event: MouseEvent,
  opts: UnifiedPaperMenuOptions
): void {
  const MenuCtor = (obsidian as unknown as Record<string, unknown>).Menu as
    | (new () => {
        addItem: (
          cb: (item: {
            setTitle: (title: string) => unknown;
            setIcon?: (icon: string) => unknown;
            onClick: (cb: () => void) => unknown;
          }) => void
        ) => void;
        addSeparator?: () => void;
        showAtMouseEvent: (e: MouseEvent) => void;
      })
    | undefined;
  if (typeof MenuCtor !== "function") return;
  event.preventDefault();
  event.stopPropagation();

  const menu = new MenuCtor();
  if (opts.onOpenNote && opts.notePath) {
    menu.addItem((item) => {
      item.setTitle(t("ctx_open_note"));
      item.setIcon?.("file-text");
      item.onClick(() => opts.onOpenNote?.());
    });
  }
  if (opts.hasPdf && opts.onOpenPdf) {
    menu.addItem((item) => {
      item.setTitle(t("ctx_open_pdf"));
      item.setIcon?.("book-open");
      item.onClick(() => opts.onOpenPdf?.());
    });
  }
  if (opts.hasPdf && opts.notePath && opts.onOpenSplit) {
    menu.addItem((item) => {
      item.setTitle(t("pdf_open_note_split"));
      item.setIcon?.("columns-2");
      item.onClick(() => opts.onOpenSplit?.());
    });
  }
  if (opts.key) {
    menu.addSeparator?.();
    menu.addItem((item) => {
      item.setTitle(t("ctx_copy_key").replace("{key}", opts.key));
      item.setIcon?.("copy");
      item.onClick(() => {
        if (
          typeof navigator !== "undefined" &&
          navigator.clipboard?.writeText
        ) {
          void navigator.clipboard.writeText(opts.key).then(() => {
            new Notice(t("ctx_copied_key").replace("{key}", opts.key));
          });
        }
      });
    });
  }
  if (opts.onRunOcr) {
    menu.addItem((item) => {
      item.setTitle(t("base_run_selected_ocr"));
      item.setIcon?.("play");
      item.onClick(() => opts.onRunOcr?.());
    });
  }
  if (opts.needsDiagnostic && opts.onOpenDiagnostic) {
    menu.addItem((item) => {
      item.setTitle(t("ctx_open_diag"));
      item.setIcon?.("stethoscope");
      item.onClick(() => opts.onOpenDiagnostic?.());
    });
  }
  menu.showAtMouseEvent(event);
}
