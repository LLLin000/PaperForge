/**
 * Vitest tests for commands.js — ACTIONS, buildCommandArgs, runSubprocess.
 *
 * runSubprocess uses dependency injection (last _spawn param) instead of
 * vi.mock to avoid CJS/ESM module mocking limitations in vitest v2.1.x.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

const { ACTIONS, buildCommandArgs, runSubprocess } = await import('../src/commands.js');

describe('ACTIONS', () => {
    it('has exactly 6 entries', () => {
        expect(ACTIONS).toHaveLength(6);
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
    it('repair action has disabled: true', () => {
        expect(ACTIONS.find(a => a.id === 'paperforge-repair')?.disabled).toBe(true);
    });
    it('copy-context action has needsKey', () => {
        expect(ACTIONS.find(a => a.id === 'paperforge-copy-context')?.needsKey).toBe(true);
    });
    it('copy-collection-context action has needsFilter', () => {
        expect(ACTIONS.find(a => a.id === 'paperforge-copy-collection-context')?.needsFilter).toBe(true);
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
