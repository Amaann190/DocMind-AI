import { afterEach, describe, expect, it, vi } from "vitest";
import { api, storageKey, storePreferences } from "./api.js";

afterEach(() => vi.unstubAllGlobals());

function respond(status, body) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    statusText: "Bad",
    json: () => Promise.resolve(body),
  });
}

describe("api", () => {
  it("sends the client header and JSON content type", async () => {
    const fetch = respond(200, { ok: true });
    vi.stubGlobal("fetch", fetch);
    await api("/settings", { method: "PUT", body: "{}" });
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/api/settings");
    expect(options.headers["X-DocMind-Client"]).toBe("react");
    expect(options.headers["Content-Type"]).toBe("application/json");
  });
  it("lets the browser set multipart headers for FormData", async () => {
    const fetch = respond(200, {});
    vi.stubGlobal("fetch", fetch);
    await api("/upload", { method: "POST", body: new FormData() });
    expect(fetch.mock.calls[0][1].headers["Content-Type"]).toBeUndefined();
  });
  it("surfaces the server's error detail", async () => {
    vi.stubGlobal("fetch", respond(409, { detail: "A task is still running." }));
    await expect(api("/upload")).rejects.toThrow("A task is still running.");
  });
  it("hides structured validation errors behind a readable message", async () => {
    vi.stubGlobal("fetch", respond(422, { detail: [{ loc: ["body"] }] }));
    await expect(api("/settings")).rejects.toThrow("Check your settings and try again.");
  });
});

describe("storePreferences", () => {
  it("never stores credentials in the browser", () => {
    storePreferences({ chat_model: "llama3", api_key: "secret", r2r_key: "secret2" });
    expect(JSON.parse(localStorage.getItem(storageKey))).toEqual({ chat_model: "llama3" });
  });
});
