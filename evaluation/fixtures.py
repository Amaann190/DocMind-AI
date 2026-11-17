"""Small fixture corpus and probe queries for the structural suites."""


DOCS = {
    "refund_policy.txt": (
        "Refund Policy\n"
        "Full refunds are available within 30 days of purchase. "
        "Electronics are covered for 15 days only. "
        "Contact support@docmind.test for returns. "
        "All refunds are processed within 5 business days."
    ),
    "annual_report.txt": (
        "Annual Report 2024\n"
        "Revenue grew 23% to $4.2M in fiscal year 2024. "
        "Community outreach expanded to 12 new districts. "
        "Operating costs were reduced by 8% through automation."
    ),
    "python_guide.txt": (
        "Python Guide — Fetching URLs\n"
        "Use requests.get('https://example.com') to fetch web content. "
        "Set timeout=10 to avoid hanging. "
        "Handle errors with try/except and check response.status_code."
    ),
    "hr_policy.txt": (
        "HR Policy — Leave\n"
        "Employees receive 20 days of annual leave and 10 days of sick leave per year. "
        "Work from home is allowed 2 days per week with manager approval."
    ),
    "cooking.txt": (
        "Cooking — Pasta Recipe\n"
        "Boil water, add pasta and cook 10 minutes. "
        "Add tomatoes, basil, and olive oil. Serve warm."
    ),
}


# Retrieval queries — each maps to a feature under test
QUERIES = [
    {"query": "What is the refund policy?", "expected": "refund_policy.txt", "feature": "basic"},
    {"query": "money back rules", "expected": "refund_policy.txt", "feature": "synonym"},
    {"query": "30-day returns", "expected": "refund_policy.txt", "feature": "hyphen"},
    {"query": "refund policy batao", "expected": "refund_policy.txt", "feature": "hinglish"},
    {"query": "annual report revenue growth", "expected": "annual_report.txt", "feature": "title-aware"},
    {"query": "How to fetch a URL in Python?", "expected": "python_guide.txt", "feature": "basic"},
    {"query": "How many leave days per year?", "expected": "hr_policy.txt", "feature": "basic"},
    {"query": "pasta cooking time", "expected": "cooking.txt", "feature": "basic"},
    {"query": "What is the capital of France?", "expected": None, "feature": "no-match"},
    {"query": "quantum physics equations", "expected": None, "feature": "no-match"},
    {"query": "refunded purchases", "expected": "refund_policy.txt", "feature": "stemming"},
    {"query": "tell me about the annual report", "expected": "annual_report.txt", "feature": "filler-filter"},
    {"query": "what about purchases?", "expected": "refund_policy.txt", "feature": "stemming"},
    {"query": "Who painted the Mona Lisa?", "expected": None, "feature": "no-match"},
    {"query": "How do I repot an orchid?", "expected": None, "feature": "no-match"},
    {"query": "Explain the plot of Hamlet", "expected": None, "feature": "no-match"},
    {"query": "melting point of tungsten", "expected": None, "feature": "no-match"},
]


# Retrieval ablation: the four configurations compared in the results paper.
RETRIEVAL_CONFIGS = ("vector_only", "bm25_only", "hybrid_no_floor", "full")
