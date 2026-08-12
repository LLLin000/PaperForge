/**
 * EmbedBuildController — single owner of the embed-build child process
 * lifecycle (issue #120).
 *
 * Consolidates the correct credential flow that previously lived only in
 * _renderVectorReady.startBuild: resolve credentials FIRST (await
 * buildTargetedEnv), then spawn with an explicit env so the real
 * ChildProcess handle is retained — _callPython's credentialType branch
 * returned null, which made duplicate-start guards and stop impossible on
 * the active path.
 *
 * States: idle → resolving_credentials → running → stopping
 *              → success | success_with_warning | failed
 */
import { spawn } from "child_process";

import { NdjsonStreamParser } from "./long-task-client";

export type EmbedBuildState =
  | "idle"
  | "resolving_credentials"
  | "running"
  | "stopping"
  | "success"
  | "success_with_warning"
  | "failed";

export interface EmbedBuildProgress {
  current: number;
  total: number;
  key: string;
}

export interface EmbedBuildControllerCallbacks {
  /** Fired on every state/progress change so the UI can re-render. */
  onStateChange: (
    state: EmbedBuildState,
    progress: EmbedBuildProgress,
    warning: string | null,
    stopResult: string | null
  ) => void;
}

interface EmbedBuildControllerOptions {
  vaultPath: string;
  pythonPath: string;
  pythonArgs: string[];
  /** Resolve the credential env for the embed command (await before spawn). */
  resolveEnv: () => Promise<Record<string, string | undefined>>;
  /** Run a short non-streaming python command (for stop). */
  runShort: (
    args: string[],
    timeoutMs: number
  ) => Promise<{ code: number; stdout: string; stderr: string }>;
  callbacks: EmbedBuildControllerCallbacks;
}

export class EmbedBuildController {
  private _state: EmbedBuildState = "idle";
  private _child: ReturnType<typeof spawn> | null = null;
  private _poll: ReturnType<typeof setInterval> | null = null;
  private _progress: EmbedBuildProgress = { current: 0, total: 0, key: "" };
  private _warning: string | null = null;
  private _stopResult: string | null = null;
  private _stderr = "";
  private _parser = new NdjsonStreamParser();
  private _graceTimer: ReturnType<typeof setTimeout> | null = null;
  private _disposed = false;

  constructor(private readonly _opts: EmbedBuildControllerOptions) {}

  get state(): EmbedBuildState {
    return this._state;
  }

  get progress(): EmbedBuildProgress {
    return this._progress;
  }

  get warning(): string | null {
    return this._warning;
  }

  /** True when a build is in flight or being stopped (blocks new starts). */
  get busy(): boolean {
    return (
      this._state === "resolving_credentials" ||
      this._state === "running" ||
      this._state === "stopping"
    );
  }

  /**
   * Start an embed build. No-op unless idle — the real duplicate-start
   * guard (the old `_embedProcess` check was null on the active path).
   */
  async start(flag: string): Promise<void> {
    if (this.busy || this._disposed) return;
    this._setState("resolving_credentials");
    this._warning = null;
    this._stopResult = null;
    this._stderr = "";
    this._parser = new NdjsonStreamParser();
    this._progress = { current: 0, total: 0, key: "" };

    let env: Record<string, string | undefined>;
    try {
      env = await this._opts.resolveEnv();
    } catch (err) {
      // A rejected secret promise must NOT leave the UI stuck running.
      this._warning = `Failed to resolve credentials: ${String(err)}`;
      this._setState("failed");
      return;
    }
    env.PYTHONIOENCODING = "utf-8";
    env.PYTHONUTF8 = "1";

    const child = spawn(
      this._opts.pythonPath,
      [...this._opts.pythonArgs, "embed", "build", flag],
      { cwd: this._opts.vaultPath, env, windowsHide: true }
    );
    this._child = child;

    child.stdout.on("data", (data: unknown) => {
      const text =
        typeof data === "string"
          ? data
          : Buffer.isBuffer(data)
            ? data.toString("utf-8")
            : String(data);
      const events = this._parser.feed(text);
      for (const ev of events) {
        // #137 NDJSON events (colon-token shapes retired).
        if (ev.event === "start") {
          this._progress.total = ev.total || 0;
        } else if (ev.event === "progress") {
          this._progress.current = ev.current || 0;
          this._progress.key = ev.item_id || "";
        } else if (ev.event === "result") {
          this._progress.current = this._progress.total;
          const res = ev.result as Record<string, unknown> | null;
          const warnings = res?.warnings as string[] | undefined;
          if (warnings && warnings.length > 0) {
            this._warning = String(warnings[0]);
          }
        } else if (ev.event === "error") {
          const err = (ev.result as Record<string, unknown> | null)
            ?.error as Record<string, unknown> | null;
          if (err && typeof err.message === "string") {
            this._warning = err.message;
          }
        }
      }
      this._emit();
    });

    child.stderr.on("data", (data: unknown) => {
      this._stderr += String(data);
    });

    child.on("error", (err: Error) => {
      this._child = null;
      this._stopPoll();
      this._warning = err.message || String(err);
      this._setState("failed");
    });

    child.on("close", (code: number | null) => {
      this._parser.finishEOF();
      if (this._graceTimer) clearTimeout(this._graceTimer);
      this._child = null;
      this._stopPoll();
      this._progress.current = this._progress.total;
      if (code === 0) {
        // The backend reports post-publish bookkeeping failures as rc=0
        // with the warning on stderr (non-JSON mode) or via EMBED_NOTICE —
        // surface them instead of silently showing a clean success.
        const stderrTail = (this._stderr || "").trim().slice(0, 300);
        if (!this._warning && stderrTail) {
          this._warning = stderrTail;
        }
        this._setState(this._warning ? "success_with_warning" : "success");
      } else {
        this._warning =
          (this._stderr || "").slice(0, 300) || `exit code ${code}`;
        this._setState("failed");
      }
      this._stderr = "";
    });

    this._startPoll();
    this._setState("running");
  }

  /**
   * #137 cooperative stop (T8 closure #169): stdin `PAPERFORGE_STOP\n`,
   * then a grace window, then hard escalation (Windows taskkill /T /F,
   * POSIX process-group SIGKILL).  The backend `embed stop` control plane
   * is retired — this controller owns its child.
   */
  async stop(): Promise<void> {
    if (this._state !== "running" || this._disposed) return;
    this._setState("stopping");
    this._stopResult = "stopped";
    const child = this._child;
    try {
      child?.stdin?.write("PAPERFORGE_STOP\n");
    } catch {
      // stdin closed — the exit path still settles.
    }
    if (this._graceTimer) return;
    const graceMs = 5000;
    this._graceTimer = setTimeout(() => {
      if (child && child.exitCode === null && !child.killed) {
        if (process.platform === "win32") {
          try {
            const pid = child.pid;
            if (!pid) return;
            spawn("taskkill", ["/T", "/F", "/PID", String(pid)], {
              stdio: "ignore",
            });
          } catch {
            child.kill("SIGKILL");
          }
        } else {
          try {
            const pid = child.pid;
            if (pid) process.kill(-pid, "SIGKILL");
          } catch {
            child.kill("SIGKILL");
          }
        }
        this._warning = "Build stopped after grace window (hard kill).";
      }
    }, graceMs);
  }

  /** Plugin unload: kill our own child, clear the poll. Bounded wait. */
  dispose(): void {
    this._disposed = true;
    this._stopPoll();
    const child = this._child;
    this._child = null;
    if (child && !child.killed) {
      child.kill();
    }
  }

  // ── internals ────────────────────────────────────────────────────────

  private _startPoll(): void {
    this._stopPoll();
    this._poll = setInterval(() => {
      if (this._state !== "running") return;
      void this._opts
        .runShort(["embed", "status", "--json"], 5000)
        .then(({ code, stdout }) => {
          if (code !== 0 || !stdout || this._state !== "running") return;
          try {
            const data = (JSON.parse(stdout) as { data?: unknown }).data as
              | { build_state?: Record<string, unknown> }
              | undefined;
            const bs = data?.build_state;
            if (bs && typeof bs.current === "number") {
              this._progress.current = bs.current;
              this._progress.total =
                typeof bs.total === "number" && bs.total > 0 ? bs.total : 1;
              this._progress.key = String(bs.paper_id ?? "");
              this._emit();
            }
          } catch {
            /* transient parse failure — ignore */
          }
        })
        .catch(() => {
          /* poll is best-effort */
        });
    }, 2000);
  }

  private _stopPoll(): void {
    clearInterval(this._poll ?? undefined);
    this._poll = null;
  }

  private _setState(state: EmbedBuildState): void {
    this._state = state;
    this._emit();
  }

  private _emit(): void {
    if (this._disposed) return;
    this._opts.callbacks.onStateChange(
      this._state,
      this._progress,
      this._warning,
      this._stopResult
    );
  }
}
