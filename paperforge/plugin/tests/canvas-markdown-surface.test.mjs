import { describe, expect, it, vi } from 'vitest';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { renderMarkdownSurface } = require('../src/canvas');

describe('renderMarkdownSurface', () => {
    it('renders the complete markdown through the injected renderer', async () => {
        const host = document.createElement('div');
        host.textContent = 'stale content';
        const renderMarkdown = vi.fn(async (markdown, element) => {
            element.textContent = markdown;
        });
        const markdown = '# Complete paper\n\nFull reading text.';

        const result = await renderMarkdownSurface({
            host,
            markdown,
            sourcePath: 'papers/example.md',
            renderMarkdown,
        });

        expect(renderMarkdown).toHaveBeenCalledWith(
            markdown,
            result.article,
            'papers/example.md'
        );
        expect(result).toEqual({
            state: 'ready',
            article: result.article,
        });
        expect(result.article.tagName).toBe('ARTICLE');
        expect(host.contains(result.article)).toBe(true);
        expect(result.article.textContent).toBe(markdown);
    });

    it('renders a visible error state when the markdown renderer throws', async () => {
        const host = document.createElement('div');
        host.textContent = 'stale content';
        const renderMarkdown = vi.fn(() => {
            throw new Error('renderer unavailable');
        });

        const result = await renderMarkdownSurface({
            host,
            markdown: '# Paper',
            sourcePath: 'papers/example.md',
            renderMarkdown,
        });

        const error = host.querySelector('[data-canvas-state="render-error"]');
        expect(result.state).toBe('render-error');
        expect(error).not.toBeNull();
        expect(error.textContent).not.toBe('');
        expect(error.hidden).toBe(false);
        expect(host.textContent).not.toBe('');
    });
});
