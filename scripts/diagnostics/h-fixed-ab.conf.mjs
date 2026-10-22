// Shared diagnostic configuration for the fixed-host A/B harness.
// Standalone wdio config: does NOT import production wdio.conf.mts
// (which copies the keyring fixture into the published runtime and
// reads a production pointer). No production credentials, no runtime
// pointer, no paid APIs, no full-H journey steps.
//
// Values are overridden per-cell by h-fixed-ab.mjs (old/new x on/off);
// this file only holds the shared skeleton. The vault entry below is a
// placeholder: the harness always overrides it with a per-cell GENERATED
// seed dir (Welcome.md), never a repo fixture path.

export const APP_VERSION = "1.14.4";
export const INSTALLER_VERSION = "1.5.8";

// Pinned full SHAs. Recorded per-cell and asserted; mismatch aborts the job.
export const OLD_REF = "ba666a57e81ca7094c46467547a34623b646890e";
export const NEW_REF = "a856f84f6bac666cebe22226110530133f489e33";

// Fail-closed boot probe budget (ms). Bounds one cell end to end: the
// parent enforces it as a hard child-process deadline (owned tree killed
// on timeout); it is also the single-command budget passed to the session.
export const BOOT_TIMEOUT_MS = 120000;

// Dead proxy for renderer HTTP(S). Loopback bypass preserves the CDP /
// driver channel on 127.0.0.1; everything else fails fast. This pairs with
// the in-harness Windows firewall block (owned ephemeral CI only), which is
// the genuine egress control — proxy env vars alone are not.
export const DEAD_PROXY = "http://127.0.0.1:9";

// Display-name prefix for the per-program firewall rules applied by run-all.
export const FIREWALL_RULE_PREFIX = "h-fixed-ab-block";

export function baseCapabilities() {
  return {
    browserName: "obsidian",
    browserVersion: APP_VERSION,
    "wdio:obsidianOptions": {
      appVersion: APP_VERSION,
      installerVersion: INSTALLER_VERSION,
      vault: "test/vaults/simple",
      copy: true,
      // binaryPath / appPath / plugins are forced per-cell by the harness.
    },
    // Forced per-cell to the pre-downloaded pinned driver; loopback only.
    // allowedIps: [] is passed through as --allowed-ips to chromedriver.
    "wdio:chromedriverOptions": {
      allowedIps: [],
    },
    // Explicit renderer proxy with loopback bypass. The service merges these
    // args after its own --user-data-dir handling, so they survive intact.
    "goog:chromeOptions": {
      args: [`--proxy-server=${DEAD_PROXY}`, "--proxy-bypass-list=<-loopback>"],
    },
  };
}
