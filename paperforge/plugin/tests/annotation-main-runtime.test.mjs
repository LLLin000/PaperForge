/**
 * Runtime harness for PaperForgeStatusView annotation bridge wiring.
 *
 * These tests exercise the real main.js view methods while stubbing the
 * Obsidian runtime and the annotation loader so no Python subprocess runs.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRequire } from 'node:module';
import Module from 'node:module';

const require = createRequire(import.meta.url);

const {
    ANNOTATION_LOAD_STATES,
    makeAnnotationState,
} = await import('../src/testable.js');

let originalLoad;
let PaperForgeStatusView;

function installObsidianStub() {
    originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (request === 'obsidian') {
            return {
                Plugin: class Plugin {},
                Notice: class Notice {},
                ItemView: class ItemView {
                    constructor(leaf) {
                        this.leaf = leaf;
                        this.app = leaf && leaf.app;
                        this.containerEl = leaf && leaf.containerEl;
                    }
                },
                Modal: class Modal {},
                Setting: class Setting {},
                PluginSettingTab: class PluginSettingTab {},
                addIcon: vi.fn(),
            };
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    const mainPath = require.resolve('../main.js');
    delete require.cache[mainPath];
    const pluginModule = require('../main.js');
    PaperForgeStatusView = pluginModule.__test.PaperForgeStatusView;
}

function uninstallObsidianStub() {
    if (originalLoad) Module._load = originalLoad;
    const mainPath = require.resolve('../main.js');
    delete require.cache[mainPath];
    originalLoad = null;
}

function readyState(paperKey, count) {
    return makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
        paperKey,
        annotations: Array.from({ length: count }, (_, i) => ({ id: `${paperKey}-${i}` })),
        message: `${count} annotation(s) loaded.`,
    });
}

function makeRuntimeView(opts = {}) {
    const view = Object.create(PaperForgeStatusView.prototype);
    view.app = {
        vault: { adapter: { basePath: 'C:/vault' } },
        plugins: { plugins: { paperforge: { settings: {} } } },
        workspace: { getActiveFile: vi.fn(() => ({ path: 'Paper.md' })) },
    };
    view._currentPaperKey = Object.prototype.hasOwnProperty.call(opts, 'paperKey')
        ? opts.paperKey
        : 'PAPER_A';
    view._currentPaperEntry = null;
    view._currentMode = opts.mode ?? 'paper';
    view._currentFilePath = opts.filePath ?? 'Paper.md';
    view._annotationLoadSeq = 0;
    view._annotationState = makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE);
    view._annotationLoader = opts.loader || vi.fn(async ({ paperKey }) => readyState(paperKey, 1));
    return view;
}

beforeEach(() => {
    installObsidianStub();
});

afterEach(() => {
    uninstallObsidianStub();
    vi.restoreAllMocks();
});

describe('PaperForgeStatusView annotation runtime bridge', () => {
    it('loadAnnotationsForCurrentPaper passes the current paper key to the bridge loader', async () => {
        const loader = vi.fn(async ({ paperKey }) => readyState(paperKey, 3));
        const view = makeRuntimeView({ paperKey: 'PAPER_A', loader });

        const result = await view.loadAnnotationsForCurrentPaper('manual');

        expect(loader).toHaveBeenCalledTimes(1);
        expect(loader.mock.calls[0][0]).toMatchObject({
            paperKey: 'PAPER_A',
            cwd: 'C:/vault',
            timeout: 30000,
        });
        expect(result.state).toBe(ANNOTATION_LOAD_STATES.READY);
        expect(result.paperKey).toBe('PAPER_A');
        expect(result.annotations.length).toBe(3);
    });

    it('missing current paper sets missing-paper and does not call the bridge loader', async () => {
        const loader = vi.fn();
        const view = makeRuntimeView({ paperKey: null, loader });

        const result = await view.loadAnnotationsForCurrentPaper('auto');

        expect(result).toBeNull();
        expect(loader).not.toHaveBeenCalled();
        expect(view.getAnnotationState().state).toBe(ANNOTATION_LOAD_STATES.MISSING_PAPER);
        expect(view.getAnnotationState().message).not.toContain('Traceback');
    });

    it('stale async results cannot overwrite state for a newer active paper', async () => {
        let resolveA;
        const pendingA = new Promise((resolve) => { resolveA = resolve; });
        const loader = vi.fn(({ paperKey }) => {
            if (paperKey === 'PAPER_A') return pendingA;
            return Promise.resolve(readyState('PAPER_B', 5));
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', loader });

        const promiseA = view.loadAnnotationsForCurrentPaper('auto');
        view._currentPaperKey = 'PAPER_B';
        const resultB = await view.loadAnnotationsForCurrentPaper('auto');
        resolveA(readyState('PAPER_A', 99));
        await promiseA;

        expect(resultB.paperKey).toBe('PAPER_B');
        expect(view.getAnnotationState().paperKey).toBe('PAPER_B');
        expect(view.getAnnotationState().annotations.length).toBe(5);
    });

    it('getAnnotationState returns the stored runtime annotation state', () => {
        const view = makeRuntimeView();
        const stored = readyState('PAPER_A', 2);
        view._annotationState = stored;

        expect(view.getAnnotationState()).toBe(stored);
    });

    it('_detectAndSwitch reuses the annotation loader after resolving the active paper', () => {
        const view = makeRuntimeView({ paperKey: null });
        view._resolveModeForFile = vi.fn(() => ({ mode: 'paper', filePath: 'Paper.md', key: 'PAPER_DETECTED' }));
        view._findEntry = vi.fn(() => ({ zotero_key: 'PAPER_DETECTED' }));
        view._switchMode = vi.fn();
        view.loadAnnotationsForCurrentPaper = vi.fn();

        view._detectAndSwitch();

        expect(view._currentPaperKey).toBe('PAPER_DETECTED');
        expect(view._switchMode).toHaveBeenCalledWith('paper', 'Paper.md');
        expect(view.loadAnnotationsForCurrentPaper).toHaveBeenCalledWith('auto');
    });

    it('_refreshCurrentMode refreshes stored annotation state without changing paper identity', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', mode: 'paper' });
        view._contentEl = { empty: vi.fn(), addClass: vi.fn(), removeClass: vi.fn() };
        view._invalidateIndex = vi.fn();
        view._findEntry = vi.fn(() => ({ zotero_key: 'PAPER_A' }));
        view._renderModeHeader = vi.fn();
        view._renderPaperMode = vi.fn();
        view.loadAnnotationsForCurrentPaper = vi.fn();

        view._refreshCurrentMode();

        expect(view._currentPaperKey).toBe('PAPER_A');
        expect(view._renderPaperMode).toHaveBeenCalled();
        expect(view.loadAnnotationsForCurrentPaper).toHaveBeenCalledWith('auto');
    });
});
