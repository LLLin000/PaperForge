import { describe, expect, it } from "vitest";

import { PaperForgeClient } from "../../src/client/paperforge-client";
import { MockTransport } from "./mock-transport";

describe("runtimeStatus retry", () => {
  it("survives one cold-start failure and returns the second answer", async () => {
    const transport = new MockTransport();
    let calls = 0;
    transport.executeHandler = () => {
      calls += 1;
      if (calls === 1) throw new Error("cold venv: exit 1");
      return JSON.stringify({ runtime_ready: true, runtime_state: "ready" });
    };
    const client = new PaperForgeClient({ transport });

    const status = await client.runtimeStatus("2.0.0rc5");

    expect(status.runtime_ready).toBe(true);
    expect(calls).toBe(2);
  });

  it("reports the first failure when both attempts fail", async () => {
    const transport = new MockTransport();
    let calls = 0;
    transport.executeHandler = () => {
      calls += 1;
      throw new Error(`attempt ${calls} failed`);
    };
    const client = new PaperForgeClient({ transport });

    await expect(client.runtimeStatus("2.0.0rc5")).rejects.toThrow(
      "attempt 1 failed"
    );
    expect(calls).toBe(2);
  });
});
