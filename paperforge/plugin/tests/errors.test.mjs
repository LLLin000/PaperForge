/**
 * Vitest tests for errors.js — classifyError, buildRuntimeInstallCommand, parseRuntimeStatus.
 */
import { describe, it, expect } from 'vitest';

const {
    classifyError,
    buildRuntimeInstallCommand,
    parseRuntimeStatus,
} = await import('../src/testable.js');

describe('classifyError', () => {
    it('classifies ENOENT as python_missing', () => {
        const result = classifyError('ENOENT');
        expect(result.type).toBe('python_missing');
        expect(result.recoverable).toBe(true);
        expect(result.message).toContain('Python');
    });

    it('classifies MODULE_NOT_FOUND as import_failed', () => {
        const result = classifyError('MODULE_NOT_FOUND');
        expect(result.type).toBe('import_failed');
        expect(result.recoverable).toBe(true);
    });

    it('classifies version-mismatch with sync-runtime action', () => {
        const result = classifyError('version-mismatch');
        expect(result.type).toBe('version_mismatch');
        expect(result.recoverable).toBe(true);
        expect(result.action).toBe('sync-runtime');
    });

    it('classifies pip-failed as pip_install_failure', () => {
        const result = classifyError('pip-failed');
        expect(result.type).toBe('pip_install_failure');
        expect(result.recoverable).toBe(true);
    });

    it('classifies ETIMEDOUT as timeout with retry action', () => {
        const result = classifyError('ETIMEDOUT');
        expect(result.type).toBe('timeout');
        expect(result.recoverable).toBe(true);
        expect(result.action).toBe('retry');
    });

    it('classifies unknown error strings as unknown', () => {
        const result = classifyError('SOME_RANDOM_ERROR');
        expect(result.type).toBe('unknown');
        expect(result.recoverable).toBe(false);
        expect(result.message).toBe('SOME_RANDOM_ERROR');
    });

    it('classifies numeric exit codes as unknown', () => {
        const result = classifyError(1);
        expect(result.type).toBe('unknown');
        expect(result.recoverable).toBe(false);
    });
});

describe('buildRuntimeInstallCommand', () => {
    it('constructs correct URL with version tag', () => {
        const result = buildRuntimeInstallCommand('python', '1.4.17rc3');
        expect(result.cmd).toBe('python');
        expect(result.url).toBe('git+https://github.com/LLLin000/PaperForge.git@1.4.17rc3');
        expect(result.args).toContain('-m');
        expect(result.args).toContain('pip');
        expect(result.args).toContain('install');
        expect(result.args).toContain('--upgrade');
    });

    it('includes extraArgs when provided', () => {
        const result = buildRuntimeInstallCommand('python', '1.4.17rc3', ['-3']);
        expect(result.args[0]).toBe('-3');
    });

    it('timeout is 120000', () => {
        const result = buildRuntimeInstallCommand('python', '1.4.17rc3');
        expect(result.timeout).toBe(120000);
    });
});

describe('parseRuntimeStatus', () => {
    it('returns ok with version on success', () => {
        const result = parseRuntimeStatus(null, '1.4.17rc3\n', '');
        expect(result.status).toBe('ok');
        expect(result.version).toBe('1.4.17rc3');
    });

    it('classifies ENOENT as python_missing', () => {
        const err = new Error('spawn ENOENT');
        err.code = 'ENOENT';
        const result = parseRuntimeStatus(err, null, '');
        expect(result.status).toBe('error');
        expect(result.type).toBe('python_missing');
    });

    it('classifies ModuleNotFoundError in stderr as import_failed', () => {
        const result = parseRuntimeStatus(new Error('fail'), null, 'No module named paperforge');
        expect(result.status).toBe('error');
        expect(result.type).toBe('import_failed');
    });

    it('classifies killed/timeout subprocess as timeout', () => {
        const err = new Error('timeout');
        err.killed = true;
        const result = parseRuntimeStatus(err, null, '');
        expect(result.status).toBe('error');
        expect(result.type).toBe('timeout');
    });

    it('classifies generic error as unknown', () => {
        const err = new Error('Something went wrong');
        const result = parseRuntimeStatus(err, null, 'some output');
        expect(result.status).toBe('error');
        expect(result.type).toBe('unknown');
    });
});
