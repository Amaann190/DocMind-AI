import React from "react";
import ReactMarkdown from "react-markdown";
import { ArrowUp, ArrowUpRight, ArrowRight, Plus, Library, FileText, Globe2, Github, X, Check, ChevronDown, Sparkles, Download, Trash2, PanelRightClose, PanelRightOpen, LoaderCircle, RefreshCw, Search, Paperclip, Cpu, AlertCircle, BookOpen, Copy, CheckCheck, Zap, Square } from "lucide-react";
import { Brand, IconButton, ResizeHandle } from "./ui.jsx";
import { api } from "../api.js";

export function ChatPage({
  bottom,
  copied,
  copy,
  disabled,
  hasReadySources,
  input,
  messages,
  nav,
  panelWidths,
  question,
  readySourceCount,
  sample,
  send,
  setError,
  setModal,
  setPanelWidths,
  setPreview,
  setQuestion,
  setShowSources,
  setStopping,
  settings,
  showSources,
  sources,
  stopping,
  streaming,
}) {
  return (
    <div className="chat-layout">
      <section className="chat-area">
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
        <div className="conversation-scroll">
          {!messages.length ? (
            <div className="welcome">
              <div className="welcome-symbol">
                <Sparkles size={25} />
              </div>
              <span className="welcome-kicker">
                LESS SEARCHING. MORE UNDERSTANDING.
              </span>
              <h1>
                A clearer view of
                <br />
                <em>everything you know.</em>
              </h1>
              <p>
                Bring your documents. Follow your curiosity.
                <br />
                Find the answers hiding between the lines.
              </p>
              <div className="start-card">
                <div className="paper-art" aria-hidden="true">
                  <div className="paper paper-back" />
                  <div className="paper paper-front">
                    <span />
                    <span />
                    <span />
                    <span />
                    <i>
                      <Check size={13} />
                    </i>
                  </div>
                  <span className="art-spark">✦</span>
                </div>
                <div>
                  <span className="eyebrow">START WITH A SOURCE</span>
                  <h3>
                    {hasReadySources
                      ? "Your knowledge is ready."
                      : "Good questions start here."}
                  </h3>
                  <p>
                    {hasReadySources
                      ? `${readySourceCount} source${readySourceCount === 1 ? "" : "s"} ready to explore. Ask your first question below.`
                      : "Add a document, a website, or a repository. We’ll help you make sense of it."}
                  </p>
                  <button
                    className="text-link"
                    onClick={() =>
                      hasReadySources
                        ? input.current?.focus()
                        : setModal("import")
                    }
                    disabled={disabled}
                  >
                    {hasReadySources
                      ? "Ask a question"
                      : "Add your first source"}
                    <ArrowRight size={16} />
                  </button>
                </div>
              </div>
              <div className="suggestion-heading">
                <span>A LITTLE INSPIRATION</span>
                {!hasReadySources && (
                  <button disabled={disabled} onClick={sample}>
                    Try a sample document
                    <ArrowUpRight size={13} />
                  </button>
                )}
              </div>
              <div className="suggestion-grid">
                {[
                  {
                    icon: BookOpen,
                    title: "Find the big picture",
                    text: "Summarize my documents",
                  },
                  {
                    icon: Search,
                    title: "Connect the details",
                    text: "What are the key dates and decisions?",
                  },
                  {
                    icon: Zap,
                    title: "Make it actionable",
                    text: "What are the next steps?",
                  },
                ].map((s) => (
                  <button
                    key={s.title}
                    disabled={disabled}
                    onClick={() => {
                      setQuestion(s.text);
                      input.current?.focus();
                    }}
                  >
                    <s.icon size={18} />
                    <strong>{s.title}</strong>
                    <span>{s.text}</span>
                    <ArrowUpRight size={14} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages">
              {messages.map((message, i) => (
                <article
                  key={i}
                  className={"message " + message.role}
                >
                  <div className="message-avatar">
                    {message.role === "user" ? "A" : <Brand small />}
                  </div>
                  <div className="message-body">
                    <div className="message-name">
                      {message.role === "user" ? "You" : "DocMind"}
                      {message.role === "assistant" && (
                        <span>DOCUMENT ASSISTANT</span>
                      )}
                    </div>
                    {message.stopped && (
                      <p className="response-status">
                        Stopped ·{" "}
                        {message.content
                          ? "Partial answer saved"
                          : "No answer generated"}
                      </p>
                    )}
                    {message.content ? (
                      <ReactMarkdown
                        components={{
                          img: ({ alt }) => (
                            <span>
                              [Image: {alt || "not loaded"}]
                            </span>
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : !message.stopped ? (
                      <div className="thinking">
                        <span />
                        <span />
                        <span />
                      </div>
                    ) : null}
                    {message.sources?.length > 0 && (
                      <div className="citation-list">
                        {message.sources.map((source) => (
                          <button
                            key={source.number}
                            onClick={() => setPreview(source)}
                          >
                            <span>{source.number}</span>
                            <FileText size={12} />
                            {source.name}
                            {source.page != null && (
                              <small>p. {source.page}</small>
                            )}
                            <ArrowUpRight size={12} />
                          </button>
                        ))}
                      </div>
                    )}
                    {message.no_evidence && !disabled && (
                      <button
                        className="text-link"
                        onClick={() =>
                          send(messages[i - 1]?.content || "", true)
                        }
                      >
                        Ask without documents
                        <ArrowRight size={14} />
                      </button>
                    )}
                    {message.content &&
                      message.role === "assistant" && (
                        <IconButton
                          title="Copy answer"
                          onClick={() => copy(message.content, i)}
                        >
                          {copied === i ? (
                            <CheckCheck size={14} />
                          ) : (
                            <Copy size={14} />
                          )}
                        </IconButton>
                      )}
                    {message.role === "assistant" &&
                      i === messages.length - 1 &&
                      !streaming && (
                        <button
                          className="text-button regenerate"
                          disabled={disabled}
                          onClick={() =>
                            send(
                              messages[i - 1]?.content || "",
                              false,
                              true,
                            )
                          }
                        >
                          <RefreshCw size={14} />
                          Regenerate answer
                        </button>
                      )}
                  </div>
                </article>
              ))}
              <div ref={bottom} />
            </div>
          )}
        </div>
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
      </section>
      {showSources && (
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
      )}
    </div>
  );
}
