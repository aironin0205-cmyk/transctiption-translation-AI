import json
from sqlalchemy.orm import Session
from .models import Job, JobCue, JobGlossaryTerm, TMEntry
from .storage import save_output, save_report, job_workdir
from .audio_prep import ffmpeg_normalize, cobra_vad_optional
from .asr import transcribe_with_assemblyai
from .segmenter import segment_from_words, segment_fallback
from .risk_router import risk_level
from .agents import strategist, terminologist, translator, qa_polisher, librarian_should_store
from .srt_builder import Cue, build_srt, clamp_non_overlapping
from .tm import embed_texts, tm_topk, composite_confidence, judge_tm_reuse, en_hash
from .config import settings

def set_status(db: Session, job: Job, status: str):
    job.status = status
    db.add(job)
    db.commit()

def run_pipeline(db: Session, job_id: str):
    job = db.get(Job, job_id)
    if not job:
        raise RuntimeError("Job not found")

    set_status(db, job, "AUDIO_PREP")
    normalized = ffmpeg_normalize(job.input_uri, job_id)
    normalized = cobra_vad_optional(normalized, job_id)
    job.normalized_uri = normalized
    db.commit()

    set_status(db, job, "ASR")
    asr = transcribe_with_assemblyai(normalized)
    wd = job_workdir(job_id)
    asr_json = wd / "asr.json"
    asr_json.write_text(json.dumps(asr, ensure_ascii=False, indent=2), encoding="utf-8")
    job.asr_json_uri = str(asr_json)
    db.commit()

    set_status(db, job, "SEGMENT")
    words = asr.get("words") or []
    seg = segment_from_words(words) if words else segment_fallback(asr.get("text",""))
    db.query(JobCue).filter(JobCue.job_id == job_id).delete()
    for i, c in enumerate(seg, start=1):
        db.add(JobCue(job_id=job_id, cue_index=i, start_ms=c.start_ms, end_ms=c.end_ms, en_text=c.text))
    db.commit()

    cues = db.query(JobCue).filter(JobCue.job_id == job_id).order_by(JobCue.cue_index).all()
    en_srt = build_srt(clamp_non_overlapping([Cue(i, c.start_ms, c.end_ms, c.en_text) for i,c in enumerate(cues, start=1)]))
    save_output(job_id, "en.srt", en_srt)

    set_status(db, job, "STRATEGY")
    sample_text = (asr.get("text","") or "")[:20000]
    rl = risk_level(sample_text)
    job.risk_level = rl
    db.commit()

    st = strategist(db, job_id, rl, sample_text)
    job.genre = st.get("genre")
    job.tone = st.get("tone")
    job.domain_tags = st.get("domain_tags", [])
    job.difficulty_score = int(st.get("difficulty_score", 5))
    job.strategist_conf = int(st.get("strategist_confidence", 70))
    db.commit()

    set_status(db, job, "TM_GATING")
    cues = db.query(JobCue).filter(JobCue.job_id == job_id).order_by(JobCue.cue_index).all()
    embeddings = embed_texts([c.en_text for c in cues])

    for c, emb in zip(cues, embeddings):
        cands = tm_topk(db, emb, k=8)
        if not cands:
            c.needs_translation = True
            continue
        best = cands[0]
        sim_guess = 0.90
        conf = composite_confidence(c.en_text, best.en_text, sim_guess)
        c.tm_confidence = conf
        if conf >= settings.tm_auto_reuse_threshold:
            c.tm_reused = True
            c.tm_entry_id = best.tm_entry_id
            c.needs_translation = False
            c.fa_text = best.fa_text
        elif conf >= settings.tm_judge_threshold:
            if judge_tm_reuse(db, job_id, c.en_text, best.fa_text):
                c.tm_reused = True
                c.tm_entry_id = best.tm_entry_id
                c.needs_translation = False
                c.fa_text = best.fa_text
            else:
                c.needs_translation = True
        else:
            c.needs_translation = True
    db.commit()

    glossary_terms = []
    if bool(st.get("needs_terminologist")) and job.difficulty_score >= 4:
        set_status(db, job, "TERMS")
        term_out = terminologist(db, job_id, job.difficulty_score, sample_text)
        db.query(JobGlossaryTerm).filter(JobGlossaryTerm.job_id == job_id).delete()
        for t in term_out.get("terms", []):
            db.add(JobGlossaryTerm(
                job_id=job_id,
                en_term=t["en_term"],
                fa_term=t["fa_term"],
                term_type=t.get("term_type"),
                mandatory=bool(t.get("mandatory", True)),
                confidence=t.get("confidence"),
                notes=t.get("notes"),
            ))
            glossary_terms.append(t)
        db.commit()
    else:
        for t in db.query(JobGlossaryTerm).filter(JobGlossaryTerm.job_id == job_id).all():
            glossary_terms.append({"en_term": t.en_term, "fa_term": t.fa_term, "term_type": t.term_type, "mandatory": t.mandatory})

    set_status(db, job, "TRANSLATE")
    need = [c for c in cues if c.needs_translation]
    bs = int(settings.translation_batch_size)
    for i in range(0, len(need), bs):
        batch = need[i:i+bs]
        payload = [{"cue_id": c.cue_id, "start_ms": c.start_ms, "end_ms": c.end_ms, "en_text": c.en_text} for c in batch]
        out = translator(db, job_id, job.difficulty_score, glossary_terms, payload)
        for c in batch:
            c.fa_text = out.get(c.cue_id, c.fa_text)
    db.commit()

    set_status(db, job, "QA")
    payload = [{"cue_id": c.cue_id, "start_ms": c.start_ms, "end_ms": c.end_ms, "en_text": c.en_text} for c in cues]
    translations = {c.cue_id: (c.fa_text or "") for c in cues}
    qa = qa_polisher(db, job_id, job.difficulty_score, glossary_terms, payload, translations)

    for c in cues:
        c.fa_text_qa = qa.get("polished", {}).get(c.cue_id, c.fa_text or "")
        c.qa_score = qa.get("qa_scores", {}).get(c.cue_id)
        c.issues = {"issues": qa.get("issues", {}).get(c.cue_id, [])}
    db.commit()

    set_status(db, job, "FINALIZE")
    fa_cues = [Cue(i, c.start_ms, c.end_ms, (c.fa_text_qa or c.fa_text or "").strip()) for i, c in enumerate(cues, start=1)]
    fa_srt = build_srt(clamp_non_overlapping(fa_cues))
    job.final_srt_uri = save_output(job_id, "fa.srt", fa_srt)
    db.commit()

    rep = {
        "job_id": job_id,
        "risk_level": job.risk_level,
        "difficulty_score": job.difficulty_score,
        "genre": job.genre,
        "tone": job.tone,
        "domain_tags": job.domain_tags,
        "cues": [
            {
                "cue_index": c.cue_index,
                "cue_id": c.cue_id,
                "tm_reused": c.tm_reused,
                "tm_confidence": float(c.tm_confidence) if c.tm_confidence is not None else None,
                "qa_score": float(c.qa_score) if c.qa_score is not None else None,
                "issues": (c.issues or {}).get("issues", []),
            } for c in cues
        ]
    }
    save_report(job_id, "qa_report.json", json.dumps(rep, ensure_ascii=False, indent=2))

    set_status(db, job, "LIBRARIAN")
    stored = 0
    for c in cues:
        issues = (c.issues or {}).get("issues", [])
        if not librarian_should_store(c.qa_score, issues):
            continue
        en = c.en_text.strip()
        fa = (c.fa_text_qa or c.fa_text or "").strip()
        if not en or not fa:
            continue
        h = en_hash(en)
        exists = db.query(TMEntry).filter(TMEntry.en_hash == h).first()
        if exists:
            continue
        emb = embed_texts([en])[0]
        db.add(TMEntry(
            en_text=en, fa_text=fa, en_hash=h,
            domain_tags=job.domain_tags,
            quality_grade="trusted",
            qa_score=float(c.qa_score) if c.qa_score is not None else None,
            confidence=90,
            embedding=emb
        ))
        stored += 1
    db.commit()
    save_report(job_id, "librarian.json", json.dumps({"stored_tm_entries": stored}, ensure_ascii=False, indent=2))

    set_status(db, job, "DONE")
