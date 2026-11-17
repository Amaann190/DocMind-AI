"""Ingestion suite: file types, exclusions, chunking, dedup, titles, cache."""
import csv
import os
import shutil
import tempfile
from functools import partial
from pathlib import Path

from evaluation.common import _check, _setup_hash_embeddings, summarize_results
from evaluation.fixtures import DOCS


def suite_ingestion(mock: bool):
    """Ingestion pipeline: file types, exclusions, chunking, dedup, title, cache."""
    print("\n[Suite] Ingestion")
    from utils.runtime import st
    if st.session_state.get("embedding_model") is None:
        if mock:
            _setup_hash_embeddings()
        else:
            raise RuntimeError("Real embedding setup is required for live ingestion checks")
    results = []
    check = partial(_check, results)

    # 1 — load_documents filters excluded patterns
    def t_excluded():
        from utils.llama_index import EXCLUDED_FILE_PATTERNS, load_documents
        d = tempfile.mkdtemp()
        try:
            Path(d, "keep.txt").write_text("hello world content for testing keep file", encoding="utf-8")
            Path(d, "ignore.png").write_bytes(b"\x89PNG")
            Path(d, "ignore.zip").write_bytes(b"PK")
            docs = load_documents(d)
            texts = " ".join(getattr(doc, "text", "") or "" for doc in docs)
            ok = "hello world" in texts and len(docs) == 1
            return ok, f"loaded={len(docs)} patterns={len(EXCLUDED_FILE_PATTERNS)}"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("excluded_patterns", t_excluded)

    # 2 — title-aware
    def t_title():
        from llama_index.core.schema import TextNode

        from utils.llama_index import _document_title, _prepend_document_title
        n = TextNode(text="body content here", metadata={"file_name": "annual_report.md"})
        title = _document_title(n)
        _prepend_document_title([n])
        ok = title == "Annual Report" and n.get_content().startswith("Annual Report.")
        return ok, f"title='{title}'"
    check("title_aware", t_title)

    # 3 — dedup
    def t_dedup():
        from llama_index.core.schema import Document

        from utils.llama_index import _dedupe_exact_nodes
        chunks = [
            Document(text="Welcome to our annual report. The company grew a lot this year."),
            Document(text="Welcome to our annual report. The company grew a lot this year!"),
            Document(text="Revenues increased by 12 percent."),
        ]
        deduped = _dedupe_exact_nodes(chunks + [chunks[0]])
        return deduped == chunks, f"{len(chunks) + 1} -> {len(deduped)} (distinct evidence preserved)"
    check("dedupe", t_dedup)

    # 4 — chunking + index creation (file-type coverage: txt, md, csv, docx)
    def t_index_multiformat():
        from utils.llama_index import create_index, load_documents
        d = tempfile.mkdtemp()
        try:
            Path(d, "a.txt").write_text(DOCS["refund_policy.txt"], encoding="utf-8")
            Path(d, "b.md").write_text("# Annual Report\n" + DOCS["annual_report.txt"], encoding="utf-8")
            # csv
            with open(os.path.join(d, "c.csv"), "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["topic", "detail"])
                w.writerow(["leave", "20 days annual"])
                w.writerow(["refund", "30 days"])
            import docx
            doc = docx.Document()
            doc.add_paragraph(DOCS["python_guide.txt"])
            doc.save(os.path.join(d, "d.docx"))
            docs = load_documents(d)
            index = create_index(docs)
            # check that we got docs from multiple extensions
            found = {Path(doc.metadata["file_name"]).suffix for doc in docs}
            ok = found == {".txt", ".md", ".csv", ".docx"} and index is not None
            return ok, f"loaded formats={sorted(found)}"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("multiformat_index", t_index_multiformat)

    # 5 — cache: same docs produce same cache key and hit on second build
    def t_cache():
        from utils.llama_index import (
            create_index,
            index_cache_dir,
            index_cache_key,
            load_documents,
            load_index_from_cache,
            persist_index_to_cache,
        )
        d = tempfile.mkdtemp()
        try:
            for name, content in list(DOCS.items())[:2]:
                Path(d, name).write_text(content, encoding="utf-8")
            docs = load_documents(d)
            k1 = index_cache_key(docs)
            k2 = index_cache_key(docs)
            ok = k1 == k2 and len(k1) == 20
            # try persist/load round-trip (best effort)
            try:
                idx = create_index(docs)
                cdir = index_cache_dir(docs)
                if cdir:
                    persist_index_to_cache(idx, cdir)
                    loaded = load_index_from_cache(cdir)
                    ok = ok and (loaded is not None)
                    detail = f"key={k1} persist={'hit' if loaded else 'miss'}"
                else:
                    ok, detail = False, "No cache directory was created"
            except Exception as e:
                ok, detail = False, f"Cache round-trip failed: {e}"
            return ok, detail
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("cache_key_and_persist", t_cache)

    # 6 — short facts survive indexing
    def t_min_chars():
        from utils.llama_index import MIN_CHUNK_CHARS, create_index, load_documents
        d = tempfile.mkdtemp()
        try:
            Path(d, "tiny.txt").write_text("hi", encoding="utf-8")
            Path(d, "ok.txt").write_text("This is a sufficiently long document content for chunking tests. " * 5, encoding="utf-8")
            docs = load_documents(d)
            try:
                idx = create_index(docs)
                found = any(node.metadata.get("file_name") == "tiny.txt" for node in idx.docstore.docs.values())
                return found, f"MIN_CHARS={MIN_CHUNK_CHARS} tiny_indexed={found}"
            except Exception as e:
                return False, str(e)[:60]
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("min_chunk_filter", t_min_chars)

    # 7 — website / github helpers (input validation)
    def t_helpers():
        from utils.helpers import normalize_github_repo
        try:
            ok1 = normalize_github_repo("owner/repo") == "owner/repo"
            ok2 = normalize_github_repo("https://github.com/owner/repo") == "owner/repo"
            ok3 = False
            try:
                normalize_github_repo("https://gitlab.com/owner/repo")
            except Exception:
                ok3 = True
            return (ok1 and ok2 and ok3), f"owner/repo={ok1} url={ok2} reject_gitlab={ok3}"
        except Exception as e:
            return False, str(e)
    check("helpers_github_normalize", t_helpers)

    return summarize_results("ingestion", results)
