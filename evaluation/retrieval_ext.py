"""Retrieval metrics and baselines for the results paper, kept outside the DocMind app code.

Pure helpers (hit, true recall, depth filling, fusion, alpha selection, the stricter
keyword-evidence rule) are unit tested offline. The classes below wrap the app's
retriever or add plain baselines without editing anything under ``utils/``.
"""
import copy
import math
import re

KEYWORD_SHARE = 0.5          # DocMind's "half of the question's terms" rule
CANDIDATE_DEPTH = 100        # per-channel candidate depth for the plain fusions
RERANK_DEPTH = 50
RRF_K = 60
ALPHAS = tuple(round(i / 10, 1) for i in range(11))
CROSS_ENCODER = "cross-encoder/ms-marco-MiniLM-L-6-v2"
NOMIC_QUERY_PREFIX = "search_query: "
NOMIC_DOCUMENT_PREFIX = "search_document: "


# ---------------------------------------------------------------- metrics

def hit_at_k(ranked, relevant, k):
    """1.0 when any relevant document is in the top k (what the older ``recall@k`` key measures)."""
    return 1.0 if any(doc in relevant for doc in ranked[:k]) else 0.0


def true_recall_at_k(ranked, relevant, k):
    """Fraction of the relevant documents that appear in the top k (0.0 when nothing is relevant)."""
    relevant = set(relevant)
    if not relevant:
        return 0.0
    return len(relevant & set(ranked[:k])) / len(relevant)


def fill_distinct(ranked, depth):
    """First ``depth`` distinct items of ``ranked`` in order (fewer when the list runs out)."""
    seen, out = set(), []
    for item in ranked:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
        if len(out) >= depth:
            break
    return out


def drop_item(ranked, item):
    """``ranked`` without ``item`` (BEIR ignores a query's own document, as ArguAna queries are in its corpus)."""
    return [doc for doc in ranked if doc != item]


# ---------------------------------------------------------------- fusion

def rrf_fusion(rankings, k=RRF_K):
    """Reciprocal Rank Fusion of several ranked id lists; ties broken by id for determinism."""
    scores = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return [doc for doc, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def minmax(scores):
    """Min-max normalise {doc: score} to [0, 1]. A constant (or single) list maps to 1.0 everywhere."""
    if not scores:
        return {}
    low, high = min(scores.values()), max(scores.values())
    if high == low:
        return {doc: 1.0 for doc in scores}
    return {doc: (score - low) / (high - low) for doc, score in scores.items()}


def convex_fusion(dense, sparse, alpha):
    """Rank by ``alpha * dense + (1 - alpha) * sparse`` after min-max normalising each channel.

    ``dense`` and ``sparse`` map doc -> raw score over each channel's candidates; a document
    missing from a channel scores 0 there. Ties are broken by id.
    """
    dense, sparse = minmax(dense), minmax(sparse)
    fused = {doc: alpha * dense.get(doc, 0.0) + (1 - alpha) * sparse.get(doc, 0.0) for doc in set(dense) | set(sparse)}
    return [doc for doc, _ in sorted(fused.items(), key=lambda item: (-item[1], item[0]))]


def choose_alpha(ndcg_by_alpha):
    """Alpha with the highest calibration nDCG@10; the smallest alpha wins a tie."""
    if not ndcg_by_alpha:
        raise ValueError("no alpha scores to choose from")
    best = max(ndcg_by_alpha.values())
    return min(alpha for alpha, value in ndcg_by_alpha.items() if value == best)


# ---------------------------------------------------------------- keyword evidence

def keyword_rule_passes(matched, n_terms, min_terms=1, share=KEYWORD_SHARE):
    """DocMind's keyword-evidence rule plus an optional absolute minimum.

    The app requires ``max(1, ceil(share * n_terms))`` matched terms. ``min_terms`` additionally
    requires ``min(min_terms, n_terms)`` matched terms, so a long question cannot pass on a
    single incidental word. ``min_terms=1`` is exactly the app's rule.
    """
    return matched >= max(1, math.ceil(n_terms * share)) and matched >= min(min_terms, n_terms)


def keyword_variant(hybrid, min_terms=2):
    """Copy of an app ``HybridRetriever`` whose keyword-evidence rule needs ``min_terms`` matches.

    The copy shares the BM25 index and vector retriever with ``hybrid`` (no re-tokenising); only
    ``_keyword_evidence`` is replaced, by a subclass defined here, so the app code is untouched.
    """
    from utils.llama_index.retrieval import HybridRetriever

    class _MinTerms(HybridRetriever):
        def _keyword_evidence(self, questions):
            from utils.llama_index.query import PHRASE_SYNONYMS, _stemmed_synonyms
            synonyms = _stemmed_synonyms()
            hits = set()
            for node_id, terms in zip(self.corpus, self._token_sets, strict=True):
                for content in questions:
                    matched = {term for term in content if term in terms or synonyms.get(term, set()) & terms}
                    for phrase, meaning in PHRASE_SYNONYMS.items():
                        if all(word in content for word in phrase) and terms.intersection(meaning):
                            matched.update(phrase)
                    if keyword_rule_passes(len(matched), len(content), self.min_terms):
                        hits.add(node_id)
                        break
            return hits

    variant = copy.copy(hybrid)
    variant.__class__ = _MinTerms
    variant.min_terms = min_terms
    return variant


# ---------------------------------------------------------------- plain baselines

def plain_tokens(text):
    """Lower-case alphanumeric tokens without stopwords (no stemming, no keyword-evidence rule)."""
    from utils.llama_index.query import _STOPWORDS
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS]


class PlainSignals:
    """Whole-document BM25 (Okapi) and dense candidate lists, each ``depth`` distinct documents."""

    def __init__(self, corpus, dense_retriever, depth=CANDIDATE_DEPTH):
        from rank_bm25 import BM25Okapi
        self.ids = list(corpus)
        self.depth = depth
        self.dense_retriever = dense_retriever
        self.bm25 = BM25Okapi([plain_tokens(corpus[doc_id]) or [""] for doc_id in self.ids])

    def sparse(self, query, exclude=None):
        """[(doc_id, score)] with score > 0, best first, up to depth."""
        tokens = plain_tokens(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], self.ids[i]))
        out = [(self.ids[i], float(scores[i])) for i in order[:self.depth + 1] if scores[i] > 0 and self.ids[i] != exclude]
        return out[:self.depth]

    def dense(self, query, exclude=None):
        """[(doc_id, best chunk similarity)], best first, up to depth distinct documents."""
        best = {}
        for node in self.dense_retriever.retrieve(query):
            doc_id = (node.node.metadata or {}).get("file_name", "").removesuffix(".txt")
            if not doc_id or doc_id == exclude:
                continue
            best[doc_id] = max(best.get(doc_id, float("-inf")), node.score or 0.0)
        ranked = sorted(best.items(), key=lambda item: (-item[1], item[0]))
        return ranked[:self.depth]


def plain_rankings(dense, sparse, alpha, k):
    """Top-k id lists for the plain baselines from candidate lists [(doc, score)].

    Returns (rankings, rrf_full): ``rrf_full`` is the whole fused list, used as the reranker's pool.
    """
    dense_ids, sparse_ids = [d for d, _ in dense], [d for d, _ in sparse]
    rrf_full = rrf_fusion([dense_ids, sparse_ids])
    return {"bm25_plain": fill_distinct(sparse_ids, k), "dense_plain": fill_distinct(dense_ids, k),
            "rrf_plain": rrf_full[:k],
            "convex": convex_fusion(dict(dense), dict(sparse), alpha)[:k]}, rrf_full


class CrossEncoderReranker:
    """Cross-encoder reranking of a candidate pool (sentence-transformers, loaded on first use)."""

    def __init__(self, name=CROSS_ENCODER, max_length=512):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(name, max_length=max_length)

    def rerank(self, query, candidates, corpus, top=RERANK_DEPTH):
        pool = candidates[:top]
        if not pool:
            return []
        scores = self.model.predict([(query, corpus[doc]) for doc in pool], batch_size=32, show_progress_bar=False)
        return [doc for doc, _ in sorted(zip(pool, scores, strict=True), key=lambda item: -item[1])]


# ---------------------------------------------------------------- nomic prefixes

def prefixed_embedding(wrapped, query_prefix=NOMIC_QUERY_PREFIX, document_prefix=NOMIC_DOCUMENT_PREFIX):
    """Embedding model that prepends task prefixes before delegating (queries and documents differ)."""
    from llama_index.core.embeddings import BaseEmbedding

    class PrefixedEmbedding(BaseEmbedding):
        wrapped_model: BaseEmbedding

        def _get_query_embedding(self, query):
            return self.wrapped_model.get_query_embedding(query_prefix + query)

        async def _aget_query_embedding(self, query):
            return self._get_query_embedding(query)

        def _get_text_embedding(self, text):
            return self.wrapped_model.get_text_embedding(document_prefix + text)

        def get_text_embedding_batch(self, texts, show_progress=False, **kwargs):
            return self.wrapped_model.get_text_embedding_batch(
                [document_prefix + text for text in texts], show_progress=False, **kwargs)

    return PrefixedEmbedding(wrapped_model=wrapped, model_name=wrapped.model_name,
                             embed_batch_size=wrapped.embed_batch_size)
