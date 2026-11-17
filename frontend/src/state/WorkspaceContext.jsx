import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { api, storageKey, storePreferences } from "../api.js";
import { applyChatEvent, optimisticMessages, readEvents } from "../lib/chatStream.js";
import { useLayout } from "./useLayout.js";
import { useTheme } from "./useTheme.js";

// Exported for tests, which render components with a fixed context value.
export const WorkspaceContext = createContext(null);

/** Read workspace state and actions. Components must render inside WorkspaceProvider. */
export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error("useWorkspace must be used inside <WorkspaceProvider>.");
  return value;
}

/** Restore saved preferences into a fresh workspace without overwriting a live one. */
async function openSession(setError) {
  let current = await api("/session", { method: "POST" });
  let saved;
  try {
    saved = JSON.parse(localStorage.getItem(storageKey) || "null");
  } catch {
    saved = null;
  }
  if (saved && !current.sources.length && !current.messages.length) {
    try {
      current = await api("/settings", { method: "PUT", body: JSON.stringify(saved) });
    } catch {
      setError("Saved preferences could not be restored. Default settings are available.");
    }
  }
  return current;
}

export function WorkspaceProvider({ children }) {
  const theme = useTheme();
  const layout = useLayout();

  const [workspace, setWorkspace] = useState(null);
  const [page, setPage] = useState("chat");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [modal, setModal] = useState(null);
  const [preview, setPreview] = useState(null);
  const [chatSearch, setChatSearch] = useState("");
  const [chatResults, setChatResults] = useState(null);
  const [editingChat, setEditingChat] = useState(null);
  const [deletingChat, setDeletingChat] = useState(null);
  const [removingSource, setRemovingSource] = useState(null);
  const [online, setOnline] = useState(null);
  const [question, setQuestion] = useState("");
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState(-1);
  const [boot, setBoot] = useState(0);
  const bottom = useRef();
  const input = useRef();
  const replacement = useRef();
  const alive = useRef(true);

  // Debounced conversation search.
  useEffect(() => {
    if (!chatSearch.trim()) {
      setChatResults(null);
      return undefined;
    }
    let active = true;
    const timer = setTimeout(
      () =>
        api("/conversations?q=" + encodeURIComponent(chatSearch))
          .then((rows) => active && setChatResults(rows))
          .catch((e) => active && setError(e.message)),
      200,
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [chatSearch, workspace?.conversations]);

  // Open (or reopen after "Try again") the workspace session.
  useEffect(() => {
    alive.current = true;
    (async () => {
      try {
        const current = await openSession(setError);
        if (!alive.current) return;
        setWorkspace(current);
        await refreshOnline();
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

  // Poll while the server is busy (indexing, background chat naming).
  useEffect(() => {
    if (streaming || (!busy && !workspace?.busy && !workspace?.naming)) return undefined;
    const timer = setInterval(
      () =>
        api("/state")
          .then((s) =>
            setWorkspace((old) => (busy ? { ...old, status: s.status, progress: s.progress } : s)),
          )
          .catch(() => {}),
      1000,
    );
    return () => clearInterval(timer);
  }, [busy, streaming, workspace?.busy, workspace?.naming]);

  async function refreshOnline() {
    try {
      const models = await api("/models");
      if (alive.current) setOnline(models.online);
    } catch {
      if (alive.current) setOnline(false);
    }
  }

  /** Run an API call that returns workspace state; report errors and resync. */
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
      } catch {
        // Keep the last known state if the server is unreachable.
      }
      return undefined;
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
    setWorkspace((old) => ({ ...old, messages: optimisticMessages(old.messages, text, regenerate) }));
    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-DocMind-Client": "react" },
        body: JSON.stringify({ text, without_documents: without, regenerate }),
      });
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "The request failed.");
      }
      await readEvents(response.body, (event) => {
        if (event.type === "warning") setError(event.text);
        else setWorkspace((old) => ({ ...old, messages: applyChatEvent(old.messages, event) }));
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setStreaming(false);
      setStopping(false);
      try {
        setWorkspace(await api("/state"));
      } catch {
        // The streamed answer is already shown; a later poll resyncs.
      }
      input.current?.focus();
    }
  }

  async function sample() {
    setModal(null);
    await action("/import", { method: "POST", body: JSON.stringify({ kind: "sample" }) }, () =>
      setPage("chat"),
    );
  }

  async function saveSettings(draft) {
    const result = await action("/settings", { method: "PUT", body: JSON.stringify(draft) });
    if (result) {
      storePreferences(result.settings);
      setOnline(null);
      await refreshOnline();
    }
    return result;
  }

  async function copy(text, i) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(i);
      setTimeout(() => setCopied(-1), 1800);
    } catch {
      setError("Copy unavailable. Select the answer text to copy it.");
    }
  }

  const nav = (id) => {
    setPage(id);
    layout.setMobileNav(false);
  };

  const sources = workspace?.sources || [];
  const messages = workspace?.messages || [];
  const readySourceCount = sources.filter((source) => source.status === "ready").length;
  const value = {
    ...theme,
    ...layout,
    workspace, setWorkspace, page, setPage, nav,
    error, setError, busy, streaming, stopping, setStopping,
    disabled: busy || streaming || workspace?.busy,
    modal, setModal, preview, setPreview,
    chatSearch, setChatSearch,
    conversations: (chatResults ?? workspace?.conversations ?? []).filter((chat) => chat.started),
    editingChat, setEditingChat, deletingChat, setDeletingChat, removingSource, setRemovingSource,
    online, question, setQuestion, search, setSearch, copied, copy,
    retry: () => {
      setError("");
      setBoot((n) => n + 1);
    },
    bottom, input, replacement,
    sources, messages, readySourceCount,
    hasReadySources: Boolean(workspace?.has_index && readySourceCount),
    settings: workspace?.settings,
    action, send, sample, saveSettings,
  };
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}
