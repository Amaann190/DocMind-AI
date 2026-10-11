"""Lightweight client for the R2R (RAG to Riches) REST API.

R2R is an external RAG server that handles ingestion, embedding, retrieval
and generation on its own hardware. Pointing DocMind at it moves the heavy
embedding/indexing work off the local machine entirely: less RAM, less heat,
less disk usage.

Only the endpoints DocMind needs are wrapped. The client is synchronous and
time-boxed so an unreachable server fails fast instead of hanging the app.
"""

import os
from urllib.parse import quote
from uuid import uuid4

import httpx
from utils.runtime import st

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
