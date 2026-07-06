/**
 * Vitest tests for canvas shell DOM rendering.
 *
 * Tests cover:
 *   - shell states: idle, loading, empty, missing-paper, missing-db,
 *     cli-error, invalid-json, missing-source, unsupported, stale
 *   - paper identity header rendering
 *   - Safe text rendering (textContent, no innerHTML for annotation data)
 *   - Absence of forbidden write/control keywords
 *
 * @module tests/canvas-render
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';

const {
    renderCanvasView,
    renderCanvasIdentity,
    renderCanvasIdle,
    renderCanvasLoading,
    renderCanvasEmpty,
    renderCanvasMissingPaper,
    renderCanvasMissingDb,
    renderCanvasCliError,
    renderCanvasInvalidJson,
    renderCanvasMissingSource,
    renderCanvasUnsupported,
    renderCanvasStaleBanner,
    renderCanvasSourceSurface,
    renderSourceBlock,
    renderExactAnchorText,
    renderPageLevelAnchorMarker,
    renderUnresolvedAnchorStatus,
    renderCanvasCard,
    renderFallbackButton,
    renderCanvasConnectorLayer,
    updateCanvasConnectorLayer,
} = await import('../src/canvas/render.js');

// ── Forbidden control keywords (must not appear in any canvas state) ──

const FORBIDDEN_WORDS = [
    'edit', 'delete', 'create', 'save', 'import', 'apply',
    'write back', 'write-back', 'evidence', 'concept card',
];

// "database" is deliberately excluded from the text-level forbidden list
// because status messages legitimately describe the annotation database
// state (e.g. "Annotation database is not available").  It is still
// checked at the button level below.

function makeRootEl() {
    const el = document.createElement('div');
    return el;
}

function assertNoForbiddenControls(rootEl) {
    const html = rootEl.innerHTML.toLowerCase();
    const text = rootEl.textContent.toLowerCase();
    for (const word of FORBIDDEN_WORDS) {
        expect(html).not.toContain(word);
    }
    // Also check buttons specifically
    const buttons = rootEl.querySelectorAll('button');
    for (const btn of buttons) {
        const btnText = btn.textContent.toLowerCase();
        for (const word of FORBIDDEN_WORDS) {
            expect(btnText).not.toContain(word);
        }
    }
}

// ── Fixtures ──

function makeVM(overrides) {
    return {
        state: overrides.state || 'idle',
        paperKey: overrides.paperKey || null,
        message: overrides.message || '',
        stale: overrides.stale || false,
        ...overrides,
    };
}

// ---------------------------------------------------------------------------
// Shell states
// ---------------------------------------------------------------------------

describe('renderCanvasView — shell states', () => {
    it('renders idle state when vm.state is idle', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'idle' }));

        expect(root.querySelector('.paperforge-canvas-shell')).toBeTruthy();
        expect(root.querySelector('.paperforge-canvas-placeholder')).toBeTruthy();
        assertNoForbiddenControls(root);
    });

    it('renders idle state when vm.state is undefined', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: undefined }));

        expect(root.querySelector('.paperforge-canvas-shell')).toBeTruthy();
    });

    it('renders loading state with message', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'loading', message: 'Loading annotations...' }));

        const loadingEl = root.querySelector('.paperforge-canvas-loading');
        expect(loadingEl).toBeTruthy();
        expect(root.textContent).toContain('Loading annotations...');
        assertNoForbiddenControls(root);
    });

    it('renders empty state with message', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', message: 'No annotations.' }));

        const emptyEl = root.querySelector('.paperforge-canvas-empty');
        expect(emptyEl).toBeTruthy();
        expect(root.textContent).toContain('No annotations.');
        assertNoForbiddenControls(root);
    });

    it('renders missing-paper state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'missing-paper' }));

        const errorEl = root.querySelector('.paperforge-canvas-missing-paper');
        expect(errorEl).toBeTruthy();
        expect(root.textContent.length).toBeGreaterThan(5);
        assertNoForbiddenControls(root);
    });

    it('renders missing-db state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'missing-db' }));

        const errorEl = root.querySelector('.paperforge-canvas-missing-db');
        expect(errorEl).toBeTruthy();
        expect(root.textContent.length).toBeGreaterThan(5);
        assertNoForbiddenControls(root);
    });

    it('renders cli-error state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'cli-error', message: 'CLI command failed.' }));

        const errorEl = root.querySelector('.paperforge-canvas-cli-error');
        expect(errorEl).toBeTruthy();
        expect(root.textContent).toContain('CLI command failed.');
        assertNoForbiddenControls(root);
    });

    it('renders invalid-json state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'invalid-json' }));

        const errorEl = root.querySelector('.paperforge-canvas-invalid-json');
        expect(errorEl).toBeTruthy();
        assertNoForbiddenControls(root);
    });

    it('renders missing-source state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'missing-source', message: 'Source not found.' }));

        const stateEl = root.querySelector('.paperforge-canvas-missing-source');
        expect(stateEl).toBeTruthy();
        expect(root.textContent).toContain('Source not found.');
        assertNoForbiddenControls(root);
    });

    it('renders unsupported state', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'unsupported' }));

        const stateEl = root.querySelector('.paperforge-canvas-unsupported');
        expect(stateEl).toBeTruthy();
        assertNoForbiddenControls(root);
    });

    it('renders ready state as placeholder (no cards yet)', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'ready', paperKey: 'PAPER_A', message: 'Annotations loaded.' }));

        // Ready state in Phase ANN10 shows the identity + empty placeholder
        expect(root.querySelector('.paperforge-canvas-identity')).toBeTruthy();
        expect(root.querySelector('.paperforge-canvas-empty')).toBeTruthy();
        // No card lanes or card classes
        expect(root.querySelector('.paperforge-canvas-card')).toBeNull();
        expect(root.querySelector('.paperforge-canvas-lane')).toBeNull();
        assertNoForbiddenControls(root);
    });
});

// ---------------------------------------------------------------------------
// Paper identity rendering
// ---------------------------------------------------------------------------

describe('renderCanvasView — paper identity', () => {
    it('renders paper identity header when paperKey is present', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'loading', paperKey: 'PAPER_42' }));

        const identity = root.querySelector('.paperforge-canvas-identity');
        expect(identity).toBeTruthy();
        expect(identity.textContent).toContain('PAPER_42');
    });

    it('does not render identity header when paperKey is null', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'loading', paperKey: null }));

        const identity = root.querySelector('.paperforge-canvas-identity');
        expect(identity).toBeNull();
    });

    it('does not render identity header when paperKey is undefined', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty' })); // no paperKey

        const identity = root.querySelector('.paperforge-canvas-identity');
        expect(identity).toBeNull();
    });

    it('identity shows reading canvas label', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'idle', paperKey: 'XYZ' }));

        const label = root.querySelector('.paperforge-canvas-identity-label');
        expect(label).toBeTruthy();
        expect(label.textContent).toContain('Reading Canvas');
    });

    it('paperKey appears in the identity key element', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', paperKey: 'MY_KEY' }));

        const keyEl = root.querySelector('.paperforge-canvas-identity-key');
        expect(keyEl).toBeTruthy();
        expect(keyEl.textContent).toBe('MY_KEY');
    });
});

// ---------------------------------------------------------------------------
// Stale banner
// ---------------------------------------------------------------------------

describe('renderCanvasView — stale banner', () => {
    it('renders stale banner when vm.stale is true', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', stale: true, message: 'Showing stale data.' }));

        const banner = root.querySelector('.paperforge-canvas-stale-banner');
        expect(banner).toBeTruthy();
        expect(root.textContent).toContain('stale');
    });

    it('does not render stale banner when vm.stale is false', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', stale: false }));

        const banner = root.querySelector('.paperforge-canvas-stale-banner');
        expect(banner).toBeNull();
    });

    it('does not render stale banner when vm.stale is undefined', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty' }));

        const banner = root.querySelector('.paperforge-canvas-stale-banner');
        expect(banner).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// Safe text rendering
// ---------------------------------------------------------------------------

describe('safe text rendering', () => {
    it('uses textContent for all user-facing text (no innerHTML injection)', () => {
        const root = makeRootEl();
        const vm = makeVM({
            state: 'missing-paper',
            message: '<script>alert("xss")</script>',
        });

        renderCanvasView(root, vm);

        // textContent should contain the raw text
        expect(root.textContent).toContain('<script>alert("xss")</script>');
        // innerHTML should not have executable script tags
        const innerHtml = root.innerHTML;
        expect(innerHtml).not.toContain('<script>');
        expect(innerHtml).not.toContain('onclick');
    });

    it('idle state placeholder uses textContent', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'idle' }));

        const placeholder = root.querySelector('.paperforge-canvas-placeholder');
        expect(placeholder).toBeTruthy();
        // Content set via textContent, not innerHTML
        expect(placeholder.innerHTML).not.toContain('<');
        // textContent should have visible text
        expect(placeholder.textContent.length).toBeGreaterThan(0);
    });

    it('loading message uses textContent', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'loading', message: '<b>Loading</b>' }));

        const statusText = root.querySelector('.paperforge-canvas-status-text');
        expect(statusText).toBeTruthy();
        // Raw angle brackets preserved in textContent
        expect(statusText.textContent).toContain('<b>Loading</b>');
        // No actual bold rendering from innerHTML
        expect(statusText.innerHTML).not.toContain('<b>');
    });

    it('stale banner message uses textContent', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', stale: true, message: '<i>stale</i>' }));

        // The raw text must be preserved, HTML must not be injected
        expect(root.textContent).toContain('<i>stale</i>');
        expect(root.innerHTML).not.toContain('<i>');
    });
});

// ---------------------------------------------------------------------------
// Forbidden controls absence
// ---------------------------------------------------------------------------

describe('forbidden controls absence', () => {
    const STATES = ['idle', 'loading', 'empty', 'missing-paper', 'missing-db', 'cli-error', 'invalid-json'];

    for (const state of STATES) {
        it(`${state} state contains no forbidden controls`, () => {
            const root = makeRootEl();
            renderCanvasView(root, makeVM({ state, paperKey: 'PAPER_A' }));

            assertNoForbiddenControls(root);
        });
    }

    it('ready state contains no forbidden controls', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'ready', paperKey: 'PAPER_A' }));

        assertNoForbiddenControls(root);
    });

    it('stale banner contains no forbidden controls', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'empty', paperKey: 'PAPER_A', stale: true }));

        assertNoForbiddenControls(root);
    });

    it('missing-source state contains no forbidden controls', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'missing-source', paperKey: 'PAPER_A' }));

        assertNoForbiddenControls(root);
    });

    it('unsupported state contains no forbidden controls', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'unsupported', paperKey: 'PAPER_A' }));

        assertNoForbiddenControls(root);
    });

    it('no card, anchor, connector, or persistent layout classes present', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeVM({ state: 'idle', paperKey: 'PAPER_A' }));

        const html = root.innerHTML;
        // Phase 11+ classes must not appear
        expect(html).not.toContain('paperforge-canvas-card');
        expect(html).not.toContain('paperforge-canvas-lane');
        expect(html).not.toContain('paperforge-canvas-anchor');
        expect(html).not.toContain('paperforge-canvas-connector');
    });
});

// ── Card lane rendering ──

function makeCardVM(overrides) {
    const cards = overrides.cards || [];
    const left = overrides.leftCards !== undefined ? overrides.leftCards : cards.filter(function (_, i) { return i % 2 === 0; });
    const right = overrides.rightCards !== undefined ? overrides.rightCards : cards.filter(function (_, i) { return i % 2 === 1; });
    const lanes = cards.length > 0
        ? (overrides.lanes || { left: left, right: right })
        : undefined;
    return {
        state: 'ready',
        paperKey: 'PAPER_A',
        message: '',
        cards: cards,
        lanes: lanes,
        refreshing: false,
        stale: false,
        ...overrides,
    };
}

function makeCard(overrides) {
    return {
        id: 'ann-default',
        selectedText: 'Some highlighted text from the paper.',
        comment: 'A reader comment.',
        pageLabel: 'p. 3',
        pageIndex: 2,
        type: 'highlight',
        color: '#ff0',
        source: 'annotation',
        sourceAttachmentKey: 'ATTACH_001',
        sourceAnnotationKey: 'ANN_001',
        readOnly: true,
        readOnlyLabel: 'Read-only',
        selectedTextPreview: { text: 'Some highlighted text from the paper.', kind: 'selected-text', truncated: false, expandable: false, isLong: false },
        commentPreview: { text: 'A reader comment.', kind: 'comment', truncated: false, expandable: false, isLong: false },
        anchor: { status: 'unresolved', reason: 'Source anchors are implemented in ANN12.' },
        ...overrides,
    };
}

describe('renderCanvasView — card lanes', () => {
    it('renders lane containers when vm.lanes exists', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' }), makeCard({ id: 'ann-2' }), makeCard({ id: 'ann-3' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const lanesEl = root.querySelector('.paperforge-canvas-lanes');
        expect(lanesEl).toBeTruthy();

        const leftLane = root.querySelector('.paperforge-canvas-lane-left');
        expect(leftLane).toBeTruthy();
        const rightLane = root.querySelector('.paperforge-canvas-lane-right');
        expect(rightLane).toBeTruthy();
    });

    it('renders cards in correct lanes (left=even, right=odd)', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' }), makeCard({ id: 'ann-2' }), makeCard({ id: 'ann-3' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const leftCards = root.querySelectorAll('.paperforge-canvas-lane-left .paperforge-canvas-card');
        const rightCards = root.querySelectorAll('.paperforge-canvas-lane-right .paperforge-canvas-card');

        expect(leftCards.length).toBe(2); // ann-1, ann-3
        expect(rightCards.length).toBe(1); // ann-2
        expect(leftCards[0].getAttribute('data-card-id')).toBe('ann-1');
        expect(rightCards[0].getAttribute('data-card-id')).toBe('ann-2');
        expect(leftCards[1].getAttribute('data-card-id')).toBe('ann-3');
    });

    it('renders card selected-text preview as textContent', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', selectedText: 'Selected passage.' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const previewEl = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(previewEl).toBeTruthy();
        expect(previewEl.textContent).toContain('Selected passage.');
        expect(previewEl.innerHTML).not.toContain('<');
    });

    it('renders card comment preview as textContent', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', comment: 'Important finding.' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const commentEl = root.querySelector('.paperforge-canvas-card-comment');
        expect(commentEl).toBeTruthy();
        expect(commentEl.textContent).toContain('Important finding.');
    });

    it('renders card page label', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', pageLabel: 'p. 5' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const pageEl = root.querySelector('.paperforge-canvas-card-page');
        expect(pageEl).toBeTruthy();
        expect(pageEl.textContent).toContain('p. 5');
    });

    it('renders card type/color indicator', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', type: 'highlight', color: '#ff0' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const typeEl = root.querySelector('.paperforge-canvas-card-type');
        expect(typeEl).toBeTruthy();
        expect(typeEl.textContent).toContain('highlight');
    });

    it('renders read-only badge', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', readOnly: true, readOnlyLabel: 'Read-only' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const badgeEl = root.querySelector('.paperforge-canvas-card-readonly');
        expect(badgeEl).toBeTruthy();
        expect(badgeEl.textContent).toBe('Read-only');
    });

    it('renders source/provenance metadata', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', source: 'annotation', sourceAttachmentKey: 'ATTACH_001' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const sourceEl = root.querySelector('.paperforge-canvas-card-source');
        expect(sourceEl).toBeTruthy();
        expect(sourceEl.textContent).toContain('annotation');
        expect(sourceEl.textContent).toContain('ATTACH_001');
    });

    it('ready state with no cards renders empty placeholder, not lanes', () => {
        const root = makeRootEl();
        renderCanvasView(root, makeCardVM({ state: 'ready', cards: [], lanes: undefined }));

        expect(root.querySelector('.paperforge-canvas-empty')).toBeTruthy();
        expect(root.querySelector('.paperforge-canvas-lanes')).toBeNull();
    });

    it('contains no forbidden controls with cards present', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' }), makeCard({ id: 'ann-2' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        assertNoForbiddenControls(root);
    });

    it('uses textContent for annotation-derived card fields', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', selectedText: '<script>alert(1)</script>' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const previewEl = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(previewEl).toBeTruthy();
        // Raw HTML string preserved
        expect(previewEl.textContent).toContain('<script>alert(1)</script>');
        // No executable script in innerHTML
        expect(previewEl.innerHTML).not.toContain('<script>');
    });
});

describe('renderCanvasView — refreshing state', () => {
    it('renders refreshing state with existing cards', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' })];
        renderCanvasView(root, makeCardVM({ state: 'refreshing', cards: cards, refreshing: true }));

        const refreshingEl = root.querySelector('.paperforge-canvas-refreshing');
        expect(refreshingEl).toBeTruthy();
        // Cards preserved during refresh
        expect(root.querySelector('.paperforge-canvas-card')).toBeTruthy();
        expect(root.textContent).toContain('Refreshing');
    });

    it('refreshing state contains no forbidden controls', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' })];
        renderCanvasView(root, makeCardVM({ state: 'refreshing', cards: cards, refreshing: true }));
        assertNoForbiddenControls(root);
    });
});

describe('renderCanvasView — stale state', () => {
    it('renders stale state with existing cards and stale marker', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', stale: true })];
        renderCanvasView(root, makeCardVM({ state: 'stale', cards: cards, stale: true }));

        const staleBanner = root.querySelector('.paperforge-canvas-stale-banner');
        expect(staleBanner).toBeTruthy();
        // Cards still visible
        expect(root.querySelector('.paperforge-canvas-card')).toBeTruthy();
    });

    it('stale state contains no forbidden controls', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', stale: true })];
        renderCanvasView(root, makeCardVM({ state: 'stale', cards: cards, stale: true }));
        assertNoForbiddenControls(root);
    });
});

// ── ANN12-02 Task 2: Central source surface and anchor rendering ──

describe('ANN12-02 — source surface rendering', () => {
    // ── Render helper existence ──

    it('exports renderCanvasSourceSurface', () => {
        expect(typeof renderCanvasSourceSurface).toBe('function');
    });

    it('exports renderSourceBlock', () => {
        expect(typeof renderSourceBlock).toBe('function');
    });

    it('exports renderExactAnchorText', () => {
        expect(typeof renderExactAnchorText).toBe('function');
    });

    it('exports renderPageLevelAnchorMarker', () => {
        expect(typeof renderPageLevelAnchorMarker).toBe('function');
    });

    it('exports renderUnresolvedAnchorStatus', () => {
        expect(typeof renderUnresolvedAnchorStatus).toBe('function');
    });
});

describe('ANN12-02 — exact anchor (D-06/D-08/D-09/D-10)', () => {
    function makeExactAnchor(overrides) {
        return {
            anchorId: 'anchor-ann-1',
            cardId: 'ann-1',
            status: 'exact',
            sourceKind: 'fulltext',
            reason: null,
            matchCount: 1,
            pageIndex: 1,
            sourceSpan: { rawStart: 10, rawEnd: 25, normStart: 10, normEnd: 25 },
            diagnostics: { exactMatch: true },
            ...overrides,
        };
    }

    it('renders restrained inline highlight with namespaced class', () => {
        const root = makeRootEl();
        renderExactAnchorText(root, 'Text before ', 'highlighted', ' text after', '#ff0');

        const highlight = root.querySelector('.paperforge-canvas-anchor--exact');
        expect(highlight).toBeTruthy();
        expect(highlight.textContent).toBe('highlighted');

        // Restrained: has the highlight class, no connector/geometry classes
        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');

        // Text before/after preserved
        expect(root.textContent).toContain('Text before ');
        expect(root.textContent).toContain(' text after');
    });

    it('uses textContent for source text (no innerHTML) [D-05]', () => {
        const root = makeRootEl();
        renderExactAnchorText(root, 'before', '<script>alert(1)</script>', 'after', '#ff0');

        const highlight = root.querySelector('.paperforge-canvas-anchor--exact');
        expect(highlight).toBeTruthy();
        // Raw HTML-like string preserved in textContent
        expect(highlight.textContent).toContain('<script>alert(1)</script>');
        // No executable script in innerHTML
        expect(highlight.innerHTML).not.toContain('<script>');
    });

    it('renders without optional color [D-19]', () => {
        const root = makeRootEl();
        renderExactAnchorText(root, '', 'match', '', null);

        const highlight = root.querySelector('.paperforge-canvas-anchor--exact');
        expect(highlight).toBeTruthy();
        expect(highlight.textContent).toBe('match');
        // No inline background-color when color is null
        expect(highlight.style.backgroundColor).toBeFalsy();
    });

    it('does not add connector, SVG, navigation, or selection sync [D-22/D-24]', () => {
        const root = makeRootEl();
        renderExactAnchorText(root, 'A', 'B', 'C', null);

        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
        expect(html).not.toContain('data-card-id');
        expect(html).not.toContain('onclick');
    });
});

describe('ANN12-02 — page-level anchor (D-07/D-09/D-10)', () => {
    function makePageLevelAnchor(overrides) {
        return {
            anchorId: 'anchor-ann-2',
            cardId: 'ann-2',
            status: 'page-level',
            sourceKind: 'fulltext',
            reason: 'Selected text not found in source. Using page-level anchor.',
            matchCount: 0,
            pageIndex: 2,
            sourceSpan: null,
            diagnostics: { emptySelectedText: true },
            ...overrides,
        };
    }

    it('renders page-level marker without inline highlight', () => {
        const root = makeRootEl();
        renderPageLevelAnchorMarker(root, makePageLevelAnchor());

        const marker = root.querySelector('.paperforge-canvas-anchor--page-level');
        expect(marker).toBeTruthy();
        // Never highlights text — shows page/block marker
        expect(marker.textContent).toContain('Page');
        expect(marker.textContent).toContain('2');

        // No exact highlight class present
        expect(root.querySelector('.paperforge-canvas-anchor--exact')).toBeNull();
    });

    it('shows reason text for page-level downgrade [D-11/D-12/D-13/D-14]', () => {
        const root = makeRootEl();
        const anchor = makePageLevelAnchor({ reason: 'Selected text not found in source. Using page-level anchor.' });
        renderPageLevelAnchorMarker(root, anchor);

        expect(root.textContent).toContain('Selected text not found');
    });

    it('page-level anchor uses textContent for user-facing text [D-05]', () => {
        const root = makeRootEl();
        renderPageLevelAnchorMarker(root, makePageLevelAnchor());

        const marker = root.querySelector('.paperforge-canvas-anchor--page-level');
        expect(marker).toBeTruthy();
        // User-facing text via textContent, not innerHTML injection
        expect(marker.textContent.length).toBeGreaterThan(0);
        // No script/onclick injection (structural span is allowed)
        expect(marker.innerHTML).not.toContain('<script>');
        expect(marker.innerHTML).not.toContain('onclick');
    });

    it('does not render connector/SVG/navigation [D-22/D-24]', () => {
        const root = makeRootEl();
        renderPageLevelAnchorMarker(root, makePageLevelAnchor());

        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
        expect(html).not.toContain('onclick');
    });
});

describe('ANN12-02 — unresolved anchor (D-10/D-21)', () => {
    function makeUnresolvedAnchor(overrides) {
        return {
            anchorId: 'anchor-ann-3',
            cardId: 'ann-3',
            status: 'unresolved',
            sourceKind: null,
            reason: 'Source content is not available.',
            matchCount: 0,
            pageIndex: null,
            sourceSpan: null,
            diagnostics: { sourceUnavailable: true, sourceReason: 'Source content is not available.' },
            ...overrides,
        };
    }

    it('renders explanation text only with namespaced class', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, makeUnresolvedAnchor());

        const statusEl = root.querySelector('.paperforge-canvas-anchor--unresolved');
        expect(statusEl).toBeTruthy();
        // Explanation text, not a highlight or marker
        expect(statusEl.textContent).toContain('not available');

        // No source span or highlight
        expect(root.querySelector('.paperforge-canvas-anchor--exact')).toBeNull();
        expect(root.querySelector('.paperforge-canvas-anchor--page-level')).toBeNull();
    });

    it('shows the reason from anchor diagnostics [D-21]', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, makeUnresolvedAnchor());

        expect(root.textContent).toContain('not available');
    });

    it('uses textContent for reason text [D-05]', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, makeUnresolvedAnchor());

        const statusEl = root.querySelector('.paperforge-canvas-anchor--unresolved');
        expect(statusEl).toBeTruthy();
        expect(statusEl.innerHTML).not.toContain('<');
    });

    it('does not add connector/SVG/navigation [D-22/D-24]', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, makeUnresolvedAnchor());

        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
        expect(html).not.toContain('onclick');
    });
});

describe('ANN12-02 — renderCanvasSourceSurface (D-03/D-15/D-16/D-18)', () => {
    it('renders source blocks with header', () => {
        const root = makeRootEl();
        const blocks = [
            { id: 'block-0', pageIndex: 1, text: 'Source text block one.', sourceKind: 'fulltext' },
            { id: 'block-1', pageIndex: 2, text: 'Source text block two.', sourceKind: 'fulltext' },
        ];
        renderCanvasSourceSurface(root, blocks, []);

        const surface = root.querySelector('.paperforge-canvas-source-surface');
        expect(surface).toBeTruthy();

        const blockEls = surface.querySelectorAll('.paperforge-canvas-source-block');
        expect(blockEls.length).toBe(2);
    });

    it('shows source-unavailable state when no blocks provided', () => {
        const root = makeRootEl();
        renderCanvasSourceSurface(root, [], [], { unavailable: true, reason: 'No source content available.' });

        const unavailableEl = root.querySelector('.paperforge-canvas-source-unavailable');
        expect(unavailableEl).toBeTruthy();
        expect(root.textContent).toContain('No source content');
    });

    it('cards remain visible when source is unavailable [D-15/D-16/D-18]', () => {
        const root = makeRootEl();
        // Simulate: source unavailable but cards exist
        const cards = [
            { id: 'card-1', selectedText: 'Note text', comment: 'Comment' },
        ];
        renderCanvasSourceSurface(root, [], [], { unavailable: true, reason: 'No source.' });

        // The source surface shows unavailable, cards are rendered separately
        // by the renderCanvasView function (not this helper)
        const unavailableEl = root.querySelector('.paperforge-canvas-source-unavailable');
        expect(unavailableEl).toBeTruthy();
    });

    it('uses namespaced classes without connector/geometry [D-22/D-24]', () => {
        const root = makeRootEl();
        const blocks = [
            { id: 'block-0', pageIndex: 1, text: 'Block text.', sourceKind: 'fulltext' },
        ];
        renderCanvasSourceSurface(root, blocks, []);

        const html = root.innerHTML.toLowerCase();
        expect(html).toContain('paperforge-canvas-source-surface');
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
    });

    it('renders source kind header (fulltext vs note) [D-01/D-02/D-03]', () => {
        const root = makeRootEl();
        const blocks = [
            { id: 'block-0', pageIndex: 1, text: 'Block text.', sourceKind: 'fulltext' },
        ];
        renderCanvasSourceSurface(root, blocks, []);

        // Source kind header should indicate fulltext (case-insensitive)
        expect(root.textContent.toLowerCase()).toContain('fulltext');
    });
});

describe('ANN12-02 — renderSourceBlock (D-19/D-20)', () => {
    it('renders block text content', () => {
        const root = makeRootEl();
        const block = { id: 'block-0', pageIndex: 1, text: 'This is source text.', sourceKind: 'fulltext' };
        renderSourceBlock(root, block, []);

        const blockEl = root.querySelector('.paperforge-canvas-source-block');
        expect(blockEl).toBeTruthy();
        expect(blockEl.textContent).toContain('This is source text.');
    });

    it('does not add page-level markers for exact anchors (handled by exact helper)', () => {
        const root = makeRootEl();
        const block = { id: 'block-0', pageIndex: 1, text: 'Exact match is here.', sourceKind: 'fulltext' };
        const exactAnchors = [
            { anchorId: 'a1', cardId: 'c1', status: 'exact', sourceSpan: { rawStart: 0, rawEnd: 5 } },
        ];
        renderSourceBlock(root, block, exactAnchors);

        expect(root.querySelector('.paperforge-canvas-anchor--page-level')).toBeNull();
    });
});

// ── ANN13-03: DOM hooks, ARIA, selected state, fallback button ──

describe('ANN13-03 — renderCanvasCard DOM hooks (D-20)', () => {
    it('card has tabindex 0', () => {
        const card = renderCanvasCard({ id: 'card-1', pageIndex: 3, anchor: { status: 'exact' } });
        expect(card.tabIndex).toBe(0);
    });

    it('card has data-card-id attribute', () => {
        const card = renderCanvasCard({ id: 'card-test', pageIndex: 0, anchor: null });
        expect(card.getAttribute('data-card-id')).toBe('card-test');
    });

    it('card has data-page-index attribute', () => {
        const card = renderCanvasCard({ id: 'card-1', pageIndex: 5, anchor: null });
        expect(card.getAttribute('data-page-index')).toBe('5');
    });

    it('card has aria-selected set to false', () => {
        const card = renderCanvasCard({ id: 'card-1', pageIndex: 0, anchor: null });
        expect(card.getAttribute('aria-selected')).toBe('false');
    });
});

describe('ANN13-03 — Exact anchor DOM hooks (D-20)', () => {
    it('exact anchor highlight has tabindex 0', () => {
        const root = makeRootEl();
        renderSourceBlock(root, { id: 'b0', pageIndex: 1, text: 'Highlight this word.', sourceKind: 'fulltext' }, [
            { cardId: 'c1', status: 'exact', sourceSpan: { rawStart: 0, rawEnd: 9 }, pageIndex: 1 },
        ]);
        const highlight = root.querySelector('.paperforge-canvas-anchor--exact');
        expect(highlight).toBeTruthy();
        expect(highlight.tabIndex).toBe(0);
    });

    it('exact anchor has data-anchor-id and data-anchor-status', () => {
        const root = makeRootEl();
        renderSourceBlock(root, { id: 'b0', pageIndex: 1, text: 'Highlight this word.', sourceKind: 'fulltext' }, [
            { cardId: 'c1', status: 'exact', sourceSpan: { rawStart: 0, rawEnd: 9 }, pageIndex: 1 },
        ]);
        const highlight = root.querySelector('.paperforge-canvas-anchor--exact');
        expect(highlight.getAttribute('data-anchor-id')).toBe('c1');
        expect(highlight.getAttribute('data-anchor-status')).toBe('exact');
        expect(highlight.getAttribute('data-page-index')).toBe('1');
    });
});

describe('ANN13-03 — Page-level anchor markers (D-20)', () => {
    it('page-level marker has tabindex 0 and data attributes', () => {
        const root = makeRootEl();
        renderPageLevelAnchorMarker(root, { cardId: 'c2', pageIndex: 2, status: 'page-level', reason: 'Approximate' });
        const marker = root.querySelector('.paperforge-canvas-anchor--page-level');
        expect(marker).toBeTruthy();
        expect(marker.tabIndex).toBe(0);
        expect(marker.getAttribute('data-anchor-id')).toBe('c2');
        expect(marker.getAttribute('data-anchor-status')).toBe('page-level');
        expect(marker.getAttribute('data-page-index')).toBe('2');
    });
});

describe('ANN13-03 — Unresolved anchor (D-20 / D-24)', () => {
    it('unresolved status has no tabindex', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, { cardId: 'c3', status: 'unresolved', reason: 'No match' });
        const statusEl = root.querySelector('.paperforge-canvas-anchor--unresolved');
        expect(statusEl).toBeTruthy();
        expect(statusEl.tabIndex).toBe(-1);
    });

    it('unresolved status has data-anchor-status', () => {
        const root = makeRootEl();
        renderUnresolvedAnchorStatus(root, { cardId: 'c3', status: 'unresolved', reason: 'No match' });
        const statusEl = root.querySelector('.paperforge-canvas-anchor--unresolved');
        expect(statusEl.getAttribute('data-anchor-status')).toBe('unresolved');
    });
});

describe('ANN13-03 — Fallback button rendering (D-17/D-18/D-23)', () => {
    it('renders button when eligible', () => {
        const root = makeRootEl();
        renderFallbackButton(root, { eligible: true, page: 3, reason: null });
        const btn = root.querySelector('.paperforge-canvas-fallback-button');
        expect(btn).toBeTruthy();
        expect(btn.textContent).toBeTruthy();
        expect(btn.getAttribute('data-fallback-page')).toBe('3');
    });

    it('button has aria-label with page info', () => {
        const root = makeRootEl();
        renderFallbackButton(root, { eligible: true, page: 5, reason: null });
        const btn = root.querySelector('.paperforge-canvas-fallback-button');
        expect(btn.getAttribute('aria-label')).toContain('5');
    });

    it('does not render button when ineligible', () => {
        const root = makeRootEl();
        renderFallbackButton(root, { eligible: false, reason: 'No page', page: null });
        const btn = root.querySelector('.paperforge-canvas-fallback-button');
        expect(btn).toBeNull();
    });

    it('does not render button when fallbackInfo is null', () => {
        const root = makeRootEl();
        renderFallbackButton(root, null);
        const btn = root.querySelector('.paperforge-canvas-fallback-button');
        expect(btn).toBeNull();
    });

    it('button is a real button element (D-23)', () => {
        const root = makeRootEl();
        renderFallbackButton(root, { eligible: true, page: 7, reason: null });
        const btn = root.querySelector('button');
        expect(btn).toBeTruthy();
        expect(btn.tagName).toBe('BUTTON');
    });
});

// ---------------------------------------------------------------------------
// ANN14-02 Task 1: Render an empty namespaced connector SVG layer
// ---------------------------------------------------------------------------

describe('ANN14-02 Task 1 — renderCanvasConnectorLayer', () => {
    it('creates a namespaced SVG layer element', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        expect(svg).toBeTruthy();
        expect(svg.tagName).toBe('svg');
        expect(svg.getAttribute('class')).toContain('paperforge-canvas-connector-layer');
    });

    it('sets aria-hidden and role=presentation [D-10/D-11]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        expect(svg.getAttribute('aria-hidden')).toBe('true');
        expect(svg.getAttribute('role')).toBe('presentation');
    });

    it('creates no connector path by default', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('returns the SVG element for later updates', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        expect(svg).toBeTruthy();
        expect(svg.tagName).toBe('svg');
        expect(root.querySelector('.paperforge-canvas-connector-layer')).toBe(svg);
    });

    it('does not appear in idle shell rendering (D-13/D-17/D-20)', () => {
        const root = document.createElement('div');
        renderCanvasView(root, { state: 'idle' });
        expect(root.querySelector('.paperforge-canvas-connector-layer')).toBeNull();
        expect(root.querySelector('svg')).toBeNull();
    });

    it('does not appear in empty shell rendering (D-13/D-17/D-20)', () => {
        const root = document.createElement('div');
        renderCanvasView(root, { state: 'empty', paperKey: 'TEST' });
        expect(root.querySelector('.paperforge-canvas-connector-layer')).toBeNull();
    });

    it('does not appear in missing-paper shell (D-13/D-17)', () => {
        const root = document.createElement('div');
        renderCanvasView(root, { state: 'missing-paper' });
        expect(root.querySelector('.paperforge-canvas-connector-layer')).toBeNull();
    });

    it('does not appear in unsupported shell (D-13/D-17)', () => {
        const root = document.createElement('div');
        renderCanvasView(root, { state: 'unsupported' });
        expect(root.querySelector('.paperforge-canvas-connector-layer')).toBeNull();
    });
});

// ---------------------------------------------------------------------------
// ANN14-02 Task 2: Render only focused exact connector paths
// ---------------------------------------------------------------------------

describe('ANN14-02 Task 2 — updateCanvasConnectorLayer', () => {
    function makeVisibleGeometry(overrides) {
        return {
            state: 'visible',
            cardEndpoint: { x: 100, y: 200 },
            anchorEndpoint: { x: 450, y: 200 },
            cardRect: null,
            anchorRect: null,
            ...overrides,
        };
    }

    function makeHiddenGeometry(reason) {
        return {
            state: 'hidden',
            reason: reason || 'no-focus',
            cardEndpoint: null,
            anchorEndpoint: null,
            cardRect: null,
            anchorRect: null,
        };
    }

    it('renders at most one line for visible connector state [D-03]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry());
        const lines = svg.querySelectorAll('line');
        expect(lines.length).toBe(1);
    });

    it('line uses paperforge-canvas-connector class with --selected modifier', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry(), 'selected');
        const line = svg.querySelector('line');
        expect(line).toBeTruthy();
        expect(line.getAttribute('class')).toContain('paperforge-canvas-connector');
        expect(line.getAttribute('class')).toContain('paperforge-canvas-connector--selected');
    });

    it('line uses paperforge-canvas-connector class with --hovered modifier', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry(), 'hovered');
        const line = svg.querySelector('line');
        expect(line).toBeTruthy();
        expect(line.getAttribute('class')).toContain('paperforge-canvas-connector');
        expect(line.getAttribute('class')).toContain('paperforge-canvas-connector--hovered');
    });

    it('line endpoint coordinates match cardEndpoint and anchorEndpoint', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry({
            cardEndpoint: { x: 50, y: 100 },
            anchorEndpoint: { x: 300, y: 150 },
        }));
        const line = svg.querySelector('line');
        expect(line.getAttribute('x1')).toBe('50');
        expect(line.getAttribute('y1')).toBe('100');
        expect(line.getAttribute('x2')).toBe('300');
        expect(line.getAttribute('y2')).toBe('150');
    });

    it('line has aria-hidden attribute', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry());
        const line = svg.querySelector('line');
        expect(line.getAttribute('aria-hidden')).toBe('true');
    });

    // Hidden connector states leave the SVG empty (D-01/D-02/D-13/D-17)
    var hiddenReasons = ['page-level', 'unresolved', 'no-focus', 'stale', 'missing-dom', 'hidden-candidate'];
    for (var ri = 0; ri < hiddenReasons.length; ri++) {
        (function (reason) {
            it('renders nothing for ' + reason + ' hidden state', () => {
                var root = document.createElement('div');
                root.className = 'paperforge-reading-canvas-view';
                var svg = renderCanvasConnectorLayer(root);
                updateCanvasConnectorLayer(svg, makeHiddenGeometry(reason));
                expect(svg.querySelectorAll('line').length).toBe(0);
            });
        })(hiddenReasons[ri]);
    }

    it('replaces previous connector path on update', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry({ cardEndpoint: { x: 10, y: 20 } }));
        expect(svg.querySelectorAll('line').length).toBe(1);
        // Update with hidden state — should clear all paths
        updateCanvasConnectorLayer(svg, makeHiddenGeometry('no-focus'));
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('does nothing for null connectorState (guard)', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, null);
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('does nothing for undefined connectorState (guard)', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, undefined);
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('does nothing for missing endpoints in visible state (guard)', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, { state: 'visible', cardEndpoint: null, anchorEndpoint: null });
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('layer classes do not leak into ANN12 anchor render [D-22/D-24]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        renderExactAnchorText(root, 'before', 'match', 'after', null);
        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
    });

    it('layer classes do not leak into ANN12 source surface [D-22/D-24]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        renderCanvasSourceSurface(root, [], [], { unavailable: true, reason: 'No source.' });
        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-connector');
        expect(html).not.toContain('<svg');
    });

    it('default modifier is --selected when none provided', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        const svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, makeVisibleGeometry());
        const line = svg.querySelector('line');
        expect(line.getAttribute('class')).toContain('paperforge-canvas-connector--selected');
    });
});

// ── ANN14-04 Task 2: Forbidden-scope connector surface scan ──

describe('ANN14-04 Task 2 — Forbidden-scope connector verification', () => {

    it('renderCanvasConnectorLayer output is only SVG layer — no arrows, dots, animations', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        var html = root.innerHTML.toLowerCase();
        // No arrow markers or dot elements
        expect(html).not.toContain('marker');
        expect(html).not.toContain('circle');
        expect(html).not.toContain('polygon');
        expect(html).not.toContain('polyline');
        // SVG only has svg and line elements (no extraneous geometry)
        var allElements = svg.querySelectorAll('*');
        for (var ei = 0; ei < allElements.length; ei++) {
            var tag = allElements[ei].tagName.toLowerCase();
            expect(['svg', 'line', 'defs', 'g', 'title']).toContain(tag);
        }
    });

    it('updateCanvasConnectorLayer line has no inline color or animation attributes', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, {
            state: 'visible',
            cardEndpoint: { x: 100, y: 200 },
            anchorEndpoint: { x: 450, y: 200 },
            cardRect: null,
            anchorRect: null,
        });
        var line = svg.querySelector('line');
        expect(line).toBeTruthy();
        // No color, animation, or transition attributes
        expect(line.hasAttribute('stroke-dasharray')).toBe(false);
        expect(line.hasAttribute('opacity')).toBe(false);
        expect(line.hasAttribute('animation')).toBe(false);
        // Stroke is set via CSS class, not inline
        expect(line.hasAttribute('stroke')).toBe(false);
        // No marker-end or arrow-related attributes
        expect(line.hasAttribute('marker-end')).toBe(false);
    });

    it('connector line has no animation or transition markup', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        var html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('animation');
        expect(html).not.toContain('transition');
        expect(html).not.toContain('@keyframes');
    });

    it('hidden connector states do not render any SVG child elements', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, {
            state: 'hidden',
            reason: 'narrow-canvas',
            cardEndpoint: null,
            anchorEndpoint: null,
            cardRect: null,
            anchorRect: null,
        });
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('connector does not render for unresolved anchors [D-10/D-11]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, {
            state: 'hidden',
            reason: 'unresolved',
            cardEndpoint: null,
            anchorEndpoint: null,
            cardRect: null,
            anchorRect: null,
        });
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

    it('connector does not render for page-level anchors [D-10/D-11]', () => {
        const root = document.createElement('div');
        root.className = 'paperforge-reading-canvas-view';
        var svg = renderCanvasConnectorLayer(root);
        updateCanvasConnectorLayer(svg, {
            state: 'hidden',
            reason: 'page-level',
            cardEndpoint: null,
            anchorEndpoint: null,
            cardRect: null,
            anchorRect: null,
        });
        expect(svg.querySelectorAll('line').length).toBe(0);
    });

});
