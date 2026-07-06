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
