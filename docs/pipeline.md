# Architecture

DocMind has a React/Vite frontend, a FastAPI backend and shared Python processing utilities.

1. React calls same-origin `/api` endpoints for settings, sources and conversations.
2. FastAPI selects an isolated workspace using an HttpOnly cookie.
3. Upload validation enforces names, extensions, sizes and archive expansion limits.
4. Readers extract text and metadata from 25 file types; websites require public HTTPS
   and GitHub inputs are normalized and cloned into a temporary session directory.
5. The backend builds an index with the selected embedding model. Hybrid retrieval
   combines vector similarity and keyword evidence.
6. Retrieved passages, bounded conversation history and the current question feed
   the selected chat model. Answers stream to React with citation data.
7. SQLite stores transcript text, title and citation passages.

Local document chat expands referential follow-ups with up to three recent user
questions before searching. Long earlier answers are shortened to preserve their
questions within the context budget. Source changes and turns explicitly sent
without documents are excluded; earlier model answers are never retrieval evidence.
Website ingestion retains absolute links and the main page content. Index chunks
carry their section headings, and an explicitly requested section takes precedence
over neighboring categories. Existing website sources need to be imported again
after this ingestion change.

`utils/runtime.py` supplies explicit context-local state through `request_state`.
There is no global UI/session fallback. Every API operation and evaluator supplies
its own state. Locks isolate mutations inside a workspace.

Source replacement/removal rebuilds the bounded local index before committing it;
a failed replacement retains the prior index. Source changes exclude older document
context from subsequent answers. Ingestion progress is exposed in API state.

Source bytes and indexes are temporary. Conversations persist in
`data/react-history.sqlite3`, or the directory specified by `DOCMIND_DATA_DIR`.
Saved chats share current sources. Serve the application with a single API worker.

R2R is an optional external ingestion/retrieval service. Remote document IDs are
tracked per active workspace and used to scope queries and cleanup.
