/**
 * PaperForge i18n dictionary — ANN11 card labels and canvas state text.
 *
 * Scoped to ANN11 card labels, placeholders, provenance, read-only badges,
 * and state copy.  Zh/en dictionaries are exposed via the `t()` helper.
 *
 * Usage:
 *   const { t } = require('./i18n');
 *   t('card.selected_text')  // → 'Selected Text' or '选中文本'
 *
 * @module i18n
 */

const _DICT = {
    zh: {
        // ── Card field labels ──
        'card.selected_text': '选中文本',
        'card.comment': '备注',
        'card.page': '页码',
        'card.type': '类型',
        'card.source': '来源',
        'card.attachment': '附件',
        'card.annotation': '批注',

        // ── Read-only badge ──
        'card.read_only': '只读',
        'card.read_only_label': '只读',

        // ── Placeholders ──
        'card.no_comment': '',
        'card.no_selected_text': '',

        // ── Canvas state copy ──
        'state.refreshing': '正在刷新批注…',
        'state.stale': '显示之前加载的（过期）数据。',

        // ── ANN12 source and anchor copy ──
        'source.surface_label': '原文来源',
        'source.fulltext': '全文',
        'source.note': '笔记',
        'source.unavailable': '本文无法获取原文内容。',
        'source.unavailable_reason': '无法获取原文内容。',
        'anchor.exact': '精确匹配',
        'anchor.page_level': '页面级别',
        'anchor.unresolved': '无法定位',
        'anchor.page_marker': '第',
        'anchor.downgrade_short': '选中文本过短，无法精确锚定。',
        'anchor.downgrade_ambiguous': '在原文中找到多处匹配（不精确）。',
        'anchor.downgrade_not_found': '在原文中未找到匹配文本。',
    },

    en: {
        // ── Card field labels ──
        'card.selected_text': 'Selected Text',
        'card.comment': 'Comment',
        'card.page': 'Page',
        'card.type': 'Type',
        'card.source': 'Source',
        'card.attachment': 'Attachment',
        'card.annotation': 'Annotation',

        // ── Read-only badge ──
        'card.read_only': 'Read-only',
        'card.read_only_label': 'Read-only',

        // ── Placeholders ──
        'card.no_comment': '',
        'card.no_selected_text': '',

        // ── Canvas state copy ──
        'state.refreshing': 'Refreshing annotations…',
        'state.stale': 'Showing previously loaded (stale) data.',

        // ── ANN12 source and anchor copy ──
        'source.surface_label': 'Source',
        'source.fulltext': 'Fulltext',
        'source.note': 'Note',
        'source.unavailable': 'Source content is not available for this paper.',
        'source.unavailable_reason': 'No source content available.',
        'anchor.exact': 'Exact match',
        'anchor.page_level': 'Page-level',
        'anchor.unresolved': 'Unresolved',
        'anchor.page_marker': 'Page',
        'anchor.downgrade_short': 'Selected text is too short for exact anchoring.',
        'anchor.downgrade_ambiguous': 'Multiple matches found in source (ambiguous).',
        'anchor.downgrade_not_found': 'Text not found in source.',
    },
};

/**
 * Detect preferred language from the runtime environment.
 *
 * Checks `navigator.language` in browser/jsdom context, falls back
 * to `process.env.LANG` or `'en'`.  Returns 'zh' for any `zh*` match,
 * 'en' otherwise.
 *
 * @returns {'zh'|'en'}
 */
function detectLang() {
    if (typeof navigator !== 'undefined' && navigator.language) {
        return navigator.language.startsWith('zh') ? 'zh' : 'en';
    }
    if (typeof process !== 'undefined' && process.env && process.env.LANG) {
        return process.env.LANG.startsWith('zh') ? 'zh' : 'en';
    }
    return 'en';
}

/**
 * Look up a translated string by key.
 *
 * @param {string} key - Dot-separated i18n key.
 * @param {'zh'|'en'} [lang] - Optional language override.
 * @returns {string} Translated string or the key itself if not found.
 */
function t(key, lang) {
    var l = lang || detectLang();
    var dict = _DICT[l] || _DICT.en;
    return dict[key] !== undefined ? dict[key] : key;
}

module.exports = {
    t: t,
    detectLang: detectLang,
    _DICT: _DICT,
};
