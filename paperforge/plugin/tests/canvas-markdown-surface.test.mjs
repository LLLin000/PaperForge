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
        expect(host.textContent).not.toContain('stale content');
        expect(result.article.classList.contains('paperforge-canvas-article')).toBe(true);
        expect(result.article.classList.contains('markdown-rendered')).toBe(true);
        expect(result.article.textContent).toBe(markdown);
    });

    it('clears the host through the Obsidian empty helper', async () => {
        const host = document.createElement('div');
        host.textContent = 'stale content';
        host.empty = vi.fn(() => host.replaceChildren());

        const result = await renderMarkdownSurface({
            host,
            markdown: '# Paper',
            sourcePath: 'fulltext.md',
            renderMarkdown: vi.fn(),
        });

        expect(host.empty).toHaveBeenCalledOnce();
        expect(host.textContent).not.toContain('stale content');
        expect(host.firstElementChild).toBe(result.article);
    });

    it('renders a visible error state when the markdown renderer throws', async () => {
        const host = document.createElement('div');
        host.textContent = 'stale content';
        const rendererError = new Error('renderer unavailable');
        const renderMarkdown = vi.fn(() => {
            throw rendererError;
        });

        const result = await renderMarkdownSurface({
            host,
            markdown: '# Paper',
            sourcePath: 'fulltext.md',
            renderMarkdown,
        });

        const article = host.querySelector('article[data-canvas-state="render-error"]');
        expect(result).toEqual({
            state: 'render-error',
            article,
            error: rendererError,
        });
        expect(article).not.toBeNull();
        expect(article).toBe(result.article);
        expect(article.textContent).toBe(
            'Could not render fulltext.md: renderer unavailable'
        );
        expect(article.textContent).toContain(rendererError.message);
        expect(article.hidden).toBe(false);
        expect(host.children).toHaveLength(1);
    });
});
