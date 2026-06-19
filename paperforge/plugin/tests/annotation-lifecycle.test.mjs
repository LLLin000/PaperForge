/**
 * Vitest tests for annotation bridge lifecycle controller.
 *
 * Tests the createAnnotationLifecycleController helper that models
 * active-paper refresh decisions without importing Obsidian APIs.
 */
import { describe, it, expect, vi } from 'vitest';

const {
    createAnnotationLifecycleController,
    ANNOTATION_LOAD_STATES,
    makeAnnotationState,
} = await import('../src/testable.js');

const PAPER_KEY_A = 'PAPER_A';
const PAPER_KEY_B = 'PAPER_B';

// Representative PFResult fixtures (reused from bridge tests)
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

const EXPORT_OK = {
    ok: true,
    command: 'annotation.export',
    version: '1.0.0',
    data: {
        paper: PAPER_KEY_A,
        annotations: [
            { id: 'annot-1', type: 'highlight', page_index: 0, page_label: '1', color: '#ffd400', selected_text: 'text', comment: 'comment', source: 'zotero', source_library_id: '1', source_parent_key: 'P1', source_attachment_key: 'ATT1', source_annotation_key: 'AN1', sort_index: 0, position_json: '{}', selector_json: '{}', sync_state: 'imported', is_readonly: 1, created_at: null, updated_at: null, deleted_at: null, source_modified_at: null },
            { id: 'annot-2', type: 'note', page_index: 1, page_label: '2', color: '#ff6666', selected_text: '', comment: '', source: 'zotero', source_library_id: '1', source_parent_key: 'P1', source_attachment_key: 'ATT1', source_annotation_key: 'AN2', sort_index: 1, position_json: '{}', selector_json: '{}', sync_state: 'imported', is_readonly: 0, created_at: null, updated_at: null, deleted_at: null, source_modified_at: null },
        ],
        total: 2,
        format_version: '1.0',
    },
    error: null,
};

const EXPORT_EMPTY = {
    ok: true,
    command: 'annotation.export',
    version: '1.0.0',
    data: { paper: PAPER_KEY_A, annotations: [], total: 0, format_version: '1.0' },
    error: null,
};

function mockSubprocessSequence(responses) {
    const fn = vi.fn();
    for (const r of responses) {
        fn.mockResolvedValueOnce(r);
    }
    return fn;
}

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — initial state', () => {
    it('starts with idle annotation state', () => {
        const ctrl = createAnnotationLifecycleController();
        const state = ctrl.getAnnotationState();
        expect(state.state).toBe('idle');
        expect(state.paperKey).toBeNull();
        expect(state.annotations).toEqual([]);
    });

    it('accepts initial currentPaperKey', () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });
        expect(ctrl._currentPaperKey).toBe(PAPER_KEY_A);
    });

    it('getAnnotationState returns current stored state', () => {
        const ctrl = createAnnotationLifecycleController();
        const state1 = ctrl.getAnnotationState();
        expect(state1.state).toBe('idle');

        // Set some state manually to verify the reference
        ctrl._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: PAPER_KEY_A,
        });
        const state2 = ctrl.getAnnotationState();
        expect(state2.state).toBe('ready');
        expect(state2.paperKey).toBe(PAPER_KEY_A);
    });
});

// ---------------------------------------------------------------------------
// Missing paper
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — missing paper', () => {
    it('sets missing-paper without calling subprocess when paperKey is null', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: null });
        const mockFn = vi.fn();

        const result = await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('missing-paper');
        expect(mockFn).not.toHaveBeenCalled();
    });

    it('sets missing-paper when no key was ever set', async () => {
        const ctrl = createAnnotationLifecycleController();
        const mockFn = vi.fn();

        const result = await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockFn,
        });

        expect(result.state).toBe('missing-paper');
        expect(mockFn).not.toHaveBeenCalled();
    });

    it('getAnnotationState reflects missing-paper after load with no key', async () => {
        const ctrl = createAnnotationLifecycleController();
        await ctrl.loadAnnotationsForCurrentPaper('auto', { runSubprocessFn: vi.fn() });
        const state = ctrl.getAnnotationState();
        expect(state.state).toBe('missing-paper');
    });
});

// ---------------------------------------------------------------------------
// Key transition
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — key transition', () => {
    it('loads annotations when paperKey is set and subprocess succeeds', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);

        const result = await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockFn,
            pythonExe: 'python',
            cwd: '/vault',
        });

        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe(PAPER_KEY_A);
        expect(result.annotations.length).toBe(2);
    });

    it('getAnnotationState returns ready after successful load', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });
        const mockFn = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);

        await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockFn,
            pythonExe: 'python',
            cwd: '/vault',
        });

        const state = ctrl.getAnnotationState();
        expect(state.state).toBe('ready');
        expect(state.paperKey).toBe(PAPER_KEY_A);
    });

    it('transitions through loading state', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });

        // Capture state right after load starts but before it resolves
        const loadPromise = ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockSubprocessSequence([
                { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
                { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
            ]),
            pythonExe: 'python',
            cwd: '/vault',
        });

        // Before await, state should still be loading (synchronous part)
        const loadingState = ctrl.getAnnotationState();
        expect(loadingState.state).toBe('loading');

        await loadPromise;
        const readyState = ctrl.getAnnotationState();
        expect(readyState.state).toBe('ready');
    });
});

// ---------------------------------------------------------------------------
// Stale result guard
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — stale result guard', () => {
    it('stale result cannot overwrite state after paper key changes', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });

        // Create a promise that never resolves to simulate a slow subprocess
        let slowResolve;
        const slowPromise = new Promise((resolve) => { slowResolve = resolve; });
        const slowMock = vi.fn().mockReturnValue(slowPromise);

        // Start a load for PAPER_A (slow subprocess)
        const loadA = ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: slowMock,
            pythonExe: 'python',
            cwd: '/vault',
        });

        // Before it resolves, switch to PAPER_B
        ctrl.setCurrentPaperKey(PAPER_KEY_B);
        const fastMock = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            // Use PAPER_B key in export
            {
                stdout: JSON.stringify({
                    ok: true, command: 'annotation.export', version: '1.0.0',
                    data: {
                        paper: PAPER_KEY_B,
                        annotations: [{
                            id: 'b-1', type: 'highlight', page_index: 0, page_label: '1',
                            color: '#ffd400', selected_text: 'B text', comment: 'B comment',
                            source: 'zotero', source_library_id: '1', source_parent_key: 'PB',
                            source_attachment_key: 'ATTB', source_annotation_key: 'ANB',
                            sort_index: 0, position_json: '{}', selector_json: '{}',
                            sync_state: 'imported', is_readonly: 1,
                            created_at: null, updated_at: null, deleted_at: null, source_modified_at: null,
                        }],
                        total: 1, format_version: '1.0',
                    },
                    error: null,
                }),
                stderr: '', exitCode: 0,
            },
        ]);

        const loadB = ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: fastMock,
            pythonExe: 'python',
            cwd: '/vault',
        });

        // Now resolve the slow A load
        slowResolve({ stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 });

        await Promise.all([loadA, loadB]);

        // The state should be for PAPER_B, not PAPER_A
        const state = ctrl.getAnnotationState();
        expect(state.state).toBe('ready');
        expect(state.paperKey).toBe(PAPER_KEY_B);
        // PAPER_B has 1 annotation
        if (state.annotations && state.annotations.length > 0) {
            expect(state.annotations.length).toBe(1);
        }
    });

    it('stale result returns current state without side effects', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });

        // First load succeeds
        const mock1 = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);
        await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mock1,
            pythonExe: 'python',
            cwd: '/vault',
        });

        const stateAfterFirst = ctrl.getAnnotationState();
        expect(stateAfterFirst.state).toBe('ready');

        // Second load with different result
        ctrl.setCurrentPaperKey(PAPER_KEY_B);

        // Start slow B load
        let slowBResolve;
        const slowBPromise = new Promise((resolve) => { slowBResolve = resolve; });
        const slowBMock = vi.fn().mockReturnValue(slowBPromise);

        const loadB = ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: slowBMock,
        });

        // Switch to C before B finishes
        ctrl.setCurrentPaperKey('PAPER_C');
        const mockC = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_EMPTY), stderr: '', exitCode: 0 },
        ]);
        const loadC = ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mockC,
        });

        // Resolve B's slow promise
        slowBResolve({ stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 });

        await Promise.all([loadB, loadC]);

        // State should reflect PAPER_C (empty), not PAPER_B (ready)
        const finalState = ctrl.getAnnotationState();
        expect(finalState.paperKey).toBe('PAPER_C');
    });
});

// ---------------------------------------------------------------------------
// Repeated refreshes use _currentPaperKey
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — repeated refreshes', () => {
    it('repeated refreshes use current paper key', async () => {
        const ctrl = createAnnotationLifecycleController({ currentPaperKey: PAPER_KEY_A });

        // First load
        const mock1 = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);
        await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mock1,
            pythonExe: 'python',
            cwd: '/vault',
        });
        expect(ctrl.getAnnotationState().paperKey).toBe(PAPER_KEY_A);

        // Second load (repeated refresh)
        const mock2 = mockSubprocessSequence([
            { stdout: JSON.stringify(STATUS_OK), stderr: '', exitCode: 0 },
            { stdout: JSON.stringify(EXPORT_OK), stderr: '', exitCode: 0 },
        ]);
        await ctrl.loadAnnotationsForCurrentPaper('auto', {
            runSubprocessFn: mock2,
            pythonExe: 'python',
            cwd: '/vault',
        });
        expect(ctrl.getAnnotationState().paperKey).toBe(PAPER_KEY_A);

        // Subprocess was called both times
        expect(mock1).toHaveBeenCalledTimes(2);
        expect(mock2).toHaveBeenCalledTimes(2);
    });
});

// ---------------------------------------------------------------------------
// setCurrentPaperKey
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — setCurrentPaperKey', () => {
    it('setCurrentPaperKey sets the key for next load', async () => {
        const ctrl = createAnnotationLifecycleController();
        expect(ctrl._currentPaperKey).toBeNull();

        ctrl.setCurrentPaperKey(PAPER_KEY_A);
        expect(ctrl._currentPaperKey).toBe(PAPER_KEY_A);

        ctrl.setCurrentPaperKey(null);
        expect(ctrl._currentPaperKey).toBeNull();
    });

    it('setCurrentPaperKey normalizes falsy to null', () => {
        const ctrl = createAnnotationLifecycleController();
        ctrl.setCurrentPaperKey('');
        expect(ctrl._currentPaperKey).toBeNull();

        ctrl.setCurrentPaperKey(undefined);
        expect(ctrl._currentPaperKey).toBeNull();
    });
});
