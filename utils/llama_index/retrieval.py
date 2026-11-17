"""Hybrid BM25 + dense retrieval with Reciprocal Rank Fusion and an evidence floor."""
import re

from rank_bm25 import BM25Plus

import utils.logs as logs
from llama_index.core.schema import NodeWithScore
from utils import runtime
from utils.llama_index.chunking import _node_dedup_key
from utils.llama_index.query import (
    _bm25_expanded_tokens,
    _bm25_tokens,
    _overview_stems,
    _rewrite_query,
)
from utils.llama_index.settings import (
    MIN_VECTOR_CANDIDATES,
    VECTOR_CANDIDATE_MULTIPLIER,
    VECTOR_EVIDENCE_FLOOR,
    _context_char_budget,
    _is_eco_mode,
)


class HybridRetriever:
    """Fuse vector similarity with BM25 keyword scores.

    BM25 runs entirely on the CPU in a few milliseconds per query and catches
    exact keyword matches (names, codes, numbers) that vector search misses.
    Fusion uses Reciprocal Rank Fusion (RRF): no extra GPU work, no LLM calls.
    Includes similarity cutoff, duplicate filtering, and context budgeting.
    """

    def __init__(self, vector_retriever, docstore, corpus, top_k, similarity_cutoff=None,
                 evidence_floor=VECTOR_EVIDENCE_FLOOR, use_vector=True, use_bm25=True):
        self.vector_retriever = vector_retriever
        self.docstore = docstore
        self.corpus = corpus
        self.top_k = top_k
        self.similarity_cutoff = similarity_cutoff if similarity_cutoff is not None else 0.3
        # None disables the evidence floor (ablation baseline "hybrid, no floor").
        self.evidence_floor = evidence_floor
        # Channel switches exist for ablations (vector-only / BM25-only).
        self.use_vector = use_vector
        self.use_bm25 = use_bm25
        self._tokens = [self._tokenize(node_id) for node_id in corpus]
        self._bm25 = BM25Plus(self._tokens) if any(self._tokens) else None

    def _tokenize(self, node_id):
        node = self.docstore.get_node(node_id)
        return _bm25_tokens(node.get_content())

    @staticmethod
    def _is_doc_level_query(query: str, rewritten: str) -> bool:
        """Heuristically detect questions about the document itself.

        "What is this document about?", "summarize the document", "tell me
        about the uploaded file" are answered best by the document's opening
        chunks, which state the topic explicitly. Specific fact questions keep
        many meaningful tokens after query cleaning and are left untouched.
        """
        lower = query.lower()
        if "summar" in lower or "overview" in lower:
            return True
        if any(word in lower for word in ("document", "website", "page")) and len(rewritten.split()) <= 4:
            return True
        return False

    def _apply_live_settings(self):
        """Refresh Top K / similarity cutoff from session state.

        The retriever is cached for the session, but the Advanced Settings
        sliders change `session_state` directly. Reading them here makes slider
        changes take effect on the very next query instead of after a re-ingest.
        """
        try:
            top_k = max(int(runtime.st.session_state.get("top_k", self.top_k)), 1)
            cutoff = float(
                runtime.st.session_state.get("similarity_cutoff", self.similarity_cutoff)
            )
        except (TypeError, ValueError):
            return
        if _is_eco_mode():
            # Eco Mode: fewer chunks per query = less prompt = less heat.
            top_k = min(top_k, 3)
        self.top_k = top_k
        self.similarity_cutoff = cutoff
        # The underlying vector retriever caps its candidate list too. Fetch a
        # wider pool than Top K so fusion has dense candidates to re-rank; the
        # final selection below is still capped at Top K.
        pool = max(top_k * VECTOR_CANDIDATE_MULTIPLIER, MIN_VECTOR_CANDIDATES)
        try:
            if self.vector_retriever._similarity_top_k != pool:
                self.vector_retriever._similarity_top_k = pool
        except AttributeError:
            pass

    def retrieve(self, query: str):
        self._apply_live_settings()
        rewritten = _rewrite_query(query)
        rrf_scores = {}
        vector_scores = {}

        # Vector search ranks
        # Embeddings need natural language; stemming is only for lexical search.
        vector_nodes = self.vector_retriever.retrieve(query) if self.use_vector else []
        for rank, node_score in enumerate(vector_nodes):
            node_id = node_score.node.node_id
            vector_scores[node_id] = max(
                vector_scores.get(node_id, 0.0), node_score.score or 0.0
            )
            rrf_scores[node_id] = rrf_scores.get(node_id, 0.0) + 1.0 / (60 + rank)

        # BM25 keyword ranks (exact term matches). Short queries are widened with
        # curated synonyms; the vector search above still used the clean query.
        # ``rewritten`` is already stemmed once; do not stem it again.
        tokens = rewritten.split()
        expanded_tokens = _bm25_expanded_tokens(tokens)
        bm25_hit_ids = set()
        if self.use_bm25 and expanded_tokens and self._bm25 is not None:
            bm25_scores = self._bm25.get_scores(expanded_tokens)
            bm25_hit_ids = {
                node_id
                for node_id, terms in zip(self.corpus, self._tokens)
                if set(expanded_tokens).intersection(terms)
            }
            bm25_ids = [node_id for node_id, _ in sorted(
                ((node_id, score) for node_id, score in zip(self.corpus, bm25_scores)
                 if node_id in bm25_hit_ids), key=lambda item: item[1], reverse=True,
            )]
            for rank, node_id in enumerate(bm25_ids):
                rrf_scores[node_id] = rrf_scores.get(node_id, 0.0) + 1.0 / (60 + rank)

        # Drop weak matches: below the similarity cutoff they are more likely
        # to cause hallucinated answers than to help. Chunks with a weak
        # vector score additionally need a BM25 keyword hit as evidence,
        # otherwise an unrelated question could still pull irrelevant context
        # (small local embedding models score everything in a tight band).
        def _is_credible(node_id):
            if node_id in bm25_hit_ids:
                return True
            vector = vector_scores.get(node_id, 0.0)
            if vector < self.similarity_cutoff:
                return False
            if (
                self.evidence_floor is not None
                and self.similarity_cutoff > 0
                and vector < self.evidence_floor
            ):
                return False
            return True

        filtered = {
            node_id: rrf
            for node_id, rrf in rrf_scores.items()
            if _is_credible(node_id)
        }
        # An explicitly named website section is stronger evidence than a
        # semantically similar neighboring category (e.g. another kind of player).
        section_matches = set()
        for node_id in filtered:
            section = self.docstore.get_node(node_id).metadata.get("section", "")
            terms = set(_bm25_tokens(section.rsplit(" / ", 1)[-1]))
            if terms and terms <= set(tokens):
                section_matches.add(node_id)
        if section_matches:
            filtered = {node_id: score for node_id, score in filtered.items() if node_id in section_matches}
        # Only a generic request for an overview may use document openings
        # without a topic match. A summary of a named topic follows normal retrieval.
        if self._is_doc_level_query(query, rewritten) and set(tokens) <= _overview_stems():
            openings = {}
            for node_id in self.corpus:
                node = self.docstore.get_node(node_id)
                metadata = node.metadata or {}
                source = metadata.get("source_path") or metadata.get("file_path") or metadata.get("source") or metadata.get("file_name") or node.ref_doc_id or node_id
                openings.setdefault(source, node_id)
            filtered = {node_id: 1.0 / (60 + rank) for rank, node_id in enumerate(openings.values())}
        if not filtered:
            return []

        # Exact-phrase boost: if the user quoted "refund policy", chunks
        # containing that exact phrase (case-insensitive) get +0.5 RRF.
        # Zero cost, catches user-intended exact search.
        phrases = re.findall(r'"([^"]+)"', query)
        # also handle single quotes for convenience
        phrases += re.findall(r"'([^']+)'", query)
        if phrases:
            for node_id in list(filtered.keys()):
                try:
                    content = self.docstore.get_node(node_id).get_content().lower()
                    for phrase in phrases:
                        if phrase.lower().strip() and phrase.lower().strip() in content:
                            filtered[node_id] = filtered[node_id] + 0.5
                            break
                except Exception:
                    continue

        # Keep the top chunks within a token budget that fits the model's
        # context window (light context compression).
        ranked = sorted(filtered.items(), key=lambda kv: kv[1], reverse=True)
        selected = []
        seen = set()
        used_chars = 0
        context_budget = _context_char_budget()

        for node_id, rrf_score in ranked:
            node = self.docstore.get_node(node_id)
            content = node.get_content()
            key = _node_dedup_key(node)
            if key in seen:
                continue
            if selected and used_chars + len(content) + 16 > context_budget:
                continue
            if not selected and len(content) + 16 > context_budget:
                node = node.model_copy(update={"text": content[:max(0, context_budget - 16)]})
                content = node.get_content()
            used_chars += len(content) + 16
            seen.add(key)
            selected.append(NodeWithScore(node=node, score=vector_scores.get(node_id, 0.0)))
            if len(selected) >= self.top_k:
                break
        return selected


def build_hybrid_retriever(vector_retriever, index, top_k, similarity_cutoff=None, **options):
    """Return a vector+BM25 hybrid retriever over the index's docstore.

    ``options`` are passed to HybridRetriever (evidence_floor, use_vector,
    use_bm25) and exist for ablation baselines; the app uses the defaults.
    """
    try:
        docstore = index.docstore
        corpus = list(docstore.docs.keys())
        if similarity_cutoff is None:
            similarity_cutoff = runtime.st.session_state.get("similarity_cutoff", 0.3)
        return HybridRetriever(
            vector_retriever=vector_retriever,
            docstore=docstore,
            corpus=corpus,
            top_k=top_k,
            similarity_cutoff=similarity_cutoff,
            **options,
        )
    except Exception as err:
        logs.log.warning(f"Hybrid retriever unavailable, falling back to vector: {err}")
        return vector_retriever
