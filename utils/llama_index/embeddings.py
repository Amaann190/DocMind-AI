"""Embedding model clients, validation, batching and progress reporting."""
import hashlib

import ollama
from pydantic import Field, PrivateAttr

import utils.logs as logs
from llama_index.core.embeddings import BaseEmbedding
from utils import runtime
from utils.errors import MODEL_SERVER_ERRORS


class ProgressReportingEmbedding(BaseEmbedding):
    """Delegate embeddings while reporting exact batch progress."""

    wrapped_model: BaseEmbedding
    progress_callback: object = Field(exclude=True)
    total_texts: int = Field(default=0)
    completed_texts: int = Field(default=0)

    def _get_query_embedding(self, query: str):
        return self.wrapped_model.get_query_embedding(query)

    async def _aget_query_embedding(self, query: str):
        return await self.wrapped_model.aget_query_embedding(query)

    def _get_text_embedding(self, text: str):
        return self.wrapped_model.get_text_embedding(text)

    def get_text_embedding_batch(self, texts, show_progress=False, **kwargs):
        self.total_texts = len(texts)
        result = []
        batch_size = self.wrapped_model.embed_batch_size
        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            result.extend(
                self.wrapped_model.get_text_embedding_batch(
                    batch,
                    show_progress=False,
                    **kwargs,
                )
            )
            self.completed_texts += len(batch)
            self.progress_callback(self.completed_texts, self.total_texts)
        return result


class OllamaEmbedding(BaseEmbedding):
    """LlamaIndex embedding adapter backed by an Ollama server.
    
    Uses batched embed requests for significantly faster ingestion.
    """

    base_url: str = Field(description="Ollama server base URL")
    embed_batch_size: int = Field(default=16, description="Chunks per embed request")

    _client: ollama.Client | None = PrivateAttr(default=None)

    def _client_inst(self):
        # Reuse a single persistent client. Creating a fresh client per call
        # opens a new connection each time, which on Windows can cost ~2s per
        # embed due to IPv6 -> IPv4 fallback against a 127.0.0.1-bound server.
        client = self._client
        if client is None:
            client = ollama.Client(host=self.base_url, timeout=300)
            self._client = client
        return client

    def _get_query_embedding(self, query: str):
        return self._client_inst().embed(model=self.model_name, input=[query]).embeddings[0]

    async def _aget_query_embedding(self, query: str):
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str):
        return self._client_inst().embed(model=self.model_name, input=[text]).embeddings[0]

    def get_text_embedding_batch(self, texts, show_progress=False, **kwargs):
        """Send chunks in batches to Ollama, shrinking the batch on failure.

        A batch that is too large can exhaust GPU memory on the Ollama server
        (CUDA OOM). The failed batch is retried with a smaller size so ingestion
        finishes instead of crashing mid-way; the smaller size is kept for the
        rest of the run to avoid repeated failures.
        """
        result = []
        client = self._client_inst()
        index = 0
        batch_size = self.embed_batch_size
        while index < len(texts):
            batch = texts[index : index + batch_size]
            try:
                response = client.embed(model=self.model_name, input=batch)
                result.extend(response.embeddings)
                index += len(batch)
            except Exception as err:
                if len(batch) <= 1:
                    raise
                logs.log.warning(
                    f"Embedding batch of {len(batch)} failed ({err}); "
                    f"shrinking batch size and retrying"
                )
                batch_size = max(1, batch_size // 2)
                self.embed_batch_size = batch_size
        return result


###################################
#
# Setup Embedding Model
#
###################################


def _ollama_model_names(client) -> list[str]:
    """Return the installed model names from an Ollama client.

    Handles both the dict-based API responses and the pydantic model objects
    returned by newer versions of the `ollama` library.
    """
    try:
        data = client.list()
    except MODEL_SERVER_ERRORS:
        return []
    models = data.get("models", []) if isinstance(data, dict) else getattr(data, "models", [])
    names = []
    for model in models:
        try:
            name = model.get("model") or model.get("name")
        except AttributeError:
            name = getattr(model, "model", None) or getattr(model, "name", None)
        if name:
            names.append(name)
    return names


def verify_embedding_model(model: str, base_url: str) -> bool:
    """Return whether a model exists on the Ollama server and can embed.

    Guards against silently ingesting with a stale or mistyped embedding model.
    Checking the live server here is authoritative: the session-state model list
    can go stale after an endpoint change or a model removal.
    """
    try:
        client = ollama.Client(host=base_url, timeout=30)
        if model not in _ollama_model_names(client):
            return False
        details = client.show(model)
        capabilities = getattr(details, "capabilities", None) or details.get("capabilities", [])
        return "embedding" in capabilities
    except MODEL_SERVER_ERRORS:
        return False


# Model instances and chunk settings belong only to the calling session.
def setup_embedding_model(
    model: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    backend: str = "Ollama",
    ollama_endpoint: str | None = None,
    api_key: str = "",
):
    """
    Sets up the embedding model used for document ingestion.

    Args:
        model (str): The name of the embedding model to use.
        chunk_size (int, optional): Chunk size in tokens.
        chunk_overlap (int, optional): Chunk overlap in tokens.
        backend (str): "Ollama" (local Ollama server) or "OpenAI"
            (any OpenAI-compatible embeddings endpoint).
        ollama_endpoint (str, optional): Server base URL.
        api_key (str, optional): API key for OpenAI-compatible backends.

    Returns:
        An instance of the configured embedding model.

    Raises:
        ValueError: If the specified model is not a valid embedding model.
    """
    try:
        if not ollama_endpoint:
            raise ValueError("A server endpoint is required for embeddings")

        # Lazy import: utils.ollama imports TEXT_QA_TEMPLATE from this module,
        # so a top-level import here would be circular.
        from utils.ollama import _embed_batch_size, is_openai_backend

        if is_openai_backend(backend):
            from llama_index.embeddings.openai import OpenAIEmbedding

            embed_model = OpenAIEmbedding(
                model_name=model,
                api_key=api_key or "sk-docmind-local",
                api_base=ollama_endpoint,
                embed_batch_size=_embed_batch_size(),
            )
            logs.log.info(
                f"Using OpenAI-compatible model {model} to generate embeddings "
                f"(batched, {ollama_endpoint})"
            )
        else:
            if not verify_embedding_model(model, ollama_endpoint):
                raise ValueError(
                    f"Embedding model '{model}' is not available on the Ollama server "
                    f"at {ollama_endpoint}. Pull it first with: ollama pull {model}"
                )
            embed_model = OllamaEmbedding(
                model_name=model,
                base_url=ollama_endpoint,
                embed_batch_size=_embed_batch_size(),
            )
            logs.log.info(f"Using Ollama model {model} to generate embeddings (batched)")

        runtime.st.session_state["embedding_model"] = embed_model
        runtime.st.session_state["embedding_config"] = {
            "model": model, "backend": backend, "endpoint": ollama_endpoint.rstrip("/"),
            "chunk_size": chunk_size if chunk_size is not None else 256,
            "chunk_overlap": chunk_overlap if chunk_overlap is not None else 32,
            "credential_fingerprint": hashlib.sha256(api_key.encode()).hexdigest(),
        }

        logs.log.info("Embedding model created successfully")

        return embed_model
    except Exception as err:
        logs.log.error(f"Failed to setup the embedding model: {err}")
        raise


###################################
#
# Load Documents
#
###################################
