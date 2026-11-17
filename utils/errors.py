"""Exception groups shared by modules that talk to model servers."""
import httpx
import ollama

# Errors a model server or its client library raises when the server is
# unreachable, slow, missing a model or returns an unexpected payload.
# Catch this instead of a bare ``Exception`` around discovery and validation
# calls, so programming errors elsewhere still surface.
MODEL_SERVER_ERRORS = (
    ollama.ResponseError,
    httpx.HTTPError,
    ConnectionError,
    TimeoutError,
    OSError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
)
