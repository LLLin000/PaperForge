/**
 * Pure connector eligibility and geometry helpers for focused
 * card-anchor pairs (Phase ANN14, Plan 01).
 *
 * Decides whether a focused connector may exist and converts
 * measured PaperForge-owned endpoint rectangles into connector
 * geometry.  No DOM rendering, CSS, runtime listeners, or
 * Obsidian integration.
 *
 * All output is serializable plain objects — no DOM refs,
 * timers, Obsidian objects, or persisted layout fields.
 *
 * @module canvas/connectors
 */

// ── Connector state constants ──

/**
 * Visible vs hidden connector states.
 *
 * @enum {string}
 * @readonly
 */
const CONNECTOR_STATES = Object.freeze({
    VISIBLE: 'visible',
    HIDDEN: 'hidden',
});

/**
 * Hidden reason constants explaining why a connector is hidden.
 *
 * @enum {string}
 * @readonly
 */
const HIDDEN_REASONS = Object.freeze({
    /** Card has page-level anchor only — not exact enough for a connector line. */
    PAGE_LEVEL: 'page-level',
    /** Anchor status could not be resolved — no connector. */
    UNRESOLVED: 'unresolved',
    /** Source content is unavailable — cannot anchor. */
    SOURCE_UNAVAILABLE: 'source-unavailable',
    /** Card type or source kind does not support connectors. */
    UNSUPPORTED: 'unsupported',
    /** Navigation state references a card that no longer exists in the card list. */
    MISSING_CARD: 'missing-card',
    /** Navigation state references an anchor that no longer exists. */
    MISSING_ANCHOR: 'missing-anchor',
    /** The card's anchor's DOMRect is no longer available. */
    MISSING_DOM: 'missing-dom',
    /** Selected card ID and selected anchor ID resolve to different cards. */
    MISMATCHED_IDS: 'mismatched-ids',
    /** No focused card or anchor selected/hovered. */
    NO_FOCUS: 'no-focus',
    /** Connector candidate state is stale (e.g. paper changed without clearing). */
    STALE: 'stale',
    /** Navigation state is missing required fields. */
    MISSING_NAV_STATE: 'missing-nav-state',
    /** Card list/map is missing or empty. */
    MISSING_CARD_LIST: 'missing-card-list',
    /** Geometry specific: one or both endpoint rectangles are missing. */
    MISSING_RECT: 'missing-rect',
    /** Geometry specific: rectangle has zero or negative dimensions. */
    ZERO_SIZE: 'zero-size',
    /** Geometry specific: rectangle contains non-finite coordinates. */
    NON_FINITE: 'non-finite',
    /** Geometry specific: endpoint rectangle is outside or clipped by visible canvas bounds. */
    OUTSIDE_CANVAS: 'outside-canvas',
    /** Geometry specific: canvas has unreadable narrow dimensions. */
    NARROW_CANVAS: 'narrow-canvas',
    /** Connector candidate is in hidden state — geometry not applicable. */
    HIDDEN_CANDIDATE: 'hidden-candidate',
});

// ─── Connector candidate shape ──

/**
 * Create a visible connector candidate.
 *
 * @param {string} cardId
 * @param {string} anchorId
 * @param {object} card
 * @param {object} anchor
 * @returns {object} ConnectorCandidate
 * @private
 */
function _visibleCandidate(cardId, anchorId, card, anchor) {
    return {
        state: CONNECTOR_STATES.VISIBLE,
        cardId: cardId,
        anchorId: anchorId,
        reason: null,
        card: card,
        anchor: anchor,
    };
}

/**
 * Create a hidden connector candidate with a reason.
 *
 * @param {string} reason - One of HIDDEN_REASONS.
 * @param {string} [cardId]
 * @param {string} [anchorId]
 * @returns {object} ConnectorCandidate
 * @private
 */
function _hiddenCandidate(reason, cardId, anchorId) {
    var result = {
        state: CONNECTOR_STATES.HIDDEN,
        cardId: cardId || null,
        anchorId: anchorId || null,
        reason: reason,
        card: null,
        anchor: null,
    };
    return result;
}

// ─── Eligibility helper ──

/**
 * Determine whether a focused connector candidate exists for the
 * current navigation and/or hover state.
 *
 * Input fields:
 *   - navState          ({ selectedCardId, selectedAnchorId, ... })
 *   - hoverState        ({ hoveredCardId, hoveredAnchorId, ... }) or null
 *   - cards             (Array) current card list
 *   - paperKey          (string|null) current paper key
 *
 * Decision order (D-01/D-02/D-03/D-04/D-19/D-20):
 *   1. Prefer selected state over hover when both are present.
 *   2. Require both card ID and anchor ID to exist and resolve
 *      to the same current card.
 *   3. Require `card.anchor.status === 'exact'`.
 *   4. Page-level, unresolved, source-unavailable, unsupported,
 *      stale, missing, and mismatched pairs return hidden states.
 *
 * The helper does NOT import or call `resolveCanvasAnchor`, read
 * native PDF viewer selectors, or infer precision from source text.
 *
 * @param {object} input
 * @param {object} [input.navState] - Current navigation state from ANN13.
 * @param {object} [input.hoverState] - Optional hover state.
 * @param {Array<object>} [input.cards] - Current card list.
 * @param {string} [input.paperKey] - Current paper identity key.
 * @returns {object} ConnectorCandidate — { state, cardId, anchorId, reason, card, anchor }
 */
function computeFocusedConnectorCandidate(input) {
    // ── Guard: missing or empty input ──
    if (!input) {
        return _hiddenCandidate(HIDDEN_REASONS.MISSING_NAV_STATE);
    }

    var navState = input.navState;
    var hoverState = input.hoverState || null;
    var cards = input.cards;
    var paperKey = input.paperKey || null;

    // ── Guard: missing navigation state ──
    if (!navState) {
        return _hiddenCandidate(HIDDEN_REASONS.MISSING_NAV_STATE);
    }

    // ── Guard: missing or empty card list ──
    if (!Array.isArray(cards) || cards.length === 0) {
        return _hiddenCandidate(HIDDEN_REASONS.MISSING_CARD_LIST);
    }

    // ── Determine candidate IDs: prefer selected over hover ──
    var cardId = navState.selectedCardId || null;
    var anchorId = navState.selectedAnchorId || null;

    // If no selected state, fall back to hover
    if (!cardId && !anchorId && hoverState) {
        cardId = hoverState.hoveredCardId || null;
        anchorId = hoverState.hoveredAnchorId || null;
    }

    // ── Guard: no focus at all ──
    if (!cardId && !anchorId) {
        return _hiddenCandidate(HIDDEN_REASONS.NO_FOCUS);
    }

    // ── Resolve card from list by cardId ──
    var card = null;
    if (cardId) {
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].cardId === cardId) {
                card = cards[i];
                break;
            }
        }
    }

    // ── Guard: card not found ──
    if (!card) {
        return _hiddenCandidate(HIDDEN_REASONS.MISSING_CARD, cardId, anchorId);
    }

    // ── Guard: mismatched IDs (card and anchor point to different cards) ──
    if (anchorId && anchorId !== cardId) {
        return _hiddenCandidate(HIDDEN_REASONS.MISMATCHED_IDS, cardId, anchorId);
    }

    // ── Guard: anchor not found on card ──
    var anchor = card.anchor || null;
    if (!anchor) {
        return _hiddenCandidate(HIDDEN_REASONS.MISSING_ANCHOR, cardId, anchorId);
    }

    // ── Guard: paper key mismatch (stale) ──
    if (paperKey && card.paperKey && paperKey !== card.paperKey) {
        return _hiddenCandidate(HIDDEN_REASONS.STALE, cardId, anchorId);
    }

    // ── Guard: source unavailable ──
    if (anchor.status === 'source-unavailable') {
        return _hiddenCandidate(HIDDEN_REASONS.SOURCE_UNAVAILABLE, cardId, anchorId);
    }

    // ── Guard: unsupported status ──
    if (anchor.status !== 'exact' && anchor.status !== 'page-level' && anchor.status !== 'unresolved') {
        return _hiddenCandidate(HIDDEN_REASONS.UNSUPPORTED, cardId, anchorId);
    }

    // ── Guard: page-level anchors get hidden (D-01) ──
    if (anchor.status === 'page-level') {
        return _hiddenCandidate(HIDDEN_REASONS.PAGE_LEVEL, cardId, anchorId);
    }

    // ── Guard: unresolved anchors get hidden (D-02) ──
    if (anchor.status === 'unresolved') {
        return _hiddenCandidate(HIDDEN_REASONS.UNRESOLVED, cardId, anchorId);
    }

    // ── Exact match → visible candidate (D-03) ──
    if (anchor.status === 'exact') {
        return _visibleCandidate(cardId, anchorId, card, anchor);
    }

    // ── Fallback: hidden (shouldn't reach here) ──
    return _hiddenCandidate(HIDDEN_REASONS.UNSUPPORTED, cardId, anchorId);
}

// ─── Geometry helper ──

/**
 * Minimum visible canvas width or height below which the canvas
 * is considered too narrow for connector rendering.
 *
 * @type {number}
 */
const MIN_CANVAS_DIMENSION = 50;

/**
 * Measure connector endpoints in the Reading Canvas coordinate
 * frame from DOMRect-like endpoint rectangles.
 *
 * Input fields:
 *   - candidate        ({ state, card, ... }) — result of
 *                       computeFocusedConnectorCandidate()
 *   - canvasRect       ({ x, y, width, height }) — visible canvas bounds
 *   - cardRect         ({ x, y, width, height }) — card endpoint rect
 *   - anchorRect       ({ x, y, width, height }) — anchor endpoint rect
 *
 * Returns a connector geometry object with the following shape
 * when geometry is valid:
 *   {
 *     state: 'visible',
 *     cardEndpoint: { x, y },
 *     anchorEndpoint: { x, y },
 *     cardRect,       // original rect (frozen)
 *     anchorRect,     // original rect (frozen)
 *   }
 *
 * Returns hidden for zero-size, non-finite, outside-canvas,
 * clipped, narrow-canvas, and hidden-candidate inputs per
 * D-05/D-07/D-08/D-14/D-15/D-17.
 *
 * @param {object} input
 * @param {object} input.candidate - ConnectorCandidate from computeFocusedConnectorCandidate.
 * @param {object} input.canvasRect - Visible canvas bounds.
 * @param {object} input.cardRect - Card endpoint DOMRect-like.
 * @param {object} input.anchorRect - Anchor endpoint DOMRect-like.
 * @returns {object} ConnectorGeometry — { state, cardEndpoint, anchorEndpoint, ... }
 */
function measureConnectorGeometry(input) {
    // ── Guard: missing input ──
    if (!input) {
        return _hiddenGeometry(HIDDEN_REASONS.MISSING_RECT);
    }

    var candidate = input.candidate;
    var canvasRect = input.canvasRect;
    var cardRect = input.cardRect;
    var anchorRect = input.anchorRect;

    // ── Guard: hidden candidate → no geometry ──
    if (!candidate || candidate.state !== CONNECTOR_STATES.VISIBLE) {
        return _hiddenGeometry(
            (candidate && candidate.reason) || HIDDEN_REASONS.HIDDEN_CANDIDATE,
            candidate
        );
    }

    // ── Guard: missing rectangles ──
    if (!canvasRect || !cardRect || !anchorRect) {
        return _hiddenGeometry(HIDDEN_REASONS.MISSING_RECT, candidate);
    }

    // ── Collect rect values ──
    var cw = canvasRect.width;
    var ch = canvasRect.height;
    var cx = canvasRect.x;
    var cy = canvasRect.y;

    var cardX = cardRect.x;
    var cardY = cardRect.y;
    var cardW = cardRect.width;
    var cardH = cardRect.height;

    var anchorX = anchorRect.x;
    var anchorY = anchorRect.y;
    var anchorW = anchorRect.width;
    var anchorH = anchorRect.height;

    // ── Guard: narrow canvas (unreadable dimensions) ──
    if (
        cw == null || ch == null ||
        cw < MIN_CANVAS_DIMENSION || ch < MIN_CANVAS_DIMENSION
    ) {
        return _hiddenGeometry(HIDDEN_REASONS.NARROW_CANVAS, candidate);
    }

    // ── Guard: zero or negative dimensions ──
    if (cardW <= 0 || cardH <= 0 || anchorW <= 0 || anchorH <= 0) {
        return _hiddenGeometry(HIDDEN_REASONS.ZERO_SIZE, candidate);
    }

    // ── Guard: non-finite values ──
    if (
        !_isFiniteCoord(cardX) || !_isFiniteCoord(cardY) ||
        !_isFiniteCoord(cardW) || !_isFiniteCoord(cardH) ||
        !_isFiniteCoord(anchorX) || !_isFiniteCoord(anchorY) ||
        !_isFiniteCoord(anchorW) || !_isFiniteCoord(anchorH) ||
        !_isFiniteCoord(cx) || !_isFiniteCoord(cy) ||
        !_isFiniteCoord(cw) || !_isFiniteCoord(ch)
    ) {
        return _hiddenGeometry(HIDDEN_REASONS.NON_FINITE, candidate);
    }

    // ── Guard: endpoint outside or clipped by visible canvas ──
    // The visible canvas region is [cx, cy] to [cx + cw, cy + ch].
    // An endpoint is considered outside if it lies completely
    // outside the visible bounds on any axis, or clipped if the
    // intersection is too small to be meaningful.
    var canvasRight = cx + cw;
    var canvasBottom = cy + ch;

    var cardRight = cardX + cardW;
    var cardBottom = cardY + cardH;
    var anchorRight = anchorX + anchorW;
    var anchorBottom = anchorY + anchorH;

    // Card endpoint checks
    if (
        cardRight <= cx || cardX >= canvasRight ||
        cardBottom <= cy || cardY >= canvasBottom
    ) {
        return _hiddenGeometry(HIDDEN_REASONS.OUTSIDE_CANVAS, candidate);
    }

    // Anchor endpoint checks
    if (
        anchorRight <= cx || anchorX >= canvasRight ||
        anchorBottom <= cy || anchorY >= canvasBottom
    ) {
        return _hiddenGeometry(HIDDEN_REASONS.OUTSIDE_CANVAS, candidate);
    }

    // ── Compute connector endpoints (center of each rect edge) ──
    // For both card and anchor, find the closest facing edge and
    // use its midpoint as the connector endpoint.
    var cardEndpoint = _computeClosestEdge(
        cardX, cardY, cardW, cardH,
        anchorX, anchorY, anchorW, anchorH
    );

    var anchorEndpoint = _computeClosestEdge(
        anchorX, anchorY, anchorW, anchorH,
        cardX, cardY, cardW, cardH
    );

    return {
        state: CONNECTOR_STATES.VISIBLE,
        cardEndpoint: { x: cardEndpoint.x, y: cardEndpoint.y },
        anchorEndpoint: { x: anchorEndpoint.x, y: anchorEndpoint.y },
        cardRect: _freezeRect(cardRect),
        anchorRect: _freezeRect(anchorRect),
    };
}

/**
 * Create a hidden geometry result.
 *
 * @param {string} reason
 * @param {object} [candidate]
 * @returns {object}
 * @private
 */
function _hiddenGeometry(reason, candidate) {
    return {
        state: CONNECTOR_STATES.HIDDEN,
        reason: reason,
        cardEndpoint: null,
        anchorEndpoint: null,
        cardRect: (candidate && candidate.card) ? { cardId: candidate.cardId } : null,
        anchorRect: null,
    };
}

/**
 * Test whether a coordinate value is a finite number.
 *
 * @param {*} value
 * @returns {boolean}
 * @private
 */
function _isFiniteCoord(value) {
    return typeof value === 'number' && isFinite(value);
}

/**
 * Compute the midpoint of the closest-facing edge of a source
 * rectangle toward a target rectangle.
 *
 * Returns { x, y } for the midpoint of the edge that faces the
 * target.  For horizontal separation (rects side by side), returns
 * the midpoint of the left/right edge.  For vertical separation,
 * returns the midpoint of the top/bottom edge.  When overlapping
 * on both axes, prefers horizontal.
 *
 * @param {number} sx  - Source x
 * @param {number} sy  - Source y
 * @param {number} sw  - Source width
 * @param {number} sh  - Source height
 * @param {number} tx  - Target x
 * @param {number} ty  - Target y
 * @param {number} tw  - Target width
 * @param {number} th  - Target height
 * @returns {{ x: number, y: number }}
 * @private
 */
function _computeClosestEdge(sx, sy, sw, sh, tx, ty, tw, th) {
    var sCenterX = sx + sw / 2;
    var sCenterY = sy + sh / 2;
    var tCenterX = tx + tw / 2;
    var tCenterY = ty + th / 2;

    var dx = tCenterX - sCenterX;
    var dy = tCenterY - sCenterY;

    // Determine the dominant axis: use the axis with greater
    // separation.  If rectangles overlap on one axis, the other
    // axis determines the facing edge.
    var absDx = dx >= 0 ? dx : -dx;
    var absDy = dy >= 0 ? dy : -dy;

    // Check overlap on each axis
    var overlapX = (sx < tx + tw) && (sx + sw > tx);
    var overlapY = (sy < ty + th) && (sy + sh > ty);

    if (overlapX && overlapY) {
        // Complete overlap: use vertical if dy is larger
        if (absDx >= absDy) {
            // Horizontal edge (top or bottom)
            return dy >= 0
                ? { x: sCenterX, y: sy + sh }
                : { x: sCenterX, y: sy };
        }
        // Vertical edge (left or right)
        return dx >= 0
            ? { x: sx + sw, y: sCenterY }
            : { x: sx, y: sCenterY };
    }

    if (overlapX) {
        // Overlapping on horizontal axis → use top or bottom edge
        return dy >= 0
            ? { x: sCenterX, y: sy + sh }
            : { x: sCenterX, y: sy };
    }

    if (overlapY) {
        // Overlapping on vertical axis → use left or right edge
        return dx >= 0
            ? { x: sx + sw, y: sCenterY }
            : { x: sx, y: sCenterY };
    }

    // No overlap on either axis: use the primary facing direction
    if (absDx >= absDy) {
        return dx >= 0
            ? { x: sx + sw, y: sCenterY }
            : { x: sx, y: sCenterY };
    }

    return dy >= 0
        ? { x: sCenterX, y: sy + sh }
        : { x: sCenterX, y: sy };
}

/**
 * Return a frozen subset of a DOMRect-like object (no prototype).
 *
 * @param {object} rect
 * @returns {object}
 * @private
 */
function _freezeRect(rect) {
    if (!rect) return null;
    return Object.freeze({
        x: rect.x,
        y: rect.y,
        width: rect.width,
        height: rect.height,
    });
}

// ── Exports ──

module.exports = {
    CONNECTOR_STATES: CONNECTOR_STATES,
    HIDDEN_REASONS: HIDDEN_REASONS,
    MIN_CANVAS_DIMENSION: MIN_CANVAS_DIMENSION,
    computeFocusedConnectorCandidate: computeFocusedConnectorCandidate,
    measureConnectorGeometry: measureConnectorGeometry,
};
