"""DocMind local API: FastAPI app assembly. Run one worker; document state stays in this process.

Modules: ``workspace`` (sessions and conversation state), ``sources`` (source
lifecycle and indexing), ``security`` (request boundary), ``settings`` and
``routes/`` (HTTP endpoints). Names below are re-exported for tests and tools
that import ``backend.app``.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.staticfiles import StaticFiles

from backend import history  # noqa: F401
from backend.routes import chat, conversations, session, sources
from backend.security import RequestBodyLimit, local_boundary, max_request_bytes  # noqa: F401
from backend.settings import Settings  # noqa: F401
from backend.sources import commit_documents, tag_documents  # noqa: F401
from backend.workspace import (  # noqa: F401
    COOKIE,
    open_conversation,
    operation,
    save_conversation,
    sessions,
    start_title,
)
from utils import helpers, ollama  # noqa: F401
from utils import llama_index as indexer  # noqa: F401
from utils.r2r import R2RClient  # noqa: F401

app = FastAPI(title="DocMind Workspace", docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
app.add_middleware(RequestBodyLimit)
app.middleware("http")(local_boundary)
for module in (session, sources, conversations, chat):
    app.include_router(module.router)


dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        return FileResponse(dist / "index.html")
