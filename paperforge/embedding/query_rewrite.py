"""Query expansion for @ Deep Search — abbreviation expansion and synonym mapping."""

from __future__ import annotations

import re

# Common orthopedic/medical abbreviations used in literature
ABBREVIATIONS: dict[str, str] = {
    "ACL": "anterior cruciate ligament",
    "PCL": "posterior cruciate ligament",
    "MCL": "medial collateral ligament",
    "LCL": "lateral collateral ligament",
    "VTE": "venous thromboembolism",
    "DVT": "deep vein thrombosis",
    "RCT": "rotator cuff",
    "OA": "osteoarthritis",
    "THA": "total hip arthroplasty",
    "TKA": "total knee arthroplasty",
    "ROM": "range of motion",
    "BMI": "body mass index",
    "NSAID": "nonsteroidal anti-inflammatory drug",
    "RSA": "reverse shoulder arthroplasty",
    "TSA": "total shoulder arthroplasty",
    "ORIF": "open reduction internal fixation",
    "TFCC": "triangular fibrocartilage complex",
    "CCI": "charlson comorbidity index",
    "ASA": "american society of anesthesiologists",
    "PROM": "patient reported outcome measure",
    "PROMIS": "patient reported outcomes measurement information system",
}

MEDICAL_SYNONYMS: dict[str, list[str]] = {
    "knee": ["knee joint", "genu"],
    "shoulder": ["glenohumeral joint", "shoulder joint"],
    "hip": ["hip joint", "acetabulofemoral joint"],
    "elbow": ["elbow joint"],
    "ankle": ["ankle joint", "talocrural joint"],
    "wrist": ["wrist joint", "radiocarpal joint"],
    "spine": ["vertebral column", "spinal column"],
    "fracture": ["fracture", "break"],
    "repair": ["repair", "reconstruction", "fixation"],
    "replacement": ["arthroplasty", "replacement"],
    "complication": ["complication", "adverse event", "comorbidity"],
    "pain": ["pain", "analgesia", "pain management"],
}
def expand_query(query: str) -> list[str]:
    """Expand query by replacing known abbreviations with full forms.

    Returns a list of query variants with the original query first,
    followed by expanded versions (one per abbreviation expanded).
    """
    variants = [query]
    seen: set[str] = set()

    # Try expanding all abbreviations
    expanded = query
    for abbr, full in ABBREVIATIONS.items():
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        if pattern.search(query):
            candidate = pattern.sub(full, expanded)
            if candidate != expanded and candidate not in seen:
                seen.add(candidate)
                variants.append(candidate)

    # If no abbreviation was expanded, try synonym expansion
    if len(variants) == 1:
        for term, synonyms in MEDICAL_SYNONYMS.items():
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            if pattern.search(query):
                for syn in synonyms:
                    candidate = pattern.sub(syn, query)
                    if candidate != query and candidate not in seen:
                        seen.add(candidate)
                        variants.append(candidate)
                break  # one synonym expansion is enough

    return variants
