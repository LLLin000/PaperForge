/**
 * Vitest tests for the canvas session lifecycle controller.
 *
 * Tests cover:
 *   - Fixed paperKey (never reads global _currentPaperKey)
 *   - Stale-result discard via monotonic load sequence
 *   - Refresh coordination (multiple loadAnnotations calls)
 *   - Teardown disposes controller and prevents further loads
 *   - State tracking (getState, getPaperKey)
 *
 * @module tests/canvas-controller
 */

import { describe, it, expect, vi } from 'vitest';

const { createCanvasSessionController } = await import('../src/canvas/controller.js');
const { createCanvasAnnotationLoader } = await import('../src/canvas/annotations.js');

// ── Helpers ──

/**
 * Create a mock v0.2 loader function (loadAnnotationsForPaper-compatible).
 * This is the function injected into createCanvasAnnotationLoader, which
 * wraps it so the controller can call loadForPaper(paperKey, loadOptions).
 */
function makeV02Loader() {
    return vi.fn(async ({ paperKey }) => ({
        state: 'ready',
        paperKey,
        annotations: [],
        message: `Loaded ${paperKey}`,
        errorCode: null,
        raw: null,
    }));
}

/** Shorthand: create annotation loader wrapping a v0.2 mock. */
function makeMockLoader(v02Mock) {
    return createCanvasAnnotationLoader({ loadAnnotationsForPaper: v02Mock });
}

function makeFailV02Loader() {
    return vi.fn(async ({ paperKey }) => ({
        state: 'cli-error',
        paperKey,
        annotations: [],
        message: 'Failed to load.',
        errorCode: 'INTERNAL_ERROR',
        raw: null,
    }));
}

function makeSlowV02Loader(delayMs) {
    return vi.fn(async ({ paperKey }) => {
        await new Promise(r => setTimeout(r, delayMs));
        return {
            state: 'ready',
            paperKey,
            annotations: [{ id: 'ann-1' }],
            message: `Loaded ${paperKey}`,
            errorCode: null,
            raw: null,
        };
    });
}

// ── Fixed paperKey ──

describe('fixed paperKey', () => {
    it('stores and returns the paperKey provided at construction', () => {
        const loader = makeMockLoader(makeV02Loader());
        const controller = createCanvasSessionController({ paperKey: 'MY_PAPER', annotationLoader: loader });

        expect(controller.getPaperKey()).toBe('MY_PAPER');
    });

    it('returns null paperKey when none provided at construction', () => {
        const loader = makeMockLoader(makeV02Loader());
        const controller = createCanvasSessionController({ annotationLoader: loader });

        expect(controller.getPaperKey()).toBeNull();
    });

    it('returns the fixed paperKey even after loadAnnotations', () => {
        const loader = makeMockLoader(makeV02Loader());
        const controller = createCanvasSessionController({ paperKey: 'FIXED_KEY', annotationLoader: loader });

        controller.loadAnnotations();

        expect(controller.getPaperKey()).toBe('FIXED_KEY');
    });

    it('returns the fixed paperKey even after teardown', () => {
        const loader = makeMockLoader(makeV02Loader());
        const controller = createCanvasSessionController({ paperKey: 'SURVIVE_TEARDOWN', annotationLoader: loader });

        controller.teardown();

        // getPaperKey should still return the original fixed key per design
        // (the paperKey is captured at construction and never cleared)
        expect(controller.getPaperKey()).toBe('SURVIVE_TEARDOWN');
    });

    it('stringifies numeric paperKey', () => {
        const controller = createCanvasSessionController({ paperKey: 42, annotationLoader: makeMockLoader(makeV02Loader()) });
        expect(controller.getPaperKey()).toBe('42');
    });
});

// ── State tracking ──

describe('state tracking', () => {
    it('getState returns null before any load', () => {
        const controller = createCanvasSessionController({
            paperKey: 'PAPER_A',
            annotationLoader: makeMockLoader(makeV02Loader()),
        });

        expect(controller.getState()).toBeNull();
    });

    it('getState returns the annotation state after load', async () => {
        const v02loader = makeV02Loader();
        const loader = makeMockLoader(v02loader);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        await controller.loadAnnotations();

        const state = controller.getState();
        expect(state).toBeTruthy();
        expect(state.state).toBe('ready');
        expect(state.paperKey).toBe('PAPER_A');
    });

    it('getState returns the latest loaded state after multiple loads', async () => {
        let callCount = 0;
        const v02Fn = vi.fn(async ({ paperKey }) => {
            callCount++;
            return {
                state: callCount === 1 ? 'empty' : 'ready',
                paperKey,
                annotations: callCount === 2 ? [{ id: 'ann-1' }] : [],
                message: `Load ${callCount}`,
                errorCode: null,
                raw: null,
            };
        });
        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: v02Fn });
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        await controller.loadAnnotations();
        expect(controller.getState().state).toBe('empty');
        expect(controller.getState().message).toContain('Load 1');

        await controller.loadAnnotations();
        expect(controller.getState().state).toBe('ready');
        expect(controller.getState().message).toContain('Load 2');
    });
});

// ── Stale-result discard ──

describe('stale-result discard', () => {
    it('discards stale result when load is superseded by another load', async () => {
        const slowV02 = makeSlowV02Loader(50);
        const loader = makeMockLoader(slowV02);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        // Start first load
        const firstPromise = controller.loadAnnotations();

        // Start second load before first completes
        const secondPromise = controller.loadAnnotations();

        // First result should be discarded (null)
        const firstResult = await firstPromise;
        expect(firstResult).toBeNull();

        // Second result should succeed
        const secondResult = await secondPromise;
        expect(secondResult).not.toBeNull();
        expect(secondResult.state).toBe('ready');
    });

    it('discards stale result when controller is disposed during load', async () => {
        const slowV02 = makeSlowV02Loader(100);
        const loader = makeMockLoader(slowV02);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        const loadPromise = controller.loadAnnotations();

        // Teardown before the slow load completes
        controller.teardown();

        const result = await loadPromise;
        expect(result).toBeNull();
    });

    it('preserves the first load result when no superseding load occurs', async () => {
        const v02loader = makeV02Loader();
        const loader = makeMockLoader(v02loader);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        const result = await controller.loadAnnotations();
        expect(result).not.toBeNull();
        expect(result.state).toBe('ready');
        expect(result.paperKey).toBe('PAPER_A');
    });

    it('stale guard uses monotonic sequence — third load discards second', async () => {
        // Use a v0.2 loader that returns controlled promises
        let resolve1, resolve2, resolve3;
        const p1 = new Promise(r => { resolve1 = r; });
        const p2 = new Promise(r => { resolve2 = r; });
        const p3 = new Promise(r => { resolve3 = r; });

        const v02Fn = vi.fn();
        v02Fn.mockReturnValueOnce(p1);
        v02Fn.mockReturnValueOnce(p2);
        v02Fn.mockReturnValueOnce(p3);

        const loader = createCanvasAnnotationLoader({ loadAnnotationsForPaper: v02Fn });
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        const r1 = controller.loadAnnotations();
        const r2 = controller.loadAnnotations();
        const r3 = controller.loadAnnotations();

        // Resolve in order: second, third, first
        resolve2({ state: 'empty', paperKey: 'PAPER_A', annotations: [], message: 'Second', errorCode: null, raw: null });
        resolve3({ state: 'ready', paperKey: 'PAPER_A', annotations: [{ id: 'x' }], message: 'Third', errorCode: null, raw: null });
        resolve1({ state: 'empty', paperKey: 'PAPER_A', annotations: [], message: 'First', errorCode: null, raw: null });

        const a1 = await r1;
        const a2 = await r2;
        const a3 = await r3;

        // First and second are stale (superseded by third)
        expect(a1).toBeNull();
        expect(a2).toBeNull();
        // Third is the current sequence
        expect(a3).not.toBeNull();
        expect(a3.state).toBe('ready');
        expect(a3.message).toBe('Third');

        // State should be the third load
        expect(controller.getState().message).toBe('Third');
    });
});

// ── Refresh coordination ──

describe('refresh coordination', () => {
    it('loadAnnotations can be called multiple times (refresh)', async () => {
        const v02loader = makeV02Loader();
        const loader = makeMockLoader(v02loader);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        await controller.loadAnnotations();
        expect(v02loader).toHaveBeenCalledTimes(1);

        await controller.loadAnnotations();
        expect(v02loader).toHaveBeenCalledTimes(2);
    });

    it('each refresh forwards the same fixed paperKey to the loader', async () => {
        const v02loader = makeV02Loader();
        const loader = makeMockLoader(v02loader);
        const controller = createCanvasSessionController({ paperKey: 'REFRESH_KEY', annotationLoader: loader });

        await controller.loadAnnotations();
        await controller.loadAnnotations();
        await controller.loadAnnotations();

        for (const call of v02loader.mock.calls) {
            expect(call[0].paperKey).toBe('REFRESH_KEY');
        }
    });

    it('refresh with error state still updates getState', async () => {
        const failV02 = makeFailV02Loader();
        const loader = makeMockLoader(failV02);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        await controller.loadAnnotations();
        const state = controller.getState();
        expect(state.state).toBe('cli-error');
        expect(state.errorCode).toBe('INTERNAL_ERROR');
    });

    it('refresh forwards loadOptions to the annotation loader', async () => {
        const v02loader = makeV02Loader();
        const loader = makeMockLoader(v02loader);
        const controller = createCanvasSessionController({ paperKey: 'PAPER_A', annotationLoader: loader });

        await controller.loadAnnotations({ pythonExe: '/custom/python', cwd: '/vault', timeout: 60000 });

        const callOpts = v02loader.mock.calls[0][0];
        expect(callOpts).toBeTruthy();
        expect(callOpts.paperKey).toBe('PAPER_A');
        expect(callOpts.pythonExe).toBe('/custom/python');
        expect(callOpts.cwd).toBe('/vault');
        expect(callOpts.timeout).toBe(60000);
    });
});

// ── Teardown ──

describe('teardown', () => {
    it('loadAnnotations returns null after teardown', async () => {
        const controller = createCanvasSessionController({
            paperKey: 'PAPER_A',
            annotationLoader: makeMockLoader(makeV02Loader()),
        });

        controller.teardown();
        const result = await controller.loadAnnotations();
        expect(result).toBeNull();
    });

    it('teardown clears state (getState returns null)', () => {
        const controller = createCanvasSessionController({
            paperKey: 'PAPER_A',
            annotationLoader: makeMockLoader(makeV02Loader()),
        });

        controller.teardown();
        expect(controller.getState()).toBeNull();
    });

    it('teardown is safe to call multiple times', () => {
        const controller = createCanvasSessionController({
            paperKey: 'PAPER_A',
            annotationLoader: makeMockLoader(makeV02Loader()),
        });

        expect(() => {
            controller.teardown();
            controller.teardown();
            controller.teardown();
        }).not.toThrow();
    });

    it('loadAnnotations returns null when no paperKey and no teardown', async () => {
        const controller = createCanvasSessionController({
            annotationLoader: makeMockLoader(makeV02Loader()),
        });

        const result = await controller.loadAnnotations();
        expect(result).toBeNull();
    });
});
