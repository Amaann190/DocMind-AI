"""Architecture suite: settings, export and import boundaries."""
import sys
from functools import partial
from pathlib import Path

from evaluation.common import _check, _setup_runtime_state, summarize_results


def suite_architecture(mock: bool):
    print("\n[Suite] Architecture & Features")
    results = []
    check = partial(_check, results)

    def t_presets():
        from typing import get_args

        from backend.settings import Settings
        presets = get_args(Settings.model_fields["provider"].annotation)
        ok = {"Ollama", "OpenAI", "LM Studio (Local AI)"}.issubset(presets)
        return ok, f"presets={presets}"
    check("backend_presets", t_presets)

    def t_export():
        from unittest.mock import patch

        from backend.routes.conversations import export
        with patch("backend.routes.conversations.get_session", return_value={"messages": [
            {"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi there"}]}):
            data = export(None).body
        ok = len(data) > 1000 and data[:2] == b"PK"  # docx is zip
        return ok, f"docx {len(data)} bytes"
    check("export_docx", t_export)

    def t_api_settings():
        from backend.settings import Settings
        public = Settings(api_key="private").model_dump(exclude={"api_key", "r2r_key"})
        return "api_key" not in public and public["provider"] == "Ollama", "Public settings exclude credentials"
    check("api_settings", t_api_settings)

    def t_ollama_helpers():
        from utils.ollama import _estimate_tokens, _trim_history
        _setup_runtime_state()
        est = _estimate_tokens("hello world")
        ok1 = est == 2 or est == 3
        # trim history keeps most recent
        from llama_index.core.llms import ChatMessage, MessageRole
        msgs = [ChatMessage(role=MessageRole.USER, content="a" * 4000), ChatMessage(role=MessageRole.USER, content="short")]
        trimmed = _trim_history(msgs, budget_tokens=10)
        ok2 = len(trimmed) <= 2
        return (ok1 and ok2), f"estimate={est} trim={len(trimmed)}"
    check("ollama_helpers", t_ollama_helpers)

    def t_embedding_verify_mock():
        from unittest.mock import patch

        from utils.llama_index import verify_embedding_model
        class FakeClient:
            def __init__(self, *a, **kw): pass
            def list(self): return {"models": [{"model": "nomic-embed-text:latest"}]}
            def show(self, m): return {"capabilities": ["embedding"]}
        with patch("utils.llama_index.embeddings.ollama.Client", FakeClient):
            ok = verify_embedding_model("nomic-embed-text:latest", "http://localhost:11434")
        return ok, "mock verify"
    check("embedding_verify", t_embedding_verify_mock)

    def t_r2r_mock():
        from unittest.mock import patch

        from utils import r2r as r2r_mod
        with patch.object(r2r_mod, "get_client") as gc:
            gc.return_value.health.return_value = True
            ok = r2r_mod.get_client().health() is True
            return ok, "health mocked"
    check("r2r_health", t_r2r_mock)

    def t_import_boundaries():
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_import_boundaries.py"],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, timeout=60, check=False,
        )
        return result.returncode == 0, "Fresh-process import checks: " + result.stderr[-200:]
    check("no_torch_at_import", t_import_boundaries)

    return summarize_results("architecture", results)
