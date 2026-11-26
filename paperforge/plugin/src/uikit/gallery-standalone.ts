/**
 * Standalone browser entry point for `paperforge/plugin/prototypes/ui-gallery.html`.
 * Built by `npm run gallery` (`node scripts/build-gallery.mjs`).
 */

import { installDomPolyfills } from "./gallery-obsidian-shim";
import { PaperForgeGalleryController } from "./gallery";

installDomPolyfills();

async function bootGallery(): Promise<void> {
  const root = document.getElementById("pf-gallery-app");
  if (!root) return;

  const ctrl = new PaperForgeGalleryController(root, {
    preset: "obsidian",
    mode: "light",
    density: "default",
    liquidGlass: true,
    reduceMotion: false,
  });

  await ctrl.mount();
  (
    window as unknown as { __PF_GALLERY_READY__: boolean }
  ).__PF_GALLERY_READY__ = true;
  (
    window as unknown as { __PF_GALLERY_CTRL__: PaperForgeGalleryController }
  ).__PF_GALLERY_CTRL__ = ctrl;
}

void bootGallery().catch((err) => {
  console.error("Failed to boot PaperForge UI Gallery:", err);
  (window as unknown as { __PF_GALLERY_ERROR__: string }).__PF_GALLERY_ERROR__ =
    err instanceof Error ? `${err.message}\n${err.stack}` : String(err);
});
