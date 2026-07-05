/**
 * Canvas context resolution helpers.
 *
 * Pure functions for building canvas contexts from paper entries.
 * No Obsidian, subprocess, database, or Zotero dependencies.
 *
 * @module canvas/context
 */

/**
 * Build a canvas context from a valid paper entry.
 *
 * The entry's `key` property is treated as the authoritative paper identity.
 * Returns an explicit `{ ok, paperKey, entry, reason }` result so callers
 * always have a stable shape to inspect, never a thrown exception.
 *
 * @param {object|null|undefined} entry - Paper entry with a `key` property.
 * @returns {{ ok: boolean, paperKey: string|null, entry: object|null, reason: string|null }}
 */
function buildCanvasContextFromEntry(entry) {
    // ── Guard: missing entry ──
    if (entry == null || typeof entry !== 'object') {
        return {
            ok: false,
            paperKey: null,
            entry: null,
            reason: 'No paper entry provided.',
        };
    }

    // ── Guard: missing key ──
    const rawKey = entry.key;
    if (rawKey == null || (typeof rawKey === 'string' && rawKey.trim() === '')) {
        return {
            ok: false,
            paperKey: null,
            entry: null,
            reason: 'Paper entry has no key.',
        };
    }

    const paperKey = String(rawKey);

    return {
        ok: true,
        paperKey: paperKey,
        entry: entry,
        reason: null,
    };
}

/**
 * Build a missing canvas context with a descriptive reason.
 *
 * Useful when no paper is active, the index is unavailable, or context
 * prerequisites are not met.  Always returns a fail-closed result.
 *
 * @param {string} [reason='Paper context is not available.'] - Human-readable reason.
 * @returns {{ ok: false, paperKey: null, entry: null, reason: string }}
 */
function buildMissingCanvasContext(reason) {
    return {
        ok: false,
        paperKey: null,
        entry: null,
        reason: typeof reason === 'string' && reason.trim().length > 0
            ? reason
            : 'Paper context is not available.',
    };
}

module.exports = {
    buildCanvasContextFromEntry,
    buildMissingCanvasContext,
};
