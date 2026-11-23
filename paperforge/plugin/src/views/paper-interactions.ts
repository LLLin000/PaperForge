import { Notice } from "obsidian";
import * as obsidian from "obsidian";
import { t } from "../i18n";

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
