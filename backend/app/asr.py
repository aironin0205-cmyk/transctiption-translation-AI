import assemblyai as aai
from .config import settings

def transcribe_with_assemblyai(audio_path: str) -> dict:
    aai.settings.api_key = settings.assemblyai_api_key
    config = aai.TranscriptionConfig(
        punctuate=True,
        format_text=True,
        speaker_labels=False,
        language_code="en_us",
    )
    t = aai.Transcriber().transcribe(audio_path, config=config)
    if t.status == aai.TranscriptStatus.error:
        raise RuntimeError(t.error)
    out = {"text": t.text or "", "words": []}
    if getattr(t, "words", None):
        for w in t.words:
            out["words"].append({"text": w.text, "start": w.start, "end": w.end})
    return out
