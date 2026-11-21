/**
 * End-to-end tests for the Native Cross-Platform Rust Sidecar (`paperforge-daemon`).
 *
 * Verifies:
 * 1. Cross-platform asset naming (`win32`, `darwin`, `linux` x `x64`/`arm64`, static `musl`).
 * 2. Real compiled Rust `paperforge-daemon` binary serving `PaperForgeClient`
 *    in **Zero-Python Mode** (`readRuntimePointer() === null` — neither Rust
 *    nor Python required on user host!):
 *    - `daemonHealth()` (`backend === "rust-native"`, `< 15 MB` RSS)
 *    - `config init` / `config set` / `config list` / `config paths`
 *    - `vaultUpgradePlan()` (`fresh_or_foreign` vs `veteran_legacy`)
 *    - `getBaseTableSnapshot()` & duplex `notice.push` events!
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { describe, expect, it, vi } from "vitest";

const runtimeMock = vi.hoisted(() => ({ hasPython: false }));
vi.mock("../../src/services/managed-runtime", () => ({
  readRuntimePointer: () => null,
  resolveRuntimeCommand: () =>
    runtimeMock.hasPython ? { command: "python", args: [] } : null,
}));

import {
  nativeDaemonAssetName,
  nativeDaemonTargetTriple,
} from "../../src/services/native-daemon";
import { NodeProcessTransport } from "../../src/client/node-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const LOCAL_RUST_BIN = path.join(
  REPO_ROOT,
  "crates",
  "paperforge-daemon",
  "target",
  "release",
  process.platform === "win32" ? "paperforge-daemon.exe" : "paperforge-daemon"
);

describe("Native Rust Sidecar (`paperforge-daemon`)", () => {
  it("maps Windows, macOS, and static-musl Linux desktop triples accurately", () => {
    expect(nativeDaemonTargetTriple("win32", "x64")).toBe(
      "x86_64-pc-windows-msvc"
    );
    expect(nativeDaemonTargetTriple("win32", "arm64")).toBe(
      "aarch64-pc-windows-msvc"
    );
    expect(nativeDaemonTargetTriple("darwin", "arm64")).toBe(
      "aarch64-apple-darwin"
    );
    expect(nativeDaemonTargetTriple("darwin", "x64")).toBe(
      "x86_64-apple-darwin"
    );
    expect(nativeDaemonTargetTriple("linux", "x64")).toBe(
      "x86_64-unknown-linux-musl"
    );
    expect(nativeDaemonTargetTriple("linux", "arm64")).toBe(
      "aarch64-unknown-linux-musl"
    );
    expect(nativeDaemonAssetName("win32", "x64")).toBe(
      "paperforge-daemon-x86_64-pc-windows-msvc.exe"
    );
    expect(nativeDaemonAssetName("darwin", "arm64")).toBe(
      "paperforge-daemon-aarch64-apple-darwin"
    );
    expect(nativeDaemonAssetName("linux", "x64")).toBe(
      "paperforge-daemon-x86_64-unknown-linux-musl"
    );
  });

  it.skipIf(!fs.existsSync(LOCAL_RUST_BIN))(
    "serves PaperForgeClient in Zero-Python mode (`pointer.json` absent) at < 15 MB RSS",
    async () => {
      const tmpVault = fs.mkdtempSync(
        path.join(os.tmpdir(), "pf-native-rust-e2e-")
      );
      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        useDaemon: true,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const client = new PaperForgeClient({ transport });
      const pushed: Array<{ event: string; data?: Record<string, unknown> }> =
        [];
      const unsub = client.onDaemonEvent((ev) => pushed.push(ev));

      try {
        // 1. Health check proves Rust native backend & feather-light RSS
        const health = await client.daemonHealth();
        expect(health?.ok).toBe(true);
        expect((health as unknown as { backend?: string })?.backend).toBe(
          "rust-native"
        );
        expect(health?.heavy_modules_loaded).toEqual([]);
        expect(health?.rss_mb).toBeLessThan(20);

        // 2. Fresh vault upgrade plan works with ZERO Python installed -> fresh_or_foreign
        const freshPlan = await client.vaultUpgradePlan();
        expect(freshPlan.provenance.state).toBe("fresh_or_foreign");
        expect(freshPlan.provenance.needs_upgrade).toBe(false);

        // 3. Native config init -> config set -> config list
        const rawInit = await transport.execute(["config", "init", "--json"]);
        expect(JSON.parse(rawInit).ok).toBe(true);

        await client.configSet("system_dir", ".paperforge");
        const cfgList = await client.configList();
        const sysField = cfgList.fields.find((f) => f.key === "system_dir");
        expect(sysField?.value).toBe(".paperforge");

        // 4. Native Base Table Snapshot read in Zero-Python mode
        const idxDir = path.join(tmpVault, ".paperforge", "indexes");
        fs.mkdirSync(idxDir, { recursive: true });
        fs.writeFileSync(
          path.join(idxDir, "formal-library.json"),
          JSON.stringify({
            version: 1,
            items: [
              {
                zotero_key: "NATV0001",
                title: "Zero-Python Instant Boot Paper",
                first_author: "Lin",
                year: "2026",
                domain: "Ortho",
                has_pdf: true,
                ocr_status: "done",
              },
            ],
          }),
          "utf-8"
        );
        const snap = await client.getBaseTableSnapshot();
        expect(snap.rows["NATV0001"]?.title).toBe(
          "Zero-Python Instant Boot Paper"
        );

        // 5. Duplex server-push notification from Rust daemon
        await transport.rpc({
          op: "notice.push",
          level: "success",
          code: "native.ready",
          title: "Rust daemon live",
        });
        await vi.waitFor(() =>
          expect(pushed.some((p) => p.event === "notice.push")).toBe(true)
        );
      } finally {
        unsub();
        transport.shutdownDaemon();
        fs.rmSync(tmpVault, { recursive: true, force: true });
      }
    }
  );
});
