import React, { useRef, useState } from "react";
import { ArrowUpRight, Plus, FileText, Globe2, Github, LoaderCircle, Paperclip, AlertCircle } from "lucide-react";
import { Modal } from "./ui.jsx";

export function ImportModal({ close, disabled, hasSources, formats, submit, sample }) {
  const [tab, setTab] = useState("files"),
    [files, setFiles] = useState([]),
    [value, setValue] = useState(""),
    [error, setError] = useState(""),
    [drag, setDrag] = useState(false);
  const picker = useRef();
  function choose(items) {
    const list = Array.from(items);
    setError("");
    if (
      list.length > 10 ||
      list.some((f) => f.size > 25 * 1024 * 1024) ||
      list.reduce((n, f) => n + f.size, 0) > 100 * 1024 * 1024
    ) {
      setError("Choose up to 10 files, 25 MB each and 100 MB total.");
      return;
    }
    setFiles(list);
  }
  return (
    <Modal
      title="Bring your knowledge in."
      subtitle="A document, a link, an idea worth understanding."
      close={close}
    >
      <div className="import-tabs">
        {[
          { id: "files", label: "Upload files", Icon: FileText },
          { id: "website", label: "Website", Icon: Globe2 },
          { id: "github", label: "GitHub", Icon: Github },
        ].map(({ id, label, Icon }) => (
          <button
            key={id}
            className={tab === id ? "active" : ""}
            onClick={() => {
              setTab(id);
              setValue("");
            }}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>
      {hasSources && (
        <div className="inline-note">
          <AlertCircle size={15} />
          New sources are added to your library. Existing documents stay
          available.
        </div>
      )}
      {tab === "files" ? (
        <>
          <input
            type="file"
            hidden
            multiple
            accept={formats.join(",")}
            ref={picker}
            onChange={(e) => choose(e.target.files)}
          />
          <button
            className={"dropzone " + (drag ? "drag" : "")}
            onClick={() => picker.current.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              choose(e.dataTransfer.files);
            }}
          >
            <span>
              <Paperclip size={24} />
            </span>
            <strong>
              {files.length
                ? `${files.length} file${files.length === 1 ? "" : "s"} selected`
                : "Drop your documents here"}
            </strong>
            <p>
              or <u>browse files</u> from your computer
            </p>
            <small>25 formats · 25 MB per file · 10 files at a time</small>
          </button>
          <div className="selected-files">
            {files.map((f) => (
              <div key={f.name}>
                <FileText size={15} />
                <span>{f.name}</span>
                <small>{(f.size / 1024).toFixed(0)} KB</small>
              </div>
            ))}
          </div>
        </>
      ) : (
        <label className="field import-field">
          {tab === "website"
            ? "Public HTTPS links (one per line)"
            : "Public repository"}
          <textarea
            rows={3}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={
              tab === "website"
                ? "https://example.com/article"
                : "owner/repository"
            }
          />
          <small>
            {tab === "website"
              ? "Up to 5 pages. Private and local network addresses are blocked."
              : "Use owner/repository or a GitHub repository URL."}
          </small>
        </label>
      )}
      {error && <p className="field-error">{error}</p>}
      <div className="modal-footer">
        <button className="text-button" disabled={disabled} onClick={sample}>
          Try a sample instead
          <ArrowUpRight size={14} />
        </button>
        <button
          className="primary"
          disabled={
            disabled || (tab === "files" ? !files.length : !value.trim())
          }
          onClick={() => submit(tab, tab === "files" ? files : value)}
        >
          {disabled ? (
            <LoaderCircle className="spin" size={16} />
          ) : (
            <Plus size={16} />
          )}
          Add to workspace
        </button>
      </div>
    </Modal>
  );
}
