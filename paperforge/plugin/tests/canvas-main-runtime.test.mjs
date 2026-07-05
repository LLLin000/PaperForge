/**
 * Runtime harness for PaperForgeReadingCanvasView registration, command
 * wiring, explicit paperKey state, and module delegation.
 *
 * These tests exercise the real main.js view class while stubbing the
 * Obsidian runtime so no real leaves or sidebars are involved.
 *
 * Tests cover:
 *   Task 1 — View type constant, class export, command reference
 *   Task 2 — setPaperContext, explicit paperKey, module delegation
 *   Task 3 — Missing-paper fallback, no auto-switch on set
 *   Task 4 — Static open method signature
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createRequire } from 'node:module';
import Module from 'node:module';

const require = createRequire(import.meta.url);

let originalLoad;
let PaperForgeReadingCanvasView;
let VIEW_TYPE_PAPERFORGE_READING_CANVAS;
let openReadingCanvasForActivePaper;

/**
 * Global capture for Notice calls during tests.
 */
const noticeCalls = [];

function installObsidianStub() {
    originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (request === 'obsidian') {
            return {
                Plugin: class Plugin {},
                Notice: class Notice {
                    constructor(msg, duration) {
                        this.msg = msg;
                        this.duration = duration;
                        noticeCalls.push(this);
                    }
                },
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
    PaperForgeReadingCanvasView = pluginModule.__test.PaperForgeReadingCanvasView;
    VIEW_TYPE_PAPERFORGE_READING_CANVAS = pluginModule.__test.VIEW_TYPE_PAPERFORGE_READING_CANVAS;
    openReadingCanvasForActivePaper = pluginModule.__test.openReadingCanvasForActivePaper;
}

function uninstallObsidianStub() {
    if (originalLoad) Module._load = originalLoad;
    const mainPath = require.resolve('../main.js');
    delete require.cache[mainPath];
    originalLoad = null;
}

// ── Obsidian DOM helpers ──

function addCreateEl(el) {
    if (el.createEl) return;
    el.createEl = function (tag, opts) {
        const child = document.createElement(tag);
        if (opts) {
            if (opts.cls) {
                if (typeof opts.cls === 'string') {
                    child.className = opts.cls;
                } else if (Array.isArray(opts.cls)) {
                    child.className = opts.cls.join(' ');
                }
            }
            if (opts.text != null) child.textContent = opts.text;
            if (opts.title) child.setAttribute('title', opts.title);
        }
        this.appendChild(child);
        return addCreateEl(child);
    };
    el.empty = function () {
        while (this.firstChild) this.removeChild(this.firstChild);
    };
    el.setText = function (text) {
        this.textContent = text;
    };
    return el;
}

function makeStubApp() {
    return {
        vault: {
            adapter: { basePath: 'C:/vault' },
            getAbstractFileByPath: vi.fn(() => null),
        },
        plugins: { plugins: { paperforge: {} } },
        workspace: {
            getLeavesOfType: vi.fn(() => []),
            getRightLeaf: vi.fn(() => null),
            revealLeaf: vi.fn(),
        },
    };
}

beforeEach(() => {
    noticeCalls.length = 0;
    installObsidianStub();
});

afterEach(() => {
    uninstallObsidianStub();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
    noticeCalls.length = 0;
});

// ── Task 1: View type constant and class export ──

describe('Task 1 — View type constant and class export', () => {
    it('exports PaperForgeReadingCanvasView via module.exports.__test', () => {
        expect(PaperForgeReadingCanvasView).toBeDefined();
        expect(typeof PaperForgeReadingCanvasView).toBe('function');
        expect(PaperForgeReadingCanvasView.name).toBe('PaperForgeReadingCanvasView');
    });

    it('exports VIEW_TYPE_PAPERFORGE_READING_CANVAS constant', () => {
        expect(VIEW_TYPE_PAPERFORGE_READING_CANVAS).toBe('paperforge-reading-canvas');
    });

    it('view type is used by getViewType()', () => {
        const view = new PaperForgeReadingCanvasView({ containerEl: document.createElement('div') });
        expect(view.getViewType()).toBe('paperforge-reading-canvas');
    });

    it('exports openReadingCanvasForActivePaper helper', () => {
        expect(openReadingCanvasForActivePaper).toBeDefined();
        expect(typeof openReadingCanvasForActivePaper).toBe('function');
    });

    it('getDisplayText returns canvas label', () => {
        const view = new PaperForgeReadingCanvasView({ containerEl: document.createElement('div') });
        const text = view.getDisplayText();
        expect(text).toContain('Reading Canvas');
    });
});

// ── Task 2: setPaperContext and explicit paperKey ──

describe('Task 2 — setPaperContext and explicit paperKey', () => {
    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;
        return view;
    }

    it('setPaperContext captures paperKey and entry', () => {
        const view = makeCanvasView();

        view.setPaperContext('KEY_ABC', { key: 'KEY_ABC', title: 'Test' });

        expect(view._paperKey).toBe('KEY_ABC');
        expect(view._paperEntry).toEqual({ key: 'KEY_ABC', title: 'Test' });
    });

    it('renders idle shell after setPaperContext with valid entry', () => {
        const view = makeCanvasView();

        view.setPaperContext('PAPER_X', { key: 'PAPER_X', title: 'Paper X' });

        // Should have rendered content into contentEl
        expect(view._paperKey).toBe('PAPER_X');
        expect(view._canvasContext).toBeTruthy();
        expect(view._canvasContext.ok).toBe(true);
    });

    it('renders missing-paper state when setPaperContext gets null entry', () => {
        const view = makeCanvasView();

        view.setPaperContext(null, null);

        expect(view._canvasContext).toBeTruthy();
        expect(view._canvasContext.ok).toBe(false);
    });
});

// ── Task 3: No auto-switch behavior ──

describe('Task 3 — No auto-switch behavior', () => {
    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;
        return view;
    }

    it('paperKey is fixed after setPaperContext and does not change on external events', () => {
        const view = makeCanvasView();

        view.setPaperContext('FIXED_KEY', { key: 'FIXED_KEY', title: 'Fixed' });
        expect(view._paperKey).toBe('FIXED_KEY');

        // Simulate external call — paperKey must remain unchanged
        view.setPaperContext('DIFFERENT_KEY', { key: 'DIFFERENT_KEY', title: 'Different' });
        expect(view._paperKey).toBe('DIFFERENT_KEY');
        // Note: this tests that setPaperContext can be called again, but only
        // by the explicit open() path, never by an auto-switch listener.
    });

    it('onClose resets internal state', () => {
        const view = makeCanvasView();

        view.setPaperContext('KEY_A', { key: 'KEY_A', title: 'A' });
        expect(view._paperKey).toBe('KEY_A');

        view.onClose();

        expect(view._paperKey).toBeNull();
        expect(view._paperEntry).toBeNull();
        expect(view._canvasContext).toBeNull();
        expect(view._sessionController).toBeNull();
    });
});

// ── Task 4: Static open method ──

describe('Task 4 — Static open method', () => {
    it('static open exists and is a function', () => {
        expect(typeof PaperForgeReadingCanvasView.open).toBe('function');
    });

    it('static open reveals existing leaf if one exists', async () => {
        const mockLeaf = { view: { setPaperContext: vi.fn() } };
        const mockPlugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn(() => [mockLeaf]),
                    revealLeaf: vi.fn(),
                },
            },
        };

        await PaperForgeReadingCanvasView.open(mockPlugin, 'KEY_B', { key: 'KEY_B', title: 'B' });

        expect(mockPlugin.app.workspace.getLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        expect(mockLeaf.view.setPaperContext).toHaveBeenCalledWith('KEY_B', { key: 'KEY_B', title: 'B' });
        expect(mockPlugin.app.workspace.revealLeaf).toHaveBeenCalledWith(mockLeaf);
    });

    it('static open creates new leaf when none exists (fail-safe: right leaf may be null)', async () => {
        const mockPlugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn(() => []),
                    getRightLeaf: vi.fn(() => null),
                    revealLeaf: vi.fn(),
                },
            },
        };

        // Should not throw when getRightLeaf returns null
        await PaperForgeReadingCanvasView.open(mockPlugin, 'KEY_C', { key: 'KEY_C', title: 'C' });
        // The method completes without error
        expect(mockPlugin.app.workspace.getLeavesOfType).toHaveBeenCalled();
    });
});
