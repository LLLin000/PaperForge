import * as path from "path";
import * as os from "node:os";
import { execFileSync } from "node:child_process";
import { copyFileSync, readFileSync, rmSync } from "node:fs";

// Isolation: use a disposable file backend rather than the machine keyring.
// The real-provider W03 E2E test seeds this file with a fake key; every run
// starts empty, so credential-isolation checks cannot inherit developer keys.
const E2E_KEYRING_FILE = path.resolve(
  ".obsidian-cache",
  "paperforge-e2e-keyring.json"
);
rmSync(E2E_KEYRING_FILE, { force: true });
process.env.PAPERFORGE_KEYRING_BACKEND = "e2e_keyring.Keyring";
process.env.PAPERFORGE_E2E_KEYRING_FILE = E2E_KEYRING_FILE;
const keyringFixtureDir = path.resolve("test", "fixtures");
process.env.PYTHONPATH = process.env.PYTHONPATH
  ? `${keyringFixtureDir}${path.delimiter}${process.env.PYTHONPATH}`
  : keyringFixtureDir;

// The child environment sanitizer strips PYTHONPATH from plugin-spawned
// children (a deliberate guard), so the e2e keyring backend must be
// importable from the runtime environment itself: copy the fixture into the
// published runtime's site-packages. Without this, credential-gated actions
// (ocr.run, embed.*) report `unavailable` in-plugin even though the seed
// file is in place.
try {
  const pointerPath = path.resolve(
    os.homedir(),
    ".paperforge",
    "runtime",
    "pointer.json"
  );
  const pointer = JSON.parse(readFileSync(pointerPath, "utf8")) as {
    python_path?: string;
  };
  if (pointer.python_path) {
    // sysconfig.purelib, NOT site.getsitepackages(): the latter returns the
    // venv ROOT first for virtualenv pythons, which silently parked the
    // fixture outside import range.
    const sitePackages = execFileSync(
      pointer.python_path,
      ["-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
      { encoding: "utf8" }
    ).trim();
    if (sitePackages) {
      copyFileSync(
        path.resolve(keyringFixtureDir, "e2e_keyring.py"),
        path.resolve(sitePackages, "e2e_keyring.py")
      );
    }
  }
} catch {
  // No published runtime yet (install-journey cells publish one later).
}

// The child environment sanitizer still removes legacy credential variables;
// this backend only changes where the test's explicit seed is read.

const OBSIDIAN_APP_VERSION = process.env.PF_OBSIDIAN_APP_VERSION ?? "latest";
const OBSIDIAN_INSTALLER_VERSION =
  process.env.PF_OBSIDIAN_INSTALLER_VERSION ?? "latest";

export const config: WebdriverIO.Config = {
  runner: "local",
  framework: "mocha",
  specs: ["./test/specs/**/*.e2e.ts"],
  maxInstances: 1,
  capabilities: [
    {
      browserName: "obsidian",
      browserVersion: OBSIDIAN_APP_VERSION,
      "wdio:obsidianOptions": {
        installerVersion: OBSIDIAN_INSTALLER_VERSION,
        plugins: ["."],
        vault: "test/vaults/simple",
      },
    },
  ],
  services: ["obsidian"],
  reporters: ["obsidian"],
  cacheDir: path.resolve(".obsidian-cache"),
  // NOTE: @wdio/utils wraps every command in a timer derived from THIS
  // config value — per-test `this.timeout()` overrides do not raise it.
  // Slow profiles (P2 proxy networks) legitimately exceed 120s inside a
  // single install wait, so the budget must cover A01's 540s wait and the
  // journey's inner waits (found on the owner machine: a healthy install
  // poll was killed at ~118s with the 120000 default).
  mochaOpts: { ui: "bdd", timeout: 1200000 },
  logLevel: "warn",
};
