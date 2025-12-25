import uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from .db import SessionLocal, init_db
from .models import Job
from .storage import save_upload, ensure_dirs
from .worker import celery_app

app = FastAPI(title="Subtitle AI MVP", version="0.1.0")

@app.on_event("startup")
def _startup():
    ensure_dirs()
    init_db()

def db() -> Session:
    return SessionLocal()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/jobs")
async def create_job(file: UploadFile = File(...)):
    s = db()
    try:
        job_id = str(uuid.uuid4())
        data = await file.read()
        input_path = save_upload(job_id, file.filename, data)
        job = Job(job_id=job_id, status="UPLOADED", input_uri=input_path, input_type="upload")
        s.add(job)
        s.commit()
        celery_app.send_task("run_job_pipeline", args=[job_id])
        return {"job_id": job_id, "status": job.status}
    finally:
        s.close()

@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    s = db()
    try:
        job = s.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return {
            "job_id": job.job_id,
            "status": job.status,
            "risk_level": job.risk_level,
            "difficulty_score": job.difficulty_score,
            "strategist_conf": job.strategist_conf,
            "genre": job.genre,
            "tone": job.tone,
            "domain_tags": job.domain_tags,
        }
    finally:
        s.close()

@app.get("/jobs/{job_id}/download/{kind}")
def download(job_id: str, kind: str):
    base = Path("/data")
    m = {
        "en_srt": base / "outputs" / f"{job_id}__en.srt",
        "fa_srt": base / "outputs" / f"{job_id}__fa.srt",
        "qa_report": base / "reports" / f"{job_id}__qa_report.json",
        "librarian": base / "reports" / f"{job_id}__librarian.json",
    }
    p = m.get(kind)
    if not p:
        raise HTTPException(400, "Invalid kind")
    if not p.exists():
        raise HTTPException(404, "File not ready")
    return FileResponse(str(p), filename=p.name)
