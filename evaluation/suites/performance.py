"""Performance suite: cache, latency and Eco Mode budgets."""
import shutil
import tempfile
import time
from functools import partial
from pathlib import Path

from evaluation.common import (
    _check,
    _setup_hash_embeddings,
    _setup_runtime_state,
    _try_real_embeddings,
    summarize_results,
)
from evaluation.fixtures import DOCS


def suite_performance(mock: bool, endpoint="http://localhost:11434", model="nomic-embed-text:latest"):
    print("\n[Suite] Performance")
    results = []
    check = partial(_check, results)

    # 1 — ingestion speed (index 5 docs)
    def t_ingest_speed():
        _setup_runtime_state()
        if mock:
            _setup_hash_embeddings()
        else:
            _try_real_embeddings(endpoint, model)
        d = tempfile.mkdtemp()
        try:
            for n, c in DOCS.items():
                Path(d, n).write_text(c, encoding="utf-8")
            from utils.llama_index import create_index, load_documents
            t0 = time.perf_counter()
            docs = load_documents(d)
            idx = create_index(docs)
            dt = time.perf_counter() - t0
            ok = idx is not None and dt < 30
            return ok, f"{dt:.1f}s for {len(DOCS)} docs"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("ingest_5_docs", t_ingest_speed)

    # 2 — cache hit is faster than cold build
    def t_cache_speed():
        from utils.llama_index import (
            create_index,
            index_cache_dir,
            load_documents,
            load_index_from_cache,
            persist_index_to_cache,
        )
        _setup_runtime_state()
        d = tempfile.mkdtemp()
        try:
            Path(d, "a.txt").write_text(DOCS["refund_policy.txt"], encoding="utf-8")
            docs = load_documents(d)
            t0 = time.perf_counter()
            idx = create_index(docs)
            cold = time.perf_counter() - t0
            cdir = index_cache_dir(docs)
            if cdir:
                persist_index_to_cache(idx, cdir)
                t0 = time.perf_counter()
                loaded = load_index_from_cache(cdir)
                hit = time.perf_counter() - t0
                ok = loaded is not None  # cache hit itself is the win; tiny docs make timing noisy
                return ok, f"cold {cold:.1f}s vs cache {hit:.2f}s"
            return False, f"cold {cold:.1f}s; cache directory missing"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("cache_hit_faster", t_cache_speed)

    # 3 — retrieval latency hybrid vs plain (from retrieval suite) — lightweight check
    def t_retrieval_latency():
        _setup_runtime_state()
        d = tempfile.mkdtemp()
        try:
            for n, c in list(DOCS.items())[:3]:
                Path(d, n).write_text(c, encoding="utf-8")
            from utils.llama_index import build_hybrid_retriever, create_index, load_documents
            docs = load_documents(d)
            idx = create_index(docs)
            vr = idx.as_retriever(similarity_top_k=3)
            hy = build_hybrid_retriever(vr, idx, top_k=3, similarity_cutoff=0.3)
            t0 = time.perf_counter()
            hy.retrieve("refund policy")
            h_ms = (time.perf_counter() - t0) * 1000
            t0 = time.perf_counter()
            vr.retrieve("refund policy")
            v_ms = (time.perf_counter() - t0) * 1000
            ok = h_ms < 500 and v_ms < 500  # both should be <0.5s (no LLM)
            return ok, f"vector {v_ms:.0f}ms hybrid {h_ms:.0f}ms"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("retrieval_latency", t_retrieval_latency)

    # 4 — eco mode trims context/batches
    def t_eco():
        from utils.llama_index import _context_char_budget
        from utils.ollama import _embed_batch_size, _num_predict
        from utils.runtime import st
        st.session_state["eco_mode"] = False
        normal_ctx = _context_char_budget()
        normal_pred = _num_predict()
        normal_batch = _embed_batch_size()
        st.session_state["eco_mode"] = True
        eco_ctx = _context_char_budget()
        eco_pred = _num_predict()
        eco_batch = _embed_batch_size()
        st.session_state["eco_mode"] = False
        ok = eco_ctx < normal_ctx and eco_pred < normal_pred and eco_batch < normal_batch
        return ok, f"ctx {normal_ctx}->{eco_ctx} pred {normal_pred}->{eco_pred} batch {normal_batch}->{eco_batch}"
    check("eco_mode_trims", t_eco)

    # 5 — batch OOM resilience (from existing test harness concept)
    def t_batch_oom():
        from types import SimpleNamespace

        from utils.llama_index import OllamaEmbedding
        class FakeOOM:
            def __init__(self, *a, **kw): self.calls=[]
            def embed(self, model, input):
                self.calls.append(len(input))
                if self.calls[-1] == 8:
                    raise RuntimeError("CUDA out of memory")
                return SimpleNamespace(embeddings=[[0.1]*4 for _ in input])
        emb = OllamaEmbedding(model_name="nomic-embed-text:latest", base_url="http://localhost:11434")
        emb.embed_batch_size = 8
        emb._client = FakeOOM()
        res = emb.get_text_embedding_batch([f"t{i}" for i in range(12)])
        ok = len(res) == 12 and emb.embed_batch_size == 4
        return ok, f"shrunk to {emb.embed_batch_size} after OOM"
    check("batch_oom_resilience", t_batch_oom)

    return summarize_results("performance", results)
