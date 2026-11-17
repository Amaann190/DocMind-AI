import React from "react";
import { Download, PanelRightClose, PanelRightOpen } from "lucide-react";
import { IconButton } from "./ui.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Toolbar above the conversation: export, clear and sources toggle. */
export function ChatToolbar() {
  const { disabled, messages, setShowSources, showSources } = useWorkspace();
  return (
    <div className="chat-toolbar">
      <span className="eyebrow">YOUR THINKING SPACE</span>
      <div>
        <button
          className="text-button"
          disabled={!messages.length || disabled}
          onClick={() => window.location.assign("/api/export")}
        >
          <Download size={15} />
          Export
        </button>
        <IconButton
          title={
            showSources
              ? "Hide source panel"
              : "Show source panel"
          }
          onClick={() => setShowSources(!showSources)}
          aria-expanded={showSources}
          aria-controls="sources-panel"
        >
          {showSources ? (
            <PanelRightClose size={18} />
          ) : (
            <PanelRightOpen size={18} />
          )}
        </IconButton>
      </div>
    </div>
  );
}
