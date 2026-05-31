import { describe, it, expect } from 'vitest';
import { shouldBlockStep3 } from '../src/views/step3-gate';

describe('shouldBlockStep3', () => {
  it('validated key + valid Zotero dir → no block', () => {
    expect(shouldBlockStep3(true, '/valid/zotero')).toEqual({ blocked: false });
  });

  it('unvalidated key + valid Zotero dir → confirmation needed (NOT hard block)', () => {
    const r = shouldBlockStep3(false, '/valid/zotero');
    expect(r.blocked).toBe(true);
    expect(r.reason).toBe('ocr');
  });

  it('unvalidated key + missing Zotero dir → hard block (Zotero)', () => {
    const r = shouldBlockStep3(false, '');
    expect(r.blocked).toBe(true);
    expect(r.reason).toBe('zotero');
  });

  it('validated key + missing Zotero dir → hard block (Zotero)', () => {
    const r = shouldBlockStep3(true, '');
    expect(r.blocked).toBe(true);
    expect(r.reason).toBe('zotero');
  });

  it('unvalidated key + whitespace Zotero dir → hard block', () => {
    const r = shouldBlockStep3(false, '   ');
    expect(r.blocked).toBe(true);
    expect(r.reason).toBe('zotero');
  });

  it('Zotero check takes priority over OCR check', () => {
    const r = shouldBlockStep3(false, '');
    expect(r.blocked).toBe(true);
    expect(r.reason).toBe('zotero');
  });
});
