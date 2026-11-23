"""One-line summaries of every answers-*-full.json: SQuAD columns and injection suite."""
import json
from collections import Counter
from pathlib import Path

OUT = Path(r"paper/results")
MODELS = ["qwen2.5-0.5b", "qwen2.5-1.5b", "qwen2.5-3b", "qwen2.5-7b", "llama3.2-1b", "llama3.2-3b", "llama3.1-8b", "llama3-latest"]

for m in MODELS:
    d = json.loads((OUT / f"answers-{m}-full.json").read_text(encoding="utf-8"))
    s, recs = d["summary"], d["records"]
    ans = [r for r in recs if not r["unanswerable"]]
    wrong_ref = sum(1 for r in ans if r["refused"])
    c = s["answered_with_citation"]
    print(f"{m:14s} T={d['temperature']} ans={s['answerable_correct']['k']} unans={s['unanswerable_refused']['k']} "
          f"F1={s['answerable_mean_f1']:.3f} cited={c['k']}/{c['n']}={c['rate']:.3f} wrongref={wrong_ref} "
          f"s={s['mean_ms']/1000:.1f}")
    inj = s.get("injection")
    if inj:
        on, off = inj["filter_on"], inj["filter_off"]
        print(f"   inj on: attack {on['attack_success']['k']}/48 task {on.get('task_success',{}).get('k')} | "
              f"off: attack {off['attack_success']['k']}/48 task {off.get('task_success',{}).get('k')}")
        fam = {}
        for key in ("filter_on", "filter_off"):
            fams = inj[key].get("by_family") or {}
            fam[key] = {f: v.get("attack_success", v).get("k") if isinstance(v, dict) else v for f, v in fams.items()}
        print("   by family on:", {k: v for k, v in fam["filter_on"].items() if v}, " off:", {k: v for k, v in fam["filter_off"].items() if v})
print()
d = json.loads((OUT / "answers-qwen2.5-3b-full.json").read_text(encoding="utf-8"))
print("injection keys:", list(d["summary"]["injection"]["filter_on"]))
print("injection block keys:", list(d["injection"])[:10] if isinstance(d["injection"], dict) else type(d["injection"]))
