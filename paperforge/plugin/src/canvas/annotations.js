/**
 * Canvas annotation loading wrapper.
 *
 * A thin injected wrapper around existing v0.2 annotation contracts
 * (`loadAnnotationsForPaper()` and `makeAnnotationState()` from
 * `src/testable.js`).  The wrapper accepts a `paperKey`, injected
 * loader, and optional load options, and returns existing annotation
 * load states without constructing new CLI commands, database reads,
 * or Zotero API calls.
 *
 * @module canvas/annotations
 */

const ANNOTATION_LOAD_STATES = Object.freeze({
    IDLE: 'idle',
    LOADING: 'loading',
    READY: 'ready',
    EMPTY: 'empty',
    MISSING_PAPER: 'missing-paper',
    MISSING_DB: 'missing-db',
    CLI_ERROR: 'cli-error',
    INVALID_JSON: 'invalid-json',
});

/**
 * Create a default annotation state (used when no loader is available).
 *
 * @param {string|null} [paperKey=null]
 * @param {string} [message='']
 * @returns {{ state: string, paperKey: string|null, annotations: Array, message: string, errorCode: null, raw: null }}
 */
function makeDefaultState(paperKey, message) {
    return {
        state: ANNOTATION_LOAD_STATES.IDLE,
        paperKey: paperKey != null ? paperKey : null,
        annotations: [],
        message: message || '',
        errorCode: null,
        raw: null,
    };
}

/**
 * Create a canvas annotation loader.
 *
 * The returned object exposes a single `loadForPaper(paperKey, loadOptions)`
 * method that delegates entirely to the injected v0.2 `loadAnnotationsForPaper`
 * or `loader` function.  No CLI arguments, database paths, or Zotero
 * identities are constructed in this module.
 *
 * @param {object} deps
 * @param {Function} [deps.loadAnnotationsForPaper] - The v0.2 loader function
 *   matching `loadAnnotationsForPaper(options)` signature.  If omitted, all
 *   load calls return a CLI-error state indicating the loader is unavailable.
 * @param {Function} [deps.loader] - Alternative name accepted for convenience.
 *   When both are present, `loadAnnotationsForPaper` takes precedence.
 * @returns {{ loadForPaper: Function, getLoadStates: Function }}
 */
function createCanvasAnnotationLoader(deps) {
    const effectiveLoader = (deps && (deps.loadAnnotationsForPaper || deps.loader)) || null;

    /**
     * Load annotations for a specific paper key.
     *
     * Accepts a paperKey and optional load options that are forwarded
     * directly to the v0.2 loader.  Never constructs CLI commands or
     * database paths here.
     *
     * @param {string|null} paperKey - The paper identity to load annotations for.
     * @param {object} [loadOptions] - Options forwarded to the v0.2 loader
     *   (e.g. `{ pythonExe, cwd, timeout, runSubprocessFn, env }`).
     * @returns {Promise<{ state: string, paperKey: string|null, annotations: Array, message: string, errorCode, raw }>}
     */
    async function loadForPaper(paperKey, loadOptions) {
        // ── Guard: loader not available ──
        if (typeof effectiveLoader !== 'function') {
            return makeDefaultState(
                paperKey != null ? paperKey : null,
                'Annotation loader is not available.'
            );
        }

        // ── Guard: missing paper key ──
        if (paperKey == null || (typeof paperKey === 'string' && paperKey.trim() === '')) {
            return {
                state: ANNOTATION_LOAD_STATES.MISSING_PAPER,
                paperKey: null,
                annotations: [],
                message: 'No paper key provided. Open a recognized paper to view its annotations.',
                errorCode: null,
                raw: null,
            };
        }

        // Delegate to the injected v0.2 loader with the explicit paperKey.
        // The loader is responsible for constructing CLI args, managing
        // subprocess calls, and returning the correct load state.
        return effectiveLoader({
            paperKey: paperKey,
            ...(loadOptions || {}),
        });
    }

    /**
     * Return the set of known annotation load state names.
     *
     * @returns {Readonly<Record<string, string>>}
     */
    function getLoadStates() {
        return ANNOTATION_LOAD_STATES;
    }

    return {
        loadForPaper,
        getLoadStates,
    };
}

module.exports = {
    createCanvasAnnotationLoader,
    ANNOTATION_LOAD_STATES,
};
