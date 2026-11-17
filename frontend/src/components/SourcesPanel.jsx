import React from "react";
import { Plus, Library, FileText, Globe2, Github, X, Check, Sparkles, Trash2, AlertCircle } from "lucide-react";
import { IconButton, ResizeHandle } from "./ui.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Right-hand panel listing the workspace's sources. */
export function SourcesPanel() {
  const { disabled, panelWidths, setModal, setPanelWidths, setPreview, setShowSources, sources } = useWorkspace();
  return (
    <>
      <ResizeHandle
        side="right"
        value={panelWidths.right}
        change={(right) =>
          setPanelWidths((old) => ({ ...old, right }))
        }
      />
      <aside
        id="sources-panel"
        aria-label="Sources"
        className="source-panel"
      >
        <div className="source-panel-header">
          <div>
            <Library size={17} />
            <strong>Sources</strong>
            <span className="source-count">{sources.length}</span>
          </div>
          <div className="source-panel-actions">
            <IconButton
              title="Add source"
              disabled={disabled}
              onClick={() => setModal("import")}
            >
              <Plus size={17} />
            </IconButton>
            <IconButton
              title="Close source panel"
              onClick={() => setShowSources(false)}
            >
              <X size={17} />
            </IconButton>
          </div>
        </div>
        <p className="panel-description">
          The context behind your answers.
        </p>
        {sources.length ? (
          <div className="source-list">
            {sources.map((source) => (
              <button
                key={source.id}
                onClick={() => setPreview(source)}
              >
                <span className={"file-icon " + source.kind}>
                  {source.kind === "website" ? (
                    <Globe2 size={18} />
                  ) : source.kind === "github" ? (
                    <Github size={18} />
                  ) : (
                    <FileText size={18} />
                  )}
                </span>
                <div>
                  <strong>{source.name}</strong>
                  <small>
                    {source.kind === "sample"
                      ? "Sample document"
                      : source.kind === "r2r"
                        ? "Remote index"
                        : `${Math.ceil(source.characters / 1000)}k characters`}{" "}
                    ·{" "}
                    {source.status === "error"
                      ? "Needs attention"
                      : "Ready"}
                  </small>
                </div>
                {source.status === "error" ? (
                  <AlertCircle size={13} />
                ) : (
                  <Check size={13} />
                )}
              </button>
            ))}
          </div>
        ) : (
          <div className="source-empty">
            <div className="empty-stack">
              <FileText size={26} />
            </div>
            <h3>A home for your knowledge</h3>
            <p>
              Your sources will appear here.
              <br />
              Add something worth exploring.
            </p>
            <button
              className="secondary"
              disabled={disabled}
              onClick={() => setModal("import")}
            >
              <Plus size={15} />
              Add sources
            </button>
          </div>
        )}
        <div className="supported-note">
          <span>ROOM FOR EVERY KIND OF IDEA</span>
          <div>
            <b>PDF</b>
            <b>DOCX</b>
            <b>TXT</b>
            <b>+22</b>
          </div>
          <p>
            Documents, spreadsheets, emails
            <br />
            and more. Up to 25 MB per file.
          </p>
        </div>
        {sources.length > 0 && (
          <button
            className="text-button remove-sources"
            disabled={disabled}
            onClick={() => setModal("remove")}
          >
            <Trash2 size={14} />
            Remove all sources
          </button>
        )}
        <div className="source-tip">
          <Sparkles size={16} />
          <p>
            <strong>Stay curious.</strong> Try asking the same
            question across different sources.
          </p>
        </div>
      </aside>
    </>
  );
}
