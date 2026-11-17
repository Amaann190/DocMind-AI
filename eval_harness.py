"""DocMind AI — Comprehensive Evaluation Harness
Covers the WHOLE project: ingestion, retrieval, generation, performance,
robustness, and architecture. Compares plain vector RAG vs DocMind hybrid.

Run:
  python eval_harness.py              # real embeddings + real LLM if Ollama running
  python eval_harness.py --mock       # no Ollama required (deterministic hash embeddings, mocked LLM)
  python eval_harness.py --suite retrieval  # run single suite
  python eval_harness.py --quick      # alias for --mock (fast smoke test)

Suites:
  ingestion   — file-type coverage, chunking, dedup, title-aware, cache, exclusions
  retrieval   — hit rate, synonyms, hyphen, Hinglish, title-aware, evidence floor, BM25
  generation  — no-hallucination fallback, citations, tone presets, multi-turn, e2e
  performance — ingestion speed, retrieval latency, eco-mode, cache hit
  robustness  — empty/binary handling, security validation, malformed inputs
  architecture— backend presets, settings persistence, export, R2R/embedding helpers
  benchmark   — labelled 20-document benchmark (run with --suite benchmark)
  public      — BEIR SciFact public benchmark (run with --suite public)

Code lives in the evaluation/ package; this file is the command-line entry point.

Outputs:
  eval_results.json — machine-readable (per-suite)
  eval_report.md    — human report ready for README / thesis appendix"""
import argparse

from evaluation.common import (  # noqa: F401  (re-exported for tests and tools)
    _check,
    _setup_hash_embeddings,
    _setup_runtime_state,
    _try_real_embeddings,
    summarize_results,
)
from evaluation.report import _write_outputs
from evaluation.runner import ALL_SUITES, OPTIONAL_SUITES, run_full_eval

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DocMind full-project eval harness")
    parser.add_argument("--endpoint", default="http://localhost:11434", help="Ollama endpoint")
    parser.add_argument("--model", default="nomic-embed-text:latest", help="Embedding model")
    parser.add_argument("--chat-model", default="llama3:latest", help="Exact installed Ollama chat model")
    parser.add_argument("--mock", action="store_true", help="Use hash embeddings + mocked LLM (no Ollama)")
    parser.add_argument("--quick", action="store_true", help="Alias for --mock")
    parser.add_argument("--suite", choices=ALL_SUITES + OPTIONAL_SUITES, help="Run only one suite")
    parser.add_argument("--out", default=".", help="Output directory")
    args = parser.parse_args()

    use_mock = args.mock or args.quick
    suites = [args.suite] if args.suite else None

    all_results, overall = run_full_eval(endpoint=args.endpoint, model=args.model, use_mock=use_mock, suites=suites, chat_model=args.chat_model)
    _write_outputs(all_results, overall, out_dir=args.out)
    raise SystemExit(1 if overall["failed"] else 0)

