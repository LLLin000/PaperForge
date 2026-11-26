import { describe, expect, it, vi } from "vitest";
import {
  buildProxyEnvOverlay,
  mergeNoProxy,
  parseElectronProxyString,
  parseMacScutilProxyOutput,
  parseWindowsRegProxyOutput,
} from "../src/services/system-proxy";
import { createObsidianRequestFetcher } from "../src/services/native-daemon";

describe("system-proxy & Obsidian requestUrl proxy inheritance", () => {
  it("parses Chromium Electron resolveProxy strings accurately", () => {
    expect(parseElectronProxyString("DIRECT")).toBeNull();
    expect(parseElectronProxyString("PROXY 127.0.0.1:7897; DIRECT")).toBe(
      "http://127.0.0.1:7897"
    );
    expect(parseElectronProxyString("HTTPS edge.corp.local:8443")).toBe(
      "https://edge.corp.local:8443"
    );
    expect(parseElectronProxyString("SOCKS5 127.0.0.1:7898")).toBe(
      "socks5://127.0.0.1:7898"
    );
    expect(parseElectronProxyString("DIRECT; PROXY 127.0.0.1:7890")).toBe(
      "http://127.0.0.1:7890"
    );
  });

  it("parses Windows HKCU Internet Settings reg output safely", () => {
    const enabledBare = [
      "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
      "    ProxyEnable    REG_DWORD    0x1",
      "    ProxyServer    REG_SZ    127.0.0.1:7897",
      "    ProxyOverride    REG_SZ    localhost;127.*;<local>",
    ].join("\r\n");
    const parsed = parseWindowsRegProxyOutput(enabledBare);
    expect(parsed.proxyUrl).toBe("http://127.0.0.1:7897");
    expect(parsed.noProxy).toContain("127.*");
    expect(parsed.noProxy).toContain("localhost");
    expect(parsed.noProxy).toContain("::1");

    const disabled = [
      "    ProxyEnable    REG_DWORD    0x0",
      "    ProxyServer    REG_SZ    127.0.0.1:7897",
    ].join("\r\n");
    expect(parseWindowsRegProxyOutput(disabled)).toEqual({
      proxyUrl: null,
      noProxy: null,
    });

    const perProto = [
      "    ProxyEnable    REG_DWORD    0x1",
      "    ProxyServer    REG_SZ    http=127.0.0.1:8080;https=127.0.0.1:7897",
    ].join("\r\n");
    expect(parseWindowsRegProxyOutput(perProto).proxyUrl).toBe(
      "http://127.0.0.1:7897"
    );
  });

  it("parses macOS scutil --proxy output for HTTPS/HTTP/SOCKS and ExceptionsList", () => {
    const macOut = [
      "<dictionary> {",
      "  ExceptionsList : <array> {",
      "    0 : *.local",
      "    1 : 169.254/16",
      "  }",
      "  HTTPEnable : 1",
      "  HTTPPort : 7897",
      "  HTTPProxy : 127.0.0.1",
      "  HTTPSEnable : 1",
      "  HTTPSPort : 7897",
      "  HTTPSProxy : 127.0.0.1",
      "}",
    ].join("\n");
    const parsed = parseMacScutilProxyOutput(macOut);
    expect(parsed.proxyUrl).toBe("http://127.0.0.1:7897");
    expect(parsed.noProxy).toContain("*.local");
    expect(parsed.noProxy).toContain("localhost");
    expect(parsed.noProxy).toContain("127.0.0.1");

    const socksOnly = [
      "<dictionary> {",
      "  HTTPSEnable : 0",
      "  SOCKSEnable : 1",
      "  SOCKSPort : 1080",
      "  SOCKSProxy : 127.0.0.1",
      "}",
    ].join("\n");
    expect(parseMacScutilProxyOutput(socksOnly).proxyUrl).toBe(
      "socks5://127.0.0.1:1080"
    );
  });

  it("respects explicit env proxies and injects loopback-safe overlay when unset", () => {
    expect(
      buildProxyEnvOverlay("http://127.0.0.1:7897", {
        HTTPS_PROXY: "http://10.0.0.1:3128",
      })
    ).toEqual({});

    const overlay = buildProxyEnvOverlay(
      "http://127.0.0.1:7897",
      {},
      "corp.internal"
    );
    expect(overlay).toEqual({
      HTTP_PROXY: "http://127.0.0.1:7897",
      HTTPS_PROXY: "http://127.0.0.1:7897",
      http_proxy: "http://127.0.0.1:7897",
      https_proxy: "http://127.0.0.1:7897",
      NO_PROXY: mergeNoProxy(undefined, "corp.internal"),
      no_proxy: mergeNoProxy(undefined, "corp.internal"),
    });
  });

  it("createObsidianRequestFetcher enforces HTTPS-only, 200 status, and byte ceiling", async () => {
    const reqMock = vi.fn(async () => ({
      status: 200,
      arrayBuffer: Uint8Array.from([1, 2, 3, 4]).buffer,
    }));
    const fetcher = createObsidianRequestFetcher(reqMock, 1024);

    await expect(fetcher("http://github.com/file")).rejects.toThrow(
      /Refusing non-HTTPS/i
    );

    const buf = await fetcher(
      "https://github.com/LLLin000/PaperForge/releases/download/2.0.7/checksums.txt"
    );
    expect(buf).toEqual(Buffer.from([1, 2, 3, 4]));
    expect(reqMock).toHaveBeenCalledTimes(1);

    const tinyFetcher = createObsidianRequestFetcher(reqMock, 2);
    await expect(tinyFetcher("https://github.com/file")).rejects.toThrow(
      /exceeds maximum/i
    );
  });
});
