export function getDisclosureState(
  store: Record<string, unknown> | null | undefined,
  key: string,
  defaultCollapsed: boolean,
): boolean {
  if (!store || typeof store !== "object") return !!defaultCollapsed;
  if (!Object.prototype.hasOwnProperty.call(store, key)) return !!defaultCollapsed;
  return !!store[key];
}

export function toggleDisclosureState(
  store: Record<string, unknown> | null | undefined,
  key: string,
  defaultCollapsed: boolean,
): boolean {
  const next = !getDisclosureState(store, key, defaultCollapsed);
  if (store && typeof store === "object") {
    store[key] = next;
  }
  return next;
}
