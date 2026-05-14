import { describe, expect, it } from 'vitest';

import { shouldRenderVectorReady } from '../src/testable.js';

describe('shouldRenderVectorReady', () => {
  it('keeps vector advanced UI visible while build status text is temporarily null', () => {
    expect(shouldRenderVectorReady(true, null)).toBe(true);
  });
});
