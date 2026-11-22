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

import { execFileSync } from "child_process";
import * as crypto from "crypto";
import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import { describe, expect, it, vi } from "vitest";

const runtimeMock = vi.hoisted(() => ({
  pythonPath: null as string | null,
}));
vi.mock("../../src/services/managed-runtime", () => ({
  readRuntimePointer: () =>
    runtimeMock.pythonPath
      ? {
          schemaVersion: 1,
          pythonPath: runtimeMock.pythonPath,
          paperforgeVersion: "2.0.0",
        }
      : null,
  resolveRuntimeCommand: () =>
    runtimeMock.pythonPath
      ? { command: runtimeMock.pythonPath, args: [] }
      : null,
}));

function detectHostPython(): string | null {
  const candidates = [
    process.env.PF_PYTHON,
    process.platform === "win32" ? "python" : "python3",
    "python",
  ].filter((x): x is string => Boolean(x && x.trim()));
  for (const cand of candidates) {
    try {
      const exe = execFileSync(
        cand,
        ["-c", "import sys; print(sys.executable)"],
        { encoding: "utf-8", timeout: 5000 }
      ).trim();
      if (exe && fs.existsSync(exe)) return exe;
    } catch {
      // try next candidate
    }
  }
  return null;
}

function isPidAlive(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err: unknown) {
    const code = (err as { code?: string } | null)?.code;
    return code === "EPERM";
  }
}

function rmTempSafe(dir: string): void {
  try {
    fs.rmSync(dir, {
      recursive: true,
      force: true,
      maxRetries: 12,
      retryDelay: 100,
    });
  } catch {
    // Best-effort temp cleanup on Windows when antivirus/kernel delays cwd release.
  }
}

function writeMockWorkerPackage(vaultDir: string): void {
  const pkgDir = path.join(vaultDir, "paperforge");
  fs.mkdirSync(pkgDir, { recursive: true });
  fs.writeFileSync(path.join(pkgDir, "__init__.py"), "", "utf-8");
  fs.writeFileSync(
    path.join(pkgDir, "__main__.py"),
    [
      "import json, os, sys, time",
      "args = sys.argv[1:]",
      "vault = ''",
      "if '--vault' in args:",
      "    idx = args.index('--vault')",
      "    if idx + 1 < len(args):",
      "        vault = args[idx + 1]",
      "if 'slow-rpc' in args:",
      "    time.sleep(1.2)",
      "    print(json.dumps({'ok': True, 'mode': 'slow-rpc'}), flush=True)",
      "    sys.exit(0)",
      "if 'stream-cancel-test' in args:",
      "    print(json.dumps({'schema_version': 1, 'event': 'start', 'operation': 'ocr', 'total': 5}), flush=True)",
      "    print(json.dumps({'schema_version': 1, 'event': 'progress', 'operation': 'ocr', 'current': 1, 'total': 5, 'item_id': 'P001'}), flush=True)",
      "    line = sys.stdin.readline()",
      "    if 'PAPERFORGE_STOP' in line:",
      "        print(json.dumps({'schema_version': 1, 'event': 'cancelled', 'operation': 'ocr', 'current': 1, 'total': 5}), flush=True)",
      "        sys.exit(130)",
      "    print(json.dumps({'schema_version': 1, 'event': 'result', 'operation': 'ocr', 'result': {'ok': True}}), flush=True)",
      "    sys.exit(0)",
      "if 'orphan-sleep-test' in args:",
      "    if vault:",
      "        with open(os.path.join(vault, '.worker.pid'), 'w', encoding='utf-8') as f:",
      "            f.write(str(os.getpid()))",
      "    print(json.dumps({'schema_version': 1, 'event': 'start', 'operation': 'ocr', 'total': 1}), flush=True)",
      "    print(json.dumps({'schema_version': 1, 'event': 'progress', 'operation': 'ocr', 'current': 1, 'total': 1, 'item_id': 'ORPHAN1'}), flush=True)",
      "    time.sleep(30)",
      "    sys.exit(0)",
      "print(json.dumps({'ok': True, 'argv': args}), flush=True)",
    ].join("\n"),
    "utf-8"
  );
}

import {
  ensureNativeDaemonDownloaded,
  managedNativeDaemonPath,
  nativeDaemonAssetName,
  nativeDaemonTargetTriple,
  readNativeDaemonMeta,
  resolveNativeDaemonBinary,
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

  it("returns pre-installed native daemon immediately without network roundtrips", async () => {
    const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "pf-native-home-"));
    try {
      const binPath = managedNativeDaemonPath(tmpHome, process.platform);
      fs.mkdirSync(path.dirname(binPath), { recursive: true });
      fs.writeFileSync(binPath, Buffer.from("stub-binary"));

      const resolved = await ensureNativeDaemonDownloaded("2.0.1", {
        home: tmpHome,
        platform: process.platform,
        arch: process.arch,
      });
      expect(resolved).toBe(binPath);
    } finally {
      fs.rmSync(tmpHome, { recursive: true, force: true });
    }
  });

  it("detects SHA-256 drift even under identical SemVer and atomically flips to a versioned binary without Windows lock race", async () => {
    const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), "pf-native-sha-"));
    try {
      const asset = nativeDaemonAssetName(process.platform, process.arch)!;
      const binV1 = Buffer.from("paperforge-daemon-build-1");
      const shaV1 = crypto.createHash("sha256").update(binV1).digest("hex");
      const binV2 = Buffer.from("paperforge-daemon-build-2-fixed");
      const shaV2 = crypto.createHash("sha256").update(binV2).digest("hex");

      // 1. Seed initial install for tag 2.0.1 (build 1)
      let currentPayload = binV1;
      let currentSha = shaV1;
      let binFetches = 0;
      const mockFetch = async (url: string): Promise<Buffer> => {
        if (url.endsWith("/checksums.txt")) {
          return Buffer.from(`${currentSha}  ${asset}\n`, "utf-8");
        }
        binFetches += 1;
        return currentPayload;
      };

      const p1 = await ensureNativeDaemonDownloaded("2.0.1", {
        home: tmpHome,
        platform: process.platform,
        arch: process.arch,
        checkVersionUpdate: true,
        fetchBuffer: mockFetch,
      });
      expect(p1).toBeTruthy();
      expect(binFetches).toBe(1);
      expect(readNativeDaemonMeta(tmpHome, process.platform)?.sha256).toBe(
        shaV1
      );

      // 2. Same tag + SAME SHA-256 -> skips binary download
      const p1Again = await ensureNativeDaemonDownloaded("2.0.1", {
        home: tmpHome,
        platform: process.platform,
        arch: process.arch,
        checkVersionUpdate: true,
        fetchBuffer: mockFetch,
      });
      expect(p1Again).toBe(p1);
      expect(binFetches).toBe(1);

      // 3. Same tag + DIFFERENT SHA-256 -> downloads to a NEW versioned path & awaits onBeforeReplace
      currentPayload = binV2;
      currentSha = shaV2;
      let stoppedOld = false;
      const p2 = await ensureNativeDaemonDownloaded("2.0.1", {
        home: tmpHome,
        platform: process.platform,
        arch: process.arch,
        checkVersionUpdate: true,
        fetchBuffer: mockFetch,
        onBeforeReplace: async () => {
          stoppedOld = true;
        },
      });
      expect(binFetches).toBe(2);
      expect(stoppedOld).toBe(true);
      expect(p2).toBeTruthy();
      expect(p2).not.toBe(p1);
      expect(readNativeDaemonMeta(tmpHome, process.platform)?.sha256).toBe(
        shaV2
      );
      expect(
        resolveNativeDaemonBinary({
          home: tmpHome,
          platform: process.platform,
          arch: process.arch,
        })
      ).toBe(p2);

      // 4. Corrupt 1 byte of the on-disk binary while leaving .daemon-meta.json untouched:
      //    ensureNativeDaemonDownloaded MUST hash the live file and repair it!
      const corrupted = Buffer.from(binV2);
      corrupted[0] ^= 0xff;
      fs.writeFileSync(p2!, corrupted);
      let repairStopped = false;
      const p2Repaired = await ensureNativeDaemonDownloaded("2.0.1", {
        home: tmpHome,
        platform: process.platform,
        arch: process.arch,
        checkVersionUpdate: true,
        fetchBuffer: mockFetch,
        onBeforeReplace: async () => {
          repairStopped = true;
        },
      });
      expect(binFetches).toBe(3);
      expect(repairStopped).toBe(true);
      expect(p2Repaired).toBe(p2);
      expect(fs.readFileSync(p2Repaired!).equals(binV2)).toBe(true);
    } finally {
      rmTempSafe(tmpHome);
    }
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
        expect(snap.state_authority).toBe("legacy_json_fallback");
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

        // 6. Native Zero-Python zoteroDetect handles missing dir cleanly in <5ms
        const zotMissing = await client.zoteroDetect(
          path.join(tmpVault, "nonexistent-zotero")
        );
        expect(zotMissing.found).toBe(false);
        expect(zotMissing.collections).toEqual([]);
      } finally {
        unsub();
        transport.shutdownDaemon();
        rmTempSafe(tmpVault);
      }
    }
  );

  const HOST_PYTHON = detectHostPython();

  it.skipIf(!fs.existsSync(LOCAL_RUST_BIN) || !HOST_PYTHON)(
    "supervises NodeProcessTransport.stream() via Rust job.stream with unified job.list visibility and cooperative cancel",
    async () => {
      const tmpVault = fs.mkdtempSync(
        path.join(os.tmpdir(), "pf-native-stream-e2e-")
      );
      writeMockWorkerPackage(tmpVault);
      runtimeMock.pythonPath = HOST_PYTHON;

      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        useDaemon: true,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const client = new PaperForgeClient({ transport });
      const taskEvents: Array<Record<string, unknown>> = [];
      const unsub = client.onDaemonEvent((ev) => {
        if (ev.event === "task.updated" && ev.data) {
          taskEvents.push(ev.data);
        }
      });

      try {
        const seenEvents: string[] = [];
        const handle = transport.stream(["ocr", "stream-cancel-test"], {
          graceMs: 3000,
          onEvent: (ev) => seenEvents.push(ev.event),
        });

        // Wait until worker emits progress through Rust stream.chunk
        await vi.waitFor(() => expect(seenEvents).toContain("progress"), {
          timeout: 10000,
        });

        // Rust daemon job.list MUST see this interactive stream job!
        const jobsDuring = await client.daemonListJobs(true);
        expect(jobsDuring.active.length).toBe(1);
        const activeJob = jobsDuring.active[0];
        expect(activeJob.source).toBe("stream");
        expect(activeJob.kind).toBe("ocr");
        expect(activeJob.status).toBe("running");
        expect(activeJob.trace_id).toMatch(/^tr_/);
        expect(activeJob.current).toBe(1);
        expect(activeJob.item_id).toBe("P001");

        // Cooperative cancel via handle.stop() -> Rust job.cancel -> PAPERFORGE_STOP
        handle.stop();
        const outcome = await handle.outcome;
        expect(outcome.cancelled).toBe(true);
        expect(outcome.jobId).toBe(activeJob.job_id);
        expect(outcome.traceId).toBe(activeJob.trace_id);

        // Terminal job transitions out of active into recent_jobs
        await vi.waitFor(async () => {
          const jobsAfter = await client.daemonListJobs(true);
          expect(jobsAfter.active.length).toBe(0);
          const rec = jobsAfter.recent.find(
            (j) => j.job_id === activeJob.job_id
          );
          expect(rec?.status).toBe("cancelled");
        });
        expect(
          taskEvents.some(
            (e) => e.job_id === activeJob.job_id && e.status === "cancelled"
          )
        ).toBe(true);
      } finally {
        unsub();
        runtimeMock.pythonPath = null;
        transport.shutdownDaemon();
        rmTempSafe(tmpVault);
      }
    }
  );

  it.skipIf(!fs.existsSync(LOCAL_RUST_BIN) || !HOST_PYTHON)(
    "keeps Rust daemon RPC non-blocking while a slow Python worker is executing",
    async () => {
      const tmpVault = fs.mkdtempSync(
        path.join(os.tmpdir(), "pf-native-concurrent-e2e-")
      );
      writeMockWorkerPackage(tmpVault);
      runtimeMock.pythonPath = HOST_PYTHON;

      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        useDaemon: true,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const client = new PaperForgeClient({ transport });

      try {
        // Warm daemon first
        const warm = await client.daemonHealth();
        expect(warm?.ok).toBe(true);

        // Kick off a slow 1.2s delegated Python command
        const slowPromise = transport.execute(["slow-rpc"], {
          timeoutMs: 15000,
        });
        await new Promise((r) => setTimeout(r, 120));

        // Concurrent daemon.health MUST return immediately (< 500ms) while Python is busy
        const t0 = Date.now();
        const health = await client.daemonHealth();
        const elapsedMs = Date.now() - t0;
        expect(health?.ok).toBe(true);
        expect(elapsedMs).toBeLessThan(600);

        const slowOut = await slowPromise;
        expect(JSON.parse(slowOut).mode).toBe("slow-rpc");
      } finally {
        runtimeMock.pythonPath = null;
        transport.shutdownDaemon();
        rmTempSafe(tmpVault);
      }
    }
  );

  it.skipIf(!fs.existsSync(LOCAL_RUST_BIN) || !HOST_PYTHON)(
    "reaps child Python worker immediately when Rust daemon is hard-killed (zero orphans)",
    async () => {
      const tmpVault = fs.mkdtempSync(
        path.join(os.tmpdir(), "pf-native-orphan-e2e-")
      );
      writeMockWorkerPackage(tmpVault);
      runtimeMock.pythonPath = HOST_PYTHON;

      const transport = new NodeProcessTransport({
        vaultPath: tmpVault,
        useDaemon: true,
        nativeDaemonPath: LOCAL_RUST_BIN,
      });
      const pidFile = path.join(tmpVault, ".worker.pid");

      try {
        const handle = transport.stream(["ocr", "orphan-sleep-test"]);
        await vi.waitFor(() => expect(fs.existsSync(pidFile)).toBe(true), {
          timeout: 10000,
        });
        const workerPid = Number(fs.readFileSync(pidFile, "utf-8").trim());
        expect(workerPid).toBeGreaterThan(0);
        expect(isPidAlive(workerPid)).toBe(true);

        // Force-kill the Rust daemon process WITHOUT graceful shutdown RPC.
        // Windows Job Object (KILL_ON_JOB_CLOSE) / Linux PR_SET_PDEATHSIG must kill the worker.
        transport.shutdownDaemon(true);
        await handle.outcome;

        await vi.waitFor(() => expect(isPidAlive(workerPid)).toBe(false), {
          timeout: 5000,
        });
      } finally {
        runtimeMock.pythonPath = null;
        transport.shutdownDaemon(true);
        rmTempSafe(tmpVault);
      }
    }
  );

  it.skipIf(!fs.existsSync(LOCAL_RUST_BIN) || !HOST_PYTHON)(
    "serves Base Snapshot with SQLite SSOT authority over stale formal-library.json",
    async () => {
      const tmpVault = fs.mkdtempSync(
        path.join(os.tmpdir(), "pf-native-ssot-e2e-")
      );
      runtimeMock.pythonPath = null;

      try {
        const idxDir = path.join(tmpVault, ".paperforge", "indexes");
        fs.mkdirSync(idxDir, { recursive: true });
        fs.writeFileSync(
          path.join(idxDir, "formal-library.json"),
          JSON.stringify({
            version: 1,
            items: [
              {
                zotero_key: "SSOT0001",
                title: "Stale JSON Title",
                ocr_status: "pending",
                domain: "OldDomain",
                has_pdf: false,
              },
              {
                zotero_key: "DELETED99",
                title: "Deleted Ghost Paper",
                ocr_status: "done",
              },
            ],
          }),
          "utf-8"
        );
        const dbPath = path.join(idxDir, "paperforge.db");
        execFileSync(
          HOST_PYTHON!,
          [
            "-c",
            [
              "import sqlite3, sys",
              "conn = sqlite3.connect(sys.argv[1])",
              "conn.execute('CREATE TABLE papers (zotero_key TEXT PRIMARY KEY, title TEXT, first_author TEXT, year TEXT, journal TEXT, domain TEXT, ocr_status TEXT, deep_reading_status TEXT, impact_factor REAL, journal_partition TEXT, has_pdf INTEGER, do_ocr INTEGER, analyze INTEGER, collections_json TEXT)')",
              "conn.execute('CREATE TABLE workspace_registry (zotero_key TEXT PRIMARY KEY, main_note_relpath TEXT, domain TEXT, title TEXT)')",
              "conn.execute(\"INSERT INTO papers VALUES ('SSOT0001','Authoritative SQLite Title','Lin','2026','Nature','Ortho','done','finished',50.5,'Q1',1,1,0,'[\\\"Ortho/ACL\\\"]')\")",
              "conn.execute(\"INSERT INTO workspace_registry VALUES ('SSOT0001','Literature/SSOT.md','Ortho','Authoritative SQLite Title')\")",
              "conn.commit(); conn.close()",
            ].join("; "),
            dbPath,
          ],
          { encoding: "utf-8", timeout: 10000 }
        );

        const transport = new NodeProcessTransport({
          vaultPath: tmpVault,
          useDaemon: true,
          nativeDaemonPath: LOCAL_RUST_BIN,
        });
        const client = new PaperForgeClient({ transport });
        try {
          const snap = await client.getBaseTableSnapshot();
          expect(snap.state_authority).toBe("sqlite");
          expect(snap.rows["SSOT0001"]?.title).toBe(
            "Authoritative SQLite Title"
          );
          expect(snap.rows["SSOT0001"]?.ocr_status).toBe("done");
          expect(snap.rows["SSOT0001"]?.deep_reading_status).toBe("finished");
          expect(snap.rows["SSOT0001"]?.journal_partition).toBe("Q1");
          expect(snap.rows["SSOT0001"]?.has_pdf).toBe(true);
          expect(snap.rows["SSOT0001"]?.do_ocr).toBe(true);
          expect(snap.rows["SSOT0001"]?.collections).toEqual(["Ortho/ACL"]);
          expect(snap.rows["DELETED99"]).toBeUndefined();
        } finally {
          transport.shutdownDaemon();
        }
      } finally {
        rmTempSafe(tmpVault);
      }
    }
  );
});
