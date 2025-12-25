from celery import shared_task
from sqlalchemy.orm import Session
from .db import SessionLocal
from .pipeline import run_pipeline

@shared_task(name="run_job_pipeline")
def run_job_pipeline(job_id: str) -> str:
    db: Session = SessionLocal()
    try:
        run_pipeline(db, job_id)
        return "ok"
    finally:
        db.close()
