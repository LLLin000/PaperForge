import { describe, expect, it } from 'vitest';

import { extractZoteroKeyFromPath } from '../src/utils/zotero-path';

describe('extractZoteroKeyFromPath', () => {
  it('extracts zotero key from workspace directory path', () => {
    expect(extractZoteroKeyFromPath('Resources/Literature/test/2AZ2EGQB - Paper/2AZ2EGQB.md')).toBe('2AZ2EGQB');
  });

  it('extracts zotero key from canonical OCR fulltext path', () => {
    expect(extractZoteroKeyFromPath('System/PaperForge/ocr/2AZ2EGQB/fulltext.md')).toBe('2AZ2EGQB');
  });
});
