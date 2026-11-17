import React from "react";
import { ArrowUpRight, Plus, FileText, Search, FolderOpen } from "lucide-react";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

export function LibraryPage() {
  const { disabled, search, setModal, setPreview, setSearch, sources } = useWorkspace();
  return (
    <section className="library-page">
      <span className="eyebrow">YOUR KNOWLEDGE, TOGETHER</span>
      <h1>
        Source library<span>.</span>
      </h1>
      <p>Everything your current conversation can draw from.</p>
      <div className="library-tools">
        <label>
          <Search size={17} />
          <input
            aria-label="Search sources"
            placeholder="Find a source…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <span>{sources.length} sources in this workspace</span>
      </div>
      {sources.length ? (
        <div className="library-grid">
          {sources
            .filter((s) =>
              s.name.toLowerCase().includes(search.toLowerCase()),
            )
            .map((source) => (
              <button
                className="library-card"
                key={source.id}
                onClick={() => setPreview(source)}
              >
                <div>
                  <span className="file-icon">
                    <FileText size={24} />
                  </span>
                  <ArrowUpRight size={17} />
                </div>
                <h3>{source.name}</h3>
                <p>{source.preview?.slice(0, 130)}</p>
                <footer>
                  <span>{source.kind}</span>
                  <span className="ready-dot">
                    {source.status === "error"
                      ? "Needs attention"
                      : "Ready"}
                  </span>
                </footer>
              </button>
            ))}
        </div>
      ) : (
        <div className="library-empty">
          <FolderOpen size={38} />
          <h2>Your next insight starts with a source.</h2>
          <p>
            Bring a document, website or public GitHub repository.
          </p>
          <button
            className="primary"
            disabled={disabled}
            onClick={() => setModal("import")}
          >
            <Plus size={17} />
            Add a source
          </button>
        </div>
      )}
    </section>
  );
}
