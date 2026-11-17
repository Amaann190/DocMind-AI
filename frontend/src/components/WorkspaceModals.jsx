import React from "react";
import { RefreshCw, Replace, Trash2 } from "lucide-react";
import { Modal } from "./ui.jsx";
import { ImportModal } from "./ImportModal.jsx";
import { PassagePreview } from "./PassagePreview.jsx";
import { RenameConversation } from "./RenameConversation.jsx";
import { storePreferences } from "../api.js";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

const MAX_REPLACEMENT_BYTES = 25 * 1024 * 1024;

function AddSourceModal() {
  const { busy, disabled, sources, workspace, sample, setModal, action, setPage } = useWorkspace();
  async function submit(kind, value) {
    let path;
    let options;
    if (kind === "files") {
      const form = new FormData();
      value.forEach((f) => form.append("files", f));
      path = "/upload";
      options = { method: "POST", body: form };
    } else {
      path = "/import";
      options = { method: "POST", body: JSON.stringify({ kind, value }) };
    }
    setModal(null);
    await action(path, options, () => setPage("chat"));
  }
  return (
    <ImportModal
      close={() => !busy && setModal(null)}
      disabled={disabled}
      hasSources={sources.length > 0}
      formats={workspace?.formats || []}
      sample={sample}
      submit={submit}
    />
  );
}

function ConfirmClearModal() {
  const { modal, setModal, action, setPage } = useWorkspace();
  const reset = modal === "reset";
  function confirm() {
    setModal(null);
    action(reset ? "/session" : "/sources", { method: "DELETE" }, (result) => {
      if (reset) storePreferences(result.settings);
      setPage("chat");
    });
  }
  return (
    <Modal
      title={reset ? "Reset this workspace?" : "Remove all sources?"}
      subtitle={
        reset
          ? "This deletes all saved conversations, documents, credentials and settings for this browser."
          : "Future answers will no longer use these sources or the earlier document conversation. Remote R2R copies will be deleted."
      }
      close={() => setModal(null)}
    >
      <div className="modal-footer">
        <button className="secondary" onClick={() => setModal(null)}>
          Keep working
        </button>
        <button className="primary" onClick={confirm}>
          Confirm {reset ? "reset" : "removal"}
        </button>
      </div>
    </Modal>
  );
}

function SourcePreviewModal() {
  const { preview, setPreview, sources, error, disabled, action, replacement, setRemovingSource } = useWorkspace();
  async function retry() {
    const result = await action(`/sources/${preview.id}/retry`, { method: "POST" });
    if (result) setPreview(result.sources.find((s) => s.id === preview.id) || null);
  }
  return (
    <Modal
      title={preview.name}
      subtitle={
        preview.number
          ? `Source ${preview.number} · Retrieved supporting passage${preview.page != null ? ` · Page ${preview.page}` : ""}`
          : "Extracted text preview · first 16,000 characters"
      }
      close={() => setPreview(null)}
      wide
    >
      <PassagePreview source={preview} sources={sources} />
      {error && (
        <p role="alert" className="source-error">
          {error}
        </p>
      )}
      {!preview.number && (
        <>
          {preview.error && (
            <p role="alert" className="source-error">
              {preview.error}
            </p>
          )}
          <div className="modal-footer source-controls">
            <button className="secondary" disabled={disabled} onClick={retry}>
              <RefreshCw size={15} />
              {preview.status === "error" ? "Retry source" : "Reindex source"}
            </button>
            <button className="secondary" disabled={disabled} onClick={() => replacement.current.click()}>
              <Replace size={15} />
              Replace file
            </button>
            <button
              className="danger-button"
              disabled={disabled}
              onClick={() => {
                setRemovingSource(preview);
                setPreview(null);
              }}
            >
              <Trash2 size={15} />
              Remove source
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}

/** Hidden file input behind "Replace file" in the source preview. */
function ReplacementInput() {
  const { replacement, workspace, preview, setPreview, setError, action } = useWorkspace();
  async function replace(e) {
    const file = e.target.files[0];
    e.target.value = "";
    if (!file || !preview) return;
    if (file.size > MAX_REPLACEMENT_BYTES) {
      setError("Choose a replacement under 25 MB.");
      return;
    }
    const form = new FormData();
    form.append("files", file);
    const id = preview.id;
    const result = await action(`/sources/${id}`, { method: "PUT", body: form });
    if (result) setPreview(result.sources.find((s) => s.id === id) || null);
  }
  return (
    <input
      hidden
      ref={replacement}
      type="file"
      aria-label="Replacement file"
      accept={(workspace?.formats || []).map((f) => "." + f.replace(/^\./, "")).join(",")}
      onChange={replace}
    />
  );
}

function ConfirmDeleteModal() {
  const { deletingChat, setDeletingChat, removingSource, setRemovingSource, disabled, action } = useWorkspace();
  const close = () => {
    setDeletingChat(null);
    setRemovingSource(null);
  };
  return (
    <Modal
      title={deletingChat ? "Delete this conversation?" : "Remove this source?"}
      subtitle={
        deletingChat
          ? `“${deletingChat.title}” will be deleted from saved history.`
          : `“${removingSource.name}” will be removed. Other sources stay available.`
      }
      close={close}
    >
      <div className="modal-footer">
        <button className="secondary" onClick={close}>
          Cancel
        </button>
        <button
          className="danger-button"
          disabled={disabled}
          onClick={() =>
            action(
              deletingChat ? `/conversations/${deletingChat.id}` : `/sources/${removingSource.id}`,
              { method: "DELETE" },
              close,
            )
          }
        >
          Confirm {deletingChat ? "deletion" : "removal"}
        </button>
      </div>
    </Modal>
  );
}

/** Every dialog the workspace can open, driven by context state. */
export function WorkspaceModals() {
  const { modal, preview, editingChat, setEditingChat, deletingChat, removingSource, disabled, action } =
    useWorkspace();
  return (
    <>
      {modal === "import" && <AddSourceModal />}
      {["remove", "reset"].includes(modal) && <ConfirmClearModal />}
      {preview && <SourcePreviewModal />}
      <ReplacementInput />
      {editingChat && (
        <RenameConversation
          conversation={editingChat}
          disabled={disabled}
          close={() => setEditingChat(null)}
          save={(title) =>
            action(
              `/conversations/${editingChat.id}`,
              { method: "PUT", body: JSON.stringify({ title }) },
              () => setEditingChat(null),
            )
          }
        />
      )}
      {(deletingChat || removingSource) && <ConfirmDeleteModal />}
    </>
  );
}
