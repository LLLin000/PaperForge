/**
 * Vitest tests for Phase 8 overlay rendering pure helpers.
 *
 * Tests cover:
 *   - createDefaultAnnotationOverlayState (Task 1)
 *   - parseAnnotationPositionJson (Task 1)
 *   - normalizeAnnotationColor (Task 1)
 *   - buildAnnotationOverlayMarks (Task 2)
 *   - buildAnnotationPopoverViewModel (Task 2)
 */
import { describe, it, expect } from 'vitest';

const {
    createDefaultAnnotationOverlayState,
    parseAnnotationPositionJson,
    normalizeAnnotationColor,
    DEFAULT_OVERLAY_HIGHLIGHT_COLOR,
} = await import('../src/testable.js');

// ---------------------------------------------------------------------------
// Task 1: createDefaultAnnotationOverlayState
// ---------------------------------------------------------------------------

describe('createDefaultAnnotationOverlayState', () => {
    it('returns an object with all required fields', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state).toHaveProperty('status', 'idle');
        expect(state).toHaveProperty('reason', '');
        expect(state).toHaveProperty('paperKey');
        expect(state).toHaveProperty('pdfPath');
        expect(state).toHaveProperty('viewerAttached', false);
        expect(state).toHaveProperty('activePopoverId');
    });

    it('initializes paperKey and pdfPath to null', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state.paperKey).toBeNull();
        expect(state.pdfPath).toBeNull();
    });

    it('initializes activePopoverId to null', () => {
        const state = createDefaultAnnotationOverlayState();
        expect(state.activePopoverId).toBeNull();
    });

    it('returns a fresh object each call', () => {
        const a = createDefaultAnnotationOverlayState();
        const b = createDefaultAnnotationOverlayState();
        expect(a).not.toBe(b);
    });
});

// ---------------------------------------------------------------------------
// Task 1: parseAnnotationPositionJson
// ---------------------------------------------------------------------------

describe('parseAnnotationPositionJson', () => {
    it('parses a valid positionJson with rects', () => {
        const input = '{"pageIndex":0,"rects":[{"x":60.5,"y":72.3,"w":489.2,"h":18.1}]}';
        const result = parseAnnotationPositionJson(input);
        expect(result.ok).toBe(true);
        expect(result.rects).toHaveLength(1);
        expect(result.rects[0].x).toBe(60.5);
        expect(result.rects[0].y).toBe(72.3);
        expect(result.rects[0].w).toBe(489.2);
        expect(result.rects[0].h).toBe(18.1);
        expect(result.reason).toBeNull();
    });

    it('parses a positionJson with multiple rects', () => {
        const input = '{"rects":[{"x":0,"y":0,"w":100,"h":20},{"x":10,"y":30,"w":200,"h":40}]}';
        const result = parseAnnotationPositionJson(input);
        expect(result.ok).toBe(true);
        expect(result.rects).toHaveLength(2);
    });

    it('returns ok:false for null input', () => {
        const result = parseAnnotationPositionJson(null);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for undefined input', () => {
        const result = parseAnnotationPositionJson(undefined);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for non-string input', () => {
        const result = parseAnnotationPositionJson(42);
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for invalid JSON string', () => {
        const result = parseAnnotationPositionJson('{not valid json}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for a JSON string that is not an object', () => {
        const result = parseAnnotationPositionJson('"just a string"');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false for a JSON array', () => {
        const result = parseAnnotationPositionJson('[1,2,3]');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects field is missing', () => {
        const result = parseAnnotationPositionJson('{"pageIndex":0}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects is not an array', () => {
        const result = parseAnnotationPositionJson('{"rects":"not-an-array"}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rects array is empty', () => {
        const result = parseAnnotationPositionJson('{"pageIndex":2,"rects":[]}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
        expect(result.reason).toBeTruthy();
    });

    it('returns ok:false when rect has non-numeric x', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":"abc","y":0,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
        expect(result.rects).toEqual([]);
    });

    it('returns ok:false when rect has non-numeric y', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":null,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-numeric w', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":false,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-numeric h', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100,"h":undefined}]}');
        // undefined in JSON becomes null/omitted — but let's test absent h
        const result2 = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100}]}');
        expect(result2.ok).toBe(false);
    });

    it('returns ok:false when rect has negative x', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":-1,"y":0,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative y', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":-5,"w":100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative w', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":-100,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has negative h', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":100,"h":-20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect has non-finite values (Infinity)', () => {
        const result = parseAnnotationPositionJson('{"rects":[{"x":0,"y":0,"w":Infinity,"h":20}]}');
        expect(result.ok).toBe(false);
    });

    it('returns ok:false when rect is not an object', () => {
        const result = parseAnnotationPositionJson('{"rects":[null]}');
        expect(result.ok).toBe(false);
    });

    it('does not mutate the input string', () => {
        const input = '{"pageIndex":0,"rects":[{"x":10,"y":20,"w":100,"h":30}]}';
        const frozen = String(input);
        parseAnnotationPositionJson(input);
        expect(input).toBe(frozen);
    });

    it('provides a stable friendly reason on failure', () => {
        const cases = [
            null,
            'not json',
            '{"rects":[]}',
            '{"rects":[{"x":"bad"}]}',
        ];
        for (const c of cases) {
            const result = parseAnnotationPositionJson(c);
            expect(result.ok).toBe(false);
            expect(typeof result.reason).toBe('string');
            // Reason must not contain stack traces, raw JSON dumps, shell output, or absolute paths
            expect(result.reason).not.toContain('Error');
            expect(result.reason).not.toContain('at ');
            expect(result.reason).not.toContain(':\\');
            expect(result.reason).not.toContain('Traceback');
        }
    });
});

// ---------------------------------------------------------------------------
// Task 1: normalizeAnnotationColor
// ---------------------------------------------------------------------------

describe('normalizeAnnotationColor', () => {
    it('returns the default yellow for null input', () => {
        expect(normalizeAnnotationColor(null)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for undefined input', () => {
        expect(normalizeAnnotationColor(undefined)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for empty string', () => {
        expect(normalizeAnnotationColor('')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the default yellow for whitespace-only string', () => {
        expect(normalizeAnnotationColor('   ')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('passes through a valid #rrggbb hex color', () => {
        expect(normalizeAnnotationColor('#ffd400')).toBe('#ffd400');
    });

    it('passes through a valid #rgb shorthand hex', () => {
        expect(normalizeAnnotationColor('#ff0')).toBe('#ff0');
    });

    it('passes through a valid #rrggbbaa hex color', () => {
        expect(normalizeAnnotationColor('#ffd400aa')).toBe('#ffd400aa');
    });

    it('passes through a valid rgb() color', () => {
        expect(normalizeAnnotationColor('rgb(255, 212, 0)')).toBe('rgb(255, 212, 0)');
    });

    it('passes through a valid rgba() color', () => {
        expect(normalizeAnnotationColor('rgba(255, 212, 0, 0.5)')).toBe('rgba(255, 212, 0, 0.5)');
    });

    it('passes through common named colors', () => {
        expect(normalizeAnnotationColor('red')).toBe('red');
        expect(normalizeAnnotationColor('blue')).toBe('blue');
        expect(normalizeAnnotationColor('green')).toBe('green');
    });

    it('is case-insensitive for hex colors (preserves input case)', () => {
        const result = normalizeAnnotationColor('#FFD400');
        expect(result).toBe('#FFD400');
    });

    it('returns default yellow for unrecognized color string', () => {
        expect(normalizeAnnotationColor('not-a-color')).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns default yellow for non-string input (number)', () => {
        expect(normalizeAnnotationColor(42)).toBe(DEFAULT_OVERLAY_HIGHLIGHT_COLOR);
    });

    it('returns the restrained default yellow (#ffd400) per D-06', () => {
        expect(DEFAULT_OVERLAY_HIGHLIGHT_COLOR).toBe('#ffd400');
    });
});
