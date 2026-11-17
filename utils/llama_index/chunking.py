"""Chunk post-processing: titles, duplicate removal, tables and code blocks."""
import csv
import io
import json
import os

import utils.logs as logs


def _node_dedup_key(node):
    """Only identical text from the same source and location is redundant."""
    return (
        node.ref_doc_id or node.node_id,
        node.get_content(),
        json.dumps(node.metadata, sort_keys=True, default=str),
    )


def _dedupe_exact_nodes(nodes):
    """Preserve changed facts and separate sources, even when most words match."""
    deduped = []
    seen = set()
    for node in nodes:
        key = _node_dedup_key(node)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(node)
    return deduped


def _document_title(node, max_chars: int = 60) -> str:
    """Return a readable title for a node's source document.

    Derived from the file name ("annual_report.md" -> "Annual Report"), used
    as a lightweight title prefix on every chunk so chunks carry their
    document's identity into BM25 and embedding search.
    """
    metadata = node.metadata or {}
    section = metadata.get("section") or metadata.get("title")
    if section:
        return str(section)[-200:]
    file_name = metadata.get("file_name") or ""
    base = os.path.splitext(file_name)[0].replace("_", " ").replace("-", " ")
    title = " ".join(base.split())[:max_chars].strip()
    if title:
        title = title.title()
    return title or file_name


def _prepend_document_title(nodes):
    """Prefix each chunk with its document's title.

    Small local models answer "what is this document about" questions far
    better when every chunk carries the title line, and queries containing
    the title words ("annual report", "refund policy") match every chunk of
    that document instead of just the first one.
    """
    for node in nodes:
        title = _document_title(node)
        if title and not node.get_content().lstrip().lower().startswith(
            title.lower()
        ):
            node.text = f"{title}.\n\n{node.get_content()}"
    return nodes


def _verbalize_tabular_docs(documents):
    """Rewrite CSV/JSON documents into natural sentences for better retrieval.

    A raw CSV like 'id,info\\n1,HR leave 20 days' is poor for embedding
    search — the header and values are not linked as a sentence. Converting
    to 'Row 1: info is HR leave 20 days.' makes the fact retrievable.
    Pure Python, no model, negligible cost.
    """
    for doc in documents:
        fname = (doc.metadata or {}).get("file_name") or ""
        lower = fname.lower()
        text = doc.text or ""
        if not text.strip():
            continue
        # CSV / TSV
        if lower.endswith((".csv", ".tsv")):
            try:
                delimiter = "\t" if lower.endswith(".tsv") else ","
                reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
                if reader.fieldnames is None:
                    continue
                rows = list(reader)
                if not rows:
                    continue
                verbalized = []
                for idx, row in enumerate(rows, start=1):
                    parts = []
                    for k, v in row.items():
                        if k is None or v is None:
                            continue
                        k = str(k).strip()
                        v = str(v).strip()
                        if not k or not v:
                            continue
                        parts.append(f"{k} is {v}")
                    if parts:
                        verbalized.append(f"Row {idx}: " + ", ".join(parts) + ".")
                if verbalized:
                    title = _document_title(doc)  # type: ignore[arg-type]
                    header = f"{title}. " if title and title.lower() not in text.lower()[:80] else ""
                    new_text = header + "\n".join(verbalized) + f"\n\nOriginal table:\n{text}"
                    try:
                        doc.set_content(new_text)
                    except (AttributeError, TypeError, ValueError):
                        try:
                            doc.text = new_text
                        except (AttributeError, TypeError, ValueError):
                            object.__setattr__(doc, "text", new_text)
            except (csv.Error, ValueError) as err:
                logs.log.debug(f"Keeping original table text for {fname}: {err}")
                continue
        # JSON / JSONL
        elif lower.endswith((".json", ".jsonl")):
            try:
                data = (
                    [json.loads(line) for line in text.splitlines() if line.strip()]
                    if lower.endswith(".jsonl") else json.loads(text)
                )
                # Normalize to list of records
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list) or not data:
                    continue
                # Other JSON shapes retain their original text unchanged.
                if not all(isinstance(r, dict) for r in data):
                    continue
                verbalized = []
                for idx, rec in enumerate(data, start=1):
                    parts = []
                    for k, v in rec.items():
                        if v is None or str(v).strip() == "":
                            continue
                        parts.append(f"{k} is {v}")
                    if parts:
                        verbalized.append(f"Record {idx}: " + ", ".join(parts) + ".")
                if verbalized:
                    title = _document_title(doc)  # type: ignore[arg-type]
                    header = f"{title}. " if title and title.lower() not in text.lower()[:80] else ""
                    new_text = header + "\n".join(verbalized) + f"\n\nOriginal JSON:\n{text}"
                    try:
                        doc.set_content(new_text)
                    except (AttributeError, TypeError, ValueError):
                        try:
                            doc.text = new_text
                        except (AttributeError, TypeError, ValueError):
                            object.__setattr__(doc, "text", new_text)
            except ValueError as err:  # includes json.JSONDecodeError
                logs.log.debug(f"Keeping original JSON text for {fname}: {err}")
                continue
    return documents


def _merge_code_blocks(nodes):
    """Merge chunks split inside a markdown code fence (```).

    LlamaIndex splitters can cut a ```python block in half, leaving an
    unclosed fence that embeddings and small LLMs mis-handle. If a chunk
    contains an odd number of ``` fences, it is inside a code block that
    was split — merge it with the next chunk.
    """
    if not nodes:
        return nodes
    merged = []
    idx = 0
    while idx < len(nodes):
        node = nodes[idx]
        text = node.get_content()
        # Odd number of fences means we are inside an unclosed block
        if (
            text.count("```") % 2 == 1 and idx + 1 < len(nodes)
            and node.ref_doc_id is not None
            and node.ref_doc_id == nodes[idx + 1].ref_doc_id
        ):
            nxt = nodes[idx + 1]
            # Merge the two and keep the first node's metadata
            node.text = text + "\n\n" + nxt.get_content()
            # Preserve file_name, etc. from first node (already in metadata)
            merged.append(node)
            idx += 2  # skip next as merged
        else:
            merged.append(node)
            idx += 1
    return merged
