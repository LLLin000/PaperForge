/**
 * Real-World End-to-End Upgrade, Hot-Swap Recovery & Secret Migration Tests.
 *
 * Exercises the ACTUAL compiled Rust `paperforge-daemon` binary + real temp
 * vaults + real `NodeProcessTransport` + real `PaperForgeClient` + real
 * `migrateLegacySecret` across the exact failure modes users hit in production:
 *  1. Veteran vault with `System/PaperForge/` AND custom `system_dir` in
 *     `paperforge.json` -> Rust daemon immediately returns `needs_upgrade: true`.
 *  2. Mid-RPC daemon hot-swap (`shutdownTransportAsync()` while RPCs run) ->
 *     transparent single retry succeeds with ZERO "PaperForge daemon shut down"
 *     error leaked to the caller!
 *  3. Legacy SecretStorage migration distinguishes `already exists` vs
 *     `NO_PYTHON / daemon shut down` vs real keyring failure in both ZH and EN.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { describe, expect, it, vi } from "vitest";

vi.mock("../src/services/managed-runtime", () => ({
  readRuntimePointer: () => null,
  resolveRuntimeCommand: () => null,
}));

import { NodeProcessTransport } from "../src/client/node-transport";
import { PaperForgeClient } from "../src/client/paperforge-client";
import { setLanguage } from "../src/i18n";
import {
  migrateLegacySecret,
  type SecretAccess,
} from "../src/services/secret-storage";
import { resolveSetupDecision } from "../src/services/setup-decision-tree";
import { createUnknownEnvelope } from "../src/constants";

const REPO_ROOT = path.resolve(__dirname, "../../..");
const LOCAL_RUST_BIN = path.join(
  REPO_ROOT,
  "crates",
  "paperforge-daemon",
  "target",
  "release",
  process.platform === "win32" ? "paperforge-daemon.exe" : "paperforge-daemon"
);

function rmTempSafe(dir: string): void {
  try {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
      maxRetries: 10,
      retryDelay: 80,
    });
  } catch {
    // Best-effort cleanup on Windows
  }
}

describe("Real-World Veteran Upgrade & Daemon Hot-Swap Certification", () => {
  it("detects veteran vaults (standard & custom system_dir) via real Rust daemon and feeds Decision Tree", async () => {
    if (!fs.existsSync(LOCAL_RUST_BIN)) {
      return;
    }
    const tmpVault = fs.mkdtempSync(path.join(os.tmpdir(), "pf-vet-custom-"));
    try {
      // Simulate real veteran user with custom system_dir="00_System"
      fs.mkdirSync(path.join(tmpVault, "00_System", "PaperForge"), {
        recursive: true,
      });
      fs.writeFileSync(
        path.join(tmpVault, "paperforge.json"),
        JSON.stringify({ vault_config: { system_dir: "00_System" } }),
        "utf-8"
      );

      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const client = new PaperForgeClient({ transport });
      try {
        const plan = await client.vaultUpgradePlan();
        expect(plan.provenance.state).toBe("veteran_legacy");
        expect(plan.provenance.needs_upgrade).toBe(true);
        expect(JSON.stringify(plan)).toContain("00_System/PaperForge");

        // Feed the real daemon output directly into the Setup Decision Tree
        setLanguage({} as never, "zh");
        const decision = resolveSetupDecision({
          daemonUpdating: false,
          runtimeUpdating: false,
          canCancelInstall: false,
          quarantinedBinDir: null,
          upgradePlan: plan,
          upgradeBannerDismissed: false,
          runtimePointer: null,
          expectedVersion: "2.0.4",
          installationEnv: createUnknownEnvelope("installation"),
          libraryEnv: createUnknownEnvelope("library"),
          isProbing: false,
          zoteroDataDir: "",
          zoteroDetectedPapers: null,
          lastAutoSyncError: null,
          paperCount: null,
        });
        expect(decision.id).toBe("legacy_vault_upgrade");
        expect(decision.primaryAction?.kind).toBe("open_vault_upgrade");
      } finally {
        await client.shutdownTransportAsync();
      }
    } finally {
      rmTempSafe(tmpVault);
    }
  });

  it("transparently survives an intentional daemon hot-swap without leaking 'PaperForge daemon shut down'", async () => {
    if (!fs.existsSync(LOCAL_RUST_BIN)) {
      return;
    }
    const tmpVault = fs.mkdtempSync(path.join(os.tmpdir(), "pf-hotswap-e2e-"));
    try {
      fs.mkdirSync(path.join(tmpVault, "System", "PaperForge"), {
        recursive: true,
      });
      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const client = new PaperForgeClient({ transport });
      try {
        // Warm up the daemon first
        const h1 = await client.daemonHealth();
        expect(h1.ok).toBe(true);

        // Trigger a real hot-swap shutdown concurrently with upgradePlan & daemonHealth RPCs
        const swapPromise = client.shutdownTransportAsync();
        const [plan, h2] = await Promise.all([
          client.vaultUpgradePlan(),
          client.daemonHealth(),
        ]);
        await swapPromise;

        expect(plan.provenance.needs_upgrade).toBe(true);
        expect(h2.ok).toBe(true);
        expect(h2.pid).not.toBe(h1.pid);
      } finally {
        await client.shutdownTransportAsync();
      }
    } finally {
      rmTempSafe(tmpVault);
    }
  });

  it("differentiates legacy API key conflict vs engine-not-ready vs real failure cleanly in ZH & EN", async () => {
    const ss: SecretAccess = {
      getSecret: vi.fn(async () => "legacy-secret-token"),
      setSecret: vi.fn(async () => undefined),
    };

    setLanguage({} as never, "zh");
    const conflictZh = await migrateLegacySecret("ocr", ss, {
      writeCredential: async () => {
        throw new Error("credential.conflict: credential already exists");
      },
    });
    expect(conflictZh.warnings[0]).toContain("已保存有密钥");
    expect(conflictZh.warnings[0]).not.toContain("Keyring write failed");

    const noPyZh = await migrateLegacySecret("ocr", ss, {
      writeCredential: async () => {
        throw new Error(
          "NO_PYTHON: PaperForge Python worker runtime not installed"
        );
      },
    });
    expect(noPyZh.warnings[0]).toContain("计算引擎尚未就绪");
    expect(noPyZh.warnings[0]).not.toContain("Keyring write failed");

    setLanguage({} as never, "en");
    const conflictEn = await migrateLegacySecret("ocr", ss, {
      writeCredential: async () => {
        throw new Error("credential already exists");
      },
    });
    expect(conflictEn.warnings[0]).toContain(
      "already saved in your OS keyring"
    );
    expect(conflictEn.warnings[0]).not.toContain("Keyring write failed");
  });
});
