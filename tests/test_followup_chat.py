"""Conversation-aware retrieval and section/link preservation regressions."""
import socket
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from llama_index.core.embeddings import MockEmbedding
from llama_index.core.schema import TextNode

from utils import helpers, llama_index as rag, ollama
from utils.runtime import request_state


class FollowupTests(unittest.TestCase):
    def answer(self, question, messages, start=0):
        node = TextNode(text="Stream aggregators include Orbit Cinema: https://orbit.example.test/")
        store = Mock()
        store.get_node.return_value = node
        vector = Mock()
        vector.retrieve.return_value = []
        retriever = rag.HybridRetriever(vector, store, [node.node_id], 3)
        llm = Mock()
        llm.stream_chat.return_value = [SimpleNamespace(delta="Orbit Cinema [1].")]
        state = {"retriever": retriever, "messages": messages, "rag_history_start": start}
        with request_state(state), patch.object(ollama, "create_llm", return_value=llm):
            answer = "".join(ollama.context_chat(question, None))
        return answer, llm, vector

    def test_names_followup_retrieves_previous_topic_after_a_long_answer(self):
        messages = [
            {"role": "user", "content": "Give me a Stream aggregator website link."},
            {"role": "assistant", "content": "A long previous answer. " * 300},
            {"role": "user", "content": "okay then just give me names"},
        ]
        answer, llm, vector = self.answer(messages[-1]["content"], messages)
        self.assertIn("Orbit Cinema", answer)
        sent = llm.stream_chat.call_args.args[0]
        self.assertTrue(any(m.content == messages[0]["content"] for m in sent))
        self.assertIn("https://orbit.example.test/", sent[-1].content)
        self.assertIn("Stream aggregator", vector.retrieve.call_args.args[0])
        self.assertIn("okay then just give me names", sent[-1].content)
        self.assertLessEqual(sum(ollama._estimate_tokens(m.content) + 8 for m in sent) + 512 + 128, 2048)

    def test_chained_followups_keep_topic_without_inventing_evidence(self):
        messages = [
            {"role": "user", "content": "Which stream aggregators are listed?"},
            {"role": "assistant", "content": "No matching information."},
            {"role": "user", "content": "Can you share a website link for an example?"},
            {"role": "assistant", "content": "No matching information."},
        ]
        answer, _, vector = self.answer("okay then just give me names", messages)
        self.assertIn("Orbit Cinema", answer)
        self.assertIn("stream aggregators", vector.retrieve.call_args.args[0])
        self.assertNotIn("No matching information", vector.retrieve.call_args.args[0])

    def test_new_topic_reset_and_free_chat_do_not_reuse_previous_topic(self):
        messages = [{"role": "user", "content": "List stream aggregators"},
                    {"role": "assistant", "content": "Orbit Cinema"}]
        cases = [("What is Jupiter's mass?", messages, 0),
                 ("okay then just give me names", messages, 2),
                 ("okay then just give me names", [{**messages[0], "without_documents": True}, messages[1]], 0)]
        for question, history, start in cases:
            with self.subTest(question=question, start=start, history=history):
                answer, llm, vector = self.answer(question, history, start)
                self.assertEqual(answer, "I could not find this information in the documents.")
                llm.stream_chat.assert_not_called()
                vector.retrieve.assert_called_once_with(question)


class WebsiteSectionTests(unittest.TestCase):
    def test_links_and_headings_stay_with_later_chunks_without_navigation(self):
        html = ("<html><head><title>Resource Directory</title></head><body>"
                "<nav>NAVIGATION-ONLY-NOISE</nav><main><h1>Resource Directory</h1>"
                "<h2>Streaming</h2><h3>Stream Aggregators</h3><p>Players combine sources.</p><ul>"
                + "".join(f'<li><a href="/watch/{i}">Orbit Cinema {i}</a> - Movies and television.</li>' for i in range(18))
                + "</ul><h3>Educational Archives</h3><p>Archive lectures.</p></main></body></html>")
        public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        response = Mock(status=200, headers={"Content-Type": "text/html; charset=utf-8"})
        response.stream.return_value = [html.encode()]
        pool = Mock()
        pool.urlopen.return_value = response
        with patch.object(helpers.socket, "getaddrinfo", return_value=public), \
                patch.object(helpers.urllib3, "HTTPSConnectionPool", return_value=pool):
            docs = helpers.load_website_documents(["https://directory.example.test/catalog"])
        self.assertNotIn("NAVIGATION-ONLY-NOISE", docs[0].text)
        self.assertIn("https://directory.example.test/watch/17", docs[0].text)
        with request_state({}):
            index = rag.create_index(docs, embed_model=MockEmbedding(embed_dim=8), chunk_size=256, chunk_overlap=32)
        chunks = list(index.docstore.docs.values())
        for chunk in chunks:
            if "Orbit Cinema" in chunk.text:
                self.assertEqual(chunk.text.count("]("), chunk.text.count(")"), chunk.text)
        later = next(n for n in chunks if "https://directory.example.test/watch/17" in n.text)
        self.assertIn("Stream Aggregators", later.text)
        self.assertNotIn("Educational Archives", later.text)
        archive = next(n for n in chunks if "Archive lectures" in n.text)
        self.assertNotIn("Stream Aggregators", archive.text)

    def test_explicit_section_does_not_mix_neighboring_categories(self):
        from llama_index.core.schema import NodeWithScore

        nodes = [TextNode(text="Streaming sites have website links for names and examples.", metadata={"section": "Videos / Multi-Server"}),
                 TextNode(text="Stream Aggregators: Orbit Cinema https://orbit.example.test/", metadata={"section": "Videos / Stream Aggregators"})]
        store = Mock()
        store.get_node.side_effect = {n.node_id: n for n in nodes}.get
        vector = Mock()
        vector.retrieve.return_value = [NodeWithScore(node=n, score=.9) for n in nodes]
        with request_state({}):
            retriever = rag.HybridRetriever(vector, store, [n.node_id for n in nodes], 3)
            found = retriever.retrieve("Share a stream aggregator website link. Okay then just give me names.")
        self.assertEqual([n.node.node_id for n in found], [nodes[1].node_id])

    def test_connected_website_overview_selects_opening(self):
        nodes = [TextNode(text="Resource Directory lists categorized links.", metadata={"source": "https://directory.example.test/"}),
                 TextNode(text="Unrelated page detail.", metadata={"source": "https://directory.example.test/"})]
        store = Mock()
        store.get_node.side_effect = {n.node_id: n for n in nodes}.get
        vector = Mock()
        vector.retrieve.return_value = []
        with request_state({}):
            retriever = rag.HybridRetriever(vector, store, [n.node_id for n in nodes], 3)
            found = retriever.retrieve("Can you tell me about the connected website?")
        self.assertEqual([n.node.text for n in found], [nodes[0].text])
