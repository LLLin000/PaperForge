/**
 * DOM regression tests for Phase 6 annotation list section.
 *
 * These tests verify the bounded, compact row list layout produced by
 * the PaperForgeStatusView annotation renderer and the CSS class hooks
 * that Plan 04's styles.css styles.
 *
 * Tests cover:
 *   Task 1 (Plan 04) — Bounded list container, compact rows, class hooks
 *   Task 2 (Plan 04) — Row content placement, preview clamping, expansion
 *                      detail boundaries, forbidden controls
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

function makeAnnotationRow(overrides) {
    var pageVal = overrides.page != null ? overrides.page : 1;
    var pageLabelVal = overrides.pageLabel != null ? overrides.pageLabel : '1';
    var srcAttachKey = Object.prototype.hasOwnProperty.call(overrides, 'sourceAttachmentKey')
        ? overrides.sourceAttachmentKey : 'ATTACH_A';
    return {
        id: overrides.id || 'r1',
        display: {
            page: pageVal,
            pageLabel: pageLabelVal,
            color: Object.prototype.hasOwnProperty.call(overrides, 'color') ? overrides.color : '#ffd400',
            type: overrides.type || 'highlight',
            selectedText: overrides.selectedText || 'Some selected text from the paper.',
            comment: Object.prototype.hasOwnProperty.call(overrides, 'comment') ? overrides.comment : 'A comment about this annotation.',
        },
        provenance: {
            source: overrides.source != null ? overrides.source : 'zotero',
            isReadonly: overrides.isReadonly != null ? overrides.isReadonly : false,
            sourceAttachmentKey: srcAttachKey,
            sourceAnnotationKey: Object.prototype.hasOwnProperty.call(overrides, 'sourceAnnotationKey') ? overrides.sourceAnnotationKey : 'ANN_A',
            createdAt: overrides.createdAt || '2024-01-15T10:00:00Z',
            updatedAt: overrides.updatedAt || '2024-01-15T10:00:00Z',
            syncState: overrides.syncState || 'imported',
        },
        pdfLocation: {
            sourceAttachmentKey: srcAttachKey,
            pageIndex: pageVal - 1,
            pageLabel: pageLabelVal,
        },
    };
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
        pdf_path: '[[99_System/Zotero/storage/ATTACH_A/test.pdf]]',
        zotero_storage_key: 'ATTACH_A',
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
    view._annotationState = opts.annotationState;
    view._annotationUiState = opts.uiState || { query: '', groupMode: 'none', typeColorFilter: 'all', expandedIds: [] };
    view._lastRenderableAnnotationState = null;
    view._annotationLoader = opts.loader || vi.fn(async ({ paperKey }) => null);
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

    vi.spyOn(view, 'loadAnnotationsForCurrentPaper').mockImplementation(opts.loaderImpl || vi.fn(async () => null));
    vi.spyOn(view, 'getAnnotationState').mockImplementation(() => view._annotationState);

    return view;
}

beforeEach(() => {
    installObsidianStub();
});

afterEach(() => {
    uninstallObsidianStub();
    vi.restoreAllMocks();
    document.body.innerHTML = '';
});

// ── Test 1: Bounded list container and compact rows (D-04, D-05) ──

describe('D-04 / D-05 — Bounded list container and compact rows', () => {
    it('renders .paperforge-annotations-list with bounded scroll container', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: Array.from({ length: 20 }, (_, i) => makeAnnotationRow({
                id: 'r' + i,
                page: i,
                pageLabel: String(i + 1),
                selectedText: 'Annotation ' + (i + 1) + ' long text.',
            })),
            message: '20 annotations loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        expect(section).toBeTruthy();

        const listContainer = section.querySelector('.paperforge-annotations-list');
        expect(listContainer).toBeTruthy();
        // The list is a div with bounded max-height, not an unbounded container
        expect(listContainer.tagName).toBe('DIV');
        expect(listContainer.children.length).toBe(20);
    });

    it('renders compact row elements with stable class hooks', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [
                makeAnnotationRow({ id: 'r1' }),
                makeAnnotationRow({ id: 'r2', page: 2, pageLabel: '2', color: null, type: 'underline' }),
            ],
            message: '2 annotations loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const rows = view._contentEl.querySelectorAll('.paperforge-annotation-row');
        expect(rows.length).toBe(2);

        // Each row should be a div element with stable class hook
        for (const row of rows) {
            expect(row.tagName).toBe('DIV');
            expect(row.className).toContain('paperforge-annotation-row');
        }
    });
});

// ── Test 2: Row DOM elements (D-08, D-10) ──

describe('D-08 / D-10 — Row contains page, swatch, type, text preview, comment preview', () => {
    it('each row has page badge, color swatch, type label, selected text, and comment', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const row = view._contentEl.querySelector('.paperforge-annotation-row');
        expect(row).toBeTruthy();

        // Page badge — semantic button with tooltip
        const badge = row.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        expect(badge.tagName).toBe('BUTTON');
        expect(badge.textContent).toBeTruthy();
        expect(badge.getAttribute('title')).toBeTruthy();
        expect(badge.getAttribute('aria-label')).toBeTruthy();

        // Color swatch
        const swatch = row.querySelector('.paperforge-annotation-swatch');
        expect(swatch).toBeTruthy();
        // Swatch has a background color when color is set
        expect(swatch.style.backgroundColor).toBeTruthy();

        // Type label
        const typeLabel = row.querySelector('.paperforge-annotation-type-label');
        expect(typeLabel).toBeTruthy();
        expect(typeLabel.textContent.length).toBeGreaterThan(0);

        // Selected text preview
        const selText = row.querySelector('.paperforge-annotation-selected-text');
        expect(selText).toBeTruthy();
        expect(selText.textContent.length).toBeGreaterThan(0);

        // Comment preview or icon
        const comment = row.querySelector('.paperforge-annotation-comment');
        expect(comment).toBeTruthy();
    });

    it('color swatch has no-color class when color is null', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', color: null })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const swatch = view._contentEl.querySelector('.paperforge-annotation-swatch');
        expect(swatch).toBeTruthy();
        expect(swatch.classList.contains('no-color')).toBe(true);
    });

    it('each row has an expand/collapse button', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const expandBtn = view._contentEl.querySelector('.paperforge-annotation-expand-btn');
        expect(expandBtn).toBeTruthy();
        expect(expandBtn.tagName).toBe('BUTTON');
    });
});

// ── Badge semantics: enabled, disabled, tooltip, aria-label (D-01, D-02, D-07, D-08, D-11) ──

describe('D-01 / D-02 / D-07 — Page badge is semantic jump button with accessible labels', () => {
    it('enabled badge has Open PDF tooltip and aria-label with page number', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', page: 2 })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const badge = view._contentEl.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        expect(badge.tagName).toBe('BUTTON');
        expect(badge.disabled).toBe(false);
        expect(badge.getAttribute('aria-disabled')).toBeNull();
        expect(badge.getAttribute('title')).toContain('Open PDF');
        expect(badge.getAttribute('title')).toContain('page');
        expect(badge.getAttribute('aria-label')).toContain('Open PDF');
        expect(badge.getAttribute('aria-label')).toContain('page');
    });

    it('unmatched attachment renders disabled badge with unavailable explanation', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', sourceAttachmentKey: 'UNKNOWN' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const badge = view._contentEl.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        expect(badge.tagName).toBe('BUTTON');
        expect(badge.disabled).toBe(true);
        expect(badge.getAttribute('aria-disabled')).toBe('true');
        const title = badge.getAttribute('title');
        expect(title).toBeTruthy();
        // Tooltip explains unavailability without navigation wording
        expect(title).not.toMatch(/open pdf/i);
        expect(title.length).toBeGreaterThan(5);
    });

    it('confirmed PDF with null pageIndex remains enabled (D-11)', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        // Override pdfLocation.pageIndex to null to simulate missing page data
        annState.annotations[0].pdfLocation.pageIndex = null;
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        // Even with null pageIndex, badge is enabled (D-11: confirmed PDF still opens)
        const badge = view._contentEl.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        expect(badge.tagName).toBe('BUTTON');
        expect(badge.disabled).toBe(false);
        const title = badge.getAttribute('title');
        expect(title).toContain('Open PDF');
        expect(title).not.toMatch(/at page/i);
    });
});

// ── Test 3: Provenance absent from default rows, present in expansion (D-09) ──

describe('D-09 — Provenance details hidden by default, shown on expansion', () => {
    it('default (non-expanded) row does not show detail lines', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const row = view._contentEl.querySelector('.paperforge-annotation-row');
        expect(row).toBeTruthy();
        expect(row.classList.contains('expanded')).toBe(false);

        // Detail container should not exist in non-expanded row
        const details = row.querySelector('.paperforge-annotation-details');
        expect(details).toBeFalsy();

        // Provenance keywords should not appear in the default row text
        const rowText = row.textContent.toLowerCase();
        expect(rowText).not.toContain('source:');
        expect(rowText).not.toContain('attachment:');
        expect(rowText).not.toContain('annotation key:');
        expect(rowText).not.toContain('created:');
        expect(rowText).not.toContain('sync:');
    });

    it('expanded row shows detail lines with provenance fields', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({
            paperKey: 'PAPER_A',
            annotationState: annState,
            uiState: { query: '', groupMode: 'none', typeColorFilter: 'all', expandedIds: ['ANN_A'] },
        });
        view._renderPaperMode();

        const row = view._contentEl.querySelector('.paperforge-annotation-row');
        expect(row).toBeTruthy();
        expect(row.classList.contains('expanded')).toBe(true);

        // Detail container should exist in expanded row
        const details = row.querySelector('.paperforge-annotation-details');
        expect(details).toBeTruthy();

        const detailLines = details.querySelectorAll('.paperforge-annotation-detail-line');
        expect(detailLines.length).toBeGreaterThanOrEqual(1);

        // Provenance content should be visible
        const detailsText = details.textContent;
        expect(detailsText).toContain('Source:');
        expect(detailsText).toContain('Attachment:');
        expect(detailsText).toContain('Annotation Key:');
        expect(detailsText).toContain('Created:');
        expect(detailsText).toContain('Sync:');
    });
});

// ── Test 4: Preview clamping CSS classes (D-06) ──

describe('D-06 — Preview clamped with CSS classes', () => {
    it('selected-text preview element has stable CSS class for 2-line clamp', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const selEl = view._contentEl.querySelector('.paperforge-annotation-selected-text');
        expect(selEl).toBeTruthy();
        // The element should exist — CSS will apply -webkit-line-clamp: 2
        // We can't test computed -webkit-line-clamp in jsdom, but we verify the class hook
        expect(selEl.className).toContain('paperforge-annotation-selected-text');
    });

    it('comment preview element has stable CSS class for 1-line clamp', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', comment: 'A fairly long comment that should be clamped' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const commentEl = view._contentEl.querySelector('.paperforge-annotation-comment');
        expect(commentEl).toBeTruthy();
        expect(commentEl.className).toContain('paperforge-annotation-comment');
    });

    it('truncated class is added when text exceeds preview threshold', () => {
        const longText = 'A'.repeat(200);
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', selectedText: longText, comment: '' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const selEl = view._contentEl.querySelector('.paperforge-annotation-selected-text');
        expect(selEl).toBeTruthy();
        // Text longer than 140 chars should be truncated (with class)
        expect(selEl.classList.contains('truncated')).toBe(true);
        // Original long text is not in DOM (truncated preview is)
        expect(selEl.textContent.length).toBeLessThan(longText.length);
    });
});

// ── Click isolation: jump and expansion are independent (D-03, D-13) ──

describe('D-03 / D-13 — Jump and expansion are isolated events', () => {
    it('clicking page badge does not alter expandedIds', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1', sourceAttachmentKey: 'MATCH_A' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({
            paperKey: 'PAPER_A',
            annotationState: annState,
            uiState: { query: '', groupMode: 'none', typeColorFilter: 'all', expandedIds: ['ANN_A'] },
            paperEntry: {
                title: 'Test Paper',
                authors: ['Author A'],
                year: 2024,
                has_pdf: true,
                zotero_key: 'PAPER_A',
                pdf_path: '[[99_System/Zotero/storage/MATCH_A/test.pdf]]',
                zotero_storage_key: 'MATCH_A',
                fulltext_path: 'test.md',
                note_path: 'notes/test.md',
                do_ocr: false,
                analyze: false,
                health: {},
            },
        });
        view._renderPaperMode();

        const badge = view._contentEl.querySelector('.paperforge-annotation-page-badge');
        expect(badge).toBeTruthy();
        badge.click();

        // expandedIds must be unchanged after badge click
        expect(view._annotationUiState.expandedIds).toEqual(['ANN_A']);
    });

    it('expand button does not invoke _openAnnotationPdf', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const expandBtn = view._contentEl.querySelector('.paperforge-annotation-expand-btn');
        expect(expandBtn).toBeTruthy();
        expandBtn.click();

        // Expand must not invoke PDF navigation
        expect(view.app.workspace.openLinkText).not.toHaveBeenCalled();
    });
});

// ── Forbidden controls absent (T-annotation-07-10, D-15, D-25) ──

describe('T-annotation-07-10 / D-15 / D-25 — Forbidden controls absent from annotation section', () => {
    it('page badge is the only row-level jump action', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');

        // The page badge IS the jump button (replaces Phase 6 forbidden-navigation assertion)
        const jumpButtons = section.querySelectorAll('.paperforge-annotation-page-badge');
        expect(jumpButtons.length).toBe(1);
        expect(jumpButtons[0].tagName).toBe('BUTTON');

        // No extra "jump to" or "go to page" text outside the badge's title/aria-label
        const sectionHtml = section.innerHTML.toLowerCase();
        const badgeHtml = jumpButtons[0].outerHTML.toLowerCase();
        const nonBadgeHtml = sectionHtml.replace(badgeHtml, '');
        expect(nonBadgeHtml).not.toContain('jump to');
        expect(nonBadgeHtml).not.toContain('go to page');
        expect(nonBadgeHtml).not.toContain('open-at-page');
    });

    it('overlay lifecycle coexists with annotation section rendering', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        // Annotation section must still render correctly
        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        expect(section).toBeTruthy();
        const header = section.querySelector('.paperforge-annotations-header');
        expect(header).toBeTruthy();
        const rows = section.querySelectorAll('.paperforge-annotation-row');
        expect(rows.length).toBeGreaterThanOrEqual(1);

        // Overlay state was initialized (fail-closed — no PDF viewer in test env)
        expect(view._annotationOverlayState).toBeDefined();

        // Overlay elements are NOT in the annotation section DOM
        // (they belong in the PDF viewer DOM, not the annotation section)
        const sectionHtml = section.innerHTML.toLowerCase();
        expect(sectionHtml).not.toContain('paperforge-annotation-overlay');
        // Confirm popover hooks are also not in the annotation section
        // (popover belongs to the PDF viewer DOM, not the sidebar/list)
        expect(sectionHtml).not.toContain('annotation-overlay-popover');
        expect(sectionHtml).not.toContain('annotation-overlay-close');
        expect(sectionHtml).not.toContain('annotation-overlay-field');
        expect(sectionHtml).not.toContain('annotation-overlay-value');

        // No edit/delete/create controls in annotation section (D-17)
        const allButtons = section.querySelectorAll('button');
        for (const btn of allButtons) {
            const text = btn.textContent.toLowerCase();
            expect(text).not.toContain('edit');
            expect(text).not.toContain('delete');
            expect(text).not.toContain('remove');
            expect(text).not.toContain('create');
        }
    });

    it('no edit, delete, or remove buttons present', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
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

    it('no write-back or DB mutation controls present', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const html = section.innerHTML.toLowerCase();
        expect(html).not.toContain('save');
        expect(html).not.toContain('write back');
        expect(html).not.toContain('sync to zotero');
        expect(html).not.toContain('database');
    });

    it('no concept-card evidence controls present', () => {
        const annState = makeAnnotationState(ANNOTATION_LOAD_STATES.READY, {
            paperKey: 'PAPER_A',
            annotations: [makeAnnotationRow({ id: 'r1' })],
            message: '1 annotation loaded.',
        });
        const view = makeRuntimeView({ paperKey: 'PAPER_A', annotationState: annState });
        view._renderPaperMode();

        const section = view._contentEl.querySelector('.paperforge-annotations-section');
        const html = section.innerHTML.toLowerCase();
        expect(html).not.toContain('evidence');
        expect(html).not.toContain('concept card');
    });
});
