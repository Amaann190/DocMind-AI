import React from "react";
import { render } from "@testing-library/react";
import { vi } from "vitest";
import { WorkspaceContext } from "../state/WorkspaceContext.jsx";

/** Render a component with a fixed workspace context; unspecified actions are spies. */
export function renderWithWorkspace(ui, overrides = {}) {
  const value = {
    workspace: { sources: [], messages: [], warnings: [], formats: [".txt"], status: "Ready" },
    sources: [],
    messages: [],
    settings: { chat_model: "llama3:latest", r2r: false },
    disabled: false,
    busy: false,
    streaming: false,
    stopping: false,
    error: "",
    question: "",
    hasReadySources: false,
    online: null,
    theme: "light",
    page: "chat",
    navigationVisible: true,
    panelWidths: { left: 244, right: 274 },
    input: { current: null },
    bottom: { current: null },
    replacement: { current: null },
    send: vi.fn(),
    setQuestion: vi.fn(),
    setModal: vi.fn(),
    nav: vi.fn(),
    setError: vi.fn(),
    setStopping: vi.fn(),
    toggleTheme: vi.fn(),
    toggleNavigation: vi.fn(),
    action: vi.fn(),
    ...overrides,
  };
  return { value, ...render(<WorkspaceContext.Provider value={value}>{ui}</WorkspaceContext.Provider>) };
}
