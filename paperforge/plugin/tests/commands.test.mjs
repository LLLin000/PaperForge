/**
 * Vitest tests for commands.js — ACTIONS, buildCommandArgs, runSubprocess.
 *
 * runSubprocess uses dependency injection (last _spawn param) instead of
 * vi.mock to avoid CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const {
    ACTIONS, buildCommandArgs, runSubprocess,
    ANNOTATION_COLORS, ANNOTATION_DEFAULT_COLOR,
    buildAnnotationSubprocessArgs, buildAnnotationListArgs,
    buildAnnotationCreateArgs, buildAnnotationPatchArgs,
    buildAnnotationDeleteArgs,
    parseAnnotationResult, isReadonlyAnnotation,
    groupAnnotationsByPage, isAnnotationSupportedType,
    normalizeAnnotationRects,
    buildAnnotationPayloadFromSelection,
} = await import('../src/testable.js');

describe('ACTIONS', () => {
    it('has exactly 4 entries', () => {
        expect(ACTIONS).toHaveLength(4);
    });
    it('every entry has id, title, cmd, okMsg', () => {
        for (const a of ACTIONS) {
            expect(a).toHaveProperty('id');
            expect(a).toHaveProperty('title');
            expect(a).toHaveProperty('cmd');
            expect(a).toHaveProperty('okMsg');
        }
    });
    it('sync action has cmd: sync', () => {
        expect(ACTIONS.find(a => a.id === 'paperforge-sync')?.cmd).toBe('sync');
    });
    it('repair action is enabled (no disabled flag)', () => {
        expect(ACTIONS.find(a => a.id === 'paperforge-repair')?.disabled).toBeUndefined();
    });
});

describe('buildCommandArgs', () => {
    it('appends key when needsKey', () => {
        expect(buildCommandArgs({ args: ['--json'], needsKey: true }, 'ABC123'))
            .toEqual(['--json', 'ABC123']);
    });
    it('appends --all when needsFilter', () => {
        expect(buildCommandArgs({ needsFilter: true }, null)).toEqual(['--all']);
    });
    it('returns empty array when no flags', () => {
        expect(buildCommandArgs({})).toEqual([]);
    });
    it('copies args to avoid mutation', () => {
        const a = { args: ['--json'], needsKey: true };
        expect(buildCommandArgs(a, 'K1')).toEqual(['--json', 'K1']);
        expect(buildCommandArgs(a, 'K2')).toEqual(['--json', 'K2']);
    });
});

describe('runSubprocess', () => {
    let mockSpawn;

    function makeMockChild() {
        return {
            stdout: { on: vi.fn() },
            stderr: { on: vi.fn() },
            on: vi.fn(),
        };
    }

    beforeEach(() => {
        mockSpawn = vi.fn(makeMockChild);
    });

    it('returns stdout, stderr, exitCode from spawned process', async () => {
        const promise = runSubprocess('python', ['--version'], '/vault', undefined, mockSpawn);
        const child = mockSpawn.mock.results[0]?.value;
        expect(child).toBeDefined();

        const closeCb = child.on.mock.calls.find(([e]) => e === 'close')?.[1];
        const dataCb = child.stdout.on.mock.calls.find(([e]) => e === 'data')?.[1];
        expect(closeCb).toBeDefined();
        expect(dataCb).toBeDefined();

        dataCb('Python 3.11.0\n');
        closeCb(0);

        const r = await promise;
        expect(r.stdout).toBe('Python 3.11.0\n');
        expect(r.exitCode).toBe(0);
        expect(r.elapsed).toBeGreaterThanOrEqual(0);
    });

    it('captures stderr on non-zero exit', async () => {
        const promise = runSubprocess('python', ['bad'], '/vault', undefined, mockSpawn);
        const child = mockSpawn.mock.results[0]?.value;

        const closeCb = child.on.mock.calls.find(([e]) => e === 'close')?.[1];
        const dataCb = child.stderr.on.mock.calls.find(([e]) => e === 'data')?.[1];
        dataCb('Error: unknown');
        closeCb(1);

        const r = await promise;
        expect(r.exitCode).toBe(1);
        expect(r.stderr).toContain('Error');
    });

    it('captures spawn error events', async () => {
        const promise = runSubprocess('python', ['bad'], '/vault', undefined, mockSpawn);
        const child = mockSpawn.mock.results[0]?.value;

        const errCb = child.on.mock.calls.find(([e]) => e === 'error')?.[1];
        expect(errCb).toBeDefined();
        errCb(new Error('ENOENT'));

        const r = await promise;
        expect(r.exitCode).toBe(-1);
        expect(r.stderr).toContain('ENOENT');
    });

    it('passes timeout and windowsHide options to spawn', async () => {
        runSubprocess('python', ['cmd'], '/vault', 30000, mockSpawn);
        const opts = mockSpawn.mock.calls[0]?.[2];
        expect(opts).toHaveProperty('timeout', 30000);
        expect(opts).toHaveProperty('windowsHide', true);
    });

    it('resolves on spawn error with exitCode -1', async () => {
        const promise = runSubprocess('py', [], '/vault', 5000, mockSpawn);
        const child = mockSpawn.mock.results[0]?.value;
        const errCb = child.on.mock.calls.find(([e]) => e === 'error')?.[1];
        errCb(new Error('spawn ENOENT'));
        const r = await promise;
        expect(r.exitCode).toBe(-1);
    });
});

describe('ANNOTATION_COLORS', () => {
    it('has 8 color entries', () => {
        expect(ANNOTATION_COLORS).toHaveLength(8);
    });
    it('every entry has name and hex', () => {
        for (const c of ANNOTATION_COLORS) {
            expect(c).toHaveProperty('name');
            expect(c).toHaveProperty('hex');
            expect(c.hex).toMatch(/^#[0-9a-f]{6}$/);
        }
    });
    it('includes yellow, red, green, blue, purple', () => {
        const names = ANNOTATION_COLORS.map(c => c.name);
        expect(names).toContain('yellow');
        expect(names).toContain('red');
        expect(names).toContain('green');
        expect(names).toContain('blue');
        expect(names).toContain('purple');
    });
    it('ANNOTATION_DEFAULT_COLOR is yellow hex', () => {
        expect(ANNOTATION_DEFAULT_COLOR).toBe('#ffd400');
    });
});

describe('buildAnnotationSubprocessArgs', () => {
    it('includes -m paperforge and --vault', () => {
        const args = buildAnnotationSubprocessArgs('/vault', { extraArgs: [] });
        expect(args).toContain('-m');
        expect(args).toContain('paperforge');
        expect(args).toContain('--vault');
        expect(args).toContain('/vault');
    });
    it('includes extraArgs from pythonInfo', () => {
        const args = buildAnnotationSubprocessArgs('/vault', { extraArgs: ['-3'] });
        expect(args[0]).toBe('-3');
    });
    it('works without pythonInfo', () => {
        const args = buildAnnotationSubprocessArgs('/vault');
        expect(args).toContain('-m');
    });
});

describe('buildAnnotationListArgs', () => {
    it('includes annotation list subcommand', () => {
        const args = buildAnnotationListArgs('/vault', { extraArgs: [] });
        expect(args).toContain('annotation');
        expect(args).toContain('list');
        expect(args).toContain('--json');
    });
    it('includes --pdf-path when provided', () => {
        const args = buildAnnotationListArgs('/vault', { extraArgs: [] }, 'paper.pdf');
        const idx = args.indexOf('--pdf-path');
        expect(idx).toBeGreaterThanOrEqual(0);
        expect(args[idx + 1]).toBe('paper.pdf');
    });
    it('omits --pdf-path when not provided', () => {
        const args = buildAnnotationListArgs('/vault', { extraArgs: [] });
        expect(args).not.toContain('--pdf-path');
    });
});

describe('buildAnnotationCreateArgs', () => {
    it('includes annotation create and payload fields', () => {
        const args = buildAnnotationCreateArgs('/vault', { extraArgs: [] }, {
            pdf_path: 'paper.pdf',
            page_index: 3,
            type: 'highlight',
            color: '#ff6666',
            selected_text: 'hello',
            comment: 'important',
            position_json: '{"pageIndex":3,"rects":[[0,0,100,20]]}',
        });
        expect(args).toContain('annotation');
        expect(args).toContain('create');
        expect(args).toContain('--pdf-path');
        expect(args).toContain('paper.pdf');
        expect(args).toContain('--page-index');
        expect(args).toContain('3');
        expect(args).toContain('--type');
        expect(args).toContain('highlight');
        expect(args).toContain('--color');
        expect(args).toContain('#ff6666');
        expect(args).toContain('--selected-text');
        expect(args).toContain('hello');
        expect(args).toContain('--comment');
        expect(args).toContain('important');
        expect(args).toContain('--position-json');
    });
    it('omits optional fields when not in payload', () => {
        const args = buildAnnotationCreateArgs('/vault', { extraArgs: [] }, { pdf_path: 'p.pdf', type: 'note' });
        expect(args).not.toContain('--selected-text');
        expect(args).not.toContain('--comment');
        expect(args).not.toContain('--color');
        expect(args).not.toContain('--page-index');
        expect(args).not.toContain('--position-json');
    });
});

describe('buildAnnotationPatchArgs', () => {
    it('includes annotation patch with id', () => {
        const args = buildAnnotationPatchArgs('/vault', { extraArgs: [] }, 42, { comment: 'updated' });
        expect(args).toContain('annotation');
        expect(args).toContain('patch');
        expect(args).toContain('42');
        expect(args).toContain('--comment');
        expect(args).toContain('updated');
    });
    it('includes color when in patch', () => {
        const args = buildAnnotationPatchArgs('/vault', { extraArgs: [] }, 7, { color: '#2ea8e5' });
        expect(args).toContain('--color');
        expect(args).toContain('#2ea8e5');
    });
    it('omits fields not in patch', () => {
        const args = buildAnnotationPatchArgs('/vault', { extraArgs: [] }, 1, {});
        expect(args).not.toContain('--comment');
        expect(args).not.toContain('--color');
    });
});

describe('buildAnnotationDeleteArgs', () => {
    it('includes annotation delete with id', () => {
        const args = buildAnnotationDeleteArgs('/vault', { extraArgs: [] }, 99);
        expect(args).toContain('annotation');
        expect(args).toContain('delete');
        expect(args).toContain('99');
        expect(args).toContain('--json');
    });
});

describe('parseAnnotationResult', () => {
    it('parses ok envelope with result array', () => {
        const r = parseAnnotationResult('{"ok": true, "result": [{"id": 1}]}');
        expect(r.ok).toBe(true);
        expect(r.data).toEqual([{ id: 1 }]);
    });
    it('parses ok envelope with data object', () => {
        const r = parseAnnotationResult('{"ok": true, "data": {"id": 1}}');
        expect(r.ok).toBe(true);
        expect(r.data).toEqual({ id: 1 });
    });
    it('parses ok envelope with null result gracefully', () => {
        const r = parseAnnotationResult('{"ok": true}');
        expect(r.ok).toBe(true);
        expect(r.data).toBeNull();
    });
    it('parses error envelope', () => {
        const r = parseAnnotationResult('{"ok": false, "error": "Zotero DB not found"}');
        expect(r.ok).toBe(false);
        expect(r.error).toContain('Zotero');
    });
    it('handles invalid JSON', () => {
        const r = parseAnnotationResult('not json');
        expect(r.ok).toBe(false);
        expect(r.error).toContain('JSON parse');
    });
    it('handles unexpected envelope', () => {
        const r = parseAnnotationResult('{"status": "ok"}');
        expect(r.ok).toBe(false);
        expect(r.error).toContain('envelope');
    });
});

describe('isReadonlyAnnotation', () => {
    it('returns true for zotero_synced annotation', () => {
        expect(isReadonlyAnnotation({ sync_state: 'zotero_synced' })).toBe(true);
    });
    it('returns false for local annotation', () => {
        expect(isReadonlyAnnotation({ sync_state: 'local' })).toBe(false);
    });
    it('returns false for null annotation', () => {
        expect(isReadonlyAnnotation(null)).toBe(false);
    });
    it('returns false for no sync_state', () => {
        expect(isReadonlyAnnotation({})).toBe(false);
    });
});

describe('groupAnnotationsByPage', () => {
    it('groups annotations by page_index', () => {
        const annotations = [
            { id: 1, page_index: 0 },
            { id: 2, page_index: 1 },
            { id: 3, page_index: 0 },
        ];
        const grouped = groupAnnotationsByPage(annotations);
        expect(grouped[0]).toHaveLength(2);
        expect(grouped[1]).toHaveLength(1);
        expect(grouped[0][0].id).toBe(1);
        expect(grouped[0][1].id).toBe(3);
    });
    it('handles empty array', () => {
        expect(groupAnnotationsByPage([])).toEqual({});
    });
    it('handles null input', () => {
        expect(groupAnnotationsByPage(null)).toEqual({});
    });
    it('defaults missing page_index to 0', () => {
        const annotations = [{ id: 1 }, { id: 2, page_index: 1 }];
        const grouped = groupAnnotationsByPage(annotations);
        expect(grouped[0]).toHaveLength(1);
        expect(grouped[1]).toHaveLength(1);
    });
});

describe('isAnnotationSupportedType', () => {
    it('returns true for highlight', () => {
        expect(isAnnotationSupportedType('highlight')).toBe(true);
    });
    it('returns true for underline', () => {
        expect(isAnnotationSupportedType('underline')).toBe(true);
    });
    it('returns true for note', () => {
        expect(isAnnotationSupportedType('note')).toBe(true);
    });
    it('returns false for image', () => {
        expect(isAnnotationSupportedType('image')).toBe(false);
    });
    it('returns false for ink', () => {
        expect(isAnnotationSupportedType('ink')).toBe(false);
    });
    it('returns false for unknown', () => {
        expect(isAnnotationSupportedType('text')).toBe(false);
    });
});

describe('normalizeAnnotationRects', () => {
    it('extracts rects from position.rects', () => {
        const ann = { position: { pageIndex: 1, rects: [[0, 0, 100, 20], [50, 30, 150, 40]] } };
        const rects = normalizeAnnotationRects(ann);
        expect(rects).toHaveLength(2);
        expect(rects[0]).toEqual([0, 0, 100, 20]);
    });
    it('parses rects from rects_json string', () => {
        const ann = { rects_json: '[[10, 20, 100, 30]]' };
        const rects = normalizeAnnotationRects(ann);
        expect(rects).toHaveLength(1);
        expect(rects[0]).toEqual([10, 20, 100, 30]);
    });
    it('returns null for null input', () => {
        expect(normalizeAnnotationRects(null)).toBeNull();
    });
    it('returns null when no rects available', () => {
        expect(normalizeAnnotationRects({})).toBeNull();
    });
    it('returns null for invalid rects_json', () => {
        expect(normalizeAnnotationRects({ rects_json: 'not json' })).toBeNull();
    });
});

describe('buildAnnotationPayloadFromSelection', () => {
    it('constructs payload with position JSON', () => {
        const payload = buildAnnotationPayloadFromSelection('paper.pdf', 'selected text', 2, { left: 0, top: 10, right: 100, bottom: 20 }, 'highlight');
        expect(payload.pdf_path).toBe('paper.pdf');
        expect(payload.selected_text).toBe('selected text');
        expect(payload.page_index).toBe(2);
        expect(payload.type).toBe('highlight');
        expect(payload.color).toBe('#ffd400');
        expect(payload.position_json).toContain('"pageIndex":2');
        expect(payload.position_json).toContain('"rects"');
    });
    it('defaults type to highlight', () => {
        const payload = buildAnnotationPayloadFromSelection('p.pdf', 'txt', 0, { left: 0, top: 0, right: 10, bottom: 10 });
        expect(payload.type).toBe('highlight');
    });
    it('accepts custom type', () => {
        const payload = buildAnnotationPayloadFromSelection('p.pdf', 'txt', 0, { left: 0, top: 0, right: 10, bottom: 10 }, 'underline');
        expect(payload.type).toBe('underline');
    });
});
