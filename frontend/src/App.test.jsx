import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { App } from "./App.jsx";

afterEach(() => vi.unstubAllGlobals());

const session = {
  settings: { chat_model: "llama3:latest", r2r: false },
  conversation_id: "c1",
  title: "New conversation",
  naming: false,
  conversations: [],
  sources: [],
  messages: [],
  warnings: [],
  busy: false,
  status: "Ready",
  progress: null,
  has_index: false,
  formats: [".txt"],
};

describe("App", () => {
  it("opens a session and shows the composer once the workspace loads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((url) =>
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve(url.endsWith("/models") ? { online: true } : session),
        }),
      ),
    );
    render(<App />);
    expect(await screen.findByRole("textbox", { name: "Ask DocMind" })).toBeInTheDocument();
    expect(await screen.findByText("Model connected")).toBeInTheDocument();
  });

  it("offers a retry when the server is unreachable", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("Failed to fetch"))));
    render(<App />);
    expect(await screen.findByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Failed to fetch");
  });
});
