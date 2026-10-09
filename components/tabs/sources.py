import streamlit as st

from components.tabs.local_files import local_files
from components.tabs.github_repo import github_repo
from components.tabs.website import website
from components.ingestion_prerequisites import (
    ingestion_is_configured,
    render_ingestion_settings_warning,
)


def sources():
    st.title("Directly import your data")
    st.caption("Convert your data into embeddings for utilization during chat")
    st.write("")

    if not ingestion_is_configured():
        render_ingestion_settings_warning()
        st.write("")

    with st.expander("💻 &nbsp; **Local Files**", expanded=False):
        local_files()

    with st.expander("🗂️ &nbsp;**GitHub Repo**", expanded=False):
        github_repo()

    with st.expander("🌐 &nbsp; **Website**", expanded=False):
        website()

    with st.expander("💡 &nbsp; **Cooling & Speed Tips**", expanded=False):
        st.markdown(
            "- **Prefer short documents:** 10-20 page PDFs (or `.txt`/`.md`) embed in seconds. "
            "A 300-page book takes minutes and heats the laptop.\n"
            "- **Don't re-upload the same files:** every upload re-embeds everything from scratch. "
            "Reuse the existing index instead — just chat.\n"
            "- **Split big documents** into chapters/sections and ingest only what you need.\n"
            "- **Limit sources:** 1-2 websites or one small GitHub repo at a time.\n"
            "- **Chat is cheap:** Q&A uses a tiny model on your GPU (~0.5s per answer). "
            "Ingestion is the heavy part.\n"
            "- **When idle** the GPU drops to ~40°C within a minute."
        )
