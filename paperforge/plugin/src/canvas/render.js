/**
 * Canvas shell DOM rendering helpers for Phase ANN10 and ANN11.
 *
 * Renders read-only shell states: shell container, paper identity, loading,
 * empty, missing-paper, missing-db, CLI-error/invalid-json, missing-source,
 * unsupported, stale banner, and card lane containers.
 *
 * All user-facing text is inserted via `textContent` / Obsidian `setText()`
 * — never `innerHTML` for annotation content.  No edit, delete, create,
 * save, import, apply, write-back, database, evidence, or concept-card
 * controls appear in any state.
 *
 * Card lane rendering (ANN11-02) produces left/right annotation card lanes
 * from the view-model's lane output.  Cards are read-only with no expandable
 * details, drawers, popovers, editable forms, anchors, connectors, or
 * draggable handles.
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

// ── i18n helper (ANN11 card labels) ──
//
// Provides zh/en text keys scoped to ANN11 card labels, placeholders,
// provenance, read-only badges, and state copy.  No unrelated ANN10
// shell text is duplicated here.

const _I18N = {
    en: {
        'card.selected_text': 'Selected Text',
        'card.comment': 'Comment',
        'card.page': 'Page',
        'card.type': 'Type',
        'card.source': 'Source',
        'card.read_only': 'Read-only',
        'card.read_only_label': 'Read-only',
        'card.no_comment': '',
        'card.no_selected_text': '',
        'card.attachment': 'Attachment',
        'card.annotation': 'Annotation',
        'state.refreshing': 'Refreshing annotations…',
        'state.stale': 'Showing previously loaded (stale) data.',
    },
    zh: {
        'card.selected_text': '选中文本',
        'card.comment': '备注',
        'card.page': '页码',
        'card.type': '类型',
        'card.source': '来源',
        'card.read_only': '只读',
        'card.read_only_label': '只读',
        'card.no_comment': '',
        'card.no_selected_text': '',
        'card.attachment': '附件',
        'card.annotation': '批注',
        'state.refreshing': '正在刷新批注…',
        'state.stale': '显示之前加载的（过期）数据。',
    },
};

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

// ── Card lane rendering (ANN11-02) ──

/**
 * Render a single read-only annotation card DOM element.
 *
 * Produces namespaced elements for selected-text preview, comment preview,
 * page, type/color, source/provenance, and read-only status per D-01, D-02,
 * D-19, and D-20.  All annotation-derived text uses textContent — no
 * innerHTML.  No expandable details, drawers, popovers, editable forms,
 * or controls per D-03, D-21, D-22.
 *
 * @param {object} card - Card object from buildCanvasCard().
 * @returns {HTMLElement} The card DOM element.
 */
function renderCanvasCard(card) {
    var cardEl = createEl('div', { cls: 'paperforge-canvas-card' });
    cardEl.setAttribute('data-card-id', card.id || '');

    // ── Selected text preview ──
    var selTextEl = createEl('div', {
        cls: 'paperforge-canvas-card-selected-text' + (card.selectedText === '' ? ' paperforge-canvas-card-selected-text--empty' : '') + (card.selectedTextPreview && card.selectedTextPreview.isLong ? ' paperforge-canvas-card-selected-text--long' : ''),
        text: card.selectedText || '',
    });
    cardEl.appendChild(selTextEl);

    // ── Comment preview ──
    var commentEl = createEl('div', {
        cls: 'paperforge-canvas-card-comment' + (card.comment === '' ? ' paperforge-canvas-card-comment--empty' : '') + (card.commentPreview && card.commentPreview.isLong ? ' paperforge-canvas-card-comment--long' : ''),
        text: card.comment || '',
    });
    cardEl.appendChild(commentEl);

    // ── Page label ──
    var pageEl = createEl('div', { cls: 'paperforge-canvas-card-page', text: card.pageLabel || '' });
    cardEl.appendChild(pageEl);

    // ── Type / color indicator ──
    var typeEl = createEl('div', { cls: 'paperforge-canvas-card-type', text: card.type || 'annotation' });
    if (card.color) {
        typeEl.style.borderLeftColor = card.color;
    }
    cardEl.appendChild(typeEl);

    // ── Source / provenance ──
    var sourceParts = [];
    if (card.source) sourceParts.push(card.source);
    if (card.sourceAttachmentKey) sourceParts.push(card.sourceAttachmentKey);
    if (card.sourceAnnotationKey) sourceParts.push(card.sourceAnnotationKey);
    var sourceEl = createEl('div', { cls: 'paperforge-canvas-card-source', text: sourceParts.join(' · ') || '' });
    cardEl.appendChild(sourceEl);

    // ── Read-only badge ──
    var badgeCls = 'paperforge-canvas-card-readonly';
    badgeCls += card.readOnly ? ' paperforge-canvas-card-readonly--true' : ' paperforge-canvas-card-readonly--false';
    var badgeEl = createEl('span', { cls: badgeCls, text: card.readOnlyLabel || '' });
    cardEl.appendChild(badgeEl);

    return cardEl;
}

/**
 * Render left and right card lane containers from a lanes object.
 *
 * Lane containers are named from ANN11-01's deterministic lane assignment
 * (D-07, D-08).  Lane order and lane/laneIndex are preserved — no
 * re-sorting, drag, or persistence.
 *
 * @param {HTMLElement} contentEl - Parent element.
 * @param {object} lanes - Lane object { left: Array, right: Array }.
 */
function renderCanvasCardLanes(contentEl, lanes) {
    if (!lanes) return;

    var lanesContainer = createEl('div', { cls: 'paperforge-canvas-lanes' });

    // Left lane
    var leftLaneEl = createEl('div', { cls: 'paperforge-canvas-lane-left' });
    leftLaneEl.setAttribute('data-lane-index', '0');
    (lanes.left || []).forEach(function (card) {
        leftLaneEl.appendChild(renderCanvasCard(card));
    });
    lanesContainer.appendChild(leftLaneEl);

    // Right lane
    var rightLaneEl = createEl('div', { cls: 'paperforge-canvas-lane-right' });
    rightLaneEl.setAttribute('data-lane-index', '1');
    (lanes.right || []).forEach(function (card) {
        rightLaneEl.appendChild(renderCanvasCard(card));
    });
    lanesContainer.appendChild(rightLaneEl);

    contentEl.appendChild(lanesContainer);
}

/**
 * Render the refreshing state with preserved cards.
 *
 * Shows a "refreshing" message while existing cards remain visible.
 *
 * @param {HTMLElement} contentEl
 * @param {object} vm - View-model.
 */
function renderCanvasRefreshing(contentEl, vm) {
    var stateEl = createEl('div', { cls: 'paperforge-canvas-refreshing' });
    var msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: vm.message || 'Refreshing annotations…' });
    stateEl.appendChild(msg);
    contentEl.appendChild(stateEl);

    // Preserve existing cards
    if (vm.lanes) {
        renderCanvasCardLanes(contentEl, vm.lanes);
    }
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
 * @param {string} vm.state - One of: 'idle', 'loading', 'relaxed', 'ready',
 *   'refreshing', 'stale', 'empty', 'missing-paper', 'missing-db',
 *   'cli-error', 'invalid-json', 'missing-source', 'unsupported'.
 * @param {string|null} [vm.paperKey]
 * @param {string} [vm.message]
 * @param {boolean} [vm.stale]
 * @param {boolean} [vm.refreshing]
 * @param {Array} [vm.cards]
 * @param {object} [vm.lanes] - { left: Array, right: Array }
 */
function renderCanvasView(contentEl, vm) {
    if (!contentEl) return;

    // Clear previous content
    emptyEl(contentEl);

    var v = vm || {};
    var state = v.state || 'idle';

    // ── Render paper identity header when we have a paperKey ──
    if (v.paperKey) {
        renderCanvasIdentity(contentEl, v.paperKey);
    }

    // ── Render state-specific content ──
    switch (state) {
        case 'loading':
            renderCanvasLoading(contentEl, v);
            break;
        case 'ready':
            // ANN11-02: render card lanes when available, else show empty
            if (v.lanes) {
                renderCanvasCardLanes(contentEl, v.lanes);
            } else {
                renderCanvasEmpty(contentEl, { ...v, message: v.message || 'Annotations loaded. Card layout is available in a future phase.' });
            }
            break;
        case 'refreshing':
            renderCanvasRefreshing(contentEl, v);
            break;
        case 'stale':
            // Show cards + stale banner
            if (v.lanes) {
                renderCanvasCardLanes(contentEl, v.lanes);
            }
            renderCanvasStaleBanner(contentEl, v);
            break;
        case 'empty':
            renderCanvasEmpty(contentEl, v);
            break;
        case 'missing-paper':
            renderCanvasMissingPaper(contentEl, v);
            break;
        case 'missing-db':
            renderCanvasMissingDb(contentEl, v);
            break;
        case 'cli-error':
            renderCanvasCliError(contentEl, v);
            break;
        case 'invalid-json':
            renderCanvasInvalidJson(contentEl, v);
            break;
        case 'missing-source':
            renderCanvasMissingSource(contentEl, v);
            break;
        case 'unsupported':
            renderCanvasUnsupported(contentEl, v);
            break;
        default:
            renderCanvasIdle(contentEl);
            break;
    }

    // ── Stale overlay banner for states without their own stale handling ──
    if (v.stale && state !== 'stale') {
        renderCanvasStaleBanner(contentEl, v);
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
    renderCanvasCard,
    renderCanvasCardLanes,
    renderCanvasRefreshing,
};
