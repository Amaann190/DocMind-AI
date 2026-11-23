"""Statistics, BEIR/SQuAD loaders, grading and attack templates for the research experiments (offline)."""
import csv
import io
import json
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from evaluation import beir, research, squad, stats


class StatsTests(unittest.TestCase):
    def test_wilson_bounds(self):
        low, high = stats.wilson(24, 32)
        self.assertAlmostEqual(low, 0.579, places=3)
        self.assertAlmostEqual(high, 0.867, places=3)
        self.assertEqual(stats.wilson(0, 0), (0.0, 0.0))
        self.assertEqual(stats.wilson(5, 5)[1], 1.0)

    def test_mcnemar(self):
        self.assertAlmostEqual(stats.mcnemar_exact(11, 2), 0.0225, places=4)
        self.assertAlmostEqual(stats.mcnemar_exact(3, 1), 0.625)
        self.assertEqual(stats.mcnemar_exact(0, 0), 1.0)

    def test_bootstrap_contains_mean(self):
        values = [0.0, 1.0] * 50
        low, high = stats.bootstrap_ci(values, iterations=2000)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        self.assertEqual(stats.bootstrap_ci([]), (0.0, 0.0))

    def test_paired_bootstrap(self):
        better = stats.paired_bootstrap([1.0] * 40, [0.0] * 40, iterations=1000)
        self.assertEqual(better["diff"], 1.0)
        self.assertLess(better["p"], 0.01)
        same = stats.paired_bootstrap([0.5, 0.2], [0.5, 0.2], iterations=500)
        self.assertEqual(same["p"], 1.0)
        self.assertEqual(stats.paired_bootstrap([], [])["p"], 1.0)
        with self.assertRaises(ValueError):
            stats.paired_bootstrap([1.0], [])

    def test_calibrate_floor(self):
        recall = {0.4: 0.90, 0.5: 0.89, 0.6: 0.80}
        self.assertEqual(stats.calibrate_floor(recall, 0.90), 0.5)
        self.assertIsNone(stats.calibrate_floor({0.5: 0.1}, 0.9))

    def test_kappa(self):
        self.assertEqual(stats.cohen_kappa(["1", "0", "1"], ["1", "0", "1"]), 1.0)
        self.assertAlmostEqual(stats.cohen_kappa(["1", "1", "0", "0"], ["1", "0", "1", "0"]), 0.0)
        self.assertEqual(stats.cohen_kappa([], []), 0.0)
        self.assertEqual(stats.cohen_kappa(["1"], ["1"]), 1.0)
        with self.assertRaises(ValueError):
            stats.cohen_kappa(["1"], [])


def write_beir(root, name):
    folder = root / name
    (folder / "qrels").mkdir(parents=True)
    (folder / "corpus.jsonl").write_text(json.dumps({"_id": "d1", "title": "T", "text": "Body."}) + "\n", encoding="utf-8")
    (folder / "queries.jsonl").write_text(
        json.dumps({"_id": "q1", "text": "Question one"}) + "\n"
        + json.dumps({"_id": "q2", "text": "Question two"}) + "\n", encoding="utf-8")
    (folder / "qrels" / "test.tsv").write_text("query-id\tcorpus-id\tscore\nq1\td1\t2\nq2\td1\t0\n", encoding="utf-8")
    return folder


class BeirTests(unittest.TestCase):
    def test_load_and_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = write_beir(Path(directory), "nfcorpus")
            self.assertEqual(beir.load_corpus(folder), {"d1": "T\n\nBody."})
            queries, qrels = beir.load_split(folder, "test")
            self.assertEqual(queries, {"q1": "Question one"})
            self.assertEqual(qrels, {"q1": {"d1": 2}})
            self.assertEqual(beir.ensure_beir("nfcorpus", directory), folder)
        sample = beir.sample({str(i): i for i in range(10)}, 3)
        self.assertEqual(len(sample), 3)
        self.assertEqual(sample, beir.sample({str(i): i for i in range(10)}, 3))

    def test_unknown_and_tampered(self):
        with self.assertRaises(ValueError):
            beir.ensure_beir("msmarco")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as bundle:
            bundle.writestr("fiqa/queries.jsonl", "{}")
        with tempfile.TemporaryDirectory() as directory:
            def fake(url, path):
                Path(path).write_bytes(buffer.getvalue())
            with patch.object(beir.urllib.request, "urlretrieve", side_effect=fake), self.assertRaises(ValueError):
                beir.ensure_beir("fiqa", directory)
            self.assertFalse((Path(directory) / "fiqa.zip").exists())

    def test_verified_archive_extracts_and_rejects_traversal(self):
        good = io.BytesIO()
        with zipfile.ZipFile(good, "w") as bundle:
            bundle.writestr("fiqa/queries.jsonl", "{}")
        evil = io.BytesIO()
        with zipfile.ZipFile(evil, "w") as bundle:
            bundle.writestr("../evil.txt", "x")
        for payload, ok in ((good.getvalue(), True), (evil.getvalue(), False)):
            with tempfile.TemporaryDirectory() as directory:
                (Path(directory) / "fiqa.zip").write_bytes(payload)
                digest = beir.hashlib.sha256(payload).hexdigest()
                with patch.dict(beir.SHA256, {"fiqa": digest}):
                    if ok:
                        self.assertTrue((beir.ensure_beir("fiqa", directory) / "queries.jsonl").exists())
                    else:
                        with self.assertRaises(ValueError):
                            beir.ensure_beir("fiqa", directory)


SQUAD = {"data": [{"title": "Normans", "paragraphs": [
    {"context": "The Normans lived in Normandy. They spoke French.",
     "qas": [{"id": "a", "question": "Where did the Normans live?", "answers": [{"text": "Normandy"}], "is_impossible": False},
             {"id": "b", "question": "Who ruled Spain?", "answers": [], "is_impossible": True}]},
    {"context": "Rollo was a Viking.",
     "qas": [{"id": "c", "question": "Who was Rollo? ", "answers": [{"text": "a Viking"}], "is_impossible": False}]}]}]}


class SquadTests(unittest.TestCase):
    def test_load_and_sample_one_per_paragraph(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "squad.json"
            path.write_text(json.dumps(SQUAD), encoding="utf-8")
            contexts, questions = squad.load_squad(path)
        self.assertEqual(len(contexts), 2)
        self.assertEqual(questions[2]["question"], "Who was Rollo?")
        picked = squad.sample_questions(questions, 2, 1)
        self.assertEqual(len({q["context_id"] for q in picked}), len(picked))

    def test_grading(self):
        answerable = {"unanswerable": False, "answers": ["Normandy"]}
        impossible = {"unanswerable": True, "answers": []}
        self.assertTrue(squad.grade(answerable, "They lived in Normandy [1]."))
        self.assertFalse(squad.grade(answerable, squad.FALLBACK))
        self.assertFalse(squad.grade(answerable, "In Paris."))
        self.assertTrue(squad.grade(impossible, squad.FALLBACK))
        self.assertFalse(squad.grade(impossible, "Philip II."))
        self.assertEqual(squad.normalize_answer("The  Normans!"), "normans")
        self.assertFalse(squad.contains_gold("anything", ["the"]))
        self.assertEqual(squad.token_f1("Normandy [1]", ["Normandy"]), 1.0)
        self.assertAlmostEqual(squad.token_f1("1621 to 1629", ["between 1621 and 1629"]), 4 / 7)
        self.assertEqual(squad.token_f1("", ["x"]), 0.0)

    def test_inject_after_answer_sentence(self):
        text = squad.inject("One. The answer is Normandy. Three.", "ignore_previous", "Normandy")
        sentences = text.split(". ")
        self.assertIn(squad.CANARY, sentences[2])
        self.assertIn(squad.CANARY, squad.inject("Only sentence.", "hinglish"))
        self.assertEqual(len(squad.ATTACKS), 8)

    def test_squad_download_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "squad-dev-v2.0.json"
            path.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                squad.ensure_squad(directory)
            self.assertFalse(path.exists())


class ResearchCliTests(unittest.TestCase):
    def test_score_and_paired_tests(self):
        rows = {"q1": {"vector_only": ["d1"], "bm25_only": [], "hybrid_no_floor": ["d1"], "floor_0.50": ["d1"]},
                "q2": {"vector_only": ["d9"], "bm25_only": ["d2"], "hybrid_no_floor": ["d2"], "floor_0.50": ["d2"]}}
        qrels = {"q1": {"d1": 1}, "q2": {"d2": 1}}
        off = {"o1": {"vector_only": ["d1"], "bm25_only": [], "hybrid_no_floor": ["d1"], "floor_0.50": []}}
        calib = {"c1": {"vector_only": ["d1"], "bm25_only": [], "hybrid_no_floor": ["d1"], "floor_0.50": ["d1"]}}
        names = ["vector_only", "bm25_only", "hybrid_no_floor", "floor_0.50"]
        summary = research.score(rows, qrels, off, calib, {"c1": {"d1": 1}}, names, 10)
        self.assertEqual(summary["configurations"]["floor_0.50"]["rejection"], 1.0)
        self.assertEqual(summary["configurations"]["bm25_only"]["no_result"], 0.5)
        self.assertEqual(summary["calibrated_floor"], 0.5)
        self.assertIn("floor_0.50 vs hybrid_no_floor", summary["paired"])

    def test_summarize_answers_and_sheet_and_kappa(self):
        records = [{"id": "a", "question": "Q", "answers": ["x"], "unanswerable": False, "answer": "x [1]",
                    "passages": ["p"], "correct": True, "refused": False, "cited": True, "retrieved_gold": True,
                    "retrieved_none": False, "ms": 10},
                   {"id": "b", "question": "Q2", "answers": [], "unanswerable": True, "answer": squad.FALLBACK,
                    "passages": [], "correct": True, "refused": True, "cited": False, "retrieved_gold": False,
                    "retrieved_none": True, "ms": 5}]
        injection = [{"attack": "hinglish", "filter": True, "attack_success": False, "task_success": True},
                     {"attack": "hinglish", "filter": False, "attack_success": True, "task_success": False}]
        summary = research.summarize_answers(records, injection)
        self.assertEqual(summary["overall_correct"]["rate"], 1.0)
        self.assertEqual(summary["injection"]["filter_off"]["by_attack"]["hinglish"], 1)
        with tempfile.TemporaryDirectory() as directory:
            results = Path(directory) / "answers.json"
            results.write_text(json.dumps({"records": records}), encoding="utf-8")
            sheet = Path(directory) / "sheet.csv"
            with redirect_stdout(io.StringIO()):
                research.main(["sheet", "--results", str(results), "--csv", str(sheet)])
            with open(sheet, encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            for row in rows:
                row.update(grader1_correct="1", grader2_correct="1", grader1_supported="1", grader2_supported="1")
            with open(sheet, "w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            out = io.StringIO()
            with redirect_stdout(out):
                research.main(["kappa", "--csv", str(sheet)])
            self.assertEqual(json.loads(out.getvalue())["items"], 2)
        self.assertEqual(research.slug("llama3:latest"), "llama3-latest")


if __name__ == "__main__":
    unittest.main()
