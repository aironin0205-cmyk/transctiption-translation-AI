import hashlib, re, json
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import TMEntry
from .config import settings
from .llm_router import client, call_with_fallbacks

def normalize_for_hash(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def en_hash(s: str) -> str:
    return hashlib.sha256(normalize_for_hash(s).encode("utf-8")).hexdigest()

def embed_texts(texts: List[str]) -> List[List[float]]:
    return client.embed(settings.embedding_model, texts)

def tm_topk(db: Session, emb: List[float], k: int = 8) -> List[TMEntry]:
    stmt = (
        select(TMEntry)
        .where(TMEntry.embedding.is_not(None))
        .order_by(TMEntry.embedding.cosine_distance(emb))
        .limit(k)
    )
    return list(db.execute(stmt).scalars().all())

def composite_confidence(en_text: str, cand_en: str, sim: float) -> float:
    a = en_text.strip()
    b = cand_en.strip()
    if not a or not b:
        return 0.0
    len_ratio = min(len(a), len(b)) / max(len(a), len(b))
    nums_a = re.findall(r"\d+(?:\.\d+)?", a)
    nums_b = re.findall(r"\d+(?:\.\d+)?", b)
    num_match = 1.0 if nums_a == nums_b else 0.0
    conf = 0.75 * sim + 0.15 * len_ratio + 0.10 * num_match
    return float(max(0.0, min(1.0, conf)))

def judge_tm_reuse(db: Session, job_id: str, en_text: str, fa_text: str) -> bool:
    sys = "You are a strict bilingual subtitle QA judge (EN→FA)."
    usr = (
        "Decide if the Persian translation can be reused AS-IS for the English sentence. "
        "Return ONLY JSON: {\"reuse\": true/false, \"reason\": \"...\"}.\n\n"
        f"English: {en_text}\nPersian: {fa_text}"
    )
    content = call_with_fallbacks(
        db=db, job_id=job_id, cue_id=None, agent_name="tm_judge",
        primary_model=settings.model_tm_judge, fallback_models=[],
        messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.0, max_tokens=200, meta={"purpose":"tm_reuse_judge"},
    )
    try:
        obj = json.loads(content.strip())
        return bool(obj.get("reuse"))
    except Exception:
        return False
