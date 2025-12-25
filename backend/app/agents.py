import json
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from .config import settings
from .llm_router import call_with_fallbacks, models_from_csv
from .persian import normalize_persian_spacing, strip_speaker_ids

def strategist(db: Session, job_id: str, risk_level: str, text: str) -> dict:
    sys = "You are Strategist Agent for EN→FA subtitles. Be precise and structured."
    usr = f'''
Output STRICT JSON:
{{
  "genre": "tech_tutorial|interview|documentary|casual|academic|legal|medical|entertainment|other",
  "tone": "formal|neutral|casual|humorous|persuasive|emotional",
  "domain_tags": ["..."],
  "difficulty_score": 1-10,
  "strategist_confidence": 0-100,
  "needs_terminologist": true/false,
  "notes_for_translator": ["..."]
}}

Transcript:
{text}
'''
    if risk_level == "high":
        primary = settings.model_strategist_high
        fallbacks = models_from_csv(settings.fallback_strategist_high)
    else:
        primary = settings.model_strategist_low
        fallbacks = ["anthropic/claude-haiku-4.5", "deepseek/deepseek-v3.2"]

    content = call_with_fallbacks(
        db, job_id, None, "strategist", primary, fallbacks,
        [{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.1, max_tokens=800, meta={"risk_level": risk_level}
    )
    return json.loads(content.strip())

def terminologist(db: Session, job_id: str, difficulty: int, transcript: str) -> dict:
    sys = "You are Terminologist Agent for EN→FA subtitles. Build a strict bilingual glossary."
    usr = f'''
Extract specialized terms and output STRICT JSON:
{{
  "terms": [
    {{
      "en_term": "...",
      "fa_term": "...",
      "term_type": "jargon|product|acronym|name|other",
      "mandatory": true,
      "confidence": 0-100,
      "notes": "short context"
    }}
  ]
}}

Transcript:
{transcript}
'''
    primary = settings.model_terminologist_hard if difficulty >= 8 else settings.model_terminologist_mid
    fallbacks = models_from_csv(settings.fallback_terminologist)
    content = call_with_fallbacks(
        db, job_id, None, "terminologist", primary, fallbacks,
        [{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.1, max_tokens=1400, meta={"difficulty": difficulty}
    )
    return json.loads(content.strip())

def translator(db: Session, job_id: str, difficulty: int, glossary: List[Dict[str, Any]], cues: List[Dict[str, Any]]) -> Dict[str, str]:
    sys = "You are Translator Agent for EN→FA subtitles. Follow glossary strictly. No speaker IDs."
    glossary_text = "\n".join([f"- {t['en_term']} => {t['fa_term']}" for t in glossary]) if glossary else "(none)"
    usr = f'''
Translate cues to Persian. Output STRICT JSON mapping cue_id -> Persian text. No markdown.

Glossary (MANDATORY):
{glossary_text}

Cues JSON:
{json.dumps(cues, ensure_ascii=False)}
'''
    if difficulty <= 3:
        primary = settings.model_translator_easy
        fallbacks = ["google/gemini-3-flash", "deepseek/deepseek-v3.2"]
    elif difficulty <= 7:
        primary = settings.model_translator_mid
        fallbacks = models_from_csv(settings.fallback_translator_mid)
    else:
        primary = settings.model_translator_hard
        fallbacks = models_from_csv(settings.fallback_translator_hard)

    content = call_with_fallbacks(
        db, job_id, None, "translator", primary, fallbacks,
        [{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.2, max_tokens=2600, meta={"difficulty": difficulty, "batch_size": len(cues)}
    )
    obj = json.loads(content.strip())
    out = {}
    for k,v in obj.items():
        s = normalize_persian_spacing(strip_speaker_ids(str(v)))
        out[str(k)] = s
    return out

def qa_polisher(db: Session, job_id: str, difficulty: int, glossary: List[Dict[str, Any]], cues: List[Dict[str, Any]], translations: Dict[str, str]) -> dict:
    sys = "You are QA & Polisher Agent for EN→FA subtitles. Fix meaning, glossary compliance, punctuation, subtitle readability."
    glossary_text = "\n".join([f"- {t['en_term']} => {t['fa_term']}" for t in glossary]) if glossary else "(none)"
    payload = {"cues": cues, "translations": translations}
    usr = f'''
Output STRICT JSON:
{{
  "polished": {{ "cue_id": "fa_text" }},
  "qa_scores": {{ "cue_id": 0-100 }},
  "issues": {{ "cue_id": ["..."] }}
}}

Glossary (MANDATORY):
{glossary_text}

Input JSON:
{json.dumps(payload, ensure_ascii=False)}
'''
    if difficulty <= 3:
        primary = settings.model_qa_easy
        fallbacks = ["anthropic/claude-haiku-4.5"]
    else:
        primary = settings.model_qa_hard
        fallbacks = models_from_csv(settings.fallback_qa_hard)

    content = call_with_fallbacks(
        db, job_id, None, "qa_polisher", primary, fallbacks,
        [{"role":"system","content":sys},{"role":"user","content":usr}],
        temperature=0.1, max_tokens=2600, meta={"difficulty": difficulty}
    )
    obj = json.loads(content.strip())
    polished = {}
    for k,v in obj.get("polished", {}).items():
        polished[str(k)] = normalize_persian_spacing(strip_speaker_ids(str(v)))
    obj["polished"] = polished
    return obj

def librarian_should_store(qa_score, issues) -> bool:
    if qa_score is None or float(qa_score) < 85:
        return False
    issues = issues or []
    bad = set(issues)
    return ("meaning_drift" not in bad and "numbers_mismatch" not in bad)
