import React, { useEffect, useRef, useState } from "react";
import { Plus, X, ChevronRight, Trash2, PanelLeftClose, PanelLeftOpen, LoaderCircle, RefreshCw, AlertCircle, Copy, Replace, Moon, Sun } from "lucide-react";
import { Brand, IconButton, Modal } from "./components/ui.jsx";
import { RenameConversation } from "./components/RenameConversation.jsx";
import { PassagePreview } from "./components/PassagePreview.jsx";
import { ImportModal } from "./components/ImportModal.jsx";
import { SettingsPage } from "./components/SettingsPage.jsx";
import { Sidebar } from "./components/Sidebar.jsx";
import { ChatPage } from "./components/ChatPage.jsx";
import { LibraryPage } from "./components/LibraryPage.jsx";
import { api, storePreferences, storageKey } from "./api.js";

export function App() {
  const [theme, setTheme] = useState(
    () => document.documentElement.dataset.theme || "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.style.colorScheme = theme;
    document.querySelector('meta[name="theme-color"]').content =
      theme === "dark" ? "#171c19" : "#f7f6f2";
  }, [theme]);
  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    try {
      localStorage.setItem("docmind-theme", next);
    } catch {}
  }
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
    if (streaming || (!busy && !workspace?.busy && !workspace?.naming)) return;
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
  }, [busy, streaming, workspace?.busy, workspace?.naming]);
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
  const readySourceCount = sources.filter((source) => source.status === "ready").length;
  const hasReadySources = Boolean(workspace?.has_index && readySourceCount);
  const settings = workspace?.settings;
  const conversations = (chatResults ?? workspace?.conversations ?? []).filter(
    (chat) => chat.started,
  );
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
      <Sidebar
        action={action}
        chatSearch={chatSearch}
        conversations={conversations}
        disabled={disabled}
        input={input}
        nav={nav}
        navigationVisible={navigationVisible}
        page={page}
        panelWidths={panelWidths}
        setChatSearch={setChatSearch}
        setDeletingChat={setDeletingChat}
        setEditingChat={setEditingChat}
        setPanelWidths={setPanelWidths}
        setQuestion={setQuestion}
        settings={settings}
        sources={sources}
        toggleNavigation={toggleNavigation}
        workspace={workspace}
      />
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
            <IconButton
              title={
                theme === "dark"
                  ? "Switch to light mode"
                  : "Switch to dark mode"
              }
              onClick={toggleTheme}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </IconButton>
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
                      {typeof w === "string" ? w : `${w.file}: ${w.error}`}
                    </p>
                  ))}
                </div>
              </div>
            )}
            {page === "chat" && (
              <ChatPage
                bottom={bottom}
                copied={copied}
                copy={copy}
                disabled={disabled}
                hasReadySources={hasReadySources}
                input={input}
                messages={messages}
                nav={nav}
                panelWidths={panelWidths}
                question={question}
                readySourceCount={readySourceCount}
                sample={sample}
                send={send}
                setError={setError}
                setModal={setModal}
                setPanelWidths={setPanelWidths}
                setPreview={setPreview}
                setQuestion={setQuestion}
                setShowSources={setShowSources}
                setStopping={setStopping}
                settings={settings}
                showSources={showSources}
                sources={sources}
                stopping={stopping}
                streaming={streaming}
              />
            )}
            {page === "library" && (
              <LibraryPage
                disabled={disabled}
                input={input}
                search={search}
                setModal={setModal}
                setPreview={setPreview}
                setSearch={setSearch}
                sources={sources}
                workspace={workspace}
              />
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
