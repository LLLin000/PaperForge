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
    renderCanvasCard,
    renderCanvasCardLanes,
    renderCanvasRefreshing,
    renderCanvasSourceSurface,
    renderSourceBlock,
    renderExactAnchorText,
    renderPageLevelAnchorMarker,
    renderUnresolvedAnchorStatus,
} = require('./render');

const {
    buildCanvasCard,
    buildCanvasCardViewModel,
    normalizeCanvasCardPreview,
} = require('./view-model');

const {
    compareCanvasCardsByReadingOrder,
    sortCanvasCardsForReadingOrder,
    assignCanvasCardsToLanes,
    getCardIdentity,
} = require('./layout');

// ── Source surface (ANN12) ──
const {
    SOURCE_KINDS,
    SOURCE_STATES,
    buildCanvasSourceModel,
    buildSourceBlocks,
    normalizeSourceTextForAnchors,
} = require('./surface');

// ── Anchor resolver (ANN12) ──
const {
    ANCHOR_STATUSES,
    MIN_EXACT_TEXT_CHARS,
    resolveCanvasAnchor,
    resolveCanvasAnchors,
    findNormalizedSourceMatches,
} = require('./anchors');

// ── Navigation reducers (ANN13) ──
const {
    NAVIGATION_ACTIONS,
    SELECTION_STATUSES: NAV_SELECTION_STATUSES,
    createInitialNavState,
    reduceCardSelection,
    reduceSourceSelection,
    reduceLifecycleAction,
} = require('./navigation');

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
    renderCanvasCard,
    renderCanvasCardLanes,
    renderCanvasRefreshing,
    // ── Source surface and anchor rendering (ANN12-02) ──
    renderCanvasSourceSurface,
    renderSourceBlock,
    renderExactAnchorText,
    renderPageLevelAnchorMarker,
    renderUnresolvedAnchorStatus,

    // ── Card view-models (ANN11) ──
    buildCanvasCard,
    buildCanvasCardViewModel,
    normalizeCanvasCardPreview,

    // ── Layout helpers (ANN11) ──
    compareCanvasCardsByReadingOrder,
    sortCanvasCardsForReadingOrder,
    assignCanvasCardsToLanes,
    getCardIdentity,

    // ── Source surface (ANN12) ──
    SOURCE_KINDS,
    SOURCE_STATES,
    buildCanvasSourceModel,
    buildSourceBlocks,
    normalizeSourceTextForAnchors,

    // ── Anchor resolver (ANN12) ──
    ANCHOR_STATUSES,
    MIN_EXACT_TEXT_CHARS,
    resolveCanvasAnchor,
    resolveCanvasAnchors,
    findNormalizedSourceMatches,

    // ── Navigation reducers (ANN13) ──
    NAVIGATION_ACTIONS,
    NAV_SELECTION_STATUSES,
    createInitialNavState,
    reduceCardSelection,
    reduceSourceSelection,
    reduceLifecycleAction,
};
