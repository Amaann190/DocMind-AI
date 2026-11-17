import React from "react";
import { ArrowUpRight, ArrowRight, Check, Sparkles, Search, BookOpen, Zap } from "lucide-react";
import { useWorkspace } from "../state/WorkspaceContext.jsx";

/** Empty-conversation view with getting-started cards. */
export function Welcome() {
  const { disabled, hasReadySources, input, readySourceCount, sample, setModal, setQuestion } = useWorkspace();
  return (
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
  );
}
