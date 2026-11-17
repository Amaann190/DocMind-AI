"""Shared evaluation helpers: request state, embeddings, indexes and result records."""
import hashlib
import time
from pathlib import Path
from unittest import SkipTest

from evaluation.fixtures import DOCS


def _setup_runtime_state():
    try:
        from utils.runtime import st
        defaults = {
            "top_k": 3,
            "similarity_cutoff": 0.3,
            "eco_mode": False,
            "chunk_size": 256,
            "chunk_overlap": 32,
            "chunk_overlap_pct": 12,
            "temperature": 0.4,
            "advanced": False,
            "llm_backend": "Ollama",
            "ollama_endpoint": "http://localhost:11434",
            "ollama_embedding_model": "nomic-embed-text:latest",
            "selected_model": "qwen2.5:0.5b",
            "system_prompt": "You are DocMind AI.",
            "messages": [],
            "retriever": None,
            "query_engine": None,
            "last_doc_sources": [],
            "last_rag_no_result": False,
        }
        for k, v in defaults.items():
            st.session_state.setdefault(k, v)
    except RuntimeError:  # no request state yet; suites set up their own
        return


def _try_real_embeddings(endpoint, model):
    from utils.llama_index import setup_embedding_model
    try:
        setup_embedding_model(
            model=model, chunk_size=256, chunk_overlap=32,
            backend="Ollama", ollama_endpoint=endpoint,
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Real embeddings unavailable: {e}. Use --mock explicitly for offline checks.") from e


def _setup_hash_embeddings():
    from llama_index.core.embeddings import BaseEmbedding

    from utils.llama_index import _bm25_tokens
    from utils.runtime import st

    class HashEmbedding(BaseEmbedding):
        model_name: str = "hash-mock"
        def _get_text_embedding(self, text: str):
            vec = [0.0] * 64
            for tok in _bm25_tokens(text):
                h = int.from_bytes(hashlib.sha256(tok.encode("utf-8")).digest()[:8], "big") % 64
                vec[h] += 1.0
            norm = sum(x * x for x in vec) ** 0.5 or 1.0
            return [x / norm for x in vec]
        def _get_query_embedding(self, query: str):
            return self._get_text_embedding(query)
        async def _aget_query_embedding(self, query: str):
            return self._get_query_embedding(query)

    st.session_state["embedding_model"] = HashEmbedding()
    st.session_state["embedding_config"] = {"model": "hash-mock", "backend": "test", "endpoint": "offline", "chunk_size": 256, "chunk_overlap": 32}
    print("  Using deterministic hash embeddings (no Ollama).")


def _create_index_from_docs(tmpdir: str):
    from utils.llama_index import create_index, load_documents
    for name, content in DOCS.items():
        Path(tmpdir, name).write_text(content, encoding="utf-8")
    docs = load_documents(tmpdir)
    return create_index(docs)


def _evaluate_retriever(retriever, query: str, expected: str | None):
    t0 = time.perf_counter()
    try:
        nodes = retriever.retrieve(query)
    except Exception as e:
        return {"error": str(e), "hit": False, "latency": time.perf_counter() - t0, "top_file": None, "top_score": 0.0, "num_nodes": 0}
    latency = time.perf_counter() - t0
    if expected is None:
        hit = len(nodes) == 0
        top_file = nodes[0].node.metadata.get("file_name") if nodes else None
        top_score = nodes[0].score if nodes else 0.0
    else:
        files = [(n.node.metadata.get("file_name") or "") for n in nodes]
        hit = any(r == expected for r in files)
        top_file = files[0] if files else None
        top_score = nodes[0].score if nodes else 0.0
    return {"hit": hit, "latency": latency, "top_file": top_file, "top_score": round(float(top_score), 3) if nodes else 0.0, "num_nodes": len(nodes)}


def _check(results, name, fn):
    started = time.perf_counter()
    try:
        ok, detail = fn()
        status = "passed" if ok else "failed"
    except SkipTest as error:
        ok, detail, status = None, str(error), "skipped"
    except Exception as error:
        ok, detail, status = False, f"{type(error).__name__}: {error}", "failed"
    elapsed = round((time.perf_counter() - started) * 1000)
    print(f"  {status.upper():7s} {name:32s} {detail} ({elapsed}ms)")
    results.append({"test": name, "pass": ok, "status": status, "detail": detail, "ms": elapsed})


def summarize_results(name, results, **extra):
    passed = sum(item.get("pass") is True for item in results)
    skipped = sum(item.get("pass") is None for item in results)
    failed = len(results) - passed - skipped
    executed = passed + failed
    return {"suite": name, "results": results, "passed": passed, "failed": failed,
            "skipped": skipped, "total": len(results), "executed": executed,
            "score": round(passed / executed, 3) if executed else None, **extra}
