/**
 * Vitest tests for runtime.js — resolvePythonExecutable, getPluginVersion, checkRuntimeVersion.
 *
 * Uses dependency injection (last parameter) instead of vi.mock to avoid
 * CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const {
    readPathConfig,
    resolveRuntimePaths,
    resolvePythonExecutable,
    getPluginVersion,
    checkRuntimeVersion,
    runAnnotationSubprocess,
    normalizePdfRectToViewportPercent,
    groupAnnotationsByPage,
    isReadonlyAnnotation,
    isAnnotationSupportedType,
    ANNOTATION_COLORS,
} = await import('../src/testable.js');

describe('readPathConfig', () => {
    it('uses vault_config system_dir when present', () => {
        const mockFs = {
            existsSync: vi.fn(() => true),
            readFileSync: vi.fn(() => JSON.stringify({ vault_config: { system_dir: '99_System' } })),
        };
        const cfg = readPathConfig('/vault', mockFs);
        expect(cfg.system_dir).toBe('99_System');
        expect(cfg._warning).toBeNull();
    });

    it('falls back to defaults with warning when config is missing', () => {
        const mockFs = {
            existsSync: vi.fn(() => false),
            readFileSync: vi.fn(),
        };
        const cfg = readPathConfig('/vault', mockFs);
        expect(cfg.system_dir).toBe('System');
        expect(cfg._warning).toContain('using defaults');
    });

    it('falls back to defaults with warning when config is invalid', () => {
        const mockFs = {
            existsSync: vi.fn(() => true),
            readFileSync: vi.fn(() => '{bad json'),
        };
        const cfg = readPathConfig('/vault', mockFs);
        expect(cfg.system_dir).toBe('System');
        expect(cfg._warning).toContain('invalid');
    });
});

describe('resolveRuntimePaths', () => {
    it('uses configured system_dir for runtime file paths', () => {
        const mockFs = {
            existsSync: vi.fn(() => true),
            readFileSync: vi.fn(() => JSON.stringify({ vault_config: { system_dir: '99_System' } })),
        };
        const paths = resolveRuntimePaths('/vault', mockFs);
        expect(paths.memoryStatePath).toContain('99_System');
        expect(paths.exportsDir).toContain('99_System');
        expect(paths.ocrDir).toContain('99_System');
    });
});

describe('resolvePythonExecutable', () => {
    /** Create injected fs + execFileSync mocks */
    function mockDeps(existsSyncImpl, execFileSyncImpl) {
        return {
            fs: { existsSync: vi.fn(existsSyncImpl) },
            execFileSync: vi.fn(execFileSyncImpl),
        };
    }

    it('returns manual override when python_path is set and exists', () => {
        const d = mockDeps(() => true);
        const r = resolvePythonExecutable('/vault', { python_path: 'C:\\custom\\python.exe' }, d.fs, d.execFileSync);
        expect(r).toEqual({ path: 'C:\\custom\\python.exe', source: 'manual', extraArgs: [] });
        expect(d.fs.existsSync).toHaveBeenCalledWith('C:\\custom\\python.exe');
    });

    it('falls through when manual path does not exist and all candidates fail', () => {
        const d = mockDeps(() => false, () => { throw new Error('not found'); });
        const r = resolvePythonExecutable('/vault', { python_path: '/bad' }, d.fs, d.execFileSync);
        expect(r.path).toBe('python');
        expect(r.source).toBe('auto-detected');
    });

    it('returns venv path when .venv/Scripts/python.exe exists', () => {
        const d = mockDeps((p) => p.includes('.venv') && p.includes('python.exe'));
        const r = resolvePythonExecutable('/vault', {}, d.fs, d.execFileSync);
        expect(r.path).toContain('.venv');
        expect(r.source).toBe('auto-detected');
    });

    it('returns system candidate py -3 when it responds with python version', () => {
        const d = mockDeps(() => false, () => 'Python 3.11.0');
        const r = resolvePythonExecutable('/vault', {}, d.fs, d.execFileSync);
        expect(r).toEqual({ path: 'py', source: 'auto-detected', extraArgs: ['-3'] });
    });

    it('returns fallback python when nothing works', () => {
        const d = mockDeps(() => false, () => { throw new Error('not found'); });
        const r = resolvePythonExecutable('/vault', {}, d.fs, d.execFileSync);
        expect(r).toEqual({ path: 'python', source: 'auto-detected', extraArgs: [] });
    });
});

describe('getPluginVersion', () => {
    it('returns version from app.plugins manifest', () => {
        const app = {
            plugins: { plugins: { paperforge: { manifest: { version: '1.4.17rc3' } } } },
        };
        expect(getPluginVersion(app)).toBe('1.4.17rc3');
    });

    it('returns null when plugin not loaded', () => {
        expect(getPluginVersion({ plugins: { plugins: {} } })).toBeNull();
    });

    it('returns null for null app', () => {
        expect(getPluginVersion(null)).toBeNull();
    });
});

describe('checkRuntimeVersion', () => {
    let mockExecFile;

    beforeEach(() => {
        mockExecFile = vi.fn();
    });

    it('returns match when versions align', async () => {
        mockExecFile.mockImplementation((_e, _a, _o, cb) => cb(null, '1.4.17rc3\n'));
        const r = await checkRuntimeVersion('python', '1.4.17rc3', '/vault', 10000, mockExecFile);
        expect(r.status).toBe('match');
        expect(r.pyVersion).toBe('1.4.17rc3');
    });

    it('returns mismatch when versions differ', async () => {
        mockExecFile.mockImplementation((_e, _a, _o, cb) => cb(null, '1.4.16\n'));
        const r = await checkRuntimeVersion('python', '1.4.17rc3', '/vault', 10000, mockExecFile);
        expect(r.status).toBe('mismatch');
        expect(r.pyVersion).toBe('1.4.16');
    });

    it('returns not-installed on execFile error', async () => {
        mockExecFile.mockImplementation((_e, _a, _o, cb) => cb(new Error('ENOENT'), null));
        const r = await checkRuntimeVersion('python', '1.4.17rc3', '/vault', 10000, mockExecFile);
        expect(r.status).toBe('not-installed');
        expect(r.pyVersion).toBeNull();
        expect(r.error).toContain('ENOENT');
    });

    it('uses default timeout of 10000 when not provided', async () => {
        mockExecFile.mockImplementation((_e, _a, opts, cb) => {
            expect(opts.timeout).toBe(10000);
            cb(null, '1.4.17rc3\n');
        });
        await checkRuntimeVersion('python', '1.4.17rc3', '/vault', undefined, mockExecFile);
    });
});

describe('runAnnotationSubprocess', () => {
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

    it('prepends -m paperforge --vault before annotation args', async () => {
        const promise = runAnnotationSubprocess('/vault', { path: 'python', extraArgs: [] }, ['annotation', 'list', '--json'], 30000, mockSpawn);
        const [cmd, args] = mockSpawn.mock.calls[0];
        expect(cmd).toBe('python');
        expect(args).toContain('-m');
        expect(args).toContain('paperforge');
        expect(args).toContain('--vault');
        expect(args).toContain('/vault');
        expect(args).toContain('annotation');
        expect(args).toContain('list');
        expect(args).toContain('--json');
    });

    it('includes extraArgs from pythonInfo', async () => {
        runAnnotationSubprocess('/vault', { path: 'py', extraArgs: ['-3'] }, ['list'], 30000, mockSpawn);
        const args = mockSpawn.mock.calls[0][1];
        expect(args[0]).toBe('-3');
    });

    it('uses default timeout of 30000', async () => {
        runAnnotationSubprocess('/vault', { path: 'python', extraArgs: [] }, ['list'], undefined, mockSpawn);
        const opts = mockSpawn.mock.calls[0][2];
        expect(opts.timeout).toBe(30000);
    });

    it('returns subprocess result with stdout/exitCode', async () => {
        const promise = runAnnotationSubprocess('/vault', { path: 'python', extraArgs: [] }, ['list'], 30000, mockSpawn);
        const child = mockSpawn.mock.results[0].value;
        const closeCb = child.on.mock.calls.find(([e]) => e === 'close')[1];
        const dataCb = child.stdout.on.mock.calls.find(([e]) => e === 'data')[1];
        dataCb('{"ok": true, "result": []}');
        closeCb(0);
        const r = await promise;
        expect(r.exitCode).toBe(0);
        expect(r.stdout).toContain('ok');
    });

    it('resolves on spawn error gracefully', async () => {
        const promise = runAnnotationSubprocess('/vault', { path: 'python', extraArgs: [] }, ['list'], 30000, mockSpawn);
        const child = mockSpawn.mock.results[0].value;
        const errCb = child.on.mock.calls.find(([e]) => e === 'error')[1];
        errCb(new Error('ENOENT'));
        const r = await promise;
        expect(r.exitCode).toBe(-1);
    });
});

describe('annotation contract: normalizePdfRectToViewportPercent', () => {
    it('mirrors Y and returns correct percentages for letter-size viewBox', () => {
        // A Zotero highlight at bottom of page 1
        // rect: [left=61.1, bottom=323.2, right=291.8, top=331.8]
        // viewBox for US Letter: [0, 0, 612, 792]
        const pct = normalizePdfRectToViewportPercent(
            [61.137, 323.189, 291.762, 331.788],
            [0, 0, 612, 792]
        );
        expect(pct.left).toBeCloseTo(9.99, 1);
        expect(pct.top).toBeCloseTo(58.11, 1);
        expect(pct.width).toBeCloseTo(37.68, 1);
        expect(pct.height).toBeCloseTo(1.09, 1);
    });

    it('mirrors Y for a top-of-page rect', () => {
        const pct = normalizePdfRectToViewportPercent(
            [47.976, 127.268, 186.025, 135.866],
            [0, 0, 612, 792]
        );
        expect(pct.top).toBeCloseTo(82.85, 1);
        expect(pct.left).toBeCloseTo(7.84, 1);
    });

    it('returns zeros for empty input', () => {
        const pct = normalizePdfRectToViewportPercent(null, [0, 0, 612, 792]);
        expect(pct.left).toBe(0);
        expect(pct.top).toBe(0);
    });

    it('returns zeros for missing viewBox', () => {
        const pct = normalizePdfRectToViewportPercent([61, 323, 292, 332], null);
        expect(pct.left).toBe(0);
    });
});

describe('annotation contract: groupAnnotationsByPage', () => {
    it('groups annotations by page_index', () => {
        const anns = [
            { id: 'a', page_index: 0 },
            { id: 'b', page_index: 1 },
            { id: 'c', page_index: 0 },
        ];
        const g = groupAnnotationsByPage(anns);
        expect(g[0]).toHaveLength(2);
        expect(g[1]).toHaveLength(1);
    });

    it('uses 0 for missing page_index', () => {
        const g = groupAnnotationsByPage([{ id: 'x' }]);
        expect(g[0]).toHaveLength(1);
    });

    it('returns empty object for null', () => {
        expect(groupAnnotationsByPage(null)).toEqual({});
    });
});

describe('annotation contract: isReadonlyAnnotation', () => {
    it('returns true for zotero_synced annotations', () => {
        expect(isReadonlyAnnotation({ sync_state: 'zotero_synced' })).toBe(true);
    });

    it('returns false for local annotations', () => {
        expect(isReadonlyAnnotation({ sync_state: 'local' })).toBe(false);
        expect(isReadonlyAnnotation({})).toBe(false);
        expect(isReadonlyAnnotation(null)).toBe(false);
    });
});

describe('annotation contract: isAnnotationSupportedType', () => {
    it('supports highlight, underline, note', () => {
        expect(isAnnotationSupportedType('highlight')).toBe(true);
        expect(isAnnotationSupportedType('underline')).toBe(true);
        expect(isAnnotationSupportedType('note')).toBe(true);
    });

    it('rejects image, ink, text', () => {
        expect(isAnnotationSupportedType('image')).toBe(false);
        expect(isAnnotationSupportedType('ink')).toBe(false);
        expect(isAnnotationSupportedType('text')).toBe(false);
    });
});

describe('annotation contract: ANNOTATION_COLORS', () => {
    it('has 8 named colors', () => {
        expect(ANNOTATION_COLORS).toHaveLength(8);
        expect(ANNOTATION_COLORS[0].name).toBe('yellow');
    });

    it('each entry has a hex color', () => {
        for (const c of ANNOTATION_COLORS) {
            expect(c.hex).toMatch(/^#[0-9a-fA-F]{6}$/);
        }
    });
});
