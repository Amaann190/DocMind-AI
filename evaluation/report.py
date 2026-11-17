"""Write eval_results.json and eval_report.md."""
import json
import time
from pathlib import Path

from evaluation.fixtures import RETRIEVAL_CONFIGS


def _write_outputs(all_results, overall, out_dir="."):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"meta": {"generated": time.strftime("%Y-%m-%d %H:%M"),
                        "overall": overall}, "suites": all_results}
    (out_dir / "eval_results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    md = ["# DocMind evaluation report", "",
          f"Generated {time.strftime('%Y-%m-%d %H:%M')} · Mode: **{overall['mode']}**",
          f"Chat model: {overall['chat_model'] or 'not used'} · Embeddings: {overall['embedding_model']}", "",
          f"**{overall['passed']} passed · {overall['failed']} failed · {overall['skipped']} skipped**", "",
          "Scores describe these checks only, not general answer accuracy. Mock checks do not "
          "measure model quality. Skips are not passes. Rule-based answer checks require human "
          "review; valid citation numbers alone do not prove every claim is supported.", "",
          "| Suite | Passed | Failed | Skipped |", "|---|---:|---:|---:|"]
    counts = overall.get("answer_checks")
    if counts and any(counts.values()):
        md[6:6] = [f"Live-answer checks separately: **{counts['passed']} passed · {counts['failed']} failed · {counts['skipped']} skipped**", ""]
    for name, result in all_results.items():
        md.append(f"| {name} | {result['passed']} | {result['failed']} | {result['skipped']} |")
    summary = all_results.get("retrieval", {}).get("summary") or {}
    if "full_hit_rate" in summary:
        md.extend(["", "## Retrieval ablation", "",
                   f"{summary['answerable_queries']} answerable and {summary['no_match_queries']} unanswerable "
                   f"queries · embeddings: {summary['embedding']}. Hit = an expected source is retrieved; "
                   "rejection = nothing is retrieved for an unanswerable query. "
                   "Latency excludes generation; configuration order is rotated per query.", "",
                   "| Configuration | Answerable hit rate | Correct rejection | Mean retrieval ms |",
                   "|---|---:|---:|---:|"])
        for config in RETRIEVAL_CONFIGS:
            md.append(f"| {config} | {summary[config + '_hit_rate']:.0%} | {summary[config + '_rejection']:.0%} | "
                      f"{summary[config + '_avg_ms']} |")
    bench = all_results.get("benchmark", {}).get("summary")
    if bench:
        from evaluation.benchmark import markdown_report
        md.extend([""] + markdown_report(bench, bench.get("embedding", "")))
    for name, result in all_results.items():
        md.extend(["", f"## {name}", ""])
        for item in result["results"]:
            label = item.get("test", item.get("query", "check"))
            status = item.get("status", "passed" if item.get("pass") else "failed")
            detail = item.get("detail", "")
            if not detail and "full_hit" in item:
                detail = " · ".join(f"{config}: {'hit' if item[config + '_hit'] else 'miss'}"
                                    for config in RETRIEVAL_CONFIGS)
            md.append(f"- **{status.upper()} — {label}**: {detail}")
            if "answer" in item:
                md.append("  Answer: " + item["answer"].replace("\n", " "))
                md.append("  Sources: " + json.dumps(item.get("sources", [])))
    md.extend(["", "## Reproduce", "", "```bash",
               "pipenv run python eval_harness.py --mock --out output/eval-mock",
               f"pipenv run python eval_harness.py --chat-model {overall.get('chat_model') or 'llama3:latest'} --out output/eval-live",
               "```", ""])
    (out_dir / "eval_report.md").write_text("\n".join(md), encoding="utf-8")
    return out_dir / "eval_results.json", out_dir / "eval_report.md"
