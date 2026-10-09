import streamlit as st

import utils.logs as logs

from utils.session_workspace import clear_session_workspace
from utils.ollama import default_embedding_model, get_models, get_embedding_models
from utils.browser_settings import (
    PERSISTED_SETTINGS_HASH_STATE_KEY,
    ensure_ollama_endpoint,
    restore_settings_from_browser_storage,
    should_refresh_models_for_endpoint,
)

WELCOME_MESSAGE = {
    "role": "assistant",
    "content": (
        "Hi! I'm **DocMind AI** — your private document assistant. 👋\n\n"
        "**How to use — 3 simple steps:**\n"
        "1. Add your files, GitHub repo, or a website from the left sidebar\n"
        "2. Wait a moment while it reads them\n"
        "3. Ask anything below — answers come from your documents\n\n"
        "_No documents? Just chat — ask me anything._"
    ),
}


def perform_project_reset(state):
    """Wipe all stored data and restore the app to a fresh-project state.

    Must run BEFORE any widget with a session key is instantiated in the
    current script run, otherwise Streamlit rejects modifying widget keys.
    """
    from utils.r2r import clear_remote_documents
    if not clear_remote_documents(state):
        state["reset_error"] = "Reset paused: some R2R documents could not be deleted. Restore the original server connection and retry Reset Project. Their IDs have been retained."
        return False
    clear_session_workspace(state)
    state.pop("embedding_model", None)
    state.pop("embedding_config", None)

    state["query_engine"] = None
    state["active_ingestion_source"] = None
    state["retriever"] = None
    state["llm"] = None
    state["documents"] = None
    state["file_list"] = []
    state["processed_file_signature"] = None
    state["processing_file_signature"] = None
    state["processed_github_repo"] = None
    state["processed_website_urls"] = None
    state["github_ingestion_stages"] = []
    state["website_ingestion_stages"] = []
    state["file_ingestion_stages"] = []
    for key in ("file_ingestion_stages", "github_ingestion_stages", "website_ingestion_stages"):
        state[key + "_errors"] = []
    state["r2r_ingestion_stages"] = []
    state["r2r_document_ids"] = []
    state["r2r_connection_ok"] = None
    state["messages"] = [dict(WELCOME_MESSAGE)]
    state["rag_history_start"] = 0
    state["chat_history_start"] = 0
    state["last_doc_sources"] = []
    state.update(last_rag_no_result=False, last_rag_question=None, ask_without_docs=False,
                 github_repo="", websites=[], new_website="", website_input_error=None,
                 r2r_enabled=False, r2r_base_url="http://localhost:7272", r2r_api_key="",
                 r2r_document_origin=None, r2r_ingestion_failed=False,
                 openai_api_key="", similarity_cutoff=0.3, system_prompt=None,
                 confirm_project_reset=False, reset_error=None, failed_upload_signature=None)
    state["upload_epoch"] = state.get("upload_epoch", 0) + 1
    from utils.browser_settings import DEFAULT_OLLAMA_ENDPOINT
    state["ollama_endpoint"] = DEFAULT_OLLAMA_ENDPOINT
    for key in ("selected_model", "ollama_embedding_model", "ollama_models", "ollama_embedding_models",
                "ollama_models_endpoint", "ollama_embedding_models_endpoint"):
        state.pop(key, None)

    # Widget-backed keys: safe here only because no widgets exist yet.
    state["top_k"] = 3
    state["chunk_size"] = 256
    state["chunk_overlap"] = 32
    state["chunk_overlap_pct"] = 12
    state["advanced"] = False
    state["temperature"] = 0.4
    state["eco_mode"] = False
    state["quick_answer_style"] = "Balanced (default)"
    state["answer_style"] = "Balanced (default)"
    state["llm_backend"] = "Ollama"
    state["openai_base_url"] = "http://localhost:1234/v1"
    state["openai_model"] = ""
    state["openai_embedding_model"] = "text-embedding-3-small"
    state["openai_models"] = []

    # Force the next persist round to write clean defaults to localStorage
    # instead of the stale pre-reset values.
    state[PERSISTED_SETTINGS_HASH_STATE_KEY] = None

    logs.log.info("Project reset: caches and data cleared")
    return True


def default_chat_model(models):
    """Return the preferred default chat model from discovered Ollama models."""
    preferred_models = (
        "gemma4:latest",
        "llama3:8b",
        "llama3:latest",
        "llama2:7b",
    )

    for model in preferred_models:
        if model in models:
            return model

    if models:
        return models[0]

    return None


def ensure_valid_model_selections(state):
    """Keep selected model values consistent with discovered model lists."""
    chat_models = state.get("ollama_models", [])
    if chat_models:
        if state.get("selected_model") not in chat_models:
            state["selected_model"] = default_chat_model(chat_models)
    elif "selected_model" in state:
        state["selected_model"] = None

    embedding_models = state.get("ollama_embedding_models", [])
    if embedding_models:
        if state.get("ollama_embedding_model") not in embedding_models:
            state["ollama_embedding_model"] = default_embedding_model(embedding_models)
    elif "ollama_embedding_model" in state:
        state["ollama_embedding_model"] = None


def set_initial_state():
    restore_settings_from_browser_storage()

    # A pending project reset (requested from the sidebar button) must be
    # executed here: widgets are not instantiated yet, so resetting
    # widget-backed keys is still legal.
    if st.session_state.get("reset_requested"):
        perform_project_reset(st.session_state)
        st.session_state["reset_requested"] = False

    ###########
    # General #
    ###########

    if "sidebar_state" not in st.session_state:
        st.session_state["sidebar_state"] = "expanded"

    ensure_ollama_endpoint(st.session_state)

    if "ollama_embedding_model" not in st.session_state:
        st.session_state["ollama_embedding_model"] = "nomic-embed-text:latest"

    if should_refresh_models_for_endpoint(st.session_state, "ollama_models"):
        try:
            models = get_models()
            st.session_state["ollama_models"] = models
        except Exception:
            st.session_state["ollama_models"] = []
            pass
        st.session_state["ollama_models_endpoint"] = st.session_state["ollama_endpoint"]

    if should_refresh_models_for_endpoint(st.session_state, "ollama_embedding_models"):
        try:
            models = get_embedding_models()
            st.session_state["ollama_embedding_models"] = models
        except Exception:
            st.session_state["ollama_embedding_models"] = []
            pass
        st.session_state["ollama_embedding_models_endpoint"] = st.session_state["ollama_endpoint"]

    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = default_chat_model(
            st.session_state.get("ollama_models", [])
        )

    ensure_valid_model_selections(st.session_state)

    if "messages" not in st.session_state:
        st.session_state["messages"] = [dict(WELCOME_MESSAGE)]

    ################################
    #  Files, Documents & Websites #
    ################################

    if "file_list" not in st.session_state:
        st.session_state["file_list"] = []

    if "processed_file_signature" not in st.session_state:
        st.session_state["processed_file_signature"] = None

    if "processing_file_signature" not in st.session_state:
        st.session_state["processing_file_signature"] = None

    if "file_ingestion_stages" not in st.session_state:
        st.session_state["file_ingestion_stages"] = []

    if "r2r_ingestion_stages" not in st.session_state:
        st.session_state["r2r_ingestion_stages"] = []

    if "r2r_document_ids" not in st.session_state:
        st.session_state["r2r_document_ids"] = []

    if "r2r_connection_ok" not in st.session_state:
        st.session_state["r2r_connection_ok"] = None

    if "github_ingestion_stages" not in st.session_state:
        st.session_state["github_ingestion_stages"] = []

    if "website_ingestion_stages" not in st.session_state:
        st.session_state["website_ingestion_stages"] = []

    if "github_repo" not in st.session_state:
        st.session_state["github_repo"] = ""
    elif st.session_state["github_repo"] is None:
        st.session_state["github_repo"] = ""

    if "processed_github_repo" not in st.session_state:
        st.session_state["processed_github_repo"] = None

    if "websites" not in st.session_state:
        st.session_state["websites"] = []

    if "new_website" not in st.session_state:
        st.session_state["new_website"] = ""

    if "website_input_error" not in st.session_state:
        st.session_state["website_input_error"] = None

    ###############
    # Llama-Index #
    ###############

    if "llm" not in st.session_state:
        st.session_state["llm"] = None

    if "documents" not in st.session_state:
        st.session_state["documents"] = None

    if "query_engine" not in st.session_state:
        st.session_state["query_engine"] = None

    if "retriever" not in st.session_state:
        st.session_state["retriever"] = None

    #####################
    # Advanced Settings #
    #####################

    if "advanced" not in st.session_state:
        st.session_state["advanced"] = False

    if "system_prompt" not in st.session_state:
        st.session_state["system_prompt"] = (
            "You are DocMind AI, a helpful and accurate virtual assistant. "
            "When document context is provided, answer strictly from that context "
            "and do not invent information. If you are unsure, say so directly. "
            "Otherwise answer from your general knowledge. "
            "Be concise, factual, and conversational."
        )

    if "top_k" not in st.session_state:
        st.session_state["top_k"] = 3

    if "chunk_size" not in st.session_state:
        st.session_state["chunk_size"] = 256

    if "chunk_overlap" not in st.session_state:
        st.session_state["chunk_overlap"] = 32

    if "chunk_overlap_pct" not in st.session_state:
        st.session_state["chunk_overlap_pct"] = 12

    if "similarity_cutoff" not in st.session_state:
        st.session_state["similarity_cutoff"] = 0.3

    if "temperature" not in st.session_state:
        st.session_state["temperature"] = 0.4

    if "eco_mode" not in st.session_state:
        st.session_state["eco_mode"] = False

    if "quick_answer_style" not in st.session_state:
        st.session_state["quick_answer_style"] = "Balanced (default)"

    if "answer_style" not in st.session_state:
        st.session_state["answer_style"] = st.session_state.get("quick_answer_style", "Balanced (default)")

    ##################
    # LLM Backends   #
    ##################

    if "llm_backend" not in st.session_state:
        st.session_state["llm_backend"] = "Ollama"

    if "openai_base_url" not in st.session_state:
        st.session_state["openai_base_url"] = "http://localhost:1234/v1"

    if "openai_api_key" not in st.session_state:
        st.session_state["openai_api_key"] = ""

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = ""

    if "openai_embedding_model" not in st.session_state:
        st.session_state["openai_embedding_model"] = "text-embedding-3-small"

    if "openai_models" not in st.session_state:
        st.session_state["openai_models"] = []

    ###########
    # R2R     #
    ###########

    if "r2r_enabled" not in st.session_state:
        st.session_state["r2r_enabled"] = False

    if "r2r_base_url" not in st.session_state:
        st.session_state["r2r_base_url"] = "http://localhost:7272"

    if "r2r_api_key" not in st.session_state:
        st.session_state["r2r_api_key"] = ""
