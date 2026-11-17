"""Robustness suite: malformed input and tokenization edge cases."""
import shutil
import tempfile
from functools import partial
from pathlib import Path

from evaluation.common import _check, summarize_results


def suite_robustness(mock: bool):
    print("\n[Suite] Robustness & Security")
    results = []
    check = partial(_check, results)

    def t_github_validation():
        from utils.helpers import normalize_github_repo
        cases = [
            ("owner/repo", True),
            ("https://github.com/owner/repo", True),
            ("https://gitlab.com/owner/repo", False),
            ("https://github.com/owner/repo/extra/path", False),
            ("", False),
        ]
        oks = []
        for inp, should_pass in cases:
            try:
                normalize_github_repo(inp)
                passed = should_pass
            except Exception:
                passed = not should_pass
            oks.append(passed)
        return all(oks), f"{sum(oks)}/{len(oks)} cases"
    check("github_validation", t_github_validation)

    def t_url_validation():
        from unittest.mock import patch

        from utils.helpers import validate_website_urls
        try:
            # URL validation is a deterministic control check, not a live fetch.
            with patch("utils.helpers.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]):
                validate_website_urls(["https://docs.python.org/3/"])
            ok1 = True
        except Exception:
            ok1 = False
        try:
            validate_website_urls(["not a url"])
            ok2 = False
        except Exception:
            ok2 = True
        try:
            validate_website_urls(["javascript:alert(1)"])
            ok3 = False
        except Exception:
            ok3 = True
        return (ok1 and ok2 and ok3), f"mock DNS: https={ok1} bad={ok2} xss={ok3}"
    check("url_validation", t_url_validation)

    def t_empty_docs():
        from utils.llama_index import create_index, load_documents
        d = tempfile.mkdtemp()
        try:
            Path(d, "empty.txt").write_text("", encoding="utf-8")
            try:
                docs = load_documents(d)
                create_index(docs)
                return False, "should have raised for no usable content"
            except ValueError as e:
                return ("No usable" in str(e) or "No files could be loaded" in str(e)), str(e)[:80]
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("empty_docs_rejected", t_empty_docs)

    def t_binary_exclusion():
        from utils.llama_index import load_documents
        d = tempfile.mkdtemp()
        try:
            Path(d, "a.txt").write_text("real content " * 20, encoding="utf-8")
            Path(d, "b.png").write_bytes(b"\x89PNG" + b"\x00" * 100)
            docs = load_documents(d)
            ok = len(docs) == 1
            return ok, f"loaded {len(docs)} (png excluded)"
        finally:
            shutil.rmtree(d, ignore_errors=True)
    check("binary_exclusion", t_binary_exclusion)

    def t_special_chars():
        from utils.llama_index import _bm25_tokens
        toks = _bm25_tokens("30-day money-back (refund)!!!")
        ok = "30" in toks and "day" in toks and "money" in toks
        return ok, f"tokens={toks[:5]}"
    check("special_chars_tokenization", t_special_chars)

    def t_hinglish_filter():
        from utils.llama_index import _rewrite_query
        q = _rewrite_query("batao refund policy kya hai please")
        ok = "refund" in q and "batao" not in q and "kya" not in q
        return ok, f"rewritten='{q}'"
    check("hinglish_filler_filter", t_hinglish_filter)

    return summarize_results("robustness", results)
