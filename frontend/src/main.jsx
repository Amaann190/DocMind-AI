import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import "@fontsource/dm-sans/latin-700.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/latin-800.css";
import {
  ArrowUp,
  ArrowUpRight,
  ArrowRight,
  Plus,
  MessageSquare,
  Library,
  Settings2,
  FileText,
  Globe2,
  Github,
  X,
  Check,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Download,
  Trash2,
  PanelRightClose,
  PanelRightOpen,
  PanelLeftClose,
  PanelLeftOpen,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Search,
  Paperclip,
  Cpu,
  AlertCircle,
  BookOpen,
  Copy,
  CheckCheck,
  FolderOpen,
  Zap,
  Pencil,
  Square,
  Replace,
} from "lucide-react";
import "./style.css";

const storageKey = "docmind-react-preferences";
async function api(path, options = {}) {
  const headers = { "X-DocMind-Client": "react", ...options.headers };
  if (options.body && !(options.body instanceof FormData))
    headers["Content-Type"] = "application/json";
  const response = await fetch("/api" + path, { ...options, headers });
  if (!response.ok) {
    let detail;
    try {
      detail = (await response.json()).detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(
      typeof detail === "string"
        ? detail
        : "Check your settings and try again.",
    );
  }
  return response.json();
}
function storePreferences(settings) {
  const { api_key, r2r_key, ...safe } = settings;
  try {
    localStorage.setItem(storageKey, JSON.stringify(safe));
  } catch {
    /* Session still works without browser storage. */
  }
}
function Brand({ small = false }) {
  return (
    <div className={"brand " + (small ? "small" : "")}>
      <span className="brand-mark">
        <span />
        <span />
        <span />
      </span>
      {!small && (
        <>
          docmind<span className="brand-dot">.</span>
        </>
      )}
    </div>
  );
}
function IconButton({ title, children, ...props }) {
  return (
    <button
      type="button"
      className="icon-button"
      aria-label={title}
      title={title}
      {...props}
    >
      {children}
    </button>
  );
}
function Modal({ title, subtitle, close, children, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const previous = document.activeElement;
    ref.current.showModal();
    return () => previous?.focus();
  }, []);
  return (
    <dialog
      ref={ref}
      className={"modal " + (wide ? "wide" : "")}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => {
        if (event.target === ref.current) close();
      }}
    >
      <div className="modal-header">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <IconButton title="Close dialog" onClick={close}>
          <X size={20} />
        </IconButton>
      </div>
      {children}
    </dialog>
  );
}

function ResizeHandle({ side, value, change }) {
  const start = useRef(null);
  const min = side === "left" ? 220 : 240;
  const max = side === "left" ? 400 : 440;
  function resize(next) {
    change(
      Math.max(
        min,
        Math.min(
          max,
          window.innerWidth * (side === "left" ? 0.32 : 0.36),
          next,
        ),
      ),
    );
  }
  return (
    <div
      className={`resize-handle ${side}`}
      role="separator"
      tabIndex={0}
      aria-label={`Resize ${side === "left" ? "navigation" : "sources"} panel`}
      aria-orientation="vertical"
      aria-valuemin={min}
      aria-valuemax={max}
      aria-valuenow={Math.round(value)}
      onPointerDown={(e) => {
        start.current = { x: e.clientX, value };
        e.currentTarget.setPointerCapture(e.pointerId);
      }}
      onPointerMove={(e) => {
        if (start.current)
          resize(
            start.current.value +
              (e.clientX - start.current.x) * (side === "left" ? 1 : -1),
          );
      }}
      onPointerUp={() => {
        start.current = null;
      }}
      onLostPointerCapture={() => {
        start.current = null;
      }}
      onKeyDown={(e) => {
        if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
          e.preventDefault();
          resize(
            e.key === "Home"
              ? min
              : e.key === "End"
                ? max
                : value +
                  (e.key === "ArrowRight" ? 10 : -10) *
                    (side === "left" ? 1 : -1),
          );
        }
      }}
    />
  );
}

function RenameConversation({ conversation, close, save, disabled }) {
  const [title, setTitle] = useState(conversation.title);
  return (
    <Modal title="Rename conversation" close={close}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save(title.trim());
        }}
      >
        <label className="rename-label">
          Conversation name
          <input
            autoFocus
            value={title}
            maxLength={100}
            required
            onChange={(e) => setTitle(e.target.value)}
          />
        </label>
        <div className="modal-footer">
          <button className="primary" disabled={disabled || !title.trim()}>
            Save name
          </button>
        </div>
      </form>
    </Modal>
  );
}

function PassagePreview({ source, sources }) {
  const document = sources.find((s) => s.id === source.source_id);
  const text = document?.preview || "";
  const position = source.text ? text.indexOf(source.text) : -1;
  return (
    <>
      {source.number && (
        <p className="citation-explanation">
          Highlighted text was retrieved for this answer.
          {source.page != null
            ? ` Page ${source.page}.`
            : " Page information is not available for this passage."}
        </p>
      )}
      <div className="source-preview">
        {source.number ? (
          position >= 0 ? (
            <>
              {text.slice(Math.max(0, position - 350), position)}
              <mark>{source.text}</mark>
              {text.slice(
                position + source.text.length,
                position + source.text.length + 350,
              )}
            </>
          ) : (
            <mark>{source.text}</mark>
          )
        ) : (
          source.preview || source.error || "No text preview available."
        )}
      </div>
    </>
  );
}

function App() {
  const [workspace, setWorkspace] = useState(null),
    [page, setPage] = useState("chat");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [streaming, setStreaming] = useState(false);
  const [modal, setModal] = useState(null),
    [preview, setPreview] = useState(null),
    [showSources, setShowSources] = useState(() => window.innerWidth > 980);
  const [showNavigation, setShowNavigation] = useState(true);
  const [chatSearch, setChatSearch] = useState("");
  const [chatResults, setChatResults] = useState(null);
  const [editingChat, setEditingChat] = useState(null);
  const [deletingChat, setDeletingChat] = useState(null);
  const [removingSource, setRemovingSource] = useState(null);
  const [stopping, setStopping] = useState(false);
  const [panelWidths, setPanelWidths] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("docmind-panel-widths"));
      return {
        left: Math.max(220, Math.min(400, Number(saved?.left) || 244)),
        right: Math.max(240, Math.min(440, Number(saved?.right) || 274)),
      };
    } catch {
      return { left: 244, right: 274 };
    }
  });
  const replacement = useRef();
  const [mobile, setMobile] = useState(() => window.innerWidth <= 700);
  const [online, setOnline] = useState(null),
    [question, setQuestion] = useState(""),
    [mobileNav, setMobileNav] = useState(false);
  const [search, setSearch] = useState(""),
    [copied, setCopied] = useState(-1),
    [boot, setBoot] = useState(0);
  const bottom = useRef(),
    input = useRef(),
    alive = useRef(true);
  useEffect(() => {
    try {
      localStorage.setItem("docmind-panel-widths", JSON.stringify(panelWidths));
    } catch {}
  }, [panelWidths]);
  useEffect(() => {
    if (!chatSearch.trim()) {
      setChatResults(null);
      return;
    }
    let active = true;
    const timer = setTimeout(
      () =>
        api("/conversations?q=" + encodeURIComponent(chatSearch))
          .then((rows) => {
            if (active) setChatResults(rows);
          })
          .catch((e) => {
            if (active) setError(e.message);
          }),
      200,
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [chatSearch, workspace?.conversations]);
  useEffect(() => {
    const navigation = window.matchMedia("(max-width: 700px)");
    const sources = window.matchMedia("(max-width: 980px)");
    const updateNavigation = () => {
      setMobile(navigation.matches);
      setMobileNav(false);
    };
    const updateSources = () => setShowSources(!sources.matches);
    navigation.addEventListener("change", updateNavigation);
    sources.addEventListener("change", updateSources);
    return () => {
      navigation.removeEventListener("change", updateNavigation);
      sources.removeEventListener("change", updateSources);
    };
  }, []);
  useEffect(() => {
    alive.current = true;
    (async () => {
      try {
        let current = await api("/session", { method: "POST" });
        let saved;
        try {
          saved = JSON.parse(localStorage.getItem(storageKey) || "null");
        } catch {
          saved = null;
        }
        // Do not overwrite a live workspace's configuration on refresh.
        if (saved && !current.sources.length && !current.messages.length) {
          try {
            current = await api("/settings", {
              method: "PUT",
              body: JSON.stringify(saved),
            });
          } catch {
            setError(
              "Saved preferences could not be restored. Default settings are available.",
            );
          }
        }
        if (!alive.current) return;
        setWorkspace(current);
        try {
          const models = await api("/models");
          if (alive.current) setOnline(models.online);
        } catch {
          if (alive.current) setOnline(false);
        }
      } catch (e) {
        if (alive.current) setError(e.message);
      }
    })();
    return () => {
      alive.current = false;
    };
  }, [boot]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [workspace?.messages?.length, streaming]);
  useEffect(() => {
    if (!busy && !workspace?.busy) return;
    const timer = setInterval(
      () =>
        api("/state")
          .then((s) =>
            setWorkspace((old) =>
              busy ? { ...old, status: s.status, progress: s.progress } : s,
            ),
          )
          .catch(() => {}),
      1000,
    );
    return () => clearInterval(timer);
  }, [busy, workspace?.busy]);
  async function action(path, options, success) {
    setBusy(true);
    setError("");
    try {
      const result = await api(path, options);
      setWorkspace(result);
      success?.(result);
      return result;
    } catch (e) {
      setError(e.message);
      try {
        setWorkspace(await api("/state"));
      } catch {}
    } finally {
      setBusy(false);
    }
  }
  async function send(text = question, without = false, regenerate = false) {
    text = text.trim();
    if (!text || busy || streaming || workspace?.busy) return;
    setQuestion("");
    setError("");
    setStreaming(true);
    setStopping(false);
    setPage("chat");
    setWorkspace((old) => ({
      ...old,
      messages: [
        ...(regenerate ? old.messages.slice(0, -2) : old.messages),
        { role: "user", content: text },
        { role: "assistant", content: "", sources: [] },
      ],
    }));
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-DocMind-Client": "react",
        },
        body: JSON.stringify({ text, without_documents: without, regenerate }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "The request failed.");
      }
      const reader = response.body.getReader(),
        decoder = new TextDecoder();
      let pending = "";
      const consume = (line) => {
        if (!line.trim()) return;
        const event = JSON.parse(line);
        if (event.type === "warning") {
          setError(event.text);
          return;
        }
        setWorkspace((old) => {
          const messages = [...old.messages];
          const last = messages.length - 1;
          if (event.type === "token")
            messages[last] = {
              ...messages[last],
              content: messages[last].content + event.text,
            };
          else if (event.message) messages[last] = event.message;
          return { ...old, messages };
        });
      };
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        pending += decoder.decode(value, { stream: true });
        const lines = pending.split("\n");
        pending = lines.pop();
        lines.forEach(consume);
      }
      pending += decoder.decode();
      if (pending.trim()) consume(pending);
    } catch (e) {
      setError(e.message);
    } finally {
      setStreaming(false);
      setStopping(false);
      try {
        setWorkspace(await api("/state"));
      } catch {}
      input.current?.focus();
    }
  }
  async function sample() {
    setModal(null);
    await action(
      "/import",
      { method: "POST", body: JSON.stringify({ kind: "sample" }) },
      () => setPage("chat"),
    );
  }
  const disabled = busy || streaming || workspace?.busy;
  const sources = workspace?.sources || [],
    messages = workspace?.messages || [];
  const settings = workspace?.settings;
  const conversations = chatResults ?? workspace?.conversations ?? [];
  const navigationVisible = mobile ? mobileNav : showNavigation;
  const toggleNavigation = () =>
    mobile ? setMobileNav(!mobileNav) : setShowNavigation(!showNavigation);
  const nav = (id) => {
    setPage(id);
    setMobileNav(false);
  };
  async function copy(text, i) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(-1), 1800);
    } catch {
      setError("Copy unavailable. Select the answer text to copy it.");
    }
  }

  return (
    <div
      className={"app-shell " + (!navigationVisible ? "navigation-hidden" : "")}
      style={{
        "--navigation-width": `${panelWidths.left}px`,
        "--sources-width": `${panelWidths.right}px`,
      }}
    >
      <aside
        id="navigation-panel"
        aria-label="Workspace navigation"
        className={
          "sidebar " + (navigationVisible ? "mobile-open" : "panel-hidden")
        }
      >
        <div className="sidebar-header">
          <Brand />
          <IconButton
            title="Hide navigation"
            onClick={toggleNavigation}
            aria-controls="navigation-panel"
            aria-expanded={navigationVisible}
          >
            <PanelLeftClose size={18} />
          </IconButton>
        </div>
        <div className="sidebar-scroll">
          <div className="workspace-switch">
            <span className="workspace-avatar">A</span>
            <div>
              Personal workspace<small>Your private thinking space</small>
            </div>
            <ChevronDown size={14} />
          </div>
          <button
            className="new-chat"
            disabled={disabled}
            onClick={() =>
              action("/conversations", { method: "POST" }, () => {
                setChatSearch("");
                nav("chat");
              })
            }
          >
            <Plus size={18} />
            New conversation<span>↗</span>
          </button>
          <div className="nav-label">WORKSPACE</div>
          <nav aria-label="Main navigation">
            <button
              className={page === "chat" ? "active" : ""}
              onClick={() => nav("chat")}
            >
              <MessageSquare size={18} />
              Chat
              <span className="nav-indicator" />
            </button>
            <button
              className={page === "library" ? "active" : ""}
              onClick={() => nav("library")}
            >
              <Library size={18} />
              Source library<span className="count">{sources.length}</span>
            </button>
            <button
              className={page === "settings" ? "active" : ""}
              onClick={() => nav("settings")}
            >
              <Settings2 size={18} />
              Settings
            </button>
          </nav>
          <div className="nav-label recent-label">SAVED CONVERSATIONS</div>
          <label className="chat-search">
            <Search size={14} />
            <input
              aria-label="Search conversations"
              placeholder="Search chats…"
              value={chatSearch}
              onChange={(e) => setChatSearch(e.target.value)}
            />
          </label>
          <div className="conversation-list">
            {conversations.map((chat) => (
              <div
                key={chat.id}
                className={
                  "conversation-row " +
                  (chat.id === workspace?.conversation_id ? "selected" : "")
                }
              >
                <button
                  className="recent-chat"
                  disabled={disabled}
                  aria-current={
                    chat.id === workspace?.conversation_id ? "page" : undefined
                  }
                  onClick={() =>
                    action(
                      `/conversations/${chat.id}/open`,
                      { method: "POST" },
                      () => {
                        setQuestion("");
                        nav("chat");
                      },
                    )
                  }
                  title={chat.title}
                >
                  <MessageSquare size={13} />
                  <span>{chat.title}</span>
                </button>
                <IconButton
                  title={`Rename ${chat.title}`}
                  disabled={disabled}
                  onClick={() => setEditingChat(chat)}
                >
                  <Pencil size={13} />
                </IconButton>
                <IconButton
                  title={`Delete ${chat.title}`}
                  disabled={disabled}
                  onClick={() => setDeletingChat(chat)}
                >
                  <Trash2 size={13} />
                </IconButton>
              </div>
            ))}
            {chatSearch && !conversations.length && (
              <p className="history-note">No matching conversations.</p>
            )}
          </div>
          <p className="history-note">
            Chats save on this device. Conversations share the current source
            library.
          </p>
          <div className="sidebar-bottom">
            <div className="local-card">
              <span className="local-card-icon">
                <ShieldCheck size={19} />
              </span>
              <strong>Your ideas. Your space.</strong>
              <p>
                {settings?.provider === "Ollama" && !settings?.r2r
                  ? "Documents stay with your configured Ollama server."
                  : "Connected to your chosen model provider."}
              </p>
              <span className="local-caption">BUILT FOR CURIOUS MINDS</span>
            </div>
          </div>
        </div>
        <button className="profile" onClick={() => nav("settings")}>
          <span className="profile-avatar">A</span>
          <div>
            My workspace<small>On this device · saved chats</small>
          </div>
          <Settings2 size={16} />
        </button>
        <ResizeHandle
          side="left"
          value={panelWidths.left}
          change={(left) => setPanelWidths((old) => ({ ...old, left }))}
        />
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <IconButton
              title="Toggle navigation"
              onClick={toggleNavigation}
              aria-expanded={navigationVisible}
              aria-controls="navigation-panel"
            >
              {navigationVisible ? (
                <PanelLeftClose size={18} />
              ) : (
                <PanelLeftOpen size={18} />
              )}
            </IconButton>
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>
              {
                {
                  chat: "Chat",
                  library: "Source library",
                  settings: "Settings",
                }[page]
              }
            </strong>
          </div>
          <div className="top-actions">
            <span className={"connection " + (online ? "connected" : "")}>
              <span />
              {online === null
                ? "Checking connection"
                : online
                  ? "Model connected"
                  : "Model offline"}
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
        {error && (
          <div className="error-banner" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
            <IconButton title="Dismiss error" onClick={() => setError("")}>
              <X size={16} />
            </IconButton>
          </div>
        )}
        {!workspace ? (
          <div className="loading-page">
            <Brand small />
            <h2>Opening your thinking space</h2>
            {error ? (
              <button
                className="primary"
                onClick={() => {
                  setError("");
                  setBoot(boot + 1);
                }}
              >
                Try again
              </button>
            ) : (
              <LoaderCircle className="spin" />
            )}
          </div>
        ) : (
          <>
            {busy && (
              <div className="task-banner" role="status">
                <LoaderCircle size={17} className="spin" />
                <span>
                  {workspace.status === "Ready"
                    ? "Preparing your workspace…"
                    : workspace.status}
                </span>
                {workspace.progress && (
                  <span>
                    {workspace.progress.done} / {workspace.progress.total}{" "}
                    chunks
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
                    <p key={i}>
                      {w.file}: {w.error}
                    </p>
                  ))}
                </div>
              </div>
            )}
            {page === "chat" && (
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
                              {sources.length
                                ? "Your knowledge is ready."
                                : "Good questions start here."}
                            </h3>
                            <p>
                              {sources.length
                                ? `${sources.length} source${sources.length === 1 ? "" : "s"} ready to explore. Ask your first question below.`
                                : "Add a document, a website, or a repository. We’ll help you make sense of it."}
                            </p>
                            <button
                              className="text-link"
                              onClick={() =>
                                sources.length
                                  ? input.current?.focus()
                                  : setModal("import")
                              }
                              disabled={disabled}
                            >
                              {sources.length
                                ? "Ask a question"
                                : "Add your first source"}
                              <ArrowRight size={16} />
                            </button>
                          </div>
                        </div>
                        <div className="suggestion-heading">
                          <span>A LITTLE INSPIRATION</span>
                          {!sources.length && (
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
                          sources.length
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
                        {sources.length
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
            )}
            {page === "library" && (
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
            )}
            {page === "settings" && (
              <SettingsPage
                settings={settings}
                disabled={disabled}
                save={async (draft) => {
                  const result = await action("/settings", {
                    method: "PUT",
                    body: JSON.stringify(draft),
                  });
                  if (result) {
                    storePreferences(result.settings);
                    setOnline(null);
                    try {
                      setOnline((await api("/models")).online);
                    } catch {
                      setOnline(false);
                    }
                  }
                  return result;
                }}
                reset={() => setModal("reset")}
              />
            )}
          </>
        )}
      </main>
      {modal === "import" && (
        <ImportModal
          close={() => !busy && setModal(null)}
          disabled={disabled}
          hasSources={sources.length > 0}
          formats={workspace?.formats || []}
          sample={sample}
          submit={async (kind, value) => {
            let options, path;
            if (kind === "files") {
              const form = new FormData();
              value.forEach((f) => form.append("files", f));
              path = "/upload";
              options = { method: "POST", body: form };
            } else {
              path = "/import";
              options = {
                method: "POST",
                body: JSON.stringify({ kind, value }),
              };
            }
            setModal(null);
            await action(path, options, () => setPage("chat"));
          }}
        />
      )}
      {["remove", "reset"].includes(modal) && (
        <Modal
          title={
            modal === "reset" ? "Reset this workspace?" : "Remove all sources?"
          }
          subtitle={
            modal === "reset"
              ? "This deletes all saved conversations, documents, credentials and settings for this browser."
              : "Future answers will no longer use these sources or the earlier document conversation. Remote R2R copies will be deleted."
          }
          close={() => setModal(null)}
        >
          <div className="modal-footer">
            <button className="secondary" onClick={() => setModal(null)}>
              Keep working
            </button>
            <button
              className="primary"
              onClick={() => {
                const type = modal;
                setModal(null);
                action(
                  type === "reset" ? "/session" : "/sources",
                  { method: "DELETE" },
                  (result) => {
                    if (type === "reset") storePreferences(result.settings);
                    setPage("chat");
                  },
                );
              }}
            >
              Confirm {modal === "reset" ? "reset" : "removal"}
            </button>
          </div>
        </Modal>
      )}
      {preview && (
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
                <button
                  className="secondary"
                  disabled={disabled}
                  onClick={async () => {
                    const result = await action(
                      `/sources/${preview.id}/retry`,
                      { method: "POST" },
                    );
                    if (result)
                      setPreview(
                        result.sources.find((s) => s.id === preview.id) || null,
                      );
                  }}
                >
                  <RefreshCw size={15} />
                  {preview.status === "error"
                    ? "Retry source"
                    : "Reindex source"}
                </button>
                <button
                  className="secondary"
                  disabled={disabled}
                  onClick={() => replacement.current.click()}
                >
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
      )}
      <input
        hidden
        ref={replacement}
        type="file"
        aria-label="Replacement file"
        accept={(workspace?.formats || [])
          .map((f) => "." + f.replace(/^\./, ""))
          .join(",")}
        onChange={async (e) => {
          const file = e.target.files[0];
          e.target.value = "";
          if (!file || !preview) return;
          if (file.size > 25 * 1024 * 1024) {
            setError("Choose a replacement under 25 MB.");
            return;
          }
          const form = new FormData();
          form.append("files", file);
          const id = preview.id;
          const result = await action(`/sources/${id}`, {
            method: "PUT",
            body: form,
          });
          if (result)
            setPreview(result.sources.find((s) => s.id === id) || null);
        }}
      />
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
      {(deletingChat || removingSource) && (
        <Modal
          title={
            deletingChat ? "Delete this conversation?" : "Remove this source?"
          }
          subtitle={
            deletingChat
              ? `“${deletingChat.title}” will be deleted from saved history.`
              : `“${removingSource.name}” will be removed. Other sources stay available.`
          }
          close={() => {
            setDeletingChat(null);
            setRemovingSource(null);
          }}
        >
          <div className="modal-footer">
            <button
              className="secondary"
              onClick={() => {
                setDeletingChat(null);
                setRemovingSource(null);
              }}
            >
              Cancel
            </button>
            <button
              className="danger-button"
              disabled={disabled}
              onClick={() =>
                action(
                  deletingChat
                    ? `/conversations/${deletingChat.id}`
                    : `/sources/${removingSource.id}`,
                  { method: "DELETE" },
                  () => {
                    setDeletingChat(null);
                    setRemovingSource(null);
                  },
                )
              }
            >
              Confirm {deletingChat ? "deletion" : "removal"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function ImportModal({ close, disabled, hasSources, formats, submit, sample }) {
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

function SettingsPage({ settings, disabled, save, reset }) {
  const [draft, setDraft] = useState({ ...settings, api_key: "", r2r_key: "" }),
    [models, setModels] = useState(null),
    [notice, setNotice] = useState(""),
    [refreshing, setRefreshing] = useState(false);
  useEffect(() => {
    setDraft({ ...settings, api_key: "", r2r_key: "" });
  }, [settings]);
  const update = (key, value) => setDraft((old) => ({ ...old, [key]: value }));
  const presets = {
    Ollama: [
      "http://localhost:11434",
      "llama3:latest",
      "nomic-embed-text:latest",
    ],
    OpenAI: [
      "https://api.openai.com/v1",
      "gpt-4o-mini",
      "text-embedding-3-small",
    ],
    "LM Studio (Local AI)": [
      "http://localhost:1234/v1",
      "local-model",
      "local-embedding-model",
    ],
    TabbyAPI: [
      "http://localhost:5000/v1",
      "local-model",
      "local-embedding-model",
    ],
  };
  return (
    <section className="settings-page">
      <span className="eyebrow">MAKE ROOM FOR YOUR WAY OF THINKING</span>
      <h1>
        A workspace that fits<span>.</span>
      </h1>
      <p>Your models, your preferences, your pace.</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setNotice("");
          if (await save(draft)) setNotice("Preferences saved.");
        }}
      >
        <div className="settings-section">
          <div className="section-heading">
            <span className="section-icon">
              <Cpu size={19} />
            </span>
            <div>
              <h2>Model connection</h2>
              <p>Choose the intelligence behind your workspace.</p>
            </div>
          </div>
          <div className="form-grid">
            <label className="field">
              Provider
              <select
                value={draft.provider}
                onChange={(e) => {
                  const [endpoint, chat_model, embedding_model] =
                    presets[e.target.value];
                  setDraft({
                    ...draft,
                    provider: e.target.value,
                    endpoint,
                    chat_model,
                    embedding_model,
                    api_key: "",
                  });
                }}
              >
                {Object.keys(presets).map((p) => (
                  <option key={p}>{p}</option>
                ))}
              </select>
            </label>
            <label className="field">
              Server address
              <input
                value={draft.endpoint}
                onChange={(e) => update("endpoint", e.target.value)}
                required
              />
            </label>
            <label className="field">
              Chat model
              <input
                list="chat-models"
                value={draft.chat_model}
                onChange={(e) => update("chat_model", e.target.value)}
                required
              />
              <datalist id="chat-models">
                {models?.chat.map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </datalist>
            </label>
            <label className="field">
              Embedding model
              <input
                list="embedding-models"
                value={draft.embedding_model}
                onChange={(e) => update("embedding_model", e.target.value)}
                required
              />
              <datalist id="embedding-models">
                {models?.embeddings.map((m) => (
                  <option key={m}>{m}</option>
                ))}
              </datalist>
            </label>
            {draft.provider !== "Ollama" && (
              <label className="field full">
                API key
                <input
                  type="password"
                  autoComplete="off"
                  value={draft.api_key}
                  placeholder="Optional for local servers · stored in server memory only"
                  onChange={(e) => update("api_key", e.target.value)}
                />
              </label>
            )}
          </div>
          <div className="settings-inline">
            <button
              type="button"
              className="secondary"
              disabled={disabled || refreshing}
              onClick={async () => {
                setRefreshing(true);
                try {
                  const result = await api("/models");
                  setModels(result);
                  setNotice(
                    result.online
                      ? "Models loaded from the saved connection."
                      : "No models found. Check the saved connection.",
                  );
                } catch (e) {
                  setNotice(e.message);
                } finally {
                  setRefreshing(false);
                }
              }}
            >
              <RefreshCw size={14} className={refreshing ? "spin" : ""} />
              Refresh model list
            </button>
            <span>Uses your saved connection.</span>
          </div>
          {notice && (
            <p className="settings-notice" role="status">
              {notice}
            </p>
          )}
        </div>
        <div className="settings-section">
          <div className="section-heading">
            <span className="section-icon">
              <Sparkles size={19} />
            </span>
            <div>
              <h2>The way you get answers</h2>
              <p>A little more detail, or straight to the point.</p>
            </div>
          </div>
          <div className="style-options">
            {[
              "Balanced",
              "Concise",
              "Detailed",
              "Bulleted",
              "Technical",
              "Simple",
            ].map((style) => (
              <button
                type="button"
                className={draft.style === style ? "chosen" : ""}
                key={style}
                onClick={() => update("style", style)}
              >
                {style}
                {draft.style === style && <Check size={14} />}
              </button>
            ))}
          </div>
          <label className="toggle-row">
            <div>
              <strong>Eco mode</strong>
              <p>
                Smaller batches and shorter answers for lighter resource use.
              </p>
            </div>
            <input
              type="checkbox"
              checked={draft.eco}
              onChange={(e) => update("eco", e.target.checked)}
            />
          </label>
          <details>
            <summary>
              Retrieval & advanced controls
              <ChevronDown size={15} />
            </summary>
            <div className="form-grid advanced-grid">
              {[
                {
                  key: "temperature",
                  label: "Creativity",
                  min: 0,
                  max: 1.5,
                  step: 0.05,
                },
                {
                  key: "top_k",
                  label: "Sources per answer",
                  min: 1,
                  max: 10,
                  step: 1,
                },
                {
                  key: "similarity",
                  label: "Relevance threshold",
                  min: 0,
                  max: 1,
                  step: 0.05,
                },
                {
                  key: "chunk_size",
                  label: "Chunk size",
                  min: 64,
                  max: 8192,
                  step: 1,
                },
                {
                  key: "overlap",
                  label: "Chunk overlap",
                  min: 0,
                  max: 4096,
                  step: 1,
                },
              ].map((f) => (
                <label className="field" key={f.key}>
                  {f.label}
                  <input
                    type="number"
                    required
                    min={f.min}
                    max={f.max}
                    step={f.step}
                    value={draft[f.key]}
                    onChange={(e) => update(f.key, Number(e.target.value))}
                  />
                </label>
              ))}
            </div>
          </details>
          <details>
            <summary>
              External RAG server (R2R)
              <ChevronDown size={15} />
            </summary>
            <label className="toggle-row">
              <div>
                <strong>Use R2R</strong>
                <p>Requires your own R2R server. File uploads only.</p>
              </div>
              <input
                type="checkbox"
                checked={draft.r2r}
                onChange={(e) => update("r2r", e.target.checked)}
              />
            </label>
            {draft.r2r && (
              <div className="form-grid">
                <label className="field">
                  R2R address
                  <input
                    value={draft.r2r_url}
                    onChange={(e) => update("r2r_url", e.target.value)}
                  />
                </label>
                <label className="field">
                  R2R API key
                  <input
                    type="password"
                    autoComplete="off"
                    value={draft.r2r_key}
                    onChange={(e) => update("r2r_key", e.target.value)}
                  />
                </label>
              </div>
            )}
          </details>
        </div>
        <div className="settings-footer">
          <p>
            <ShieldCheck size={16} />
            Preferences stay in this browser. Keys stay in server memory.
            <br />
            Changing embedding or server settings clears the current source
            index.
          </p>
          <button className="primary" disabled={disabled} type="submit">
            <Check size={16} />
            Save preferences
          </button>
        </div>
      </form>
      <div className="reset-row">
        <div>
          <strong>Start with a clean slate</strong>
          <p>Remove sources, conversation and saved preferences.</p>
        </div>
        <button
          className="text-button danger"
          disabled={disabled}
          onClick={reset}
        >
          <Trash2 size={15} />
          Reset workspace
        </button>
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
