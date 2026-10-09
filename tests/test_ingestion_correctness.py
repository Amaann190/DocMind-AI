"""Content-preservation and truthful partial-ingestion regressions; no model server."""

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llama_index.core.embeddings import MockEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, NodeRelationship, NodeWithScore, RelatedNodeInfo, TextNode

from utils import llama_index as ingestion
from utils import rag_pipeline as pipeline


def node(text, source="source-a", **metadata):
    return TextNode(text=text, metadata=metadata, relationships={
        NodeRelationship.SOURCE: RelatedNodeInfo(node_id=source),
    })


class ContentPreservationTests(unittest.TestCase):
    def test_large_json_and_jsonl_keep_every_record_and_original(self):
        records = [{"row": number, "value": f"FACT-{number}"} for number in range(120)]
        for extension in ("json", "jsonl"):
            with self.subTest(extension=extension):
                text = json.dumps(records) if extension == "json" else "\n".join(map(json.dumps, records))
                document = Document(text=text, metadata={"file_name": "data." + extension})
                ingestion._verbalize_tabular_docs([document])
                self.assertIn("Record 120: row is 119, value is FACT-119.", document.text)
                self.assertTrue(document.text.endswith(text))

    def test_csv_preserves_extra_columns_beyond_old_excerpt_limit(self):
        text = 'name,value\n' + ('entry,"long multiline\nvalue"\n' * 60) + 'last,known,UNNAMED-EXTRA\n'
        document = Document(text=text, metadata={"file_name": "data.csv"})
        ingestion._verbalize_tabular_docs([document])
        self.assertTrue(document.text.endswith(text))
        self.assertIn("UNNAMED-EXTRA", document.text)

    def test_mixed_json_keeps_original_structure(self):
        text = json.dumps([{"a": i} for i in range(6)] + [False, None, ["TAIL-FACT"]])
        document = Document(text=text, metadata={"file_name": "mixed.json"})
        ingestion._verbalize_tabular_docs([document])
        self.assertEqual(document.text, text)

    def test_dedup_preserves_numbers_negations_word_order_and_sources(self):
        nodes = [
            node("Employees receive 20 days annual leave."),
            node("Employees receive 25 days annual leave."),
            node("Employees do not receive 20 days annual leave."),
            node("Alice paid Bob."), node("Bob paid Alice."),
            node("Employees receive 20 days annual leave.", source="source-b"),
            node("Employees receive 20 days annual leave.", page_label="2"),
        ]
        repeated = node(nodes[0].text)
        self.assertEqual(ingestion._dedupe_exact_nodes(nodes + [repeated]), nodes)

    def test_code_fences_never_merge_separate_sources(self):
        first = node("```python\nprint('one')", "source-a")
        second = node("SECRET-OTHER-SOURCE", "source-b")
        self.assertEqual(ingestion._merge_code_blocks([first, second]), [first, second])
        self.assertNotIn("SECRET", first.text)
        continuation = node("print('two')\n```", "source-a")
        self.assertEqual(len(ingestion._merge_code_blocks([first, continuation])), 1)
        self.assertIn("print('two')", first.text)

    def test_short_facts_and_similar_rows_survive_real_indexing(self):
        documents = [
            Document(text="42", metadata={"file_name": "answer.txt"}),
            Document(text="ORBIT-7429", metadata={"file_name": "code.xml"}),
            Document(text="Staff receive 20 days of leave.", metadata={"file_name": "old.txt"}),
            Document(text="Staff receive 25 days of leave.", metadata={"file_name": "new.txt"}),
        ]
        index = ingestion.create_index(documents, embed_model=MockEmbedding(embed_dim=8), chunk_size=64, chunk_overlap=0)
        stored = {item.metadata["file_name"]: item.text for item in index.docstore.docs.values()}
        self.assertEqual(set(stored), {doc.metadata["file_name"] for doc in documents})
        self.assertIn("42", stored["answer.txt"])
        self.assertIn("ORBIT-7429", stored["code.xml"])
        self.assertIn("20 days", stored["old.txt"])
        self.assertIn("25 days", stored["new.txt"])

    def test_retrieval_keeps_similar_but_conflicting_evidence(self):
        nodes = [node("Staff receive 20 days of leave."), node("Staff receive 25 days of leave.")]
        lookup = {item.node_id: item for item in nodes}
        vector = Mock()
        vector.retrieve.return_value = [NodeWithScore(node=item, score=0.8) for item in nodes]
        docstore = Mock()
        docstore.get_node.side_effect = lookup.__getitem__
        with patch.object(ingestion, "st", SimpleNamespace(session_state={})):
            retriever = ingestion.HybridRetriever(vector, docstore, list(lookup), top_k=3)
            results = retriever.retrieve("How many leave days?")
        self.assertEqual({result.node.node_id for result in results}, set(lookup))


class FileFailureTests(unittest.TestCase):
    def test_mixed_batch_reports_corrupt_and_empty_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.txt").write_text("KEEP-THIS-FACT")
            (root / "empty.txt").write_text(" \n")
            (root / "broken.docx").write_bytes(b"not a ZIP archive")
            errors = []
            documents = ingestion.load_documents(directory, input_files=list(root.iterdir()), errors=errors)
        self.assertEqual(len(documents), 1)
        self.assertIn("KEEP-THIS-FACT", documents[0].text)
        self.assertEqual({entry["file"] for entry in errors}, {"broken.docx", "empty.txt"})
        self.assertTrue(all(entry["error"] for entry in errors))

    def test_directory_exclusions_survive_a_broken_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "good.txt").write_text("KEEP-THIS-FACT")
            (root / "broken.docx").write_bytes(b"not a ZIP archive")
            (root / "excluded.png").write_text("MUST-NOT-APPEAR")
            (root / ".secret.txt").write_text("MUST-NOT-APPEAR")
            (root / "node_modules").mkdir()
            (root / "node_modules/private.txt").write_text("MUST-NOT-APPEAR")
            errors = []
            documents = ingestion.load_documents(directory, errors=errors)
        self.assertEqual([doc.metadata["file_name"] for doc in documents], ["good.txt"])
        self.assertEqual([entry["file"] for entry in errors], ["broken.docx"])

    def test_all_failed_has_file_names_and_empty_selection_reads_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.txt"
            path.write_text("")
            errors = []
            with self.assertRaisesRegex(ValueError, "empty.txt: No readable text"):
                ingestion.load_documents(directory, errors=errors)
            self.assertEqual(len(errors), 1)
            with self.assertRaisesRegex(ValueError, "No files were selected"):
                ingestion.load_documents(directory, input_files=[])

    def test_pipeline_persists_partial_results_and_warns_on_rerun(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            (root / "good.txt").write_text("KEEP-THIS-FACT")
            (root / "empty.txt").write_text("")
            state = {"selected_model": "chat", "ollama_endpoint": "http://localhost:11434",
                     "system_prompt": "", "chunk_size": 64, "chunk_overlap": 0,
                     "ollama_embedding_model": "embedding"}
            ui = Mock(session_state=state)
            stack.enter_context(patch.object(pipeline, "st", ui))
            stack.enter_context(patch.object(pipeline.ollama, "verify_chat_model", return_value=True))
            stack.enter_context(patch.object(pipeline.ollama, "create_llm"))
            stack.enter_context(patch.object(ingestion, "setup_embedding_model"))
            stack.enter_context(patch.object(pipeline.func, "remove_dir_retry"))
            def create_engine(*args, **kwargs):
                state["query_engine"] = object()
            stack.enter_context(patch.object(ingestion, "create_query_engine", side_effect=create_engine))
            self.assertIsNone(pipeline.rag_pipeline(data_dir=directory, status_state_key="github_ingestion_stages"))
            self.assertIn("Documents Loaded (1 file(s) skipped)", state["github_ingestion_stages"])
            self.assertEqual(state["github_ingestion_stages_errors"][0]["file"], "empty.txt")
            for _ in range(2):
                pipeline.render_ingestion_result("github_ingestion_stages")
            self.assertEqual(ui.warning.call_count, 2)
            self.assertIn("empty.txt", ui.text.call_args.args[0])
            ui.write.assert_not_called()
            ui.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
