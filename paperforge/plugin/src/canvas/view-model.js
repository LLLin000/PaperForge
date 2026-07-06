/**
 * Canvas card view-model helpers (Phase ANN11, Plan 01).
 *
 * Pure CommonJS helpers for building read-only annotation card models
 * and explicit canvas/card state projections from the existing v0.2
 * normalized annotation state.
 *
 * No Obsidian, subprocess, database, or Zotero dependencies.
 * No mutation controls, no action descriptors, no anchor/navigation code.
 *
 * @module canvas/view-model
 */

// ── Internal reading-order sort (mirrors testable.js algorithm) ──
//
// This is a standalone implementation used by view-model.js without
// importing src/testable.js (which contains unrelated Node runtime code).
// Tests may import sortAnnotationsForReadingOrder from testable.js to
// prove parity.

/**
 * Stable identity for a normalized annotation row.
 *
 * Mirrors getAnnotationIdentity() from src/testable.js without importing it.
 *
 * @param {object|null} row - Normalized annotation row.
 * @returns {string} Stable identity string.
 */
function _getCardIdentity(row) {
    if (!row) return '';
    const p = (row.provenance || {});
    const loc = (row.pdfLocation || {});
    const d = (row.display || {});

    if (p.sourceAnnotationKey) return String(p.sourceAnnotationKey);
    if (loc.rowId) return String(loc.rowId);
    if (p.source) return p.source + '|' + (p.sourceAttachmentKey || '') + '|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
    return 'row|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
}

/**
 * Compare two normalized rows by reading order.
 *
 * Precedence: page index → sortIndex → stable identity.
 *
 * @param {object} a - First row.
 * @param {object} b - Second row.
 * @returns {number} -1, 0, or 1.
 */
function _compareRowsByReadingOrder(a, b) {
    const locA = (a && a.pdfLocation) || {};
    const locB = (b && b.pdfLocation) || {};

    // Page index (null/missing sorts last)
    const pageA = locA.pageIndex != null ? locA.pageIndex : Number.MAX_SAFE_INTEGER;
    const pageB = locB.pageIndex != null ? locB.pageIndex : Number.MAX_SAFE_INTEGER;
    if (pageA !== pageB) return pageA - pageB;

    // sortIndex within page
    const sortA = locA.sortIndex != null ? locA.sortIndex : Number.MAX_SAFE_INTEGER;
    const sortB = locB.sortIndex != null ? locB.sortIndex : Number.MAX_SAFE_INTEGER;
    if (sortA !== sortB) return sortA - sortB;

    // Stable identity tiebreaker
    const idA = _getCardIdentity(a);
    const idB = _getCardIdentity(b);
    if (idA < idB) return -1;
    if (idA > idB) return 1;
    return 0;
}

/**
 * Sort rows by reading order without mutating the input.
 *
 * @param {Array<object>} rows - Normalized annotation rows.
 * @returns {Array<object>} New sorted array.
 */
function _sortRowsForReadingOrder(rows) {
    if (!Array.isArray(rows)) return [];
    const copy = rows.slice();
    copy.sort(_compareRowsByReadingOrder);
    return copy;
}

/**
 * Assign sorted card objects to left/right lanes by alternation.
 *
 * @param {Array<object>} cards - Card objects (already in desired order).
 * @returns {{ left: Array<object>, right: Array<object> }}
 */
function _assignCardsToLanes(cards) {
    const lanes = { left: [], right: [] };
    if (!Array.isArray(cards)) return lanes;

    cards.forEach(function (card, index) {
        const lane = index % 2 === 0 ? 'left' : 'right';
        card.lane = lane;
        card.laneIndex = Math.floor(index / 2);
        lanes[lane].push(card);
    });

    return lanes;
}

// ── Preview metadata ──

/**
 * Maximum preview length for selected-text fields (two lines approx).
 * @private
 */
const _SELECTED_TEXT_LIMIT = 140;

/**
 * Maximum preview length for comment fields (one line approx).
 * @private
 */
const _COMMENT_LIMIT = 70;

/**
 * Normalize a text value into a card preview metadata object.
 *
 * Returns safe preview metadata without DOM measurement:
 *   { text, kind, truncated, expandable, isLong }
 *
 * "selected-text" values get a ~140-char limit.
 * "comment" values get a ~70-char limit.
 *
 * @param {string|null|undefined} value - The content to preview.
 * @param {"selected-text"|"comment"} kind - The kind of content.
 * @returns {{ text: string, kind: string, truncated: boolean, expandable: boolean, isLong: boolean }}
 */
function normalizeCanvasCardPreview(value, kind) {
    const safeText = (value != null ? String(value) : '');
    const limit = kind === 'selected-text' ? _SELECTED_TEXT_LIMIT : _COMMENT_LIMIT;

    const isLong = safeText.length > limit;
    const truncated = safeText.length > limit;

    if (safeText.length <= limit) {
        return { text: safeText, kind: kind, truncated: false, expandable: false, isLong: false };
    }

    const truncatedText = safeText.substring(0, limit) + '…';
    return { text: truncatedText, kind: kind, truncated: true, expandable: true, isLong: true };
}

// ── Card builder ──

/**
 * Build a read-only annotation card from a normalized annotation row.
 *
 * Consumes an existing normalized row from the v0.2 annotation state.
 * Does NOT construct CLI args, import fs/child_process, read SQLite/Zotero,
 * or mutate row inputs.
 *
 * Per D-01, the card carries selected text, comment, page, color/type,
 * source/provenance, attachment identity, annotation identity, and
 * read-only status.
 *
 * Per D-03 and D-21, the card exposes no expandable details, drawers,
 * popovers, editable forms, local mutation state, or action controls.
 *
 * @param {object} row - A normalized annotation row ({ display, provenance, pdfLocation }).
 * @returns {object} Read-only card object.
 */
function buildCanvasCard(row) {
    const display = (row && row.display) || {};
    const provenance = (row && row.provenance) || {};
    const pdfLoc = (row && row.pdfLocation) || {};

    const selectedText = display.selectedText != null ? String(display.selectedText) : '';
    const comment = display.comment != null ? String(display.comment) : '';

    const id = _getCardIdentity(row);
    const readOnly = !(provenance.isReadonly === false);

    return {
        // ── Identity ──
        id: id,

        // ── Display fields ──
        selectedText: selectedText,
        comment: comment,
        pageLabel: pdfLoc.pageLabel || display.pageLabel || '',
        pageIndex: pdfLoc.pageIndex != null ? pdfLoc.pageIndex : null,
        type: display.type || 'annotation',
        color: display.color != null ? display.color : null,

        // ── Source / provenance ──
        source: provenance.source || 'unknown',
        sourceAttachmentKey: provenance.sourceAttachmentKey || '',
        sourceAnnotationKey: provenance.sourceAnnotationKey || '',

        // ── Read-only metadata ──
        readOnly: readOnly,
        readOnlyLabel: readOnly ? 'Read-only' : '',

        // ── Preview metadata ──
        selectedTextPreview: normalizeCanvasCardPreview(selectedText, 'selected-text'),
        commentPreview: normalizeCanvasCardPreview(comment, 'comment'),

        // ── Anchor placeholder (ANN12) ──
        anchor: { status: 'unresolved', reason: 'Source anchors are implemented in ANN12.' },
    };
}

// ── Canvas view-model builder ──

/**
 * Build a complete canvas view-model from the annotation state.
 *
 * Maps annotation load states (loaded, empty, missing-paper, missing-db,
 * cli-error, invalid-json, missing-source, unsupported, idle) plus
 * refreshing and stale variants into explicit canvas view-model states.
 *
 * Each state has a distinct `state` name so renderers can present
 * appropriate UI without re-interpreting the underlying load state.
 *
 * The `options` parameter supports:
 *   - `refreshing` (boolean): When true, the view-model is marked as
 *     'refreshing' while preserving existing cards for display.
 *   - `stale` (boolean): When true, the view-model is marked as 'stale'
 *     while preserving existing cards with per-card stale flags.
 *
 * @param {object|null|undefined} annotationState - The annotation load state
 *   ({ state, paperKey, annotations, message, errorCode, raw, stale }).
 * @param {object} [options] - Optional display flags.
 * @param {boolean} [options.refreshing] - Mark as refreshing state.
 * @param {boolean} [options.stale] - Mark as stale state.
 * @returns {{ state: string, paperKey: string|null, cards: Array, lanes: ({ left: Array, right: Array })|undefined, message: string, refreshing: boolean, stale: boolean }}
 */
function buildCanvasCardViewModel(annotationState, options) {
    const aState = annotationState || { state: 'idle', annotations: [] };
    const opts = options || {};
    const rawState = aState.state || 'idle';
    const rows = Array.isArray(aState.annotations) ? aState.annotations : [];
    const paperKey = aState.paperKey != null ? aState.paperKey : null;
    const hasStale = Boolean(aState.stale) || Boolean(opts.stale);
    const hasRefreshing = Boolean(opts.refreshing);

    // ── Build cards if we have annotation rows ──
    function buildCards() {
        if (rows.length === 0) return [];
        const sorted = _sortRowsForReadingOrder(rows);
        return sorted.map(function (row) {
            const card = buildCanvasCard(row);
            if (hasStale) card.stale = true;
            return card;
        });
    }

    // ── States with no cards ──
    if (rawState === 'idle') {
        return { state: 'idle', paperKey: paperKey, cards: [], message: aState.message || '', refreshing: false, stale: false };
    }

    if (rawState === 'loading') {
        return { state: 'loading', paperKey: paperKey, cards: [], message: aState.message || 'Loading annotations…', refreshing: false, stale: false };
    }

    if (rawState === 'empty') {
        return { state: 'empty', paperKey: paperKey, cards: [], message: aState.message || 'This paper has no annotations yet.', refreshing: false, stale: hasStale };
    }

    if (rawState === 'missing-paper') {
        return { state: 'missing-paper', paperKey: null, cards: [], message: aState.message || 'No paper is currently active.', refreshing: false, stale: false };
    }

    if (rawState === 'missing-db') {
        return { state: 'missing-db', paperKey: paperKey, cards: [], message: aState.message || 'Annotation database is not available.', refreshing: false, stale: false };
    }

    if (rawState === 'cli-error') {
        return { state: 'cli-error', paperKey: paperKey, cards: [], message: aState.message || 'Failed to load annotations.', refreshing: false, stale: false };
    }

    if (rawState === 'invalid-json') {
        return { state: 'invalid-json', paperKey: paperKey, cards: [], message: aState.message || 'Could not read annotation data.', refreshing: false, stale: false };
    }

    if (rawState === 'missing-source') {
        return { state: 'missing-source', paperKey: paperKey, cards: [], message: aState.message || 'Reading source is not available for this paper.', refreshing: false, stale: false };
    }

    if (rawState === 'unsupported') {
        return { state: 'unsupported', paperKey: paperKey, cards: [], message: aState.message || 'This paper type is not supported.', refreshing: false, stale: false };
    }

    // ── States with cards (ready, refreshing, stale) ──
    if (rawState === 'ready') {
        const cards = buildCards();
        const lanes = cards.length > 0 ? _assignCardsToLanes(cards) : undefined;

        if (hasRefreshing) {
            return {
                state: 'refreshing',
                paperKey: paperKey,
                cards: cards,
                lanes: lanes,
                message: aState.message || 'Refreshing annotations…',
                refreshing: true,
                stale: false,
            };
        }

        if (hasStale) {
            return {
                state: 'stale',
                paperKey: paperKey,
                cards: cards,
                lanes: lanes,
                message: (aState.message || '') + ' — Showing previously loaded (stale) data.',
                refreshing: false,
                stale: true,
            };
        }

        return {
            state: 'ready',
            paperKey: paperKey,
            cards: cards,
            lanes: lanes,
            message: aState.message || (cards.length + ' annotation(s) loaded.'),
            refreshing: false,
            stale: false,
        };
    }

    // ── Unknown state → fallback to idle ──
    return { state: 'idle', paperKey: paperKey, cards: [], message: '', refreshing: false, stale: false };
}

module.exports = {
    buildCanvasCard,
    buildCanvasCardViewModel,
    normalizeCanvasCardPreview,
};
