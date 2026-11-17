import React from "react";
import { ArrowUp, ChevronDown, LoaderCircle, Paperclip, Cpu, Square } from "lucide-react";
import { IconButton } from "./ui.jsx";
import { api } from "../api.js";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Question input, model chip and send/stop controls. */
export function Composer() {
  const { disabled, hasReadySources, input, nav, question, send, setError, setModal, setQuestion, setStopping, settings, stopping, streaming } = useWorkspace();
  return (
    <div className="composer-wrap">
      <form
        className="composer"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          ref={input}
          aria-label="Ask DocMind"
          placeholder={
            hasReadySources
              ? "Ask anything about your sources…"
              : "What would you like to understand?"
          }
          value={question}
          maxLength={6000}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
        />
        <div className="composer-bottom">
          <div>
            <IconButton
              title="Add a source"
              disabled={disabled}
              onClick={() => setModal("import")}
            >
              <Paperclip size={18} />
            </IconButton>
            <span className="composer-divider" />
            <button
              type="button"
              className="model-button"
              onClick={() => nav("settings")}
            >
              <Cpu size={14} />
              {settings.r2r ? "R2R" : settings.chat_model}
              <ChevronDown size={12} />
            </button>
          </div>
          {streaming ? (
            <button
              type="button"
              className="stop-button"
              disabled={stopping}
              aria-label="Stop generating"
              onClick={async () => {
                setStopping(true);
                try {
                  await api("/chat/stop", { method: "POST" });
                } catch (e) {
                  setError(e.message);
                  setStopping(false);
                }
              }}
            >
              <Square size={14} fill="currentColor" />
              {stopping ? "Stopping…" : "Stop"}
            </button>
          ) : (
            <button
              className="send-button"
              type="submit"
              aria-label="Send message"
              disabled={!question.trim() || disabled}
            >
              {streaming ? (
                <LoaderCircle className="spin" size={19} />
              ) : (
                <ArrowUp size={20} />
              )}
            </button>
          )}
        </div>
      </form>
      <div className="composer-note">
        <span>
          <span className="tiny-dot" />
          {hasReadySources
            ? "Answers grounded in your sources"
            : "Add sources for document-grounded answers"}
        </span>
        <span>Always verify important details.</span>
      </div>
    </div>
  );
}
