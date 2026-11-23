"""BEIR datasets beyond SciFact: verified download, loading and query splits.

NFCorpus, FiQA and ArguAna come from the BEIR mirror (Thakur et al., 2021). Archives are
pinned by SHA-256 and extracted into the git-ignored ``data/benchmarks`` folder;
only results are committed. FiQA's corpus is not indexed: its questions serve
as naturally written off-topic queries against scientific and nutrition corpora.
"""
import hashlib
import json
import random
import re
import urllib.request
import zipfile
from pathlib import Path

from evaluation.public import DEFAULT_DIR, SCIFACT_SHA256

BEIR_URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/{name}.zip"
SHA256 = {
    "scifact": SCIFACT_SHA256,
    "nfcorpus": "efe5be03f8c5b86a5870102d0599d227c8c6e2484328e68c6522560385671b0b",
    "fiqa": "32c7df99ed21252fdfb2cf3f5673502a8d245ee0c44c4a133570d92ce2b3ad02",
    "arguana": "ARGUANA_SHA_PLACEHOLDER",
}
# Query splits shipped in each archive. SciFact "train" and NFCorpus "dev" were never
# used while the retrieval pipeline was developed, so they serve as held-out checks.
SPLITS = {
    "scifact": ("train", "test"),
    "nfcorpus": ("train", "dev", "test"),
    "fiqa": ("train", "dev", "test"),
    "arguana": ("test",),
}


def ensure_beir(name, data_dir=DEFAULT_DIR):
    """Download (if needed), verify and extract a BEIR dataset; return its folder."""
    if name not in SHA256:
        raise ValueError(f"Unknown BEIR dataset {name!r}")
    data_dir = Path(data_dir)
    folder = data_dir / name
    if (folder / "queries.jsonl").exists():
        return folder
    data_dir.mkdir(parents=True, exist_ok=True)
    archive = data_dir / f"{name}.zip"
    if not archive.exists():
        urllib.request.urlretrieve(BEIR_URL.format(name=name), archive)  # noqa: S310 - fixed https URL, verified below
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", SHA256[name]):
        # Not pinned yet: report the digest of the download (kept on disk) instead of trusting it.
        raise ValueError(f"{name} is not pinned yet; the downloaded archive has sha256 {digest}. "
                         "Check it, then put it in beir.SHA256.")
    if digest != SHA256[name]:
        archive.unlink()
        raise ValueError(f"{name} download failed verification (sha256 {digest}).")
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (data_dir / member.filename).resolve()
            if not target.is_relative_to(data_dir.resolve()):
                raise ValueError(f"Unsafe path in archive: {member.filename}")
        bundle.extractall(data_dir)
    return folder


def load_corpus(folder):
    """Return {doc_id: "title\\n\\ntext"}."""
    corpus = {}
    with (Path(folder) / "corpus.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            corpus[row["_id"]] = f"{row.get('title', '').strip()}\n\n{row['text'].strip()}".strip()
    return corpus


def available_splits(name):
    """Query splits that exist for a BEIR dataset."""
    if name not in SPLITS:
        raise ValueError(f"Unknown BEIR dataset {name!r}")
    return SPLITS[name]


def load_split(folder, split):
    """Return (queries {id: text}, qrels {id: {doc_id: grade}}) for queries judged in ``split``."""
    folder = Path(folder)
    qrels = {}
    path = folder / "qrels" / f"{split}.tsv"
    if not path.exists():
        raise ValueError(f"{folder.name} has no {split!r} split (found: "
                         f"{sorted(p.stem for p in (folder / 'qrels').glob('*.tsv'))})")
    with path.open(encoding="utf-8") as handle:
        next(handle)
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
    return queries, {query_id: qrels[query_id] for query_id in queries}


def sample(mapping, n, seed=13):
    """Deterministic sample of up to ``n`` items from a dict, preserving key order of the sample."""
    keys = sorted(mapping)
    random.Random(seed).shuffle(keys)
    return {key: mapping[key] for key in keys[:n]}
