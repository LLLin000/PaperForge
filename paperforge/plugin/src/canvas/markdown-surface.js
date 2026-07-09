'use strict';

function clearHost(host) {
    if (typeof host.empty === 'function') {
        host.empty();
        return;
    }
    host.replaceChildren();
}

function formatErrorMessage(error) {
    if (
        error &&
        typeof error.message === 'string' &&
        error.message.trim()
    ) {
        return error.message;
    }
    if (typeof error === 'string' && error.trim()) {
        return error;
    }
    return 'Unknown error';
}

async function renderMarkdownSurface({
    host,
    markdown,
    sourcePath,
    renderMarkdown,
}) {
    clearHost(host);

    const article = host.ownerDocument.createElement('article');
    article.className = 'paperforge-canvas-article markdown-rendered';
    host.appendChild(article);

    try {
        await renderMarkdown(markdown, article, sourcePath);
        return { state: 'ready', article };
    } catch (error) {
        article.dataset.canvasState = 'render-error';
        article.textContent =
            `Could not render ${sourcePath}: ${formatErrorMessage(error)}`;
        return { state: 'render-error', article, error };
    }
}

module.exports = {
    renderMarkdownSurface,
};
