"""Document ingestion, indexing and hybrid retrieval for DocMind.

The implementation lives in focused submodules; this package re-exports the
names other code and tests import from ``utils.llama_index``.
"""
import os

# Transformers 5.x can emit a large volume of non-actionable alias warnings
# during startup. Keep app logs focused on failures we can act on.
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

from utils.llama_index.cache import (  # noqa: F401
    _prune_index_cache,
    index_cache_dir,
    index_cache_key,
    load_index_from_cache,
    persist_index_to_cache,
)
from utils.llama_index.chunking import (  # noqa: F401
    _dedupe_exact_nodes,
    _document_title,
    _merge_code_blocks,
    _node_dedup_key,
    _prepend_document_title,
    _verbalize_tabular_docs,
)
from utils.llama_index.embeddings import (  # noqa: F401
    OllamaEmbedding,
    ProgressReportingEmbedding,
    _ollama_model_names,
    setup_embedding_model,
    verify_embedding_model,
)
from utils.llama_index.engine import (  # noqa: F401
    create_query_engine,
)
from utils.llama_index.ingestion import (  # noqa: F401
    EXCLUDED_FILE_PATTERNS,
    _document_text,
    create_index,
    load_documents,
)
from utils.llama_index.query import (  # noqa: F401
    _FILLER_STEMS,
    _NUMBER_WORDS,
    _OVERVIEW_STEMS,
    _OVERVIEW_WORDS,
    _QUERY_FILLER_WORDS,
    _QUERY_SYNONYMS,
    _STEMMED_SYNONYMS,
    _STEMMER,
    _bm25_expanded_tokens,
    _bm25_tokens,
    _filler_stems,
    _overview_stems,
    _rewrite_query,
    _stemmed_synonyms,
    _stemmer,
)
from utils.llama_index.retrieval import (  # noqa: F401
    HybridRetriever,
    build_hybrid_retriever,
)
from utils.llama_index.settings import (  # noqa: F401
    CONTEXT_CHAR_BUDGET,
    INDEX_CACHE_KEEP,
    INDEX_CACHE_VERSION,
    MIN_CHUNK_CHARS,
    MIN_VECTOR_CANDIDATES,
    TEXT_QA_TEMPLATE,
    VECTOR_CANDIDATE_MULTIPLIER,
    VECTOR_EVIDENCE_FLOOR,
    _context_char_budget,
    _is_eco_mode,
    _is_oom_error,
)
