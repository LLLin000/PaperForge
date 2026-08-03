/**
 * Deferred — Promise with externally held resolvers.
 *
 * The runtime target (Obsidian Electron / Node 20, lib ES2018) has no
 * Promise.withResolvers; this is the same pattern managed-runtime.ts
 * already used locally, shared here so callers keep linear control flow
 * without callback nesting.
 */
export interface Deferred<T> {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (err: unknown) => void;
}

export function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (err: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}
