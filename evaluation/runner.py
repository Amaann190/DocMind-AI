"""Run selected suites with isolated request state and summarize the results."""
from evaluation.common import _setup_hash_embeddings, _setup_runtime_state, _try_real_embeddings, summarize_results
from evaluation.suites.architecture import suite_architecture
from evaluation.suites.benchmark import suite_benchmark
from evaluation.suites.generation import suite_generation
from evaluation.suites.ingestion import suite_ingestion
from evaluation.suites.performance import suite_performance
from evaluation.suites.retrieval import suite_retrieval
from evaluation.suites.robustness import suite_robustness

ALL_SUITES = ["ingestion", "retrieval", "generation", "performance", "robustness", "architecture"]


# Run on request only (--suite benchmark): slower, and it reports metrics rather than pass/fail checks.
OPTIONAL_SUITES = ["benchmark"]


def run_full_eval(*args, **kwargs):
    from utils.runtime import request_state
    with request_state({}):
        return _run_full_eval(*args, **kwargs)


def _run_full_eval(endpoint="http://localhost:11434", model="nomic-embed-text:latest",
                  use_mock=False, suites=None, chat_model="llama3:latest"):
    from utils.runtime import st
    from utils.session_workspace import clear_session_workspace

    saved_state = dict(st.session_state)
    st.session_state.clear()
    _setup_runtime_state()
    st.session_state.update(ollama_endpoint=endpoint, ollama_embedding_model=model,
                            selected_model=chat_model)
    target = suites or ALL_SUITES
    suite_fns = {
        "ingestion": lambda: suite_ingestion(use_mock),
        "retrieval": lambda: suite_retrieval(use_mock, endpoint, model),
        "generation": lambda: suite_generation(use_mock, endpoint, model, chat_model),
        "performance": lambda: suite_performance(use_mock, endpoint, model),
        "robustness": lambda: suite_robustness(use_mock),
        "architecture": lambda: suite_architecture(use_mock),
        "benchmark": lambda: suite_benchmark(use_mock, endpoint, model),
    }
    all_results = {}
    try:
        for name in target:
            try:
                if name in {"ingestion", "retrieval", "performance", "benchmark"}:
                    if use_mock:
                        _setup_hash_embeddings()
                    else:
                        _try_real_embeddings(endpoint, model)
                all_results[name] = suite_fns[name]()
            except Exception as error:
                all_results[name] = summarize_results(name, [{
                    "test": "suite_execution", "pass": False, "status": "failed",
                    "detail": f"{type(error).__name__}: {error}"}])
    finally:
        clear_session_workspace(st.session_state)
        st.session_state.clear()
        st.session_state.update(saved_state)

    passed = sum(r["passed"] for r in all_results.values())
    failed = sum(r["failed"] for r in all_results.values())
    skipped = sum(r["skipped"] for r in all_results.values())
    executed = passed + failed
    overall = {"passed": passed, "failed": failed, "skipped": skipped,
               "executed": executed, "total": executed + skipped,
               "overall_score": round(passed / executed, 3) if executed else None,
               "suites": list(target), "mode": "mock" if use_mock else "live",
               "embedding_model": "hash-mock" if use_mock else model,
               # Only the generation suite calls a chat model; do not attribute others to one.
               "chat_model": None if use_mock or "generation" not in target else chat_model,
               "endpoint": endpoint}
    answers = [item for result in all_results.values() for item in result["results"]
               if item.get("kind") == "live_answer"]
    overall["answer_checks"] = {
        "passed": sum(item["pass"] is True for item in answers),
        "failed": sum(item["pass"] is False for item in answers),
        "skipped": sum(item["pass"] is None for item in answers),
    }
    print(f"\nResult: {passed} passed, {failed} failed, {skipped} skipped")
    return all_results, overall
