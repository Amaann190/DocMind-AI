"""Private temporary files owned by one Streamlit session."""

import tempfile
from pathlib import Path

from utils.runtime import st


def session_directory(kind, state=None):
    if kind not in {"data", "cache"}:
        raise ValueError("Unknown session directory")
    state = st.session_state if state is None else state
    if "_workspace" not in state:
        state["_workspace"] = tempfile.TemporaryDirectory(prefix="docmind_session_")
    directory = Path(state["_workspace"].name) / kind
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clear_session_workspace(state):
    workspace = state.pop("_workspace", None)
    if workspace is not None:
        workspace.cleanup()
