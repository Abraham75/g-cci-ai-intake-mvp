RAG_CORPUS = [
    "Georgia tort law",
    "Comparative negligence",
    "Statutes of limitation",
    "FMCSA regulations",
    "Georgia trucking case law",
    "Internal Graham Firm educational materials"
]

FILTERS = [
    "Georgia advertising rules",
    "ABA Model Rules 7.1–7.3",
    "No legal advice",
    "No guarantees"
]

def evaluate_compliance(text: str):
    flags = []
    banned = ["guarantee", "we will win", "legal advice"]

    for b in banned:
        if b in text.lower():
            flags.append("DISALLOWED_LANGUAGE")

    status = "PASS"
    if flags:
        status = "REVIEW"

    return status, FILTERS, flags
