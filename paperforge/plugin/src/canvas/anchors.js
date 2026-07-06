/**
 * Pure conservative anchor resolver for PaperForge-owned source text
 * (Phase ANN12, Plan 01).
 *
 * Pure CommonJS helpers for resolving card annotations to exact,
 * page-level, or unresolved anchor statuses based on normalized
 * source text matching.  No fs, no Obsidian, no native PDF DOM,
 * no innerHTML, no subprocess.
 *
 * Anchor statuses per D-06 through D-10:
 *   exact      — Normalized selected text has exactly one owned-source match.
 *   page-level — Page metadata available without unique text grounding.
 *   unresolved — No source content or page metadata available.
 *
 * @module canvas/anchors
 */

// ── Anchor constants ──

/**
 * Anchor precision statuses.
 *
 * @enum {string}
 * @readonly
 */
const ANCHOR_STATUSES = Object.freeze({
    EXACT: 'exact',
    PAGE_LEVEL: 'page-level',
    UNRESOLVED: 'unresolved',
});

/**
 * Minimum character length for selected text to qualify for exact anchoring.
 * Text below this threshold always downgrades to page-level or unresolved.
 *
 * @type {number}
 */
const MIN_EXACT_TEXT_CHARS = 3;

// ── Placeholder exports (Task 2 will implement) ──

function resolveCanvasAnchor(card, sourceModel, options) {
    // Stub — Task 2 GREEN will implement
    return {
        anchorId: '',
        cardId: (card && card.cardId) || '',
        status: ANCHOR_STATUSES.UNRESOLVED,
        sourceKind: null,
        reason: 'Anchor resolver not yet implemented.',
        matchCount: 0,
        pageIndex: (card && card.pageIndex) != null ? card.pageIndex : null,
        diagnostics: {},
    };
}

function resolveCanvasAnchors(cards, sourceModel, options) {
    if (!Array.isArray(cards)) return [];
    return cards.map(function (card) {
        return resolveCanvasAnchor(card, sourceModel, options);
    });
}

function findNormalizedSourceMatches(sourceText, selectedText) {
    // Stub — Task 2 GREEN will implement
    return [];
}

module.exports = {
    ANCHOR_STATUSES: ANCHOR_STATUSES,
    MIN_EXACT_TEXT_CHARS: MIN_EXACT_TEXT_CHARS,
    resolveCanvasAnchor: resolveCanvasAnchor,
    resolveCanvasAnchors: resolveCanvasAnchors,
    findNormalizedSourceMatches: findNormalizedSourceMatches,
};
