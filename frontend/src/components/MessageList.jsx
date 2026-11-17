import React from "react";
import ReactMarkdown from "react-markdown";
import { ArrowUpRight, ArrowRight, FileText, RefreshCw, Copy, CheckCheck } from "lucide-react";
import { Brand, IconButton } from "./ui.jsx";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Conversation messages with citations, copy and regenerate. */
export function MessageList() {
  const { bottom, copied, copy, disabled, messages, send, setPreview, streaming } = useWorkspace();
  return (
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
  );
}
