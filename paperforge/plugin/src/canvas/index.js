/**
 * PaperForge Reading Canvas — CommonJS module entry point.
 *
 * Exports a narrow surface of Phase ANN10 contracts:
 *   - context helpers (buildCanvasContextFromEntry, buildMissingCanvasContext)
 *   - annotation loader wrapper (createCanvasAnnotationLoader, ANNOTATION_LOAD_STATES)
 *
 * Controller and render modules are added in Task 2.
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

module.exports = {
    // ── Context helpers ──
    buildCanvasContextFromEntry,
    buildMissingCanvasContext,

    // ── Annotation loading ──
    createCanvasAnnotationLoader,
    ANNOTATION_LOAD_STATES,
};
