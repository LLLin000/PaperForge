/**
 * Real-Obsidian end-to-end smoke for the PaperForge plugin (Ticket 07
 * post-closure frontend verification).
 *
 * Runs against a SANDBOXED Obsidian with the repo plugin installed from "."
 * — the same bundle Obsidian loads in production. Read-only assertions:
 * plugin load, registered surface, and the client reaching the real Python
 * backend.
 */
import { browser } from "@wdio/globals";

describe("PaperForge plugin in real Obsidian", function () {
  it("loads the plugin from the built bundle", async function () {
    await browser.reloadObsidian({ vault: "./test/vaults/simple" });
    const info = await browser.executeObsidian(({ app }) => {
      const plugin = (
        app as unknown as { plugins: { plugins: Record<string, any> } }
      ).plugins.plugins["paperforge"];
      return {
        present: !!plugin,
        id: plugin?.manifest?.id ?? null,
        version: plugin?.manifest?.version ?? null,
        hasClient: typeof plugin?.getClient === "function",
      };
    });
    expect(info.present).toBe(true);
    expect(info.id).toBe("paperforge");
    expect(info.hasClient).toBe(true);
  });

  it("reaches the real Python backend through the client interface", async function () {
    const result = await browser.executeObsidian(async ({ app }) => {
      const plugin = (
        app as unknown as { plugins: { plugins: Record<string, any> } }
      ).plugins.plugins["paperforge"];
      const client = plugin.getClient();
      const version = await client.backendVersion();
      // The sandbox vault carries a canonical paperforge.json, so the
      // installation probe must resolve through the real runtime pointer.
      const probe = await client.probe("installation");
      const typed = await client.dashboardStats();
      return {
        version,
        capability_state: probe?.capability_state ?? null,
        user_state: probe?.user_state ?? null,
        dashboard_keys: Object.keys(typed ?? {}).sort(),
      };
    });
    expect(result.version).toBe("1.5.15");
    expect(result.capability_state).toBe("ready");
    expect(result.user_state).toBe("ready");
    // typed DTO surface survived the real app round trip
    expect(result.dashboard_keys).toContain("stats");
    expect(result.dashboard_keys).toContain("items");
  });

  it("exposes the debug trace handle and renders the status panel", async function () {
    const traceOk = await browser.executeObsidian(({ app }) => {
      const plugin = (
        app as unknown as { plugins: { plugins: Record<string, any> } }
      ).plugins.plugins["paperforge"];
      return (
        typeof plugin.getDebugTrace === "function" &&
        typeof plugin.getDebugTrace() === "string"
      );
    });
    expect(traceOk).toBe(true);

    await browser.executeObsidianCommand("paperforge:paperforge-status-panel");
    const panel = await browser.$(".paperforge-header-title");
    await expect(panel).toExist();
  });
});
