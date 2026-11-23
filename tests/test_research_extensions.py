"""Helpers added for the extended research experiments (offline: no Ollama, no downloads)."""
import json
import tempfile
import time
import unittest
import unittest.mock
from pathlib import Path
from types import SimpleNamespace

from evaluation import beir, endtoend, overnight, prompts, research, resources, retrieval_ext, squad


class MetricTests(unittest.TestCase):
    def test_hit_and_true_recall_differ(self):
        ranked = ["a", "x", "b", "y"]
        relevant = {"a", "b", "c", "d"}
        self.assertEqual(retrieval_ext.hit_at_k(ranked, relevant, 10), 1.0)
        self.assertEqual(retrieval_ext.hit_at_k(ranked, relevant, 1), 1.0)
        self.assertEqual(retrieval_ext.hit_at_k(["x"], relevant, 10), 0.0)
        self.assertEqual(retrieval_ext.true_recall_at_k(ranked, relevant, 10), 0.5)
        self.assertEqual(retrieval_ext.true_recall_at_k(ranked, relevant, 1), 0.25)
        self.assertEqual(retrieval_ext.true_recall_at_k([], relevant, 10), 0.0)
        self.assertEqual(retrieval_ext.true_recall_at_k(ranked, set(), 10), 0.0)

    def test_fill_distinct_depth(self):
        self.assertEqual(retrieval_ext.fill_distinct(["a", "a", "b", "a", "c", "d"], 3), ["a", "b", "c"])
        self.assertEqual(retrieval_ext.fill_distinct(["a", "a"], 10), ["a"])  # fewer than asked: "where possible"
        self.assertEqual(retrieval_ext.fill_distinct([], 5), [])
        self.assertEqual(retrieval_ext.drop_item(["q", "a", "b"], "q"), ["a", "b"])

    def test_score_records_new_metrics(self):
        names = ["vector_only", "bm25_only", "hybrid_no_floor", "floor_0.50"]
        rows = {"q1": dict.fromkeys(names, ["d1", "d1x"]), "q2": {name: [] for name in names}}
        summary = research.score(rows, {"q1": {"d1": 1, "d2": 1}, "q2": {"d3": 1}}, {}, {}, {}, names, 10)
        stat = summary["configurations"]["hybrid_no_floor"]
        self.assertEqual(stat["hit@10"], 0.5)
        self.assertEqual(stat["recall@10"], 0.5)  # the old key is kept with the old (hit) meaning
        self.assertEqual(stat["true_recall@10"], 0.25)
        self.assertEqual(stat["distinct_docs_mean"], 1.0)
        self.assertEqual(stat["distinct_docs_min"], 0)
        self.assertEqual(stat["empty_rate"], 0.5)


class FusionTests(unittest.TestCase):
    def test_minmax_normalisation(self):
        self.assertEqual(retrieval_ext.minmax({"a": 2.0, "b": 4.0, "c": 6.0}), {"a": 0.0, "b": 0.5, "c": 1.0})
        self.assertEqual(retrieval_ext.minmax({"a": 3.0}), {"a": 1.0})
        self.assertEqual(retrieval_ext.minmax({"a": 3.0, "b": 3.0}), {"a": 1.0, "b": 1.0})
        self.assertEqual(retrieval_ext.minmax({}), {})

    def test_convex_fusion_uses_normalised_scores(self):
        dense = {"a": 0.9, "b": 0.5}          # cosine scale
        sparse = {"b": 30.0, "c": 10.0}       # BM25 scale: raw sums would let BM25 dominate
        self.assertEqual(retrieval_ext.convex_fusion(dense, sparse, 1.0)[:2], ["a", "b"])
        self.assertEqual(retrieval_ext.convex_fusion(dense, sparse, 0.0)[0], "b")
        # alpha 0.5: a = 0.5, b = 0.5 * 0 + 0.5 * 1, c = 0 -> tie a/b broken by id
        self.assertEqual(retrieval_ext.convex_fusion(dense, sparse, 0.5), ["a", "b", "c"])
        self.assertEqual(retrieval_ext.convex_fusion({}, {}, 0.5), [])

    def test_rrf_matches_app_formula(self):
        fused = retrieval_ext.rrf_fusion([["a", "b"], ["b", "c"]])
        self.assertEqual(fused, ["b", "a", "c"])  # b: 1/61 + 1/60 beats a: 1/60

    def test_choose_alpha(self):
        self.assertEqual(retrieval_ext.choose_alpha({0.0: 0.30, 0.5: 0.45, 1.0: 0.40}), 0.5)
        self.assertEqual(retrieval_ext.choose_alpha({0.2: 0.4, 0.6: 0.4}), 0.2)  # tie: smaller alpha
        with self.assertRaises(ValueError):
            retrieval_ext.choose_alpha({})

    def test_plain_rankings_filled_to_depth(self):
        dense = [(f"d{i}", 1 - i / 100) for i in range(20)]
        sparse = [(f"s{i}", 10 - i) for i in range(5)]
        rankings, pool = retrieval_ext.plain_rankings(dense, sparse, 0.5, 10)
        self.assertEqual(len(rankings["dense_plain"]), 10)
        self.assertEqual(len(rankings["bm25_plain"]), 5)  # only five documents match: not padded
        self.assertEqual(len(rankings["rrf_plain"]), 10)
        self.assertEqual(len(rankings["convex"]), 10)
        self.assertEqual(len(pool), 25)

    def test_plain_tokens_drop_stopwords_without_stemming(self):
        self.assertEqual(retrieval_ext.plain_tokens("The Cats are running, in 2024!"), ["cats", "running", "2024"])


class KeywordRuleTests(unittest.TestCase):
    def test_min_terms_rule(self):
        rule = retrieval_ext.keyword_rule_passes
        # default (min_terms=1) is DocMind's own rule: ceil(half of the terms), at least one
        self.assertTrue(rule(1, 2))
        self.assertFalse(rule(1, 4))
        self.assertTrue(rule(2, 4))
        # min_terms=2 additionally needs min(2, n_terms) matches
        self.assertFalse(rule(1, 2, 2))
        self.assertTrue(rule(2, 2, 2))
        self.assertTrue(rule(1, 1, 2))     # a one-term question can only ever match one term
        self.assertFalse(rule(0, 1, 2))
        self.assertFalse(rule(2, 6, 2))    # half-of-terms rule still applies
        self.assertTrue(rule(3, 6, 2))

    def test_variant_matches_app_when_min_terms_is_one_and_is_stricter_at_two(self):
        from utils.llama_index.retrieval import HybridRetriever
        texts = {"n1": "alpha only here", "n2": "alpha beta together", "n3": "nothing relevant"}
        docstore = SimpleNamespace(get_node=lambda node_id: SimpleNamespace(
            get_content=lambda: texts[node_id], metadata={}))
        hybrid = HybridRetriever(None, docstore, list(texts), top_k=3)
        questions = [["alpha", "beta"]]
        self.assertEqual(hybrid._keyword_evidence(questions), {"n1", "n2"})
        self.assertEqual(retrieval_ext.keyword_variant(hybrid, 1)._keyword_evidence(questions), {"n1", "n2"})
        strict = retrieval_ext.keyword_variant(hybrid, 2)
        self.assertEqual(strict._keyword_evidence(questions), {"n2"})
        self.assertEqual(hybrid._keyword_evidence(questions), {"n1", "n2"})  # the original is untouched


class SweepNamingTests(unittest.TestCase):
    def test_default_names_are_unchanged(self):
        self.assertEqual(research.sweep_output_name("scifact", "nomic-embed-text:latest"),
                         "sweep-scifact-nomic-embed-text-latest.json")
        self.assertEqual(research.answers_output_name("llama3:latest"), "answers-llama3-latest-full.json")
        self.assertEqual(research.answers_output_name("llama3:latest", "full", 0.4), "answers-llama3-latest-full-t0.4.json")
        self.assertEqual(research.answers_output_name("llama3:latest", "no_floor"), "answers-llama3-latest-no_floor.json")

    def test_new_option_names(self):
        self.assertEqual(research.sweep_output_name("scifact", "all-minilm:latest", "train", True, 2),
                         "sweep-scifact-train-all-minilm-latest-plain-kw2.json")
        self.assertEqual(research.sweep_output_name("nfcorpus", "nomic-embed-text:latest", nomic_prefixes=True),
                         "sweep-nfcorpus-nomic-embed-text-latest-prefix.json")
        self.assertEqual(research.answers_output_name("qwen2.5:7b", repeat=2), "answers-qwen2.5-7b-full-r2.json")
        self.assertEqual(research.answers_output_name("qwen2.5:7b", prompt_variant="alt", seed=3, repeat=1),
                         "answers-qwen2.5-7b-full-alt-s3-r1.json")

    def test_calibration_never_uses_the_evaluation_split(self):
        for dataset, split in (("scifact", "test"), ("scifact", "train"), ("nfcorpus", "test"),
                               ("nfcorpus", "dev"), ("nfcorpus", "train")):
            self.assertNotEqual(research.calibration_split(dataset, split), split)
        self.assertEqual(research.calibration_split("scifact", "test"), "train")   # as in the original runs
        self.assertEqual(research.calibration_split("nfcorpus", "test"), "dev")
        self.assertIsNone(research.calibration_split("arguana", "test"))

    def test_config_order_keeps_original_grouping(self):
        names = ["rerank", "kw2_floor_0.50", "floor_0.50", "vector_only", "hybrid_no_floor", "bm25_only", "convex"]
        self.assertEqual(sorted(names, key=research.config_order),
                         ["bm25_only", "hybrid_no_floor", "vector_only", "floor_0.50", "kw2_floor_0.50", "convex", "rerank"])


class BeirSplitTests(unittest.TestCase):
    def test_splits_and_missing_split_error(self):
        self.assertEqual(beir.available_splits("arguana"), ("test",))
        self.assertIn("train", beir.available_splits("scifact"))
        self.assertIn("dev", beir.available_splits("nfcorpus"))
        self.assertIn("arguana", beir.SHA256)
        with self.assertRaises(ValueError):
            beir.available_splits("msmarco")
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "qrels").mkdir()
            with self.assertRaises(ValueError):
                beir.load_split(directory, "dev")


class UnpinnedDownloadTests(unittest.TestCase):
    def test_unpinned_dataset_reports_digest_and_keeps_archive(self):
        import io
        import zipfile
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            bundle.writestr("arguana/queries.jsonl", "{}")
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "arguana.zip").write_bytes(buffer.getvalue())
            with unittest.mock.patch.dict(beir.SHA256, {"arguana": "NOT_PINNED"}):
                with self.assertRaisesRegex(ValueError, "not pinned yet"):
                    beir.ensure_beir("arguana", directory)
            self.assertTrue((Path(directory) / "arguana.zip").exists())
            self.assertFalse((Path(directory) / "arguana").exists())


class PromptVariantTests(unittest.TestCase):
    def test_default_is_the_original_prompt(self):
        system, template = prompts.prompt_variant("default")
        self.assertEqual(system, "Answer briefly and cite the supplied document passages.")
        self.assertIsNone(template)  # None keeps DocMind's own template

    def test_alt_rewords_but_keeps_the_rules(self):
        system, template = prompts.prompt_variant("alt")
        self.assertNotEqual(system, prompts.DEFAULT_SYSTEM_PROMPT)
        for placeholder in ("{context_str}", "{query_str}"):
            self.assertIn(placeholder, template)
        self.assertIn(squad.FALLBACK, template)   # graders depend on the exact fallback sentence
        self.assertIn("(from [n])", template)
        with self.assertRaises(ValueError):
            prompts.prompt_variant("other")

    def test_alt_template_matches_the_app_template_rules(self):
        from utils.llama_index import TEXT_QA_TEMPLATE
        self.assertNotEqual(prompts.ALT_TEMPLATE, TEXT_QA_TEMPLATE.template)
        self.assertEqual(sorted(TEXT_QA_TEMPLATE.template_vars), ["context_str", "query_str"])


class EndToEndHelperTests(unittest.TestCase):
    def test_refusal_and_citations(self):
        self.assertTrue(endtoend.is_refused(squad.FALLBACK))
        self.assertTrue(endtoend.is_refused('"I could not find this information in the documents." (from [1])'))
        self.assertFalse(endtoend.is_refused("The claim is supported (from [1])."))
        files = ["d1", "d2", "d3"]
        self.assertEqual(endtoend.cited_documents("Yes (from [2]) and [1] and [2], not [9] or [0].", files), ["d2", "d1"])
        self.assertTrue(endtoend.cites_relevant("Shown in (from [2]).", files, {"d2"}))
        self.assertFalse(endtoend.cites_relevant("Shown in (from [1]).", files, {"d2"}))
        self.assertFalse(endtoend.cites_relevant("No citation.", files, {"d2"}))

    def test_gate_summary(self):
        def rec(kind, refused, none=False, cites=None, relevant=False, ms=100):
            return {"kind": kind, "refused": refused, "retrieved_none": none, "cites_relevant": cites,
                    "retrieved_relevant": relevant, "ms": ms}
        records = [rec("fiqa", True, none=True, ms=10), rec("fiqa", False, ms=300),
                   rec("scifact", False, cites=True, relevant=True), rec("scifact", True, relevant=True),
                   rec("scifact", False, cites=False, relevant=True)]
        summary = endtoend.summarize_gate(records)
        self.assertEqual(summary["appropriate_refusals_fiqa"]["k"], 1)
        self.assertEqual(summary["unnecessary_refusals_scifact"]["k"], 1)
        self.assertEqual(summary["supported_answers_scifact"]["k"], 1)
        self.assertEqual(summary["model_calls_avoided_all"]["k"], 1)
        self.assertEqual(summary["model_calls_avoided_all"]["n"], 5)
        self.assertAlmostEqual(summary["mean_ms_fiqa"], 155)
        self.assertEqual(endtoend.gate_label(None), "no_floor")
        self.assertEqual(endtoend.gate_label(0.6), "floor_0.60")


class ResourceHelperTests(unittest.TestCase):
    def test_ollama_stats_and_throughput(self):
        raw = {"eval_count": 50, "eval_duration": 2_000_000_000, "prompt_eval_count": 300,
               "prompt_eval_duration": 500_000_000, "load_duration": 1_000_000_000}
        stats = resources.ollama_stats(raw)
        self.assertEqual(stats["eval_ms"], 2000)
        self.assertEqual(resources.tokens_per_second(stats["eval_count"], stats["eval_ms"]), 25)
        self.assertIsNone(resources.ollama_stats({"done": False}))
        self.assertIsNone(resources.ollama_stats(None))
        self.assertEqual(resources.tokens_per_second(0, 0), 0.0)

    def test_summarize_resources(self):
        records = [{"unanswerable": False, "correct": True, "retrieval_ms": 10, "generation_ms": 1000, "total_ms": 1100,
                    "ttft_ms": 200, "eval_count": 20, "eval_ms": 1000, "prompt_tokens": 100},
                   {"unanswerable": True, "correct": False, "retrieval_ms": 20, "generation_ms": 0, "total_ms": 30}]
        summary = resources.summarize_resources(records)
        self.assertEqual(summary["model_called"], 1)
        self.assertEqual(summary["tokens_per_second"], 20)
        self.assertEqual(summary["mean_retrieval_ms"], 15)
        self.assertEqual(summary["accuracy"], 0.5)
        self.assertEqual(summary["answerable_accuracy"], 1.0)
        self.assertEqual(summary["unanswerable_refused"], 0.0)

    def test_ollama_process_detection(self):
        self.assertTrue(resources.is_ollama_process("ollama.exe", None))
        self.assertTrue(resources.is_ollama_process("llama-server.exe", "C:/Users/x/Programs/Ollama/lib/ollama/llama-server.exe"))
        self.assertFalse(resources.is_ollama_process("python.exe", "C:/Python313/python.exe"))
        self.assertFalse(resources.is_ollama_process(None, None))

    def test_peak_monitor_keeps_peak_and_ignores_failures(self):
        values = iter([5.0, 9.0, 7.0])

        def broken():
            raise RuntimeError("no gpu")
        monitor = resources.PeakMonitor({"ram": lambda: next(values), "vram": broken, "none": lambda: None})
        for _ in range(3):
            monitor.sample()
        self.assertEqual(monitor.peaks, {"ram": 9.0, "vram": None, "none": None})
        self.assertEqual(monitor.first["ram"], 5.0)
        self.assertEqual(resources.resources_output_name("llama3:latest", "on"), "resources-llama3-latest-eco-on.json")

    def test_peak_monitor_thread_samples(self):
        with resources.PeakMonitor({"x": lambda: 1.0}, interval=0.01) as monitor:
            time.sleep(0.05)
        self.assertGreaterEqual(monitor.samples, 2)
        self.assertEqual(monitor.peaks["x"], 1.0)


def job(name, output=None):
    return {"name": name, "args": ["sweep", "--dataset", name], "output": output or f"{name}.json"}


class OvernightTests(unittest.TestCase):
    def test_skip_logic(self):
        jobs = [job("a"), job("b"), job("c")]
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "b.json").write_text("{}", encoding="utf-8")
            to_run, skipped = overnight.pending_jobs(jobs, directory)
            self.assertEqual([j["name"] for j in to_run], ["a", "c"])
            self.assertEqual([j["name"] for j in skipped], ["b"])
            self.assertEqual([j["name"] for j in overnight.pending_jobs(jobs, directory, only=["c"])[0]], ["c"])

    def test_run_resumes_restarts_ollama_and_continues_past_failures(self):
        jobs = [job("done"), job("bad"), job("good"), job("needs-model")]
        jobs[3]["requires"] = ["absent:1b"]
        calls, restarts, messages = [], [], []
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            (out / "done.json").write_text("{}", encoding="utf-8")

            def execute(j, out_dir):
                calls.append(j["name"])
                if j["name"] == "good":
                    (Path(out_dir) / j["output"]).write_text("{}", encoding="utf-8")
                    return 0, out / "log.txt"
                return 1, out / "log.txt"
            state = {"up": False}

            def restart():
                restarts.append(1)
                state["up"] = True
                return True
            outcome = overnight.run(jobs, out, health=lambda: state["up"], restart=restart,
                                    models=lambda: {"llama3:latest"}, execute=execute, log=messages.append)
            self.assertEqual(calls, ["bad", "good"])       # 'done' skipped, 'needs-model' never started
            self.assertEqual(restarts, [1])                  # restarted once; healthy afterwards
            self.assertEqual(outcome["done"], ["good"])
            self.assertEqual(outcome["failed"], ["bad", "needs-model"])
            self.assertEqual(outcome["skipped"], ["done"])
            self.assertTrue(any("ERROR bad" in m for m in messages))
            self.assertTrue(any("not installed" in m for m in messages))
            # A second run only retries what is still missing.
            calls.clear()
            overnight.run(jobs, out, health=lambda: True, restart=restart, models=lambda: {"absent:1b"},
                          execute=execute, log=messages.append)
            self.assertEqual(calls, ["bad", "needs-model"])

    def test_restart_failure_is_logged_not_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            messages = []
            outcome = overnight.run([job("a"), job("b")], directory, health=lambda: False, restart=lambda: False,
                                    models=lambda: set(), execute=lambda j, o: (0, None), log=messages.append)
            self.assertEqual(outcome["failed"], ["a", "b"])
            self.assertIn("did not come back", " ".join(messages))

    def test_missing_models_accepts_latest_alias(self):
        self.assertEqual(overnight.missing_models({"requires": ["llama3", "qwen2.5:3b"]}, {"llama3:latest"}), ["qwen2.5:3b"])
        self.assertEqual(overnight.missing_models({}, set()), [])

    def test_job_file_is_consistent_with_output_names(self):
        jobs = overnight.load_jobs()
        outputs = [j["output"] for j in jobs]
        self.assertEqual(len(outputs), len(set(outputs)))
        for j in jobs:
            args = j["args"]
            value = lambda flag, default=None: args[args.index(flag) + 1] if flag in args else default  # noqa: E731
            if args[0] == "sweep":
                expected = research.sweep_output_name(value("--dataset"), value("--model"), value("--split", "test"),
                                                      "--plain" in args, int(value("--keyword-min-terms", 1)),
                                                      "--nomic-prefixes" in args)
            elif args[0] == "answers":
                expected = research.answers_output_name(value("--chat-model"), "full", 0.0, value("--prompt-variant", "default"),
                                                        None, int(value("--repeat", 0)))
            elif args[0] == "endtoend":
                expected = endtoend.endtoend_output_name(value("--chat-model"))
            else:
                expected = resources.resources_output_name(value("--chat-model"), value("--eco"))
            self.assertEqual(j["output"], expected, j["name"])
        kinds = [j["args"][0] for j in jobs]
        # Jobs are ordered by priority, not by kind; check the mix instead of the order.
        self.assertEqual(set(kinds), {"sweep", "answers", "endtoend", "resources"})
        self.assertGreaterEqual(kinds.count("sweep"), 6)
        self.assertEqual(json.loads(Path(overnight.JOBS_FILE).read_text(encoding="utf-8"))["jobs"], jobs)


if __name__ == "__main__":
    unittest.main()
