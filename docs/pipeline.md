# RAG Pipeline

DocMind builds an in-memory LlamaIndex query engine from one source at a time: local file uploads, a GitHub repository clone, or fetched website documents.

## Ingestion Flow

1. Validate the current Ollama chat model and embedding settings.
2. Initialize the selected Ollama chat model.
3. Configure the embedding backend:
   - Ollama embeddings through the configured Ollama endpoint
4. Load documents:
   - Local files and GitHub repositories are loaded with LlamaIndex `SimpleDirectoryReader`.
   - Each file is read separately; failures and files with no readable text are reported by name.
   - Directory exclusions remain in effect when a file fails. An empty explicit selection reads nothing.
   - Websites are fetched with request size, redirect, content type, and network guardrails, then converted to text.
5. Validate ingestion limits:
   - At most 300 loaded documents
   - At most 4,194,304 extracted and preprocessed text characters; exceeding this fails explicitly
6. Split documents into chunks using the configured chunk size and chunk overlap.
   Preserve short facts and distinct evidence. Remove only exact duplicates from
   the same source and location; never merge code chunks across source documents.
7. Generate embeddings and display exact progress while indexing.
8. Create a streaming LlamaIndex query engine with the configured `top_k` and response mode.
9. Remove this operation's temporary upload or clone directory on success or failure.

Models, embedding configuration and caches belong to the current Streamlit session.
The pipeline passes model objects explicitly to LlamaIndex instead of changing its
process-wide Settings. Cache keys include backend/endpoint, chunk settings, record
boundaries and source metadata. Cache reuse and pruning stay within the owning
session; reset cannot delete another session's documents or indexes.

## Source-Specific Stages

The UI stores completed ingestion stages in Streamlit session state so reruns can show the current status without reprocessing unchanged inputs.

Partial imports retain a skipped-file count and per-file reasons on rerun. A batch
with no readable content cannot report success. Reprocessing clears the old report.

- Local files: files uploaded, documents loaded, embeddings generated, index ready
- GitHub repositories: repository validated, repository cloned, repository files loaded, embeddings generated, index ready
- Websites: websites fetched, website content loaded, embeddings generated, index ready

## Key Parameters

Users can adjust these advanced settings:

1. **`top_k`**: Number of similar chunks retrieved for each query. Higher values provide more context but may add noise. Applies to the next query immediately.
2. **`similarity_cutoff`**: Minimum vector similarity score for a chunk to be used. Higher = only strong matches (less hallucination), lower = more recall. `0` disables the filter. Applies to the next query immediately.
3. **`chunk_size`**: Maximum size of each text chunk before embedding. Smaller chunks can improve precision but increase embedding work. Applies to the next ingestion.
4. **`chunk_overlap`**: Overlap between consecutive chunks. This must be greater than or equal to `0` and less than `chunk_size`. Applies to the next ingestion.

## Runtime State

A successful RAG conversation requires:

- `llm`: the initialized Ollama LLM
- `documents`: loaded source documents
- `query_engine`: the LlamaIndex query engine

If any of these are missing, ingestion did not complete and chat is blocked until data is imported successfully.
