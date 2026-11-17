import React from "react";
import { AlertCircle, LoaderCircle, X } from "lucide-react";
import { IconButton } from "./ui.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Dismissible error banner shown above every page. */
export function ErrorBanner() {
  const { error, setError } = useWorkspace();
  if (!error) return null;
  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={18} />
      <span>{error}</span>
      <IconButton title="Dismiss error" onClick={() => setError("")}>
        <X size={16} />
      </IconButton>
    </div>
  );
}

/** Progress for a running task and warnings about unreadable files. */
export function TaskBanners() {
  const { busy, workspace } = useWorkspace();
  return (
    <>
      {busy && (
        <div className="task-banner" role="status">
          <LoaderCircle size={17} className="spin" />
          <span>{workspace.status === "Ready" ? "Preparing your workspace…" : workspace.status}</span>
          {workspace.progress && (
            <span>
              {workspace.progress.done} / {workspace.progress.total} chunks
            </span>
          )}
        </div>
      )}
      {workspace.warnings.length > 0 && (
        <div className="warning-banner" role="status">
          <AlertCircle size={17} />
          <div>
            <strong>Some files couldn’t be read</strong>
            {workspace.warnings.map((w, i) => (
              <p key={i}>{typeof w === "string" ? w : `${w.file}: ${w.error}`}</p>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
