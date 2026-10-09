# DocMind evaluation report

Generated 2026-10-06 21:30 · Mode: **live**
Chat model: llama3:latest · Embeddings: nomic-embed-text:latest

**36 passed · 2 failed · 0 skipped**

Scores describe these checks only, not general answer accuracy. Mock checks do not measure model quality. Skips are not passes. Rule-based answer checks require human review; valid citation numbers alone do not prove every claim is supported.

| Suite | Passed | Failed | Skipped |
|---|---:|---:|---:|
| generation | 36 | 2 | 0 |

## generation

- **PASSED — qa_template_guards**: has_guards=True len=579
- **PASSED — query_helpers**: hyphen=True hinglish=True synonym=True
- **PASSED — no_hallucination_fallback**: fallback=hit
- **PASSED — tone_presets**: presets=6 distinct=True
- **PASSED — multi_turn_history**: messages_in_prompt=5
- **PASSED — refund_days**: All checks passed
  Answer: According to the provided document, general purchases may be returned within (from [1]): 30 days.
  Sources: [["refund.txt", 0.7382023495609842]]
- **PASSED — electronics_exception**: All checks passed
  Answer: According to the provided document, electronics can be returned within 15 days. (from [1])
  Sources: [["refund.txt", 0.7807787269762876]]
- **PASSED — exact_numbers**: All checks passed
  Answer: According to the provided document, the revenue in 2024 was $4.2 million, and it grew by 23%. (from [1])
  Sources: [["annual.txt", 0.6930001008250753]]
- **PASSED — different_source_policies**: All checks passed
  Answer: According to the provided documents, the return deadlines for Orion Store and Vega Store are:  * Orion Store: 14 days (from [2]) * Vega Store: 45 days (from [1])  Therefore, Vega Store has a longer return deadline compared to Orion Store.
  Sources: [["vega.txt", 0.7159375765731617], ["orion.txt", 0.7151827404093326]]
- **PASSED — unrelated_question**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: []
- **PASSED — missing_detail**: All checks passed
  Answer: I could not find this information in the documents.
  Sources: [["refund.txt", 0.6506626499036163]]
- **PASSED — document_instruction_injection**: All checks passed
  Answer: According to the provided context, the approved launch code is "ANCHOR-5317" (from [1]).
  Sources: [["launch.txt", 0.7545405586184265]]
- **PASSED — follow_up**: All checks passed
  Answer: Electronics may be returned within 15 days. (from [1])
  Sources: [["refund.txt", 0.5311019671215664]]
- **PASSED — format.csv**: All checks passed
  Answer: (from [1]): The approval code for Engine is ORBIT-7429.
  Sources: [["sample.csv", 0.6873749213983936]]
- **PASSED — format.doc**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.doc", 0.7585938561591514]]
- **PASSED — format.docx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.docx", 0.7439870285641141]]
- **PASSED — format.eml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.eml", 0.7426068143586517]]
- **PASSED — format.epub**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.epub", 0.7647639160859168]]
- **PASSED — format.htm**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.htm", 0.7542847627817697]]
- **PASSED — format.html**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.html", 0.7671323267505854]]
- **PASSED — format.ipynb**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.ipynb", 0.7191325197608931]]
- **PASSED — format.json**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.json", 0.6537315536148981]]
- **FAILED — format.jsonl**: Failed: citations, expected_cited_sources
  Answer: The launch approval code is ORBIT-7429. (from [2])
  Sources: [["sample.jsonl", 0.6956115390501233]]
- **PASSED — format.markdown**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.markdown", 0.7844642794959525]]
- **PASSED — format.mbox**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.mbox", 0.7351937489735545]]
- **PASSED — format.md**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.md", 0.7770895139969903]]
- **PASSED — format.mhtml**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.mhtml", 0.7524973627783709]]
- **PASSED — format.msg**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.msg", 0.7647251289259867]]
- **PASSED — format.odt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.odt", 0.744553801384702]]
- **PASSED — format.pdf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.pdf", 0.7545123745264949]]
- **PASSED — format.ppt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.ppt", 0.7965551766046933]]
- **PASSED — format.pptx**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.pptx", 0.7864165298588883]]
- **PASSED — format.rtf**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.rtf", 0.7521867799868663]]
- **PASSED — format.tsv**: All checks passed
  Answer: The approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.tsv", 0.6838637301256024]]
- **PASSED — format.txt**: All checks passed
  Answer: The launch approval code is ORBIT-7429. (from [1])
  Sources: [["sample.txt", 0.7497087738381367]]
- **PASSED — format.xls**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.xls", 0.7074115841932496], ["sample.xls", 0.5439730836593597]]
- **PASSED — format.xlsx**: All checks passed
  Answer: According to the provided context, the approval code for Engine is ORBIT-7429. (from [1])
  Sources: [["sample.xlsx", 0.7040042711522716], ["sample.xlsx", 0.5364487204431654]]
- **FAILED — format.xml**: Failed: required_facts, citations, expected_cited_sources
  Answer: I could not find this information in the documents.
  Sources: [["sample.xml", 0.5457767716595341]]

## Reproduce

```bash
pipenv run python eval_harness.py --mock --out output/eval-mock
pipenv run python eval_harness.py --chat-model qwen2.5:0.5b --out output/eval-live
```
