import React from "react";
import { Plus, MessageSquare, Library, Settings2, ChevronDown, Trash2, PanelLeftClose, ShieldCheck, Search, Pencil } from "lucide-react";
import { Brand, IconButton, ResizeHandle } from "./ui.jsx";

export function Sidebar({
  action,
  chatSearch,
  conversations,
  disabled,
  input,
  nav,
  navigationVisible,
  page,
  panelWidths,
  setChatSearch,
  setDeletingChat,
  setEditingChat,
  setPanelWidths,
  setQuestion,
  settings,
  sources,
  toggleNavigation,
  workspace,
}) {
  return (
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
          {!chatSearch && !conversations.length && (
            <p className="history-note">
              Your chats will appear here after your first message.
            </p>
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
  );
}
