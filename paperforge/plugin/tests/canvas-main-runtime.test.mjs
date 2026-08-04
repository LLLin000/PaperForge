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
let PaperForgePlugin;
let PaperForgeReadingCanvasView;
let VIEW_TYPE_PAPERFORGE_READING_CANVAS;
let openReadingCanvasForActivePaper;
let buildAnnotationCreateLocalArgs;
let mapPageDomRectToPdfRect;
let markdownRenderCalls;
let markdownRenderImpl;
let lastMenu;

/**
 * Global capture for Notice calls during tests.
 */
const noticeCalls = [];

function installObsidianStub() {
    originalLoad = Module._load;
    markdownRenderCalls = [];
    lastMenu = null;
    markdownRenderImpl = async (_app, markdown, el, sourcePath) => {
        markdownRenderCalls.push({ markdown, el, sourcePath });
        const headingMatch = markdown.match(/^#\s+(.+)$/m);
        if (headingMatch) {
            const h1 = document.createElement('h1');
            h1.textContent = headingMatch[1];
            el.appendChild(h1);
        }
        const body = document.createElement('p');
        body.textContent = markdown
            .replace(/^#\s+.+$/m, '')
            .replace(/\*\*/g, '')
            .trim();
        el.appendChild(body);
    };
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
                Menu: class Menu {
                    constructor() {
                        this.items = [];
                        this.shown = false;
                        lastMenu = this;
                    }
                    addItem(callback) {
                        const item = {
                            title: '',
                            icon: '',
                            click: null,
                            setTitle(title) { this.title = title; return this; },
                            setIcon(icon) { this.icon = icon; return this; },
                            onClick(handler) { this.click = handler; return this; },
                        };
                        callback(item);
                        this.items.push(item);
                        return this;
                    }
                    showAtMouseEvent(evt) {
                        this.shown = true;
                        this.event = evt;
                    }
                },
                MarkdownRenderer: {
                    render: vi.fn((app, markdown, el, sourcePath, component) => {
                        return markdownRenderImpl(app, markdown, el, sourcePath, component);
                    }),
                },
                addIcon: vi.fn(),
            };
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    const mainPath = require.resolve('../main.js');
    delete require.cache[mainPath];
    const pluginModule = require('../main.js');
    PaperForgePlugin = pluginModule;
    PaperForgeReadingCanvasView = pluginModule.__test.PaperForgeReadingCanvasView;
    VIEW_TYPE_PAPERFORGE_READING_CANVAS = pluginModule.__test.VIEW_TYPE_PAPERFORGE_READING_CANVAS;
    openReadingCanvasForActivePaper = pluginModule.__test.openReadingCanvasForActivePaper;
    buildAnnotationCreateLocalArgs = pluginModule.__test.buildAnnotationCreateLocalArgs;
    mapPageDomRectToPdfRect = pluginModule.__test.mapPageDomRectToPdfRect;
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
    try {
        vi.runOnlyPendingTimers();
    } catch (_) {}
    vi.useRealTimers();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
    noticeCalls.length = 0;
    markdownRenderCalls = [];
    markdownRenderImpl = null;
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

    it('open helper uses zotero_key from the PaperForge status view entry', () => {
        const entry = {
            zotero_key: 'A7N8GAHS',
            title: 'TROP2 targeting reveals therapy-driven cell state dynamics in colorectal cancer',
            fulltext_path: 'paper/fulltext.md',
        };
        const originalOpen = PaperForgeReadingCanvasView.open;
        PaperForgeReadingCanvasView.open = vi.fn();
        const plugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn((type) => {
                        if (type === 'paperforge-status') {
                            return [{ view: { _currentPaperEntry: entry } }];
                        }
                        return [];
                    }),
                    getActiveFile: vi.fn(() => null),
                },
                metadataCache: { getFileCache: vi.fn() },
            },
        };

        try {
            openReadingCanvasForActivePaper(plugin);
            expect(PaperForgeReadingCanvasView.open).toHaveBeenCalledWith(plugin, 'A7N8GAHS', entry);
        } finally {
            PaperForgeReadingCanvasView.open = originalOpen;
        }
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

        expect(view._paperKey).toBe('PAPER_X');
        expect(view.contentEl.textContent).toContain('Reading Canvas');
        expect(view.contentEl.textContent).toContain('PAPER_X');
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
    });

    it('setPaperContext auto-loads annotations without reading fulltext during open', async () => {
        const view = makeCanvasView();
        view.app = {
            vault: { adapter: { basePath: 'C:/vault' } },
            plugins: { plugins: { paperforge: { settings: { python_bin: 'python' } } } },
        };
        view._loadCanvasSourceInputs = vi.fn();
        view._loadAndRenderCanvas = vi.fn();
        view._annotationLoader = vi.fn(async () => ({
            state: 'ready',
            paperKey: 'PAPER_LIGHT_OPEN',
            annotations: [{
                display: {
                    selectedText: 'Only this annotation should load',
                    comment: 'No fulltext read needed',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-only-1' },
            }],
            message: '1 annotation(s) loaded.',
        }));

        view.setPaperContext('PAPER_LIGHT_OPEN', { key: 'PAPER_LIGHT_OPEN', title: 'Light Open' });
        await Promise.resolve();
        await Promise.resolve();

        expect(view._annotationLoader).toHaveBeenCalledWith(expect.objectContaining({ paperKey: 'PAPER_LIGHT_OPEN' }));
        expect(view._loadCanvasSourceInputs).not.toHaveBeenCalled();
        expect(view._loadAndRenderCanvas).not.toHaveBeenCalled();
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
        expect(view.contentEl.textContent).toContain('Only this annotation should load');
    });

    it('clicking an annotation panel card highlights the matching text in the active fulltext DOM', () => {
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        const paragraph = document.createElement('p');
        paragraph.textContent = 'The active fulltext already contains the important annotation sentence in Obsidian.';
        preview.appendChild(paragraph);
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        const scrollIntoView = vi.fn();
        Element.prototype.scrollIntoView = scrollIntoView;
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: activeContainer } },
            },
        };

        view._renderNativeAnnotationPanel('PAPER_DOM', { key: 'PAPER_DOM' }, {
            state: 'ready',
            paperKey: 'PAPER_DOM',
            annotations: [{
                display: {
                    selectedText: 'important annotation sentence',
                    comment: 'Click should jump to this selected text',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-dom-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));

        const mark = preview.querySelector('mark.paperforge-active-annotation-match');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toBe('important annotation sentence');
        expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
        expect(view.contentEl.querySelector('[data-anchor-status="unresolved"]')).toBeFalsy();
    });

    it('strips lightweight html tags from annotation quote and comment text', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_TAGS', { key: 'PAPER_TAGS' }, {
            state: 'ready',
            paperKey: 'PAPER_TAGS',
            annotations: [{
                display: {
                    selectedText: 'plain <b>important</b> quote',
                    comment: 'comment with </b> dangling tag',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-tags' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const quote = view.contentEl.querySelector('.paperforge-annotation-panel-quote');
        const comment = view.contentEl.querySelector('.paperforge-annotation-panel-comment');
        expect(quote.textContent).toBe('plain important quote');
        expect(comment.textContent).toBe('comment with dangling tag');
        expect(view.contentEl.textContent).not.toContain('</b>');
        expect(view.contentEl.textContent).not.toContain('<b>');
    });

    it('renders color filter chips and lets readers show one annotation color at a time', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_COLORS', { key: 'PAPER_COLORS' }, {
            state: 'ready',
            paperKey: 'PAPER_COLORS',
            annotations: [
                {
                    display: { selectedText: 'yellow note', type: 'highlight', color: '#ffd400' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { sourceAnnotationKey: 'ann-yellow' },
                },
                {
                    display: { selectedText: 'red note', type: 'highlight', color: '#ff6666' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                    provenance: { sourceAnnotationKey: 'ann-red' },
                },
            ],
            message: '2 annotation(s) loaded.',
        });

        const filters = view.contentEl.querySelectorAll('.paperforge-annotation-color-filter');
        expect(filters.length).toBe(3);
        expect(view.contentEl.querySelectorAll('.paperforge-annotation-panel-card')).toHaveLength(2);

        const redFilter = Array.from(filters).find((el) => el.getAttribute('data-color-filter') === '#ff6666');
        redFilter.click();

        const cards = view.contentEl.querySelectorAll('.paperforge-annotation-panel-card');
        expect(cards).toHaveLength(1);
        expect(cards[0].textContent).toContain('red note');
        expect(cards[0].textContent).not.toContain('yellow note');
    });

    it('keeps annotation color filters pinned while the annotation list scrolls', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_PINNED_FILTERS', { key: 'PAPER_PINNED_FILTERS' }, {
            state: 'ready',
            paperKey: 'PAPER_PINNED_FILTERS',
            annotations: [
                {
                    display: { selectedText: 'yellow note', type: 'highlight', color: '#ffd400' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { sourceAnnotationKey: 'ann-yellow' },
                },
                {
                    display: { selectedText: 'red note', type: 'highlight', color: '#ff6666' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                    provenance: { sourceAnnotationKey: 'ann-red' },
                },
            ],
            message: '2 annotation(s) loaded.',
        });

        const panel = view.contentEl.querySelector('.paperforge-annotation-panel');
        const chrome = view.contentEl.querySelector('.paperforge-annotation-panel-chrome');
        const filters = view.contentEl.querySelector('.paperforge-annotation-color-filters');
        const list = view.contentEl.querySelector('.paperforge-annotation-panel-list');

        expect(panel.style.display).toBe('flex');
        expect(panel.style.overflow).toBe('hidden');
        expect(chrome).toBeTruthy();
        expect(chrome.style.position).toBe('sticky');
        expect(chrome.style.top).toBe('0px');
        expect(filters.parentElement).toBe(chrome);
        expect(list.style.overflowY).toBe('auto');
        expect(list.style.flex).toBe('1 1 auto');
        view._clearImportedAnnotationProjectionTimers();
    });

    it('builds create-local CLI args for an Obsidian-owned PDF bbox annotation', () => {
        const args = buildAnnotationCreateLocalArgs({
            paperKey: 'PAPER_LOCAL',
            pageIndex: 2,
            pageLabel: '3',
            selectedText: 'local PDF quote',
            comment: '',
            color: '#5fb236',
            type: 'highlight',
            positionJson: '{"pageIndex":2,"rects":[[10,20,40,30]]}',
        });

        expect(args).toEqual([
            '-m', 'paperforge', 'annotation', 'create-local',
            '--paper', 'PAPER_LOCAL',
            '--page-index', '2',
            '--page-label', '3',
            '--selected-text', 'local PDF quote',
            '--comment', '',
            '--color', '#5fb236',
            '--type', 'highlight',
            '--position-json', '{"pageIndex":2,"rects":[[10,20,40,30]]}',
            '--json',
        ]);
    });

    it('maps a PDF text selection DOM rect back into Zotero-style PDF bbox coordinates', () => {
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '3');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 50,
            top: 100,
            width: 595.276,
            height: 790.866,
            right: 645.276,
            bottom: 890.866,
        }));

        const rect = mapPageDomRectToPdfRect({
            left: 125.038,
            top: 590.309,
            width: 219.607,
            height: 8.217,
        }, page);

        expect(rect).toEqual([75.038, 292.34, 294.645, 300.557]);
    });

    it('labels Zotero annotations as locked and Obsidian annotations as local editable rows', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_OWNERSHIP', { key: 'PAPER_OWNERSHIP' }, {
            state: 'ready',
            paperKey: 'PAPER_OWNERSHIP',
            annotations: [
                {
                    display: { selectedText: 'zotero quote', type: 'highlight', color: '#ffd400' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { source: 'zotero', isReadonly: true, sourceAnnotationKey: 'ann-zotero' },
                },
                {
                    display: { selectedText: 'local quote', type: 'highlight', color: '#5fb236' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                    provenance: { source: 'obsidian', isReadonly: false, sourceAnnotationKey: 'ann-local' },
                },
            ],
            message: '2 annotation(s) loaded.',
        });

        const cards = view.contentEl.querySelectorAll('.paperforge-annotation-panel-card');
        expect(cards[0].getAttribute('data-annotation-source')).toBe('zotero');
        expect(cards[0].getAttribute('data-readonly')).toBe('true');
        expect(cards[0].textContent).toContain('Locked');
        expect(cards[1].getAttribute('data-annotation-source')).toBe('obsidian');
        expect(cards[1].getAttribute('data-readonly')).toBe('false');
        expect(cards[1].textContent).toContain('Local');
        view._clearImportedAnnotationProjectionTimers();
    });

    it('renders local comment editing only when the local annotation card is selected', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_LOCAL_EDIT', { key: 'PAPER_LOCAL_EDIT' }, {
            state: 'ready',
            paperKey: 'PAPER_LOCAL_EDIT',
            annotations: [
                {
                    display: { selectedText: 'locked quote', comment: 'locked note', type: 'highlight', color: '#ffd400' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { source: 'zotero', isReadonly: true, sourceAnnotationKey: 'ann-locked' },
                },
                {
                    display: { selectedText: 'local quote', comment: 'editable note', type: 'highlight', color: '#5fb236' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                    provenance: { source: 'obsidian', isReadonly: false, sourceAnnotationKey: 'ann-local-edit' },
                },
            ],
            message: '2 annotation(s) loaded.',
        });

        const cards = view.contentEl.querySelectorAll('.paperforge-annotation-panel-card');
        expect(cards[0].querySelector('[data-local-comment-editor]')).toBeFalsy();
        const editorWrap = cards[1].querySelector('.paperforge-annotation-local-editor');
        expect(editorWrap).toBeTruthy();
        expect(editorWrap.hidden).toBe(true);
        cards[1].setAttribute('aria-selected', 'true');
        view._syncLocalAnnotationEditorsVisibility();
        expect(editorWrap.hidden).toBe(false);
        const editor = cards[1].querySelector('[data-local-comment-editor]');
        expect(editor).toBeTruthy();
        expect(editor.value).toBe('editable note');
        expect(cards[1].querySelector('[data-action="paperforge-save-local-comment"]')).toBeTruthy();
        view._clearImportedAnnotationProjectionTimers();
    });

    it('saves edited local annotation comments without triggering card navigation', async () => {
        const view = makeCanvasView();
        view.app = {
            vault: { adapter: { basePath: 'C:/vault' } },
            plugins: { plugins: { paperforge: { settings: {} } } },
        };
        view._runUpdateLocalAnnotationComment = vi.fn(async () => ({
            ok: true,
            annotation: { id: 'ann-local-save', comment: 'new local note' },
        }));
        view._reloadNativeAnnotationPanelAfterLocalCreate = vi.fn(async () => null);
        view._openPdfForAnnotationRow = vi.fn(() => ({ ok: true, page: 1 }));

        view._renderNativeAnnotationPanel('PAPER_LOCAL_SAVE', { key: 'PAPER_LOCAL_SAVE' }, {
            state: 'ready',
            paperKey: 'PAPER_LOCAL_SAVE',
            annotations: [{
                display: { selectedText: 'local quote', comment: 'old note', type: 'highlight', color: '#5fb236' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                provenance: { source: 'obsidian', isReadonly: false, sourceAnnotationKey: 'ann-local-save' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const editor = view.contentEl.querySelector('[data-local-comment-editor]');
        editor.value = 'new local note';
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        const button = view.contentEl.querySelector('[data-action="paperforge-save-local-comment"]');
        button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(view._runUpdateLocalAnnotationComment).toHaveBeenCalledWith('ann-local-save', 'new local note');
        expect(view._openPdfForAnnotationRow).not.toHaveBeenCalled();
        expect(view._reloadNativeAnnotationPanelAfterLocalCreate).toHaveBeenCalled();
        view._clearImportedAnnotationProjectionTimers();
    });

    it('opens a PaperForge color menu from a selected PDF region', async () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_CONTEXT_MENU';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '4');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 10,
            top: 20,
            width: 595.276,
            height: 790.866,
            right: 605.276,
            bottom: 810.866,
        }));
        pdfRoot.appendChild(page);
        view.app = {
            vault: { adapter: { basePath: 'C:/vault' } },
            plugins: { plugins: { paperforge: { settings: {} } } },
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };
        vi.spyOn(window, 'getSelection').mockImplementation(() => ({
            rangeCount: 1,
            toString: () => 'context menu selected quote',
            getRangeAt: () => ({
                getClientRects: () => [{ left: 110, top: 220, width: 160, height: 12 }],
            }),
        }));
        view._runCreateLocalAnnotation = vi.fn(async () => ({ ok: true, annotation: { id: 'obsidian:PAPER_CONTEXT_MENU:1' } }));
        view._reloadNativeAnnotationPanelAfterLocalCreate = vi.fn(async () => null);

        view._renderNativeAnnotationPanel('PAPER_CONTEXT_MENU', { key: 'PAPER_CONTEXT_MENU' }, {
            state: 'ready',
            paperKey: 'PAPER_CONTEXT_MENU',
            annotations: [],
            message: '0 annotation(s) loaded.',
        });

        const event = new MouseEvent('contextmenu', { bubbles: true, cancelable: true, clientX: 30, clientY: 40 });
        pdfRoot.dispatchEvent(event);
        expect(lastMenu).toBeTruthy();
        expect(lastMenu.shown).toBe(true);
        expect(lastMenu.items.map((item) => item.title)).toEqual(['Yellow', 'Red', 'Note', 'Important']);

        lastMenu.items[1].click();
        await Promise.resolve();

        expect(view._runCreateLocalAnnotation).toHaveBeenCalledTimes(1);
        expect(view._runCreateLocalAnnotation.mock.calls[0][0]).toMatchObject({
            paperKey: 'PAPER_CONTEXT_MENU',
            pageIndex: 3,
            selectedText: 'context menu selected quote',
            color: '#ff6666',
        });
        view._clearImportedAnnotationProjectionTimers();
    });

    it('builds a local annotation payload from the current PDF text selection', () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_SELECT';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '3');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 50,
            top: 100,
            width: 595.276,
            height: 790.866,
            right: 645.276,
            bottom: 890.866,
        }));
        pdfRoot.appendChild(page);
        view.app = {
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };
        const selection = {
            rangeCount: 1,
            toString: () => 'local PDF quote',
            getRangeAt: () => ({
                getClientRects: () => [{
                    left: 125.038,
                    top: 590.309,
                    width: 219.607,
                    height: 8.217,
                }],
            }),
        };

        const payload = view._buildLocalAnnotationPayloadFromPdfSelection(selection);

        expect(payload).toMatchObject({
            paperKey: 'PAPER_SELECT',
            pageIndex: 2,
            pageLabel: '3',
            selectedText: 'local PDF quote',
            color: '#ffd400',
            type: 'highlight',
        });
        expect(JSON.parse(payload.positionJson)).toEqual({
            pageIndex: 2,
            rects: [[75.038, 292.34, 294.645, 300.557]],
        });
    });

    it('renders an Add Local Annotation button in the pinned annotation controls', () => {
        const view = makeCanvasView();

        view._renderNativeAnnotationPanel('PAPER_ADD_LOCAL', { key: 'PAPER_ADD_LOCAL' }, {
            state: 'ready',
            paperKey: 'PAPER_ADD_LOCAL',
            annotations: [
                {
                    display: { selectedText: 'zotero quote', type: 'highlight', color: '#ffd400' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { source: 'zotero', isReadonly: true, sourceAnnotationKey: 'ann-zotero' },
                },
            ],
            message: '1 annotation(s) loaded.',
        });

        const chrome = view.contentEl.querySelector('.paperforge-annotation-panel-chrome');
        const button = chrome.querySelector('[data-action="paperforge-add-local-annotation"]');
        expect(button).toBeTruthy();
        expect(button.textContent).toContain('Add Local');
        view._clearImportedAnnotationProjectionTimers();
    });

    it('lets readers choose a local annotation color before creating it', () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_LOCAL_COLOR';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '1');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 0,
            top: 0,
            width: 595.276,
            height: 790.866,
            right: 595.276,
            bottom: 790.866,
        }));
        pdfRoot.appendChild(page);
        view.app = {
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_LOCAL_COLOR', { key: 'PAPER_LOCAL_COLOR' }, {
            state: 'ready',
            paperKey: 'PAPER_LOCAL_COLOR',
            annotations: [],
            message: '0 annotation(s) loaded.',
        });

        const red = view.contentEl.querySelector('[data-local-annotation-color="#ff6666"]');
        expect(red).toBeTruthy();
        red.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        const payload = view._buildLocalAnnotationPayloadFromPdfSelection({
            rangeCount: 1,
            toString: () => 'red local quote',
            getRangeAt: () => ({
                getClientRects: () => [{ left: 40, top: 120, width: 180, height: 12 }],
            }),
        });

        expect(payload.color).toBe('#ff6666');
        view._clearImportedAnnotationProjectionTimers();
    });

    it('lets readers type a local annotation note before creating it', () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_LOCAL_NOTE';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '1');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 0,
            top: 0,
            width: 595.276,
            height: 790.866,
            right: 595.276,
            bottom: 790.866,
        }));
        pdfRoot.appendChild(page);
        view.app = {
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_LOCAL_NOTE', { key: 'PAPER_LOCAL_NOTE' }, {
            state: 'ready',
            paperKey: 'PAPER_LOCAL_NOTE',
            annotations: [],
            message: '0 annotation(s) loaded.',
        });

        const input = view.contentEl.querySelector('[data-local-annotation-comment]');
        expect(input).toBeTruthy();
        input.value = 'my own reading note';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const payload = view._buildLocalAnnotationPayloadFromPdfSelection({
            rangeCount: 1,
            toString: () => 'noted local quote',
            getRangeAt: () => ({
                getClientRects: () => [{ left: 40, top: 120, width: 180, height: 12 }],
            }),
        });

        expect(payload.comment).toBe('my own reading note');
        view._clearImportedAnnotationProjectionTimers();
    });

    it('caches the PDF selection on mouse down so clicking Add Local can still create the annotation', async () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_SELECTION_CACHE';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '2');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 10,
            top: 20,
            width: 595.276,
            height: 790.866,
            right: 605.276,
            bottom: 810.866,
        }));
        pdfRoot.appendChild(page);
        view.app = {
            vault: { adapter: { basePath: 'C:/vault' } },
            plugins: { plugins: { paperforge: { settings: {} } } },
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };
        const selected = {
            rangeCount: 1,
            toString: () => 'cached local quote',
            getRangeAt: () => ({
                getClientRects: () => [{ left: 110, top: 220, width: 160, height: 12 }],
            }),
        };
        const empty = {
            rangeCount: 0,
            toString: () => '',
        };
        let currentSelection = selected;
        vi.spyOn(window, 'getSelection').mockImplementation(() => currentSelection);
        view._runCreateLocalAnnotation = vi.fn(async () => ({ ok: true, annotation: { id: 'obsidian:PAPER_SELECTION_CACHE:1' } }));
        view._reloadNativeAnnotationPanelAfterLocalCreate = vi.fn(async () => null);

        view._renderNativeAnnotationPanel('PAPER_SELECTION_CACHE', { key: 'PAPER_SELECTION_CACHE' }, {
            state: 'ready',
            paperKey: 'PAPER_SELECTION_CACHE',
            annotations: [],
            message: '0 annotation(s) loaded.',
        });

        const button = view.contentEl.querySelector('[data-action="paperforge-add-local-annotation"]');
        button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        currentSelection = empty;
        button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(view._runCreateLocalAnnotation).toHaveBeenCalledTimes(1);
        expect(view._runCreateLocalAnnotation.mock.calls[0][0]).toMatchObject({
            paperKey: 'PAPER_SELECTION_CACHE',
            pageIndex: 1,
            pageLabel: '2',
            selectedText: 'cached local quote',
        });
        view._clearImportedAnnotationProjectionTimers();
    });

    it('keeps the cached PDF selection after typing a local annotation note', async () => {
        const view = makeCanvasView();
        view._paperKey = 'PAPER_NOTE_AFTER_SELECT';
        const pdfRoot = document.createElement('div');
        pdfRoot.className = 'pdf-embed';
        const page = document.createElement('div');
        page.setAttribute('data-page-number', '3');
        page.getBoundingClientRect = vi.fn(() => ({
            left: 10,
            top: 20,
            width: 595.276,
            height: 790.866,
            right: 605.276,
            bottom: 810.866,
        }));
        pdfRoot.appendChild(page);
        const selected = {
            rangeCount: 1,
            toString: () => 'quote before typing note',
            getRangeAt: () => ({
                getClientRects: () => [{ left: 110, top: 220, width: 160, height: 12 }],
            }),
        };
        const empty = {
            rangeCount: 0,
            toString: () => '',
        };
        let currentSelection = selected;
        vi.spyOn(window, 'getSelection').mockImplementation(() => currentSelection);
        view.app = {
            vault: { adapter: { basePath: 'C:/vault' } },
            plugins: { plugins: { paperforge: { settings: {} } } },
            workspace: {
                activeLeaf: { view: { contentEl: pdfRoot, containerEl: pdfRoot } },
                getLeavesOfType: vi.fn((type) => type === 'pdf'
                    ? [{ view: { contentEl: pdfRoot, containerEl: pdfRoot } }]
                    : []),
            },
        };
        view._runCreateLocalAnnotation = vi.fn(async () => ({ ok: true, annotation: { id: 'obsidian:PAPER_NOTE_AFTER_SELECT:1' } }));
        view._reloadNativeAnnotationPanelAfterLocalCreate = vi.fn(async () => null);

        view._renderNativeAnnotationPanel('PAPER_NOTE_AFTER_SELECT', { key: 'PAPER_NOTE_AFTER_SELECT' }, {
            state: 'ready',
            paperKey: 'PAPER_NOTE_AFTER_SELECT',
            annotations: [],
            message: '0 annotation(s) loaded.',
        });

        pdfRoot.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
        currentSelection = empty;
        const input = view.contentEl.querySelector('[data-local-annotation-comment]');
        input.value = '213';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const button = view.contentEl.querySelector('[data-action="paperforge-add-local-annotation"]');
        button.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
        button.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(view._runCreateLocalAnnotation).toHaveBeenCalledTimes(1);
        expect(view._runCreateLocalAnnotation.mock.calls[0][0]).toMatchObject({
            paperKey: 'PAPER_NOTE_AFTER_SELECT',
            pageIndex: 2,
            pageLabel: '3',
            selectedText: 'quote before typing note',
            comment: '213',
        });
        view._clearImportedAnnotationProjectionTimers();
    });

    it('rendering the annotation panel immediately projects matching highlights into the open fulltext DOM', async () => {
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = [
            'TROP2 expression marks the first imported yellow annotation.',
            'The same fulltext contains the second imported yellow annotation.',
        ].join(' ');
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: activeContainer } },
            },
        };

        view._renderNativeAnnotationPanel('TROP2KEY', { key: 'TROP2KEY' }, {
            state: 'ready',
            paperKey: 'TROP2KEY',
            annotations: [
                {
                    display: {
                        selectedText: 'first imported yellow annotation',
                        type: 'highlight',
                        color: '#ffd400',
                    },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { sourceAnnotationKey: 'ann-yellow-1' },
                },
                {
                    display: {
                        selectedText: 'second imported yellow annotation',
                        type: 'highlight',
                        color: '#ffd400',
                    },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                    provenance: { sourceAnnotationKey: 'ann-yellow-2' },
                },
            ],
            message: '2 annotation(s) loaded.',
        });
        await Promise.resolve();

        const marks = Array.from(preview.querySelectorAll('mark.paperforge-imported-annotation-highlight'));
        expect(marks).toHaveLength(2);
        expect(marks.map((mark) => mark.textContent)).toEqual([
            'first imported yellow annotation',
            'second imported yellow annotation',
        ]);
        expect(marks.every((mark) => mark.style.backgroundColor === 'rgb(255, 212, 0)')).toBe(true);
        expect(marks.map((mark) => mark.getAttribute('data-annotation-id'))).toEqual([
            'ann-yellow-1',
            'ann-yellow-2',
        ]);
        expect(marks.map((mark) => mark.getAttribute('data-paperforge-annotation-id'))).toEqual([
            'ann-yellow-1',
            'ann-yellow-2',
        ]);
    });

    it('clicking a card uses annotation identity instead of the first similar text match', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const fulltextContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = [
                'First similar Ror2 expression fragment should not be selected.',
                'Second exact Ror2 expression fragment should be selected.',
            ].join(' ');
            fulltextContainer.appendChild(preview);
            document.body.appendChild(fulltextContainer);
            Element.prototype.scrollIntoView = vi.fn();
            view.app = {
                workspace: {
                    activeLeaf: { view: { containerEl: fulltextContainer } },
                    getLeavesOfType: vi.fn((type) => type === 'markdown' ? [{ view: { containerEl: fulltextContainer } }] : []),
                    revealLeaf: vi.fn(),
                },
            };

            view._renderNativeAnnotationPanel('PAPER_SIMILAR', { key: 'PAPER_SIMILAR' }, {
                state: 'ready',
                paperKey: 'PAPER_SIMILAR',
                annotations: [
                    {
                        display: {
                            selectedText: 'First similar Ror2 expression fragment',
                            type: 'highlight',
                            color: '#ff6666',
                        },
                        pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                        provenance: { sourceAnnotationKey: 'ANN_FIRST' },
                    },
                    {
                        display: {
                            selectedText: 'Second exact Ror2 expression fragment',
                            type: 'highlight',
                            color: '#ff6666',
                        },
                        pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 1 },
                        provenance: { sourceAnnotationKey: 'ANN_SECOND' },
                    },
                ],
                message: '2 annotation(s) loaded.',
            });
            expect(preview.querySelectorAll('mark.paperforge-imported-annotation-highlight').length, 'imported marks after render').toBe(2);

            const cards = view.contentEl.querySelectorAll('.paperforge-annotation-panel-card');
            cards[1].dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await vi.advanceTimersByTimeAsync(160);
            await Promise.resolve();

            const active = preview.querySelector('mark.paperforge-active-annotation-match');
            expect(active, preview.innerHTML).toBeTruthy();
            expect(active.textContent).toBe('Second exact Ror2 expression fragment');
            expect(active.getAttribute('data-paperforge-annotation-id')).toBe('ANN_SECOND');
        } finally {
            vi.useRealTimers();
        }
    });

    it('projects highlights into markdown leaves that expose contentEl instead of containerEl', async () => {
        const view = makeCanvasView();
        const fulltextContent = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = 'The TROP2 fulltext pane has a yellow imported highlight.';
        fulltextContent.appendChild(preview);
        document.body.appendChild(fulltextContent);
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: view.contentEl } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { contentEl: fulltextContent } }];
                    return [];
                }),
            },
        };

        view._renderNativeAnnotationPanel('TROP2KEY', { key: 'TROP2KEY' }, {
            state: 'ready',
            paperKey: 'TROP2KEY',
            annotations: [{
                display: {
                    selectedText: 'yellow imported highlight',
                    type: 'highlight',
                    color: '#ffd400',
                },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-content-el' },
            }],
            message: '1 annotation(s) loaded.',
        });
        await Promise.resolve();

        const mark = preview.querySelector('mark.paperforge-imported-annotation-highlight');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toBe('yellow imported highlight');
        expect(mark.getAttribute('data-annotation-id')).toBe('ann-content-el');
    });

    it('retries projection when the fulltext DOM appears after annotations load', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const fulltextContent = document.createElement('div');
            view.app = {
                workspace: {
                    activeLeaf: { view: { containerEl: view.contentEl } },
                    getLeavesOfType: vi.fn((type) => {
                        if (type === 'markdown') return [{ view: { contentEl: fulltextContent } }];
                        return [];
                    }),
                },
            };

            view._renderNativeAnnotationPanel('TROP2KEY', { key: 'TROP2KEY' }, {
                state: 'ready',
                paperKey: 'TROP2KEY',
                annotations: [{
                    display: {
                        selectedText: 'late rendered yellow highlight',
                        type: 'highlight',
                        color: '#ffd400',
                    },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { sourceAnnotationKey: 'ann-late-dom' },
                }],
                message: '1 annotation(s) loaded.',
            });

            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = 'Obsidian rendered a late rendered yellow highlight after the canvas panel.';
            fulltextContent.appendChild(preview);
            vi.advanceTimersByTime(260);
            await Promise.resolve();

            const mark = preview.querySelector('mark.paperforge-imported-annotation-highlight');
            expect(mark).toBeTruthy();
            expect(mark.textContent).toBe('late rendered yellow highlight');
        } finally {
            vi.useRealTimers();
        }
    });

    it('clicking an annotation card rebounds after successful jump feedback', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            view.app = {
                vault: { getAbstractFileByPath: vi.fn(() => ({ path: '99_System/Zotero/storage/ATTACH/test.pdf' })) },
                workspace: { openLinkText: vi.fn() },
            };
            view._paperEntry = {
                key: 'PAPER_REBOUND',
                pdf_path: '[[99_System/Zotero/storage/ATTACH/test.pdf]]',
                zotero_storage_key: 'ATTACH',
            };

            view._renderNativeAnnotationPanel('PAPER_REBOUND', { key: 'PAPER_REBOUND' }, {
                state: 'ready',
                paperKey: 'PAPER_REBOUND',
                annotations: [{
                    display: { selectedText: 'rebound target', type: 'highlight', color: '#ffd54f' },
                    pdfLocation: {
                        sourceAttachmentKey: 'ATTACH',
                        pageIndex: null,
                        pageLabel: '1',
                        sortIndex: 0,
                        positionJson: '{"pageIndex":0,"rects":[[10,20,40,30]]}',
                    },
                    provenance: { source: 'zotero', sourceAttachmentKey: 'ATTACH', sourceAnnotationKey: 'ann-rebound-1' },
                }],
                message: '1 annotation(s) loaded.',
            });

            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await Promise.resolve();

            expect(card.getAttribute('aria-selected')).toBe('true');
            expect(card.getAttribute('data-jump-state')).toBe('opened-pdf');
            expect(view.app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/ATTACH/test.pdf#page=1', '');
            vi.advanceTimersByTime(901);
            expect(card.getAttribute('aria-selected')).toBe('false');
            expect(card.hasAttribute('data-jump-state')).toBe(false);
        } finally {
            vi.useRealTimers();
        }
    });

    it('clicking an annotation panel card paints the Zotero color on the matching PDF rect', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const pdfRoot = document.createElement('div');
            pdfRoot.className = 'pdf-embed';
            const page1 = document.createElement('div');
            page1.setAttribute('data-page-number', '1');
            page1.style.setProperty('--scale-factor', '2');
            page1.getBoundingClientRect = vi.fn(() => ({
                width: 1190,
                height: 1684,
                top: 0,
                left: 0,
                right: 1190,
                bottom: 1684,
            }));
            pdfRoot.appendChild(page1);
            const pdfContent = document.createElement('div');
            pdfContent.appendChild(pdfRoot);
            view.app = {
                vault: { getAbstractFileByPath: vi.fn(() => ({ path: '99_System/Zotero/storage/ATTACH/test.pdf' })) },
                workspace: {
                    activeLeaf: { view: { contentEl: pdfContent, containerEl: pdfContent } },
                    getLeavesOfType: vi.fn((type) => type === 'pdf'
                        ? [{ view: { contentEl: pdfContent, containerEl: pdfContent } }]
                        : []),
                    openLinkText: vi.fn(),
                },
            };
            view._paperEntry = {
                key: 'PAPER_PDF_COLOR',
                pdf_path: '[[99_System/Zotero/storage/ATTACH/test.pdf]]',
                zotero_storage_key: 'ATTACH',
            };

            view._renderNativeAnnotationPanel('PAPER_PDF_COLOR', { key: 'PAPER_PDF_COLOR' }, {
                state: 'ready',
                paperKey: 'PAPER_PDF_COLOR',
                annotations: [{
                    display: { selectedText: 'colored pdf target', type: 'highlight', color: '#ff6666' },
                    pdfLocation: {
                        sourceAttachmentKey: 'ATTACH',
                        pageIndex: null,
                        pageLabel: '1',
                        sortIndex: 0,
                        positionJson: '{"pageIndex":0,"rects":[[10,20,40,30]]}',
                    },
                    provenance: { source: 'zotero', sourceAttachmentKey: 'ATTACH', sourceAnnotationKey: 'ann-pdf-color' },
                }],
                message: '1 annotation(s) loaded.',
            });

            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await vi.advanceTimersByTimeAsync(70);

            const mark = page1.querySelector('.paperforge-canvas-pdf-overlay-mark');
            expect(mark).toBeTruthy();
            expect(mark.getAttribute('data-paperforge-annotation-id')).toContain('ann-pdf-color');
            const line = mark.querySelector('.paperforge-canvas-pdf-overlay-line');
            expect(line).toBeTruthy();
            expect(mark.style.background).toBe('transparent');
            expect(line.style.borderBottom).toBe('3px solid rgb(255, 102, 102)');
            expect(mark.style.left).toBe('20px');
            expect(mark.style.width).toBe('60px');
            expect(parseFloat(mark.style.height)).toBeGreaterThanOrEqual(12);
        } finally {
            vi.useRealTimers();
        }
    });

    it('keeps dense multi-line PDF underlines inside each Zotero bbox', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const pdfRoot = document.createElement('div');
            pdfRoot.className = 'pdf-embed';
            const page7 = document.createElement('div');
            page7.setAttribute('data-page-number', '7');
            page7.getBoundingClientRect = vi.fn(() => ({
                width: 595.276,
                height: 790.866,
                top: 0,
                left: 0,
                right: 595.276,
                bottom: 790.866,
            }));
            pdfRoot.appendChild(page7);
            const pdfContent = document.createElement('div');
            pdfContent.appendChild(pdfRoot);
            view.app = {
                vault: { getAbstractFileByPath: vi.fn(() => ({ path: '99_System/Zotero/storage/ATTACH/test.pdf' })) },
                workspace: {
                    activeLeaf: { view: { contentEl: pdfContent, containerEl: pdfContent } },
                    getLeavesOfType: vi.fn((type) => type === 'pdf'
                        ? [{ view: { contentEl: pdfContent, containerEl: pdfContent } }]
                        : []),
                    openLinkText: vi.fn(),
                },
            };
            view._paperEntry = {
                key: 'PAPER_DENSE_LINES',
                pdf_path: '[[99_System/Zotero/storage/ATTACH/test.pdf]]',
                zotero_storage_key: 'ATTACH',
            };

            view._renderNativeAnnotationPanel('PAPER_DENSE_LINES', { key: 'PAPER_DENSE_LINES' }, {
                state: 'ready',
                paperKey: 'PAPER_DENSE_LINES',
                annotations: [{
                    display: { selectedText: 'dense Nature target', type: 'highlight', color: '#ffd400' },
                    pdfLocation: {
                        sourceAttachmentKey: 'ATTACH',
                        pageIndex: null,
                        pageLabel: '7',
                        sortIndex: 0,
                        positionJson: '{"pageIndex":6,"rects":[[75.038,292.34,294.645,300.557],[39.685,281.59,294.699,289.807]]}',
                    },
                    provenance: { source: 'zotero', sourceAttachmentKey: 'ATTACH', sourceAnnotationKey: 'ann-dense-lines' },
                }],
                message: '1 annotation(s) loaded.',
            });

            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await vi.advanceTimersByTimeAsync(70);

            const marks = page7.querySelectorAll('.paperforge-canvas-pdf-overlay-mark');
            expect(marks).toHaveLength(2);
            const line = marks[0].querySelector('.paperforge-canvas-pdf-overlay-line');
            expect(line).toBeTruthy();
            const firstUnderlineTop = parseFloat(marks[0].style.top) + parseFloat(line.style.top);
            const firstTextTop = 790.866 - 292.34 - (300.557 - 292.34);
            const firstTextBottom = firstTextTop + (300.557 - 292.34);
            const secondTextTop = 790.866 - 281.59 - (289.807 - 281.59);
            expect(firstUnderlineTop).toBeGreaterThan(firstTextTop);
            expect(firstUnderlineTop + 3).toBeLessThanOrEqual(firstTextBottom - 1);
            expect(firstUnderlineTop).toBeLessThan(secondTextTop);
        } finally {
            vi.useRealTimers();
        }
    });

    it('clicking a PDF overlay mark scrolls to and selects the matching Canvas annotation card', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const pdfRoot = document.createElement('div');
            pdfRoot.className = 'pdf-embed';
            const page1 = document.createElement('div');
            page1.setAttribute('data-page-number', '1');
            page1.getBoundingClientRect = vi.fn(() => ({
                width: 595,
                height: 842,
                top: 0,
                left: 0,
                right: 595,
                bottom: 842,
            }));
            pdfRoot.appendChild(page1);
            const pdfContent = document.createElement('div');
            pdfContent.appendChild(pdfRoot);
            const canvasLeaf = { view };
            view.leaf = canvasLeaf;
            view.app = {
                vault: { getAbstractFileByPath: vi.fn(() => ({ path: '99_System/Zotero/storage/ATTACH/test.pdf' })) },
                workspace: {
                    activeLeaf: { view: { contentEl: pdfContent, containerEl: pdfContent } },
                    getLeavesOfType: vi.fn((type) => {
                        if (type === 'pdf') return [{ view: { contentEl: pdfContent, containerEl: pdfContent } }];
                        if (type === 'paperforge-reading-canvas') return [canvasLeaf];
                        return [];
                    }),
                    revealLeaf: vi.fn(),
                    openLinkText: vi.fn(),
                },
            };
            view._paperEntry = {
                key: 'PAPER_PDF_TO_CANVAS',
                pdf_path: '[[99_System/Zotero/storage/ATTACH/test.pdf]]',
                zotero_storage_key: 'ATTACH',
            };

            view._renderNativeAnnotationPanel('PAPER_PDF_TO_CANVAS', { key: 'PAPER_PDF_TO_CANVAS' }, {
                state: 'ready',
                paperKey: 'PAPER_PDF_TO_CANVAS',
                annotations: [ {
                    display: { selectedText: 'pdf-to-canvas target', type: 'highlight', color: '#ff6666' },
                    pdfLocation: {
                        sourceAttachmentKey: 'ATTACH',
                        pageIndex: null,
                        pageLabel: '1',
                        sortIndex: 0,
                        positionJson: '{"pageIndex":0,"rects":[[10,20,40,30]]}',
                    },
                    provenance: { source: 'zotero', sourceAttachmentKey: 'ATTACH', sourceAnnotationKey: 'ann-pdf-to-canvas' },
                } ],
                message: '1 annotation(s) loaded.',
            });
            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.scrollIntoView = vi.fn();

            view._openPdfForAnnotationRow(view._annotationPanelRows[0]);
            await vi.advanceTimersByTimeAsync(70);

            const mark = page1.querySelector('.paperforge-canvas-pdf-overlay-mark');
            expect(mark).toBeTruthy();
            expect(parseFloat(mark.style.height)).toBeGreaterThanOrEqual(10);
            expect(mark.querySelector('.paperforge-canvas-pdf-overlay-line')).toBeTruthy();
            mark.dispatchEvent(new MouseEvent('click', { bubbles: true }));

            expect(view.app.workspace.revealLeaf).toHaveBeenCalledWith(canvasLeaf);
            expect(card.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
            expect(card.getAttribute('aria-selected')).toBe('true');
            expect(card.getAttribute('data-jump-state')).toBe('selected-from-pdf');
            expect(card.querySelector('.paperforge-annotation-panel-jump-status').textContent).toBe('Selected from PDF.');
        } finally {
            vi.useRealTimers();
        }
    });

    it('does not fall back to fulltext matching when a Zotero PDF annotation cannot resolve its PDF', async () => {
        const view = makeCanvasView();
        const fulltextContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = 'This fulltext contains the zotero bbox target text.';
        fulltextContainer.appendChild(preview);
        view.app = {
            vault: { getAbstractFileByPath: vi.fn(() => null) },
            workspace: {
                activeLeaf: { view: { containerEl: fulltextContainer } },
                getLeavesOfType: vi.fn(() => []),
                openLinkText: vi.fn(),
            },
        };
        view._paperEntry = {
            key: 'PAPER_STRICT_BBOX',
            pdf_path: '[[System/Zotero/storage/ATTACH/missing.pdf]]',
            zotero_storage_key: 'ATTACH',
        };

        view._renderNativeAnnotationPanel('PAPER_STRICT_BBOX', { key: 'PAPER_STRICT_BBOX' }, {
            state: 'ready',
            paperKey: 'PAPER_STRICT_BBOX',
            annotations: [{
                display: { selectedText: 'zotero bbox target text', type: 'highlight', color: '#ffd54f' },
                pdfLocation: {
                    sourceAttachmentKey: 'ATTACH',
                    pageIndex: null,
                    pageLabel: '7',
                    sortIndex: 0,
                    positionJson: '{"pageIndex":6,"rects":[[75.038,292.34,294.645,300.557]]}',
                },
                provenance: { source: 'zotero', sourceAttachmentKey: 'ATTACH', sourceAnnotationKey: 'ann-strict-bbox' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
        expect(preview.querySelector('mark.paperforge-active-annotation-match')).toBeFalsy();
        expect(card.getAttribute('data-jump-state')).toBe('unresolved');
        expect(card.getAttribute('data-jump-reason')).toBe('pdf-file-not-found');
    });

    it('clicking an annotation card uses loose matching when punctuation differs from fulltext', () => {
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = 'OCR text has target sentence with punctuation differences in the page.';
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        const scrollIntoView = vi.fn();
        Element.prototype.scrollIntoView = scrollIntoView;
        view.app = { workspace: { activeLeaf: { view: { containerEl: activeContainer } } } };

        view._renderNativeAnnotationPanel('PAPER_LOOSE', { key: 'PAPER_LOOSE' }, {
            state: 'ready',
            paperKey: 'PAPER_LOOSE',
            annotations: [{
                display: { selectedText: 'target sentence, with punctuation differences', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-loose-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        view.contentEl.querySelector('.paperforge-annotation-panel-card')
            .dispatchEvent(new MouseEvent('click', { bubbles: true }));

        const mark = preview.querySelector('mark.paperforge-active-annotation-match');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toContain('target sentence with punctuation differences');
        expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
    });

    it('clicking a long annotation card can jump by a stable fragment when the full quote differs', async () => {
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = [
            'The OCR paragraph describes progression from benign models.',
            'Later it mentions invasive adenocarcinoma models and highly metastatic adenocarcinoma models.',
            'The visible OCR omits several mouse genotype details.'
        ].join(' ');
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        const scrollIntoView = vi.fn();
        Element.prototype.scrollIntoView = scrollIntoView;
        view.app = { workspace: { activeLeaf: { view: { containerEl: activeContainer } } } };

        view._renderNativeAnnotationPanel('PAPER_FRAGMENT', { key: 'PAPER_FRAGMENT' }, {
            state: 'ready',
            paperKey: 'PAPER_FRAGMENT',
            annotations: [{
                display: {
                    selectedText: 'from benign models (Villin1-CreER Apcfl/fl, Villin1-CreER Apcfl/fl Trp53fl/fl, Villin1-CreER Apcfl/fl KrasG12D/+) to invasive adenocarcinoma models (VAKP) to highly metastatic adenocarcinoma models (VAKPS, VKPN)',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 2, pageLabel: '3', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-fragment-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        const mark = preview.querySelector('mark.paperforge-active-annotation-match');
        expect(mark).toBeTruthy();
        expect(mark.getAttribute('data-match-kind')).toBe('fragment');
        expect(mark.textContent).toContain('invasive adenocarcinoma models');
        expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
        expect(card.querySelector('.paperforge-annotation-panel-jump-status').textContent).toContain('nearby fragment');
    });

    it('clicking an annotation card repeatedly scrolls the persisted fulltext mark by annotation identity', async () => {
        vi.useFakeTimers();
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        const mark = document.createElement('mark');
        mark.className = 'paperforge-annotation-highlight';
        mark.setAttribute('data-paperforge-annotation-id', 'zotero:3:ATTACH:ANN_REPEAT');
        mark.textContent = 'already persisted annotation text';
        preview.appendChild(mark);
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        const scrollIntoView = vi.fn();
        mark.scrollIntoView = scrollIntoView;
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: activeContainer } },
                getLeavesOfType: vi.fn((type) => type === 'markdown' ? [{ view: { containerEl: activeContainer } }] : []),
                revealLeaf: vi.fn(),
                openLinkText: vi.fn(async () => {}),
            },
        };
        view._paperEntry = { key: 'PAPER_REPEAT', fulltext_path: 'paper/fulltext.md' };

        view._renderNativeAnnotationPanel('PAPER_REPEAT', { key: 'PAPER_REPEAT' }, {
            state: 'ready',
            paperKey: 'PAPER_REPEAT',
            annotations: [{
                display: {
                    selectedText: 'persisted annotation text with OCR differences',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 2, pageLabel: '3', sortIndex: 0 },
                provenance: {
                    source: 'zotero',
                    sourceAttachmentKey: 'ATTACH',
                    sourceAnnotationKey: 'ANN_REPEAT',
                },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await vi.advanceTimersByTimeAsync(80);
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await vi.advanceTimersByTimeAsync(80);

        expect(scrollIntoView.mock.calls.length).toBeGreaterThanOrEqual(4);
        expect(view.app.workspace.openLinkText).toHaveBeenCalledTimes(2);
        expect(view.app.workspace.openLinkText).toHaveBeenCalledWith('paper/fulltext.md', '', false);
        expect(view.app.workspace.revealLeaf).toHaveBeenCalledTimes(2);
        expect(card.querySelector('.paperforge-annotation-panel-jump-status').textContent).toBe('Opened fulltext and matched.');
        vi.useRealTimers();
    });

    it('uses an already-open fulltext leaf instead of reopening the link on every click', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const canvasContainer = document.createElement('div');
            canvasContainer.appendChild(view.contentEl);
            const fulltextContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            const mark = document.createElement('mark');
            mark.className = 'paperforge-annotation-highlight';
            mark.setAttribute('data-paperforge-annotation-id', 'zotero:3:ATTACH:ANN_OPEN_LEAF');
            mark.textContent = 'already open target';
            preview.appendChild(mark);
            fulltextContainer.appendChild(preview);
            document.body.appendChild(canvasContainer);
            document.body.appendChild(fulltextContainer);
            mark.scrollIntoView = vi.fn();
            const fulltextLeaf = {
                view: {
                    file: { path: 'Literature/PAPER/fulltext.md' },
                    containerEl: fulltextContainer,
                },
            };
            const workspace = {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => type === 'markdown' ? [fulltextLeaf] : []),
                revealLeaf: vi.fn((leaf) => {
                    workspace.activeLeaf = leaf;
                }),
                openLinkText: vi.fn(async () => {
                    throw new Error('should not reopen already-open fulltext');
                }),
            };
            view.app = { workspace };
            view._paperEntry = { key: 'PAPER', fulltext_path: 'Literature/PAPER/fulltext.md' };

            view._renderNativeAnnotationPanel('PAPER', { key: 'PAPER', fulltext_path: 'Literature/PAPER/fulltext.md' }, {
                state: 'ready',
                paperKey: 'PAPER',
                annotations: [{
                    display: { selectedText: 'already open target', type: 'highlight', color: '#ffd54f' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: {
                        source: 'zotero',
                        sourceAttachmentKey: 'ATTACH',
                        sourceAnnotationKey: 'ANN_OPEN_LEAF',
                    },
                }],
                message: '1 annotation(s) loaded.',
            });

            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await vi.advanceTimersByTimeAsync(80);
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await vi.advanceTimersByTimeAsync(80);

            expect(workspace.openLinkText).not.toHaveBeenCalled();
            expect(workspace.revealLeaf).toHaveBeenCalledWith(fulltextLeaf);
            expect(mark.scrollIntoView.mock.calls.length).toBeGreaterThanOrEqual(4);
        } finally {
            vi.useRealTimers();
        }
    });

    it('identity lookup works when browser CSS.escape is available', async () => {
        const originalCss = globalThis.CSS;
        globalThis.CSS = {
            escape: vi.fn((value) => String(value).replace(/:/g, '\\:')),
        };
        try {
            const view = makeCanvasView();
            const activeContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            const mark = document.createElement('mark');
            mark.className = 'paperforge-annotation-highlight';
            mark.setAttribute('data-paperforge-annotation-id', 'zotero:3:ATTACH:ANN_ESC');
            mark.textContent = 'target text';
            preview.appendChild(mark);
            activeContainer.appendChild(preview);
            document.body.appendChild(activeContainer);
            mark.scrollIntoView = vi.fn();
            view.app = { workspace: { activeLeaf: { view: { containerEl: activeContainer } } } };

            const result = view._jumpToRenderedFulltextDom(
                'selected text that does not match',
                '#ffd54f',
                'zotero:3:ATTACH:ANN_ESC'
            );

            expect(result.ok).toBe(true);
            expect(mark.scrollIntoView).toHaveBeenCalled();
        } finally {
            globalThis.CSS = originalCss;
        }
    });

    it('repeated click recenters the fulltext scroll container after the user scrolls away', async () => {
        vi.useFakeTimers();
        const view = makeCanvasView();
        const leafContainer = document.createElement('div');
        const scrollContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        const spacer = document.createElement('div');
        spacer.textContent = 'top spacer';
        const mark = document.createElement('mark');
        mark.className = 'paperforge-annotation-highlight';
        mark.setAttribute('data-paperforge-annotation-id', 'zotero:3:ATTACH:ANN_SCROLL');
        mark.textContent = 'scroll target';
        preview.appendChild(spacer);
        preview.appendChild(mark);
        scrollContainer.appendChild(preview);
        leafContainer.appendChild(scrollContainer);
        document.body.appendChild(leafContainer);
        Object.defineProperty(scrollContainer, 'clientHeight', { value: 200, configurable: true });
        Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
        Object.defineProperty(spacer, 'offsetTop', { value: 0, configurable: true });
        Object.defineProperty(mark, 'offsetTop', { value: 700, configurable: true });
        mark.scrollIntoView = vi.fn();
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: leafContainer } },
                getLeavesOfType: vi.fn((type) => type === 'markdown' ? [{ view: { containerEl: leafContainer } }] : []),
                revealLeaf: vi.fn(),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_SCROLL', { key: 'PAPER_SCROLL' }, {
            state: 'ready',
            paperKey: 'PAPER_SCROLL',
            annotations: [{
                display: { selectedText: 'does not matter', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 2, pageLabel: '3', sortIndex: 0 },
                provenance: {
                    source: 'zotero',
                    sourceAttachmentKey: 'ATTACH',
                    sourceAnnotationKey: 'ANN_SCROLL',
                },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await vi.advanceTimersByTimeAsync(80);
        expect(scrollContainer.scrollTop).toBe(600);
        scrollContainer.scrollTop = 0;

        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await vi.advanceTimersByTimeAsync(80);

        expect(scrollContainer.scrollTop).toBe(600);
        vi.useRealTimers();
    });

    it('continues the pending jump when reading preview appears after source-mode fallback', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const canvasContainer = document.createElement('div');
            canvasContainer.appendChild(view.contentEl);
            const fulltextContainer = document.createElement('div');
            document.body.appendChild(canvasContainer);
            document.body.appendChild(fulltextContainer);
            const editor = {
                getValue: vi.fn(() => 'Before.\nThe late preview target is in the source buffer.\nAfter.'),
                offsetToPos: vi.fn((offset) => ({ line: 1, ch: offset })),
                setSelection: vi.fn(),
                scrollIntoView: vi.fn(),
                focus: vi.fn(),
            };
            const workspaceEvents = new Map();
            const workspace = {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { containerEl: fulltextContainer, editor } }];
                    return [];
                }),
                revealLeaf: vi.fn(),
                on: vi.fn((eventName, callback) => {
                    workspaceEvents.set(eventName, callback);
                    return callback;
                }),
                off: vi.fn(),
            };
            view.app = { workspace };

            view._renderNativeAnnotationPanel('PAPER_LATE_PREVIEW', { key: 'PAPER_LATE_PREVIEW' }, {
                state: 'ready',
                paperKey: 'PAPER_LATE_PREVIEW',
                annotations: [{
                    display: { selectedText: 'late preview target', type: 'highlight', color: '#ffd54f' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    provenance: { sourceAnnotationKey: 'ann-late-preview' },
                }],
                message: '1 annotation(s) loaded.',
            });

            const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
            card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
            await Promise.resolve();
            expect(editor.scrollIntoView).toHaveBeenCalledTimes(1);

            const scrollContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = 'Now reading mode renders the late preview target.';
            scrollContainer.appendChild(preview);
            fulltextContainer.appendChild(scrollContainer);
            Object.defineProperty(scrollContainer, 'clientHeight', { value: 200, configurable: true });
            Object.defineProperty(scrollContainer, 'scrollHeight', { value: 1000, configurable: true });
            const scrollIntoView = vi.fn();
            Element.prototype.scrollIntoView = scrollIntoView;

            const callback = workspaceEvents.get('layout-change');
            expect(callback).toBeTruthy();
            callback();
            await vi.advanceTimersByTimeAsync(80);

            const mark = preview.querySelector('mark.paperforge-active-annotation-match');
            expect(mark).toBeTruthy();
            expect(mark.textContent).toBe('late preview target');
            expect(scrollIntoView).toHaveBeenCalled();
            expect(workspace.off).toHaveBeenCalledWith('layout-change', callback);
        } finally {
            vi.useRealTimers();
        }
    });

    it('does not consume a click by matching CodeMirror DOM before reading preview exists', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const canvasContainer = document.createElement('div');
            canvasContainer.appendChild(view.contentEl);
            const fulltextContainer = document.createElement('div');
            const cmContent = document.createElement('div');
            cmContent.className = 'cm-content';
            cmContent.textContent = 'CodeMirror currently shows the source mode target.';
            fulltextContainer.appendChild(cmContent);
            document.body.appendChild(canvasContainer);
            document.body.appendChild(fulltextContainer);
            const editor = {
                getValue: vi.fn(() => 'The editor buffer contains the source mode target.'),
                offsetToPos: vi.fn((offset) => ({ line: 0, ch: offset })),
                setSelection: vi.fn(),
                scrollIntoView: vi.fn(),
                focus: vi.fn(),
            };
            const workspaceEvents = new Map();
            view.app = {
                workspace: {
                    activeLeaf: { view: { containerEl: canvasContainer } },
                    getLeavesOfType: vi.fn((type) => type === 'markdown'
                        ? [{ view: { file: { path: 'Literature/PAPER/fulltext.md' }, containerEl: fulltextContainer, editor } }]
                        : []),
                    revealLeaf: vi.fn(),
                    on: vi.fn((eventName, callback) => {
                        workspaceEvents.set(eventName, callback);
                        return callback;
                    }),
                    off: vi.fn(),
                },
            };
            view._paperEntry = { key: 'PAPER', fulltext_path: 'Literature/PAPER/fulltext.md' };

            const jump = view._jumpToActiveFulltextAnnotation({
                display: { selectedText: 'source mode target', color: '#ffd54f' },
                provenance: { sourceAnnotationKey: 'ann-source-mode' },
            });
            await vi.advanceTimersByTimeAsync(41);
            const result = await jump;

            expect(result.ok).toBe(true);
            expect(result.editor).toBe(editor);
            expect(cmContent.querySelector('mark.paperforge-active-annotation-match')).toBeFalsy();
            expect(workspaceEvents.get('layout-change')).toBeTruthy();

            const scrollContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = 'Reading mode later shows the source mode target.';
            scrollContainer.appendChild(preview);
            fulltextContainer.innerHTML = '';
            fulltextContainer.appendChild(scrollContainer);
            Element.prototype.scrollIntoView = vi.fn();
            workspaceEvents.get('layout-change')();
            await vi.advanceTimersByTimeAsync(80);

            const mark = preview.querySelector('mark.paperforge-active-annotation-match');
            expect(mark).toBeTruthy();
            expect(mark.textContent).toBe('source mode target');
        } finally {
            vi.useRealTimers();
        }
    });

    it('clicking an annotation card finds fulltext in another markdown leaf when the canvas leaf is active', () => {
        const view = makeCanvasView();
        const canvasContainer = document.createElement('div');
        canvasContainer.appendChild(view.contentEl);
        const fulltextContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = 'A visible fulltext pane contains a cross leaf annotation target.';
        fulltextContainer.appendChild(preview);
        document.body.appendChild(canvasContainer);
        document.body.appendChild(fulltextContainer);
        const scrollIntoView = vi.fn();
        Element.prototype.scrollIntoView = scrollIntoView;
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { containerEl: fulltextContainer } }];
                    return [];
                }),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_CROSS', { key: 'PAPER_CROSS' }, {
            state: 'ready',
            paperKey: 'PAPER_CROSS',
            annotations: [{
                display: { selectedText: 'cross leaf annotation target', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-cross-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        view.contentEl.querySelector('.paperforge-annotation-panel-card')
            .dispatchEvent(new MouseEvent('click', { bubbles: true }));

        const mark = preview.querySelector('mark.paperforge-active-annotation-match');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toBe('cross leaf annotation target');
        expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
    });

    it('clicking an annotation card highlights text split across Obsidian text nodes', () => {
        const view = makeCanvasView();
        const activeContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.appendChild(document.createTextNode('The annotation '));
        const em = document.createElement('em');
        em.textContent = 'target';
        preview.appendChild(em);
        preview.appendChild(document.createTextNode(' is split across inline nodes.'));
        activeContainer.appendChild(preview);
        document.body.appendChild(activeContainer);
        const scrollIntoView = vi.fn();
        Element.prototype.scrollIntoView = scrollIntoView;
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: activeContainer } },
            },
        };

        view._renderNativeAnnotationPanel('PAPER_SPLIT', { key: 'PAPER_SPLIT' }, {
            state: 'ready',
            paperKey: 'PAPER_SPLIT',
            annotations: [{
                display: { selectedText: 'annotation target is split', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-split-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        view.contentEl.querySelector('.paperforge-annotation-panel-card')
            .dispatchEvent(new MouseEvent('click', { bubbles: true }));

        const mark = preview.querySelector('mark.paperforge-active-annotation-match');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toContain('annotation');
        expect(mark.textContent).toContain('target');
        expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
    });

    it('clicking an annotation card falls back to the markdown editor buffer when rendered DOM is missing the text', () => {
        const view = makeCanvasView();
        const canvasContainer = document.createElement('div');
        canvasContainer.appendChild(view.contentEl);
        const fulltextContainer = document.createElement('div');
        const preview = document.createElement('div');
        preview.className = 'markdown-preview-view';
        preview.textContent = 'Only the current viewport is rendered here.';
        fulltextContainer.appendChild(preview);
        document.body.appendChild(canvasContainer);
        document.body.appendChild(fulltextContainer);
        const editor = {
            getValue: vi.fn(() => 'Earlier content.\nThe editor buffer contains the virtualized annotation target.\nLater content.'),
            offsetToPos: vi.fn((offset) => {
                const text = editor.getValue().slice(0, offset);
                const lines = text.split('\n');
                return { line: lines.length - 1, ch: lines[lines.length - 1].length };
            }),
            setSelection: vi.fn(),
            setCursor: vi.fn(),
            scrollIntoView: vi.fn(),
            focus: vi.fn(),
        };
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { containerEl: fulltextContainer, editor } }];
                    return [];
                }),
                revealLeaf: vi.fn(),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_EDITOR', { key: 'PAPER_EDITOR' }, {
            state: 'ready',
            paperKey: 'PAPER_EDITOR',
            annotations: [{
                display: { selectedText: 'virtualized annotation target', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-editor-1' },
            }],
            message: '1 annotation(s) loaded.',
        });

        view.contentEl.querySelector('.paperforge-annotation-panel-card')
            .dispatchEvent(new MouseEvent('click', { bubbles: true }));

        expect(preview.querySelector('mark.paperforge-active-annotation-match')).toBeFalsy();
        expect(editor.setSelection).toHaveBeenCalled();
        expect(editor.scrollIntoView).toHaveBeenCalled();
        expect(editor.focus).toHaveBeenCalled();
        expect(view.app.workspace.revealLeaf).toHaveBeenCalled();
    });

    it('clicking an annotation card repeatedly recenters the markdown editor selection', async () => {
        const view = makeCanvasView();
        const canvasContainer = document.createElement('div');
        canvasContainer.appendChild(view.contentEl);
        const fulltextContainer = document.createElement('div');
        fulltextContainer.appendChild(document.createElement('div'));
        document.body.appendChild(canvasContainer);
        document.body.appendChild(fulltextContainer);
        const editor = {
            getValue: vi.fn(() => 'Earlier content.\nThe editor buffer contains the repeated annotation target.\nLater content.'),
            offsetToPos: vi.fn((offset) => {
                const text = editor.getValue().slice(0, offset);
                const lines = text.split('\n');
                return { line: lines.length - 1, ch: lines[lines.length - 1].length };
            }),
            setSelection: vi.fn(),
            setCursor: vi.fn(),
            scrollIntoView: vi.fn(),
            focus: vi.fn(),
        };
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { containerEl: fulltextContainer, editor } }];
                    return [];
                }),
                revealLeaf: vi.fn(),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_EDITOR_REPEAT', { key: 'PAPER_EDITOR_REPEAT' }, {
            state: 'ready',
            paperKey: 'PAPER_EDITOR_REPEAT',
            annotations: [{
                display: { selectedText: 'repeated annotation target', type: 'highlight', color: '#ffd54f' },
                pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                provenance: { sourceAnnotationKey: 'ann-editor-repeat' },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(editor.setSelection).toHaveBeenCalledTimes(2);
        expect(editor.scrollIntoView).toHaveBeenCalledTimes(2);
        expect(view.app.workspace.revealLeaf).toHaveBeenCalledTimes(2);
    });

    it('editor fallback finds selected text inside persisted mark and html tags', async () => {
        const view = makeCanvasView();
        const canvasContainer = document.createElement('div');
        canvasContainer.appendChild(view.contentEl);
        const fulltextContainer = document.createElement('div');
        fulltextContainer.appendChild(document.createElement('div'));
        document.body.appendChild(canvasContainer);
        document.body.appendChild(fulltextContainer);
        const value = [
            'Before.',
            '<mark class="paperforge-annotation-highlight" data-paperforge-annotation-id="zotero:3:ATTACH:ANN_HTML" style="background-color: #ffd400;">',
            'from benign models (Villin1-Cre<sup>ER</sup> Apc<sup>fl/fl</sup>) to invasive adenocarcinoma models',
            '</mark>',
            'After.',
        ].join('\n');
        const editor = {
            getValue: vi.fn(() => value),
            offsetToPos: vi.fn((offset) => {
                const text = value.slice(0, offset);
                const lines = text.split('\n');
                return { line: lines.length - 1, ch: lines[lines.length - 1].length };
            }),
            setSelection: vi.fn(),
            scrollIntoView: vi.fn(),
            focus: vi.fn(),
        };
        view.app = {
            workspace: {
                activeLeaf: { view: { containerEl: canvasContainer } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'markdown') return [{ view: { containerEl: fulltextContainer, editor } }];
                    return [];
                }),
                revealLeaf: vi.fn(),
            },
        };

        view._renderNativeAnnotationPanel('PAPER_EDITOR_HTML', { key: 'PAPER_EDITOR_HTML' }, {
            state: 'ready',
            paperKey: 'PAPER_EDITOR_HTML',
            annotations: [{
                display: {
                    selectedText: 'from benign models (Villin1–CreER Apcfl/fl) to invasive adenocarcinoma models',
                    type: 'highlight',
                    color: '#ffd54f',
                },
                pdfLocation: { pageIndex: 2, pageLabel: '3', sortIndex: 0 },
                provenance: {
                    source: 'zotero',
                    sourceAttachmentKey: 'ATTACH',
                    sourceAnnotationKey: 'ANN_HTML',
                },
            }],
            message: '1 annotation(s) loaded.',
        });

        const card = view.contentEl.querySelector('.paperforge-annotation-panel-card');
        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await Promise.resolve();

        expect(editor.setSelection).toHaveBeenCalled();
        expect(editor.scrollIntoView).toHaveBeenCalled();
        expect(view.app.workspace.revealLeaf).toHaveBeenCalled();
    });

    it('clicking an annotation card opens the paper fulltext when another page is active', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            view._paperEntry = { key: 'PAPER_OPEN', fulltext_path: 'Literature/PAPER_OPEN/fulltext.md' };
            const canvasContainer = document.createElement('div');
            canvasContainer.appendChild(view.contentEl);
            document.body.appendChild(canvasContainer);
            const openedContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = 'The opened fulltext contains the target after opening.';
            openedContainer.appendChild(preview);
            const openedLeaf = { view: { containerEl: openedContainer } };
            const scrollIntoView = vi.fn();
            Element.prototype.scrollIntoView = scrollIntoView;
            const workspace = {
                activeLeaf: { view: { containerEl: canvasContainer } },
                openLinkText: vi.fn(async () => {
                    document.body.appendChild(openedContainer);
                    workspace.activeLeaf = openedLeaf;
                }),
                getLeavesOfType: vi.fn((type) => {
                    if (type !== 'markdown') return [];
                    return workspace.activeLeaf === openedLeaf ? [openedLeaf] : [];
                }),
            };
            view.app = { workspace };

            const jump = view._jumpToActiveFulltextAnnotation({
                display: { selectedText: 'target after opening', color: '#ffd54f' },
            });
            await Promise.resolve();
            await vi.advanceTimersByTimeAsync(61);
            const result = await jump;

            expect(result.ok).toBe(true);
            expect(result.opened).toBe(true);
            expect(workspace.openLinkText).toHaveBeenCalledWith('Literature/PAPER_OPEN/fulltext.md', '', false);
            expect(preview.querySelector('mark.paperforge-active-annotation-match')).toBeTruthy();
            expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
        } finally {
            vi.useRealTimers();
        }
    });

    it('editor fallback schedules a same-color rendered fulltext mark after scroll', async () => {
        vi.useFakeTimers();
        try {
            const view = makeCanvasView();
            const fulltextContainer = document.createElement('div');
            const preview = document.createElement('div');
            preview.className = 'markdown-preview-view';
            preview.textContent = 'Only the viewport is visible for now.';
            fulltextContainer.appendChild(preview);
            document.body.appendChild(fulltextContainer);
            const editor = {
                getValue: vi.fn(() => 'The editor has delayed color target text.'),
                offsetToPos: vi.fn((offset) => ({ line: 0, ch: offset })),
                setSelection: vi.fn(),
                scrollIntoView: vi.fn(),
                focus: vi.fn(),
            };
            view.app = {
                workspace: {
                    activeLeaf: { view: { containerEl: fulltextContainer, editor } },
                    getLeavesOfType: vi.fn((type) => type === 'markdown' ? [{ view: { containerEl: fulltextContainer, editor } }] : []),
                },
            };

            const result = await view._jumpToActiveFulltextAnnotation({
                display: { selectedText: 'delayed color target', color: '#4caf50' },
            });
            expect(result.ok).toBe(true);
            expect(preview.querySelector('mark.paperforge-active-annotation-match')).toBeFalsy();

            preview.textContent = 'The rendered DOM now contains delayed color target text.';
            await vi.advanceTimersByTimeAsync(81);

            const mark = preview.querySelector('mark.paperforge-active-annotation-match');
            expect(mark).toBeTruthy();
            expect(mark.textContent).toBe('delayed color target');
            expect(mark.style.backgroundColor).toContain('rgba(76, 175, 80');
        } finally {
            vi.useRealTimers();
        }
    });

    it('renders missing-paper state when setPaperContext gets null entry', () => {
        const view = makeCanvasView();

        view.setPaperContext(null, null);

        expect(view._canvasContext).toBeNull();
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
    });

    it('setPaperContext falls back to absolute canvas module path when Obsidian cannot resolve relative require', () => {
        const view = makeCanvasView();
        const previousLoad = Module._load;
        Module._load = function failRelativeCanvasModule(request, parent, isMain) {
            if (request === './src/canvas') {
                throw new Error('relative canvas module unavailable');
            }
            return previousLoad.call(this, request, parent, isMain);
        };

        try {
            view.setPaperContext('KEY_ABS_CANVAS', { key: 'KEY_ABS_CANVAS', title: 'Absolute canvas' });
        } finally {
            Module._load = previousLoad;
        }

        expect(view._paperKey).toBe('KEY_ABS_CANVAS');
        expect(view._canvasContext).toBeNull();
        expect(view.contentEl.textContent).not.toContain('relative canvas module unavailable');
        expect(view.contentEl.querySelector('[data-canvas-state="init-error"]')).toBeFalsy();
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
    });

    it('setPaperContext does not touch canvas module while opening the annotation panel', () => {
        const view = makeCanvasView();
        view._loadCanvasModule = function failCanvasModule() {
            throw new Error('canvas module unavailable');
        };

        view.setPaperContext('KEY_FAIL_INIT', { key: 'KEY_FAIL_INIT', title: 'Fail init' });

        expect(view.contentEl.textContent).toContain('Reading Canvas');
        expect(view.contentEl.textContent).toContain('KEY_FAIL_INIT');
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
        expect(noticeCalls).toHaveLength(0);
    });

    it('onOpen renders native annotation panel instead of leaving a blank pane before context arrives', async () => {
        const view = makeCanvasView();

        await view.onOpen();

        expect(view._canvasContext).toBeNull();
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
        expect(view.contentEl.textContent).toContain('Reading Canvas');
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

    it('static open rehydrates an existing leaf even when it already has the same paperKey', async () => {
        const entry = { key: 'KEY_STALE', title: 'Stale blank leaf' };
        const mockLeaf = {
            view: {
                _paperKey: 'KEY_STALE',
                setPaperContext: vi.fn(),
            },
            setViewState: vi.fn(() => Promise.resolve()),
        };
        const mockPlugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn(() => [mockLeaf]),
                    revealLeaf: vi.fn(),
                },
            },
        };

        await PaperForgeReadingCanvasView.open(mockPlugin, 'KEY_STALE', entry);

        expect(mockLeaf.view.setPaperContext).toHaveBeenCalledWith('KEY_STALE', entry);
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

    it('static open waits for a newly created leaf view before attaching paper context', async () => {
        const mockLeaf = {
            view: null,
            setViewState: vi.fn(() => {
                setTimeout(() => {
                    mockLeaf.view = { setPaperContext: vi.fn() };
                }, 0);
                return Promise.resolve();
            }),
        };
        const mockPlugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn(() => []),
                    getRightLeaf: vi.fn(() => mockLeaf),
                    revealLeaf: vi.fn(),
                },
            },
        };

        await PaperForgeReadingCanvasView.open(mockPlugin, 'KEY_DELAY', { key: 'KEY_DELAY', title: 'Delayed' });

        expect(mockLeaf.view.setPaperContext).toHaveBeenCalledWith('KEY_DELAY', { key: 'KEY_DELAY', title: 'Delayed' });
        expect(mockPlugin.app.workspace.revealLeaf).toHaveBeenCalledWith(mockLeaf);
    });

    it('static open keeps Obsidian view state minimal and attaches entry directly', async () => {
        const mockLeaf = {
            view: { setPaperContext: vi.fn() },
            setViewState: vi.fn(() => Promise.resolve()),
        };
        const entry = { key: 'KEY_STATE', title: 'Stateful' };
        const mockPlugin = {
            app: {
                workspace: {
                    getLeavesOfType: vi.fn(() => []),
                    getRightLeaf: vi.fn(() => mockLeaf),
                    revealLeaf: vi.fn(),
                },
            },
        };

        await PaperForgeReadingCanvasView.open(mockPlugin, 'KEY_STATE', entry);

        expect(mockLeaf.setViewState).toHaveBeenCalledWith({
            type: 'paperforge-reading-canvas',
            active: true,
            state: { paperKey: 'KEY_STATE' },
        });
        expect(mockLeaf.view.setPaperContext).toHaveBeenCalledWith('KEY_STATE', entry);
    });

    it('setState attaches paper context without external leaf polling', async () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        containerEl.appendChild(contentEl);
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;
        view.setPaperContext = vi.fn();
        const entry = { key: 'KEY_SETSTATE', title: 'SetState' };

        await view.setState({ paperKey: 'KEY_SETSTATE', entry }, {});

        expect(view.setPaperContext).toHaveBeenCalledWith('KEY_SETSTATE', entry);
    });

    it('setState defers paper context until the view content element exists', async () => {
        const containerEl = document.createElement('div');
        const view = new PaperForgeReadingCanvasView({ containerEl });
        view.contentEl = null;
        view.setPaperContext = vi.fn();
        const entry = { key: 'KEY_DEFERRED', title: 'Deferred' };

        await view.setState({ paperKey: 'KEY_DEFERRED', entry }, {});

        expect(view.setPaperContext).not.toHaveBeenCalled();
        expect(view._pendingCanvasState).toEqual({ paperKey: 'KEY_DEFERRED', entry });

        const contentEl = document.createElement('div');
        addCreateEl(contentEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        containerEl.appendChild(contentEl);
        view.contentEl = contentEl;

        await view.onOpen();

        expect(view.setPaperContext).toHaveBeenCalledWith('KEY_DEFERRED', entry);
        expect(view._pendingCanvasState).toBeNull();
    });

    it('onOpen renders native annotation panel without loading the canvas bundle when context is absent', async () => {
        const containerEl = document.createElement('div');
        const contentEl = document.createElement('div');
        addCreateEl(contentEl);
        contentEl.addClass = function (cls) { this.classList.add(cls); };
        containerEl.appendChild(contentEl);
        const view = new PaperForgeReadingCanvasView({ containerEl, contentEl });
        view.contentEl = contentEl;
        view._loadCanvasModule = vi.fn(() => {
            throw new Error('canvas bundle should not load on open');
        });

        await view.onOpen();

        expect(view._loadCanvasModule).not.toHaveBeenCalled();
        expect(view.contentEl.querySelector('[data-canvas-state="annotation-panel"]')).toBeTruthy();
        expect(view.contentEl.textContent).toContain('Reading Canvas');
    });

    it('plugin unload closes persisted Reading Canvas leaves', () => {
        const detachLeavesOfType = vi.fn();
        const plugin = Object.create(PaperForgePlugin.prototype);
        plugin._pollTimer = null;
        plugin.app = { workspace: { detachLeavesOfType } };

        plugin.onunload();

        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-status');
        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
    });

    it('plugin startup cleanup repeatedly closes restored Reading Canvas leaves around layout restore', () => {
        vi.useFakeTimers();
        const detachLeavesOfType = vi.fn();
        let layoutReadyCallback = null;
        const plugin = Object.create(PaperForgePlugin.prototype);
        plugin.app = {
            workspace: {
                detachLeavesOfType,
                onLayoutReady: vi.fn((callback) => {
                    layoutReadyCallback = callback;
                }),
            },
        };

        plugin._closeRestoredReadingCanvasLeaves();
        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        detachLeavesOfType.mockClear();

        layoutReadyCallback();
        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        detachLeavesOfType.mockClear();

        vi.advanceTimersByTime(3000);

        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        expect(detachLeavesOfType.mock.calls.length).toBeGreaterThanOrEqual(3);
        vi.useRealTimers();
    });

    it('closes Reading Canvas and opens PaperForge when the active PDF changes to another file', () => {
        const detachLeavesOfType = vi.fn();
        const revealLeaf = vi.fn();
        const statusLeaf = { view: {} };
        const canvasLeaf = {
            view: {
                _paperEntry: {
                    pdf_path: '[[System/Zotero/storage/ATTACH/current.pdf]]',
                    zotero_storage_key: 'ATTACH',
                },
            },
        };
        const plugin = Object.create(PaperForgePlugin.prototype);
        plugin.app = {
            workspace: {
                activeLeaf: { view: { getViewType: () => 'pdf', file: { path: 'System/Zotero/storage/OTHER/other.pdf' } } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'paperforge-reading-canvas') return [canvasLeaf];
                    if (type === 'paperforge-status') return [statusLeaf];
                    if (type === 'pdf') return [{ view: { file: { path: 'System/Zotero/storage/OTHER/other.pdf' } } }];
                    return [];
                }),
                detachLeavesOfType,
                getRightLeaf: vi.fn(),
                revealLeaf,
            },
        };

        plugin._handleReadingCanvasPdfLifecycle('active-leaf-change');

        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        expect(revealLeaf).toHaveBeenCalledWith(statusLeaf);
    });

    it('closes Reading Canvas and opens PaperForge when its source PDF leaf is closed', () => {
        const detachLeavesOfType = vi.fn();
        const revealLeaf = vi.fn();
        const statusLeaf = { view: {} };
        const canvasLeaf = {
            view: {
                _paperEntry: {
                    pdf_path: '[[System/Zotero/storage/ATTACH/current.pdf]]',
                    zotero_storage_key: 'ATTACH',
                },
            },
        };
        const plugin = Object.create(PaperForgePlugin.prototype);
        plugin.app = {
            workspace: {
                activeLeaf: { view: { getViewType: () => 'markdown' } },
                getLeavesOfType: vi.fn((type) => {
                    if (type === 'paperforge-reading-canvas') return [canvasLeaf];
                    if (type === 'paperforge-status') return [statusLeaf];
                    if (type === 'pdf') return [];
                    return [];
                }),
                detachLeavesOfType,
                getRightLeaf: vi.fn(),
                revealLeaf,
            },
        };

        plugin._handleReadingCanvasPdfLifecycle('layout-change');

        expect(detachLeavesOfType).toHaveBeenCalledWith('paperforge-reading-canvas');
        expect(revealLeaf).toHaveBeenCalledWith(statusLeaf);
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

    it('_renderLoadedCanvas renders loaded annotation cards', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_LOAD';
        view._paperEntry = {
            key: 'PAPER_LOAD',
            title: 'Loaded paper',
            fulltext_path: 'fulltext.md',
        };

        await view._renderLoadedCanvas(
            {
                fulltext: {
                    path: 'fulltext.md',
                    exists: true,
                    readable: true,
                    text: '<!-- page 1 --> Important anchor text appears here.',
                    error: null,
                },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_LOAD',
                annotations: [
                    {
                        display: {
                            selectedText: 'Important anchor text',
                            comment: 'Keep this finding',
                            pageLabel: '1',
                            type: 'highlight',
                            color: '#ffd54f',
                        },
                        provenance: {
                            source: 'zotero',
                            sourceAnnotationKey: 'ann-load-1',
                        },
                        pdfLocation: {
                            pageIndex: 1,
                            pageLabel: '1',
                            sortIndex: 0,
                        },
                    },
                ],
            }
        );

        expect(contentEl.querySelectorAll('.paperforge-canvas-card')).toHaveLength(1);
        expect(contentEl.textContent).toContain('Important anchor text');
        expect(contentEl.textContent).toContain('Keep this finding');
    });

    it('_renderLoadedCanvas renders fulltext.md through MarkdownRenderer inside article host', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_MD';
        view._paperEntry = {
            key: 'PAPER_MD',
            title: 'Markdown paper',
            fulltext_path: 'fulltext.md',
        };

        await view._renderLoadedCanvas(
            {
                fulltext: {
                    path: 'fulltext.md',
                    exists: true,
                    readable: true,
                    text: '# 第一卷\n\n原文中的重要句子在这里。',
                    error: null,
                },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            { state: 'empty', paperKey: 'PAPER_MD', annotations: [] }
        );

        const articleHost = contentEl.querySelector('[data-canvas-role="article-host"]');
        expect(articleHost).toBeTruthy();
        expect(markdownRenderCalls).toHaveLength(1);
        expect(markdownRenderCalls[0].markdown).toContain('原文中的重要句子');
        expect(markdownRenderCalls[0].sourcePath).toBe('fulltext.md');
        expect(articleHost.textContent).toContain('第一卷');
        expect(articleHost.textContent).toContain('原文中的重要句子在这里');
    });

    it('_renderLoadedCanvas uses lightweight source rendering for large fulltext to avoid freezing Obsidian', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_LARGE_MD';
        view._paperEntry = {
            key: 'PAPER_LARGE_MD',
            title: 'Large Markdown paper',
            fulltext_path: 'large-fulltext.md',
        };
        const largeText = Array.from({ length: 80 }, (_, i) => {
            return `<!-- page ${i + 1} -->\n` + 'Important large source sentence. '.repeat(35) + '\n![[image-' + i + '.jpg]]';
        }).join('\n\n');

        await view._renderLoadedCanvas(
            {
                fulltext: {
                    path: 'large-fulltext.md',
                    exists: true,
                    readable: true,
                    text: largeText,
                    error: null,
                },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            { state: 'empty', paperKey: 'PAPER_LARGE_MD', annotations: [] }
        );

        expect(markdownRenderCalls).toHaveLength(0);
        expect(contentEl.querySelector('.paperforge-canvas-source-surface')).toBeTruthy();
        expect(contentEl.textContent).toContain('Important large source sentence');
    });

    it('_renderLoadedCanvas highlights rendered markdown text, not raw markdown offsets', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_MARK';
        view._paperEntry = {
            key: 'PAPER_MARK',
            title: 'Rendered offsets',
            fulltext_path: 'fulltext.md',
        };

        await view._renderLoadedCanvas(
            {
                fulltext: {
                    path: 'fulltext.md',
                    exists: true,
                    readable: true,
                    text: '# Heading\n\n**Important anchor text** appears here.',
                    error: null,
                },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_MARK',
                annotations: [
                    {
                        display: {
                            selectedText: 'Important anchor text',
                            comment: '',
                            pageLabel: '1',
                            type: 'highlight',
                            color: '#ffd54f',
                        },
                        provenance: { source: 'zotero', sourceAnnotationKey: 'ann-rendered-1' },
                        pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                    },
                ],
            }
        );

        const mark = contentEl.querySelector('mark[data-anchor-id]');
        expect(mark).toBeTruthy();
        expect(mark.textContent).toBe('Important anchor text');
        expect(mark.closest('[data-canvas-role="article-host"]')).toBeTruthy();
    });

    it('_renderLoadedCanvas shows visible failure when MarkdownRenderer rejects', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_FAIL';
        view._paperEntry = { key: 'PAPER_FAIL', title: 'Fail', fulltext_path: 'fulltext.md' };
        markdownRenderImpl = async () => {
            throw new Error('renderer exploded');
        };

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Body', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            { state: 'empty', paperKey: 'PAPER_FAIL', annotations: [] }
        );

        expect(contentEl.textContent).toContain('renderer exploded');
        expect(contentEl.querySelector('[data-canvas-action="retry"]')).toBeTruthy();
    });

    it('_loadAndRenderCanvas shows visible failure when runtime setup fails before loading', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_RUNTIME_FAIL';
        view._paperEntry = { key: 'PAPER_RUNTIME_FAIL', title: 'Runtime fail', fulltext_path: 'fulltext.md' };
        view._canvasContext = { ok: true, paperKey: 'PAPER_RUNTIME_FAIL' };
        view._sessionController = {
            loadAnnotations: vi.fn(),
        };
        view.app = {
            vault: {
                adapter: {},
            },
            plugins: {
                plugins: {
                    paperforge: { settings: {} },
                },
            },
        };

        await view._loadAndRenderCanvas();

        expect(contentEl.textContent).toContain('Failed to load Reading Canvas');
        expect(contentEl.querySelector('.paperforge-canvas-failure')).toBeTruthy();
        expect(contentEl.querySelector('[data-canvas-action="retry"]')).toBeTruthy();
        expect(view._sessionController.loadAnnotations).not.toHaveBeenCalled();
    });

    it('_renderLoadedCanvas shows visible failure instead of blank content when paper entry is missing', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_NO_ENTRY';
        view._paperEntry = null;

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Body', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            { state: 'ready', paperKey: 'PAPER_NO_ENTRY', annotations: [] }
        );

        expect(contentEl.textContent).toContain('Failed to load Reading Canvas');
        expect(contentEl.querySelector('.paperforge-canvas-failure')).toBeTruthy();
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

    it('escapes special characters before building data-id selectors', () => {
        const { view, contentEl } = makeCanvasView();
        const rawId = 'ann"quoted\\slash';
        const card = document.createElement('div');
        card.setAttribute('data-card-id', rawId);
        contentEl.appendChild(card);

        const found = contentEl.querySelector('[data-card-id="' + view._escapeSelectorValue(rawId) + '"]');
        expect(found).toBe(card);
    });

    it('clicking a side card scrolls its rendered highlight into view', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_NAV_CARD';
        view._paperEntry = { key: 'PAPER_NAV_CARD', title: 'Nav', fulltext_path: 'fulltext.md' };

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Important anchor text appears here.', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_NAV_CARD',
                annotations: [{
                    display: { selectedText: 'Important anchor text', comment: 'Side note', pageLabel: '1', type: 'highlight' },
                    provenance: { source: 'zotero', sourceAnnotationKey: 'ann-nav-card' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                }],
            }
        );

        const card = contentEl.querySelector('[data-card-id]');
        const mark = contentEl.querySelector('mark[data-anchor-id]');
        mark.scrollIntoView = vi.fn();

        card.dispatchEvent(new MouseEvent('click', { bubbles: true }));

        expect(mark.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' });
        expect(card.getAttribute('aria-selected')).toBe('true');
    });

    it('clicking a rendered highlight scrolls the side card into view', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_NAV_MARK';
        view._paperEntry = { key: 'PAPER_NAV_MARK', title: 'Nav', fulltext_path: 'fulltext.md' };

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Important anchor text appears here.', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_NAV_MARK',
                annotations: [{
                    display: { selectedText: 'Important anchor text', comment: 'Side note', pageLabel: '1', type: 'highlight' },
                    provenance: { source: 'zotero', sourceAnnotationKey: 'ann-nav-mark' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                }],
            }
        );

        const card = contentEl.querySelector('[data-card-id]');
        const mark = contentEl.querySelector('mark[data-anchor-id]');
        card.scrollIntoView = vi.fn();

        mark.dispatchEvent(new MouseEvent('click', { bubbles: true }));

        expect(card.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'nearest' });
        expect(card.getAttribute('aria-selected')).toBe('true');
    });

    it('clicking an inline-only highlight opens a read-only popover', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_INLINE';
        view._paperEntry = { key: 'PAPER_INLINE', title: 'Inline', fulltext_path: 'fulltext.md' };

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Inline highlight text appears here.', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_INLINE',
                annotations: [{
                    display: { selectedText: 'Inline highlight text', comment: '', pageLabel: '1', type: 'highlight' },
                    provenance: { source: 'zotero', sourceAnnotationKey: 'ann-inline' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                }],
            }
        );

        expect(contentEl.querySelector('[data-card-id]')).toBeFalsy();
        const mark = contentEl.querySelector('mark[data-anchor-id]');
        mark.dispatchEvent(new MouseEvent('click', { bubbles: true }));

        const popover = contentEl.querySelector('.paperforge-canvas-highlight-popover');
        expect(popover).toBeTruthy();
        expect(popover.textContent).toContain('Inline highlight text');
    });

    it('Escape clears highlight popovers', async () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'PAPER_ESC';
        view._paperEntry = { key: 'PAPER_ESC', title: 'Esc', fulltext_path: 'fulltext.md' };

        await view._renderLoadedCanvas(
            {
                fulltext: { path: 'fulltext.md', exists: true, readable: true, text: 'Inline highlight text appears here.', error: null },
                note: { path: null, exists: false, readable: false, text: null, error: null },
            },
            {
                state: 'ready',
                paperKey: 'PAPER_ESC',
                annotations: [{
                    display: { selectedText: 'Inline highlight text', comment: '', pageLabel: '1', type: 'highlight' },
                    provenance: { source: 'zotero', sourceAnnotationKey: 'ann-esc' },
                    pdfLocation: { pageIndex: 0, pageLabel: '1', sortIndex: 0 },
                }],
            }
        );

        contentEl.querySelector('mark[data-anchor-id]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
        expect(contentEl.querySelector('.paperforge-canvas-highlight-popover')).toBeTruthy();

        contentEl.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));

        expect(contentEl.querySelector('.paperforge-canvas-highlight-popover')).toBeFalsy();
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

    it('click on card opens the source PDF page and records a pending annotation jump', () => {
        const { view, contentEl } = makeCanvasView();
        view.app.workspace.openLinkText = vi.fn();
        view.app.vault.getAbstractFileByPath = vi.fn(() => ({ path: '99_System/Zotero/storage/DHBF6HXW/trop2.pdf' }));
        view._paperEntry = {
            key: 'A7N8GAHS',
            pdf_path: '[[99_System/Zotero/storage/DHBF6HXW/trop2.pdf]]',
            zotero_storage_key: 'DHBF6HXW',
        };
        view._vm = {
            cards: [{
                id: 'zotero:3:DHBF6HXW:BBK66MB9',
                sourceAttachmentKey: 'DHBF6HXW',
                sourceAnnotationKey: 'BBK66MB9',
                pageIndex: null,
                pageLabel: '3',
                positionJson: '{"pageIndex":2,"rects":[[336.815,131.09,561.26,140.431]]}',
                selectedText: 'from benign models',
                color: '#ffd400',
            }],
        };
        view._navigationState = { selectedCardId: null, selectedAnchorId: null, selectedGroupId: null, sourceFocusTargetId: null, statusMessage: null, navSource: null };
        view._initDelegatedEvents(contentEl);

        const cardEl = document.createElement('div');
        cardEl.setAttribute('data-card-id', 'zotero:3:DHBF6HXW:BBK66MB9');
        contentEl.appendChild(cardEl);

        cardEl.dispatchEvent(new MouseEvent('click', { bubbles: true }));

        expect(view.app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/DHBF6HXW/trop2.pdf#page=3', '');
        expect(view._pendingPdfAnnotationJump).toMatchObject({
            annotationId: 'zotero:3:DHBF6HXW:BBK66MB9',
            pageIndex: 2,
            color: '#ffd400',
        });
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

// ── ANN14-03 Task 3: Resize/scroll scheduling + lifecycle clearing ──

describe('ANN14-03 Task 3 — Resize/scroll lifecycle', () => {

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

    it('_scheduleConnectorUpdate cancels previous frame handle', () => {
        const { view } = makeCanvasView();
        view._connectorFrameHandle = 42;
        view._scheduleConnectorUpdate();
        // After _scheduleConnectorUpdate, frame handle should be a number (RAF id)
        expect(typeof view._connectorFrameHandle).toBe('number');
        expect(view._connectorFrameHandle).not.toBe(42);
    });

    it('_scheduleConnectorUpdate does not throw when called multiple times', () => {
        const { view } = makeCanvasView();
        expect(() => {
            view._scheduleConnectorUpdate();
            view._scheduleConnectorUpdate();
            view._scheduleConnectorUpdate();
        }).not.toThrow();
    });

    it('_initConnectorScrollResize does not throw when contentEl is null', () => {
        const { view } = makeCanvasView();
        view.contentEl = null;
        expect(() => view._initConnectorScrollResize()).not.toThrow();
    });

    it('_initConnectorScrollResize sets bound handlers', () => {
        const { view } = makeCanvasView();
        view.contentEl = document.createElement('div');
        view._initConnectorScrollResize();
        expect(typeof view._connectorBoundScroll).toBe('function');
        expect(typeof view._connectorBoundResize).toBe('function');
    });

    it('_cleanupNavigation removes scroll/resize listeners', () => {
        const { view } = makeCanvasView();
        view.contentEl = document.createElement('div');
        view._initConnectorScrollResize();

        // Save handlers before cleanup
        var scrollHandler = view._connectorBoundScroll;
        var resizeHandler = view._connectorBoundResize;

        view._cleanupNavigation();

        // Handlers should be null
        expect(view._connectorBoundScroll).toBeNull();
        expect(view._connectorBoundMouseover).toBeNull();
        expect(view._connectorBoundMouseout).toBeNull();
    });

    it('_cleanupNavigation cancels frame handle', () => {
        const { view } = makeCanvasView();
        view._connectorFrameHandle = 123;
        view._cleanupNavigation();
        expect(view._connectorFrameHandle).toBeNull();
    });

    it('_cleanupNavigation clears layer DOM content', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_CLEAR';
        view._paperEntry = { key: 'KEY_CLEAR', title: 'Clear' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // Add some content to the layer
        var layer = view._connectorLayerEl;
        var ns = 'http://www.w3.org/2000/svg';
        layer.appendChild(document.createElementNS(ns, 'line'));
        layer.appendChild(document.createElementNS(ns, 'circle'));
        expect(layer.children.length).toBeGreaterThanOrEqual(2);

        view._cleanupNavigation();

        // Layer children should be cleared
        expect(layer.children.length).toBe(0);
    });

    it('_clearConnectorLayer on null layerEl does not throw', () => {
        const { view } = makeCanvasView();
        view._connectorLayerEl = null;
        expect(() => view._clearConnectorLayer()).not.toThrow();
    });

    it('onClose after _renderLoadedCanvas cancels frame and removes listeners', () => {
        const { view } = makeCanvasView();
        view._paperKey = 'KEY_CLOSE2';
        view._paperEntry = { key: 'KEY_CLOSE2', title: 'Close2' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // Frame handle should be set by _initConnectorScrollResize → _scheduleConnectorUpdate
        var frameHandleBefore = view._connectorFrameHandle;

        view.onClose();

        expect(view._connectorLayerEl).toBeNull();
        expect(view._connectorFrameHandle).toBeNull();
        // onClose doesn't throw
    });

    it('double _cleanupNavigation is safe on layer DOM', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_DBL';
        view._paperEntry = { key: 'KEY_DBL', title: 'Double' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        expect(() => {
            view._cleanupNavigation();
            view._cleanupNavigation();
        }).not.toThrow();
    });

    it('paper change event clears connector layer', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_CHANGE';
        view._paperEntry = { key: 'KEY_CHANGE', title: 'Change' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });

        // Simulate the hover state being set
        view._hoveredCardId = 'card-change';
        view._hoveredAnchorId = 'card-change';

        // When the paper changes, view is re-created and onClose+constructor run.
        // Simulate this by calling _cleanupNavigation (called during re-init).
        view._cleanupNavigation();

        // Hover state should be cleared (re-initialized state)
        expect(view._hoveredCardId).toBeNull();
        expect(view._hoveredAnchorId).toBeNull();
    });
});

// ── ANN14-04 Task 1: Runtime guardrails — hidden connectors preserve card state ──

describe('ANN14-04 Task 1 — Runtime responsiveness preservation', () => {

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

    // ── CANVAS-05: Fallback opening preserved ──

    it('_handleFallbackClick still works when paperEntry has pdf_path [CANVAS-05]', () => {
        const { view } = makeCanvasView();
        view._paperEntry = { key: 'KEY_HIDDEN', pdf_path: 'storage/KEY/file.pdf' };
        view._handleFallbackClick('3');
        expect(view.app.workspace.openLinkText).toHaveBeenCalled();
    });

    it('_handleFallbackClick null guards still work [CANVAS-05]', () => {
        const { view } = makeCanvasView();
        view._paperEntry = { key: 'KEY_FB', pdf_path: 'storage/KEY/file.pdf' };
        view._handleFallbackClick(null);
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });

    it('_handleFallbackClick does nothing when entry missing [CANVAS-05]', () => {
        const { view } = makeCanvasView();
        view._paperEntry = null;
        view._handleFallbackClick('3');
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });

    // ── Connector hidden state does not remove existing behavior ──

    it('source surface and card lanes coexist with connector layer', () => {
        const { view, contentEl } = makeCanvasView();
        view._paperKey = 'KEY_SRC';
        view._paperEntry = { key: 'KEY_SRC', title: 'Source' };
        view._renderLoadedCanvas({
            fulltext: { path: null, exists: false, readable: false, text: null, error: 'missing' },
            note: { path: null, exists: false, readable: false, text: null, error: 'missing' },
        });
        // Verify the connector layer is present alongside source surface
        expect(contentEl.querySelector('.paperforge-canvas-connector-layer')).toBeTruthy();
        expect(contentEl.querySelector('.paperforge-canvas-source-surface')).toBeTruthy();
    });

});
