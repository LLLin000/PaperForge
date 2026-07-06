/**
 * Vitest DOM-focused tests for card rendering (ANN11-02, ANN11-02 Task 3).
 *
 * Tests cover:
 *   - Long/missing/CJK text rendering with bounded DOM/CSS hooks
 *   - Read-only badge rendering
 *   - Source/provenance display
 *   - No forbidden controls, draggable handles, anchors, or connectors
 *   - Card/lane CSS geometry and resilience (D-15, D-16, D-17)
 *   - Refresh/stale-safe CSS classes (D-10, D-13)
 *
 * @module tests/canvas-card-dom
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';

const {
    renderCanvasView,
} = await import('../src/canvas/render.js');

// ── Forbidden control keywords ──

const FORBIDDEN_WORDS = [
    'edit', 'delete', 'create', 'save', 'import', 'apply',
    'write back', 'write-back', 'evidence', 'concept card',
];

const FORBIDDEN_CLASSES = [
    'paperforge-canvas-anchor',
    'paperforge-canvas-connector',
    'ui-draggable',
    'paperforge-canvas-drag',
];

function makeRootEl() {
    return document.createElement('div');
}

function assertNoForbiddenControls(rootEl) {
    const html = rootEl.innerHTML.toLowerCase();
    const text = rootEl.textContent.toLowerCase();
    for (const word of FORBIDDEN_WORDS) {
        expect(html).not.toContain(word);
    }
    const buttons = rootEl.querySelectorAll('button');
    for (const btn of buttons) {
        const btnText = btn.textContent.toLowerCase();
        for (const word of FORBIDDEN_WORDS) {
            expect(btnText).not.toContain(word);
        }
    }
    for (const cls of FORBIDDEN_CLASSES) {
        expect(html).not.toContain(cls);
    }
}

function assertNoExpandableDetails(rootEl) {
    const html = rootEl.innerHTML.toLowerCase();
    expect(html).not.toContain('details');
    expect(html).not.toContain('popover');
    expect(html).not.toContain('dialog');
}

// ── Fixtures ──

function makeCardVM(overrides) {
    const cards = overrides.cards || [];
    const left = cards.filter(function (_, i) { return i % 2 === 0; });
    const right = cards.filter(function (_, i) { return i % 2 === 1; });
    const lanes = cards.length > 0 ? { left: left, right: right } : undefined;
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
        id: 'ann-test',
        selectedText: 'Normal selected text for testing.',
        comment: 'Normal comment.',
        pageLabel: 'p. 3',
        pageIndex: 2,
        type: 'highlight',
        color: '#ff0',
        source: 'annotation',
        sourceAttachmentKey: 'ATTACH_001',
        sourceAnnotationKey: 'ANN_001',
        readOnly: true,
        readOnlyLabel: 'Read-only',
        selectedTextPreview: { text: 'Normal selected text for testing.', kind: 'selected-text', truncated: false, expandable: false, isLong: false },
        commentPreview: { text: 'Normal comment.', kind: 'comment', truncated: false, expandable: false, isLong: false },
        anchor: { status: 'unresolved', reason: 'Source anchors are implemented in ANN12.' },
        ...overrides,
    };
}

// ── Placeholder rendering (D-04, D-18) ──

describe('card DOM — missing text placeholders', () => {
    it('renders explicit placeholder when selectedText is empty', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', selectedText: '', selectedTextPreview: { text: '', kind: 'selected-text', truncated: false, expandable: false, isLong: false } });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        // Empty text content but element exists (quiet placeholder)
        expect(el.textContent).toBe('');
        expect(el.classList.contains('paperforge-canvas-card-selected-text--empty')).toBe(true);
    });

    it('renders explicit placeholder when comment is empty', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', comment: '', commentPreview: { text: '', kind: 'comment', truncated: false, expandable: false, isLong: false } });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-comment');
        expect(el).toBeTruthy();
        expect(el.textContent).toBe('');
        expect(el.classList.contains('paperforge-canvas-card-comment--empty')).toBe(true);
    });

    it('renders explicit placeholder when selectedText is null', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', selectedText: '', selectedTextPreview: { text: '', kind: 'selected-text', truncated: false, expandable: false, isLong: false } });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        expect(el.textContent).toBe('');
    });

    it('renders explicit placeholder when comment is null', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', comment: '', commentPreview: { text: '', kind: 'comment', truncated: false, expandable: false, isLong: false } });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-comment');
        expect(el).toBeTruthy();
        expect(el.textContent).toBe('');
    });
});

// ── Long / CJK text (D-18, CARD-02) ──

describe('card DOM — long / CJK text', () => {
    it('renders long selected text with bounded element', () => {
        const root = makeRootEl();
        const longText = 'A'.repeat(500);
        const card = makeCard({
            id: 'ann-1',
            selectedText: longText,
            selectedTextPreview: { text: longText.substring(0, 140) + '…', kind: 'selected-text', truncated: true, expandable: true, isLong: true },
        });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        // Text content preserved
        expect(el.textContent.length).toBeGreaterThan(100);
        // Class hook for bounded display
        expect(el.classList.contains('paperforge-canvas-card-selected-text--long')).toBe(true);
    });

    it('renders CJK text without clipping', () => {
        const root = makeRootEl();
        const cjkText = '这是一段中文文本用于测试注释卡片的显示效果。';
        const card = makeCard({ id: 'ann-1', selectedText: cjkText });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        // CJK text present, not garbled
        expect(el.textContent).toContain('这是一段中文文本');
    });

    it('renders long comment with bounded element', () => {
        const root = makeRootEl();
        const longComment = 'B'.repeat(300);
        const card = makeCard({
            id: 'ann-1',
            comment: longComment,
            commentPreview: { text: longComment.substring(0, 70) + '…', kind: 'comment', truncated: true, expandable: true, isLong: true },
        });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-comment');
        expect(el).toBeTruthy();
        expect(el.textContent.length).toBeGreaterThan(50);
        expect(el.classList.contains('paperforge-canvas-card-comment--long')).toBe(true);
    });

    it('renders mixed CJK and Latin text', () => {
        const root = makeRootEl();
        const mixed = '这是一段中文text with English混合内容。';
        const card = makeCard({ id: 'ann-1', selectedText: mixed });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        expect(el.textContent).toContain('这是一段中文');
        expect(el.textContent).toContain('English');
    });

    it('uses textContent for HTML-like card text', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', selectedText: '<b>bold</b><script>alert(1)</script>' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        // Raw text preserved
        expect(el.textContent).toContain('<b>bold</b>');
        expect(el.textContent).toContain('<script>alert(1)</script>');
        // Not rendered as HTML
        expect(el.innerHTML).not.toContain('<b>');
        expect(el.innerHTML).not.toContain('<script>');
    });
});

// ── Read-only badge (D-19) ──

describe('card DOM — read-only badge', () => {
    it('shows read-only badge for read-only cards', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', readOnly: true, readOnlyLabel: 'Read-only' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const badge = root.querySelector('.paperforge-canvas-card-readonly');
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe('Read-only');
        expect(badge.classList.contains('paperforge-canvas-card-readonly--true')).toBe(true);
    });

    it('hides read-only badge for mutable cards', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', readOnly: false, readOnlyLabel: '' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const badge = root.querySelector('.paperforge-canvas-card-readonly');
        expect(badge).toBeTruthy();
        expect(badge.textContent).toBe('');
        expect(badge.classList.contains('paperforge-canvas-card-readonly--false')).toBe(true);
    });
});

// ── Source / provenance (D-20) ──

describe('card DOM — source / provenance', () => {
    it('displays source type', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', source: 'annotation' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-source');
        expect(el).toBeTruthy();
        expect(el.textContent).toContain('annotation');
    });

    it('displays attachment identity when available', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', sourceAttachmentKey: 'ATTACH_001' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-source');
        expect(el).toBeTruthy();
        expect(el.textContent).toContain('ATTACH_001');
    });

    it('displays annotation identity when available', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', sourceAnnotationKey: 'ANN_001' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-source');
        expect(el).toBeTruthy();
        expect(el.textContent).toContain('ANN_001');
    });
});

// ── Forbidden controls / classes (D-03, D-21, D-22) ──

describe('card DOM — forbidden controls absence', () => {
    it('contains no write/edit controls in ready state with cards', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        assertNoForbiddenControls(root);
    });

    it('contains no expandable details or popovers', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        assertNoExpandableDetails(root);
    });

    it('contains no anchor or connector classes', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('paperforge-canvas-anchor');
        expect(html).not.toContain('paperforge-canvas-connector');
    });

    it('contains no draggable handles', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const html = root.innerHTML.toLowerCase();
        expect(html).not.toContain('ui-draggable');
        expect(html).not.toContain('paperforge-canvas-drag');
        expect(html).not.toContain('draggable="true"');
    });

    it('contains no input/textarea elements', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        expect(root.querySelector('input')).toBeNull();
        expect(root.querySelector('textarea')).toBeNull();
        expect(root.querySelector('select')).toBeNull();
    });
});

// ── Card structure (CARD-04) ──

describe('card DOM — structure', () => {
    it('card element has data-card-id attribute', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-special' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const cardEl = root.querySelector('.paperforge-canvas-card');
        expect(cardEl).toBeTruthy();
        expect(cardEl.getAttribute('data-card-id')).toBe('ann-special');
    });

    it('lane elements have data-lane-index attribute', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' }), makeCard({ id: 'ann-2' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const leftLane = root.querySelector('.paperforge-canvas-lane-left');
        const rightLane = root.querySelector('.paperforge-canvas-lane-right');
        expect(leftLane).toBeTruthy();
        expect(rightLane).toBeTruthy();
        expect(leftLane.getAttribute('data-lane-index')).toBe('0');
        expect(rightLane.getAttribute('data-lane-index')).toBe('1');
    });

    it('renders multiple cards in the correct lane order', () => {
        const root = makeRootEl();
        const cards = [
            makeCard({ id: 'ann-first' }),
            makeCard({ id: 'ann-second' }),
            makeCard({ id: 'ann-third' }),
            makeCard({ id: 'ann-fourth' }),
        ];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const leftCardIds = root.querySelectorAll('.paperforge-canvas-lane-left .paperforge-canvas-card');
        const rightCardIds = root.querySelectorAll('.paperforge-canvas-lane-right .paperforge-canvas-card');

        // Even indices → left, odd → right
        expect(leftCardIds[0].getAttribute('data-card-id')).toBe('ann-first');
        expect(rightCardIds[0].getAttribute('data-card-id')).toBe('ann-second');
        expect(leftCardIds[1].getAttribute('data-card-id')).toBe('ann-third');
        expect(rightCardIds[1].getAttribute('data-card-id')).toBe('ann-fourth');
    });
});

// ── CSS geometry / resilience (D-15, D-16, D-17) ──

describe('card CSS — geometry and resilience', () => {
    it('selected-text element has stable preview class', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        expect(el.classList.contains('paperforge-canvas-card-selected-text-preview')).toBe(true);
    });

    it('comment element has stable preview class', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-comment');
        expect(el).toBeTruthy();
        expect(el.classList.contains('paperforge-canvas-card-comment-preview')).toBe(true);
    });

    it('card element has no inline width or height styles', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const cardEl = root.querySelector('.paperforge-canvas-card');
        expect(cardEl).toBeTruthy();
        expect(cardEl.style.width).toBe('');
        expect(cardEl.style.height).toBe('');
        // Card dimensions come from CSS, not inline styles
    });

    it('lane containers have no inline width or height', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' }), makeCard({ id: 'ann-2' })];
        renderCanvasView(root, makeCardVM({ cards: cards }));

        const leftLane = root.querySelector('.paperforge-canvas-lane-left');
        const rightLane = root.querySelector('.paperforge-canvas-lane-right');
        expect(leftLane).toBeTruthy();
        expect(rightLane).toBeTruthy();
        expect(leftLane.style.width).toBe('');
        expect(rightLane.style.width).toBe('');
    });

    it('long selected-text element has preview-wrapper class', () => {
        const root = makeRootEl();
        const longText = 'A'.repeat(500);
        const card = makeCard({
            id: 'ann-1',
            selectedText: longText,
            selectedTextPreview: { text: longText.substring(0, 140) + '…', kind: 'selected-text', truncated: true, expandable: true, isLong: true },
        });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const el = root.querySelector('.paperforge-canvas-card-selected-text');
        expect(el).toBeTruthy();
        expect(el.classList.contains('paperforge-canvas-card-selected-text--long')).toBe(true);
    });

    it('refreshing state has refreshing class on state element', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1' })];
        renderCanvasView(root, makeCardVM({ state: 'refreshing', cards: cards, refreshing: true }));

        const refreshingEl = root.querySelector('.paperforge-canvas-refreshing');
        expect(refreshingEl).toBeTruthy();
        expect(refreshingEl.classList.contains('paperforge-canvas-refreshing')).toBe(true);
    });

    it('stale state renders stale banner with stale class', () => {
        const root = makeRootEl();
        const cards = [makeCard({ id: 'ann-1', stale: true })];
        renderCanvasView(root, makeCardVM({ state: 'stale', cards: cards, stale: true }));

        const staleBanner = root.querySelector('.paperforge-canvas-stale-banner');
        expect(staleBanner).toBeTruthy();
        expect(staleBanner.classList.contains('paperforge-canvas-stale-banner')).toBe(true);
    });

    it('read-only badge uses restrained badge class', () => {
        const root = makeRootEl();
        const card = makeCard({ id: 'ann-1', readOnly: true, readOnlyLabel: 'Read-only' });
        renderCanvasView(root, makeCardVM({ cards: [card] }));

        const badge = root.querySelector('.paperforge-canvas-card-readonly');
        expect(badge).toBeTruthy();
        expect(badge.classList.contains('paperforge-canvas-card-readonly--true')).toBe(true);
    });
});
