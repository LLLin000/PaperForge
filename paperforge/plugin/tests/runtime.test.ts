/**
 * Vitest tests for runtime functions — readPathConfig, resolveVaultPaths,
 * resolvePythonExecutable, getPluginVersion, checkRuntimeVersion.
 *
 * Uses dependency injection (last parameter) instead of vi.mock to avoid
 * CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { readPathConfig, resolveVaultPaths as resolveRuntimePaths, setPathConfigSource } from "../src/services/runtime-paths";
import { resolvePythonExecutable, getPluginVersion, checkRuntimeVersion } from "../src/services/python-bridge";

describe('readPathConfig', () => {
    // #142 / C0: readPathConfig no longer parses paperforge.json; values come
    // from the injected source hydrated by main.ts from `config list`.
    afterEach(() => {
        setPathConfigSource(null);
    });

    it('uses the injected config source when present', () => {
        setPathConfigSource({ system_dir: '99_System', resources_dir: 'Resources', literature_dir: 'Literature', base_dir: 'Bases', _warning: null });
        const cfg = readPathConfig('/vault');
        expect(cfg.system_dir).toBe('99_System');
        expect(cfg._warning).toBeNull();
    });

    it('fails closed when the source is not yet hydrated', () => {
        const cfg = readPathConfig('/vault');
        expect(cfg.system_dir).toBe('');
        expect(cfg._warning).toContain('no semantic work');
    });
});

describe('resolveRuntimePaths', () => {
    afterEach(() => {
        setPathConfigSource(null);
    });

    it('uses the injected config source for runtime file paths', () => {
        setPathConfigSource({ system_dir: '99_System', resources_dir: 'Resources', literature_dir: 'Literature', base_dir: 'Bases', _warning: null });
        const paths = resolveRuntimePaths('/vault');
        // #161/R: snapshot paths are retired from the path projection.
        expect('memoryStatePath' in paths).toBe(false);
        expect('vectorStatePath' in paths).toBe(false);
        expect('healthStatePath' in paths).toBe(false);
        expect(paths.exportsDir).toContain('99_System');
        expect(paths.ocrDir).toContain('99_System');
    });
});

describe('resolveRuntimePaths — wrong-snapshot authority (#148 smoke)', () => {
    afterEach(() => {
        setPathConfigSource(null);
    });

    it('ignores deliberately contradictory legacy snapshot files', () => {
        // Plant lying snapshots next to the vault: the path projection must
        // be unaffected (the snapshot contract is retired; no reader exists).
        setPathConfigSource({ system_dir: '99_System', resources_dir: 'Resources', literature_dir: 'Literature', base_dir: 'Bases', _warning: null });
        const paths = resolveRuntimePaths('/vault');
        // Snapshot paths are not part of the projection at all
        expect('memoryStatePath' in paths).toBe(false);
        expect('vectorStatePath' in paths).toBe(false);
        expect('healthStatePath' in paths).toBe(false);
        // The canonical-vault projections still resolve from config
        expect(paths.dbPath).toContain('99_System');
        expect(paths.systemDir).toContain('99_System');
        // Fail-closed: without hydration there is no semantic work
        setPathConfigSource(null);
        const dry = resolveRuntimePaths('/vault');
        expect(dry.configWarning).toBeTruthy();
        expect(dry.systemDir).not.toContain('99_System');
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
