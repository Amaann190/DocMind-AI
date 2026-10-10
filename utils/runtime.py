"""Reuse processing code from Streamlit or an isolated API request."""
from contextlib import contextmanager
from contextvars import ContextVar

_state = ContextVar("docmind_request_state", default=None)


class Runtime:
    @property
    def session_state(self):
        state = _state.get()
        if state is not None:
            return state
        import streamlit
        return streamlit.session_state


st = Runtime()


@contextmanager
def request_state(state):
    token = _state.set(state)
    try:
        yield
    finally:
        _state.reset(token)
