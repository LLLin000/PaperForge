/**
 * Vitest tests for createAnnotationLifecycleController — active-paper
 * annotation refresh lifecycle: missing-paper skipping, key transition
 * loading, stale-result guard, state exposure, and repeated refreshes.
 */
import { describe, it, expect, vi } from 'vitest';

const {
    createAnnotationLifecycleController,
    ANNOTATION_LOAD_STATES,
    makeAnnotationState,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const KEY_A = 'PAPER_A';
const KEY_B = 'PAPER_B';

function makeReadyState(key, count) {
    return makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
        paperKey: key,
        annotations: Array.from({ length: count }, (_, i) => ({
            id: `${key}-annot-${i}`,
        })),
        message: `${count} annotation(s) loaded.`,
    });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('createAnnotationLifecycleController — initial state', () => {
    it('starts with idle state', () => {
        const ctrl = createAnnotationLifecycleController();
        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.IDLE);
        expect(state.paperKey).toBeNull();
        expect(state.annotations).toEqual([]);
    });

    it('starts with null currentPaperKey', () => {
        const ctrl = createAnnotationLifecycleController();
        expect(ctrl.getCurrentPaperKey()).toBeNull();
    });

    it('accepts getAnnotationState without throwing', () => {
        const ctrl = createAnnotationLifecycleController();
        expect(() => ctrl.getAnnotationState()).not.toThrow();
    });
});

describe('createAnnotationLifecycleController — missing paper', () => {
    it('setCurrentPaperKey(null) sets missing-paper without calling loader', async () => {
        const loader = vi.fn();
        const ctrl = createAnnotationLifecycleController({ loader });

        const result = ctrl.setCurrentPaperKey(null);
        expect(result).toBeNull();

        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.MISSING_PAPER);
        expect(state.paperKey).toBeNull();
        expect(loader).not.toHaveBeenCalled();
    });

    it('setCurrentPaperKey("") sets missing-paper without calling loader', async () => {
        const loader = vi.fn();
        const ctrl = createAnnotationLifecycleController({ loader });

        const result = ctrl.setCurrentPaperKey('');
        expect(result).toBeNull();

        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.MISSING_PAPER);
        expect(loader).not.toHaveBeenCalled();
    });

    it('loadAnnotationsForCurrentPaper when key is null returns null and sets missing-paper', async () => {
        const loader = vi.fn();
        const ctrl = createAnnotationLifecycleController({ loader });

        const result = ctrl.loadAnnotationsForCurrentPaper('auto');
        expect(result).toBeNull();

        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.MISSING_PAPER);
        expect(loader).not.toHaveBeenCalled();
    });

    it('missing-paper has friendly user message', () => {
        const ctrl = createAnnotationLifecycleController();
        ctrl.setCurrentPaperKey(null);

        const state = ctrl.getAnnotationState();
        expect(state.message).toBeTruthy();
        expect(state.message).not.toContain('Traceback');
    });
});

describe('createAnnotationLifecycleController — key transition loads', () => {
    it('setCurrentPaperKey(key) transitions to loading then ready via loader', async () => {
        const loader = vi.fn().mockResolvedValue(makeReadyState(KEY_A, 2));
        const ctrl = createAnnotationLifecycleController({ loader });

        const promise = ctrl.setCurrentPaperKey(KEY_A);
        expect(promise).not.toBeNull();

        // During load, state should be loading
        let state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.LOADING);

        // Wait for load to complete
        const result = await promise;
        expect(result.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(result.paperKey).toBe(KEY_A);
        expect(result.annotations.length).toBe(2);

        // After load, stored state matches
        state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(state.paperKey).toBe(KEY_A);
    });

    it('loadAnnotationsForCurrentPaper calls loader with current key', async () => {
        const loader = vi.fn().mockResolvedValue(makeReadyState(KEY_A, 1));
        const ctrl = createAnnotationLifecycleController({ loader });

        // Set key first
        ctrl.setCurrentPaperKey(KEY_A);

        // Reset mock to track loadAnnotationsForCurrentPaper call
        loader.mockResolvedValue(makeReadyState(KEY_A, 3));
        const promise = ctrl.loadAnnotationsForCurrentPaper('manual');
        expect(promise).not.toBeNull();

        const result = await promise;
        expect(loader).toHaveBeenCalledWith(KEY_A, 'manual');
        expect(result.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(result.annotations.length).toBe(3);
    });

    it('repeated refreshes use current paper key', async () => {
        const loader = vi.fn().mockResolvedValue(makeReadyState(KEY_A, 1));
        const ctrl = createAnnotationLifecycleController({ loader });

        ctrl.setCurrentPaperKey(KEY_A);
        await ctrl.loadAnnotationsForCurrentPaper('auto');

        const state = ctrl.getAnnotationState();
        expect(state.paperKey).toBe(KEY_A);
        expect(loader).toHaveBeenCalledTimes(2); // setCurrentPaperKey + loadAnnotationsForCurrentPaper
    });
});

describe('createAnnotationLifecycleController — stale-result guard', () => {
    it('stale async result cannot overwrite newer paper state', async () => {
        // Simulate a slow load for KEY_A, then a quick switch to KEY_B
        let resolveA;
        const promiseA = new Promise((resolve) => { resolveA = resolve; });

        const loader = vi.fn();
        loader.mockImplementation((key) => {
            if (key === KEY_A) return promiseA;
            if (key === KEY_B) return Promise.resolve(makeReadyState(KEY_B, 5));
            return Promise.resolve(makeReadyState(key, 0));
        });

        const ctrl = createAnnotationLifecycleController({ loader });

        // Start load for KEY_A
        const promiseResultA = ctrl.setCurrentPaperKey(KEY_A);
        expect(promiseResultA).not.toBeNull();

        // Switch to KEY_B before KEY_A finishes
        const promiseResultB = ctrl.setCurrentPaperKey(KEY_B);
        expect(promiseResultB).not.toBeNull();

        // KEY_B finishes immediately
        const resultB = await promiseResultB;
        expect(resultB.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(resultB.paperKey).toBe(KEY_B);

        // Now KEY_A's stale result resolves
        resolveA(makeReadyState(KEY_A, 99));

        // Wait for KEY_A's promise to resolve
        const resultA = await promiseResultA;

        // Stale result must NOT overwrite KEY_B's state
        const finalState = ctrl.getAnnotationState();
        expect(finalState.paperKey).toBe(KEY_B);
        expect(finalState.annotations.length).toBe(5);
    });

    it('stale async result from older key is safely ignored', async () => {
        let resolveA;
        const promiseA = new Promise((resolve) => { resolveA = resolve; });

        const loader = vi.fn();
        loader.mockImplementation((key) => {
            if (key === KEY_A) return promiseA;
            if (key === KEY_B) return Promise.resolve(makeReadyState(KEY_B, 3));
            return Promise.resolve(makeReadyState(key, 0));
        });

        const ctrl = createAnnotationLifecycleController({ loader });

        // Start load for KEY_A
        const promiseA_Result = ctrl.setCurrentPaperKey(KEY_A);
        expect(promiseA_Result).not.toBeNull();

        // Switch to KEY_B
        const promiseB = ctrl.setCurrentPaperKey(KEY_B);
        expect(promiseB).not.toBeNull();

        // KEY_B resolves
        await promiseB;

        // KEY_A resolves stale
        resolveA(makeReadyState(KEY_A, 99));
        const staleResult = await promiseA_Result;

        // Stale result is discarded — returns current state, not stale result
        const currentState = ctrl.getAnnotationState();
        expect(currentState.paperKey).toBe(KEY_B);
        expect(currentState.annotations.length).toBe(3);
    });
});

describe('createAnnotationLifecycleController — getAnnotationState', () => {
    it('returns the currently stored state after successful load', async () => {
        const loader = vi.fn().mockResolvedValue(makeReadyState(KEY_A, 4));
        const ctrl = createAnnotationLifecycleController({ loader });

        await ctrl.setCurrentPaperKey(KEY_A);
        const state = ctrl.getAnnotationState();

        expect(state.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(state.paperKey).toBe(KEY_A);
        expect(state.annotations.length).toBe(4);
    });

    it('returns missing-paper state after setting null key following a load', async () => {
        const loader = vi.fn().mockResolvedValue(makeReadyState(KEY_A, 2));
        const ctrl = createAnnotationLifecycleController({ loader });

        // Load for KEY_A
        await ctrl.setCurrentPaperKey(KEY_A);
        expect(ctrl.getAnnotationState().state).toBe(ANNOTATION_LOAD_STATES.READY);

        // Switch to null (missing paper)
        ctrl.setCurrentPaperKey(null);
        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.MISSING_PAPER);
        expect(state.paperKey).toBeNull();
    });

    it('returns loading state during pending load', () => {
        const neverResolve = new Promise(() => {}); // never resolves
        const loader = vi.fn().mockReturnValue(neverResolve);
        const ctrl = createAnnotationLifecycleController({ loader });

        ctrl.setCurrentPaperKey(KEY_A);

        const state = ctrl.getAnnotationState();
        expect(state.state).toBe(ANNOTATION_LOAD_STATES.LOADING);
    });
});
