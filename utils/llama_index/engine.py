"""Query engine assembly for a session's documents."""


import utils.logs as logs
from utils import runtime
from utils.llama_index.cache import (
    index_cache_dir,
    load_index_from_cache,
    persist_index_to_cache,
)
from utils.llama_index.ingestion import create_index
from utils.llama_index.retrieval import build_hybrid_retriever
from utils.llama_index.settings import TEXT_QA_TEMPLATE


def create_query_engine(documents, progress_callback=None):
    """
    Creates a query engine from the provided documents and service context.

    Args:
        documents (list[str]): A list of strings representing the content of the documents to be indexed.

    Returns:
        An instance of `QueryEngine`, containing the indexed data and allowing for querying of the data using a variety of parameters.

    Raises:
        Exception: If there is an error creating the query engine.

    Notes:
        The `documents` parameter should be a list of strings representing the content of the documents to be indexed.

        This function uses the `create_index` function to create an index from the provided documents and service context, and then creates a query engine from the resulting index. The `query_engine` parameter is used to specify the parameters of the query engine, including the number of top-ranked items to return (`similarity_top_k`) and the response mode (`response_mode`).
    """
    try:
        # Reuse a persisted index when the same documents + settings have
        # already been embedded (no repeated GPU work / heat).
        cache_dir = index_cache_dir(documents)
        index = load_index_from_cache(cache_dir) if cache_dir else None

        if index is None:
            index = create_index(documents, progress_callback=progress_callback)
            if cache_dir:
                persist_index_to_cache(index, cache_dir)

        # top_k of 0 would break retrieval; clamp to a sane minimum.
        similarity_top_k = max(int(runtime.st.session_state.get("top_k", 3)), 1)

        query_engine = index.as_query_engine(
            llm=runtime.st.session_state["llm"],
            similarity_top_k=similarity_top_k,
            response_mode="compact",
            streaming=True,
        )

        # Replace the generic llama-index QA prompt with the explicit
        # document-grounded template above.
        query_engine.update_prompts(
            {"response_synthesizer:text_qa_template": TEXT_QA_TEMPLATE}
        )

        # Keep a dedicated retriever in session state so doc-mode chat can
        # retrieve and stream token-by-token instead of buffering the whole
        # response through the (non-streaming) compact synthesizer. Vector +
        # BM25 hybrid catches keyword matches that pure vector search misses.
        vector_retriever = index.as_retriever(similarity_top_k=similarity_top_k)
        runtime.st.session_state["retriever"] = build_hybrid_retriever(
            vector_retriever, index, similarity_top_k,
            runtime.st.session_state.get("similarity_cutoff", 0.3)
        )

        runtime.st.session_state["query_engine"] = query_engine

        logs.log.info("Query Engine created successfully")

        return query_engine
    except Exception as e:  # noqa: BLE001 - logged and re-raised with context
        logs.log.error(f"Error when creating Query Engine: {e}")
        raise RuntimeError(f"Error when creating Query Engine: {e}") from e
