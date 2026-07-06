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
