import React, { useEffect, useState } from "react";
import { Check, ChevronDown, Sparkles, Trash2, RefreshCw, ShieldCheck, Cpu } from "lucide-react";
import { api } from "../api.js";

export function SettingsPage({ settings, disabled, save, reset }) {
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
          <label className="toggle-row">
            <div>
              <strong>Keep sources after restart</strong>
              <p>
                Saves your sources' text and uploaded files on this computer so they
                return when DocMind restarts. Turning this off deletes the saved copy.
              </p>
            </div>
            <input
              type="checkbox"
              aria-label="Keep sources after restart"
              checked={Boolean(draft.keep_sources)}
              disabled={draft.r2r}
              onChange={(e) => update("keep_sources", e.target.checked)}
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
