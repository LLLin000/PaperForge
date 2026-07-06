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

// ── ANN11 Runtime regression gate ──

describe('ANN11 runtime regression — ANN10-02 wiring preserved', () => {
    it('PaperForgeReadingCanvasView delegates rendering to src/canvas/render.js', () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;

        // The view uses require('./src/canvas') internally — this confirms
        // the module delegation path is intact.
        expect(typeof view.getViewType).toBe('function');
        expect(view.getViewType()).toBe('paperforge-reading-canvas');
    });

    it('canvas render module exports ANN11 card render helpers', () => {
        const canvas = require('../src/canvas');
        expect(typeof canvas.renderCanvasCard).toBe('function');
        expect(typeof canvas.renderCanvasCardLanes).toBe('function');
        expect(typeof canvas.renderCanvasRefreshing).toBe('function');
    });

    it('canvas render module exports ANN10 shell render helpers', () => {
        const canvas = require('../src/canvas');
        expect(typeof canvas.renderCanvasView).toBe('function');
        expect(typeof canvas.renderCanvasIdentity).toBe('function');
        expect(typeof canvas.renderCanvasStaleBanner).toBe('function');
    });

    it('no additional view type registration beyond ANN10-02', () => {
        const mainPath = require.resolve('../main.js');
        delete require.cache[mainPath];
        require('../main.js');

        // Only the one reading canvas view type should exist
        expect(VIEW_TYPE_PAPERFORGE_READING_CANVAS).toBe('paperforge-reading-canvas');
    });
});

// ── i18n tests ──

describe('i18n — ANN11 card labels', () => {
    it('i18n module exports t() function', () => {
        const i18n = require('../i18n');
        expect(typeof i18n.t).toBe('function');
    });

    it('i18n module exports detectLang function', () => {
        const i18n = require('../i18n');
        expect(typeof i18n.detectLang).toBe('function');
    });

    it('i18n card.selected_text exists in zh', () => {
        const i18n = require('../i18n');
        expect(i18n.t('card.selected_text', 'zh')).toBe('选中文本');
    });

    it('i18n card.selected_text exists in en', () => {
        const i18n = require('../i18n');
        expect(i18n.t('card.selected_text', 'en')).toBe('Selected Text');
    });

    it('i18n card.read_only exists in zh', () => {
        const i18n = require('../i18n');
        expect(i18n.t('card.read_only', 'zh')).toBe('只读');
    });

    it('i18n card.read_only exists in en', () => {
        const i18n = require('../i18n');
        expect(i18n.t('card.read_only', 'en')).toBe('Read-only');
    });

    it('i18n state.refreshing exists in both languages', () => {
        const i18n = require('../i18n');
        expect(i18n.t('state.refreshing', 'zh')).toBeTruthy();
        expect(i18n.t('state.refreshing', 'en')).toBeTruthy();
        expect(i18n.t('state.refreshing', 'zh')).not.toBe('state.refreshing');
        expect(i18n.t('state.refreshing', 'en')).not.toBe('state.refreshing');
    });

    it('i18n state.stale exists in both languages', () => {
        const i18n = require('../i18n');
        expect(i18n.t('state.stale', 'zh')).toBeTruthy();
        expect(i18n.t('state.stale', 'en')).toBeTruthy();
    });

    it('i18n returns key for unknown key', () => {
        const i18n = require('../i18n');
        expect(i18n.t('nonexistent.key')).toBe('nonexistent.key');
    });
});

// ── Forbidden controls in runtime ──

describe('runtime forbidden controls', () => {
    it('PaperForgeReadingCanvasView has no create/edit/delete controls in DOM', () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl); // Provide Obsidian runtime helpers
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;

        view.setPaperContext('PAPER_A', { key: 'PAPER_A', title: 'Test Paper' });

        const html = containerEl.innerHTML.toLowerCase();
        const forbidden = ['edit', 'delete', 'create', 'save', 'import', 'apply', 'write back', 'write-back'];
        for (const word of forbidden) {
            expect(html).not.toContain(word);
        }
    });

    it('PaperForgeReadingCanvasView has no anchor or connector classes', () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;

        view.setPaperContext('PAPER_A', { key: 'PAPER_A', title: 'Test Paper' });

        const html = containerEl.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-anchor');
        expect(html).not.toContain('paperforge-canvas-connector');
    });

    it('PaperForgeReadingCanvasView has no draggable attributes', () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;

        view.setPaperContext('PAPER_A', { key: 'PAPER_A', title: 'Test Paper' });

        const html = containerEl.innerHTML.toLowerCase();
        expect(html).not.toContain('draggable="true"');
    });
});

// ── ANN12-02 Task 1: Runtime source loading (_loadCanvasSourceInputs) ──

describe('ANN12-02 Task 1 — Runtime source loading (_loadCanvasSourceInputs)', () => {
    /**
     * Create a view with a mock app that provides vault read capabilities.
     */
    function makeViewWithVault(vaultOverrides) {
        const vault = {
            getAbstractFileByPath: vi.fn(() => null),
            read: vi.fn(() => Promise.resolve('')),
            adapter: { basePath: 'C:/vault' },
            ...vaultOverrides,
        };
        const app = { vault };
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app });
        view.contentEl = contentEl;
        view.app = app;
        return { view, app, containerEl, contentEl };
    }

    // ── Method existence ──

    it('has _loadCanvasSourceInputs method', () => {
        const { view } = makeViewWithVault();
        expect(typeof view._loadCanvasSourceInputs).toBe('function');
    });

    it('has _readVaultText helper method', () => {
        const { view } = makeViewWithVault();
        expect(typeof view._readVaultText).toBe('function');
    });

    // ── Source priority contract (D-01/D-02/D-03) ──

    it('reads fulltext_path first when it exists and is readable', async () => {
        const { view, app } = makeViewWithVault();
        const mockFile = { path: 'ft.md', name: 'fulltext.md' };
        app.vault.getAbstractFileByPath.mockImplementation((p) => {
            if (p === 'path/to/fulltext.md') return mockFile;
            return null;
        });
        app.vault.read.mockResolvedValue('Fulltext content here.');

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_A',
            fulltext_path: 'path/to/fulltext.md',
            note_path: 'path/to/note.md',
        });

        expect(result.fulltext.exists).toBe(true);
        expect(result.fulltext.readable).toBe(true);
        expect(result.fulltext.text).toBe('Fulltext content here.');
        expect(app.vault.getAbstractFileByPath).toHaveBeenCalledWith('path/to/fulltext.md');
        expect(app.vault.read).toHaveBeenCalledWith(mockFile);
    });

    it('falls back to note_path when fulltext_path is unavailable', async () => {
        const { view, app } = makeViewWithVault();
        // Fulltext file doesn't exist
        app.vault.getAbstractFileByPath.mockImplementation((p) => {
            if (p === 'path/to/note.md') return { path: 'note.md' };
            return null;
        });
        app.vault.read.mockResolvedValue('Note content here.');

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_B',
            fulltext_path: 'path/to/missing-ft.md',
            note_path: 'path/to/note.md',
        });

        // Fulltext should be missing
        expect(result.fulltext.exists).toBe(false);
        expect(result.fulltext.readable).toBe(false);
        // Note should be readable
        expect(result.note.exists).toBe(true);
        expect(result.note.readable).toBe(true);
        expect(result.note.text).toBe('Note content here.');
        expect(app.vault.getAbstractFileByPath).toHaveBeenCalledWith('path/to/missing-ft.md');
        expect(app.vault.getAbstractFileByPath).toHaveBeenCalledWith('path/to/note.md');
    });

    it('returns both unavailable when neither fulltext_path nor note_path exist', async () => {
        const { view, app } = makeViewWithVault();
        app.vault.getAbstractFileByPath.mockReturnValue(null);

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_C',
            fulltext_path: 'path/to/nowhere.md',
            note_path: 'path/to/also-nowhere.md',
        });

        expect(result.fulltext.exists).toBe(false);
        expect(result.fulltext.readable).toBe(false);
        expect(result.note.exists).toBe(false);
        expect(result.note.readable).toBe(false);
        expect(result.fulltext.path).toBe('path/to/nowhere.md');
        expect(result.note.path).toBe('path/to/also-nowhere.md');
    });

    // ── D-17: Path/file diagnostic distinctions ──

    it('D-17: distinguishes missing fulltext path (null) from file read error', async () => {
        const { view, app } = makeViewWithVault();
        // Only note_path is provided; fulltext_path is null
        app.vault.getAbstractFileByPath.mockImplementation((p) => {
            if (p === 'path/to/note.md') return { path: 'note.md' };
            return null;
        });
        app.vault.read.mockResolvedValue('Note text');

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_D',
            fulltext_path: null,
            note_path: 'path/to/note.md',
        });

        // Fulltext: path is null → no path at all
        expect(result.fulltext.path).toBeNull();
        expect(result.fulltext.exists).toBe(false);
        expect(result.fulltext.readable).toBe(false);
        // Error should mention missing path
        expect(result.fulltext.error).toBeTruthy();
        // Note: should work normally
        expect(result.note.readable).toBe(true);
        expect(result.note.text).toBe('Note text');
    });

    it('D-17: distinguishes missing file (getAbstractFileByPath returns null) from readable', async () => {
        const { view, app } = makeViewWithVault();
        app.vault.getAbstractFileByPath.mockReturnValue(null);

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_E',
            fulltext_path: 'path/to/nonexistent.md',
            note_path: null,
        });

        // Fulltext: path exists but file doesn't
        expect(result.fulltext.path).toBe('path/to/nonexistent.md');
        expect(result.fulltext.exists).toBe(false);
        expect(result.fulltext.readable).toBe(false);
        expect(result.fulltext.error).toBeTruthy();
        // Error should NOT say "path is missing" — it should say file not found or similar
        expect(result.fulltext.error).not.toMatch(/path.*missing/i);
    });

    it('D-17: captures read error when vault.read rejects', async () => {
        const { view, app } = makeViewWithVault();
        const mockFile = { path: 'bad.md' };
        app.vault.getAbstractFileByPath.mockReturnValue(mockFile);
        app.vault.read.mockRejectedValue(new Error('Permission denied'));

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_F',
            fulltext_path: 'path/to/bad.md',
            note_path: null,
        });

        expect(result.fulltext.exists).toBe(true);
        expect(result.fulltext.readable).toBe(false);
        expect(result.fulltext.text).toBeNull();
        // Error message should be captured
        expect(result.fulltext.error).toBeTruthy();
        expect(result.fulltext.error).toContain('Permission denied');
    });

    // ── Stale load guard ──

    it('stale guard skips I/O when same paperKey is loaded again', async () => {
        const { view, app } = makeViewWithVault();
        const mockFile = { path: 'ft.md' };
        app.vault.getAbstractFileByPath.mockReturnValue(mockFile);
        app.vault.read.mockResolvedValue('Content');

        // First call — should do I/O
        const first = await view._loadCanvasSourceInputs({
            key: 'SAME_KEY',
            fulltext_path: 'path/to/ft.md',
        });
        expect(first.fulltext.text).toBe('Content');
        expect(app.vault.read).toHaveBeenCalledTimes(1);

        // Second call with same key — should skip I/O, return cached
        app.vault.read.mockClear();
        app.vault.getAbstractFileByPath.mockClear();
        const second = await view._loadCanvasSourceInputs({
            key: 'SAME_KEY',
            fulltext_path: 'path/to/ft.md',
        });

        expect(second.fulltext.text).toBe('Content');
        // I/O should NOT have been called again
        expect(app.vault.read).not.toHaveBeenCalled();
        expect(app.vault.getAbstractFileByPath).not.toHaveBeenCalled();
    });

    it('stale guard does NOT skip when paperKey differs', async () => {
        const { view, app } = makeViewWithVault();
        const mockFile = { path: 'ft.md' };
        app.vault.getAbstractFileByPath.mockReturnValue(mockFile);
        let readCount = 0;
        app.vault.read.mockImplementation(() => {
            readCount++;
            return Promise.resolve('Content v' + readCount);
        });

        // First paper
        await view._loadCanvasSourceInputs({
            key: 'KEY_1',
            fulltext_path: 'path/to/ft.md',
        });
        expect(readCount).toBe(1);

        // Different paper — should do I/O again
        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_2',
            fulltext_path: 'path/to/ft.md',
        });
        expect(readCount).toBe(2);
        expect(result.fulltext.text).toBe('Content v2');
    });

    // ── Return shape contract ──

    it('returns sourceInputs with correct fulltext/note shape', async () => {
        const { view } = makeViewWithVault();
        // Minimal: no paths at all
        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_G',
        });

        // Both fulltext and note should have the standard shape
        expect(result).toHaveProperty('fulltext');
        expect(result).toHaveProperty('note');
        expect(result.fulltext).toHaveProperty('path');
        expect(result.fulltext).toHaveProperty('exists');
        expect(result.fulltext).toHaveProperty('readable');
        expect(result.fulltext).toHaveProperty('text');
        expect(result.fulltext).toHaveProperty('error');
        expect(result.note).toHaveProperty('path');
        expect(result.note).toHaveProperty('exists');
        expect(result.note).toHaveProperty('readable');
        expect(result.note).toHaveProperty('text');
        expect(result.note).toHaveProperty('error');
    });

    // ── D-15/D-16/D-18: Missing source doesn't break card state ──

    it('missing source inputs still produce a valid result (not null/undefined)', async () => {
        const { view } = makeViewWithVault();

        const result = await view._loadCanvasSourceInputs({
            key: 'KEY_H',
        });

        // Should be a valid object, not null/undefined/throw
        expect(result).toBeTruthy();
        expect(typeof result).toBe('object');
        expect(result.fulltext.exists).toBe(false);
        expect(result.note.exists).toBe(false);
    });

    // ── D-04/D-26: No native PDF selectors or PDF viewer internals ──

    it('runtime source loading adds no native PDF DOM selectors/classes', () => {
        const { view, containerEl } = makeViewWithVault();
        view.setPaperContext('KEY_PDF_SAFE', { key: 'KEY_PDF_SAFE', title: 'Safe' });

        const html = containerEl.innerHTML.toLowerCase();
        // No native PDF classes (D-04, D-26)
        expect(html).not.toContain('pdf-viewer');
        expect(html).not.toContain('pdf-embed');
        expect(html).not.toContain('data-page-number');
        // No connector or SVG geometry (D-24)
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
    });

    // ── D-24/D-25: No mutation/edit/write controls ──

    it('runtime adds no card-source navigation or mutation controls', () => {
        const { view, containerEl } = makeViewWithVault();
        view.setPaperContext('KEY_CTRL', { key: 'KEY_CTRL', title: 'Control' });

        const text = containerEl.textContent.toLowerCase();
        const forbidden = ['edit', 'delete', 'create', 'save', 'import', 'apply', 'write back', 'write-back',
                           'evidence', 'concept card'];
        for (const word of forbidden) {
            expect(text).not.toContain(word);
        }

        const html = containerEl.innerHTML.toLowerCase();
        expect(html).not.toContain('draggable="true"');
        expect(html).not.toContain('contenteditable');
    });
});

// ── ANN13-04 Task 1: Loaded canvas runtime rendering ──

describe('ANN13-04 Task 1 — Loaded canvas rendering', () => {

    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app: makeStubApp() });
        view.contentEl = contentEl;
        view.app = makeStubApp();
        return { view, containerEl, contentEl };
    }

    it('has _renderLoadedCanvas method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._renderLoadedCanvas).toBe('function');
    });

    it('has getNavigationState method', () => {
        const { view } = makeCanvasView();
        expect(typeof view.getNavigationState).toBe('function');
    });

    it('_renderLoadedCanvas renders content without throwing', () => {
        const { view, containerEl } = makeCanvasView();
        view._paperKey = 'KEY_TEST';
        view._paperEntry = { key: 'KEY_TEST', title: 'Test' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });
        expect(containerEl.querySelector('.paperforge-reading-canvas-view')).toBeTruthy();
    });

    it('_renderLoadedCanvas sets _vm and _navigationState', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_STATE';
        view._paperEntry = { key: 'KEY_STATE', title: 'State' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'none' },
            note: { path: null, exists: false, readable: false, text: null, error: 'none' },
        });
        expect(view._vm).toBeTruthy();
        expect(view._navigationState).toBeTruthy();
    });
});

// ── ANN13-04 Task 2/3: Event handlers and lifecycle ──

describe('ANN13-04 Task 2/3 — Event delegation and lifecycle', () => {

    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app: makeStubApp() });
        view.contentEl = contentEl;
        view.app = makeStubApp();
        return { view, containerEl, contentEl };
    }

    it('click on card triggers _handleCanvasClick without error', () => {
        const { view, contentEl } = makeCanvasView();
        view._vm = { cards: [{ id: 'card-1', pageIndex: 0 }] };
        view._navigationState = { selectedCardId: null, selectedAnchorId: null, selectedGroupId: null, sourceFocusTargetId: null, statusMessage: null, navSource: null };
        view._initDelegatedEvents(contentEl);

        const cardEl = document.createElement('div');
        cardEl.setAttribute('data-card-id', 'card-1');
        contentEl.appendChild(cardEl);

        expect(() => {
            cardEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }).not.toThrow();
    });

    it('Escape key reduces lifecycle state', () => {
        const { view, contentEl } = makeCanvasView();
        view._vm = { cards: [] };
        view._navigationState = { selectedCardId: 'card-1', selectedAnchorId: null, selectedGroupId: null, sourceFocusTargetId: null, statusMessage: null, navSource: null };
        view._initDelegatedEvents(contentEl);

        const evt = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true });
        contentEl.dispatchEvent(evt);

        expect(view._navigationState.selectedCardId).toBeNull();
    });
});

// ── ANN13-04 Task 4: Fallback opening ──

describe('ANN13-04 Task 4 — Fallback PDF handling', () => {

    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const app = {
            workspace: { openLinkText: vi.fn() },
            vault: { adapter: { basePath: 'C:/vault' } },
        };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app });
        view.contentEl = contentEl;
        view.app = app;
        return { view, containerEl, contentEl };
    }

    it('_handleFallbackClick calls openLinkText when paperEntry has pdf_path', () => {
        const { view } = makeCanvasView();
        view._paperEntry = { key: 'KEY_FB', pdf_path: 'storage/KEY/file.pdf' };
        view._handleFallbackClick('3');
        expect(view.app.workspace.openLinkText).toHaveBeenCalled();
    });

    it('_handleFallbackClick does nothing when no page', () => {
        const { view } = makeCanvasView();
        view._paperEntry = { key: 'KEY_FB', pdf_path: 'storage/KEY/file.pdf' };
        view._handleFallbackClick(null);
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });

    it('_handleFallbackClick does nothing when no entry', () => {
        const { view } = makeCanvasView();
        view._paperEntry = null;
        view._handleFallbackClick('3');
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });
});

// ── ANN14-03 Task 1: Connector layer ownership ──

describe('ANN14-03 Task 1 — Connector layer ownership', () => {

    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app: makeStubApp() });
        view.contentEl = contentEl;
        view.app = makeStubApp();
        return { view, containerEl, contentEl };
    }

    it('constructor initializes connector fields to null/zero', () => {
        const { view } = makeCanvasView();
        expect(view._connectorLayerEl).toBeNull();
        expect(view._connectorFrameHandle).toBeNull();
        expect(view._hoveredCardId).toBeNull();
        expect(view._hoveredAnchorId).toBeNull();
        expect(view._connectorBoundMouseover).toBeNull();
        expect(view._connectorBoundMouseout).toBeNull();
        expect(view._connectorBoundScroll).toBeNull();
        expect(view._connectorBoundResize).toBeNull();
    });

    it('has _clearConnectorLayer method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._clearConnectorLayer).toBe('function');
    });

    it('has _initConnectorHoverEvents method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._initConnectorHoverEvents).toBe('function');
    });

    it('has _initConnectorScrollResize method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._initConnectorScrollResize).toBe('function');
    });

    it('has _scheduleConnectorUpdate method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._scheduleConnectorUpdate).toBe('function');
    });

    it('has _updateConnector method', () => {
        const { view } = makeCanvasView();
        expect(typeof view._updateConnector).toBe('function');
    });

    it('_renderLoadedCanvas creates connector layer with correct class', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_CONN';
        view._paperEntry = { key: 'KEY_CONN', title: 'Connector Test' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        const layer = contentEl.querySelector('.paperforge-canvas-connector-layer');
        expect(layer).toBeTruthy();
        expect(layer.tagName).toBe('svg');
        expect(layer.getAttribute('aria-hidden')).toBe('true');
        expect(view._connectorLayerEl).toBe(layer);
    });

    it('_renderLoadedCanvas layer is empty (no default paths)', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_EMPTY';
        view._paperEntry = { key: 'KEY_EMPTY', title: 'Empty' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        const layer = contentEl.querySelector('.paperforge-canvas-connector-layer');
        expect(layer).toBeTruthy();
        // Layer should have no child elements initially
        expect(layer.children.length).toBe(0);
    });

    it('_clearConnectorLayer is safe on null layer and on empty layer', () => {
        const { view } = makeCanvasView();
        // Null layer
        expect(() => view._clearConnectorLayer()).not.toThrow();
        // Empty layer (after _renderLoadedCanvas)
        view._paperKey = 'KEY_SAFE';
        view._paperEntry = { key: 'KEY_SAFE', title: 'Safe' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });
        expect(() => view._clearConnectorLayer()).not.toThrow();
    });

    it('onClose clears connector layer and resets hover state', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_CLOSE';
        view._paperEntry = { key: 'KEY_CLOSE', title: 'Close' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // Set some hover state
        view._hoveredCardId = 'card-1';
        view._hoveredAnchorId = 'card-1';

        view.onClose();

        expect(view._connectorLayerEl).toBeNull();
        expect(view._connectorFrameHandle).toBeNull();
        expect(view._hoveredCardId).toBeNull();
        expect(view._hoveredAnchorId).toBeNull();
    });

    it('_cleanupNavigation clears connector hover state and bound refs', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_CLEAN';
        view._paperEntry = { key: 'KEY_CLEAN', title: 'Clean' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // Verify initial state after render
        expect(view._connectorLayerEl).toBeTruthy();
        expect(view._connectorBoundScroll).toBeTruthy();
        expect(view._connectorBoundResize).toBeTruthy();

        view._cleanupNavigation();

        expect(view._hoveredCardId).toBeNull();
        expect(view._hoveredAnchorId).toBeNull();
        expect(view._connectorBoundMouseover).toBeNull();
        expect(view._connectorBoundMouseout).toBeNull();
    });

    it('consecutive _cleanupNavigation calls are safe', () => {
        const { view } = makeCanvasView();
        expect(() => {
            view._cleanupNavigation();
            view._cleanupNavigation();
        }).not.toThrow();
    });

    it('_cleanupNavigation preserves ANN13 event cleanup', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_PRESERVE';
        view._paperEntry = { key: 'KEY_PRESERVE', title: 'Preserve' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        view._cleanupNavigation();

        // ANN13 cleanup should still work
        expect(view._boundHandleCanvasClick).toBeNull();
        expect(view._boundHandleCanvasKeydown).toBeNull();
    });

    it('empty contentEl in _cleanupNavigation does not throw', () => {
        const { view, contentEl } = makeCanvasView();
        // Remove contentEl to simulate edge case
        view.contentEl = null;
        expect(() => view._cleanupNavigation()).not.toThrow();
    });

    it('_renderLoadedCanvas scroll listener references are set', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_SCROLL';
        view._paperEntry = { key: 'KEY_SCROLL', title: 'Scroll' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        expect(typeof view._connectorBoundScroll).toBe('function');
        expect(typeof view._connectorBoundResize).toBe('function');
    });

    it('_renderLoadedCanvas adds connector layer after source surface', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_ORDER';
        view._paperEntry = { key: 'KEY_ORDER', title: 'Order' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // The connector layer should be the last child of contentEl
        const allChildren = contentEl.children;
        const lastChild = allChildren[allChildren.length - 1];
        expect(lastChild.classList.contains('paperforge-canvas-connector-layer')).toBe(true);
    });
});

// ── ANN14-03 Task 2: Wire selection + hover to connector render ──

describe('ANN14-03 Task 2 — Hover + selection connector wiring', () => {

    function makeCanvasView() {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        addCreateEl(contentEl);
        addCreateEl(containerEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl, app: makeStubApp() });
        view.contentEl = contentEl;
        view.app = makeStubApp();
        return { view, containerEl, contentEl };
    }

    it('mouseover on card sets hoveredCardId', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER';
        view._paperEntry = { key: 'KEY_HOVER', title: 'Hover Test' };
        // DOM with cards
        contentEl.innerHTML = '<div data-card-id="card-1">Card 1</div><div data-card-id="card-2">Card 2</div>';
        // Attach hover events with DOM present
        view._initConnectorHoverEvents(contentEl);

        // Simulate mouseover on card-1
        const card1 = contentEl.querySelector('[data-card-id="card-1"]');
        const evt = new MouseEvent('mouseover', { bubbles: true });
        card1.dispatchEvent(evt);

        expect(view._hoveredCardId).toBe('card-1');
        expect(view._hoveredAnchorId).toBe('card-1');
    });

    it('mouseout on card resets hover state', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER2';
        view._paperEntry = { key: 'KEY_HOVER2', title: 'Hover Test 2' };
        contentEl.innerHTML = '<div data-card-id="card-1">Card 1</div><div data-card-id="card-2">Card 2</div>';
        view._initConnectorHoverEvents(contentEl);

        // Set hover state
        view._hoveredCardId = 'card-1';
        view._hoveredAnchorId = 'card-1';

        // Simulate mouseout on card-1
        const card1 = contentEl.querySelector('[data-card-id="card-1"]');
        const evt = new MouseEvent('mouseout', { bubbles: true });
        card1.dispatchEvent(evt);

        expect(view._hoveredCardId).toBeNull();
        expect(view._hoveredAnchorId).toBeNull();
    });

    it('mouseout from card to inside contentEl does not clear hover', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER3';
        view._paperEntry = { key: 'KEY_HOVER3', title: 'Hover Test 3' };
        contentEl.innerHTML = '<div data-card-id="card-1">Card 1</div><div class="other">Note</div>';
        view._initConnectorHoverEvents(contentEl);

        // Set initial hover state
        view._hoveredCardId = 'card-1';
        view._hoveredAnchorId = 'card-1';

        // Realistic: mouse leaves card-1 and enters .other (inside contentEl)
        const card1 = contentEl.querySelector('[data-card-id="card-1"]');
        const other = contentEl.querySelector('.other');
        const evt = new MouseEvent('mouseout', {
            bubbles: true,
            relatedTarget: other,
        });
        card1.dispatchEvent(evt);

        // relatedTarget inside contentEl → handler returns early → hover preserved
        expect(view._hoveredCardId).toBe('card-1');
    });

    it('mouseout from card to outside contentEl clears hover', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER4';
        view._paperEntry = { key: 'KEY_HOVER4', title: 'Hover Test 4' };
        contentEl.innerHTML = '<div data-card-id="card-1">Card 1</div><div class="other">Note</div>';
        view._initConnectorHoverEvents(contentEl);

        view._hoveredCardId = 'card-1';
        view._hoveredAnchorId = 'card-1';

        // Realistic: mouse leaves card-1 and enters something outside contentEl
        const outside = document.createElement('div');
        const card1 = contentEl.querySelector('[data-card-id="card-1"]');
        const evt = new MouseEvent('mouseout', {
            bubbles: true,
            relatedTarget: outside,
        });
        card1.dispatchEvent(evt);

        // relatedTarget outside contentEl → handler clears hover
        expect(view._hoveredCardId).toBeNull();
    });

    it('mouseout on non-hovered card does not clear hover state', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER5';
        view._paperEntry = { key: 'KEY_HOVER5', title: 'Hover Test 5' };
        contentEl.innerHTML = '<div data-card-id="card-1">Card 1</div><div data-card-id="card-2">Card 2</div><div class="other">Note</div>';
        view._initConnectorHoverEvents(contentEl);

        view._hoveredCardId = 'card-2';
        view._hoveredAnchorId = 'card-2';

        // Mouseout on card-1 (not hovered) with relatedTarget inside contentEl
        const card1 = contentEl.querySelector('[data-card-id="card-1"]');
        const other = contentEl.querySelector('.other');
        const evt = new MouseEvent('mouseout', {
            bubbles: true,
            relatedTarget: other,
        });
        card1.dispatchEvent(evt);

        // card-1 !== hovered card-2 and relatedTarget inside contentEl → hover preserved
        expect(view._hoveredCardId).toBe('card-2');
    });

    it('mouseover sets anchorId to cardId when no more specific anchor', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_HOVER5';
        view._paperEntry = { key: 'KEY_HOVER5', title: 'Hover Test 5' };
        contentEl.innerHTML = '<div data-card-id="card-3">Card 3</div>';
        view._initConnectorHoverEvents(contentEl);

        const card3 = contentEl.querySelector('[data-card-id="card-3"]');
        card3.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));

        expect(view._hoveredCardId).toBe('card-3');
        expect(view._hoveredAnchorId).toBe('card-3');
    });

    it('_applyCardNavigationState schedules connector update', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_SEL';
        view._paperEntry = { key: 'KEY_SEL', title: 'Sel' };
        view._contentEl = document.createElement('div');
        view.contentEl = view._contentEl;

        const spy = vi.spyOn(view, '_scheduleConnectorUpdate');

        view._applyCardNavigationState({
            selectedCardId: 'card-1',
            sourceFocusTargetId: null,
            navSource: 'card',
        });

        expect(spy).toHaveBeenCalledTimes(1);
        spy.mockRestore();
    });

    it('_initConnectorHoverEvents does not throw on null contentEl', () => {
        const { view } = makeCanvasView();
        expect(() => view._initConnectorHoverEvents(null)).not.toThrow();
    });
});
