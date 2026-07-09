/**
 * Canvas card view-model helpers (Phase ANN11, Plan 01; expanded ANN12).
 *
 * Pure CommonJS helpers for building read-only annotation card models
 * and explicit canvas/card state projections from the existing v0.2
 * normalized annotation state.
 *
 * ANN12 extension: cards receive computed source anchors from an optional
 * `sourceModel` parameter, resolving to exact/page-level/unresolved.
 *
 * No Obsidian, subprocess, database, or Zotero dependencies.
 * No mutation controls, no action descriptors, no navigation/connector code.
 *
 * @module canvas/view-model
 */

const {
    sortCanvasCardsForReadingOrder,
    assignCanvasCardsToLanes,
    getCardIdentity,
} = require('./layout');

const {
    resolveCanvasAnchor,
} = require('./anchors');

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
 * Return whether an annotation payload contains content for a side card.
 *
 * Anchor resolution is intentionally irrelevant here: card eligibility is
 * determined only by authored annotation content.
 *
 * @param {object} annotation - Normalized annotation row or raw payload.
 * @returns {boolean}
 */
function annotationNeedsSideCard(annotation) {
    const payload = annotation || {};
    const display = payload.display || {};
    const raw = payload.raw || {};
    const values = [
        display.comment, display.note, display.imagePath, display.imageData,
        payload.comment, payload.note, payload.imagePath, payload.imageData,
        raw.comment, raw.note, raw.imagePath, raw.imageData,
        raw.image_path, raw.image_data,
    ];

    function hasContent(value) {
        if (value == null) return false;
        if (typeof value === 'string') return value.trim().length > 0;
        if (Array.isArray(value)) return value.some(hasContent);
        if (typeof value === 'object') {
            return Object.keys(value).some(function (key) {
                return hasContent(value[key]);
            });
        }
        return true;
    }

    return values.some(hasContent);
}

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
 * ANN12 extension: when `sourceModel` is provided, the card receives a
 * computed anchor via `resolveCanvasAnchor`.  Without sourceModel,
 * the anchor is a safe fallback (unresolved with explanation).
 *
 * @param {object} row - A normalized annotation row ({ display, provenance, pdfLocation }).
 * @param {object} [sourceModel] - Optional source model from buildCanvasSourceModel().
 * @returns {object} Read-only card object.
 */
function buildCanvasCard(row, sourceModel) {
    const display = (row && row.display) || {};
    const provenance = (row && row.provenance) || {};
    const pdfLoc = (row && row.pdfLocation) || {};

    const selectedText = display.selectedText != null ? String(display.selectedText) : '';
    const comment = display.comment != null ? String(display.comment) : '';

    const id = getCardIdentity(row);
    const readOnly = !(provenance.isReadonly === false);

    // ── Compute anchor from sourceModel if provided ──
    var anchor;
    if (sourceModel) {
        var anchorCard = {
            cardId: id,
            selectedText: selectedText,
            pageIndex: pdfLoc.pageIndex != null ? pdfLoc.pageIndex : null,
            pageLabel: pdfLoc.pageLabel || display.pageLabel || '',
        };
        anchor = resolveCanvasAnchor(anchorCard, sourceModel);
    } else {
        anchor = { status: 'unresolved', reason: 'No source model provided for anchor resolution.' };
    }

    return {
        // ── Identity ──
        id: id,

        // ── Display fields ──
        selectedText: selectedText,
        comment: comment,
        note: display.note,
        imagePath: display.imagePath,
        imageData: display.imageData,
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

        // ── Anchor (ANN12) ──
        anchor: anchor,
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
 *   - `sourceModel` (object): Optional source model from
 *     buildCanvasSourceModel(). When provided, each card receives a
 *     computed anchor (exact/page-level/unresolved) via the anchor
 *     resolver.
 *
 * @param {object|null|undefined} annotationState - The annotation load state
 *   ({ state, paperKey, annotations, message, errorCode, raw, stale }).
 * @param {object} [options] - Optional display flags.
 * @param {boolean} [options.refreshing] - Mark as refreshing state.
 * @param {boolean} [options.stale] - Mark as stale state.
 * @param {object} [options.sourceModel] - Source model for anchor resolution.
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
    var sourceModel = opts.sourceModel || null;

    function buildAnnotationProjections() {
        if (rows.length === 0) return [];
        const sorted = sortCanvasCardsForReadingOrder(rows);
        return sorted.map(function (row) {
            const card = buildCanvasCard(row, sourceModel);
            if (hasStale) card.stale = true;
            return { row: row, card: card };
        });
    }

    function completeViewModel(viewModel) {
        if (!Object.prototype.hasOwnProperty.call(viewModel, 'sourceModel')) {
            viewModel.sourceModel = sourceModel;
        }
        if (!Array.isArray(viewModel.highlights)) viewModel.highlights = [];
        if (!Array.isArray(viewModel.unresolved)) viewModel.unresolved = [];
        if (viewModel.unresolvedCount == null) {
            viewModel.unresolvedCount = viewModel.unresolved.length;
        }
        return viewModel;
    }

    // ── States with no cards ──
    if (rawState === 'idle') {
        return completeViewModel({ state: 'idle', paperKey: paperKey, cards: [], message: aState.message || '', refreshing: false, stale: false });
    }

    if (rawState === 'loading') {
        return completeViewModel({ state: 'loading', paperKey: paperKey, cards: [], message: aState.message || 'Loading annotations…', refreshing: false, stale: false });
    }

    if (rawState === 'empty') {
        return completeViewModel({ state: 'empty', paperKey: paperKey, cards: [], message: aState.message || 'This paper has no annotations yet.', refreshing: false, stale: hasStale });
    }

    if (rawState === 'missing-paper') {
        return completeViewModel({ state: 'missing-paper', paperKey: null, cards: [], message: aState.message || 'No paper is currently active.', refreshing: false, stale: false });
    }

    if (rawState === 'missing-db') {
        return completeViewModel({ state: 'missing-db', paperKey: paperKey, cards: [], message: aState.message || 'Annotation database is not available.', refreshing: false, stale: false });
    }

    if (rawState === 'cli-error') {
        return completeViewModel({ state: 'cli-error', paperKey: paperKey, cards: [], message: aState.message || 'Failed to load annotations.', refreshing: false, stale: false });
    }

    if (rawState === 'invalid-json') {
        return completeViewModel({ state: 'invalid-json', paperKey: paperKey, cards: [], message: aState.message || 'Could not read annotation data.', refreshing: false, stale: false });
    }

    if (rawState === 'missing-source') {
        return completeViewModel({ state: 'missing-source', paperKey: paperKey, cards: [], message: aState.message || 'Reading source is not available for this paper.', refreshing: false, stale: false });
    }

    if (rawState === 'unsupported') {
        return completeViewModel({ state: 'unsupported', paperKey: paperKey, cards: [], message: aState.message || 'This paper type is not supported.', refreshing: false, stale: false });
    }

    // ── States with cards (ready, refreshing, stale) ──
    if (rawState === 'ready') {
        const projections = buildAnnotationProjections();
        const resolvedProjections = projections
            .filter(function (item) {
                return item.card.anchor.status === 'exact' || item.card.anchor.status === 'resolved';
            });
        const highlights = resolvedProjections.map(function (item) { return item.card; });
        const unresolved = projections
            .filter(function (item) {
                return item.card.anchor.status !== 'exact' && item.card.anchor.status !== 'resolved';
            })
            .map(function (item) {
                return Object.assign({}, item.row, item.card, {
                    annotation: item.row,
                    card: item.card,
                    anchor: item.card.anchor,
                });
            });
        const cardProjections = sourceModel ? resolvedProjections : projections;
        const cards = cardProjections
            .filter(function (item) { return annotationNeedsSideCard(item.row); })
            .map(function (item) { return item.card; });
        const lanes = cards.length > 0 ? assignCanvasCardsToLanes(cards) : undefined;
        const projectionFields = {
            sourceModel: sourceModel,
            highlights: highlights,
            unresolved: unresolved,
            unresolvedCount: unresolved.length,
        };

        if (hasRefreshing) {
            return completeViewModel({
                state: 'refreshing',
                paperKey: paperKey,
                cards: cards,
                lanes: lanes,
                message: aState.message || 'Refreshing annotations…',
                refreshing: true,
                stale: false,
                ...projectionFields,
            });
        }

        if (hasStale) {
            return completeViewModel({
                state: 'stale',
                paperKey: paperKey,
                cards: cards,
                lanes: lanes,
                message: (aState.message || '') + ' — Showing previously loaded (stale) data.',
                refreshing: false,
                stale: true,
                ...projectionFields,
            });
        }

        return completeViewModel({
            state: 'ready',
            paperKey: paperKey,
            cards: cards,
            lanes: lanes,
            message: aState.message || (cards.length + ' annotation(s) loaded.'),
            refreshing: false,
            stale: false,
            ...projectionFields,
        });
    }

    // ── Unknown state → fallback to idle ──
    return completeViewModel({ state: 'idle', paperKey: paperKey, cards: [], message: '', refreshing: false, stale: false });
}

module.exports = {
    annotationNeedsSideCard,
    buildCanvasCard,
    buildCanvasCardViewModel,
    normalizeCanvasCardPreview,
};
