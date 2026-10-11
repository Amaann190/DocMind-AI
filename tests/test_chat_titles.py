import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from utils import ollama


class ChatTitleTests(unittest.TestCase):
    def test_title_output_is_bounded_and_uses_selected_provider(self):
        for backend in ("Ollama", "OpenAI", "LM Studio (Local AI)", "TabbyAPI"):
            model = Mock(additional_kwargs={})
            model.chat.return_value = SimpleNamespace(message=SimpleNamespace(content='"How Photosynthesis Works"'))
            with self.subTest(backend=backend), patch.object(ollama, "create_llm", return_value=model) as create:
                title = ollama.conversation_title("question" * 500, "answer" * 500,
                    model="chosen-model", base_url="http://localhost:11434", backend=backend)
                self.assertEqual(title, "How Photosynthesis Works")
                self.assertEqual(create.call_args.kwargs["backend"], backend)
                self.assertLess(len(model.chat.call_args.args[0][1].content), 1900)
                if backend == "Ollama":
                    self.assertEqual(model.request_timeout, 15)
                    self.assertEqual(model.additional_kwargs["num_predict"], 40)
                else:
                    self.assertEqual(model.timeout, 15)
                    self.assertEqual(model.max_tokens, 40)

    def test_malformed_titles_fall_back_instead_of_becoming_sidebar_text(self):
        model = Mock(additional_kwargs={})
        for value in ("", "x" * 71, "First line\nExplanation", "<think>unfinished", "one " * 11):
            model.chat.return_value = SimpleNamespace(message=SimpleNamespace(content=value))
            with self.subTest(value=value), patch.object(ollama, "create_llm", return_value=model):
                self.assertEqual(ollama.conversation_title("q", "a", model="test", base_url="http://localhost"), "")
