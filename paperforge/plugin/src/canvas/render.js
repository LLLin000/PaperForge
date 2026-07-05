/**
 * Canvas shell DOM rendering helpers for Phase ANN10.
 *
 * Renders read-only shell states: shell container, paper identity, loading,
 * empty, missing-paper, missing-db, CLI-error/invalid-json, missing-source,
 * unsupported, and stale banner.
 *
 * All user-facing text is inserted via `textContent` / Obsidian `setText()`
 * — never `innerHTML` for annotation content.  No edit, delete, create,
 * save, import, apply, write-back, database, evidence, or concept-card
 * controls appear in any state.
 *
 * @module canvas/render
 */

// ── Safe element creation helper ──

/**
 * Create a DOM element with optional class and text.
 *
 * Uses `document.createElement` for cross-environment compatibility
 * (works in jsdom and Obsidian).  Text is set via `textContent`.
 *
 * @param {string} tag - HTML tag name.
 * @param {object} [opts]
 * @param {string|string[]} [opts.cls] - Class name or array of class names.
 * @param {string} [opts.text] - Text content (set via textContent).
 * @returns {HTMLElement}
 */
function createEl(tag, opts) {
    const el = document.createElement(tag);
    if (opts) {
        if (opts.cls) {
            el.className = Array.isArray(opts.cls) ? opts.cls.join(' ') : opts.cls;
        }
        if (opts.text != null) {
            el.textContent = opts.text;
        }
    }
    return el;
}

/**
 * Empty all children from a DOM element.
 *
 * @param {HTMLElement} el
 */
function emptyEl(el) {
    while (el && el.firstChild) {
        el.removeChild(el.firstChild);
    }
}

// ── View-model shape ──
//
// The view-model passed to `renderCanvasView()` should have:
//   { state: string, paperKey: string|null, message: string,
//     annotations: Array, stale: boolean, errorCode: string|null }
//
// Minimal states: idle | loading | ready | empty | missing-paper |
//   missing-db | cli-error | invalid-json

// ── State renderers ──

/**
 * Render the paper identity header.
 *
 * @param {HTMLElement} contentEl - Parent element.
 * @param {string} paperKey - The paper identity label.
 */
function renderCanvasIdentity(contentEl, paperKey) {
    const header = createEl('div', { cls: 'paperforge-canvas-identity' });
    header.createEl = header.createEl || function (tag, opts) {
        const child = document.createElement(tag);
        if (opts) {
            if (opts.cls) child.className = Array.isArray(opts.cls) ? opts.cls.join(' ') : opts.cls;
            if (opts.text != null) child.textContent = opts.text;
            if (opts.title) child.setAttribute('title', opts.title);
        }
        this.appendChild(child);
        return child;
    };
    header.setText = header.setText || function (text) { this.textContent = text; };
    header.empty = header.empty || function () {
        while (this.firstChild) this.removeChild(this.firstChild);
    };

    const label = header.createEl('span', { cls: 'paperforge-canvas-identity-label', text: 'Reading Canvas' });
    const keyEl = header.createEl('span', { cls: 'paperforge-canvas-identity-key', text: paperKey });

    contentEl.appendChild(header);
    return header;
}

/**
 * Render the initial (idle) shell state.
 *
 * Shows a minimal placeholder indicating the canvas is ready but no
 * data has been loaded yet.
 *
 * @param {HTMLElement} contentEl
 */
function renderCanvasIdle(contentEl) {
    const shell = createEl('div', { cls: 'paperforge-canvas-shell' });
    const placeholder = createEl('div', { cls: 'paperforge-canvas-placeholder', text: 'Reading Canvas' });
    shell.appendChild(placeholder);
    contentEl.appendChild(shell);
}

/**
 * Render the loading state.
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model (uses vm.message).
 */
function renderCanvasLoading(contentEl, vm) {
    const stateEl = createEl('div', { cls: 'paperforge-canvas-loading' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Loading annotations...' });
    stateEl.appendChild(msg);
    contentEl.appendChild(stateEl);
}

/**
 * Render the empty state (no annotations found).
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasEmpty(contentEl, vm) {
    const emptyEl = createEl('div', { cls: 'paperforge-canvas-empty' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'This paper has no annotations yet.' });
    emptyEl.appendChild(msg);
    contentEl.appendChild(emptyEl);
}

/**
 * Render the missing-paper state (no paper key available).
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasMissingPaper(contentEl, vm) {
    const errorEl = createEl('div', { cls: 'paperforge-canvas-error paperforge-canvas-missing-paper' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'No paper is currently active. Open a recognized paper to view its annotations.' });
    errorEl.appendChild(msg);
    contentEl.appendChild(errorEl);
}

/**
 * Render the missing-db state (annotations database not available).
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasMissingDb(contentEl, vm) {
    const errorEl = createEl('div', { cls: 'paperforge-canvas-error paperforge-canvas-missing-db' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Annotation database is not available. Sync your library first.' });
    errorEl.appendChild(msg);
    contentEl.appendChild(errorEl);
}

/**
 * Render a CLI error state.
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasCliError(contentEl, vm) {
    const errorEl = createEl('div', { cls: 'paperforge-canvas-error paperforge-canvas-cli-error' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Failed to load annotations. Retry or check PaperForge status.' });
    errorEl.appendChild(msg);
    contentEl.appendChild(errorEl);
}

/**
 * Render an invalid-json state.
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasInvalidJson(contentEl, vm) {
    const errorEl = createEl('div', { cls: 'paperforge-canvas-error paperforge-canvas-invalid-json' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Could not read annotation data for this paper.' });
    errorEl.appendChild(msg);
    contentEl.appendChild(errorEl);
}

/**
 * Render the missing-source state (no fulltext or note path available).
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasMissingSource(contentEl, vm) {
    const stateEl = createEl('div', { cls: 'paperforge-canvas-missing-source' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Reading source content is not available for this paper.' });
    stateEl.appendChild(msg);
    contentEl.appendChild(stateEl);
}

/**
 * Render the unsupported state (canvas cannot be shown for this paper).
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasUnsupported(contentEl, vm) {
    const stateEl = createEl('div', { cls: 'paperforge-canvas-unsupported' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'This paper type is not supported by the Reading Canvas.' });
    stateEl.appendChild(msg);
    contentEl.appendChild(stateEl);
}

/**
 * Render a stale data banner.
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasStaleBanner(contentEl, vm) {
    const banner = createEl('div', { cls: 'paperforge-canvas-stale-banner' });
    const msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Showing previously loaded data. Refresh failed.' });
    banner.appendChild(msg);
    contentEl.appendChild(banner);
}

// ── Main render dispatch ──

/**
 * Render the canvas view from a view-model object.
 *
 * Clears the content element, then renders the appropriate state UI.
 * All user-facing text uses textContent — no innerHTML for annotation data.
 *
 * @param {HTMLElement} contentEl - The DOM element to render into.
 * @param {object} vm - View-model with at minimum `{ state }`.
 * @param {string} vm.state - One of: 'idle', 'loading', 'ready', 'empty',
 *   'missing-paper', 'missing-db', 'cli-error', 'invalid-json'.
 * @param {string|null} [vm.paperKey]
 * @param {string} [vm.message]
 * @param {boolean} [vm.stale]
 */
function renderCanvasView(contentEl, vm) {
    if (!contentEl) return;

    // Clear previous content
    emptyEl(contentEl);

    const state = (vm && vm.state) || 'idle';

    // ── Render paper identity header when we have a paperKey ──
    if (vm && vm.paperKey) {
        renderCanvasIdentity(contentEl, vm.paperKey);
    }

    // ── Render state-specific content ──
    switch (state) {
        case 'loading':
            renderCanvasLoading(contentEl, vm);
            break;
        case 'ready':
            // Phase ANN10 ready state is a placeholder — card lanes
            // and source surface belong to Phase 11+.
            renderCanvasEmpty(contentEl, { ...vm, message: vm.message || 'Annotations loaded. Card layout is available in a future phase.' });
            break;
        case 'empty':
            renderCanvasEmpty(contentEl, vm);
            break;
        case 'missing-paper':
            renderCanvasMissingPaper(contentEl, vm);
            break;
        case 'missing-db':
            renderCanvasMissingDb(contentEl, vm);
            break;
        case 'cli-error':
            renderCanvasCliError(contentEl, vm);
            break;
        case 'invalid-json':
            renderCanvasInvalidJson(contentEl, vm);
            break;
        case 'missing-source':
            renderCanvasMissingSource(contentEl, vm);
            break;
        case 'unsupported':
            renderCanvasUnsupported(contentEl, vm);
            break;
        default:
            renderCanvasIdle(contentEl);
            break;
    }

    // ── Stale overlay banner ──
    if (vm && vm.stale) {
        renderCanvasStaleBanner(contentEl, vm);
    }
}

module.exports = {
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
};
