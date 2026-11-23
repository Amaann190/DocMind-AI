"""Resource use of the answer path for one chat model with Eco Mode on or off.

50 SQuAD questions (25 answerable, 25 unanswerable) run through DocMind's answer path, one
collection per article as in the answers experiment. Per question: retrieval and generation
latency and Ollama's own token counts and durations. Over the whole run: peak RAM of this python
process and of the Ollama processes (psutil), peak VRAM (nvidia-smi, sampled every 0.5 s) and the
time to build the SQuAD collections. Eco Mode is toggled the way the app does it, through the
``eco_mode`` session setting, before the embedding model and indexes are built.
"""
import json
import os
import statistics
import subprocess
import threading
import time
import urllib.request
from unittest.mock import patch

from evaluation import squad

SAMPLE_SECONDS = 0.5


def add_arguments(p):
    p.add_argument("--endpoint", default="http://localhost:11434")
    p.add_argument("--model", default="nomic-embed-text:latest", help="Embedding model")
    p.add_argument("--out", default="output/research")
    p.add_argument("--chat-model", required=True)
    p.add_argument("--eco", choices=["on", "off"], required=True, help="Eco Mode setting")
    p.add_argument("--n", type=int, default=50, help="SQuAD questions (half answerable, half unanswerable)")
    p.add_argument("--temperature", type=float, default=0.0)


# ---------------------------------------------------------------- sampling

def is_ollama_process(name, exe):
    """The Ollama server and its model runners (``llama-server.exe`` lives under the Ollama install)."""
    return "ollama" in (name or "").lower() or "ollama" in (exe or "").lower()


def ollama_ram_mb():
    """Resident memory of all Ollama processes in MiB (server, tray app and model runners)."""
    import psutil
    total = 0
    for proc in psutil.process_iter(["name", "exe", "memory_info"]):
        try:
            if is_ollama_process(proc.info["name"], proc.info["exe"]) and proc.info["memory_info"]:
                total += proc.info["memory_info"].rss
        except psutil.Error:
            continue
    return total / 2**20


def python_ram_mb():
    import psutil
    return psutil.Process(os.getpid()).memory_info().rss / 2**20


def vram_mb():
    """GPU memory in use (MiB, summed over GPUs) from nvidia-smi, or None when unavailable."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5, check=True).stdout
        return float(sum(int(line) for line in out.split() if line.strip().isdigit()))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


class PeakMonitor:
    """Samples named gauges on a background thread and keeps each one's peak (and its first sample)."""

    def __init__(self, gauges, interval=SAMPLE_SECONDS):
        self.gauges, self.interval = gauges, interval
        self.peaks = dict.fromkeys(gauges)
        self.first = dict.fromkeys(gauges)
        self.samples = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def sample(self):
        for name, gauge in self.gauges.items():
            try:
                value = gauge()
            except Exception:  # noqa: BLE001 - a failed sample must not stop the experiment
                value = None
            if value is None:
                continue
            if self.first[name] is None:
                self.first[name] = value
            self.peaks[name] = value if self.peaks[name] is None else max(self.peaks[name], value)
        self.samples += 1

    def _loop(self):
        while not self._stop.is_set():
            self.sample()
            self._stop.wait(self.interval)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self.sample()


def unload_models(endpoint, models):
    """Ask Ollama to drop the models from memory so each run starts cold (best effort)."""
    for model in models:
        body = json.dumps({"model": model, "keep_alive": 0}).encode()
        request = urllib.request.Request(endpoint.rstrip("/") + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(request, timeout=30).read()  # noqa: S310 - local Ollama endpoint
        except OSError:
            pass
    time.sleep(2)


# ---------------------------------------------------------------- pure helpers

def ollama_stats(raw):
    """Token counts and durations (ms) from the final streamed chunk of an Ollama chat response."""
    if raw is None:
        return None
    get = raw.get if hasattr(raw, "get") else (lambda key, default=None: getattr(raw, key, default))
    count, duration = get("eval_count"), get("eval_duration")
    if count is None or duration is None:
        return None
    return {"eval_count": int(count), "eval_ms": duration / 1e6,
            "prompt_tokens": int(get("prompt_eval_count") or 0), "prompt_ms": (get("prompt_eval_duration") or 0) / 1e6,
            "load_ms": (get("load_duration") or 0) / 1e6}


def tokens_per_second(eval_count, eval_ms):
    return eval_count / (eval_ms / 1000) if eval_ms else 0.0


def summarize_resources(records):
    """Latency percentiles-by-stage, token throughput and correctness over per-question records."""
    def mean(key, items=records):
        values = [r[key] for r in items if r.get(key) is not None]
        return sum(values) / len(values) if values else 0.0
    generated = [r for r in records if r.get("eval_count")]
    tokens, eval_ms = sum(r["eval_count"] for r in generated), sum(r["eval_ms"] for r in generated)
    answerable = [r for r in records if not r["unanswerable"]]
    unanswerable = [r for r in records if r["unanswerable"]]
    return {"questions": len(records), "model_called": len(generated),
            "mean_retrieval_ms": mean("retrieval_ms"), "mean_generation_ms": mean("generation_ms"),
            "mean_total_ms": mean("total_ms"),
            "median_total_ms": statistics.median(r["total_ms"] for r in records) if records else 0.0,
            "mean_ttft_ms": mean("ttft_ms", generated),
            "tokens_generated": tokens, "tokens_per_second": tokens_per_second(tokens, eval_ms),
            "mean_tokens_per_second_per_answer": (sum(tokens_per_second(r["eval_count"], r["eval_ms"]) for r in generated)
                                                  / len(generated)) if generated else 0.0,
            "mean_prompt_tokens": mean("prompt_tokens", generated),
            "correct": sum(bool(r["correct"]) for r in records), "accuracy": mean_bool(records, "correct"),
            "answerable_accuracy": mean_bool(answerable, "correct"),
            "unanswerable_refused": mean_bool(unanswerable, "correct")}


def mean_bool(items, key):
    return sum(bool(i[key]) for i in items) / len(items) if items else 0.0


def resources_output_name(chat_model, eco):
    from evaluation.research import slug
    return f"resources-{slug(chat_model)}-eco-{eco}.json"


# ---------------------------------------------------------------- experiment

class TimedRetriever:
    """Wraps a retriever and accumulates the time spent retrieving."""

    def __init__(self, inner):
        self.inner, self.elapsed = inner, 0.0

    def retrieve(self, query):
        begun = time.perf_counter()
        try:
            return self.inner.retrieve(query)
        finally:
            self.elapsed += time.perf_counter() - begun


def run(args):
    from llama_index.core import Document

    from evaluation import research
    from utils.llama_index import build_hybrid_retriever, create_index
    from utils.ollama import context_chat, verify_chat_model
    from utils import ollama as app_ollama
    contexts, questions = squad.load_squad(squad.ensure_squad())
    half = args.n // 2
    picked = squad.sample_questions(questions, half, args.n - half)
    eco = args.eco == "on"
    captured = {}
    original_create = app_ollama.create_llm

    def timed_create(*a, **kw):
        llm = original_create(*a, **kw)
        stream_chat = llm.stream_chat

        def timed_stream(messages, **kwargs):
            begun, first = time.perf_counter(), None
            last_raw = None
            for chunk in stream_chat(messages, **kwargs):
                if first is None and (chunk.delta or ""):
                    first = time.perf_counter() - begun
                last_raw = chunk.raw if chunk.raw is not None else last_raw
                yield chunk
            captured.update(generation=time.perf_counter() - begun, ttft=first, stats=ollama_stats(last_raw))
        object.__setattr__(llm, "stream_chat", timed_stream)
        return llm

    unload_models(args.endpoint, [args.chat_model, args.model])
    baseline_vram = vram_mb()
    monitor = PeakMonitor({"python_ram_mb": python_ram_mb, "ollama_ram_mb": ollama_ram_mb, "vram_mb": vram_mb})
    started = time.perf_counter()
    records, build_seconds, chunks = [], 0.0, 0
    with monitor, research.live_state(args.endpoint, args.model, args.chat_model, {"eco_mode": eco}) as st, \
            patch("utils.ollama.create_llm", timed_create):
        if not verify_chat_model(args.chat_model, args.endpoint):
            raise SystemExit(f"Chat model {args.chat_model!r} is not installed at {args.endpoint}")
        st.session_state.update(selected_model=args.chat_model, temperature=args.temperature, eco_mode=eco, top_k=3,
                                similarity_cutoff=research.CUTOFF,
                                system_prompt="Answer briefly and cite the supplied document passages.")
        retrievers = {}
        for item in picked:  # build every collection first so index time is measured on its own
            article = item["context_id"].rsplit("_", 1)[0]
            if article in retrievers:
                continue
            begun = time.perf_counter()
            index = create_index([Document(text=text, metadata={"file_name": f"{cid}.txt"})
                                  for cid, text in contexts.items() if cid.rsplit("_", 1)[0] == article])
            build_seconds += time.perf_counter() - begun
            chunks += len(index.docstore.docs)
            retrievers[article] = TimedRetriever(build_hybrid_retriever(
                index.as_retriever(similarity_top_k=3), index, top_k=3, similarity_cutoff=research.CUTOFF))
        print(f"  indexed {len(retrievers)} collections ({chunks} chunks) in {build_seconds:.1f}s", flush=True)
        for number, item in enumerate(picked, 1):
            retriever = retrievers[item["context_id"].rsplit("_", 1)[0]]
            retriever.elapsed = 0.0
            captured.clear()
            st.session_state.update(retriever=retriever, messages=[], rag_history_start=0, last_doc_sources=[],
                                    last_doc_passages=[])
            begun = time.perf_counter()
            answer = "".join(context_chat(item["question"], query_engine=None))
            total = time.perf_counter() - begun
            token_stats = captured.get("stats") or {}
            records.append({"id": item["id"], "unanswerable": item["unanswerable"], "answer": answer,
                            "correct": squad.grade(item, answer), "retrieved_none": not st.session_state.get("last_doc_sources"),
                            "retrieval_ms": retriever.elapsed * 1000, "generation_ms": captured.get("generation", 0.0) * 1000,
                            "ttft_ms": None if captured.get("ttft") is None else captured["ttft"] * 1000,
                            "total_ms": total * 1000, **token_stats})
            if number % 10 == 0:
                print(f"  {number}/{len(picked)}", flush=True)
    summary = summarize_resources(records)
    summary.update(eco_mode=eco, index_build_seconds=build_seconds, index_chunks=chunks, collections=len(retrievers),
                   peak_ram_python_mb=monitor.peaks["python_ram_mb"], peak_ram_ollama_mb=monitor.peaks["ollama_ram_mb"],
                   peak_vram_mb=monitor.peaks["vram_mb"], vram_baseline_mb=baseline_vram,
                   model_load_ms=max((r.get("load_ms", 0.0) for r in records), default=0.0), monitor_samples=monitor.samples)
    payload = {"experiment": "resources", "chat_model": args.chat_model, "embedding": args.model, "eco": args.eco,
               "temperature": args.temperature, "seconds": round(time.perf_counter() - started),
               "summary": summary, "records": records, "generated": time.strftime("%Y-%m-%d %H:%M")}
    research.write(args.out, resources_output_name(args.chat_model, args.eco), payload)
    print(json.dumps(summary, indent=1, default=str))
