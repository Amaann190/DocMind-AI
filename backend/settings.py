"""Validated model and retrieval settings for one workspace."""
import os
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


class Settings(BaseModel):
    provider: Literal["Ollama", "OpenAI", "LM Studio (Local AI)", "TabbyAPI"] = "Ollama"
    endpoint: str = Field(default_factory=lambda: os.environ.get("DOCMIND_OLLAMA_ENDPOINT", "").strip() or "http://localhost:11434")
    chat_model: str = "llama3:latest"
    embedding_model: str = "nomic-embed-text:latest"
    api_key: str = ""
    style: Literal["Balanced", "Concise", "Detailed", "Bulleted", "Technical", "Simple"] = "Balanced"
    temperature: float = Field(default=.4, ge=0, le=1.5)
    top_k: int = Field(default=3, ge=1, le=10)
    chunk_size: int = Field(default=256, ge=64, le=8192)
    overlap: int = Field(default=32, ge=0, le=4096)
    similarity: float = Field(default=.3, ge=0, le=1)
    eco: bool = False
    # Opt-in: save sources on disk so they survive a backend restart (backend/source_store.py).
    keep_sources: bool = False
    r2r: bool = False
    r2r_url: str = "http://localhost:7272"
    r2r_key: str = ""

    @model_validator(mode="after")
    def validate_settings(self):
        for address in (self.endpoint, self.r2r_url):
            url = urlparse(address)
            if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError("Use a server URL without embedded credentials, query or fragment.")
        if self.overlap >= self.chunk_size:
            raise ValueError("Chunk overlap must be smaller than chunk size.")
        return self
