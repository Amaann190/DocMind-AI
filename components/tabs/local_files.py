import hashlib

import streamlit as st

import utils.rag_pipeline as rag
import utils.r2r as r2r
import utils.helpers as func
from components.ingestion_prerequisites import (
    ingestion_is_configured,
)

supported_files = tuple(sorted(ext.lstrip(".") for ext in func.ALLOWED_UPLOAD_EXTENSIONS))


def _bytes_to_mb(size_in_bytes):
    return size_in_bytes // (1024 * 1024)


def upload_limit_help_text():
    return (
        f"Up to {func.MAX_UPLOAD_FILES} files. "
        f"{_bytes_to_mb(func.MAX_UPLOAD_FILE_BYTES)}MB per file, "
        f"{_bytes_to_mb(func.MAX_TOTAL_UPLOAD_BYTES)}MB total."
    )


def uploaded_files_signature(uploaded_files):
    """Return a stable signature for the current uploader contents."""
    return tuple(
        (
            uploaded_file.name,
            uploaded_file.size,
            uploaded_file.type,
            hashlib.sha256(uploaded_file.getvalue()).hexdigest(),
        )
        for uploaded_file in uploaded_files
    )


def should_process_uploads(
    current_signature,
    processed_signature,
    processing_signature,
    query_engine,
):
    """Return whether uploaded files need ingestion for the current app state."""
    if current_signature == processing_signature:
        return False
    if st.session_state.get("r2r_enabled"):
        return current_signature != processed_signature or not r2r.r2r_is_ready(st.session_state)
    return current_signature != processed_signature or query_engine is None


def local_files():
    # Force users to confirm Settings before uploading files
    if ingestion_is_configured():
        uploaded_files = st.file_uploader(
            "Select Files",
            accept_multiple_files=True,
            type=supported_files,
            key=f"upload_files_{st.session_state.get('upload_epoch', 0)}",
            help=upload_limit_help_text(),
        )
    else:
        file_upload_container = st.container(border=True)
        with file_upload_container:
            uploaded_files = st.file_uploader(
                "Select Files",
                accept_multiple_files=True,
                type=supported_files,
                key=f"upload_files_{st.session_state.get('upload_epoch', 0)}",
                disabled=True,
                help=upload_limit_help_text(),
            )

    if not uploaded_files:
        state = st.session_state
        if state.get("active_ingestion_source") == "file_ingestion_stages":
            for key in ("query_engine", "retriever", "documents", "active_ingestion_source"):
                state[key] = None
            state["last_doc_sources"] = []
            state["last_rag_no_result"] = False
            state["last_rag_question"] = None
            # Keep displayed chat, but do not send removed document facts back to the model.
            state["chat_history_start"] = len(state.get("messages", []))
            state["rag_history_start"] = state["chat_history_start"]
        if state.get("file_list") and state.get("r2r_document_ids"):
            # Retain ownership IDs for Reset Project cleanup; disallow further queries.
            state["r2r_ingestion_failed"] = True
        state["file_list"] = []
        for key in ("processed_file_signature", "processing_file_signature", "failed_upload_signature"):
            state[key] = None
        state["file_ingestion_stages"] = []
        state["file_ingestion_stages_errors"] = []
        state["r2r_ingestion_stages"] = []
        return

    if len(uploaded_files) > 0:
        try:
            func.validate_uploaded_files(uploaded_files)
        except ValueError as err:
            st.error(str(err))
            return

        large_files = [
            f.name
            for f in uploaded_files
            if getattr(f, "size", 0) > 8 * 1024 * 1024
        ]
        if large_files:
            st.info(
                "💡 **Large file(s):** "
                + ", ".join(large_files)
                + ". Big files take minutes to embed and heat up your laptop. "
                "Consider splitting them into 10-20 page PDFs or smaller documents."
            )

        st.session_state["file_list"] = uploaded_files
        current_upload_signature = uploaded_files_signature(uploaded_files)
        retry = st.button("Reprocess files", key="reprocess_files",
                          help="Retry a failed import or apply changed embedding/chunk settings.")
        if st.session_state.get("failed_upload_signature") == current_upload_signature and not retry:
            st.warning("The last import failed. Fix the settings or files, then choose Reprocess files.")
            return
        needs_processing = should_process_uploads(
            current_upload_signature,
            st.session_state["processed_file_signature"],
            st.session_state["processing_file_signature"],
            st.session_state["query_engine"],
        )

        status_container = st.empty()

        if needs_processing or retry:
            with st.spinner("Processing..."):
                st.session_state["processing_file_signature"] = (
                    current_upload_signature
                )
                try:
                    # Initiate the RAG pipeline only for new file contents or missing index state.
                    if st.session_state.get("r2r_enabled"):
                        error = r2r.r2r_ingest_files(
                            uploaded_files, status_container=status_container
                        )
                        if error is None:
                            st.session_state["processed_file_signature"] = current_upload_signature
                    else:
                        error = rag.rag_pipeline(
                            uploaded_files, status_container=status_container
                        )

                        # Display errors (if any) or proceed
                        if error is None:
                            st.session_state["processed_file_signature"] = (
                                current_upload_signature
                            )
                    st.session_state["failed_upload_signature"] = current_upload_signature if error is not None else None
                finally:
                    st.session_state["processing_file_signature"] = None
        else:
            if st.session_state.get("r2r_enabled"):
                status_container.empty()
            else:
                rag.render_pipeline_status(
                    status_container,
                    st.session_state["file_ingestion_stages"],
                )

        if r2r.r2r_is_ready(st.session_state):
            st.write(
                "Your files are ready on the R2R server. Let's chat! 😎"
            )
        elif st.session_state["query_engine"] is not None:
            rag.render_ingestion_result("file_ingestion_stages")
