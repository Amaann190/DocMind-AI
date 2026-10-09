import unittest
from types import SimpleNamespace
from unittest.mock import patch

import utils.ollama
from utils.ollama import (
    _build_rag_messages,
    _embed_batch_size,
    _num_predict,
    _rag_history_budget,
    create_llm,
    get_embedding_models,
    get_models,
    get_openai_models,
    verify_chat_model,
)


class OllamaTests(unittest.TestCase):
    def test_get_embedding_models_prefers_embeddinggemma_latest(self):
        state = {
            "ollama_endpoint": "http://localhost:11434",
            "ollama_embedding_model": "missing:latest",
        }
        client = SimpleNamespace(
            list=lambda: {
                "models": [
                    {"model": "nomic-embed-text:latest"},
                    {"model": "embeddinggemma:latest"},
                    {"model": "gemma4:latest"},
                ]
            },
            show=lambda model_name: {
                "capabilities": (
                    ["completion"]
                    if model_name == "gemma4:latest"
                    else ["embedding"]
                )
            },
        )

        with patch("utils.ollama.st", SimpleNamespace(session_state=state)), patch(
            "utils.ollama.create_client", return_value=client
        ):
            models = get_embedding_models()

        self.assertEqual(
            models,
            ["nomic-embed-text:latest", "embeddinggemma:latest"],
        )
        self.assertEqual(state["ollama_embedding_model"], "embeddinggemma:latest")

    def test_get_models_clears_stale_models_when_discovery_fails(self):
        state = {
            "ollama_endpoint": "",
            "ollama_models": ["gemma4:latest"],
        }

        with patch("utils.ollama.st", SimpleNamespace(session_state=state)), patch(
            "utils.ollama.create_client", side_effect=RuntimeError("bad endpoint")
        ):
            models = get_models()

        self.assertEqual(models, [])
        self.assertEqual(state["ollama_models"], [])


class ChatModelValidationTests(unittest.TestCase):
    def _client(self):
        return SimpleNamespace(
            list=lambda: {
                "models": [
                    {"model": "qwen2.5:0.5b"},
                    {"model": "nomic-embed-text:latest"},
                ]
            },
            show=lambda model_name: {
                "capabilities": (
                    ["completion"]
                    if model_name == "qwen2.5:0.5b"
                    else ["embedding"]
                )
            },
        )

    def test_verify_chat_model_accepts_completion_model(self):
        with patch(
            "utils.ollama.create_client", return_value=self._client()
        ):
            self.assertTrue(
                verify_chat_model("qwen2.5:0.5b", "http://localhost:11434")
            )

    def test_verify_chat_model_rejects_missing_model(self):
        with patch(
            "utils.ollama.create_client", return_value=self._client()
        ):
            self.assertFalse(
                verify_chat_model("missing:latest", "http://localhost:11434")
            )

    def test_verify_chat_model_rejects_embedding_only_model(self):
        with patch(
            "utils.ollama.create_client", return_value=self._client()
        ):
            self.assertFalse(
                verify_chat_model(
                    "nomic-embed-text:latest", "http://localhost:11434"
                )
            )

    def test_verify_chat_model_false_when_server_down(self):
        with patch(
            "utils.ollama.create_client", side_effect=RuntimeError("boom")
        ):
            self.assertFalse(
                verify_chat_model("qwen2.5:0.5b", "http://localhost:11434")
            )


class GetOpenAIModelsTests(unittest.TestCase):
    def _response(self, models):
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"data": [{"id": name} for name in models]},
        )

    def test_get_openai_models_parses_server_response(self):
        with patch(
            "utils.ollama.requests.get",
            return_value=self._response(["model-a", "model-b"]),
        ) as request:
            models = get_openai_models("http://localhost:1234/v1")

        self.assertEqual(models, ["model-a", "model-b"])
        self.assertEqual(
            request.call_args.args[0], "http://localhost:1234/v1/models"
        )

    def test_get_openai_models_returns_empty_on_error(self):
        with patch(
            "utils.ollama.requests.get", side_effect=RuntimeError("boom")
        ):
            self.assertEqual(get_openai_models("http://localhost:1234/v1"), [])


class CreateLLMDispatchTests(unittest.TestCase):
    def test_dispatches_to_openai_for_openai_backend(self):
        state = {"llm_backend": "OpenAI"}
        with patch(
            "utils.ollama.st", SimpleNamespace(session_state=state)
        ), patch("utils.ollama.create_openai_llm") as openai_llm, patch(
            "utils.ollama.create_ollama_llm"
        ) as ollama_llm:
            create_llm("my-model", "http://x/v1", "key", None, 0.7)

        openai_llm.assert_called_once_with("my-model", "http://x/v1", "key", 0.7, eco_mode=False)
        ollama_llm.assert_not_called()

    def test_dispatches_to_ollama_by_default(self):
        state = {"llm_backend": "Ollama"}
        with patch(
            "utils.ollama.st", SimpleNamespace(session_state=state)
        ), patch("utils.ollama.create_openai_llm") as openai_llm, patch(
            "utils.ollama.create_ollama_llm"
        ) as ollama_llm:
            create_llm("qwen2.5:0.5b", "http://localhost:11434", system_prompt="sys")

        ollama_llm.assert_called_once_with(
            "qwen2.5:0.5b", "http://localhost:11434", "sys", temperature=None, eco_mode=False
        )
        openai_llm.assert_not_called()


class EcoModeTests(unittest.TestCase):
    def test_eco_mode_defaults_off(self):
        state = {}
        with patch("utils.ollama.st", SimpleNamespace(session_state=state)):
            self.assertEqual(_num_predict(), 512)
            self.assertEqual(_embed_batch_size(), 16)
            self.assertEqual(_rag_history_budget(), 500)

    def test_eco_mode_slows_work_down(self):
        state = {"eco_mode": True}
        with patch("utils.ollama.st", SimpleNamespace(session_state=state)):
            self.assertEqual(_num_predict(), 256)
            self.assertEqual(_embed_batch_size(), 4)
            self.assertEqual(_rag_history_budget(), 300)

    def test_eco_mode_is_false_when_session_state_unavailable(self):
        with patch(
            "utils.ollama.st",
            SimpleNamespace(session_state=None),
        ):
            self.assertFalse(utils.ollama._is_eco_mode())


class RAGMessageBuildingTests(unittest.TestCase):
    def _message(self, role, content):
        return utils.ollama.ChatMessage(
            role=utils.ollama.MessageRole.ASSISTANT
            if role == "assistant"
            else utils.ollama.MessageRole.USER,
            content=content,
        )

    def test_rag_messages_include_history_before_current_question(self):
        state = {}
        with patch("utils.ollama.st", SimpleNamespace(session_state=state)):
            history = [
                self._message("user", "What is the refund policy?"),
                self._message("assistant", "30 days."),
            ]
            messages = _build_rag_messages(
                "And for electronics?",
                "[1]:\nRefunds take 30 days.",
                history,
                "You are DocMind.",
            )

        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0].role, utils.ollama.MessageRole.SYSTEM)
        self.assertEqual(messages[1].role, utils.ollama.MessageRole.SYSTEM)
        self.assertEqual(messages[2].content, "What is the refund policy?")
        self.assertEqual(messages[3].content, "30 days.")
        self.assertIn("Refunds take 30 days.", messages[4].content)
        self.assertIn("And for electronics?", messages[4].content)

    def test_rag_messages_work_without_history_or_system_prompt(self):
        state = {}
        with patch("utils.ollama.st", SimpleNamespace(session_state=state)):
            messages = _build_rag_messages(
                "Question?", "[1]:\nContext text.", [], ""
            )

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, utils.ollama.MessageRole.SYSTEM)
        self.assertEqual(messages[1].role, utils.ollama.MessageRole.USER)
        self.assertIn("Context text.", messages[1].content)

    def test_rag_history_is_trimmed_to_budget(self):
        state = {}
        with patch("utils.ollama.st", SimpleNamespace(session_state=state)):
            history = [
                self._message("user", "word " * 4000),
                self._message("assistant", "OK"),
            ]
            messages = _build_rag_messages(
                "Next?", "[1]:\nCtx", history, ""
            )

        # The oversized first turn must be dropped, keeping only the tail.
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1].content, "OK")
        self.assertIn("Next?", messages[2].content)


if __name__ == "__main__":
    unittest.main()
