/**
 * Vitest tests for canvas card view-models (Phase ANN11, Plan 01).
 *
 * Tests cover:
 *   Task 1 — buildCanvasCard: card fields, missing values, identity,
 *            source/provenance, read-only, anchor placeholder,
 *            no action controls.
 *   Task 1 — buildCanvasCardViewModel: all 11 canvas/card states,
 *            loaded cards with lane metadata, stale-safe.
 *   Task 1 — normalizeCanvasCardPreview: long, CJK, HTML-like,
 *            missing values, forbidden verbs absent.
 *
 * @module tests/canvas-viewmodel
 */

import { describe, it, expect } from 'vitest';

const {
    buildCanvasCard,
    buildCanvasCardViewModel,
    normalizeCanvasCardPreview,
} = await import('../src/canvas/view-model.js');

const {
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
        selected_text: overrides.selected_text || 'selected text for testing',
        comment: overrides.comment || 'a comment about this annotation',
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

// Standard rows
const rowStandard = makeRow({ id: 'r1', page_index: 0, page_label: '1', sort_index: 0, type: 'highlight', color: '#ffd400', selected_text: 'Alpha bravo selected text', comment: 'Alpha comment' });
const rowNote = makeRow({ id: 'r2', page_index: 1, page_label: '2', sort_index: 0, type: 'note', color: null, selected_text: 'Beta selected', comment: '' });
const rowReadOnly = makeRow({ id: 'r3', page_index: 0, page_label: '1', sort_index: 1, type: 'highlight', color: '#ff6666', selected_text: 'Gamma selected', comment: 'Gamma comment', is_readonly: 1 });
const rowMissingSelectedText = makeRow({ id: 'r4', page_index: 2, page_label: '3', sort_index: 0, type: 'highlight', color: '#00ff00', selected_text: '', comment: 'Only a comment' });
const rowMissingComment = makeRow({ id: 'r5', page_index: 2, page_label: '3', sort_index: 1, type: 'sticky_note', color: null, selected_text: 'Only selected', comment: '' });
const rowMinimal = (() => {
    // Raw row with only essential fields
    const raw = {
        id: 'r6',
        paper_id: 'PAPER_B',
        source: 'zotero',
        source_library_id: '1',
        source_annotation_key: null,
        source_attachment_key: 'ATTACH_B',
        source_parent_key: null,
        source_modified_at: null,
        type: 'highlight',
        page_index: null,
        page_label: null,
        selected_text: null,
        comment: null,
        color: null,
        sort_index: null,
        tags_json: '[]',
        position_json: '{}',
        selector_json: '{}',
        sync_state: null,
        is_readonly: 0,
        created_at: null,
        updated_at: null,
        deleted_at: null,
    };
    return normalizeAnnotationExportRow(raw);
})();

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCard — card field preservation (D-01 / CARD-01)
// ---------------------------------------------------------------------------

describe('buildCanvasCard — card field preservation (D-01 / CARD-01)', () => {
    it('produces a card object with all required fields', () => {
        const card = buildCanvasCard(rowStandard);

        expect(card).toHaveProperty('id');
        expect(card).toHaveProperty('selectedText');
        expect(card).toHaveProperty('comment');
        expect(card).toHaveProperty('pageLabel');
        expect(card).toHaveProperty('pageIndex');
        expect(card).toHaveProperty('type');
        expect(card).toHaveProperty('color');
        expect(card).toHaveProperty('source');
        expect(card).toHaveProperty('sourceAttachmentKey');
        expect(card).toHaveProperty('sourceAnnotationKey');
        expect(card).toHaveProperty('readOnly');
        expect(card).toHaveProperty('anchor');
    });

    it('preserves selected text from the normalized row', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.selectedText).toBe('Alpha bravo selected text');
    });

    it('preserves comment from the normalized row', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.comment).toBe('Alpha comment');
    });

    it('preserves page label from the normalized row', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.pageLabel).toBe('1');
    });

    it('preserves page index from pdfLocation', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.pageIndex).toBe(0);
    });

    it('preserves type from the normalized row', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.type).toBe('highlight');
    });

    it('preserves color from the normalized row', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.color).toBe('#ffd400');
    });

    it('preserves source from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.source).toBe('zotero');
    });

    it('preserves sourceAttachmentKey from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.sourceAttachmentKey).toBe('ATTACH_A');
    });

    it('preserves sourceAnnotationKey from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.sourceAnnotationKey).toBe('ann-r1');
    });

    it('preserves readOnly status from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        // Default is_readonly=0 → readOnly should be false
        expect(card.readOnly).toBe(false);
    });

    it('marks cards with is_readonly=1 as readOnly:true', () => {
        const card = buildCanvasCard(rowReadOnly);
        expect(card.readOnly).toBe(true);
    });

    it('includes an anchor placeholder with unresolved status when no sourceModel', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.anchor).toEqual({
            status: 'unresolved',
            reason: expect.any(String),
        });
    });

    it('includes computed anchor when sourceModel is provided', () => {
        const surface = { SOURCE_KINDS: { FULLTEXT: 'fulltext' }, SOURCE_STATES: { READY: 'ready' } };
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Sample text for testing the annotation card anchor resolution.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        // Row has selected_text='selected text for testing' → should find exact match
        const card = buildCanvasCard(rowStandard, sourceModel);
        expect(card.anchor).toBeDefined();
        expect(typeof card.anchor.status).toBe('string');
        expect(['exact', 'page-level', 'unresolved']).toContain(card.anchor.status);
        expect(card.anchor).toHaveProperty('anchorId');
        expect(card.anchor).toHaveProperty('cardId');
    });

    it('anchor with sourceModel does not break card identity or display fields', () => {
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Some sample text for testing.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const card = buildCanvasCard(rowStandard, sourceModel);
        expect(card.id).toBeTruthy();
        expect(card.selectedText).toBe('Alpha bravo selected text');
        expect(card.comment).toBe('Alpha comment');
        expect(card.type).toBe('highlight');
        expect(card.readOnly).toBe(false);
    });

    it('includes a stable id matching the row identity', async () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.id).toBeTruthy();
        expect(typeof card.id).toBe('string');
        // Should match getAnnotationIdentity result
        const { getAnnotationIdentity } = await import('../src/testable.js');
        expect(card.id).toBe(getAnnotationIdentity(rowStandard));
    });

    it('preserves type for note annotations', () => {
        const card = buildCanvasCard(rowNote);
        expect(card.type).toBe('note');
    });

    it('preserves null color as null', () => {
        const card = buildCanvasCard(rowNote);
        expect(card.color).toBeNull();
    });

    it('handles null pageIndex gracefully', () => {
        const card = buildCanvasCard(rowMinimal);
        expect(card.pageIndex).toBeNull();
    });

    it('handles null pageLabel gracefully', () => {
        const card = buildCanvasCard(rowMinimal);
        expect(card.pageLabel).toBe('');
    });

    it('includes readOnlyLabel showing read-only sync metadata', () => {
        const card = buildCanvasCard(rowStandard);
        // readOnlyLabel should be present and be a string
        expect(card).toHaveProperty('readOnlyLabel');
        expect(typeof card.readOnlyLabel).toBe('string');
    });

    it('readOnlyLabel is empty for non-read-only cards', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.readOnlyLabel).toBe('');
    });

    it('readOnlyLabel shows status for read-only cards', () => {
        const card = buildCanvasCard(rowReadOnly);
        expect(card.readOnlyLabel).toBeTruthy();
        expect(typeof card.readOnlyLabel).toBe('string');
        expect(card.readOnlyLabel.length).toBeGreaterThan(0);
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCard — missing values as explicit placeholders (D-04 / CARD-02)
// ---------------------------------------------------------------------------

describe('buildCanvasCard — missing values (D-04 / CARD-02)', () => {
    it('missing selected text renders as empty string, not absent', () => {
        const card = buildCanvasCard(rowMissingSelectedText);
        expect(card.selectedText).toBe('');
        expect(card).toHaveProperty('selectedText');
    });

    it('missing selected text includes preview metadata', () => {
        const card = buildCanvasCard(rowMissingSelectedText);
        expect(card).toHaveProperty('selectedTextPreview');
        expect(card.selectedTextPreview.text).toBe('');
        expect(card.selectedTextPreview.truncated).toBe(false);
    });

    it('missing comment renders as empty string, not absent', () => {
        const card = buildCanvasCard(rowMissingComment);
        expect(card.comment).toBe('');
        expect(card).toHaveProperty('comment');
    });

    it('missing comment includes preview metadata', () => {
        const card = buildCanvasCard(rowMissingComment);
        expect(card).toHaveProperty('commentPreview');
        expect(card.commentPreview.text).toBe('');
        expect(card.commentPreview.truncated).toBe(false);
    });

    it('null selected text renders as empty string with placeholder preview', () => {
        const card = buildCanvasCard(rowMinimal);
        expect(card.selectedText).toBe('');
        expect(card.selectedTextPreview.text).toBe('');
    });

    it('null comment renders as empty string with placeholder preview', () => {
        const card = buildCanvasCard(rowMinimal);
        expect(card.comment).toBe('');
        expect(card.commentPreview.text).toBe('');
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCard — source identity (CARD-04)
// ---------------------------------------------------------------------------

describe('buildCanvasCard — source identity (CARD-04)', () => {
    it('includes attachmentKey from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.sourceAttachmentKey).toBe('ATTACH_A');
    });

    it('includes annotation key from provenance', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.sourceAnnotationKey).toBe('ann-r1');
    });

    it('includes source string', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card.source).toBe('zotero');
    });

    it('card id is stable for the same row', () => {
        const card1 = buildCanvasCard(rowStandard);
        const card2 = buildCanvasCard(rowStandard);
        expect(card1.id).toBe(card2.id);
    });

    it('card id differs for different rows', () => {
        const card1 = buildCanvasCard(rowStandard);
        const card2 = buildCanvasCard(rowNote);
        expect(card1.id).not.toBe(card2.id);
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCard — no action/control fields (D-21 / D-22)
// ---------------------------------------------------------------------------

describe('buildCanvasCard — cards visible when source missing (D-15 / D-18)', () => {
    it('card has all fields when sourceModel is unavailable', () => {
        const sourceModel = {
            status: 'source-unavailable',
            sourceKind: null,
            text: null,
            paperKey: 'PAPER_A',
            diagnostics: { fulltext: { miss: true, reason: 'File missing.' }, note: { miss: true, reason: 'Note missing.' } },
            reason: 'No source available.',
        };
        const card = buildCanvasCard(rowStandard, sourceModel);
        expect(card.id).toBeTruthy();
        expect(card.selectedText).toBe('Alpha bravo selected text');
        expect(card.comment).toBe('Alpha comment');
        expect(card.anchor.status).toBe('unresolved');
        expect(card.anchor.reason).toBeTruthy();
        // Card remains fully formed
        expect(card.type).toBe('highlight');
        expect(card.pageIndex).toBe(0);
    });

    it('cards remain visible with unresolved anchor when source is missing', () => {
        const sourceModel = {
            status: 'source-unavailable',
            sourceKind: null,
            text: null,
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: 'No reading source is available for this paper.',
        };
        const card = buildCanvasCard(rowStandard, sourceModel);
        // Card fields are all present
        expect(card).toHaveProperty('id');
        expect(card).toHaveProperty('selectedText');
        expect(card).toHaveProperty('comment');
        expect(card).toHaveProperty('pageLabel');
        expect(card).toHaveProperty('pageIndex');
        expect(card).toHaveProperty('type');
        expect(card).toHaveProperty('color');
        expect(card).toHaveProperty('source');
        // Anchor is unresolved (not absent)
        expect(card.anchor.status).toBe('unresolved');
    });

    it('no forbidden verbs present when sourceModel is provided', () => {
        const FORBIDDEN = ['edit', 'delete', 'create', 'save', 'import', 'apply', 'writeBack', 'writeback', 'write_back'];
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Example text for testing.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const card = buildCanvasCard(rowStandard, sourceModel);
        const keys = Object.keys(card);
        for (const verb of FORBIDDEN) {
            expect(keys).not.toContain(verb);
        }
        // Anchor model should not have forbidden verbs either
        const anchorKeys = Object.keys(card.anchor);
        for (const verb of ['edit', 'delete', 'create', 'save', 'import', 'apply', 'writeBack']) {
            expect(anchorKeys).not.toContain(verb);
        }
    });

    it('no navigation, connector, or SVG in anchor when sourceModel provided', () => {
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Example text for navigation test.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const card = buildCanvasCard(rowStandard, sourceModel);
        const anchor = card.anchor;
        expect(anchor).not.toHaveProperty('navigation');
        expect(anchor).not.toHaveProperty('connector');
        expect(anchor).not.toHaveProperty('svg');
        expect(anchor).not.toHaveProperty('svgPath');
        expect(anchor).not.toHaveProperty('scrollTo');
        expect(anchor).not.toHaveProperty('focus');
    });
});

describe('buildCanvasCard — no action/control fields (D-21 / D-22)', () => {
    const FORBIDDEN_VERBS = [
        'edit', 'delete', 'create', 'save', 'import', 'apply',
        'writeBack', 'writeback', 'write_back',
    ];

    it('card has no create/edit/delete/save properties', () => {
        const card = buildCanvasCard(rowStandard);
        const keys = Object.keys(card);
        for (const verb of FORBIDDEN_VERBS) {
            expect(keys).not.toContain(verb);
        }
    });

    it('card has no function/action properties', () => {
        const card = buildCanvasCard(rowStandard);
        for (const [key, value] of Object.entries(card)) {
            expect(typeof value).not.toBe('function');
        }
    });

    it('card JSON representation contains no forbidden action verbs', () => {
        const card = buildCanvasCard(rowStandard);
        const json = JSON.stringify(card).toLowerCase();
        for (const verb of FORBIDDEN_VERBS) {
            expect(json).not.toContain(verb);
        }
    });

    it('card has no onDelete/onEdit/onSave/onCreate handlers', () => {
        const card = buildCanvasCard(rowStandard);
        expect(card).not.toHaveProperty('onDelete');
        expect(card).not.toHaveProperty('onEdit');
        expect(card).not.toHaveProperty('onSave');
        expect(card).not.toHaveProperty('onCreate');
    });
});

// ---------------------------------------------------------------------------
// Task 1: normalizeCanvasCardPreview — preview metadata (D-18 / CARD-02)
// ---------------------------------------------------------------------------

describe('normalizeCanvasCardPreview — preview metadata (D-18 / CARD-02)', () => {
    it('returns preview object with text, kind, truncated, expandable fields', () => {
        const preview = normalizeCanvasCardPreview('some text', 'selected-text');
        expect(preview).toHaveProperty('text');
        expect(preview).toHaveProperty('kind');
        expect(preview).toHaveProperty('truncated');
        expect(preview).toHaveProperty('expandable');
        expect(preview).toHaveProperty('isLong');
    });

    it('marks selected-text correctly in preview kind', () => {
        const preview = normalizeCanvasCardPreview('text', 'selected-text');
        expect(preview.kind).toBe('selected-text');
    });

    it('marks comment correctly in preview kind', () => {
        const preview = normalizeCanvasCardPreview('text', 'comment');
        expect(preview.kind).toBe('comment');
    });

    it('truncates long selected text (> 140 chars) and marks truncated', () => {
        const longText = 'x'.repeat(200);
        const preview = normalizeCanvasCardPreview(longText, 'selected-text');
        expect(preview.truncated).toBe(true);
        expect(preview.expandable).toBe(true);
        expect(preview.text.length).toBeLessThan(longText.length);
        expect(preview.text).toMatch(/…$/);
    });

    it('truncates long comment (> 70 chars) with shorter limit', () => {
        const longComment = 'y'.repeat(100);
        const preview = normalizeCanvasCardPreview(longComment, 'comment');
        expect(preview.truncated).toBe(true);
        expect(preview.text.length).toBeLessThan(longComment.length);
    });

    it('does not truncate short text', () => {
        const preview = normalizeCanvasCardPreview('short', 'selected-text');
        expect(preview.truncated).toBe(false);
        expect(preview.expandable).toBe(false);
        expect(preview.text).toBe('short');
    });

    it('handles empty string', () => {
        const preview = normalizeCanvasCardPreview('', 'selected-text');
        expect(preview.text).toBe('');
        expect(preview.truncated).toBe(false);
    });

    it('handles null value', () => {
        const preview = normalizeCanvasCardPreview(null, 'selected-text');
        expect(preview.text).toBe('');
        expect(preview.truncated).toBe(false);
    });

    it('handles undefined value', () => {
        const preview = normalizeCanvasCardPreview(undefined, 'selected-text');
        expect(preview.text).toBe('');
        expect(preview.truncated).toBe(false);
    });

    it('handles CJK-heavy text without crashing', () => {
        const cjkText = '这是一个测试用的中文文本，包含了大量中文字符和标点符号。我们需要确保CJK文本也能被正确处理。';
        const preview = normalizeCanvasCardPreview(cjkText, 'selected-text');
        expect(preview).toHaveProperty('text');
        expect(preview.truncated).toBe(cjkText.length > 140);
    });

    it('handles CJK-heavy comment text', () => {
        const cjkComment = '这是一个中文评论，包含了一些观察和思考。';
        const preview = normalizeCanvasCardPreview(cjkComment, 'comment');
        expect(preview).toHaveProperty('text');
        expect(preview.text).toBeTruthy();
    });

    it('handles HTML-like strings safely (no injection)', () => {
        const htmlLike = '<script>alert("xss")</script>';
        const preview = normalizeCanvasCardPreview(htmlLike, 'selected-text');
        expect(preview.text).toBe(htmlLike);
        // HTML-like content is preserved as literal text, not rendered
        expect(preview.text).toContain('<script>');
    });

    it('isLong flag reflects whether text exceeds threshold', () => {
        const short = normalizeCanvasCardPreview('short', 'selected-text');
        expect(short.isLong).toBe(false);

        const long = normalizeCanvasCardPreview('x'.repeat(300), 'selected-text');
        expect(long.isLong).toBe(true);
    });

    it('has different truncation limits for selected-text (140) vs comment (70)', () => {
        const text = 'a'.repeat(120);
        const selectedPreview = normalizeCanvasCardPreview(text, 'selected-text');
        const commentPreview = normalizeCanvasCardPreview(text, 'comment');

        // Comment should be truncated at 70, selected-text at 140
        expect(commentPreview.truncated).toBe(true);
        expect(selectedPreview.truncated).toBe(false);
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCardViewModel — state mapping (D-10 through D-14 / CANVAS-04)
// ---------------------------------------------------------------------------

describe('buildCanvasCardViewModel — state mapping (D-10 through D-14 / CANVAS-04)', () => {
    it('produces loading state with no cards', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey: 'PAPER_A',
            message: 'Loading annotations...',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('loading');
        expect(vm.cards).toEqual([]);
        expect(vm.lanes).toBeUndefined();
        expect(vm.message).toBeTruthy();
    });

    it('produces ready state with cards from annotation rows', () => {
        const rows = [rowStandard, rowNote, rowReadOnly];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
            message: '3 annotations loaded.',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('ready');
        expect(Array.isArray(vm.cards)).toBe(true);
        expect(vm.cards.length).toBe(3);
    });

    it('ready state cards preserve row content', () => {
        const rows = [rowStandard];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.cards[0].selectedText).toBe('Alpha bravo selected text');
        expect(vm.cards[0].comment).toBe('Alpha comment');
        expect(vm.cards[0].type).toBe('highlight');
    });

    it('ready state cards are sorted by reading order', () => {
        // Page 1 annotation should come before page 2
        const rowPage0 = makeRow({ id: 'p0', page_index: 0, sort_index: 1, selected_text: 'page 0 later' });
        const rowPage1 = makeRow({ id: 'p1', page_index: 1, sort_index: 0, selected_text: 'page 1' });
        const rows = [rowPage1, rowPage0];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.cards.length).toBe(2);
        // Page 0 should come before page 1
        expect(vm.cards[0].pageIndex).toBe(0);
        expect(vm.cards[1].pageIndex).toBe(1);
    });

    it('produces empty state with no cards', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey: 'PAPER_A',
            message: 'No annotations yet.',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('empty');
        expect(vm.cards).toEqual([]);
    });

    it('produces missing-paper state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
            message: 'No paper active.',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('missing-paper');
        expect(vm.cards).toEqual([]);
    });

    it('produces missing-db state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
            paperKey: 'PAPER_A',
            message: 'DB not available.',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('missing-db');
        expect(vm.cards).toEqual([]);
    });

    it('produces cli-error state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: 'PAPER_A',
            message: 'CLI error.',
            errorCode: 'TIMEOUT',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('cli-error');
        expect(vm.cards).toEqual([]);
    });

    it('produces invalid-json state', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
            paperKey: 'PAPER_A',
            message: 'Invalid JSON.',
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('invalid-json');
        expect(vm.cards).toEqual([]);
    });

    it('produces missing-source state when source is not available', () => {
        const annState = { state: 'missing-source', paperKey: 'PAPER_A', annotations: [], message: 'Source not available.' };
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('missing-source');
        expect(vm.cards).toEqual([]);
    });

    it('produces unsupported state', () => {
        const annState = { state: 'unsupported', paperKey: 'PAPER_A', annotations: [], message: 'Unsupported.' };
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('unsupported');
        expect(vm.cards).toEqual([]);
    });

    it('produces refreshing state when refreshing=true', () => {
        const rows = [rowStandard];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { refreshing: true });
        expect(vm.state).toBe('refreshing');
        expect(vm.cards.length).toBe(1);
        expect(vm.refreshing).toBe(true);
    });

    it('refreshing state includes existing cards', () => {
        const rows = [rowStandard, rowNote];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { refreshing: true });
        expect(vm.cards.length).toBe(2);
        expect(vm.refreshing).toBe(true);
        expect(vm.state).toBe('refreshing');
    });

    it('produces stale state when stale=true', () => {
        const rows = [rowStandard];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { stale: true });
        expect(vm.state).toBe('stale');
        expect(vm.cards.length).toBe(1);
        expect(vm.stale).toBe(true);
        expect(vm.message).toContain('stale');
    });

    it('stale state includes existing cards with stale flag', () => {
        const rows = [rowStandard];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { stale: true });
        expect(vm.cards[0]).toHaveProperty('stale', true);
    });

    it('idle/default state returns idle with no cards', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('idle');
        expect(vm.cards).toEqual([]);
    });

    it('error states never masquerade as empty (D-12)', () => {
        // D-12: Error and stale states should never masquerade as an empty annotation list
        const errorStates = ['missing-paper', 'missing-db', 'cli-error', 'invalid-json', 'missing-source', 'unsupported'];
        for (const state of errorStates) {
            const annState = makeAnnotationState(state, { paperKey: null, message: 'Error' });
            const vm = buildCanvasCardViewModel(annState);
            expect(vm.state).toBe(state);
            // State name should not be 'empty'
            expect(vm.state).not.toBe('empty');
        }
    });

    it('invalid state name falls back to idle', () => {
        const annState = makeAnnotationState('nonexistent-state', { paperKey: 'PAPER_A' });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('idle');
        expect(vm.cards).toEqual([]);
    });

    it('null annotation state defaults to idle', () => {
        const vm = buildCanvasCardViewModel(null);
        expect(vm.state).toBe('idle');
        expect(vm.cards).toEqual([]);
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCardViewModel — lane integration
// ---------------------------------------------------------------------------

describe('buildCanvasCardViewModel — lane integration', () => {
    it('ready state includes lanes when not refreshing or stale', () => {
        const rows = [rowStandard, rowNote, rowReadOnly];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm).toHaveProperty('lanes');
        expect(vm.lanes).toHaveProperty('left');
        expect(vm.lanes).toHaveProperty('right');
    });

    it('ready state lanes contain all cards', () => {
        const rows = [rowStandard, rowNote, rowReadOnly];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState);
        const totalLaneCards = vm.lanes.left.length + vm.lanes.right.length;
        expect(totalLaneCards).toBe(rows.length);
    });

    it('refreshing state also includes lanes with cards', () => {
        const rows = [rowStandard, rowNote];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { refreshing: true });
        expect(vm).toHaveProperty('lanes');
        expect(vm.lanes.left.length + vm.lanes.right.length).toBe(2);
    });

    it('stale state also includes lanes with cards', () => {
        const rows = [rowStandard, rowNote];
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { stale: true });
        expect(vm).toHaveProperty('lanes');
        expect(vm.lanes.left.length + vm.lanes.right.length).toBe(2);
    });
});

// ---------------------------------------------------------------------------
// Task 2: buildCanvasCardViewModel — sourceModel anchor integration (ANN12)
// ---------------------------------------------------------------------------

describe('buildCanvasCardViewModel — sourceModel anchor integration (ANN12)', () => {
    it('passes sourceModel through buildCards and computes anchors', () => {
        const surface = { SOURCE_KINDS: { FULLTEXT: 'fulltext' }, SOURCE_STATES: { READY: 'ready' } };
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Alpha bravo selected text for the test paper content.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const rows = [rowStandard];
        const annState = makeAnnotationState('ready', {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { sourceModel: sourceModel });
        expect(vm.state).toBe('ready');
        expect(vm.cards.length).toBe(1);
        expect(vm.cards[0].anchor).toBeDefined();
        expect(vm.cards[0].anchor.cardId).toBeTruthy();
        expect(vm.cards[0].anchor.sourceKind).toBe('fulltext');
    });

    it('view-model with sourceModel still produces expected state fields', () => {
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Some text for anchor testing.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const rows = [rowStandard, rowNote];
        const annState = makeAnnotationState('ready', {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { sourceModel: sourceModel });
        expect(vm.state).toBe('ready');
        expect(Array.isArray(vm.cards)).toBe(true);
        expect(vm.cards.length).toBe(2);
        expect(vm).toHaveProperty('lanes');
        expect(vm.lanes.left.length + vm.lanes.right.length).toBe(2);
    });

    it('view-model with sourceModel still handles stale correctly', () => {
        const sourceModel = {
            status: 'ready',
            sourceKind: 'fulltext',
            text: 'Text for testing.',
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: null,
        };
        const rows = [rowStandard];
        const annState = makeAnnotationState('ready', {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { sourceModel: sourceModel, stale: true });
        expect(vm.state).toBe('stale');
        expect(vm.cards.length).toBe(1);
        expect(vm.cards[0].stale).toBe(true);
        expect(vm.cards[0].anchor).toBeDefined();
    });

    it('view-model with missing source still shows cards with unresolved anchors', () => {
        const sourceModel = {
            status: 'source-unavailable',
            sourceKind: null,
            text: null,
            paperKey: 'PAPER_A',
            diagnostics: {},
            reason: 'No source available.',
        };
        const rows = [rowStandard, rowNote];
        const annState = makeAnnotationState('ready', {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState, { sourceModel: sourceModel });
        expect(vm.state).toBe('ready');
        expect(vm.cards.length).toBe(2);
        expect(vm.cards[0].anchor.status).toBe('unresolved');
        expect(vm.cards[1].anchor.status).toBe('unresolved');
    });

    it('view-model without sourceModel still produces unresolved anchors (backward compat)', () => {
        const rows = [rowStandard];
        const annState = makeAnnotationState('ready', {
            paperKey: 'PAPER_A',
            annotations: rows,
        });
        const vm = buildCanvasCardViewModel(annState);
        expect(vm.state).toBe('ready');
        expect(vm.cards.length).toBe(1);
        expect(vm.cards[0].anchor.status).toBe('unresolved');
        expect(vm.cards[0].anchor.reason).toBe('No source model provided for anchor resolution.');
    });
});

// ---------------------------------------------------------------------------
// Task 1: buildCanvasCard — long/CJK/HTML test (D-18)
// ---------------------------------------------------------------------------

describe('buildCanvasCard — long/CJK/HTML values (D-18)', () => {
    it('long selected text gets preview metadata', () => {
        const longText = 'Lorem ipsum '.repeat(20); // ~240 chars
        const row = makeRow({ id: 'long', selected_text: longText });
        const card = buildCanvasCard(row);
        expect(card.selectedText).toBe(longText);
        expect(card).toHaveProperty('selectedTextPreview');
        expect(card.selectedTextPreview.truncated).toBe(true);
        expect(card.selectedTextPreview.text.length).toBeLessThan(longText.length);
    });

    it('long comment gets preview metadata', () => {
        const longComment = 'Comment text '.repeat(20); // ~200 chars
        const row = makeRow({ id: 'long-comment', comment: longComment });
        const card = buildCanvasCard(row);
        expect(card.comment).toBe(longComment);
        expect(card).toHaveProperty('commentPreview');
        expect(card.commentPreview.truncated).toBe(true);
    });

    it('CJK-heavy selected text is preserved and has preview', () => {
        const cjkText = '细胞凋亡在肿瘤发生发展中的作用机制研究及临床应用前景分析这篇论文主要探讨了细胞凋亡通路在癌症治疗中的潜在靶点。';
        const row = makeRow({ id: 'cjk', selected_text: cjkText, comment: '重要发现' });
        const card = buildCanvasCard(row);
        expect(card.selectedText).toBe(cjkText);
        expect(card.selectedTextPreview.text).toBeTruthy();
        expect(card.comment).toBe('重要发现');
    });

    it('HTML-like strings in selected text are preserved as-is', () => {
        const htmlText = '<b>bold text</b> and <script>alert(1)</script>';
        const row = makeRow({ id: 'html', selected_text: htmlText });
        const card = buildCanvasCard(row);
        expect(card.selectedText).toBe(htmlText);
        // Preview should preserve the literal text, not strip tags
        expect(card.selectedTextPreview.text).toContain('<b>');
    });

    it('HTML-like strings in comment are preserved as-is', () => {
        const htmlComment = 'Comment with <img src=x onerror=alert(1)>';
        const row = makeRow({ id: 'html-cmt', comment: htmlComment });
        const card = buildCanvasCard(row);
        expect(card.comment).toBe(htmlComment);
        expect(card.commentPreview.text).toContain('<img');
    });
});
