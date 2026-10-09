# Changelog

Release notes for DocMind are published with GitHub Releases:

https://github.com/Ashita-no-Kaushar/DocMind-AI/releases

## Vulnerability Disclosure in Release Notes

When a release fixes a publicly known runtime vulnerability in DocMind that already has a CVE or similar public identifier at release time, the release notes identify that vulnerability and summarize the upgrade impact.

If a release has no such vulnerability fixes, the release notes may omit this section.

## Versioning

DocMind release tags use semantic versioning, for example `v1.5.0`.

## [Unreleased]

- Remove dead dependencies (torch, torchvision, transformers, huggingface-hub, sentence-transformers, streamlit-tags, streamlit-extras, pyexiftool): the venv shrinks by ~500 MB and app startup is lighter; Ollama serves both embeddings and chat, so no local deep-learning stack is needed.
- Remove unused assets (demo.gif, logo.png) and the broken requirements.txt (Pipfile is the canonical dependency file).
- Remove unused imports in utils/rag_pipeline.py and two tests.

- Add optional R2R (RAG to Riches) backend: uploaded files are ingested, embedded and indexed on an R2R server instead of locally (less RAM, heat and disk use).
- Validate the embedding model against the live Ollama server before ingestion; clear guidance when it is missing or not embedding-capable.
- Handle GPU out-of-memory during embedding: batches are shrunk and retried automatically so ingestion completes instead of crashing.
- Make chunk overlap proportional to chunk size (percentage slider) instead of an absolute token count.
- Add a temperature setting for the LLM (persisted alongside the other settings).
- Add OpenAI-compatible backend support with presets for LM Studio (Local AI) and TabbyAPI: any server exposing the OpenAI API can serve chat and embeddings.
- Validate the chat model against the live Ollama server before ingestion; clear guidance when it is missing or not completion-capable.
- Expand upload file-type support (doc, html, rtf, odt, xlsx, eml, mbox, ...) while keeping executables and archives blocked.
- Add Eco Mode (Settings): embedding batches shrink to 4, answers cap at ~256 tokens, retrieval keeps at most 3 chunks and the context budget shrinks — less heat and faster answers on weak machines.
- Keep conversation history in RAG answers, so follow-up questions ("what about the second one?") resolve against the documents.
- Stem queries and index tokens (Porter) so "documents", "documented" and "documenting" all match — better retrieval without any extra compute.
- Skip embedding near-duplicate chunks (headers/footers/boilerplate), saving embedding work and heat.
- Add a per-conversation answer-tone selector above the chat input (overrides the Settings preset).
- Drop Hinglish/Hindi question fillers ("batao", "kya", "hai", ...) during retrieval so mixed-language queries find the right chunks.
- Offer "Ask without documents" when RAG finds no matches, so a failed retrieval can fall back to a general-knowledge answer.
- Add a Clear Chat button in the sidebar to keep the conversation (and each prompt) small on weak machines.
- Require keyword evidence for weakly-scored chunks: unrelated questions no longer pull irrelevant context (small embedding models score everything in a tight band), so the "could not find" fallback actually triggers.
- Prepend each chunk with its document's title: title-word queries ("annual report") now match every chunk of that document, and small models can tell which document a chunk belongs to.
- Expand short queries with curated keyword synonyms for BM25 only ("money back rules" finds the refund policy; the vector search stays untouched).
- Normalize tokenization: hyphens split ("30-days" matches "30 days") and stray single letters drop ("company's" -> "company").
- Tighten the grounded-answer template: quote exact numbers/dates/names, cite numbered chunks like (from [n]).
- Bump index cache version so existing caches rebuild once with the new chunking behavior.

## [v1.5.0] - 2026-08-15

- Fix GitHub repository ingestion failures caused by stale checkouts and transient Windows file locks.
- Purge stale `__pycache__` on startup so the app never runs outdated bytecode.
- Only load files that were just uploaded during ingestion (no stale-leftover pollution).
- Remove the Local Hugging Face embedding backend (Ollama embeddings only).
- Apply Top K / similarity threshold settings live; remove the dead Chat Mode setting.
- Retrieve document introductions for summary/about-the-document questions.
- Export chat history as a Word (.docx) document; remove the Custom answer-style preset.
- General reliability and security hardening.
