import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import httpx
from utils import ollama, r2r


class ProviderTransportTests(unittest.TestCase):
    def test_compatible_custom_model_metadata_and_temperature_are_current(self):
        for backend in ("OpenAI", "LM Studio (Local AI)", "TabbyAPI"):
            for temperature in (.1, 1.2):
                with patch.object(ollama, "st", SimpleNamespace(session_state={"llm_backend": backend, "temperature": temperature})):
                    model = ollama.create_llm("my-local-model", "http://localhost:1234/v1")
                    self.assertEqual(model.metadata.model_name, "my-local-model")
                    self.assertTrue(model.metadata.is_chat_model)
                    self.assertEqual(model.temperature, temperature)

    def test_custom_model_stream_uses_real_compatible_transport(self):
        from llama_index.core.llms import ChatMessage, MessageRole
        def respond(request):
            payload = json.loads(request.content)
            self.assertEqual(payload["model"], "my-local-model")
            self.assertTrue(payload["stream"])
            self.assertEqual(request.url.path, "/v1/chat/completions")
            event = {"id": "test", "created": 1, "model": "my-local-model", "object": "chat.completion.chunk",
                     "choices": [{"index": 0, "delta": {"role": "assistant", "content": "READY"}, "finish_reason": None}]}
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  text="data: " + json.dumps(event) + "\n\ndata: [DONE]\n\n")
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            model = ollama.CompatibleChatLLM(model="my-local-model", api_key="test",
                api_base="http://local.test/v1", http_client=client, max_tokens=32, max_retries=0)
            answer = "".join(chunk.delta or "" for chunk in model.stream_chat([
                ChatMessage(role=MessageRole.USER, content="Hello")]))
        self.assertEqual(answer, "READY")

    def test_r2r_upload_contract_and_partial_ids(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.txt"
            path.write_text("fact")
            response = Mock()
            response.json.return_value = {"results": {"document_id": "owned"}}
            client = r2r.R2RClient()
            ids = []
            with patch.object(client, "_request", side_effect=[response, r2r.R2RConnectionError("failed")]) as request, patch.object(r2r, "uuid4", side_effect=["owned", "pending"]):
                with self.assertRaises(r2r.R2RConnectionError):
                    client.upload_documents([path, path], ids)
                self.assertEqual(ids, ["owned", "pending"])
                self.assertIn("file", request.call_args_list[0].kwargs["files"])
                self.assertEqual(request.call_args_list[0].kwargs["data"]["run_with_orchestration"], "false")
        with patch.object(client, "_request") as request:
            with self.assertRaises(r2r.R2RConnectionError):
                client.rag("unscoped")
            request.assert_not_called()
