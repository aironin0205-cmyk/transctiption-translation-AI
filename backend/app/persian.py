import re
ARABIC_TO_PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

def to_persian_digits(s: str) -> str:
    return s.translate(ARABIC_TO_PERSIAN_DIGITS)

def normalize_persian_spacing(s: str) -> str:
    s = re.sub(r"[ \t]+", " ", (s or "")).strip()
    s = re.sub(r"\s*([،؛:!؟])\s*", r"\1 ", s)
    s = re.sub(r"\s*\.\s*", ". ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def strip_speaker_ids(s: str) -> str:
    s = (s or "").strip()
    return re.sub(r"^(speaker\s*\d+|[A-Z][A-Z0-9 _-]{1,30})\s*:\s*", "", s, flags=re.IGNORECASE).strip()
