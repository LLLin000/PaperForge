/**
 * Deterministic reading-order side-lane layout (Phase ANN11, Plan 01).
 *
 * Pure CommonJS helpers for sorting annotation cards/rows by reading
 * order and assigning them to left/right lanes by alternation.
 *
 * The sort algorithm matches `sortAnnotationsForReadingOrder()` from
 * `src/testable.js` — page index first, then sort index, then stable
 * annotation identity — but is implemented independently here because
 * `src/testable.js` imports Node runtime helpers unrelated to canvas
 * rendering.
 *
 * No random, draggable, persisted, localStorage, settings, or Obsidian
 * `.canvas` layout data is created or used.
 *
 * @module canvas/layout
 */

// ── Identity helpers ──

/**
 * Compute a stable identity for a normalized annotation row or card.
 *
 * Mirrors `getAnnotationIdentity()` from `src/testable.js` without
 * importing that module.
 *
 * @param {object|null} item - Normalized row or card-like object.
 * @returns {string} Stable identity string.
 */
function _getIdentity(item) {
    if (!item) return '';
    // Accept both normalized row shape ({ display, provenance, pdfLocation })
    // and card shape ({ id, ... }).
    if (item.id) return String(item.id);

    const p = (item.provenance || {});
    const loc = (item.pdfLocation || {});
    const d = (item.display || {});

    if (p.sourceAnnotationKey) return String(p.sourceAnnotationKey);
    if (loc.rowId) return String(loc.rowId);
    if (p.source) return p.source + '|' + (p.sourceAttachmentKey || '') + '|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
    return 'row|' + (d.page != null ? d.page : '') + '|' + (loc.sortIndex != null ? loc.sortIndex : 0);
}

// ── Reading-order sort ──

/**
 * Extract the page index from a card or normalized row.
 *
 * @param {object} item - Card or normalized row.
 * @returns {number} Page index, or MAX_SAFE_INTEGER if missing.
 * @private
 */
function _getPageIndex(item) {
    if (item == null) return Number.MAX_SAFE_INTEGER;

    // Check card shape first (cards have pageIndex directly)
    if (item.pageIndex != null) return item.pageIndex;

    // Check normalized row pdfLocation
    const loc = item.pdfLocation || {};
    return loc.pageIndex != null ? loc.pageIndex : Number.MAX_SAFE_INTEGER;
}

/**
 * Extract the sort index from a card or normalized row.
 *
 * @param {object} item - Card or normalized row.
 * @returns {number} Sort index, or MAX_SAFE_INTEGER if missing.
 * @private
 */
function _getSortIndex(item) {
    if (item == null) return Number.MAX_SAFE_INTEGER;

    // Card shape
    if (item.sortIndex != null) return item.sortIndex;

    // Normalized row shape
    const loc = item.pdfLocation || {};
    return loc.sortIndex != null ? loc.sortIndex : Number.MAX_SAFE_INTEGER;
}

/**
 * Compare two cards or normalized rows by reading order.
 *
 * Precedence:
 *   1. Page index ascending (missing sorts last).
 *   2. sortIndex ascending within the same page.
 *   3. Stable identity tiebreaker for deterministic ordering.
 *
 * @param {object} a - First card or row.
 * @param {object} b - Second card or row.
 * @returns {number} Negative if a < b, positive if a > b, 0 if equal.
 */
function compareCanvasCardsByReadingOrder(a, b) {
    // Page index
    const pageA = _getPageIndex(a);
    const pageB = _getPageIndex(b);
    if (pageA !== pageB) return pageA - pageB;

    // Sort index within page
    const sortA = _getSortIndex(a);
    const sortB = _getSortIndex(b);
    if (sortA !== sortB) return sortA - sortB;

    // Stable identity tiebreaker
    const idA = _getIdentity(a);
    const idB = _getIdentity(b);
    if (idA < idB) return -1;
    if (idA > idB) return 1;
    return 0;
}

/**
 * Sort cards or normalized rows by reading order.
 *
 * Does NOT mutate the input array.
 * Uses `compareCanvasCardsByReadingOrder` for ordering.
 *
 * @param {Array<object>} items - Cards or normalized rows.
 * @returns {Array<object>} New sorted array.
 */
function sortCanvasCardsForReadingOrder(items) {
    if (!Array.isArray(items)) return [];
    const copy = items.slice();
    copy.sort(compareCanvasCardsByReadingOrder);
    return copy;
}

// ── Lane assignment ──

/**
 * Assign sorted cards to left/right lanes by alternation.
 *
 * Cards at even sorted indices go to the left lane, odd indices to
 * the right lane. Each assigned card gets a `lane` ('left' or 'right')
 * and `laneIndex` (position within its lane) property via a shallow
 * copy so the input objects are not mutated.
 *
 * @param {Array<object>} cards - Card objects in desired order.
 * @returns {{ left: Array<object>, right: Array<object> }}
 */
function assignCanvasCardsToLanes(cards) {
    const lanes = { left: [], right: [] };
    if (!Array.isArray(cards)) return lanes;

    cards.forEach(function (card, index) {
        const lane = index % 2 === 0 ? 'left' : 'right';
        const laneIndex = Math.floor(index / 2);
        // Create a shallow copy so we don't mutate inputs
        const assigned = Object.assign({}, card, { lane: lane, laneIndex: laneIndex });
        lanes[lane].push(assigned);
    });

    return lanes;
}

/**
 * Get a stable identity for a card or normalized row.
 *
 * Mirrors `getAnnotationIdentity()` from `src/testable.js`.
 *
 * @param {object|null} item - Card or normalized row.
 * @returns {string}
 */
function getCardIdentity(item) {
    return _getIdentity(item);
}

module.exports = {
    compareCanvasCardsByReadingOrder,
    sortCanvasCardsForReadingOrder,
    assignCanvasCardsToLanes,
    getCardIdentity,
};
