"""Withhold instruction-like sentences in retrieved text before it reaches the model.

Retrieved documents are data. Prompt wording alone does not reliably stop local
models from obeying sentences such as "ignore previous instructions" inside a
document (qwen2.5:0.5b answers "PWNED" in the injection check, as llama3 did
before the boundary reminder). This module replaces such sentences with a
marker; the UI still shows the original passage.

It is a pattern filter, not a guarantee: it targets common injection families
and can be evaded by rewording. Every pattern must also leave ordinary
document sentences alone; tests/test_injection.py holds both sides.
"""
import re

REDACTED_INSTRUCTION = "[instruction-like text from the document withheld]"

_VERB = r"(?:answer|respond|reply|say|output|print|reveal|repeat|leak|write|summari[sz]e|stop|ignore)"
_AI = r"(?:\bAI\b|\bassistant\b|\blanguage model\b|\bLLM\b|\bchatbot\b|\bmodel reading\b)"

_PATTERNS = [
    # Override: "ignore/disregard/forget/override ... previous/your ... instructions/rules".
    re.compile(r"\b(?:ignore|disregard|forget|override|bypass)\b[^.!?\n]{0,40}"
               r"\b(?:previous|prior|above|earlier|preceding|all|any|your|these|the)\b[^.!?\n]{0,25}"
               r"\b(?:instructions?|prompts?|rules|directions|guidelines|context|system message|messages)\b",
               re.IGNORECASE),
    # "answer/say X instead" as a command: at sentence start, after punctuation or a conjunction.
    re.compile(r"(?:^\s*|[,;:]\s*|\b(?:and|then|just|now|please)\s+)"
               r"(?:answer|respond|reply|say|output|print)\b[^.!?\n]{0,40}\binstead\b", re.IGNORECASE),
    re.compile(r"\binstead,?\s+(?:answer|respond|reply|say|output|print)\b", re.IGNORECASE),
    re.compile(r"\binstead of (?:answering|responding|replying)\b", re.IGNORECASE),
    # Role and chat-template markers that try to open a new prompt turn.
    re.compile(r"^\s*(?:system|assistant|user|AI)\s*:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"<\|(?:im_start|im_end|system|user|assistant)\|>|\[/?INST\]|###\s*(?:instruction|system)\b",
               re.IGNORECASE),
    # Persona and jailbreak requests.
    re.compile(r"\byou are now (?:a|an|the|in|my|acting|free|unrestricted|DAN)\b|\bdeveloper mode\b|\bjailbr(?:eak|oken)\b"
               r"|\bpretend (?:you are|to be)\b|\bact as (?:DAN\b|an? (?:unrestricted|unfiltered|uncensored))",
               re.IGNORECASE),
    re.compile(r"\bnew (?:system )?instructions?\s*:", re.IGNORECASE),
    re.compile(r"\b(?:reveal|print|show|output|repeat|leak)\s+(?:your|the)\s+(?:system prompt|hidden|secret)",
               re.IGNORECASE),
    # A command addressed to the AI reading the document.
    re.compile(rf"{_AI}[^.!?\n]{{0,60}}\b{_VERB}\b|\b{_VERB}\b[^.!?\n]{{0,30}}(?:if you are|as) an? {_AI}",
               re.IGNORECASE),
]
# A sentence, or a line on its own (role markers and template tokens are line-based).
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]*\n?|\n")


def is_instruction_like(sentence):
    """Whether a sentence addresses the model rather than stating document content."""
    return any(pattern.search(sentence) for pattern in _PATTERNS)


def withhold_instructions(text):
    """Replace instruction-like sentences in retrieved text with a marker."""
    parts = []
    for sentence in _SENTENCE.findall(text):
        if is_instruction_like(sentence):
            parts.append(REDACTED_INSTRUCTION + ("\n" if sentence.endswith("\n") else " "))
        else:
            parts.append(sentence)
    return "".join(parts)
