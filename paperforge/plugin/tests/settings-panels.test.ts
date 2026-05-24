import { describe, expect, test } from 'vitest';

import { getDisclosureState, toggleDisclosureState } from "../src/utils/disclosure";

describe('feature panel disclosure state', () => {
  test('defaults vector config panel to expanded when no state exists', () => {
    expect(getDisclosureState({}, 'vectorConfig', false)).toBe(false);
  });

  test('persists collapsed state in the shared panel store', () => {
    const store = {};

    expect(toggleDisclosureState(store, 'vectorConfig', false)).toBe(true);
    expect(store.vectorConfig).toBe(true);
    expect(getDisclosureState(store, 'vectorConfig', false)).toBe(true);
  });

  test('reopens panel from stored collapsed state', () => {
    const store = { vectorConfig: true };

    expect(toggleDisclosureState(store, 'vectorConfig', false)).toBe(false);
    expect(store.vectorConfig).toBe(false);
    expect(getDisclosureState(store, 'vectorConfig', false)).toBe(false);
  });
});
