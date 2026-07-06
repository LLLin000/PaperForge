import { describe, it, expect } from 'vitest';

const NAV = await import('../src/canvas/navigation.js');

const {
    NAVIGATION_ACTIONS,
    SELECTION_STATUSES,
    createInitialNavState,
    reduceCardSelection,
    reduceSourceSelection,
    reduceLifecycleAction,
} = NAV;

describe('ANN13-01 — Navigation state shapes (Task 1)', () => {

    it('exports NAVIGATION_ACTIONS', () => {
        expect(NAVIGATION_ACTIONS.SELECT_CARD).toBe('select-card');
        expect(NAVIGATION_ACTIONS.SELECT_SOURCE).toBe('select-source');
        expect(NAVIGATION_ACTIONS.SELECT_PAGE_GROUP).toBe('select-page-group');
        expect(NAVIGATION_ACTIONS.CLEAR_ALL).toBe('clear-all');
        expect(NAVIGATION_ACTIONS.CLEAR_GROUP).toBe('clear-group');
        expect(NAVIGATION_ACTIONS.SET_STATUS).toBe('set-status');
        expect(NAVIGATION_ACTIONS.CLEAR_STATUS).toBe('clear-status');
        expect(NAVIGATION_ACTIONS.ESCAPE).toBe('escape');
        expect(NAVIGATION_ACTIONS.REFRESH_PRESERVE).toBe('refresh-preserve');
        expect(NAVIGATION_ACTIONS.TEARDOWN).toBe('teardown');
        expect(NAVIGATION_ACTIONS.PAPER_CHANGE).toBe('paper-change');
    });

    it('exports SELECTION_STATUSES', () => {
        expect(SELECTION_STATUSES.SELECTED).toBe('selected');
        expect(SELECTION_STATUSES.AVAILABLE).toBe('available');
        expect(SELECTION_STATUSES.UNAVAILABLE).toBe('unavailable');
        expect(SELECTION_STATUSES.PARTIAL).toBe('partial');
    });

    it('createInitialNavState returns serializable plain object', () => {
        const state = createInitialNavState();
        expect(state).toEqual({
            selectedCardId: null,
            selectedAnchorId: null,
            selectedGroupId: null,
            sourceFocusTargetId: null,
            statusMessage: null,
            navSource: null,
        });
        expect(JSON.parse(JSON.stringify(state))).toEqual(state);
    });

    it('createInitialNavState returns fresh copy each call', () => {
        const a = createInitialNavState();
        const b = createInitialNavState();
        expect(a).not.toBe(b);
    });

});

describe('ANN13-01 — Card-to-source reducers (Task 2)', () => {

    const makeCard = (overrides) => ({
        cardId: 'card-1',
        selectedText: 'cell division',
        pageIndex: 2,
        paperKey: 'PAPER_A',
        anchor: { status: 'exact', reason: 'exact match', matchCount: 1, pageIndex: 2 },
        ...overrides,
    });

    it('D-01: exact anchor sets selectedCardId + sourceFocusTargetId', () => {
        const state = createInitialNavState();
        const card = makeCard();
        const next = reduceCardSelection(state, card);
        expect(next.selectedCardId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBe('card-1');
        expect(next.navSource).toBe('card');
    });

    it('D-02: page-level anchor sets selectedCardId + page-marker sourceFocusTargetId', () => {
        const state = createInitialNavState();
        const card = makeCard({ anchor: { status: 'page-level', reason: 'page only', matchCount: 0, pageIndex: 2 } });
        const next = reduceCardSelection(state, card);
        expect(next.selectedCardId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBe('card-1');
        expect(next.navSource).toBe('card');
    });

    it('D-03: unresolved anchor sets selectedCardId only, no sourceFocusTargetId', () => {
        const state = createInitialNavState();
        const card = makeCard({ anchor: { status: 'unresolved', reason: 'no match', matchCount: 0, pageIndex: null } });
        const next = reduceCardSelection(state, card);
        expect(next.selectedCardId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBeNull();
        expect(next.navSource).toBe('card');
    });

    it('D-04: selecting a different card replaces previous selection', () => {
        const state = createInitialNavState();
        const card1 = makeCard({ cardId: 'card-A' });
        const after1 = reduceCardSelection(state, card1);
        expect(after1.selectedCardId).toBe('card-A');
        const card2 = makeCard({ cardId: 'card-B' });
        const after2 = reduceCardSelection(after1, card2);
        expect(after2.selectedCardId).toBe('card-B');
        expect(after2.sourceFocusTargetId).toBe('card-B');
    });

    it('D-05: missing anchor sets selectedCardId with statusMessage, no scroll', () => {
        const state = createInitialNavState();
        const card = makeCard({ anchor: null });
        const next = reduceCardSelection(state, card);
        expect(next.selectedCardId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBeNull();
        expect(next.statusMessage).toBeTruthy();
        expect(next.navSource).toBe('card');
    });

    it('D-06: skipScroll option suppresses sourceFocusTargetId', () => {
        const state = createInitialNavState();
        const card = makeCard();
        const next = reduceCardSelection(state, card, null, { skipScroll: true });
        expect(next.selectedCardId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBeNull();
    });

});

describe('ANN13-01 — Source-to-card reducers (Task 3)', () => {

    it('D-07: exact source target resolves one card focus target', () => {
        const state = createInitialNavState();
        const card = { cardId: 'card-1', paperKey: 'PAPER_A' };
        const next = reduceSourceSelection(state, card);
        expect(next.selectedAnchorId).toBe('card-1');
        expect(next.selectedCardId).toBe('card-1');
        expect(next.navSource).toBe('source');
    });

    it('D-08: page-level group sets selectedGroupId, not single selectedCardId', () => {
        const state = createInitialNavState();
        const group = { groupId: 'page-2', cardIds: ['card-A', 'card-B'], pageIndex: 2 };
        const next = reduceSourceSelection(state, null, { group });
        expect(next.selectedGroupId).toBe('page-2');
        expect(next.selectedCardId).toBeNull();
        expect(next.navSource).toBe('source');
    });

    it('D-09: single card focus sets navSource to source', () => {
        const state = createInitialNavState();
        const card = { cardId: 'card-1', paperKey: 'PAPER_A' };
        const next = reduceSourceSelection(state, card);
        expect(next.navSource).toBe('source');
    });

    it('D-10: unavailable card clears selection with statusMessage', () => {
        const state = createInitialNavState();
        state.selectedCardId = 'card-old';
        state.selectedAnchorId = 'card-old';
        const next = reduceSourceSelection(state, null, { unavailable: true });
        expect(next.selectedCardId).toBeNull();
        expect(next.selectedAnchorId).toBeNull();
        expect(next.statusMessage).toBeTruthy();
    });

});

describe('ANN13-01 — Lifecycle reducers (Task 4)', () => {

    const makeSelectedState = () => {
        const s = createInitialNavState();
        s.selectedCardId = 'card-1';
        s.selectedAnchorId = 'card-1';
        s.sourceFocusTargetId = 'card-1';
        s.statusMessage = 'some status';
        s.navSource = 'card';
        return s;
    };

    it('D-11: paperChange clears all state', () => {
        const next = reduceLifecycleAction(makeSelectedState(), NAVIGATION_ACTIONS.PAPER_CHANGE);
        expect(next).toEqual(createInitialNavState());
    });

    it('D-11: teardown clears all state', () => {
        const next = reduceLifecycleAction(makeSelectedState(), NAVIGATION_ACTIONS.TEARDOWN);
        expect(next).toEqual(createInitialNavState());
    });

    it('D-12: refreshPreserve preserves selectedCardId but clears scroll', () => {
        const next = reduceLifecycleAction(makeSelectedState(), NAVIGATION_ACTIONS.REFRESH_PRESERVE);
        expect(next.selectedCardId).toBe('card-1');
        expect(next.selectedAnchorId).toBe('card-1');
        expect(next.sourceFocusTargetId).toBeNull();
        expect(next.navSource).toBeNull();
    });

    it('D-13: stale clears selection with statusMessage when card gone', () => {
        const state = makeSelectedState();
        const next = reduceLifecycleAction(state, NAVIGATION_ACTIONS.CLEAR_ALL, { stale: true, cardId: 'card-1' });
        expect(next.selectedCardId).toBeNull();
        expect(next.selectedAnchorId).toBeNull();
        expect(next.statusMessage).toBeTruthy();
    });

    it('D-14: escape clears selection and status, no scroll', () => {
        const next = reduceLifecycleAction(makeSelectedState(), NAVIGATION_ACTIONS.ESCAPE);
        expect(next.selectedCardId).toBeNull();
        expect(next.selectedAnchorId).toBeNull();
        expect(next.sourceFocusTargetId).toBeNull();
        expect(next.statusMessage).toBeNull();
        expect(next.navSource).toBeNull();
    });

});

describe('ANN13-01 — Scope boundaries (D-25 / D-26 / D-27)', () => {

    it('D-25: navigation state has no mutation/connector/PDF fields', () => {
        const state = createInitialNavState();
        const keys = Object.keys(state);
        expect(keys).not.toContain('edit');
        expect(keys).not.toContain('delete');
        expect(keys).not.toContain('import');
        expect(keys).not.toContain('writeBack');
        expect(keys).not.toContain('connector');
        expect(keys).not.toContain('svg');
    });

    it('D-26: no connector geometry paths in exports', () => {
        expect(NAV).not.toHaveProperty('drawConnector');
        expect(NAV).not.toHaveProperty('renderConnector');
        expect(NAV).not.toHaveProperty('connectorGeometry');
    });

    it('D-27: no native PDF viewer DOM fields in state', () => {
        const state = createInitialNavState();
        const json = JSON.stringify(state);
        expect(json).not.toContain('pdf-viewer');
        expect(json).not.toContain('pdfEmbed');
        expect(json).not.toContain('data-page-number');
    });

});
