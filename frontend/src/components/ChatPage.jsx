import React from "react";
import { ChatToolbar } from "./ChatToolbar.jsx";
import { Composer } from "./Composer.jsx";
import { MessageList } from "./MessageList.jsx";
import { SourcesPanel } from "./SourcesPanel.jsx";
import { Welcome } from "./Welcome.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Chat page: conversation column plus the optional sources panel. */
export function ChatPage() {
  const { messages, showSources } = useWorkspace();
  return (
    <div className="chat-layout">
      <section className="chat-area">
        <ChatToolbar />
        <div className="conversation-scroll">
          {!messages.length ? <Welcome /> : <MessageList />}
        </div>
        <Composer />
      </section>
      {showSources && <SourcesPanel />}
    </div>
  );
}
