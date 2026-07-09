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

function createCanvasAction(action, label, icon) {
    var button = createEl('button', { cls: 'paperforge-canvas-tool-button' });
    button.type = 'button';
    button.setAttribute('data-canvas-action', action);
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);
    var iconEl = createEl('span', { cls: 'paperforge-canvas-tool-icon', text: icon });
    iconEl.setAttribute('aria-hidden', 'true');
    button.appendChild(iconEl);
    return button;
}

function renderReadingCanvasShell(root, options) {
    var opts = options || {};
    emptyEl(root);
    var shell = createEl('div', { cls: 'paperforge-canvas-reading-shell' });
    shell.setAttribute('data-canvas-role', 'shell');
    var toolbar = createEl('div', { cls: 'paperforge-canvas-toolbar' });
    toolbar.setAttribute('data-canvas-role', 'toolbar');
    toolbar.appendChild(createCanvasAction('refresh', 'Refresh annotations', '\u21bb'));
    var countValue = String(Number.isFinite(opts.unresolvedCount) ? opts.unresolvedCount : 0);
    var count = createCanvasAction('unresolved-count', countValue + ' unresolved annotations', '\u25cf');
    count.classList.add('paperforge-canvas-unresolved-count');
    count.setAttribute('data-canvas-role', 'unresolved-count');
    count.appendChild(createEl('span', { cls: 'paperforge-canvas-unresolved-value', text: countValue }));
    toolbar.appendChild(count);
    toolbar.appendChild(createCanvasAction('open-pdf', 'Open PDF', '\u2197'));
    toolbar.appendChild(createCanvasAction('toggle-annotations', 'Toggle annotations', '\u25d0'));
    var layout = createEl('div', { cls: 'paperforge-canvas-reading-layout' });
    var leftRail = createEl('aside', { cls: 'paperforge-canvas-reading-rail paperforge-canvas-reading-rail--left' });
    leftRail.setAttribute('data-canvas-role', 'left-rail');
    var articleHost = createEl('main', { cls: 'paperforge-canvas-article-host' });
    articleHost.setAttribute('data-canvas-role', 'article-host');
    var rightRail = createEl('aside', { cls: 'paperforge-canvas-reading-rail paperforge-canvas-reading-rail--right' });
    rightRail.setAttribute('data-canvas-role', 'right-rail');
    layout.appendChild(leftRail);
    layout.appendChild(articleHost);
    layout.appendChild(rightRail);
    var drawer = createEl('div', { cls: 'paperforge-canvas-unresolved-drawer' });
    drawer.setAttribute('data-canvas-role', 'drawer');
    shell.appendChild(toolbar);
    shell.appendChild(layout);
    shell.appendChild(drawer);
    root.appendChild(shell);
    return { shell, toolbar, leftRail, articleHost, rightRail, drawer };
}

function renderCanvasFailure(root, failure) {
    var data = failure || {};
    emptyEl(root);
    var failureEl = createEl('div', {
        cls: 'paperforge-canvas-failure',
        text: data.message || 'Reading Canvas could not be loaded.',
    });
    failureEl.setAttribute('data-canvas-state', data.state || 'error');
    failureEl.setAttribute('role', 'alert');
    failureEl.appendChild(createCanvasAction('retry', 'Retry', '\u21bb'));
    root.appendChild(failureEl);
    return failureEl;
}

function appendAnnotationText(parent, cls, value) {
    if (value == null || value === '') return;
    parent.appendChild(createEl('div', { cls, text: String(value) }));
}

function renderHighlightPopover(root, annotation) {
    var item = annotation || {};
    var popover = createEl('div', { cls: 'paperforge-canvas-highlight-popover' });
    popover.setAttribute('data-annotation-id', item.id || '');
    popover.setAttribute('role', 'dialog');
    appendAnnotationText(popover, 'paperforge-canvas-highlight-quote', item.selectedText);
    appendAnnotationText(popover, 'paperforge-canvas-highlight-comment', item.comment);
    appendAnnotationText(popover, 'paperforge-canvas-highlight-page', item.pageLabel);
    root.appendChild(popover);
    return popover;
}

function renderUnresolvedDrawer(root, annotations) {
    var drawer = root.matches && root.matches('[data-canvas-role="drawer"]')
        ? root
        : root.querySelector && root.querySelector('[data-canvas-role="drawer"]');
    if (!drawer) {
        drawer = createEl('div', { cls: 'paperforge-canvas-unresolved-drawer' });
        drawer.setAttribute('data-canvas-role', 'drawer');
        root.appendChild(drawer);
    }
    emptyEl(drawer);
    (annotations || []).forEach(function (annotation) {
        var item = createEl('div', { cls: 'paperforge-canvas-unresolved-item' });
        item.setAttribute('data-annotation-id', annotation.id || '');
        appendAnnotationText(item, 'paperforge-canvas-unresolved-quote', annotation.selectedText);
        appendAnnotationText(item, 'paperforge-canvas-unresolved-comment', annotation.comment);
        drawer.appendChild(item);
    });
    return drawer;
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
    cardEl.setAttribute('data-page-index', card.pageIndex != null ? String(card.pageIndex) : '');
    cardEl.setAttribute('data-anchor-status', (card.anchor && card.anchor.status) || '');
    cardEl.setAttribute('aria-selected', 'false');
    cardEl.tabIndex = 0;

    // ── Selected text preview ──
    var selTextCls = 'paperforge-canvas-card-selected-text paperforge-canvas-card-selected-text-preview';
    if (card.selectedText === '') selTextCls += ' paperforge-canvas-card-selected-text--empty';
    if (card.selectedTextPreview && card.selectedTextPreview.isLong) selTextCls += ' paperforge-canvas-card-selected-text--long';
    var selTextEl = createEl('div', { cls: selTextCls, text: card.selectedText || '' });
    cardEl.appendChild(selTextEl);

    // ── Comment preview ──
    var commentCls = 'paperforge-canvas-card-comment paperforge-canvas-card-comment-preview';
    if (card.comment === '') commentCls += ' paperforge-canvas-card-comment--empty';
    if (card.commentPreview && card.commentPreview.isLong) commentCls += ' paperforge-canvas-card-comment--long';
    var commentEl = createEl('div', { cls: commentCls, text: card.comment || '' });
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

// ── ANN12 i18n source/anchor keys ──

_I18N.en['source.surface_label'] = 'Source';
_I18N.en['source.fulltext'] = 'Fulltext';
_I18N.en['source.note'] = 'Note';
_I18N.en['source.unavailable'] = 'Source content is not available for this paper.';
_I18N.en['source.unavailable_reason'] = 'No source content available.';
_I18N.en['anchor.exact'] = 'Exact match';
_I18N.en['anchor.page_level'] = 'Page-level';
_I18N.en['anchor.unresolved'] = 'Unresolved';
_I18N.en['anchor.page_marker'] = 'Page';
_I18N.en['anchor.downgrade_short'] = 'Selected text is too short for exact anchoring.';
_I18N.en['anchor.downgrade_ambiguous'] = 'Multiple matches found in source (ambiguous).';
_I18N.en['fallback.open_pdf_page'] = 'Open PDF page';
_I18N.en['fallback.unable_to_locate'] = 'Unable to locate anchor in source.';
_I18N.en['fallback.card_unavailable'] = 'Card is no longer available.';
_I18N.en['fallback.previous_unavailable'] = 'Previous selection is no longer available.';
_I18N.en['anchor.downgrade_not_found'] = 'Text not found in source.';

_I18N.zh['source.surface_label'] = '原文来源';
_I18N.zh['source.fulltext'] = '全文';
_I18N.zh['source.note'] = '笔记';
_I18N.zh['source.unavailable'] = '本文无法获取原文内容。';
_I18N.zh['source.unavailable_reason'] = '无法获取原文内容。';
_I18N.zh['anchor.exact'] = '精确匹配';
_I18N.zh['anchor.page_level'] = '页面级别';
_I18N.zh['anchor.unresolved'] = '无法定位';
_I18N.zh['anchor.page_marker'] = '页';
_I18N.zh['anchor.downgrade_short'] = '选中文本过短，无法精确锚定。';
_I18N.zh['anchor.downgrade_ambiguous'] = '在原文中找到多处匹配（不精确）。';
_I18N.zh['anchor.downgrade_not_found'] = '在原文中未找到匹配文本。';
_I18N.zh['fallback.open_pdf_page'] = '打开 PDF 页面';
_I18N.zh['fallback.unable_to_locate'] = '无法在原文中定位锚点。';
_I18N.zh['fallback.card_unavailable'] = '该批注卡已不可用。';
_I18N.zh['fallback.previous_unavailable'] = '之前的选中内容已不可用。';

// ── ANN12-02 source surface rendering helpers ──

/**
 * Look up an i18n string from the embedded render dictionary.
 *
 * @param {string} key - Dot-separated i18n key.
 * @returns {string}
 * @private
 */
function _t(key) {
    var lang = typeof navigator !== 'undefined' && navigator.language && navigator.language.startsWith('zh') ? 'zh' : 'en';
    var dict = _I18N[lang] || _I18N.en;
    return dict[key] !== undefined ? dict[key] : key;
}

/**
 * Render an exact anchor as a restrained inline highlight span.
 *
 * Exact anchors split source text around the match and wrap only the matched
 * span in a namespaced highlight element.  All text content uses textContent,
 * never innerHTML.  The optional color sets an inline background hint.
 *
 * @param {HTMLElement} containerEl - Parent element for the anchor fragment.
 * @param {string} beforeText - Text before the exact match span.
 * @param {string} anchorText - The exact matched text (highlighted).
 * @param {string} afterText - Text after the exact match span.
 * @param {string|null} [color] - Optional annotation color (CSS color string).
 */
function renderExactAnchorText(containerEl, beforeText, anchorText, afterText, color, anchor) {
    if (beforeText) {
        containerEl.appendChild(document.createTextNode(beforeText));
    }
    var highlight = document.createElement('span');
    highlight.className = 'paperforge-canvas-anchor paperforge-canvas-anchor--exact';
    highlight.setAttribute('data-anchor-id', (anchor && anchor.cardId) || '');
    highlight.setAttribute('data-anchor-status', 'exact');
    highlight.setAttribute('data-page-index', (anchor && anchor.pageIndex != null) ? String(anchor.pageIndex) : '');
    highlight.tabIndex = 0;
    if (color) {
        highlight.style.backgroundColor = color;
    }
    highlight.textContent = anchorText || '';
    containerEl.appendChild(highlight);
    // After text as text node
    if (afterText) {
        containerEl.appendChild(document.createTextNode(afterText));
    }
}

/**
 * Render a page-level anchor marker.
 *
 * Page-level anchors show a block/page marker with status text and reason.
 * They do NOT render inline highlights or source span wrappers.
 *
 * @param {HTMLElement} containerEl - Parent element.
 * @param {object} anchor - Anchor result ({ status, pageIndex, reason, ... }).
 */
function renderPageLevelAnchorMarker(containerEl, anchor) {
    var marker = createEl('div', { cls: 'paperforge-canvas-anchor paperforge-canvas-anchor--page-level' });
    marker.setAttribute('data-anchor-id', (anchor && anchor.cardId) || '');
    marker.setAttribute('data-anchor-status', 'page-level');
    marker.setAttribute('data-page-index', (anchor && anchor.pageIndex != null) ? String(anchor.pageIndex) : '');
    marker.tabIndex = 0;
    var pageInfo = anchor.pageIndex != null
        ? _t('anchor.page_marker') + ' ' + (anchor.pageLabel || anchor.pageIndex)
        : _t('anchor.page_marker');
    marker.appendChild(document.createTextNode(pageInfo));
    if (anchor.reason) {
        var reasonEl = createEl('span', { cls: 'paperforge-canvas-anchor-reason', text: ' — ' + anchor.reason });
        marker.appendChild(reasonEl);
    }
    containerEl.appendChild(marker);
}

/**
 * Render an unresolved anchor status explanation.
 *
 * Unresolved anchors render explanation/status text only.  No source marker,
 * no highlight, no span wrapper.
 *
 * @param {HTMLElement} containerEl - Parent element.
 * @param {object} anchor - Anchor result ({ status, reason, ... }).
 */
function renderUnresolvedAnchorStatus(containerEl, anchor) {
    var statusEl = createEl('div', { cls: 'paperforge-canvas-anchor paperforge-canvas-anchor--unresolved' });
    statusEl.setAttribute('data-anchor-id', (anchor && anchor.cardId) || '');
    statusEl.setAttribute('data-anchor-status', 'unresolved');
    var reason = anchor.reason || _t('source.unavailable_reason');
    statusEl.textContent = _t('anchor.unresolved') + ': ' + reason;
    containerEl.appendChild(statusEl);
}

/**
 * Render a single source block with anchor overlays.
 *
 * The block text and any matching anchors are rendered as a single DOM
 * fragment.  Exact anchors produce inline highlights within the block text.
 * Page-level anchors add markers after the block.  Unresolved anchors add
 * explanation text.
 *
 * @param {HTMLElement} containerEl - Parent element.
 * @param {object} block - Source block ({ id, pageIndex, text, sourceKind }).
 * @param {Array} blockAnchors - Anchors whose page matches this block.
 * @param {object} [options] - Options.
 * @param {Function} [options.getAnchorColor] - Optional callback(cardId) -> color|null.
 */
function renderSourceBlock(containerEl, block, blockAnchors, options) {
    var blockEl = createEl('div', { cls: 'paperforge-canvas-source-block' });
    blockEl.setAttribute('data-block-id', block.id || '');

    // Render block text with exact anchor highlights
    var exactAnchors = Array.isArray(blockAnchors)
        ? blockAnchors.filter(function (a) { return a && a.status === 'exact'; })
        : [];
    var pageLevelAnchors = Array.isArray(blockAnchors)
        ? blockAnchors.filter(function (a) { return a && a.status === 'page-level'; })
        : [];
    var unresolvedAnchors = Array.isArray(blockAnchors)
        ? blockAnchors.filter(function (a) { return a && a.status === 'unresolved'; })
        : [];

    if (exactAnchors.length === 0) {
        // No exact anchors — render block text as a single text node
        blockEl.textContent = block.text || '';
    } else {
        // Render source text with exact anchor highlights
        // For simplicity with the current data model, render text with highlights
        // by inserting highlighted spans at each exact anchor position.
        var blockText = block.text || '';

        // Sort exact anchors by sourceSpan.rawStart
        var sorted = exactAnchors.slice().sort(function (a, b) {
            var aStart = (a.sourceSpan && a.sourceSpan.rawStart != null) ? a.sourceSpan.rawStart : -1;
            var bStart = (b.sourceSpan && b.sourceSpan.rawStart != null) ? b.sourceSpan.rawStart : -1;
            return aStart - bStart;
        });

        // If the sourceSpan offsets map to this block's text range, split.
        // For block-relative rendering, we assume sourceSpan raw offsets
        // correspond to the block's trimmed text when the anchor was resolved
        // against this block's segment.
        var pos = 0;
        var getColor = (options && options.getAnchorColor) || function () { return null; };
        for (var ai = 0; ai < sorted.length; ai++) {
            var anchor = sorted[ai];
            var span = anchor.sourceSpan;
            var rawStart = (span && span.rawStart != null) ? span.rawStart : -1;
            var rawEnd = (span && span.rawEnd != null) ? span.rawEnd : -1;

            if (rawStart < 0 || rawEnd < 0 || rawStart >= blockText.length) {
                // Span out of range for this block — render as plain text
                continue;
            }
            if (rawEnd > blockText.length) rawEnd = blockText.length;

            // Text before this anchor
            if (rawStart > pos) {
                blockEl.appendChild(document.createTextNode(blockText.substring(pos, rawStart)));
            }
            // Highlighted anchor text
            var anchorText = blockText.substring(rawStart, rawEnd);
            var color = getColor(anchor.cardId);
            var highlight = document.createElement('span');
            highlight.className = 'paperforge-canvas-anchor paperforge-canvas-anchor--exact';
            highlight.setAttribute('data-anchor-id', anchor.cardId || '');
            highlight.setAttribute('data-anchor-status', 'exact');
            highlight.setAttribute('data-page-index', (anchor.pageIndex != null) ? String(anchor.pageIndex) : '');
            highlight.tabIndex = 0;
            if (color) highlight.style.backgroundColor = color;
            highlight.textContent = anchorText;
            blockEl.appendChild(highlight);
            pos = rawEnd;
        }
        // Text after last anchor
        if (pos < blockText.length) {
            blockEl.appendChild(document.createTextNode(blockText.substring(pos)));
        }
    }

    // Render page-level anchor markers
    for (var pi = 0; pi < pageLevelAnchors.length; pi++) {
        renderPageLevelAnchorMarker(blockEl, pageLevelAnchors[pi]);
    }

    // Render unresolved anchor status
    for (var ui = 0; ui < unresolvedAnchors.length; ui++) {
        renderUnresolvedAnchorStatus(blockEl, unresolvedAnchors[ui]);
    }

    containerEl.appendChild(blockEl);
}

/**
 * Render the central PaperForge-owned source surface.
 *
 * Renders a source surface container with source kind header and blocks.
 * When source is unavailable, shows the unavailable state instead.
 *
 * @param {HTMLElement} contentEl - Parent element.
 * @param {Array} sourceBlocks - Source blocks from buildSourceBlocks().
 * @param {Array} cardAnchors - Card anchor objects from vm.cards[].anchor.
 * @param {object} [options] - Options.
 * @param {boolean} [options.unavailable] - Show source-unavailable state.
 * @param {string} [options.reason] - Reason for unavailability.
 * @param {string} [options.sourceKind] - 'fulltext' or 'note'.
 * @param {Function} [options.getAnchorColor] - Optional callback(cardId) -> color|null.
 */
function renderCanvasSourceSurface(contentEl, sourceBlocks, cardAnchors, options) {
    var opts = options || {};

    // ── Source surface container ──
    var surfaceEl = createEl('div', { cls: 'paperforge-canvas-source-surface' });

    // ── Source-unavailable state ──
    if (opts.unavailable) {
        var unavailableEl = createEl('div', { cls: 'paperforge-canvas-source-unavailable' });
        var msg = createEl('span', { cls: 'paperforge-canvas-status-text', text: opts.reason || _t('source.unavailable') });
        unavailableEl.appendChild(msg);
        surfaceEl.appendChild(unavailableEl);
        contentEl.appendChild(surfaceEl);
        return;
    }

    // Source kind header
    var headerEl = createEl('div', { cls: 'paperforge-canvas-source-header' });
    var kindLabel = opts.sourceKind === 'note' ? _t('source.note') : _t('source.fulltext');
    headerEl.textContent = _t('source.surface_label') + ': ' + kindLabel;
    surfaceEl.appendChild(headerEl);

    // Group card anchors by pageIndex
    var anchorsByPage = {};
    if (Array.isArray(cardAnchors)) {
        for (var ai = 0; ai < cardAnchors.length; ai++) {
            var a = cardAnchors[ai];
            if (!a) continue;
            // Use pageIndex from anchor or fallback to 0
            var pageKey = a.pageIndex != null ? String(a.pageIndex) : '0';
            if (!anchorsByPage[pageKey]) anchorsByPage[pageKey] = [];
            anchorsByPage[pageKey].push(a);
        }
    }

    // Render each source block with its matching anchors
    var blocks = Array.isArray(sourceBlocks) ? sourceBlocks : [];
    for (var bi = 0; bi < blocks.length; bi++) {
        var block = blocks[bi];
        var pageKey = block.pageIndex != null ? String(block.pageIndex) : '0';
        var blockAnchors = anchorsByPage[pageKey] || [];
        renderSourceBlock(surfaceEl, block, blockAnchors, opts);
    }

    contentEl.appendChild(surfaceEl);
}

/**
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

function renderFallbackButton(containerEl, fallbackInfo) {
    if (!fallbackInfo || !fallbackInfo.eligible) return;
    var btn = document.createElement('button');
    btn.className = 'paperforge-canvas-fallback-button';
    btn.textContent = _t('fallback.open_pdf_page');
    btn.setAttribute('aria-label', _t('fallback.open_pdf_page') + ' — ' + (_t('anchor.page_marker') + ' ' + (fallbackInfo.page || '')));
    btn.setAttribute('data-fallback-page', fallbackInfo.page != null ? String(fallbackInfo.page) : '');
    containerEl.appendChild(btn);
}

// ── ANN14-02: Connector state constants (from connectors module) ──

const {
    CONNECTOR_STATES,
} = require('./connectors');

// ── ANN14-02: Connector SVG layer rendering helpers ──

/**
 * The base CSS class for the connector SVG layer element.
 * @type {string}
 */
var CANVAS_CONNECTOR_LAYER_CLS = 'paperforge-canvas-connector-layer';

/**
 * The base CSS class for a connector path/line element.
 * @type {string}
 */
var CANVAS_CONNECTOR_CLS = 'paperforge-canvas-connector';

/**
 * CSS modifier class for a selected connector.
 * @type {string}
 */
var CANVAS_CONNECTOR_SELECTED = 'paperforge-canvas-connector--selected';

/**
 * CSS modifier class for a hovered connector.
 * @type {string}
 */
var CANVAS_CONNECTOR_HOVERED = 'paperforge-canvas-connector--hovered';

/**
 * Create an empty namespaced connector SVG layer element.
 *
 * Creates exactly one <svg> under .paperforge-reading-canvas-view using the
 * namespaced class paperforge-canvas-connector-layer.  The layer is hidden
 * from the accessibility tree (aria-hidden, role=presentation) and contains
 * no paths by default.
 *
 * Must only be called by runtime after loaded canvas rendering.  Does NOT
 * appear in idle, missing-paper, missing-db, missing-source, unsupported,
 * or card-only shell states unless explicitly called (D-13/D-17/D-20).
 *
 * @param {HTMLElement} containerEl - Parent element (typically .paperforge-reading-canvas-view).
 * @returns {SVGSVGElement} The created SVG layer element.
 */
function renderCanvasConnectorLayer(containerEl) {
    var ns = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('class', CANVAS_CONNECTOR_LAYER_CLS);
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('role', 'presentation');
    containerEl.appendChild(svg);
    return svg;
}

/**
 * Update a connector SVG layer with at most one connector path.
 *
 * Clears the layer and renders a single <line> element when the connector
 * state is visible.  Applies the --selected (default) or --hovered modifier
 * class based on the `modifier` parameter.
 *
 * For hidden states — page-level, unresolved, stale, missing-dom,
 * hidden-candidate, and any other hidden reason — the layer is left empty
 * (no path elements) per D-01/D-02/D-03/D-13/D-17.
 *
 * @param {SVGSVGElement} layerEl - The SVG layer from renderCanvasConnectorLayer.
 * @param {object} connectorState - Connector geometry from measureConnectorGeometry().
 * @param {string} [modifier] - 'selected' or 'hovered' (defaults to 'selected').
 */
function updateCanvasConnectorLayer(layerEl, connectorState, modifier) {
    // Clear existing connector elements
    while (layerEl.firstChild) {
        layerEl.removeChild(layerEl.firstChild);
    }

    // Only render for visible connector state; hidden states leave the
    // layer empty (no path elements)
    if (!connectorState || connectorState.state !== CONNECTOR_STATES.VISIBLE) {
        return;
    }

    var cardEp = connectorState.cardEndpoint;
    var anchorEp = connectorState.anchorEndpoint;

    // Guard: missing endpoints (shouldn't happen for visible state, but
    // protect against malformed input)
    if (!cardEp || !anchorEp) return;

    var ns = 'http://www.w3.org/2000/svg';
    var line = document.createElementNS(ns, 'line');

    // Build class: base + modifier
    var cls = CANVAS_CONNECTOR_CLS;
    cls += (modifier === 'hovered')
        ? ' ' + CANVAS_CONNECTOR_HOVERED
        : ' ' + CANVAS_CONNECTOR_SELECTED;
    line.setAttribute('class', cls);

    // Endpoint coordinates
    line.setAttribute('x1', String(cardEp.x));
    line.setAttribute('y1', String(cardEp.y));
    line.setAttribute('x2', String(anchorEp.x));
    line.setAttribute('y2', String(anchorEp.y));

    // Accessible presentation (hidden from AT — visual decoration only)
    line.setAttribute('aria-hidden', 'true');

    layerEl.appendChild(line);
}

module.exports = {
    renderReadingCanvasShell,
    renderCanvasFailure,
    renderHighlightPopover,
    renderUnresolvedDrawer,
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
    // ── ANN13-03 navigation and fallback rendering ──
    renderFallbackButton,
    // ── ANN12-02 source surface and anchor rendering ──
    renderCanvasSourceSurface,
    renderSourceBlock,
    renderExactAnchorText,
    renderPageLevelAnchorMarker,
    renderUnresolvedAnchorStatus,

    // ── ANN14-02 connector layer rendering ──
    renderCanvasConnectorLayer,
    updateCanvasConnectorLayer,
};
