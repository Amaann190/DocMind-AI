import os
import tempfile

import streamlit as st

import utils.helpers as func
import utils.ollama as ollama
import utils.llama_index as llama_index
import utils.logs as logs
from utils.session_workspace import session_directory

MAX_INGESTED_DOCUMENTS = 300
MAX_INGESTED_TEXT_CHARS = 4 * 1024 * 1024


def _document_text(document):
    if hasattr(document, "get_content"):
        return document.get_content() or ""
    if hasattr(document, "text"):
        return document.text or ""
    return str(document)


def validate_ingested_documents(documents):
    if len(documents) > MAX_INGESTED_DOCUMENTS:
        raise ValueError(
            f"Too many documents were loaded. Limit: {MAX_INGESTED_DOCUMENTS}."
        )

    total_chars = sum(len(_document_text(document)) for document in documents)
    if total_chars > MAX_INGESTED_TEXT_CHARS:
        raise ValueError("Loaded documents exceed the ingestion text limit.")


def render_pipeline_status(status_container, completed_stages, active_stage=None):
    """Render truthful ingestion progress for the currently running pipeline."""
    if status_container is None:
        return

    status_container.empty()
    with status_container.container():
        for stage in completed_stages:
            st.caption(f"✔️ {stage}")
        if active_stage is not None:
            st.caption(f"⏳ {active_stage}")


def render_embedding_progress(status_container, completed_stages, completed, total):
    """Render exact embedding progress for the active indexing stage."""
    if status_container is None:
        return

    progress = 0 if total == 0 else min(completed / total, 1)
    progress_label = f"Generating Embeddings — {progress:.0%}"

    status_container.empty()
    with status_container.container():
        for stage in completed_stages:
            st.caption(f"✔️ {stage}")
        st.caption("⏳ Generating Embeddings")
        st.progress(progress, text=progress_label)
        st.caption(f"{completed:,} / {total:,} chunks embedded")


def render_completed_ingestion_status(status_container, completed_stages):
    """Render final ingestion status without leaving stale progress widgets behind."""
    if status_container is None:
        return

    status_container.empty()
    with status_container.container():
        for stage in completed_stages:
            st.caption(f"✔️ {stage}")
        # Replace the old progress-bar slots from the active embedding render.
        # Streamlit can otherwise leave stale child elements visible for this
        # run when the final render has fewer elements than the progress render.
        st.empty()
        st.empty()


def render_ingestion_result(status_state_key):
    """Keep partial-import warnings visible on subsequent Streamlit reruns."""
    errors = st.session_state.get(status_state_key + "_errors", [])
    if errors:
        st.warning(
            f"Only the successfully read files are ready. {len(errors)} file(s) "
            "were skipped; answers will not include them."
        )
        for failure in errors:
            st.text(f"{failure['file']}: {failure['error']}")
    else:
        st.write("Your files are ready. Let's chat! 😎")


def rag_pipeline(
    uploaded_files: list = None,
    documents: list = None,
    data_dir: str | None = None,
    status_container=None,
    initial_stages: list[str] | None = None,
    status_state_key: str = "file_ingestion_stages",
    documents_loaded_stage: str = "Documents Loaded",
):
    st.session_state["active_ingestion_source"] = status_state_key
    for key in ("query_engine", "retriever", "documents"):
        st.session_state[key] = None
    st.session_state["last_doc_sources"] = []
    # Remote IDs remain available for explicit cleanup on reset.
    st.session_state["last_rag_no_result"] = False
    st.session_state["last_rag_question"] = None
    # Cleanup also runs when Streamlit interrupts this operation with st.stop().
    with tempfile.TemporaryDirectory(prefix="upload_", dir=session_directory("data")) as save_dir:
        return _rag_pipeline(
            uploaded_files, documents, data_dir, status_container, initial_stages,
            status_state_key, documents_loaded_stage, save_dir,
        )


def _rag_pipeline(uploaded_files, documents, data_dir, status_container, initial_stages,
                  status_state_key, documents_loaded_stage, save_dir):
    """
    RAG pipeline for Llama-based chatbots.

    Parameters:
        - uploaded_files (list, optional): List of files to be processed.
            If none are provided, the function will load files from the current working directory.

    Yields:
        - str: Successive chunks of conversation from the Ollama model with context.

    Raises:
        - Exception: If there is an error retrieving answers from the Ollama model or creating the service context.

    Notes:
        This function initiates a chat with context using the Llama-Index library and the Ollama language model. It takes one optional parameter, `uploaded_files`, which should be a list of files to be processed. If no files are provided, the function will load files from the current working directory. The function returns an iterable yielding successive chunks of conversation from the Ollama model with context. If there is an error retrieving answers from the Ollama model or creating the service context, the function raises an exception.

    Context:
        - logs.log: A logger for logging events related to this function.

    Side Effects:
        - Creates a service context using the provided Ollama model and embedding file.
        - Loads documents from the current working directory or the provided list of files.
        - Removes the loaded documents and any temporary files created during processing.
    """
    error = None
    completed_stages = list(initial_stages or [])
    file_errors = []
    st.session_state[status_state_key + "_errors"] = file_errors

    def record_completed_stages():
        st.session_state[status_state_key] = list(completed_stages)

    render_pipeline_status(status_container, completed_stages)

    ingest_dir = data_dir or save_dir

    ######################################
    # Create Llama-Index service-context #
    # to use local LLMs and embeddings   #
    ######################################

    backend = st.session_state.get("llm_backend", "Ollama")

    try:
        if ollama.is_openai_backend(backend):
            llm = ollama.create_llm(
                st.session_state.get("openai_model")
                or st.session_state["selected_model"],
                st.session_state.get("openai_base_url")
                or ollama.DEFAULT_OPENAI_BASE_URL,
                st.session_state.get("openai_api_key") or "",
                system_prompt=st.session_state["system_prompt"],
            )
        else:
            selected_model = st.session_state["selected_model"]
            if not ollama.verify_chat_model(
                selected_model, st.session_state["ollama_endpoint"]
            ):
                raise ValueError(
                    f"Chat model '{selected_model}' is not available on the "
                    f"Ollama server at {st.session_state['ollama_endpoint']}. "
                    f"Pull it first with: ollama pull {selected_model}"
                )
            llm = ollama.create_llm(
                selected_model,
                st.session_state["ollama_endpoint"],
                system_prompt=st.session_state["system_prompt"],
            )
        st.session_state["llm"] = llm
        completed_stages.append("LLM Initialized")
        record_completed_stages()
        render_pipeline_status(status_container, completed_stages)

        # resp = llm.complete("Hello!")
        # print(resp)
    except Exception as err:
        logs.log.error(f"Failed to setup LLM: {str(err)}")
        error = err
        message = str(err)
        if "is not available on the Ollama server" in message:
            st.warning(
                "⚠️ **Chat model unavailable.**\n\n"
                f"{message}\n\n"
                "Go to **Settings → Chat**, click **Refresh Models**, and select "
                "an available chat model before uploading files.",
                icon=None,
            )
        else:
            st.exception(error)
        return error

    ####################################
    # Determine embedding model to use #
    ####################################

    try:
        chunk_size = int(st.session_state["chunk_size"])
        chunk_overlap = int(st.session_state["chunk_overlap"])
        if chunk_size <= 0:
            raise ValueError("Chunk Size must be > 0")
        if chunk_overlap < 0:
            raise ValueError("Chunk Overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("Chunk Overlap must be less than Chunk Size")

        if ollama.is_openai_backend(backend):
            selected_embedding_model = st.session_state.get(
                "openai_embedding_model"
            ) or "text-embedding-3-small"
            embedding_base_url = st.session_state.get("openai_base_url") or ollama.DEFAULT_OPENAI_BASE_URL
            llama_index.setup_embedding_model(
                selected_embedding_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                backend="OpenAI",
                ollama_endpoint=embedding_base_url,
                api_key=st.session_state.get("openai_api_key") or "",
            )
        else:
            selected_embedding_model = st.session_state["ollama_embedding_model"]
            llama_index.setup_embedding_model(
                selected_embedding_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                backend="Ollama",
                ollama_endpoint=st.session_state["ollama_endpoint"],
            )
        completed_stages.append("Embedding Model Ready")
        record_completed_stages()
        render_pipeline_status(status_container, completed_stages)
    except Exception as err:
        logs.log.error(f"Setting up Embedding Model failed: {str(err)}")
        error = err
        message = str(err)
        if "is not available on the Ollama server" in message:
            st.warning(
                "⚠️ **Embedding model unavailable.**\n\n"
                f"{message}\n\n"
                "Go to **Settings → Embeddings**, click **Refresh Models**, and "
                "select an available embedding model before uploading files.",
                icon=None,
            )
        else:
            st.exception(error)
        return error

    try:
        # Always reset the query engine before ingesting fresh source content.
        st.session_state["query_engine"] = None
        st.session_state["retriever"] = None
        st.session_state["documents"] = None

        if documents is not None:
            if len(documents) == 0:
                raise ValueError("No documents were loaded from the selected source.")
            validate_ingested_documents(documents)
            st.session_state["documents"] = documents
            completed_stages.append(documents_loaded_stage)
            record_completed_stages()
            render_pipeline_status(status_container, completed_stages)
        else:
            uploaded_paths = None
            if uploaded_files is not None:
                func.validate_uploaded_files(uploaded_files)
                uploaded_paths = []
                for uploaded_file in uploaded_files:
                    with st.spinner(f"Processing {uploaded_file.name}..."):
                        func.save_uploaded_file(uploaded_file, save_dir)
                        uploaded_paths.append(
                            os.path.join(save_dir, uploaded_file.name)
                        )
                completed_stages.append("Files Uploaded")
                record_completed_stages()
                render_pipeline_status(status_container, completed_stages)

            ingested_documents = llama_index.load_documents(
                ingest_dir, input_files=uploaded_paths, errors=file_errors
            )
            if len(ingested_documents) == 0:
                raise ValueError("No files were found to process.")
            validate_ingested_documents(ingested_documents)
            st.session_state["documents"] = ingested_documents
            loaded_stage = documents_loaded_stage
            if file_errors:
                loaded_stage += f" ({len(file_errors)} file(s) skipped)"
            completed_stages.append(loaded_stage)
            record_completed_stages()
            render_pipeline_status(status_container, completed_stages)
    except Exception as err:
        logs.log.error(f"Document Load Error: {str(err)}")
        error = err
        st.exception(error)
        return error

    ###########################################
    # Create an index from ingested documents #
    ###########################################

    try:

        def update_embedding_progress(completed, total):
            if total is None or total == 0:
                render_pipeline_status(
                    status_container, completed_stages, "Generating Embeddings"
                )
                return
            render_embedding_progress(
                status_container, completed_stages, completed, total
            )

        render_pipeline_status(
            status_container, completed_stages, "Generating Embeddings"
        )
        llama_index.create_query_engine(
            st.session_state["documents"],
            progress_callback=update_embedding_progress,
        )
        completed_stages.append("Embeddings Generated")
        completed_stages.append("Index Ready")
        record_completed_stages()
        render_completed_ingestion_status(status_container, completed_stages)
    except Exception as err:
        logs.log.error(f"Index Creation Error: {str(err)}")
        error = err
        st.exception(error)
        st.session_state["query_engine"] = None
        st.session_state["retriever"] = None
        return error

    st.session_state["rag_history_start"] = len(st.session_state.get("messages", []))

    return error  # If no errors occurred, None is returned
