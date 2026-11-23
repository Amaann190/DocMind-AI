"""End-to-end gate experiment: does the evidence floor save model calls without hurting answers?

100 answerable SciFact test claims and 100 off-topic FiQA questions go through the full DocMind
answer path (retrieval gate, then generation) under three gate settings: the default floor
0.50, the calibrated floor 0.60 and no floor. Per item: retrieved passages (``retrieved``, in
citation order, and ``retrieved_docs``, the distinct documents), whether retrieval returned
nothing (so the model was never called), the answer, whether it refused, whether it cites a
relevant document (SciFact claims, via qrels) and latency.
"""
import re
import time
from contextlib import ExitStack
from unittest.mock import patch

from evaluation import beir, squad, stats

GATES = (("floor_0.50", 0.50), ("floor_0.60", 0.60), ("no_floor", None))
FALLBACK = squad.FALLBACK


def add_arguments(p):
    p.add_argument("--endpoint", default="http://localhost:11434")
    p.add_argument("--model", default="nomic-embed-text:latest", help="Embedding model")
    p.add_argument("--out", default="output/research")
    p.add_argument("--chat-model", required=True)
    p.add_argument("--n-claims", type=int, default=100, help="Answerable SciFact test claims")
    p.add_argument("--n-offtopic", type=int, default=100, help="Off-topic FiQA questions")
    p.add_argument("--sample-seed", type=int, default=13)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=None, help="Ollama sampling seed (default: not set)")


def is_refused(answer):
    """The model (or the retrieval gate) said the documents do not contain the answer."""
    return squad.is_refusal(answer) or squad.normalize_answer(FALLBACK) in squad.normalize_answer(answer)


def cited_documents(answer, source_files):
    """Documents the answer cites: ``[n]`` marks (also inside "(from [n])") mapped to the numbered sources."""
    cited = []
    for number in dict.fromkeys(int(n) for n in re.findall(r"\[(\d+)\]", answer)):
        if 1 <= number <= len(source_files) and source_files[number - 1] not in cited:
            cited.append(source_files[number - 1])
    return cited


def cites_relevant(answer, source_files, relevant):
    return any(doc in relevant for doc in cited_documents(answer, source_files))


def gate_label(floor):
    return "no_floor" if floor is None else f"floor_{floor:.2f}"


def summarize_gate(records):
    """Gate-level numbers from per-item records (see ``run``)."""
    def rate(items, key):
        hits = sum(bool(i[key]) for i in items)
        return {"k": hits, "n": len(items), "rate": hits / len(items) if items else 0.0,
                "ci": stats.wilson(hits, len(items))}

    def mean_ms(items):
        return sum(i["ms"] for i in items) / len(items) if items else 0.0
    claims = [r for r in records if r["kind"] == "scifact"]
    offtopic = [r for r in records if r["kind"] == "fiqa"]
    answered = [r for r in claims if not r["refused"]]
    for r in claims:
        r["supported"] = (not r["refused"]) and bool(r["cites_relevant"])
    return {"appropriate_refusals_fiqa": rate(offtopic, "refused"),
            "unnecessary_refusals_scifact": rate(claims, "refused"),
            "supported_answers_scifact": rate(claims, "supported"),
            "scifact_answered_cites_relevant": {"k": sum(bool(r["cites_relevant"]) for r in answered), "n": len(answered)},
            "retrieved_relevant_scifact": rate(claims, "retrieved_relevant"),
            "model_calls_avoided_all": rate(records, "retrieved_none"),
            "model_calls_avoided_fiqa": rate(offtopic, "retrieved_none"),
            "model_calls_avoided_scifact": rate(claims, "retrieved_none"),
            "mean_ms_all": mean_ms(records), "mean_ms_scifact": mean_ms(claims), "mean_ms_fiqa": mean_ms(offtopic),
            "errors": sum(bool(r.get("error")) for r in records)}


def run(args):
    from llama_index.core import Document

    from evaluation import research
    from utils.llama_index import build_hybrid_retriever, create_index
    from utils.ollama import context_chat, verify_chat_model
    started = time.perf_counter()
    claims, qrels = beir.load_split(beir.ensure_beir("scifact"), "test")
    claims = beir.sample(claims, args.n_claims, args.sample_seed)
    fiqa = beir.sample(beir.load_split(beir.ensure_beir("fiqa"), "test")[0], args.n_offtopic, args.sample_seed)
    corpus = beir.load_corpus(beir.ensure_beir("scifact"))
    items = ([{"kind": "scifact", "id": qid, "query": text, "relevant": sorted(qrels[qid])} for qid, text in claims.items()]
             + [{"kind": "fiqa", "id": f"fiqa_{qid}", "query": text, "relevant": []} for qid, text in fiqa.items()])
    results = {}
    with ExitStack() as stack, research.live_state(args.endpoint, args.model, args.chat_model) as st:
        if args.seed is not None:
            stack.enter_context(patch("utils.ollama.create_llm", research.seeded_create_llm(args.seed)))
        if not verify_chat_model(args.chat_model, args.endpoint):
            raise SystemExit(f"Chat model {args.chat_model!r} is not installed at {args.endpoint}")
        st.session_state.update(selected_model=args.chat_model, temperature=args.temperature, eco_mode=False,
                                top_k=3, similarity_cutoff=research.CUTOFF,
                                system_prompt="Answer briefly and cite the supplied document passages.")
        index = create_index([Document(text=text, metadata={"file_name": f"{doc_id}.txt"})
                              for doc_id, text in corpus.items()])
        index_seconds = time.perf_counter() - started
        print(f"  indexed in {index_seconds:.0f}s", flush=True)
        hybrid = build_hybrid_retriever(index.as_retriever(similarity_top_k=3), index, top_k=3,
                                        similarity_cutoff=research.CUTOFF)
        st.session_state["retriever"] = hybrid
        for label, floor in GATES:
            hybrid.evidence_floor = floor
            records = []
            for number, item in enumerate(items, 1):
                st.session_state.update(messages=[], rag_history_start=0, last_doc_sources=[], last_doc_passages=[])
                begun = time.perf_counter()
                answer = "".join(context_chat(item["query"], query_engine=None))
                ms = round((time.perf_counter() - begun) * 1000)
                files = [name.removesuffix(".txt") for name, _ in st.session_state.get("last_doc_sources") or []]
                records.append({**item, "retrieved": files, "retrieved_docs": list(dict.fromkeys(files)), "retrieved_none": not files, "model_called": bool(files),
                                "answer": answer, "refused": is_refused(answer),
                                "error": answer.lstrip().startswith("⚠"),
                                "cited": cited_documents(answer, files),
                                "cites_relevant": cites_relevant(answer, files, set(item["relevant"]))
                                if item["kind"] == "scifact" else None,
                                "retrieved_relevant": bool(set(files) & set(item["relevant"])), "ms": ms})
                if number % 50 == 0:
                    print(f"  {label}: {number}/{len(items)}", flush=True)
            results[label] = {"floor": floor, "summary": summarize_gate(records), "records": records}
            s = results[label]["summary"]
            print(f"  {label:11s} FiQA refused {s['appropriate_refusals_fiqa']['rate']:.0%}  SciFact refused "
                  f"{s['unnecessary_refusals_scifact']['rate']:.0%}  supported {s['supported_answers_scifact']['rate']:.0%}  "
                  f"calls avoided {s['model_calls_avoided_all']['rate']:.0%}  {s['mean_ms_all']:.0f} ms", flush=True)
    payload = {"experiment": "endtoend", "chat_model": args.chat_model, "embedding": args.model, "temperature": args.temperature,
               "claims": len(claims), "offtopic": len(fiqa), "sample_seed": args.sample_seed, "index_seconds": round(index_seconds, 1),
               "seconds": round(time.perf_counter() - started), "gates": results,
               "generated": time.strftime("%Y-%m-%d %H:%M")}
    if args.seed is not None:
        payload["seed"] = args.seed
    research.write(args.out, endtoend_output_name(args.chat_model, args.temperature, args.seed), payload)


def endtoend_output_name(chat_model, temperature=0.0, seed=None):
    from evaluation.research import slug
    return f"endtoend-{slug(chat_model)}" + (f"-t{temperature}" if temperature else "") + (f"-s{seed}" if seed is not None else "") + ".json"
