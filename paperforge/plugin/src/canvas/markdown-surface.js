'use strict';

function clearHost(host) {
    if (typeof host.empty === 'function') {
        host.empty();
        return;
    }
    host.replaceChildren();
}

async function renderMarkdownSurface({
    host,
    markdown,
    sourcePath,
    renderMarkdown,
}) {
    clearHost(host);

    const article = host.ownerDocument.createElement('article');
    host.appendChild(article);

    try {
        await renderMarkdown(markdown, article, sourcePath);
        return { state: 'ready', article };
    } catch (error) {
        clearHost(host);
        const errorElement = host.ownerDocument.createElement('div');
        errorElement.dataset.canvasState = 'render-error';
        errorElement.textContent = 'Unable to render this Markdown document.';
        host.appendChild(errorElement);
        return { state: 'render-error' };
    }
}

module.exports = {
    renderMarkdownSurface,
};
