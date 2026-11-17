"""Loading source files into documents and building vector indexes."""
import fnmatch
import os
import re
from pathlib import Path

import utils.logs as logs
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.core.ingestion import run_transformations
from llama_index.core.node_parser import SentenceSplitter
from utils import runtime
from utils.llama_index.chunking import (
    _dedupe_exact_nodes,
    _merge_code_blocks,
    _prepend_document_title,
    _verbalize_tabular_docs,
)
from utils.llama_index.embeddings import ProgressReportingEmbedding
from utils.llama_index.settings import MIN_CHUNK_CHARS, _is_oom_error

EXCLUDED_FILE_PATTERNS = [
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.bmp", "*.ico", "*.svg", "*.webp",
    "*.zip", "*.tar", "*.gz", "*.bz2", "*.7z", "*.rar",
    "*.exe", "*.dll", "*.so", "*.dylib", "*.bin", "*.iso", "*.msi",
    "*.pyc", "*.pyo", "*.pyd", "*.class",
    "*.mp3", "*.mp4", "*.avi", "*.mov", "*.wav", "*.mkv",
    "*.git*", "*.venv*", "*node_modules*",
]


def load_documents(data_dir: str, input_files: list = None, errors: list = None):
    """Load readable files and append per-file failures to the optional errors list.

    Directory discovery uses one candidate list; a corrupt file cannot cause a
    fallback scan to read excluded or hidden files. An explicit empty selection
    never falls back to reading the directory. Fail if no readable text remains.
    """
    from utils.document_readers import document_file_extractors
    from utils.helpers import (
        MAX_TOTAL_UPLOAD_BYTES,
        MAX_UPLOAD_FILE_BYTES,
        validate_document_archive,
    )

    extractors = document_file_extractors()
    failures = errors if errors is not None else []
    paths = input_files if input_files is not None else SimpleDirectoryReader(
        input_dir=data_dir, recursive=True, exclude=EXCLUDED_FILE_PATTERNS,
    ).input_files
    if input_files is None:
        # Also check directory components: upstream directory-glob exclusion
        # differs between Windows and POSIX path separators.
        paths = [path for path in paths if not any(
            fnmatch.fnmatchcase(part.lower(), pattern.lower())
            for part in Path(os.path.relpath(path, data_dir)).parts
            for pattern in EXCLUDED_FILE_PATTERNS
        )]
    if not paths:
        raise ValueError("No files were selected to process.")
    if len(paths) > 1000:
        raise ValueError("Too many source files; process at most 1000 files at once.")
    documents = []
    total_bytes = 0
    for path in paths:
        try:
            resolved = Path(path).resolve()
            if not resolved.is_relative_to(Path(data_dir).resolve()) or Path(path).is_symlink():
                raise ValueError("File links outside the selected source are not allowed.")
            size = resolved.stat().st_size
            if size > MAX_UPLOAD_FILE_BYTES:
                raise ValueError("File exceeds the 25 MB extraction limit.")
            total_bytes += size
            if total_bytes > MAX_TOTAL_UPLOAD_BYTES:
                raise ValueError("Source files exceed the 100 MB extraction limit.")
            validate_document_archive(resolved)
            docs = SimpleDirectoryReader(
                input_files=[path], file_extractor=extractors,
                raise_on_error=True, errors="strict",
            ).load_data()
            docs = [doc for doc in docs if doc.get_content().strip()]
            if not docs:
                raise ValueError("No readable text found. The file may be empty or need OCR.")
            for doc in docs:
                doc.metadata["source_path"] = os.path.relpath(path, data_dir)
            documents.extend(docs)
        except Exception as err:
            reason = str(err.__cause__ or err)
            try:
                name = os.path.relpath(path, data_dir)
            except ValueError:  # Explicit paths can be on a different Windows drive.
                name = str(path)
            failures.append({"file": name, "error": reason})
            logs.log.warning(f"Skipping unreadable file {path}: {reason}")
    if not documents:
        details = "\n".join(f"{failure['file']}: {failure['error']}" for failure in failures)
        raise ValueError(f"No files could be loaded.\n{details}")
    documents = _verbalize_tabular_docs(documents)
    logs.log.info(f"Loaded {len(documents):,} documents; {len(failures)} files skipped")
    return documents


###################################
#
# Create Document Index
#
###################################


def create_index(documents, progress_callback=None, *, embed_model=None, chunk_size=None, chunk_overlap=None):
    """
    Creates an index from the provided documents and service context.

    Args:
        documents (list[str]): A list of strings representing the content of the documents to be indexed.

    Returns:
        An instance of `VectorStoreIndex`, containing the indexed data.

    Raises:
        Exception: If there is an error creating the index.

    Notes:
        The `documents` parameter should be a list of strings representing the content of the documents to be indexed.
    """

    try:
        embed_model = embed_model if embed_model is not None else runtime.st.session_state.get("embedding_model")
        if embed_model is None:
            raise ValueError("Configure an embedding model in this session before indexing.")
        config = runtime.st.session_state.get("embedding_config", {})
        splitter = SentenceSplitter(
            chunk_size=chunk_size if chunk_size is not None else config.get("chunk_size", 256),
            chunk_overlap=chunk_overlap if chunk_overlap is not None else config.get("chunk_overlap", 32),
        )
        # Keep website sections separate before token-sized splitting. Otherwise
        # a category heading can be detached from every example/link below it.
        from llama_index.core.node_parser import MarkdownNodeParser
        website_splitter = SentenceSplitter(chunk_size=splitter.chunk_size,
            chunk_overlap=splitter.chunk_overlap, paragraph_separator="\n")
        nodes = []
        for document in documents:
            if not document.metadata.get("source", "").startswith(("http://", "https://")):
                nodes.extend(run_transformations([document], [splitter], show_progress=True))
                continue
            sections = []
            for section in MarkdownNodeParser().get_nodes_from_documents([document]):
                parent = section.metadata.pop("header_path", "").strip("/")
                heading = re.match(r"^#{1,6}\s+(.+)", section.text)
                if heading and not section.text[heading.end():].strip():
                    continue  # The heading is carried by its child sections.
                label = " / ".join(part for part in (parent, heading[1] if heading else "") if part)
                if label:
                    section.metadata["section"] = label[-200:]
                for key in ("section", "title"):
                    section.excluded_embed_metadata_keys.append(key)
                    section.excluded_llm_metadata_keys.append(key)
                sections.append(section)
            nodes.extend(run_transformations(sections, [website_splitter], show_progress=True))

        # Keep code fences intact before any filtering — a ``` block split
        # across two chunks leaves an unclosed fence that confuses embeddings.
        nodes = _merge_code_blocks(nodes)

        # Preserve short codes, single-cell values, and other small facts.
        nodes = [
            node for node in nodes if len(node.get_content().strip()) >= MIN_CHUNK_CHARS
        ]
        nodes = _dedupe_exact_nodes(nodes)
        # Carry each chunk's document title into the chunk text itself, so
        # title-word queries match every chunk and small models can tell
        # which document a chunk belongs to.
        nodes = _prepend_document_title(nodes)
        if not nodes:
            raise ValueError(
                "No usable content was extracted from the documents. "
                "The files may be empty or contain only images."
            )

        if progress_callback is not None:
            progress_callback(0, len(nodes))
            embed_model = ProgressReportingEmbedding(
                wrapped_model=embed_model,
                progress_callback=progress_callback,
                model_name=embed_model.model_name,
                embed_batch_size=embed_model.embed_batch_size,
            )

        index = VectorStoreIndex(
            nodes=nodes,
            embed_model=embed_model,
            transformations=[splitter],
            show_progress=False,
        )

        logs.log.info("Index created from loaded documents successfully")

        return index
    except Exception as err:
        logs.log.error(f"Index creation failed: {err}")
        if _is_oom_error(err):
            raise Exception(
                "Not enough GPU memory to embed these documents. "
                "Try a smaller chunk size, fewer documents, or a smaller "
                "embedding model."
            ) from err
        raise Exception(f"Index creation failed: {err}")


###################################
#
# Index Cache (disk persistence)
#
###################################


def _document_text(document):
    if hasattr(document, "get_content"):
        return document.get_content() or ""
    if hasattr(document, "text"):
        return document.text or ""
    return str(document)
