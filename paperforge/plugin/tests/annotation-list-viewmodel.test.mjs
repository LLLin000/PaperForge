/**
 * Vitest tests for annotation list view-model helpers.
 *
 * Tests cover:
 *   Sorting, grouping, filtering, search, preview, expansion,
 *   stale-refresh merge, and render-state view-model decisions.
 *
 * All helpers are pure: no DOM, no Obsidian APIs, no CLI calls.
 */
import { describe, it, expect, vi } from 'vitest';

const {
    // Task 1 — helpers
    createDefaultAnnotationListUiState,
    getAnnotationIdentity,
    sortAnnotationsForReadingOrder,
    groupAnnotationRows,
    buildAnnotationFilterOptions,
    matchesAnnotationSearch,
    matchesAnnotationTypeColorFilter,
    // Task 2 — helpers
    getAnnotationPreview,
    toggleAnnotationExpansion,
    buildAnnotationListViewModel,
    mergeAnnotationRefreshResult,
    // Reused from Phase 5 bridge
    normalizeAnnotationExportRow,
    makeAnnotationState,
    ANNOTATION_LOAD_STATES,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Fixtures — normalized annotation rows
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

// Standard rows for testing
const rowPage0 = makeRow({ id: 'r1', page_index: 0, page_label: '1', sort_index: 0, type: 'highlight', color: '#ffd400', selected_text: 'alpha selected' });
const rowPage0b = makeRow({ id: 'r2', page_index: 0, page_label: '1', sort_index: 1, type: 'note', color: null, selected_text: 'beta selected', comment: 'beta comment' });
const rowPage1 = makeRow({ id: 'r3', page_index: 1, page_label: '2', sort_index: 0, type: 'highlight', color: '#ff6666', selected_text: 'gamma selected' });
const rowPage1b = makeRow({ id: 'r4', page_index: 1, page_label: '2', sort_index: 1, type: 'highlight', color: '#ffd400', selected_text: 'delta selected', comment: 'delta comment' });
const rowNoColor = makeRow({ id: 'r5', page_index: 2, page_label: '3', sort_index: 0, type: 'underline', color: null, selected_text: 'epsilon selected' });
const rowNoComment = makeRow({ id: 'r6', page_index: 2, page_label: '3', sort_index: 1, type: 'sticky_note', color: '#00ff00', selected_text: 'zeta selected', comment: '' });

const allRows = [rowPage0, rowPage0b, rowPage1, rowPage1b, rowNoColor, rowNoComment];

// ---------------------------------------------------------------------------
// Task 1: createDefaultAnnotationListUiState
// ---------------------------------------------------------------------------

describe('createDefaultAnnotationListUiState', () => {
    it('returns expected defaults', () => {
        const state = createDefaultAnnotationListUiState();
        expect(state).toEqual({
            query: '',
            groupMode: 'none',
            typeColorFilter: 'all',
            expandedIds: [],
        });
    });

    it('returns a fresh object on each call', () => {
        const a = createDefaultAnnotationListUiState();
        const b = createDefaultAnnotationListUiState();
        expect(a).not.toBe(b);
        expect(a).toEqual(b);
    });
});

// ---------------------------------------------------------------------------
// Task 1: getAnnotationIdentity
// ---------------------------------------------------------------------------

describe('getAnnotationIdentity', () => {
    it('returns stable identity from display or provenance fields', () => {
        const id1 = getAnnotationIdentity(rowPage0);
        expect(id1).toBeTruthy();
        expect(typeof id1).toBe('string');
    });

    it('returns consistent identity for the same row', () => {
        const id1 = getAnnotationIdentity(rowPage0);
        const id2 = getAnnotationIdentity(rowPage0);
        expect(id1).toBe(id2);
    });

    it('returns different identities for different rows', () => {
        const id1 = getAnnotationIdentity(rowPage0);
        const id2 = getAnnotationIdentity(rowPage1);
        expect(id1).not.toBe(id2);
    });

    it('falls back to a position-based identity when row lacks annotation key', () => {
        const sparseRow = makeRow({ source_annotation_key: null, id: null });
        const id = getAnnotationIdentity(sparseRow);
        expect(id).toBeTruthy();
        expect(typeof id).toBe('string');
    });
});

// ---------------------------------------------------------------------------
// Task 1: sortAnnotationsForReadingOrder
// ---------------------------------------------------------------------------

describe('sortAnnotationsForReadingOrder', () => {
    it('sorts by page ascending, then sortIndex', () => {
        const unsorted = [rowPage1, rowPage0, rowPage1b, rowPage0b];
        const sorted = sortAnnotationsForReadingOrder(unsorted);
        expect(sorted[0].pdfLocation.rowId).toBe('r1');
        expect(sorted[1].pdfLocation.rowId).toBe('r2');
        expect(sorted[2].pdfLocation.rowId).toBe('r3');
        expect(sorted[3].pdfLocation.rowId).toBe('r4');
    });

    it('same page same sortIndex uses stable identity tiebreaker', () => {
        // Create two rows with same page and same sortIndex
        const a = makeRow({ id: 'a-id', page_index: 0, sort_index: 0, selected_text: 'a text' });
        const b = makeRow({ id: 'b-id', page_index: 0, sort_index: 0, selected_text: 'b text' });
        const result = sortAnnotationsForReadingOrder([b, a]);
        // Stable order: should always be a, b based on identity
        expect(result[0].pdfLocation.rowId).toBe('a-id');
        expect(result[1].pdfLocation.rowId).toBe('b-id');
    });

    it('does not mutate the original array', () => {
        const original = [...allRows];
        const copy = [...allRows];
        sortAnnotationsForReadingOrder(allRows);
        expect(allRows).toEqual(copy);
    });

    it('returns empty array for empty input', () => {
        expect(sortAnnotationsForReadingOrder([])).toEqual([]);
    });

    it('handles rows with missing page or sortIndex gracefully', () => {
        const broken = makeRow({ id: 'broken', page_index: null, sort_index: null });
        const result = sortAnnotationsForReadingOrder([rowPage0, broken]);
        expect(result.length).toBe(2);
    });
});

// ---------------------------------------------------------------------------
// Task 1: groupAnnotationRows
// ---------------------------------------------------------------------------

describe('groupAnnotationRows', () => {
    it('returns ungrouped rows for "none" mode', () => {
        const result = groupAnnotationRows(allRows, 'none');
        expect(result.mode).toBe('none');
        expect(result.groups).toHaveLength(1);
        expect(result.groups[0].key).toBe('all');
        expect(result.groups[0].rows.length).toBe(allRows.length);
        expect(result.groups[0].rows).toEqual(allRows);
    });

    it('groups by page for "page" mode', () => {
        const result = groupAnnotationRows(allRows, 'page');
        expect(result.mode).toBe('page');
        // 3 distinct pages: 0, 1, 2
        expect(result.groups.length).toBeGreaterThanOrEqual(3);

        const keys = result.groups.map(g => g.key).sort();
        expect(keys).toContain('page-0');
        expect(keys).toContain('page-1');
        expect(keys).toContain('page-2');
    });

    it('page groups preserve reading-order sort within each group', () => {
        const result = groupAnnotationRows(allRows, 'page');
        const page0 = result.groups.find(g => g.key === 'page-0');
        expect(page0).toBeTruthy();
        const ids = page0.rows.map(r => r.pdfLocation.rowId);
        expect(ids).toEqual(['r1', 'r2']); // r1 sort_index=0, r2 sort_index=1
    });

    it('page groups have labels', () => {
        const result = groupAnnotationRows(allRows, 'page');
        for (const g of result.groups) {
            expect(g.label).toBeTruthy();
        }
    });

    it('groups by type and color for "type-color" mode', () => {
        const result = groupAnnotationRows(allRows, 'type-color');
        expect(result.mode).toBe('type-color');
        expect(result.groups.length).toBeGreaterThanOrEqual(3);

        const keys = result.groups.map(g => g.key);
        expect(keys).toContain('type-color-highlight-#ffd400');
        expect(keys).toContain('type-color-note-null');
        expect(keys).toContain('type-color-highlight-#ff6666');
    });

    it('type-color groups have labels including type and color where present', () => {
        const result = groupAnnotationRows(allRows, 'type-color');
        for (const g of result.groups) {
            expect(g.label).toBeTruthy();
        }
        // Highlight rows
        const highlightGroup = result.groups.find(g => g.key === 'type-color-highlight-#ffd400');
        expect(highlightGroup.label).toContain('highlight');
        expect(highlightGroup.label).toContain('#ffd400');
    });

    it('returns stable group order', () => {
        const result1 = groupAnnotationRows(allRows, 'page');
        const result2 = groupAnnotationRows(allRows, 'page');
        expect(result1.groups.map(g => g.key)).toEqual(result2.groups.map(g => g.key));
    });

    it('returns empty groups for empty rows', () => {
        const result = groupAnnotationRows([], 'none');
        expect(result.groups).toHaveLength(1);
        expect(result.groups[0].rows).toEqual([]);
    });

    it('correctly handles null color rows in type-color grouping', () => {
        const rows = [
            makeRow({ id: 'na', page_index: 0, type: 'highlight', color: null, selected_text: 'no color' }),
            makeRow({ id: 'nb', page_index: 0, type: 'highlight', color: '#ffd400', selected_text: 'has color' }),
        ];
        const result = groupAnnotationRows(rows, 'type-color');
        const keys = result.groups.map(g => g.key);
        expect(keys).toContain('type-color-highlight-null');
        expect(keys).toContain('type-color-highlight-#ffd400');
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildAnnotationFilterOptions
// ---------------------------------------------------------------------------

describe('buildAnnotationFilterOptions', () => {
    it('deduplicates type/color choices', () => {
        const options = buildAnnotationFilterOptions(allRows);
        expect(Array.isArray(options)).toBe(true);

        // Should have a unique entry for each distinct type+color combination
        const expectedTypes = new Set(allRows.map(r => r.display.type + '|' + r.display.color));
        expect(options.length).toBe(expectedTypes.size);
    });

    it('includes type and color in labels where present', () => {
        const options = buildAnnotationFilterOptions(allRows);
        const highlight = options.find(o => o.type === 'highlight' && o.color === '#ffd400');
        expect(highlight).toBeTruthy();
        expect(highlight.label).toContain('highlight');
        expect(highlight.label).toContain('#ffd400');
    });

    it('includes rows with null color', () => {
        const options = buildAnnotationFilterOptions(allRows);
        const noColor = options.find(o => o.color === null);
        expect(noColor).toBeTruthy();
    });

    it('returns empty array for empty rows', () => {
        expect(buildAnnotationFilterOptions([])).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// Task 1: matchesAnnotationSearch
// ---------------------------------------------------------------------------

describe('matchesAnnotationSearch', () => {
    it('matches case-insensitively on selectedText', () => {
        const row = makeRow({ selected_text: 'Hello World' });
        expect(matchesAnnotationSearch(row, 'hello')).toBe(true);
        expect(matchesAnnotationSearch(row, 'world')).toBe(true);
        expect(matchesAnnotationSearch(row, 'WORLD')).toBe(true);
    });

    it('matches on comment', () => {
        const row = makeRow({ comment: 'Important note here' });
        expect(matchesAnnotationSearch(row, 'important')).toBe(true);
        expect(matchesAnnotationSearch(row, 'note')).toBe(true);
    });

    it('does NOT match raw/provenance/debug fields', () => {
        const row = makeRow({
            selected_text: 'some text',
            comment: 'a comment',
            source_annotation_key: 'SECRET-KEY-123',
            id: 'secret-id',
            source: 'zotero',
            source_library_id: 'hidden-lib',
        });
        // Should match selected_text and comment
        expect(matchesAnnotationSearch(row, 'text')).toBe(true);
        expect(matchesAnnotationSearch(row, 'comment')).toBe(true);
        // Should NOT match raw provenance fields
        expect(matchesAnnotationSearch(row, 'SECRET-KEY')).toBe(false);
        expect(matchesAnnotationSearch(row, 'secret-id')).toBe(false);
        expect(matchesAnnotationSearch(row, 'hidden-lib')).toBe(false);
        expect(matchesAnnotationSearch(row, 'zotero')).toBe(false);
    });

    it('does not crash on empty query', () => {
        expect(matchesAnnotationSearch(rowPage0, '')).toBe(true);
        expect(matchesAnnotationSearch(rowPage0, null)).toBe(true);
        expect(matchesAnnotationSearch(rowPage0, undefined)).toBe(true);
    });

    it('returns false when query does not match', () => {
        const row = makeRow({ selected_text: 'apples', comment: 'oranges' });
        expect(matchesAnnotationSearch(row, 'bananas')).toBe(false);
        expect(matchesAnnotationSearch(row, 'apples oranges')).toBe(false);
    });

    it('matches on selectedText when comment is empty', () => {
        const row = makeRow({ selected_text: 'only selected', comment: '' });
        expect(matchesAnnotationSearch(row, 'selected')).toBe(true);
        expect(matchesAnnotationSearch(row, 'only')).toBe(true);
    });

    it('matches on comment when selectedText is empty', () => {
        const row = makeRow({ selected_text: '', comment: 'only comment' });
        expect(matchesAnnotationSearch(row, 'comment')).toBe(true);
        expect(matchesAnnotationSearch(row, 'only')).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// Task 1: matchesAnnotationTypeColorFilter
// ---------------------------------------------------------------------------

describe('matchesAnnotationTypeColorFilter', () => {
    it('returns true for "all" filter', () => {
        expect(matchesAnnotationTypeColorFilter(rowPage0, 'all')).toBe(true);
        expect(matchesAnnotationTypeColorFilter(rowPage0, undefined)).toBe(true);
        expect(matchesAnnotationTypeColorFilter(rowPage0, null)).toBe(true);
    });

    it('matches by type', () => {
        expect(matchesAnnotationTypeColorFilter(rowPage0, 'highlight')).toBe(true);
        expect(matchesAnnotationTypeColorFilter(rowPage0, 'note')).toBe(false);
    });

    it('matches by type and color', () => {
        expect(matchesAnnotationTypeColorFilter(rowPage0, 'highlight|#ffd400')).toBe(true);
        expect(matchesAnnotationTypeColorFilter(rowPage0, 'highlight|#ff6666')).toBe(false);
    });

    it('matches rows with null color', () => {
        expect(matchesAnnotationTypeColorFilter(rowNoColor, 'underline|null')).toBe(true);
        expect(matchesAnnotationTypeColorFilter(rowNoColor, 'underline|#something')).toBe(false);
    });

    it('empty filter value is treated as "all"', () => {
        expect(matchesAnnotationTypeColorFilter(rowPage0, '')).toBe(true);
    });
});

// ---------------------------------------------------------------------------
// Task 2: getAnnotationPreview
// ---------------------------------------------------------------------------

describe('getAnnotationPreview', () => {
    it('marks selected-text as two-line preview content', () => {
        const preview = getAnnotationPreview('some selected text', 'selected-text');
        expect(preview).toHaveProperty('text');
        expect(preview).toHaveProperty('truncated');
        expect(preview).toHaveProperty('expandable');
        expect(preview.kind).toBe('selected-text');
        expect(preview.text).toBe('some selected text');
    });

    it('marks comment as one-line preview content', () => {
        const preview = getAnnotationPreview('my comment', 'comment');
        expect(preview.kind).toBe('comment');
        expect(preview.text).toBe('my comment');
    });

    it('returns truncation info for long text', () => {
        const longText = 'x'.repeat(200);
        const preview = getAnnotationPreview(longText, 'selected-text');
        expect(preview.truncated).toBe(true);
        expect(preview.expandable).toBe(true);
        expect(preview.text.length).toBeLessThan(longText.length);
    });

    it('returns no truncation for short text', () => {
        const shortText = 'short';
        const preview = getAnnotationPreview(shortText, 'comment');
        expect(preview.truncated).toBe(false);
        expect(preview.expandable).toBe(false);
        expect(preview.text).toBe(shortText);
    });

    it('handles empty text gracefully', () => {
        const preview = getAnnotationPreview('', 'selected-text');
        expect(preview.text).toBe('');
        expect(preview.truncated).toBe(false);
        expect(preview.expandable).toBe(false);
    });

    it('handles null/undefined text gracefully', () => {
        const preview1 = getAnnotationPreview(null, 'selected-text');
        expect(preview1.text).toBe('');
        expect(preview1.truncated).toBe(false);

        const preview2 = getAnnotationPreview(undefined, 'comment');
        expect(preview2.text).toBe('');
    });

    it('uses different truncation limits for selected-text vs comment', () => {
        const text = 'a'.repeat(150);
        const selectedPreview = getAnnotationPreview(text, 'selected-text');
        const commentPreview = getAnnotationPreview(text, 'comment');
        // Comment should be shorter (one-line preview vs two-line)
        expect(commentPreview.text.length).toBeLessThan(selectedPreview.text.length);
    });
});

// ---------------------------------------------------------------------------
// Task 2: toggleAnnotationExpansion
// ---------------------------------------------------------------------------

describe('toggleAnnotationExpansion', () => {
    it('adds an ID when not present', () => {
        const state = createDefaultAnnotationListUiState();
        const result = toggleAnnotationExpansion(state, 'row1');
        expect(result.expandedIds).toContain('row1');
    });

    it('removes an ID when already present', () => {
        const state = createDefaultAnnotationListUiState();
        const first = toggleAnnotationExpansion(state, 'row1');
        const second = toggleAnnotationExpansion(first, 'row1');
        expect(second.expandedIds).not.toContain('row1');
    });

    it('does not mutate the original uiState', () => {
        const state = createDefaultAnnotationListUiState();
        const result = toggleAnnotationExpansion(state, 'row1');
        expect(state.expandedIds).not.toContain('row1');
        expect(result.expandedIds).toContain('row1');
    });

    it('preserves unrelated settings when toggling', () => {
        const state = createDefaultAnnotationListUiState();
        state.query = 'something';
        const result = toggleAnnotationExpansion(state, 'row2');
        expect(result.query).toBe('something');
        expect(result.groupMode).toBe('none');
        expect(result.typeColorFilter).toBe('all');
    });

    it('supports multiple expanded IDs', () => {
        const state = createDefaultAnnotationListUiState();
        const r1 = toggleAnnotationExpansion(state, 'a');
        const r2 = toggleAnnotationExpansion(r1, 'b');
        expect(r2.expandedIds).toContain('a');
        expect(r2.expandedIds).toContain('b');
    });
});

// ---------------------------------------------------------------------------
// Task 2: buildAnnotationListViewModel
// ---------------------------------------------------------------------------

function makeUiState(overrides = {}) {
    return { ...createDefaultAnnotationListUiState(), ...overrides };
}

describe('buildAnnotationListViewModel — state decisions', () => {
    it('produces loading state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey: 'PAPER_A',
            message: 'Loading...',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('loading');
        expect(vm.rows).toEqual([]);
        expect(vm.groups).toBeUndefined();
        expect(vm.banner).toBeTruthy();
        expect(vm.emptyMessage).toBeUndefined();
        expect(vm.errorMessage).toBeUndefined();
    });

    it('produces ready state with rows', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations loaded.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('ready');
        expect(vm.rows.length).toBe(6);
        expect(vm.total).toBe(6);
        expect(vm.banner).toBeUndefined();
        expect(vm.emptyMessage).toBeUndefined();
        expect(vm.errorMessage).toBeUndefined();
    });

    it('produces empty state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey: 'PAPER_A',
            message: 'This paper has no annotations yet.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('empty');
        expect(vm.rows).toEqual([]);
        expect(vm.emptyMessage).toBe('This paper has no annotations yet.');
        expect(vm.banner).toBeUndefined();
    });

    it('produces missing-db state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
            paperKey: 'PAPER_A',
            message: 'Annotation database is not yet available.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('missing-db');
        expect(vm.rows).toEqual([]);
        expect(vm.errorMessage).toBe('Annotation database is not yet available.');
    });

    it('produces missing-paper state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
            message: 'No paper active.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('missing-paper');
        expect(vm.rows).toEqual([]);
        expect(vm.errorMessage).toBe('No paper active.');
    });

    it('produces cli-error state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'Failed to load annotations.',
            errorCode: 'INTERNAL_ERROR',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('cli-error');
        expect(vm.rows).toEqual([]);
        expect(vm.errorMessage).toBe('Failed to load annotations.');
    });

    it('produces invalid-json state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
            paperKey: 'PAPER_A',
            message: 'Could not read annotation data.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('invalid-json');
        expect(vm.rows).toEqual([]);
        expect(vm.errorMessage).toBe('Could not read annotation data.');
    });

    it('empty state uses fallback message suggesting import when not provided', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey: 'PAPER_A',
            // No message — triggers fallback
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('empty');
        expect(vm.emptyMessage).toMatch(/import/i);
    });

    it('missing-db state uses fallback message suggesting init/repair', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
            paperKey: 'PAPER_A',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('missing-db');
        expect(vm.errorMessage).toMatch(/initial|repair/i);
    });

    it('missing-paper state uses fallback message suggesting opening a paper', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('missing-paper');
        expect(vm.errorMessage).toMatch(/open|paper/i);
    });

    it('cli-error state uses fallback message suggesting retry', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('cli-error');
        expect(vm.errorMessage).toMatch(/retry|check/i);
    });

    it('invalid-json state uses fallback message suggesting check', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
            paperKey: 'PAPER_A',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('invalid-json');
        expect(vm.errorMessage).toMatch(/check|local/i);
    });

    it('idle state does not render', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('idle');
        expect(vm.rows).toEqual([]);
        expect(vm.banner).toBeUndefined();
    });

    it('ready state includes sorted rows by reading order', () => {
        const unsorted = [rowPage1, rowPage0, rowPage1b, rowPage0b];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: unsorted,
            message: '4 annotations loaded.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('ready');
        expect(vm.rows[0].pdfLocation.rowId).toBe('r1');
        expect(vm.rows[1].pdfLocation.rowId).toBe('r2');
        expect(vm.rows[2].pdfLocation.rowId).toBe('r3');
        expect(vm.rows[3].pdfLocation.rowId).toBe('r4');
    });
});

describe('buildAnnotationListViewModel — with uiState', () => {
    it('filters by typeColorFilter', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState({ typeColorFilter: 'highlight|null' }));
        for (const row of vm.rows) {
            expect(row.display.type).toBe('highlight');
            expect(row.display.color).toBeNull();
        }
    });

    it('filters by query on selected text', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState({ query: 'gamma' }));
        expect(vm.rows.length).toBe(1);
        expect(vm.rows[0].display.selectedText).toContain('gamma');
    });

    it('groups by page when groupMode is page', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState({ groupMode: 'page' }));
        expect(vm.groups).toBeDefined();
        expect(vm.groups.mode).toBe('page');
        expect(vm.groups.groups.length).toBeGreaterThanOrEqual(3);
    });

    it('groups by type-color when groupMode is type-color', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState({ groupMode: 'type-color' }));
        expect(vm.groups).toBeDefined();
        expect(vm.groups.mode).toBe('type-color');
        expect(vm.groups.groups.length).toBeGreaterThanOrEqual(5);
    });

    it('computes total before applying filters', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState({ query: 'NONEXISTENT' }));
        expect(vm.total).toBe(6);
        expect(vm.rows.length).toBe(0);
    });

    it('includes filter options in view-model', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.filterOptions).toBeDefined();
        expect(Array.isArray(vm.filterOptions)).toBe(true);
    });

    it('includes current uiState values in view-model', () => {
        const uiState = makeUiState({ query: 'searching', groupMode: 'page', typeColorFilter: 'highlight' });
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, uiState);
        expect(vm.uiState.query).toBe('searching');
        expect(vm.uiState.groupMode).toBe('page');
        expect(vm.uiState.typeColorFilter).toBe('highlight');
    });

    it('still works for ready with zero annotations', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [],
            message: '0 annotations.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('ready');
        expect(vm.rows).toEqual([]);
        expect(vm.total).toBe(0);
    });
});

// ---------------------------------------------------------------------------
// Task 2: mergeAnnotationRefreshResult
// ---------------------------------------------------------------------------

describe('mergeAnnotationRefreshResult', () => {
    it('returns the new state when previous is null', () => {
        const newState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows.slice(0, 2),
            message: '2 annotations.',
        });
        const result = mergeAnnotationRefreshResult(null, newState);
        expect(result.state).toBe('ready');
        expect(result.annotations.length).toBe(2);
        expect(result.stale).toBeFalsy();
    });

    it('returns the new state when previous was an error (no previous success)', () => {
        const prevError = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'First failure.',
        });
        const newError = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'Second failure.',
        });
        const result = mergeAnnotationRefreshResult(prevError, newError);
        expect(result.state).toBe('cli-error');
        expect(result.stale).toBeFalsy();
    });

    it('preserves last successful state and marks stale when refresh fails after ready', () => {
        const prevReady = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows,
            message: '6 annotations.',
        });
        const newError = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'Refresh failed.',
            errorCode: 'TIMEOUT',
        });
        const result = mergeAnnotationRefreshResult(prevReady, newError);
        // State should be ready (from previous), but marked stale
        expect(result.state).toBe('ready');
        expect(result.stale).toBe(true);
        expect(result.annotations.length).toBe(6);
        expect(result.message).toContain('stale');
        expect(result.message).toContain('Refresh failed');
    });

    it('preserves last successful state and marks stale when refresh fails after empty', () => {
        const prevEmpty = makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey: 'PAPER_A',
            annotations: [],
            message: 'No annotations.',
        });
        const newInvalid = makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
            paperKey: 'PAPER_A',
            message: 'Invalid data.',
        });
        const result = mergeAnnotationRefreshResult(prevEmpty, newInvalid);
        expect(result.state).toBe('empty');
        expect(result.stale).toBe(true);
        expect(result.message).toContain('stale');
    });

    it('does not preserve stale state when new load is successful after previous failure', () => {
        const prevError = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'Failed before.',
        });
        const newReady = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: allRows.slice(0, 3),
            message: '3 annotations loaded.',
        });
        const result = mergeAnnotationRefreshResult(prevError, newReady);
        expect(result.state).toBe('ready');
        expect(result.stale).toBeFalsy();
        expect(result.annotations.length).toBe(3);
    });
});

// ---------------------------------------------------------------------------
// Task 2: Unsafe/missing row fields do not crash and produce safe fallback labels
// ---------------------------------------------------------------------------

describe('graceful handling of missing/unsupported fields', () => {
    it('buildAnnotationListViewModel does not crash on rows missing display fields', () => {
        const weirdRow = {
            display: {},
            provenance: {},
            pdfLocation: {},
            raw: {},
        };
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [weirdRow],
            message: '1 annotation.',
        });
        const vm = buildAnnotationListViewModel(annState, makeUiState());
        expect(vm.state).toBe('ready');
        expect(vm.rows.length).toBe(1);
    });

    it('sortAnnotationsForReadingOrder handles rows with missing pdfLocation', () => {
        const broken = { display: {}, provenance: {}, pdfLocation: null, raw: {} };
        const result = sortAnnotationsForReadingOrder([broken, rowPage0]);
        expect(result.length).toBe(2);
    });

    it('groupAnnotationRows does not crash on rows with missing display type', () => {
        const weird = { display: {}, provenance: {}, pdfLocation: { rowId: 'w', pageIndex: 0, sortIndex: 0 }, raw: {} };
        const result = groupAnnotationRows([weird, rowPage0], 'type-color');
        expect(result.groups.length).toBeGreaterThanOrEqual(1);
    });
});
