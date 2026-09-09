/**
 * Semantic-Boundary Cutover Integration Tests (Ticket 07 step 5 corrective).
 *
 * Verifies that:
 * 1. PaperForgeClient.resolvePaperContext() routes canonical identity
 *    resolution through `paper-lookup --from-path --json` and unwraps the
 *    PFResult envelope to the identity payload.
 * 2. Dashboard._resolveModeForFile() passes ONLY the host fact (the active
 *    vault-relative path) and consumes the Python identity — paper,
 *    collection (Base domain), and global (fail-closed) modes.
 * 3. Dashboard mode resolution NEVER reads Obsidian frontmatter, never
 *    infers identity from filenames/workspace keys, and never touches
 *    canonical files.
 * 4. _findEntry() returns the Python DTO entry as-is (frontmatter overlay
 *    is deleted) and the formal-library.json filename watcher is gone.
 * 5. Export health comes from Python check_permissions().can_sync, not a
 *    host-local exports-dir filesystem scan.
 */

import "obsidian-test-mocks/jest-setup";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { MockTransport } from "./mock-transport";
import { PaperForgeClient } from "../../src/client/paperforge-client";
import { PaperForgeStatusView } from "../../src/views/dashboard";
import { PaperForgeSettingTab } from "../../src/settings";

const { mockExecFile, mockSpawn } = vi.hoisted(() => ({
  mockExecFile: vi.fn(),
  mockSpawn: vi.fn(),
}));

vi.mock("child_process", () => ({
  execFile: mockExecFile,
  spawn: mockSpawn,
  default: { execFile: mockExecFile, spawn: mockSpawn },
}));

let transport: MockTransport;
let client: PaperForgeClient;

beforeEach(() => {
  transport = new MockTransport();
  client = new PaperForgeClient({ transport });
  mockExecFile.mockClear();
  mockSpawn.mockClear();
});

describe("PaperForgeClient.resolvePaperContext (Python authority)", () => {
  it("routes paper-lookup --from-path and unwraps the identity payload", async () => {
    transport.executeHandler = (argv) => {
      expect(argv).toEqual([
        "paper-lookup",
        "--from-path",
        "03_Resources/Literature/Cardio/ABCD1234/ABCD1234.md",
        "--json",
      ]);
      return JSON.stringify({
        ok: true,
        data: {
          intent: "paper-lookup",
          identity: {
            kind: "paper",
            zotero_key: "ABCD1234",
            entry: { zotero_key: "ABCD1234", title: "T" },
          },
        },
      });
    };
    const identity = await client.resolvePaperContext(
      "03_Resources/Literature/Cardio/ABCD1234/ABCD1234.md"
    );
    expect(identity && identity.kind).toBe("paper");
    expect(identity && identity.zotero_key).toBe("ABCD1234");
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockSpawn).not.toHaveBeenCalled();
  });

  it("resolves Base domains and returns null when the envelope carries none", async () => {
    transport.executeHandler = (argv) =>
      argv.includes("05_Bases/Cardio.base")
        ? JSON.stringify({
            ok: true,
            data: { identity: { kind: "domain", domain: "Cardio" } },
          })
        : JSON.stringify({
            ok: true,
            data: { identity: { kind: "unknown" } },
          });
    const domain = await client.resolvePaperContext("05_Bases/Cardio.base");
    expect(domain && domain.kind).toBe("domain");
    expect(domain && domain.domain).toBe("Cardio");
    // Unknown stays an identity OBJECT (informative); null is reserved for
    // a backend/transport failure (the dashboard catches that itself).
    const unknown = await client.resolvePaperContext("random/file.md");
    expect(unknown && unknown.kind).toBe("unknown");
  });

  it("propagates backend failure; the dashboard layer owns the catch", async () => {
    transport.executeHandler = () => {
      throw new Error("backend down");
    };
    await expect(
      client.resolvePaperContext("03_Resources/Literature/x.md")
    ).rejects.toThrow("backend down");
  });
});

describe("Dashboard mode resolution consumes Python identity", () => {
  function makeDashboard(clientInstance: PaperForgeClient | null) {
    const leaf = {} as any;
    const view = new (PaperForgeStatusView as any)(leaf) as any;
    view._getClient = () => clientInstance;
    view.app = {
      workspace: {
        getActiveFile: () => ({
          path: "03_Resources/Literature/Cardio/ABCD1234/ABCD1234.md",
          extension: "md",
          basename: "ABCD1234",
        }),
      },
      // NO metadataCache: if the resolver reaches for it, it throws —
      // making any frontmatter inference an observable failure.
    };
    return view;
  }

  it("paper identity -> paper mode with the canonical zotero_key", async () => {
    transport.executeHandler = () =>
      JSON.stringify({
        ok: true,
        data: {
          identity: { kind: "paper", zotero_key: "ABCD1234", entry: null },
        },
      });
    const view = makeDashboard(client);
    const resolved = await view._resolveModeForFile(
      view.app.workspace.getActiveFile()
    );
    expect(resolved.mode).toBe("paper");
    expect(resolved.key).toBe("ABCD1234");
    expect(resolved.domain).toBeNull();
  });

  it("domain identity -> collection mode without any filename parsing", async () => {
    const fileView = makeDashboard(client);
    fileView.app.workspace.getActiveFile = () =>
      ({
        path: "05_Bases/Cardio.base",
        extension: "base",
        basename: "Cardio",
      }) as any;
    transport.executeHandler = (argv) =>
      JSON.stringify({
        ok: true,
        data: { identity: { kind: "domain", domain: "Cardio" } },
      });
    const resolved = await fileView._resolveModeForFile(
      fileView.app.workspace.getActiveFile()
    );
    expect(resolved.mode).toBe("collection");
    expect(resolved.domain).toBe("Cardio");
    expect(resolved.key).toBeNull();
  });

  it("unknown identity fails closed to global mode (no filename inference)", async () => {
    transport.executeHandler = () =>
      JSON.stringify({
        ok: true,
        data: { identity: { kind: "unknown" } },
      });
    const view = makeDashboard(client);
    const resolved = await view._resolveModeForFile(
      view.app.workspace.getActiveFile()
    );
    expect(resolved.mode).toBe("global");
    expect(resolved.key).toBeNull();
    expect(resolved.domain).toBeNull();
  });

  it("backend-unavailable fails closed to global mode", async () => {
    transport.executeHandler = () => {
      throw new Error("down");
    };
    const view = makeDashboard(client);
    const resolved = await view._resolveModeForFile(
      view.app.workspace.getActiveFile()
    );
    expect(resolved.mode).toBe("global");
    expect(resolved.key).toBeNull();
  });

  it("no client -> global mode (thin-client fail-closed)", async () => {
    const view = makeDashboard(null);
    const resolved = await view._resolveModeForFile(
      view.app.workspace.getActiveFile()
    );
    expect(resolved.mode).toBe("global");
    expect(resolved.key).toBeNull();
  });
});

describe("Note workflow flags are Python authority (note set-flag)", () => {
  it("routes the toggle through note set-flag with the exact argv", async () => {
    transport.executeHandler = (argv) => {
      expect(argv).toEqual([
        "note",
        "set-flag",
        "--key",
        "ABCD1234",
        "--field",
        "do_ocr",
        "--value",
        "true",
        "--json",
      ]);
      return JSON.stringify({
        ok: true,
        data: { intent: "note-set-flag", changed: true },
      });
    };
    const out = await client.setNoteFlag("ABCD1234", "do_ocr", true);
    expect(out.changed).toBe(true);
    expect(mockExecFile).not.toHaveBeenCalled();
    expect(mockSpawn).not.toHaveBeenCalled();
  });

  it("reports changed=false for an idempotent backend no-op", async () => {
    transport.executeHandler = () =>
      JSON.stringify({
        ok: true,
        data: { intent: "note-set-flag", changed: false },
      });
    const out = await client.setNoteFlag("K1", "analyze", false);
    expect(out.changed).toBe(false);
  });

  it("advances the mutation epoch in a finally (success AND rejection)", async () => {
    let fail = true;
    transport.executeHandler = () => {
      if (fail)
        return JSON.stringify({
          ok: false,
          data: null,
          error: { code: "VALIDATION_ERROR", message: "unknown paper key" },
        });
      return JSON.stringify({
        ok: true,
        data: { intent: "note-set-flag", changed: true },
      });
    };
    const before = client.getEpoch();
    await expect(client.setNoteFlag("K1", "do_ocr", true)).rejects.toThrow(
      "unknown paper key"
    );
    // a settled failed mutation still closes the generation boundary —
    // stale in-flight reads must not resurrect across it
    expect(client.getEpoch()).toBe(before + 1);
    fail = false;
    const beforeOk = client.getEpoch();
    await client.setNoteFlag("K1", "do_ocr", true);
    expect(client.getEpoch()).toBe(beforeOk + 1);
  });

  it("propagates backend rejection (unknown field fails closed upstream)", async () => {
    transport.executeHandler = () =>
      // real PFResult serialization always carries "data" (null on failure)
      JSON.stringify({
        ok: false,
        data: null,
        error: {
          code: "VALIDATION_ERROR",
          message: "field must be one of do_ocr, analyze",
        },
      });
    await expect(client.setNoteFlag("K1", "analyze", true)).rejects.toThrow(
      "field must be one of"
    );
  });
});

describe("Single client owner (step 6 item 4)", () => {
  it("Settings never constructs a fallback client — it fails closed on the singleton", () => {
    const app = { vault: { adapter: { basePath: "/vault" } } } as any;
    const plugin = { settings: {} } as any; // NO getClient
    const tab = new (PaperForgeSettingTab as any)(app, plugin) as any;
    expect(() => tab.getClient()).toThrow(
      /plugin\.getClient singleton is missing/
    );
    // no second OperationLock/long-task owner can be created
    expect(tab._client).toBeNull();
  });

  it("Settings binds the plugin singleton when present", () => {
    const sentinel = { runAction: vi.fn() };
    const app = { vault: { adapter: { basePath: "/vault" } } } as any;
    const plugin = { getClient: () => sentinel, settings: {} } as any;
    const tab = new (PaperForgeSettingTab as any)(app, plugin) as any;
    expect(tab.getClient()).toBe(sentinel);
  });
});

describe("Version history is Python authority (step 6 item 6)", () => {
  it("routes discovery/manifest/backups/paths through the versions command", async () => {
    const calls: string[][] = [];
    transport.executeHandler = (argv) => {
      calls.push([...argv]);
      if (argv[1] === "list")
        return JSON.stringify({
          ok: true,
          data: {
            papers: [
              {
                key: "K1",
                title: "T",
                versions: [
                  {
                    label: "v1",
                    source_path: "/ocr/K1/versions/v1/fulltext.md",
                  },
                ],
                current_label: "v1",
                current_path: "/ocr/K1/render/fulltext.md",
                total_size: 5,
              },
            ],
          },
        });
      if (argv[1] === "show")
        return JSON.stringify({
          ok: true,
          data: {
            versions: [
              { label: "v2", source_path: "/ocr/K1/versions/v2/fulltext.md" },
            ],
            current_label: "v2",
            current_path: "/ocr/K1/render/fulltext.md",
          },
        });
      if (argv[1] === "backups")
        return JSON.stringify({
          ok: true,
          data: {
            backups: [
              {
                label: "backup-20250102030405",
                source_path: "/ocr/K1/backups/x.md",
              },
            ],
          },
        });
      if (argv[1] === "paths")
        return JSON.stringify({
          ok: true,
          data: {
            label: "v1",
            kind: "version",
            source_path: "/ocr/K1/versions/v1/fulltext.md",
            current_path: "/ocr/K1/render/fulltext.md",
          },
        });
      return JSON.stringify({
        ok: true,
        data: { target_path: "/ocr/K1/render/fulltext.md", label: "v1" },
      });
    };
    const list = await client.versionsList();
    expect(list[0].current_label).toBe("v1");
    expect(list[0].versions[0].source_path).toBe(
      "/ocr/K1/versions/v1/fulltext.md"
    );
    const show = await client.versionsShow("K1");
    expect(show.current_path).toBe("/ocr/K1/render/fulltext.md");
    const backups = await client.versionsBackups("K1");
    expect(backups[0].label).toBe("backup-20250102030405");
    const paths = await client.versionsPaths("K1", "v1");
    expect(paths.kind).toBe("version");
    expect(calls.map((c) => c[1])).toEqual([
      "list",
      "show",
      "backups",
      "paths",
    ]);
  });

  it("restore is a mutation: exact argv + epoch invalidation", async () => {
    transport.executeHandler = (argv) => {
      expect(argv).toEqual([
        "versions",
        "restore",
        "--key",
        "K1",
        "--label",
        "v1",
        "--json",
      ]);
      return JSON.stringify({
        ok: true,
        data: { target_path: "/ocr/K1/render/fulltext.md", label: "v1" },
      });
    };
    const before = client.getEpoch();
    const res = await client.versionsRestore("K1", "v1");
    expect(res.label).toBe("v1");
    expect(client.getEpoch()).toBe(before + 1);
  });
});

describe("Semantic-boundary source gates (frontmatter overlay deleted)", () => {
  const SRC = join(__dirname, "..", "..", "src");
  const dashboard = readFileSync(join(SRC, "views", "dashboard.ts"), "utf-8");
  const workspace = readFileSync(
    join(SRC, "views", "ocr-workspace.ts"),
    "utf-8"
  );
  const constants = readFileSync(join(SRC, "constants.ts"), "utf-8");

  it("_resolveModeForFile never reads Obsidian frontmatter or workspace keys", () => {
    const resolverStart = dashboard.indexOf("_resolveModeForFile");
    const resolverEnd = dashboard.indexOf("_detectAndSwitch", resolverStart);
    const resolver = dashboard.slice(resolverStart, resolverEnd);
    expect(resolver).not.toContain("metadataCache");
    expect(resolver).not.toContain("frontmatter");
    expect(resolver).not.toContain("_extractZoteroKeyFromPath");
    expect(resolver).toContain("resolvePaperContext");
  });

  it("_findEntry returns the Python DTO without the host overlay", () => {
    expect(dashboard).not.toContain("overlayEntryWorkflowState");
    expect(constants).not.toContain("overlayEntryWorkflowState");
  });

  it("no formal-library.json filename watcher (mutations reach the UI via refresh/sync only)", () => {
    expect(dashboard).not.toContain('path.endsWith("formal-library.json")');
    expect(dashboard).not.toContain('vault.on("modify"');
  });

  it("views never parse version manifests or legacy backup filenames", () => {
    for (const file of [dashboard, workspace]) {
      expect(file).not.toContain("manifest.json");
      expect(file).not.toContain("fulltext.pre-rebuild");
      expect(file).not.toContain("versionContentPath");
      expect(file).not.toContain("persistRestoreProvenance");
      expect(file).not.toContain("version-history");
    }
  });

  it("workflow toggles never mutate frontmatter client-side", () => {
    expect(dashboard).not.toContain("processFrontMatter(");
  });

  it("export health comes from Python permissions.can_sync, not an exports-dir fs scan", () => {
    expect(dashboard).toContain("_dashboardPermissions.can_sync");
    expect(dashboard).not.toContain('"PaperForge", "exports"');
  });
});
