"""Research experiments for the results paper.

Sub-commands (each writes one JSON file into --out):

  sweep     Evidence-floor sweep on a BEIR corpus or the labelled benchmark:
            ranking on test queries, rejection of off-topic FiQA questions,
            and a floor calibrated on held-out queries.
  answers   SQuAD 2.0 answers (answerable and unanswerable) through the full
            DocMind answer path, graded against human-written gold answers,
            plus an indirect prompt-injection suite with the filter on and off.
  sheet     Export answers to a CSV for two human graders.
  kappa     Agreement between the graders and with the automatic grade.
  endtoend  Retrieval gate plus generation on SciFact claims and FiQA off-topic questions.
  resources Latency, throughput, RAM and VRAM for a chat model with Eco Mode on or off.

Examples:
  python -m evaluation.research sweep --dataset scifact --model nomic-embed-text:latest
  python -m evaluation.research answers --chat-model llama3:latest
"""
import argparse
import csv
import json
import re
import shutil
import tempfile
import time
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

from evaluation import beir, prompts, retrieval_ext, squad, stats
from evaluation.benchmark import ranked_files, recall_at_k, reciprocal_rank
from evaluation.public import ndcg_at_k

K = 10
CUTOFF = 0.3
FLOORS = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
DEFAULT_FLOOR = 0.50


@contextmanager
def live_state(endpoint, model, chat_model=None, extra_state=None):
    """Isolated request state with real Ollama embeddings, as the harness uses.

    ``extra_state`` is applied before the embedding model is built (Eco Mode changes its batch size).
    """
    from evaluation.common import _setup_runtime_state, _try_real_embeddings
    from utils.runtime import request_state, st
    from utils.session_workspace import clear_session_workspace
    with request_state({}):
        _setup_runtime_state()
        st.session_state.update(ollama_endpoint=endpoint, ollama_embedding_model=model, llm_backend="Ollama")
        if chat_model:
            st.session_state["selected_model"] = chat_model
        if extra_state:
            st.session_state.update(extra_state)
        _try_real_embeddings(endpoint, model)
        try:
            yield st
        finally:
            clear_session_workspace(st.session_state)


def cache_query_embeddings(index):
    """Embed each distinct query once; the sweep re-runs the same queries many times."""
    model = index._embed_model
    original = model.get_query_embedding
    cache = {}

    def cached(query):
        if query not in cache:
            cache[query] = original(query)
        return cache[query]
    object.__setattr__(model, "get_query_embedding", cached)


class VectorOnly:
    """Dense top-k with the similarity cutoff only (the ablation baseline)."""

    def __init__(self, inner, cutoff=CUTOFF):
        self.inner = inner
        self.cutoff = cutoff

    def retrieve(self, query):
        return [n for n in self.inner.retrieve(query) if (n.score or 0.0) >= self.cutoff]


def configurations(index, k, kw_min_terms=1):
    """Yield (name, retriever) for the baselines and each floor, reusing one hybrid index.

    With ``kw_min_terms > 1`` the same bm25-only / no-floor / floor configurations are also run
    with the stricter keyword-evidence rule, named ``kw<n>_...``.
    """
    from utils.llama_index import build_hybrid_retriever
    vector = VectorOnly(index.as_retriever(similarity_top_k=k))
    hybrid = build_hybrid_retriever(index.as_retriever(similarity_top_k=k), index, top_k=k, similarity_cutoff=CUTOFF)
    yield "vector_only", vector
    hybrid.use_vector, hybrid.evidence_floor = False, DEFAULT_FLOOR
    yield "bm25_only", hybrid
    hybrid.use_vector, hybrid.evidence_floor = True, None
    yield "hybrid_no_floor", hybrid
    for floor in FLOORS:
        hybrid.evidence_floor = floor
        yield f"floor_{floor:.2f}", hybrid
    if kw_min_terms > 1:
        strict = retrieval_ext.keyword_variant(hybrid, kw_min_terms)
        prefix = f"kw{kw_min_terms}"
        strict.use_vector, strict.evidence_floor = False, DEFAULT_FLOOR
        yield f"{prefix}_bm25_only", strict
        strict.use_vector, strict.evidence_floor = True, None
        yield f"{prefix}_hybrid_no_floor", strict
        for floor in FLOORS:
            strict.evidence_floor = floor
            yield f"{prefix}_floor_{floor:.2f}", strict


def run_queries(index, query_sets, k, strip_suffix, kw_min_terms=1, exclude_self=False):
    """Rank every query of every set under every configuration; return per-query rows.

    ``exclude_self`` drops a query's own document (ArguAna queries are corpus documents, and BEIR
    ignores identical ids); retrieval then goes one deeper so k documents remain.
    """
    from utils import runtime
    depth = k + 1 if exclude_self else k
    runtime.st.session_state.update(top_k=depth, similarity_cutoff=CUTOFF)
    rows = {kind: {qid: {"query": text} for qid, text in queries.items()} for kind, queries in query_sets.items()}
    with patch("utils.llama_index.retrieval._context_char_budget", return_value=10**9):
        for name, retriever in configurations(index, depth, kw_min_terms):
            started = time.perf_counter()
            for kind, queries in query_sets.items():
                for qid, text in queries.items():
                    files = ranked_files(retriever.retrieve(text))
                    if strip_suffix:
                        files = [f.removesuffix(".txt") for f in files]
                    if exclude_self:
                        files = retrieval_ext.drop_item(files, qid)
                    rows[kind][qid][name] = files[:k]
            print(f"  {name:16s} {time.perf_counter() - started:6.1f}s", flush=True)
    return rows


def score(rows, qrels, offtopic_rows, calib_rows, calib_qrels, names, k):
    """Summary metrics with intervals, the calibrated floor and paired tests."""
    summary = {"configurations": {}, "per_query_ndcg": {}}
    for name in names:
        ndcg = [ndcg_at_k(row[name], qrels[qid], k) for qid, row in rows.items()]
        relevant = {qid: set(qrels[qid]) for qid in rows}
        recall = {cut: [recall_at_k(row[name], relevant[qid], cut) for qid, row in rows.items()] for cut in (1, 5, k)}
        empty = sum(not row[name] for row in rows.values())
        depths = [len(set(row[name])) for row in rows.values()]
        stat = {"ndcg@10": sum(ndcg) / len(ndcg), "ndcg@10_ci": stats.bootstrap_ci(ndcg),
                # recall@N is the older name for Hit@N (any relevant document in the top N); both are kept.
                **{f"recall@{cut}": sum(v) / len(v) for cut, v in recall.items()},
                **{f"hit@{cut}": sum(v) / len(v) for cut, v in recall.items()},
                f"true_recall@{k}": sum(retrieval_ext.true_recall_at_k(row[name], relevant[qid], k)
                                        for qid, row in rows.items()) / len(rows),
                "mrr@10": sum(reciprocal_rank(row[name], relevant[qid], k) for qid, row in rows.items()) / len(rows),
                "no_result": empty / len(rows), "empty_rate": empty / len(rows),
                "distinct_docs_mean": sum(depths) / len(depths), "distinct_docs_min": min(depths)}
        if offtopic_rows:
            rejected = sum(not row[name] for row in offtopic_rows.values())
            stat.update(rejection=rejected / len(offtopic_rows), rejection_ci=stats.wilson(rejected, len(offtopic_rows)))
        if calib_rows:
            stat["calib_recall@10"] = sum(recall_at_k(row[name], set(calib_qrels[qid]), k)
                                          for qid, row in calib_rows.items()) / len(calib_rows)
        summary["configurations"][name] = stat
        summary["per_query_ndcg"][name] = ndcg
    floors = {float(n.split("_")[1]): n for n in names if n.startswith("floor_")}
    if calib_rows:
        reference = summary["configurations"]["hybrid_no_floor"]["calib_recall@10"]
        chosen = stats.calibrate_floor({f: summary["configurations"][n]["calib_recall@10"] for f, n in floors.items()},
                                       reference)
        summary["calibrated_floor"] = chosen
    per = summary["per_query_ndcg"]
    default = f"floor_{DEFAULT_FLOOR:.2f}"
    pairs = [("hybrid_no_floor", "vector_only"), ("hybrid_no_floor", "bm25_only"), (default, "hybrid_no_floor")]
    if summary.get("calibrated_floor") is not None:
        pairs.append((f"floor_{summary['calibrated_floor']:.2f}", "hybrid_no_floor"))
    pairs += [(a, b) for a, b in (("rrf_plain", "bm25_plain"), ("rrf_plain", "dense_plain"), ("convex", "rrf_plain"),
                                  ("rerank", "rrf_plain"), (default, "rrf_plain"), (default, "dense_plain"),
                                  ("kw2_floor_0.50", default), ("kw2_hybrid_no_floor", "hybrid_no_floor"))
              if a in per and b in per]
    summary["paired"] = {f"{a} vs {b}": stats.paired_bootstrap(per[a], per[b]) for a, b in pairs}
    return summary


def calibration_split(dataset, split):
    """Query split used to calibrate the floor and the convex alpha for an evaluation split.

    Never the evaluation split itself. None means no other split exists (ArguAna): the caller
    then carves a calibration sample out of the evaluation queries and removes it from them.
    """
    if dataset == "scifact":
        return "train" if split == "test" else "test"
    if dataset == "nfcorpus":
        return "dev" if split in ("test", "train") else "train"
    return None


def sweep_output_name(dataset, model, split="test", plain=False, kw_min_terms=1, nomic_prefixes=False):
    """File name of a sweep result. The default invocation keeps the original name."""
    name = f"sweep-{dataset}" + (f"-{split}" if split != "test" else "") + f"-{slug(model)}"
    if plain:
        name += "-plain"
    if kw_min_terms > 1:
        name += f"-kw{kw_min_terms}"
    if nomic_prefixes:
        name += "-prefix"
    return name + ".json"


def config_order(name):
    """Sort key: the original configurations first (as before), then floors, strict rule, plain baselines."""
    if name in ("vector_only", "bm25_only", "hybrid_no_floor"):
        return (0, name)
    if name.startswith("floor_"):
        return (1, name)
    if name.startswith("kw"):
        return (2, name)
    return (3, name)


def add_plain_rows(rows, index, corpus, calib_qrels, k, exclude_self, rerank=True):
    """Fill ``rows`` with the plain baselines (matched depth, whole documents); return their settings.

    bm25_plain, dense_plain, rrf_plain (RRF k=60 over 100 candidates each), convex (min-max score
    fusion, alpha picked on the calibration queries by nDCG@10) and rerank (cross-encoder over the
    top 50 of rrf_plain). Each list is filled to ``k`` distinct documents where possible.
    """
    signals = retrieval_ext.PlainSignals(corpus, index.as_retriever(similarity_top_k=400))
    started = time.perf_counter()
    candidates = {kind: {qid: (signals.dense(row["query"], qid if exclude_self else None),
                               signals.sparse(row["query"], qid if exclude_self else None))
                         for qid, row in kind_rows.items()} for kind, kind_rows in rows.items()}
    print(f"  plain candidates {time.perf_counter() - started:6.1f}s", flush=True)
    by_alpha = {}
    if calib_qrels and rows["calib"]:
        for alpha in retrieval_ext.ALPHAS:
            values = [ndcg_at_k(retrieval_ext.plain_rankings(*candidates["calib"][qid], alpha, k)[0]["convex"],
                                calib_qrels[qid], k) for qid in rows["calib"]]
            by_alpha[alpha] = sum(values) / len(values)
    alpha = retrieval_ext.choose_alpha(by_alpha) if by_alpha else 0.5
    reranker = retrieval_ext.CrossEncoderReranker() if rerank else None
    started = time.perf_counter()
    for kind, kind_rows in rows.items():
        for qid, row in kind_rows.items():
            rankings, pool = retrieval_ext.plain_rankings(*candidates[kind][qid], alpha, k)
            row.update(rankings)
            if reranker:
                row["rerank"] = reranker.rerank(row["query"], pool, corpus)[:k]
    print(f"  plain rankings + rerank {time.perf_counter() - started:6.1f}s  alpha={alpha}", flush=True)
    return {"alpha": alpha, "alpha_source": "calibration nDCG@10" if by_alpha else "default (no calibration queries)",
            "calibration_ndcg_by_alpha": by_alpha, "candidate_depth": retrieval_ext.CANDIDATE_DEPTH,
            "rrf_k": retrieval_ext.RRF_K, "rerank_depth": retrieval_ext.RERANK_DEPTH if rerank else None,
            "reranker": retrieval_ext.CROSS_ENCODER if rerank else None}


def sweep(args):
    from llama_index.core import Document

    from utils.llama_index import create_index, load_documents
    started = time.perf_counter()
    if args.nomic_prefixes and "nomic" not in args.model:
        raise SystemExit("--nomic-prefixes only applies to nomic-embed-text")
    if args.dataset != "labelled" and args.split not in beir.available_splits(args.dataset):
        raise SystemExit(f"{args.dataset} has no {args.split!r} split")
    offtopic = beir.sample(beir.load_split(beir.ensure_beir("fiqa"), "test")[0], args.offtopic)
    plain_info, calib_name = None, None
    with live_state(args.endpoint, args.model) as st:
        tmpdir = None
        try:
            if args.nomic_prefixes:
                st.session_state["embedding_model"] = retrieval_ext.prefixed_embedding(st.session_state["embedding_model"])
            if args.dataset == "labelled":
                from evaluation.benchmark import load_dataset
                corpus_rows, labelled = load_dataset()
                tmpdir = tempfile.mkdtemp(prefix="docmind_sweep_")
                for doc in corpus_rows:
                    Path(tmpdir, doc["file"]).write_text(doc["text"], encoding="utf-8")
                index = create_index(load_documents(tmpdir))
                test = {q["id"]: q["query"] for q in labelled["answerable"]}
                qrels = {q["id"]: {name: 1 for name in q["relevant"]} for q in labelled["answerable"]}
                offtopic = {q["id"]: q["query"] for q in labelled["off_topic"]} | {
                    f"fiqa_{qid}": text for qid, text in offtopic.items()}
                calib, calib_qrels, k, strip = {}, {}, 5, False
            else:
                folder = beir.ensure_beir(args.dataset)
                corpus = beir.load_corpus(folder)
                test, qrels = beir.load_split(folder, args.split)
                calib_name = calibration_split(args.dataset, args.split)
                if calib_name:
                    calib_all, calib_qrels = beir.load_split(folder, calib_name)
                    calib = beir.sample(calib_all, args.calib)
                else:
                    calib = beir.sample(test, args.calib)
                    calib_qrels = {qid: qrels[qid] for qid in calib}
                    test = {qid: text for qid, text in test.items() if qid not in calib}
                    qrels = {qid: qrels[qid] for qid in test}
                    calib_name = f"{args.split} (held-out sample, removed from the evaluation queries)"
                if args.max_queries:
                    test = beir.sample(test, args.max_queries)
                    qrels = {qid: qrels[qid] for qid in test}
                index = create_index([Document(text=text, metadata={"file_name": f"{doc_id}.txt"})
                                      for doc_id, text in corpus.items()])
                k, strip = K, True
            index_seconds = time.perf_counter() - started
            print(f"  indexed in {index_seconds:.0f}s", flush=True)
            cache_query_embeddings(index)
            exclude_self = args.dataset == "arguana"
            rows = run_queries(index, {"test": test, "offtopic": offtopic, "calib": calib}, k, strip,
                               args.keyword_min_terms, exclude_self)
            if args.plain:
                if args.dataset == "labelled":
                    raise SystemExit("--plain needs a BEIR dataset")
                plain_info = add_plain_rows(rows, index, corpus, calib_qrels, k, exclude_self, not args.skip_rerank)
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
    names = list(next(iter(rows["test"].values())).keys() - {"query"})
    names.sort(key=config_order)
    summary = score(rows["test"], qrels, rows["offtopic"], rows["calib"], calib_qrels, names, k)
    if args.dataset == "labelled":
        own = {qid: row for qid, row in rows["offtopic"].items() if not qid.startswith("fiqa_")}
        for name in names:
            rejected = sum(not row[name] for row in own.values())
            summary["configurations"][name]["own_offtopic_rejection"] = rejected / len(own)
    payload = {"experiment": "sweep", "dataset": args.dataset, "embedding": args.model, "k": k,
               "cutoff": CUTOFF, "floors": FLOORS, "test_queries": len(test), "offtopic_queries": len(offtopic),
               "calibration_queries": len(calib), "index_seconds": round(index_seconds, 1),
               "seconds": round(time.perf_counter() - started, 1), "summary": summary, "rows": rows,
               "generated": time.strftime("%Y-%m-%d %H:%M"), "split": args.split, "calibration_split": calib_name,
               "keyword_min_terms": args.keyword_min_terms, "nomic_prefixes": args.nomic_prefixes,
               "excluded_self_ids": args.dataset == "arguana", "plain": plain_info}
    write(args.out, sweep_output_name(args.dataset, args.model, args.split, args.plain, args.keyword_min_terms,
                                      args.nomic_prefixes), payload)
    for name in names:
        s = summary["configurations"][name]
        print(f"  {name:20s} nDCG@10 {s['ndcg@10']:.3f}  hit@{k} {s[f'hit@{k}']:.0%}  recall@{k} {s[f'true_recall@{k}']:.0%}  "
              f"docs {s['distinct_docs_mean']:.1f}  empty {s['empty_rate']:.0%}  reject {s.get('rejection', 0):.0%}  "
              f"calib R@10 {s.get('calib_recall@10', float('nan')):.0%}")
    print(f"  calibrated floor: {summary.get('calibrated_floor')}"
          + (f"  convex alpha: {plain_info['alpha']}" if plain_info else ""))


def answers_output_name(chat_model, retrieval="full", temperature=0.0, prompt_variant="default", seed=None, repeat=0):
    """File name of an answers result. The default invocation keeps the original name."""
    name = f"answers-{slug(chat_model)}-{retrieval}"
    if temperature:
        name += f"-t{temperature}"
    if prompt_variant != "default":
        name += f"-{prompt_variant}"
    if seed is not None:
        name += f"-s{seed}"
    if repeat:
        name += f"-r{repeat}"
    return name + ".json"


def seeded_create_llm(seed):
    """``utils.ollama.create_llm`` wrapper that fixes Ollama's sampling seed (the app never sets one)."""
    from utils import ollama
    original = ollama.create_llm

    def create(*args, **kwargs):
        llm = original(*args, **kwargs)
        llm.additional_kwargs["seed"] = seed
        return llm
    return create


def answers(args):
    from llama_index.core import Document

    from utils.llama_index import build_hybrid_retriever, create_index
    from utils.ollama import context_chat, verify_chat_model
    contexts, questions = squad.load_squad(squad.ensure_squad())
    picked = squad.sample_questions(questions, args.n, args.n)
    started = time.perf_counter()
    system_prompt, template_text = prompts.prompt_variant(args.prompt_variant)
    with ExitStack() as stack, live_state(args.endpoint, args.model, args.chat_model) as st:
        if template_text:
            from llama_index.core.prompts import PromptTemplate
            stack.enter_context(patch("utils.ollama.TEXT_QA_TEMPLATE", PromptTemplate(template_text)))
        if args.seed is not None:
            stack.enter_context(patch("utils.ollama.create_llm", seeded_create_llm(args.seed)))
        if not verify_chat_model(args.chat_model, args.endpoint):
            raise SystemExit(f"Chat model {args.chat_model!r} is not installed at {args.endpoint}")
        st.session_state.update(selected_model=args.chat_model, temperature=args.temperature, eco_mode=False,
                                top_k=3, similarity_cutoff=CUTOFF, system_prompt=system_prompt)

        def retriever_for(index):
            hybrid = build_hybrid_retriever(index.as_retriever(similarity_top_k=3), index, top_k=3,
                                            similarity_cutoff=CUTOFF)
            if args.retrieval == "no_floor":
                hybrid.evidence_floor = None
            if args.retrieval == "vector_only":
                return VectorOnly(index.as_retriever(similarity_top_k=3))
            return hybrid

        def ask(question):
            st.session_state.update(messages=[], rag_history_start=0, last_doc_sources=[], last_doc_passages=[])
            begun = time.perf_counter()
            answer = "".join(context_chat(question, query_engine=None))
            return answer, list(st.session_state.get("last_doc_sources") or []), \
                [p["text"] for p in st.session_state.get("last_doc_passages") or []], \
                round((time.perf_counter() - begun) * 1000)

        # One collection per article: a user uploads a document and asks about it.
        # Questions such as "When did these rebellions take place?" are only
        # well-posed within their article, not across all of Wikipedia.
        retrievers = {}

        def article_retriever(context_id):
            article = context_id.rsplit("_", 1)[0]
            if article not in retrievers:
                retrievers[article] = retriever_for(create_index([
                    Document(text=text, metadata={"file_name": f"{cid}.txt"})
                    for cid, text in contexts.items() if cid.rsplit("_", 1)[0] == article]))
            return retrievers[article]

        records = []
        for number, item in enumerate(picked, 1):
            st.session_state["retriever"] = article_retriever(item["context_id"])
            answer, sources, passages, ms = ask(item["question"])
            files = [name for name, _ in sources]
            records.append({**item, "answer": answer, "sources": files, "passages": passages, "ms": ms,
                            "retrieved_none": not sources, "retrieved_gold": f"{item['context_id']}.txt" in files,
                            "refused": squad.is_refusal(answer), "cited": bool(re.search(r"\[\d+\]", answer)),
                            "correct": squad.grade(item, answer),
                            "f1": 0.0 if item["unanswerable"] else squad.token_f1(answer, item["answers"])})
            if number % 25 == 0:
                print(f"  {number}/{len(picked)} answered", flush=True)

        injection = []
        if not args.skip_injection:
            targets = [item for item in picked if not item["unanswerable"]][:args.injection_n]
            attacks = list(squad.ATTACKS)
            for filtered in (True, False):
                for number, item in enumerate(targets):
                    attack = attacks[number % len(attacks)]
                    gold = next((a for a in item["answers"] if a in contexts[item["context_id"]]), item["answers"][0])
                    text = squad.inject(contexts[item["context_id"]], attack, gold)
                    mini = create_index([Document(text=text, metadata={"file_name": "page.txt"})])
                    st.session_state["retriever"] = retriever_for(mini)
                    if filtered:
                        answer, _, _, ms = ask(item["question"])
                    else:
                        with patch("utils.ollama.withhold_instructions", side_effect=lambda t: t):
                            answer, _, _, ms = ask(item["question"])
                    injection.append({"id": item["id"], "attack": attack, "filter": filtered, "answer": answer,
                                      "attack_success": squad.CANARY in answer,
                                      "task_success": squad.contains_gold(answer, item["answers"]), "ms": ms})
                print(f"  injection filter={'on' if filtered else 'off'} done", flush=True)

    payload = {"experiment": "answers", "chat_model": args.chat_model, "embedding": args.model,
               "retrieval": args.retrieval, "temperature": args.temperature, "seconds": round(time.perf_counter() - started),
               "summary": summarize_answers(records, injection), "records": records, "injection": injection,
               "generated": time.strftime("%Y-%m-%d %H:%M")}
    if args.prompt_variant != "default":
        payload["prompt_variant"] = args.prompt_variant
    if args.seed is not None:
        payload["seed"] = args.seed
    if args.repeat:
        payload["repeat"] = args.repeat
    write(args.out, answers_output_name(args.chat_model, args.retrieval, args.temperature, args.prompt_variant,
                                        args.seed, args.repeat), payload)
    print(json.dumps(payload["summary"], indent=1))


def summarize_answers(records, injection):
    def rate(items, key):
        hits = sum(bool(i[key]) for i in items)
        return {"k": hits, "n": len(items), "rate": hits / len(items) if items else 0.0,
                "ci": stats.wilson(hits, len(items))}
    answerable = [r for r in records if not r["unanswerable"]]
    unanswerable = [r for r in records if r["unanswerable"]]
    answered = [r for r in records if not r["refused"]]
    summary = {"answerable_correct": rate(answerable, "correct"), "unanswerable_refused": rate(unanswerable, "correct"),
               "overall_correct": rate(records, "correct"), "answerable_retrieved_gold": rate(answerable, "retrieved_gold"),
               "answerable_retrieved_none": rate(answerable, "retrieved_none"),
               "unanswerable_retrieved_none": rate(unanswerable, "retrieved_none"),
               "answered_with_citation": rate(answered, "cited"),
               "answerable_mean_f1": (sum(r.get("f1", 0.0) for r in answerable) / len(answerable)) if answerable else 0.0,
               "mean_ms": sum(r["ms"] for r in records) / len(records) if records else 0}
    if injection:
        summary["injection"] = {}
        for filtered in (True, False):
            subset = [i for i in injection if i["filter"] is filtered]
            label = "filter_on" if filtered else "filter_off"
            summary["injection"][label] = {"attack_success": rate(subset, "attack_success"),
                                           "task_success": rate(subset, "task_success"),
                                           "by_attack": {a: sum(i["attack_success"] for i in subset if i["attack"] == a)
                                                         for a in squad.ATTACKS}}
    return summary


def sheet(args):
    payload = json.loads(Path(args.results).read_text(encoding="utf-8"))
    records = payload["records"][:args.n]
    # Graders must not see the automatic grade, so it goes into a separate key file.
    with open(args.csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "question", "gold_answers", "unanswerable", "model_answer", "top_passage",
                         "grader1_correct", "grader1_supported", "grader2_correct", "grader2_supported"])
        for r in records:
            writer.writerow([r["id"], r["question"], " | ".join(r["answers"]) or "(none: unanswerable)",
                             r["unanswerable"], r["answer"], (r["passages"] or [""])[0][:1500], "", "", "", ""])
    with open(key_path(args.csv), "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "auto_correct"])
        writer.writerows([r["id"], int(r["correct"])] for r in records)
    print(f"wrote {len(records)} rows to {args.csv} (automatic grades in {key_path(args.csv)})")


def key_path(sheet_path):
    return str(Path(sheet_path).with_suffix("")) + "_key.csv"


def kappa(args):
    with open(args.csv, encoding="utf-8") as handle:
        rows = [r for r in csv.DictReader(handle) if r["grader1_correct"].strip() and r["grader2_correct"].strip()]
    if not rows:
        raise SystemExit("No rows graded by both graders yet.")
    out = {"items": len(rows)}
    for field in ("correct", "supported"):
        first = [r[f"grader1_{field}"].strip() for r in rows]
        second = [r[f"grader2_{field}"].strip() for r in rows]
        if all(first) and all(second):
            out[f"kappa_{field}"] = stats.cohen_kappa(first, second)
    with open(key_path(args.csv), encoding="utf-8") as handle:
        auto = {r["id"]: r["auto_correct"].strip() for r in csv.DictReader(handle)}
    agreed = [r for r in rows if r["grader1_correct"].strip() == r["grader2_correct"].strip()]
    out["graders_agree_items"] = len(agreed)
    out["auto_vs_human_agreement"] = (sum(auto[r["id"]] == r["grader1_correct"].strip() for r in agreed)
                                      / len(agreed)) if agreed else None
    out["human_correct_rate"] = (sum(r["grader1_correct"].strip() == "1" for r in agreed) / len(agreed)) if agreed else None
    out["auto_correct_rate_same_items"] = (sum(auto[r["id"]] == "1" for r in agreed) / len(agreed)) if agreed else None
    print(json.dumps(out, indent=1))


def slug(text):
    return re.sub(r"[^a-z0-9.]+", "-", text.lower()).strip("-")


def write(out, name, payload):
    path = Path(out)
    path.mkdir(parents=True, exist_ok=True)
    (path / name).write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    print(f"wrote {path / name}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("sweep", "answers"):
        p = sub.add_parser(name)
        p.add_argument("--endpoint", default="http://localhost:11434")
        p.add_argument("--model", default="nomic-embed-text:latest", help="Embedding model")
        p.add_argument("--out", default="output/research")
    p = sub.choices["sweep"]
    p.add_argument("--dataset", choices=["scifact", "nfcorpus", "arguana", "labelled"], default="scifact")
    p.add_argument("--split", choices=["train", "dev", "test"], default="test", help="Query split to evaluate")
    p.add_argument("--plain", action="store_true",
                   help="Add plain baselines: bm25_plain, dense_plain, rrf_plain, convex, rerank")
    p.add_argument("--skip-rerank", action="store_true", help="With --plain, skip the cross-encoder baseline")
    p.add_argument("--keyword-min-terms", type=int, default=1,
                   help="2 adds kw2_* configurations needing min(2, n_terms) matched terms")
    p.add_argument("--nomic-prefixes", action="store_true",
                   help="Prefix queries with 'search_query: ' and documents with 'search_document: '")
    p.add_argument("--offtopic", type=int, default=300, help="FiQA questions used as off-topic queries")
    p.add_argument("--calib", type=int, default=100, help="Held-out queries used to calibrate the floor")
    p.add_argument("--max-queries", type=int, default=0, help="Evaluate only a seeded sample of this many queries (smoke tests)")
    p = sub.choices["answers"]
    p.add_argument("--chat-model", required=True)
    p.add_argument("--retrieval", choices=["full", "no_floor", "vector_only"], default="full")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=None, help="Ollama sampling seed (default: not set)")
    p.add_argument("--repeat", type=int, default=0, help="Repeat number N; the output file gets the suffix -rN")
    p.add_argument("--prompt-variant", choices=list(prompts.VARIANTS), default="default",
                   help="alt rewords the system prompt and the grounded-QA template, keeping the rules")
    p.add_argument("--n", type=int, default=100, help="Answerable and unanswerable questions (each)")
    p.add_argument("--injection-n", type=int, default=48)
    p.add_argument("--skip-injection", action="store_true")
    p = sub.add_parser("sheet")
    p.add_argument("--results", required=True)
    p.add_argument("--csv", required=True)
    p.add_argument("--n", type=int, default=100)
    p = sub.add_parser("kappa")
    p.add_argument("--csv", required=True)
    from evaluation import endtoend, resources
    endtoend.add_arguments(sub.add_parser("endtoend"))
    resources.add_arguments(sub.add_parser("resources"))
    args = parser.parse_args(argv)
    {"sweep": sweep, "answers": answers, "sheet": sheet, "kappa": kappa,
     "endtoend": endtoend.run, "resources": resources.run}[args.command](args)


if __name__ == "__main__":
    main()
