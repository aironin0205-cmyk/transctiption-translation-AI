from pathlib import Path
from .config import settings

BASE = Path(settings.data_dir)

def ensure_dirs():
    for d in ["uploads", "work", "outputs", "reports"]:
        (BASE / d).mkdir(parents=True, exist_ok=True)

def save_upload(job_id: str, filename: str, data: bytes) -> str:
    ensure_dirs()
    safe = filename.replace("/", "_")
    p = BASE / "uploads" / f"{job_id}__{safe}"
    p.write_bytes(data)
    return str(p)

def job_workdir(job_id: str) -> Path:
    ensure_dirs()
    p = BASE / "work" / job_id
    p.mkdir(parents=True, exist_ok=True)
    return p

def save_output(job_id: str, name: str, text: str) -> str:
    ensure_dirs()
    p = BASE / "outputs" / f"{job_id}__{name}"
    p.write_text(text, encoding="utf-8")
    return str(p)

def save_report(job_id: str, name: str, text: str) -> str:
    ensure_dirs()
    p = BASE / "reports" / f"{job_id}__{name}"
    p.write_text(text, encoding="utf-8")
    return str(p)
