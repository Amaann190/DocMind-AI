import io
from datetime import datetime

import docx
import streamlit as st

import utils.ollama as ollama
import utils.r2r as r2r
from components.page_state import default_chat_model
from utils.browser_settings import DEFAULT_OLLAMA_ENDPOINT, ensure_ollama_endpoint


def _check_r2r_connection():
    """Probe the configured R2R server and record the result for the UI."""
    st.session_state["r2r_connection_ok"] = r2r.get_client().health()


def _clear_r2r_connection_check():
    st.session_state["r2r_connection_ok"] = None


def _style_to_prompt(style: str) -> str:
    """Return the system prompt for a given answer style preset."""
    base = (
        "You are DocMind AI, a helpful and accurate virtual assistant. "
        "When document context is provided, answer strictly from that context "
        "and do not invent information. Otherwise answer from your general "
        "knowledge. Be factual and conversational."
    )
    style_instructions = {
        "Concise": " Keep answers as short as possible — one or two sentences.",
        "Balanced (default)": " Keep answers concise but complete.",
        "Detailed": " Provide thorough explanations with context and examples.",
        "Bulleted": " Structure answers as bullet points for readability.",
        "Technical": " Use precise terminology; assume a technical audience.",
        "Simple / ELI5": " Explain simply, like you're talking to a 12-year-old. Avoid jargon.",
    }
    return base + style_instructions.get(style, style_instructions["Balanced (default)"])


BACKEND_PRESETS = {
    "Ollama": {"base_url": DEFAULT_OLLAMA_ENDPOINT, "chat_model": "", "embedding_model": ""},
    "OpenAI": {"base_url": "https://api.openai.com/v1", "chat_model": "gpt-4o-mini", "embedding_model": "text-embedding-3-small"},
    "LM Studio (Local AI)": {"base_url": "http://localhost:1234/v1", "chat_model": "local-model", "embedding_model": "text-embedding-3-small"},
    "TabbyAPI": {"base_url": "http://localhost:5000/v1", "chat_model": "local-model", "embedding_model": "text-embedding-3-small"},
}


def _apply_backend_preset():
    """Prefill OpenAI-compatible fields when the backend preset changes."""
    preset = st.session_state.get("llm_backend", "Ollama")
    details = BACKEND_PRESETS.get(preset, {})
    if preset == "Ollama":
        st.session_state["ollama_endpoint"] = details.get(
            "base_url", DEFAULT_OLLAMA_ENDPOINT
        )
    else:
        st.session_state["openai_base_url"] = details.get(
            "base_url", ollama.DEFAULT_OPENAI_BASE_URL
        )
        if details.get("chat_model"):
            st.session_state["openai_model"] = details["chat_model"]
        if details.get("embedding_model"):
            st.session_state["openai_embedding_model"] = details["embedding_model"]


def _fetch_openai_models():
    """Fetch model ids from the configured OpenAI-compatible server."""
    st.session_state["openai_models"] = ollama.get_openai_models(
        st.session_state.get("openai_base_url") or ollama.DEFAULT_OPENAI_BASE_URL,
        st.session_state.get("openai_api_key") or "",
    )


def _refresh_models():
    ensure_ollama_endpoint(st.session_state)
    ollama.get_models()
    ollama.get_embedding_models()
    if st.session_state.get("selected_model") not in st.session_state["ollama_models"]:
        st.session_state["selected_model"] = default_chat_model(
            st.session_state["ollama_models"]
        )
    st.session_state["ollama_models_endpoint"] = st.session_state["ollama_endpoint"]
    st.session_state["ollama_embedding_models_endpoint"] = st.session_state["ollama_endpoint"]


def _refresh_embedding_models():
    ensure_ollama_endpoint(st.session_state)
    ollama.get_embedding_models()
    st.session_state["ollama_embedding_models_endpoint"] = st.session_state["ollama_endpoint"]


def _chat_history_signature(messages):
    """Return a hashable snapshot of the chat history for cache keying."""
    return tuple((m.get("role"), m.get("content"), tuple(tuple(source) for source in m.get("sources", []))) for m in messages)


@st.cache_data(show_spinner=False)
def chat_history_docx(signature):
    """Serialize chat history to a Word document, in memory."""
    document = docx.Document()
    document.add_heading("DocMind AI — Chat History", level=0)
    document.add_paragraph(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for message in signature:
        role, content = message[:2]
        paragraph = document.add_paragraph()
        label = "User" if role == "user" else "Assistant"
        paragraph.add_run(f"[{label}] ").bold = True
        paragraph.add_run(str(content))
        if len(message) > 2:
            for index, (name, _score) in enumerate(message[2], 1):
                document.add_paragraph(f"Source [{index}]: {name}")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def settings():
    st.header("Settings")
    st.caption("Pick your models and answer style — everything else is optional.")

    # ── 1. Chat model ──────────────────────────────────────────────
    st.subheader("Chat")
    st.caption("The model that writes your answers.")
    with st.container(border=True):
        backend = st.selectbox(
            "Provider",
            options=list(BACKEND_PRESETS.keys()),
            key="llm_backend",
            on_change=_apply_backend_preset,
            help="Ollama runs offline on your device. Other options connect to a compatible server (LM Studio, TabbyAPI, OpenAI, etc.).",
        )
        if backend == "Ollama":
            st.selectbox(
                "Chat Model",
                st.session_state["ollama_models"],
                key="selected_model",
                disabled=len(st.session_state["ollama_models"]) == 0,
                placeholder="Select Chat Model" if len(st.session_state["ollama_models"]) > 0 else "No Models Available",
            )
            st.button(
                "Refresh Models",
                key="refresh_chat_models",
                on_click=_refresh_models,
            )
            if len(st.session_state["ollama_models"]) == 0:
                st.info("No models found. Start Ollama and refresh. The tested document-chat model is `llama3:latest`.")
            with st.expander("Connection", expanded=False):
                st.text_input(
                    "Ollama Endpoint",
                    key="ollama_endpoint",
                    placeholder="http://localhost:11434",
                    on_change=_refresh_models,
                    help="Change only if Ollama runs on a different address.",
                )
        else:
            st.text_input(
                "Server URL",
                key="openai_base_url",
                placeholder=ollama.DEFAULT_OPENAI_BASE_URL,
                help="Example: http://localhost:1234/v1 for LM Studio.",
            )
            st.text_input(
                "API Key",
                key="openai_api_key",
                type="password",
                help="Leave empty for local servers without auth.",
            )
            st.text_input(
                "Chat Model",
                key="openai_model",
                placeholder="gpt-4o-mini  or  local-model",
            )
            st.button(
                "Fetch Models from Server",
                key="fetch_openai_models",
                on_click=_fetch_openai_models,
            )
            fetched = st.session_state.get("openai_models") or []
            if fetched:
                st.caption("Found: " + ", ".join(fetched[:10]) + ("…" if len(fetched) > 10 else ""))

    # ── 2. Embeddings ──────────────────────────────────────────────
    st.subheader("Document Search")
    st.caption("The model that understands your documents. Change only if answers feel off.")
    with st.container(border=True):
        if backend == "Ollama":
            st.selectbox(
                "Embedding Model",
                st.session_state["ollama_embedding_models"],
                key="ollama_embedding_model",
                disabled=len(st.session_state["ollama_embedding_models"]) == 0,
                placeholder=(
                    "Select Model"
                    if len(st.session_state["ollama_embedding_models"]) > 0
                    else "No Embedding Models Available"
                ),
            )
            st.button(
                "Refresh Models",
                key="refresh_embedding_models",
                on_click=_refresh_embedding_models,
            )
            if len(st.session_state["ollama_embedding_models"]) == 0:
                st.caption("Need one? Try: `ollama pull nomic-embed-text`")
        else:
            st.text_input(
                "Embedding Model",
                key="openai_embedding_model",
                placeholder="text-embedding-3-small",
            )

    # ── 3. Answer Style ────────────────────────────────────────────
    st.subheader("Answer Style")
    st.caption("How the assistant should sound.")
    with st.container(border=True):
        style = st.radio(
            "Style",
            options=[
                "Concise",
                "Balanced (default)",
                "Detailed",
                "Bulleted",
                "Technical",
                "Simple / ELI5",
            ],
            index=1,
            horizontal=True,
            key="answer_style",
        )
        st.session_state["system_prompt"] = _style_to_prompt(style)
        # Keep chatbox quick selector in sync
        st.session_state["quick_answer_style"] = style
        with st.expander("Preview prompt", expanded=False):
            st.caption(_style_to_prompt(style))

    # ── 4. Everyday toggles ────────────────────────────────────────
    st.subheader("Preferences")
    with st.container(border=True):
        st.toggle(
            "Eco Mode — save power & stay cool",
            key="eco_mode",
            help="Fewer chunks, shorter answers, smaller batches. Turn on if the laptop gets hot or slow.",
        )
        if st.session_state.get("eco_mode"):
            st.caption("On: smaller batches · shorter answers · fewer chunks.")
        else:
            st.caption("Off: best quality. Turn on when the machine runs hot.")
        st.divider()
        st.toggle("Show advanced controls", key="advanced")
        st.caption("Reveals fine-tuning sliders and server options below.")

    # ── 5. Advanced (only when enabled) ─────────────────────────────
    if st.session_state.get("advanced"):
        with st.container(border=True):
            st.markdown("**Fine-tuning**")
            st.select_slider(
                "Sources per answer",
                options=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                value=st.session_state["top_k"],
                key="top_k",
                help="How many document chunks to include when answering.",
            )
            st.slider(
                "Relevance threshold",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                value=st.session_state.get("similarity_cutoff", 0.3),
                help="Higher = stricter, only very relevant chunks.",
                key="similarity_cutoff",
            )
            st.slider(
                "Creativity",
                min_value=0.0,
                max_value=1.5,
                step=0.05,
                value=float(st.session_state.get("temperature", 0.4)),
                help="Lower = focused & factual, higher = more creative.",
                key="temperature",
            )
            st.number_input(
                "Chunk Size",
                key="chunk_size",
                min_value=64, max_value=8192, step=32,
                help="Tokens per document piece (~4 chars each). Smaller = more precise, more work.",
            )
            chunk_overlap_pct = st.slider(
                "Chunk Overlap",
                min_value=0,
                max_value=50,
                step=1,
                value=st.session_state.get("chunk_overlap_pct", 12),
                help="Overlap between chunks as % of chunk size. Keeps context across boundaries.",
                key="chunk_overlap_pct",
            )
            chunk_size = int(st.session_state.get("chunk_size") or 256)
            st.session_state["chunk_overlap"] = max(0, chunk_size * int(chunk_overlap_pct) // 100)
            st.caption(f"→ {st.session_state['chunk_overlap']} tokens overlap")

    # ── 6. R2R (collapsed by default) ──────────────────────────────
    with st.expander("External RAG server (R2R) — optional", expanded=False):
        st.caption("Use an external R2R server instead of local indexing. Most users can ignore this.")
        st.toggle(
            "Enable R2R",
            key="r2r_enabled",
            help="When on, files are indexed on the R2R server.",
        )
        st.text_input(
            "R2R URL",
            key="r2r_base_url",
            placeholder=r2r.DEFAULT_R2R_BASE_URL,
            on_change=_clear_r2r_connection_check,
        )
        st.text_input(
            "API Key (optional)",
            key="r2r_api_key",
            type="password",
        )
        st.button(
            "Test Connection",
            key="check_r2r_connection",
            on_click=_check_r2r_connection,
        )
        if st.session_state.get("r2r_connection_ok") is True:
            st.success("R2R server reachable.")
        elif st.session_state.get("r2r_connection_ok") is False:
            st.error("Could not reach R2R. Check the URL or disable R2R.")
        if st.session_state.get("r2r_enabled") and not st.session_state.get("r2r_document_ids"):
            st.info("R2R is on — upload files in Data Sources → Local Files.")

    # ── 7. Export ──────────────────────────────────────────────────
    st.subheader("Export")
    with st.container(border=True):
        st.caption("Save your conversation as a Word file.")
        st.download_button(
            label="Download chat (.docx)",
            data=chat_history_docx(_chat_history_signature(st.session_state["messages"])),
            file_name=f"docmind-chat-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
