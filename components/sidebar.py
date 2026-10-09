import streamlit as st

from components.page_state import WELCOME_MESSAGE
from components.tabs.sources import sources
from components.tabs.settings import settings
from utils.browser_settings import persist_settings_to_browser_storage
from utils.r2r import r2r_is_ready


def reset_project():
    """Flag a full project reset; performed in set_initial_state before any
    widget is instantiated (widget keys can't be changed after their widget)."""
    st.session_state["reset_requested"] = True


def sidebar():
    with st.sidebar:
        tab1, tab2 = st.sidebar.tabs(["Data Sources", "Settings"])

        with tab1:
            sources()

        with tab2:
            settings()

        st.divider()

        # Status Badge
        if st.session_state.get("reset_error"):
            st.error(st.session_state["reset_error"])
        if r2r_is_ready(st.session_state):
            st.success("🟢 **R2R Mode**: Grounded via R2R backend")
        elif st.session_state.get("query_engine"):
            st.success("🟢 **RAG Mode**: Grounded in documents")
        else:
            st.info("💬 **Chat Mode**: Direct LLM conversation")

        with st.expander("🧹 Clear Chat & Reset", expanded=False):
            if st.button("💬 Clear Chat", use_container_width=True):
                st.session_state["messages"] = [dict(WELCOME_MESSAGE)]
                st.session_state["last_doc_sources"] = []
                st.session_state["last_rag_no_result"] = False
                st.session_state["last_rag_question"] = None
                st.session_state["rag_history_start"] = 0
                st.session_state["chat_history_start"] = 0
                st.rerun()

            st.markdown(
                "Clears only the conversation above. To wipe everything "
                "(indexes, uploads, settings), use **Reset Project** below."
            )

            # Reset Project (danger zone)
            st.warning(
                "Deletes this session's indexes, uploads, and its tracked R2R documents, "
                "clears credentials, and restores default settings. "
                "If remote cleanup fails, reset pauses so you can retry."
            )
            if st.checkbox("I understand", key="confirm_project_reset"):
                if st.button("Yes, reset everything", use_container_width=True):
                    reset_project()
                    st.rerun()

        persist_settings_to_browser_storage()
