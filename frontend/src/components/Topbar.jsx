import React from "react";
import { ChevronRight, Moon, PanelLeftClose, PanelLeftOpen, Plus, Sun } from "lucide-react";
import { IconButton } from "./ui.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

const PAGE_TITLES = { chat: "Chat", library: "Source library", settings: "Settings" };

/** Breadcrumb, theme toggle, model connection status and the Add source button. */
export function Topbar() {
  const { navigationVisible, toggleNavigation, page, theme, toggleTheme, online, workspace, disabled, setModal } =
    useWorkspace();
  return (
    <header className="topbar">
      <div className="breadcrumb">
        <IconButton
          title="Toggle navigation"
          onClick={toggleNavigation}
          aria-expanded={navigationVisible}
          aria-controls="navigation-panel"
        >
          {navigationVisible ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </IconButton>
        <span>Workspace</span>
        <ChevronRight size={14} />
        <strong>{PAGE_TITLES[page]}</strong>
      </div>
      <div className="top-actions">
        <IconButton
          title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          onClick={toggleTheme}
        >
          {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
        </IconButton>
        <span className={"connection " + (online ? "connected" : "")}>
          <span />
          {online === null ? "Checking connection" : online ? "Model connected" : "Model offline"}
        </span>
        <button
          className="primary small-button"
          onClick={() => setModal("import")}
          disabled={!workspace || disabled}
        >
          <Plus size={16} /> Add source
        </button>
      </div>
    </header>
  );
}
