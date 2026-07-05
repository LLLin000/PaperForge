/**
 * Canvas session lifecycle controller.
 *
 * Owns a fixed paper identity for one canvas session, coordinates
 * initial annotation loading and refresh through the annotation wrapper,
 * discards stale async results with a monotonic load sequence, and
 * exposes teardown.  Never reads a live global `_currentPaperKey` —
 * the paper identity is captured at construction time.
 *
 * @module canvas/controller
 */

/**
 * Create a canvas session controller.
 *
 * @param {object} deps
 * @param {string} [deps.paperKey] - The fixed paper identity for this
 *   canvas session.  Stored at construction and never re-read from
 *   external state.
 * @param {object} [deps.annotationLoader] - An annotation loader object
 *   with a `loadForPaper(paperKey, loadOptions)` method (e.g. the
 *   object returned by `createCanvasAnnotationLoader()`).
 * @returns {CanvasSessionController}
 */
function createCanvasSessionController(deps) {
    const { annotationLoader } = deps || {};
    const _paperKey = (deps && deps.paperKey != null) ? String(deps.paperKey) : null;
    let _loadSeq = 0;
    let _state = null;
    let _disposed = false;

    /**
     * Return the fixed paper key for this canvas session.
     *
     * @returns {string|null}
     */
    function getPaperKey() {
        return _paperKey;
    }

    /**
     * Return the current annotation state (or null if nothing loaded yet).
     *
     * @returns {object|null}
     */
    function getState() {
        return _state;
    }

    /**
     * Load annotations through the injected annotation loader.
     *
     * Captures the current paper key and a monotonic load sequence
     * before the async call.  When the promise resolves, the result
     * is discarded if:
     *   - The controller has been disposed.
     *   - Another load was started (sequence mismatch).
     *   - The paper key changed (defensive — the key is fixed, but
     *     this guard prevents stale dispatches from edge cases).
     *
     * @param {object} [loadOptions] - Options forwarded to the annotation
     *   loader's `loadForPaper()` method.
     * @returns {Promise<object|null>} The loaded annotation state, or null
     *   if the result was discarded as stale or no paper key is set.
     */
    async function loadAnnotations(loadOptions) {
        if (_disposed) return null;
        if (!_paperKey) return null;

        const capturedKey = _paperKey;
        const capturedSeq = ++_loadSeq;

        const result = await annotationLoader.loadForPaper(capturedKey, loadOptions);

        // ── Stale guard ──
        if (_disposed || capturedSeq !== _loadSeq || _paperKey !== capturedKey) {
            return null;
        }

        _state = result;
        return result;
    }

    /**
     * Tear down the canvas session.
     *
     * Disposes the controller, clears stored state, and increments the
     * load sequence so any in-flight async results are discarded.
     * After teardown, `loadAnnotations()` returns null.
     */
    function teardown() {
        _disposed = true;
        _loadSeq = -1;
        _state = null;
    }

    return {
        getPaperKey,
        getState,
        loadAnnotations,
        teardown,
    };
}

/**
 * @typedef {object} CanvasSessionController
 * @property {() => string|null} getPaperKey
 * @property {() => object|null} getState
 * @property {(loadOptions?: object) => Promise<object|null>} loadAnnotations
 * @property {() => void} teardown
 */

module.exports = {
    createCanvasSessionController,
};
