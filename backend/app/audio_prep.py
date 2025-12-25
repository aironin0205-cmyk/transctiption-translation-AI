import subprocess
from .storage import job_workdir
from .config import settings

def ffmpeg_normalize(input_path: str, job_id: str) -> str:
    wd = job_workdir(job_id)
    out = wd / "normalized.wav"
    cmd = [
        "ffmpeg-normalize", input_path,
        "-o", str(out),
        "-f",
        "-nt", "ebu",
        "-ar", "16000",
        "-c:a", "pcm_s16le",
    ]
    subprocess.check_call(cmd)
    return str(out)

def cobra_vad_optional(input_wav: str, job_id: str) -> str:
    # MVP: If PICOVOICE_ACCESS_KEY not set, skip.
    if not settings.picovoice_access_key:
        return input_wav
    # If you install pv-cobra, implement trimming here.
    return input_wav
