import * as path from "path";

// Isolation: the OS keyring is machine-level, so a sandbox vault inherits the
// developer's real credential — `paperforge auth status` reported
// `state=available, source=keyring` inside a throw-away vault. That makes every
// "fails closed without credentials" assertion meaningless and lets a test
// spend a real provider quota. The transport's credential strip cannot help
// here (it removes env prefixes; the secret never was in the environment), so
// the backend is pointed at a null keyring instead. `paperforge/credentials.py`
// honours PAPERFORGE_KEYRING_BACKEND, and the strip only removes
// PAPERFORGE_CREDENTIAL_* / PADDLEOCR_* / VECTOR_DB_* / OPENAI_*, so this value
// reaches the child intact.
process.env.PAPERFORGE_KEYRING_BACKEND = "keyring.backends.null.Keyring";

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
