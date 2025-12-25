from dataclasses import dataclass
from typing import List, Dict, Any
import re
from .config import settings

@dataclass
class SegCue:
    start_ms: int
    end_ms: int
    text: str

def segment_from_words(words: List[Dict[str, Any]]) -> List[SegCue]:
    # Heuristics:
    # - break on pauses > 450ms
    # - enforce max cue duration
    # - enforce rough char limit (max_lines * max_chars_per_line)
    if not words:
        return []
    max_chars = settings.max_chars_per_line * settings.max_lines
    min_ms = settings.min_cue_ms
    max_ms = settings.max_cue_ms

    cues: List[SegCue] = []
    buf = []
    cue_start = int(words[0].get("start", 0))
    last_end = int(words[0].get("end", cue_start))

    def flush(end_ms: int):
        nonlocal buf, cue_start
        if not buf:
            return
        text = " ".join(buf).strip()
        if text:
            cues.append(SegCue(int(cue_start), int(end_ms), text))
        buf = []

    for w in words:
        t = str(w.get("text", "")).strip()
        if not t:
            continue
        start = int(w.get("start", last_end))
        end = int(w.get("end", start))
        pause = start - last_end

        if buf and pause > 450 and (last_end - cue_start) >= min_ms:
            flush(last_end)
            cue_start = start

        buf.append(t)
        last_end = end

        if (last_end - cue_start) >= max_ms:
            flush(last_end)
            cue_start = last_end

        if buf and len(" ".join(buf)) >= max_chars:
            flush(last_end)
            cue_start = last_end

    flush(last_end)

    fixed = []
    for c in cues:
        s = c.start_ms
        e = max(c.end_ms, s + 200)
        fixed.append(SegCue(s, e, c.text))
    return fixed

def segment_fallback(transcript_text: str) -> List[SegCue]:
    text = (transcript_text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[\.!?])\s+", text)
    parts = [p.strip() for p in parts if p.strip()]
    cues = []
    t = 0
    for p in parts:
        est = max(1200, 150 * max(1, len(p.split())))
        cues.append(SegCue(t, t + est, p))
        t += est
    return cues
