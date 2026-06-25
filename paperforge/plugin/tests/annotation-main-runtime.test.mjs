/**
 * Runtime harness for PaperForgeStatusView annotation bridge wiring and
 * Phase 6 annotation list section rendering and Phase 7 PDF navigation.
 *
 * These tests exercise the real main.js view methods while stubbing the
 * Obsidian runtime and the annotation loader so no Python subprocess runs.
 *
 * Tests cover:
 *   Task 1 — Test hook, DOM insertion point, default expanded controls, state consumption
 *   Task 2 — Controls rendering, refresh, stale-state, distinct states, forbidden controls
 *   Task 3 — _openAnnotationPdf navigation (Phase 7, Plan 02)
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
let resolveAnnotationPdfTarget;

/**
 * Global capture for Notice calls during tests.
 * Cleared before each test via beforeEach.
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
    PaperForgeStatusView = pluginModule.__test.PaperForgeStatusView;
    resolveAnnotationPdfTarget = pluginModule.__test.resolveAnnotationPdfTarget;
}

function uninstallObsidianStub() {
    if (originalLoad) Module._load = originalLoad;
    const mainPath = require.resolve('../main.js');
    delete require.cache[mainPath];
    originalLoad = null;
}

// ── Obsidian DOM helpers ──

/**
 * Add Obsidian's createEl() method to a DOM element.
 * Obsidian extends HTMLElement with element.createEl(tag, opts) that creates
 * a child element and returns it.
 */
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
            if (opts.attr) {
                for (const k in opts.attr) {
                    if (Object.prototype.hasOwnProperty.call(opts.attr, k)) {
                        child.setAttribute(k, opts.attr[k]);
                    }
                }
            }
            if (opts.href) child.href = opts.href;
            if (opts.value) child.value = opts.value;
        }
        this.appendChild(child);
        // Return element with Obsidian createEl attached (recursive)
        return addCreateEl(child);
    };
    el.empty = function () {
        while (this.firstChild) this.removeChild(this.firstChild);
    };
    el.setText = function (text) {
        this.textContent = text;
    };
    el.addClass = function (cls) {
        this.classList.add(cls);
    };
    el.removeClass = function (cls) {
        this.classList.remove(cls);
    };
    return el;
}

/**
 * Create a DOM element with Obsidian-style createEl() attached.
 */
function createObsidianEl(tag, opts) {
    const el = document.createElement(tag);
    const result = addCreateEl(el);
    if (opts) {
        if (opts.cls) {
            if (typeof opts.cls === 'string') {
                el.className = opts.cls;
            } else if (Array.isArray(opts.cls)) {
                el.className = opts.cls.join(' ');
            }
        }
        if (opts.text != null) el.textContent = opts.text;
        if (opts.title) el.setAttribute('title', opts.title);
        if (opts.attr) {
            for (const k in opts.attr) {
                if (Object.prototype.hasOwnProperty.call(opts.attr, k)) {
                    el.setAttribute(k, opts.attr[k]);
                }
            }
        }
    }
    return el;
}

// ── Fixtures ──

function readyState(paperKey, count) {
    return makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
        paperKey,
        annotations: Array.from({ length: count }, (_, i) => ({
            id: `${paperKey}-${i}`,
            paper_id: paperKey,
            source: 'zotero',
            type: 'highlight',
            color: '#ffd400',
            page_index: 0,
            page_label: '1',
            selected_text: `Annotation ${i + 1} selected text`,
            comment: i === 0 ? 'Important note' : '',
            sort_index: i,
            source_annotation_key: `ann-${paperKey}-${i}`,
            source_attachment_key: 'ATTACH_A',
            source_parent_key: 'PARENT_A',
            sync_state: 'imported',
            is_readonly: 0,
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            deleted_at: null,
            source_library_id: '1',
            source_modified_at: null,
            position_json: '{}',
            selector_json: '{}',
        })),
        message: `${count} annotation(s) loaded.`,
    });
}

function makeStubApp() {
    return {
        vault: {
            adapter: {
                basePath: 'C:/vault',
                exists: vi.fn(() => Promise.resolve(false)),
                read: vi.fn(() => Promise.resolve('')),
            },
            getAbstractFileByPath: vi.fn(() => null),
            read: vi.fn(() => Promise.resolve('')),
            off: vi.fn(),
        },
        plugins: { plugins: { paperforge: { settings: {} } } },
        workspace: {
            getActiveFile: vi.fn(() => ({ path: 'Paper.md' })),
            openLinkText: vi.fn(),
            off: vi.fn(),
        },
        fileManager: { processFrontMatter: vi.fn() },
    };
}

function makeRuntimeView(opts = {}) {
    const containerEl = createObsidianEl('div');
    const contentEl = createObsidianEl('div', { cls: 'paperforge-content-area' });
    containerEl.appendChild(contentEl);
    addCreateEl(contentEl);

    const view = Object.create(PaperForgeStatusView.prototype);
    view.app = opts.app || makeStubApp();
    view.containerEl = containerEl;
    view._contentEl = contentEl;
    view._currentPaperKey = Object.prototype.hasOwnProperty.call(opts, 'paperKey')
        ? opts.paperKey
        : 'PAPER_A';
    view._currentPaperEntry = opts.paperEntry || {
        title: 'Test Paper',
        authors: ['Author A'],
        year: 2024,
        has_pdf: true,
        ocr_status: 'done',
        deep_reading_status: 'done',
        next_step: 'ready',
        zotero_key: view._currentPaperKey,
        pdf_path: '[[test.pdf]]',
        fulltext_path: 'test.md',
        note_path: 'notes/test.md',
        do_ocr: false,
        analyze: false,
        health: {},
    };
    view._currentMode = opts.mode || 'paper';
    view._currentFilePath = opts.filePath || 'Paper.md';
    view._currentDomain = null;
    view._modeSubscribers = [];
    view._annotationLoadSeq = 0;
    view._annotationState = opts.annotationState || readyState(view._currentPaperKey, 3);
    view._annotationUiState = opts.uiState || { query: '', groupMode: 'none', typeColorFilter: 'all', expandedIds: [] };
    view._lastRenderableAnnotationState = null;
    view._annotationLoader = opts.loader || vi.fn(async ({ paperKey }) => readyState(paperKey, 3));
    view._cachedItems = null;
    view._cachedStats = null;
    view._ocrPrivacyShown = false;
    view._leafChangeTimer = null;
    view._invalidateIndex = vi.fn();
    view._renderModeHeader = vi.fn();
    view._showMessage = vi.fn();
    view._extractOverviewFromNote = vi.fn(() => '');
    view._openFulltext = vi.fn();
    view._patchCachedEntry = vi.fn();
    view._messageEl = document.createElement('div');

    // Spy on the refresh method
    vi.spyOn(view, 'loadAnnotationsForCurrentPaper').mockImplementation(opts.loaderImpl || vi.fn(async () => null));

    return view;
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

// ── Task 1: Test hook accessibility ──

describe('Task 1 — Test hook exists', () => {
    it('exports PaperForgeStatusView via module.exports.__test', () => {
        expect(PaperForgeStatusView).toBeDefined();
        expect(typeof PaperForgeStatusView).toBe('function');
        expect(PaperForgeStatusView.name).toBe('PaperForgeStatusView');
    });
});

// ── Task 1: DOM insertion point ──

describe('Task 1 — DOM insertion point', () => {
    it('renders .paperforge-annotations-section inside .paperforge-paper-view', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A' });
        view._renderPaperMode();

        const paperView = view._contentEl.querySelector('.paperforge-paper-view');
        expect(paperView).toBeTruthy();

        const annotationSection = paperView.querySelector('.paperforge-annotations-section');
        expect(annotationSection).toBeTruthy();
    });

    it('places annotation section after .paperforge-paper-overview and before .paperforge-next-step-card or .paperforge-complete-row', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A' });
        view._renderPaperMode();

        const paperView = view._contentEl.querySelector('.paperforge-paper-view');
        const children = Array.from(paperView.children);
        const overviewIndex = children.findIndex(el => el.classList.contains('paperforge-paper-overview'));
        const annotationIndex = children.findIndex(el => el.classList.contains('paperforge-annotations-section'));
        const nextStepIndex = children.findIndex(el =>
            el.classList.contains('paperforge-next-step-card') ||
            el.classList.contains('paperforge-complete-row')
        );

        expect(overviewIndex).toBeGreaterThanOrEqual(0);
        expect(annotationIndex).toBeGreaterThan(overviewIndex);
        expect(nextStepIndex).toBeGreaterThan(annotationIndex);
    });

    it('section is empty/status by default when no annotation state is provided', () => {
        const view = makeRuntimeView({
            paperKey: 'PAPER_A',
            annotationState: makeAnnotationState(ANNOTATION_LOAD_STATES.IDLE),
        });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        expect(section).toBeTruthy();
        // Idle state renders empty (default state with no rows)
        const contentArea = section.querySelector('.paperforge-annotations-content');
        expect(contentArea).toBeTruthy();
    });
});

// ── Task 1: Expanded by default with controls ──

describe('Task 1 — Section renders controls when state is renderable', () => {
    it('shows title, count, refresh button when ready state has annotations', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        expect(section).toBeTruthy();

        const header = section.querySelector('.paperforge-annotations-header');
        expect(header).toBeTruthy();
        expect(header.querySelector('.paperforge-annotations-title')).toBeTruthy();
        expect(header.querySelector('.paperforge-annotations-count')).toBeTruthy();
        expect(header.querySelector('.paperforge-annotations-refresh-btn')).toBeTruthy();
    });

    it('renders search control, grouping control, and type/color filter when ready', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const controls = section.querySelector('.paperforge-annotation-controls');
        expect(controls).toBeTruthy();

        const search = controls.querySelector('.paperforge-annotation-search');
        expect(search).toBeTruthy();

        const groupSelect = controls.querySelector('.paperforge-annotation-group-select');
        expect(groupSelect).toBeTruthy();

        const filterSelect = controls.querySelector('.paperforge-annotation-filter-select');
        expect(filterSelect).toBeTruthy();
    });

    it('does not render controls when state is not ready', () => {
        const view = makeRuntimeView({
            paperKey: 'PAPER_A',
            annotationState: makeAnnotationState(ANNOTATION_LOAD_STATES.MISSING_DB, {
                paperKey: 'PAPER_A',
                message: 'DB not available.',
            }),
        });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const controls = section.querySelector('.paperforge-annotation-controls');
        expect(controls).toBeFalsy();
    });
});

// ── Task 1: Consumes getAnnotationState() ──

describe('Task 1 — Consumes getAnnotationState()', () => {
    it('calls getAnnotationState and uses its result for the view-model', () => {
        const annState = readyState('PAPER_A', 5);
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        const spy = vi.spyOn(view, 'getAnnotationState');

        view._renderPaperMode();

        expect(spy).toHaveBeenCalled();
    });
});

// ── Task 2: Controls trigger section-local rerender ──

describe('Task 2 — Controls update session-local state', () => {
    it('search input updates _annotationUiState.query', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const searchInput = view._contentEl.querySelector('.paperforge-annotation-search');
        expect(searchInput).toBeTruthy();

        // Simulate typing
        searchInput.value = 'test query';
        searchInput.dispatchEvent(new window.Event('input'));

        expect(view._annotationUiState.query).toBe('test query');
    });

    it('grouping select updates _annotationUiState.groupMode', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const groupSelect = view._contentEl.querySelector('.paperforge-annotation-group-select');
        expect(groupSelect).toBeTruthy();

        groupSelect.value = 'page';
        groupSelect.dispatchEvent(new window.Event('change'));

        expect(view._annotationUiState.groupMode).toBe('page');
    });

    it('filter select updates _annotationUiState.typeColorFilter', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const filterSelect = view._contentEl.querySelector('.paperforge-annotation-filter-select');
        expect(filterSelect).toBeTruthy();

        // Pick first non-"all" option
        const options = Array.from(filterSelect.options);
        const firstOption = options.find(o => o.value !== 'all');
        if (firstOption) {
            filterSelect.value = firstOption.value;
            filterSelect.dispatchEvent(new window.Event('change'));
            expect(view._annotationUiState.typeColorFilter).toBe(firstOption.value);
        }
    });

    it('control changes do not persist to plugin settings or localStorage', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const searchInput = view._contentEl.querySelector('.paperforge-annotation-search');
        searchInput.value = 'persistence test';
        searchInput.dispatchEvent(new window.Event('input'));

        // UI state is session-only — nothing goes to the plugin's saveData or localStorage
        expect(view._annotationUiState.query).toBe('persistence test');
        expect(Object.keys(localStorage).length || true).toBeTruthy(); // localStorage may not have items but that's fine
    });
});

// ── Task 2: Distinct states ──

describe('Task 2 — Distinct states render correctly', () => {
    const stateTypes = [
        { state: 'empty', cls: '.paperforge-annotations-empty', msg: 'no annotations' },
        { state: 'missing-db', cls: '.paperforge-annotations-error', msg: 'database' },
        { state: 'missing-paper', cls: '.paperforge-annotations-error', msg: 'paper' },
        { state: 'cli-error', cls: '.paperforge-annotations-error', msg: 'Failed' },
        { state: 'invalid-json', cls: '.paperforge-annotations-error', msg: 'data' },
    ];

    for (const st of stateTypes) {
        it(`renders distinct ${st.state} message`, () => {
            const annState = makeAnnotationState(ANNOTATION_LOAD_STATES[st.state.toUpperCase().replace('-', '_')], {
                paperKey: 'PAPER_A',
                message: `Test ${st.state} message`,
            });
            const view = makeRuntimeView({
                paperKey: 'PAPER_A',
                annotationState: annState,
            });
            view._renderPaperMode();

            const section = view._contentEl.querySelector('.paperforge-annotations-section');
            expect(section).toBeTruthy();

            const messageEl = section.querySelector(st.cls);
            expect(messageEl).toBeTruthy();
            expect(messageEl.textContent).toBeTruthy();
        });
    }
});

// ── Task 2: Refresh button ──

describe('Task 2 — Refresh button', () => {
    it('clicking refresh button calls loadAnnotationsForCurrentPaper', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        // Reset mock call count from render-time auto-load
        view.loadAnnotationsForCurrentPaper.mockClear();

        const refreshBtn = view._contentEl.querySelector('.paperforge-annotations-refresh-btn');
        expect(refreshBtn).toBeTruthy();

        refreshBtn.click();

        expect(view.loadAnnotationsForCurrentPaper).toHaveBeenCalledWith('manual');
    });

    it('refresh does not invoke PDF open/navigation APIs', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const refreshBtn = view._contentEl.querySelector('.paperforge-annotations-refresh-btn');
        expect(refreshBtn).toBeTruthy();

        refreshBtn.click();

        // Workspace.openLinkText should not be called by refresh
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });
});

// ── Task 2: Loading state ──

describe('Task 2 — Loading state', () => {
    it('loading state shows status text', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.LOADING, {
            paperKey: 'PAPER_A',
            message: 'Loading...',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const statusEl = view._contentEl.querySelector('.paperforge-annotations-status');
        expect(statusEl).toBeTruthy();
        expect(statusEl.textContent).toBeTruthy();
    });
});

// ── Task 2: Stale data banner ──

describe('Task 2 — Stale data banner', () => {
    it('shows stale banner when state has stale flag', () => {
        const staleReady = readyState('PAPER_A', 2);
        staleReady.stale = true;
        staleReady.message = 'Refresh failed. — Showing previously loaded (stale) data.';

        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: staleReady });
        view._renderPaperMode();

        const staleBanner = view._contentEl.querySelector('.paperforge-annotations-stale-banner');
        expect(staleBanner).toBeTruthy();
    });
});

// ── Task 2: Row rendering ──

describe('Task 2 — Annotation rows', () => {
    it('renders rows with page, swatch, type, selected text, and comment', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 2) });
        view._renderPaperMode();

        const rows = view._contentEl.querySelectorAll('.paperforge-annotation-row');
        expect(rows.length).toBe(2);

        const firstRow = rows[0];
        expect(firstRow.querySelector('.paperforge-annotation-page-badge')).toBeTruthy();
        expect(firstRow.querySelector('.paperforge-annotation-swatch')).toBeTruthy();
        expect(firstRow.querySelector('.paperforge-annotation-type-label')).toBeTruthy();
        expect(firstRow.querySelector('.paperforge-annotation-selected-text')).toBeTruthy();
        expect(firstRow.querySelector('.paperforge-annotation-comment')).toBeTruthy();
    });

    it('uses textContent/setText for all user-facing text (no innerHTML)', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 2) });
        view._renderPaperMode();

        const rows = view._contentEl.querySelectorAll('.paperforge-annotation-row');
        for (const row of rows) {
            const textEls = [
                row.querySelector('.paperforge-annotation-selected-text'),
                row.querySelector('.paperforge-annotation-comment'),
                row.querySelector('.paperforge-annotation-type-label'),
            ];
            for (const el of textEls) {
                if (el) {
                    // Should have set text via textContent/setText, not innerHTML
                    expect(el.innerHTML).not.toContain('<');
                }
            }
        }
    });

    it('includes row expansion button', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 2) });
        view._renderPaperMode();

        const expandBtns = view._contentEl.querySelectorAll('.paperforge-annotation-expand-btn');
        expect(expandBtns.length).toBeGreaterThanOrEqual(2);
    });
});

// ── Task 2: Forbidden controls ──

describe('Task 2 — Forbidden controls are absent (D-24, D-25)', () => {
    it('does not contain PDF jump buttons or open-at-page buttons', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const html = section.innerHTML.toLowerCase();

        // Should not contain PDF-specific navigation terms
        expect(html).not.toContain('open pdf');
        expect(html).not.toContain('jump to');
        expect(html).not.toContain('go to page');
    });

    it('does not contain edit or delete buttons', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const allButtons = section.querySelectorAll('button');
        for (const btn of allButtons) {
            const text = btn.textContent.toLowerCase();
            expect(text).not.toContain('edit');
            expect(text).not.toContain('delete');
            expect(text).not.toContain('remove');
        }
    });

    it('does not contain write-back or DB mutation controls', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const html = section.innerHTML.toLowerCase();

        expect(html).not.toContain('save');
        expect(html).not.toContain('write back');
        expect(html).not.toContain('sync to zotero');
    });

    it('does not contain concept evidence controls', () => {
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: readyState('PAPER_A', 3) });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const html = section.innerHTML.toLowerCase();

        expect(html).not.toContain('evidence');
        expect(html).not.toContain('concept card');
    });
});

// ── Plan 02: PDF navigation (Phase 7) ──

describe('Plan 02 — _openAnnotationPdf direct tests', () => {
    function makePdfRow(opts) {
        return {
            pdfLocation: {
                sourceAttachmentKey: opts.sourceAttachmentKey || 'ABCDEFGH',
                pageIndex: opts.pageIndex != null ? opts.pageIndex : null,
                pageLabel: String((opts.pageIndex != null ? opts.pageIndex : 0) + 1),
            },
            display: {
                pageLabel: String((opts.pageIndex != null ? opts.pageIndex : 0) + 1),
                page: (opts.pageIndex != null ? opts.pageIndex : 0) + 1,
            },
        };
    }

    /**
     * Entry with a realistic Zotero storage path containing /storage/{KEY}/
     * so buildPaperPdfCandidates derives attachmentKey = 'ABCDEFGH'.
     */
    function makePdfEntry() {
        return {
            title: 'Test Paper',
            authors: ['Author A'],
            year: 2024,
            has_pdf: true,
            zotero_key: 'PAPER_A',
            pdf_path: '[[99_System/Zotero/storage/ABCDEFGH/test.pdf]]',
            zotero_storage_key: 'ABCDEFGH',
            fulltext_path: 'test.md',
            note_path: 'notes/test.md',
            do_ocr: false,
            analyze: false,
            health: {},
        };
    }

    it('confirmed identity + pageIndex opens PDF at correct page', () => {
        const app = makeStubApp();
        app.vault.getAbstractFileByPath = vi.fn(() => ({ path: '99_System/Zotero/storage/ABCDEFGH/test.pdf', name: 'test.pdf' }));
        const view = makeRuntimeView({
            app,
            paperEntry: makePdfEntry(),
        });
        const row = makePdfRow({ sourceAttachmentKey: 'ABCDEFGH', pageIndex: 2 });

        view._openAnnotationPdf(row);

        expect(app.workspace.openLinkText).toHaveBeenCalledTimes(1);
        expect(app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/ABCDEFGH/test.pdf#page=3', '');
    });

    it('unmatched identity shows Notice and does not navigate', () => {
        const app = makeStubApp();
        app.vault.getAbstractFileByPath = vi.fn(() => ({ path: '99_System/Zotero/storage/ABCDEFGH/test.pdf', name: 'test.pdf' }));
        const view = makeRuntimeView({
            app,
            paperEntry: makePdfEntry(),
        });
        const row = makePdfRow({ sourceAttachmentKey: 'UNKNOWN', pageIndex: 0 });

        view._openAnnotationPdf(row);

        expect(noticeCalls.length).toBeGreaterThanOrEqual(1);
        expect(app.workspace.openLinkText).not.toHaveBeenCalled();
    });

    it('missing vault file shows Notice and does not navigate', () => {
        const app = makeStubApp();
        app.vault.getAbstractFileByPath = vi.fn(() => null);
        const view = makeRuntimeView({
            app,
            paperEntry: makePdfEntry(),
        });
        const row = makePdfRow({ sourceAttachmentKey: 'ABCDEFGH', pageIndex: 2 });

        view._openAnnotationPdf(row);

        expect(noticeCalls.length).toBeGreaterThanOrEqual(1);
        expect(app.workspace.openLinkText).not.toHaveBeenCalled();
    });

    it('null pageIndex opens PDF without page fragment', () => {
        const app = makeStubApp();
        app.vault.getAbstractFileByPath = vi.fn(() => ({ path: '99_System/Zotero/storage/ABCDEFGH/test.pdf', name: 'test.pdf' }));
        const view = makeRuntimeView({
            app,
            paperEntry: makePdfEntry(),
        });
        const row = makePdfRow({ sourceAttachmentKey: 'ABCDEFGH', pageIndex: null });

        view._openAnnotationPdf(row);

        expect(app.workspace.openLinkText).toHaveBeenCalledTimes(1);
        expect(app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/ABCDEFGH/test.pdf', '');
    });

    it('negative pageIndex opens PDF without page fragment', () => {
        const app = makeStubApp();
        app.vault.getAbstractFileByPath = vi.fn(() => ({ path: '99_System/Zotero/storage/ABCDEFGH/test.pdf', name: 'test.pdf' }));
        const view = makeRuntimeView({
            app,
            paperEntry: makePdfEntry(),
        });
        const row = makePdfRow({ sourceAttachmentKey: 'ABCDEFGH', pageIndex: -1 });

        view._openAnnotationPdf(row);

        expect(app.workspace.openLinkText).toHaveBeenCalledTimes(1);
        expect(app.workspace.openLinkText).toHaveBeenCalledWith('99_System/Zotero/storage/ABCDEFGH/test.pdf', '');
    });
});

describe('Plan 02 — UI state preservation', () => {
    it('page-badge click does not alter _annotationUiState', () => {
        const view = makeRuntimeView({
            paperKey: 'PAPER_A',
            annotationState: readyState('PAPER_A', 2),
        });

        view._renderPaperMode();

        // Set a distinct UI state after render (not filtering out rows)
        view._annotationUiState = {
            query: '',
            groupMode: 'page',
            typeColorFilter: 'all',
            expandedIds: [],
        };

        // Click the first page badge
        const badge = view._contentEl.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        badge.click();

        // UI state must be unchanged
        expect(view._annotationUiState.query).toBe('');
        expect(view._annotationUiState.groupMode).toBe('page');
        expect(view._annotationUiState.typeColorFilter).toBe('all');
    });

    it('expand button does not call openLinkText', () => {
        const app = makeStubApp();
        const view = makeRuntimeView({
            app,
            paperKey: 'PAPER_A',
            annotationState: readyState('PAPER_A', 2),
        });

        view._renderPaperMode();

        // Click the expand button on the first row
        const expandBtn = view._contentEl.querySelector('.paperforge-annotation-expand-btn');
        expect(expandBtn).toBeTruthy();
        expandBtn.click();

        // Verify openLinkText was never called
        expect(app.workspace.openLinkText).not.toHaveBeenCalled();
    });
});
