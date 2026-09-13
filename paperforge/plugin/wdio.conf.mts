import * as path from "path";
import { rmSync } from "node:fs";

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

// The child environment sanitizer still removes legacy credential variables;
// this backend only changes where the test's explicit seed is read.

export const config: WebdriverIO.Config = {
  runner: "local",
  framework: "mocha",
  specs: ["./test/specs/**/*.e2e.ts"],
  maxInstances: 1,
  capabilities: [
    {
      browserName: "obsidian",
      browserVersion: "latest",
      "wdio:obsidianOptions": {
        installerVersion: "latest",
        plugins: ["."],
        vault: "test/vaults/simple",
      },
    },
  ],
  services: ["obsidian"],
  reporters: ["obsidian"],
  cacheDir: path.resolve(".obsidian-cache"),
  mochaOpts: { ui: "bdd", timeout: 120000 },
  logLevel: "warn",
};
