"""Request-local processing state shared by the API and offline evaluation."""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

_state: ContextVar[dict[str, Any] | None] = ContextVar("docmind_request_state", default=None)


class Runtime:
    @property
    def session_state(self) -> dict[str, Any]:
        state = _state.get()
        if state is not None:
            return state
        raise RuntimeError("Processing requires an explicit request_state context.")


st = Runtime()


@contextmanager
def request_state(state):
    token = _state.set(state)
    try:
        yield
    finally:
        _state.reset(token)
