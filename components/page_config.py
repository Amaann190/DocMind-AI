import streamlit as st


def set_page_config():
    if "sidebar_state" not in st.session_state:
        st.session_state["sidebar_state"] = "expanded"

    st.set_page_config(
        page_title="DocMind AI",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state=st.session_state["sidebar_state"],
        menu_items={
            "Get Help": "https://github.com/Ashita-no-Kaushar/DocMind-AI/discussions",
            "Report a bug": "https://github.com/Ashita-no-Kaushar/DocMind-AI/issues",
        },
    )

    st.markdown(
        r"""
    <style>
    /* Hide Streamlit chrome */
    .stDeployButton, [data-testid="stDeployButton"],
    [data-testid="stToolbar"], [data-testid="stHeaderActionElements"],
    #MainMenu, footer { visibility: hidden !important; display: none !important; }
    header[data-testid="stHeader"] { background: transparent !important; }

    /* Centered readable width */
    .block-container {
            max-width: 780px;
            margin-left: auto;
            margin-right: auto;
            padding-top: 1.0rem;
            padding-bottom: 1rem;
        }

    /* Subtle chat bubbles */
    [data-testid="stChatMessage"] { padding: 0.6rem 0.85rem; }
    [data-testid="stChatMessage"] p { line-height: 1.55; }

    /* Suggestion pills — simple */
    div[data-testid="stPills"] { gap: 6px !important; }
    div[data-testid="stPills"] button {
            border-radius: 999px !important; font-size: 0.83rem !important;
            padding: 6px 12px !important;
        }
    </style>
    """,
        unsafe_allow_html=True,
    )
