"""Request boundary for the local API: origin, client header and body size."""
from urllib.parse import urlparse

from fastapi import HTTPException, Response

from utils import helpers


def max_request_bytes():
    return helpers.MAX_TOTAL_UPLOAD_BYTES + 1024 * 1024


class RequestBodyLimit:
    """Count body bytes as they arrive.

    The Content-Length check in ``local_boundary`` cannot see chunked requests,
    which carry no length header; this caps them while they stream, before the
    multipart parser spools them to disk.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_request_bytes():
                    raise HTTPException(413, "Upload exceeds 100 MB")
            return message

        await self.app(scope, limited_receive, send)


async def local_boundary(request, call_next):
    if request.url.path.startswith("/api"):
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return Response("Cross-origin requests are not allowed", status_code=403)
        if request.method not in ("GET", "HEAD") and request.headers.get("x-docmind-client") != "react":
            return Response("Missing application request header", status_code=403)
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > max_request_bytes():
            return Response("Upload exceeds 100 MB", status_code=413)
    return await call_next(request)
