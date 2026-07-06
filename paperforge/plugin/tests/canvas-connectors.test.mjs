import { describe, it, expect } from 'vitest';

const CONN = await import('../src/canvas/connectors.js');

const {
    CONNECTOR_STATES,
    HIDDEN_REASONS,
    MIN_CANVAS_DIMENSION,
    computeFocusedConnectorCandidate,
    measureConnectorGeometry,
} = CONN;

// ─── Test helpers ──

function makeCard(overrides) {
    return {
        cardId: 'card-1',
        paperKey: 'PAPER_A',
        anchor: {
            status: 'exact',
            reason: null,
            matchCount: 1,
            pageIndex: 3,
        },
        ...overrides,
    };
}

function makeNav(overrides) {
    return {
        selectedCardId: 'card-1',
        selectedAnchorId: 'card-1',
        selectedGroupId: null,
        sourceFocusTargetId: 'card-1',
        statusMessage: null,
        navSource: 'card',
        ...overrides,
    };
}

function makeHover(overrides) {
    return {
        hoveredCardId: 'card-1',
        hoveredAnchorId: 'card-1',
        ...overrides,
    };
}

function makeCanvasRect(overrides) {
    return {
        x: 0,
        y: 0,
        width: 800,
        height: 600,
        ...overrides,
    };
}

function makeCardRect(overrides) {
    return {
        x: 20,
        y: 100,
        width: 280,
        height: 80,
        ...overrides,
    };
}

function makeAnchorRect(overrides) {
    return {
        x: 500,
        y: 100,
        width: 280,
        height: 80,
        ...overrides,
    };
}

// ─── Task 1: Exact-only connector eligibility ──

describe('ANN14-01 — Connector constants (Task 1)', () => {

    it('exports CONNECTOR_STATES with VISIBLE and HIDDEN', () => {
        expect(CONNECTOR_STATES.VISIBLE).toBe('visible');
        expect(CONNECTOR_STATES.HIDDEN).toBe('hidden');
        expect(Object.freeze(CONNECTOR_STATES)).toBe(CONNECTOR_STATES);
    });

    it('exports HIDDEN_REASONS with all expected entries', () => {
        expect(HIDDEN_REASONS.PAGE_LEVEL).toBe('page-level');
        expect(HIDDEN_REASONS.UNRESOLVED).toBe('unresolved');
        expect(HIDDEN_REASONS.SOURCE_UNAVAILABLE).toBe('source-unavailable');
        expect(HIDDEN_REASONS.UNSUPPORTED).toBe('unsupported');
        expect(HIDDEN_REASONS.MISSING_CARD).toBe('missing-card');
        expect(HIDDEN_REASONS.MISSING_ANCHOR).toBe('missing-anchor');
        expect(HIDDEN_REASONS.MISSING_DOM).toBe('missing-dom');
        expect(HIDDEN_REASONS.MISMATCHED_IDS).toBe('mismatched-ids');
        expect(HIDDEN_REASONS.NO_FOCUS).toBe('no-focus');
        expect(HIDDEN_REASONS.STALE).toBe('stale');
        expect(HIDDEN_REASONS.MISSING_NAV_STATE).toBe('missing-nav-state');
        expect(HIDDEN_REASONS.MISSING_CARD_LIST).toBe('missing-card-list');
    });

    it('constants are frozen (serializable plain objects)', () => {
        expect(Object.isFrozen(CONNECTOR_STATES)).toBe(true);
        expect(Object.isFrozen(HIDDEN_REASONS)).toBe(true);
    });

});

describe('ANN14-01 — Exact selected pairs return visible candidates (Task 1)', () => {

    it('D-03: exact anchor with selected nav returns visible candidate (card-1)', () => {
        const card = makeCard();
        const input = {
            navState: makeNav(),
            cards: [card],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        expect(result.cardId).toBe('card-1');
        expect(result.anchorId).toBe('card-1');
        expect(result.reason).toBeNull();
        expect(result.card).toBe(card);
        expect(result.anchor).toBe(card.anchor);
    });

    it('D-03: exact anchor in first card of multiple resolves correctly', () => {
        const cardA = makeCard({ cardId: 'card-A', anchor: { status: 'exact', reason: null, matchCount: 1, pageIndex: 2 } });
        const cardB = makeCard({ cardId: 'card-B' });
        const input = {
            navState: makeNav({ selectedCardId: 'card-B', selectedAnchorId: 'card-B' }),
            cards: [cardA, cardB],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        expect(result.cardId).toBe('card-B');
    });

    it('output is serializable plain object with no DOM refs', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        const json = JSON.parse(JSON.stringify(result));
        expect(json).toEqual({
            state: 'visible',
            cardId: 'card-1',
            anchorId: 'card-1',
            reason: null,
            card: { cardId: 'card-1', paperKey: 'PAPER_A', anchor: { status: 'exact', reason: null, matchCount: 1, pageIndex: 3 } },
            anchor: { status: 'exact', reason: null, matchCount: 1, pageIndex: 3 },
        });
    });

});

describe('ANN14-01 — Exact hovered pairs return visible candidates (Task 1)', () => {

    it('prefers selected state over hover when both present', () => {
        // Hover has card-B, selected has card-1
        const card1 = makeCard({ cardId: 'card-1' });
        const input = {
            navState: makeNav({ selectedCardId: 'card-1', selectedAnchorId: 'card-1' }),
            hoverState: makeHover({ hoveredCardId: 'card-2', hoveredAnchorId: 'card-2' }),
            cards: [card1, makeCard({ cardId: 'card-2' })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        expect(result.cardId).toBe('card-1');
    });

    it('uses hover state when selected state is empty', () => {
        const card2 = makeCard({ cardId: 'card-2' });
        const input = {
            navState: makeNav({ selectedCardId: null, selectedAnchorId: null }),
            hoverState: makeHover({ hoveredCardId: 'card-2', hoveredAnchorId: 'card-2' }),
            cards: [makeCard({ cardId: 'card-1' }), card2],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        expect(result.cardId).toBe('card-2');
    });

    it('returns no-focus when both selected and hover are empty', () => {
        const input = {
            navState: makeNav({ selectedCardId: null, selectedAnchorId: null }),
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NO_FOCUS);
    });

});

describe('ANN14-01 — Page-level and unresolved return hidden (D-01/D-02) (Task 1)', () => {

    it('D-01: page-level anchor returns hidden with PAGE_LEVEL reason', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ anchor: { status: 'page-level', reason: 'page only', matchCount: 0, pageIndex: 2 } })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.PAGE_LEVEL);
        expect(result.card).toBeNull();
    });

    it('D-02: unresolved anchor returns hidden with UNRESOLVED reason', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ anchor: { status: 'unresolved', reason: 'no match', matchCount: 0, pageIndex: null } })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.UNRESOLVED);
        expect(result.card).toBeNull();
    });

    it('source-unavailable anchor returns hidden with SOURCE_UNAVAILABLE reason', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ anchor: { status: 'source-unavailable', reason: 'No source content.' } })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.SOURCE_UNAVAILABLE);
    });

});

describe('ANN14-01 — Missing, stale, and mismatched return hidden (Task 1)', () => {

    it('missing-card when cardId does not appear in card list', () => {
        const input = {
            navState: makeNav({ selectedCardId: 'card-nonexistent', selectedAnchorId: 'card-nonexistent' }),
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_CARD);
        expect(result.cardId).toBe('card-nonexistent');
    });

    it('missing-anchor when card has no anchor property', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ anchor: null })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_ANCHOR);
    });

    it('stale when paperKey mismatches', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ paperKey: 'PAPER_B' })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.STALE);
    });

    it('mismatched-ids when selectedCardId differs from selectedAnchorId', () => {
        const input = {
            navState: makeNav({ selectedCardId: 'card-1', selectedAnchorId: 'card-2' }),
            cards: [makeCard({ cardId: 'card-1' }), makeCard({ cardId: 'card-2' })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISMATCHED_IDS);
    });

    it('missing-nav-state when navState is null', () => {
        const input = {
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_NAV_STATE);
    });

    it('missing-card-list when cards is empty array', () => {
        const input = {
            navState: makeNav(),
            cards: [],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_CARD_LIST);
    });

    it('missing-card-list when cards is null', () => {
        const input = {
            navState: makeNav(),
            cards: null,
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_CARD_LIST);
    });

    it('hidden candidates have no card/anchor geometry', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard({ anchor: { status: 'page-level', reason: 'page only', matchCount: 0, pageIndex: 2 } })],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        expect(result.card).toBeNull();
        expect(result.anchor).toBeNull();
        const json = JSON.stringify(result);
        expect(json).not.toContain('x');
        expect(json).not.toContain('y');
        expect(json).not.toContain('width');
        expect(json).not.toContain('height');
    });

});

// ─── Task 2: Conservative DOMRect geometry ──

describe('ANN14-01 — MIN_CANVAS_DIMENSION constant (Task 2)', () => {

    it('exports MIN_CANVAS_DIMENSION as a positive number', () => {
        expect(MIN_CANVAS_DIMENSION).toBeGreaterThan(0);
        expect(typeof MIN_CANVAS_DIMENSION).toBe('number');
    });

});

describe('ANN14-01 — Valid left/right geometry (Task 2)', () => {

    it('visible candidate with valid rects returns visible geometry', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        expect(result.cardEndpoint).toBeTruthy();
        expect(result.anchorEndpoint).toBeTruthy();
        expect(typeof result.cardEndpoint.x).toBe('number');
        expect(typeof result.cardEndpoint.y).toBe('number');
        expect(typeof result.anchorEndpoint.x).toBe('number');
        expect(typeof result.anchorEndpoint.y).toBe('number');
    });

    it('returns frozen rects in output', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(Object.isFrozen(result.cardRect)).toBe(true);
        expect(Object.isFrozen(result.anchorRect)).toBe(true);
    });

    it('card left of anchor produces card endpoint at right edge', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ x: 0, y: 0, width: 800, height: 600 }),
            cardRect: makeCardRect({ x: 20, y: 100, width: 280, height: 80 }),
            anchorRect: makeAnchorRect({ x: 500, y: 100, width: 280, height: 80 }),
        };
        const result = measureConnectorGeometry(input);
        // Card is left of anchor → cardEndpoint should be on the right edge
        expect(result.cardEndpoint.x).toBe(20 + 280);
        expect(result.cardEndpoint.y).toBe(100 + 80 / 2);
    });

    it('output is serializable plain object', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        const json = JSON.parse(JSON.stringify(result));
        expect(json.state).toBe('visible');
        expect(json.cardEndpoint.x).toBeGreaterThanOrEqual(0);
        expect(json.anchorEndpoint.x).toBeGreaterThanOrEqual(0);
    });

});

describe('ANN14-01 — Zero-size and missing rectangles return hidden (Task 2)', () => {

    it('zero-size card rect returns hidden with ZERO_SIZE reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect({ width: 0, height: 80 }),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.ZERO_SIZE);
    });

    it('negative card height returns hidden with ZERO_SIZE reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect({ width: 280, height: -5 }),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.ZERO_SIZE);
    });

    it('missing cardRect returns hidden with MISSING_RECT reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: null,
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_RECT);
    });

    it('missing canvasRect returns hidden with MISSING_RECT reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: null,
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_RECT);
    });

});

describe('ANN14-01 — Non-finite values return hidden (Task 2)', () => {

    it('NaN card x returns hidden with NON_FINITE reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect({ x: NaN }),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NON_FINITE);
    });

    it('Infinity anchor y returns hidden with NON_FINITE reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect({ y: Infinity }),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NON_FINITE);
    });

});

describe('ANN14-01 — Outside and clipped canvas return hidden (Task 2)', () => {

    it('card entirely left of canvas returns hidden with OUTSIDE_CANVAS', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ x: 100, y: 0, width: 800, height: 600 }),
            cardRect: makeCardRect({ x: 20, y: 100, width: 50, height: 80 }),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.OUTSIDE_CANVAS);
    });

    it('anchor below canvas returns hidden with OUTSIDE_CANVAS', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ x: 0, y: 0, width: 800, height: 400 }),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect({ y: 500 }),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.OUTSIDE_CANVAS);
    });

});

describe('ANN14-01 — Narrow canvas returns hidden (Task 2)', () => {

    it('canvas narrower than MIN_CANVAS_DIMENSION returns hidden', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: 30, height: 600 }),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NARROW_CANVAS);
    });

    it('canvas shorter than MIN_CANVAS_DIMENSION returns hidden', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: 800, height: 20 }),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NARROW_CANVAS);
    });

});

// ─── ANN14-04 Task 1: Boundary conditions around MIN_CANVAS_DIMENSION ──

function makeFittingCardRect(overrides) {
    return { x: 2, y: 2, width: 20, height: 10, ...overrides };
}

function makeFittingAnchorRect(overrides) {
    return { x: 28, y: 2, width: 20, height: 10, ...overrides };
}

function makeFittingTallCardRect(overrides) {
    return { x: 100, y: 2, width: 100, height: 20, ...overrides };
}

function makeFittingTallAnchorRect(overrides) {
    return { x: 400, y: 2, width: 100, height: 20, ...overrides };
}

describe('ANN14-04 — Narrow-canvas boundary conditions (Task 1)', () => {

    it('canvas just above MIN_CANVAS_DIMENSION width returns visible', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: MIN_CANVAS_DIMENSION + 1, height: 600 }),
            cardRect: makeFittingCardRect(),
            anchorRect: makeFittingAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
        // visible state has no reason set
    });

    it('canvas just below MIN_CANVAS_DIMENSION width returns hidden with NARROW_CANVAS', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: MIN_CANVAS_DIMENSION - 1, height: 600 }),
            cardRect: makeFittingCardRect(),
            anchorRect: makeFittingAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NARROW_CANVAS);
    });

    it('both dimensions below threshold returns hidden with NARROW_CANVAS', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: 30, height: 20 }),
            cardRect: makeFittingCardRect(),
            anchorRect: makeFittingAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NARROW_CANVAS);
    });

    it('canvas exactly MIN_CANVAS_DIMENSION height with fitting rects returns visible', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: 800, height: MIN_CANVAS_DIMENSION }),
            cardRect: makeFittingTallCardRect(),
            anchorRect: makeFittingTallAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.VISIBLE);
    });

    it('canvas just below MIN_CANVAS_DIMENSION height returns hidden with NARROW_CANVAS', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect({ width: 800, height: MIN_CANVAS_DIMENSION - 1 }),
            cardRect: makeFittingTallCardRect(),
            anchorRect: makeFittingTallAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.NARROW_CANVAS);
    });

});

describe('ANN14-01 — Hidden candidate input returns hidden (Task 2)', () => {

    it('hidden candidate returns hidden geometry with HIDDEN_CANDIDATE reason', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.HIDDEN,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: HIDDEN_REASONS.PAGE_LEVEL,
                card: null,
                anchor: null,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.PAGE_LEVEL);
    });

    it('null candidate returns hidden with HIDDEN_CANDIDATE reason', () => {
        const input = {
            candidate: null,
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.HIDDEN_CANDIDATE);
    });

    it('undefined candidate returns hidden with HIDDEN_CANDIDATE reason', () => {
        const input = {
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.HIDDEN_CANDIDATE);
    });

});

describe('ANN14-01 — Input guards (Task 2)', () => {

    it('null input returns hidden', () => {
        const result = measureConnectorGeometry(null);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_RECT);
    });

    it('undefined input returns hidden', () => {
        const result = measureConnectorGeometry(undefined);
        expect(result.state).toBe(CONNECTOR_STATES.HIDDEN);
        expect(result.reason).toBe(HIDDEN_REASONS.MISSING_RECT);
    });

});

// ─── Task 3: Serializable contract (no DOM refs, no timers, no Obsidian objects) ──

describe('ANN14-01 — Serialization contract (Task 3)', () => {

    it('visible candidate JSON-serializes without data loss', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        const json = JSON.parse(JSON.stringify(result));
        expect(json.state).toBe('visible');
        expect(json.cardId).toBe('card-1');
        expect(json.reason).toBeNull();
        expect(json.card).toBeTruthy();
        expect(json.anchor).toBeTruthy();
    });

    it('visible geometry JSON-serializes without data loss', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        const json = JSON.parse(JSON.stringify(result));
        expect(json.state).toBe('visible');
        expect(json.cardEndpoint).toBeTruthy();
        expect(json.anchorEndpoint).toBeTruthy();
        expect(json.cardRect).toBeTruthy();
        expect(json.anchorRect).toBeTruthy();
    });

    it('geometry output has no DOM refs, timers, or Obsidian objects', () => {
        const input = {
            candidate: {
                state: CONNECTOR_STATES.VISIBLE,
                cardId: 'card-1',
                anchorId: 'card-1',
                reason: null,
                card: makeCard(),
                anchor: makeCard().anchor,
            },
            canvasRect: makeCanvasRect(),
            cardRect: makeCardRect(),
            anchorRect: makeAnchorRect(),
        };
        const result = measureConnectorGeometry(input);
        const keys = Object.keys(result);
        expect(keys).not.toContain('domRef');
        expect(keys).not.toContain('timer');
        expect(keys).not.toContain('obsidian');
        expect(keys).not.toContain('setTimeout');
        expect(keys).not.toContain('interval');
        expect(keys).not.toContain('persist');
        expect(keys).not.toContain('writeBack');
        expect(result.cardEndpoint).not.toHaveProperty('domRef');
        expect(result.anchorEndpoint).not.toHaveProperty('domRef');
    });

    it('candidate output has no DOM refs, timers, or Obsidian objects', () => {
        const input = {
            navState: makeNav(),
            cards: [makeCard()],
            paperKey: 'PAPER_A',
        };
        const result = computeFocusedConnectorCandidate(input);
        const keys = Object.keys(result);
        expect(keys).not.toContain('domRef');
        expect(keys).not.toContain('timer');
        expect(keys).not.toContain('obsidian');
        expect(keys).not.toContain('setTimeout');
        expect(keys).not.toContain('interval');
        expect(keys).not.toContain('persist');
        expect(keys).not.toContain('writeBack');
    });

});

describe('ANN14-01 — No anchor resolver imports (Task 3)', () => {

    it('connectors module does not export resolveCanvasAnchor', () => {
        expect(CONN).not.toHaveProperty('resolveCanvasAnchor');
        expect(CONN).not.toHaveProperty('resolveCanvasAnchors');
    });

    it('exports only narrow ANN14 helper surface', () => {
        // CJS → ESM import adds `default` and `module.exports` keys
        const exportedKeys = Object.keys(CONN.default || CONN);
        expect(exportedKeys).toContain('CONNECTOR_STATES');
        expect(exportedKeys).toContain('HIDDEN_REASONS');
        expect(exportedKeys).toContain('MIN_CANVAS_DIMENSION');
        expect(exportedKeys).toContain('computeFocusedConnectorCandidate');
        expect(exportedKeys).toContain('measureConnectorGeometry');
        expect(exportedKeys.length).toBe(5);
    });

});
