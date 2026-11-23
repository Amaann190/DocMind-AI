# Results-paper artifact

Material behind *Experimental Evaluation of DocMind AI: Hybrid Retrieval and Evidence-Floor Abstention in Local RAG*.

## Contents

- `results/`: per-query JSON for every run reported in the paper (rankings, answers, end-to-end and resource runs). These are copies of `output/research/`, which is ignored by git.
- `squad_adjudication.csv`: the re-examination of the 100 nominally unanswerable SQuAD 2.0 questions. It includes each question's label (`answerable`, `partial` or `unrelated`), the evidence paragraph and quote, the accepted answer and per-model grades.
- `analysis/`: the scripts that computed the paper's statistics from `results/`. These include paired and article-level bootstraps, TOST, Holm correction, calibration in every direction, lenient refusal detection, end-to-end transitions, repeatability and prompt comparisons.

## Reproducing

Run experiments from the repository root with the project environment:

```bash
python -m evaluation.overnight            # runs every job in evaluation/overnight_jobs.json, skipping finished ones
python -m evaluation.research sweep --dataset scifact --model nomic-embed-text:latest --plain --keyword-min-terms 2
python -m evaluation.research answers --chat-model llama3:latest
python -m evaluation.research endtoend --chat-model llama3:latest
python -m evaluation.research resources --chat-model llama3.2:3b --eco on
```

Run the analysis scripts from the repository root. For example:

```bash
python paper/analysis/reanalysis.py
python paper/analysis/t1.py
```

They read `paper/results/` and were written for one-off use, so some expect helper outputs from earlier scripts (see `common_sw.py`).

Ollama model digests, versions and settings are listed in the paper's reproducibility section. GPU embeddings and Ollama decoding are not guaranteed to be bit-reproducible across days.
