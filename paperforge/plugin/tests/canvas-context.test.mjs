/**
 * Vitest tests for canvas context and annotation contract modules.
 *
 * Tests cover:
 *   Task 1 — buildCanvasContextFromEntry: valid entry, missing paper,
 *            invalid entry, missing key, friendly reasons, no input mutation.
 *   Task 1 — buildMissingCanvasContext: default reason and custom reason.
 *   Task 1 — createCanvasAnnotationLoader: delegates to injected v0.2 loader
 *            with explicit paperKey, handles missing loader, handles blank key.
 *
 * @module tests/canvas-context
 */

import { describe, it, expect, vi } from 'vitest';

const {
    buildCanvasContextFromEntry,
    buildMissingCanvasContext,
} = await import('../src/canvas/context.js');

const {
    createCanvasAnnotationLoader,
    ANNOTATION_LOAD_STATES,
} = await import('../src/canvas/annotations.js');

// ── Fixtures ──

function makeEntry(overrides) {
    return {
        key: 'PAPER_A',
        title: 'Test Paper',
        authors: ['Author A'],
        year: 2024,
        ...overrides,
    };
}

const STATUS_OK = {
    ok: true,
    command: 'annotation.status',
    version: '1.0.0',
    data: {
        db_path: '/vault/System/PaperForge/indexes/annotations.db',
        db_available: true,
        total_annotations: 2,
        source_counts: { zotero: 2 },
        readonly_count: 2,
        deleted_count: 0,
        total_papers_with_annotations: 1,
    },
    error: null,
};

const EXPORT_OK = {
    ok: true,
    command: 'annotation.export',
    version: '1.0.0',
    data: {
        paper: 'PAPER_A',
        annotations: [
            { id: 'ann-1', type: 'highlight', color: '#ffd400', page_index: 0, page_label: '1', selected_text: 'Sample', comment: '', sort_index: 0, source: 'zotero', is_readonly: 1, source_attachment_key: 'ATTACH_A', source_annotation_key: 'ANN_1' },
        ],
        total: 1,
        format_version: '1.0',
    },
    error: null,
};

// ---------------------------------------------------------------------------
// buildCanvasContextFromEntry
// ---------------------------------------------------------------------------

describe('buildCanvasContextFromEntry', () => {
    it('returns ok:true with paperKey and entry for a valid entry', () => {
        const entry = makeEntry({ key: 'VALID_KEY' });
        const result = buildCanvasContextFromEntry(entry);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('VALID_KEY');
        expect(result.entry).toBe(entry);
        expect(result.reason).toBeNull();
    });

    it('returns ok:false with reason when entry is null', () => {
        const result = buildCanvasContextFromEntry(null);

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.entry).toBeNull();
        expect(result.reason).toBeTruthy();
        expect(typeof result.reason).toBe('string');
    });

    it('returns ok:false with reason when entry is undefined', () => {
        const result = buildCanvasContextFromEntry(undefined);

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.entry).toBeNull();
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false with reason when entry has no key property', () => {
        const result = buildCanvasContextFromEntry({ title: 'No Key Paper' });

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.entry).toBeNull();
        expect(result.reason).toContain('no key');
    });

    it('returns ok:false with reason when entry.key is null', () => {
        const result = buildCanvasContextFromEntry(makeEntry({ key: null }));

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.reason).toContain('no key');
    });

    it('returns ok:false with reason when entry.key is empty string', () => {
        const result = buildCanvasContextFromEntry(makeEntry({ key: '' }));

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.reason).toContain('no key');
    });

    it('returns ok:false with reason when entry.key is only whitespace', () => {
        const result = buildCanvasContextFromEntry(makeEntry({ key: '   ' }));

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.reason).toContain('no key');
    });

    it('accepts PaperForge index entries that identify papers with zotero_key', () => {
        const entry = {
            zotero_key: 'A7N8GAHS',
            title: 'TROP2 targeting reveals therapy-driven cell state dynamics in colorectal cancer',
            fulltext_path: '4.Paper/Literature/肿瘤可塑性/A7N8GAHS/fulltext.md',
        };

        const result = buildCanvasContextFromEntry(entry);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('A7N8GAHS');
        expect(result.entry).toBe(entry);
        expect(result.reason).toBeNull();
    });

    it('falls back to zotero_key when entry.key is blank', () => {
        const entry = makeEntry({ key: '', zotero_key: 'ZOTERO_KEY' });

        const result = buildCanvasContextFromEntry(entry);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('ZOTERO_KEY');
    });

    it('returns friendly reason messages without raw error signatures', () => {
        const nullResult = buildCanvasContextFromEntry(null);
        const noKeyResult = buildCanvasContextFromEntry({ title: 'x' });

        for (const r of [nullResult, noKeyResult]) {
            expect(r.reason).not.toContain('Traceback');
            expect(r.reason).not.toContain('Error:');
            expect(r.reason).not.toContain('undefined');
            expect(r.reason).not.toContain('[object Object]');
        }
    });

    it('does not mutate the input entry object', () => {
        const entry = makeEntry({ key: 'MY_KEY', extraField: 'value' });
        const frozen = Object.freeze({ ...entry });
        const result = buildCanvasContextFromEntry(frozen);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('MY_KEY');
        // Input should not be modified — it was frozen so any mutation attempt
        // would throw in strict mode. Just confirming the result is correct.
        expect(result.entry).toBe(frozen);
    });

    it('treats entry.key as authoritative — reads from key property', () => {
        const entry = makeEntry({ key: 'AUTHORITATIVE_KEY', zotero_key: 'ZOTERO_KEY' });
        const result = buildCanvasContextFromEntry(entry);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('AUTHORITATIVE_KEY');
    });

    it('converts non-string key to string', () => {
        const entry = makeEntry({ key: 12345 });
        const result = buildCanvasContextFromEntry(entry);

        expect(result.ok).toBe(true);
        expect(result.paperKey).toBe('12345');
    });
});

// ---------------------------------------------------------------------------
// buildMissingCanvasContext
// ---------------------------------------------------------------------------

describe('buildMissingCanvasContext', () => {
    it('returns ok:false with default reason when no argument provided', () => {
        const result = buildMissingCanvasContext();

        expect(result.ok).toBe(false);
        expect(result.paperKey).toBeNull();
        expect(result.entry).toBeNull();
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false with custom reason when provided', () => {
        const result = buildMissingCanvasContext('Index is not loaded yet.');

        expect(result.ok).toBe(false);
        expect(result.reason).toBe('Index is not loaded yet.');
    });

    it('returns ok:false with default reason when empty string provided', () => {
        const result = buildMissingCanvasContext('');

        expect(result.ok).toBe(false);
        expect(result.reason).toBe('Paper context is not available.');
    });

    it('friendly reason without raw error signatures', () => {
        const result = buildMissingCanvasContext('Paper not found in index.');

        expect(result.reason).not.toContain('Traceback');
        expect(result.reason).not.toContain('Error:');
    });
});

// ---------------------------------------------------------------------------
// createCanvasAnnotationLoader — delegation tests
// ---------------------------------------------------------------------------

describe('createCanvasAnnotationLoader — delegation', () => {
    it('delegates to injected loadAnnotationsForPaper with explicit paperKey', async () => {
        const mockLoader = vi.fn(async ({ paperKey }) => ({
            state: 'ready',
            paperKey,
            annotations: [],
            message: 'Loaded.',
            errorCode: null,
            raw: null,
        }));

        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: mockLoader });
        const result = await loader.loadForPaper('MY_KEY');

        expect(mockLoader).toHaveBeenCalledTimes(1);
        // The loader must be called with the explicit paperKey
        expect(mockLoader.mock.calls[0][0].paperKey).toBe('MY_KEY');
        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe('MY_KEY');
    });

    it('delegates load options to the injected loader', async () => {
        const mockLoader = vi.fn(async ({ paperKey }) => ({
            state: 'ready',
            paperKey,
            annotations: [],
            message: 'Loaded.',
            errorCode: null,
            raw: null,
        }));

        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: mockLoader });
        await loader.loadForPaper('MY_KEY', { pythonExe: 'python3', cwd: '/vault', timeout: 5000 });

        const callOpts = mockLoader.mock.calls[0][0];
        expect(callOpts.paperKey).toBe('MY_KEY');
        expect(callOpts.pythonExe).toBe('python3');
        expect(callOpts.cwd).toBe('/vault');
        expect(callOpts.timeout).toBe(5000);
    });

    it('returns missing-paper state when paperKey is null', async () => {
        const mockLoader = vi.fn();
        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: mockLoader });
        const result = await loader.loadForPaper(null);

        expect(result.state).toBe('missing-paper');
        expect(result.paperKey).toBeNull();
        // Must not delegate to the loader when key is missing
        expect(mockLoader).not.toHaveBeenCalled();
    });

    it('returns missing-paper state when paperKey is empty string', async () => {
        const mockLoader = vi.fn();
        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: mockLoader });
        const result = await loader.loadForPaper('');

        expect(result.state).toBe('missing-paper');
        expect(mockLoader).not.toHaveBeenCalled();
    });

    it('returns idle/default state when no loader is injected', async () => {
        const loader = createCanvasAnnotationLoader({});
        const result = await loader.loadForPaper('PAPER_A');

        expect(result.state).toBeDefined();
        expect(result.paperKey).toBe('PAPER_A');
        expect(result.message).toBeTruthy();
    });

    it('returns idle/default state when loadAnnotationsForPaper is not a function', async () => {
        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: 'not-a-function' });
        const result = await loader.loadForPaper('PAPER_A');

        expect(result.state).toBeDefined();
        expect(result.paperKey).toBe('PAPER_A');
        expect(result.message).toBeTruthy();
    });

    it('accepts loader alias for convenience', async () => {
        const mockLoader = vi.fn(async ({ paperKey }) => ({
            state: 'ready',
            paperKey,
            annotations: [],
            message: 'Loaded.',
            errorCode: null,
            raw: null,
        }));

        const loader = createCanvasAnnotationLoader({ loader: mockLoader });
        const result = await loader.loadForPaper('PAPER_A');

        expect(mockLoader).toHaveBeenCalledTimes(1);
        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe('PAPER_A');
    });

    it('prefers loadAnnotationsForPaper over loader alias when both present', async () => {
        const primaryLoader = vi.fn(async ({ paperKey }) => ({
            state: 'ready', paperKey, annotations: [], message: 'Primary.', errorCode: null, raw: null,
        }));
        const aliasLoader = vi.fn();

        const loader = createCanvasAnnotationLoader({
            loadAnnotationsForPaper: primaryLoader,
            loader: aliasLoader,
        });
        await loader.loadForPaper('PAPER_A');

        expect(primaryLoader).toHaveBeenCalledTimes(1);
        expect(aliasLoader).not.toHaveBeenCalled();
    });
});

// ---------------------------------------------------------------------------
// createCanvasAnnotationLoader — delegates to real v0.2 loader via paperKey
// ---------------------------------------------------------------------------

describe('createCanvasAnnotationLoader — delegates to v0.2 loader with paperKey', () => {
    it('forwards the exact paperKey string to the injected loader', async () => {
        const sentinelKey = 'SENTINEL_KEY_42';
        const mockLoader = vi.fn(async ({ paperKey }) => ({
            state: 'ready',
            paperKey,
            annotations: [],
            message: `Loaded ${paperKey}`,
            errorCode: null,
            raw: null,
        }));

        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: mockLoader });
        await loader.loadForPaper(sentinelKey);

        // Verify the exact paperKey is forwarded
        expect(mockLoader.mock.calls[0][0].paperKey).toBe(sentinelKey);
    });

    it('wraps the existing makeAnnotationState / loadAnnotationsForPaper return shape', async () => {
        // Simulate the real v0.2 loader returning the contract shape
        const realContractLoader = async ({ paperKey }) => ({
            state: 'ready',
            paperKey: paperKey,
            annotations: [
                { display: { page: 1, type: 'highlight' }, provenance: { source: 'zotero' }, pdfLocation: {}, raw: {} },
            ],
            message: '1 annotation(s) loaded.',
            errorCode: null,
            raw: { exportPfResult: EXPORT_OK, statusPfResult: STATUS_OK },
        });

        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: realContractLoader });
        const result = await loader.loadForPaper('PAPER_A');

        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe('PAPER_A');
        expect(Array.isArray(result.annotations)).toBe(true);
        expect(result.annotations.length).toBe(1);
        expect(result.annotations[0]).toHaveProperty('display');
        expect(result.annotations[0]).toHaveProperty('provenance');
        expect(result.raw).toBeTruthy();
    });

    it('preserves load state names from the v0.2 contract', () => {
        const states = ANNOTATION_LOAD_STATES;
        expect(states.IDLE).toBe('idle');
        expect(states.LOADING).toBe('loading');
        expect(states.READY).toBe('ready');
        expect(states.EMPTY).toBe('empty');
        expect(states.MISSING_PAPER).toBe('missing-paper');
        expect(states.MISSING_DB).toBe('missing-db');
        expect(states.CLI_ERROR).toBe('cli-error');
        expect(states.INVALID_JSON).toBe('invalid-json');
    });

    it('getLoadStates returns the v0.2-compatible load state names', () => {
        const loader = createCanvasAnnotationLoader({});
        const states = loader.getLoadStates();
        expect(states.READY).toBe('ready');
        expect(states.EMPTY).toBe('empty');
        expect(states.CLI_ERROR).toBe('cli-error');
    });
});
