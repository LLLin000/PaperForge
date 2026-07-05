/**
 * PaperForge Reading Canvas — CommonJS module entry point.
 *
 * Exports Phase ANN10 contracts:
 *   - context helpers (buildCanvasContextFromEntry, buildMissingCanvasContext)
 *   - annotation loader wrapper (createCanvasAnnotationLoader, ANNOTATION_LOAD_STATES)
 *   - canvas session controller (createCanvasSessionController)
 *   - shell DOM rendering (renderCanvasView, renderCanvas*)
 *
 * @module canvas/index
 */

const {
    buildCanvasContextFromEntry,
    buildMissingCanvasContext,
} = require('./context');

const {
    createCanvasAnnotationLoader,
    ANNOTATION_LOAD_STATES,
} = require('./annotations');

const {
    createCanvasSessionController,
} = require('./controller');

const {
    renderCanvasView,
    renderCanvasIdentity,
    renderCanvasIdle,
    renderCanvasLoading,
    renderCanvasEmpty,
    renderCanvasMissingPaper,
    renderCanvasMissingDb,
    renderCanvasCliError,
    renderCanvasInvalidJson,
    renderCanvasMissingSource,
    renderCanvasUnsupported,
    renderCanvasStaleBanner,
} = require('./render');

module.exports = {
    // ── Context helpers ──
    buildCanvasContextFromEntry,
    buildMissingCanvasContext,

    // ── Annotation loading ──
    createCanvasAnnotationLoader,
    ANNOTATION_LOAD_STATES,

    // ── Canvas session controller ──
    createCanvasSessionController,

    // ── Canvas DOM rendering ──
    renderCanvasView,
    renderCanvasIdentity,
    renderCanvasIdle,
    renderCanvasLoading,
    renderCanvasEmpty,
    renderCanvasMissingPaper,
    renderCanvasMissingDb,
    renderCanvasCliError,
    renderCanvasInvalidJson,
    renderCanvasMissingSource,
    renderCanvasUnsupported,
    renderCanvasStaleBanner,
};
