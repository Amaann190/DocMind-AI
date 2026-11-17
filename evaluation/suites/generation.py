"""Generation suite: prompt guards, helpers and live answer checks."""
from functools import partial

from evaluation.common import _check, _setup_runtime_state, summarize_results


def suite_generation(mock: bool, endpoint="http://localhost:11434", model="nomic-embed-text:latest", chat_model="llama3:latest"):
    print("\n[Suite] Generation (RAG answer quality)")
    results = []

    check = partial(_check, results)

    # 1 — TEXT_QA_TEMPLATE exists and has required guards
    def t_template():
        from utils.llama_index import TEXT_QA_TEMPLATE
        tmpl = TEXT_QA_TEMPLATE.template if hasattr(TEXT_QA_TEMPLATE, "template") else str(TEXT_QA_TEMPLATE)
        ok = "ONLY the context" in tmpl and "could not find" in tmpl.lower() and "{context_str}" in tmpl
        return ok, f"has_guards={ok} len={len(tmpl)}"
    check("qa_template_guards", t_template)

    # 2 — _rewrite_query / BM25 helpers (covers stemming, Hinglish, hyphen)
    def t_query_helpers():
        from utils.llama_index import _bm25_expanded_tokens, _bm25_tokens, _rewrite_query
        ok1 = _bm25_tokens("30-day guarantee's") == ["30", "day", "guarante"]
        ok2 = "batao" not in _rewrite_query("batao refund policy kya hai")
        ok3 = "return" in _bm25_expanded_tokens(["refund", "polici"])
        return (ok1 and ok2 and ok3), f"hyphen={ok1} hinglish={ok2} synonym={ok3}"
    check("query_helpers", t_query_helpers)

    # 3 — context_chat no-hallucination fallback (mock retriever returns [])
    def t_no_hallucination():
        from unittest.mock import MagicMock, patch

        from utils import ollama as oll_mod
        from utils.runtime import st
        # fake retriever that returns []
        fake_qe = MagicMock()
        fake_qe._retriever = MagicMock()
        fake_qe._retriever.retrieve.return_value = []
        # ensure st.session_state has needed keys
        _setup_runtime_state()
        st.session_state["retriever"] = fake_qe._retriever
        st.session_state["query_engine"] = fake_qe
        # mock LLM to ensure not called
        with patch.object(oll_mod, "create_llm") as mock_llm:
            from utils.ollama import context_chat
            chunks = list(context_chat("quantum physics", query_engine=fake_qe))
            text = "".join(chunks)
            ok = "could not find" in text.lower() and not mock_llm.called
            return ok, f"fallback={'hit' if ok else 'miss'}"
    check("no_hallucination_fallback", t_no_hallucination)

    # 4 — tone presets produce distinct prompts
    def t_tone():
        from typing import get_args

        from backend.settings import Settings
        from backend.workspace import configure, new_session
        styles = get_args(Settings.model_fields["style"].annotation)
        state = new_session()
        prompts = {}
        for style in styles:
            state["config"] = Settings(style=style)
            configure(state)
            prompts[style] = state["system_prompt"]
        ok = len(set(prompts.values())) == len(styles)
        return ok, f"presets={len(prompts)} distinct={ok}"
    check("tone_presets", t_tone)

    # 5 — multi-turn: context_chat includes history
    def t_multiturn():
        from unittest.mock import MagicMock, patch

        from llama_index.core.schema import NodeWithScore, TextNode

        from utils import ollama as oll_mod
        from utils.runtime import st
        _setup_runtime_state()
        st.session_state["messages"] = [
            {"role": "user", "content": "What is refund policy?"},
            {"role": "assistant", "content": "30 days."},
        ]
        st.session_state["system_prompt"] = "You are DocMind AI."
        # retriever returns one node
        node = TextNode(text="Refund 30 days.", metadata={"file_name": "refund_policy.txt"})
        fake_retriever = MagicMock()
        fake_retriever.retrieve.return_value = [NodeWithScore(node=node, score=0.9)]
        fake_qe = MagicMock()
        fake_qe._retriever = fake_retriever
        st.session_state["retriever"] = fake_retriever
        st.session_state["query_engine"] = fake_qe
        captured = {}
        fake_llm = MagicMock()
        def fake_stream(messages):
            captured["messages"] = messages
            yield type("obj", (), {"delta": "ok"})()
        fake_llm.stream_chat.side_effect = fake_stream
        with patch.object(oll_mod, "create_llm", return_value=fake_llm):
            from utils.ollama import context_chat
            list(context_chat("and for electronics?", query_engine=fake_qe))
            msgs = captured.get("messages", [])
            # history should be included (2 prior + system + current)
            ok = len(msgs) >= 3
            return ok, f"messages_in_prompt={len(msgs)}"
    check("multi_turn_history", t_multiturn)

    from eval_quality import evaluate_answers
    results.extend(evaluate_answers(mock, endpoint, model, chat_model))

    return summarize_results("generation", results)
