import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Composer } from "./Composer.jsx";
import { ErrorBanner } from "./StatusBanners.jsx";
import { Topbar } from "./Topbar.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";
import { renderWithWorkspace } from "../test/renderWithWorkspace.jsx";

describe("useWorkspace", () => {
  it("fails clearly outside the provider", () => {
    function Orphan() {
      useWorkspace();
      return null;
    }
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<Orphan />)).toThrow("useWorkspace must be used inside <WorkspaceProvider>.");
  });
});

describe("Composer", () => {
  it("disables sending an empty question", () => {
    renderWithWorkspace(<Composer />);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });
  it("sends on Enter but not on Shift+Enter", () => {
    const { value } = renderWithWorkspace(<Composer />, { question: "What changed?" });
    const box = screen.getByRole("textbox", { name: "Ask DocMind" });
    fireEvent.keyDown(box, { key: "Enter", shiftKey: true });
    expect(value.send).not.toHaveBeenCalled();
    fireEvent.keyDown(box, { key: "Enter" });
    expect(value.send).toHaveBeenCalledTimes(1);
  });
  it("shows a stop button while streaming", () => {
    renderWithWorkspace(<Composer />, { streaming: true });
    expect(screen.getByRole("button", { name: "Stop generating" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Send message" })).toBeNull();
  });
  it("tells the user whether answers are grounded", () => {
    renderWithWorkspace(<Composer />, { hasReadySources: true });
    expect(screen.getByText("Answers grounded in your sources")).toBeInTheDocument();
  });
});

describe("Topbar", () => {
  it("reports model status and opens the import dialog", () => {
    const { value } = renderWithWorkspace(<Topbar />, { online: false });
    expect(screen.getByText("Model offline")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Add source/ }));
    expect(value.setModal).toHaveBeenCalledWith("import");
  });
});

describe("ErrorBanner", () => {
  it("renders nothing without an error", () => {
    const { container } = renderWithWorkspace(<ErrorBanner />);
    expect(container).toBeEmptyDOMElement();
  });
  it("shows the error and can be dismissed", () => {
    const { value } = renderWithWorkspace(<ErrorBanner />, { error: "Upload failed" });
    expect(screen.getByRole("alert")).toHaveTextContent("Upload failed");
    fireEvent.click(screen.getByRole("button", { name: "Dismiss error" }));
    expect(value.setError).toHaveBeenCalledWith("");
  });
});
