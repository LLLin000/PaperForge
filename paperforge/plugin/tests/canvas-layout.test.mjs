/**
 * Vitest tests for deterministic reading-order side-lane layout (Phase ANN11, Plan 01).
 *
 * Tests cover:
 *   Task 2 — compareCanvasCardsByReadingOrder: matches existing sort algorithm
 *   Task 2 — sortCanvasCardsForReadingOrder: page → sortIndex → identity
 *   Task 2 — assignCanvasCardsToLanes: left/right alternation, balanced lanes,
 *            deterministic, no persistence
 *
 * @module tests/canvas-layout
 */

import { describe, it, expect } from 'vitest';

const {
    compareCanvasCardsByReadingOrder,
    sortCanvasCardsForReadingOrder,
    assignCanvasCardsToLanes,
} = await import('../src/canvas/layout.js');

const {
    normalizeAnnotationExportRow,
    sortAnnotationsForReadingOrder,
    getAnnotationIdentity,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/** Shorthand: create a normalized annotation row directly. */
function makeRow(overrides = {}) {
    const raw = {
        id: 'ann-' + (overrides.id || '1'),
        paper_id: 'PAPER_A',
        source: 'zotero',
        source_library_id: '1',
        source_annotation_key: 'ann-' + (overrides.id || '1'),
        source_attachment_key: 'ATTACH_A',
        source_parent_key: 'PARENT_A',
        source_modified_at: '2024-01-15T10:00:00Z',
        type: overrides.type || 'highlight',
        page_index: overrides.page_index != null ? overrides.page_index : 0,
        page_label: overrides.page_label != null ? String(overrides.page_label) : '1',
        selected_text: overrides.selected_text || 'selected text',
        comment: overrides.comment || '',
        color: overrides.color || '#ffd400',
        sort_index: overrides.sort_index != null ? overrides.sort_index : 0,
        tags_json: '[]',
        position_json: '{}',
        selector_json: '{}',
        sync_state: 'imported',
        is_readonly: 0,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        deleted_at: null,
        ...overrides,
    };
    return normalizeAnnotationExportRow(raw);
}

/** Build card objects from rows (minimal card shape needed for layout tests). */
function makeCardFromRow(row) {
    const d = row.display || {};
    const loc = row.pdfLocation || {};
    const p = row.provenance || {};
    return {
        id: getAnnotationIdentity(row),
        pageIndex: loc.pageIndex != null ? loc.pageIndex : null,
        sortIndex: loc.sortIndex != null ? loc.sortIndex : null,
        type: d.type || 'annotation',
        color: d.color != null ? d.color : null,
        source: p.source || 'unknown',
        sourceAttachmentKey: p.sourceAttachmentKey || '',
    };
}

// Standard rows for testing
const rowPage0a = makeRow({ id: 'r1', page_index: 0, page_label: '1', sort_index: 0, selected_text: 'alpha' });
const rowPage0b = makeRow({ id: 'r2', page_index: 0, page_label: '1', sort_index: 1, selected_text: 'beta' });
const rowPage0c = makeRow({ id: 'r3', page_index: 0, page_label: '1', sort_index: 2, selected_text: 'gamma' });
const rowPage1a = makeRow({ id: 'r4', page_index: 1, page_label: '2', sort_index: 0, selected_text: 'delta' });
const rowPage1b = makeRow({ id: 'r5', page_index: 1, page_label: '2', sort_index: 1, selected_text: 'epsilon' });
const rowPage2a = makeRow({ id: 'r6', page_index: 2, page_label: '3', sort_index: 0, selected_text: 'zeta' });

const allRows = [rowPage0a, rowPage0b, rowPage0c, rowPage1a, rowPage1b, rowPage2a];

const cardPage0a = makeCardFromRow(rowPage0a);
const cardPage0b = makeCardFromRow(rowPage0b);
const cardPage0c = makeCardFromRow(rowPage0c);
const cardPage1a = makeCardFromRow(rowPage1a);
const cardPage1b = makeCardFromRow(rowPage1b);
const cardPage2a = makeCardFromRow(rowPage2a);

const allCards = [cardPage0a, cardPage0b, cardPage0c, cardPage1a, cardPage1b, cardPage2a];

// ---------------------------------------------------------------------------
// Task 2: compareCanvasCardsByReadingOrder (D-05 / CARD-03)
// ---------------------------------------------------------------------------

describe('compareCanvasCardsByReadingOrder — parity with sortAnnotationsForReadingOrder (D-05)', () => {
    it('sorts cards by page ascending, then sortIndex', () => {
        const unsorted = [cardPage2a, cardPage0c, cardPage1a, cardPage0a];
        const sorted = unsorted.slice().sort(compareCanvasCardsByReadingOrder);
        expect(sorted[0].id).toBe(cardPage0a.id);
        expect(sorted[1].id).toBe(cardPage0c.id);
        expect(sorted[2].id).toBe(cardPage1a.id);
        expect(sorted[3].id).toBe(cardPage2a.id);
    });

    it('matches sortAnnotationsForReadingOrder result for the same rows', () => {
        const unsortedRows = [rowPage2a, rowPage0c, rowPage1a, rowPage0a];
        const layoutSorted = unsortedRows.slice().sort(compareCanvasCardsByReadingOrder);
        const expectedSorted = sortAnnotationsForReadingOrder(unsortedRows);
        expect(layoutSorted.length).toBe(expectedSorted.length);
        for (let i = 0; i < layoutSorted.length; i++) {
            expect(layoutSorted[i].display.selectedText).toBe(expectedSorted[i].display.selectedText);
            expect(layoutSorted[i].pdfLocation.pageIndex).toBe(expectedSorted[i].pdfLocation.pageIndex);
        }
    });

    it('sorts same-page same-sortIndex cards by stable identity', () => {
        const a = makeRow({ id: 'ann-a', page_index: 0, sort_index: 0, selected_text: 'A' });
        const b = makeRow({ id: 'ann-b', page_index: 0, sort_index: 0, selected_text: 'B' });
        const result = [b, a].sort(compareCanvasCardsByReadingOrder);
        expect(result[0].display.selectedText).toBe('A');
        expect(result[1].display.selectedText).toBe('B');
    });

    it('sorts null pageIndex cards last', () => {
        const noPage = makeRow({ id: 'no-page', page_index: null, sort_index: 0, selected_text: 'no page' });
        const result = [noPage, rowPage0a].sort(compareCanvasCardsByReadingOrder);
        expect(result[0].pdfLocation.pageIndex).toBe(0);
        expect(result[1].pdfLocation.pageIndex).toBeNull();
    });

    it('sorts null sortIndex after same-page cards with sortIndex', () => {
        const noSort = makeRow({ id: 'no-sort', page_index: 0, sort_index: null, selected_text: 'no sort' });
        const result = [noSort, rowPage0a].sort(compareCanvasCardsByReadingOrder);
        expect(result[0].pdfLocation.sortIndex).toBe(0);
        expect(result[1].pdfLocation.sortIndex).toBeNull();
    });

    it('returns 0 for the same card compared to itself', () => {
        expect(compareCanvasCardsByReadingOrder(rowPage0a, rowPage0a)).toBe(0);
    });

    it('returns negative when first card precedes second', () => {
        expect(compareCanvasCardsByReadingOrder(rowPage0a, rowPage1a)).toBeLessThan(0);
    });

    it('returns positive when first card follows second', () => {
        expect(compareCanvasCardsByReadingOrder(rowPage1a, rowPage0a)).toBeGreaterThan(0);
    });
});

// ---------------------------------------------------------------------------
// Task 2: sortCanvasCardsForReadingOrder (D-05 / D-06)
// ---------------------------------------------------------------------------

describe('sortCanvasCardsForReadingOrder (D-05 / D-06)', () => {
    it('sorts cards by page ascending, then sortIndex, then identity', () => {
        const unsorted = [cardPage2a, cardPage0c, cardPage1a, cardPage0a];
        const sorted = sortCanvasCardsForReadingOrder(unsorted);
        expect(sorted[0].id).toBe(cardPage0a.id);
        expect(sorted[1].id).toBe(cardPage0c.id);
        expect(sorted[2].id).toBe(cardPage1a.id);
        expect(sorted[3].id).toBe(cardPage2a.id);
    });

    it('preserves existing sort order metadata when available (D-06)', () => {
        // Same page but different sort indices should preserve that order
        const unsorted = [cardPage0c, cardPage0a, cardPage0b];
        const sorted = sortCanvasCardsForReadingOrder(unsorted);
        expect(sorted[0].id).toBe(cardPage0a.id); // sort_index=0 first
        expect(sorted[1].id).toBe(cardPage0b.id); // sort_index=1
        expect(sorted[2].id).toBe(cardPage0c.id); // sort_index=2
    });

    it('falls back to stable identity when sortIndex is missing (D-06)', () => {
        const a = makeRow({ id: 'z-ann', page_index: 0, sort_index: null, selected_text: 'Z identity' });
        const b = makeRow({ id: 'a-ann', page_index: 0, sort_index: null, selected_text: 'A identity' });
        const result = sortCanvasCardsForReadingOrder([a, b]);
        // Should sort by stable identity
        expect(result[0].display.selectedText).toBe('A identity');
        expect(result[1].display.selectedText).toBe('Z identity');
    });

    it('does not mutate the input array', () => {
        const original = [...allCards];
        const copy = [...allCards];
        sortCanvasCardsForReadingOrder(allCards);
        expect(allCards).toEqual(copy);
    });

    it('returns empty array for empty input', () => {
        expect(sortCanvasCardsForReadingOrder([])).toEqual([]);
    });

    it('matches sortAnnotationsForReadingOrder for the same rows', () => {
        const unsortedRows = [rowPage2a, rowPage0c, rowPage1a, rowPage0a];
        const layoutSortedRows = sortCanvasCardsForReadingOrder(unsortedRows);
        const expectedSorted = sortAnnotationsForReadingOrder(unsortedRows);
        expect(layoutSortedRows.length).toBe(expectedSorted.length);
        for (let i = 0; i < layoutSortedRows.length; i++) {
            expect(layoutSortedRows[i].display.selectedText).toBe(expectedSorted[i].display.selectedText);
            expect(layoutSortedRows[i].pdfLocation.pageIndex).toBe(expectedSorted[i].pdfLocation.pageIndex);
        }
    });
});

// ---------------------------------------------------------------------------
// Task 2: assignCanvasCardsToLanes (D-07 / D-08 / D-09)
// ---------------------------------------------------------------------------

describe('assignCanvasCardsToLanes — alternation (D-07)', () => {
    it('returns an object with left and right arrays', () => {
        const result = assignCanvasCardsToLanes(allCards);
        expect(result).toHaveProperty('left');
        expect(result).toHaveProperty('right');
        expect(Array.isArray(result.left)).toBe(true);
        expect(Array.isArray(result.right)).toBe(true);
    });

    it('alternates cards: even index → left, odd index → right', () => {
        const result = assignCanvasCardsToLanes(allCards);
        // With default sorting, page 0 sort 0 goes left, page 0 sort 1 goes right, etc.
        expect(result.left[0].id).toBe(cardPage0a.id);   // index 0 → left
        expect(result.right[0].id).toBe(cardPage0b.id);  // index 1 → right
        expect(result.left[1].id).toBe(cardPage0c.id);   // index 2 → left
        expect(result.right[1].id).toBe(cardPage1a.id);  // index 3 → right
        expect(result.left[2].id).toBe(cardPage1b.id);   // index 4 → left
        expect(result.right[2].id).toBe(cardPage2a.id);  // index 5 → right
    });

    it('preserves reading order within each lane', () => {
        const result = assignCanvasCardsToLanes(allCards);
        // Left lane: indices 0, 2, 4
        expect(result.left[0].id).toBe(cardPage0a.id);
        expect(result.left[1].id).toBe(cardPage0c.id);
        expect(result.left[2].id).toBe(cardPage1b.id);
        // Right lane: indices 1, 3, 5
        expect(result.right[0].id).toBe(cardPage0b.id);
        expect(result.right[1].id).toBe(cardPage1a.id);
        expect(result.right[2].id).toBe(cardPage2a.id);
    });

    it('produces balanced lanes for odd card count', () => {
        const oddCards = allCards.slice(0, 5); // 5 cards
        const result = assignCanvasCardsToLanes(oddCards);
        // Left: indices 0,2,4 → 3 cards; Right: indices 1,3 → 2 cards
        expect(result.left.length).toBe(3);
        expect(result.right.length).toBe(2);
    });

    it('produces balanced lanes for even card count', () => {
        const result = assignCanvasCardsToLanes(allCards); // 6 cards
        expect(result.left.length).toBe(3);
        expect(result.right.length).toBe(3);
    });

    it('single card goes to left lane', () => {
        const result = assignCanvasCardsToLanes([cardPage0a]);
        expect(result.left.length).toBe(1);
        expect(result.right.length).toBe(0);
    });

    it('two cards alternate left then right', () => {
        const result = assignCanvasCardsToLanes([cardPage0a, cardPage0b]);
        expect(result.left.length).toBe(1);
        expect(result.right.length).toBe(1);
        expect(result.left[0].id).toBe(cardPage0a.id);
        expect(result.right[0].id).toBe(cardPage0b.id);
    });

    it('returns empty lanes for empty input', () => {
        const result = assignCanvasCardsToLanes([]);
        expect(result.left).toEqual([]);
        expect(result.right).toEqual([]);
    });
});

describe('assignCanvasCardsToLanes — lane and laneIndex (D-07)', () => {
    it('sets lane property on each card', () => {
        const result = assignCanvasCardsToLanes(allCards);
        for (const card of result.left) {
            expect(card).toHaveProperty('lane');
            expect(card.lane).toBe('left');
        }
        for (const card of result.right) {
            expect(card).toHaveProperty('lane');
            expect(card.lane).toBe('right');
        }
    });

    it('sets laneIndex property on each card', () => {
        const result = assignCanvasCardsToLanes(allCards);
        expect(result.left[0].laneIndex).toBe(0);
        expect(result.left[1].laneIndex).toBe(1);
        expect(result.left[2].laneIndex).toBe(2);
        expect(result.right[0].laneIndex).toBe(0);
        expect(result.right[1].laneIndex).toBe(1);
        expect(result.right[2].laneIndex).toBe(2);
    });
});

describe('assignCanvasCardsToLanes — deterministic (D-08 / D-09)', () => {
    it('returns identical results for the same input', () => {
        const result1 = assignCanvasCardsToLanes(allCards);
        const result2 = assignCanvasCardsToLanes(allCards);
        expect(result1).toEqual(result2);
    });

    it('returns identical results across multiple calls', () => {
        for (let i = 0; i < 10; i++) {
            const result = assignCanvasCardsToLanes(allCards);
            expect(result.left.length).toBe(3);
            expect(result.right.length).toBe(3);
            expect(result.left[0].id).toBe(cardPage0a.id);
            expect(result.right[0].id).toBe(cardPage0b.id);
        }
    });

    it('does not use random or persisted state (D-08)', () => {
        // Verify no random-looking patterns: same input always produces same output
        const result1 = assignCanvasCardsToLanes(allCards);
        const result2 = assignCanvasCardsToLanes(allCards);
        const result3 = assignCanvasCardsToLanes(allCards);
        expect(result1).toEqual(result2);
        expect(result2).toEqual(result3);
    });
});

describe('assignCanvasCardsToLanes — no mutation (D-08)', () => {
    it('does not mutate the input array', () => {
        const original = [...allCards];
        const copy = original.map(c => ({ ...c }));
        assignCanvasCardsToLanes(copy);
        // Input properties should be unchanged (lane/laneIndex are added to copies)
        for (const card of copy) {
            expect(card).not.toHaveProperty('lane');
            expect(card).not.toHaveProperty('laneIndex');
        }
    });

    it('lane and laneIndex are set on derived copies, not input objects', () => {
        const input = allCards.map(c => ({ ...c }));
        const result = assignCanvasCardsToLanes(input);
        // Original objects should not have lane/laneIndex
        for (const card of input) {
            expect(card).not.toHaveProperty('lane');
            expect(card).not.toHaveProperty('laneIndex');
        }
        // But result cards should
        for (const card of result.left) {
            expect(card).toHaveProperty('lane');
            expect(card).toHaveProperty('laneIndex');
        }
    });
});

describe('assignCanvasCardsToLanes — no persistence (D-08)', () => {
    it('does not contain localStorage/plugin settings/session fields', () => {
        const result = assignCanvasCardsToLanes(allCards);
        const keys = Object.keys(result);
        expect(keys).not.toContain('settings');
        expect(keys).not.toContain('persisted');
        expect(keys).not.toContain('saved');
        expect(keys).not.toContain('draggable');
        expect(keys).not.toContain('random');
    });

    it('lane result has no unexpected persistence fields', () => {
        const result = assignCanvasCardsToLanes(allCards);
        const json = JSON.stringify(result).toLowerCase();
        expect(json).not.toContain('localstorage');
        expect(json).not.toContain('persist');
        expect(json).not.toContain('draggable');
        expect(json).not.toContain('.canvas');
    });
});

// ---------------------------------------------------------------------------
// Task 2: Reading-order then alternation integration
// ---------------------------------------------------------------------------

describe('reading-order sort then lane assignment', () => {
    it('sorts then assigns lanes by alternation', () => {
        // Rows in reverse page order
        const unsortedCards = [cardPage2a, cardPage1b, cardPage1a, cardPage0c, cardPage0b, cardPage0a];
        const sorted = sortCanvasCardsForReadingOrder(unsortedCards);
        expect(sorted[0].id).toBe(cardPage0a.id);
        expect(sorted[1].id).toBe(cardPage0b.id);
        expect(sorted[2].id).toBe(cardPage0c.id);

        const lanes = assignCanvasCardsToLanes(sorted);
        expect(lanes.left[0].id).toBe(cardPage0a.id);
        expect(lanes.right[0].id).toBe(cardPage0b.id);
        expect(lanes.left[1].id).toBe(cardPage0c.id);
        expect(lanes.right[1].id).toBe(cardPage1a.id);
    });

    it('works with cards that have missing page/sortIndex', () => {
        const noPageCard = makeCardFromRow(makeRow({ id: 'no-page', page_index: null, sort_index: null }));
        const cards = [cardPage0a, noPageCard, cardPage0b];
        const sorted = sortCanvasCardsForReadingOrder(cards);
        expect(sorted.length).toBe(3);
        const lanes = assignCanvasCardsToLanes(sorted);
        expect(lanes.left.length + lanes.right.length).toBe(3);
    });
});
