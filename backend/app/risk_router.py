import re
from typing import Literal

TECH = re.compile(r"\b(API|HTTP|SQL|Docker|Kubernetes|TLS|DNS|VLAN|OAuth|JWT|GPU|RAM|CPU|CLI|Regex)\b", re.I)
MATH = re.compile(r"[=+\-*/]|(\b\d+(\.\d+)?\b)")
LEGAL = re.compile(r"[§¶]|(\bAct\b|\bRegulation\b|\bArticle\b)", re.I)
MED = re.compile(r"\b(mg|ml|ICD|dose|diagnosis|patient)\b", re.I)

def risk_level(text: str) -> Literal["low","medium","high"]:
    text = text or ""
    length = len(text)
    long_sent = sum(1 for s in re.split(r"[.!?]\s+", text) if len(s.split()) >= 25)
    markers = sum(bool(r.search(text)) for r in [TECH, MATH, LEGAL, MED])

    if length > 25000 or markers >= 3 or long_sent >= 8:
        return "high"
    if length > 9000 or markers >= 2 or long_sent >= 4:
        return "medium"
    return "low"
