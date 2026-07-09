import { describe, expect, it } from 'vitest';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const {
    applyDomHighlights,
    buildTextNodeIndex,
} = require('../src/canvas');

describe('canvas DOM anchors', () => {
    it('indexes all text nodes and marks blocked nodes without compressing offsets', () => {
        const article = document.createElement('article');
        article.innerHTML = [
            '<p>Alpha <strong>beta</strong> gamma.</p>',
            '<script>ignored script</script>',
            '<style>ignored style</style>',
            '<mark>ignored mark</mark>',
        ].join('');

        const index = buildTextNodeIndex(article);

        expect(index.map(({ start, end, node, blocked }) => ({
            start,
            end,
            text: node.nodeValue,
            blocked,
        }))).toEqual([
            { start: 0, end: 6, text: 'Alpha ', blocked: false },
            { start: 6, end: 10, text: 'beta', blocked: false },
            { start: 10, end: 17, text: ' gamma.', blocked: false },
            { start: 17, end: 31, text: 'ignored script', blocked: true },
            { start: 31, end: 44, text: 'ignored style', blocked: true },
            { start: 44, end: 56, text: 'ignored mark', blocked: true },
        ]);
    });

    it('applies a range across text nodes without changing article text', () => {
        const article = document.createElement('article');
        article.innerHTML = '<p>Alpha <strong>beta</strong> gamma.</p>';
        const originalText = article.textContent;

        const result = applyDomHighlights(article, [{
            id: 'ANN-1',
            renderedStart: 6,
            renderedEnd: 16,
            color: '#ffe08a',
        }]);

        const marks = article.querySelectorAll('[data-anchor-id="ANN-1"]');
        expect(result).toEqual({ applied: ['ANN-1'], unresolved: [] });
        expect(marks.length).toBeGreaterThan(0);
        expect(Array.from(marks).map((mark) => mark.textContent).join('')).toBe('beta gamma');
        expect(Array.from(marks).every((mark) => (
            mark.tagName === 'MARK'
            && mark.className === 'paperforge-canvas-highlight'
            && mark.getAttribute('data-anchor-status') === 'exact'
            && mark.getAttribute('tabindex') === '0'
            && mark.style.getPropertyValue('--paperforge-highlight-color') === '#ffe08a'
        ))).toBe(true);
        expect(article.textContent).toBe(originalText);
    });

    it('reports an out-of-bounds range without modifying the DOM', () => {
        const article = document.createElement('article');
        article.innerHTML = '<p>Alpha beta.</p>';
        const originalHtml = article.innerHTML;

        const result = applyDomHighlights(article, [{
            id: 'ANN-OOB',
            renderedStart: 6,
            renderedEnd: 99,
        }]);

        expect(result).toEqual({ applied: [], unresolved: ['ANN-OOB'] });
        expect(article.innerHTML).toBe(originalHtml);
    });

    it('applies multiple non-overlapping anchors without offset drift', () => {
        const article = document.createElement('article');
        article.innerHTML = '<p>Alpha <strong>beta</strong> gamma.</p>';

        const result = applyDomHighlights(article, [
            { id: 'ANN-A', renderedStart: 0, renderedEnd: 5 },
            { id: 'ANN-B', renderedStart: 6, renderedEnd: 16 },
        ]);

        expect(result).toEqual({ applied: ['ANN-A', 'ANN-B'], unresolved: [] });
        expect(article.querySelector('[data-anchor-id="ANN-A"]').textContent).toBe('Alpha');
        expect(Array.from(article.querySelectorAll('[data-anchor-id="ANN-B"]'))
            .map((mark) => mark.textContent).join('')).toBe('beta gamma');
        expect(article.textContent).toBe('Alpha beta gamma.');
    });

    it('reports invalid and overlapping anchors without partially applying them', () => {
        const article = document.createElement('article');
        article.innerHTML = '<p>Alpha beta gamma.</p>';

        const result = applyDomHighlights(article, [
            { id: 'ANN-VALID', renderedStart: 0, renderedEnd: 5 },
            { id: 'ANN-OVERLAP', renderedStart: 4, renderedEnd: 10 },
            { id: 'ANN-INVALID', renderedStart: 12, renderedEnd: 12 },
        ]);

        expect(result).toEqual({
            applied: ['ANN-VALID'],
            unresolved: ['ANN-OVERLAP', 'ANN-INVALID'],
        });
        expect(article.querySelectorAll('[data-anchor-id]')).toHaveLength(1);
        expect(article.textContent).toBe('Alpha beta gamma.');
    });

    it('does not treat markdown source offsets as rendered text offsets', () => {
        const article = document.createElement('article');
        article.innerHTML = '<p>Alpha <strong>beta</strong></p>';
        const originalHtml = article.innerHTML;

        const rawOnly = applyDomHighlights(article, [{
            id: 'ANN-MARKDOWN',
            rawStart: 6,
            rawEnd: 10,
        }]);

        expect(rawOnly).toEqual({
            applied: [],
            unresolved: ['ANN-MARKDOWN'],
        });
        expect(article.innerHTML).toBe(originalHtml);

        const rendered = applyDomHighlights(article, [{
            id: 'ANN-MARKDOWN',
            rawStart: 6,
            rawEnd: 10,
            renderedStart: 6,
            renderedEnd: 10,
        }]);

        expect(rendered).toEqual({
            applied: ['ANN-MARKDOWN'],
            unresolved: [],
        });
        expect(article.querySelector('[data-anchor-id="ANN-MARKDOWN"]').textContent)
            .toBe('beta');
    });

    it('reports duplicate ids as unresolved and creates one navigation target', () => {
        const article = document.createElement('article');
        article.textContent = 'Alpha beta gamma.';

        const result = applyDomHighlights(article, [
            { id: 'ANN-DUP', renderedStart: 0, renderedEnd: 5 },
            { id: 'ANN-DUP', renderedStart: 6, renderedEnd: 10 },
        ]);

        expect(result).toEqual({
            applied: ['ANN-DUP'],
            unresolved: ['ANN-DUP'],
        });
        expect(article.querySelectorAll('[data-anchor-id="ANN-DUP"]')).toHaveLength(1);
        expect(article.querySelector('[data-anchor-id="ANN-DUP"]').textContent)
            .toBe('Alpha');
    });

    it('preserves complete article offsets after an existing mark', () => {
        const article = document.createElement('article');
        article.innerHTML = 'A<mark>OLD</mark> beta longtail';
        const originalText = article.textContent;

        const result = applyDomHighlights(article, [{
            id: 'ANN-BETA',
            renderedStart: 5,
            renderedEnd: 9,
        }]);

        expect(result).toEqual({ applied: ['ANN-BETA'], unresolved: [] });
        expect(article.querySelector('[data-anchor-id="ANN-BETA"]').textContent)
            .toBe('beta');
        expect(article.querySelector('mark').textContent).toBe('OLD');
        expect(article.querySelector('mark mark')).toBeNull();
        expect(article.textContent).toBe(originalText);
    });

    it('reports a range intersecting blocked text as unresolved', () => {
        const article = document.createElement('article');
        article.innerHTML = 'A<mark>OLD</mark> beta longtail';
        const originalHtml = article.innerHTML;

        const result = applyDomHighlights(article, [{
            id: 'ANN-BLOCKED',
            renderedStart: 1,
            renderedEnd: 6,
        }]);

        expect(result).toEqual({
            applied: [],
            unresolved: ['ANN-BLOCKED'],
        });
        expect(article.innerHTML).toBe(originalHtml);
    });
});
