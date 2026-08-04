/**
 * Vitest tests for Phase 8 overlay rendering pure helpers.
 *
 * Tests cover:
 *   - createDefaultAnnotationOverlayState (Task 1)
 *   - parseAnnotationPositionJson (Task 1)
 *   - normalizeAnnotationColor (Task 1)
 *   - buildAnnotationOverlayMarks (Task 2)
 *   - buildAnnotationPopoverViewModel (Task 2)
 */
import { describe, it, expect } from 'vitest';

const {
    createDefaultAnnotationOverlayState,
    parseAnnotationPositionJson,
    normalizeAnnotationColor,
    DEFAULT_OVERLAY_HIGHLIGHT_COLOR,
    buildAnnotationOverlayMarks,
    buildAnnotationPopoverViewModel,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Task 1: createDefaultAnnotationOverlayState
// ---------------------------------------------------------------------------

describe('createDefaultAnnotationOverlayState', () => {
    it('returns an object with all required fields', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state).toHaveProperty('status', 'idle');
        expect(state).toHaveProperty('reason', '');
        expect(state).toHaveProperty('paperKey');
        expect(state).toHaveProperty('pdfPath');
        expect(state).toHaveProperty('viewerAttached', false);
        expect(state).toHaveProperty('activePopoverId');
    });

    it('initializes paperKey and pdfPath to null', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state.paperKey).toBeNull();
        expect(state.pdfPath).toBeNull();
    });

    it('initializes activePopoverId to null', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state.activePopoverId).toBeNull();
    });

    it('returns a fresh object each call', () => {
        const a = createDefaultAnnotationOverlayState();
        const b = createDefaultAnnotationOverlayState();
        expect(a).not.toBe(b);
    });
});

// ---------------------------------------------------------------------------
// Task 1: parseAnnotationPositionJson
// ---------------------------------------------------------------------------

describe('parseAnnotationPositionJson', () => {
    it('parses a valid positionJson with rects', () => {
        const input = '{"pageIndex":0,"rects":[{"x":60.5,"y":72.3,"w":489.2,"h":18.1}]}';
        const result = parseAnnotationPositionJson(input);
        expect(result.ok).toBe(true);
        expect(result.rects).toHaveLength(1);
        expect(result.rects[0].x).toBe(60.5);
        expect(result.rects[0].y).toBe(72.3);
        expect(result.rects[0].w).toBe(489.2);
        expect(result.rects[0].h).toBe(18.1);
        expect(result.reason).toBeNull();
    });

    it('parses a positionJson with multiple rects', () => {
        const input = '{"rects":[{"x":0,"y":0,"w":100,"h":20},{"x":10,"y":30,"w":200,"h":40}]}';
        const result = parseAnnotationPositionJson(input);
        expect(result.ok).toBe(true);
        expect(result.rects).toHaveLength(2);
    });

    it('parses real Zotero rect arrays as x1/y1/x2/y2 coordinates', () => {
        const input = '{"pageIndex":2,"rects":[[220.095,432.09,294.815,440.307],[39.685,421.34,294.803,429.557]]}';
        const result = parseAnnotationPositionJson(input);
        expect(result.ok).toBe(true);
        expect(result.pageIndex).toBe(2);
        expect(result.rects).toEqual([
            { x: 220.095, y: 432.09, w: 74.72, h: 8.217 },
            { x: 39.685, y: 421.34, w: 255.118, h: 8.217 },
        ]);
    });

    it('returns ok:false for null input', () => {
        const result = parseAnnotationPositionJson(null);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for undefined input', () => {
        const result = parseAnnotationPositionJson(undefined);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for non-string input', () => {
        const result = parseAnnotationPositionJson(42);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for invalid JSON string', () => {
        const result = parseAnnotationPositionJson('{not valid json}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for a JSON string that is not an object', () => {
        const result = parseAnnotationPositionJson('"just a string"');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for a JSON array', () => {
        const result = parseAnnotationPositionJson('[1,2,3]');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects field is missing', () => {
        const result = parseAnnotationPositionJson('{"pageIndex":0}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects is not an array', () => {
        const result = parseAnnotationPositionJson('{"rects":"not-an-array"}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects array is empty', () => {
        const result = parseAnnotationPositionJson('{"pageIndex":2,"rects":[]}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rect has non-numeric x', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":"abc","y":0,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
    });

    it('returns ok:false when rect has non-numeric y', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":null,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-numeric w', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":false,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-numeric h', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100,"h":undefined}]}');
        // undefined in JSON becomes null/omitted — but let's test absent h
        const result2 = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100}]}');
        expect(result2.ok).toBe(false);
    });

    it('returns ok:false when rect has negative x', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":-1,"y":0,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative y', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":-5,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative w', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":-100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative h', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100,"h":-20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-finite values (Infinity)', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":Infinity,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect is not an object', () => {
        const result = parseAnnotationPositionJson('{"rects":[null]}');
        expect(result.ok).toBe(false);
    });

    it('does not mutate the input string', () => {
        const input = '{"pageIndex":0,"rects":[{"x":10,"y":20,"w":100,"h":30}]}';
        const frozen = String(input);
        parseAnnotationPositionJson(input);
        expect(input).toBe(frozen);
    });

    it('provides a stable friendly reason on failure', () => {
        const cases = [
            null,
            'not json',
            '{"rects":[]}',
            '{"rects":[{"x":"bad"}]}',
        ];
        for (const c of cases) {
            const result = parseAnnotationPositionJson(c);
            expect(result.ok).toBe(false);
            expect(typeof result.reason).toBe('string');
            // Reason must not contain stack traces, raw JSON dumps, shell output, or absolute paths
            expect(result.reason).not.toContain('Error');
            expect(result.reason).not.toContain('at ');
            expect(result.reason).not.toContain(':\\');
            expect(result.reason).not.toContain('Traceback');
        }
    });
});

// ---------------------------------------------------------------------------
// Task 1: normalizeAnnotationColor
// ---------------------------------------------------------------------------

describe('normalizeAnnotationColor', () => {
    it('returns the default yellow for null input', () => {
        expect(normalizeAnnotationColor(null)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for undefined input', () => {
        expect(normalizeAnnotationColor(undefined)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for empty string', () => {
        expect(normalizeAnnotationColor('')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for whitespace-only string', () => {
        expect(normalizeAnnotationColor('   ')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('passes through a valid #rrggbb hex color', () => {
        expect(normalizeAnnotationColor('#ffd400')).toBe('#ffd400');
    });

    it('passes through a valid #rgb shorthand hex', () => {
        expect(normalizeAnnotationColor('#ff0')).toBe('#ff0');
    });

    it('passes through a valid #rrggbbaa hex color', () => {
        expect(normalizeAnnotationColor('#ffd400aa')).toBe('#ffd400aa');
    });

    it('passes through a valid rgb() color', () => {
        expect(normalizeAnnotationColor('rgb(255, 212, 0)')).toBe('rgb(255, 212, 0)');
    });

    it('passes through a valid rgba() color', () => {
        expect(normalizeAnnotationColor('rgba(255, 212, 0, 0.5)')).toBe('rgba(255, 212, 0, 0.5)');
    });

    it('passes through common named colors', () => {
        expect(normalizeAnnotationColor('red')).toBe('red');
        expect(normalizeAnnotationColor('blue')).toBe('blue');
        expect(normalizeAnnotationColor('green')).toBe('green');
    });

    it('is case-insensitive for hex colors (preserves input case)', () => {
        const result = normalizeAnnotationColor('#FFD400');
        expect(result).toBe('#FFD400');
    });

    it('returns default yellow for unrecognized color string', () => {
        expect(normalizeAnnotationColor('not-a-color')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns default yellow for non-string input (number)', () => {
        expect(normalizeAnnotationColor(42)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the restrained default yellow (#ffd400) per D-06', () => {
        expect(DEFAULT_OVERLAY_HIGHLIGHT_COLOR).toBe('#ffd400');
    });
});

// ---------------------------------------------------------------------------
// Fixtures for Task 2: buildAnnotationOverlayMarks and buildAnnotationPopoverViewModel
// ---------------------------------------------------------------------------

const ATTACH_KEY_MAIN = 'STORAGE_ABC';
const ATTACH_KEY_SUPP = 'STORAGE_DEF';

/** A minimal paper entry with main PDF and supplementary. */
function makePaperEntry(overrides) {
    var o = overrides || {};
    return {
        pdf_path: '[[99_System/Zotero/storage/STORAGE_ABC/main.pdf]]',
        zotero_storage_key: 'STORAGE_ABC',
        supplementary: [
            '[[99_System/Zotero/storage/STORAGE_DEF/supp.pdf]]',
        ],
        ...o,
    };
}

/** Create a normalized annotation row for overlay testing.
 *  Uses property-level merging so overrides don't replace entire sub-objects. */
function makeAnnotationRow(overrides) {
    var o = overrides || {};
    return {
        display: Object.assign({
            page: 0,
            pageLabel: '1',
            type: 'highlight',
            color: '#ffd400',
            selectedText: 'selected text sample',
            comment: 'comment sample',
        }, o.display),
        provenance: Object.assign({
            source: 'zotero',
            isReadonly: true,
            sourceAttachmentKey: ATTACH_KEY_MAIN,
            sourceAnnotationKey: 'ANNOT_1',
        }, o.provenance),
        pdfLocation: Object.assign({
            pageIndex: 0,
            pageLabel: '1',
            sourceAttachmentKey: ATTACH_KEY_MAIN,
            positionJson: '{"pageIndex":0,"rects":[{"x":60.5,"y":72.3,"w":489.2,"h":18.1}]}',
            selectorJson: '{}',
            sortIndex: 0,
            rowId: 'r1',
        }, o.pdfLocation),
        raw: o.raw !== undefined ? o.raw : {},
    };
}

/** Create a mock annotationState in 'ready' state with given rows. */
function makeReadyState(rows) {
    return {
        state: 'ready',
        paperKey: 'PAPER_A',
        annotations: rows || [makeAnnotationRow()],
        message: '',
        errorCode: null,
        raw: null,
    };
}

const ACTIVE_PDF_PATH = '99_System/Zotero/storage/STORAGE_ABC/main.pdf';
const SUPP_PDF_PATH = '99_System/Zotero/storage/STORAGE_DEF/supp.pdf';
const WRONG_PDF_PATH = '99_System/Zotero/storage/WRONG/other.pdf';

// ---------------------------------------------------------------------------
// Task 2: buildAnnotationOverlayMarks
// ---------------------------------------------------------------------------

describe('buildAnnotationOverlayMarks', () => {
    it('returns disabled when annotation state is not ready', () => {
        const states = ['idle', 'loading', 'empty', 'missing-paper', 'missing-db', 'cli-error', 'invalid-json'];
        for (const s of states) {
            const result = buildAnnotationOverlayMarks({ state: s, annotations: [] }, makePaperEntry(), ACTIVE_PDF_PATH);
            expect(result.ok).toBe(false);
            expect(result.status).toBe('disabled');
            expect(result.marks).toEqual([]);
            expect(result.reason).toBeTruthy();
        }
    });

    it('returns disabled when annotation state is null', () => {
        const result = buildAnnotationOverlayMarks(null, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(false);
        expect(result.status).toBe('disabled');
    });

    it('returns disabled when paper entry is null', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, null, ACTIVE_PDF_PATH);
        expect(result.ok).toBe(false);
        expect(result.status).toBe('disabled');
    });

    it('returns disabled when activePdfPath is null', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), null);
        expect(result.ok).toBe(false);
        expect(result.status).toBe('disabled');
    });

    it('returns disabled when activePdfPath is empty string', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), '');
        expect(result.ok).toBe(false);
        expect(result.status).toBe('disabled');
    });

    it('returns empty status when no annotations in state', () => {
        const state = makeReadyState([]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.status).toBe('empty');
        expect(result.marks).toEqual([]);
        expect(result.skipped).toBe(0);
        expect(result.reason).toBeNull();
    });

    it('builds a mark for a valid row matching the active PDF', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.status).toBe('rendered');
        expect(result.marks).toHaveLength(1);
        expect(result.skipped).toBe(0);
        expect(result.reason).toBeNull();
    });

    it('includes required fields in the mark view-model', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        const mark = result.marks[0];
        expect(mark).toHaveProperty('id');
        expect(mark).toHaveProperty('pageIndex', 0);
        expect(mark).toHaveProperty('rects');
        expect(Array.isArray(mark.rects)).toBe(true);
        expect(mark.rects[0]).toHaveProperty('x');
        expect(mark.rects[0]).toHaveProperty('y');
        expect(mark.rects[0]).toHaveProperty('w');
        expect(mark.rects[0]).toHaveProperty('h');
        expect(mark).toHaveProperty('color', '#ffd400');
        expect(mark).toHaveProperty('selectedText', 'selected text sample');
        expect(mark).toHaveProperty('comment', 'comment sample');
        expect(mark).toHaveProperty('pageLabel');
        expect(mark).toHaveProperty('source', 'zotero');
        expect(mark).toHaveProperty('isReadonly', true);
        expect(mark).toHaveProperty('attachmentKey', ATTACH_KEY_MAIN);
        expect(mark).toHaveProperty('pdfPath', ACTIVE_PDF_PATH);
    });

    it('skips rows with wrong attachment key (D-07 mismatch)', () => {
        const row = makeAnnotationRow({
            provenance: { sourceAttachmentKey: 'UNKNOWN' },
            pdfLocation: { sourceAttachmentKey: 'UNKNOWN', pageIndex: 0, pageLabel: '1' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows whose resolved PDF does not match activePdfPath', () => {
        // Row targets the main PDF but we pass a wrong path
        const row = makeAnnotationRow(); // targets ATTACH_KEY_MAIN → main.pdf
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), WRONG_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows whose resolved PDF matches a supplementary but not the active path', () => {
        // Row targets supp PDF (ATTACH_KEY_SUPP) but active path is main.pdf
        const row = makeAnnotationRow({
            provenance: { sourceAttachmentKey: ATTACH_KEY_SUPP },
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_SUPP, pageIndex: 0, pageLabel: '1' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('renders supplementary annotations when supplementary PDF is the active path', () => {
        const row = makeAnnotationRow({
            provenance: { sourceAttachmentKey: ATTACH_KEY_SUPP },
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_SUPP, pageIndex: 0, pageLabel: '1' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), SUPP_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.status).toBe('rendered');
        expect(result.marks).toHaveLength(1);
    });

    it('skips rows with missing pageIndex', () => {
        const row = makeAnnotationRow({
            pdfLocation: {
                sourceAttachmentKey: ATTACH_KEY_MAIN,
                pageLabel: '1',
                positionJson: '{"rects":[{"x":60.5,"y":72.3,"w":489.2,"h":18.1}]}',
            },
        });
        delete row.pdfLocation.pageIndex;
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('uses pageIndex from Zotero positionJson when the database page_index is missing', () => {
        const row = makeAnnotationRow({
            pdfLocation: {
                sourceAttachmentKey: ATTACH_KEY_MAIN,
                pageIndex: null,
                pageLabel: '3',
                positionJson: '{"pageIndex":2,"rects":[[220.095,432.09,294.815,440.307]]}',
            },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.status).toBe('rendered');
        expect(result.skipped).toBe(0);
        expect(result.marks).toHaveLength(1);
        expect(result.marks[0].pageIndex).toBe(2);
        expect(result.marks[0].rects[0]).toEqual({ x: 220.095, y: 432.09, w: 74.72, h: 8.217 });
    });

    it('skips rows with negative pageIndex', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_MAIN, pageIndex: -1, pageLabel: '' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows with fractional pageIndex', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_MAIN, pageIndex: 0.5, pageLabel: '' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows with invalid positionJson', () => {
        const row = makeAnnotationRow({
            pdfLocation: {
                sourceAttachmentKey: ATTACH_KEY_MAIN,
                pageIndex: 0,
                pageLabel: '1',
                positionJson: 'not valid json',
            },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows with empty rects in positionJson', () => {
        const row = makeAnnotationRow({
            pdfLocation: {
                sourceAttachmentKey: ATTACH_KEY_MAIN,
                pageIndex: 0,
                pageLabel: '1',
                positionJson: '{"pageIndex":0,"rects":[]}',
            },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('skips rows with missing positionJson (null)', () => {
        const row = makeAnnotationRow({
            pdfLocation: {
                sourceAttachmentKey: ATTACH_KEY_MAIN,
                pageIndex: 0,
                pageLabel: '1',
                positionJson: null,
            },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(0);
        expect(result.skipped).toBe(1);
    });

    it('processes multiple rows: valid rendered, invalid skipped', () => {
        const validRow = makeAnnotationRow({
            provenance: { sourceAttachmentKey: ATTACH_KEY_MAIN, sourceAnnotationKey: 'VALID' },
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_MAIN, pageIndex: 0, pageLabel: '1', positionJson: '{"rects":[{"x":0,"y":0,"w":100,"h":20}]}' },
        });
        const invalidRow = makeAnnotationRow({
            provenance: { sourceAttachmentKey: 'UNKNOWN', sourceAnnotationKey: 'INVALID' },
            pdfLocation: { sourceAttachmentKey: 'UNKNOWN', pageIndex: 0, pageLabel: '1' },
        });
        const state = makeReadyState([validRow, invalidRow]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.ok).toBe(true);
        expect(result.marks).toHaveLength(1);
        expect(result.marks[0].id).toContain('VALID');
        expect(result.skipped).toBe(1);
    });

    it('uses the annotation color when available', () => {
        const row = makeAnnotationRow({
            display: { color: '#ff6666', selectedText: 'pink highlight' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.marks[0].color).toBe('#ff6666');
    });

    it('falls back to default color when annotation has no color', () => {
        const row = makeAnnotationRow({
            display: { color: null, selectedText: 'no color' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.marks[0].color).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('does not mutate the input annotationState', () => {
        const state = makeReadyState();
        const frozenState = JSON.stringify(state);
        buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(JSON.stringify(state)).toBe(frozenState);
    });

    it('does not mutate the input paper entry', () => {
        const entry = makePaperEntry();
        const frozenEntry = JSON.stringify(entry);
        buildAnnotationOverlayMarks(makeReadyState(), entry, ACTIVE_PDF_PATH);
        expect(JSON.stringify(entry)).toBe(frozenEntry);
    });

    it('returns stable status: rendered when marks exist', () => {
        const state = makeReadyState();
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.status).toBe('rendered');
    });

    it('returns stable status: empty when no marks after filtering', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: 'UNKNOWN', pageIndex: 0, pageLabel: '1' },
        });
        const state = makeReadyState([row]);
        const result = buildAnnotationOverlayMarks(state, makePaperEntry(), ACTIVE_PDF_PATH);
        expect(result.status).toBe('empty');
    });

    it('returns friendly reasons, not stack traces or raw values', () => {
        const disabledCases = [
            { state: null, entry: makePaperEntry(), path: ACTIVE_PDF_PATH },
            { state: makeReadyState(), entry: null, path: ACTIVE_PDF_PATH },
            { state: makeReadyState(), entry: makePaperEntry(), path: null },
        ];
        for (const c of disabledCases) {
            const result = buildAnnotationOverlayMarks(c.state, c.entry, c.path);
            expect(result.ok).toBe(false);
            expect(result.reason).toBeTruthy();
            expect(result.reason).not.toContain('Error');
            expect(result.reason).not.toContain('at ');
            expect(result.reason).not.toContain(':\\');
            expect(result.reason).not.toContain('Traceback');
        }
    });
});

// ---------------------------------------------------------------------------
// Task 2: buildAnnotationPopoverViewModel
// ---------------------------------------------------------------------------

describe('buildAnnotationPopoverViewModel', () => {
    it('returns ok:false with reason for null row', () => {
        const result = buildAnnotationPopoverViewModel(null);
        expect(result.ok).toBe(false);
        expect(result.data).toBeNull();
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for undefined row', () => {
        const result = buildAnnotationPopoverViewModel(undefined);
        expect(result.ok).toBe(false);
        expect(result.data).toBeNull();
    });

    it('returns popover data with expected fields for a valid row', () => {
        const row = makeAnnotationRow();
        const result = buildAnnotationPopoverViewModel(row);
        expect(result.ok).toBe(true);
        expect(result.reason).toBeNull();
        const data = result.data;
        expect(data).toHaveProperty('selectedText', 'selected text sample');
        expect(data).toHaveProperty('comment', 'comment sample');
        expect(data).toHaveProperty('pageLabel', '1');
        expect(data).toHaveProperty('pageNumber', 1);
        expect(data).toHaveProperty('type', 'highlight');
        expect(data).toHaveProperty('color', '#ffd400');
        expect(data).toHaveProperty('source', 'zotero');
        expect(data).toHaveProperty('isReadonly', true);
        expect(data).toHaveProperty('attachmentKey', ATTACH_KEY_MAIN);
        expect(data).toHaveProperty('annotationKey', 'ANNOT_1');
    });

    it('popover data has no edit/delete/create controls', () => {
        const row = makeAnnotationRow();
        const result = buildAnnotationPopoverViewModel(row);
        const data = result.data;
        // Must NOT contain write-back/database/evidence/delete/create/edit fields
        expect(data).not.toHaveProperty('edit');
        expect(data).not.toHaveProperty('delete');
        expect(data).not.toHaveProperty('remove');
        expect(data).not.toHaveProperty('create');
        expect(data).not.toHaveProperty('writeBack');
        expect(data).not.toHaveProperty('save');
        expect(data).not.toHaveProperty('database');
        expect(data).not.toHaveProperty('evidence');
        expect(data).not.toHaveProperty('actions');
        expect(data).not.toHaveProperty('controls');
    });

    it('popover data has no raw or internal fields', () => {
        const row = makeAnnotationRow();
        const result = buildAnnotationPopoverViewModel(row);
        const data = result.data;
        expect(data).not.toHaveProperty('raw');
        expect(data).not.toHaveProperty('error');
        expect(data).not.toHaveProperty('stack');
        expect(data).not.toHaveProperty('trace');
    });

    it('pageNumber is null when pageIndex is null', () => {
        const row = makeAnnotationRow({
            pdfLocation: { sourceAttachmentKey: ATTACH_KEY_MAIN, pageIndex: null, pageLabel: '' },
        });
        const result = buildAnnotationPopoverViewModel(row);
        expect(result.ok).toBe(true);
        expect(result.data.pageNumber).toBeNull();
    });

    it('popover data uses normalized color (fallback to default)', () => {
        const row = makeAnnotationRow({
            display: { color: null, selectedText: 'test' },
        });
        const result = buildAnnotationPopoverViewModel(row);
        expect(result.data.color).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('popover data is read-only (isReadonly preserved from provenance)', () => {
        const row = makeAnnotationRow({
            provenance: { isReadonly: true, source: 'zotero', sourceAttachmentKey: ATTACH_KEY_MAIN, sourceAnnotationKey: 'K' },
        });
        const result = buildAnnotationPopoverViewModel(row);
        expect(result.data.isReadonly).toBe(true);
    });

    it('does not mutate the input row', () => {
        const row = makeAnnotationRow();
        const frozen = JSON.stringify(row);
        buildAnnotationPopoverViewModel(row);
        expect(JSON.stringify(row)).toBe(frozen);
    });
});
