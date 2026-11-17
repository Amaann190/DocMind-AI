"""Public retrieval benchmark: BEIR SciFact (Wadden et al., 2020; Thakur et al., 2021).

SciFact pairs 300 test claims with the scientific abstracts that support or
refute them, over a corpus of 5,183 abstracts. It is licensed CC BY-NC 2.0, so
the data is downloaded on demand into the git-ignored ``data/`` folder and only
results are committed. The download is pinned by SHA-256.

SciFact has no unanswerable queries, so it measures ranking (Recall@k, MRR@10,
nDCG@10), not abstention; the labelled DocMind benchmark covers rejection.
"""
import hashlib
import json
import math
import urllib.request
import zipfile
from pathlib import Path

SCIFACT_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip"
SCIFACT_SHA256 = "536e14446a0ba56ed1398ab1055f39fe852686ecad24a6306c80c490fa8e0165"
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "data" / "benchmarks"


def ensure_scifact(data_dir=DEFAULT_DIR):
    """Download (if needed), verify and extract SciFact; return the extracted folder."""
    data_dir = Path(data_dir)
    archive = data_dir / "scifact.zip"
    folder = data_dir / "scifact"
    if (folder / "corpus.jsonl").exists():
        return folder
    data_dir.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        urllib.request.urlretrieve(SCIFACT_URL, archive)  # noqa: S310 - fixed https URL, verified below
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SCIFACT_SHA256:
        archive.unlink()
        raise ValueError(f"SciFact download failed verification (sha256 {digest}).")
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (data_dir / member.filename).resolve()
            if not target.is_relative_to(data_dir.resolve()):
                raise ValueError(f"Unsafe path in archive: {member.filename}")
        bundle.extractall(data_dir)
    return folder


def load_scifact(folder, split="test"):
    """Return (corpus {id: text}, queries {id: text}, qrels {query_id: {doc_id: grade}})."""
    folder = Path(folder)
    corpus = {}
    with (folder / "corpus.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            corpus[row["_id"]] = f"{row.get('title', '').strip()}\n\n{row['text'].strip()}".strip()
    qrels = {}
    with (folder / "qrels" / f"{split}.tsv").open(encoding="utf-8") as handle:
        next(handle)  # header
        for line in handle:
            query_id, doc_id, grade = line.rstrip("\n").split("\t")
            if int(grade) > 0:
                qrels.setdefault(query_id, {})[doc_id] = int(grade)
    queries = {}
    with (folder / "queries.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["_id"] in qrels:
                queries[row["_id"]] = row["text"]
    return corpus, queries, qrels


def ndcg_at_k(ranked, grades, k):
    """Normalised discounted cumulative gain over the top k ranked ids."""
    dcg = sum(grades.get(doc_id, 0) / math.log2(position + 1)
              for position, doc_id in enumerate(ranked[:k], start=1))
    ideal = sorted(grades.values(), reverse=True)[:k]
    idcg = sum(grade / math.log2(position + 1) for position, grade in enumerate(ideal, start=1))
    return dcg / idcg if idcg else 0.0
