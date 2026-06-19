/**
 * Vitest tests for annotation bridge helpers — normalizeAnnotationExportRow,
 * annotation load states, buildAnnotationStatusArgs, buildAnnotationExportArgs,
 * and loadAnnotationsForPaper.
 *
 * Uses the existing runSubprocess injection pattern: loadAnnotationsForPaper
 * accepts an optional runSubprocessFn that, when provided, replaces the default
 * runSubprocess call returning Promise<{stdout, stderr, exitCode}>.
 */
import { describe, it, expect, vi } from 'vitest';

const {
    normalizeAnnotationExportRow,
    makeAnnotationState,
    ANNOTATION_LOAD_STATES,
    buildAnnotationStatusArgs,
    buildAnnotationExportArgs,
    loadAnnotationsForPaper,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Representative PFResult fixtures based on Python CLI contract tests
// ---------------------------------------------------------------------------

const PAPER_KEY_A = 'PAPER_A';
const PAPER_KEY_B = 'PAPER_B';

/** An export row matching the _rows_to_export() shape from annotation.py. */
function makeExportRow(overrides = {}) {
    return {
        id: 'zotero:1:ATTACH_A:ANNOT_1',
        paper_id: PAPER_KEY_A,
        source: 'zotero',
        source_library_id: '1',
        source_annotation_key: 'ANNOT_1',
        source_attachment_key: 'ATTACH_A',
        source_parent_key: 'PARENT_A',
        source_modified_at: '2024-01-15T10:00:00Z',
        type: 'highlight',
        page_index: 0,
        page_label: '1',
        selected_text: 'selected text A1',
        comment: 'comment A1',
        color: '#ffd400',
        sort_index: 0,
        tags_json: '["tag1"]',
        position_json: '{"pageIndex":0,"rects":[{"x":0,"y":0,"w":100,"h":20}]}',
        selector_json: '{}',
        sync_state: 'imported',
        is_readonly: 1,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        deleted_at: null,
        ...overrides,
    };
}

/** PFResult envelope for annotation status --json with db_available = true. */
const STATUS_OK = {
    ok: true,
    command: 'annotation.status',
    version: '1.0.0',
    data: {
        db_path: '/vault/System/PaperForge/indexes/annotations.db',
        schema_version: 1,
        total_annotations: 2,
        source_counts: { zotero: 2 },
        readonly_count: 2,
        deleted_count: 0,
        db_available: true,
        total_papers_with_annotations: 1,
    },
    error: null,
};

/** PFResult envelope for annotation status --json with db_available = false. */
const STATUS_DB_MISSING = {
    ok: true,
    command: 'annotation.status',
    version: '1.0.0',
    data: {
        db_path: null,
        schema_version: 0,
        total_annotations: 0,
        source_counts: {},
        readonly_count: 0,
        deleted_count: 0,
        db_available: false,
        total_papers_with_annotations: 0,
    },
    error: null,
};

/** PFResult for annotation export --paper KEY --json with annotations. */
const EXPORT_OK = {
    ok: true,
    command: 'annotation.export',
    version: '1.0.0',
    data: {
        paper: PAPER_KEY_A,
        annotations: [
            makeExportRow({ id: 'annot-1', type: 'highlight', color: '#ffd400', comment: 'comment A1' }),
            makeExportRow({
                id: 'annot-2',
                type: 'note',
                page_index: 1,
                page_label: '2',
                color: '#ff6666',
                selected_text: 'selected text A2',
                comment: '',
                sort_index: 1,
            }),
        ],
        total: 2,
        format_version: '1.0',
    },
    error: null,
};

/** PFResult for annotation export --paper KEY --json with zero annotations. */
const EXPORT_EMPTY = {
    ok: true,
    command: 'annotation.export',
    version: '1.0.0',
    data: {
        paper: PAPER_KEY_A,
        annotations: [],
        total: 0,
        format_version: '1.0',
    },
    error: null,
};

/** PFResult error envelope representing a CLI failure. */
const CLI_ERROR_PF = {
    ok: false,
    command: 'annotation.export',
    version: '1.0.0',
    data: null,
    error: {
        code: 'INTERNAL_ERROR',
        message: 'Error reading annotation database',
        details: { exception: 'RuntimeError("corrupt database")' },
        suggestions: ['Run doctor to check database health'],
    },
};

// ---------------------------------------------------------------------------
// Task 1: normalizedAnnotationExportRow
// ---------------------------------------------------------------------------

describe('normalizeAnnotationExportRow', () => {
    it('returns {display, provenance, pdfLocation, raw} preserving exact input', () => {
        const row = makeExportRow();
        const result = normalizeAnnotationExportRow(row);

        expect(result).toHaveProperty('display');
        expect(result).toHaveProperty('provenance');
        expect(result).toHaveProperty('pdfLocation');
        expect(result).toHaveProperty('raw');
        // raw must reference the exact same input object
        expect(result.raw).toBe(row);
    });

    it('maps display fields: page, pageLabel, type, color, selectedText, comment', () => {
        const row = makeExportRow({
            page_index: 0,
            page_label: '1',
            type: 'highlight',
            color: '#ffd400',
            selected_text: 'hello world',
            comment: 'my comment',
        });
        const result = normalizeAnnotationExportRow(row);

        expect(result.display.page).toBe(0);
        expect(result.display.pageLabel).toBe('1');
        expect(result.display.type).toBe('highlight');
        expect(result.display.color).toBe('#ffd400');
        expect(result.display.selectedText).toBe('hello world');
        expect(result.display.comment).toBe('my comment');
    });

    it('maps provenance fields from full export row', () => {
        const row = makeExportRow({
            source: 'zotero',
            is_readonly: 1,
            source_library_id: '1',
            source_parent_key: 'PARENT_A',
            source_attachment_key: 'ATTACH_A',
            source_annotation_key: 'ANNOT_1',
            sync_state: 'imported',
            source_modified_at: '2024-01-15T10:00:00Z',
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            deleted_at: '2024-06-01T00:00:00Z',
        });
        const result = normalizeAnnotationExportRow(row);

        expect(result.provenance.source).toBe('zotero');
        expect(result.provenance.isReadonly).toBe(true);
        expect(result.provenance.sourceLibraryId).toBe('1');
        expect(result.provenance.sourceParentKey).toBe('PARENT_A');
        expect(result.provenance.sourceAttachmentKey).toBe('ATTACH_A');
        expect(result.provenance.sourceAnnotationKey).toBe('ANNOT_1');
        expect(result.provenance.syncState).toBe('imported');
        expect(result.provenance.sourceModifiedAt).toBe('2024-01-15T10:00:00Z');
        expect(result.provenance.createdAt).toBe('2024-01-15T10:00:00Z');
        expect(result.provenance.updatedAt).toBe('2024-01-15T10:00:00Z');
        expect(result.provenance.deletedAt).toBe('2024-06-01T00:00:00Z');
    });

    it('maps pdfLocation fields', () => {
        const row = makeExportRow({
            page_index: 2,
            page_label: '3',
            source_attachment_key: 'ATTACH_A',
            position_json: '{"pageIndex":2,"rects":[]}',
            selector_json: '{"type":"text","value":"test"}',
            sort_index: 1,
            id: 'annot-id-123',
        });
        const result = normalizeAnnotationExportRow(row);

        expect(result.pdfLocation.pageIndex).toBe(2);
        expect(result.pdfLocation.pageLabel).toBe('3');
        expect(result.pdfLocation.sourceAttachmentKey).toBe('ATTACH_A');
        expect(result.pdfLocation.positionJson).toBe('{"pageIndex":2,"rects":[]}');
        expect(result.pdfLocation.selectorJson).toBe('{"type":"text","value":"test"}');
        expect(result.pdfLocation.sortIndex).toBe(1);
        expect(result.pdfLocation.rowId).toBe('annot-id-123');
    });

    it('handles is_readonly zero to become false', () => {
        const row = makeExportRow({ is_readonly: 0 });
        const result = normalizeAnnotationExportRow(row);
        expect(result.provenance.isReadonly).toBe(false);
    });

    it('handles null timestamps gracefully', () => {
        const row = makeExportRow({
            source_modified_at: null,
            created_at: null,
            updated_at: null,
            deleted_at: null,
        });
        const result = normalizeAnnotationExportRow(row);
        expect(result.provenance.sourceModifiedAt).toBeNull();
        expect(result.provenance.createdAt).toBeNull();
        expect(result.provenance.updatedAt).toBeNull();
        expect(result.provenance.deletedAt).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Task 1: Annotation load states
// ---------------------------------------------------------------------------

describe('ANNOTATION_LOAD_STATES', () => {
    it('lists all eight required state names', () => {
        const names = Object.values(ANNOTATION_LOAD_STATES);
        expect(names).toContain('idle');
        expect(names).toContain('loading');
        expect(names).toContain('ready');
        expect(names).toContain('empty');
        expect(names).toContain('missing-paper');
        expect(names).toContain('missing-db');
        expect(names).toContain('cli-error');
        expect(names).toContain('invalid-json');
        expect(names.length).toBe(8);
    });

    it('state names are stable strings', () => {
        expect(ANNOTATION_LOAD_STATES.IDLE).toBe('idle');
        expect(ANNOTATION_LOAD_STATES.LOADING).toBe('loading');
        expect(ANNOTATION_LOAD_STATES.READY).toBe('ready');
        expect(ANNOTATION_LOAD_STATES.EMPTY).toBe('empty');
        expect(ANNOTATION_LOAD_STATES.MISSING_PAPER).toBe('missing-paper');
        expect(ANNOTATION_LOAD_STATES.MISSING_DB).toBe('missing-db');
        expect(ANNOTATION_LOAD_STATES.CLI_ERROR).toBe('cli-error');
        expect(ANNOTATION_LOAD_STATES.INVALID_JSON).toBe('invalid-json');
    });
});

describe('makeAnnotationState', () => {
    const testAnnotations = [makeExportRow()].map(normalizeAnnotationExportRow);

    it('creates an idle state with default empty values', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
        expect(state.state).toBe('idle');
        expect(state.paperKey).toBeNull();
        expect(state.annotations).toEqual([]);
        expect(state.message).toBe('');
        expect(state.errorCode).toBeNull();
        expect(state.raw).toBeNull();
    });

    it('creates a ready state with provided fields', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: PAPER_KEY_A,
            annotations: testAnnotations,
            message: '2 annotations loaded',
            errorCode: null,
            raw: EXPORT_OK,
        });

        expect(state.state).toBe('ready');
        expect(state.paperKey).toBe(PAPER_KEY_A);
        expect(state.annotations).toEqual(testAnnotations);
        expect(state.message).toBe('2 annotations loaded');
        expect(state.errorCode).toBeNull();
        expect(state.raw).toStrictEqual(EXPORT_OK);
    });

    it('creates a missing-paper state', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_PAPER, {
            paperKey: null,
            annotations: [],
            message: 'No paper is currently active',
            errorCode: null,
        });
        expect(state.state).toBe('missing-paper');
        expect(state.message).toContain('No paper');
    });

    it('creates a missing-db state', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
            paperKey: PAPER_KEY_A,
            annotations: [],
            message: 'Annotation database is not yet available',
            errorCode: null,
            raw: { subprocessOutput: '...' },
        });
        expect(state.state).toBe('missing-db');
    });

    it('creates an empty state with paperKey and no annotations', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.EMPTY, {
            paperKey: PAPER_KEY_A,
            annotations: [],
            message: 'This paper has no annotations',
        });
        expect(state.state).toBe('empty');
        expect(state.paperKey).toBe(PAPER_KEY_A);
        expect(state.annotations).toEqual([]);
    });

    it('creates a cli-error state with errorCode and message', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.CLI_ERROR, {
            paperKey: PAPER_KEY_A,
            annotations: [],
            message: 'Failed to load annotations from CLI',
            errorCode: 'INTERNAL_ERROR',
            raw: CLI_ERROR_PF,
        });
        expect(state.state).toBe('cli-error');
        expect(state.errorCode).toBe('INTERNAL_ERROR');
        expect(state.message).toContain('Failed to load');
    });

    it('creates an invalid-json state preserving raw stdout for debugging', () => {
        const badOutput = '<html>not json</html>';
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.INVALID_JSON, {
            paperKey: PAPER_KEY_A,
            annotations: [],
            message: 'Annotation data could not be parsed',
            errorCode: null,
            raw: { stdout: badOutput, stderr: 'error' },
        });
        expect(state.state).toBe('invalid-json');
        expect(state.raw.stdout).toBe(badOutput);
        // User-facing message must NOT expose raw output
        expect(state.message).not.toContain('<html>');
    });

    it('creates a loading state', () => {
        const state = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey: PAPER_KEY_A,
            annotations: [],
            message: 'Loading annotations...',
        });
        expect(state.state).toBe('loading');
        expect(state.paperKey).toBe(PAPER_KEY_A);
    });
});

// ---------------------------------------------------------------------------
// Task 2: buildAnnotationStatusArgs
// ---------------------------------------------------------------------------

describe('buildAnnotationStatusArgs', () => {
    it('builds args for "-m paperforge annotation status --json"', () => {
        const args = buildAnnotationStatusArgs([]);
        expect(args).toEqual(['-m', 'paperforge', 'annotation', 'status', '--json']);
    });

    it('includes extra args when provided', () => {
        const args = buildAnnotationStatusArgs(['--vault', '/my/vault']);
        expect(args).toEqual(['-m', 'paperforge', 'annotation', 'status', '--json', '--vault', '/my/vault']);
    });

    it('returns a fresh array each call', () => {
        const a = buildAnnotationStatusArgs([]);
        const b = buildAnnotationStatusArgs([]);
        expect(a).toEqual(b);
        expect(a).not.toBe(b);
    });
});

// ---------------------------------------------------------------------------
// Task 2: buildAnnotationExportArgs
// ---------------------------------------------------------------------------

describe('buildAnnotationExportArgs', () => {
    it('builds args for "-m paperforge annotation export --paper KEY --json"', () => {
        const args = buildAnnotationExportArgs(PAPER_KEY_A, []);
        const expected = ['-m', 'paperforge', 'annotation', 'export', '--paper', PAPER_KEY_A, '--json'];
        expect(args).toEqual(expected);
    });

    it('includes extra args after json flag', () => {
        const args = buildAnnotationExportArgs(PAPER_KEY_A, ['--vault', '/vault']);
        expect(args).toEqual([
            '-m', 'paperforge', 'annotation', 'export',
            '--paper', PAPER_KEY_A, '--json',
            '--vault', '/vault',
        ]);
    });

    it('returns a fresh array each call', () => {
        const a = buildAnnotationExportArgs(PAPER_KEY_A, []);
        const b = buildAnnotationExportArgs(PAPER_KEY_A, []);
        expect(a).toEqual(b);
        expect(a).not.toBe(b);
    });
});

// ---------------------------------------------------------------------------
// Task 2: Mock subprocess helper
// ---------------------------------------------------------------------------

/**
 * Creates a mock for the runSubprocess injection pattern.
 * The returned mockRunSubprocessFn is a vi.fn that resolves with
 * { stdout, stderr, exitCode } — matching runSubprocess return shape.
 *
 * Use mockStatusResponse / mockExportResponse / mockRunOnce to queue
 * sequential subprocess call results (status first, then export).
 */
function mockSubprocessSequence(responses) {
    const fn = vi.fn();
    for (const r of responses) {
        fn.mockResolvedValueOnce(r);
    }
    return fn;
}

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — blank / missing paper
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — blank key (missing-paper)', () => {
    it('returns missing-paper without spawning subprocess when paperKey is null', async () => {
        const mockFn = vi.fn();
        const result = await loadAnnotationsForPaper({
            paperKey: null,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('missing-paper');
        expect(mockFn).not.toHaveBeenCalled();
    });

    it('returns missing-paper without spawning subprocess when paperKey is empty string', async () => {
        const mockFn = vi.fn();
        const result = await loadAnnotationsForPaper({
            paperKey: '',
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('missing-paper');
        expect(mockFn).not.toHaveBeenCalled();
    });

    it('returns missing-paper with friendly message', async () => {
        const result = await loadAnnotationsForPaper({
            paperKey: null,
            runSubprocessFn: vi.fn(),
        });
        expect(result.message).toBeTruthy();
        expect(result.message).not.toContain('Traceback');
        expect(result.message).not.toContain('Error:');
    });
});

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — missing DB
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — missing-db', () => {
    it('returns missing-db when status reports db_available === false', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_DB_MISSING), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            pythonExe: 'python',
            cwd: '/vault',
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('missing-db');
        expect(result.paperKey).toBe(PAPER_KEY_A);
        expect(result.annotations).toEqual([]);
        expect(result.raw).toBeTruthy();
        expect(result.raw).toHaveProperty('statusPfResult');

        // Verify status args were built correctly
        const statusCall = mockFn.mock.calls[0];
        expect(statusCall[0]).toBe('python');
        expect(statusCall[1]).toContain('status');
        expect(statusCall[1]).toContain('--json');
    });

    it('does NOT interpret missing-db as empty', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_DB_MISSING), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).not.toBe('empty');
        expect(result.state).toBe('missing-db');
    });

    it('only calls status once for missing-db', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_DB_MISSING), stderr: '', exitCode: 0 },
        ]);

        await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        // Only status was called, not export
        expect(mockFn).toHaveBeenCalledTimes(1);
    });

    it('returns missing-db with friendly user message', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_DB_MISSING), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.message).toBeTruthy();
        expect(result.message).not.toContain('Traceback');
    });
});

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — empty paper
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — empty', () => {
    it('returns empty when status is available but export has zero annotations', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_EMPTY), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('empty');
        expect(result.paperKey).toBe(PAPER_KEY_A);
        expect(result.annotations).toEqual([]);
    });

    it('does not mix up missing-db and empty', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_EMPTY), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_B,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('empty');
        expect(result.errorCode).toBeNull();
    });

    it('calls export with correct paper key', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_EMPTY), stderr: '', exitCode: 0 },
        ]);

        await loadAnnotationsForPaper({
            paperKey: 'MY_PAPER',
            runSubprocessFn: mockFn,
        });

        const exportCall = mockFn.mock.calls[1];
        expect(exportCall[1]).toContain('export');
        expect(exportCall[1]).toContain('--paper');
        expect(exportCall[1]).toContain('MY_PAPER');
    });
});

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — ready / success
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — ready', () => {
    it('returns ready with normalized rows when status and export succeed', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe(PAPER_KEY_A);
        expect(Array.isArray(result.annotations)).toBe(true);
        expect(result.annotations.length).toBe(2);

        // Each row is normalized
        for (const ann of result.annotations) {
            expect(ann).toHaveProperty('display');
            expect(ann).toHaveProperty('provenance');
            expect(ann).toHaveProperty('pdfLocation');
            expect(ann).toHaveProperty('raw');
        }

        expect(result.errorCode).toBeNull();
    });

    it('normalized rows have expected display fields', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        const first = result.annotations[0];
        expect(first.display).toHaveProperty('page');
        expect(first.display).toHaveProperty('pageLabel');
        expect(first.display).toHaveProperty('type');
        expect(first.display).toHaveProperty('color');
        expect(first.display).toHaveProperty('selectedText');
        expect(first.display).toHaveProperty('comment');
    });
});

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — CLI error
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — cli-error', () => {
    it('returns cli-error when PFResult has ok: false from export', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(CLI_ERROR_PF), stderr: '', exitCode: 1 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('cli-error');
        expect(result.errorCode).toBe('INTERNAL_ERROR');
        // User-facing message must be friendly
        expect(result.message).toBeTruthy();
        expect(result.message).not.toContain('Traceback');
    });

    it('returns cli-error when subprocess exits with non-zero and garbage output', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: 'garbage output', stderr: 'something went wrong', exitCode: 1 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('cli-error');
        expect(result.errorCode).toBeTruthy();
        // Message is friendly
        expect(result.message).toBeTruthy();
        expect(result.message).not.toContain('Traceback');
    });

    it('captures raw subprocess output in detail field', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: 'raw error', stderr: 'stderr error msg', exitCode: 1 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.raw).toBeTruthy();
        // Should preserve raw output for debugging
        expect(result.raw.stdout).toBe('raw error');
        expect(result.raw.stderr).toBe('stderr error msg');
    });
});

// ---------------------------------------------------------------------------
// Task 2: loadAnnotationsForPaper — invalid JSON
// ---------------------------------------------------------------------------

describe('loadAnnotationsForPaper — invalid-json', () => {
    it('returns invalid-json when status stdout is not valid JSON', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: 'not json at all', stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('invalid-json');
        expect(result.raw).toBeTruthy();
        // Must preserve raw stdout for debugging
        expect(result.raw.stdout).toBe('not json at all');
        // But user-facing message must NOT contain raw strings
        expect(result.message).not.toContain('not json at all');
    });

    it('returns invalid-json when export stdout is not valid JSON', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: '{invalid: true}', stderr: '', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('invalid-json');
        // Must not re-interpret invalid JSON as empty
        expect(result.state).not.toBe('empty');
        expect(result.state).not.toBe('ready');
    });

    it('preserves raw stdout/stderr in raw field for debugging', async () => {
        const mockFn = mockSubprocessSequence([
            { stdout: 'not-json', stderr: 'stderr content', exitCode: 0 },
        ]);

        const result = await loadAnnotationsForPaper({
            paperKey: PAPER_KEY_A,
            runSubprocessFn: mockFn,
        });

        expect(result.raw.stdout).toBe('not-json');
        expect(result.raw.stderr).toBe('stderr content');
    });
});
