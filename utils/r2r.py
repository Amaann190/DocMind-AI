"""Lightweight client for the R2R (RAG to Riches) REST API.

R2R is an external RAG server that handles ingestion, embedding, retrieval
and generation on its own hardware. Pointing DocMind at it moves the heavy
embedding/indexing work off the local machine entirely: less RAM, less heat,
less disk usage.

Only the endpoints DocMind needs are wrapped. The client is synchronous and
time-boxed so an unreachable server fails fast instead of hanging the app.
"""

import os
import tempfile
from urllib.parse import quote
from uuid import uuid4
from utils.session_workspace import session_directory

import httpx
import streamlit as st

import utils.helpers as func
import utils.logs as logs

DEFAULT_R2R_BASE_URL = "http://localhost:7272"
R2R_REQUEST_TIMEOUT = 120.0


class R2RConnectionError(Exception):
    """Raised when the R2R server cannot be reached or returns an error."""


class R2RClient:
    """Minimal HTTP client for the R2R REST API."""

    def __init__(
        self,
        base_url: str = DEFAULT_R2R_BASE_URL,
        api_key: str = "",
        timeout: float = R2R_REQUEST_TIMEOUT,
    ):
        self.base_url = str(base_url or DEFAULT_R2R_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        try:
            response = httpx.request(
                method, url, headers=self._headers, timeout=self.timeout, **kwargs
            )
        except httpx.HTTPError as err:
            raise R2RConnectionError(
                f"Could not reach R2R at {self.base_url}: {err}"
            ) from err
        if response.status_code >= 400 and not (method == "DELETE" and response.status_code == 404):
            raise R2RConnectionError(
                f"R2R returned HTTP {response.status_code} for {method} {path}: "
                f"{response.text[:300]}"
            )
        return response

    def health(self) -> bool:
        """Return whether the R2R server is reachable."""
        try:
            response = self._request("GET", "/v3/health")
            return response.status_code == 200
        except R2RConnectionError:
            return False

    def upload_documents(self, file_paths: list, document_ids=None) -> list:
        """Upload local files to R2R, returning the created document ids."""
        if document_ids is None:
            document_ids = []
        for file_path in file_paths:
            # Track an owned ID before sending: a timeout may happen after creation.
            document_id = str(uuid4())
            document_ids.append(document_id)
            self._upload_one(file_path, document_id)
            logs.log.info(f"Uploaded {os.path.basename(file_path)} to R2R (id={document_id})")
        return document_ids

    def _upload_one(self, file_path: str, document_id: str) -> str:
        name = os.path.basename(file_path)
        with open(file_path, "rb") as handle:
            files = {"file": (name, handle)}
            response = self._request("POST", "/v3/documents", files=files,
                                     data={"id": document_id, "run_with_orchestration": "false"})
        payload = _as_dict(response)
        if _extract_document_id(payload) != document_id:
            raise R2RConnectionError("R2R returned an unexpected document ID.")
        return document_id

    def delete_documents(self, document_ids: list):
        """Best-effort deletion of documents previously uploaded to R2R."""
        failed = []
        for document_id in document_ids:
            try:
                self._request("DELETE", f"/v3/documents/{quote(str(document_id), safe='')}")
                logs.log.info(f"Deleted R2R document {document_id}")
            except R2RConnectionError as err:
                failed.append(document_id)
                logs.log.warning(
                    f"Failed to delete R2R document {document_id}: {err}"
                )
        return failed

    def rag(self, query: str, document_ids: list = None) -> str:
        """Run a RAG query against R2R and return the generated answer text."""
        if not document_ids:
            raise R2RConnectionError("No session documents are available for this query.")
        payload = {"query": query, "search_settings": {
            "filters": {"document_id": {"$in": document_ids}},
            "graph_settings": {"enabled": False}},
            "rag_generation_config": {"stream": False}}
        response = self._request("POST", "/v3/retrieval/rag", json=payload)
        data = _as_dict(response)
        return _extract_answer(data)


def _as_dict(response) -> dict:
    try:
        data = response.json()
    except ValueError as err:
        raise R2RConnectionError(
            f"R2R returned a non-JSON response: {response.text[:300]}"
        ) from err
    if not isinstance(data, dict):
        raise R2RConnectionError(f"Unexpected R2R response shape: {data}")
    return data


def _extract_document_id(payload: dict) -> str:
    """Extract a document id from an upload response (single or bulk shape)."""
    results = payload.get("results", payload)
    candidates = results if isinstance(results, list) else [results]
    for entry in candidates:
        if isinstance(entry, dict):
            document_id = entry.get("document_id") or entry.get("id")
            if document_id:
                return str(document_id)
    raise R2RConnectionError(
        f"Could not parse a document id from the R2R response: {payload}"
    )


def _extract_answer(payload: dict) -> str:
    """Extract the generated answer from a RAG response payload."""
    results = payload.get("results", payload)
    if isinstance(results, dict):
        answer = (
            results.get("rag_response")
            or results.get("generated_answer")
            or results.get("answer")
        )
        if answer is not None:
            return str(answer)
    raise R2RConnectionError(
        f"R2R response did not contain an answer: {payload}"
    )


def get_client() -> R2RClient:
    """Return an R2RClient configured from session state."""
    return R2RClient(
        base_url=st.session_state.get("r2r_base_url") or DEFAULT_R2R_BASE_URL,
        api_key=st.session_state.get("r2r_api_key") or "",
    )


def r2r_is_ready(state) -> bool:
    """Return whether R2R mode is enabled and documents are loaded in R2R."""
    origin = state.get("r2r_document_origin")
    same_server = not origin or origin == {
        "base_url": (state.get("r2r_base_url") or DEFAULT_R2R_BASE_URL).rstrip("/"),
        "api_key": state.get("r2r_api_key") or ""}
    return bool(state.get("r2r_enabled") and state.get("r2r_document_ids")
                and same_server and not state.get("r2r_ingestion_failed"))


def clear_remote_documents(state):
    """Delete only this session's tracked IDs at their original server."""
    ids = state.get("r2r_document_ids") or []
    if not ids:
        return True
    origin = state.get("r2r_document_origin")
    if not origin:
        # Never guess ownership of documents from an older session format.
        return False
    failed = R2RClient(**origin).delete_documents(ids)
    state["r2r_document_ids"] = failed
    if failed:
        state["r2r_ingestion_failed"] = True
    else:
        state["r2r_document_origin"] = None
    return not failed


def _render_status(status_container, completed_stages, active_stage=None):
    if status_container is None:
        return
    status_container.empty()
    with status_container.container():
        for stage in completed_stages:
            st.caption(f"✔️ {stage}")
        if active_stage is not None:
            st.caption(f"⏳ {active_stage}")


def _render_completed(status_container, completed_stages):
    if status_container is None:
        return
    status_container.empty()
    with status_container.container():
        for stage in completed_stages:
            st.caption(f"✔️ {stage}")
        st.empty()
        st.empty()


def r2r_ingest_files(
    uploaded_files: list,
    status_container=None,
    status_state_key: str = "r2r_ingestion_stages",
):
    """Upload uploaded files to the configured R2R server.

    Files are saved to a temporary directory, uploaded to R2R, and the
    directory is removed afterwards. The returned document ids are stored in
    session state so chat can query them. Mirrors rag_pipeline's progress
    rendering and stop-on-error behavior.
    """
    completed_stages = []
    st.session_state["active_ingestion_source"] = "file_ingestion_stages"
    st.session_state["query_engine"] = None
    st.session_state["retriever"] = None
    st.session_state["last_doc_sources"] = []
    st.session_state["last_rag_no_result"] = False
    st.session_state["last_rag_question"] = None
    st.session_state["r2r_ingestion_failed"] = True

    def record_completed_stages():
        st.session_state[status_state_key] = list(completed_stages)

    _render_status(status_container, completed_stages)

    try:
        if not clear_remote_documents(st.session_state):
            raise R2RConnectionError("Could not clean up the previous R2R upload. Retry when its original server is reachable.")
        client = get_client()
        if not client.health():
            raise R2RConnectionError(
                f"R2R server is not reachable at {client.base_url}. "
                "Start the R2R server or disable the R2R backend in Settings."
            )
        completed_stages.append("R2R Connection OK")
        record_completed_stages()
        _render_status(status_container, completed_stages)

        func.validate_uploaded_files(uploaded_files)
        save_dir = tempfile.mkdtemp(prefix="r2r_", dir=session_directory("data"))
        uploaded_paths = []
        try:
            for uploaded_file in uploaded_files:
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    func.save_uploaded_file(uploaded_file, save_dir)
                    uploaded_paths.append(
                        os.path.join(save_dir, uploaded_file.name)
                    )
            completed_stages.append("Files Uploaded")
            record_completed_stages()
            _render_status(status_container, completed_stages)

            st.session_state["r2r_document_origin"] = {
                "base_url": client.base_url, "api_key": st.session_state.get("r2r_api_key") or ""}
            st.session_state["r2r_document_ids"] = []
            document_ids = client.upload_documents(uploaded_paths, st.session_state["r2r_document_ids"])
            if not document_ids:
                raise R2RConnectionError(
                    "R2R did not return any document ids after upload."
                )
            st.session_state["r2r_document_ids"] = document_ids
            st.session_state["query_engine"] = None
            st.session_state["retriever"] = None
            st.session_state["r2r_ingestion_failed"] = False
            st.session_state["rag_history_start"] = len(st.session_state.get("messages", []))
            completed_stages.append("Documents Indexed by R2R")
            record_completed_stages()
            _render_completed(status_container, completed_stages)
        finally:
            if os.path.isdir(save_dir):
                if not func.remove_dir_retry(save_dir):
                    logs.log.warning(
                        "Unable to delete R2R upload directory, "
                        "you may want to clean-up manually."
                    )
    except Exception as err:
        logs.log.error(f"R2R ingestion failed: {str(err)}")
        st.exception(err)
        clear_remote_documents(st.session_state)
        return err


def r2r_chat(prompt: str):
    """Query the R2R backend with the ingested documents.

    Yields the complete answer text (R2R's RAG endpoint is not streamed by
    this integration). Falls back to a clear error message on failure.
    """
    try:
        if not r2r_is_ready(st.session_state):
            raise R2RConnectionError("No ready documents for the currently selected R2R server.")
        client = get_client()
        document_ids = st.session_state.get("r2r_document_ids") or []
        answer = client.rag(prompt, document_ids=document_ids or None)
        yield answer
    except Exception as err:
        logs.log.error(f"R2R chat error: {str(err)}")
        yield (
            f"⚠️ **R2R error:** {err}. "
            "Check that the R2R server is running and reachable."
        )
        return
