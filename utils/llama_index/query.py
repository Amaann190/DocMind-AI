"""Query normalization: tokenization, stemming, fillers, synonyms and rewriting."""
import re

# Lazy Porter stemmer (pure Python, no model data): normalizes word endings
# ("running" -> "run") so BM25 keyword matching understands inflected forms
# of the query without any GPU work.
_STEMMER = None


def _stemmer():
    global _STEMMER
    if _STEMMER is None:
        from nltk.stem import PorterStemmer

        _STEMMER = PorterStemmer()
    return _STEMMER


def _bm25_tokens(text):
    """Lowercase word tokens without punctuation, stemmed for BM25 matching.

    Hyphens are split ("30-days" -> "30", "day") and single-letter tokens
    dropped ("company's" -> "company"). Applied symmetrically to the corpus
    and queries, so "30-days" and "30 days" match each other.
    """
    stemmer = _stemmer()
    text = text.lower().replace("-", " ")
    words = re.findall(r"[^\W_]+", text, flags=re.UNICODE)
    return [stemmer.stem(word) for word in words if len(word) > 1 or word.isdecimal()]


# Curated keyword synonyms used to expand SHORT queries for BM25 matching
# only. The vector search still uses the original question, so the expansion
# cannot dilute semantics: it only widens exact keyword recall. Entries are
# written as plain words and stemmed once with the same stemmer as the corpus
# (see _stemmed_synonyms), so every key and value can actually match.
# Kept deliberately small: every entry must be high-confidence.
_QUERY_SYNONYMS = {
    "refund": {"return", "money", "back"},
    "policy": {"rule", "guideline", "term", "condition"},
    "purchase": {"buy", "order", "acquire"},
    "buy": {"purchase", "order"},
    "salary": {"pay", "wage", "income", "compensation"},
    "vacation": {"leave", "holiday", "timeoff"},
    "job": {"work", "employment", "position"},
    "cost": {"price", "charge", "fee", "expense"},
    "revenue": {"income", "sales", "earnings"},
    "customer": {"client", "user", "buyer", "consumer"},
    "document": {"file", "report", "paper", "manual"},
    "help": {"assist", "support"},
    "problem": {"issue", "error", "bug"},
    "fix": {"repair", "solve", "correct"},
}
_STEMMED_SYNONYMS = None


def _stemmed_synonyms():
    """Stem the curated synonym table once, exactly like corpus tokens."""
    global _STEMMED_SYNONYMS
    if _STEMMED_SYNONYMS is None:
        stem = _stemmer().stem
        table = {}
        for word, synonyms in _QUERY_SYNONYMS.items():
            table.setdefault(stem(word), set()).update(stem(s) for s in synonyms)
        _STEMMED_SYNONYMS = table
    return _STEMMED_SYNONYMS


def _bm25_expanded_tokens(tokens):
    """Widen short queries with curated synonyms for BM25 matching.

    ``tokens`` must already be stemmed (output of ``_bm25_tokens``). Long,
    specific queries are left untouched: they already contain enough exact
    terms, and expanding them would add noise.
    """
    if len(tokens) > 4:
        return tokens
    expanded = list(tokens)
    synonyms = _stemmed_synonyms()
    # Treat "money back" as a phrase, not either ambiguous word in isolation.
    if "money" in tokens and "back" in tokens:
        expanded.extend(word for word in ("refund", "return") if word not in expanded)
    for token in tokens:
        for synonym in sorted(synonyms.get(token, ())):
            if synonym not in expanded:
                expanded.append(synonym)
    return expanded


# Numeric words → digits so "thirty days" matches "30 days" without embedding help.
_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100",
}


# Filler words that carry no retrieval value: removing them helps BM25
# weight the real terms and slightly improves vector matching too.
# Includes common Hinglish/Hindi question words (batao, kya, hai, ...) so
# mixed-language queries retrieve the right chunks as well.
_QUERY_FILLER_WORDS = {
    "please", "tell", "me", "about", "can", "you", "could", "would",
    "i", "want", "to", "know", "what", "is", "are", "was", "were",
    "the", "a", "an", "of", "for", "with", "and", "or", "do", "does",
    "batao", "bata", "kya", "kyaa", "hai", "hain", "kaise", "karke",
    "karne", "mein", "ho", "hoga",
}
_FILLER_STEMS = None


def _filler_stems():
    """Filler words in the stemmed form they take after ``_bm25_tokens``."""
    global _FILLER_STEMS
    if _FILLER_STEMS is None:
        stem = _stemmer().stem
        _FILLER_STEMS = frozenset(stem(word) for word in _QUERY_FILLER_WORDS)
    return _FILLER_STEMS


# Words that, on their own, ask about a document as a whole ("summarize this
# file", "what is the website about"). Stemmed once on first use.
_OVERVIEW_WORDS = {
    "summary", "summarize", "summarise", "summarization", "overview",
    "document", "file", "upload", "uploaded", "key", "point", "main", "my",
    "website", "page", "connect", "connected", "this", "suppose", "supposed",
    "purpose",
}
_OVERVIEW_STEMS = None


def _overview_stems():
    global _OVERVIEW_STEMS
    if _OVERVIEW_STEMS is None:
        stem = _stemmer().stem
        _OVERVIEW_STEMS = frozenset(stem(word) for word in _OVERVIEW_WORDS)
    return _OVERVIEW_STEMS


def _rewrite_query(query):
    """Light, rule-based query cleanup: no LLM calls, no GPU cost.

    Returns space-separated BM25 tokens, stemmed exactly once (the same
    normalization the corpus receives), so "documents", "documented" and
    "documenting" all match "document" in the index. Stemming twice is not
    safe: Porter is not idempotent ("purchases" -> "purchas" -> "purcha").
    """
    # Normalize numeric words before tokenization so "thirty days" == "30 days"
    lowered = query.lower()
    for word, digit in _NUMBER_WORDS.items():
        lowered = re.sub(rf"\b{re.escape(word)}\b", digit, lowered)
    tokens = _bm25_tokens(lowered)
    fillers = _filler_stems()
    words = [word for word in tokens if word not in fillers]
    return " ".join(words or tokens)
