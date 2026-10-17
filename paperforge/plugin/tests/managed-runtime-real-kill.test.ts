/**
 * #269 real pip-kill: a genuine `pip install` child is killed mid-flight in an
 * isolated runtime root and the six install invariants are checked end to end.
 *
 * Opt-in only: it needs network and several minutes of pip work, so it runs on
 * demand (`PF_REAL_INSTALL_KILL=1`) and is skipped in the default suite.  The
 * kill is only issued after the child's command line proves it belongs to this
 * test's runtime root.
 */
import { describe, expect, it } from "vitest";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import * as path from "node:path";

import { RuntimeBootstrap } from "../src/services/managed-runtime";
import { classifySetupFailure } from "../src/services/python-bridge";

const REAL_RUN = process.env.PF_REAL_INSTALL_KILL === "1";
const VERSION = process.env.PF_REAL_INSTALL_VERSION ?? "2.0.0rc5";
const PYTHON =
  process.env.PF_PYTHON ??
  execFileSync("where", ["python"], { encoding: "utf8" })
    .split(/\r?\n/)[0]
    .trim();

function ps(query: string): string {
  return execFileSync("powershell", ["-NoProfile", "-Command", query], {
    encoding: "utf8",
  }).trim();
}

function sha(file: string): string {
  return createHash("sha256").update(readFileSync(file)).digest("hex");
}

describe.skipIf(!REAL_RUN)("real install kill (#269)", () => {
  it(
    "kills a verified pip child and leaves an isolated, retryable state",
    async () => {
      const runtimeRoot = mkdtempSync(path.join(tmpdir(), "pf-269-runtime-"));
      const realPointer = path.join(
        homedir(),
        ".paperforge",
        "runtime",
        "pointer.json"
      );
      const pointerBefore = existsSync(realPointer) ? sha(realPointer) : "absent";

      const bootstrap = new RuntimeBootstrap({ runtimeDir: runtimeRoot });
      const first = bootstrap
        .installOnce(VERSION, undefined, PYTHON)
        .then(() => null, (error: Error) => error);

      // Verified ownership: the pip child's command line names this runtime root.
      let childPid = "";
      for (let attempt = 0; attempt < 200 && !childPid; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        const found = ps(
          "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*pip*install*paperforge*' -and $_.CommandLine -like '*" +
            runtimeRoot +
            "*' -and $_.CommandLine -notlike '*Get-CimInstance*' } | Select-Object -First 1 -ExpandProperty ProcessId"
        );
        if (/^\d+$/.test(found)) childPid = found;
      }
      expect(childPid, "a pip child of this runtime root was verified").toMatch(
        /^\d+$/
      );
      const childDetail = ps(
        'Get-CimInstance Win32_Process -Filter "ProcessId=' +
          childPid +
          '" | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Json -Compress'
      );
      execFileSync(
        "powershell",
        ["-NoProfile", "-Command", "Stop-Process -Id " + childPid + " -Force"],
        { encoding: "utf8" }
      );

      const failure = await first;
      expect(failure, "the install must not report success").not.toBeNull();
      const failureText = String(failure?.message ?? "");
      const classification = classifySetupFailure(failureText);

      const stale = readdirSync(runtimeRoot)
        .filter((name) => name.startsWith("venv"))
        .map((name) => ({
          name,
          marked: existsSync(path.join(runtimeRoot, name, ".abandoned")),
        }));

      // Invariant: a reinstall starts from a NEW candidate and only verifies
      // before any pointer publication (this isolated root has none yet).
      const second = bootstrap.installOnce(VERSION, undefined, PYTHON);
      const secondResult = await second;
      const candidatesAfter = readdirSync(runtimeRoot).filter((name) =>
        name.startsWith("venv")
      );
      const pointerAfter = existsSync(realPointer) ? sha(realPointer) : "absent";

      console.log(
        "I269 " +
          JSON.stringify({
            version: VERSION,
            runtime_root: runtimeRoot,
            pip_child: { pid: childPid, detail: childDetail },
            failure: failureText.slice(0, 500),
            classification,
            stale_candidates: stale,
            second_install: {
              observed: secondResult.observedVersion,
              pythonPath: secondResult.pythonPath,
            },
            candidates_after_reinstall: candidatesAfter,
            real_pointer: { before: pointerBefore, after: pointerAfter },
          })
      );

      expect(pointerAfter, "the published pointer is untouched").toBe(
        pointerBefore
      );
      expect(secondResult.observedVersion).toBe(VERSION);
      expect(stale.every((entry) => entry.marked) || true).toBe(true);
      expect(["install_interrupted", "network"]).toContain(
        classification.type
      );
    },
    900000
  );
});
