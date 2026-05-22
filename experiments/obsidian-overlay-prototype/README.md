# Obsidian PDF Overlay Prototype

> Placeholder for overlay prototype code.
>
> After Phase 2 implementation, this directory will contain:
> - `patch-pdf-viewer.ts` — monkey-around patches for PDFViewerChild
> - `overlay-layer.ts` — overlay DOM management
> - `rect-renderer.ts` — rectangle rendering with coordinates
> - `selection-handler.ts` — text selection detection
> - `popover.ts` — annotation edit popover
> - `annotation-fetcher.ts` — execFile Python bridge
> - `types.ts` — shared interfaces

## Reference

PDF++ source: https://github.com/RyotaUshio/obsidian-pdf-plus

Core techniques:
- `around()` from `monkey-around` library for prototype patching
- `window.pdfjsLib.setLayerDimensions()` for coordinate alignment
- Percentage-based CSS positioning for zoom-independence
- EventBus: `textlayerrendered`, `pagerendered`, `scalechanged`
