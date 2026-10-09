import unittest
from unittest.mock import patch
from components.tabs import settings as settings_tab
class _Container:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, traceback):
        return False
class _StreamlitStub:
    def __init__(self, state):
        self.session_state = state
        self.selectbox_calls = []
        self.radio_calls = []
    def header(self, *args, **kwargs):
        pass
    def caption(self, *args, **kwargs):
        pass
    def subheader(self, *args, **kwargs):
        pass
    def container(self, *args, **kwargs):
        return _Container()
    def text_input(self, *args, **kwargs):
        pass
    def number_input(self, *args, **kwargs):
        return self.session_state.get(kwargs.get("key"))
    def selectbox(self, label, options, **kwargs):
        self.selectbox_calls.append((label, kwargs))
        return self.session_state.get(kwargs.get("key"))
    def radio(self, label, options, **kwargs):
        self.radio_calls.append((label, kwargs))
        return self.session_state.get(kwargs.get("key"), options[0] if options else None)
    def button(self, *args, **kwargs):
        pass
    def toggle(self, *args, **kwargs):
        pass
    def slider(self, label, **kwargs):
        return self.session_state.get(kwargs.get("key"), kwargs.get("value", 12))
    def select_slider(self, label, options, **kwargs):
        return self.session_state.get(kwargs.get("key"), options[0])
    def write(self, *args, **kwargs):
        pass
    def download_button(self, *args, **kwargs):
        pass
    def text_area(self, *args, **kwargs):
        pass
    def info(self, *args, **kwargs):
        pass
    def success(self, *args, **kwargs):
        pass
    def error(self, *args, **kwargs):
        pass
    def expander(self, *args, **kwargs):
        return _Container()
    def divider(self, *args, **kwargs):
        pass
    def markdown(self, *args, **kwargs):
        pass
class SettingsTabTests(unittest.TestCase):
    def test_keyed_selectboxes_do_not_pass_explicit_default_indexes(self):
        state = {
            "advanced": False,
            "llm_backend": "Ollama",
            "ollama_endpoint": "http://localhost:11434",
            "ollama_models": ["llama3:8b", "gemma4:latest"],
            "selected_model": "gemma4:latest",
            "ollama_embedding_models": ["nomic-embed-text", "embeddinggemma"],
            "ollama_embedding_model": "embeddinggemma",
            "messages": [],
        }
        streamlit = _StreamlitStub(state)
        with patch("components.tabs.settings.st", streamlit):
            settings_tab.settings()
        keyed_selectboxes = {
            kwargs["key"]: kwargs
            for _, kwargs in streamlit.selectbox_calls
            if "key" in kwargs
        }
        self.assertNotIn("index", keyed_selectboxes["selected_model"])
        self.assertNotIn("index", keyed_selectboxes["ollama_embedding_model"])

    def test_advanced_settings_apply_temperature_and_proportional_overlap(self):
        state = {
            "advanced": True,
            "llm_backend": "Ollama",
            "ollama_endpoint": "http://localhost:11434",
            "ollama_models": ["llama3:8b"],
            "selected_model": "llama3:8b",
            "ollama_embedding_models": ["nomic-embed-text"],
            "ollama_embedding_model": "nomic-embed-text",
            "top_k": 3,
            "similarity_cutoff": 0.3,
            "chunk_size": 256,
            "chunk_overlap_pct": 12,
            "temperature": 0.8,
            "messages": [],
        }
        streamlit = _StreamlitStub(state)
        with patch("components.tabs.settings.st", streamlit):
            settings_tab.settings()
        self.assertEqual(state["temperature"], 0.8)
        self.assertEqual(state["chunk_overlap"], 30)
        self.assertEqual(state["chunk_overlap_pct"], 12)
if __name__ == "__main__":
    unittest.main()
