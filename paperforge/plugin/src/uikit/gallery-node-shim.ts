/**
 * Browser-safe Node built-in stubs used ONLY when bundling the standalone
 * `ui-gallery.html` prototype via esbuild. Never imported by `main.js`.
 */

const normalizeSlash = (p: string): string =>
  String(p || "").replace(/\\/g, "/");

export const sep = "/";
export const delimiter = ":";

export function join(...parts: string[]): string {
  return normalizeSlash(parts.filter(Boolean).join("/")).replace(/\/+/g, "/");
}

export function resolve(...parts: string[]): string {
  const joined = join(...parts);
  return joined.startsWith("/") ? joined : `/${joined}`;
}

export function dirname(p: string): string {
  const s = normalizeSlash(p).replace(/\/+$/, "");
  const idx = s.lastIndexOf("/");
  return idx <= 0 ? (idx === 0 ? "/" : ".") : s.slice(0, idx);
}

export function basename(p: string, ext = ""): string {
  const s = normalizeSlash(p).replace(/\/+$/, "");
  const idx = s.lastIndexOf("/");
  let base = idx >= 0 ? s.slice(idx + 1) : s;
  if (ext && base.endsWith(ext)) {
    base = base.slice(0, base.length - ext.length);
  }
  return base;
}

export function extname(p: string): string {
  const base = basename(p);
  const idx = base.lastIndexOf(".");
  return idx > 0 ? base.slice(idx) : "";
}

export function relative(_from: string, to: string): string {
  return normalizeSlash(to).replace(/^\/+/, "");
}

export function isAbsolute(p: string): boolean {
  const s = normalizeSlash(p);
  return s.startsWith("/") || /^[A-Za-z]:\//.test(s);
}

export function existsSync(): boolean {
  return false;
}

export function mkdirSync(): void {}

export function readdirSync(): string[] {
  return [];
}

export function opendirSync() {
  return {
    readSync: () => null,
    closeSync: () => {},
  };
}

export const posix = {
  sep,
  delimiter,
  join,
  resolve,
  dirname,
  basename,
  extname,
  relative,
  isAbsolute,
};

export function statSync() {
  return {
    isDirectory: () => false,
    isFile: () => false,
    size: 0,
    mtimeMs: 0,
  };
}

export function readFileSync(): string {
  return "";
}

export function writeFileSync(): void {}
export function unlinkSync(): void {}
export function watch() {
  return { close() {} };
}

export const promises = {
  readFile: async () => "",
  writeFile: async () => {},
  stat: async () => statSync(),
  readdir: async () => [],
};

export function homedir(): string {
  return "/mock-home";
}

export function tmpdir(): string {
  return "/tmp";
}

export function platform(): string {
  return "win32";
}

export function arch(): string {
  return "x64";
}

export function get() {
  return {
    on: () => {},
    end: () => {},
  };
}

export function request() {
  return get();
}

export function spawn() {
  return {
    stdout: { on: () => {} },
    stderr: { on: () => {} },
    on: () => {},
    kill: () => {},
  };
}

export function execFile() {
  return spawn();
}

export function createHash() {
  return {
    update: () => ({
      digest: () => "00000000",
    }),
  };
}

export default {
  sep,
  delimiter,
  join,
  resolve,
  dirname,
  basename,
  extname,
  relative,
  isAbsolute,
  existsSync,
  mkdirSync,
  readdirSync,
  opendirSync,
  posix,
  statSync,
  readFileSync,
  writeFileSync,
  unlinkSync,
  watch,
  promises,
  homedir,
  tmpdir,
  platform,
  arch,
  get,
  request,
  spawn,
  execFile,
  createHash,
};
